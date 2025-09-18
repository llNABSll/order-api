Feature: Get an order
  As a user
  I want to retrieve a specific order
  So that I can check its content and status

  Scenario: List orders when empty
    When I list orders
    Then the response should have status code 200
    And the list should be empty

  Scenario: List orders after creation
    Given an order exists with id "26" for customer "1"
    When I list orders
    Then the response should have status code 200
    And the list should contain at least 1 order

  Scenario: Retrieve an existing order
    Given an order exists with id "26" for customer "1"
    When I get the order "1"
    Then the response should contain customer "1"
    And the status should be "pending"

  Scenario: Fail if the order does not exist
    When I get the order "9999"
    Then the response should have status code 404
