Feature: Update orders
  As a user
  I want to update an order
  So that I can change its content or status

  Scenario: Update the status of an order from pending to confirmed
    Given an order exists with id "1" for customer "1" and status "pending"
    When I update the status of order "1" to "confirmed"
    Then the order should have status "confirmed"

  Scenario: Update the status of an order from confirmed to completed
    Given an order exists with id "1" for customer "1" and status "confirmed"
    When I update the status of order "1" to "completed"
    Then the order should have status "completed"

  Scenario: Update the status of an order from pending to cancelled
    Given an order exists with id "1" for customer "1" and status "pending"
    When I update the status of order "1" to "cancelled"
    Then the order should have status "cancelled"

  Scenario: Fail to update status with invalid value
    Given an order exists with id "1" for customer "1" and status "pending"
    When I update the status of order "1" to "unknown"
    Then the response status code is "400"

  Scenario: Fail to update a non-existing order
    When I update the status of order "9999" to "confirmed"
    Then the response status code is "404"