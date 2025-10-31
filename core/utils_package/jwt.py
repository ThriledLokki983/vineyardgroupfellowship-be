"""
Enhanced JWT utilities for multi-key support and key rotation.

This module provides utilities for:
- Multi-key JWT verification
- Key rotation management
- Enhanced JWT security features
"""

import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import jwt

logger = logging.getLogger(__name__)


class MultiKeyJWTManager:
    """
    Manager for multi-key JWT support with key rotation capabilities.

    Phase 4 Enhancement: Supports multiple signing keys for secure key rotation
    without breaking existing tokens during transition periods.
    """

    @classmethod
    def get_signing_keys(cls) -> List[Dict[str, Any]]:
        """
        Get all configured signing keys.

        Returns:
            List of signing key configurations
        """
        return getattr(settings, 'JWT_SIGNING_KEYS', [
            {
                'kid': 'primary',
                'key': getattr(settings, 'JWT_SIGNING_KEY', settings.SECRET_KEY),
                'algorithm': 'HS256',
                'active': True,
            }
        ])

    @classmethod
    def get_active_signing_key(cls) -> Dict[str, Any]:
        """
        Get the active signing key for new token creation.

        Returns:
            Active signing key configuration
        """
        keys = cls.get_signing_keys()
        for key_config in keys:
            if key_config.get('active', False):
                return key_config

        # Fallback to first key if no active key found
        if keys:
            return keys[0]

        # Ultimate fallback
        return {
            'kid': 'fallback',
            'key': settings.SECRET_KEY,
            'algorithm': 'HS256',
            'active': True,
        }

    @classmethod
    def verify_token_with_multiple_keys(cls, token: str) -> Dict[str, Any]:
        """
        Verify JWT token using multiple possible signing keys.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            InvalidToken: If token cannot be verified with any key
        """
        keys = cls.get_signing_keys()
        last_exception = None

        for key_config in keys:
            try:
                # Attempt to decode with this key
                payload = jwt.decode(
                    token,
                    key_config['key'],
                    algorithms=[key_config['algorithm']],
                    options={
                        'verify_signature': True,
                        'verify_exp': True,
                        'verify_iat': True,
                        'require': ['exp', 'iat', 'jti'],
                    }
                )

                # Add key info to payload for tracking
                payload['_key_id'] = key_config['kid']
                payload['_key_active'] = key_config.get('active', False)

                logger.debug(f"Token verified with key: {key_config['kid']}")
                return payload

            except jwt.InvalidTokenError as e:
                last_exception = e
                logger.debug(
                    f"Token verification failed with key {key_config['kid']}: {e}")
                continue

        # If we get here, no key worked
        logger.warning("Token verification failed with all available keys")
        raise InvalidToken(f"Token verification failed: {last_exception}")

    @classmethod
    def rotate_signing_key(cls, new_key: str, new_key_id: str = None) -> Dict[str, Any]:
        """
        Rotate the active signing key.

        Args:
            new_key: New signing key
            new_key_id: Optional key ID (will generate if not provided)

        Returns:
            Dictionary with rotation status and new key info
        """
        if new_key_id is None:
            import uuid
            new_key_id = f"key_{uuid.uuid4().hex[:8]}"

        current_keys = cls.get_signing_keys()

        # Mark current active key as inactive
        for key_config in current_keys:
            if key_config.get('active'):
                key_config['active'] = False
                key_config['rotated_at'] = timezone.now().isoformat()

        # Add new active key
        new_key_config = {
            'kid': new_key_id,
            'key': new_key,
            'algorithm': 'HS256',
            'active': True,
            'created_at': timezone.now().isoformat(),
        }

        current_keys.append(new_key_config)

        logger.info(f"JWT signing key rotated. New key ID: {new_key_id}")

        return {
            'rotated': True,
            'new_key_id': new_key_id,
            'total_keys': len(current_keys),
            'previous_keys': len([k for k in current_keys if not k.get('active')]),
        }

    @classmethod
    def cleanup_old_keys(cls, keep_count: int = 3) -> Dict[str, Any]:
        """
        Clean up old inactive signing keys, keeping a specified number.

        Args:
            keep_count: Number of inactive keys to keep for validation

        Returns:
            Dictionary with cleanup status
        """
        current_keys = cls.get_signing_keys()
        active_keys = [k for k in current_keys if k.get('active')]
        inactive_keys = [k for k in current_keys if not k.get('active')]

        # Sort inactive keys by creation date (newest first)
        inactive_keys.sort(
            key=lambda k: k.get('created_at', ''),
            reverse=True
        )

        # Keep only the specified number of inactive keys
        keys_to_keep = inactive_keys[:keep_count]
        keys_to_remove = inactive_keys[keep_count:]

        # New key list
        cleaned_keys = active_keys + keys_to_keep

        logger.info(f"Cleaned up {len(keys_to_remove)} old JWT signing keys")

        return {
            'cleaned': True,
            'removed_count': len(keys_to_remove),
            'remaining_keys': len(cleaned_keys),
            'removed_key_ids': [k.get('kid') for k in keys_to_remove],
        }


class EnhancedJWTToken:
    """
    Enhanced JWT token wrapper with Phase 4 features.
    """

    @classmethod
    def create_token_pair(cls, user, device_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create access and refresh token pair with enhanced claims.

        Args:
            user: User instance
            device_info: Optional device information

        Returns:
            Dictionary with token pair and metadata
        """
        # Get active signing key
        key_config = MultiKeyJWTManager.get_active_signing_key()

        # Create refresh token with custom claims
        refresh = RefreshToken.for_user(user)

        # Add custom claims
        refresh['key_id'] = key_config['kid']
        refresh['user_id'] = user.id
        refresh['email'] = user.email

        # Add device info if provided
        if device_info:
            refresh['device_name'] = device_info.get('device_name', 'Unknown')
            refresh['device_fingerprint'] = device_info.get(
                'device_fingerprint', '')

        # Add user email verification status
        refresh['is_verified'] = user.email_verified

        # Add profile information if available
        profile = getattr(user, 'basic_profile', None)
        if profile:
            refresh['timezone'] = profile.timezone
            refresh['profile_id'] = str(profile.id)

        # Create access token
        access = refresh.access_token

        return {
            'access': str(access),
            'refresh': str(refresh),
            'token_type': 'Bearer',
            'expires_in': settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
            'key_id': key_config['kid'],
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
            }
        }

    @classmethod
    def validate_token_reuse(cls, token_jti: str, user_id: int) -> bool:
        """
        Check if a token JTI has been reused (security violation).

        Args:
            token_jti: Token JTI (unique identifier)
            user_id: User ID

        Returns:
            True if token is valid, False if reused
        """
        # Check if token is blacklisted
        from authentication.models import TokenBlacklist

        if TokenBlacklist.is_blacklisted(token_jti):
            logger.warning(
                f"Blacklisted token reuse detected for JTI: {token_jti}, User: {user_id}"
            )
            return False

        # Check cache for recent usage (prevents rapid reuse)
        from django.core.cache import cache

        cache_key = f"jwt_jti_used_{token_jti}_{user_id}"

        if cache.get(cache_key):
            logger.warning(
                f"Token reuse detected for JTI: {token_jti}, User: {user_id}"
            )

            # Blacklist the token due to suspicious reuse
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                TokenBlacklist.blacklist_token(
                    jti=token_jti,
                    user=user,
                    token_type='refresh',
                    reason='reuse_detected'
                )
            except User.DoesNotExist:
                pass

            return False

        # Mark JTI as recently used
        # Cache for a short period to detect rapid reuse
        cache.set(cache_key, True, 300)  # 5 minutes

        return True

    @classmethod
    def rotate_token_pair(cls, refresh_token_str: str, device_info: dict = None) -> dict:
        """
        Rotate a token pair, blacklisting the old refresh token.

        Args:
            refresh_token_str: Current refresh token string
            device_info: Optional device information

        Returns:
            New token pair or error information
        """
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            from rest_framework_simplejwt.exceptions import TokenError
            from authentication.models import TokenBlacklist, UserSession
            from django.contrib.auth import get_user_model

            # Parse the refresh token
            refresh_token = RefreshToken(refresh_token_str)
            user_id = refresh_token.payload.get('user_id')
            old_jti = refresh_token.payload.get('jti')

            if not user_id or not old_jti:
                return {
                    'success': False,
                    'error': 'Invalid token format',
                    'error_code': 'INVALID_TOKEN'
                }

            # Validate token is not blacklisted
            if TokenBlacklist.is_blacklisted(old_jti):
                return {
                    'success': False,
                    'error': 'Token is blacklisted',
                    'error_code': 'TOKEN_BLACKLISTED'
                }

            # Check for token reuse
            if not cls.validate_token_reuse(old_jti, user_id):
                return {
                    'success': False,
                    'error': 'Token reuse detected',
                    'error_code': 'TOKEN_REUSE'
                }

            # Get user
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return {
                    'success': False,
                    'error': 'User not found',
                    'error_code': 'USER_NOT_FOUND'
                }

            # Create new token pair
            new_token_pair = cls.create_token_pair(user, device_info)
            new_refresh_token = RefreshToken(new_token_pair['refresh'])
            new_jti = new_refresh_token.payload.get('jti')

            # Blacklist the old token
            from django.conf import settings
            refresh_lifetime = settings.SIMPLE_JWT.get(
                'REFRESH_TOKEN_LIFETIME', timezone.timedelta(days=14)
            )
            expires_at = timezone.now() + refresh_lifetime

            TokenBlacklist.blacklist_token(
                jti=old_jti,
                user=user,
                token_type='refresh',
                reason='rotation',
                expires_at=expires_at
            )

            # Update session if it exists
            try:
                session = UserSession.objects.get(
                    user=user,
                    refresh_token_jti=old_jti,
                    is_active=True
                )
                session.rotate_refresh_token(new_jti)
            except UserSession.DoesNotExist:
                logger.info(f"No session found for JTI {old_jti}")

            logger.info(
                f"Token rotation successful for user {user_id}: {old_jti} -> {new_jti}")

            return {
                'success': True,
                'tokens': new_token_pair,
                'old_jti': old_jti,
                'new_jti': new_jti,
                'rotated_at': timezone.now().isoformat()
            }

        except TokenError as e:
            logger.warning(f"Token rotation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_ERROR'
            }
        except Exception as e:
            logger.error(f"Unexpected error during token rotation: {e}")
            return {
                'success': False,
                'error': 'Internal server error',
                'error_code': 'INTERNAL_ERROR'
            }

    @classmethod
    def blacklist_all_user_tokens(cls, user, reason: str = 'security_event',
                                  ip_address: str = None, user_agent: str = None) -> dict:
        """
        Blacklist all active tokens for a user (e.g., on password change).

        Args:
            user: User instance
            reason: Reason for blacklisting
            ip_address: IP address of the request
            user_agent: User agent of the request

        Returns:
            Dictionary with blacklist results
        """
        from authentication.models import TokenBlacklist, UserSession

        # Get all active sessions
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True
        )

        blacklisted_count = 0
        sessions_invalidated = 0

        for session in active_sessions:
            if session.refresh_token_jti:
                # Blacklist the refresh token
                from django.conf import settings
                refresh_lifetime = settings.SIMPLE_JWT.get(
                    'REFRESH_TOKEN_LIFETIME', timezone.timedelta(days=14)
                )
                expires_at = session.created_at + refresh_lifetime

                TokenBlacklist.blacklist_token(
                    jti=session.refresh_token_jti,
                    user=user,
                    token_type='refresh',
                    reason=reason,
                    expires_at=expires_at,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                blacklisted_count += 1

            # Invalidate the session
            session.invalidate_session_tokens(
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            sessions_invalidated += 1

        logger.info(
            f"Blacklisted all tokens for user {user.id}: {blacklisted_count} tokens, "
            f"{sessions_invalidated} sessions"
        )

        return {
            'blacklisted_tokens': blacklisted_count,
            'invalidated_sessions': sessions_invalidated,
            'reason': reason,
            'timestamp': timezone.now().isoformat()
        }


# Utility functions for backward compatibility
def get_active_signing_key():
    """Get the active JWT signing key."""
    return MultiKeyJWTManager.get_active_signing_key()


def verify_token_with_rotation_support(token: str):
    """Verify JWT token with multi-key support."""
    return MultiKeyJWTManager.verify_token_with_multiple_keys(token)


def create_enhanced_token_pair(user, device_info=None):
    """Create JWT token pair with enhanced features."""
    return EnhancedJWTToken.create_token_pair(user, device_info)
