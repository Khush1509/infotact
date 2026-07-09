# Infotact Solutions & Co. Internship Project
## Project 3: Media & Entertainment (OTT) — Video Transcoding & Analytics Pipeline

Welcome to the Infotact internship repository. This guide covers the **Four-Week Engineering Roadmap**, **GitHub version control rules**, and complete **setup & deployment instructions** for the full ecosystem.

---

## 📋 Table of Contents
1. [Architecture Overview](#-architecture-overview)
2. [Four-Week Roadmap](#-four-week-engineering-roadmap)
3. [GitHub Guidelines & Rules](#-github-guidelines--evaluation-rules)
4. [Quick Start (Docker)](#-quick-start-with-docker-compose)
5. [Local Development Setup](#-local-development-setup)
6. [Running Lint & Tests](#-running-lint-and-tests)
7. [End-to-End Flow Verification](#-end-to-end-flow-verification)
8. [Environment Variables](#-environment-variables)
9. [GitHub Issues Automation](#-automatically-create-github-issues)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Network                               │
│                                                                     │
│  ┌──────────────┐    video-analytics     ┌─────────────────────┐   │
│  │  Flask API   │ ──── Kafka Topic ────► │ Analytics Consumer  │   │
│  │  (port 5000) │                        │   (daemon script)   │   │
│  │              │                        │         │           │   │
│  │  + FFmpeg    │                        │         ▼           │   │
│  │    Worker    │                        │    PostgreSQL DB     │   │
│  └──────────────┘                        └─────────────────────┘   │
│         │                                        │                  │
│         └──────────── Kafka ◄── Zookeeper        │                  │
│                       (port 9092)                │                  │
│                                                  │                  │
│                                     PostgreSQL (port 5432)          │
└─────────────────────────────────────────────────────────────────────┘
```

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Flask API + Worker | `flask_api` | `5000` | Upload, transcode, publish analytics events |
| Analytics Consumer | `analytics_consumer` | — | Consume Kafka events, persist to DB |
| Apache Kafka | `kafka` | `9092` | Event streaming broker |
| Zookeeper | `zookeeper` | `2181` | Kafka coordination |
| PostgreSQL | `postgres` | `5432` | Analytics metrics storage |

---

## 📅 Four-Week Engineering Roadmap

### Week 1: Flask Upload API and Storage Mocking
- Build a Flask application to handle large file uploads in chunks to prevent server memory overflow.
- Assign a unique UUID to every uploaded video asset and store files in `src/app/storage/`.

### Week 2: Subprocess FFmpeg Transcoding Worker
- Background worker using Python's `subprocess` module to run `ffmpeg` commands.
- Transcode uploaded videos into `720p` and `480p` formats and extract a preview thumbnail at the 5-second mark.

### Week 3: Kafka Message Broker Integration
- Set up Apache Kafka via Docker Compose for event streaming.
- Add `/analytics/track` endpoint to receive and publish video events (`play`, `pause`, `buffer`, `complete`) to the `video-analytics` Kafka topic.

### Week 4: Analytics Consumer and Final Polish
- Standalone Kafka Consumer daemon (`consumer/analytics_consumer.py`) subscribing to the event topic.
- Aggregate analytics data (total views/buffers/playtime per video) and persist to PostgreSQL.
- Full ecosystem orchestrated via a single `docker-compose.yml`.

---

## 🛠️ GitHub Guidelines & Evaluation Rules

### 1. Project Tracking and Issues
- Navigate to the repository's **Projects** tab and set up a **Kanban Board** (To Do → In Progress → Done).
- The repository must contain **16+ weekly issues** (4 per week). Use the provided automation script to populate them.

### 2. Branching Strategy
- **Solo workers**: Commit directly to `main`.
- **Team workers**: Use feature branches (e.g. `feature/week-1-upload`) and merge via Pull Requests.

### 3. Commit Frequency & Calendar
- **Mid Review (20th–27th)**: Commits on at least **10 different days**.
- **Final Review (5th–10th)**: Commits on **all 20 days** (no gaps).
- Aim for **3–5 commits per active development day**.

### 4. Semantic Commit Referencing
Every commit must link to a GitHub Issue:
```
feat: implement FFmpeg subprocess for 720p transcoding (fixes #6)
```

### 5. Commit Validity
- ✅ **Valid**: Code changes, config, tests, documentation, project assets.
- ❌ **Invalid**: Empty commits, single-character changes, spam, duplicate commits.

---

## 🚀 Quick Start with Docker Compose

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### Step 1 — Clone the repository
```bash
git clone https://github.com/Khush1509/infotact.git
cd infotact
```

### Step 2 — Configure environment variables
```bash
# Copy the example file
copy .env.example .env   # Windows
# OR
cp .env.example .env     # macOS/Linux

# Edit .env and set a strong SECRET_KEY
notepad .env             # Windows
```

### Step 3 — Launch the entire ecosystem
```bash
docker compose up --build
```

> All 5 services will start: **Zookeeper → Kafka → PostgreSQL → Flask API → Analytics Consumer**

### Step 4 — Verify all containers are running
```bash
docker compose ps
```

Expected output:
```
NAME                  SERVICE    STATUS     PORTS
zookeeper             zookeeper  Up         0.0.0.0:2181->2181/tcp
kafka                 kafka      Up         0.0.0.0:9092->9092/tcp
postgres              db         Up         0.0.0.0:5432->5432/tcp
flask_api             api        Up         0.0.0.0:5000->5000/tcp
analytics_consumer    consumer   Up
```

### Step 5 — Check the Flask API
```bash
curl http://localhost:5000/
```
Expected: `{"status": "running"}`

### Stopping the ecosystem
```bash
# Stop containers (keeps data)
docker compose down

# Stop and wipe all data volumes
docker compose down -v
```

---

## 💻 Local Development Setup

### Prerequisites
- Python 3.10+
- FFmpeg installed and on system PATH
- Docker & Docker Compose (for Kafka and PostgreSQL)

### Step 1 — Create and activate a virtual environment
```bash
# Create virtual environment
python -m venv .venv

# Activate — Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate — macOS/Linux
source .venv/bin/activate
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Start infrastructure services only
```bash
# Start Kafka, Zookeeper, and PostgreSQL only (not the app containers)
docker compose up -d zookeeper kafka db
```

### Step 4 — Configure local environment
```bash
copy .env.example .env
# Edit .env — change KAFKA_BOOTSTRAP_SERVERS=localhost:9092 and DB_HOST=localhost
```

### Step 5 — Run the Flask application locally
```bash
python run.py
```

### Step 6 — Run the consumer daemon locally (separate terminal)
```bash
python infotact/consumer/analytics_consumer.py
```

---

## 🧪 Running Lint and Tests

### Syntax check (flake8)
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### Style validation (black)
```bash
# Check only (no changes)
black --check .

# Auto-format
black .
```

### Run test suite (pytest)
```bash
pytest
```

### Run all checks together (Windows PowerShell)
```powershell
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
black --check .
pytest
```

---

## 🔄 End-to-End Flow Verification

With the full ecosystem running (`docker compose up --build`):

### 1. Check Flask API status
```bash
curl http://localhost:5000/
# Expected: {"status": "running"}
```

### 2. Upload a video chunk
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "video_id=vid_001" \
  -F "chunk_index=0" \
  -F "total_chunks=1" \
  -F "file=@/path/to/your/video.mp4"
```

### 3. Send an analytics event
```bash
curl -X POST http://localhost:5000/analytics/track \
  -H "Content-Type: application/json" \
  -d '{"video_id": "vid_001", "event": "play", "timestamp": "2026-01-01T00:00:00Z"}'
# Expected: {"status": "ok"}
```

### 4. Send multiple events and verify aggregation
```bash
# Send 5 play events
for i in 1 2 3 4 5; do
  curl -s -X POST http://localhost:5000/analytics/track \
    -H "Content-Type: application/json" \
    -d "{\"video_id\": \"vid_001\", \"event\": \"play\", \"timestamp\": \"2026-01-01T00:00:0${i}Z\"}"
done
```

### 5. Query the database to confirm aggregation
```bash
docker exec -it postgres psql -U infotact -d infotactdb \
  -c "SELECT video_id, total_views, total_buffers, total_playtime FROM video_metrics;"
```

Expected output:
```
 video_id | total_views | total_buffers | total_playtime
----------+-------------+---------------+----------------
 vid_001  |           5 |             0 |            0.0
```

### 6. Watch consumer logs live
```bash
docker compose logs -f consumer
```

---

## 🌍 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me-in-production` | Flask secret key |
| `UPLOAD_FOLDER` | `/app/storage` | Directory for uploaded video files |
| `FLASK_ENV` | `development` | Flask environment mode |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address (Flask API) |
| `KAFKA_BROKERS` | `kafka:9092` | Kafka broker address (Consumer) |
| `DATABASE_URL` | `postgresql://infotact:infotactpwd@db:5432/infotactdb` | Full DB URL (Flask) |
| `DB_HOST` | `db` | PostgreSQL host (Consumer) |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `infotactdb` | Database name |
| `DB_USER` | `infotact` | Database user |
| `DB_PASSWORD` | `infotactpwd` | Database password |

---

## 🤖 Automatically Create GitHub Issues

A script is provided to create all 16 issues directly on your GitHub repository.

1. Generate a **GitHub Personal Access Token** with `repo` scopes at [github.com/settings/tokens](https://github.com/settings/tokens).
2. Run the script:

```bash
# Dry run — preview without publishing
python instructions/create_issues.py --dry-run

# Create all issues on GitHub (replace with your token)
python instructions/create_issues.py --token YOUR_GITHUB_PERSONAL_ACCESS_TOKEN
```

If you prefer to create them manually, see [instructions/github_issues.md](instructions/github_issues.md) for the full issue specifications.

---

## 📁 Project Structure

```
infotact/
├── Dockerfile                  # Flask API image
├── Dockerfile.consumer         # Analytics consumer image
├── docker-compose.yml          # Full 5-service ecosystem
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
├── run.py                      # Local Flask entry point
├── db/
│   └── init.sql                # PostgreSQL schema init script
└── infotact/
    ├── src/
    │   └── app/
    │       ├── __init__.py     # Flask app factory
    │       ├── config.py       # App configuration
    │       ├── routes.py       # API endpoints
    │       └── kafka_producer.py
    │   └── worker/
    │       ├── __init__.py     # Background worker threads
    │       └── ffmpeg_worker.py
    ├── consumer/
    │   ├── analytics_consumer.py  # Kafka consumer daemon
    │   └── db.py                  # PostgreSQL persistence layer
    └── tests/
        ├── test_upload.py
        ├── test_analytics.py
        └── test_worker.py
```
