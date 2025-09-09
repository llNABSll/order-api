from app.security.security import AuthContext, require_read, require_write
from pytest_bdd            import given, when, then, parsers, scenarios
from fastapi.testclient    import TestClient
from app.main              import app
from common_steps          import *
import pytest

scenarios("../features/update.feature")

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

@given(parsers.parse('an order exists with id "{order_id}" for customer "{customer_id}" and status "{status}"'))
def step_given_existing_order_with_status(client, scenario_data, order_id, customer_id, status):
    payload = {
        "customer_id": int(customer_id),
        "items": [
            {"product_id": 42, "quantity": 1}
        ]
    }
    response = client.post("/orders/", json=payload)
    assert response.status_code == 201
    created = response.json()
    scenario_data["order_id"] = created["id"]
    # Patch status si besoin
    if status != created.get("status"):
        patch_resp = client.put(f"/orders/{scenario_data['order_id']}/status", json={"status": status})
        assert patch_resp.status_code in (200, 201)

@when(parsers.parse('I update the status of order "{order_id}" to "{new_status}"'))
def step_when_update_status(client, scenario_data, order_id, new_status):
    # real_order_id = scenario_data.get("order_id", order_id)
    payload = {"status": new_status}
    scenario_data["response"] = client.put(f"/orders/{order_id}/status", json=payload)

@then(parsers.parse('the order should have status "{status}"'))
def step_then_order_updated_status(scenario_data, status):
    data = scenario_data["response"].json()
    assert data["status"] == status

@then(parsers.parse('the order should contain product "{product_id}"'))
def step_then_order_contains_product(scenario_data, product_id):
    data = scenario_data["response"].json()
    product_ids = [str(p["product_id"]) for p in data.get("items", [])]
    assert product_id in product_ids

@then('the total amount should be updated')
def step_then_total_updated(scenario_data):
    data = scenario_data["response"].json()
    assert data["total_amount"] > 0
