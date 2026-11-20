# business/tests.py
# Tests for products, sales, expenses, dashboard, and cross-owner isolation.

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from business.models import Business, Product, Sale, Expense


class BusinessTestBase(TestCase):
    def setUp(self):
        self.owner_a = User.objects.create_user(username="a", password="pass12345")
        self.owner_b = User.objects.create_user(username="b", password="pass12345")
        self.biz_a = Business.objects.create(
            owner=self.owner_a, name="Biz A", category="Food",
            university="Uni", phone="0700000001", is_approved=True,
        )
        self.biz_b = Business.objects.create(
            owner=self.owner_b, name="Biz B", category="Fashion",
            university="Uni", phone="0700000002", is_approved=True,
        )
        self.prod_a = Product.objects.create(
            business=self.biz_a, name="P1", selling_price=Decimal("100.00"),
            stock=10, reorder_level=2,
        )
        self.prod_b = Product.objects.create(
            business=self.biz_b, name="P2", selling_price=Decimal("50.00"),
            stock=5, reorder_level=1,
        )


class SaleCalculationsTests(BusinessTestBase):
    def test_sale_copies_price_and_totals_and_reduces_stock(self):
        self.client.force_login(self.owner_a)
        resp = self.client.post(reverse("business:sale_add"), {
            "product": self.prod_a.id,
            "quantity": 3,
            "payment_method": "Cash",
            "date": timezone.localdate().isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        sale = Sale.objects.get(business=self.biz_a)
        self.assertEqual(sale.unit_price, Decimal("100.00"))
        self.assertEqual(sale.total_amount, Decimal("300.00"))
        self.prod_a.refresh_from_db()
        self.assertEqual(self.prod_a.stock, 7)

    def test_oversized_sale_rejected_and_stock_unchanged(self):
        self.client.force_login(self.owner_a)
        resp = self.client.post(reverse("business:sale_add"), {
            "product": self.prod_a.id,
            "quantity": 100,
            "payment_method": "Cash",
            "date": timezone.localdate().isoformat(),
        })
        # No sale created, stock unchanged.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Sale.objects.count(), 0)
        self.prod_a.refresh_from_db()
        self.assertEqual(self.prod_a.stock, 10)

    def test_later_price_change_does_not_change_old_sale(self):
        self.client.force_login(self.owner_a)
        self.client.post(reverse("business:sale_add"), {
            "product": self.prod_a.id,
            "quantity": 2,
            "payment_method": "Cash",
            "date": timezone.localdate().isoformat(),
        })
        sale = Sale.objects.get(business=self.biz_a)
        original_total = sale.total_amount
        self.prod_a.selling_price = Decimal("999.00")
        self.prod_a.save()
        sale.refresh_from_db()
        self.assertEqual(sale.total_amount, original_total)

    def test_deleting_sale_restores_stock(self):
        self.client.force_login(self.owner_a)
        self.client.post(reverse("business:sale_add"), {
            "product": self.prod_a.id,
            "quantity": 4,
            "payment_method": "Cash",
            "date": timezone.localdate().isoformat(),
        })
        self.prod_a.refresh_from_db()
        self.assertEqual(self.prod_a.stock, 6)
        sale = Sale.objects.get(business=self.biz_a)
        self.client.post(reverse("business:sale_delete", args=[sale.id]))
        self.prod_a.refresh_from_db()
        self.assertEqual(self.prod_a.stock, 10)
        self.assertFalse(Sale.objects.filter(pk=sale.pk).exists())


class ProductDeleteTests(BusinessTestBase):
    def test_product_with_sales_cannot_be_deleted(self):
        Sale.objects.create(
            business=self.biz_a, product=self.prod_a, quantity=1,
            unit_price=self.prod_a.selling_price,
            total_amount=self.prod_a.selling_price,
            payment_method="Cash", date=timezone.localdate(),
        )
        self.client.force_login(self.owner_a)
        self.client.post(reverse("business:product_delete", args=[self.prod_a.id]))
        self.assertTrue(Product.objects.filter(pk=self.prod_a.pk).exists())

    def test_product_without_sales_can_be_deleted(self):
        self.client.force_login(self.owner_a)
        self.client.post(reverse("business:product_delete", args=[self.prod_a.id]))
        self.assertFalse(Product.objects.filter(pk=self.prod_a.pk).exists())


class CrossOwner404Tests(BusinessTestBase):
    def test_owner_a_gets_404_on_owner_b_product(self):
        self.client.force_login(self.owner_a)
        resp = self.client.get(reverse("business:product_edit", args=[self.prod_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_owner_a_gets_404_on_owner_b_sale(self):
        sale_b = Sale.objects.create(
            business=self.biz_b, product=self.prod_b, quantity=1,
            unit_price=self.prod_b.selling_price,
            total_amount=self.prod_b.selling_price,
            payment_method="Cash", date=timezone.localdate(),
        )
        self.client.force_login(self.owner_a)
        resp = self.client.get(reverse("business:sale_delete", args=[sale_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_owner_a_gets_404_on_owner_b_expense(self):
        exp_b = Expense.objects.create(
            business=self.biz_b, description="X", category="Misc",
            amount=Decimal("10.00"), date=timezone.localdate(),
        )
        self.client.force_login(self.owner_a)
        resp = self.client.get(reverse("business:expense_delete", args=[exp_b.id]))
        self.assertEqual(resp.status_code, 404)


class LoginRedirectTests(BusinessTestBase):
    def test_logged_out_redirected_to_login(self):
        for name in ("business:dashboard", "business:product_list", "business:sale_list", "business:expense_list"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login/", resp.url)


class DashboardFiguresTests(BusinessTestBase):
    def test_dashboard_totals_match_manual_calculation(self):
        today = timezone.localdate()
        # Sales: 2 x 100 = 200 ; 3 x 50 = 150 ; total 350
        Sale.objects.create(
            business=self.biz_a, product=self.prod_a, quantity=2,
            unit_price=Decimal("100.00"), total_amount=Decimal("200.00"),
            payment_method="Cash", date=today,
        )
        Sale.objects.create(
            business=self.biz_a, product=self.prod_a, quantity=3,
            unit_price=Decimal("50.00"), total_amount=Decimal("150.00"),
            payment_method="M-PESA", date=today,
        )
        # Expenses: 80 + 20 = 100
        Expense.objects.create(business=self.biz_a, description="X", category="C",
                               amount=Decimal("80.00"), date=today)
        Expense.objects.create(business=self.biz_a, description="Y", category="C",
                               amount=Decimal("20.00"), date=today)

        self.client.force_login(self.owner_a)
        resp = self.client.get(reverse("business:dashboard"))
        self.assertEqual(resp.context["all_sales"], Decimal("350.00"))
        self.assertEqual(resp.context["all_expenses"], Decimal("100.00"))
        self.assertEqual(resp.context["all_net"], Decimal("250.00"))
        # Same day is within week and month (safe assumption for today).
        self.assertEqual(resp.context["week_sales"], Decimal("350.00"))
        self.assertEqual(resp.context["month_sales"], Decimal("350.00"))


class CsrfTests(BusinessTestBase):
    def test_post_without_csrf_token_is_rejected(self):
        # Django's test client normally enforces CSRF; use enforce_csrf_checks.
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner_a)
        resp = strict.post(reverse("business:product_add"), {
            "name": "New", "selling_price": "10.00", "stock": 1, "reorder_level": 0,
        })
        self.assertEqual(resp.status_code, 403)


