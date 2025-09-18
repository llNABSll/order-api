import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.order_services import NotFoundError

pytestmark = pytest.mark.asyncio

@pytest.fixture
def db_session():
    return MagicMock()

@pytest.fixture
def publisher():
    return AsyncMock()

# ----- CUSTOMER DELETED -----
async def test_handle_customer_deleted_no_id(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_deleted
    await handle_customer_deleted({}, db_session, publisher)
    assert "payload sans id" in caplog.text

@patch('app.infra.events.handlers.OrderService')
@patch('app.infra.events.handlers.OrderRepository')
async def test_handle_customer_deleted_success(mock_repo, mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_customer_deleted

    orders = [MagicMock(id=1), MagicMock(id=2)]
    repo = mock_repo.return_value
    repo.list.return_value = orders
    service = mock_service.return_value
    # ensure async methods
    service.update_order_status = AsyncMock()

    await handle_customer_deleted({"id": 123}, db_session, publisher)

    repo.list.assert_called_once_with(filters={"customer_id": 123})
    assert service.update_order_status.call_count == 2
    service.update_order_status.assert_any_call(1, "cancelled")
    service.update_order_status.assert_any_call(2, "cancelled")

@patch('app.infra.events.handlers.OrderService')
@patch('app.infra.events.handlers.OrderRepository')
async def test_handle_customer_deleted_order_not_found(mock_repo, mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_deleted

    orders = [MagicMock(id=1)]
    repo = mock_repo.return_value
    repo.list.return_value = orders
    service = mock_service.return_value
    service.update_order_status = AsyncMock(side_effect=NotFoundError())

    await handle_customer_deleted({"id": 123}, db_session, publisher)

    assert "déjà supprimée" in caplog.text

# ----- ORDER UPDATED -----
async def test_handle_customer_update_order_invalid_payload(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_update_order
    await handle_customer_update_order({}, db_session, publisher)
    assert "payload invalide" in caplog.text

@patch('app.infra.events.handlers.OrderService')
@patch('app.infra.events.handlers.OrderRepository')
async def test_handle_customer_update_order_success(mock_repo, mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_customer_update_order

    payload = {"id": 12, "items": [{"product_id": 3, "quantity": 5}]}
    service = mock_service.return_value
    service.update_order_items = AsyncMock()

    await handle_customer_update_order(payload, db_session, publisher)

    service.update_order_items.assert_called_once_with(12, payload["items"])

@patch('app.infra.events.handlers.OrderService')
@patch('app.infra.events.handlers.OrderRepository')
async def test_handle_customer_update_order_not_found(mock_repo, mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_update_order

    payload = {"id": 12, "items": [{"product_id": 3, "quantity": 5}]}
    service = mock_service.return_value
    service.update_order_items = AsyncMock(side_effect=NotFoundError())

    await handle_customer_update_order(payload, db_session, publisher)

    assert "commande 12 introuvable" in caplog.text

# ----- ORDER DELETED -----
async def test_handle_customer_delete_order_no_id(db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_delete_order
    await handle_customer_delete_order({}, db_session, publisher)
    assert "payload sans id" in caplog.text

@patch('app.infra.events.handlers.OrderService')
@patch('app.infra.events.handlers.OrderRepository')
async def test_handle_customer_delete_order_success(mock_repo, mock_service, db_session, publisher):
    from app.infra.events.handlers import handle_customer_delete_order

    service = mock_service.return_value
    service.update_order_status = AsyncMock()
    await handle_customer_delete_order({"id": 12}, db_session, publisher)

    service.update_order_status.assert_called_once_with(12, "cancelled")

@patch('app.infra.events.handlers.OrderService')
@patch('app.infra.events.handlers.OrderRepository')
async def test_handle_customer_delete_order_not_found(mock_repo, mock_service, db_session, publisher, caplog):
    from app.infra.events.handlers import handle_customer_delete_order

    service = mock_service.return_value
    service.update_order_status = AsyncMock(side_effect=NotFoundError())

    await handle_customer_delete_order({"id": 12}, db_session, publisher)

    assert "commande 12 introuvable" in caplog.text
