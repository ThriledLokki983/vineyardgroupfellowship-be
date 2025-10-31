"""
Authentication Services for Vineyard Group Fellowship Platform.

This module provides business logic for authentication operations including
token exchange, user sessions, and secure authentication flows.
"""

import secrets
import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserSession, AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)


class ExchangeTokenService:
    """
    Service for managing temporary exchange tokens for secure authentication flows.

    Exchange tokens are short-lived, single-use tokens that can be exchanged
    for JWT access/refresh tokens. This pattern is more secure than passing
    JWT tokens directly in URLs.
    """

    # Cache key prefix for exchange tokens
    CACHE_PREFIX = "exchange_token"

    # Exchange token expiry (short-lived for security)
    TOKEN_EXPIRY_SECONDS = 60  # 1 minute

    @classmethod
    def generate_exchange_token(cls, user: User, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a one-time exchange token for a user.

        Args:
            user: The user to generate the token for
            context: Optional context data to store with the token

        Returns:
            The exchange token string
        """
        # Generate cryptographically secure random token
        exchange_token = secrets.token_urlsafe(32)

        # Prepare token data
        token_data = {
            'user_id': user.id,
            'created_at': timezone.now().isoformat(),
            'context': context or {},
            'used': False
        }

        # Store in cache with expiry
        cache_key = f"{cls.CACHE_PREFIX}:{exchange_token}"
        cache.set(cache_key, token_data, timeout=cls.TOKEN_EXPIRY_SECONDS)

        logger.info(f"Generated exchange token for user {user.id}")

        return exchange_token

    @classmethod
    def exchange_for_jwt_tokens(
        cls,
        exchange_token: str,
        request_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Exchange a one-time token for JWT access/refresh tokens.

        Args:
            exchange_token: The exchange token to validate and consume
            request_meta: Request metadata for session creation

        Returns:
            Dict containing access_token, refresh_token, and user info

        Raises:
            ValueError: If token is invalid, expired, or already used
        """
        cache_key = f"{cls.CACHE_PREFIX}:{exchange_token}"

        # Retrieve token data from cache
        token_data = cache.get(cache_key)

        if not token_data:
            raise ValueError("Invalid or expired exchange token")

        if token_data.get('used', False):
            raise ValueError("Exchange token has already been used")

        # Mark token as used (prevents reuse)
        token_data['used'] = True
        cache.set(cache_key, token_data, timeout=cls.TOKEN_EXPIRY_SECONDS)

        # Get user
        try:
            user = User.objects.get(id=token_data['user_id'])
        except User.DoesNotExist:
            raise ValueError("User not found for exchange token")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Create user session (same as login flow)
        session = cls._create_user_session(user, refresh, request_meta)

        # Log successful token exchange
        cls._log_token_exchange(user, request_meta, success=True)

        # Delete the exchange token from cache (single use)
        cache.delete(cache_key)

        return {
            'access_token': str(access_token),
            'refresh_token': str(refresh),
            'user_id': user.id,
            'email': user.email,
            'session_id': str(session.id),
            # 15 minutes default
            'expires_in': access_token.get('exp') - timezone.now().timestamp() if access_token.get('exp') else 900,
            'context': token_data.get('context', {})
        }

    @classmethod
    def _create_user_session(
        cls,
        user: User,
        refresh_token: RefreshToken,
        request_meta: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """Create a user session for the token exchange login."""
        request_meta = request_meta or {}

        # Generate a shorter session key that fits in 40 characters
        # Format: {jti}_{short_timestamp}
        import hashlib
        timestamp = str(int(timezone.now().timestamp()))
        session_key = f"{refresh_token['jti'][:24]}_{timestamp[:8]}"

        session = UserSession.objects.create(
            user=user,
            device_fingerprint=request_meta.get('device_fingerprint', ''),
            device_name=request_meta.get(
                'device_name', 'Email Verification Login'),
            user_agent=request_meta.get('user_agent', ''),
            ip_address=request_meta.get('ip_address', ''),
            refresh_token_jti=str(refresh_token['jti']),
            session_key=session_key,
            expires_at=timezone.now() + timedelta(days=14)  # Match refresh token expiry
        )

        return session

    @classmethod
    def _log_token_exchange(
        cls,
        user: User,
        request_meta: Optional[Dict[str, Any]] = None,
        success: bool = True
    ):
        """Log the token exchange attempt for audit purposes."""
        request_meta = request_meta or {}

        AuditLog.objects.create(
            user=user,
            event_type='security_event',
            description=f'Exchange token {"used" if success else "failed"} for auto-login',
            ip_address=request_meta.get('ip_address', ''),
            user_agent=request_meta.get('user_agent', ''),
            metadata={
                'auto_login': True,
                'method': 'email_verification_exchange'
            },
            success=success,
            risk_level='low' if success else 'medium'
        )


class AuthenticationService:
    """
    Service for core authentication operations.

    Provides high-level authentication methods that can be used
    across different views and flows.
    """

    @staticmethod
    def authenticate_user(validated_data: Dict[str, Any], request) -> Dict[str, Any]:
        """
        Authenticate user and create session with JWT tokens.

        Args:
            validated_data: Dictionary containing user and session data from serializer
            request: HTTP request object

        Returns:
            Dict containing access_token, refresh_token, user, session, and metadata
        """
        user = validated_data['user']
        device_name = validated_data.get('device_name', 'Unknown Device')
        device_fingerprint = validated_data.get('device_fingerprint', '')
        remember_me = validated_data.get('remember_me', False)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Extract request metadata
        request_meta = {
            'device_fingerprint': device_fingerprint or AuthenticationService.get_device_fingerprint(request),
            'device_name': device_name,
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
            'ip_address': request.META.get('REMOTE_ADDR', ''),
        }

        # Create user session
        from .models import UserSession
        session = UserSession.objects.create(
            user=user,
            device_fingerprint=request_meta['device_fingerprint'],
            device_name=request_meta['device_name'],
            user_agent=request_meta['user_agent'],
            ip_address=request_meta['ip_address'],
            refresh_token_jti=str(refresh['jti']),
            session_key=f"{refresh['jti'][:24]}_{str(int(timezone.now().timestamp()))[:8]}",
            expires_at=timezone.now() + timedelta(days=14 if remember_me else 7)
        )

        # Log successful login
        AuditLog.objects.create(
            user=user,
            event_type='login_success',
            description='User logged in successfully',
            ip_address=request_meta['ip_address'],
            user_agent=request_meta['user_agent'],
            session_id=str(session.id),
            success=True,
            risk_level='low',
            metadata={
                'device_name': device_name,
                'remember_me': remember_me
            }
        )

        return {
            'access_token': str(access_token),
            'refresh_token': str(refresh),
            'user': user,
            'session': session,
            'expires_in': 900,  # 15 minutes
            'token_type': 'Bearer'
        }

    @staticmethod
    def get_device_fingerprint(request) -> str:
        """
        Generate a device fingerprint from request headers.

        This is a simple implementation - in production you might want
        to use more sophisticated fingerprinting.
        """
        user_agent = request.META.get('HTTP_USER_AGENT', 'Test Client')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')

        # Create a simple hash of key headers
        import hashlib
        fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    @staticmethod
    def extract_request_metadata(request) -> Dict[str, Any]:
        """Extract metadata from request for session creation and logging."""
        return {
            'device_fingerprint': AuthenticationService.get_device_fingerprint(request),
            'device_name': 'Email Verification Login',
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Test Client'),
            'ip_address': request.META.get('REMOTE_ADDR', ''),
        }


class PasswordService:
    """
    Service class for password-related operations.
    """

    @staticmethod
    def validate_password_change(user, old_password, new_password):
        """
        Validate password change request.

        Args:
            user: User instance
            old_password: Current password
            new_password: New password

        Returns:
            dict: Validation result
        """
        # Check if old password is correct
        if not user.check_password(old_password):
            return {
                'valid': False,
                'error': 'Current password is incorrect'
            }

        # Validate new password strength
        from .utils.auth import validate_password_strength
        strength_result = validate_password_strength(new_password, user)

        if not strength_result.get('valid', False):
            return {
                'valid': False,
                'error': 'New password does not meet security requirements',
                'details': strength_result
            }

        return {
            'valid': True,
            'message': 'Password validation successful'
        }

    @staticmethod
    def change_password(user, new_password):
        """
        Change user password and log the action.

        Args:
            user: User instance
            new_password: New password

        Returns:
            bool: Success status
        """
        try:
            # Set the new password
            user.set_password(new_password)
            user.save()

            # Log the password change
            AuditLog.objects.create(
                user=user,
                event_type='password_changed',
                description='User changed their password',
                success=True,
                risk_level='medium'
            )

            return True
        except Exception as e:
            logger.error(f"Failed to change password for user {user.id}: {e}")
            return False


class SessionService:
    """
    Service class for session management operations.
    """

    @staticmethod
    def get_user_sessions(user):
        """
        Get all active sessions for a user.

        Args:
            user: User instance

        Returns:
            QuerySet of UserSession objects
        """
        return UserSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-last_activity')

    @staticmethod
    def terminate_session(user, session_id):
        """
        Terminate a specific user session.

        Args:
            user: User instance
            session_id: ID of session to terminate

        Returns:
            bool: Success status
        """
        try:
            session = UserSession.objects.get(
                id=session_id,
                user=user,
                is_active=True
            )
            session.is_active = False
            session.save()

            # Log the session termination
            AuditLog.objects.create(
                user=user,
                event_type='session_terminated',
                description=f'Session {session_id} terminated',
                success=True,
                risk_level='low'
            )

            return True
        except UserSession.DoesNotExist:
            logger.warning(
                f"Session {session_id} not found for user {user.id}")
            return False
        except Exception as e:
            logger.error(f"Failed to terminate session {session_id}: {e}")
            return False

    @staticmethod
    def terminate_all_sessions(user, exclude_current=True, current_session_id=None):
        """
        Terminate all user sessions.

        Args:
            user: User instance
            exclude_current: Whether to exclude the current session
            current_session_id: ID of current session to exclude

        Returns:
            int: Number of sessions terminated
        """
        try:
            sessions = UserSession.objects.filter(
                user=user,
                is_active=True
            )

            if exclude_current and current_session_id:
                sessions = sessions.exclude(id=current_session_id)

            terminated_count = sessions.update(is_active=False)

            # Log the bulk session termination
            AuditLog.objects.create(
                user=user,
                event_type='all_sessions_terminated',
                description=f'Terminated {terminated_count} sessions',
                success=True,
                risk_level='medium'
            )

            return terminated_count
        except Exception as e:
            logger.error(
                f"Failed to terminate all sessions for user {user.id}: {e}")
            return 0

    @staticmethod
    def create_session(user, request):
        """
        Create a new user session.

        Args:
            user: User instance
            request: Django request object

        Returns:
            UserSession instance or None
        """
        try:
            from .utils.sessions import get_device_fingerprint

            session = UserSession.objects.create(
                user=user,
                device_name=request.META.get(
                    'HTTP_USER_AGENT', 'Unknown Device')[:100],
                device_fingerprint=get_device_fingerprint(request),
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                is_active=True
            )

            return session
        except Exception as e:
            logger.error(f"Failed to create session for user {user.id}: {e}")
            return None
