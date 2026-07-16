from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections, transaction
from django.db.utils import OperationalError
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document
from .serializers import BatchUploadSerializer, DocumentSerializer
from .storage import save_uploaded_document


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


