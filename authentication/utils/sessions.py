"""
Session management utilities for Vineyard Group Fellowship platform.

This module provides comprehensive session management functionality with:
- Device fingerprinting and identification
- Session security monitoring and anomaly detection
- Geographic location tracking and analysis
- Suspicious activity detection
- Session analytics and reporting
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from user_agents import parse as parse_user_agent

User = get_user_model()
logger = logging.getLogger(__name__)


class DeviceFingerprinter:
    """
    Advanced device fingerprinting for session security.

    Features:
    - User agent parsing and device identification
    - Device fingerprint generation
    - Device type classification
    - Browser and OS detection
    """

    def __init__(self):
        """Initialize the device fingerprinter."""
        self.suspicious_patterns = [
            r'bot|crawler|spider|scraper',
            r'wget|curl|http',
            r'python|perl|ruby|php',
            r'automated|test|phantom'
        ]

    def generate_fingerprint(self, request) -> str:
        """
        Generate a device fingerprint from request data.

        Args:
            request: Django request object

        Returns:
            Unique device fingerprint string
        """
        # Collect fingerprinting data
        user_agent = request.META.get('HTTP_USER_AGENT', 'Test Client')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        accept = request.META.get('HTTP_ACCEPT', '')

        # Additional headers for fingerprinting
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        x_real_ip = request.META.get('HTTP_X_REAL_IP', '')

        # Create fingerprint string
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}|{accept}"

        # Generate hash
        fingerprint = hashlib.sha256(
            fingerprint_data.encode()).hexdigest()[:32]

        return fingerprint

    def parse_device_info(self, user_agent: str) -> Dict[str, Any]:
        """
        Parse user agent string to extract device information.

        Args:
            user_agent: User agent string

        Returns:
            Dictionary with parsed device information
        """
        try:
            parsed = parse_user_agent(user_agent)

            device_info = {
                'browser_family': parsed.browser.family,
                'browser_version': parsed.browser.version_string,
                'os_family': parsed.os.family,
                'os_version': parsed.os.version_string,
                'device_family': parsed.device.family,
                'device_brand': parsed.device.brand,
                'device_model': parsed.device.model,
                'is_mobile': parsed.is_mobile,
                'is_tablet': parsed.is_tablet,
                'is_pc': parsed.is_pc,
                'is_bot': parsed.is_bot
            }

            # Add device type classification
            device_info['device_type'] = self._classify_device_type(
                device_info)

            # Add device display name
            device_info['display_name'] = self._generate_device_display_name(
                device_info)

            return device_info

        except Exception as e:
            logger.error(f"Error parsing user agent: {e}")
            return {
                'browser_family': 'Unknown',
                'browser_version': '',
                'os_family': 'Unknown',
                'os_version': '',
                'device_family': 'Unknown',
                'device_brand': '',
                'device_model': '',
                'is_mobile': False,
                'is_tablet': False,
                'is_pc': True,
                'is_bot': False,
                'device_type': 'unknown',
                'display_name': 'Unknown Device'
            }

    def _classify_device_type(self, device_info: Dict[str, Any]) -> str:
        """
        Classify device type based on parsed information.

        Args:
            device_info: Parsed device information

        Returns:
            Device type classification
        """
        if device_info.get('is_bot'):
            return 'bot'
        elif device_info.get('is_mobile'):
            return 'mobile'
        elif device_info.get('is_tablet'):
            return 'tablet'
        elif device_info.get('is_pc'):
            return 'desktop'
        else:
            return 'unknown'

    def _generate_device_display_name(self, device_info: Dict[str, Any]) -> str:
        """
        Generate a user-friendly device display name.

        Args:
            device_info: Parsed device information

        Returns:
            Human-readable device name
        """
        parts = []

        # Add device brand and model if available
        if device_info.get('device_brand') and device_info.get('device_model'):
            parts.append(
                f"{device_info['device_brand']} {device_info['device_model']}")
        elif device_info.get('device_family') and device_info['device_family'] != 'Other':
            parts.append(device_info['device_family'])

        # Add OS information
        if device_info.get('os_family') and device_info['os_family'] != 'Other':
            os_part = device_info['os_family']
            if device_info.get('os_version'):
                os_part += f" {device_info['os_version']}"
            parts.append(os_part)

        # Add browser information
        if device_info.get('browser_family') and device_info['browser_family'] != 'Other':
            browser_part = device_info['browser_family']
            if device_info.get('browser_version'):
                browser_part += f" {device_info['browser_version']}"
            parts.append(browser_part)

        # Fallback to device type if no specific info
        if not parts:
            device_type = device_info.get('device_type', 'unknown')
            parts.append(device_type.title() + ' Device')

        return ' - '.join(parts)

    def detect_suspicious_agent(self, user_agent: str) -> Dict[str, Any]:
        """
        Detect suspicious user agent patterns.

        Args:
            user_agent: User agent string to analyze

        Returns:
            Dictionary with suspicion analysis
        """
        result = {
            'is_suspicious': False,
            'risk_level': 'low',
            'reasons': []
        }

        if not user_agent:
            result['is_suspicious'] = True
            result['risk_level'] = 'medium'
            result['reasons'].append('Missing user agent')
            return result

        # Check against suspicious patterns
        user_agent_lower = user_agent.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, user_agent_lower):
                result['is_suspicious'] = True
                result['risk_level'] = 'high'
                result['reasons'].append(
                    f'Matches suspicious pattern: {pattern}')

        # Check for unusual characteristics
        if len(user_agent) < 20:
            result['is_suspicious'] = True
            result['risk_level'] = 'medium'
            result['reasons'].append('Unusually short user agent')

        if len(user_agent) > 500:
            result['is_suspicious'] = True
            result['risk_level'] = 'medium'
            result['reasons'].append('Unusually long user agent')

        return result


class SessionSecurityMonitor:
    """
    Security monitoring for user sessions.

    Features:
    - Anomaly detection for session behavior
    - Geographic location analysis
    - Concurrent session monitoring
    - Suspicious activity detection
    """

    def __init__(self):
        """Initialize the session security monitor."""
        self.max_concurrent_sessions = getattr(
            settings, 'MAX_CONCURRENT_SESSIONS', 10)
        self.session_timeout = getattr(settings, 'SESSION_TIMEOUT_HOURS', 24)

    def analyze_session_security(self, user, request, existing_sessions) -> Dict[str, Any]:
        """
        Analyze security aspects of a new session.

        Args:
            user: User creating the session
            request: Django request object
            existing_sessions: QuerySet of existing user sessions

        Returns:
            Dictionary with security analysis
        """
        analysis = {
            'risk_level': 'low',
            'warnings': [],
            'recommendations': [],
            'should_alert': False,
            'should_require_verification': False
        }

        # Check concurrent session count
        active_sessions_count = existing_sessions.filter(
            is_active=True).count()
        if active_sessions_count >= self.max_concurrent_sessions:
            analysis['risk_level'] = 'high'
            analysis['warnings'].append('Maximum concurrent sessions reached')
            analysis['recommendations'].append('Terminate unused sessions')
            analysis['should_alert'] = True

        # Check for geographic anomalies
        ip_address = self._get_client_ip(request)
        location_analysis = self._analyze_location_anomaly(
            user, ip_address, existing_sessions)
        if location_analysis['is_anomalous']:
            analysis['risk_level'] = 'medium' if analysis['risk_level'] == 'low' else 'high'
            analysis['warnings'].extend(location_analysis['warnings'])
            analysis['should_require_verification'] = location_analysis['requires_verification']

        # Check for device anomalies
        fingerprinter = DeviceFingerprinter()
        device_fingerprint = fingerprinter.generate_fingerprint(request)
        device_analysis = self._analyze_device_anomaly(
            user, device_fingerprint, existing_sessions)
        if device_analysis['is_new_device']:
            analysis['risk_level'] = 'medium' if analysis['risk_level'] == 'low' else analysis['risk_level']
            analysis['warnings'].extend(device_analysis['warnings'])

        # Check time-based anomalies
        time_analysis = self._analyze_time_anomaly(user, existing_sessions)
        if time_analysis['is_anomalous']:
            analysis['warnings'].extend(time_analysis['warnings'])

        return analysis

    def _get_client_ip(self, request) -> str:
        """
        Extract client IP address from request.

        Args:
            request: Django request object

        Returns:
            Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

    def _analyze_location_anomaly(self, user, ip_address: str, existing_sessions) -> Dict[str, Any]:
        """
        Analyze location-based anomalies.

        Args:
            user: User object
            ip_address: Client IP address
            existing_sessions: QuerySet of existing sessions

        Returns:
            Dictionary with location analysis
        """
        analysis = {
            'is_anomalous': False,
            'warnings': [],
            'requires_verification': False
        }

        # Get recent session IPs
        recent_sessions = existing_sessions.filter(
            created_at__gte=timezone.now() - timedelta(days=7),
            is_active=True
        ).values_list('ip_address', flat=True)

        recent_ips = set(recent_sessions)

        # Check if this is a completely new IP
        if ip_address not in recent_ips and recent_ips:
            analysis['is_anomalous'] = True
            analysis['warnings'].append('Login from new IP address')

            # If user has a history of sessions, require verification for new IPs
            if len(recent_ips) > 0:
                analysis['requires_verification'] = True

        return analysis

    def _analyze_device_anomaly(self, user, device_fingerprint: str, existing_sessions) -> Dict[str, Any]:
        """
        Analyze device-based anomalies.

        Args:
            user: User object
            device_fingerprint: Device fingerprint
            existing_sessions: QuerySet of existing sessions

        Returns:
            Dictionary with device analysis
        """
        analysis = {
            'is_new_device': False,
            'warnings': []
        }

        # Get recent device fingerprints
        recent_fingerprints = set(
            existing_sessions.filter(
                created_at__gte=timezone.now() - timedelta(days=30),
                is_active=True
            ).values_list('device_fingerprint', flat=True)
        )

        # Check if this is a new device
        if device_fingerprint not in recent_fingerprints and recent_fingerprints:
            analysis['is_new_device'] = True
            analysis['warnings'].append('Login from new device')

        return analysis

    def _analyze_time_anomaly(self, user, existing_sessions) -> Dict[str, Any]:
        """
        Analyze time-based anomalies.

        Args:
            user: User object
            existing_sessions: QuerySet of existing sessions

        Returns:
            Dictionary with time analysis
        """
        analysis = {
            'is_anomalous': False,
            'warnings': []
        }

        # Check for rapid successive logins
        recent_sessions = existing_sessions.filter(
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).count()

        if recent_sessions > 3:
            analysis['is_anomalous'] = True
            analysis['warnings'].append('Rapid successive login attempts')

        return analysis


class SessionAnalytics:
    """
    Analytics and reporting for user sessions.

    Features:
    - Session usage statistics
    - Device usage patterns
    - Security metrics
    - Activity summaries
    """

    def __init__(self):
        """Initialize the session analytics."""
        pass

    def get_session_summary(self, user) -> Dict[str, Any]:
        """
        Get comprehensive session summary for a user.

        Args:
            user: User object

        Returns:
            Dictionary with session summary
        """
        from .models import UserSession

        sessions = UserSession.objects.filter(user=user)
        active_sessions = sessions.filter(is_active=True)

        summary = {
            'total_sessions': sessions.count(),
            'active_sessions': active_sessions.count(),
            'devices': self._get_device_summary(sessions),
            'locations': self._get_location_summary(sessions),
            'security_events': self._get_security_summary(user),
            'activity_pattern': self._get_activity_pattern(sessions)
        }

        return summary

    def _get_device_summary(self, sessions) -> Dict[str, Any]:
        """
        Get device usage summary.

        Args:
            sessions: QuerySet of user sessions

        Returns:
            Dictionary with device summary
        """
        device_types = {}
        unique_devices = set()

        for session in sessions:
            # Count unique device fingerprints
            unique_devices.add(session.device_fingerprint)

            # Parse device type from user agent if available
            if session.user_agent:
                fingerprinter = DeviceFingerprinter()
                device_info = fingerprinter.parse_device_info(
                    session.user_agent)
                device_type = device_info.get('device_type', 'unknown')
                device_types[device_type] = device_types.get(
                    device_type, 0) + 1

        return {
            'unique_devices_count': len(unique_devices),
            'device_type_breakdown': device_types,
            'most_used_device_type': max(device_types.items(), key=lambda x: x[1])[0] if device_types else None
        }

    def _get_location_summary(self, sessions) -> Dict[str, Any]:
        """
        Get location usage summary.

        Args:
            sessions: QuerySet of user sessions

        Returns:
            Dictionary with location summary
        """
        unique_ips = set(sessions.values_list('ip_address', flat=True))

        # Group by IP address for frequency analysis
        ip_frequency = {}
        for session in sessions:
            ip = session.ip_address
            ip_frequency[ip] = ip_frequency.get(ip, 0) + 1

        return {
            'unique_locations_count': len(unique_ips),
            'most_frequent_ip': max(ip_frequency.items(), key=lambda x: x[1])[0] if ip_frequency else None,
            'location_diversity': len(unique_ips) / max(sessions.count(), 1)
        }

    def _get_security_summary(self, user) -> Dict[str, Any]:
        """
        Get security events summary.

        Args:
            user: User object

        Returns:
            Dictionary with security summary
        """
        from .models import AuditLog

        security_events = AuditLog.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        )

        return {
            'total_security_events': security_events.count(),
            'high_risk_events': security_events.filter(risk_level='high').count(),
            'failed_logins': security_events.filter(event_type='login_failed').count(),
            'password_changes': security_events.filter(event_type='password_changed').count()
        }

    def _get_activity_pattern(self, sessions) -> Dict[str, Any]:
        """
        Get user activity pattern analysis.

        Args:
            sessions: QuerySet of user sessions

        Returns:
            Dictionary with activity pattern
        """
        if not sessions.exists():
            return {
                'most_active_hour': None,
                'session_duration_avg': 0,
                'login_frequency': 0
            }

        # Analyze session creation times
        session_hours = []
        for session in sessions:
            session_hours.append(session.created_at.hour)

        # Find most active hour
        hour_frequency = {}
        for hour in session_hours:
            hour_frequency[hour] = hour_frequency.get(hour, 0) + 1

        most_active_hour = max(hour_frequency.items(), key=lambda x: x[1])[
            0] if hour_frequency else None

        # Calculate average session duration (simplified)
        active_sessions = sessions.filter(is_active=True)
        if active_sessions.exists():
            total_duration = sum(
                (timezone.now() - session.created_at).total_seconds()
                for session in active_sessions
            )
            avg_duration = total_duration / active_sessions.count()
        else:
            avg_duration = 0

        # Calculate login frequency (sessions per week)
        recent_sessions = sessions.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        return {
            'most_active_hour': most_active_hour,
            'session_duration_avg': avg_duration / 3600,  # Convert to hours
            'login_frequency': recent_sessions
        }


# Utility instances for easy import
device_fingerprinter = DeviceFingerprinter()
session_security_monitor = SessionSecurityMonitor()
session_analytics = SessionAnalytics()


def analyze_new_session(user, request, existing_sessions=None):
    """
    Convenience function to analyze a new session.

    Args:
        user: User object
        request: Django request object
        existing_sessions: Optional QuerySet of existing sessions

    Returns:
        Dictionary with session analysis
    """
    if existing_sessions is None:
        from .models import UserSession
        existing_sessions = UserSession.objects.filter(user=user)

    return session_security_monitor.analyze_session_security(user, request, existing_sessions)


def get_device_info(user_agent: str) -> Dict[str, Any]:
    """
    Convenience function to get device information.

    Args:
        user_agent: User agent string

    Returns:
        Dictionary with device information
    """
    return device_fingerprinter.parse_device_info(user_agent)


def generate_device_fingerprint(request) -> str:
    """
    Convenience function to generate device fingerprint.

    Args:
        request: Django request object

    Returns:
        Device fingerprint string
    """
    return device_fingerprinter.generate_fingerprint(request)


# Alias for backwards compatibility
get_device_fingerprint = generate_device_fingerprint


def is_suspicious_user_agent(user_agent: str) -> bool:
    """
    Check if user agent appears suspicious.

    Args:
        user_agent: User agent string to check

    Returns:
        True if user agent appears suspicious
    """
    return device_fingerprinter.is_suspicious(user_agent)


def detect_session_anomalies(request, user) -> List[str]:
    """
    Detect potential session anomalies.

    Args:
        request: Django request object
        user: User object

    Returns:
        List of detected anomalies
    """
    anomalies = []

    # Check for suspicious user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    if is_suspicious_user_agent(user_agent):
        anomalies.append('suspicious_user_agent')

    # Check for rapid requests (basic rate limiting check)
    client_ip = request.META.get('REMOTE_ADDR', '')
    # Add more anomaly detection logic as needed

    return anomalies


def calculate_session_risk_score(request, user) -> int:
    """
    Calculate a risk score for the session.

    Args:
        request: Django request object
        user: User object

    Returns:
        Risk score (0-100, higher is riskier)
    """
    score = 0

    # Check for anomalies
    anomalies = detect_session_anomalies(request, user)
    score += len(anomalies) * 20

    # Add more risk factors as needed

    return min(score, 100)


def get_session_summary(request, user) -> Dict[str, Any]:
    """
    Get a summary of session information.

    Args:
        request: Django request object
        user: User object

    Returns:
        Dictionary with session summary
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    device_info = get_device_info(user_agent)

    return {
        'device_info': device_info,
        'fingerprint': get_device_fingerprint(request),
        'risk_score': calculate_session_risk_score(request, user),
        'anomalies': detect_session_anomalies(request, user),
        'client_ip': request.META.get('REMOTE_ADDR', ''),
        'user_agent': user_agent,
    }
