Feature: Create Orders

  As a reseller or webshop user
  I want to create coffee orders via the API
  So that I can manage new customer orders

  Background:
    Given the Orders API is available

  Scenario: Create a valid order
    When I create an order with product "arabica coffee" and quantity 10
    Then the order should be created with a unique ID

  Scenario: Create an order with a non-existing product
    When I create an order with product "unicorn coffee" and quantity 5
    Then an error should be returned indicating the product does not exist

  Scenario: Create an order with a negative quantity
    When I create an order with product "robusta coffee" and quantity -3
    Then an error should be returned indicating the quantity is invalid

  Scenario: Create an order without specifying a product
    When I create an order without specifying a product
    Then an error should be returned indicating the product field is required

  Scenario: Create an order after the product was deleted from the Product service
    Given product "jamaican coffee" was deleted from the Product service
    When I create an order with that product
    Then an error should be returned indicating the product is not found

  Scenario: API is temporarily unavailable
    When I try to create an order during a network outage
    Then a network error should be returned and the order should not be created

  Scenario: Check correct HTTP status code for successful creation
    When I create a valid order
    Then the HTTP response status should be 201 Created
