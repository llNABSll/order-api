from app.security.security import AuthContext, require_read, require_write
from pytest_bdd            import when, then, parsers, scenarios
from fastapi.testclient    import TestClient
from app.main              import app
from common_steps         import *
import pytest

scenarios("../features/read.feature")

@pytest.fixture
def client():
    fake_ctx = AuthContext(
        user="test-user",
        email="test@example.com",
        roles=["order:read", "order:write"],
    )
    app.dependency_overrides[require_read] = lambda: fake_ctx
    app.dependency_overrides[require_write] = lambda: fake_ctx
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def scenario_data():
    return {}


@when(parsers.parse('I get the order "{order_id}"'))
def step_when_get_order(client, scenario_data, order_id):
    # Utilise l'order_id créé si présent
    real_order_id = scenario_data.get("order_id", order_id)
    scenario_data["response"] = client.get(f"/orders/{real_order_id}")


@then(parsers.parse('the response should contain customer "{customer_id}"'))
def step_then_response_contains_customer(scenario_data, customer_id):
    data = scenario_data["response"].json()
    assert str(data["customer_id"]) == customer_id


@then(parsers.parse('the status should be "{status}"'))
def step_then_status(scenario_data, status):
    data = scenario_data["response"].json()
    assert data["status"] == status


@then(parsers.parse('the response should have status code {status_code:d}'))
def step_then_status_code(scenario_data, status_code):
    assert scenario_data["response"].status_code == status_code


# ---------- New list orders steps ----------
@when('I list orders')
def step_when_list_orders(client, scenario_data):
    scenario_data["response"] = client.get("/orders/?skip=0&limit=100")

@then('the list should be empty')
def step_then_list_empty(scenario_data):
    data = scenario_data["response"].json()
    assert isinstance(data, list)
    assert len(data) == 0

@then('the list should contain at least 1 order')
def step_then_list_not_empty(scenario_data):
    data = scenario_data["response"].json()
    assert isinstance(data, list)
    assert len(data) >= 1
