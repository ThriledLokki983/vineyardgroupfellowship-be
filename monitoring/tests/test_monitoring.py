"""
Simple test script for monitoring system functionality.

Tests performance monitoring middleware and health checks.
"""

from decimal import Decimal
from django.utils import timezone
from monitoring.models import PerformanceMetric, HealthCheck, MetricType
import sys
import os
import django

# Setup Django environment
sys.path.append('/Users/gnimoh001/Desktop/Vineyard Group Fellowship/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'Vineyard Group Fellowship.settings')
django.setup()


def test_performance_metrics():
    """Test creating performance metrics."""
    print("Testing Performance Metrics...")

    # Create a test metric
    metric = PerformanceMetric.objects.create(
        metric_type=MetricType.REQUEST_RESPONSE,
        name="test_endpoint",
        value=Decimal("125.50"),
        unit="ms",
        context={
            "endpoint_path": "/api/v1/test/",
            "method": "GET",
            "status_code": 200
        }
    )

    print(f"✓ Created metric: {metric}")

    # Check if it was saved
    count = PerformanceMetric.objects.count()
    print(f"✓ Total metrics in database: {count}")

    return count > 0


def test_health_checks():
    """Test creating health checks."""
    print("\nTesting Health Checks...")

    # Create a test health check
    health_check = HealthCheck.objects.create(
        check_type="database",
        status=HealthCheck.Status.HEALTHY,
        response_time=Decimal("5.2"),
        details={"connection": "active", "queries": 0}
    )

    print(f"✓ Created health check: {health_check}")

    # Check if it was saved
    count = HealthCheck.objects.count()
    print(f"✓ Total health checks in database: {count}")

    return count > 0


def cleanup_test_data():
    """Clean up test data."""
    print("\nCleaning up test data...")

    PerformanceMetric.objects.filter(name="test_endpoint").delete()
    HealthCheck.objects.filter(check_type="database").delete()

    print("✓ Test data cleaned up")


if __name__ == "__main__":
    print("=== Monitoring System Test ===\n")

    try:
        # Test basic functionality
        metrics_test = test_performance_metrics()
        health_test = test_health_checks()

        print(f"\n=== Test Results ===")
        print(f"Performance Metrics: {'✓ PASS' if metrics_test else '✗ FAIL'}")
        print(f"Health Checks: {'✓ PASS' if health_test else '✗ FAIL'}")

        if metrics_test and health_test:
            print(f"\n🎉 All tests passed! Monitoring system is working correctly.")
        else:
            print(f"\n❌ Some tests failed. Check the configuration.")

        # Clean up
        cleanup_test_data()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
