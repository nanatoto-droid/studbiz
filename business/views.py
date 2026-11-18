# business/views.py
# Dashboard, products CRUD, sales CRUD, expenses CRUD, date filtering.

# business/views.py
# Dashboard, products CRUD, sales CRUD, expenses CRUD, date filtering.

from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import Business, Product, Sale, Expense
from .forms import ProductForm, SaleForm, ExpenseForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _own_business_or_none(request):
    """Return the logged-in user's Business or None (staff/user without one)."""
    return getattr(request.user, "business", None)


def _parse_date(value):
    """Parse YYYY-MM-DD from a query string. Returns None on failure."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _start_of_week():
    today = timezone.localdate()
    return today - timedelta(days=today.weekday())


def _start_of_month():
    today = timezone.localdate()
    return today.replace(day=1)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    business = _own_business_or_none(request)
    if business is None:
        if request.user.is_staff:
            return redirect("/admin/")
        messages.error(request, "No business profile found for this account.")
        return redirect("accounts:login")

    today = timezone.localdate()
    week_start = _start_of_week()
    month_start = _start_of_month()

    def totals(qs_sales, qs_expenses):
        s = qs_sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        e = qs_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        return s, e, (s - e)

    week_sales = Sale.objects.filter(business=business, date__gte=week_start, date__lte=today)
    week_expenses = Expense.objects.filter(business=business, date__gte=week_start, date__lte=today)
    month_sales = Sale.objects.filter(business=business, date__gte=month_start, date__lte=today)
    month_expenses = Expense.objects.filter(business=business, date__gte=month_start, date__lte=today)
    all_sales = Sale.objects.filter(business=business)
    all_expenses = Expense.objects.filter(business=business)

    w_s, w_e, w_net = totals(week_sales, week_expenses)
    m_s, m_e, m_net = totals(month_sales, month_expenses)
    a_s, a_e, a_net = totals(all_sales, all_expenses)

    # Top 5 best sellers by quantity sold.
    top_sellers = (
        Sale.objects.filter(business=business)
        .values("product__name")
        .annotate(qty=Sum("quantity"), revenue=Sum("total_amount"))
        .order_by("-qty")[:5]
    )

    # Low-stock products: stock <= reorder_level.
    low_stock = Product.objects.filter(business=business, stock__lte=models.F("reorder_level")) if False else [
        p for p in Product.objects.filter(business=business) if p.stock <= p.reorder_level
    ]

    # Suggested businesses: approved, same category OR same university, not self.
    from network.models import PartnershipRequest
    already_sent = set(
        PartnershipRequest.objects.filter(sender=business).values_list("receiver_id", flat=True)
    )
    suggested = (
        Business.objects.filter(is_approved=True)
        .exclude(id=business.id)
        .filter(models.Q(category=business.category) | models.Q(university=business.university))
        .exclude(id__in=already_sent)
        .order_by("name")[:5]
    )

    context = {
        "business": business,
        "week_start": week_start,
        "month_start": month_start,
        "today": today,
        "week_sales": w_s, "week_expenses": w_e, "week_net": w_net,
        "month_sales": m_s, "month_expenses": m_e, "month_net": m_net,
        "all_sales": a_s, "all_expenses": a_e, "all_net": a_net,
        "top_sellers": top_sellers,
        "low_stock": low_stock,
        "suggested": suggested,
    }
    return render(request, "business/dashboard.html", context)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@login_required
def product_list(request):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)
    products = Product.objects.filter(business=business).order_by("name")
    return render(request, "business/product_list.html", {"business": business, "products": products})


@login_required
def product_add(request):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.business = business
            product.save()
            messages.success(request, f"Product '{product.name}' added.")
            return redirect("business:product_list")
    else:
        form = ProductForm()
    return render(request, "business/product_form.html", {"form": form, "mode": "Add"})


@login_required
def product_edit(request, pk):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)
    product = get_object_or_404(Product, pk=pk, business=business)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect("business:product_list")
    else:
        form = ProductForm(instance=product)
    return render(request, "business/product_form.html", {"form": form, "mode": "Edit"})


@login_required
def product_delete(request, pk):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)
    product = get_object_or_404(Product, pk=pk, business=business)

    if product.has_sales():
        messages.error(
            request,
            "Cannot delete this product because it has sale records. Delete those sales first.",
        )
        return redirect("business:product_list")

    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect("business:product_list")

    return render(request, "business/product_confirm_delete.html", {"product": product})


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

@login_required
def sale_list(request):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)

    start = _parse_date(request.GET.get("start"))
    end = _parse_date(request.GET.get("end"))

    qs = Sale.objects.filter(business=business).select_related("product").order_by("-date", "-id")
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    total = qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    return render(request, "business/sale_list.html", {
        "business": business,
        "sales": qs,
        "total": total,
        "start": request.GET.get("start", ""),
        "end": request.GET.get("end", ""),
    })


@login_required
def sale_add(request):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)

    if request.method == "POST":
        form = SaleForm(request.POST, business=business)
        if form.is_valid():
            product_id = form.cleaned_data["product"].id
            qty = form.cleaned_data["quantity"]
            payment = form.cleaned_data["payment_method"]
            sale_date = form.cleaned_data["date"]

            try:
                with transaction.atomic():
                    product = (
                        Product.objects.select_for_update()
                        .get(pk=product_id, business=business)
                    )
                    if qty > product.stock:
                        raise ValueError(
                            f"Not enough stock. Available: {product.stock}."
                        )
                    unit_price = product.selling_price
                    total = unit_price * qty
                    Sale.objects.create(
                        business=business,
                        product=product,
                        quantity=qty,
                        unit_price=unit_price,
                        total_amount=total,
                        payment_method=payment,
                        date=sale_date,
                    )
                    product.stock = product.stock - qty
                    product.save(update_fields=["stock"])
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, "business/sale_form.html", {"form": form})
            except Product.DoesNotExist:
                messages.error(request, "That product no longer exists.")
                return redirect("business:product_list")

            messages.success(request, "Sale recorded and stock updated.")
            return redirect("business:sale_list")
    else:
        form = SaleForm(business=business)

    return render(request, "business/sale_form.html", {"form": form})


@login_required
def sale_delete(request, pk):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)
    sale = get_object_or_404(Sale, pk=pk, business=business)

    if request.method == "POST":
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=sale.product_id)
            product.stock = product.stock + sale.quantity
            product.save(update_fields=["stock"])
            sale.delete()
        messages.success(request, "Sale deleted and stock restored.")
        return redirect("business:sale_list")

    return render(request, "business/sale_confirm_delete.html", {"sale": sale})


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

@login_required
def expense_list(request):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)

    start = _parse_date(request.GET.get("start"))
    end = _parse_date(request.GET.get("end"))

    qs = Expense.objects.filter(business=business).order_by("-date", "-id")
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    return render(request, "business/expense_list.html", {
        "business": business,
        "expenses": qs,
        "total": total,
        "start": request.GET.get("start", ""),
        "end": request.GET.get("end", ""),
    })


@login_required
def expense_add(request):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)

    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.business = business
            expense.save()
            messages.success(request, "Expense recorded.")
            return redirect("business:expense_list")
    else:
        form = ExpenseForm()

    return render(request, "business/expense_form.html", {"form": form})


@login_required
def expense_delete(request, pk):
    business = _own_business_or_none(request)
    if business is None:
        return _no_business(request)
    expense = get_object_or_404(Expense, pk=pk, business=business)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted.")
        return redirect("business:expense_list")

    return render(request, "business/expense_confirm_delete.html", {"expense": expense})


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _no_business(request):
    """Staff or owner without a Business — do not crash."""
    if request.user.is_staff:
        messages.info(request, "Staff accounts use the admin site.")
        return redirect("/admin/")
    messages.error(request, "No business profile found for this account.")
    return redirect("accounts:login")