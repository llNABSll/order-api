Feature: Update orders
  As a user
  I want to update an order
  So that I can change its content or status

  Scenario: Update the status of an order
    Given an order exists with id "20" and status "pending"
    When I update the status of order "20" to "paid"
    Then the order should have status "paid"

  Scenario: Add a product to an order
    Given an order exists with id "26" for customer "1"
    When I add 1 product with id "55" 
    Then the order should contain product "55"
