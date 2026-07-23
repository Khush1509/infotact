"""Serializers for the parser app.

Provides validation and serialization for batch PDF contract uploads.
"""

from rest_framework import serializers
from .models import Document, ExtractedClause, RiskFlag


class DocumentSerializer(serializers.ModelSerializer):
    """Serializes Document model instances for API responses."""

    class Meta:
        model = Document
        fields = ['id', 'file', 'original_filename', 'file_size', 'content_hash', 'storage_backend', 'uploaded_at']
        read_only_fields = ['id', 'original_filename', 'file_size', 'content_hash', 'storage_backend', 'uploaded_at']


class RiskFlagSerializer(serializers.ModelSerializer):
    """Serializes RiskFlag model instances."""

    class Meta:
        model = RiskFlag
        fields = ['id', 'clause', 'flag_type', 'description', 'confidence_score', 'flagged_at']
        read_only_fields = ['id', 'flagged_at']


class ExtractedClauseSerializer(serializers.ModelSerializer):
    """Serializes ExtractedClause model instances."""
    risk_flags = RiskFlagSerializer(many=True, read_only=True)

    class Meta:
        model = ExtractedClause
        fields = ['id', 'document', 'clause_number', 'text', 'category', 'jurisdiction', 'risk_flags', 'extracted_at']
        read_only_fields = ['id', 'extracted_at']


class ParagraphItemSerializer(serializers.Serializer):
    """Serializer for individual paragraph text inputs."""
    clause_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    text = serializers.CharField(required=True)


class ClauseCategorizationRequestSerializer(serializers.Serializer):
    """Request serializer for categorizing paragraphs, extracting governing law jurisdictions, and risk evaluation."""
    document_id = serializers.IntegerField(required=False, allow_null=True)
    paragraphs = serializers.ListField(
        child=ParagraphItemSerializer(),
        min_length=1,
        help_text='List of paragraphs/clauses to categorize.'
    )
    save_to_db = serializers.BooleanField(default=False, help_text='Save extracted clauses to database if document_id is provided.')
    evaluate_risk = serializers.BooleanField(default=True, help_text='Evaluate paragraphs/sentences for legal risk.')




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

