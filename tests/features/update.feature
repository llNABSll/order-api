Feature: Update orders
  As a user
  I want to update an order
  So that I can change its content or status

  Scenario: Update the status of an order from pending to paid
    Given an order exists with id "1" for customer "1" and status "pending"
    When I update the status of order "1" to "paid"
    Then the order should have status "paid"

  Scenario: Update the status of an order from paid to shipped
    Given an order exists with id "1" for customer "1" and status "paid"
    When I update the status of order "1" to "shipped"
    Then the order should have status "shipped"

  Scenario: Update the status of an order from pending to cancelled
    Given an order exists with id "1" for customer "1" and status "pending"
    When I update the status of order "1" to "cancelled"
    Then the order should have status "cancelled"

    Scenario: Fail to update status with invalid value
      Given an order exists with id "1" for customer "1" and status "pending"
      When I update the status of order "1" to "unknown"
      Then the response status code is "400"
  
    Scenario: Fail to update a non-existing order
      When I update the status of order "9999" to "paid"
      Then the response status code is "404"