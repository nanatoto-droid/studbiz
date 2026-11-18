
# business/models.py
# Business, Product, Sale, and Expense models.

from decimal import Decimal
from django.db import models
from django.conf import settings


class Business(models.Model):
    """One business per owner. Created on registration, pending approval."""

    CATEGORY_CHOICES = [
        ("Food", "Food"),
        ("Fashion", "Fashion"),
        ("Beauty", "Beauty"),
        ("Services", "Services"),
        ("Technology", "Technology"),
        ("Agribusiness", "Agribusiness"),
        ("Other", "Other"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business",
    )
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    university = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    """A product sold by one business. Stock can never be negative."""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=150)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    def has_sales(self):
        """Return True if this product has any sale records."""
        return self.sale_set.exists()


class Sale(models.Model):
    """A sale copies the product's current price; later changes don't affect it."""

    PAYMENT_CHOICES = [
        ("Cash", "Cash"),
        ("M-PESA", "M-PESA"),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="sale_set",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    date = models.DateField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Expense(models.Model):
    """An expense recorded by a business."""

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    description = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"{self.description} ({self.amount})"