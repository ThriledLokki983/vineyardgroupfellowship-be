"""
ViewSets for messaging app API endpoints.

Implements RESTful API for discussions, comments, reactions, and feed.
"""

from django.db.models import F, Q, Prefetch
from django.utils import timezone
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
import django_filters

from .models import (
    Discussion, Comment, CommentHistory, Reaction,
    FeedItem, NotificationPreference, ContentReport,
    PrayerRequest, Testimony, Scripture,
    Conversation, PrivateMessage
)
from .serializers import (
    DiscussionListSerializer, DiscussionDetailSerializer, DiscussionCreateSerializer,
    CommentSerializer, CommentSimpleSerializer, CommentCreateSerializer,
    ReactionSerializer, FeedItemSerializer, NotificationPreferenceSerializer,
    CommentHistorySerializer,
    PrayerRequestListSerializer, PrayerRequestDetailSerializer, PrayerRequestCreateSerializer,
    PrayerRequestAnswerSerializer,
    TestimonyListSerializer, TestimonyDetailSerializer, TestimonyCreateSerializer,
    TestimonyPublicShareSerializer,
    ScriptureListSerializer, ScriptureDetailSerializer, ScriptureCreateSerializer,
    ScriptureVerseSearchSerializer,
    ConversationListSerializer, ConversationDetailSerializer,
    PrivateMessageSerializer, CreateConversationSerializer,
    SendMessageSerializer, CloseConversationSerializer, StartConversationSerializer,
)
from .utils import (
    validate_can_message_user,
    get_or_create_direct_conversation,
)
from .services import FeedService
from .filters import CommentFilter
from .permissions import (
    IsGroupMember, IsAuthorOrGroupLeaderOrReadOnly,
    IsAuthorOrReadOnly, CanModerateGroup, IsConversationParticipant
)
from .throttling import (
    DiscussionCreateThrottle, CommentCreateThrottle,
    ReactionCreateThrottle, BurstProtectionThrottle
)
from group.models import GroupMembership, Group


class FeedItemFilter(FilterSet):
    """
    Custom filter for FeedItem to handle content_type aliases.

    Allows both 'prayer' and 'prayer_request' to work for prayer requests.
    This provides better frontend compatibility.
    """
    content_type = django_filters.ChoiceFilter(
        method='filter_content_type',
        choices=[
            ('discussion', 'Discussion'),
            ('prayer', 'Prayer Request'),
            ('prayer_request', 'Prayer Request'),  # Alias for 'prayer'
            ('testimony', 'Testimony'),
            ('scripture', 'Scripture'),
        ]
    )

    class Meta:
        model = FeedItem
        fields = ['group', 'content_type']

    def filter_content_type(self, queryset, name, value):
        """Normalize content_type value before filtering."""
        # Map prayer_request -> prayer for database query
        if value == 'prayer_request':
            value = 'prayer'
        return queryset.filter(content_type=value)


class DiscussionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Discussion CRUD operations.

    Endpoints:
    - GET /discussions/ - List discussions (with filtering)
    - POST /discussions/ - Create discussion
    - GET /discussions/{id}/ - Get discussion detail
    - PUT/PATCH /discussions/{id}/ - Update discussion
    - DELETE /discussions/{id}/ - Soft delete discussion
    - POST /discussions/{id}/pin/ - Pin discussion (leaders only)
    """

    permission_classes = [IsAuthenticated,
                          IsGroupMember, IsAuthorOrGroupLeaderOrReadOnly]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group', 'category', 'is_pinned']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'comment_count', 'reaction_count']
    ordering = ['-is_pinned', '-created_at']

    def get_queryset(self):
        """Return discussions from user's groups only."""
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        # Return discussions from those groups (not deleted)
        queryset = Discussion.objects.filter(
            group_id__in=user_groups,
            is_deleted=False
        ).select_related('group', 'author').prefetch_related(
            Prefetch('comments', queryset=Comment.objects.filter(
                is_deleted=False))
        )

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DiscussionListSerializer
        elif self.action == 'create':
            return DiscussionCreateSerializer
        else:
            return DiscussionDetailSerializer

    def get_throttles(self):
        """Apply throttling only on create."""
        if self.action == 'create':
            return [DiscussionCreateThrottle(), BurstProtectionThrottle()]
        return []

    def perform_create(self, serializer):
        """Set author to current user."""
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanModerateGroup])
    def pin(self, request, pk=None):
        """Pin/unpin a discussion (leaders only)."""
        discussion = self.get_object()
        discussion.is_pinned = not discussion.is_pinned
        discussion.save(update_fields=['is_pinned'])

        serializer = self.get_serializer(discussion)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGroupMember])
    def report(self, request, pk=None):
        """Report a discussion for moderation."""
        from .serializers import ContentReportCreateSerializer
        from django.contrib.contenttypes.models import ContentType

        discussion = self.get_object()

        # Create report data
        data = {
            'content_type': ContentType.objects.get_for_model(discussion).id,
            'object_id': str(discussion.id),
            'reason': request.data.get('reason'),
            'details': request.data.get('details', ''),
        }

        serializer = ContentReportCreateSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': 'Content reported successfully.'},
            status=status.HTTP_201_CREATED
        )


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Comment CRUD operations.

    Endpoints:
    - GET /comments/ - List comments (filtered by discussion, scripture, prayer, or testimony)
    - POST /comments/ - Create comment
    - GET /comments/{id}/ - Get comment detail
    - PUT/PATCH /comments/{id}/ - Update comment (within 15 min)
    - DELETE /comments/{id}/ - Soft delete comment
    - GET /comments/{id}/history/ - Get edit history

    Filtering:
    - ?discussion=<uuid> - Comments on a discussion
    - ?scripture=<uuid> - Comments on a scripture
    - ?prayer=<uuid> - Comments on a prayer request
    - ?testimony=<uuid> - Comments on a testimony
    - ?parent=<uuid> - Replies to a specific comment
    """

    permission_classes = [IsAuthenticated, IsGroupMember, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = CommentFilter
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_queryset(self):
        """
        Return comments from user's groups only.
        Works with polymorphic content (discussions, scriptures, prayers, testimonies).
        """
        from django.contrib.contenttypes.models import ContentType
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        # Get content types for all commentable models
        discussion_type = ContentType.objects.get_for_model(Discussion)

        # Build Q objects for filtering by group
        # For discussions: filter by discussion__group_id
        # For scriptures/prayers/testimonies: filter by their respective group_id fields

        # Start with base queryset
        queryset = Comment.objects.filter(is_deleted=False)

        # Filter by user's groups based on content type
        # This uses a Q filter to check different FK paths depending on content_type
        group_filter = Q()

        # Discussion comments (both old discussion FK and new polymorphic)
        group_filter |= Q(discussion__group_id__in=user_groups)
        group_filter |= Q(
            content_type=discussion_type,
            content_id__in=Discussion.objects.filter(
                group_id__in=user_groups).values_list('id', flat=True)
        )

        # Scripture comments
        try:
            scripture_type = ContentType.objects.get_for_model(Scripture)
            group_filter |= Q(
                content_type=scripture_type,
                content_id__in=Scripture.objects.filter(
                    group_id__in=user_groups).values_list('id', flat=True)
            )
        except:
            pass

        # Prayer comments
        try:
            prayer_type = ContentType.objects.get_for_model(PrayerRequest)
            group_filter |= Q(
                content_type=prayer_type,
                content_id__in=PrayerRequest.objects.filter(
                    group_id__in=user_groups).values_list('id', flat=True)
            )
        except:
            pass

        # Testimony comments
        try:
            testimony_type = ContentType.objects.get_for_model(Testimony)
            group_filter |= Q(
                content_type=testimony_type,
                content_id__in=Testimony.objects.filter(
                    group_id__in=user_groups).values_list('id', flat=True)
            )
        except:
            pass

        queryset = queryset.filter(group_filter).select_related(
            'content_type', 'author', 'parent', 'discussion'
        ).prefetch_related('replies')

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CommentSimpleSerializer
        elif self.action == 'create':
            return CommentCreateSerializer
        else:
            return CommentSerializer

    def get_throttles(self):
        """Apply throttling only on create."""
        if self.action == 'create':
            return [CommentCreateThrottle(), BurstProtectionThrottle()]
        return []

    def perform_create(self, serializer):
        """Set author to current user."""
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get edit history for a comment."""
        comment = self.get_object()
        history = CommentHistory.objects.filter(
            comment=comment).order_by('-edited_at')
        serializer = CommentHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGroupMember])
    def report(self, request, pk=None):
        """Report a comment for moderation."""
        from .serializers import ContentReportCreateSerializer
        from django.contrib.contenttypes.models import ContentType

        comment = self.get_object()

        # Create report data
        data = {
            'content_type': ContentType.objects.get_for_model(comment).id,
            'object_id': str(comment.id),
            'reason': request.data.get('reason'),
            'details': request.data.get('details', ''),
        }

        serializer = ContentReportCreateSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': 'Content reported successfully.'},
            status=status.HTTP_201_CREATED
        )


class ReactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Reaction operations.

    Endpoints:
    - GET /reactions/ - List reactions (filtered by discussion/comment)
    - POST /reactions/ - Create reaction (toggle existing)
    - DELETE /reactions/{id}/ - Remove reaction

    Note: PUT/PATCH not allowed - reactions are create/delete only
    """

    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated, IsGroupMember, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['discussion', 'comment', 'reaction_type']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        """Return reactions from user's group discussions only."""
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        # Return reactions from discussions in those groups
        queryset = Reaction.objects.filter(
            Q(discussion__group_id__in=user_groups) |
            Q(comment__discussion__group_id__in=user_groups)
        ).select_related('user', 'discussion', 'comment')

        return queryset

    def get_throttles(self):
        """Apply throttling only on create."""
        if self.action == 'create':
            return [ReactionCreateThrottle(), BurstProtectionThrottle()]
        return []

    def create(self, request, *args, **kwargs):
        """
        Create reaction or toggle if already exists.

        If user already reacted with same type, remove it (toggle off).
        If user reacted with different type, update it.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        reaction_type = serializer.validated_data['reaction_type']
        discussion = serializer.validated_data.get('discussion')
        comment = serializer.validated_data.get('comment')

        # Check for existing reaction
        if discussion:
            existing = Reaction.objects.filter(
                user=user,
                discussion=discussion
            ).first()
        else:
            existing = Reaction.objects.filter(
                user=user,
                comment=comment
            ).first()

        if existing:
            if existing.reaction_type == reaction_type:
                # Toggle off - delete the reaction
                existing.delete()
                return Response(
                    {'detail': 'Reaction removed'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                # Update reaction type
                existing.reaction_type = reaction_type
                existing.save(update_fields=['reaction_type'])
                return Response(
                    ReactionSerializer(existing).data,
                    status=status.HTTP_200_OK
                )

        # Create new reaction
        serializer.save(user=user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Group Feed (read-only).

    Endpoints:
    - GET /feed/ - List feed items for user's groups
    - GET /feed/{id}/ - Get specific feed item
    - POST /feed/{id}/mark-viewed/ - Mark item as viewed
    - POST /feed/mark-all-viewed/ - Mark all items as viewed

    Feed items are auto-populated via signals, no manual creation.

    Supports content_type filtering with aliases:
    - 'discussion' or 'prayer' or 'testimony' or 'scripture'
    - 'prayer_request' (alias for 'prayer')

    View Tracking:
    - Each feed item has a 'has_viewed' field indicating if current user viewed it
    - Uses optimized prefetch_related to avoid N+1 queries
    """

    serializer_class = FeedItemSerializer
    permission_classes = [IsAuthenticated, IsGroupMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = FeedItemFilter  # Use custom filter instead of filterset_fields
    ordering_fields = ['created_at', 'comment_count', 'reaction_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Return feed items from user's groups with optimized view tracking.

        Uses prefetch_related to efficiently load view status for current user,
        avoiding N+1 query problems.
        """
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        # Import FeedItemView here to avoid circular imports
        from .models import FeedItemView

        # Return feed items from those groups (not deleted)
        # Optimize: prefetch only current user's views
        queryset = FeedItem.objects.filter(
            group_id__in=user_groups,
            is_deleted=False
        ).select_related('group', 'author').prefetch_related(
            Prefetch(
                'views',
                queryset=FeedItemView.objects.filter(user=user),
                to_attr='user_views'
            )
        ).order_by('-created_at')

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Override list to use cached feed service for single-group queries.

        When querying a single group's feed, uses Redis caching for
        improved performance. Falls back to standard queryset for
        multi-group or complex queries.
        """
        # Check if this is a single-group query (can use caching)
        group_param = request.query_params.get('group')

        if group_param:
            # Single group query - use cached feed service
            try:
                # Parse pagination parameters
                page = int(request.query_params.get('page', 1))
                page_size = int(request.query_params.get('page_size', 25))
                content_type = request.query_params.get('content_type')

                # Get cached feed
                result = FeedService.get_feed(
                    group_id=group_param,
                    page=page,
                    page_size=page_size,
                    content_type=content_type,
                    user=request.user
                )

                # Return cached response with pagination
                return Response({
                    'results': result['items'],
                    'count': result['pagination']['total_count'],
                    'next': self._get_next_url(request, result['pagination']) if result['pagination']['has_next'] else None,
                    'previous': self._get_previous_url(request, result['pagination']) if result['pagination']['has_previous'] else None,
                    'cached': result['from_cache'],  # Debug info
                })
            except Exception as e:
                # Fall back to standard queryset on any error
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Feed cache failed, falling back to queryset: {e}")

        # Multi-group or complex query - use standard queryset
        return super().list(request, *args, **kwargs)

    def _get_next_url(self, request, pagination):
        """Generate next page URL."""
        if not pagination['has_next']:
            return None
        params = request.query_params.copy()
        params['page'] = pagination['page'] + 1
        return request.build_absolute_uri('?' + params.urlencode())

    def _get_previous_url(self, request, pagination):
        """Generate previous page URL."""
        if not pagination['has_previous']:
            return None
        params = request.query_params.copy()
        params['page'] = pagination['page'] - 1
        return request.build_absolute_uri('?' + params.urlencode())

    @action(detail=True, methods=['post'], url_path='mark-viewed')
    def mark_viewed(self, request, pk=None):
        """
        Mark a specific feed item as viewed by current user.

        Creates a FeedItemView record if it doesn't exist.
        Idempotent: calling multiple times has the same effect as calling once.

        Returns:
            200: Item marked as viewed (includes viewed_at timestamp)
        """
        from .models import FeedItemView

        feed_item = self.get_object()
        view, created = FeedItemView.objects.get_or_create(
            feed_item=feed_item,
            user=request.user
        )

        return Response({
            'detail': 'Marked as viewed',
            'viewed_at': view.viewed_at,
            'was_new': created
        })

    @action(detail=False, methods=['post'], url_path='mark-all-viewed')
    def mark_all_viewed(self, request):
        """
        Mark all feed items in current queryset as viewed.

        Useful for "mark all as read" functionality.
        Uses bulk_create for efficiency with ignore_conflicts=True to handle duplicates.

        Query parameters:
        - All standard filters apply (group, content_type, etc.)

        Returns:
            200: Count of items marked as viewed
        """
        from .models import FeedItemView

        # Get filtered queryset (respects all query params like group, content_type)
        feed_items = self.filter_queryset(self.get_queryset())

        # Create view records (bulk operation for efficiency)
        views_to_create = [
            FeedItemView(feed_item=item, user=request.user)
            for item in feed_items
        ]

        # Use ignore_conflicts to handle items already viewed
        FeedItemView.objects.bulk_create(
            views_to_create, ignore_conflicts=True)

        return Response({
            'detail': 'Marked all items as viewed',
            'count': len(views_to_create)
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user notification preferences.

    Endpoints:
    - GET /preferences/ - Get user's preferences
    - PUT/PATCH /preferences/ - Update preferences

    Each user has one preference object (auto-created).
    """

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        """Return only current user's preference."""
        return NotificationPreference.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create user's preference object."""
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj

    def list(self, request, *args, **kwargs):
        """Return user's preference as single object, not list."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ContentReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing content reports (leaders only).

    Endpoints:
    - GET /reports/ - List reports for groups user leads
    - GET /reports/{id}/ - Get report detail
    - PATCH /reports/{id}/ - Update report status
    - POST /reports/{id}/review/ - Resolve or dismiss report
    """

    from .serializers import ContentReportSerializer, ContentReportReviewSerializer
    from .models import ContentReport

    queryset = ContentReport.objects.all()
    serializer_class = ContentReportSerializer
    permission_classes = [IsAuthenticated, CanModerateGroup]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'reason', 'content_type']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    # Note: http_method_names doesn't restrict custom @action methods
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        """Return reports for groups user is a leader of."""
        from group.models import GroupMembership

        user = self.request.user

        # Get groups user is a leader/co-leader of OR where they're the main leader
        leader_groups = GroupMembership.objects.filter(
            user=user,
            role__in=['leader', 'co-leader'],
            status='active'
        ).values_list('group_id', flat=True)

        # Also include groups where user is the main leader
        main_leader_groups = Group.objects.filter(
            leader=user
        ).values_list('id', flat=True)

        # Combine both querysets
        all_leader_groups = set(list(leader_groups) + list(main_leader_groups))

        # Return reports from those groups
        queryset = ContentReport.objects.filter(
            content_type__model__in=['discussion', 'comment']
        ).select_related(
            'reporter',
            'reviewed_by',
            'content_type'
        )

        # Filter by group through the content object
        # This is a bit complex due to GenericForeignKey
        from django.db.models import Q
        from django.contrib.contenttypes.models import ContentType

        discussion_ct = ContentType.objects.get_for_model(Discussion)
        comment_ct = ContentType.objects.get_for_model(Comment)

        # Get discussion IDs and comment IDs from leader's groups
        discussion_ids = Discussion.objects.filter(
            group_id__in=all_leader_groups
        ).values_list('id', flat=True)

        comment_ids = Comment.objects.filter(
            discussion__group_id__in=all_leader_groups
        ).values_list('id', flat=True)

        queryset = queryset.filter(
            Q(content_type=discussion_ct, object_id__in=discussion_ids) |
            Q(content_type=comment_ct, object_id__in=comment_ids)
        )

        return queryset

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """
        Resolve or dismiss a report.

        Request body:
        {
            "action": "resolve" or "dismiss",
            "notes": "Optional notes about the decision"
        }
        """
        from .serializers import ContentReportReviewSerializer

        report = self.get_object()
        serializer = ContentReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')

        if action == 'resolve':
            report.resolve(reviewed_by=request.user, notes=notes)
            message = 'Report resolved successfully.'
        else:  # dismiss
            report.dismiss(reviewed_by=request.user, notes=notes)
            message = 'Report dismissed successfully.'

        # Return updated report
        response_serializer = self.get_serializer(report)
        return Response({
            'detail': message,
            'report': response_serializer.data
        })


# =============================================================================
# PHASE 2: FAITH FEATURES VIEWSETS
# =============================================================================

class PrayerRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Prayer Request CRUD operations.

    Endpoints:
    - GET /prayer-requests/ - List prayer requests
    - POST /prayer-requests/ - Create prayer request
    - GET /prayer-requests/{id}/ - Get prayer detail
    - PUT/PATCH /prayer-requests/{id}/ - Update prayer
    - DELETE /prayer-requests/{id}/ - Delete prayer
    - POST /prayer-requests/{id}/mark_answered/ - Mark as answered
    - POST /prayer-requests/{id}/pray/ - Add to praying count
    """

    permission_classes = [IsAuthenticated, IsGroupMember, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group', 'category', 'urgency', 'is_answered']
    search_fields = ['title', 'content', 'answer_description']
    ordering_fields = ['created_at', 'prayer_count', 'urgency']
    ordering = ['-urgency', '-created_at']

    def get_queryset(self):
        """Return prayer requests from user's groups only."""
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        return PrayerRequest.objects.filter(
            group_id__in=user_groups
        ).select_related('group', 'author')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PrayerRequestListSerializer
        elif self.action == 'create':
            return PrayerRequestCreateSerializer
        elif self.action == 'mark_answered':
            return PrayerRequestAnswerSerializer
        else:
            return PrayerRequestDetailSerializer

    def get_throttles(self):
        """Apply throttling on create and pray actions."""
        if self.action == 'create':
            return [DiscussionCreateThrottle(), BurstProtectionThrottle()]
        elif self.action == 'pray':
            return [BurstProtectionThrottle()]
        return []

    def perform_create(self, serializer):
        """Set author to current user."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-answered')
    def mark_answered(self, request, pk=None):
        """
        Mark prayer request as answered.

        Only the author can mark their prayer as answered.
        """
        prayer = self.get_object()

        # Check permission
        if prayer.author != request.user:
            return Response(
                {'detail': 'Only the author can mark this prayer as answered.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if prayer.is_answered:
            return Response(
                {'detail': 'This prayer is already marked as answered.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and mark as answered
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answer_description = serializer.validated_data.get(
            'answer_description', '')
        prayer.mark_answered(answer_description=answer_description)

        # Return updated prayer
        response_serializer = PrayerRequestDetailSerializer(
            prayer,
            context={'request': request}
        )

        return Response({
            'detail': 'Prayer marked as answered! Praise God! 🙏',
            'prayer': response_serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGroupMember])
    def pray(self, request, pk=None):
        """
        Increment prayer count (user is committing to pray).

        This increments the prayer_count to track how many people
        are praying for this request.
        """
        prayer = self.get_object()

        if prayer.is_answered:
            return Response(
                {'detail': 'This prayer has already been answered.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Increment prayer count
        prayer.increment_prayer_count()

        # Return updated prayer
        response_serializer = PrayerRequestDetailSerializer(
            prayer,
            context={'request': request}
        )

        return Response({
            'detail': f'You are now praying for this request. {prayer.prayer_count} people praying! 🙏',
            'prayer': response_serializer.data
        })


class TestimonyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Testimony CRUD operations.

    Endpoints:
    - GET /testimonies/ - List testimonies
    - POST /testimonies/ - Create testimony
    - GET /testimonies/{id}/ - Get testimony detail
    - PUT/PATCH /testimonies/{id}/ - Update testimony
    - DELETE /testimonies/{id}/ - Delete testimony
    - POST /testimonies/{id}/share_public/ - Share publicly
    - POST /testimonies/{id}/approve_public/ - Approve for public (leaders)
    """

    permission_classes = [IsAuthenticated, IsGroupMember, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group', 'is_public',
                        'is_public_approved', 'answered_prayer']
    search_fields = ['title', 'content']
    ordering_fields = ['created_at', 'reaction_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return testimonies from user's groups or public approved ones."""
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        # Return testimonies from user's groups OR public approved ones
        return Testimony.objects.filter(
            Q(group_id__in=user_groups) |
            Q(is_public=True, is_public_approved=True)
        ).select_related('group', 'author', 'answered_prayer', 'approved_by')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TestimonyListSerializer
        elif self.action == 'create':
            return TestimonyCreateSerializer
        elif self.action == 'share_public':
            return TestimonyPublicShareSerializer
        else:
            return TestimonyDetailSerializer

    def get_throttles(self):
        """Apply throttling on create."""
        if self.action == 'create':
            return [DiscussionCreateThrottle(), BurstProtectionThrottle()]
        return []

    def perform_create(self, serializer):
        """Set author to current user."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], url_path='share-public')
    def share_public(self, request, pk=None):
        """
        Share testimony publicly (requires approval).

        Only the author can share their testimony publicly.
        """
        testimony = self.get_object()

        # Check permission
        if testimony.author != request.user:
            return Response(
                {'detail': 'Only the author can share this testimony publicly.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if testimony.is_public:
            return Response(
                {'detail': 'This testimony is already shared publicly.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Share publicly (pending approval)
        testimony.share_publicly()

        # Return updated testimony
        response_serializer = TestimonyDetailSerializer(
            testimony,
            context={'request': request}
        )

        return Response({
            'detail': 'Testimony submitted for public sharing. Awaiting approval from group leaders.',
            'testimony': response_serializer.data
        })

    @action(detail=True, methods=['post'], url_path='approve-public',
            permission_classes=[IsAuthenticated, CanModerateGroup])
    def approve_public(self, request, pk=None):
        """
        Approve testimony for public sharing.

        Only group leaders can approve testimonies.
        """
        testimony = self.get_object()

        if not testimony.is_public:
            return Response(
                {'detail': 'This testimony has not been submitted for public sharing.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if testimony.is_public_approved:
            return Response(
                {'detail': 'This testimony is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Approve for public sharing
        testimony.is_public_approved = True
        testimony.approved_by = request.user
        testimony.save(update_fields=['is_public_approved', 'approved_by'])

        # Return updated testimony
        response_serializer = TestimonyDetailSerializer(
            testimony,
            context={'request': request}
        )

        return Response({
            'detail': 'Testimony approved for public sharing! 🌍',
            'testimony': response_serializer.data
        })


class ScriptureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Scripture sharing CRUD operations.

    Endpoints:
    - GET /scriptures/ - List scriptures
    - POST /scriptures/ - Create scripture share
    - GET /scriptures/{id}/ - Get scripture detail
    - PUT/PATCH /scriptures/{id}/ - Update scripture
    - DELETE /scriptures/{id}/ - Delete scripture
    - POST /scriptures/verse-lookup/ - Look up Bible verse via API
    """

    permission_classes = [IsAuthenticated, IsGroupMember, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group', 'translation', 'source']
    search_fields = ['reference', 'verse_text', 'personal_reflection']
    ordering_fields = ['created_at', 'reaction_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return scriptures from user's groups only."""
        user = self.request.user

        # Get groups user is a member of
        user_groups = GroupMembership.objects.filter(
            user=user,
            status='active'
        ).values_list('group_id', flat=True)

        return Scripture.objects.filter(
            group_id__in=user_groups
        ).select_related('group', 'author')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ScriptureListSerializer
        elif self.action == 'create':
            return ScriptureCreateSerializer
        elif self.action == 'verse_lookup':
            return ScriptureVerseSearchSerializer
        else:
            return ScriptureDetailSerializer

    def get_throttles(self):
        """Apply throttling on create and verse lookup."""
        if self.action in ['create', 'verse_lookup']:
            return [DiscussionCreateThrottle(), BurstProtectionThrottle()]
        return []

    def perform_create(self, serializer):
        """Set author to current user."""
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get', 'post'], url_path='verse-lookup')
    def verse_lookup(self, request):
        """
        Look up Bible verse using Bible API.

        Returns verse text and reference for easy scripture sharing.

        Query parameters (GET):
        - reference: Bible verse reference (e.g., "John 3:16" or "Romans 8:28-30")
        - translation: Bible translation (default: KJV)

        Body parameters (POST):
        - reference: Bible verse reference
        - translation: Bible translation (optional, default: KJV)
        """
        from .services.bible_api import bible_service

        # Validate request - use query_params for GET, data for POST
        data_source = request.query_params if request.method == 'GET' else request.data
        serializer = self.get_serializer(data=data_source)
        serializer.is_valid(raise_exception=True)

        reference = serializer.validated_data['reference']
        translation = serializer.validated_data.get('translation', 'KJV')

        try:
            # Fetch verse from Bible API
            verse_data = bible_service.get_verse(reference, translation)

            return Response({
                'detail': 'Verse found successfully! 📖',
                'verse': verse_data
            })

        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Error fetching verse: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


# =============================================================================
# PRIVATE MESSAGING VIEWSETS
# =============================================================================

class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for private conversation management.

    Endpoints:
    - GET /conversations/ - List all user's conversations
    - GET /conversations/{id}/ - Get conversation detail with messages
    - POST /conversations/group-inquiry/ - Create conversation with group leader
    - POST /conversations/start/ - Start peer-to-peer conversation with another user
    - POST /conversations/{id}/messages/ - Send message in conversation
    - PATCH /conversations/{id}/close/ - Close conversation
    - PATCH /conversations/{id}/reopen/ - Reopen conversation
    """

    permission_classes = [IsAuthenticated, IsConversationParticipant]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['last_message_at', 'created_at']
    ordering = ['-last_message_at']

    def get_queryset(self):
        """Return only conversations user is part of."""
        user = self.request.user
        return Conversation.objects.filter(
            participants=user
        ).prefetch_related('participants').select_related('group', 'closed_by')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'group_inquiry':
            return CreateConversationSerializer
        elif self.action == 'start':
            return StartConversationSerializer
        elif self.action == 'send_message':
            return SendMessageSerializer
        elif self.action == 'close':
            return CloseConversationSerializer
        return ConversationDetailSerializer

    def get_permissions(self):
        """Customize permissions per action."""
        if self.action in ['group_inquiry', 'start']:
            # Anyone authenticated can initiate a group inquiry or P2P conversation
            return [IsAuthenticated()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        """
        List all conversations for the current user.

        Query params:
        - status: Filter by status (active, closed, archived)
        """
        queryset = self.get_queryset()

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Apply ordering
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Get conversation detail with full message history.

        Also marks all messages as read for the current user.
        """
        conversation = self.get_object()

        # Mark messages as read
        conversation.mark_messages_as_read(request.user)

        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='group-inquiry')
    def group_inquiry(self, request):
        """
        Create or retrieve a conversation with a group leader.

        Request body:
        - group_id: UUID of the group
        - message: Initial message content

        Returns:
        - conversation: Conversation object with full message history
        - message: The newly created message
        - redirect_url: URL to redirect to the conversation
        - is_existing_conversation: Boolean indicating if conversation existed
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_id = serializer.validated_data['group_id']
        message_content = serializer.validated_data['message']

        # Get the group
        try:
            group = Group.objects.select_related('leader').get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {'error': 'group_not_found',
                    'message': 'The specified group does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get group leader
        leader = group.leader

        if not leader:
            return Response(
                {'error': 'no_leader',
                    'message': 'This group does not have a leader assigned.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is trying to message themselves
        if leader == request.user:
            return Response(
                {'error': 'cannot_message_self',
                    'message': 'You cannot message yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if conversation already exists between user and leader for this group
        existing_conversation = Conversation.objects.filter(
            participants=request.user,
            group=group,
            context_type='group_inquiry'
        ).filter(
            participants=leader
        ).first()

        is_existing = existing_conversation is not None

        if existing_conversation:
            conversation = existing_conversation
        else:
            # Create new conversation
            conversation = Conversation.objects.create(
                context_type='group_inquiry',
                group=group,
                status='active'
            )
            conversation.participants.add(request.user, leader)

        # Create the message
        message = PrivateMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_content
        )

        # Serialize response
        conversation_serializer = ConversationDetailSerializer(
            conversation,
            context={'request': request}
        )
        message_serializer = PrivateMessageSerializer(message)

        response_data = {
            'conversation': conversation_serializer.data,
            'message': message_serializer.data,
            'redirect_url': f'/messages/{conversation.id}',
            'is_existing_conversation': is_existing
        }

        response_status = status.HTTP_200_OK if is_existing else status.HTTP_201_CREATED
        return Response(response_data, status=response_status)

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        """
        Start a peer-to-peer conversation with another user.

        Request body:
        - recipient_id: UUID of the user to message
        - message: Initial message content
        - group_id: Optional group context

        Returns:
        - conversation: Conversation object with full message history
        - message: The newly created message
        - is_existing_conversation: Boolean indicating if conversation existed
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_id = serializer.validated_data['recipient_id']
        message_content = serializer.validated_data['message']
        group_id = serializer.validated_data.get('group_id')

        # Get the recipient user
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'user_not_found',
                    'message': 'The specified user does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate if sender can message recipient
        can_message, error_code = validate_can_message_user(
            request.user, recipient)

        if not can_message:
            error_messages = {
                'cannot_message_self': 'You cannot message yourself.',
                'no_shared_group': 'You and the recipient are not in any shared groups.',
            }
            return Response(
                {'error': error_code, 'message': error_messages.get(
                    error_code, 'Cannot message this user.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get optional group context
        group = None
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                return Response(
                    {'error': 'group_not_found',
                        'message': 'The specified group does not exist.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Get or create conversation
        conversation, created = get_or_create_direct_conversation(
            request.user,
            recipient,
            group=group
        )

        # Create the message (save() method will auto-update conversation.last_message_at)
        message = PrivateMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=message_content
        )

        # Serialize response
        conversation_serializer = ConversationDetailSerializer(
            conversation,
            context={'request': request}
        )
        message_serializer = PrivateMessageSerializer(message)

        response_data = {
            'conversation': conversation_serializer.data,
            'message': message_serializer.data,
            'is_existing_conversation': not created
        }

        response_status = status.HTTP_200_OK if not created else status.HTTP_201_CREATED
        return Response(response_data, status=response_status)

    @action(detail=True, methods=['post'], url_path='messages')
    def send_message(self, request, pk=None):
        """
        Send a message in an existing conversation.

        Request body:
        - content: Message content
        """
        conversation = self.get_object()

        # Check if conversation is closed
        if conversation.status == 'closed':
            return Response(
                {'error': 'conversation_closed',
                    'message': 'Cannot send messages to a closed conversation. Reopen it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if conversation.status == 'archived':
            return Response(
                {'error': 'conversation_archived',
                    'message': 'Cannot send messages to an archived conversation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create message
        message = PrivateMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=serializer.validated_data['content']
        )

        message_serializer = PrivateMessageSerializer(message)
        return Response(
            {'message': message_serializer.data},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['patch'])
    def close(self, request, pk=None):
        """
        Close a conversation.

        Request body (optional):
        - reason: Reason for closing (joined_group, not_interested, resolved, other)
        """
        conversation = self.get_object()

        if conversation.status == 'closed':
            return Response(
                {'error': 'already_closed',
                    'message': 'Conversation is already closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('reason')
        conversation.close(user=request.user, reason=reason)

        return Response({
            'conversation': {
                'id': str(conversation.id),
                'status': conversation.status,
                'closed_at': conversation.closed_at,
                'closed_by': {
                    'id': str(conversation.closed_by.id),
                    'username': conversation.closed_by.username,
                    'first_name': conversation.closed_by.first_name,
                    'last_name': conversation.closed_by.last_name,
                },
                'close_reason': conversation.close_reason,
            },
            'message': 'Conversation closed successfully.'
        })

    @action(detail=True, methods=['patch'])
    def reopen(self, request, pk=None):
        """
        Reopen a closed conversation.
        """
        conversation = self.get_object()

        if conversation.status != 'closed':
            return Response(
                {'error': 'not_closed',
                    'message': 'Only closed conversations can be reopened.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation.reopen()

        return Response({
            'conversation': {
                'id': str(conversation.id),
                'status': conversation.status,
                'closed_at': None,
                'reopened_at': conversation.updated_at,
            },
            'message': 'Conversation reopened successfully.'
        })
