"""
Authentication serializers for Vineyard Group Fellowship platform.

This module contains DRF serializers for core authentication functionality:
- User registration and login
- Password management (change/reset)
- Email verification
- JWT token management
- Session management
- Audit logging

Phase 2: Clean architecture - only authentication concerns, no cross-app imports.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field

from .models import UserSession, AuditLog, TokenBlacklist
from profiles.models import UserProfileBasic as UserProfile
from .utils.auth import (
    validate_password_strength,
    send_password_reset_email,
    send_verification_email,
    verify_email_token,
    check_password_breach,
    password_reset_token
)

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Enhanced user registration with user purpose system.

    Creates User and UserProfile records, sends verification email,
    and handles user purpose selection for personalized onboarding.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=128,
        help_text="Password must be at least 8 characters long"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,  # Make optional since we also accept confirmPassword
        help_text="Must match password field"
    )

    # Handle frontend field name mismatch (confirmPassword -> password_confirm)
    confirmPassword = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Alternative field name for password confirmation"
    )

    # Privacy policy acceptance (required for GDPR compliance)
    privacy_policy_accepted = serializers.BooleanField(
        required=True,
        help_text="User must accept privacy policy"
    )
    terms_of_service_accepted = serializers.BooleanField(
        required=True,
        help_text="User must accept terms of service"
    )

    # Optional profile fields
    display_name = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Optional display name"
    )

    # Handle frontend fields (firstName, lastName) - currently not used but accepted
    firstName = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="First name (currently not stored)"
    )
    lastName = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Last name (currently not stored)"
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm', 'confirmPassword',
            'privacy_policy_accepted', 'terms_of_service_accepted',
            'display_name', 'firstName', 'lastName'
        )
        extra_kwargs = {
            'username': {'required': True, 'max_length': 150},
            'email': {'required': True}
        }

    def validate_email(self, value):
        """Enhanced email validation with stricter checks."""
        if not value:
            raise serializers.ValidationError("Email is required")

        # Since EmailField automatically strips whitespace, we need to check
        # the original value from the request data
        request = self.context.get('request')
        if request and hasattr(request, 'data'):
            original_email = request.data.get('email', '')
            # Check original value for leading/trailing spaces
            if isinstance(original_email, str) and (original_email.startswith(' ') or original_email.endswith(' ')):
                raise serializers.ValidationError(
                    "Enter a valid email address")

        # Normalize email (lowercase)
        value = value.lower().strip()

        # Basic email format validation
        if '@' not in value or value.count('@') != 1:
            raise serializers.ValidationError("Enter a valid email address")

        local, domain = value.split('@')
        if not local or not domain:
            raise serializers.ValidationError("Enter a valid email address")

        # Check for spaces
        if ' ' in value:
            raise serializers.ValidationError("Enter a valid email address")

        # Check for consecutive dots
        if '..' in value:
            raise serializers.ValidationError("Enter a valid email address")

        # Domain must have at least one dot (for TLD)
        if '.' not in domain:
            raise serializers.ValidationError("Enter a valid email address")

        # Domain cannot start or end with dot
        if domain.startswith('.') or domain.endswith('.'):
            raise serializers.ValidationError("Enter a valid email address")

        # Check for existing users
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "User with this email already exists")

        return value

    def validate_username(self, value):
        """Validate username."""
        if not value:
            raise serializers.ValidationError("Username is required")

        # Length validation
        if len(value) < 2:
            raise serializers.ValidationError(
                "Username must be at least 2 characters long")
        if len(value) > 150:
            raise serializers.ValidationError(
                "Username must not exceed 150 characters")

        # Format validation
        if ' ' in value:
            raise serializers.ValidationError("Username cannot contain spaces")

        # Check for email format (not allowed as username)
        if '@' in value:
            raise serializers.ValidationError(
                "Username cannot be an email address")

        # Check reserved words
        reserved_words = ['admin', 'root',
                          'administrator', 'moderator', 'support']
        if value.lower() in reserved_words:
            raise serializers.ValidationError("This username is reserved")

        # Check for existing users
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "User with this username already exists")

        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # Handle both password_confirm and confirmPassword field names
        password = attrs.get('password')
        password_confirm = attrs.get(
            'password_confirm') or attrs.get('confirmPassword')

        if not password_confirm:
            raise serializers.ValidationError({
                'password_confirm': "Password confirmation is required"
            })

        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match"
            })

        # Validate password strength
        try:
            validate_password(attrs['password'])
            validate_password_strength(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        # Check for password breaches
        if check_password_breach(attrs['password']):
            raise serializers.ValidationError({
                'password': _("This password has been found in data breaches. Please choose a different password.")
            })

        # Validate privacy policy and terms acceptance
        if not attrs.get('privacy_policy_accepted', False):
            raise serializers.ValidationError({
                'privacy_policy_accepted': "You must accept the privacy policy to register"
            })

        if not attrs.get('terms_of_service_accepted', False):
            raise serializers.ValidationError({
                'terms_of_service_accepted': "You must accept the terms of service to register"
            })

        # Remove confirmPassword from attrs to avoid issues in create()
        attrs.pop('confirmPassword', None)
        attrs.pop('firstName', None)  # Remove unused fields
        attrs.pop('lastName', None)

        return attrs

    def create(self, validated_data):
        """Create user and profile."""
        from django.utils import timezone

        # Extract non-user fields
        password_confirm = validated_data.pop('password_confirm', None)
        privacy_accepted = validated_data.pop('privacy_policy_accepted')
        terms_accepted = validated_data.pop('terms_of_service_accepted')
        display_name = validated_data.pop('display_name', '')

        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False  # Require email verification
        )

        # Create the UserProfile (it's not created automatically)
        from profiles.models import UserProfileBasic
        profile = UserProfileBasic.objects.create(user=user)

        # Update the profile with display_name if provided
        if display_name:
            profile.display_name = display_name
            profile.save()

        # Note: Verification email is sent from the view to include request context
        return user


class LoginSerializer(serializers.Serializer):
    """
    User login with audit logging.

    Supports login with username or email.
    """
    email_or_username = serializers.CharField(
        help_text="Username or email address"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    device_name = serializers.CharField(
        required=False,
        default="Unknown Device",
        help_text="Device name for session tracking"
    )
    device_fingerprint = serializers.CharField(
        required=False,
        default="",
        help_text="Device fingerprint for security"
    )
    remember_me = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether to remember this login"
    )

    def validate(self, attrs):
        """Authenticate user and create audit log."""
        email_or_username = attrs.get('email_or_username')
        password = attrs.get('password')

        if not email_or_username or not password:
            raise serializers.ValidationError(
                "Both email_or_username and password are required"
            )

        # Try to find user by username or email
        user = None
        try:
            # First try username
            user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
            try:
                # Then try email
                user = User.objects.get(email=email_or_username.lower())
            except User.DoesNotExist:
                pass

        if user and user.check_password(password):
            if not user.is_active:
                raise serializers.ValidationError(
                    "Account is not verified. Please check your email."
                )

            attrs['user'] = user
            return attrs
        else:
            # Log failed login attempt
            request = self.context.get('request')
            AuditLog.objects.create(
                user=user if user else None,
                action='login_failed',
                ip_address=request.META.get(
                    'REMOTE_ADDR', '127.0.0.1') if request else '127.0.0.1',
                user_agent=request.META.get(
                    'HTTP_USER_AGENT', 'Test Client') if request else 'Test Client',
                details={'login_attempt': email_or_username}
            )

            # Record failed login attempt for existing users
            if user and hasattr(user, 'basic_profile'):
                user.basic_profile.record_failed_login()

            raise serializers.ValidationError(
                "Invalid credentials provided."
            )


class PasswordChangeSerializer(serializers.Serializer):
    """Change password for authenticated users."""
    current_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_current_password(self, value):
        """Verify current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "New passwords do not match"
            })

        # Validate password strength
        try:
            validate_password(attrs['new_password'])
            validate_password_strength(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})

        # Check password history to prevent reuse
        user = self.context['request'].user
        from .models import PasswordHistory

        # Check last 5 passwords to prevent reuse
        recent_passwords = PasswordHistory.objects.filter(
            user=user
        ).order_by('-created_at')[:5]

        for password_entry in recent_passwords:
            if user.check_password(attrs['new_password']):
                # This would mean the new password is the same as current password
                raise serializers.ValidationError({
                    'new_password': "Cannot reuse the current password"
                })
            # Create a temporary user instance to check against historical passwords
            temp_user = User()
            temp_user.password = password_entry.password_hash
            if temp_user.check_password(attrs['new_password']):
                raise serializers.ValidationError({
                    'new_password': "Cannot reuse a previous password. Please choose a different password."
                })

        return attrs

    def save(self):
        """Update user password and store old password in history."""
        user = self.context['request'].user
        from .models import PasswordHistory

        # Store current password in history before changing
        PasswordHistory.objects.create(
            user=user,
            password_hash=user.password
        )

        # Keep only the last 5 passwords in history
        recent_passwords = PasswordHistory.objects.filter(
            user=user
        ).order_by('-created_at')[5:]

        if recent_passwords:
            # Delete older password history entries
            older_ids = [p.id for p in recent_passwords]
            PasswordHistory.objects.filter(id__in=older_ids).delete()

        # Set the new password
        user.set_password(self.validated_data['new_password'])
        user.save()

        # Log password change
        request = self.context['request']
        AuditLog.objects.create(
            user=user,
            action='password_changed',
            ip_address=request.META.get(
                'REMOTE_ADDR', '127.0.0.1') if request else '127.0.0.1',
            user_agent=request.META.get(
                'HTTP_USER_AGENT', 'Test Client') if request else 'Test Client'
        )

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset via email."""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Normalize email and check if user exists."""
        value = value.lower().strip()
        try:
            user = User.objects.get(email=value)
            self.user = user
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            pass
        return value

    def save(self):
        """Send password reset email if user exists."""
        if hasattr(self, 'user'):
            send_password_reset_email(self.user)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm password reset with token."""
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate token and passwords."""
        # Verify password reset token
        user = password_reset_token.decode_uid(attrs['uidb64'])
        if not user:
            raise serializers.ValidationError(
                {'uidb64': "Invalid user ID"})

        if not password_reset_token.check_token(user, attrs['token']):
            raise serializers.ValidationError(
                {'token': "Invalid or expired token"})

        # Check passwords match
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Passwords do not match"
            })

        # Validate password strength
        try:
            validate_password(attrs['new_password'])
            validate_password_strength(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})

        attrs['user'] = user
        return attrs

    def save(self):
        """Reset user password."""
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()

        # Log password reset
        request = self.context.get('request')
        AuditLog.objects.create(
            user=user,
            action='password_reset',
            ip_address=request.META.get(
                'REMOTE_ADDR', '127.0.0.1') if request else '127.0.0.1',
            user_agent=request.META.get(
                'HTTP_USER_AGENT', 'Test Client') if request else 'Test Client'
        )

        return user


class EmailVerificationSerializer(serializers.Serializer):
    """Verify email address with token."""
    uidb64 = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        """Verify email verification token."""
        uidb64 = attrs.get('uidb64')
        token = attrs.get('token')

        result = verify_email_token(uidb64, token)
        if not result.get('is_valid'):
            raise serializers.ValidationError(
                result.get('error', "Invalid or expired verification token"))

        user = result.get('user')
        if not user:
            raise serializers.ValidationError("Invalid verification token")

        if user.is_active:
            raise serializers.ValidationError("Email is already verified")

        self.user = user
        return attrs

    def save(self):
        """Activate user account and verify email."""
        from django.utils import timezone

        user = self.user
        user.is_active = True
        user.email_verified = True
        user.email_verified_at = timezone.now()
        user.save(update_fields=['is_active', 'email_verified', 'email_verified_at'])

        # Log email verification
        request = self.context.get('request')
        user_agent = ''
        if request and hasattr(request, 'META'):
            user_agent = request.META.get('HTTP_USER_AGENT', 'Test Client')
        if not user_agent:
            user_agent = 'Test Client'

        AuditLog.objects.create(
            user=user,
            action='email_verified',
            ip_address=request.META.get(
                'REMOTE_ADDR', '127.0.0.1') if request else '127.0.0.1',
            user_agent=user_agent
        )

        return user


class EmailVerificationResendSerializer(serializers.Serializer):
    """Resend email verification."""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Find user and check if verification is needed."""
        value = value.lower().strip()
        try:
            user = User.objects.get(email=value)
            if user.is_active:
                raise serializers.ValidationError("Email is already verified")
            self.user = user
        except User.DoesNotExist:
            # Don't reveal if email exists or not
            pass
        return value

    def save(self):
        """Send verification email if user exists and needs verification."""
        if hasattr(self, 'user'):
            send_verification_email(self.user)


# Aliases for backwards compatibility
UserLoginSerializer = LoginSerializer


class AuthResponseSerializer(serializers.Serializer):
    """
    Serializer for authentication response with tokens.
    """
    access = serializers.CharField(
        help_text="JWT access token for API authentication"
    )
    refresh = serializers.CharField(
        help_text="JWT refresh token for token renewal",
        required=False
    )
    user = serializers.SerializerMethodField(
        help_text="Basic user information"
    )

    @extend_schema_field(serializers.DictField())
    def get_user(self, obj):
        """Return basic user information."""
        if 'user' in obj:
            user = obj['user']
            return {
                'id': user.id,
                'email': user.email,
                'is_verified': user.is_verified,
                'date_joined': user.date_joined.isoformat(),
            }
        return None


class SuccessMessageSerializer(serializers.Serializer):
    """
    Serializer for success message responses.
    """
    message = serializers.CharField(
        help_text="Success message"
    )
    status = serializers.CharField(
        default="success",
        help_text="Status indicator"
    )


class UserSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for user session information.
    """
    device_info = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    # Explicitly define ip_address field to avoid DRF version compatibility issues
    ip_address = serializers.CharField(max_length=45, read_only=True)

    class Meta:
        model = UserSession
        fields = [
            'id', 'device_name', 'device_fingerprint', 'ip_address',
            'user_agent', 'city', 'country', 'is_active', 'is_verified',
            'created_at', 'last_activity_at', 'expires_at',
            'device_info', 'location', 'is_current', 'is_expired'
        ]
        read_only_fields = [
            'id', 'created_at', 'device_fingerprint', 'ip_address',
            'user_agent', 'city', 'country', 'last_activity_at'
        ]

    @extend_schema_field(serializers.DictField())
    def get_device_info(self, obj):
        """Return parsed device information."""
        if obj.user_agent:
            # Basic user agent parsing - you can enhance this with a proper library
            user_agent = obj.user_agent.lower()
            device_info = {
                'browser': 'Unknown',
                'os': 'Unknown',
                'device_type': 'Unknown'
            }

            # Simple browser detection
            if 'chrome' in user_agent:
                device_info['browser'] = 'Chrome'
            elif 'firefox' in user_agent:
                device_info['browser'] = 'Firefox'
            elif 'safari' in user_agent:
                device_info['browser'] = 'Safari'
            elif 'edge' in user_agent:
                device_info['browser'] = 'Edge'

            # Simple OS detection
            if 'windows' in user_agent:
                device_info['os'] = 'Windows'
            elif 'mac' in user_agent or 'darwin' in user_agent:
                device_info['os'] = 'macOS'
            elif 'linux' in user_agent:
                device_info['os'] = 'Linux'
            elif 'android' in user_agent:
                device_info['os'] = 'Android'
            elif 'ios' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent:
                device_info['os'] = 'iOS'

            # Simple device type detection
            if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
                device_info['device_type'] = 'Mobile'
            elif 'tablet' in user_agent or 'ipad' in user_agent:
                device_info['device_type'] = 'Tablet'
            else:
                device_info['device_type'] = 'Desktop'

            return device_info
        return None

    @extend_schema_field(serializers.DictField())
    def get_location(self, obj):
        """Return location information from IP address."""
        return {
            'city': obj.city or 'Unknown',
            'country': obj.country or 'Unknown',
            'ip': obj.ip_address or 'Unknown'
        }

    @extend_schema_field(serializers.BooleanField())
    def get_is_current(self, obj):
        """Check if this is the current session."""
        request = self.context.get('request')
        if request and hasattr(request, 'session'):
            # Compare session fingerprints or IDs
            return str(obj.id) == request.session.get('session_id')
        return False


class SessionTerminateSerializer(serializers.Serializer):
    """
    Serializer for session termination requests.
    """
    session_id = serializers.CharField(
        help_text="ID of the session to terminate",
        required=False
    )
    terminate_all = serializers.BooleanField(
        default=False,
        help_text="Whether to terminate all sessions"
    )

    def validate(self, data):
        """Validate termination request."""
        if not data.get('session_id') and not data.get('terminate_all'):
            raise serializers.ValidationError(
                "Either session_id or terminate_all must be provided"
            )
        return data


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check responses.
    """
    status = serializers.CharField(
        help_text="Overall health status"
    )
    timestamp = serializers.DateTimeField(
        help_text="Timestamp of health check"
    )
    version = serializers.CharField(
        help_text="Application version",
        required=False
    )
    checks = serializers.DictField(
        help_text="Individual component health checks",
        required=False
    )
    uptime = serializers.CharField(
        help_text="Application uptime",
        required=False
    )


class SessionTerminateSerializer(serializers.Serializer):
    """
    Serializer for session termination requests.
    """
    session_id = serializers.CharField(
        help_text="ID of the session to terminate",
        required=False
    )
    terminate_all = serializers.BooleanField(
        default=False,
        help_text="Whether to terminate all sessions except current"
    )

    def validate(self, attrs):
        """Validate that either session_id or terminate_all is provided."""
        session_id = attrs.get('session_id')
        terminate_all = attrs.get('terminate_all')

        if not session_id and not terminate_all:
            raise serializers.ValidationError(
                "Either 'session_id' or 'terminate_all' must be provided"
            )

        if session_id and terminate_all:
            raise serializers.ValidationError(
                "Cannot specify both 'session_id' and 'terminate_all'"
            )

        return attrs


class SessionSecuritySerializer(serializers.Serializer):
    """
    Serializer for session security analysis.

    Features:
    - Security threat assessment
    - Anomaly detection results
    - Risk level evaluation
    - Mitigation recommendations
    """

    overall_risk_level = serializers.CharField(read_only=True)
    threats_detected = serializers.ListField(read_only=True)
    anomalies = serializers.ListField(read_only=True)
    security_recommendations = serializers.ListField(read_only=True)
    last_security_scan = serializers.DateTimeField(read_only=True)
    suspicious_sessions = serializers.IntegerField(read_only=True)
    geographic_anomalies = serializers.IntegerField(read_only=True)
    device_anomalies = serializers.IntegerField(read_only=True)

    def to_representation(self, instance):
        """Generate security analysis representation."""
        user = instance
        from .models import UserSession

        sessions = UserSession.objects.filter(user=user, is_active=True)

        threats = []
        anomalies = []
        suspicious_count = 0
        geo_anomalies = 0
        device_anomalies = 0

        # Analyze each session for threats
        for session in sessions:
            if session.user_agent:
                suspicion = device_fingerprinter.detect_suspicious_agent(
                    session.user_agent)
                if suspicion['is_suspicious']:
                    suspicious_count += 1
                    threats.extend(suspicion['reasons'])

        # Check for geographic anomalies (simplified)
        unique_ips = sessions.values_list('ip_address', flat=True).distinct()
        if len(unique_ips) > 5:  # More than 5 different IPs
            geo_anomalies = len(unique_ips) - 5
            anomalies.append(
                f'Login from {len(unique_ips)} different IP addresses')

        # Check for device anomalies
        unique_fingerprints = sessions.values_list(
            'device_fingerprint', flat=True).distinct()
        if len(unique_fingerprints) > 10:  # More than 10 different devices
            device_anomalies = len(unique_fingerprints) - 10
            anomalies.append(
                f'Sessions from {len(unique_fingerprints)} different devices')

        # Determine overall risk level
        if suspicious_count > 2 or geo_anomalies > 5:
            risk_level = 'high'
        elif suspicious_count > 0 or geo_anomalies > 2 or device_anomalies > 5:
            risk_level = 'medium'
        elif anomalies:
            risk_level = 'low'
        else:
            risk_level = 'minimal'

        # Generate recommendations
        recommendations = []
        if suspicious_count > 0:
            recommendations.append('Terminate suspicious sessions immediately')
        if geo_anomalies > 3:
            recommendations.append(
                'Review login locations and terminate unknown sessions')
        if device_anomalies > 8:
            recommendations.append(
                'Review and clean up unused device sessions')
        if not recommendations:
            recommendations.append(
                'Your sessions appear secure. Continue monitoring regularly.')

        return {
            'overall_risk_level': risk_level,
            'threats_detected': list(set(threats)),  # Remove duplicates
            'anomalies': anomalies,
            'security_recommendations': recommendations,
            'last_security_scan': timezone.now(),
            'suspicious_sessions': suspicious_count,
            'geographic_anomalies': geo_anomalies,
            'device_anomalies': device_anomalies
        }
