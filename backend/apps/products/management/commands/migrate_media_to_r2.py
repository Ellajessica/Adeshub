"""
Management command to migrate existing local media files (product and category images)
to Cloudflare R2 object storage.

Usage:
    python manage.py migrate_media_to_r2
    python manage.py migrate_media_to_r2 --dry-run
    python manage.py migrate_media_to_r2 --overwrite
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.products.models import Category, ProductImage
from config.storage_backends import CloudflareR2MediaStorage, HAS_S3_STORAGE


class Command(BaseCommand):
    help = (
        'Migrates existing local category and product image files from MEDIA_ROOT to '
        'Cloudflare R2 object storage, preserving exact relative paths.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate migration without uploading files to Cloudflare R2.'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Re-upload and overwrite files even if they already exist in R2.'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        overwrite = options.get('overwrite', False)

        self.stdout.write(self.style.MIGRATE_HEADING("=== AdesHub Cloudflare R2 Media Migration ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN MODE] No remote files will be created."))

        # Check R2 configuration
        use_r2 = getattr(settings, 'USE_R2_STORAGE', False) and HAS_S3_STORAGE
        if not use_r2:
            self.stdout.write(self.style.WARNING(
                "NOTE: Cloudflare R2 environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, "
                "AWS_STORAGE_BUCKET_NAME, AWS_S3_ENDPOINT_URL) are not fully configured in your current environment."
            ))
            self.stdout.write(
                "Scanning local filesystem and database references to report files ready for migration...\n"
            )

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write(self.style.ERROR(f"MEDIA_ROOT does not exist: {media_root}"))
            return

        # 1. Collect all local media files on disk relative to MEDIA_ROOT
        files_on_disk = set()
        for root, _, files in os.walk(media_root):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(media_root).as_posix()
                files_on_disk.add(rel_path)

        self.stdout.write(f"Discovered {len(files_on_disk)} total file(s) in local MEDIA_ROOT ({media_root})")

        # 2. Collect files referenced in Category and ProductImage models
        db_references = set()
        for cat in Category.objects.exclude(image='').exclude(image__isnull=True):
            if cat.image and cat.image.name:
                db_references.add(cat.image.name.replace('\\', '/'))

        for prod_img in ProductImage.objects.exclude(image='').exclude(image__isnull=True):
            if prod_img.image and prod_img.image.name:
                db_references.add(prod_img.image.name.replace('\\', '/'))

        self.stdout.write(f"Discovered {len(db_references)} active media file reference(s) in database models.")

        # Combine files to process
        all_targets = sorted(files_on_disk.union(db_references))
        if not all_targets:
            self.stdout.write(self.style.SUCCESS("No media files found to migrate."))
            return

        # Instantiate R2 storage backend if available
        r2_storage = None
        if use_r2 and not dry_run:
            r2_storage = CloudflareR2MediaStorage()

        uploaded_count = 0
        skipped_count = 0
        missing_count = 0

        self.stdout.write("-" * 70)
        for rel_path in all_targets:
            local_path = media_root / rel_path

            if not local_path.exists():
                self.stdout.write(self.style.ERROR(f"[MISSING LOCAL FILE] {rel_path} referenced in DB but not on disk."))
                missing_count += 1
                continue

            file_size_kb = local_path.stat().st_size / 1024.0

            if dry_run or not use_r2:
                self.stdout.write(f"[READY] {rel_path} ({file_size_kb:.1f} KB)")
                uploaded_count += 1
                continue

            # Upload to Cloudflare R2
            if r2_storage is None:
                continue

            try:
                # Check if file already exists in R2
                if not overwrite and r2_storage.exists(rel_path):
                    self.stdout.write(self.style.NOTICE(f"[EXISTS / SKIPPED] {rel_path} (use --overwrite to replace)"))
                    skipped_count += 1
                    continue

                with open(local_path, 'rb') as f:
                    # In CloudflareR2MediaStorage, if overwrite is requested and file exists, delete it first
                    if overwrite and r2_storage.exists(rel_path):
                        r2_storage.delete(rel_path)
                    saved_name = r2_storage.save(rel_path, f)

                r2_url = r2_storage.url(saved_name)
                self.stdout.write(self.style.SUCCESS(f"[UPLOADED] {rel_path} -> {r2_url}"))
                uploaded_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAILED] {rel_path}: {e}"))

        self.stdout.write("-" * 70)
        self.stdout.write(self.style.SUCCESS(
            f"Migration Summary: {uploaded_count} processed/uploaded, {skipped_count} skipped, {missing_count} missing."
        ))
        if not use_r2 and not dry_run:
            self.stdout.write(self.style.WARNING(
                "\nTo perform actual uploads to Cloudflare R2, set the AWS_* environment variables in your environment "
                "or run this command on Render after configuring your service environment variables."
            ))
