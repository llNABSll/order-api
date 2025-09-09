Feature: Update orders
  As a user
  I want to update an order
  So that I can change its content or status

  Scenario: Update the status of an order from pending to paid
    Given an order exists with id "26" for customer "1" and status "pending"
    When I update the status of order "26" to "paid"
    Then the order should have status "paid"

  Scenario: Update the status of an order from paid to shipped
    Given an order exists with id "22" for customer "1" and status "paid"
    When I update the status of order "22" to "shipped"
    Then the order should have status "shipped"