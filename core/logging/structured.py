"""
Structured logging utilities with JSON formatting and sensitive data filtering.

Provides secure, production-ready logging with:
- Correlation ID tracking across requests
- PII and sensitive data filtering
- Structured JSON output for log aggregation
- Context-aware logging with user/session info
"""

import json
import logging
import re
import uuid
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.conf import settings
from django.http import HttpRequest

# Lazy import to avoid circular dependencies and app registry issues


def get_user_model():
    from django.contrib.auth import get_user_model
    return get_user_model()


class SensitiveDataFilter(logging.Filter):
    """
    Filter to remove sensitive data from log records.

    Prevents PII leakage by filtering out common sensitive patterns.
    """

    # Patterns for sensitive data that should be filtered
    SENSITIVE_PATTERNS = [
        # Email patterns
        (re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
        # Phone numbers - more specific pattern that won't match timestamps
        # Matches: (123) 456-7890, 123-456-7890, 123.456.7890, 1234567890
        # But NOT: standalone 10-digit numbers without separators or parentheses in URLs
        (re.compile(r'\b(\(\d{3}\)\s*|\d{3}[-.])\d{3}[-.]?\d{4}\b'), '[PHONE]'),
        # Credit card numbers
        (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), '[CARD]'),
        # Social Security Numbers
        (re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'), '[SSN]'),
        # Passwords and tokens
        (re.compile(
            r'(password|token|secret|key)\s*[:=]\s*[\'"][^\'"\s]+[\'"]', re.IGNORECASE), r'\1=[FILTERED]'),
        # JWT tokens
        (re.compile(
            r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'), '[JWT_TOKEN]'),
    ]

    # Fields that should be completely removed from logs
    SENSITIVE_FIELDS = {
        'password', 'password1', 'password2', 'token', 'secret', 'key',
        'authorization', 'auth_token', 'access_token', 'refresh_token',
        'csrf_token', 'session_key', 'secret_key'
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter sensitive data from log record.

        Returns True to allow the record to be logged.
        """
        try:
            # Filter message content
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                record.msg = self._filter_string(record.msg)

            # Filter arguments
            if hasattr(record, 'args') and record.args:
                filtered_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        filtered_args.append(self._filter_string(arg))
                    elif isinstance(arg, dict):
                        filtered_args.append(self._filter_dict(arg))
                    else:
                        filtered_args.append(arg)
                record.args = tuple(filtered_args)

            # Filter any extra attributes
            for attr_name in dir(record):
                if not attr_name.startswith('_') and attr_name not in ['name', 'msg', 'args', 'levelno', 'levelname', 'pathname', 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process']:
                    attr_value = getattr(record, attr_name)
                    if isinstance(attr_value, str):
                        setattr(record, attr_name,
                                self._filter_string(attr_value))
                    elif isinstance(attr_value, dict):
                        setattr(record, attr_name,
                                self._filter_dict(attr_value))

        except Exception:
            # Don't let filtering errors prevent logging
            pass

        return True

    def _filter_string(self, text: str) -> str:
        """Filter sensitive patterns from string."""
        if not text:
            return text

        filtered_text = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            filtered_text = pattern.sub(replacement, filtered_text)

        return filtered_text

    def _filter_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive fields from dictionary."""
        if not isinstance(data, dict):
            return data

        filtered_data = {}
        for key, value in data.items():
            if key.lower() in self.SENSITIVE_FIELDS:
                filtered_data[key] = '[FILTERED]'
            elif isinstance(value, str):
                filtered_data[key] = self._filter_string(value)
            elif isinstance(value, dict):
                filtered_data[key] = self._filter_dict(value)
            elif isinstance(value, list):
                filtered_data[key] = [
                    self._filter_dict(item) if isinstance(item, dict)
                    else self._filter_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                filtered_data[key] = value

        return filtered_data


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON for better parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        try:
            # Base log entry
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
            }

            # Add correlation ID if available
            if hasattr(record, 'correlation_id'):
                log_entry['correlation_id'] = record.correlation_id

            # Add user context if available
            if hasattr(record, 'user_id'):
                log_entry['user_id'] = record.user_id

            # Add request context if available
            if hasattr(record, 'request_path'):
                log_entry['request_path'] = record.request_path
            if hasattr(record, 'request_method'):
                log_entry['request_method'] = record.request_method
            if hasattr(record, 'status_code'):
                log_entry['status_code'] = record.status_code

            # Add exception information if present
            if record.exc_info:
                log_entry['exception'] = {
                    'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                    'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                    'traceback': traceback.format_exception(*record.exc_info)
                }

            # Add any extra attributes
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelno', 'levelname', 'pathname', 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'exc_info', 'exc_text', 'stack_info'] and not key.startswith('_'):
                    if key not in log_entry:  # Don't overwrite existing keys
                        log_entry[key] = value

            return json.dumps(log_entry, ensure_ascii=False)

        except Exception as e:
            # Fallback to simple formatting if JSON formatting fails
            return f"LOG_FORMAT_ERROR: {record.getMessage()} (Error: {e})"


class ContextualLogger:
    """
    Logger with context awareness for requests, users, and correlation IDs.

    Automatically adds request context and correlation IDs to log messages.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._local_context = {}

    def set_context(self, **context):
        """Set context that will be added to all log messages."""
        self._local_context.update(context)

    def clear_context(self):
        """Clear the local context."""
        self._local_context.clear()

    def _log_with_context(self, level: int, message: str, *args, **kwargs):
        """Log message with context information."""
        extra = kwargs.get('extra', {})
        extra.update(self._local_context)
        kwargs['extra'] = extra

        self.logger.log(level, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Log exception with context and traceback."""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, *args, **kwargs)


def get_contextual_logger(name: str) -> ContextualLogger:
    """Get a contextual logger instance."""
    return ContextualLogger(name)


def setup_request_logging(request: HttpRequest) -> str:
    """
    Set up logging context for a request.

    Returns the correlation ID for this request.
    """
    correlation_id = str(uuid.uuid4())

    # Store correlation ID in request for middleware
    request.correlation_id = correlation_id

    return correlation_id


def log_security_event(event_type: str, request: HttpRequest, details: Dict[str, Any] = None, user=None):
    """
    Log a security-related event.

    Args:
        event_type: Type of security event (login_failed, token_expired, etc.)
        request: HTTP request object
        details: Additional details about the event
        user: User object if available
    """
    logger = get_contextual_logger('security')

    log_data = {
        'event_type': event_type,
        'ip_address': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'request_path': request.path,
        'correlation_id': getattr(request, 'correlation_id', None),
    }

    if user:
        log_data['user_id'] = user.id
        log_data['username'] = user.username

    if details:
        log_data['details'] = details

    logger.info(f"Security event: {event_type}", extra=log_data)


def log_performance_issue(operation: str, duration_ms: float, threshold_ms: float, context: Dict[str, Any] = None):
    """
    Log a performance issue when operations exceed thresholds.

    Args:
        operation: Name of the operation
        duration_ms: How long the operation took
        threshold_ms: The threshold that was exceeded
        context: Additional context about the operation
    """
    logger = get_contextual_logger('performance')

    log_data = {
        'operation': operation,
        'duration_ms': duration_ms,
        'threshold_ms': threshold_ms,
        'performance_issue': True,
    }

    if context:
        log_data.update(context)

    logger.warning(
        f"Performance issue: {operation} took {duration_ms:.2f}ms (threshold: {threshold_ms}ms)",
        extra=log_data
    )


def log_business_event(event_type: str, user=None, details: Dict[str, Any] = None):
    """
    Log important business events for analytics and monitoring.

    Args:
        event_type: Type of business event (user_registered, profile_completed, etc.)
        user: User associated with the event
        details: Additional details about the event
    """
    logger = get_contextual_logger('business')

    log_data = {
        'event_type': event_type,
        'business_event': True,
    }

    if user:
        log_data['user_id'] = user.id

    if details:
        log_data.update(details)

    logger.info(f"Business event: {event_type}", extra=log_data)


def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request, considering proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip
