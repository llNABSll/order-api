
from behave import given, when, then
from fastapi.testclient import TestClient
from dev.src.main import app

client = TestClient(app)


@given('an order exists with id "{order_id}" for customer "{customer_id}"')
def step_given_existing_order(context, order_id, customer_id):
    payload = {
        "customer_id": int(customer_id),
        "products": [
            {"product_id": 42, "product_name": "Test Coffee", "unit_price": 9.90, "quantity": 1}
        ]
    }
    response = client.post("/orders/", json=payload)
    assert response.status_code == 201
    created = response.json()
    context.order_id = created["id"]


@when('I get the order "{order_id}"')
def step_when_get_order(context, order_id):
    # Use the real order_id from context if it exists (created in the 'given' step)
    real_order_id = getattr(context, "order_id", order_id)
    context.response = client.get(f"/orders/{real_order_id}")


@then('the response should contain customer "{customer_id}"')
def step_then_response_contains_customer(context, customer_id):
    data = context.response.json()
    print("CACA:", context.response.status_code, context.response.text)
    assert str(data["customer_id"]) == customer_id


@then('the status should be "{status}"')
def step_then_status(context, status):
    data = context.response.json()
    assert data["status"] == status


@then('the response should have status code {status_code:d}')
def step_then_status_code(context, status_code):
    assert context.response.status_code == status_code
