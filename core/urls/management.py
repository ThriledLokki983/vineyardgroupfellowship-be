"""
Management URLs for one-time administrative tasks.
"""
from django.urls import path
from core.management_views import create_admin_user

urlpatterns = [
    path('create-admin/', create_admin_user, name='create-admin'),
]