# network/urls.py
from django.urls import path
from . import views

app_name = "network"

urlpatterns = [
    path("directory/", views.directory, name="directory"),
    path("directory/<int:pk>/", views.directory_detail, name="directory_detail"),
    path("directory/<int:pk>/request/", views.send_request, name="send_request"),
    path("partnership/requests/", views.request_list, name="request_list"),
    path("partnership/requests/<int:pk>/accept/", views.accept_request, name="accept_request"),
    path("partnership/requests/<int:pk>/decline/", views.decline_request, name="decline_request"),
]