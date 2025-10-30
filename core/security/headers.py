"""
Phase 6: Security Headers Enhancement for Vineyard Group Fellowship API.

This module provides comprehensive security headers implementation including:
- Content Security Policy (CSP) with nonce support
- HTTP Strict Transport Security (HSTS)
- PII scrubbing for logs and responses
- Security monitoring and violation reporting
- Production-ready security configurations
"""

import hashlib
import logging
import re
import uuid
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Phase 6: Comprehensive security headers middleware.

    Implements enterprise-grade security headers for the Vineyard Group Fellowship platform
    with special considerations for addiction recovery applications.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

        # Load security configuration
        self.security_config = self._load_security_config()

        # PII patterns for scrubbing
        self.pii_patterns = self._compile_pii_patterns()

        # CSP nonce cache
        self.nonce_cache = {}

    def process_request(self, request: HttpRequest) -> None:
        """
        Process incoming request for security enhancements.

        Args:
            request: Django request object
        """
        # Generate CSP nonce for this request
        request.csp_nonce = self._generate_csp_nonce()

        # Add security metadata
        request.security_metadata = {
            'timestamp': timezone.now(),
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'origin': request.META.get('HTTP_ORIGIN', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'request_id': str(uuid.uuid4()),
        }

        # Log security-sensitive requests
        self._log_security_request(request)

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Add comprehensive security headers to response.

        Args:
            request: Django request object
            response: Django response object

        Returns:
            Response with security headers added
        """
        # Apply core security headers
        self._apply_core_headers(request, response)

        # Apply Content Security Policy
        self._apply_csp_headers(request, response)

        # Apply additional security headers
        self._apply_additional_headers(request, response)

        # Scrub PII from response if needed (but exclude API documentation)
        if (self.security_config.get('scrub_pii', True) and
                not self._is_api_documentation(request)):
            self._scrub_response_pii(response)

        # Log security response
        self._log_security_response(request, response)

        return response

    def _load_security_config(self) -> Dict[str, Any]:
        """Load security configuration from settings."""
        return {
            # 1 year
            'hsts_max_age': getattr(settings, 'SECURE_HSTS_SECONDS', 31536000),
            'hsts_include_subdomains': getattr(settings, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', True),
            'hsts_preload': getattr(settings, 'SECURE_HSTS_PRELOAD', True),
            'content_type_nosniff': True,
            'frame_options': getattr(settings, 'X_FRAME_OPTIONS', 'DENY'),
            'referrer_policy': getattr(settings, 'REFERRER_POLICY', 'strict-origin-when-cross-origin'),
            'permissions_policy': getattr(settings, 'PERMISSIONS_POLICY', {}),
            'scrub_pii': getattr(settings, 'SECURITY_SCRUB_PII', True),
            'csp_report_uri': getattr(settings, 'CSP_REPORT_URI', '/api/v1/security/csp-report/'),
            'enable_csp_reporting': getattr(settings, 'CSP_ENABLE_REPORTING', True),
        }

    def _compile_pii_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for PII detection."""
        patterns = [
            # Email addresses
            re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE),

            # Phone numbers (various formats)
            re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),

            # SSN (XXX-XX-XXXX format)
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),

            # Credit card numbers (basic pattern)
            re.compile(r'\b(?:\d{4}[-.\s]?){3}\d{4}\b'),

            # IP addresses
            re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),

            # Potential session tokens or API keys (long alphanumeric strings)
            re.compile(r'\b[A-Za-z0-9]{20,}\b'),
        ]
        return patterns

    def _generate_csp_nonce(self) -> str:
        """Generate a cryptographically secure nonce for CSP."""
        nonce = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:16]
        return nonce

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    def _apply_core_headers(self, request: HttpRequest, response: HttpResponse) -> None:
        """Apply core security headers."""

        # HTTP Strict Transport Security (HSTS)
        if request.is_secure():
            hsts_value = f"max-age={self.security_config['hsts_max_age']}"
            if self.security_config['hsts_include_subdomains']:
                hsts_value += "; includeSubDomains"
            if self.security_config['hsts_preload']:
                hsts_value += "; preload"
            response['Strict-Transport-Security'] = hsts_value

        # X-Content-Type-Options
        if self.security_config['content_type_nosniff']:
            response['X-Content-Type-Options'] = 'nosniff'

        # X-Frame-Options
        response['X-Frame-Options'] = self.security_config['frame_options']

        # Referrer Policy
        response['Referrer-Policy'] = self.security_config['referrer_policy']

        # X-XSS-Protection (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'

        # Remove server information
        response['Server'] = 'Vineyard Group Fellowship'

        # Add security request ID for tracking
        if hasattr(request, 'security_metadata'):
            response['X-Request-ID'] = request.security_metadata['request_id']

    def _apply_csp_headers(self, request: HttpRequest, response: HttpResponse) -> None:
        """Apply Content Security Policy headers."""

        # Get CSP nonce
        nonce = getattr(request, 'csp_nonce', '')

        # Build CSP directives
        csp_directives = self._build_csp_directives(request, nonce)

        # Set CSP header
        csp_value = '; '.join([f"{directive} {' '.join(sources)}"
                              for directive, sources in csp_directives.items()])

        response['Content-Security-Policy'] = csp_value

        # Add CSP reporting if enabled (temporarily disabled for API docs debugging)
        # if self.security_config['enable_csp_reporting']:
        #     report_only_csp = self._build_report_only_csp(nonce)
        #     if report_only_csp:
        #         response['Content-Security-Policy-Report-Only'] = report_only_csp

    def _build_csp_directives(self, request: HttpRequest, nonce: str) -> Dict[str, List[str]]:
        """Build CSP directives based on environment and request."""

        # Base directives for addiction recovery platform
        directives = {
            'default-src': ["'self'"],
            'script-src': ["'self'", f"'nonce-{nonce}'"],
            # Some CSS frameworks need inline styles
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "blob:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'media-src': ["'none'"],  # No media initially to prevent triggers
            'object-src': ["'none'"],
            'frame-src': ["'none'"],
            'frame-ancestors': ["'none'"],
            'form-action': ["'self'"],
            'base-uri': ["'self'"],
            'upgrade-insecure-requests': [],
        }

        # Development environment adjustments
        if settings.DEBUG:
            # Allow localhost for development
            localhost_sources = ['localhost:*', '127.0.0.1:*', '0.0.0.0:*']
            directives['connect-src'].extend(localhost_sources)
            directives['script-src'].extend(localhost_sources)

            # Allow unsafe-eval for development tools
            directives['script-src'].append("'unsafe-eval'")

        # Production environment adjustments
        else:
            # Add production CDN domains if configured
            cdn_domains = getattr(settings, 'CSP_CDN_DOMAINS', [])
            if cdn_domains:
                directives['script-src'].extend(cdn_domains)
                directives['style-src'].extend(cdn_domains)
                directives['font-src'].extend(cdn_domains)
                directives['img-src'].extend(cdn_domains)

        # API-specific adjustments
        if request.path.startswith('/api/v1/'):
            # Only actual API endpoints don't need script/style sources
            # Exclude documentation and schema endpoints
            if not self._is_api_documentation(request):
                directives['script-src'] = ["'none'"]
                directives['style-src'] = ["'none'"]
                directives['img-src'] = ["'none'"]

        # Allow CDN resources for API documentation
        if self._is_api_documentation(request):
            # Get CDN sources from settings (same as production)
            cdn_sources = getattr(settings, 'CSP_CDN_DOMAINS', [])
            if cdn_sources:
                directives['script-src'].extend(cdn_sources)
                directives['style-src'].extend(cdn_sources)
                directives['img-src'].extend(cdn_sources)
                directives['font-src'].extend(cdn_sources)
                # Add CDN to connect-src for CSS source maps and other resources
                directives['connect-src'].extend(cdn_sources)

            # For API docs, use unsafe-inline instead of nonce for better compatibility
            # Remove nonce and add unsafe-inline for swagger UI inline scripts
            directives['script-src'] = [src for src in directives['script-src']
                                        if not src.startswith("'nonce-")]
            if "'unsafe-inline'" not in directives['script-src']:
                directives['script-src'].append("'unsafe-inline'")

        # Django admin-specific adjustments
        if request.path.startswith('/admin/'):
            # Django admin needs unsafe-inline and unsafe-eval for its JavaScript
            if "'unsafe-inline'" not in directives['script-src']:
                directives['script-src'].append("'unsafe-inline'")
            if "'unsafe-eval'" not in directives['script-src']:
                directives['script-src'].append("'unsafe-eval'")

            # Remove nonce requirement for admin
            directives['script-src'] = [src for src in directives['script-src']
                                        if not src.startswith("'nonce-")]

        # Add report-uri if configured
        if self.security_config['csp_report_uri']:
            directives['report-uri'] = [self.security_config['csp_report_uri']]

        return directives

    def _build_report_only_csp(self, nonce: str) -> Optional[str]:
        """Build CSP Report-Only header for monitoring."""
        if not self.security_config['enable_csp_reporting']:
            return None

        # More restrictive policy for monitoring
        report_directives = {
            'default-src': ["'none'"],
            'script-src': ["'self'", f"'nonce-{nonce}'"],
            'style-src': ["'self'"],
            'img-src': ["'self'", "data:"],
            'connect-src': ["'self'"],
            'report-uri': [self.security_config['csp_report_uri']],
        }

        return '; '.join([f"{directive} {' '.join(sources)}"
                         for directive, sources in report_directives.items()])

    def _apply_additional_headers(self, request: HttpRequest, response: HttpResponse) -> None:
        """Apply additional security headers."""

        # Permissions Policy (formerly Feature Policy)
        permissions = self.security_config.get('permissions_policy', {})
        if permissions:
            policy_items = []
            for feature, allowlist in permissions.items():
                if isinstance(allowlist, list):
                    policy_items.append(f"{feature}=({' '.join(allowlist)})")
                else:
                    policy_items.append(f"{feature}=({allowlist})")

            if policy_items:
                response['Permissions-Policy'] = ', '.join(policy_items)
        else:
            # Default restrictive permissions for addiction recovery platform
            default_permissions = [
                'geolocation=()',      # No location tracking
                'microphone=()',       # No microphone access
                'camera=()',           # No camera access
                'payment=()',          # No payment API
                'usb=()',             # No USB access
                'midi=()',            # No MIDI access
                'encrypted-media=()',  # No DRM content
                'autoplay=()',        # No autoplay (prevents trigger content)
            ]
            response['Permissions-Policy'] = ', '.join(default_permissions)

        # Cross-Origin headers for API security
        if request.path.startswith('/api/'):
            response['Cross-Origin-Embedder-Policy'] = 'require-corp'
            response['Cross-Origin-Opener-Policy'] = 'same-origin'
            response['Cross-Origin-Resource-Policy'] = 'cross-origin'

        # Cache control for sensitive data
        if self._is_sensitive_endpoint(request):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

    def _is_sensitive_endpoint(self, request: HttpRequest) -> bool:
        """Check if the endpoint handles sensitive data."""
        sensitive_paths = [
            '/api/v1/auth/',
            '/api/v1/profiles/',
            '/api/v1/sessions/',
            '/api/v1/security/',
            '/api/v1/gdpr/',
            '/admin/',
        ]

        return any(request.path.startswith(path) for path in sensitive_paths)

    def _is_api_documentation(self, request: HttpRequest) -> bool:
        """Check if the request is for API documentation."""
        # Handle both with and without trailing slashes
        path = request.path.rstrip('/')  # Remove trailing slash for comparison
        api_docs_base_paths = ['/api/docs', '/api/schema', '/api/redoc']
        return (path in api_docs_base_paths or
                any(request.path.startswith(base_path + '/') for base_path in api_docs_base_paths))

    def _scrub_response_pii(self, response: HttpResponse) -> None:
        """Scrub PII from response content."""
        if not hasattr(response, 'content') or not response.content:
            return

        try:
            # Only scrub text-based responses
            content_type = response.get('Content-Type', '')
            if not content_type.startswith(('application/json', 'text/', 'application/xml')):
                return

            content = response.content.decode('utf-8', errors='ignore')

            # Apply PII patterns
            for pattern in self.pii_patterns:
                content = pattern.sub('[REDACTED]', content)

            # Update response content
            response.content = content.encode('utf-8')

        except Exception as e:
            logger.warning(f"Error scrubbing PII from response: {e}")

    def _log_security_request(self, request: HttpRequest) -> None:
        """Log security-relevant request information."""
        if not hasattr(request, 'security_metadata'):
            return

        metadata = request.security_metadata

        # Log high-risk requests
        if self._is_high_risk_request(request):
            logger.warning(
                f"High-risk request: {request.method} {request.path} "
                f"from {metadata['client_ip']} ({metadata['user_agent']})"
            )

        # Log authentication attempts
        if request.path.startswith('/api/v1/auth/'):
            logger.info(
                f"Auth request: {request.method} {request.path} "
                f"from {metadata['client_ip']}"
            )

    def _log_security_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """Log security-relevant response information."""
        if not hasattr(request, 'security_metadata'):
            return

        metadata = request.security_metadata

        # Log authentication failures
        if (request.path.startswith('/api/v1/auth/') and
                response.status_code in [401, 403]):
            logger.warning(
                f"Auth failure: {response.status_code} for {request.method} {request.path} "
                f"from {metadata['client_ip']}"
            )

        # Log CSP violations (if we had a CSP reporting endpoint)
        if response.status_code == 400 and 'csp-report' in request.path:
            logger.warning(
                f"CSP violation report from {metadata['client_ip']}")

    def _is_high_risk_request(self, request: HttpRequest) -> bool:
        """Identify high-risk requests that need extra monitoring."""
        high_risk_indicators = [
            # Unusual user agents
            not request.META.get('HTTP_USER_AGENT', ''),

            # Direct IP access
            request.get_host().replace('.', '').isdigit(),

            # Suspicious paths
            any(suspicious in request.path.lower() for suspicious in [
                'admin', 'config', '.env', 'backup', 'dump'
            ]),

            # Unusual headers
            'X-Forwarded-For' in request.META and
            len(request.META['X-Forwarded-For'].split(',')) > 3,
        ]

        return any(high_risk_indicators)


class PIIScrubbingMixin:
    """
    Phase 6: Mixin for PII scrubbing in logs and responses.

    Provides utilities for identifying and removing PII from various data sources.
    """

    @staticmethod
    def scrub_dict(data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scrub PII from dictionary data.

        Args:
            data: Dictionary to scrub
            sensitive_keys: Additional keys to consider sensitive

        Returns:
            Dictionary with PII scrubbed
        """
        if sensitive_keys is None:
            sensitive_keys = []

        default_sensitive = [
            'password', 'email', 'phone', 'ssn', 'credit_card',
            'token', 'key', 'secret', 'ip_address', 'user_agent'
        ]

        all_sensitive = set(default_sensitive + sensitive_keys)

        scrubbed = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in all_sensitive):
                scrubbed[key] = '[REDACTED]'
            elif isinstance(value, dict):
                scrubbed[key] = PIIScrubbingMixin.scrub_dict(
                    value, sensitive_keys)
            elif isinstance(value, list):
                scrubbed[key] = [
                    PIIScrubbingMixin.scrub_dict(item, sensitive_keys)
                    if isinstance(item, dict) else '[REDACTED]'
                    if any(sensitive in str(item).lower() for sensitive in all_sensitive)
                    else item
                    for item in value
                ]
            else:
                scrubbed[key] = value

        return scrubbed

    @staticmethod
    def scrub_log_message(message: str) -> str:
        """
        Scrub PII from log messages.

        Args:
            message: Log message to scrub

        Returns:
            Scrubbed log message
        """
        # Email pattern
        message = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL_REDACTED]',
            message,
            flags=re.IGNORECASE
        )

        # Phone pattern
        message = re.sub(
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            '[PHONE_REDACTED]',
            message
        )

        # IP pattern
        message = re.sub(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            '[IP_REDACTED]',
            message
        )

        return message
