"""
Group Health Analytics for Phase 5

Comprehensive group-specific health metrics providing:
- Group wellness indicators and member satisfaction analysis
- Discussion quality assessment and interaction patterns
- Group optimization recommendations and interventions
- Community dynamics and social network analysis
"""

from django.db import models
from django.db.models import Count, Q, Avg, F, Sum, Max, Min, StdDev
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
import math

from groups.models import Group, GroupMembership, DiscussionTopic, Comment
from authentication.models import User

logger = logging.getLogger('group_health')


class GroupHealthAnalyticsService:
    """
    Service for comprehensive group health analytics and wellness assessment.
    """

    def __init__(self):
        self.cache_timeout = 300  # 5 minutes

    def get_group_health_dashboard(self, days: int = 30) -> Dict:
        """
        Get comprehensive group health analytics dashboard.

        Args:
            days: Number of days to analyze

        Returns:
            Complete group health analytics data
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        dashboard_data = {
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'overall_health': self._get_overall_group_health_metrics(cutoff_date),
            'group_rankings': self._rank_groups_by_health(cutoff_date),
            'health_trends': self._analyze_group_health_trends(cutoff_date),
            'community_dynamics': self._analyze_community_dynamics(cutoff_date),
            'intervention_recommendations': self._generate_intervention_recommendations(cutoff_date),
            'success_stories': self._identify_success_stories(cutoff_date),
            'at_risk_groups': self._identify_at_risk_groups(cutoff_date)
        }

        return dashboard_data

    def get_individual_group_health(self, group_id: int, days: int = 60) -> Dict:
        """
        Get detailed health analytics for a specific group.

        Args:
            group_id: Group ID to analyze
            days: Number of days to analyze

        Returns:
            Individual group health analytics data
        """
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return {'error': 'Group not found'}

        cutoff_date = timezone.now() - timedelta(days=days)

        group_data = {
            'group_id': group_id,
            'group_name': group.name,
            'group_age_days': (timezone.now() - group.created_at).days,
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'health_score': self._calculate_group_health_score(group, cutoff_date),
            'member_analytics': self._analyze_group_member_dynamics(group, cutoff_date),
            'content_quality': self._analyze_group_content_quality(group, cutoff_date),
            'engagement_patterns': self._analyze_group_engagement_patterns(group, cutoff_date),
            'social_dynamics': self._analyze_group_social_dynamics(group, cutoff_date),
            'growth_analysis': self._analyze_group_growth_patterns(group, cutoff_date),
            'recommendations': self._generate_group_specific_recommendations(group, cutoff_date),
            'comparative_metrics': self._get_comparative_group_metrics(group, cutoff_date)
        }

        return group_data

    def _get_overall_group_health_metrics(self, cutoff_date: datetime) -> Dict:
        """Get high-level group health metrics overview."""
        # Total groups and activity
        total_groups = Group.objects.count()
        active_groups = Group.objects.filter(
            discussion_topics__created_at__gte=cutoff_date
        ).distinct().count()

        # Health score distribution
        group_health_scores = []
        for group in Group.objects.all()[:50]:  # Limit for performance
            health_score = self._calculate_group_health_score(
                group, cutoff_date)
            group_health_scores.append(health_score)

        if group_health_scores:
            avg_health_score = statistics.mean(group_health_scores)
            health_std_dev = statistics.stdev(group_health_scores) if len(
                group_health_scores) > 1 else 0
        else:
            avg_health_score = 0
            health_std_dev = 0

        # Health distribution
        excellent_groups = len(
            [score for score in group_health_scores if score >= 0.8])
        good_groups = len(
            [score for score in group_health_scores if 0.6 <= score < 0.8])
        fair_groups = len(
            [score for score in group_health_scores if 0.4 <= score < 0.6])
        poor_groups = len(
            [score for score in group_health_scores if score < 0.4])

        # Group size analysis
        group_sizes = Group.objects.annotate(
            member_count=Count('memberships', filter=Q(
                memberships__status='active'))
        ).values_list('member_count', flat=True)

        avg_group_size = statistics.mean(group_sizes) if group_sizes else 0

        return {
            'total_groups': total_groups,
            'active_groups': active_groups,
            'activity_rate': round(active_groups / max(total_groups, 1) * 100, 2),
            'average_health_score': round(avg_health_score, 2),
            'health_distribution': {
                'excellent': excellent_groups,
                'good': good_groups,
                'fair': fair_groups,
                'poor': poor_groups
            },
            'average_group_size': round(avg_group_size, 2),
            'health_variance': round(health_std_dev, 2)
        }

    def _calculate_group_health_score(self, group: Group, cutoff_date: datetime) -> float:
        """
        Calculate comprehensive health score for a group (0.0 to 1.0).

        Factors considered:
        - Member engagement and activity levels
        - Content quality and discussion depth
        - Member retention and growth
        - Social dynamics and interaction quality
        - Moderator effectiveness
        """
        scores = {}

        # 1. Member Engagement Score (25%)
        scores['engagement'] = self._calculate_engagement_score(
            group, cutoff_date) * 0.25

        # 2. Content Quality Score (25%)
        scores['content_quality'] = self._calculate_content_quality_score(
            group, cutoff_date) * 0.25

        # 3. Social Dynamics Score (20%)
        scores['social_dynamics'] = self._calculate_social_dynamics_score(
            group, cutoff_date) * 0.20

        # 4. Growth and Retention Score (15%)
        scores['growth_retention'] = self._calculate_growth_retention_score(
            group, cutoff_date) * 0.15

        # 5. Community Support Score (15%)
        scores['community_support'] = self._calculate_community_support_score(
            group, cutoff_date) * 0.15

        total_score = sum(scores.values())
        return min(max(total_score, 0.0), 1.0)  # Ensure between 0 and 1

    def _calculate_engagement_score(self, group: Group, cutoff_date: datetime) -> float:
        """Calculate member engagement score."""
        # Get group discussions and comments in period
        discussions = group.discussion_topics.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(
            topic__group=group, created_at__gte=cutoff_date)

        # Active members
        active_members = User.objects.filter(
            Q(discussion_topics__group=group, discussion_topics__created_at__gte=cutoff_date) |
            Q(comments__topic__group=group, comments__created_at__gte=cutoff_date)
        ).distinct().count()

        total_members = group.memberships.filter(status='active').count()

        # Participation rate
        participation_rate = active_members / max(total_members, 1)

        # Activity per member
        total_activity = discussions.count() + comments.count()
        activity_per_member = total_activity / max(active_members, 1)

        # Discussion response rate
        discussions_with_responses = discussions.annotate(
            response_count=Count('comments')
        ).filter(response_count__gt=0).count()

        response_rate = discussions_with_responses / \
            max(discussions.count(), 1)

        # Weighted score
        engagement_score = (
            participation_rate * 0.4 +
            # Normalize to reasonable activity level
            min(activity_per_member / 10.0, 1.0) * 0.3 +
            response_rate * 0.3
        )

        return min(engagement_score, 1.0)

    def _calculate_content_quality_score(self, group: Group, cutoff_date: datetime) -> float:
        """Calculate content quality score."""
        discussions = group.discussion_topics.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(
            topic__group=group, created_at__gte=cutoff_date)

        if not discussions.exists() and not comments.exists():
            return 0.5  # Neutral score for no activity

        # Average content length (indicator of thoughtfulness)
        discussion_lengths = [len(d.content) for d in discussions if d.content]
        comment_lengths = [len(c.content) for c in comments if c.content]

        avg_discussion_length = statistics.mean(
            discussion_lengths) if discussion_lengths else 0
        avg_comment_length = statistics.mean(
            comment_lengths) if comment_lengths else 0

        # Normalize length scores (optimal around 200-500 characters)
        discussion_length_score = min(
            avg_discussion_length / 400.0, 1.0) if avg_discussion_length > 50 else 0.3
        comment_length_score = min(
            avg_comment_length / 200.0, 1.0) if avg_comment_length > 20 else 0.3

        # Discussion depth (responses per discussion)
        discussions_with_responses = discussions.annotate(
            response_count=Count('comments')
        )

        avg_responses = discussions_with_responses.aggregate(
            avg=Avg('response_count')
        )['avg'] or 0

        # Normalize to 5 responses as good depth
        depth_score = min(avg_responses / 5.0, 1.0)

        # Content freshness (recent activity)
        recent_activity = discussions.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count() + comments.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        # 10 recent activities is good
        freshness_score = min(recent_activity / 10.0, 1.0)

        quality_score = (
            discussion_length_score * 0.25 +
            comment_length_score * 0.25 +
            depth_score * 0.3 +
            freshness_score * 0.2
        )

        return min(quality_score, 1.0)

    def _calculate_social_dynamics_score(self, group: Group, cutoff_date: datetime) -> float:
        """Calculate social dynamics and interaction quality score."""
        # Member diversity in participation
        member_activity = User.objects.filter(
            Q(discussion_topics__group=group, discussion_topics__created_at__gte=cutoff_date) |
            Q(comments__topic__group=group, comments__created_at__gte=cutoff_date)
        ).annotate(
            activity_count=Count('discussion_topics', filter=Q(discussion_topics__group=group)) +
            Count('comments', filter=Q(comments__topic__group=group))
        )

        if not member_activity.exists():
            return 0.5

        activity_counts = [member.activity_count for member in member_activity]

        # Check for balanced participation (not dominated by few users)
        if len(activity_counts) > 1:
            activity_variance = statistics.stdev(activity_counts)
            activity_mean = statistics.mean(activity_counts)
            balance_score = 1.0 / \
                (1.0 + (activity_variance / max(activity_mean, 1)))
        else:
            balance_score = 0.5

        # Cross-member interactions (replies between different users)
        cross_interactions = Comment.objects.filter(
            topic__group=group,
            created_at__gte=cutoff_date
        ).exclude(
            author__in=DiscussionTopic.objects.filter(
                group=group).values('author')
        ).count()

        total_comments = Comment.objects.filter(
            topic__group=group,
            created_at__gte=cutoff_date
        ).count()

        interaction_ratio = cross_interactions / max(total_comments, 1)

        # Member retention within period
        members_at_start = group.memberships.filter(
            status='active',
            created_at__lt=cutoff_date
        ).count()

        members_still_active = group.memberships.filter(
            status='active',
            created_at__lt=cutoff_date,
            user__in=User.objects.filter(
                Q(discussion_topics__group=group, discussion_topics__created_at__gte=cutoff_date) |
                Q(comments__topic__group=group,
                  comments__created_at__gte=cutoff_date)
            )
        ).count()

        retention_rate = members_still_active / max(members_at_start, 1)

        social_score = (
            balance_score * 0.4 +
            interaction_ratio * 0.3 +
            retention_rate * 0.3
        )

        return min(social_score, 1.0)

    def _calculate_growth_retention_score(self, group: Group, cutoff_date: datetime) -> float:
        """Calculate growth and member retention score."""
        # New member acquisition
        new_members = group.memberships.filter(
            created_at__gte=cutoff_date,
            status='active'
        ).count()

        # Member churn
        churned_members = group.memberships.filter(
            status='left',
            updated_at__gte=cutoff_date
        ).count()

        total_members = group.memberships.filter(status='active').count()

        # Growth rate
        growth_rate = new_members / max(total_members, 1)
        churn_rate = churned_members / max(total_members, 1)
        net_growth = growth_rate - churn_rate

        # Normalize growth (5% monthly growth is good)
        days_in_period = (timezone.now() - cutoff_date).days
        monthly_growth = net_growth * (30 / max(days_in_period, 1))
        growth_score = min(max(monthly_growth / 0.05 + 0.5,
                           0.0), 1.0)  # Center around 0.5

        # Member activation rate (new members who become active)
        new_member_users = User.objects.filter(
            memberships__group=group,
            memberships__created_at__gte=cutoff_date
        )

        active_new_members = new_member_users.filter(
            Q(discussion_topics__group=group, discussion_topics__created_at__gte=cutoff_date) |
            Q(comments__topic__group=group, comments__created_at__gte=cutoff_date)
        ).distinct().count()

        activation_rate = active_new_members / max(new_members, 1)

        return (growth_score * 0.6 + activation_rate * 0.4)

    def _calculate_community_support_score(self, group: Group, cutoff_date: datetime) -> float:
        """Calculate community support and helpfulness score."""
        # Response time to new discussions
        discussions = group.discussion_topics.filter(
            created_at__gte=cutoff_date)

        response_times = []
        for discussion in discussions:
            first_comment = discussion.comments.first()
            if first_comment:
                response_time = (
                    # hours
                    first_comment.created_at - discussion.created_at).total_seconds() / 3600
                response_times.append(response_time)

        if response_times:
            avg_response_time = statistics.mean(response_times)
            # Good response time is within 6 hours
            response_score = max(1.0 - (avg_response_time / 6.0), 0.0)
        else:
            response_score = 0.5

        # Discussions that receive responses
        discussions_with_responses = discussions.annotate(
            response_count=Count('comments')
        ).filter(response_count__gt=0).count()

        support_rate = discussions_with_responses / max(discussions.count(), 1)

        # Member helping behavior (cross-member support)
        # This is a simplified metric - in practice you'd analyze content for helpful keywords
        helpful_interactions = Comment.objects.filter(
            topic__group=group,
            created_at__gte=cutoff_date
        ).count()  # Simplified - would analyze content sentiment

        total_members = group.memberships.filter(status='active').count()
        help_ratio = helpful_interactions / max(total_members, 1)
        # 5 helpful interactions per member is excellent
        help_score = min(help_ratio / 5.0, 1.0)

        support_score = (
            response_score * 0.4 +
            support_rate * 0.4 +
            help_score * 0.2
        )

        return min(support_score, 1.0)

    def _rank_groups_by_health(self, cutoff_date: datetime) -> List[Dict]:
        """Rank groups by health score."""
        group_rankings = []

        for group in Group.objects.all()[:20]:  # Limit for performance
            health_score = self._calculate_group_health_score(
                group, cutoff_date)
            member_count = group.memberships.filter(status='active').count()

            recent_activity = group.discussion_topics.filter(
                created_at__gte=cutoff_date
            ).count() + Comment.objects.filter(
                topic__group=group,
                created_at__gte=cutoff_date
            ).count()

            group_rankings.append({
                'group_id': group.id,
                'group_name': group.name,
                'health_score': round(health_score, 2),
                'member_count': member_count,
                'recent_activity': recent_activity,
                'health_status': self._get_health_status(health_score)
            })

        # Sort by health score
        group_rankings.sort(key=lambda x: x['health_score'], reverse=True)

        return group_rankings

    def _get_health_status(self, health_score: float) -> str:
        """Get health status label from score."""
        if health_score >= 0.8:
            return 'excellent'
        elif health_score >= 0.6:
            return 'good'
        elif health_score >= 0.4:
            return 'fair'
        else:
            return 'poor'

    def _analyze_group_health_trends(self, cutoff_date: datetime) -> Dict:
        """Analyze trends in group health over time."""
        # Weekly health trend analysis
        weekly_trends = []
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

            # Calculate average health for active groups this week
            active_groups = Group.objects.filter(
                discussion_topics__created_at__gte=week_start_dt,
                discussion_topics__created_at__lte=week_end_dt
            ).distinct()

            if active_groups.exists():
                health_scores = []
                for group in active_groups[:10]:  # Limit for performance
                    health_score = self._calculate_group_health_score(
                        group, week_start_dt)
                    health_scores.append(health_score)

                avg_health = statistics.mean(
                    health_scores) if health_scores else 0
            else:
                avg_health = 0

            weekly_trends.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'average_health_score': round(avg_health, 2),
                'active_groups_count': active_groups.count()
            })

            current_date = week_end + timedelta(days=1)

        # Trend direction
        if len(weekly_trends) >= 2:
            recent_avg = statistics.mean(
                [w['average_health_score'] for w in weekly_trends[-2:]])
            earlier_avg = statistics.mean(
                [w['average_health_score'] for w in weekly_trends[:-2]]) if len(weekly_trends) > 2 else recent_avg

            if recent_avg > earlier_avg * 1.05:
                trend_direction = 'improving'
            elif recent_avg < earlier_avg * 0.95:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'insufficient_data'

        return {
            'weekly_trends': weekly_trends,
            'trend_direction': trend_direction,
            'trend_insights': self._generate_trend_insights(weekly_trends)
        }

    def _identify_at_risk_groups(self, cutoff_date: datetime) -> List[Dict]:
        """Identify groups that are at risk and need intervention."""
        at_risk_groups = []

        for group in Group.objects.all()[:30]:  # Limit for performance
            health_score = self._calculate_group_health_score(
                group, cutoff_date)

            # Criteria for at-risk groups
            member_count = group.memberships.filter(status='active').count()
            recent_activity = group.discussion_topics.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()

            risk_factors = []

            if health_score < 0.4:
                risk_factors.append('low_health_score')

            if member_count > 10 and recent_activity == 0:
                risk_factors.append('no_recent_activity')

            if member_count < 3:
                risk_factors.append('very_small_group')

            # Check for declining trends
            older_activity = group.discussion_topics.filter(
                created_at__gte=cutoff_date,
                created_at__lt=timezone.now() - timedelta(days=7)
            ).count()

            if older_activity > recent_activity * 2:
                risk_factors.append('declining_activity')

            if risk_factors:
                at_risk_groups.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'health_score': round(health_score, 2),
                    'member_count': member_count,
                    'recent_activity': recent_activity,
                    'risk_factors': risk_factors,
                    'urgency': self._calculate_urgency_level(risk_factors, health_score)
                })

        # Sort by urgency
        at_risk_groups.sort(key=lambda x: x['urgency'], reverse=True)

        return at_risk_groups[:10]  # Return top 10 most at-risk

    def _calculate_urgency_level(self, risk_factors: List[str], health_score: float) -> int:
        """Calculate urgency level (1-10) for intervention."""
        urgency = 0

        if 'low_health_score' in risk_factors:
            urgency += 4
        if 'no_recent_activity' in risk_factors:
            urgency += 3
        if 'declining_activity' in risk_factors:
            urgency += 2
        if 'very_small_group' in risk_factors:
            urgency += 1

        # Adjust based on health score
        if health_score < 0.2:
            urgency += 3
        elif health_score < 0.3:
            urgency += 2

        return min(urgency, 10)

    def _generate_intervention_recommendations(self, cutoff_date: datetime) -> List[Dict]:
        """Generate specific intervention recommendations for improving group health."""
        recommendations = []

        # Analyze overall group health patterns
        overall_health = self._get_overall_group_health_metrics(cutoff_date)
        at_risk_groups = self._identify_at_risk_groups(cutoff_date)

        # Low overall activity rate
        if overall_health['activity_rate'] < 60:
            recommendations.append({
                'type': 'activity_improvement',
                'priority': 'high',
                'title': 'Improve Group Activity Rates',
                'description': f"Only {overall_health['activity_rate']:.1f}% of groups are active",
                'target_groups': 'inactive_groups',
                'interventions': [
                    'Send group reactivation campaigns',
                    'Provide group moderator training',
                    'Create group activity challenges',
                    'Implement group mentorship program'
                ],
                'expected_impact': 'Increase group activity rate by 15-20%',
                'success_metrics': ['group_activity_rate', 'discussions_per_group', 'member_engagement']
            })

        # High number of at-risk groups
        if len(at_risk_groups) > 5:
            recommendations.append({
                'type': 'risk_mitigation',
                'priority': 'critical',
                'title': 'Address At-Risk Groups',
                'description': f"{len(at_risk_groups)} groups require immediate intervention",
                'target_groups': 'at_risk',
                'interventions': [
                    'Assign community managers to struggling groups',
                    'Merge very small groups with similar interests',
                    'Provide crisis intervention for declining groups',
                    'Implement early warning systems'
                ],
                'expected_impact': 'Reduce at-risk groups by 40-50%',
                'success_metrics': ['at_risk_group_count', 'group_health_scores', 'member_retention']
            })

        # Poor health score distribution
        poor_groups_percentage = (overall_health['health_distribution']['poor'] /
                                  max(sum(overall_health['health_distribution'].values()), 1)) * 100

        if poor_groups_percentage > 25:
            recommendations.append({
                'type': 'health_improvement',
                'priority': 'medium',
                'title': 'Improve Group Health Standards',
                'description': f"{poor_groups_percentage:.1f}% of groups have poor health scores",
                'target_groups': 'poor_health',
                'interventions': [
                    'Develop group health improvement playbooks',
                    'Provide automated health monitoring alerts',
                    'Create group wellness coaching programs',
                    'Implement peer group learning sessions'
                ],
                'expected_impact': 'Improve average group health score by 0.15-0.25',
                'success_metrics': ['average_health_score', 'health_distribution', 'group_satisfaction']
            })

        return recommendations


class GroupHealthDashboardView(APIView):
    """
    Group health analytics dashboard view for admin users.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.health_service = GroupHealthAnalyticsService()

    @method_decorator(cache_page(60 * 10))  # Cache for 10 minutes
    def get(self, request):
        """
        Get comprehensive group health analytics dashboard.
        """
        days = int(request.query_params.get('days', 30))

        try:
            dashboard_data = self.health_service.get_group_health_dashboard(
                days=days)
            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating group health dashboard: {e}")
            return Response({
                'error': 'Failed to generate group health dashboard',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IndividualGroupHealthView(APIView):
    """
    Individual group health analytics view for detailed group analysis.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.health_service = GroupHealthAnalyticsService()

    def get(self, request, group_id):
        """
        Get detailed health analytics for a specific group.
        """
        days = int(request.query_params.get('days', 60))

        try:
            group_data = self.health_service.get_individual_group_health(
                group_id=group_id, days=days)

            if 'error' in group_data:
                return Response(group_data, status=status.HTTP_404_NOT_FOUND)

            return Response(group_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error generating individual group health analytics for group {group_id}: {e}")
            return Response({
                'error': 'Failed to generate group health analytics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GroupHealthRankingsView(APIView):
    """
    Group health rankings view for comparative analysis.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.health_service = GroupHealthAnalyticsService()

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, request):
        """
        Get group health rankings and comparative metrics.
        """
        days = int(request.query_params.get('days', 30))

        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            rankings_data = self.health_service._rank_groups_by_health(
                cutoff_date)

            return Response({
                'rankings': rankings_data,
                'generated_at': timezone.now().isoformat(),
                'period_days': days
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating group health rankings: {e}")
            return Response({
                'error': 'Failed to generate group health rankings',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
