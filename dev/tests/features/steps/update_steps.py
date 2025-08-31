
from behave import given, when, then
from fastapi.testclient import TestClient
from dev.src.main import app

client = TestClient(app)


@given('an order exists with id "{order_id}" and status "{status}"')
def step_given_existing_order_with_status(context, order_id, status):
    payload = {
        "customer_id": 123,
        "products": [
            {"product_id": 42, "product_name": "Test Coffee", "unit_price": 9.90, "quantity": 1}
        ],
        "status": status
    }
    response = client.post("/orders/", json=payload)
    assert response.status_code == 201
    created = response.json()
    context.order_id = created["id"]


@when('I update the status of order "{order_id}" to "{new_status}"')
def step_when_update_status(context, order_id, new_status):
    # Use the real order_id from context if it exists (created in the 'given' step)
    real_order_id = getattr(context, "order_id", order_id)
    payload = {"status": new_status}
    context.response = client.patch(f"/orders/{real_order_id}", json=payload)


@when('I add {quantity:d} product with id "{product_id}"')
def step_when_add_product(context, quantity, product_id):
    # Update the order with a new product list (replace all products)
    payload = {
        "products": [
            {
                "product_id": int(product_id),
                "product_name": "Extra Coffee",
                "quantity": quantity
            }
        ]
    }
    context.response = client.patch(f"/orders/{context.order_id}", json=payload)

@then('the order should have status "{status}"')
def step_then_order_updated_status(context, status):
    data = context.response.json()
    assert data["status"] == status


@then('the order should contain product "{product_id}"')
def step_then_order_contains_product(context, product_id):
    data = context.response.json()
    product_ids = [str(p["product_id"]) for p in data["products"]]
    assert product_id in product_ids


@then('the total amount should be updated')
def step_then_total_updated(context):
    data = context.response.json()
    assert data["total_amount"] > 0
