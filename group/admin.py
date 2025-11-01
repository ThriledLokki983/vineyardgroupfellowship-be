"""
Admin configuration for Group app.
"""

from django.contrib import admin
from .models import Group, GroupMembership


class GroupMembershipInline(admin.TabularInline):
    """Inline admin for group memberships."""
    model = GroupMembership
    extra = 0
    fields = ('user', 'role', 'status', 'joined_at', 'left_at')
    readonly_fields = ('joined_at', 'left_at')
    autocomplete_fields = ['user']


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Admin interface for Group model."""

    list_display = (
        'name',
        'leader',
        'location',
        'current_member_count',
        'member_limit',
        'is_open',
        'is_active',
        'visibility',
        'created_at',
    )

    list_filter = (
        'is_active',
        'is_open',
        'visibility',
        'location_type',
        'meeting_day',
        'meeting_frequency',
        'created_at',
    )

    search_fields = (
        'name',
        'description',
        'location',
        'leader__email',
    )

    readonly_fields = (
        'id',
        'current_member_count',
        'is_full',
        'available_spots',
        'can_accept_members',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'name',
                'description',
                'photo',
            )
        }),
        ('Location', {
            'fields': (
                'location',
                'location_type',
            )
        }),
        ('Leadership', {
            'fields': (
                'leader',
                'co_leaders',
            )
        }),
        ('Membership', {
            'fields': (
                'member_limit',
                'current_member_count',
                'available_spots',
                'is_full',
                'can_accept_members',
                'is_open',
            )
        }),
        ('Meeting Schedule', {
            'fields': (
                'meeting_day',
                'meeting_time',
                'meeting_frequency',
            )
        }),
        ('Settings', {
            'fields': (
                'focus_areas',
                'visibility',
                'is_active',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    filter_horizontal = ('co_leaders',)
    autocomplete_fields = ['leader']
    inlines = [GroupMembershipInline]

    def get_queryset(self, request):
        """Optimize queryset with select_related and prefetch_related."""
        qs = super().get_queryset(request)
        return qs.select_related('leader').prefetch_related('co_leaders', 'members')


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    """Admin interface for GroupMembership model."""

    list_display = (
        'user',
        'group',
        'role',
        'status',
        'joined_at',
        'left_at',
    )

    list_filter = (
        'role',
        'status',
        'joined_at',
        'left_at',
    )

    search_fields = (
        'user__email',
        'group__name',
        'notes',
    )

    readonly_fields = (
        'id',
        'joined_at',
    )

    fieldsets = (
        ('Membership', {
            'fields': (
                'id',
                'group',
                'user',
                'role',
                'status',
            )
        }),
        ('Timeline', {
            'fields': (
                'joined_at',
                'left_at',
            )
        }),
        ('Notes', {
            'fields': (
                'notes',
            )
        }),
    )

    autocomplete_fields = ['user', 'group']

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'group')
