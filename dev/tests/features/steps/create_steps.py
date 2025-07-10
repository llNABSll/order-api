# tests/features/steps/create_steps.py
from behave import when, then
from fastapi.testclient import TestClient
from dev.src.main import app
from dev.tests.features.steps.common_steps import BASE_URL, store

client = TestClient(app)

# ---------- WHEN ----------
@when('I create an order with product "{product}" and quantity {qty:d}')
def step_create_order(context, product, qty):
    payload = {"product_name": product, "quantity": qty}
    store(context, response=client.post(BASE_URL, json=payload))

@when("I create an order without specifying a product")
def step_create_without_product(context):
    store(context, response=client.post(BASE_URL, json={"quantity": 1}))

# ---------- THEN ----------
@then("the order should be created with a unique ID")
def step_order_created(context):
    assert context.response.status_code == 201
    assert "id" in context.response.json()

@then("the HTTP response status should be 201 Created")
def step_status_created(context):
    assert context.response.status_code == 201
