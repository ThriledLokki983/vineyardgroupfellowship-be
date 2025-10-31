"""
Onboarding models for Vineyard Group Fellowship.

This module contains models related to user onboarding flow,
leadership profiles, and progress tracking.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class LeadershipProfile(models.Model):
    """
    Simple leadership information for group leaders.
    Not for verification - church has already vetted these users.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='leadership_profile'
    )

    # Simple background info (optional, for church records)
    ministry_experience_years = models.PositiveIntegerField(
        _('years of ministry experience'),
        null=True,
        blank=True,
        help_text=_('Optional: Years of ministry or leadership experience')
    )

    previous_leadership_roles = models.TextField(
        _('previous leadership roles'),
        blank=True,
        help_text=_('Optional: Previous leadership experience description')
    )

    ministry_interests = models.JSONField(
        _('ministry interests'),
        default=list,
        blank=True,
        help_text=_(
            'Areas of ministry interest (e.g., youth, couples, men\'s/women\'s groups)')
    )

    # Leadership preferences
    preferred_group_size = models.CharField(
        _('preferred group size'),
        max_length=20,
        choices=[
            ('small', '5-10 people'),
            ('medium', '10-20 people'),
            ('large', '20+ people')
        ],
        default='small'
    )

    meeting_frequency_preference = models.CharField(
        _('meeting frequency preference'),
        max_length=20,
        choices=[
            ('weekly', 'Weekly'),
            ('biweekly', 'Bi-weekly'),
            ('monthly', 'Monthly')
        ],
        default='weekly'
    )

    meeting_format_preference = models.JSONField(
        _('meeting format preferences'),
        default=list,
        blank=True,
        help_text=_('Preferred formats: in_person, online, hybrid')
    )

    # Topic areas comfortable leading
    leadership_topics = models.JSONField(
        _('leadership topics'),
        default=list,
        blank=True,
        help_text=_(
            'Topic areas comfortable leading (e.g., prayer, bible_study, outreach)')
    )

    # Availability
    general_availability = models.JSONField(
        _('general availability'),
        default=dict,
        blank=True,
        help_text=_(
            'General availability by day/time (e.g., {"monday": ["evening"], "tuesday": ["morning", "evening"]})')
    )

    max_group_capacity = models.PositiveIntegerField(
        _('maximum group capacity'),
        default=1,
        help_text=_('Maximum number of groups willing to lead simultaneously')
    )

    # Status
    is_active = models.BooleanField(
        _('is active'),
        default=True,
        help_text=_('Whether the leader is currently active')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Leadership Profile')
        verbose_name_plural = _('Leadership Profiles')
        db_table = 'onboarding_leadership_profile'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Leadership Profile for {self.user.email}"

    @property
    def is_group_leader(self):
        """Check if user has leadership permissions."""
        try:
            profile = self.user.basic_profile
            return profile.leadership_info.get('can_lead_group', False)
        except:
            return False


class OnboardingProgress(models.Model):
    """
    Track detailed onboarding progress for analytics and UX improvement.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='onboarding_progress'
    )

    # Step completion tracking
    steps_completed = models.JSONField(
        _('completed steps'),
        default=dict,
        help_text=_('Dictionary tracking completion timestamp for each step')
    )

    total_steps = models.PositiveIntegerField(
        _('total steps'),
        default=0,
        help_text=_('Total number of steps in user\'s personalized flow')
    )

    completion_percentage = models.FloatField(
        _('completion percentage'),
        default=0.0,
        help_text=_('Percentage of onboarding completed')
    )

    # Time tracking
    started_at = models.DateTimeField(
        _('onboarding started at'),
        auto_now_add=True
    )

    last_activity_at = models.DateTimeField(
        _('last activity at'),
        auto_now=True
    )

    time_spent_minutes = models.PositiveIntegerField(
        _('time spent (minutes)'),
        default=0,
        help_text=_('Total time spent in onboarding process')
    )

    # Drop-off tracking
    dropped_off_at_step = models.CharField(
        _('dropped off at step'),
        max_length=50,
        blank=True,
        null=True,
        help_text=_('Step where user last stopped (for drop-off analysis)')
    )

    class Meta:
        verbose_name = _('Onboarding Progress')
        verbose_name_plural = _('Onboarding Progress Records')
        db_table = 'onboarding_progress'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['completion_percentage']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return f"Onboarding Progress for {self.user.username} ({self.completion_percentage:.1f}%)"

    def mark_step_completed(self, step_name):
        """Mark a specific step as completed."""
        from django.utils import timezone

        if not self.steps_completed:
            self.steps_completed = {}

        self.steps_completed[step_name] = timezone.now().isoformat()
        self.completion_percentage = (
            len(self.steps_completed) / self.total_steps) * 100 if self.total_steps > 0 else 0
        self.save()

    def get_next_step(self):
        """Get the next step in the onboarding flow."""
        from .utils import get_onboarding_steps_for_user

        all_steps = get_onboarding_steps_for_user(self.user)
        completed_steps = set(self.steps_completed.keys()
                              ) if self.steps_completed else set()

        for step in all_steps:
            if step not in completed_steps:
                return step

        return 'completed'


class OnboardingFeedback(models.Model):
    """
    Collect feedback about the onboarding experience.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='onboarding_feedback'
    )

    step_name = models.CharField(
        _('step name'),
        max_length=50,
        help_text=_('The onboarding step this feedback relates to')
    )

    rating = models.PositiveIntegerField(
        _('rating'),
        choices=[(i, f'{i} stars') for i in range(1, 6)],
        help_text=_('1-5 star rating for this step')
    )

    feedback_text = models.TextField(
        _('feedback text'),
        blank=True,
        help_text=_('Optional detailed feedback')
    )

    was_confusing = models.BooleanField(
        _('was confusing'),
        default=False
    )

    was_helpful = models.BooleanField(
        _('was helpful'),
        default=True
    )

    suggestions = models.TextField(
        _('suggestions'),
        blank=True,
        help_text=_('Suggestions for improvement')
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Onboarding Feedback')
        verbose_name_plural = _('Onboarding Feedback')
        db_table = 'onboarding_feedback'
        ordering = ['-created_at']
        # One feedback per step per user
        unique_together = [['user', 'step_name']]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['step_name']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return f"Feedback for {self.step_name} by {self.user.username}"
