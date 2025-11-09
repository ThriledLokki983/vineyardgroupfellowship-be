"""
Custom storage backends for Vineyard Group Fellowship.

Base64DatabaseStorage: Store images as Base64 encoded strings in the database.
Perfect for Railway deployment without file system persistence issues.
"""

import base64
import uuid
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class Base64DatabaseStorage(Storage):
    """
    Store files as Base64 encoded strings in the database.

    This storage backend is perfect for platforms with ephemeral storage
    like Railway, where file system changes don't persist across deployments.

    The actual Base64 data is stored in the model's field itself.
    """

    def __init__(self, location=None):
        self.location = location or ''

    def _open(self, name, mode='rb'):
        """
        Open a file from Base64 string.
        The 'name' parameter contains the Base64 encoded data.
        """
        if not name or name.startswith('data:'):
            # Already a data URL, extract the base64 part
            if ',' in name:
                name = name.split(',', 1)[1]

        try:
            file_data = base64.b64decode(name)
            return ContentFile(file_data)
        except Exception:
            return ContentFile(b'')

    def _save(self, name, content):
        """
        Save file by converting it to Base64.
        Returns the Base64 string (not a filename).
        """
        # Read the file content
        if hasattr(content, 'read'):
            file_content = content.read()
        else:
            file_content = content

        # Encode to Base64
        encoded = base64.b64encode(file_content).decode('utf-8')

        # Return Base64 string with data URL prefix for easy browser rendering
        # Format: data:image/jpeg;base64,<encoded_data>
        content_type = self._get_content_type(name)
        return f"data:{content_type};base64,{encoded}"

    def _get_content_type(self, name):
        """Get content type based on file extension."""
        if name.lower().endswith('.png'):
            return 'image/png'
        elif name.lower().endswith('.gif'):
            return 'image/gif'
        elif name.lower().endswith('.webp'):
            return 'image/webp'
        else:
            return 'image/jpeg'  # Default to JPEG

    def delete(self, name):
        """
        Delete a file. For Base64 storage, this is a no-op
        as the data is in the database field itself.
        """
        pass

    def exists(self, name):
        """
        Check if a file exists.
        For Base64 storage, if name is provided, it exists.
        """
        return bool(name)

    def listdir(self, path):
        """
        List directory contents.
        Not applicable for Base64 storage.
        """
        return [], []

    def size(self, name):
        """
        Return the size of the Base64 encoded data.
        """
        if not name:
            return 0

        # Remove data URL prefix if present
        if name.startswith('data:'):
            name = name.split(',', 1)[1] if ',' in name else name

        # Base64 encoded size is roughly 4/3 of original
        # Decode to get actual size
        try:
            decoded = base64.b64decode(name)
            return len(decoded)
        except Exception:
            return 0

    def url(self, name):
        """
        Return the URL for accessing the file.
        For Base64, we return the data URL directly.
        """
        if not name:
            return ''

        # If already a data URL, return as is
        if name.startswith('data:'):
            return name

        # Otherwise, construct data URL
        content_type = 'image/jpeg'  # Default
        return f"data:{content_type};base64,{name}"

    def get_accessed_time(self, name):
        """Not applicable for Base64 storage."""
        return None

    def get_created_time(self, name):
        """Not applicable for Base64 storage."""
        return None

    def get_modified_time(self, name):
        """Not applicable for Base64 storage."""
        return None
