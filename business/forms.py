# business/forms.py
# Forms for Product, Sale, and Expense.

from django import forms
from .models import Product, Sale, Expense


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "selling_price", "stock", "reorder_level"]

    def clean_selling_price(self):
        price = self.cleaned_data["selling_price"]
        if price < 0:
            raise forms.ValidationError("Selling price cannot be negative.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]
        if stock < 0:
            raise forms.ValidationError("Stock cannot be negative.")
        return stock

    def clean_reorder_level(self):
        level = self.cleaned_data["reorder_level"]
        if level < 0:
            raise forms.ValidationError("Reorder level cannot be negative.")
        return level


class SaleForm(forms.Form):
    """Sale form. Products are limited to the logged-in owner's business."""

    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.IntegerField(min_value=1)
    payment_method = forms.ChoiceField(choices=Sale.PAYMENT_CHOICES)
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        if business is not None:
            self.fields["product"].queryset = Product.objects.filter(business=business).order_by("name")

    def clean_quantity(self):
        qty = self.cleaned_data["quantity"]
        if qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return qty


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["description", "category", "amount", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount < 0:
            raise forms.ValidationError("Amount cannot be negative.")
        return amount