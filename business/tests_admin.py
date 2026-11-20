# business/tests_admin.py
# Verify only Business is registered in admin.

from django.contrib import admin
from django.test import TestCase

from business.models import Business, Product, Sale, Expense


class AdminRegistrationTests(TestCase):
    def test_business_is_registered(self):
        self.assertIn(Business, admin.site._registry)

    def test_product_not_registered(self):
        self.assertNotIn(Product, admin.site._registry)

    def test_sale_not_registered(self):
        self.assertNotIn(Sale, admin.site._registry)

    def test_expense_not_registered(self):
        self.assertNotIn(Expense, admin.site._registry)