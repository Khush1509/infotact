import os
import shutil
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Document

# Use a temporary media root so tests don't pollute the real media dir
TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'test_media')


class HealthCheckTests(TestCase):
    def test_health_check_endpoint(self):
        """
        Verify that the health check endpoint returns 200 and indicates active status.
        """
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')
        self.assertIsNone(data['error'])


def _make_pdf(name='contract.pdf', size=1024):
    """Create a minimal valid-looking PDF file for testing."""
    # A real PDF starts with %PDF- header
    content = b'%PDF-1.4 test content'
    if size > len(content):
        content += b'\x00' * (size - len(content))
    return SimpleUploadedFile(name, content, content_type='application/pdf')


def _make_txt(name='notes.txt'):
    """Create a plain text file for testing rejection."""
    return SimpleUploadedFile(name, b'just some text', content_type='text/plain')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BatchUploadTests(TestCase):
    """Tests for POST /api/v1/contracts/upload/"""

    url = reverse('batch_upload')

    @classmethod
    def tearDownClass(cls):
        """Clean up the temporary media directory after all tests."""
        super().tearDownClass()
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)

    # ── Happy-path tests ────────────────────────────────────────

    def test_batch_upload_single_pdf(self):
        """Uploading a single valid PDF returns 201 with one document."""
        pdf = _make_pdf('single.pdf')
        response = self.client.post(self.url, {'files': pdf}, format='multipart')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['documents']), 1)
        self.assertTrue(Document.objects.filter(id=data['documents'][0]['id']).exists())

    def test_batch_upload_multiple_pdfs(self):
        """Uploading 3 valid PDFs returns 201 with 3 documents."""
        pdfs = [_make_pdf(f'contract_{i}.pdf') for i in range(3)]
        response = self.client.post(self.url, {'files': pdfs}, format='multipart')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['count'], 3)
        self.assertEqual(len(data['documents']), 3)
        self.assertEqual(Document.objects.count(), 3)

    # ── Validation / rejection tests ────────────────────────────

    def test_batch_upload_rejects_non_pdf(self):
        """Uploading a non-PDF file returns 400."""
        txt = _make_txt()
        response = self.client.post(self.url, {'files': txt}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_batch_upload_rejects_empty_request(self):
        """Sending no files returns 400."""
        response = self.client.post(self.url, {}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_batch_upload_rejects_oversized_file(self):
        """A file exceeding 10 MB is rejected with 400."""
        oversized = _make_pdf('huge.pdf', size=11 * 1024 * 1024)
        response = self.client.post(self.url, {'files': oversized}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)


