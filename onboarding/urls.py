"""
URL configuration for the onboarding app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'onboarding'

# API URL patterns
urlpatterns = [
    # Onboarding completion
    path('complete/', views.OnboardingCompletionView.as_view(), name='complete'),

    # Step progression
    path('step/', views.OnboardingStepView.as_view(), name='step'),

    # Community preferences configuration
    path('community-preferences/', views.CommunityPreferencesView.as_view(),
         name='community-preferences'),

    # Personalized onboarding flow
    path('flow/', views.OnboardingFlowView.as_view(), name='flow'),

    # Leadership profile setup
    path('leadership-profile/', views.LeadershipProfileView.as_view(),
         name='leadership-profile'),

    # Feedback collection
    path('feedback/', views.OnboardingFeedbackView.as_view(), name='feedback'),
]
