"""
Management views for one-time administrative tasks.
These should only be used in production with proper authentication.
"""
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from decouple import config
import json

User = get_user_model()


@csrf_exempt
@require_POST
def create_admin_user(request):
    """Create an admin user if one doesn't exist."""

    # Allow this operation in production for initial setup
    # In a production environment, this should be secured or removed after use
    try:
        # Get credentials from environment
        admin_email = config('ADMIN_EMAIL', default='')
        admin_password = config('ADMIN_PASSWORD', default='')

        if not admin_email or not admin_password:
            return JsonResponse({
                'error': 'ADMIN_EMAIL and ADMIN_PASSWORD environment variables must be set'
            }, status=400)

        # Check if admin user already exists
        if User.objects.filter(email=admin_email).exists():
            return JsonResponse({
                'message': f'Admin user with email {admin_email} already exists',
                'created': False
            })

        # Create the admin user
        admin_user = User.objects.create_user(
            email=admin_email,
            password=admin_password,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )

        return JsonResponse({
            'message': f'Admin user created successfully with email: {admin_email}',
            'created': True,
            'user_id': admin_user.id
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to create admin user: {str(e)}'
        }, status=500)


@csrf_exempt
@require_POST
def recalculate_comment_counts(request):
    """Recalculate comment counts for all content types."""
    try:
        from messaging.models import Discussion, Scripture, PrayerRequest, Testimony, Comment
        from django.contrib.contenttypes.models import ContentType
        
        results = {
            'scripture': 0,
            'prayer_request': 0,
            'testimony': 0,
            'discussion': 0
        }
        
        # Scripture
        scripture_ct = ContentType.objects.get_for_model(Scripture)
        for scripture in Scripture.objects.all():
            count = Comment.objects.filter(
                content_type=scripture_ct,
                content_id=scripture.id,
                is_deleted=False
            ).count()
            if scripture.comment_count != count:
                scripture.comment_count = count
                scripture.save(update_fields=['comment_count'])
                results['scripture'] += 1

        # PrayerRequest
        prayer_ct = ContentType.objects.get_for_model(PrayerRequest)
        for prayer in PrayerRequest.objects.all():
            count = Comment.objects.filter(
                content_type=prayer_ct,
                content_id=prayer.id,
                is_deleted=False
            ).count()
            if prayer.comment_count != count:
                prayer.comment_count = count
                prayer.save(update_fields=['comment_count'])
                results['prayer_request'] += 1

        # Testimony
        testimony_ct = ContentType.objects.get_for_model(Testimony)
        for testimony in Testimony.objects.all():
            count = Comment.objects.filter(
                content_type=testimony_ct,
                content_id=testimony.id,
                is_deleted=False
            ).count()
            if testimony.comment_count != count:
                testimony.comment_count = count
                testimony.save(update_fields=['comment_count'])
                results['testimony'] += 1

        # Discussion
        for discussion in Discussion.objects.all():
            count = discussion.comments.filter(is_deleted=False).count()
            if discussion.comment_count != count:
                discussion.comment_count = count
                discussion.save(update_fields=['comment_count'])
                results['discussion'] += 1

        return JsonResponse({
            'message': 'Comment counts recalculated successfully',
            'updated': results
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to recalculate comment counts: {str(e)}'
        }, status=500)
