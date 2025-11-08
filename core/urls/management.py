"""
Management URLs for one-time administrative tasks.
"""
from django.urls import path
from core.management_views import create_admin_user, recalculate_comment_counts

urlpatterns = [
    path('create-admin/', create_admin_user, name='create-admin'),
    path('recalculate-comment-counts/', recalculate_comment_counts, name='recalculate-comment-counts'),
]
