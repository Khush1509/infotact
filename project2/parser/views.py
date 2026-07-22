from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections, transaction
from django.db.utils import OperationalError
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, ExtractedClause
from .serializers import (
    BatchUploadSerializer, DocumentSerializer,
    ClauseCategorizationRequestSerializer, ExtractedClauseSerializer
)
from .storage import save_uploaded_document
from .nlp import ClauseCategorizer



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
    """Categorize extracted contract paragraphs and isolate governing law jurisdiction.

    POST /api/v1/clauses/categorize/
    Body (JSON):
    {
        "document_id": 1, (optional)
        "save_to_db": true, (optional)
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
                res = ClauseCategorizer.process_paragraph(text, clause_number=clause_number)

                if document and save_to_db:
                    clause_obj = ExtractedClause.objects.create(
                        document=document,
                        clause_number=clause_number,
                        text=text,
                        category=res['category'],
                        jurisdiction=res['jurisdiction'],
                    )
                    res['id'] = clause_obj.id

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



