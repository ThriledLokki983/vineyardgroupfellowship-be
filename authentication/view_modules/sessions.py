"""
Session management views for Vineyard Group Fellowship authentication.

This module handles:
- Listing user sessions
- Terminating specific sessions
- Terminating all user sessions
- Session security monitoring
"""

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
import structlog

from ..serializers import (
    UserSessionSerializer,
    SessionTerminateSerializer,
    SuccessMessageSerializer
)
from ..services import SessionService, AuditLog
from ..models import UserSession
from ..utils.api_docs import authentication_schema, session_management_schema
from ..utils.auth import get_client_ip

logger = structlog.get_logger(__name__)
User = get_user_model()


@session_management_schema(
    operation_id='list_user_sessions',
    summary='List user sessions',
    description='''
    Device sessions, security monitoring, and device management.

    List all active sessions for the authenticated user with comprehensive
    security information including device details, IP addresses, locations,
    and activity timestamps. Helps users monitor account security and identify
    unauthorized access.

    Rate limiting: 30 requests per hour per user.
    ''',
    responses={
        200: UserSessionSerializer(many=True),
        401: 'User not authenticated',
        429: 'Rate limit exceeded'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@method_decorator(never_cache)
@ratelimit(key='user', rate='30/h', method='GET', block=True)
def list_sessions_view(request):
    """
    List all active sessions for the authenticated user.

    This endpoint returns information about all active sessions for the user,
    including device details, IP addresses, and activity timestamps.

    **Authentication**: Required
    **Rate Limiting**: 30 requests per hour per user

    **Response**:
    ```json
    [
        {
            "id": "session-uuid",
            "device_type": "desktop",
            "browser_name": "Chrome",
            "browser_version": "118.0",
            "os_name": "macOS",
            "os_version": "14.0",
            "ip_address": "192.168.1.100",
            "location": "San Francisco, CA, US",
            "is_current": true,
            "created_at": "2023-10-29T10:00:00Z",
            "last_activity": "2023-10-29T15:30:00Z"
        }
    ]
    ```

    **Response Codes**:
    - `200 OK`: Sessions retrieved successfully
    - `401 Unauthorized`: User not authenticated
    - `429 Too Many Requests`: Rate limit exceeded
    """
    try:
        # Get all active sessions for the user
        sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-last_activity')

        # Get current session ID for marking
        current_session_key = request.session.session_key
        current_session_id = None
        if current_session_key:
            try:
                current_session = UserSession.objects.get(
                    session_key=current_session_key,
                    user=request.user,
                    is_active=True
                )
                current_session_id = str(current_session.id)
            except UserSession.DoesNotExist:
                pass

        # Serialize sessions
        serializer = UserSessionSerializer(sessions, many=True, context={
            'current_session_id': current_session_id
        })

        logger.info(
            "Sessions listed",
            user_id=str(request.user.id),
            session_count=len(serializer.data)
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(
            "Session list error",
            user_id=str(request.user.id),
            error=str(e)
        )
        return Response(
            {'error': 'Failed to retrieve sessions. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@session_management_schema(
    operation_id='terminate_session',
    summary='Terminate specific session',
    description='''
    Device sessions, security monitoring, and device management.

    Terminate a specific user session by ID for enhanced security control.
    Immediately invalidates the session and associated tokens. Cannot be
    used to terminate the current session (use logout instead).

    Rate limiting: 20 terminations per hour per user.
    ''',
    request=SessionTerminateSerializer,
    responses={
        200: SuccessMessageSerializer,
        400: 'Invalid session ID or trying to terminate current session',
        401: 'User not authenticated',
        404: 'Session not found',
        429: 'Rate limit exceeded'
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@method_decorator(never_cache)
@ratelimit(key='user', rate='20/h', method='DELETE', block=True)
def terminate_session_view(request):
    """
    Terminate a specific user session.

    This endpoint terminates a specific session by ID. The session must belong
    to the authenticated user. Cannot terminate the current session.

    **Authentication**: Required
    **Rate Limiting**: 20 terminations per hour per user

    **Request Body**:
    ```json
    {
        "session_id": "session-uuid-to-terminate"
    }
    ```

    **Response**:
    - `200 OK`: Session terminated successfully
    - `400 Bad Request`: Invalid session ID or trying to terminate current session
    - `401 Unauthorized`: User not authenticated
    - `404 Not Found`: Session not found
    - `429 Too Many Requests`: Rate limit exceeded
    """
    serializer = SessionTerminateSerializer(data=request.data)

    if not serializer.is_valid():
        logger.warning(
            "Session termination validation failed",
            user_id=str(request.user.id),
            errors=serializer.errors
        )
        return Response(
            {'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        session_id = serializer.validated_data['session_id']

        # Get the session to terminate
        try:
            session = UserSession.objects.get(
                id=session_id,
                user=request.user,
                is_active=True
            )
        except UserSession.DoesNotExist:
            logger.warning(
                "Session not found for termination",
                user_id=str(request.user.id),
                session_id=session_id
            )
            return Response(
                {'error': 'Session not found or already terminated.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if trying to terminate current session
        current_session_key = request.session.session_key
        if current_session_key and session.session_key == current_session_key:
            logger.warning(
                "Attempt to terminate current session",
                user_id=str(request.user.id),
                session_id=session_id
            )
            return Response(
                {'error': 'Cannot terminate current session. Use logout instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Terminate the session
        SessionService.terminate_session(
            session=session,
            reason='user_requested',
            request=request
        )

        logger.info(
            "Session terminated by user",
            user_id=str(request.user.id),
            terminated_session_id=session_id,
            device_type=session.device_type,
            ip_address=session.ip_address
        )

        return Response(
            {
                'message': 'Session terminated successfully.',
                'detail': f'Session from {session.device_type} device has been terminated.'
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(
            "Session termination error",
            user_id=str(request.user.id),
            session_id=serializer.validated_data.get('session_id'),
            error=str(e)
        )
        return Response(
            {'error': 'Failed to terminate session. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@session_management_schema(
    operation_id='terminate_all_sessions',
    summary='Terminate all user sessions',
    description='''
    Device sessions, security monitoring, and device management.

    Terminate all user sessions except the current one for enhanced security.
    Immediately invalidates all other sessions and associated tokens.
    Useful for security incidents or when user suspects unauthorized access.

    Rate limiting: 5 terminations per hour per user.
    ''',
    responses={
        200: SuccessMessageSerializer,
        401: 'User not authenticated',
        429: 'Rate limit exceeded'
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@method_decorator(never_cache)
@ratelimit(key='user', rate='5/h', method='POST', block=True)
def terminate_all_sessions_view(request):
    """
    Terminate all user sessions except the current one.

    This endpoint terminates all active sessions for the user except the
    current session. Useful for security purposes when suspicious activity
    is detected.

    **Authentication**: Required
    **Rate Limiting**: 5 terminations per hour per user

    **Response**:
    - `200 OK`: All other sessions terminated successfully
    - `401 Unauthorized`: User not authenticated
    - `429 Too Many Requests`: Rate limit exceeded
    """
    try:
        # Get current session to exclude
        current_session_key = request.session.session_key
        current_session = None
        if current_session_key:
            try:
                current_session = UserSession.objects.get(
                    session_key=current_session_key,
                    user=request.user,
                    is_active=True
                )
            except UserSession.DoesNotExist:
                pass

        # Count sessions before termination
        all_sessions = UserSession.objects.filter(
            user=request.user,
            is_active=True
        )

        if current_session:
            other_sessions = all_sessions.exclude(id=current_session.id)
        else:
            other_sessions = all_sessions

        session_count = other_sessions.count()

        if session_count == 0:
            logger.info(
                "No other sessions to terminate",
                user_id=str(request.user.id)
            )
            return Response(
                {
                    'message': 'No other active sessions found.',
                    'detail': 'Only your current session is active.'
                },
                status=status.HTTP_200_OK
            )

        # Terminate all other sessions
        SessionService.terminate_all_sessions(
            user=request.user,
            reason='user_requested_all',
            request=request,
            exclude_current=True
        )

        logger.info(
            "All other sessions terminated by user",
            user_id=str(request.user.id),
            terminated_count=session_count
        )

        return Response(
            {
                'message': f'Successfully terminated {session_count} other session(s).',
                'detail': 'Your current session remains active.'
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(
            "Terminate all sessions error",
            user_id=str(request.user.id),
            error=str(e)
        )
        return Response(
            {'error': 'Failed to terminate sessions. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
