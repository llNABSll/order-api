import pytest
from app.repositories.order_repositories import OrderRepository

class FakeQuery:
    def __init__(self, items=None):
        self._items = items or []
        self._filters = []
        self._offset = 0
        self._limit = None

    def filter(self, *args, **kwargs):
        # try to interpret SQLAlchemy binary expressions to filter our in-memory items
        self._filters.append((args, kwargs))
        if args:
            expr = args[0]
            # SQLAlchemy BinaryExpression exposes .left.key and .right.value (or .right)
            try:
                left = getattr(expr, 'left', None)
                right = getattr(expr, 'right', None)
                key = getattr(left, 'key', None)
                # right may be a BindParameter with .value or a literal
                val = getattr(right, 'value', None) if right is not None else None
                if key is not None:
                    # apply filter to the stored items
                    self._items = [it for it in self._items if getattr(it, key) == val]
            except Exception:
                pass
        return self

    def offset(self, n):
        self._offset = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def all(self):
        return self._items[self._offset:self._offset + (self._limit or len(self._items))]

    def first(self):
        return self._items[0] if self._items else None


class FakeOrder:
    def __init__(self, id=None, customer_id=None, status='pending'):
        self.id = id
        self.customer_id = customer_id
        self.status = status
        self.items = []

    def __repr__(self):
        return f"FakeOrder(id={self.id}, customer_id={self.customer_id})"


@pytest.fixture
def fake_db():
    class DB:
        def __init__(self):
            # store added/deleted objects
            self._added = []
            self._deleted = []
            self._orders = [FakeOrder(id=1, customer_id=10), FakeOrder(id=2, customer_id=20)]
            self._query = FakeQuery(self._orders)

        def query(self, model):
            return self._query

        def add(self, obj):
            self._added.append(obj)

        def commit(self):
            # simulate assigning an id on create
            for obj in self._added:
                if getattr(obj, 'id', None) is None:
                    obj.id = 99
            # clear added for simplicity
            self._added = []

        def refresh(self, obj):
            # noop
            return obj

        def delete(self, obj):
            self._deleted.append(obj)
            try:
                self._orders.remove(obj)
            except ValueError:
                pass

    return DB()


def test_get_existing(fake_db):
    repo = OrderRepository(fake_db)
    o = repo.get(1)
    assert isinstance(o, FakeOrder)
    assert o.id == 1


def test_get_missing(fake_db):
    repo = OrderRepository(fake_db)
    # first returns the first element regardless of id in our fake
    # simulate none by emptying orders
    fake_db._query = FakeQuery([])
    o = repo.get(123)
    assert o is None


def test_list_filters_and_pagination(fake_db):
    repo = OrderRepository(fake_db)
    # test no filters
    res = repo.list()
    assert len(res) == 2

    # test pagination
    fake_db._query = FakeQuery([FakeOrder(id=i) for i in range(10)])
    res2 = repo.list(skip=2, limit=3)
    assert [o.id for o in res2] == [2, 3, 4]

    # test filters by attribute (customer_id)
    fake_db._query = FakeQuery([FakeOrder(id=1, customer_id=5), FakeOrder(id=2, customer_id=5), FakeOrder(id=3, customer_id=7)])
    res3 = repo.list(filters={'customer_id': 5})
    assert all(o.customer_id == 5 for o in res3)


def test_create_assigns_id(fake_db):
    repo = OrderRepository(fake_db)
    from app.schemas.order_schemas import OrderCreate
    oc = OrderCreate(customer_id=123, items=[])
    o = repo.create(oc)
    assert o.id == 99
    assert o.customer_id == 123


def test_update_changes_fields(fake_db):
    repo = OrderRepository(fake_db)
    order = FakeOrder(id=5, customer_id=55, status='pending')
    class DummyUpdate:
        def model_dump(self, exclude_unset=True):
            return {'status': 'shipped'}
    updated = repo.update(order, DummyUpdate())
    assert updated.status == 'shipped'


def test_delete_existing(fake_db):
    repo = OrderRepository(fake_db)
    # set query to return one existing order object
    o = fake_db._orders[0]
    fake_db._query = FakeQuery([o])
    deleted = repo.delete(o.id)
    assert deleted is o
    assert o in fake_db._deleted


def test_delete_missing(fake_db):
    repo = OrderRepository(fake_db)
    fake_db._query = FakeQuery([])
    deleted = repo.delete(999)
    assert deleted is None
