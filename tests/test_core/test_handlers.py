import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.order_services import NotFoundError
from app.models.order_models import OrderStatus

pytestmark = pytest.mark.asyncio


@pytest.fixture
def db_session():
    return MagicMock()


@pytest.fixture
def publisher():
    return AsyncMock()


# =====================================================================
# CUSTOMER DELETED
# =====================================================================

async def test_handle_customer_deleted_no_id(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_deleted
    await handle_customer_deleted({}, db_session, publisher)
    assert "payload sans id" in caplog.text


@patch("app.infra.events.handlers.OrderService")
@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_customer_deleted_success(mock_repo, mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_customer_deleted

    orders = [MagicMock(id=1), MagicMock(id=2)]
    repo = mock_repo.return_value
    repo.list.return_value = orders
    service = mock_service.return_value
    service.update_order_status = AsyncMock()

    await handle_customer_deleted({"id": 123}, db_session, publisher)

    repo.list.assert_called_once_with(filters={"customer_id": 123})
    assert service.update_order_status.await_count == 2


@patch("app.infra.events.handlers.OrderService")
@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_customer_deleted_order_not_found(mock_repo, mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_deleted

    repo = mock_repo.return_value
    repo.list.return_value = [MagicMock(id=1)]
    service = mock_service.return_value
    service.update_order_status = AsyncMock(side_effect=NotFoundError())

    await handle_customer_deleted({"id": 123}, db_session, publisher)
    assert "déjà supprimée" in caplog.text


@patch("app.infra.events.handlers.OrderService")
@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_customer_deleted_no_orders(mock_repo, mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_deleted

    repo = mock_repo.return_value
    repo.list.return_value = []
    service = mock_service.return_value

    await handle_customer_deleted({"id": 456}, db_session, publisher)

    assert "[customer.deleted] 0 commandes trouvées" in caplog.text
    service.update_order_status.assert_not_called()


@patch("app.infra.events.handlers.OrderService")
@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_customer_deleted_generic_error(mock_repo, mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_deleted

    repo = mock_repo.return_value
    repo.list.side_effect = Exception("db fail")

    await handle_customer_deleted({"id": 789}, db_session, publisher)
    assert "erreur inattendue" in caplog.text


# =====================================================================
# CUSTOMER UPDATE ORDER
# =====================================================================

async def test_handle_customer_update_order_invalid_payload(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_update_order
    await handle_customer_update_order({}, db_session, publisher)
    assert "payload invalide" in caplog.text


@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_update_order_success(mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_customer_update_order

    payload = {"order_id": 12, "items": [{"product_id": 3, "quantity": 5}]}
    service = mock_service.return_value
    service.update_order_items = AsyncMock()

    await handle_customer_update_order(payload, db_session, publisher)
    service.update_order_items.assert_awaited_once_with(12, payload["items"])


@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_update_order_not_found(mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_update_order

    payload = {"order_id": 12, "items": [{"product_id": 3, "quantity": 5}]}
    service = mock_service.return_value
    service.update_order_items = AsyncMock(side_effect=NotFoundError())

    await handle_customer_update_order(payload, db_session, publisher)
    assert "introuvable" in caplog.text


@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_update_order_generic_error(mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_update_order

    payload = {"order_id": 99, "items": [{"product_id": 5, "quantity": 10}]}
    service = mock_service.return_value
    service.update_order_items = AsyncMock(side_effect=Exception("boom"))

    await handle_customer_update_order(payload, db_session, publisher)
    assert "erreur inattendue" in caplog.text


# =====================================================================
# CUSTOMER DELETE ORDER
# =====================================================================

async def test_handle_customer_delete_order_no_id(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_delete_order
    await handle_customer_delete_order({}, db_session, publisher)
    assert "payload sans order_id" in caplog.text


@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_delete_order_success(mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_customer_delete_order

    service = mock_service.return_value
    service.update_order_status = AsyncMock()

    await handle_customer_delete_order({"order_id": 12}, db_session, publisher)
    service.update_order_status.assert_awaited_once_with(12, OrderStatus.CANCELLED, publish=False)


@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_delete_order_not_found(mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_delete_order

    service = mock_service.return_value
    service.update_order_status = AsyncMock(side_effect=NotFoundError())

    await handle_customer_delete_order({"order_id": 12}, db_session, publisher)
    assert "introuvable" in caplog.text


@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_delete_order_generic_error(mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_delete_order

    service = mock_service.return_value
    service.update_order_status = AsyncMock(side_effect=Exception("db fail"))

    await handle_customer_delete_order({"order_id": 55}, db_session, publisher)
    assert "erreur inattendue" in caplog.text


# =====================================================================
# CUSTOMER VALIDATED
# =====================================================================

@patch("app.infra.events.handlers.OrderRepository")
@patch("app.infra.events.handlers.OrderService")
async def test_handle_customer_validated_success(mock_service, mock_repo, db_session, publisher):
    from app.infra.events.handlers import handle_customer_validated

    order = MagicMock(id=1, items=[], total=100)
    mock_repo.return_value.get.return_value = order
    service = mock_service.return_value
    service.update_order_status = AsyncMock()

    await handle_customer_validated({"order_id": 1, "customer_id": 5}, db_session, publisher)
    service.update_order_status.assert_awaited_once()
    publisher.publish_message.assert_awaited()


async def test_handle_customer_validated_invalid_payload(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_validated
    await handle_customer_validated({"order_id": None}, db_session, publisher)
    assert "payload invalide" in caplog.text


@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_customer_validated_order_not_found(mock_repo, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_validated
    mock_repo.return_value.get.return_value = None
    await handle_customer_validated({"order_id": 1, "customer_id": 5}, db_session, publisher)
    assert "introuvable en base" in caplog.text


# =====================================================================
# ORDER CONFIRMED
# =====================================================================

@patch("app.infra.events.handlers.OrderService")
async def test_handle_order_confirmed_success(mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_order_confirmed
    service = mock_service.return_value
    service.update_order_status = AsyncMock()

    await handle_order_confirmed({"order_id": 42}, db_session, publisher)
    service.update_order_status.assert_awaited_once_with(42, OrderStatus.CONFIRMED, publish=False)


async def test_handle_order_confirmed_invalid_payload(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_order_confirmed
    await handle_order_confirmed({}, db_session, publisher)
    assert "payload sans id" in caplog.text


# =====================================================================
# ORDER REJECTED
# =====================================================================

@patch("app.infra.events.handlers.OrderService")
async def test_handle_order_rejected_success(mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_order_rejected
    service = mock_service.return_value
    service.update_order_status = AsyncMock()

    await handle_order_rejected({"order_id": 7, "reason": "stock out"}, db_session, publisher)
    service.update_order_status.assert_awaited_once_with(7, OrderStatus.REJECTED, publish=False)
    assert "rejetée" in caplog.text


async def test_handle_order_rejected_invalid_payload(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_order_rejected
    await handle_order_rejected({}, db_session, publisher)
    assert "payload sans id" in caplog.text


# =====================================================================
# ORDER PRICE CALCULATED
# =====================================================================

@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_order_price_calculated_success(mock_repo, db_session, publisher):
    from app.infra.events.handlers import handle_order_price_calculated
    order = MagicMock(id=1, items=[], total=0)
    mock_repo.return_value.get.return_value = order
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()

    payload = {
        "order_id": 1,
        "customer_id": 10,
        "items": [{"product_id": 5, "quantity": 2, "unit_price": 10}],
        "total": 20
    }
    await handle_order_price_calculated(payload, db_session, publisher)

    assert order.total == 20
    db_session.commit.assert_called_once()
    publisher.publish_message.assert_awaited()


async def test_handle_order_price_calculated_invalid_payload(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_order_price_calculated
    await handle_order_price_calculated({"order_id": None}, db_session, publisher)
    assert "payload invalide" in caplog.text


@patch("app.infra.events.handlers.OrderRepository")
async def test_handle_order_price_calculated_order_not_found(mock_repo, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_order_price_calculated
    mock_repo.return_value.get.return_value = None
    payload = {"order_id": 123, "customer_id": 1, "items": [{"product_id": 1, "quantity": 1, "unit_price": 5}]}
    await handle_order_price_calculated(payload, db_session, publisher)
    assert "introuvable en base" in caplog.text
