"""
Test script for enhanced error handling and logging system.

Tests the structured logging, error handling middleware, and security logging.
"""

from core.middleware.error_handling import ErrorHandlingMiddleware
from core.logging.structured import (
    get_contextual_logger,
    log_security_event,
    log_performance_issue,
    log_business_event,
    SensitiveDataFilter
)
from django.contrib.auth import get_user_model
from django.test import RequestFactory
import sys
import os
import django
import json
from decimal import Decimal

# Setup Django environment
sys.path.append('/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'Vineyard Group Fellowship.settings')
django.setup()


User = get_user_model()


def test_structured_logging():
    """Test structured logging functionality."""
    print("Testing Structured Logging...")

    # Test contextual logger
    logger = get_contextual_logger('test')

    # Set some context
    logger.set_context(
        correlation_id='test-123',
        user_id=42,
        test_context=True
    )

    # Test different log levels
    logger.info("Test info message", extra={'additional': 'data'})
    logger.warning("Test warning message")
    logger.error("Test error message")

    print("✓ Structured logging tested")
    return True


def test_sensitive_data_filtering():
    """Test sensitive data filtering."""
    print("Testing Sensitive Data Filtering...")

    # Create filter
    filter_instance = SensitiveDataFilter()

    # Test data with sensitive information
    test_message = "User email is john.doe@example.com and password is secret123"

    # Create mock log record
    import logging
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg=test_message,
        args=(),
        exc_info=None
    )

    # Apply filter
    filter_instance.filter(record)

    # Check that sensitive data was filtered
    if '[EMAIL]' in record.msg and 'john.doe@example.com' not in record.msg:
        print("✓ Email filtering works")
    else:
        print("✗ Email filtering failed")
        return False

    # Test dict filtering
    sensitive_dict = {
        'username': 'testuser',
        'password': 'secret123',
        'email': 'test@example.com',
        'safe_data': 'this is safe'
    }

    filtered_dict = filter_instance._filter_dict(sensitive_dict)

    if filtered_dict['password'] == '[FILTERED]' and filtered_dict['safe_data'] == 'this is safe':
        print("✓ Dictionary filtering works")
    else:
        print("✗ Dictionary filtering failed")
        return False

    print("✓ Sensitive data filtering tested")
    return True


def test_security_logging():
    """Test security event logging."""
    print("Testing Security Event Logging...")

    # Create mock request
    factory = RequestFactory()
    request = factory.get('/test/')
    request.META['REMOTE_ADDR'] = '127.0.0.1'
    request.META['HTTP_USER_AGENT'] = 'TestAgent/1.0'

    # Test security event logging
    log_security_event(
        'login_failed',
        request,
        details={'attempt_count': 3, 'reason': 'invalid_password'}
    )

    print("✓ Security event logged")
    return True


def test_performance_logging():
    """Test performance issue logging."""
    print("Testing Performance Logging...")

    # Test performance issue logging
    log_performance_issue(
        operation='database_query',
        duration_ms=250.5,
        threshold_ms=100.0,
        context={'query_type': 'SELECT', 'table': 'test_table'}
    )

    print("✓ Performance issue logged")
    return True


def test_business_event_logging():
    """Test business event logging."""
    print("Testing Business Event Logging...")

    # Create test user
    user = User(id=1, username='testuser', email='test@example.com')

    # Test business event logging
    log_business_event(
        'profile_completed',
        user=user,
        details={'completion_percentage': 85, 'sections_completed': 4}
    )

    print("✓ Business event logged")
    return True


def test_error_middleware():
    """Test error handling middleware."""
    print("Testing Error Handling Middleware...")

    # Create middleware instance
    middleware = ErrorHandlingMiddleware(lambda r: None)

    # Create mock request with proper host
    factory = RequestFactory()
    request = factory.get('/test/', HTTP_HOST='testserver')
    request.correlation_id = 'test-correlation-id'

    # Add testserver to allowed hosts temporarily
    from django.conf import settings
    original_allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
    settings.ALLOWED_HOSTS = original_allowed_hosts + ['testserver']

    try:
        # Test exception classification
        test_exception = ValueError("Test validation error")
        error_info = middleware._classify_error(test_exception)

        if error_info['status_code'] == 500:  # ValueError is classified as server error
            print("✓ Error classification works")
        else:
            print("✗ Error classification failed")
            return False

        # Test error response creation
        response = middleware._create_error_response(
            request, test_exception, error_info, 'test-id')

        if response.status_code == 500:
            print("✓ Error response creation works")
        else:
            print("✗ Error response creation failed")
            return False

    finally:
        # Restore original allowed hosts
        settings.ALLOWED_HOSTS = original_allowed_hosts

    print("✓ Error handling middleware tested")
    return True


def main():
    """Run all tests."""
    print("=== Enhanced Error Handling & Logging System Test ===\\n")

    tests = [
        test_structured_logging,
        test_sensitive_data_filtering,
        test_security_logging,
        test_performance_logging,
        test_business_event_logging,
        test_error_middleware,
    ]

    results = []

    for test in tests:
        try:
            result = test()
            results.append(result)
            print()  # Add spacing between tests
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with error: {e}")
            results.append(False)
            print()

    # Print summary
    passed = sum(results)
    total = len(results)

    print("=== Test Results ===")
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print(
            "🎉 All tests passed! Enhanced error handling and logging is working correctly.")
    else:
        print("❌ Some tests failed. Check the implementation.")

    return passed == total


if __name__ == "__main__":
    success = main()
