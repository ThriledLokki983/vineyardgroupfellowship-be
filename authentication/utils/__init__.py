"""
Authentication utilities package.
"""

from .auth import (
    generate_secure_token,
    generate_verification_token,
    generate_reset_token,
    normalize_email,
    is_disposable_email,
    validate_password_strength,
    estimate_password_strength,
    PasswordValidator,
    get_client_ip
)

from .sessions import (
    parse_user_agent,
    get_device_fingerprint,
    is_suspicious_user_agent,
    detect_session_anomalies,
    calculate_session_risk_score,
    get_session_summary
)

from .cookies import (
    set_refresh_token_cookie,
    clear_refresh_token_cookie,
    get_refresh_token_from_cookie,
    set_csrf_cookie,
    set_security_headers,
    create_secure_response,
    clear_all_auth_cookies
)

from .email import (
    EmailService,
    validate_email_settings,
    test_email_connection,
    EmailThrottler
)

__all__ = [
    # Auth utilities
    'generate_secure_token',
    'generate_verification_token',
    'generate_reset_token',
    'normalize_email',
    'is_disposable_email',
    'validate_password_strength',
    'estimate_password_strength',
    'PasswordValidator',
    'get_client_ip',

    # Session utilities
    'parse_user_agent',
    'get_device_fingerprint',
    'is_suspicious_user_agent',
    'detect_session_anomalies',
    'calculate_session_risk_score',
    'get_session_summary',

    # Cookie utilities
    'set_refresh_token_cookie',
    'clear_refresh_token_cookie',
    'get_refresh_token_from_cookie',
    'set_csrf_cookie',
    'set_security_headers',
    'create_secure_response',
    'clear_all_auth_cookies',

    # Email utilities
    'EmailService',
    'validate_email_settings',
    'test_email_connection',
    'EmailThrottler',
]
