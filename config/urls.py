# config/urls.py
# Top-level URL configuration for the project.

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("business.urls")),
    path("", include("network.urls")),
]

# Custom error handlers.
handler404 = "config.views.custom_404"
handler500 = "config.views.custom_500"