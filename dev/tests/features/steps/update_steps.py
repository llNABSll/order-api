# tests/features/steps/update_steps.py
from behave import when, then
from fastapi.testclient import TestClient
from dev.src.main import app
from dev.tests.features.steps.common_steps import BASE_URL, store

client = TestClient(app)

# ---------- WHEN ----------
@when("I update the quantity to {new_qty:d}")
def step_update_qty(context, new_qty):
    order_id = context.order["id"]
    payload = {"quantity": new_qty}
    store(context, response=client.put(f"{BASE_URL}/{order_id}", json=payload))

# ---------- THEN ----------
@then("the order should reflect the new quantity")
def step_reflect_new_qty(context):
    assert context.response.status_code == 200
    assert context.response.json()["quantity"] == 6
