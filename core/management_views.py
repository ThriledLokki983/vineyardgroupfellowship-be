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
