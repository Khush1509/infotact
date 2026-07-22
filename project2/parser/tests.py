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
        
        doc_id = data['documents'][0]['id']
        self.assertTrue(Document.objects.filter(id=doc_id).exists())
        doc = Document.objects.get(id=doc_id)
        self.assertEqual(doc.original_filename, 'single.pdf')
        self.assertEqual(doc.storage_backend, 'local')
        self.assertEqual(doc.file_size, len(b'%PDF-1.4 test content' + b'\x00' * (1024 - len(b'%PDF-1.4 test content'))))
        
        # Verify physical file existence in local storage
        self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, doc.file.name)))

    def test_batch_upload_multiple_pdfs(self):
        """Uploading 3 valid PDFs returns 201 with 3 documents."""
        pdfs = [_make_pdf(f'contract_{i}.pdf') for i in range(3)]
        response = self.client.post(self.url, {'files': pdfs}, format='multipart')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['count'], 3)
        self.assertEqual(len(data['documents']), 3)
        self.assertEqual(Document.objects.count(), 3)
        
        for doc in Document.objects.all():
            self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, doc.file.name)))

    @override_settings(STORAGE_BACKEND='mock_s3')
    def test_batch_upload_mock_s3(self):
        """Uploading a PDF with mock_s3 settings saves it to the mock_s3 directory."""
        pdf = _make_pdf('s3_contract.pdf')
        response = self.client.post(self.url, {'files': pdf}, format='multipart')

        self.assertEqual(response.status_code, 201)
        data = response.json()
        doc = Document.objects.get(id=data['documents'][0]['id'])
        self.assertEqual(doc.storage_backend, 'mock_s3')
        self.assertTrue(doc.file.name.startswith('mock_s3/'))
        self.assertTrue(os.path.exists(os.path.join(settings.MEDIA_ROOT, doc.file.name)))

    # ── Validation / rejection tests ────────────────────────────

    def test_batch_upload_rejects_non_pdf(self):
        """Uploading a non-PDF file returns 400."""
        txt = _make_txt()
        response = self.client.post(self.url, {'files': txt}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_batch_upload_rejects_fake_pdf(self):
        """Uploading a file claiming to be a PDF but lacking the magic signature is rejected."""
        fake_pdf = SimpleUploadedFile('fake.pdf', b'NOT_A_PDF_CONTENT', content_type='application/pdf')
        response = self.client.post(self.url, {'files': fake_pdf}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.count(), 0)

    def test_batch_upload_atomic_rollback(self):
        """If one file in a batch is invalid, all uploads must be rolled back."""
        pdf = _make_pdf('valid.pdf')
        fake_pdf = SimpleUploadedFile('fake.pdf', b'NOT_A_PDF_CONTENT', content_type='application/pdf')
        
        response = self.client.post(self.url, {'files': [pdf, fake_pdf]}, format='multipart')
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


class ClauseCategorizerTests(TestCase):
    """Unit tests for ClauseCategorizer NLP and Regex rules."""

    def test_clause_categorization_types(self):
        """Test categorization across different legal paragraph types."""
        from .nlp import ClauseCategorizer

        samples = [
            ("This Agreement shall be governed by and construed in accordance with the laws of the State of New York.", ClauseCategorizer.GOVERNING_LAW),
            ("Each party agrees to keep confidential all non-public proprietary information disclosed by the other party.", ClauseCategorizer.CONFIDENTIALITY),
            ("Either party may terminate this agreement upon 30 days written notice.", ClauseCategorizer.TERMINATION),
            ("Supplier agrees to indemnify, defend and hold harmless Buyer from all third-party claims.", ClauseCategorizer.INDEMNIFICATION),
            ("In no event shall either party be liable for any indirect, incidental, or consequential damages.", ClauseCategorizer.LIMITATION_OF_LIABILITY),
            ("Any dispute arising out of this contract shall be submitted to binding arbitration.", ClauseCategorizer.DISPUTE_RESOLUTION),
            ("All intellectual property rights, trademarks, and patents shall remain the exclusive property of Company.", ClauseCategorizer.INTELLECTUAL_PROPERTY),
            ("Payment terms are net 30 days from invoice date. Late payments incur interest.", ClauseCategorizer.PAYMENT),
            ("Neither party shall be liable for failure to perform due to acts of God or force majeure.", ClauseCategorizer.FORCE_MAJEURE),
            ("The headings in this document are for reference only.", ClauseCategorizer.GENERAL),
        ]

        for text, expected_cat in samples:
            cat = ClauseCategorizer.categorize_paragraph(text)
            self.assertEqual(cat, expected_cat, f"Failed for text: {text}")

    def test_jurisdiction_extraction(self):
        """Test isolation and extraction of governing law jurisdiction."""
        from .nlp import ClauseCategorizer

        cases = [
            (
                "This Agreement shall be governed by and construed in accordance with the laws of the State of New York, without regard to conflicts of law.",
                "State of New York"
            ),
            (
                "This contract is governed by the laws of Delaware.",
                "Delaware"
            ),
            (
                "This Agreement and any dispute arising out of it shall be governed by and interpreted in accordance with the laws of England and Wales.",
                "England and Wales"
            ),
            (
                "The parties submit to the exclusive jurisdiction of the courts of the State of California.",
                "State of California"
            ),
            (
                "Governed by the laws of the Commonwealth of Massachusetts.",
                "Commonwealth of Massachusetts"
            ),
            (
                "This agreement is governed by the laws of Texas.",
                "Texas"
            ),
        ]

        for text, expected_jur in cases:
            jur = ClauseCategorizer.extract_governing_jurisdiction(text)
            self.assertEqual(jur, expected_jur, f"Failed extracting jurisdiction for: {text}")


class ClauseCategorizationAPITests(TestCase):
    """Tests for POST /api/v1/clauses/categorize/"""

    url = reverse('categorize_clauses')

    def test_categorize_paragraphs_without_db_save(self):
        """Posting paragraphs returns categorized list without DB persistence."""
        payload = {
            "paragraphs": [
                {
                    "clause_number": "Section 1",
                    "text": "This Agreement shall be governed by the laws of Delaware."
                },
                {
                    "clause_number": "Section 2",
                    "text": "All information shared hereunder shall remain confidential."
                }
            ]
        }
        response = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['count'], 2)
        self.assertFalse(data['saved_to_db'])

        results = data['results']
        self.assertEqual(results[0]['category'], 'GOVERNING_LAW')
        self.assertEqual(results[0]['jurisdiction'], 'Delaware')
        self.assertEqual(results[1]['category'], 'CONFIDENTIALITY')
        self.assertIsNone(results[1]['jurisdiction'])

    def test_categorize_paragraphs_with_db_save(self):
        """Posting paragraphs with valid document_id and save_to_db saves records to DB."""
        from .models import Document, ExtractedClause
        doc = Document.objects.create(original_filename='test_doc.pdf', storage_backend='local')

        payload = {
            "document_id": doc.id,
            "save_to_db": True,
            "paragraphs": [
                {
                    "clause_number": "14.2",
                    "text": "This Agreement is governed by the laws of the State of New York."
                }
            ]
        }
        response = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        data = response.json()
        self.assertTrue(data['saved_to_db'])
        self.assertEqual(data['count'], 1)

        clause_id = data['results'][0]['id']
        clause_obj = ExtractedClause.objects.get(id=clause_id)
        self.assertEqual(clause_obj.document, doc)
        self.assertEqual(clause_obj.clause_number, "14.2")
        self.assertEqual(clause_obj.category, "GOVERNING_LAW")
        self.assertEqual(clause_obj.jurisdiction, "State of New York")

    def test_categorize_paragraphs_invalid_document_id(self):
        """Posting with non-existent document_id returns 404."""
        payload = {
            "document_id": 99999,
            "save_to_db": True,
            "paragraphs": [
                {"text": "Sample clause text"}
            ]
        }
        response = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 404)




