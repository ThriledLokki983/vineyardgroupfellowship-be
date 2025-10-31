"""
Email verification views: verification and resend functionality.

This module handles email verification operations including
verification token processing and resending verification emails.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from core.api_tags import APITags

from core.exceptions import ProblemDetailException
from core.throttling import (
    EmailVerificationConfirmRateThrottle,
    EmailVerificationRateThrottle,
)

from ..models import AuditLog
from ..serializers import (
    EmailVerificationSerializer,
    EmailVerificationResendSerializer,
)
from ..utils.auth import email_verification_token

logger = logging.getLogger(__name__)


class EmailVerificationView(APIView):
    """
    Email verification endpoint.

    Features:
    - Token-based email verification
    - Account activation
    - Security logging
    - URL and POST data support
    """
    permission_classes = [AllowAny]
    throttle_classes = [EmailVerificationConfirmRateThrottle]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        operation_id='auth_email_verify',
        summary='Verify Email',
        description='Verify email address with token',
        request=EmailVerificationSerializer,
        responses={
            200: OpenApiResponse(
                description='Email verified successfully',
                examples={
                    'application/json': {
                        'message': 'Email verified successfully! You can now log in.',
                        'user_id': 123,
                        'email': 'user@example.com',
                        'already_verified': False
                    }
                }
            ),
            400: OpenApiResponse(description='Invalid token or already verified'),
        },
        tags=[APITags.AUTHENTICATION]
    )
    def post(self, request, uidb64=None, token=None):
        """Verify email with token."""
        # Extract parameters from URL or request data
        uidb64 = uidb64 or request.data.get('uidb64')
        token = token or request.data.get('token')

        # Merge URL parameters into request data
        data = request.data.copy()
        if uidb64:
            data['uidb64'] = uidb64
        if token:
            data['token'] = token

        # Decode user from uidb64
        user = None
        if uidb64:
            user = email_verification_token.decode_uid(uidb64)

        # Check if already verified before validation
        if user and user.email_verified:
            # Already verified - return success with informative message
            logger.info(f"Email already verified for user: {user.email}")
            return Response({
                'message': _('Your email has already been verified. You can log in now.'),
                'user_id': user.id,
                'email': user.email,
                'already_verified': True
            }, status=status.HTTP_200_OK)

        # Initialize serializer with user context
        serializer = EmailVerificationSerializer(
            data=data,
            context={'request': request, 'user': user}
        )

        try:
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                user = serializer.save()

                logger.info(f"Email verified for user: {user.email}")

                return Response({
                    'message': _('Email verified successfully! You can now log in.'),
                    'user_id': user.id,
                    'email': user.email,
                    'already_verified': False
                }, status=status.HTTP_200_OK)

        except ValidationError as e:
            # Log failed verification attempt
            if user:
                AuditLog.objects.create(
                    user=user,
                    action='email_verification_failed',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    user_agent=request.META.get(
                        'HTTP_USER_AGENT', 'Test Client'),
                    details={'reason': str(e)},
                    success=False,
                    risk_level='medium'
                )

            raise ProblemDetailException(
                title="Email Verification Failed",
                detail=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        operation_id='auth_email_verify_get',
        summary='Verify Email via Link',
        description='Verify email address with token via GET request (email link)',
        responses={
            200: OpenApiResponse(
                description='Email verified successfully',
                examples={
                    'application/json': {
                        'message': 'Email verified successfully! You can now log in.',
                        'redirect_url': 'http://localhost:3000/auth/login?exchange_token=...'
                    }
                }
            ),
            400: OpenApiResponse(description='Invalid token or already verified'),
        },
        tags=[APITags.AUTHENTICATION]
    )
    def get(self, request, uidb64=None, token=None):
        """Handle GET requests for email verification links with exchange token flow."""
        if not uidb64 or not token:
            return Response({
                'error': _('Missing verification parameters.')
            }, status=status.HTTP_400_BAD_REQUEST)

        # For GET requests, we'll verify and redirect with exchange token
        data = {'uidb64': uidb64, 'token': token}

        # Decode user from uidb64
        user = email_verification_token.decode_uid(uidb64)

        serializer = EmailVerificationSerializer(
            data=data,
            context={'request': request, 'user': user}
        )

        try:
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                user = serializer.save()

                # Import exchange token service
                from ..services import ExchangeTokenService, AuthenticationService

                # Generate exchange token for secure token handoff
                request_metadata = AuthenticationService.extract_request_metadata(
                    request)
                exchange_token = ExchangeTokenService.generate_exchange_token(
                    user=user,
                    context={
                        'source': 'email_verification',
                        'verified_at': timezone.now().isoformat(),
                        'first_login': True
                    }
                )

                # Log successful verification with exchange token generation
                AuditLog.objects.create(
                    user=user,
                    action='email_verified_exchange_token_generated',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    user_agent=request.META.get(
                        'HTTP_USER_AGENT', 'Test Client'),
                    details={
                        'auto_login_flow': True,
                        'exchange_token_generated': True
                    },
                    success=True,
                    risk_level='low'
                )

                # Redirect to frontend with exchange token
                frontend_url = getattr(
                    settings, 'FRONTEND_URL', 'http://localhost:3000')
                redirect_url = f"{frontend_url}/auth/verified?exchange_token={exchange_token}"

                from django.http import HttpResponseRedirect
                return HttpResponseRedirect(redirect_url)

        except ValidationError as e:
            # Log failed verification attempt
            if user:
                AuditLog.objects.create(
                    user=user,
                    action='email_verification_failed',
                    ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
                    user_agent=request.META.get(
                        'HTTP_USER_AGENT', 'Test Client'),
                    details={'reason': str(e)},
                    success=False,
                    risk_level='medium'
                )

            # For GET requests, redirect to error page
            frontend_url = getattr(
                settings, 'FRONTEND_URL', 'http://localhost:3000')
            error_url = f"{frontend_url}/auth/verify-error?reason={str(e)}"

            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(error_url)


class EmailVerificationResendView(APIView):
    """
    Email verification resend endpoint.

    Features:
    - Rate limited email resending
    - Email enumeration protection
    - Security logging
    """
    permission_classes = [AllowAny]
    throttle_classes = [EmailVerificationRateThrottle]
    serializer_class = EmailVerificationResendSerializer

    @extend_schema(
        operation_id='auth_email_verification_resend',
        summary='Resend Verification Email',
        description='Resend email verification link',
        request=EmailVerificationResendSerializer,
        responses={
            200: OpenApiResponse(
                description='Verification email sent (if needed)',
                examples={
                    'application/json': {
                        'message': 'If the email exists and needs verification, a new verification email has been sent.'
                    }
                }
            ),
            429: OpenApiResponse(description='Rate limit exceeded'),
        },
        tags=[APITags.AUTHENTICATION]
    )
    def post(self, request):
        """Resend verification email."""
        serializer = EmailVerificationResendSerializer(
            data=request.data,
            context={'request': request}
        )

        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Always return success to prevent email enumeration
            return Response({
                'message': _('If the email exists and needs verification, a new verification email has been sent.')
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Email verification resend error: {e}")
            # Always return success to prevent email enumeration
            return Response({
                'message': _('If the email exists and needs verification, a new verification email has been sent.')
            }, status=status.HTTP_200_OK)
