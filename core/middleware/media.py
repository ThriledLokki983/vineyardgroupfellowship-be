"""
Media file serving middleware for production environments.

This middleware adds security headers and handles media file serving
for production deployments where Django serves media files directly.
"""

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.files.storage import default_storage
import os
import mimetypes
from urllib.parse import unquote


class MediaSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to media file responses.

    This is used in production when Django serves media files directly
    (before migrating to S3/CDN). Adds proper security headers and
    content type detection.
    """

    def process_response(self, request, response):
        """Add security headers to media file responses."""

        # Only process media URLs
        if not request.path.startswith(settings.MEDIA_URL):
            return response

        # Add security headers for media files
        if hasattr(settings, 'MEDIA_FILE_SECURITY_HEADERS'):
            for header, value in settings.MEDIA_FILE_SECURITY_HEADERS.items():
                response[header] = value

        # Ensure proper content type for images
        if request.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            file_path = request.path.replace(settings.MEDIA_URL, '', 1)
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type:
                response['Content-Type'] = content_type

        return response


class ProductionMediaMiddleware(MiddlewareMixin):
    """
    Middleware to serve media files in production with proper security.

    This is used when SERVE_MEDIA_IN_PRODUCTION=True and provides
    a secure way to serve media files before migrating to S3/CDN.
    """

    def process_request(self, request):
        """Serve media files in production with security checks."""

        # Only handle media URLs
        if not request.path.startswith(settings.MEDIA_URL):
            return None

        # Check if we should serve media in production
        serve_media = getattr(settings, 'SERVE_MEDIA_IN_PRODUCTION', False)
        if not serve_media and not settings.DEBUG:
            return None

        # Get the file path
        file_path = unquote(request.path[len(settings.MEDIA_URL):])

        # Security check: prevent path traversal
        if '..' in file_path or file_path.startswith('/'):
            raise Http404("Invalid file path")

        try:
            # Check if file exists
            if not default_storage.exists(file_path):
                raise Http404("File not found")

            # Get file content and metadata
            file_obj = default_storage.open(file_path, 'rb')
            content = file_obj.read()
            file_obj.close()

            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Create response
            response = HttpResponse(content, content_type=content_type)

            # Add security headers
            if hasattr(settings, 'MEDIA_FILE_SECURITY_HEADERS'):
                for header, value in settings.MEDIA_FILE_SECURITY_HEADERS.items():
                    response[header] = value

            # Add file size header
            response['Content-Length'] = len(content)

            # Add filename for downloads
            filename = os.path.basename(file_path)
            if filename:
                response['Content-Disposition'] = f'inline; filename="{filename}"'

            return response

        except Exception as e:
            # Log the error in production
            if not settings.DEBUG:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Media serving error for {file_path}: {e}")

            raise Http404("File not found")
