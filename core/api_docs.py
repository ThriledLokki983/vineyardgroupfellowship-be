"""
Core API Documentation utilities for security and system endpoints.
"""

from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.openapi import AutoSchema


# Core API tags for documentation organization
class CoreAPITags:
    SECURITY = "Security"
    SYSTEM = "System"
    MONITORING = "Monitoring"


# Security and system response examples
SECURITY_EXAMPLES = {
    'security_status': OpenApiExample(
        name="Security Status",
        description="Example of security status response",
        value={
            "status": "secure",
            "last_scan": "2025-10-30T06:40:00Z",
            "threats_detected": 0,
            "security_level": "high",
            "active_sessions": 42,
            "suspicious_activities": []
        }
    ),
    'security_incident': OpenApiExample(
        name="Security Incident Report",
        description="Example of security incident report",
        value={
            "incident_id": "SEC-2025-001",
            "severity": "medium",
            "type": "suspicious_login",
            "timestamp": "2025-10-30T06:40:00Z",
            "user_id": "user123",
            "ip_address": "192.168.1.1",
            "details": "Multiple failed login attempts from unknown location"
        }
    ),
    'security_analysis': OpenApiExample(
        name="Security Analysis Report",
        description="Example of security analysis report",
        value={
            "report_id": "ANALYSIS-2025-045",
            "generated_at": "2025-10-30T06:40:00Z",
            "summary": "No critical vulnerabilities found",
            "vulnerabilities": [
                {
                    "id": "VULN-001",
                    "description": "Outdated software version",
                    "severity": "low",
                    "status": "resolved"
                },
                {
                    "id": "VULN-002",
                    "description": "Weak password policy",
                    "severity": "medium",
                    "status": "in_progress"
                }
            ],
            "recommendations": [
                "Update all software to latest versions",
                "Enforce stronger password policies"
            ]
        }
    ),
    'csp_violation': OpenApiExample(
        name="CSP Violation Report",
        description="Example of Content Security Policy violation report",
        value={
            "document-uri": "https://example.com/page",
            "violated-directive": "script-src",
            "blocked-uri": "https://malicious-site.com/script.js",
            "line-number": 42,
            "column-number": 15
        }
    )
}

SYSTEM_EXAMPLES = {
    'health_check': OpenApiExample(
        name="Health Check",
        description="Example of system health check response",
        value={
            "status": "healthy",
            "timestamp": "2025-10-30T06:40:00Z",
            "services": {
                "database": {"status": "healthy", "response_time": "12ms"},
                "redis": {"status": "healthy", "response_time": "2ms"},
                "email": {"status": "healthy", "response_time": "45ms"}
            },
            "version": "1.0.0",
            "uptime": "2d 14h 32m"
        }
    ),
    'system_status': OpenApiExample(
        name="System Status",
        description="Example of detailed system status response",
        value={
            "status": "operational",
            "timestamp": "2025-10-30T06:40:00Z",
            "metrics": {
                "active_users": 1250,
                "requests_per_minute": 847,
                "memory_usage": "68%",
                "cpu_usage": "23%",
                "disk_usage": "45%"
            },
            "alerts": []
        }
    )
}

SESSION_EXAMPLES = {
    'session_list': OpenApiExample(
        name="Session List",
        description="Example of user session list response",
        value={
            "sessions": [
                {
                    "session_id": "sess_abc123",
                    "device_type": "desktop",
                    "browser": "Chrome 119.0",
                    "location": "San Francisco, CA",
                    "ip_address": "192.168.1.100",
                    "last_activity": "2025-10-30T06:35:00Z",
                    "is_current": True
                },
                {
                    "session_id": "sess_def456",
                    "device_type": "mobile",
                    "browser": "Safari Mobile 17.0",
                    "location": "New York, NY",
                    "ip_address": "192.168.1.200",
                    "last_activity": "2025-10-29T22:15:00Z",
                    "is_current": False
                }
            ],
            "total_sessions": 2,
            "active_sessions": 1
        }
    ),
    'session_terminated': OpenApiExample(
        name="Session Terminated",
        description="Example of session termination response",
        value={
            "message": "Session terminated successfully",
            "session_id": "sess_abc123",
            "terminated_at": "2025-10-30T06:40:00Z"
        }
    )
}


def security_schema(**kwargs):
    """Decorator for security operations, audit logs, and threat monitoring."""
    return extend_schema(
        tags=[CoreAPITags.SECURITY],
        **kwargs
    )


def system_schema(**kwargs):
    """Decorator for health checks and system status endpoints."""
    return extend_schema(
        tags=[CoreAPITags.SYSTEM],
        **kwargs
    )


def monitoring_schema(**kwargs):
    """Decorator for monitoring and metrics endpoints."""
    return extend_schema(
        tags=[CoreAPITags.MONITORING],
        **kwargs
    )
