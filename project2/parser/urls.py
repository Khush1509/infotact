from django.urls import path
from .views import health_check, BatchUploadView, CategorizeClausesView

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('api/v1/contracts/upload/', BatchUploadView.as_view(), name='batch_upload'),
    path('api/v1/clauses/categorize/', CategorizeClausesView.as_view(), name='categorize_clauses'),
]

