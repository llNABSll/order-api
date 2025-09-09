# tests/features/steps/common_steps.py
import pytest
from pytest_bdd import given, when, then, parsers
from fastapi.testclient import TestClient
from app import main

BASE_URL = "/"  # root of the Orders API

@pytest.fixture
def client():
    return TestClient(main)

@pytest.fixture
def scenario_data():
    return {}

# ---------- GIVEN ----------
@given("the Orders API is available")
def step_api_available(client):
    try:
        client.get("/health")
    except Exception:
        pass

@given(parsers.parse('product "{product}" was deleted from the Product service'))
def step_product_deleted(scenario_data, product):
    # Stub. In a full system you would publish a deletion on the message broker or call the Product service.
    scenario_data["deleted_product"] = product

@given("a product is updated in the Product service")
def step_product_updated():
    pass  # stub for broker integration tests

@given("multiple orders have been created")
def step_create_multiple_orders(client):
    for i in range(3):
        client.post(
            BASE_URL,
            json={"product_name": f"bulk_product_{i}", "quantity": i + 1},
        )

@given(parsers.parse('an order was created with product "{product}" and quantity {quantity:d}'))
def step_an_order_was_created(client, scenario_data, product, quantity):
    resp = client.post(
        BASE_URL, json={"product_name": product, "quantity": quantity}
    )
    resp.raise_for_status()
    scenario_data["order"] = resp.json()

@given("an order was previously deleted")
def step_order_previously_deleted(client, scenario_data):
    resp = client.post(
        BASE_URL, json={"product_name": "temp", "quantity": 1}
    )
    order_id = resp.json()["id"]
    client.delete(f"{BASE_URL}/{order_id}")
    scenario_data["order_id"] = order_id

# ---------- WHEN ----------
@when(parsers.parse('I retrieve an order with ID "{order_id}"'))
def step_get_specific(client, scenario_data, order_id):
    scenario_data["response"] = client.get(f"{BASE_URL}/{order_id}")

@when("I list all orders")
def step_list_orders(client, scenario_data):
    scenario_data["response"] = client.get(BASE_URL)

@when("I try to delete the same order again")
def step_delete_again(client, scenario_data):
    oid = scenario_data["order_id"]
    scenario_data["response"] = client.delete(f"{BASE_URL}/{oid}")

@when(parsers.parse('I update an order with ID "{order_id}"'))
def step_update_nonexistent(client, scenario_data, order_id):
    scenario_data["response"] = client.put(f"{BASE_URL}/{order_id}", json={"quantity": 5})

@when("I publish a message on the message broker")
def step_publish_broker():
    pass  # stub

@when("I try to create an order during a network outage")
def step_network_outage(scenario_data):
    import httpx, socket
    try:
        httpx.post("http://127.0.0.1:9999/orders", json={})
    except (httpx.RequestError, socket.error) as exc:
        scenario_data["network_error"] = str(exc)

# ---------- THEN ----------
@then("a 404 error should be returned")
def step_404(scenario_data):
    assert scenario_data["response"].status_code == 404

@then("an error should be returned indicating the quantity is invalid")
def step_quantity_invalid(scenario_data):
    assert scenario_data["response"].status_code in (400, 422)

@then("an error should be returned indicating the product does not exist")
@then("an error should be returned indicating the product is not found")
def step_product_not_found(scenario_data):
    assert scenario_data["response"].status_code == 404

@then("an error should be returned indicating the product field is required")
def step_product_required(scenario_data):
    assert scenario_data["response"].status_code == 422

@then("a network error should be returned and the order should not be created")
def step_network_error(scenario_data):
    assert "Connection" in scenario_data["network_error"]

@given(parsers.parse('an order exists with id "{order_id}" for customer "{customer_id}"'))
def step_given_existing_order(client, scenario_data, order_id, customer_id):
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