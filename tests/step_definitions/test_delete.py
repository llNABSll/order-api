from app.security.security import AuthContext, require_read, require_write
from pytest_bdd            import when, then, parsers, scenarios
from fastapi.testclient    import TestClient
from app.main              import app
from common_steps         import *
import pytest

scenarios("../features/delete.feature")

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

@when(parsers.parse('I delete the order "{order_id}"'))
def step_when_delete_order(client, scenario_data, order_id):
    real_order_id = scenario_data.get("order_id", order_id)
    scenario_data["response"] = client.delete(f"/orders/{real_order_id}")


@then('the order should no longer exist')
def step_then_order_not_found(client, scenario_data):
    real_order_id = scenario_data.get("order_id", None)
    assert real_order_id is not None, "No order_id in scenario_data to check deletion."
    response = client.get(f"/orders/{real_order_id}")
    assert response.status_code == 404


@then(parsers.parse('the API should return status code {status_code:d}'))
def step_then_api_status(scenario_data, status_code):
    assert scenario_data["response"].status_code == status_code
