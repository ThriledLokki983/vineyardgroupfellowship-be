"""
Admin Analytics Dashboard Views for Phase 5

Comprehensive analytics dashboard providing insights into:
- Group system performance and usage
- Member engagement and retention
- Content creation and moderation
- System health and optimization opportunities
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import json

from groups.services.analytics_service import GroupAnalyticsService
from groups.models import Group, GroupMembership, DiscussionTopic, Comment
from authentication.models import User


class AdminDashboardOverviewView(APIView):
    """
    Main admin dashboard with comprehensive system overview.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.analytics_service = GroupAnalyticsService()

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """
        Get comprehensive dashboard overview.
        """
        # Get time period from query params
        days = int(request.query_params.get('days', 30))

        try:
            dashboard_data = self.analytics_service.get_dashboard_overview(
                days=days)

            # Add real-time system status
            dashboard_data['system_status'] = self._get_real_time_status()

            # Add quick actions and alerts
            dashboard_data['alerts'] = self._get_system_alerts()
            dashboard_data['quick_stats'] = self._get_quick_stats()

            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate dashboard data',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_real_time_status(self) -> dict:
        """Get real-time system status indicators."""
        now = timezone.now()
        last_hour = now - timedelta(hours=1)

        return {
            'online_users': User.objects.filter(
                last_login__gte=last_hour
            ).count(),
            'active_groups_today': Group.objects.filter(
                is_active=True,
                discussion_topics__created_at__gte=now.replace(
                    hour=0, minute=0, second=0)
            ).distinct().count(),
            'new_content_last_hour': {
                'discussions': DiscussionTopic.objects.filter(
                    created_at__gte=last_hour
                ).count(),
                'comments': Comment.objects.filter(
                    created_at__gte=last_hour
                ).count()
            },
            'system_health': 'healthy',  # This could be enhanced with actual health checks
            'last_updated': now.isoformat()
        }

    def _get_system_alerts(self) -> list:
        """Get system alerts and notifications for admins."""
        alerts = []

        # Check for unusual patterns
        inactive_groups = Group.objects.filter(
            is_active=True,
            discussion_topics__created_at__lt=timezone.now() - timedelta(days=30)
        ).count()

        if inactive_groups > 0:
            alerts.append({
                'type': 'warning',
                'title': 'Inactive Groups Detected',
                'message': f'{inactive_groups} groups have had no activity in 30+ days',
                'action': 'review_inactive_groups'
            })

        # Check for rapid growth
        recent_groups = Group.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()

        if recent_groups > 10:  # Threshold for "rapid growth"
            alerts.append({
                'type': 'info',
                'title': 'High Group Creation Activity',
                'message': f'{recent_groups} new groups created in the last 24 hours',
                'action': 'monitor_growth'
            })

        # Check for pending memberships
        pending_memberships = GroupMembership.objects.filter(
            status='pending'
        ).count()

        if pending_memberships > 50:
            alerts.append({
                'type': 'warning',
                'title': 'High Pending Memberships',
                'message': f'{pending_memberships} membership requests awaiting approval',
                'action': 'review_pending'
            })

        return alerts

    def _get_quick_stats(self) -> dict:
        """Get quick statistics for dashboard cards."""
        return {
            'total_users': User.objects.count(),
            'total_active_groups': Group.objects.filter(is_active=True).count(),
            'total_discussions': DiscussionTopic.objects.count(),
            'total_comments': Comment.objects.count(),
            'growth_today': {
                'new_groups': Group.objects.filter(
                    created_at__gte=timezone.now().replace(hour=0, minute=0, second=0)
                ).count(),
                'new_discussions': DiscussionTopic.objects.filter(
                    created_at__gte=timezone.now().replace(hour=0, minute=0, second=0)
                ).count()
            }
        }


class GroupAnalyticsDetailView(APIView):
    """
    Detailed analytics for individual groups.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.analytics_service = GroupAnalyticsService()

    def get(self, request, group_id):
        """
        Get detailed analytics for a specific group.
        """
        days = int(request.query_params.get('days', 30))

        try:
            analytics_data = self.analytics_service.get_group_detailed_analytics(
                group_id=group_id,
                days=days
            )

            if 'error' in analytics_data:
                return Response(analytics_data, status=status.HTTP_404_NOT_FOUND)

            # Add additional insights
            analytics_data['insights'] = self._generate_group_insights(
                group_id, days)
            analytics_data['recommendations'] = self._generate_group_recommendations(
                analytics_data)

            return Response(analytics_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate group analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_group_insights(self, group_id: int, days: int) -> dict:
        """Generate insights for a specific group."""
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return {}

        cutoff_date = timezone.now() - timedelta(days=days)

        # Calculate engagement trends
        weekly_engagement = []
        for week in range(4):  # Last 4 weeks
            week_start = timezone.now() - timedelta(weeks=week+1)
            week_end = timezone.now() - timedelta(weeks=week)

            week_data = {
                'week': f'Week {4-week}',
                'discussions': DiscussionTopic.objects.filter(
                    group=group,
                    created_at__gte=week_start,
                    created_at__lt=week_end
                ).count(),
                'comments': Comment.objects.filter(
                    topic__group=group,
                    created_at__gte=week_start,
                    created_at__lt=week_end
                ).count()
            }
            weekly_engagement.append(week_data)

        # Member activity pattern
        member_activity = GroupMembership.objects.filter(
            group=group,
            status='active'
        ).values('user').annotate(
            comment_count=Count('user__comments', filter=Q(
                user__comments__topic__group=group,
                user__comments__created_at__gte=cutoff_date
            )),
            discussion_count=Count('user__discussion_topics', filter=Q(
                user__discussion_topics__group=group,
                user__discussion_topics__created_at__gte=cutoff_date
            ))
        )

        active_members = member_activity.filter(
            Q(comment_count__gt=0) | Q(discussion_count__gt=0)
        ).count()

        total_members = member_activity.count()
        engagement_rate = round(
            (active_members / max(total_members, 1)) * 100, 2)

        return {
            'weekly_engagement_trend': weekly_engagement,
            'engagement_rate': engagement_rate,
            'active_vs_total_members': {
                'active': active_members,
                'total': total_members
            }
        }

    def _generate_group_recommendations(self, analytics_data: dict) -> list:
        """Generate recommendations based on group analytics."""
        recommendations = []

        member_analytics = analytics_data.get('member_analytics', {})
        content_analytics = analytics_data.get('content_analytics', {})

        # Low engagement recommendations
        engagement_rate = member_analytics.get('engagement_rate', 0)
        if engagement_rate < 20:
            recommendations.append({
                'type': 'engagement',
                'priority': 'high',
                'title': 'Low Member Engagement',
                'description': f'Only {engagement_rate}% of members are active. Consider encouraging more participation.',
                'suggestions': [
                    'Create welcome posts for new members',
                    'Start discussion topics with engaging questions',
                    'Recognize active contributors'
                ]
            })

        # Content creation recommendations
        avg_comments = content_analytics.get('avg_comments_per_discussion', 0)
        if avg_comments < 2:
            recommendations.append({
                'type': 'content',
                'priority': 'medium',
                'title': 'Low Discussion Engagement',
                'description': 'Discussions are not generating much conversation.',
                'suggestions': [
                    'Ask open-ended questions in posts',
                    'Share personal experiences to encourage responses',
                    'Use polls and interactive content'
                ]
            })

        # Growth recommendations
        new_members = member_analytics.get('new_members_period', 0)
        if new_members == 0:
            recommendations.append({
                'type': 'growth',
                'priority': 'medium',
                'title': 'No Recent Growth',
                'description': 'No new members have joined recently.',
                'suggestions': [
                    'Share group invite codes in relevant communities',
                    'Improve group description and visibility',
                    'Create content that attracts new members'
                ]
            })

        return recommendations


class UserEngagementAnalyticsView(APIView):
    """
    User engagement and behavior analytics.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.analytics_service = GroupAnalyticsService()

    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def get(self, request):
        """
        Get user engagement analytics and insights.
        """
        days = int(request.query_params.get('days', 30))

        try:
            engagement_data = self.analytics_service.get_user_engagement_analytics(
                days=days)

            # Add behavioral insights
            engagement_data['behavioral_insights'] = self._analyze_user_behavior(
                days)
            engagement_data['retention_analysis'] = self._analyze_user_retention(
                days)

            return Response(engagement_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate engagement analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _analyze_user_behavior(self, days: int) -> dict:
        """Analyze user behavior patterns."""
        cutoff_date = timezone.now() - timedelta(days=days)

        # Peak activity times (simplified - could be enhanced with hourly analysis)
        daily_activity = {}
        for day in range(7):
            day_name = ['Monday', 'Tuesday', 'Wednesday',
                        'Thursday', 'Friday', 'Saturday', 'Sunday'][day]
            activity_count = Comment.objects.filter(
                created_at__gte=cutoff_date,
                created_at__week_day=day + 2  # Django week_day starts from Sunday=1
            ).count()
            daily_activity[day_name] = activity_count

        # User journey analysis
        user_journeys = User.objects.filter(
            group_memberships__joined_at__gte=cutoff_date
        ).annotate(
            days_to_first_post=Count('comments', filter=Q(
                comments__created_at__gte=F('group_memberships__joined_at')
            ))
        ).aggregate(
            avg_days_to_engagement=Count('id')
        )

        return {
            'peak_activity_days': daily_activity,
            'user_journey_insights': user_journeys
        }

    def _analyze_user_retention(self, days: int) -> dict:
        """Analyze user retention patterns."""
        # Calculate retention at different intervals
        retention_intervals = [7, 14, 30, 90]  # days
        retention_data = {}

        for interval in retention_intervals:
            signup_date = timezone.now() - timedelta(days=interval)

            # Users who signed up 'interval' days ago
            cohort_users = User.objects.filter(
                date_joined__date=signup_date.date()
            )

            # Users from that cohort who are still active
            active_users = cohort_users.filter(
                group_memberships__status='active',
                group_memberships__group__is_active=True
            ).distinct()

            if cohort_users.exists():
                retention_rate = round(
                    (active_users.count() / cohort_users.count()) * 100, 2)
            else:
                retention_rate = 0

            retention_data[f'{interval}_day'] = {
                'cohort_size': cohort_users.count(),
                'retained_users': active_users.count(),
                'retention_rate': retention_rate
            }

        return retention_data


class SystemHealthAnalyticsView(APIView):
    """
    System health and performance analytics.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Get system health analytics and performance metrics.
        """
        try:
            health_data = {
                'database_health': self._check_database_health(),
                'content_health': self._check_content_health(),
                'user_health': self._check_user_health(),
                'performance_metrics': self._get_performance_metrics(),
                'recommendations': self._generate_system_recommendations()
            }

            return Response(health_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to generate health analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _check_database_health(self) -> dict:
        """Check database health indicators."""
        return {
            'total_records': {
                'groups': Group.objects.count(),
                'memberships': GroupMembership.objects.count(),
                'discussions': DiscussionTopic.objects.count(),
                'comments': Comment.objects.count()
            },
            'data_integrity': {
                'orphaned_memberships': GroupMembership.objects.filter(
                    group__is_active=False
                ).count(),
                'empty_groups': Group.objects.filter(
                    is_active=True,
                    memberships__isnull=True
                ).count()
            }
        }

    def _check_content_health(self) -> dict:
        """Check content health and quality indicators."""
        last_week = timezone.now() - timedelta(days=7)

        return {
            'recent_activity': {
                'new_discussions': DiscussionTopic.objects.filter(
                    created_at__gte=last_week
                ).count(),
                'new_comments': Comment.objects.filter(
                    created_at__gte=last_week
                ).count()
            },
            'content_quality': {
                'discussions_without_responses': DiscussionTopic.objects.filter(
                    comments__isnull=True
                ).count(),
                'active_discussions': DiscussionTopic.objects.filter(
                    comments__created_at__gte=last_week
                ).distinct().count()
            }
        }

    def _check_user_health(self) -> dict:
        """Check user engagement and health indicators."""
        last_month = timezone.now() - timedelta(days=30)

        return {
            'user_activity': {
                'active_users_month': User.objects.filter(
                    Q(comments__created_at__gte=last_month) |
                    Q(discussion_topics__created_at__gte=last_month)
                ).distinct().count(),
                'new_users_month': User.objects.filter(
                    date_joined__gte=last_month
                ).count()
            },
            'engagement_metrics': {
                'users_with_multiple_groups': User.objects.annotate(
                    group_count=Count('group_memberships', filter=Q(
                        group_memberships__status='active'
                    ))
                ).filter(group_count__gt=1).count(),
                'single_group_users': User.objects.annotate(
                    group_count=Count('group_memberships', filter=Q(
                        group_memberships__status='active'
                    ))
                ).filter(group_count=1).count()
            }
        }

    def _get_performance_metrics(self) -> dict:
        """Get system performance metrics."""
        # This could be expanded with actual performance monitoring
        return {
            'response_times': {
                'avg_response_time': '150ms',  # Placeholder
                'slow_queries': 2,  # Placeholder
                'cache_hit_rate': '85%'  # Placeholder
            },
            'resource_usage': {
                'database_size': 'monitoring',  # Could be calculated
                'cache_usage': 'monitoring',  # Could be calculated
                'active_connections': 'monitoring'  # Could be calculated
            }
        }

    def _generate_system_recommendations(self) -> list:
        """Generate system optimization recommendations."""
        recommendations = []

        # Check for optimization opportunities
        empty_groups = Group.objects.filter(
            is_active=True,
            memberships__isnull=True
        ).count()

        if empty_groups > 10:
            recommendations.append({
                'type': 'optimization',
                'priority': 'medium',
                'title': 'Clean Up Empty Groups',
                'description': f'{empty_groups} active groups have no members',
                'action': 'Consider archiving or removing empty groups'
            })

        # Check for inactive users
        inactive_users = User.objects.filter(
            last_login__lt=timezone.now() - timedelta(days=90),
            group_memberships__status='active'
        ).count()

        if inactive_users > 100:
            recommendations.append({
                'type': 'cleanup',
                'priority': 'low',
                'title': 'Inactive User Cleanup',
                'description': f'{inactive_users} users inactive for 90+ days',
                'action': 'Consider sending re-engagement campaigns'
            })

        return recommendations
