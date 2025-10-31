"""
Onboarding utilities for Vineyard Group Fellowship.

This module contains utility functions for managing onboarding flows,
step progression, and user type detection (members vs leaders).
"""

from django.utils.translation import gettext_lazy as _


def get_onboarding_steps_for_user(user):
    """
    Get the complete onboarding step sequence for a user based on their role.

    Args:
        user: User instance

    Returns:
        list: Ordered list of onboarding step names
    """
    # Check if user has leadership permissions
    has_leadership = False
    try:
        profile = user.basic_profile
        has_leadership = profile.leadership_info.get('can_lead_group', False)
    except:
        pass

    if has_leadership:
        # Leadership onboarding flow (10-15 minutes)
        return [
            'welcome',
            'profile_setup',
            'privacy_settings',
            'leadership_information',
            'group_preferences',
            'community_preferences',
            'notifications',
            'guidelines_agreement',
            'completed'
        ]
    else:
        # Member onboarding flow (5-8 minutes)
        return [
            'welcome',
            'profile_setup',
            'privacy_settings',
            'community_preferences',
            'notifications',
            'completed'
        ]


def get_step_metadata():
    """
    Get metadata for all onboarding steps.

    Returns:
        dict: Step metadata with titles, descriptions, and requirements
    """
    return {
        'welcome': {
            'title': _('Welcome'),
            'description': _('Welcome to Vineyard Group Fellowship'),
            'estimated_minutes': 2,
            'required': True,
            'category': 'introduction'
        },
        'profile_setup': {
            'title': _('Profile Setup'),
            'description': _('Basic profile information'),
            'estimated_minutes': 5,
            'required': True,
            'category': 'profile'
        },
        'privacy_settings': {
            'title': _('Privacy Settings'),
            'description': _('Your privacy preferences'),
            'estimated_minutes': 3,
            'required': True,
            'category': 'privacy'
        },
        'leadership_information': {
            'title': _('Leadership Information'),
            'description': _('Tell us about your ministry experience'),
            'estimated_minutes': 5,
            'required': True,
            'category': 'leadership'
        },
        'group_preferences': {
            'title': _('Group Preferences'),
            'description': _('Your group leadership preferences'),
            'estimated_minutes': 4,
            'required': True,
            'category': 'leadership'
        },
        'community_preferences': {
            'title': _('Community'),
            'description': _('Community participation preferences'),
            'estimated_minutes': 3,
            'required': False,
            'category': 'community'
        },
        'notifications': {
            'title': _('Notifications'),
            'description': _('Notification preferences'),
            'estimated_minutes': 2,
            'required': False,
            'category': 'settings'
        },
        'guidelines_agreement': {
            'title': _('Leadership Guidelines'),
            'description': _('Review and accept leadership guidelines'),
            'estimated_minutes': 3,
            'required': True,
            'category': 'leadership'
        },
        'completed': {
            'title': _('Complete'),
            'description': _('Onboarding complete'),
            'estimated_minutes': 1,
            'required': True,
            'category': 'completion'
        }
    }


def get_next_step(current_step, user):
    """
    Get the next step in the onboarding flow.

    Args:
        current_step (str): Current onboarding step
        user: User instance

    Returns:
        str: Next step name or 'completed'
    """
    steps = get_onboarding_steps_for_user(user)

    try:
        current_index = steps.index(current_step)
        if current_index + 1 < len(steps):
            return steps[current_index + 1]
    except ValueError:
        # Current step not found, return first step
        return steps[0] if steps else 'completed'

    return 'completed'


def get_previous_step(current_step, user):
    """
    Get the previous step in the onboarding flow.

    Args:
        current_step (str): Current onboarding step
        user: User instance

    Returns:
        str: Previous step name or None if at beginning
    """
    steps = get_onboarding_steps_for_user(user)

    try:
        current_index = steps.index(current_step)
        if current_index > 0:
            return steps[current_index - 1]
    except ValueError:
        pass

    return None


def calculate_completion_percentage(completed_steps, user):
    """
    Calculate onboarding completion percentage.

    Args:
        completed_steps (list): List of completed step names
        user: User instance

    Returns:
        float: Completion percentage (0-100)
    """
    total_steps = get_onboarding_steps_for_user(user)
    if not total_steps:
        return 100.0

    completed_count = len(
        [step for step in completed_steps if step in total_steps])
    return (completed_count / len(total_steps)) * 100.0


def get_estimated_time_remaining(current_step, user):
    """
    Get estimated time remaining in onboarding.

    Args:
        current_step (str): Current onboarding step
        user: User instance

    Returns:
        int: Estimated minutes remaining
    """
    steps = get_onboarding_steps_for_user(user)
    metadata = get_step_metadata()

    try:
        current_index = steps.index(current_step)
        remaining_steps = steps[current_index + 1:]
    except ValueError:
        remaining_steps = steps

    total_minutes = sum(
        metadata.get(step, {}).get('estimated_minutes', 3)
        for step in remaining_steps
    )

    return total_minutes


def validate_step_transition(from_step, to_step, user):
    """
    Validate that a step transition is allowed.

    Args:
        from_step (str): Current step
        to_step (str): Target step
        user: User instance

    Returns:
        tuple: (is_valid, error_message)
    """
    steps = get_onboarding_steps_for_user(user)

    if to_step not in steps:
        return False, f"Step '{to_step}' is not valid for your user type"

    if from_step not in steps:
        return False, f"Current step '{from_step}' is not valid"

    from_index = steps.index(from_step)
    to_index = steps.index(to_step)

    # Allow moving forward or backward by at most 2 steps
    # This prevents users from skipping required steps but allows some flexibility
    if abs(to_index - from_index) > 2:
        return False, "Cannot skip more than 2 steps at once"

    return True, None


def get_onboarding_analytics_data(user):
    """
    Get analytics data for onboarding progress.

    Args:
        user: User instance

    Returns:
        dict: Analytics data
    """
    from .models import OnboardingProgress

    try:
        progress = user.onboarding_progress
    except OnboardingProgress.DoesNotExist:
        return {
            'started': False,
            'completion_percentage': 0.0,
            'time_spent_minutes': 0,
            'estimated_time_remaining': get_estimated_time_remaining('welcome', user)
        }

    # Get current step from completed steps
    current_step = 'welcome'
    if progress.steps_completed:
        completed_list = list(progress.steps_completed.keys())
        if completed_list:
            current_step = completed_list[-1]

    return {
        'started': True,
        'completion_percentage': progress.completion_percentage,
        'time_spent_minutes': progress.time_spent_minutes,
        'estimated_time_remaining': get_estimated_time_remaining(
            current_step,
            user
        ),
        'steps_completed': len(progress.steps_completed) if progress.steps_completed else 0,
        'last_activity': progress.last_activity_at,
        'dropped_off_at': progress.dropped_off_at_step
    }


def get_personalized_welcome_message(user):
    """
    Get a personalized welcome message based on user type.

    Args:
        user: User instance

    Returns:
        dict: Welcome message data
    """
    # Check if user has leadership permissions
    has_leadership = False
    try:
        profile = user.basic_profile
        has_leadership = profile.leadership_info.get('can_lead_group', False)
    except:
        pass

    if has_leadership:
        return {
            'title': _('Welcome, Group Leader'),
            'message': _("Thank you for choosing to lead in the Vineyard Group Fellowship. Let's set up your leadership profile."),
            'primary_action': _('Set Up Leadership Profile'),
            'secondary_message': _('We will help you connect with and support your group members.')
        }
    else:
        return {
            'title': _('Welcome to Vineyard Group Fellowship'),
            'message': _("We're glad you're here. Let's personalize your experience and connect you with your fellowship community."),
            'primary_action': _('Get Started'),
            'secondary_message': _('You can always change your preferences later.')
        }


def get_personalized_welcome_message(user):
    """
    Get a personalized welcome message based on user type.

    Args:
        user: User instance

    Returns:
        dict: Welcome message data
    """
    # Check if user has leadership permissions
    has_leadership = False
    try:
        profile = user.basic_profile
        has_leadership = profile.leadership_info.get('can_lead_group', False)
    except:
        pass

    if has_leadership:
        return {
            'title': _('Welcome, Group Leader'),
            'message': _("Thank you for choosing to lead in the Vineyard Group Fellowship. Let's set up your leadership profile."),
            'primary_action': _('Set Up Leadership Profile'),
            'secondary_message': _('We will help you connect with and support your group members.')
        }
    else:
        return {
            'title': _('Welcome to Vineyard Group Fellowship'),
            'message': _("We're glad you're here. Let's personalize your experience and connect you with your fellowship community."),
            'primary_action': _('Get Started'),
            'secondary_message': _('You can always change your preferences later.')
        }


def get_personalized_welcome_message(user_profile):
    """
    Get a personalized welcome message based on user purpose.

    Args:
        user_profile: UserProfile instance

    Returns:
        dict: Welcome message data
    """
    if user_profile.user_purpose == 'seeking_recovery':
        return {
            'title': _('Welcome to Your Recovery Journey'),
            'message': _("We're here to support you every step of the way. Let's get you connected with the right resources and community."),
            'primary_action': _('Start My Recovery Journey'),
            'secondary_message': _('Take your time - we will save your progress as you go.')
        }
    elif user_profile.user_purpose == 'providing_support':
        return {
            'title': _('Welcome, Recovery Supporter'),
            'message': _("Thank you for choosing to help others in their recovery journey. Let's set up your supporter profile."),
            'primary_action': _('Set Up My Supporter Profile'),
            'secondary_message': _('We will help you connect with people who can benefit from your experience.')
        }
    else:
        return {
            'title': _('Welcome to AddictFree'),
            'message': _("We're glad you're here. Let's personalize your experience based on how you'd like to use our platform."),
            'primary_action': _('Get Started'),
            'secondary_message': _('You can always change your preferences later.')
        }
