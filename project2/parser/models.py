from django.db import models


class Document(models.Model):
    """Represents an uploaded PDF document with storage metadata."""
    file = models.FileField(upload_to='documents/')
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    storage_backend = models.CharField(max_length=20, choices=[('local', 'Local'), ('mock_s3', 'Mock S3')], default='local')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document {self.id}"


class ExtractedClause(models.Model):
    """A clause extracted from a Document."""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='clauses')
    clause_number = models.CharField(max_length=50, blank=True, null=True)
    text = models.TextField()
    extracted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Clause {self.clause_number} from Document {self.document.id}" if self.clause_number else f"Clause {self.id} from Document {self.document.id}"


class RiskFlag(models.Model):
    """Risk flag associated with an extracted clause."""
    clause = models.ForeignKey(ExtractedClause, on_delete=models.CASCADE, related_name='risk_flags')
    flag_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    confidence_score = models.FloatField(blank=True, null=True)
    flagged_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.flag_type} (Score: {self.confidence_score}) for Clause {self.clause.id}"
