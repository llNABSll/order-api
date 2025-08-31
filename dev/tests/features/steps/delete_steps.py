
from behave import given, when, then
from fastapi.testclient import TestClient
from dev.src.main import app

client = TestClient(app)

@when('I delete the order "{order_id}"')
def step_when_delete_order(context, order_id):
    # Use the real order_id from context if it exists (created in the 'given' step)
    real_order_id = getattr(context, "order_id", order_id)
    context.response = client.delete(f"/orders/{real_order_id}")


@then('the order should no longer exist')
def step_then_order_not_found(context):
    # Use the real order_id from context if it exists
    real_order_id = getattr(context, "order_id", None)
    assert real_order_id is not None, "No order_id in context to check deletion."
    response = client.get(f"/orders/{real_order_id}")
    assert response.status_code == 404


@then('the API should return status code {status_code:d}')
def step_then_api_status(context, status_code):
    assert context.response.status_code == status_code
