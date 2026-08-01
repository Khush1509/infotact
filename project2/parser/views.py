from typing import Dict
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections, transaction
from django.db.utils import OperationalError
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, ExtractedClause, RiskFlag
from .serializers import (
    BatchUploadSerializer, DocumentSerializer,
    ClauseCategorizationRequestSerializer, ExtractedClauseSerializer,
    RiskFlagSerializer, ContractReviewSerializer
)
from .storage import save_uploaded_document
from .nlp import (
    ClauseCategorizer, RiskEvaluator,
    ContractEntityExtractor, ContractDurationTermExtractor
)


def health_check(request):
    db_conn = connections['default']
    db_ok = True
    error_message = None
    try:
        db_conn.cursor()
    except OperationalError as e:
        db_ok = False
        error_message = str(e)
    
    return JsonResponse({
        'status': 'healthy' if db_ok else 'unhealthy',
        'database': 'connected' if db_ok else 'disconnected',
        'error': error_message
    }, status=200 if db_ok else 500)


class BatchUploadView(APIView):
    """Accept multipart/form-data with one or more PDF files.

    POST /api/v1/contracts/upload/
    Body (multipart/form-data):
        files: one or more PDF files

    Returns 201 with a list of created Document records,
    or 400 with validation errors.
    """

    def post(self, request, *args, **kwargs):
        serializer = BatchUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_files = serializer.validated_data['files']
        documents = []
        storage_backend_type = getattr(settings, 'STORAGE_BACKEND', 'local')

        try:
            with transaction.atomic():
                for f in uploaded_files:
                    res = save_uploaded_document(f, f.name)
                    doc = Document(
                        original_filename=f.name,
                        file_size=res['size'],
                        content_hash=res['hash'],
                        storage_backend=storage_backend_type,
                    )
                    doc.file.name = res['path']
                    doc.save()
                    documents.append(doc)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output = DocumentSerializer(documents, many=True)
        return Response(
            {
                'count': len(documents),
                'documents': output.data,
            },
            status=status.HTTP_201_CREATED,
        )


class CategorizeClausesView(APIView):
    """Categorize extracted contract paragraphs, isolate governing law jurisdiction, and evaluate risk.

    POST /api/v1/clauses/categorize/
    Body (JSON):
    {
        "document_id": 1, (optional)
        "save_to_db": true, (optional)
        "evaluate_risk": true, (optional)
        "paragraphs": [
            {
                "clause_number": "12.1",
                "text": "This Agreement shall be governed by and construed in accordance with the laws of the State of New York..."
            }
        ]
    }
    """

    def post(self, request, *args, **kwargs):
        serializer = ClauseCategorizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        document_id = data.get('document_id')
        save_to_db = data.get('save_to_db', False)
        evaluate_risk = data.get('evaluate_risk', True)
        paragraphs = data.get('paragraphs', [])

        document = None
        if document_id:
            try:
                document = Document.objects.get(id=document_id)
            except Document.DoesNotExist:
                return Response(
                    {'error': f'Document with id {document_id} does not exist.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        results = []

        with transaction.atomic():
            for item in paragraphs:
                clause_number = item.get('clause_number')
                text = item.get('text', '')
                res = ClauseCategorizer.process_paragraph(text, clause_number=clause_number, evaluate_risk=evaluate_risk)

                if document and save_to_db:
                    clause_obj = ExtractedClause.objects.create(
                        document=document,
                        clause_number=clause_number,
                        text=text,
                        category=res['category'],
                        jurisdiction=res['jurisdiction'],
                    )
                    res['id'] = clause_obj.id

                    if evaluate_risk and res.get('risk_evaluation', {}).get('has_risk'):
                        saved_flags = []
                        for flag in res['risk_evaluation']['risk_flags']:
                            rf_obj = RiskFlag.objects.create(
                                clause=clause_obj,
                                flag_type=flag['flag_type'],
                                description=flag['description'],
                                confidence_score=flag['confidence_score'],
                            )
                            saved_flags.append(RiskFlagSerializer(rf_obj).data)
                        res['saved_risk_flags'] = saved_flags

                results.append(res)

        return Response(
            {
                'count': len(results),
                'document_id': document_id,
                'saved_to_db': bool(document and save_to_db),
                'results': results,
            },
            status=status.HTTP_201_CREATED if (document and save_to_db) else status.HTTP_200_OK,
        )


class ContractReviewView(APIView):
    """Provides a nested JSON payload of document data, categorized clauses, extracted metadata (parties, dates, duration, termination), and flagged risks for Senior Counsel review.

    GET /api/v1/contracts/<pk>/review/
    """

    def get(self, request, pk, *args, **kwargs):
        try:
            document = Document.objects.prefetch_related('clauses__risk_flags').get(pk=pk)
        except Document.DoesNotExist:
            return Response(
                {'error': f'Document with id {pk} does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        clauses = list(document.clauses.all())
        full_text = " \n ".join([c.text for c in clauses if c.text])

        # Extract entities and duration/termination
        entities_data = ContractEntityExtractor.extract_entities(full_text)
        duration_data = ContractDurationTermExtractor.extract_duration(full_text)
        termination_data = ContractDurationTermExtractor.extract_termination_clauses(full_text)

        entity_summary = {
            "parties": entities_data["parties"],
            "signing_dates": entities_data["signing_dates"],
            "effective_date": entities_data["effective_date"],
            "term_length": duration_data["term_length"],
            "auto_renewal": duration_data["auto_renewal"],
            "notice_period": termination_data["notice_period"],
            "termination_types": termination_data["termination_types"],
        }

        # Aggregate risk flags across all clauses
        all_risk_flags = []
        flag_counts: Dict[str, int] = {}
        max_score = 0.0

        for clause in clauses:
            for rf in clause.risk_flags.all():
                all_risk_flags.append(rf)
                flag_counts[rf.flag_type] = flag_counts.get(rf.flag_type, 0) + 1
                if rf.confidence_score and rf.confidence_score > max_score:
                    max_score = rf.confidence_score

        if max_score >= 0.85:
            overall_risk_level = "HIGH"
        elif max_score >= 0.70:
            overall_risk_level = "MEDIUM"
        elif all_risk_flags:
            overall_risk_level = "LOW"
        else:
            overall_risk_level = "NONE"

        risk_summary = {
            "overall_risk_level": overall_risk_level,
            "total_risk_flags": len(all_risk_flags),
            "flag_counts_by_type": flag_counts,
        }

        payload = {
            "document": document,
            "entities": entity_summary,
            "risk_summary": risk_summary,
            "clauses": clauses,
            "status": "READY_FOR_REVIEW",
        }

        serializer = ContractReviewSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
