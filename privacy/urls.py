"""
URL configuration for the privacy app.
GDPR compliance and data privacy endpoints.
"""

from django.urls import path
from .views import (
    GDPRDataExportView,
    GDPRDataErasureView,
    GDPRConsentView,
    GDPRPrivacyDashboardView,
    GDPRDataRetentionView,
    GDPRDataCleanupView
)

app_name = 'privacy'

urlpatterns = [
    # GDPR Data Export (Article 20 - Right to Data Portability)
    path('gdpr/export/', GDPRDataExportView.as_view(), name='gdpr_data_export'),

    # GDPR Data Erasure (Article 17 - Right to be Forgotten)
    path('gdpr/erasure/', GDPRDataErasureView.as_view(), name='gdpr_data_erasure'),

    # GDPR Consent Management (Article 7 - Consent)
    path('gdpr/consent/', GDPRConsentView.as_view(), name='gdpr_consent_management'),

    # GDPR Privacy Dashboard
    path('gdpr/dashboard/', GDPRPrivacyDashboardView.as_view(), name='gdpr_privacy_dashboard'),

    # GDPR Data Retention Policies
    path('gdpr/retention/', GDPRDataRetentionView.as_view(), name='gdpr_data_retention'),

    # GDPR Data Cleanup
    path('gdpr/cleanup/', GDPRDataCleanupView.as_view(), name='gdpr_data_cleanup'),
]