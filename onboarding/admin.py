"""
Admin configuration for onboarding app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import LeadershipProfile, OnboardingProgress, OnboardingFeedback


@admin.register(LeadershipProfile)
class LeadershipProfileAdmin(admin.ModelAdmin):
    """Admin interface for leadership profiles."""

    list_display = [
        'user',
        'ministry_experience_years',
        'preferred_group_size',
        'meeting_frequency_preference',
        'max_group_capacity',
        'created_at'
    ]

    list_filter = [
        'ministry_experience_years',
        'preferred_group_size',
        'meeting_frequency_preference',
        'created_at'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'ministry_interests',
        'leadership_topics'
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        (_('User Information'), {
            'fields': ('user',)
        }),
        (_('Ministry Experience'), {
            'fields': (
                'ministry_experience_years',
                'ministry_interests'
            )
        }),
        (_('Group Preferences'), {
            'fields': (
                'preferred_group_size',
                'meeting_frequency_preference',
                'max_group_capacity'
            )
        }),
        (_('Leadership Focus'), {
            'fields': (
                'leadership_topics',
                'general_availability'
            )
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    """Admin interface for onboarding progress tracking."""

    list_display = [
        'user',
        'completion_percentage',
        'time_spent_minutes',
        'dropped_off_at_step',
        'started_at',
        'last_activity_at'
    ]

    list_filter = [
        'completion_percentage',
        'dropped_off_at_step',
        'started_at',
        'last_activity_at'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'dropped_off_at_step'
    ]

    readonly_fields = ['started_at', 'last_activity_at']

    fieldsets = (
        (_('User Information'), {
            'fields': ('user',)
        }),
        (_('Progress Tracking'), {
            'fields': (
                'steps_completed',
                'total_steps',
                'completion_percentage',
                'time_spent_minutes'
            )
        }),
        (_('Drop-off Analysis'), {
            'fields': ('dropped_off_at_step',)
        }),
        (_('Timestamps'), {
            'fields': ('started_at', 'last_activity_at')
        })
    )

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(OnboardingFeedback)
class OnboardingFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for onboarding feedback."""

    list_display = [
        'user',
        'step_name',
        'rating',
        'was_helpful',
        'was_confusing',
        'created_at'
    ]

    list_filter = [
        'step_name',
        'rating',
        'was_helpful',
        'was_confusing',
        'created_at'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'step_name',
        'feedback_text',
        'suggestions'
    ]

    readonly_fields = ['created_at']

    fieldsets = (
        (_('User Information'), {
            'fields': ('user', 'step_name')
        }),
        (_('Feedback'), {
            'fields': (
                'rating',
                'feedback_text',
                'was_helpful',
                'was_confusing',
                'suggestions'
            )
        }),
        (_('Timestamp'), {
            'fields': ('created_at',)
        })
    )

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('user')

    def has_change_permission(self, request, obj=None):
        """Make feedback read-only to preserve data integrity."""
        return False
