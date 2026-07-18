# LegalTech Parsing Engine - Foundational Django Project

This is the foundational Django project for the **LegalTech Parsing Engine**, configured to connect with a PostgreSQL database.

---

## 🏗️ Architecture

- **Web Framework:** Django 5.x
- **Database:** PostgreSQL 15 (running on port `5433` locally to avoid port conflicts with project1)
- **Configuration:** Managed dynamically via environment variables (`python-dotenv`)

---

## 🚀 Quick Start (Docker Compose)

The easiest way to run the application and the database together is using Docker Compose.

### Step 1 — Set up Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```

### Step 2 — Launch Containers
Build and run the stack:
```bash
docker compose up --build
```
This starts:
1. `legaltech_postgres` (PostgreSQL database service)
2. `legaltech_web` (Django application, automatically applies migrations on startup)

### Step 3 — Verify the Setup
Visit the health check endpoint:
```bash
curl http://localhost:8000/health/
```
Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "error": null
}
```

### Step 4 — Upload Batch PDF Contracts
Users (like paralegals) can upload batch PDF contracts to the DRF endpoint via `multipart/form-data`:
```bash
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
