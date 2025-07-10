# tests/features/steps/read_steps.py
from behave import when, then
from fastapi.testclient import TestClient
from dev.src.main import app
from dev.tests.features.steps.common_steps import BASE_URL, store

client = TestClient(app)

# ---------- WHEN ----------
@when("I retrieve this order by its ID")
def step_retrieve_by_id(context):
    order_id = context.order["id"]
    store(context, response=client.get(f"{BASE_URL}/{order_id}"))

# ---------- THEN ----------
@then("the correct order should be returned")
def step_correct_order(context):
    assert context.response.status_code == 200
    assert context.response.json()["id"] == context.order["id"]

@then("all existing orders should be returned")
def step_all_orders(context):
    assert context.response.status_code == 200
    assert isinstance(context.response.json(), list)
