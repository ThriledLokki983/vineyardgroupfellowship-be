"""
Custom filters for messaging app.
"""

import django_filters
from django.contrib.contenttypes.models import ContentType
from messaging.models import Comment, Discussion, Scripture, PrayerRequest, Testimony


class CommentFilter(django_filters.FilterSet):
    """
    Custom filter for Comment model supporting polymorphic content filtering.
    
    Supports filtering by:
    - discussion (UUID) - legacy support
    - scripture (UUID) - filter by scripture ID
    - prayer (UUID) - filter by prayer request ID
    - testimony (UUID) - filter by testimony ID
    - content_type (string) - filter by content type model name
    - content_id (UUID) - filter by specific content ID
    - parent (UUID) - filter by parent comment
    """
    
    discussion = django_filters.UUIDFilter(method='filter_by_discussion', label='Discussion ID')
    scripture = django_filters.UUIDFilter(method='filter_by_scripture', label='Scripture ID')
    prayer = django_filters.UUIDFilter(method='filter_by_prayer', label='Prayer Request ID')
    testimony = django_filters.UUIDFilter(method='filter_by_testimony', label='Testimony ID')
    
    class Meta:
        model = Comment
        fields = ['discussion', 'scripture', 'prayer', 'testimony', 'content_type', 'content_id', 'parent']
    
    def filter_by_discussion(self, queryset, name, value):
        """Filter comments by discussion ID."""
        discussion_type = ContentType.objects.get_for_model(Discussion)
        return queryset.filter(content_type=discussion_type, content_id=value)
    
    def filter_by_scripture(self, queryset, name, value):
        """Filter comments by scripture ID."""
        try:
            scripture_type = ContentType.objects.get_for_model(Scripture)
            return queryset.filter(content_type=scripture_type, content_id=value)
        except Exception:
            # If Scripture model doesn't exist yet, return empty queryset
            return queryset.none()
    
    def filter_by_prayer(self, queryset, name, value):
        """Filter comments by prayer request ID."""
        try:
            prayer_type = ContentType.objects.get_for_model(PrayerRequest)
            return queryset.filter(content_type=prayer_type, content_id=value)
        except Exception:
            # If PrayerRequest model doesn't exist yet, return empty queryset
            return queryset.none()
    
    def filter_by_testimony(self, queryset, name, value):
        """Filter comments by testimony ID."""
        try:
            testimony_type = ContentType.objects.get_for_model(Testimony)
            return queryset.filter(content_type=testimony_type, content_id=value)
        except Exception:
            # If Testimony model doesn't exist yet, return empty queryset
            return queryset.none()
