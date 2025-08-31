Feature: Create orders
  As a user
  I want to create an order
  So that I can purchase products

  Scenario: Create a valid order
    Given a customer with id "123"
    And a product available with id "42" and price "9.90"
    When I create an order with 2 units of the product
    Then the order should be created with status "pending"

  Scenario: Fail if no product is provided
    Given a customer with id "123"
    When I create an order without products
    Then the order creation should fail with status code 400
