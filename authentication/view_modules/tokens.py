"""
Token management views: JWT refresh and exchange functionality.

This module handles JWT token operations including token refresh
with rotation and exchange token flows for secure authentication.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from core.api_tags import APITags

from core.exceptions import ProblemDetailException
from core.throttling import (
    TokenRefreshRateThrottle,
    AnonRateThrottle,
)

from authentication.utils.cookies import (
    set_refresh_token_cookie,
    get_refresh_token_from_request,
    get_refresh_token_from_cookie,
)

from ..models import UserSession, AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class RefreshTokenView(APIView):
    """
    Custom JWT refresh token view with httpOnly cookie support.

    Features:
    - Reads refresh token from httpOnly cookie
    - Token rotation (issues new refresh token)
    - Session validation
    - Security logging
    - Backward compatibility with body-based tokens
    """
    permission_classes = [AllowAny]
    throttle_classes = [TokenRefreshRateThrottle]

    @extend_schema(
        operation_id='auth_token_refresh',
        summary='Refresh Access Token',
        description='Refresh JWT access token using httpOnly cookie',
        request=None,  # No body needed (cookie-based)
        responses={
            200: OpenApiResponse(
                description='Token refreshed successfully',
                examples={
                    'application/json': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    }
                }
            ),
            401: OpenApiResponse(description='Invalid or expired refresh token'),
        },
        tags=[APITags.SESSION_MANAGEMENT]
    )
    def post(self, request, *args, **kwargs):
        """Refresh JWT token using httpOnly cookie."""
        try:
            # Get refresh token from cookie (with body fallback for backward compatibility)
            refresh_token_str = get_refresh_token_from_request(request)

            if not refresh_token_str:
                raise ProblemDetailException(
                    title="No Refresh Token",
                    detail=_(
                        "Refresh token not found in cookie or request body."),
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

            # Verify and decode refresh token
            try:
                refresh_token = RefreshToken(refresh_token_str)
            except TokenError as e:
                logger.warning(f"Invalid refresh token: {e}")
                raise ProblemDetailException(
                    title="Invalid Refresh Token",
                    detail=_("The provided refresh token is invalid or expired."),
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

            # Get user from token
            user_id = refresh_token.get('user_id')
            if not user_id:
                raise ProblemDetailException(
                    title="Invalid Token Payload",
                    detail=_("Refresh token does not contain user information."),
                    status_code=status.HTTP_401_UNAUTHORIZED
                )

            # Verify user still exists and is active
            try:
                user = User.objects.get(id=user_id)
                if not user.is_active:
                    raise ProblemDetailException(
                        title="Account Disabled",
                        detail=_("This account has been disabled."),
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            except User.DoesNotExist:
                raise ProblemDetailException(
                    title="User Not Found",
                    detail=_("User associated with this token no longer exists."),
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Token rotation - blacklist old token and issue new one
            if getattr(settings, 'SIMPLE_JWT', {}).get('ROTATE_REFRESH_TOKENS', False):
                # Blacklist the old refresh token
                try:
                    refresh_token.blacklist()
                except AttributeError:
                    # Token blacklist not enabled
                    pass

                # Generate new refresh token
                new_refresh = RefreshToken.for_user(user)
                new_access = new_refresh.access_token

                # Update session with new token JTI
                session = UserSession.objects.filter(
                    user=user,
                    refresh_token_jti=str(refresh_token.get('jti')),
                    is_active=True
                ).first()

                if session:
                    session.refresh_token_jti = str(new_refresh['jti'])
                    session.last_rotation_at = timezone.now()
                    session.save(update_fields=[
                                 'refresh_token_jti', 'last_rotation_at'])
            else:
                # No rotation - just issue new access token
                new_refresh = refresh_token
                new_access = refresh_token.access_token

            # Log token refresh
            AuditLog.objects.create(
                user=user,
                event_type='token_refreshed',
                description='Access token refreshed successfully',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Test Client'),
                success=True,
                risk_level='low',
                metadata={
                    'refresh_method': 'cookie' if refresh_token_str == get_refresh_token_from_cookie(request) else 'body',
                    'token_rotated': getattr(settings, 'SIMPLE_JWT', {}).get('ROTATE_REFRESH_TOKENS', False)
                }
            )

            logger.info(f"Token refreshed for user: {user.email}")

            # Response with new access token only
            response = Response({
                'access': str(new_access)
            }, status=status.HTTP_200_OK)

            # Set new refresh token cookie (rotation)
            if getattr(settings, 'SIMPLE_JWT', {}).get('ROTATE_REFRESH_TOKENS', False):
                response = set_refresh_token_cookie(response, str(new_refresh))

            return response

        except ProblemDetailException:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            raise ProblemDetailException(
                title="Token Refresh Failed",
                detail=_("An error occurred while refreshing the token."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExchangeTokenView(APIView):
    """
    Exchange a temporary verification token for JWT access/refresh tokens.

    This endpoint provides secure token exchange for email verification flows.
    Exchange tokens are short-lived, single-use tokens that prevent JWT tokens
    from appearing in URLs or browser history.

    Features:
    - Single-use exchange tokens
    - Automatic user session creation
    - Security audit logging
    - Device fingerprinting
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        operation_id='exchange_token_for_jwt',
        summary='Exchange Token for JWT',
        description='Exchange a one-time verification token for JWT access/refresh tokens',
        request=inline_serializer(
            name='ExchangeTokenRequest',
            fields={
                'exchange_token': serializers.CharField(
                    help_text='One-time exchange token from email verification'
                ),
            }
        ),
        responses={
            200: OpenApiResponse(
                description='Token exchange successful',
                examples={
                    'application/json': {
                        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'user_id': 123,
                        'email': 'user@example.com',
                        'expires_in': 900,
                        'first_login': True,
                        'message': 'Authentication successful. Welcome to Vineyard Group Fellowship!'
                    }
                }
            ),
            400: OpenApiResponse(
                description='Invalid or expired exchange token',
                examples={
                    'application/json': {
                        'error': 'Invalid or expired exchange token'
                    }
                }
            ),
            429: OpenApiResponse(description='Rate limit exceeded'),
        },
        tags=[APITags.SESSION_MANAGEMENT]
    )
    def post(self, request):
        """Exchange a temporary token for JWT access/refresh tokens."""
        exchange_token = request.data.get('exchange_token')

        if not exchange_token:
            return Response({
                'error': _('Exchange token is required.')
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Import exchange token service
            from ..services import ExchangeTokenService, AuthenticationService

            # Extract request metadata for session creation
            request_metadata = AuthenticationService.extract_request_metadata(
                request)

            # Exchange token for JWT tokens
            token_data = ExchangeTokenService.exchange_for_jwt_tokens(
                exchange_token=exchange_token,
                request_meta=request_metadata
            )

            # Create HTTP response with refresh token cookie
            response = Response({
                'access_token': token_data['access_token'],
                'user_id': token_data['user_id'],
                'email': token_data['email'],
                'expires_in': token_data['expires_in'],
                'first_login': token_data['context'].get('first_login', False),
                'message': _('Authentication successful. Welcome to Vineyard Group Fellowship!')
            }, status=status.HTTP_200_OK)

            # Set refresh token as httpOnly cookie (secure)
            response = set_refresh_token_cookie(
                response, token_data['refresh_token'])

            logger.info(
                f"Successful token exchange for user {token_data['user_id']}")

            return response

        except ValueError as e:
            # Log failed exchange attempt
            logger.warning(f"Failed token exchange attempt: {str(e)}")

            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in token exchange: {str(e)}")

            return Response({
                'error': _('An unexpected error occurred. Please try again.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TokenVerifyView(APIView):
    """
    Verify JWT access token validity.

    This endpoint verifies if a JWT access token is valid and returns
    information about the token and associated user. Useful for client-side
    token validation and debugging authentication issues.

    Features:
    - Token signature verification
    - Token expiration checking
    - User account status validation
    - Security audit logging
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        operation_id='verify_jwt_token',
        summary='Verify JWT Token',
        description='Verify the validity of a JWT access token',
        request=inline_serializer(
            name='TokenVerifyRequest',
            fields={
                'token': serializers.CharField(
                    help_text='JWT access token to verify'
                ),
            }
        ),
        responses={
            200: OpenApiResponse(
                description='Token is valid',
                examples={
                    'application/json': {
                        'valid': True,
                        'user_id': 123,
                        'email': 'user@example.com',
                        'expires_at': '2025-10-30T18:15:30Z',
                        'token_type': 'access',
                        'message': 'Token is valid'
                    }
                }
            ),
            400: OpenApiResponse(
                description='Invalid or expired token',
                examples={
                    'application/json': {
                        'valid': False,
                        'error': 'Token is invalid or expired'
                    }
                }
            ),
            429: OpenApiResponse(description='Rate limit exceeded'),
        },
        tags=[APITags.AUTHENTICATION]
    )
    def post(self, request):
        """Verify JWT access token validity."""
        token_str = request.data.get('token')

        if not token_str:
            return Response({
                'valid': False,
                'error': _('Token is required.')
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify and decode access token
            try:
                access_token = AccessToken(token_str)
            except TokenError as e:
                logger.warning(
                    f"Invalid access token verification attempt: {e}")
                return Response({
                    'valid': False,
                    'error': _('Token is invalid or expired')
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get user from token
            user_id = access_token.get('user_id')
            if not user_id:
                return Response({
                    'valid': False,
                    'error': _('Token does not contain user information')
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify user still exists and is active
            try:
                user = User.objects.get(id=user_id)
                if not user.is_active:
                    logger.warning(
                        f"Token verification for disabled user: {user.email}")
                    return Response({
                        'valid': False,
                        'error': _('User account is disabled')
                    }, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                logger.warning(
                    f"Token verification for non-existent user ID: {user_id}")
                return Response({
                    'valid': False,
                    'error': _('User no longer exists')
                }, status=status.HTTP_400_BAD_REQUEST)

            # Log successful token verification
            AuditLog.objects.create(
                user=user,
                event_type='token_verified',
                description='Access token verified successfully',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Test Client'),
                success=True,
                risk_level='low',
                metadata={
                    'token_type': 'access',
                    'expires_at': str(access_token.get('exp'))
                }
            )

            logger.info(
                f"Token verification successful for user: {user.email}")

            # Return token validity information
            return Response({
                'valid': True,
                'user_id': user.id,
                'email': user.email,
                'expires_at': timezone.datetime.fromtimestamp(
                    access_token.get('exp'), tz=timezone.get_current_timezone()
                ).isoformat(),
                'token_type': 'access',
                'message': _('Token is valid')
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Token verification failed: {e}", exc_info=True)
            return Response({
                'valid': False,
                'error': _('Token verification failed')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
