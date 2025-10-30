"""
Phase 6: Security logging configuration for Vineyard Group Fellowship API.

Provides comprehensive logging configuration for security monitoring,
incident tracking, and compliance auditing.
"""

import logging
import sys
from typing import Dict, Any
from django.conf import settings
from core.security.headers import PIIScrubbingMixin


class SecurityFormatter(logging.Formatter):
    """
    Phase 6: Custom formatter for security logs with PII scrubbing.

    Formats security logs with consistent structure and automatic PII scrubbing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scrubber = PIIScrubbingMixin()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with security enhancements.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Add security metadata if available
        if hasattr(record, 'security_incident'):
            record.security_category = record.security_incident.get(
                'category', 'unknown')
            record.security_severity = record.security_incident.get(
                'severity', 'unknown')

        # Scrub PII from message
        if hasattr(record, 'msg') and record.msg:
            record.msg = self.scrubber.scrub_log_message(str(record.msg))

        # Format with parent formatter
        formatted = super().format(record)

        return formatted


class SecurityFilter(logging.Filter):
    """
    Phase 6: Security log filter for enhanced processing.

    Filters and enhances security-related log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records for security processing.

        Args:
            record: Log record to filter

        Returns:
            True if record should be processed
        """
        # Add security context
        record.is_security_log = hasattr(
            record, 'security_incident') or hasattr(record, 'security_alert')

        # Add timestamp
        if not hasattr(record, 'security_timestamp'):
            from django.utils import timezone
            record.security_timestamp = timezone.now().isoformat()

        return True


def get_security_logging_config() -> Dict[str, Any]:
    """
    Get comprehensive security logging configuration.

    Returns:
        Dictionary with logging configuration
    """

    # Base configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'security': {
                '()': 'core.security.logging_config.SecurityFormatter',
                'format': '[{asctime}] {levelname} {name}: {message}',
                'style': '{',
            },
            'security_json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(security_timestamp)s',
            },
            'standard': {
                'format': '[{asctime}] {levelname} {name}: {message}',
                'style': '{',
            },
        },
        'filters': {
            'security': {
                '()': 'core.security.logging_config.SecurityFilter',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': sys.stdout,
            },
            'security_file': {
                'level': 'WARNING',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'security',
                'filename': 'logs/security.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'filters': ['security'],
            },
            'security_json': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'security_json',
                'filename': 'logs/security.json',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['security'],
            },
        },
        'loggers': {
            'core.security': {
                'handlers': ['console', 'security_file', 'security_json'],
                'level': 'INFO',
                'propagate': False,
            },
            'core.middleware.csrf': {
                'handlers': ['console', 'security_file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'authentication': {
                'handlers': ['console', 'security_file'],
                'level': 'INFO',
                'propagate': True,
            },
            'django.security': {
                'handlers': ['console', 'security_file'],
                'level': 'WARNING',
                'propagate': False,
            },
        },
    }

    # Production-specific configuration
    if not getattr(settings, 'DEBUG', True):
        # Add syslog handler for production
        config['handlers']['syslog'] = {
            'level': 'ERROR',
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'security',
            'address': '/dev/log',
            'facility': 'local0',
            'filters': ['security'],
        }

        # Add security logger syslog handler
        config['loggers']['core.security']['handlers'].append('syslog')

        # Add external logging service handler (placeholder)
        # This would integrate with services like:
        # - ELK Stack (Elasticsearch, Logstash, Kibana)
        # - Splunk
        # - Datadog
        # - CloudWatch Logs
        config['handlers']['external_security'] = {
            'level': 'WARNING',
            'class': 'logging.NullHandler',  # Replace with actual external handler
            'formatter': 'security_json',
            'filters': ['security'],
        }

    return config


# Security logging helper functions
def log_security_event(
    category: str,
    severity: str,
    message: str,
    extra_data: Dict[str, Any] = None
) -> None:
    """
    Log a security event with proper categorization.

    Args:
        category: Security event category
        severity: Event severity level
        message: Event description
        extra_data: Additional event data
    """
    logger = logging.getLogger('core.security')

    extra = {
        'security_incident': {
            'category': category,
            'severity': severity,
            'extra_data': extra_data or {},
        }
    }

    log_level = {
        'low': logging.INFO,
        'medium': logging.WARNING,
        'high': logging.ERROR,
        'critical': logging.CRITICAL,
    }.get(severity, logging.WARNING)

    logger.log(log_level, message, extra=extra)


def log_authentication_event(
    event_type: str,
    user_identifier: str,
    success: bool,
    client_ip: str,
    user_agent: str = '',
    additional_data: Dict[str, Any] = None
) -> None:
    """
    Log authentication-related events.

    Args:
        event_type: Type of authentication event
        user_identifier: User identifier (anonymized)
        success: Whether the event was successful
        client_ip: Client IP address
        user_agent: User agent string
        additional_data: Additional event data
    """
    logger = logging.getLogger('authentication')

    # Scrub PII from user agent
    scrubber = PIIScrubbingMixin()
    safe_user_agent = scrubber.scrub_log_message(user_agent)

    extra = {
        'auth_event': {
            'type': event_type,
            'user_id': user_identifier,
            'success': success,
            'client_ip': client_ip,
            'user_agent': safe_user_agent,
            'additional_data': additional_data or {},
        }
    }

    message = f"Auth {event_type}: {'SUCCESS' if success else 'FAILURE'} for {user_identifier} from {client_ip}"

    if success:
        logger.info(message, extra=extra)
    else:
        logger.warning(message, extra=extra)


def log_csp_violation(
    document_uri: str,
    violated_directive: str,
    blocked_uri: str,
    client_ip: str,
    additional_data: Dict[str, Any] = None
) -> None:
    """
    Log CSP violations.

    Args:
        document_uri: URI of the document where violation occurred
        violated_directive: CSP directive that was violated
        blocked_uri: URI that was blocked
        client_ip: Client IP address
        additional_data: Additional violation data
    """
    logger = logging.getLogger('core.security')

    extra = {
        'csp_violation': {
            'document_uri': document_uri,
            'violated_directive': violated_directive,
            'blocked_uri': blocked_uri,
            'client_ip': client_ip,
            'additional_data': additional_data or {},
        }
    }

    message = f"CSP violation: {violated_directive} blocked {blocked_uri} on {document_uri}"
    logger.warning(message, extra=extra)
