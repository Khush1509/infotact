# LegalTech Parsing Engine - Detailed Setup Guide

## 📖 Overview
This repository contains the LegalTech Parsing Engine built on **Django 5.x** and **Django REST Framework**. It provides a robust API for uploading PDFs, extracting clauses, categorising them, and evaluating legal risk.

---

## 🏗️ Architecture
- **Web Framework:** Django 5.x
- **Database:** PostgreSQL 15 (default port `5433` to avoid conflicts with other services)
- **Configuration:** Environment variables managed with `python-dotenv`

---

## 🚀 Quick Start (Docker Compose)
### 1️⃣ Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` if you need to customise settings (e.g., DB credentials, debug mode).

### 2️⃣ Launch the stack
```bash
docker compose up --build
```
This starts:
1. `legaltech_postgres` – PostgreSQL database
2. `legaltech_web` – Django application (auto‑applies migrations on start)

### 3️⃣ Verify the service
```bash
curl http://localhost:8000/health/
```
Expected response:
```json
curl -X POST -F "files=@contract1.pdf" -F "files=@contract2.pdf" http://localhost:8000/api/v1/contracts/upload/
```
Expected response:
```json
{
  "count": 2,
  "documents": [
    {
      "id": 1,
      "file": "/media/documents/uuid_contract1.pdf",
      "original_filename": "contract1.pdf",
      "file_size": 1024,
      "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "storage_backend": "local",
      "uploaded_at": "2026-07-18T12:00:00Z"
    },
    {
      "id": 2,
      "file": "/media/documents/uuid_contract2.pdf",
      "original_filename": "contract2.pdf",
      "file_size": 2048,
      "content_hash": "3f786850e387550fdab836ed7e6dc881de23001bdec7ae495991b7852b855aa1",
      "storage_backend": "local",
      "uploaded_at": "2026-07-18T12:00:05Z"
    }
  ]
}
```

### Step 5 — Categorize Paragraphs, Extract Jurisdiction & Evaluate Risk
Users can submit contract paragraphs to classify clause types, isolate governing law jurisdictions, and evaluate legal risks across sentences/paragraphs:
```bash
curl -X POST -H "Content-Type: application/json" -d '{
  "evaluate_risk": true,
  "paragraphs": [
    {
      "clause_number": "14.1",
      "text": "Supplier agrees to indemnify and hold harmless Buyer against any and all claims without limit. There is no limitation of liability under this agreement."
    }
  ]
}' http://localhost:8000/api/v1/clauses/categorize/
```
Expected response:
```json
{
  "count": 1,
  "document_id": null,
  "saved_to_db": false,
  "results": [
    {
      "clause_number": "14.1",
      "text": "Supplier agrees to indemnify and hold harmless Buyer against any and all claims without limit. There is no limitation of liability under this agreement.",
      "category": "INDEMNIFICATION",
      "jurisdiction": null,
      "risk_evaluation": {
        "has_risk": true,
        "overall_risk_score": 0.95,
        "risk_level": "HIGH",
        "risk_flags": [
          {
            "flag_type": "UNLIMITED_INDEMNITY",
            "description": "Clause contains uncapped or broad indemnification obligations.",
            "confidence_score": 0.9,
            "matched_text": "Supplier agrees to indemnify and hold harmless Buyer against any and all claims without limit."
          },
          {
            "flag_type": "UNLIMITED_LIABILITY",
            "description": "Clause removes or lacks liability caps, exposing the entity to unlimited liability.",
            "confidence_score": 0.95,
            "matched_text": "There is no limitation of liability under this agreement."
          }
        ]
      }
    }
  ]
}
```


---

## 💻 Local Development Setup

If you prefer to run the Django server directly on your host machine while connecting to the database:

### Step 1 — Create and Activate Virtual Environment
```bash
# Create environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate
```

### Step 2 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Spin Up Database Only
Use Docker Compose to run just the PostgreSQL database container:
```bash
docker compose up -d db
```

### Step 4 — Configure Local Environment
Ensure your `.env` file points to the local database mapping (port `5433` on `localhost`):
```env
DEBUG=True
SECRET_KEY=legaltech-local-development-secret-key-12345
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=legaltech_db
DB_USER=legaltech_user
DB_PASSWORD=legaltech_pass
DB_HOST=localhost
DB_PORT=5433
```

### Step 5 — Apply Migrations & Run Development Server
```bash
# Run migrations
python manage.py migrate

# Start server
python manage.py runserver 8000
```
The application will be available at `http://127.0.0.1:8000/`.

---

## 🧪 Testing

To run the suite of automated tests:

### Running locally
```bash
python manage.py test
```

### Running inside Docker
```bash
docker compose exec web python manage.py test
```
