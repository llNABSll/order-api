# tests/features/steps/delete_steps.py
from behave import when, then
from fastapi.testclient import TestClient
from dev.src.main import app
from dev.tests.features.steps.common_steps import BASE_URL, store

client = TestClient(app)

# ---------- WHEN ----------
@when("I delete this order")
def step_delete_order(context):
    order_id = context.order["id"]
    store(context, response=client.delete(f"{BASE_URL}/{order_id}"))

# ---------- THEN ----------
@then("the order should no longer be retrievable")
def step_no_longer_retrievable(context):
    oid = context.order["id"]
    check = client.get(f"{BASE_URL}/{oid}")
    assert check.status_code == 404
