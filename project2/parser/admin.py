from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Document, ExtractedClause, RiskFlag


class RiskFlagInline(admin.TabularInline):
    """Inline view for risk flags on the ExtractedClause detail page."""
    model = RiskFlag
    extra = 0
    readonly_fields = ('flagged_at',)
    fields = ('flag_type', 'confidence_score', 'description', 'flagged_at')


class ExtractedClauseInline(admin.TabularInline):
    """Inline view for clauses on the Document detail page."""
    model = ExtractedClause
    extra = 0
    show_change_link = True
    readonly_fields = ('extracted_at', 'risk_flag_count', 'text_preview')
    fields = ('clause_number', 'category', 'jurisdiction', 'text_preview', 'risk_flag_count', 'extracted_at')

    def text_preview(self, obj):
        if not obj.text:
            return ""
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
    text_preview.short_description = "Text Preview"

    def risk_flag_count(self, obj):
        return obj.risk_flags.count()
    risk_flag_count.short_description = "Flagged Risks"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Custom Admin view for PDF Documents with metadata, previews, and clause inlines."""
    list_display = ('id', 'original_filename', 'file_size_display', 'storage_backend', 'clause_count', 'view_pdf_link', 'uploaded_at')
    list_filter = ('storage_backend', 'uploaded_at')
    search_fields = ('original_filename', 'content_hash')
    readonly_fields = ('content_hash', 'file_size', 'uploaded_at', 'view_pdf_link', 'clause_count')
    inlines = [ExtractedClauseInline]
    ordering = ('-uploaded_at',)

    def file_size_display(self, obj):
        if not obj.file_size:
            return "0 B"
        if obj.file_size >= 1024 * 1024:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        if obj.file_size >= 1024:
            return f"{obj.file_size / 1024:.2f} KB"
        return f"{obj.file_size} B"
    file_size_display.short_description = "File Size"

    def view_pdf_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank" style="font-weight:bold; color: #2b6cb0;">📄 View PDF</a>', obj.file.url)
        return "No File"
    view_pdf_link.short_description = "PDF Preview"

    def clause_count(self, obj):
        return obj.clauses.count()
    clause_count.short_description = "Extracted Clauses"


@admin.register(ExtractedClause)
class ExtractedClauseAdmin(admin.ModelAdmin):
    """Custom Admin view for Extracted Clauses with category filters and risk flag inlines."""
    list_display = ('id', 'document_link', 'clause_number', 'category', 'jurisdiction', 'risk_flag_count', 'text_preview', 'extracted_at')
    list_filter = ('category', 'jurisdiction', 'extracted_at')
    search_fields = ('clause_number', 'text', 'jurisdiction', 'document__original_filename')
    readonly_fields = ('extracted_at', 'risk_flag_count')
    inlines = [RiskFlagInline]
    ordering = ('-extracted_at',)

    def text_preview(self, obj):
        if not obj.text:
            return ""
        return obj.text[:120] + "..." if len(obj.text) > 120 else obj.text
    text_preview.short_description = "Clause Text"

    def document_link(self, obj):
        if not obj.document:
            return "-"
        url = reverse('admin:parser_document_change', args=[obj.document.id])
        return format_html('<a href="{}">Doc #{} ({})</a>', url, obj.document.id, obj.document.original_filename or "Unnamed")
    document_link.short_description = "Document"

    def risk_flag_count(self, obj):
        count = obj.risk_flags.count()
        if count > 0:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ {} Flags</span>', count)
        return format_html('<span style="color: green;">✓ 0 Flags</span>')
    risk_flag_count.short_description = "Risk Status"


@admin.register(RiskFlag)
class RiskFlagAdmin(admin.ModelAdmin):
    """Custom Admin view for Risk Flags with confidence score and type filtering."""
    list_display = ('id', 'clause_link', 'flag_type', 'confidence_score_display', 'short_description', 'flagged_at')
    list_filter = ('flag_type', 'flagged_at')
    search_fields = ('flag_type', 'description', 'clause__text')
    readonly_fields = ('flagged_at',)
    ordering = ('-flagged_at',)

    def clause_link(self, obj):
        if not obj.clause:
            return "-"
        url = reverse('admin:parser_extractedclause_change', args=[obj.clause.id])
        num = obj.clause.clause_number or f"ID {obj.clause.id}"
        return format_html('<a href="{}">Clause {}</a>', url, num)
    clause_link.short_description = "Clause"

    def confidence_score_display(self, obj):
        if obj.confidence_score is None:
            return "N/A"
        score = obj.confidence_score
        color = "red" if score >= 0.85 else ("orange" if score >= 0.70 else "green")
        score_str = f"{score:.2f}"
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, score_str)
    confidence_score_display.short_description = "Confidence Score"

    def short_description(self, obj):
        if not obj.description:
            return ""
        return obj.description[:100] + "..." if len(obj.description) > 100 else obj.description
    short_description.short_description = "Description"
