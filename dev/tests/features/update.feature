Feature: Update Orders

  As a reseller or webshop user
  I want to update coffee orders via the API
  So that I can adjust order quantities as needed

  Background:
    Given the Orders API is available

  Scenario: Update the quantity of an existing order
    Given an order was created with product "moka coffee" and quantity 3
    When I update the quantity to 6
    Then the order should reflect the new quantity

  Scenario: Update a non-existing order
    When I update an order with ID "999999"
    Then a 404 error should be returned

  Scenario: Update an order with invalid quantity
    Given an order was created with product "moka coffee" and quantity 3
    When I update the quantity to -10
    Then an error should be returned indicating the quantity is invalid

  Scenario: Receive product update via message broker
    Given a product is updated in the Product service
    When a message is published on the message broker
    Then the Orders API should update the related product data locally
