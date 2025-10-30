"""
Password management views for Vineyard Group Fellowship authentication.

This module handles:
- Password change for authenticated users
- Password reset request flow
- Password reset confirmation
- Password validation and security
"""

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django_ratelimit.decorators import ratelimit
import structlog

from ..serializers import (
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    SuccessMessageSerializer
)
from ..services import PasswordService, AuditLog
from drf_spectacular.utils import extend_schema
from core.api_tags import APITags
from ..utils.auth import get_client_ip

logger = structlog.get_logger(__name__)
User = get_user_model()


@extend_schema(
    operation_id='change_password',
    summary='Change user password',
    description='''
    Change password for authenticated user.

    Requires current password for verification. Old password is stored in
    password history to prevent reuse. All user sessions and tokens are
    invalidated after password change.

    Rate limiting: 10 password changes per hour per user.
    ''',
    request=PasswordChangeSerializer,
    responses={
        200: SuccessMessageSerializer,
        400: 'Validation errors or incorrect current password',
        429: 'Rate limit exceeded'
    },
    tags=[APITags.AUTHENTICATION]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@method_decorator(never_cache)
@ratelimit(key='user', rate='10/h', method='POST', block=True)
def change_password_view(request):
    """
    Change password for authenticated user.

    This endpoint allows authenticated users to change their password.
    Requires the current password for verification.

    **Authentication**: Required
    **Rate Limiting**: 10 changes per hour per user

    **Request Body**:
    ```json
    {
        "current_password": "OldPassword123!",
        "new_password": "NewSecurePassword456!",
        "confirm_password": "NewSecurePassword456!"
    }
    ```

    **Response**:
    - `200 OK`: Password changed successfully
    - `400 Bad Request`: Validation errors or incorrect current password
    - `429 Too Many Requests`: Rate limit exceeded
    """
    serializer = PasswordChangeSerializer(data=request.data)

    if not serializer.is_valid():
        logger.warning(
            "Password change validation failed",
            user_id=str(request.user.id),
            errors=serializer.errors
        )
        return Response(
            {'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Change password using service
        PasswordService.change_password(
            user=request.user,
            current_password=serializer.validated_data['current_password'],
            new_password=serializer.validated_data['new_password'],
            request=request
        )

        logger.info(
            "Password changed successfully",
            user_id=str(request.user.id),
            email=request.user.email
        )

        return Response(
            {
                'message': 'Password changed successfully. Please log in again.',
                'detail': 'All sessions have been terminated for security.'
            },
            status=status.HTTP_200_OK
        )

    except ValueError as e:
        logger.warning(
            "Password change failed",
            user_id=str(request.user.id),
            error=str(e)
        )
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        logger.error(
            "Password change error",
            user_id=str(request.user.id),
            error=str(e)
        )
        return Response(
            {'error': 'Password change failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    operation_id='request_password_reset',
    summary='Request password reset',
    description='''
    Request password reset for user account.

    Sends password reset email with secure token. Always returns success
    to prevent email enumeration attacks, even if email doesn't exist.

    Rate limiting: 5 reset requests per hour per IP address.
    ''',
    request=PasswordResetRequestSerializer,
    responses={
        200: SuccessMessageSerializer,
        400: 'Validation errors',
        429: 'Rate limit exceeded'
    },
    tags=[APITags.AUTHENTICATION]
)
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def password_reset_request_view(request):
    """
    Request password reset email.

    This endpoint sends a password reset email to the specified address.
    For security, always returns success even if email doesn't exist.

    **Authentication**: Not required
    **Rate Limiting**: 5 requests per hour per IP

    **Request Body**:
    ```json
    {
        "email": "user@example.com"
    }
    ```

    **Response**:
    - `200 OK`: Reset email sent (or would be sent if email exists)
    - `400 Bad Request`: Validation errors
    - `429 Too Many Requests`: Rate limit exceeded
    """
    serializer = PasswordResetRequestSerializer(data=request.data)

    if not serializer.is_valid():
        logger.warning(
            "Password reset request validation failed",
            ip_address=get_client_ip(request),
            errors=serializer.errors
        )
        return Response(
            {'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        email = serializer.validated_data['email']

        # Process reset request (always returns True for security)
        PasswordService.request_password_reset(
            email=email,
            request=request
        )

        logger.info(
            "Password reset requested",
            email=email,
            ip_address=get_client_ip(request)
        )

        return Response(
            {
                'message': 'If an account with this email exists, a password reset link has been sent.',
                'detail': 'Please check your email for reset instructions.'
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(
            "Password reset request error",
            email=serializer.validated_data.get('email'),
            ip_address=get_client_ip(request),
            error=str(e)
        )
        return Response(
            {
                'message': 'If an account with this email exists, a password reset link has been sent.',
                'detail': 'Please check your email for reset instructions.'
            },
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Password reset confirmation endpoint.

    Supports both GET and POST methods:
    - GET: Validate reset token and show form (for email links)
    - POST: Confirm password reset with new password
    """
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id='validate_password_reset_token',
        summary='Validate password reset token',
        description='Validate password reset token from email link (GET method)',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'token_valid': {'type': 'boolean'},
                    'email': {'type': 'string'}
                }
            },
            400: {'description': 'Invalid or expired token'},
        },
        tags=[APITags.AUTHENTICATION]
    )
    def get(self, request, uidb64=None, token=None):
        """
        Validate password reset token.

        This endpoint validates a password reset token from an email link
        and returns whether the token is valid for password reset.
        """
        # Extract token from URL parameters or query parameters
        token = token or request.GET.get('token')

        if not token:
            return Response(
                {'error': 'Reset token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get and validate reset token
            from ..models import PasswordResetToken
            try:
                reset_token = PasswordResetToken.objects.get(
                    token=token,
                    is_used=False
                )
            except PasswordResetToken.DoesNotExist:
                logger.warning(
                    "Invalid password reset token accessed",
                    token=token[:8] + "...",
                    ip_address=get_client_ip(request)
                )
                return Response(
                    {'error': 'Invalid or expired reset token.', 'token_valid': False},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if token is expired
            if reset_token.is_expired():
                logger.warning(
                    "Expired password reset token accessed",
                    token_id=str(reset_token.id),
                    user_id=str(reset_token.user.id),
                    ip_address=get_client_ip(request)
                )
                return Response(
                    {'error': 'Reset token has expired. Please request a new one.',
                        'token_valid': False},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Token is valid
            logger.info(
                "Valid password reset token accessed",
                token_id=str(reset_token.id),
                user_id=str(reset_token.user.id),
                ip_address=get_client_ip(request)
            )

            return Response(
                {
                    'message': 'Reset token is valid. You can now set a new password.',
                    'token_valid': True,
                    'email': reset_token.user.email
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                "Password reset token validation error",
                error=str(e),
                ip_address=get_client_ip(request)
            )
            return Response(
                {'error': 'Token validation failed. Please try again or request a new reset link.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        operation_id='confirm_password_reset',
        summary='Confirm password reset',
        description='''
        Confirm password reset with token and set new password.

        Uses secure token from reset email to verify identity. Token is
        single-use and expires after 1 hour. All user sessions and tokens
        are invalidated after password reset.

        Rate limiting: 10 reset confirmations per hour per IP address.
        ''',
        request=PasswordResetConfirmSerializer,
        responses={
            200: SuccessMessageSerializer,
            400: 'Invalid token, expired token, or validation errors',
            429: 'Rate limit exceeded'
        },
        tags=[APITags.AUTHENTICATION]
    )
    @method_decorator(csrf_exempt)
    @method_decorator(never_cache)
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def post(self, request, uidb64=None, token=None):
        """
        Confirm password reset with token.

        This endpoint confirms a password reset using the token from the reset email
        and sets a new password for the user.
        """
        # Merge URL token with request data
        data = request.data.copy()
        if token:
            data['token'] = token

        serializer = PasswordResetConfirmSerializer(data=data)

        if not serializer.is_valid():
            logger.warning(
                "Password reset confirm validation failed",
                ip_address=get_client_ip(request),
                errors=serializer.errors
            )
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            # Get and validate reset token
            from ..models import PasswordResetToken
            try:
                reset_token = PasswordResetToken.objects.get(
                    token=token,
                    is_used=False
                )
            except PasswordResetToken.DoesNotExist:
                logger.warning(
                    "Invalid password reset token used",
                    token=token[:8] + "...",  # Log partial token for debugging
                    ip_address=get_client_ip(request)
                )
                return Response(
                    {'error': 'Invalid or expired reset token.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if token is expired
            if reset_token.is_expired():
                logger.warning(
                    "Expired password reset token used",
                    token_id=str(reset_token.id),
                    user_id=str(reset_token.user.id),
                    ip_address=get_client_ip(request)
                )
                return Response(
                    {'error': 'Reset token has expired. Please request a new one.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Reset password using service
            user = PasswordService.reset_password(
                reset_token=reset_token,
                new_password=new_password,
                request=request
            )

            logger.info(
                "Password reset completed",
                user_id=str(user.id),
                email=user.email,
                ip_address=get_client_ip(request)
            )

            return Response(
                {
                    'message': 'Password reset successfully. You can now log in with your new password.',
                    'detail': 'All previous sessions have been terminated for security.'
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            logger.warning(
                "Password reset failed",
                error=str(e),
                ip_address=get_client_ip(request)
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(
                "Password reset confirm error",
                error=str(e),
                ip_address=get_client_ip(request)
            )
            return Response(
                {'error': 'Password reset failed. Please try again or request a new reset link.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Backward compatibility function
@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(never_cache, name='dispatch')
def password_reset_confirm_view(request, uidb64=None, token=None):
    """Backward compatibility wrapper for the class-based view."""
    view = PasswordResetConfirmView()
    if request.method == 'GET':
        return view.get(request, uidb64, token)
    else:
        return view.post(request, uidb64, token)
