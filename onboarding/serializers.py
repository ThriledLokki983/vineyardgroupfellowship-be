"""
Onboarding serializers for Vineyard Group Fellowship.

This module contains serializers for onboarding flow, leadership profiles,
and onboarding progress tracking.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import OnboardingProgress, OnboardingFeedback, LeadershipProfile
from authentication.models import AuditLog

User = get_user_model()


class LeadershipProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for leadership profile setup during onboarding.
    Simple, church-facing information for group leaders.
    """

    class Meta:
        model = LeadershipProfile
        fields = [
            'ministry_experience_years',
            'previous_leadership_roles',
            'ministry_interests',
            'preferred_group_size',
            'meeting_frequency_preference',
            'meeting_format_preference',
            'leadership_topics',
            'general_availability',
            'max_group_capacity',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        """Create leadership profile."""
        request = self.context.get('request')
        validated_data['user'] = request.user
        instance = super().create(validated_data)

        # Log leadership profile creation
        if request:
            AuditLog.objects.create(
                user=request.user,
                event_type='leadership_profile_created',
                description='Leadership profile created during onboarding',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
                risk_level='low',
                metadata={
                    'has_ministry_experience': bool(instance.ministry_experience_years),
                    'preferred_group_size': instance.preferred_group_size,
                    'meeting_frequency': instance.meeting_frequency_preference,
                }
            )

        return instance


class OnboardingCompletionSerializer(serializers.Serializer):
    """
    Serializer for marking onboarding as complete.
    """

    feedback_rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False,
        help_text="Optional rating for overall onboarding experience (1-5)"
    )

    feedback_text = serializers.CharField(
        max_length=1000, required=False, allow_blank=True,
        help_text="Optional feedback about onboarding experience"
    )

    def save(self):
        """Mark user onboarding as complete."""
        request = self.context['request']
        user = request.user

        # Create or update onboarding progress
        progress, created = OnboardingProgress.objects.get_or_create(
            user=user,
            defaults={'completion_percentage': 100.0, 'total_steps': 5}
        )

        # Set completion to 100% regardless of whether it was just created
        if progress.completion_percentage < 100.0:
            progress.completion_percentage = 100.0
            progress.save()

        # Save feedback if provided
        validated_data = self.validated_data
        if validated_data.get('feedback_rating') or validated_data.get('feedback_text'):
            OnboardingFeedback.objects.create(
                user=user,
                step_name='overall_experience',
                rating=validated_data.get('feedback_rating', 5),
                feedback_text=validated_data.get('feedback_text', ''),
                was_helpful=True
            )

        # Log completion
        AuditLog.objects.create(
            user=user,
            event_type='onboarding_completed',
            description='User completed onboarding process',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
            risk_level='low',
            metadata={
                'completion_timestamp': timezone.now().isoformat(),
                'provided_feedback': bool(validated_data.get('feedback_text')),
                'total_time_hours': (timezone.now() - user.date_joined).total_seconds() / 3600,
            }
        )

        return {
            'message': _('Onboarding completed successfully!'),
            'completion_timestamp': timezone.now().isoformat(),
            'next_steps': self._get_next_steps(user),
            'status': 'completed'
        }

    def _get_next_steps(self, user):
        """Get personalized next steps based on user type."""
        # Check if user has leadership permissions
        has_leadership = False
        try:
            profile = user.basic_profile
            has_leadership = profile.leadership_info.get(
                'can_lead_group', False)
        except:
            pass

        if has_leadership:
            return {
                'primary_action': 'Start leading groups in the fellowship',
                'suggestions': [
                    'Create your first group',
                    'Explore group management tools',
                    'Connect with other group leaders',
                    'Review leadership resources'
                ]
            }
        else:
            return {
                'primary_action': 'Explore the Vineyard Group Fellowship community',
                'suggestions': [
                    'Browse available groups to join',
                    'Complete your profile',
                    'Connect with other members',
                    'Explore fellowship resources'
                ]
            }


class OnboardingStepSerializer(serializers.Serializer):
    """
    Serializer for updating onboarding step progress.
    """

    step = serializers.CharField(
        max_length=50,
        help_text="The onboarding step to mark as current"
    )

    time_spent_minutes = serializers.IntegerField(
        min_value=0, required=False,
        help_text="Optional: time spent on previous step in minutes"
    )

    def save(self):
        """Update user's current onboarding step."""
        request = self.context['request']
        user = request.user

        validated_data = self.validated_data
        new_step = validated_data['step']

        # Update or create progress tracking
        progress, created = OnboardingProgress.objects.get_or_create(
            user=user,
            defaults={'total_steps': 5}
        )

        old_step = None
        if not created and progress.steps_completed:
            # Get the last completed step
            completed_steps_list = list(progress.steps_completed.keys())
            if completed_steps_list:
                old_step = completed_steps_list[-1]

        if old_step and old_step != new_step:
            progress.mark_step_completed(old_step)

        # Add time spent if provided
        if validated_data.get('time_spent_minutes'):
            progress.time_spent_minutes += validated_data['time_spent_minutes']
            progress.save()

        # Log step progress
        AuditLog.objects.create(
            user=user,
            event_type='onboarding_step_updated',
            description=f'Onboarding step updated to {new_step}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=True,
            risk_level='low',
            metadata={
                'previous_step': old_step,
                'new_step': new_step,
                'progress_percentage': progress.completion_percentage,
                'time_spent_minutes': validated_data.get('time_spent_minutes', 0),
            }
        )

        return {
            'message': _('Onboarding step updated successfully'),
            'current_step': new_step,
            'previous_step': old_step,
            'progress_percentage': progress.completion_percentage,
        }


class CommunityPreferencesSerializer(serializers.Serializer):
    """
    Serializer for setting user's community preferences during onboarding.
    For fellowship members to express their interests and meeting preferences.
    """

    interest_areas = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="Areas of interest (e.g., 'prayer', 'bible_study', 'youth', 'worship')"
    )

    meeting_preferences = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            ('in_person', 'In Person'),
            ('online', 'Online'),
            ('hybrid', 'Hybrid')
        ]),
        required=False,
        allow_empty=True,
        help_text="Preferred meeting formats"
    )

    notification_preferences = serializers.JSONField(
        required=False,
        help_text="Notification settings"
    )

    privacy_level = serializers.ChoiceField(
        choices=[
            ('private', 'Private'),
            ('community', 'Community Only'),
            ('public', 'Public'),
        ],
        required=False,
        default='community',
        help_text="Privacy level for profile"
    )

    def save(self, user):
        """Save community preferences."""
        validated_data = self.validated_data

        # Update user's profile if exists
        try:
            profile = user.basic_profile
            if 'privacy_level' in validated_data:
                profile.profile_visibility = validated_data['privacy_level']
                profile.save()
        except:
            pass

        # Log the preference update
        AuditLog.objects.create(
            user=user,
            event_type='community_preferences_updated',
            description='Community preferences updated during onboarding',
            success=True,
            risk_level='low',
            metadata={
                'interest_areas': validated_data.get('interest_areas', []),
                'meeting_preferences': validated_data.get('meeting_preferences', []),
                'privacy_level': validated_data.get('privacy_level'),
                'updated_at': timezone.now().isoformat()
            }
        )

        return {
            'message': _('Community preferences saved successfully'),
            'preferences': validated_data
        }


class OnboardingProgressSerializer(serializers.ModelSerializer):
    """
    Serializer for onboarding progress tracking.
    """

    class Meta:
        model = OnboardingProgress
        fields = [
            'steps_completed',
            'total_steps',
            'completion_percentage',
            'started_at',
            'last_activity_at',
            'time_spent_minutes',
            'dropped_off_at_step'
        ]
        read_only_fields = ['started_at', 'last_activity_at']


class OnboardingFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer for onboarding step feedback.
    """

    class Meta:
        model = OnboardingFeedback
        fields = [
            'step_name',
            'rating',
            'feedback_text',
            'was_confusing',
            'was_helpful',
            'suggestions',
            'created_at'
        ]
        read_only_fields = ['created_at']

    def create(self, validated_data):
        """Create feedback and link to user."""
        request = self.context['request']
        validated_data['user'] = request.user
        return super().create(validated_data)
