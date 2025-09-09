from app.security.security import AuthContext, require_read, require_write
from pytest_bdd            import given, when, then, parsers, scenarios
from fastapi.testclient    import TestClient
from app.main              import app
from common_steps          import *
import pytest

scenarios("../features/create.feature")

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

@given(parsers.parse('a customer with id "{customer_id}"'))
def step_given_customer(scenario_data, customer_id):
    scenario_data["customer_id"] = int(customer_id)

@given(parsers.parse('a product available with id "{product_id}" and price "{price}"'))
def step_given_product(scenario_data, product_id, price):
    scenario_data["product_id"] = int(product_id)
    scenario_data["product_price"] = float(price)

@when(parsers.parse('I create an order with {quantity:d} units of the product'))
def step_when_create_order(client, scenario_data, quantity):
    payload = {
        "customer_id": scenario_data["customer_id"],
        "items": [
            {
                "product_id": scenario_data["product_id"],
                "quantity": quantity
            }
        ]
    }
    scenario_data["response"] = client.post("/orders/", json=payload)

@when('I create an order without products')
def step_when_create_order_empty(client, scenario_data):
    payload = {"customer_id": scenario_data["customer_id"], "items": []}
    scenario_data["response"] = client.post("/orders/", json=payload)

@then(parsers.parse('the order should be created with status "{status}"'))
def step_then_order_status_created(scenario_data, status):
    response = scenario_data["response"]
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == status

@then(parsers.parse('the order creation should fail with status code {status_code:d}'))
def step_then_order_creation_fail(scenario_data, status_code):
    response = scenario_data["response"]
    assert response.status_code == status_code


@when('I try to create an order with missing customer_id')
def step_create_order_missing_customer_id(client, scenario_data):
    payload = {
        # "customer_id" is missing
        "items": [{"product_id": 42, "quantity": 1}]
    }
    scenario_data["response"] = client.post("/orders/", json=payload)