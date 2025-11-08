"""
Authentication view modules for user registration, login, and logout.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from django.utils.translation import gettext_lazy as _
import structlog

from ..serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    AuthResponseSerializer
)
from ..services import AuthenticationService
from ..utils.cookies import (
    set_refresh_token_cookie,
    clear_refresh_token_cookie,
    get_refresh_token_from_cookie,
    get_refresh_token_from_request
)
from ..utils.api_docs import authentication_schema
from ..models import AuditLog, UserSession

logger = structlog.get_logger(__name__)
User = get_user_model()


@authentication_schema(
    operation_id='register_user',
    summary='Register new user account',
    description='''
    Register a new user account with email verification.

    The account will be inactive until email verification is completed.
    Rate limiting: 5 registrations per hour per IP address.
    ''',
    request=UserRegistrationSerializer,
    responses={
        201: AuthResponseSerializer,
        400: 'Validation errors',
        429: 'Rate limit exceeded'
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def register_view(request):
    """
    Register a new user account.

    This endpoint creates a new user account and sends an email verification.
    The account will be inactive until email is verified.

    **Rate Limiting**: 5 registrations per hour per IP

    **Request Body**:
    ```json
    {
        "email": "user@example.com",
        "username": "johndoe",
        "first_name": "John",
        "last_name": "Doe",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
        "terms_accepted": true,
        "privacy_policy_accepted": true
    }
    ```

    **Response**:
    - `201 Created`: User registered successfully
    - `400 Bad Request`: Validation errors
    - `429 Too Many Requests`: Rate limit exceeded
    """
    serializer = UserRegistrationSerializer(data=request.data)

    if not serializer.is_valid():
        # Log registration attempt with errors
        AuditLog.log_event(
            event_type='registration_failure',
            description=f"Registration failed with validation errors",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            risk_level='low',
            metadata={
                'errors': serializer.errors,
                'email': request.data.get('email', 'unknown')
            }
        )

        return Response(
            {
                'error': 'Validation failed',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # Create user
            user = serializer.save()

            # Store password for async breach check (using request data)
            # We pass the plain password to async task for breach checking
            password = request.data.get('password', '')

            # Send verification email using the utility function (async via Celery)
            from ..utils.auth import send_verification_email
            send_verification_email(user, request)

            # Check password breach asynchronously (doesn't block registration)
            # Gracefully handle Celery unavailability
            if password:
                try:
                    from ..tasks import check_password_breach_async
                    check_password_breach_async.delay(str(user.id), password)
                    logger.info("Password breach check queued", user_id=str(user.id))
                except Exception as e:
                    # Log but don't fail registration if Celery is unavailable
                    logger.warning(
                        "Failed to queue password breach check (Celery unavailable)",
                        user_id=str(user.id),
                        error=str(e)
                    )

            logger.info(
                "User registration successful",
                user_id=str(user.id),
                email=user.email,
                username=user.username
            )

            return Response(
                {
                    'message': 'Registration successful. Please check your email to verify your account.',
                    'user_id': str(user.id),
                    'email': user.email
                },
                status=status.HTTP_201_CREATED
            )

    except Exception as e:
        logger.error(
            "Registration failed with exception",
            email=request.data.get('email', 'unknown'),
            error=str(e)
        )

        # Log the error event
        AuditLog.log_event(
            event_type='registration_failure',
            description=f"Registration failed with exception: {str(e)}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            risk_level='medium',
            metadata={
                'error': str(e),
                'email': request.data.get('email', 'unknown')
            }
        )

        return Response(
            {
                'error': 'Registration failed. Please try again later.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@authentication_schema(
    operation_id='login_user',
    summary='User login',
    description='''
    Authenticate user with email/username and password.

    Returns JWT access and refresh tokens. The refresh token is set as
    an httpOnly cookie for security.
    Rate limiting: 25 login attempts per hour per IP address.
    ''',
    request=UserLoginSerializer,
    responses={
        200: AuthResponseSerializer,
        400: 'Invalid credentials or validation errors',
        423: 'Account temporarily locked',
        429: 'Rate limit exceeded'
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def login_view(request):
    """
    Authenticate user and return tokens.

    This endpoint authenticates a user and returns JWT access and refresh tokens.
    The refresh token is set as an httpOnly cookie for security.

    **Rate Limiting**: 25 login attempts per hour per IP

    **Request Body**:
    ```json
    {
        "email_or_username": "user@example.com",
        "password": "SecurePassword123!",
        "remember_me": false
    }
    ```

    **Response**:
    - `200 OK`: Login successful with tokens
    - `400 Bad Request`: Invalid credentials or validation errors
    - `423 Locked`: Account temporarily locked
    - `429 Too Many Requests`: Rate limit exceeded
    """
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        # Log failed login attempt
        AuditLog.log_event(
            event_type='login_failure',
            description="Login failed with validation errors",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            risk_level='low',
            metadata={
                'errors': serializer.errors,
                'email_or_username': request.data.get('email_or_username', 'unknown')
            }
        )

        return Response(
            {
                'error': 'Invalid credentials',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Authenticate user using service
        auth_data = AuthenticationService.authenticate_user(
            validated_data=serializer.validated_data,
            request=request
        )

        # Create response with access token
        response_data = {
            'access_token': auth_data['access_token'],
            'expires_in': auth_data['expires_in'],
            'token_type': auth_data['token_type'],
            'user': {
                'id': str(auth_data['user'].id),
                'email': auth_data['user'].email,
                'username': auth_data['user'].username,
                'first_name': auth_data['user'].first_name,
                'last_name': auth_data['user'].last_name,
                'email_verified': auth_data['user'].email_verified
            }
        }

        response = Response(response_data, status=status.HTTP_200_OK)

        # Set refresh token as httpOnly cookie
        remember_me = serializer.validated_data.get('remember_me', False)
        max_age = 14 * 24 * 60 * 60 if remember_me else 7 * \
            24 * 60 * 60  # 14 days or 7 days
        response = set_refresh_token_cookie(
            response,
            auth_data['refresh_token'],
            max_age=max_age
        )

        logger.info(
            "User login successful",
            user_id=str(auth_data['user'].id),
            email=auth_data['user'].email,
            session_id=str(auth_data['session'].id)
        )

        return response

    except Exception as e:
        logger.error(
            "Login failed with exception",
            email_or_username=request.data.get('email_or_username', 'unknown'),
            error=str(e)
        )

        # Log the error event
        AuditLog.log_event(
            event_type='login_failure',
            description=f"Login failed with exception: {str(e)}",
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=False,
            risk_level='medium',
            metadata={
                'error': str(e),
                'email_or_username': request.data.get('email_or_username', 'unknown')
            }
        )

        return Response(
            {
                'error': 'Login failed. Please try again later.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@authentication_schema(
    operation_id='logout_user',
    summary='User logout',
    description='''
    Logout user, blacklist refresh token, and clear cookies.

    This endpoint works with or without a valid access token.
    The refresh token from the httpOnly cookie is used to identify and blacklist the session.
    Even if the access token has expired, logout will succeed as long as the refresh token cookie is present.

    Features:
    - JWT token blacklisting
    - HttpOnly cookie clearing
    - Session deactivation
    - Security logging
    ''',
    responses={
        200: 'Logout successful',
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow logout even with expired tokens
@csrf_exempt
@never_cache
def logout_view(request):
    """
    Logout user and invalidate tokens.

    This endpoint logs out the current user, blacklists their refresh token,
    terminates the session, and clears the refresh token cookie.

    **Authentication**: Not required (works with expired tokens)

    **Response**:
    - `200 OK`: Logout successful (always returns success for UX)
    """
    try:
        user = None

        # Get refresh token from cookie (with body fallback)
        refresh_token_str = get_refresh_token_from_request(request)

        if not refresh_token_str:
            # No refresh token provided - idempotent operation, already logged out
            logger.info(
                "Logout called without refresh token - already logged out")
            response = Response(
                {"message": _("Successfully logged out.")},
                status=status.HTTP_200_OK
            )
            clear_refresh_token_cookie(response)
            return response

        try:
            # Blacklist the refresh token
            refresh_token = RefreshToken(refresh_token_str)
            refresh_token.blacklist()

            # Extract user from token
            user_id = refresh_token.get('user_id')
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    logger.warning(f"User {user_id} not found during logout")
                    pass

            # Find and terminate specific session by JTI
            if user:
                terminated_count = UserSession.objects.filter(
                    user=user,
                    refresh_token_jti=str(refresh_token.get('jti')),
                    is_active=True
                ).update(
                    is_active=False
                )

                logger.info(
                    "Session terminated",
                    user_id=str(user.id),
                    sessions_terminated=terminated_count,
                    jti=str(refresh_token.get('jti'))
                )

            logger.info(
                "Refresh token blacklisted",
                user_email=user.email if user else 'unknown',
                user_id=str(user.id) if user else 'unknown'
            )

        except (TokenError, AttributeError, InvalidToken) as e:
            logger.warning(
                "Could not blacklist token during logout",
                error=str(e),
                error_type=type(e).__name__
            )
            # Continue with logout even if blacklisting fails

        # Log logout if we have a user
        if user:
            AuditLog.objects.create(
                user=user,
                event_type='logout_success',
                description='User logged out successfully',
                ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown'),
                success=True,
                risk_level='low',
                metadata={'logout_method': 'manual'}
            )
            logger.info(
                "User logged out successfully",
                user_id=str(user.id),
                email=user.email
            )
        else:
            logger.info("Logout completed without valid user context")

        # Create response
        response = Response({
            'message': _('Successfully logged out.')
        }, status=status.HTTP_200_OK)

        # Clear refresh token cookie
        response = clear_refresh_token_cookie(response)

        return response

    except Exception as e:
        logger.error(
            "Logout failed with exception",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        # Return success even on errors (UX: don't block logout)
        response = Response({
            'message': _('Logout completed with warnings.')
        }, status=status.HTTP_200_OK)
        response = clear_refresh_token_cookie(response)
        return response


@authentication_schema(
    operation_id='refresh_token',
    summary='Refresh access token',
    description='''
    Refresh JWT access token using refresh token from httpOnly cookie.

    The refresh token is rotated for security. Rate limiting: 60 refresh
    attempts per hour per user.
    ''',
    responses={
        200: AuthResponseSerializer,
        401: 'Invalid or expired refresh token',
        429: 'Rate limit exceeded'
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def refresh_token_view(request):
    """
    Refresh JWT access token.

    This endpoint refreshes the JWT access token using the refresh token
    stored in the httpOnly cookie. The refresh token is rotated for security.

    **Rate Limiting**: 60 refresh attempts per hour per user

    **Response**:
    - `200 OK`: New access token provided
    - `401 Unauthorized`: Invalid or expired refresh token
    - `429 Too Many Requests`: Rate limit exceeded
    """
    try:
        # Get refresh token from cookie
        refresh_token_str = get_refresh_token_from_cookie(request)

        if not refresh_token_str:
            return Response(
                {
                    'error': 'Refresh token not found'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate and refresh token
        try:
            refresh_token = RefreshToken(refresh_token_str)
            user_id = refresh_token['user_id']
            user = User.objects.get(id=user_id)

            # Generate new tokens
            new_refresh = RefreshToken.for_user(user)
            access_token = str(new_refresh.access_token)
            new_refresh_str = str(new_refresh)

            # Blacklist old refresh token
            refresh_token.blacklist()

            response_data = {
                'access_token': access_token,
                'expires_in': int(new_refresh.access_token.lifetime.total_seconds()),
                'token_type': 'Bearer'
            }

            response = Response(response_data, status=status.HTTP_200_OK)

            # Set new refresh token cookie
            response = set_refresh_token_cookie(response, new_refresh_str)

            # Log token refresh
            AuditLog.log_event(
                event_type='token_refresh',
                user=user,
                description="JWT token refreshed successfully",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
                risk_level='low'
            )

            logger.info(
                "Token refresh successful",
                user_id=str(user.id),
                email=user.email
            )

            return response

        except Exception as token_error:
            logger.warning(
                "Token refresh failed",
                error=str(token_error)
            )

            response = Response(
                {
                    'error': 'Invalid refresh token'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

            # Clear invalid refresh token cookie
            response = clear_refresh_token_cookie(response)

            return response

    except Exception as e:
        logger.error(
            "Token refresh failed with exception",
            error=str(e)
        )

        return Response(
            {
                'error': 'Token refresh failed. Please log in again.'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Get CSRF token for SPA authentication.

    This endpoint provides CSRF tokens for single-page applications
    to use when making authenticated requests.
    """
    token = get_token(request)
    return JsonResponse({
        'csrfToken': token,
        'detail': 'CSRF token generated successfully'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_token_api(request):
    """
    DRF-compatible CSRF token endpoint.
    """
    token = get_token(request)
    return Response({
        'csrfToken': token,
        'detail': 'CSRF token generated successfully'
    })
