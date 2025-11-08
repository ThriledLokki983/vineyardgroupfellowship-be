"""
Group serializers for DRF API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field

from .models import Group, GroupMembership

User = get_user_model()


class GroupLeaderSerializer(serializers.ModelSerializer):
    """Serializer for group leader information."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'display_name']
        read_only_fields = ['id', 'email', 'display_name']

    def get_display_name(self, obj):
        """Get leader's display name from profile."""
        try:
            return obj.basic_profile.display_name_or_email
        except:
            return obj.email


class GroupMemberSerializer(serializers.ModelSerializer):
    """Serializer for group member information."""

    user_id = serializers.UUIDField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    profile_visibility = serializers.SerializerMethodField()

    class Meta:
        model = GroupMembership
        fields = [
            'id',
            'user_id',
            'email',
            'first_name',
            'last_name',
            'display_name',
            'bio',
            'photo_url',
            'profile_visibility',
            'role',
            'status',
            'joined_at',
        ]
        read_only_fields = [
            'id',
            'user_id',
            'email',
            'first_name',
            'last_name',
            'display_name',
            'bio',
            'photo_url',
            'profile_visibility',
            'joined_at',
        ]

    def get_first_name(self, obj):
        """Get member's first name from profile."""
        try:
            return obj.user.basic_profile.first_name or ''
        except:
            return ''

    def get_last_name(self, obj):
        """Get member's last name from profile."""
        try:
            return obj.user.basic_profile.last_name or ''
        except:
            return ''

    def get_display_name(self, obj):
        """Get member's display name from profile."""
        try:
            return obj.user.basic_profile.display_name_or_email
        except:
            return obj.user.email

    def get_bio(self, obj):
        """Get member's bio from profile."""
        try:
            return obj.user.basic_profile.bio or ''
        except:
            return ''

    def get_photo_url(self, obj):
        """Get member's photo URL."""
        try:
            profile_photo = obj.user.profile_photo
            if profile_photo and profile_photo.photo:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile_photo.photo.url)
        except:
            pass
        return None

    def get_profile_visibility(self, obj):
        """Get member's profile visibility setting."""
        try:
            return obj.user.basic_profile.profile_visibility
        except:
            return 'private'  # Default to private if not set


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Group model with full details.
    """

    # Leader information
    leader_info = GroupLeaderSerializer(source='leader', read_only=True)
    co_leaders_info = GroupLeaderSerializer(
        many=True, source='co_leaders', read_only=True)

    # Audit fields
    created_by_info = GroupLeaderSerializer(
        source='created_by', read_only=True)
    last_updated_by_info = GroupLeaderSerializer(
        source='last_updated_by', read_only=True)
    archived_by_info = GroupLeaderSerializer(
        source='archived_by', read_only=True)

    # Computed fields
    current_member_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    available_spots = serializers.IntegerField(read_only=True)
    can_accept_members = serializers.BooleanField(read_only=True)

    # Photo URL
    photo_url = serializers.SerializerMethodField()

    # User's membership status
    user_membership = serializers.SerializerMethodField()

    # Group members list
    group_members = serializers.SerializerMethodField()

    # Location-based fields
    distance_km = serializers.SerializerMethodField()
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    geocoded_address = serializers.CharField(read_only=True, allow_blank=True)

    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'description',
            'location',
            'location_type',
            'member_limit',
            'current_member_count',
            'is_full',
            'available_spots',
            'is_open',
            'is_active',
            'can_accept_members',
            'leader',
            'leader_info',
            'co_leaders',
            'co_leaders_info',
            'created_by',
            'created_by_info',
            'last_updated_by',
            'last_updated_by_info',
            'archived_by',
            'archived_by_info',
            'archived_at',
            'photo',
            'photo_url',
            'meeting_day',
            'meeting_time',
            'meeting_frequency',
            'focus_areas',
            'visibility',
            'user_membership',
            'group_members',
            'latitude',
            'longitude',
            'geocoded_address',
            'distance_km',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'current_member_count',
            'is_full',
            'available_spots',
            'can_accept_members',
            'leader_info',
            'co_leaders_info',
            'created_by',
            'created_by_info',
            'last_updated_by',
            'last_updated_by_info',
            'archived_by',
            'archived_by_info',
            'archived_at',
            'photo_url',
            'user_membership',
            'group_members',
            'geocoded_address',
            'distance_km',
            'created_at',
            'updated_at',
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj):
        """Get the Base64 data URL for the group photo."""
        if obj.photo:
            # Photo is already a Base64 data URL, return as-is
            return obj.photo
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_user_membership(self, obj):
        """Get current user's membership status in this group."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        try:
            membership = GroupMembership.objects.get(
                group=obj,
                user=request.user
            )
            return {
                'id': str(membership.id),
                'role': membership.role,
                'status': membership.status,
                'joined_at': membership.joined_at.isoformat(),
            }
        except GroupMembership.DoesNotExist:
            return None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, obj):
        """
        Get distance from user's location in kilometers.

        This field is populated when groups are filtered by location
        using the find_nearby_groups utility or when the distance
        annotation is added to the queryset.
        """
        # Check if distance was annotated by the queryset
        if hasattr(obj, 'distance'):
            # Distance is a Distance object, convert to km
            return round(obj.distance.km, 2)
        return None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_group_members(self, obj):
        """Get all group members including the leader."""
        # Get all active memberships for this group
        memberships = GroupMembership.objects.filter(
            group=obj,
            status='active'
        ).select_related(
            'user',
            'user__basic_profile',
            'user__profile_photo'
        ).order_by('-role', 'joined_at')  # Leaders first, then by join date

        # Use the GroupMemberSerializer to serialize each membership
        serializer = GroupMemberSerializer(
            memberships,
            many=True,
            context=self.context
        )
        return serializer.data

    def validate_member_limit(self, value):
        """Validate member limit."""
        if value < 2:
            raise serializers.ValidationError(
                "Group must allow at least 2 members.")
        if value > 100:
            raise serializers.ValidationError(
                "Group cannot exceed 100 members.")
        return value

    def validate_leader(self, value):
        """Validate that leader has leadership permissions."""
        try:
            profile = value.basic_profile
            if not profile.leadership_info.get('can_lead_group', False):
                raise serializers.ValidationError(
                    "User does not have permission to lead groups. "
                    "Please complete leadership onboarding first."
                )
        except:
            raise serializers.ValidationError(
                "User profile not found or incomplete."
            )
        return value


class GroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing groups.
    """

    leader_info = GroupLeaderSerializer(source='leader', read_only=True)
    current_member_count = serializers.IntegerField(read_only=True)
    available_spots = serializers.IntegerField(read_only=True)
    photo_url = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()
    request_date = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'description',
            'location',
            'location_type',
            'member_limit',
            'current_member_count',
            'available_spots',
            'is_open',
            'is_active',
            'leader_info',
            'photo_url',
            'meeting_day',
            'meeting_time',
            'meeting_frequency',
            'focus_areas',
            'membership_status',
            'request_date',
            'created_at',
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_photo_url(self, obj):
        """Get the Base64 data URL for the group photo."""
        if obj.photo:
            # Photo is already a Base64 data URL, return as-is
            return obj.photo
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_membership_status(self, obj):
        """
        Get current user's membership status in this group.

        Returns:
            - 'leader' if user is the group leader
            - 'co_leader' if user is a co-leader
            - 'active' if user is an active member
            - 'pending' if user has a pending join request
            - None if user has no relationship with this group
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        user = request.user

        # Check if user is the leader
        if obj.leader_id == user.id:
            return 'leader'

        # Check if user is a co-leader
        if obj.co_leaders.filter(id=user.id).exists():
            return 'co_leader'

        # Check membership status
        try:
            membership = GroupMembership.objects.get(
                group=obj,
                user=user
            )
            return membership.status  # Returns 'active' or 'pending'
        except GroupMembership.DoesNotExist:
            return None

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_request_date(self, obj):
        """
        Get the date when user requested to join this group.

        Returns the timestamp when the join request was submitted.
        Only applicable for pending requests.

        Returns:
            - ISO 8601 datetime string if user has a pending or active membership
            - None if user has no relationship with this group
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        user = request.user

        # Leaders and co-leaders don't have a request date
        if obj.leader_id == user.id or obj.co_leaders.filter(id=user.id).exists():
            return None

        # Get the membership request date
        try:
            membership = GroupMembership.objects.get(
                group=obj,
                user=user
            )
            # Return the joined_at timestamp (when request was created)
            return membership.joined_at.isoformat() if membership.joined_at else None
        except GroupMembership.DoesNotExist:
            return None


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new group.
    """

    class Meta:
        model = Group
        fields = [
            'name',
            'description',
            'location',
            'location_type',
            'member_limit',
            'is_open',
            'meeting_day',
            'meeting_time',
            'meeting_frequency',
            'focus_areas',
            'visibility',
        ]

    def validate(self, attrs):
        """Validate group creation data."""
        # Leader is set automatically to the current user
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        # Check if user can lead groups
        try:
            profile = request.user.basic_profile
            if not profile.leadership_info.get('can_lead_group', False):
                raise serializers.ValidationError(
                    "You do not have permission to create groups. "
                    "Please complete leadership onboarding first."
                )
        except:
            raise serializers.ValidationError(
                "Profile not found. Please complete your profile first."
            )

        return attrs

    def create(self, validated_data):
        """Create group with current user as leader."""
        request = self.context['request']
        validated_data['leader'] = request.user
        return super().create(validated_data)


class JoinGroupSerializer(serializers.Serializer):
    """
    Serializer for joining a group.
    """

    message = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional message to group leader"
    )
