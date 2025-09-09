Feature: Delete orders
  As a user
  I want to delete an order
  So that I can cancel an existing order

  Scenario: Delete an existing order
    Given an order exists with id "26" for customer "1"
    When I delete the order "26"
    Then the order should no longer exist
    And the API should return status code 204

  Scenario: Delete a non-existing order
    When I delete the order "9999"
    Then the API should return status code 404

  Scenario: Delete an order twice
    Given an order exists with id "26" for customer "1"
    When I delete the order "26"
    And I delete the order "26"
    Then the API should return status code 404