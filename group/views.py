"""
Group views for managing fellowship groups.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from .models import Group, GroupMembership
from .serializers import (
    GroupSerializer,
    GroupListSerializer,
    GroupCreateSerializer,
    GroupMemberSerializer,
    JoinGroupSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List all groups",
        description="Get a list of all active groups. Can filter by location, visibility, availability, and membership.",
        tags=["Groups"],
        parameters=[
            OpenApiParameter(
                name='location',
                description='Filter by location (case-insensitive contains)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='is_open',
                description='Filter by open/closed status',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='has_space',
                description='Show only groups with available spots',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='my_groups',
                description='Show only groups where user is a member, co-leader, or leader',
                required=False,
                type=bool
            ),
        ]
    ),
    create=extend_schema(
        summary="Create a new group",
        description="Create a new fellowship group. User must have leadership permissions.",
        tags=["Groups"],
    ),
    retrieve=extend_schema(
        summary="Get group details",
        description="Get detailed information about a specific group including members.",
        tags=["Groups"],
    ),
    update=extend_schema(
        summary="Update group",
        description="Update group details. Only group leader and co-leaders can update.",
        tags=["Groups"],
    ),
    partial_update=extend_schema(
        summary="Partially update group",
        description="Partially update group details. Only group leader and co-leaders can update.",
        tags=["Groups"],
    ),
    destroy=extend_schema(
        summary="Delete group",
        description="Delete a group. Only the group leader can delete.",
        tags=["Groups"],
    ),
)
class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on Groups.
    """

    queryset = Group.objects.select_related(
        'leader').prefetch_related('co_leaders').all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return GroupListSerializer
        elif self.action == 'create':
            return GroupCreateSerializer
        return GroupSerializer

    def _is_group_leader(self, group, user):
        """
        Verify if user is a leader or co-leader of the group.

        This method performs database-level verification to ensure
        the user has leadership permissions, preventing frontend bypass.

        Args:
            group: Group instance
            user: User instance

        Returns:
            bool: True if user is leader or co-leader, False otherwise
        """
        # Check if user is the primary leader
        if group.leader_id == user.id:
            return True

        # Check if user is a co-leader (database query to prevent manipulation)
        is_co_leader = group.co_leaders.filter(id=user.id).exists()

        # Additional verification: Check if user has active leadership membership
        has_leadership_membership = GroupMembership.objects.filter(
            group=group,
            user=user,
            role__in=['leader', 'co_leader'],
            status='active'
        ).exists()

        return is_co_leader or has_leadership_membership

    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters."""
        queryset = super().get_queryset()
        user = self.request.user

        # Exclude archived groups by default (unless specifically requested)
        include_archived = self.request.query_params.get(
            'include_archived', 'false').lower() == 'true'
        if not include_archived:
            queryset = queryset.filter(archived_at__isnull=True)

        # Only show active groups by default
        if self.action == 'list':
            queryset = queryset.filter(is_active=True)

        # Filter by visibility
        if not user.is_staff:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='community', leader=user) |
                Q(visibility='community', co_leaders=user) |
                Q(visibility='community', memberships__user=user) |
                Q(visibility='private', leader=user) |
                Q(visibility='private', co_leaders=user) |
                Q(visibility='private', memberships__user=user)
            ).distinct()

        # Query parameters for filtering
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        is_open = self.request.query_params.get('is_open')
        if is_open is not None:
            queryset = queryset.filter(is_open=is_open.lower() == 'true')

        has_space = self.request.query_params.get('has_space')
        if has_space and has_space.lower() == 'true':
            queryset = queryset.annotate(
                member_count=Count('memberships', filter=Q(
                    memberships__status='active'))
            ).filter(
                Q(member_count__lt=F('member_limit')) & Q(is_open=True)
            )

        # Filter by my groups (groups user is a member of, created, or has pending request for)
        my_groups = self.request.query_params.get('my_groups')
        if my_groups and my_groups.lower() == 'true':
            queryset = queryset.filter(
                Q(leader=user) |
                Q(co_leaders=user) |
                Q(memberships__user=user, memberships__status='active') |
                Q(memberships__user=user, memberships__status='pending')
            ).distinct()

        return queryset

    def perform_create(self, serializer):
        """Create group and add creator as leader member."""
        user = self.request.user

        # Check if user already has an active group they created
        existing_group = Group.objects.filter(
            created_by=user,
            is_active=True,
            archived_at__isnull=True
        ).first()

        if existing_group:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'error': 'You already have an active group. Please archive your current group before creating a new one.',
                'existing_group': {
                    'id': str(existing_group.id),
                    'name': existing_group.name
                }
            })

        # Save group with created_by and last_updated_by set to the current user
        group = serializer.save(created_by=user, last_updated_by=user)

        # Create membership for the leader
        GroupMembership.objects.create(
            group=group,
            user=user,
            role='leader',
            status='active'
        )

    def perform_update(self, serializer):
        """Only leader and co-leaders can update."""
        group = self.get_object()
        user = self.request.user

        # Check permissions
        if not (user == group.leader or user in group.co_leaders.all()):
            raise PermissionError(
                "Only group leaders can update group details.")

        # Track who updated the group
        serializer.save(last_updated_by=user)

    def perform_destroy(self, instance):
        """Archive the group instead of hard delete (soft delete)."""
        if self.request.user != instance.leader:
            raise PermissionError(
                "Only the group leader can delete this group.")

        # Archive the group (soft delete) and track who archived it
        instance.archive(user=self.request.user)

    @extend_schema(
        summary="Get group members",
        description="Get list of all members in the group.",
        tags=["Groups"],
        responses={200: GroupMemberSerializer(many=True)},
    )
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all active members of a group."""
        group = self.get_object()
        memberships = GroupMembership.objects.filter(
            group=group,
            status='active'
        ).select_related(
            'user',
            'user__basic_profile',
            'user__profile_photo'
        ).order_by('role', 'joined_at')

        serializer = GroupMemberSerializer(
            memberships,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Join group",
        description="Request to join a group. All requests require leader approval.",
        tags=["Groups"],
        request=JoinGroupSerializer,
        responses={
            200: {"description": "Join request submitted successfully"},
            400: {"description": "Cannot join group (already member, group full, etc.)"},
        },
    )
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Request to join a group."""
        group = self.get_object()
        user = request.user

        # Check if already a member
        existing_membership = GroupMembership.objects.filter(
            group=group,
            user=user
        ).first()

        if existing_membership:
            if existing_membership.status == 'pending':
                return Response(
                    {"error": "You already have a pending request for this group."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing_membership.status == 'active':
                return Response(
                    {"error": "You are already a member of this group."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if group can accept members
        if not group.can_accept_members:
            return Response(
                {"error": "This group is not accepting new members."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create membership with pending status (requires leader approval)
        serializer = JoinGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = GroupMembership.objects.create(
            group=group,
            user=user,
            role='member',
            status='pending',  # Always pending - requires leader approval
            notes=serializer.validated_data.get('message', '')
        )

        return Response({
            "message": "Join request submitted successfully. Awaiting leader approval.",
            "membership": GroupMemberSerializer(membership, context={'request': request}).data
        })

    @extend_schema(
        summary="Leave group",
        description="Leave a group you are a member of.",
        tags=["Groups"],
        responses={
            200: {"description": "Successfully left group"},
            400: {"description": "Not a member of this group"},
        },
    )
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a group."""
        group = self.get_object()
        user = request.user

        # Cannot leave if you're the leader
        if user == group.leader:
            return Response(
                {"error": "Group leader cannot leave. Please transfer leadership first or delete the group."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get membership
        try:
            membership = GroupMembership.objects.get(group=group, user=user)
        except GroupMembership.DoesNotExist:
            return Response(
                {"error": "You are not a member of this group."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update membership status
        membership.status = 'inactive'
        membership.left_at = timezone.now()
        membership.save()

        return Response({
            "message": "Successfully left group."
        })

    @extend_schema(
        summary="Upload group photo",
        description="Upload a photo for the group. Only leaders can upload photos.",
        tags=["Groups"],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'photo': {
                        'type': 'string',
                        'format': 'binary',
                    }
                }
            }
        },
        responses={
            200: GroupSerializer,
            400: {"description": "Invalid photo or permission denied"},
        },
    )
    @action(detail=True, methods=['post'])
    def upload_photo(self, request, pk=None):
        """Upload a photo for the group."""
        group = self.get_object()
        user = request.user

        # Verify leadership status with database-level validation
        if not self._is_group_leader(group, user):
            return Response(
                {"error": "Only group leaders and co-leaders can upload photos."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get photo from request
        photo = request.FILES.get('photo')
        if not photo:
            return Response(
                {"error": "No photo file provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update group photo
        group.photo = photo
        group.save()

        serializer = self.get_serializer(group)
        return Response(serializer.data)

    @extend_schema(
        summary="List pending join requests",
        description="Get all pending membership requests for the group. Only accessible by group leaders.",
        tags=["Groups"],
        responses={
            200: GroupMemberSerializer(many=True),
            403: {"description": "Permission denied - only leaders can view pending requests"},
        },
    )
    @action(detail=True, methods=['get'])
    def pending_requests(self, request, pk=None):
        """List all pending membership requests for the group."""
        group = self.get_object()
        user = request.user

        # Verify leadership status with database-level validation
        if not self._is_group_leader(group, user):
            return Response(
                {"error": "Only group leaders and co-leaders can view pending membership requests."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all pending memberships
        pending_memberships = GroupMembership.objects.filter(
            group=group,
            status='pending'
        ).select_related(
            'user',
            'user__basic_profile',
            'user__profile_photo'
        ).order_by('joined_at')

        serializer = GroupMemberSerializer(
            pending_memberships,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Approve membership request",
        description="Approve a pending membership request. Only accessible by group leaders.",
        tags=["Groups"],
        responses={
            200: {"description": "Membership request approved"},
            400: {"description": "Invalid request or membership not found"},
            403: {"description": "Permission denied - only leaders can approve requests"},
        },
    )
    @action(detail=True, methods=['post'], url_path='approve-request/(?P<membership_id>[^/.]+)')
    def approve_request(self, request, pk=None, membership_id=None):
        """Approve a pending membership request."""
        group = self.get_object()
        user = request.user

        # Verify leadership status with database-level validation
        if not self._is_group_leader(group, user):
            return Response(
                {"error": "Only group leaders and co-leaders can approve membership requests."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the membership with additional validation
        try:
            membership = GroupMembership.objects.select_related('user').get(
                id=membership_id,
                group=group,
                status='pending'
            )
        except GroupMembership.DoesNotExist:
            return Response(
                {"error": "Pending membership request not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the membership belongs to the correct group (double-check)
        if membership.group.id != group.id:
            return Response(
                {"error": "Invalid membership request for this group."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if group is full
        if group.is_full:
            return Response(
                {"error": "Cannot approve request. Group is full."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Approve the membership
        membership.status = 'active'
        membership.save()

        return Response({
            "message": f"Membership request approved for {membership.user.email}.",
            "membership": GroupMemberSerializer(membership, context={'request': request}).data
        })

    @extend_schema(
        summary="Reject membership request",
        description="Reject a pending membership request. Only accessible by group leaders.",
        tags=["Groups"],
        responses={
            200: {"description": "Membership request rejected"},
            400: {"description": "Invalid request or membership not found"},
            403: {"description": "Permission denied - only leaders can reject requests"},
        },
    )
    @action(detail=True, methods=['post'], url_path='reject-request/(?P<membership_id>[^/.]+)')
    def reject_request(self, request, pk=None, membership_id=None):
        """Reject a pending membership request."""
        group = self.get_object()
        user = request.user

        # Verify leadership status with database-level validation
        if not self._is_group_leader(group, user):
            return Response(
                {"error": "Only group leaders and co-leaders can reject membership requests."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the membership with additional validation
        try:
            membership = GroupMembership.objects.select_related('user').get(
                id=membership_id,
                group=group,
                status='pending'
            )
        except GroupMembership.DoesNotExist:
            return Response(
                {"error": "Pending membership request not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the membership belongs to the correct group (double-check)
        if membership.group.id != group.id:
            return Response(
                {"error": "Invalid membership request for this group."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Store email before deletion for response message
        user_email = membership.user.email

        # Delete the membership request (or you could set status to 'rejected' if you want to keep history)
        membership.delete()

        return Response({
            "message": f"Membership request rejected for {user_email}."
        })
