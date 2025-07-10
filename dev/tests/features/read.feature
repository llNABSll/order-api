Feature: Read Orders

  As a reseller or webshop user
  I want to retrieve coffee orders via the API
  So that I can view and verify customer orders

  Background:
    Given the Orders API is available

  Scenario: Retrieve an existing order by ID
    Given an order was created with product "moka coffee" and quantity 3
    When I retrieve this order by its ID
    Then the correct order should be returned

  Scenario: Retrieve an order with an unknown ID
    When I retrieve an order with ID "999999"
    Then a 404 error should be returned indicating the order is not found

  Scenario: List all existing orders
    Given multiple orders have been created
    When I list all orders
    Then all existing orders should be returned
