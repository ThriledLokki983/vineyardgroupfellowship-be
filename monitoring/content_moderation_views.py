"""
Content Moderation Dashboard for Phase 5

Comprehensive content moderation system providing:
- Automated content detection and flagging
- Community health metrics and trends
- Moderation queue management
- Risk assessment and escalation tools
"""

from django.db import models
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Tuple
import re
import logging
from collections import defaultdict

from groups.models import Group, GroupMembership, DiscussionTopic, Comment
from authentication.models import User

logger = logging.getLogger('content_moderation')


class ContentModerationService:
    """
    Service for content moderation analytics and automated detection.
    """

    # Content risk patterns (simplified - would be more sophisticated in production)
    RISK_PATTERNS = {
        'crisis_keywords': [
            'suicide', 'self-harm', 'kill myself', 'end it all', 'not worth living',
            'overdose', 'cutting', 'pills', 'bridge', 'gun'
        ],
        'spam_patterns': [
            r'\b(?:buy|purchase|click here|free money|earn \$\d+)\b',
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        ],
        'inappropriate_language': [
            # This would be a more comprehensive list in production
            'offensive_term_1', 'offensive_term_2', 'harassment_term'
        ],
        'substance_abuse_triggers': [
            'dealer', 'score', 'fix', 'high quality', 'pure stuff',
            'connect me', 'hook me up'
        ]
    }

    def __init__(self):
        self.cache_timeout = 300  # 5 minutes

    def get_moderation_dashboard(self, days: int = 7) -> Dict:
        """
        Get comprehensive moderation dashboard data.

        Args:
            days: Number of days to analyze

        Returns:
            Complete moderation dashboard data
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        dashboard_data = {
            'period_days': days,
            'generated_at': timezone.now().isoformat(),
            'moderation_queue': self._get_moderation_queue(),
            'content_analysis': self._get_content_analysis(cutoff_date),
            'community_health': self._get_community_health_metrics(cutoff_date),
            'risk_assessment': self._get_risk_assessment(cutoff_date),
            'automated_actions': self._get_automated_actions_summary(cutoff_date),
            'trends': self._get_moderation_trends(cutoff_date),
            'recommendations': self._generate_moderation_recommendations(cutoff_date)
        }

        return dashboard_data

    def _get_moderation_queue(self) -> Dict:
        """Get current moderation queue status."""
        # In a full implementation, this would check a moderation queue table
        # For now, we'll simulate with content that needs review

        # Recent content that might need review
        recent_discussions = DiscussionTopic.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')

        recent_comments = Comment.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')

        # Simulate flagged content
        flagged_discussions = []
        flagged_comments = []

        for discussion in recent_discussions[:10]:  # Limit for demo
            risk_score = self._calculate_content_risk_score(
                discussion.title + " " + discussion.content)
            if risk_score > 0.3:  # Threshold for review
                flagged_discussions.append({
                    'id': discussion.id,
                    'title': discussion.title,
                    'author': discussion.author.username,
                    'created_at': discussion.created_at.isoformat(),
                    'risk_score': round(risk_score, 2),
                    'risk_categories': self._identify_risk_categories(discussion.title + " " + discussion.content),
                    'group': discussion.group.name
                })

        for comment in recent_comments[:20]:  # Limit for demo
            risk_score = self._calculate_content_risk_score(comment.content)
            if risk_score > 0.3:
                flagged_comments.append({
                    'id': comment.id,
                    'content_preview': comment.content[:100] + "..." if len(comment.content) > 100 else comment.content,
                    'author': comment.author.username,
                    'created_at': comment.created_at.isoformat(),
                    'risk_score': round(risk_score, 2),
                    'risk_categories': self._identify_risk_categories(comment.content),
                    'discussion_title': comment.topic.title
                })

        return {
            'pending_reviews': len(flagged_discussions) + len(flagged_comments),
            'high_priority': len([item for item in flagged_discussions + flagged_comments if item['risk_score'] > 0.7]),
            'flagged_discussions': sorted(flagged_discussions, key=lambda x: x['risk_score'], reverse=True),
            'flagged_comments': sorted(flagged_comments, key=lambda x: x['risk_score'], reverse=True),
            'last_updated': timezone.now().isoformat()
        }

    def _get_content_analysis(self, cutoff_date: datetime) -> Dict:
        """Analyze content patterns and risks."""
        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(created_at__gte=cutoff_date)

        # Content volume analysis
        content_volume = {
            'total_discussions': discussions.count(),
            'total_comments': comments.count(),
            'daily_average_discussions': round(discussions.count() / ((timezone.now() - cutoff_date).days or 1), 2),
            'daily_average_comments': round(comments.count() / ((timezone.now() - cutoff_date).days or 1), 2)
        }

        # Risk category analysis
        risk_categories = defaultdict(int)
        total_risk_score = 0
        content_count = 0

        for discussion in discussions:
            content = discussion.title + " " + discussion.content
            categories = self._identify_risk_categories(content)
            for category in categories:
                risk_categories[category] += 1
            total_risk_score += self._calculate_content_risk_score(content)
            content_count += 1

        for comment in comments:
            categories = self._identify_risk_categories(comment.content)
            for category in categories:
                risk_categories[category] += 1
            total_risk_score += self._calculate_content_risk_score(
                comment.content)
            content_count += 1

        avg_risk_score = round(total_risk_score / max(content_count, 1), 3)

        # Content quality metrics
        quality_metrics = self._analyze_content_quality(discussions, comments)

        return {
            'content_volume': content_volume,
            'risk_categories': dict(risk_categories),
            'average_risk_score': avg_risk_score,
            'quality_metrics': quality_metrics
        }

    def _get_community_health_metrics(self, cutoff_date: datetime) -> Dict:
        """Get community health indicators."""
        # User engagement health
        active_users = User.objects.filter(
            Q(comments__created_at__gte=cutoff_date) |
            Q(discussion_topics__created_at__gte=cutoff_date)
        ).distinct().count()

        # Group health indicators
        active_groups = Group.objects.filter(
            discussion_topics__created_at__gte=cutoff_date
        ).distinct().count()

        # Participation distribution
        user_activity = User.objects.annotate(
            discussion_count=Count('discussion_topics', filter=Q(
                discussion_topics__created_at__gte=cutoff_date)),
            comment_count=Count('comments', filter=Q(
                comments__created_at__gte=cutoff_date)),
            total_activity=F('discussion_count') + F('comment_count')
        ).filter(total_activity__gt=0)

        participation_levels = {
            'very_active': user_activity.filter(total_activity__gte=20).count(),
            'moderately_active': user_activity.filter(total_activity__gte=5, total_activity__lt=20).count(),
            'lightly_active': user_activity.filter(total_activity__gte=1, total_activity__lt=5).count()
        }

        # Community interaction quality
        interaction_quality = self._analyze_interaction_quality(cutoff_date)

        # Crisis intervention metrics
        crisis_metrics = self._get_crisis_intervention_metrics(cutoff_date)

        return {
            'active_users': active_users,
            'active_groups': active_groups,
            'participation_levels': participation_levels,
            'interaction_quality': interaction_quality,
            'crisis_metrics': crisis_metrics,
            'overall_health_score': self._calculate_community_health_score(
                active_users, active_groups, participation_levels, interaction_quality
            )
        }

    def _get_risk_assessment(self, cutoff_date: datetime) -> Dict:
        """Perform comprehensive risk assessment."""
        # High-risk users (multiple flags, concerning patterns)
        high_risk_users = self._identify_high_risk_users(cutoff_date)

        # Group risk assessment
        group_risks = self._assess_group_risks(cutoff_date)

        # Content trend risks
        trend_risks = self._analyze_content_trend_risks(cutoff_date)

        # Overall risk level
        overall_risk = self._calculate_overall_risk_level(
            high_risk_users, group_risks, trend_risks)

        return {
            'overall_risk_level': overall_risk,
            'high_risk_users_count': len(high_risk_users),
            'high_risk_groups': group_risks,
            'trend_risks': trend_risks,
            'risk_factors': self._identify_current_risk_factors(cutoff_date)
        }

    def _get_automated_actions_summary(self, cutoff_date: datetime) -> Dict:
        """Get summary of automated moderation actions."""
        # In a full implementation, this would track actual automated actions
        # For now, simulate based on content analysis

        return {
            'auto_flagged_content': self._count_auto_flagged_content(cutoff_date),
            'crisis_interventions': self._count_crisis_interventions(cutoff_date),
            'spam_removed': self._count_spam_removed(cutoff_date),
            'warnings_issued': self._count_warnings_issued(cutoff_date)
        }

    def _get_moderation_trends(self, cutoff_date: datetime) -> Dict:
        """Get moderation trends over time."""
        daily_trends = []
        current_date = cutoff_date.date()
        end_date = timezone.now().date()

        while current_date <= end_date:
            day_start = timezone.make_aware(
                datetime.combine(current_date, datetime.min.time()))
            day_end = day_start + timedelta(days=1)

            day_discussions = DiscussionTopic.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            )

            day_comments = Comment.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            )

            # Calculate daily risk metrics
            daily_risk_score = 0
            content_count = 0

            for discussion in day_discussions:
                content = discussion.title + " " + discussion.content
                daily_risk_score += self._calculate_content_risk_score(content)
                content_count += 1

            for comment in day_comments:
                daily_risk_score += self._calculate_content_risk_score(
                    comment.content)
                content_count += 1

            avg_daily_risk = round(daily_risk_score / max(content_count, 1), 3)

            daily_trends.append({
                'date': current_date.isoformat(),
                'content_volume': content_count,
                'avg_risk_score': avg_daily_risk,
                'flagged_content': len([1 for _ in range(content_count) if daily_risk_score / max(content_count, 1) > 0.3])
            })

            current_date += timedelta(days=1)

        return {
            'daily_trends': daily_trends,
            'trend_analysis': self._analyze_trend_patterns(daily_trends)
        }

    def _generate_moderation_recommendations(self, cutoff_date: datetime) -> List[Dict]:
        """Generate actionable moderation recommendations."""
        recommendations = []

        # Analyze current state
        content_analysis = self._get_content_analysis(cutoff_date)
        community_health = self._get_community_health_metrics(cutoff_date)
        risk_assessment = self._get_risk_assessment(cutoff_date)

        # High risk score recommendation
        if content_analysis['average_risk_score'] > 0.5:
            recommendations.append({
                'type': 'content_quality',
                'priority': 'high',
                'title': 'Elevated Content Risk Detected',
                'description': f"Average content risk score is {content_analysis['average_risk_score']:.2f}",
                'actions': [
                    'Increase moderation team availability',
                    'Review and update content guidelines',
                    'Implement additional automated filters',
                    'Provide crisis support resources prominently'
                ],
                'expected_impact': 'Reduce harmful content by 20-30%'
            })

        # Low community engagement
        if community_health['overall_health_score'] < 0.6:
            recommendations.append({
                'type': 'community_health',
                'priority': 'medium',
                'title': 'Community Health Needs Attention',
                'description': f"Community health score is {community_health['overall_health_score']:.2f}",
                'actions': [
                    'Encourage positive interactions',
                    'Recognize helpful community members',
                    'Create engagement initiatives',
                    'Improve onboarding for new members'
                ],
                'expected_impact': 'Improve community engagement by 15-25%'
            })

        # Crisis content detection
        crisis_count = content_analysis['risk_categories'].get(
            'crisis_keywords', 0)
        if crisis_count > 5:
            recommendations.append({
                'type': 'crisis_support',
                'priority': 'critical',
                'title': 'High Crisis Content Volume',
                'description': f"{crisis_count} pieces of content flagged for crisis keywords",
                'actions': [
                    'Ensure crisis support team is available',
                    'Review crisis intervention protocols',
                    'Make mental health resources more visible',
                    'Consider temporary increased monitoring'
                ],
                'expected_impact': 'Improve crisis response time and support quality'
            })

        # Spam/inappropriate content
        spam_count = content_analysis['risk_categories'].get(
            'spam_patterns', 0)
        inappropriate_count = content_analysis['risk_categories'].get(
            'inappropriate_language', 0)

        if spam_count > 10 or inappropriate_count > 5:
            recommendations.append({
                'type': 'content_filtering',
                'priority': 'medium',
                'title': 'Increase Automated Content Filtering',
                'description': f"High volume of spam ({spam_count}) or inappropriate content ({inappropriate_count})",
                'actions': [
                    'Update spam detection algorithms',
                    'Implement stricter content filters',
                    'Review user reporting mechanisms',
                    'Consider user verification requirements'
                ],
                'expected_impact': 'Reduce spam and inappropriate content by 40-50%'
            })

        return recommendations

    # Helper methods for content analysis

    def _calculate_content_risk_score(self, content: str) -> float:
        """Calculate risk score for content (0.0 to 1.0)."""
        if not content:
            return 0.0

        content_lower = content.lower()
        risk_score = 0.0

        # Check for crisis keywords
        crisis_matches = sum(1 for keyword in self.RISK_PATTERNS['crisis_keywords']
                             if keyword in content_lower)
        if crisis_matches > 0:
            risk_score += min(crisis_matches * 0.3, 0.8)  # Cap at 0.8

        # Check for spam patterns
        spam_matches = sum(1 for pattern in self.RISK_PATTERNS['spam_patterns']
                           if re.search(pattern, content_lower, re.IGNORECASE))
        if spam_matches > 0:
            risk_score += min(spam_matches * 0.2, 0.4)  # Cap at 0.4

        # Check for inappropriate language
        inappropriate_matches = sum(1 for term in self.RISK_PATTERNS['inappropriate_language']
                                    if term in content_lower)
        if inappropriate_matches > 0:
            risk_score += min(inappropriate_matches * 0.15, 0.3)  # Cap at 0.3

        # Check for substance abuse triggers
        substance_matches = sum(1 for term in self.RISK_PATTERNS['substance_abuse_triggers']
                                if term in content_lower)
        if substance_matches > 0:
            risk_score += min(substance_matches * 0.25, 0.5)  # Cap at 0.5

        return min(risk_score, 1.0)  # Cap total at 1.0

    def _identify_risk_categories(self, content: str) -> List[str]:
        """Identify which risk categories apply to content."""
        categories = []
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in self.RISK_PATTERNS['crisis_keywords']):
            categories.append('crisis_keywords')

        if any(re.search(pattern, content_lower, re.IGNORECASE)
               for pattern in self.RISK_PATTERNS['spam_patterns']):
            categories.append('spam_patterns')

        if any(term in content_lower for term in self.RISK_PATTERNS['inappropriate_language']):
            categories.append('inappropriate_language')

        if any(term in content_lower for term in self.RISK_PATTERNS['substance_abuse_triggers']):
            categories.append('substance_abuse_triggers')

        return categories

    def _analyze_content_quality(self, discussions, comments) -> Dict:
        """Analyze overall content quality metrics."""
        if not discussions.exists() and not comments.exists():
            return {'insufficient_data': True}

        # Average content length
        discussion_lengths = [len(d.content) for d in discussions if d.content]
        comment_lengths = [len(c.content) for c in comments if c.content]

        avg_discussion_length = sum(
            discussion_lengths) / len(discussion_lengths) if discussion_lengths else 0
        avg_comment_length = sum(comment_lengths) / \
            len(comment_lengths) if comment_lengths else 0

        # Engagement quality (responses per discussion)
        discussions_with_responses = discussions.annotate(
            response_count=Count('comments')
        )

        avg_responses = discussions_with_responses.aggregate(
            avg=Avg('response_count')
        )['avg'] or 0

        return {
            'avg_discussion_length': round(avg_discussion_length, 2),
            'avg_comment_length': round(avg_comment_length, 2),
            'avg_responses_per_discussion': round(avg_responses, 2),
            # Normalize to 0-1
            'engagement_quality_score': min(avg_responses / 5.0, 1.0)
        }

    def _analyze_interaction_quality(self, cutoff_date: datetime) -> Dict:
        """Analyze quality of user interactions."""
        # This is a simplified implementation
        # In production, you'd analyze sentiment, helpfulness, etc.

        comments = Comment.objects.filter(created_at__gte=cutoff_date)

        # Basic interaction metrics
        total_interactions = comments.count()
        unique_participants = comments.values('author').distinct().count()

        # Simple quality indicators
        avg_interaction_length = comments.aggregate(
            avg_length=Avg(models.Length('content'))
        )['avg_length'] or 0

        return {
            'total_interactions': total_interactions,
            'unique_participants': unique_participants,
            'avg_interaction_length': round(avg_interaction_length, 2),
            # Simple heuristic
            'quality_score': min(avg_interaction_length / 100.0, 1.0)
        }

    def _get_crisis_intervention_metrics(self, cutoff_date: datetime) -> Dict:
        """Get crisis intervention metrics."""
        # In a full implementation, this would track actual interventions
        # For now, estimate based on crisis keyword detection

        crisis_content_count = 0
        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(created_at__gte=cutoff_date)

        for discussion in discussions:
            content = discussion.title + " " + discussion.content
            if any(keyword in content.lower() for keyword in self.RISK_PATTERNS['crisis_keywords']):
                crisis_content_count += 1

        for comment in comments:
            if any(keyword in comment.content.lower() for keyword in self.RISK_PATTERNS['crisis_keywords']):
                crisis_content_count += 1

        return {
            'potential_crisis_content': crisis_content_count,
            'interventions_needed': crisis_content_count,  # Simplified
            'response_time_hours': 2.0,  # Placeholder
            # Simplified
            'successful_interventions': max(0, crisis_content_count - 1)
        }

    def _calculate_community_health_score(self, active_users: int, active_groups: int,
                                          participation_levels: Dict, interaction_quality: Dict) -> float:
        """Calculate overall community health score (0.0 to 1.0)."""
        # Normalize metrics and create weighted score
        # Assume 100 active users is ideal
        user_score = min(active_users / 100.0, 1.0)
        # Assume 20 active groups is ideal
        group_score = min(active_groups / 20.0, 1.0)

        # Participation distribution score (higher is better for balanced participation)
        total_active = sum(participation_levels.values())
        if total_active > 0:
            participation_score = (participation_levels['moderately_active'] +
                                   participation_levels['very_active']) / total_active
        else:
            participation_score = 0.0

        quality_score = interaction_quality.get('quality_score', 0.0)

        # Weighted average
        overall_score = (user_score * 0.3 + group_score * 0.2 +
                         participation_score * 0.3 + quality_score * 0.2)

        return round(overall_score, 2)

    def _identify_high_risk_users(self, cutoff_date: datetime) -> List[Dict]:
        """Identify users with high risk patterns."""
        # This would be more sophisticated in production
        high_risk_users = []

        users_with_activity = User.objects.filter(
            Q(comments__created_at__gte=cutoff_date) |
            Q(discussion_topics__created_at__gte=cutoff_date)
        ).distinct()

        for user in users_with_activity:
            # Calculate user risk score based on content
            user_content = []

            # Collect user's recent content
            discussions = user.discussion_topics.filter(
                created_at__gte=cutoff_date)
            comments = user.comments.filter(created_at__gte=cutoff_date)

            for discussion in discussions:
                user_content.append(discussion.title +
                                    " " + discussion.content)

            for comment in comments:
                user_content.append(comment.content)

            # Calculate average risk score
            if user_content:
                total_risk = sum(self._calculate_content_risk_score(
                    content) for content in user_content)
                avg_risk = total_risk / len(user_content)

                if avg_risk > 0.4:  # High risk threshold
                    high_risk_users.append({
                        'user_id': user.id,
                        'username': user.username,
                        'avg_risk_score': round(avg_risk, 2),
                        'content_count': len(user_content),
                        'risk_categories': self._get_user_risk_categories(user_content)
                    })

        return sorted(high_risk_users, key=lambda x: x['avg_risk_score'], reverse=True)

    def _get_user_risk_categories(self, user_content: List[str]) -> List[str]:
        """Get risk categories for a user's content."""
        all_categories = set()
        for content in user_content:
            categories = self._identify_risk_categories(content)
            all_categories.update(categories)
        return list(all_categories)

    def _assess_group_risks(self, cutoff_date: datetime) -> List[Dict]:
        """Assess risk levels for groups."""
        group_risks = []

        active_groups = Group.objects.filter(
            discussion_topics__created_at__gte=cutoff_date
        ).distinct()

        for group in active_groups:
            # Collect group content
            discussions = group.discussion_topics.filter(
                created_at__gte=cutoff_date)
            comments = Comment.objects.filter(
                topic__group=group,
                created_at__gte=cutoff_date
            )

            # Calculate group risk score
            total_risk = 0
            content_count = 0

            for discussion in discussions:
                content = discussion.title + " " + discussion.content
                total_risk += self._calculate_content_risk_score(content)
                content_count += 1

            for comment in comments:
                total_risk += self._calculate_content_risk_score(
                    comment.content)
                content_count += 1

            if content_count > 0:
                avg_risk = total_risk / content_count

                if avg_risk > 0.3:  # Risk threshold for groups
                    group_risks.append({
                        'group_id': group.id,
                        'group_name': group.name,
                        'avg_risk_score': round(avg_risk, 2),
                        'content_count': content_count,
                        'member_count': group.memberships.filter(status='active').count()
                    })

        return sorted(group_risks, key=lambda x: x['avg_risk_score'], reverse=True)[:10]

    def _analyze_content_trend_risks(self, cutoff_date: datetime) -> Dict:
        """Analyze content trends for emerging risks."""
        # This would be more sophisticated with NLP in production
        return {
            'emerging_keywords': [],  # Would use trend analysis
            'unusual_patterns': [],   # Would detect anomalies
            'risk_trend': 'stable'    # Would calculate trend direction
        }

    def _calculate_overall_risk_level(self, high_risk_users: List, group_risks: List, trend_risks: Dict) -> str:
        """Calculate overall community risk level."""
        risk_score = 0

        # High risk users contribution
        if len(high_risk_users) > 10:
            risk_score += 0.4
        elif len(high_risk_users) > 5:
            risk_score += 0.2

        # High risk groups contribution
        if len(group_risks) > 5:
            risk_score += 0.3
        elif len(group_risks) > 2:
            risk_score += 0.15

        # Trend risks contribution
        if trend_risks.get('risk_trend') == 'increasing':
            risk_score += 0.3

        if risk_score > 0.7:
            return 'high'
        elif risk_score > 0.4:
            return 'medium'
        else:
            return 'low'

    def _identify_current_risk_factors(self, cutoff_date: datetime) -> List[str]:
        """Identify current risk factors in the community."""
        risk_factors = []

        # Analyze recent content for patterns
        content_analysis = self._get_content_analysis(cutoff_date)

        if content_analysis['risk_categories'].get('crisis_keywords', 0) > 5:
            risk_factors.append('elevated_crisis_content')

        if content_analysis['risk_categories'].get('spam_patterns', 0) > 10:
            risk_factors.append('spam_increase')

        if content_analysis['average_risk_score'] > 0.4:
            risk_factors.append('overall_content_quality_decline')

        return risk_factors

    def _count_auto_flagged_content(self, cutoff_date: datetime) -> int:
        """Count content that would be auto-flagged."""
        # Simulate auto-flagging based on risk scores
        count = 0

        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(created_at__gte=cutoff_date)

        for discussion in discussions:
            content = discussion.title + " " + discussion.content
            if self._calculate_content_risk_score(content) > 0.5:
                count += 1

        for comment in comments:
            if self._calculate_content_risk_score(comment.content) > 0.5:
                count += 1

        return count

    def _count_crisis_interventions(self, cutoff_date: datetime) -> int:
        """Count crisis interventions that would be triggered."""
        count = 0

        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(created_at__gte=cutoff_date)

        for discussion in discussions:
            content = discussion.title + " " + discussion.content
            if any(keyword in content.lower() for keyword in self.RISK_PATTERNS['crisis_keywords']):
                count += 1

        for comment in comments:
            if any(keyword in comment.content.lower() for keyword in self.RISK_PATTERNS['crisis_keywords']):
                count += 1

        return count

    def _count_spam_removed(self, cutoff_date: datetime) -> int:
        """Count spam content that would be removed."""
        count = 0

        discussions = DiscussionTopic.objects.filter(
            created_at__gte=cutoff_date)
        comments = Comment.objects.filter(created_at__gte=cutoff_date)

        for discussion in discussions:
            content = discussion.title + " " + discussion.content
            if any(re.search(pattern, content.lower(), re.IGNORECASE)
                   for pattern in self.RISK_PATTERNS['spam_patterns']):
                count += 1

        for comment in comments:
            if any(re.search(pattern, comment.content.lower(), re.IGNORECASE)
                   for pattern in self.RISK_PATTERNS['spam_patterns']):
                count += 1

        return count

    def _count_warnings_issued(self, cutoff_date: datetime) -> int:
        """Count warnings that would be issued."""
        # Simplified - would be based on actual warning triggers
        # Roughly 1/3 of flagged content gets warnings
        return self._count_auto_flagged_content(cutoff_date) // 3

    def _analyze_trend_patterns(self, daily_trends: List[Dict]) -> Dict:
        """Analyze patterns in daily trends."""
        if len(daily_trends) < 3:
            return {'insufficient_data': True}

        # Calculate trend direction
        recent_avg_risk = sum(day['avg_risk_score']
                              for day in daily_trends[-3:]) / 3
        earlier_avg_risk = sum(day['avg_risk_score']
                               for day in daily_trends[:-3]) / max(len(daily_trends) - 3, 1)

        if recent_avg_risk > earlier_avg_risk * 1.2:
            trend_direction = 'increasing'
        elif recent_avg_risk < earlier_avg_risk * 0.8:
            trend_direction = 'decreasing'
        else:
            trend_direction = 'stable'

        return {
            'risk_trend_direction': trend_direction,
            'recent_avg_risk': round(recent_avg_risk, 3),
            'earlier_avg_risk': round(earlier_avg_risk, 3),
            'trend_strength': abs(recent_avg_risk - earlier_avg_risk)
        }


class ContentModerationDashboardView(APIView):
    """
    Content moderation dashboard view for admin users.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.moderation_service = ContentModerationService()

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """
        Get comprehensive content moderation dashboard.
        """
        days = int(request.query_params.get('days', 7))

        try:
            dashboard_data = self.moderation_service.get_moderation_dashboard(
                days=days)
            return Response(dashboard_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating moderation dashboard: {e}")
            return Response({
                'error': 'Failed to generate moderation dashboard',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ModerationQueueView(APIView):
    """
    Real-time moderation queue view for immediate action.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.moderation_service = ContentModerationService()

    def get(self, request):
        """
        Get current moderation queue with high-priority items first.
        """
        try:
            queue_data = self.moderation_service._get_moderation_queue()
            return Response(queue_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to get moderation queue',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommunityHealthView(APIView):
    """
    Community health metrics and trends view.
    """
    permission_classes = [IsAdminUser]

    def __init__(self):
        super().__init__()
        self.moderation_service = ContentModerationService()

    def get(self, request):
        """
        Get community health metrics and analysis.
        """
        days = int(request.query_params.get('days', 30))

        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            health_data = self.moderation_service._get_community_health_metrics(
                cutoff_date)

            # Add additional health insights
            health_data['recommendations'] = self._generate_health_recommendations(
                health_data)

            return Response(health_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': 'Failed to get community health data',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_health_recommendations(self, health_data: Dict) -> List[Dict]:
        """Generate community health improvement recommendations."""
        recommendations = []

        health_score = health_data.get('overall_health_score', 0)

        if health_score < 0.6:
            recommendations.append({
                'type': 'engagement',
                'title': 'Improve Community Engagement',
                'description': 'Community health score is below optimal levels',
                'actions': [
                    'Create engaging discussion topics',
                    'Recognize active community members',
                    'Host community events or challenges'
                ]
            })

        participation = health_data.get('participation_levels', {})
        if participation.get('very_active', 0) < participation.get('lightly_active', 0) / 2:
            recommendations.append({
                'type': 'participation',
                'title': 'Encourage Deeper Participation',
                'description': 'Most users are lightly active - encourage more engagement',
                'actions': [
                    'Create mentorship programs',
                    'Implement gamification elements',
                    'Provide clear paths for increased involvement'
                ]
            })

        return recommendations
