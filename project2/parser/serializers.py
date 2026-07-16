"""Serializers for the parser app.

Provides validation and serialization for batch PDF contract uploads.
"""

from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Serializes Document model instances for API responses."""

    class Meta:
        model = Document
        fields = ['id', 'file', 'original_filename', 'file_size', 'content_hash', 'storage_backend', 'uploaded_at']
        read_only_fields = ['id', 'original_filename', 'file_size', 'content_hash', 'storage_backend', 'uploaded_at']


class BatchUploadSerializer(serializers.Serializer):
    """Validates batch PDF file uploads.

    Accepts a list of files under the 'files' key and enforces:
    - Each file must have content type 'application/pdf'
    - Each file must not exceed 10 MB
    - Between 1 and 20 files per request
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_FILE_COUNT = 20

    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=MAX_FILE_COUNT,
        help_text='Upload between 1 and 20 PDF files.',
    )

    def validate_files(self, files):
        """Validate that every uploaded file is a PDF (by content type and magic bytes) and within size limits."""
        errors = []
        for i, f in enumerate(files):
            if f.content_type != 'application/pdf':
                errors.append(
                    f'File "{f.name}" (index {i}) is not a PDF. '
                    f'Received content type: {f.content_type}.'
                )
            # Verify magic bytes
            pos = f.tell()
            f.seek(0)
            header = f.read(5)
            f.seek(pos)
            if header != b'%PDF-':
                errors.append(
                    f'File "{f.name}" (index {i}) is not a valid PDF (invalid signature).'
                )
            if f.size > self.MAX_FILE_SIZE:
                size_mb = f.size / (1024 * 1024)
                errors.append(
                    f'File "{f.name}" (index {i}) exceeds the 10 MB limit '
                    f'({size_mb:.1f} MB).'
                )
        if errors:
            raise serializers.ValidationError(errors)
        return files

