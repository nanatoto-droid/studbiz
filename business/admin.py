# business/admin.py
# Only Business is registered here. Product, Sale, Expense are NOT registered.

from django.contrib import admin
from django.contrib import messages
from .models import Business, Product, Sale, Expense


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "category", "university", "is_approved")
    list_filter = ("category", "university", "is_approved")
    search_fields = ("name", "owner__username", "university")
    actions = ["approve_businesses", "withdraw_approval", "delete_with_accounts"]

    def approve_businesses(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} business(es) approved.", messages.SUCCESS)
    approve_businesses.short_description = "Approve selected businesses"

    def withdraw_approval(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} business(es) set to pending.", messages.WARNING)
    withdraw_approval.short_description = "Withdraw approval (set to pending)"

    def delete_with_accounts(self, request, queryset):
        # Deleting the Business cascades to its owner's records.
        # Also delete the owner Users so accounts are cleaned up.
        owners = [b.owner_id for b in queryset]
        count = queryset.count()
        # Delete users; Business cascade handles the rest.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.filter(id__in=owners).delete()
        self.message_user(request, f"{count} listing(s) and their owner account(s) deleted.", messages.SUCCESS)
    delete_with_accounts.short_description = "Delete selected listings with their accounts"


# NOTE: Do NOT register Product, Sale or Expense.