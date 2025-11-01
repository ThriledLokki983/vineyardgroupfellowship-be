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
        description="Get a list of all active groups. Can filter by location, visibility, and availability.",
        tags=["Groups"],
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

    def get_queryset(self):
        """Filter queryset based on user permissions and query parameters."""
        queryset = super().get_queryset()
        user = self.request.user

        # Only show active groups by default
        if self.action == 'list':
            queryset = queryset.filter(is_active=True)

        # Filter by visibility
        if not user.is_staff:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='community', leader=user) |
                Q(visibility='community', co_leaders=user) |
                Q(visibility='community', members__user=user) |
                Q(visibility='private', leader=user) |
                Q(visibility='private', co_leaders=user) |
                Q(visibility='private', members__user=user)
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
                member_count=Count('members', filter=Q(
                    members__status='active'))
            ).filter(
                Q(member_count__lt=F('member_limit')) & Q(is_open=True)
            )

        return queryset

    def perform_create(self, serializer):
        """Create group and add creator as leader member."""
        group = serializer.save()

        # Create membership for the leader
        GroupMembership.objects.create(
            group=group,
            user=self.request.user,
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

        serializer.save()

    def perform_destroy(self, instance):
        """Only group leader can delete."""
        if self.request.user != instance.leader:
            raise PermissionError(
                "Only the group leader can delete this group.")

        # Soft delete by setting is_active to False
        instance.is_active = False
        instance.save()

    @extend_schema(
        summary="Get group members",
        description="Get list of all members in the group.",
        tags=["Groups"],
        responses={200: GroupMemberSerializer(many=True)},
    )
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of a group."""
        group = self.get_object()
        memberships = GroupMembership.objects.filter(
            group=group,
            status='active'
        ).select_related('user').order_by('role', 'joined_at')

        serializer = GroupMemberSerializer(memberships, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Join group",
        description="Request to join a group. Auto-approved for open groups, pending for closed groups.",
        tags=["Groups"],
        request=JoinGroupSerializer,
        responses={
            200: {"description": "Successfully joined group"},
            400: {"description": "Cannot join group (already member, group full, etc.)"},
        },
    )
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a group."""
        group = self.get_object()
        user = request.user

        # Check if already a member
        if GroupMembership.objects.filter(group=group, user=user).exists():
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

        # Create membership
        membership_status = 'active' if group.is_open else 'pending'
        serializer = JoinGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = GroupMembership.objects.create(
            group=group,
            user=user,
            role='member',
            status=membership_status,
            notes=serializer.validated_data.get('message', '')
        )

        message = (
            "Successfully joined group!" if membership_status == 'active'
            else "Membership request submitted. Awaiting leader approval."
        )

        return Response({
            "message": message,
            "membership": GroupMemberSerializer(membership).data
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

        # Only leaders can upload photos
        if not (user == group.leader or user in group.co_leaders.all()):
            return Response(
                {"error": "Only group leaders can upload photos."},
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
