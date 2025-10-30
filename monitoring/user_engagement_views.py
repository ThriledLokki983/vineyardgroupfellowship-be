"""
User Engagement Analytics for Phase 5

Comprehensive user behavior analysis providing:
- Individual user engagement patterns and trends
- Retention metrics and lifecycle analysis
- Personalized insights for community participation
- User journey mapping and optimization recommendations
"""

from django.db import models
from django.db.models import Count, Q, Avg, F, Sum, Max, Min
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict, Counter
import statistics

from groups.models import Group, GroupMembership, DiscussionTopic, Comment
from authentication.models import User

logger = logging.getLogger('user_engagement')


class UserEngagementAnalyticsService:
    """
    Service for comprehensive user engagement analytics and behavior analysis.
    """

    def __init__(self):
        self.cache_timeout = 300  # 5 minutes

    def get_engagement_dashboard(self, days: int = 30) -> Dict:
        """
        Get comprehensive user engagement analytics dashboard.

        Args:
            days: Number of days to analyze

        Returns:
            Complete user engagement analytics data
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        dashboard_data = {
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'user_metrics': self._get_user_metrics_overview(cutoff_date),
            'engagement_patterns': self._analyze_engagement_patterns(cutoff_date),
            'retention_analysis': self._analyze_user_retention(cutoff_date),
            'user_lifecycle': self._analyze_user_lifecycle(cutoff_date),
            'participation_trends': self._analyze_participation_trends(cutoff_date),
            'user_segments': self._segment_users_by_engagement(cutoff_date),
            'behavioral_insights': self._generate_behavioral_insights(cutoff_date),
            'recommendations': self._generate_engagement_recommendations(cutoff_date)
        }

        return dashboard_data

    def get_individual_user_analytics(self, user_id: int, days: int = 90) -> Dict:
        """
        Get detailed analytics for a specific user.

        Args:
            user_id: User ID to analyze
            days: Number of days to analyze

        Returns:
            Individual user analytics data
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {'error': 'User not found'}

        cutoff_date = timezone.now() - timedelta(days=days)

        user_data = {
            'user_id': user_id,
            'username': user.username,
            'account_age_days': (timezone.now() - user.date_joined).days,
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'activity_summary': self._get_user_activity_summary(user, cutoff_date),
            'engagement_trends': self._get_user_engagement_trends(user, cutoff_date),
            'social_metrics': self._get_user_social_metrics(user, cutoff_date),
            'content_analysis': self._analyze_user_content(user, cutoff_date),
            'group_participation': self._analyze_user_group_participation(user, cutoff_date),
            'behavioral_patterns': self._identify_user_behavioral_patterns(user, cutoff_date),
            'recommendations': self._generate_user_recommendations(user, cutoff_date)
        }

        return user_data

    def _get_user_metrics_overview(self, cutoff_date: datetime) -> Dict:
        """Get high-level user metrics overview."""
        # Total users and activity
        total_users = User.objects.count()
        active_users = User.objects.filter(
            Q(comments__created_at__gte=cutoff_date) |
            Q(discussion_topics__created_at__gte=cutoff_date)
        ).distinct().count()

        # New user registrations
        new_users = User.objects.filter(date_joined__gte=cutoff_date).count()

        # User activity distribution
        user_activity = User.objects.annotate(
            discussion_count=Count('discussion_topics', filter=Q(
                discussion_topics__created_at__gte=cutoff_date)),
            comment_count=Count('comments', filter=Q(
                comments__created_at__gte=cutoff_date)),
            total_activity=F('discussion_count') + F('comment_count')
        ).filter(total_activity__gt=0)

        # Calculate engagement levels
        very_active_users = user_activity.filter(
            total_activity__gte=20).count()
        moderately_active_users = user_activity.filter(
            total_activity__gte=5, total_activity__lt=20).count()
        lightly_active_users = user_activity.filter(
            total_activity__gte=1, total_activity__lt=5).count()

        # Average activity per user
        avg_discussions_per_user = user_activity.aggregate(
            avg=Avg('discussion_count'))['avg'] or 0
        avg_comments_per_user = user_activity.aggregate(
            avg=Avg('comment_count'))['avg'] or 0

        # Daily active users
        daily_active_users = self._calculate_daily_active_users(cutoff_date)

        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users': new_users,
            'activity_rate': round(active_users / max(total_users, 1) * 100, 2),
            'engagement_levels': {
                'very_active': very_active_users,
                'moderately_active': moderately_active_users,
                'lightly_active': lightly_active_users,
                'inactive': total_users - active_users
            },
            'average_activity': {
                'discussions_per_user': round(avg_discussions_per_user, 2),
                'comments_per_user': round(avg_comments_per_user, 2)
            },
            'daily_active_users': daily_active_users
        }

    def _analyze_engagement_patterns(self, cutoff_date: datetime) -> Dict:
        """Analyze user engagement patterns and behaviors."""
        # Time-based engagement patterns
        hourly_activity = self._analyze_hourly_activity_patterns(cutoff_date)
        daily_activity = self._analyze_daily_activity_patterns(cutoff_date)
        weekly_trends = self._analyze_weekly_engagement_trends(cutoff_date)

        # Session patterns
        session_analysis = self._analyze_user_session_patterns(cutoff_date)

        # Content interaction patterns
        content_patterns = self._analyze_content_interaction_patterns(
            cutoff_date)

        return {
            'time_patterns': {
                'hourly_activity': hourly_activity,
                'daily_activity': daily_activity,
                'weekly_trends': weekly_trends
            },
            'session_patterns': session_analysis,
            'content_patterns': content_patterns,
            'engagement_quality': self._calculate_engagement_quality(cutoff_date)
        }

    def _analyze_user_retention(self, cutoff_date: datetime) -> Dict:
        """Analyze user retention metrics and cohorts."""
        # Cohort analysis by registration month
        cohorts = self._perform_cohort_analysis()

        # Retention rates
        retention_rates = self._calculate_retention_rates(cutoff_date)

        # Churn analysis
        churn_analysis = self._analyze_user_churn(cutoff_date)

        # Lifecycle stage distribution
        lifecycle_stages = self._analyze_user_lifecycle_stages()

        return {
            'cohort_analysis': cohorts,
            'retention_rates': retention_rates,
            'churn_analysis': churn_analysis,
            'lifecycle_stages': lifecycle_stages,
            'retention_insights': self._generate_retention_insights(retention_rates, churn_analysis)
        }

    def _analyze_user_lifecycle(self, cutoff_date: datetime) -> Dict:
        """Analyze user lifecycle stages and progression."""
        # Define lifecycle stages
        lifecycle_stages = {
            'new_user': {'days': 7, 'min_activity': 0},
            'engaged_newcomer': {'days': 30, 'min_activity': 5},
            'regular_member': {'days': 90, 'min_activity': 15},
            'power_user': {'days': 365, 'min_activity': 50},
            'veteran_member': {'days': 999999, 'min_activity': 100}
        }

        stage_distribution = {}
        stage_transitions = {}

        for stage_name, criteria in lifecycle_stages.items():
            users_in_stage = self._count_users_in_lifecycle_stage(
                stage_name, criteria, cutoff_date)
            stage_distribution[stage_name] = users_in_stage

        # Analyze progression between stages
        progression_analysis = self._analyze_lifecycle_progression(cutoff_date)

        return {
            'stage_distribution': stage_distribution,
            'progression_analysis': progression_analysis,
            'average_progression_time': self._calculate_average_progression_time(),
            'stage_characteristics': self._analyze_stage_characteristics(cutoff_date)
        }

    def _analyze_participation_trends(self, cutoff_date: datetime) -> Dict:
        """Analyze trends in user participation over time."""
        # Daily participation trends
        daily_trends = []
        current_date = cutoff_date.date()
        end_date = timezone.now().date()

        while current_date <= end_date:
            day_start = timezone.make_aware(
                datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            # Count active users and activity for this day
            active_users_count = User.objects.filter(
                Q(comments__created_at__gte=day_start, comments__created_at__lt=day_end) |
                Q(discussion_topics__created_at__gte=day_start,
                  discussion_topics__created_at__lt=day_end)
            ).distinct().count()

            discussions_count = DiscussionTopic.objects.filter(
                created_at__gte=day_start, created_at__lt=day_end
            ).count()

            comments_count = Comment.objects.filter(
                created_at__gte=day_start, created_at__lt=day_end
            ).count()

            daily_trends.append({
                'date': current_date.isoformat(),
                'active_users': active_users_count,
                'discussions': discussions_count,
                'comments': comments_count,
                'total_activity': discussions_count + comments_count
            })

            current_date += timedelta(days=1)

        # Weekly aggregation
        weekly_trends = self._aggregate_weekly_trends(daily_trends)

        # Trend analysis
        trend_direction = self._calculate_trend_direction(
            daily_trends[-7:] if len(daily_trends) >= 7 else daily_trends)

        return {
            'daily_trends': daily_trends,
            'weekly_trends': weekly_trends,
            'trend_direction': trend_direction,
            'participation_insights': self._generate_participation_insights(daily_trends)
        }

    def _segment_users_by_engagement(self, cutoff_date: datetime) -> Dict:
        """Segment users based on engagement levels and behaviors."""
        # RFM-style segmentation (Recency, Frequency, Monetary value -> adapted for community)
        # Recency: How recently they were active
        # Frequency: How often they participate
        # Magnitude: How much they contribute (content quality/quantity)

        user_segments = {
            'champions': [],      # High frequency, recent activity, high contribution
            'loyal_members': [],  # High frequency, consistent activity
            'potential_loyalists': [],  # Recent joiners with good activity
            'new_members': [],    # Recently joined, low activity
            'at_risk': [],        # Previously active, now declining
            'dormant': [],        # Low activity, old users
            'lost': []           # No recent activity
        }

        # Analyze each user's engagement pattern
        users_with_activity = User.objects.annotate(
            recent_activity=Count('comments', filter=Q(
                comments__created_at__gte=cutoff_date)),
            total_discussions=Count('discussion_topics'),
            total_comments=Count('comments'),
            last_activity=Max('comments__created_at')
        )

        for user in users_with_activity:
            segment = self._classify_user_segment(user, cutoff_date)
            if segment in user_segments:
                user_segments[segment].append({
                    'user_id': user.id,
                    'username': user.username,
                    'recent_activity': user.recent_activity,
                    'total_activity': (user.total_discussions or 0) + (user.total_comments or 0),
                    'account_age_days': (timezone.now() - user.date_joined).days,
                    'last_activity': user.last_activity.isoformat() if user.last_activity else None
                })

        # Calculate segment statistics
        segment_stats = {}
        total_users = sum(len(segment) for segment in user_segments.values())

        for segment_name, users in user_segments.items():
            segment_stats[segment_name] = {
                'count': len(users),
                'percentage': round(len(users) / max(total_users, 1) * 100, 2),
                'top_users': sorted(users, key=lambda x: x['total_activity'], reverse=True)[:5]
            }

        return {
            'segments': user_segments,
            'segment_statistics': segment_stats,
            'segmentation_insights': self._generate_segmentation_insights(segment_stats)
        }

    def _generate_behavioral_insights(self, cutoff_date: datetime) -> Dict:
        """Generate insights about user behavior patterns."""
        insights = []

        # Analyze posting patterns
        posting_insights = self._analyze_posting_behavior_insights(cutoff_date)
        insights.extend(posting_insights)

        # Analyze interaction patterns
        interaction_insights = self._analyze_interaction_behavior_insights(
            cutoff_date)
        insights.extend(interaction_insights)

        # Analyze group participation patterns
        group_insights = self._analyze_group_participation_insights(
            cutoff_date)
        insights.extend(group_insights)

        # Analyze user onboarding effectiveness
        onboarding_insights = self._analyze_onboarding_effectiveness(
            cutoff_date)
        insights.extend(onboarding_insights)

        return {
            'insights': insights,
            'key_findings': self._extract_key_behavioral_findings(insights),
            'behavior_recommendations': self._generate_behavior_recommendations(insights)
        }

    def _generate_engagement_recommendations(self, cutoff_date: datetime) -> List[Dict]:
        """Generate actionable recommendations to improve user engagement."""
        recommendations = []

        # Analyze current engagement state
        user_metrics = self._get_user_metrics_overview(cutoff_date)
        retention_data = self._analyze_user_retention(cutoff_date)
        segments = self._segment_users_by_engagement(cutoff_date)

        # Low activity rate recommendation
        if user_metrics['activity_rate'] < 30:
            recommendations.append({
                'type': 'activity_improvement',
                'priority': 'high',
                'title': 'Improve Overall User Activity',
                'description': f"Only {user_metrics['activity_rate']:.1f}% of users are active",
                'target_segments': ['dormant', 'new_members'],
                'actions': [
                    'Implement personalized onboarding flow',
                    'Create engagement challenges or goals',
                    'Send targeted re-engagement notifications',
                    'Improve content discovery mechanisms'
                ],
                'expected_impact': 'Increase activity rate by 10-15%',
                'metrics_to_track': ['daily_active_users', 'activity_rate', 'new_user_retention']
            })

        # High at-risk user count
        at_risk_percentage = segments['segment_statistics']['at_risk']['percentage']
        if at_risk_percentage > 15:
            recommendations.append({
                'type': 'retention_improvement',
                'priority': 'high',
                'title': 'Address At-Risk User Segment',
                'description': f"{at_risk_percentage:.1f}% of users are at risk of churning",
                'target_segments': ['at_risk'],
                'actions': [
                    'Implement win-back campaigns',
                    'Analyze reasons for declining engagement',
                    'Provide personalized content recommendations',
                    'Create re-engagement incentives'
                ],
                'expected_impact': 'Reduce churn rate by 20-30%',
                'metrics_to_track': ['churn_rate', 'at_risk_conversion', 'user_retention']
            })

        # Low new user retention
        new_user_segment = segments['segment_statistics']['new_members']['percentage']
        if new_user_segment > 40:  # High percentage of users stuck in new member stage
            recommendations.append({
                'type': 'onboarding_optimization',
                'priority': 'medium',
                'title': 'Optimize New User Onboarding',
                'description': f"{new_user_segment:.1f}% of users remain in new member stage",
                'target_segments': ['new_members'],
                'actions': [
                    'Redesign onboarding flow',
                    'Implement mentorship program',
                    'Create guided first-week experience',
                    'Provide clearer value proposition'
                ],
                'expected_impact': 'Improve new user progression by 25-35%',
                'metrics_to_track': ['onboarding_completion', 'new_user_activity', 'progression_rate']
            })

        # Engagement quality issues
        champions_percentage = segments['segment_statistics']['champions']['percentage']
        if champions_percentage < 5:  # Low percentage of highly engaged users
            recommendations.append({
                'type': 'engagement_quality',
                'priority': 'medium',
                'title': 'Cultivate More Champion Users',
                'description': f"Only {champions_percentage:.1f}% of users are champions",
                'target_segments': ['loyal_members', 'potential_loyalists'],
                'actions': [
                    'Recognize and reward top contributors',
                    'Create leadership opportunities',
                    'Implement community ambassador program',
                    'Provide advanced features for power users'
                ],
                'expected_impact': 'Increase champion percentage to 8-10%',
                'metrics_to_track': ['champion_growth', 'user_progression', 'content_quality']
            })

        return recommendations

    # Helper methods for user activity analysis

    def _calculate_daily_active_users(self, cutoff_date: datetime) -> List[Dict]:
        """Calculate daily active user counts."""
        daily_active = []
        current_date = cutoff_date.date()
        end_date = timezone.now().date()

        while current_date <= end_date:
            day_start = timezone.make_aware(
                datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            active_count = User.objects.filter(
                Q(comments__created_at__gte=day_start, comments__created_at__lt=day_end) |
                Q(discussion_topics__created_at__gte=day_start,
                  discussion_topics__created_at__lt=day_end)
            ).distinct().count()

            daily_active.append({
                'date': current_date.isoformat(),
                'active_users': active_count
            })

            current_date += timedelta(days=1)

        return daily_active

    def _analyze_hourly_activity_patterns(self, cutoff_date: datetime) -> Dict:
        """Analyze activity patterns by hour of day."""
        # This would analyze posting times to understand when users are most active
        # Simplified implementation for demonstration
        hourly_activity = defaultdict(int)

        comments = Comment.objects.filter(created_at__gte=cutoff_date)
        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)

        for comment in comments:
            hour = comment.created_at.hour
            hourly_activity[hour] += 1

        for discussion in discussions:
            hour = discussion.created_at.hour
            hourly_activity[hour] += 1

        # Convert to list format
        hourly_data = [{'hour': hour, 'activity': hourly_activity[hour]}
                       for hour in range(24)]

        return {
            'hourly_distribution': hourly_data,
            'peak_hours': sorted(hourly_data, key=lambda x: x['activity'], reverse=True)[:3],
            'insights': self._generate_hourly_insights(hourly_data)
        }

    def _analyze_daily_activity_patterns(self, cutoff_date: datetime) -> Dict:
        """Analyze activity patterns by day of week."""
        daily_activity = defaultdict(int)

        comments = Comment.objects.filter(created_at__gte=cutoff_date)
        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)

        for comment in comments:
            day = comment.created_at.strftime('%A')
            daily_activity[day] += 1

        for discussion in discussions:
            day = discussion.created_at.strftime('%A')
            daily_activity[day] += 1

        days_order = ['Monday', 'Tuesday', 'Wednesday',
                      'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_data = [{'day': day, 'activity': daily_activity[day]}
                      for day in days_order]

        return {
            'daily_distribution': daily_data,
            'most_active_days': sorted(daily_data, key=lambda x: x['activity'], reverse=True)[:3],
            'insights': self._generate_daily_insights(daily_data)
        }

    def _analyze_weekly_engagement_trends(self, cutoff_date: datetime) -> Dict:
        """Analyze weekly engagement trends."""
        weekly_data = []

        # Group data by week
        current_date = cutoff_date.date()
        end_date = timezone.now().date()

        while current_date <= end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
            week_end = week_start + timedelta(days=6)

            if week_end > end_date:
                break

            week_start_dt = timezone.make_aware(
                datetime.combine(week_start, datetime.min.time()))
            week_end_dt = timezone.make_aware(
                datetime.combine(week_end, datetime.max.time()))

            weekly_activity = DiscussionTopic.objects.filter(
                created_at__gte=week_start_dt, created_at__lte=week_end_dt
            ).count() + Comment.objects.filter(
                created_at__gte=week_start_dt, created_at__lte=week_end_dt
            ).count()

            weekly_users = User.objects.filter(
                Q(comments__created_at__gte=week_start_dt, comments__created_at__lte=week_end_dt) |
                Q(discussion_topics__created_at__gte=week_start_dt,
                  discussion_topics__created_at__lte=week_end_dt)
            ).distinct().count()

            weekly_data.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'total_activity': weekly_activity,
                'active_users': weekly_users,
                'avg_activity_per_user': round(weekly_activity / max(weekly_users, 1), 2)
            })

            current_date = week_end + timedelta(days=1)

        return {
            'weekly_trends': weekly_data,
            'trend_analysis': self._analyze_weekly_trend_direction(weekly_data)
        }

    def _perform_cohort_analysis(self) -> Dict:
        """Perform cohort analysis based on user registration month."""
        # Group users by registration month
        users_by_month = User.objects.extra(
            select={'month': "DATE_TRUNC('month', date_joined)"}
        ).values('month').annotate(
            user_count=Count('id')
        ).order_by('month')

        cohort_data = []
        for cohort in users_by_month:
            cohort_month = cohort['month']
            cohort_size = cohort['user_count']

            # Calculate retention for subsequent months
            retention_months = []
            for month_offset in range(1, 13):  # Track 12 months
                target_month = cohort_month + timedelta(days=30 * month_offset)

                retained_users = User.objects.filter(
                    date_joined__gte=cohort_month,
                    date_joined__lt=cohort_month + timedelta(days=30)
                ).filter(
                    Q(comments__created_at__gte=target_month) |
                    Q(discussion_topics__created_at__gte=target_month)
                ).distinct().count()

                retention_rate = round(
                    retained_users / max(cohort_size, 1) * 100, 2)
                retention_months.append({
                    'month': month_offset,
                    'retained_users': retained_users,
                    'retention_rate': retention_rate
                })

            cohort_data.append({
                'cohort_month': cohort_month.strftime('%Y-%m'),
                'cohort_size': cohort_size,
                'retention_by_month': retention_months
            })

        return {
            'cohorts': cohort_data,
            'average_retention_rates': self._calculate_average_retention_rates(cohort_data)
        }

    def _calculate_retention_rates(self, cutoff_date: datetime) -> Dict:
        """Calculate various retention rate metrics."""
        # 1-day retention
        yesterday = timezone.now() - timedelta(days=1)
        users_joined_yesterday = User.objects.filter(
            date_joined__gte=yesterday - timedelta(days=1),
            date_joined__lt=yesterday
        )

        users_active_next_day = users_joined_yesterday.filter(
            Q(comments__created_at__gte=yesterday) |
            Q(discussion_topics__created_at__gte=yesterday)
        ).distinct().count()

        day_1_retention = round(
            users_active_next_day / max(users_joined_yesterday.count(), 1) * 100, 2)

        # 7-day retention
        week_ago = timezone.now() - timedelta(days=7)
        users_joined_week_ago = User.objects.filter(
            date_joined__gte=week_ago - timedelta(days=1),
            date_joined__lt=week_ago
        )

        users_active_in_week = users_joined_week_ago.filter(
            Q(comments__created_at__gte=week_ago) |
            Q(discussion_topics__created_at__gte=week_ago)
        ).distinct().count()

        day_7_retention = round(users_active_in_week /
                                max(users_joined_week_ago.count(), 1) * 100, 2)

        # 30-day retention
        month_ago = timezone.now() - timedelta(days=30)
        users_joined_month_ago = User.objects.filter(
            date_joined__gte=month_ago - timedelta(days=1),
            date_joined__lt=month_ago
        )

        users_active_in_month = users_joined_month_ago.filter(
            Q(comments__created_at__gte=month_ago) |
            Q(discussion_topics__created_at__gte=month_ago)
        ).distinct().count()

        day_30_retention = round(
            users_active_in_month / max(users_joined_month_ago.count(), 1) * 100, 2)

        return {
            'day_1_retention': day_1_retention,
            'day_7_retention': day_7_retention,
            'day_30_retention': day_30_retention,
            'retention_trend': self._calculate_retention_trend()
        }

    def _classify_user_segment(self, user, cutoff_date: datetime) -> str:
        """Classify a user into an engagement segment."""
        account_age = (timezone.now() - user.date_joined).days
        recent_activity = user.recent_activity or 0
        total_activity = (user.total_discussions or 0) + \
            (user.total_comments or 0)

        # Days since last activity
        days_since_last_activity = 999
        if user.last_activity:
            days_since_last_activity = (
                timezone.now() - user.last_activity).days

        # Classification logic
        if account_age <= 7:
            return 'new_members'
        elif recent_activity >= 20 and total_activity >= 50:
            return 'champions'
        elif recent_activity >= 10 and days_since_last_activity <= 7:
            return 'loyal_members'
        elif account_age <= 30 and recent_activity >= 5:
            return 'potential_loyalists'
        elif total_activity >= 10 and days_since_last_activity > 30:
            return 'at_risk'
        elif days_since_last_activity > 90:
            return 'lost'
        else:
            return 'dormant'

    # Additional helper methods would go here...
    # (Many more methods for detailed analysis - abbreviated for length)

    def _generate_hourly_insights(self, hourly_data: List[Dict]) -> List[str]:
        """Generate insights from hourly activity patterns."""
        insights = []

        # Find peak activity times
        peak_hour = max(hourly_data, key=lambda x: x['activity'])
        if peak_hour['activity'] > 0:
            insights.append(
                f"Peak activity occurs at {peak_hour['hour']}:00 with {peak_hour['activity']} actions")

        # Find quiet periods
        quiet_hours = [h for h in hourly_data if h['activity'] == 0]
        if quiet_hours:
            insights.append(
                f"No activity during {len(quiet_hours)} hours of the day")

        return insights

    def _generate_daily_insights(self, daily_data: List[Dict]) -> List[str]:
        """Generate insights from daily activity patterns."""
        insights = []

        most_active = max(daily_data, key=lambda x: x['activity'])
        least_active = min(daily_data, key=lambda x: x['activity'])

        insights.append(
            f"Most active day: {most_active['day']} ({most_active['activity']} actions)")
        insights.append(
            f"Least active day: {least_active['day']} ({least_active['activity']} actions)")

        return insights

    def _calculate_average_retention_rates(self, cohort_data: List[Dict]) -> Dict:
        """Calculate average retention rates across all cohorts."""
        if not cohort_data:
            return {}

        # Average retention by month
        avg_retention = {}
        for month in range(1, 13):
            month_rates = []
            for cohort in cohort_data:
                if len(cohort['retention_by_month']) >= month:
                    month_rates.append(
                        cohort['retention_by_month'][month-1]['retention_rate'])

            if month_rates:
                avg_retention[f'month_{month}'] = round(
                    statistics.mean(month_rates), 2)

        return avg_retention


class UserEngagementDetailView(APIView):
    """
    Detailed user engagement analytics view for admin users.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.engagement_service = UserEngagementAnalyticsService()

    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def get(self, request):
        """
        Get comprehensive user engagement analytics dashboard.
        """
        days = int(request.query_params.get('days', 30))

        try:
            dashboard_data = self.engagement_service.get_engagement_dashboard(
                days=days)
            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating user engagement dashboard: {e}")
            return Response({
                'error': 'Failed to generate user engagement dashboard',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IndividualUserAnalyticsView(APIView):
    """
    Individual user analytics view for detailed user analysis.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.engagement_service = UserEngagementAnalyticsService()

    def get(self, request, user_id):
        """
        Get detailed analytics for a specific user.
        """
        days = int(request.query_params.get('days', 90))

        try:
            user_data = self.engagement_service.get_individual_user_analytics(
                user_id=user_id, days=days)

            if 'error' in user_data:
                return Response(user_data, status=status.HTTP_404_NOT_FOUND)

            return Response(user_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error generating individual user analytics for user {user_id}: {e}")
            return Response({
                'error': 'Failed to generate user analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserRetentionAnalyticsView(APIView):
    """
    User retention and cohort analysis view.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.engagement_service = UserEngagementAnalyticsService()

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        """
        Get comprehensive user retention analytics.
        """
        days = int(request.query_params.get('days', 90))

        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            retention_data = self.engagement_service._analyze_user_retention(
                cutoff_date)

            return Response(retention_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating retention analytics: {e}")
            return Response({
                'error': 'Failed to generate retention analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
