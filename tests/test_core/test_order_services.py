import pytest
from unittest.mock import MagicMock, AsyncMock, ANY
from fastapi import HTTPException

from app.services.order_services import OrderService, NotFoundError
from app.models.order_models import OrderItem, OrderStatus
from app.schemas.order_schemas import OrderCreate
from datetime import datetime, timezone


pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo():
    repo = MagicMock()
    repo.db = MagicMock()
    return repo


@pytest.fixture
def publisher():
    return AsyncMock()


@pytest.fixture
def service(repo, publisher):
    return OrderService(repo, publisher)


# ==========================================================
# get_order / get_all_orders
# ==========================================================

def test_get_order_found(service, repo):
    order = MagicMock(id=1)
    repo.get.return_value = order
    result = service.get_order(1)
    assert result is order


def test_get_order_not_found(service, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        service.get_order(999)


def test_get_all_orders(service, repo):
    repo.list.return_value = ["a", "b"]
    result = service.get_all_orders()
    assert result == ["a", "b"]


# ==========================================================
# create_and_request_price
# ==========================================================

async def test_create_and_request_price_success(service, repo, publisher):
    order_in = OrderCreate(customer_id=1, items=[{"product_id": 1, "quantity": 2}])
    fake_order = MagicMock(id=123, created_at=None)
    repo.create.return_value = fake_order

    result = await service.create_and_request_price(order_in)

    assert result == fake_order
    assert publisher.publish_message.await_count == 2
    calls = [c.args[0] for c in publisher.publish_message.await_args_list]
    assert "order.created" in calls
    assert "order.request_price" in calls


async def test_create_and_request_price_empty_items(service):
    order_in = OrderCreate(customer_id=1, items=[])
    with pytest.raises(HTTPException) as e:
        await service.create_and_request_price(order_in)
    assert e.value.status_code == 400


# ==========================================================
# update_order_status
# ==========================================================

async def test_update_order_status_success(service, repo, publisher):
    order = MagicMock(id=1, status=OrderStatus.PENDING, updated_at=None, customer_id=1)
    repo.get.return_value = order

    result = await service.update_order_status(1, OrderStatus.CONFIRMED)
    assert result.status == OrderStatus.CONFIRMED
    publisher.publish_message.assert_awaited_once()
    repo.db.commit.assert_called_once()


async def test_update_order_status_not_found(service, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        await service.update_order_status(1, OrderStatus.CONFIRMED)


async def test_update_order_status_same_status(service, repo, publisher):
    order = MagicMock(id=1, status=OrderStatus.PENDING)
    repo.get.return_value = order
    result = await service.update_order_status(1, OrderStatus.PENDING)
    # no-op → pas de publish
    publisher.publish_message.assert_not_awaited()
    assert result == order


# ==========================================================
# update_order_items
# ==========================================================

def _fake_order_with_items():
    order = MagicMock(id=1, status=OrderStatus.PENDING, updated_at=datetime.now(timezone.utc))
    order.items = [
        OrderItem(product_id=1, quantity=2, unit_price=5, line_total=10, total=10, order=None)
    ]
    return order


async def test_update_order_items_modify_existing(service, repo, publisher):
    order = _fake_order_with_items()
    repo.get.return_value = order

    items = [{"product_id": 1, "quantity": 5, "unit_price": 2}]
    result = await service.update_order_items(1, items)

    assert result.items[0].quantity == 5
    assert result.items[0].unit_price == 2
    publisher.publish_message.assert_any_await("order.updated", ANY)



async def test_update_order_items_add_new_item(service, repo, publisher):
    order = _fake_order_with_items()
    repo.get.return_value = order

    items = [
        {"product_id": 1, "quantity": 2, "unit_price": 5},  # existing
        {"product_id": 2, "quantity": 1, "unit_price": 10},  # new
    ]
    result = await service.update_order_items(1, items)

    pids = {it.product_id for it in result.items}
    assert 2 in pids
    assert publisher.publish_message.await_count >= 2  # order.updated + order.items_delta


async def test_update_order_items_remove_item(service, repo, publisher):
    order = _fake_order_with_items()
    repo.get.return_value = order

    items = []  # remove all
    result = await service.update_order_items(1, items)

    assert result.items == []
    assert publisher.publish_message.await_count >= 2  # updated + delta


async def test_update_order_items_new_item_missing_price(service, repo):
    order = _fake_order_with_items()
    repo.get.return_value = order

    items = [{"product_id": 2, "quantity": 1}]  # unit_price manquant
    with pytest.raises(HTTPException):
        await service.update_order_items(1, items)


# ==========================================================
# delete_order
# ==========================================================

async def test_delete_order_success(service, repo, publisher):
    order = _fake_order_with_items()
    repo.get.return_value = order
    repo.delete.return_value = order

    result = await service.delete_order(1)
    assert result == order
    publisher.publish_message.assert_awaited_once()
    repo.delete.assert_called_once_with(1)


async def test_delete_order_not_found(service, repo):
    repo.get.return_value = None
    with pytest.raises(NotFoundError):
        await service.delete_order(1)
