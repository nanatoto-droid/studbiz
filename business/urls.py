# business/urls.py
from django.urls import path
from . import views

app_name = "business"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.product_add, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("sales/", views.sale_list, name="sale_list"),
    path("sales/add/", views.sale_add, name="sale_add"),
    path("sales/<int:pk>/delete/", views.sale_delete, name="sale_delete"),
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.expense_add, name="expense_add"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
]