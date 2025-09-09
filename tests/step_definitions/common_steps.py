from pytest_bdd import given, then, parsers

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

@then(parsers.parse('the response status code is "{status_code}"'))
def step_then_response_status_code(scenario_data, status_code):
    assert str(scenario_data["response"].status_code) == status_code