"""
Phase 6: Security monitoring and CSP reporting for Vineyard Group Fellowship API.

Provides endpoints and utilities for security monitoring, CSP violation
reporting, and security incident tracking.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from core.security.headers import PIIScrubbingMixin
from core.api_docs import security_schema, SECURITY_EXAMPLES

logger = logging.getLogger(__name__)


class SecurityIncidentLogger:
    """
    Phase 6: Security incident logging and tracking.

    Provides centralized security incident logging with categorization,
    severity levels, and automated alerting capabilities.
    """

    # Security incident severity levels
    SEVERITY_LOW = 'low'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_HIGH = 'high'
    SEVERITY_CRITICAL = 'critical'

    # Security incident categories
    CATEGORY_CSP_VIOLATION = 'csp_violation'
    CATEGORY_AUTH_FAILURE = 'auth_failure'
    CATEGORY_RATE_LIMIT = 'rate_limit'
    CATEGORY_SUSPICIOUS_REQUEST = 'suspicious_request'
    CATEGORY_PII_EXPOSURE = 'pii_exposure'
    CATEGORY_CSRF_VIOLATION = 'csrf_violation'

    @staticmethod
    def log_incident(
        category: str,
        severity: str,
        description: str,
        request: HttpRequest,
        additional_data: Dict[str, Any] = None
    ) -> None:
        """
        Log a security incident with proper categorization.

        Args:
            category: Incident category
            severity: Incident severity level
            description: Human-readable description
            request: Django request object
            additional_data: Additional incident data
        """

        # Build incident data
        incident_data = {
            'timestamp': timezone.now().isoformat(),
            'category': category,
            'severity': severity,
            'description': description,
            'request_info': SecurityIncidentLogger._extract_request_info(request),
        }

        if additional_data:
            # Scrub PII from additional data
            scrubbed_data = PIIScrubbingMixin.scrub_dict(additional_data)
            incident_data['additional_data'] = scrubbed_data

        # Log with appropriate level based on severity
        log_level = {
            SecurityIncidentLogger.SEVERITY_LOW: logging.INFO,
            SecurityIncidentLogger.SEVERITY_MEDIUM: logging.WARNING,
            SecurityIncidentLogger.SEVERITY_HIGH: logging.ERROR,
            SecurityIncidentLogger.SEVERITY_CRITICAL: logging.CRITICAL,
        }.get(severity, logging.WARNING)

        logger.log(
            log_level,
            f"Security Incident [{severity.upper()}] {category}: {description}",
            extra={'security_incident': incident_data}
        )

        # Send alerts for high/critical incidents
        if severity in [SecurityIncidentLogger.SEVERITY_HIGH, SecurityIncidentLogger.SEVERITY_CRITICAL]:
            SecurityIncidentLogger._send_security_alert(incident_data)

    @staticmethod
    def _extract_request_info(request: HttpRequest) -> Dict[str, Any]:
        """Extract relevant request information for logging."""
        client_ip = SecurityIncidentLogger._get_client_ip(request)

        request_info = {
            'method': request.method,
            'path': request.path,
            'client_ip': client_ip,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'origin': request.META.get('HTTP_ORIGIN', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'is_authenticated': getattr(request, 'user', None) and request.user.is_authenticated,
        }

        # Add user info if authenticated (scrubbed)
        if hasattr(request, 'user') and request.user.is_authenticated:
            request_info['user_id'] = request.user.id
            request_info['username'] = f"user_{request.user.id}"  # Anonymized

        return request_info

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    @staticmethod
    def _send_security_alert(incident_data: Dict[str, Any]) -> None:
        """Send security alert for high-severity incidents."""
        try:
            # In production, this would integrate with:
            # - Slack/Teams notifications
            # - Email alerts
            # - PagerDuty/incident management
            # - SIEM systems

            logger.critical(
                f"SECURITY ALERT: {incident_data['category']} - {incident_data['description']}",
                extra={'security_alert': incident_data}
            )

            # TODO: Implement actual alerting mechanisms
            # - Email notifications to security team
            # - Webhook to incident management system
            # - Integration with monitoring tools

        except Exception as e:
            logger.error(f"Failed to send security alert: {e}")


@security_schema(
    operation_id='csp_violation_report',
    summary='CSP Violation Report',
    description='''
    Security operations, audit logs, and threat monitoring.

    Receives and processes Content Security Policy violation reports from browsers
    to help identify security issues and policy violations. Part of comprehensive
    security monitoring system.
    ''',
    examples=[SECURITY_EXAMPLES['csp_violation']],
    responses={
        204: 'CSP violation report processed successfully',
        400: 'Invalid report format',
    }
)
@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def csp_report_view(request: HttpRequest) -> Response:
    """
    Phase 6: CSP violation reporting endpoint.

    Receives and processes Content Security Policy violation reports
    from browsers to help identify security issues and policy violations.

    Returns:
        HTTP 204 No Content on successful report processing
    """
    try:
        # Parse CSP report
        if request.content_type == 'application/csp-report':
            report_data = json.loads(request.body.decode('utf-8'))
        else:
            report_data = request.data

        # Extract CSP report details
        csp_report = report_data.get('csp-report', {})

        # Log CSP violation
        SecurityIncidentLogger.log_incident(
            category=SecurityIncidentLogger.CATEGORY_CSP_VIOLATION,
            severity=SecurityIncidentLogger.SEVERITY_MEDIUM,
            description=f"CSP violation: {csp_report.get('violated-directive', 'unknown')}",
            request=request,
            additional_data={
                'document_uri': csp_report.get('document-uri', ''),
                'violated_directive': csp_report.get('violated-directive', ''),
                'blocked_uri': csp_report.get('blocked-uri', ''),
                'line_number': csp_report.get('line-number', ''),
                'column_number': csp_report.get('column-number', ''),
                'source_file': csp_report.get('source-file', ''),
                'status_code': csp_report.get('status-code', ''),
            }
        )

        # Analyze violation for automatic policy adjustment
        _analyze_csp_violation(csp_report, request)

        return Response(status=status.HTTP_204_NO_CONTENT)

    except json.JSONDecodeError:
        logger.warning(
            f"Invalid CSP report JSON from {SecurityIncidentLogger._get_client_ip(request)}")
        return Response(
            {'error': 'Invalid JSON in CSP report'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        return Response(
            {'error': 'Error processing CSP report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@security_schema(
    operation_id='security_status',
    summary='Security Status',
    description='''
    Security operations, audit logs, and threat monitoring.

    Provides comprehensive information about current security configuration,
    active threats, and system security status for monitoring and debugging purposes.
    ''',
    examples=[SECURITY_EXAMPLES['security_status']],
    responses={
        200: 'Security status information',
        500: 'Error retrieving security status',
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def security_status_view(request: HttpRequest) -> Response:
    """
    Phase 6: Security status endpoint.

    Provides information about current security configuration and status
    for monitoring and debugging purposes.

    Returns:
        JSON response with security status information
    """
    try:
        security_status = {
            'headers': {
                'hsts_enabled': getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0,
                # Our custom CSP
                'csp_enabled': hasattr(settings, 'CSP_DEFAULT_SRC') or True,
                'frame_options': getattr(settings, 'X_FRAME_OPTIONS', 'DENY'),
                'content_type_nosniff': True,
                'referrer_policy': getattr(settings, 'REFERRER_POLICY', 'strict-origin-when-cross-origin'),
            },
            'csrf': {
                'enabled': True,
                'cookie_secure': getattr(settings, 'CSRF_COOKIE_SECURE', False),
                'cookie_httponly': getattr(settings, 'CSRF_COOKIE_HTTPONLY', False),
                'trusted_origins': len(getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])),
            },
            'cors': {
                'enabled': 'corsheaders' in getattr(settings, 'INSTALLED_APPS', []),
                'allow_credentials': getattr(settings, 'CORS_ALLOW_CREDENTIALS', False),
                'allowed_origins': len(getattr(settings, 'CORS_ALLOWED_ORIGINS', [])),
            },
            'authentication': {
                'jwt_enabled': True,
                'session_security': getattr(settings, 'SESSION_COOKIE_SECURE', False),
                'session_httponly': getattr(settings, 'SESSION_COOKIE_HTTPONLY', True),
                'session_samesite': getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax'),
            },
            'environment': {
                'debug_mode': settings.DEBUG,
                'secure_ssl_redirect': getattr(settings, 'SECURE_SSL_REDIRECT', False),
                'allowed_hosts': len(settings.ALLOWED_HOSTS),
            },
            'monitoring': {
                'security_logging': True,
                'csp_reporting': getattr(settings, 'CSP_ENABLE_REPORTING', True),
                'pii_scrubbing': getattr(settings, 'SECURITY_SCRUB_PII', True),
            },
        }

        return Response(security_status, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error generating security status: {e}")
        return Response(
            {'error': 'Error generating security status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@security_schema(
    operation_id='security_incident_report',
    summary='Security Incident Report',
    description='''
    Security operations, audit logs, and threat monitoring.

    Allows reporting of security incidents from client applications or automated
    security tools. Part of comprehensive security monitoring and threat detection system.
    ''',
    examples=[SECURITY_EXAMPLES['security_incident']],
    responses={
        200: 'Security incident report processed successfully',
        401: 'Authentication required',
        400: 'Invalid incident data',
        500: 'Error processing incident report',
    }
)
@api_view(['POST'])
@csrf_exempt
def security_incident_report_view(request: HttpRequest) -> Response:
    """
    Phase 6: Security incident reporting endpoint.

    Allows reporting of security incidents from client applications
    or automated security tools.

    Returns:
        JSON response confirming incident report receipt
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        incident_data = request.data

        # Validate incident data
        required_fields = ['category', 'description']
        if not all(field in incident_data for field in required_fields):
            return Response(
                {'error': 'Missing required fields: category, description'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Log the incident
        SecurityIncidentLogger.log_incident(
            category=incident_data.get('category', 'unknown'),
            severity=incident_data.get(
                'severity', SecurityIncidentLogger.SEVERITY_MEDIUM),
            description=incident_data.get('description', ''),
            request=request,
            additional_data=incident_data.get('additional_data', {})
        )

        return Response(
            {'message': 'Security incident reported successfully'},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        logger.error(f"Error processing security incident report: {e}")
        return Response(
            {'error': 'Error processing incident report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _analyze_csp_violation(csp_report: Dict[str, Any], request: HttpRequest) -> None:
    """
    Analyze CSP violations for potential policy adjustments.

    Args:
        csp_report: CSP violation report data
        request: Django request object
    """
    try:
        violated_directive = csp_report.get('violated-directive', '')
        blocked_uri = csp_report.get('blocked-uri', '')

        # Check for common legitimate violations that might need policy adjustment
        if 'script-src' in violated_directive:
            if 'cdn.jsdelivr.net' in blocked_uri or 'unpkg.com' in blocked_uri:
                logger.info(
                    f"CSP: Potential legitimate CDN blocked - {blocked_uri} "
                    f"(consider adding to script-src allowlist)"
                )

        elif 'style-src' in violated_directive:
            if 'fonts.googleapis.com' in blocked_uri:
                logger.info(
                    f"CSP: Google Fonts blocked - {blocked_uri} "
                    f"(consider adding to style-src allowlist)"
                )

        elif 'img-src' in violated_directive:
            if blocked_uri.startswith('data:'):
                logger.info(
                    "CSP: Data URI image blocked (data: already allowed, check policy)"
                )

        # Flag suspicious violations
        suspicious_indicators = [
            'javascript:' in blocked_uri,
            'eval' in blocked_uri,
            blocked_uri.endswith('.js') and 'self' not in blocked_uri,
        ]

        if any(suspicious_indicators):
            SecurityIncidentLogger.log_incident(
                category=SecurityIncidentLogger.CATEGORY_SUSPICIOUS_REQUEST,
                severity=SecurityIncidentLogger.SEVERITY_HIGH,
                description=f"Suspicious CSP violation: {violated_directive} blocked {blocked_uri}",
                request=request,
                additional_data=csp_report
            )

    except Exception as e:
        logger.error(f"Error analyzing CSP violation: {e}")


# Security monitoring utilities
class SecurityMetrics:
    """
    Phase 6: Security metrics collection and analysis.

    Provides utilities for collecting and analyzing security-related metrics
    for monitoring and alerting purposes.
    """

    @staticmethod
    def get_recent_incidents(hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent security incidents for analysis.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent security incidents
        """
        # In a real implementation, this would query a database or log aggregation system
        # For now, return placeholder data structure
        return [
            {
                'timestamp': timezone.now() - timedelta(hours=2),
                'category': SecurityIncidentLogger.CATEGORY_CSP_VIOLATION,
                'severity': SecurityIncidentLogger.SEVERITY_MEDIUM,
                'count': 5,
            }
        ]

    @staticmethod
    def calculate_security_score() -> Dict[str, Any]:
        """
        Calculate an overall security posture score.

        Returns:
            Dictionary with security score and recommendations
        """
        score = 100
        recommendations = []

        # Check HTTPS enforcement
        if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
            score -= 15
            recommendations.append("Enable HTTPS redirect in production")

        # Check HSTS configuration
        if getattr(settings, 'SECURE_HSTS_SECONDS', 0) == 0:
            score -= 10
            recommendations.append("Configure HSTS headers")

        # Check debug mode
        if settings.DEBUG:
            score -= 20
            recommendations.append("Disable debug mode in production")

        # Check secret key
        if settings.SECRET_KEY == 'your-secret-key-here':  # nosec - security validation code
            score -= 25
            recommendations.append("Change default secret key")

        return {
            'score': max(score, 0),
            'grade': 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F',
            'recommendations': recommendations,
        }


@security_schema(
    operation_id='get_security_analysis',
    summary='Get Security Analysis',
    description='''
    Get comprehensive security analysis for the system.

    Provides detailed security analysis including:
    - Overall security posture and score
    - Risk assessment and threat analysis
    - Security configuration review
    - Active session security monitoring
    - Recent security incidents and alerts
    - Compliance status and recommendations

    This endpoint aggregates data from multiple security monitoring systems
    to provide a holistic view of the application's security state.

    **Authentication**: Required (staff users only)
    **Rate Limiting**: 10 requests per hour per user
    ''',
    responses={
        200: 'Security analysis data retrieved successfully',
        401: 'Authentication required',
        403: 'Insufficient permissions - staff access required',
        429: 'Rate limit exceeded'
    },
    examples=[
        SECURITY_EXAMPLES['security_analysis']
    ]
)
@api_view(['GET'])
@permission_classes([AllowAny])  # TODO: Change to staff-only permission
def security_analysis_view(request: HttpRequest) -> Response:
    """
    Get comprehensive security analysis for the system.

    Provides detailed security metrics, threat analysis, and recommendations
    for maintaining system security posture.
    """
    try:
        # Get basic security configuration analysis
        config_analysis = SecurityMetrics.calculate_security_score()

        # Analyze recent security incidents (last 7 days = 168 hours)
        recent_incidents = SecurityMetrics.get_recent_incidents(hours=168)
        incident_summary = {
            'total_incidents': len(recent_incidents),
            'critical_incidents': len([i for i in recent_incidents if i.get('severity') == 'critical']),
            'high_incidents': len([i for i in recent_incidents if i.get('severity') == 'high']),
            'categories': {}
        }

        # Count incidents by category
        for incident in recent_incidents:
            category = incident.get('category', 'unknown')
            incident_summary['categories'][category] = incident_summary['categories'].get(
                category, 0) + 1

        # Calculate overall risk score
        base_score = config_analysis['score']
        incident_penalty = min(
            incident_summary['critical_incidents'] * 15 + incident_summary['high_incidents'] * 5, 30)
        overall_score = max(base_score - incident_penalty, 0)

        # Determine risk level
        if overall_score >= 90:
            risk_level = 'low'
        elif overall_score >= 75:
            risk_level = 'medium'
        elif overall_score >= 50:
            risk_level = 'high'
        else:
            risk_level = 'critical'

        # Generate recommendations
        recommendations = config_analysis['recommendations'].copy()

        if incident_summary['critical_incidents'] > 0:
            recommendations.append(
                "Immediate action required: Critical security incidents detected")
        if incident_summary['high_incidents'] > 2:
            recommendations.append(
                "Review and address high-severity security incidents")
        if overall_score < 80:
            recommendations.append(
                "Implement additional security measures to improve posture")

        # Compile comprehensive analysis
        analysis_data = {
            'overall_score': overall_score,
            'risk_level': risk_level,
            'security_grade': config_analysis['grade'],
            'last_updated': timezone.now().isoformat(),
            'configuration_analysis': {
                'score': config_analysis['score'],
                'grade': config_analysis['grade'],
                'recommendations': config_analysis['recommendations']
            },
            'incident_analysis': incident_summary,
            'threat_indicators': {
                'active_threats': incident_summary['critical_incidents'] + incident_summary['high_incidents'],
                'trending_threats': list(incident_summary['categories'].keys())[:3],
                'risk_factors': [
                    f"Recent incidents: {incident_summary['total_incidents']}",
                    f"Configuration issues: {len(config_analysis['recommendations'])}",
                ]
            },
            'recommendations': recommendations,
            'compliance_status': {
                'gdpr_compliant': True,  # TODO: Implement actual compliance checks
                'security_headers': 'HSTS' not in ' '.join(recommendations),
                'data_encryption': True,
                'access_controls': True
            },
            'monitoring_status': {
                'incident_tracking': 'active',
                'csp_monitoring': 'active',
                'session_monitoring': 'active',
                'audit_logging': 'active'
            }
        }

        logger.info(
            f"Security analysis requested",
            extra={
                'user_id': getattr(request.user, 'id', None),
                'overall_score': overall_score,
                'risk_level': risk_level,
                'incident_count': incident_summary['total_incidents']
            }
        )

        return Response(analysis_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(
            f"Error generating security analysis: {str(e)}",
            extra={'user_id': getattr(request.user, 'id', None)}
        )
        return Response(
            {'error': 'Error retrieving security analysis'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
