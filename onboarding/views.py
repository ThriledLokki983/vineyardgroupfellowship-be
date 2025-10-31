"""
Onboarding views for Vineyard Group Fellowship.

This module contains all views related to user onboarding flow,
leadership profile setup, and onboarding progress tracking.
"""

import logging
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import LeadershipProfile
from .serializers import (
    OnboardingCompletionSerializer,
    OnboardingStepSerializer,
    CommunityPreferencesSerializer,
    OnboardingFeedbackSerializer,
    LeadershipProfileSerializer
)
from .permissions import IsGroupLeader, OnboardingInProgress, OnboardingCompleted
from .utils import (
    get_onboarding_steps_for_user,
    get_step_metadata,
    get_personalized_welcome_message,
    get_onboarding_analytics_data
)

logger = logging.getLogger(__name__)


class OnboardingCompletionView(APIView):
    """
    Complete user onboarding process.

    Marks the user as fully onboarded and tracks completion timestamp.
    """

    permission_classes = [IsAuthenticated, OnboardingInProgress]
    throttle_scope = 'onboarding'

    @extend_schema(
        summary="Complete Onboarding",
        description="Mark user onboarding as complete with optional feedback.",
        request=OnboardingCompletionSerializer,
        responses={
            200: OpenApiResponse(description='Onboarding completed successfully'),
            400: OpenApiResponse(description='Invalid data'),
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Onboarding already completed')
        },
        tags=['Onboarding']
    )
    def post(self, request):
        """Mark user onboarding as complete."""
        try:
            serializer = OnboardingCompletionSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(
                f"Error completing onboarding for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to complete onboarding. Please try again.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OnboardingStepView(APIView):
    """
    Update current onboarding step.

    Allows frontend to track progress through onboarding flow.
    """

    permission_classes = [IsAuthenticated, OnboardingInProgress]
    throttle_scope = 'onboarding'

    @extend_schema(
        summary="Update Onboarding Step",
        description="Update the current onboarding step and track progress.",
        request=OnboardingStepSerializer,
        responses={
            200: OpenApiResponse(description='Step updated successfully'),
            400: OpenApiResponse(description='Invalid step data'),
            401: OpenApiResponse(description='Authentication required')
        },
        tags=['Onboarding']
    )
    def patch(self, request):
        """Update current onboarding step."""
        try:
            logger.info(
                f"Onboarding step update request - User: {request.user.id}, Data: {request.data}")

            serializer = OnboardingStepSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                result = serializer.save()
                return Response(result, status=status.HTTP_200_OK)
            else:
                logger.warning(
                    f"Invalid onboarding step data for user {request.user.id}: {serializer.errors}")
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(
                f"Error updating onboarding step for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to update onboarding step. Please try again.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Get Onboarding Status",
        description="Get current onboarding status and progress.",
        responses={
            200: OpenApiResponse(description='Onboarding status retrieved'),
            401: OpenApiResponse(description='Authentication required')
        },
        tags=['Onboarding']
    )
    def get(self, request):
        """Get current onboarding status."""
        try:
            user = request.user
            analytics = get_onboarding_analytics_data(user)

            # Check if onboarding is complete
            is_completed = False
            try:
                progress = user.onboarding_progress
                is_completed = progress.completion_percentage >= 100
            except:
                pass

            return Response({
                'is_onboarded': is_completed,
                'analytics': analytics
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error retrieving onboarding status for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to retrieve onboarding status.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommunityPreferencesView(APIView):
    """
    Set community preferences during onboarding.

    Dedicated endpoint for configuring user's community and privacy preferences.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = 'onboarding'

    @extend_schema(
        summary="Set Community Preferences",
        description="Configure community preferences during onboarding.",
        request=CommunityPreferencesSerializer,
        responses={
            200: OpenApiResponse(description='Preferences saved'),
            400: OpenApiResponse(description='Invalid data'),
            401: OpenApiResponse(description='Authentication required')
        },
        tags=['Onboarding']
    )
    def post(self, request):
        """Save community preferences."""
        try:
            serializer = CommunityPreferencesSerializer(data=request.data)

            if serializer.is_valid():
                result = serializer.save(user=request.user)

                response_data = {
                    'message': 'Community preferences saved successfully',
                    'next_step': 'onboarding_complete'
                }

                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(
                f"Error saving community preferences for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to save community preferences. Please try again.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Get Community Preferences",
        description="Get current community preferences.",
        responses={
            200: OpenApiResponse(description='Preferences retrieved'),
            401: OpenApiResponse(description='Authentication required')
        },
        tags=['Onboarding']
    )
    def get(self, request):
        """Get current community preferences."""
        try:
            user = request.user
            privacy_level = 'community'

            try:
                profile = user.basic_profile
                privacy_level = profile.profile_visibility
            except:
                pass

            response_data = {
                'community_preferences': {
                    'privacy_level': privacy_level
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error retrieving community preferences for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to retrieve community preferences.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OnboardingFlowView(APIView):
    """
    API endpoint for getting personalized onboarding flow based on user type.

    Returns customized step sequence, progress tracking, and step metadata
    tailored to whether the user is a group member or group leader.
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'onboarding'

    @extend_schema(
        summary="Get Onboarding Flow",
        description="Get personalized onboarding flow and progress for current user.",
        responses={
            200: OpenApiResponse(description='Onboarding flow retrieved'),
            401: OpenApiResponse(description='Authentication required')
        },
        tags=['Onboarding']
    )
    def get(self, request):
        """Get personalized onboarding flow for current user."""
        try:
            user = request.user

            # Determine if user has leadership permissions
            has_leadership = False
            try:
                profile = user.basic_profile
                has_leadership = profile.leadership_info.get(
                    'can_lead_group', False)
            except:
                pass

            user_type = 'leader' if has_leadership else 'member'

            # Try to get current step from progress
            current_step = 'welcome'
            try:
                progress = user.onboarding_progress
                if progress.steps_completed:
                    completed_list = list(progress.steps_completed.keys())
                    if completed_list and completed_list[-1] != 'completed':
                        # Get the next step after the last completed one
                        valid_steps = get_onboarding_steps_for_user(user)
                        try:
                            last_index = valid_steps.index(completed_list[-1])
                            if last_index + 1 < len(valid_steps):
                                current_step = valid_steps[last_index + 1]
                        except ValueError:
                            pass
            except:
                pass

            # Get step metadata
            step_metadata = get_step_metadata()

            # Get valid steps for user
            valid_steps = get_onboarding_steps_for_user(user)

            # Build step details
            remaining_steps = []
            completed_steps = []

            try:
                current_index = valid_steps.index(current_step)
            except ValueError:
                current_index = 0
                current_step = valid_steps[0] if valid_steps else 'welcome'

            for i, step in enumerate(valid_steps):
                step_info = {
                    'step': step,
                    'title': step_metadata.get(step, {}).get('title', step.replace('_', ' ').title()),
                    'description': step_metadata.get(step, {}).get('description', ''),
                    'required': step_metadata.get(step, {}).get('required', True),
                    'estimated_minutes': step_metadata.get(step, {}).get('estimated_minutes', 3),
                    'category': step_metadata.get(step, {}).get('category', 'general'),
                    'order': i + 1
                }

                if i < current_index:
                    completed_steps.append(step_info)
                else:
                    remaining_steps.append(step_info)

            progress_percentage = round(
                (len(completed_steps) / len(valid_steps)) * 100) if valid_steps else 0

            # Get personalized welcome message
            welcome_message = get_personalized_welcome_message(user)

            # Get analytics data
            analytics = get_onboarding_analytics_data(user)

            return Response({
                'user_type': user_type,
                'total_steps': len(valid_steps),
                'current_step': current_step,
                'completed_steps': completed_steps,
                'remaining_steps': remaining_steps,
                'progress_percentage': progress_percentage,
                'welcome_message': welcome_message,
                'analytics': analytics
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error retrieving onboarding flow for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to retrieve onboarding flow.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LeadershipProfileView(APIView):
    """
    API endpoint for leadership profile setup.

    Only group leaders can access this endpoint to set up their
    leadership profile including ministry experience and group preferences.
    """
    permission_classes = [IsAuthenticated, IsGroupLeader]
    throttle_scope = 'onboarding'

    @extend_schema(
        summary="Get Leadership Profile",
        description="Get current leadership profile information.",
        responses={
            200: LeadershipProfileSerializer,
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Only group leaders can access this')
        },
        tags=['Onboarding']
    )
    def get(self, request):
        """Get current leadership profile."""
        try:
            user = request.user

            try:
                profile = user.leadership_profile
                serializer = LeadershipProfileSerializer(profile)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except LeadershipProfile.DoesNotExist:
                return Response({}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error retrieving leadership profile for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to retrieve leadership profile.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Save Leadership Profile",
        description="Save leadership profile information and preferences.",
        request=LeadershipProfileSerializer,
        responses={
            200: OpenApiResponse(description='Leadership profile saved'),
            400: OpenApiResponse(description='Invalid data'),
            401: OpenApiResponse(description='Authentication required'),
            403: OpenApiResponse(description='Only group leaders can access this')
        },
        tags=['Onboarding']
    )
    def post(self, request):
        """Save leadership profile information."""
        try:
            user = request.user

            profile, created = LeadershipProfile.objects.get_or_create(
                user=user
            )

            serializer = LeadershipProfileSerializer(
                profile,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                profile = serializer.save()

                return Response({
                    'message': 'Leadership profile saved successfully',
                    'next_step': 'group_preferences'
                }, status=status.HTTP_200_OK)

            logger.error(f"Serializer validation failed: {serializer.errors}")
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(
                f"Error saving leadership profile for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to save supporter background.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OnboardingFeedbackView(APIView):
    """
    API endpoint for collecting onboarding feedback.
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'onboarding'

    @extend_schema(
        summary="Submit Onboarding Feedback",
        description="Submit feedback for a specific onboarding step.",
        request=OnboardingFeedbackSerializer,
        responses={
            201: OpenApiResponse(description='Feedback submitted successfully'),
            400: OpenApiResponse(description='Invalid feedback data'),
            401: OpenApiResponse(description='Authentication required')
        },
        tags=['Onboarding']
    )
    def post(self, request):
        """Submit feedback for an onboarding step."""
        try:
            serializer = OnboardingFeedbackSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                feedback = serializer.save()
                return Response({
                    'message': _('Thank you for your feedback!'),
                    'feedback_id': feedback.id
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(
                f"Error saving onboarding feedback for user {request.user.id}: {str(e)}")
            return Response({
                'error': _('Failed to save feedback. Please try again.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
