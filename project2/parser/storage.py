import os
import uuid
import hashlib
from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile

def _sanitize_filename(name: str) -> str:
    """Return a safe filename.
    - Strips directory components.
    - Replaces spaces with underscores.
    - Limits length to 200 characters.
    - Prepends a UUID prefix to avoid collisions.
    """
    base = os.path.basename(name)
    base = base.replace(' ', '_')
    if len(base) > 200:
        base = base[:200]
    return f"{uuid.uuid4().hex}_{base}"

def _verify_pdf_magic(file_obj) -> bool:
    """Check that the uploaded file starts with the %PDF- signature."""
    pos = file_obj.tell()
    file_obj.seek(0)
    header = file_obj.read(5)
    file_obj.seek(pos)
    return header == b'%PDF-'

def _hash_file(file_obj) -> str:
    """Compute SHA-256 hash of the file."""
    pos = file_obj.tell()
    file_obj.seek(0)
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(8192), b''):
        hasher.update(chunk)
    file_obj.seek(pos)
    return hasher.hexdigest()

class BaseStorageBackend:
    def save(self, name: str, file_obj) -> str:
        raise NotImplementedError('save method must be overridden')

class LocalStorageBackend(BaseStorageBackend):
    def __init__(self):
        self.storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'documents'))

    def save(self, name: str, file_obj) -> str:
        if not _verify_pdf_magic(file_obj):
            raise ValueError('Uploaded file is not a valid PDF (missing %PDF- header)')
        safe_name = _sanitize_filename(name)
        saved_path = self.storage.save(safe_name, file_obj)
        # Return path relative to MEDIA_ROOT (e.g. 'documents/xyz.pdf')
        return f"documents/{saved_path}"

class MockS3StorageBackend(BaseStorageBackend):
    def __init__(self):
        # We store mock_s3 files under MEDIA_ROOT/mock_s3
        self.base_dir = os.path.join(settings.MEDIA_ROOT, 'mock_s3')
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, name: str, file_obj) -> str:
        if not _verify_pdf_magic(file_obj):
            raise ValueError('Uploaded file is not a valid PDF (missing %PDF- header)')
        safe_name = _sanitize_filename(name)
        target_path = os.path.join(self.base_dir, safe_name)
        file_obj.seek(0)
        with open(target_path, 'wb') as out_f:
            for chunk in iter(lambda: file_obj.read(8192), b''):
                out_f.write(chunk)
        file_obj.seek(0)
        # Return mock s3 URI style or just mock_s3 relative path
        return f"mock_s3/{safe_name}"

def get_storage_backend() -> BaseStorageBackend:
    backend_name = getattr(settings, 'STORAGE_BACKEND', 'local').lower()
    if backend_name == 'mock_s3':
        return MockS3StorageBackend()
    return LocalStorageBackend()

def save_uploaded_document(file_obj, original_name: str):
    """Validate, hash and store an uploaded file.
    Returns a dict with: 'path', 'size', 'hash'.
    """
    if not _verify_pdf_magic(file_obj):
        raise ValueError("Uploaded file is not a valid PDF.")
    
    file_hash = _hash_file(file_obj)
    size = file_obj.size
    
    backend = get_storage_backend()
    stored_path = backend.save(original_name, file_obj)
    
    return {
        'path': stored_path,
        'size': size,
        'hash': file_hash
    }
