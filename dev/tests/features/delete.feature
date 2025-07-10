Feature: Delete Orders

  As a reseller or webshop user
  I want to delete coffee orders via the API
  So that I can manage canceled or erroneous orders

  Background:
    Given the Orders API is available

  Scenario: Delete an existing order
    Given an order was created with product "colombian coffee" and quantity 8
    When I delete this order
    Then the order should no longer be retrievable

  Scenario: Delete an already deleted order
    Given an order was previously deleted
    When I try to delete the same order again
    Then a 404 error should be returned
