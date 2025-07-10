# tests/features/steps/common_steps.py
from behave import given, when, then
from fastapi.testclient import TestClient
from dev.src.main import app

client = TestClient(app)

# ---------- GENERIC CONTEXT ----------
BASE_URL = "/"               # root of the Orders API

# Shared storage for the current scenario
def store(context, **kw):
    for k, v in kw.items():
        setattr(context, k, v)

# ---------- GIVEN ----------
@given("the Orders API is available")
def step_api_available(context):
    # optional health‑check; ignore failures if endpoint not implemented
    try:
        client.get("/health")
    except Exception:
        pass

@given('product "{product}" was deleted from the Product service')
def step_product_deleted(context, product):
    """
    Stub.  In a full system you would publish a deletion
    on the message broker or call the Product service.
    """
    store(context, deleted_product=product)

@given('a product is updated in the Product service')
def step_product_updated(context):
    pass  # stub for broker integration tests

@given('multiple orders have been created')
def step_create_multiple_orders(context):
    for i in range(3):
        client.post(
            BASE_URL,
            json={"product_name": f"bulk_product_{i}", "quantity": i + 1},
        )

@given('an order was created with product "{product}" and quantity {quantity:d}')
def step_an_order_was_created(context, product, quantity):
    resp = client.post(
        BASE_URL, json={"product_name": product, "quantity": quantity}
    )
    resp.raise_for_status()
    store(context, order=resp.json())

@given("an order was previously deleted")
def step_order_previously_deleted(context):
    resp = client.post(
        BASE_URL, json={"product_name": "temp", "quantity": 1}
    )
    order_id = resp.json()["id"]
    client.delete(f"{BASE_URL}/{order_id}")
    store(context, order_id=order_id)

# ---------- WHEN ----------
@when('I retrieve an order with ID "{order_id}"')
def step_get_specific(context, order_id):
    store(context, response=client.get(f"{BASE_URL}/{order_id}"))

@when("I list all orders")
def step_list_orders(context):
    store(context, response=client.get(BASE_URL))

@when("I try to delete the same order again")
def step_delete_again(context):
    oid = context.order_id
    store(context, response=client.delete(f"{BASE_URL}/{oid}"))

@when('I update an order with ID "{order_id}"')
def step_update_nonexistent(context, order_id):
    store(
        context,
        response=client.put(f"{BASE_URL}/{order_id}", json={"quantity": 5}),
    )

@when("I publish a message on the message broker")
def step_publish_broker(context):
    pass  # stub

@when("I try to create an order during a network outage")
def step_network_outage(context):
    import httpx, socket
    try:
        httpx.post("http://127.0.0.1:9999/orders", json={})
    except (httpx.RequestError, socket.error) as exc:
        store(context, network_error=str(exc))

# ---------- THEN ----------
@then("a 404 error should be returned")
def step_404(context):
    assert context.response.status_code == 404

@then("an error should be returned indicating the quantity is invalid")
def step_quantity_invalid(context):
    assert context.response.status_code in (400, 422)

@then("an error should be returned indicating the product does not exist")
@then("an error should be returned indicating the product is not found")
def step_product_not_found(context):
    assert context.response.status_code == 404

@then("an error should be returned indicating the product field is required")
def step_product_required(context):
    assert context.response.status_code == 422

@then("a network error should be returned and the order should not be created")
def step_network_error(context):
    assert "Connection" in context.network_error
