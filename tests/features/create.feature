Feature: Create orders
  As a user
  I want to create an order
  So that I can purchase products

  Scenario: Create a valid order
    Given a customer with id "123"
    And a product available with id "42" and price "9.90"
    When I create an order with 2 units of the product
    Then the order should be created with status "pending"
    And the response status code is "201"

  Scenario: Fail if no product is provided
    Given a customer with id "123"
    When I create an order without products
    Then the response status code is "400"

  Scenario: Fail if customer_id is missing
    Given a product available with id "42" and price "9.90"
    When I try to create an order with missing customer_id
    Then the response status code is "422"

  Scenario: Fail if quantity is zero
    Given a customer with id "123"
    And a product available with id "42" and price "9.90"
    When I create an order with 0 units of the product
    Then the response status code is "422"