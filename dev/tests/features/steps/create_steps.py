
from behave import given, when, then
from fastapi.testclient import TestClient
from dev.src.main import app

client = TestClient(app)


@given('a customer with id "{customer_id}"')
def step_given_customer(context, customer_id):
    context.customer_id = int(customer_id)


@given('a product available with id "{product_id}" and price "{price}"')
def step_given_product(context, product_id, price):
    context.product_id = int(product_id)
    context.product_price = float(price)


@when('I create an order with {quantity:d} units of the product')
def step_when_create_order(context, quantity):
    payload = {
        "customer_id": context.customer_id,
        "products": [
            {
                "product_id": context.product_id,
                "product_name": "Coffee Test",
                "unit_price": context.product_price,
                "quantity": quantity
            }
        ]
    }
    context.response = client.post("/orders/", json=payload)


@when('I create an order without products')
def step_when_create_order_empty(context):
    payload = {"customer_id": context.customer_id, "products": []}
    context.response = client.post("/orders/", json=payload)


@then('the order should be created with status "{status}"')
def step_then_order_status_created(context, status):
    assert context.response.status_code == 201
    data = context.response.json()
    assert data["status"] == status




@then('the order creation should fail with status code {status_code:d}')
def step_then_order_creation_fail(context, status_code):
    assert context.response.status_code == status_code
