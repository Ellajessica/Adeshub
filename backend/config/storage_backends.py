"""
Cloudflare R2 Object Storage Backend for AdesHub.

Provides S3-compatible media file storage using Cloudflare R2 via django-storages and boto3.
"""

import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage

try:
    from storages.backends.s3boto3 import S3Boto3Storage
    HAS_S3_STORAGE = True
    _BaseStorage = S3Boto3Storage
except ImportError:
    HAS_S3_STORAGE = False
    _BaseStorage = FileSystemStorage


class CloudflareR2MediaStorage(_BaseStorage):
    """
    Storage backend for user/admin uploaded media files (product and category images)
    persisted to Cloudflare R2 object storage.

    Features:
    - S3v4 signature (strictly required by Cloudflare R2)
    - ACL headers disabled (Cloudflare R2 does not support S3 ACLs; avoids 400 Bad Request)
    - File overwrite disabled (appends unique hashes to duplicate filenames)
    - Clean public URL generation via Cloudflare R2 custom domain or R2.dev public URL
    - Fallback support for local FileSystemStorage when boto3/django-storages is not installed
    """
    default_acl = None
    file_overwrite = False
    signature_version = 's3v4'
    addressing_style = 'path'

    def __init__(self, *args, **kwargs):
        if HAS_S3_STORAGE:
            # Allow AWS_LOCATION to specify a subfolder in the bucket (default: empty string = root of bucket)
            location = kwargs.pop('location', None)
            if location is None:
                location = os.getenv('AWS_LOCATION', '').strip().strip('/')
            kwargs['location'] = location
            super().__init__(*args, **kwargs)
        else:
            # Fallback initialization for FileSystemStorage in local dev
            super().__init__(*args, **kwargs)

    @property
    def custom_domain(self):
        """
        Clean the custom domain by stripping protocol prefixes (http://, https://)
        and trailing slashes, preventing double-protocol bugs (e.g. https://https://...)
        in django-storages.
        """
        raw_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None) or os.getenv('AWS_S3_CUSTOM_DOMAIN', '')
        if raw_domain:
            domain = raw_domain.strip().replace('https://', '').replace('http://', '').rstrip('/')
            return domain or None
        return None

    @property
    def querystring_auth(self):
        """
        Determine whether to generate signed query strings.
        - Defaults to False when a public custom domain is configured (for clean, CDN-cacheable URLs).
        - Defaults to True if no public domain is set (to allow presigned S3 URLs against private endpoints).
        - Can be explicitly overridden via AWS_QUERYSTRING_AUTH.
        """
        explicit = os.getenv('AWS_QUERYSTRING_AUTH', '').strip()
        if explicit:
            return explicit.lower() in ('true', '1', 'yes')
        return not bool(self.custom_domain)

    def url(self, name):
        """
        Return the public URL for the file.
        Ensures consistent https:// URLs.
        """
        if not HAS_S3_STORAGE:
            # In local fallback mode without django-storages installed
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            return f"{media_url.rstrip('/')}/{name.lstrip('/')}"

        url = super().url(name)
        # Ensure scheme is present if django-storages produces a protocol-relative '//' URL
        if url.startswith('//'):
            url = f"https:{url}"
        return url
