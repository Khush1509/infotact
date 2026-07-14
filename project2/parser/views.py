from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError

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

