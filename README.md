# Infotact Solutions & Co. Internship Project
## Project 3: Media & Entertainment (OTT) - Video Transcoding & Analytics Pipeline

Welcome to your internship project repository. This guide details the **Four-Week Engineering Roadmap**, the strict **GitHub Version Control Rules**, **Commit Calendars**, and steps to set up your project workspace and automated issue tracker.

---

## 📅 Four-Week Engineering Roadmap

### Week 1: Flask Upload API and Storage Mocking
- Build a Flask application designed to handle large file uploads in chunks to prevent server memory overflow.
- Assign a unique UUID to every uploaded video asset and securely store the files in a simulated cloud storage folder (`src/app/storage/`).

### Week 2: Subprocess FFmpeg Transcoding Worker
- Write a background worker script in Python that uses the standard library `subprocess` module to run external `ffmpeg` commands.
- Transcode uploaded videos into `720p` and `480p` formats, and extract a preview thumbnail image from the video's 5-second mark.

### Week 3: Kafka Message Broker Integration
- Set up Apache Kafka (via Docker Compose) to enable event streaming.
- Add an API endpoint `/analytics/track` to receive video event logs (e.g. `play`, `pause`, `buffer`) and publish them to a Kafka topic.

### Week 4: Analytics Consumer and Final Polish
- Write a standalone Python Kafka Consumer daemon that subscribes to the event topic.
- Aggregate analytics data (such as total views/buffers per video) and persist updates into a PostgreSQL database container.
- Bundle the entire system (Flask API, Kafka, PostgreSQL, worker) into a unified `docker-compose.yml`.

---

## 🛠️ GitHub Guidelines & Evaluation Rules

To pass the evaluations (Mid Review and Final Review), you must adhere strictly to these rules:

### 1. Project Tracking and Issues
- Navigate to your repository's **Projects** tab on GitHub and set up a new **Kanban Board** (To Do, In Progress, Done).
- Your repository must contain the **16 weekly issues** (4 per week) that track this roadmap. Use the provided automated script to populate them.

### 2. Branching & Team Strategy
- **Solo Workers**: You can commit code directly to the `main` or `master` branch.
- **Team Workers**: Direct commits to `main`/`master` are strictly forbidden. You must create individual feature branches (e.g., `feature/week-1-upload`) and merge them via Pull Requests (PRs).

### 3. Commit Frequencies & Calendar
- **Mid Review (20th–27th)**: The repository must contain commits on at least **10 different days**.
- **Final Review (5th–10th)**: The repository must contain commits on **all 20 days** of the review period (no gaps allowed).
- Commits should happen frequently (3–5 times per active development day).

### 4. Semantic Commit Referencing
- Every commit must link to a specific GitHub Issue ID using semantic annotations.
- **Example Commit Message**: `feat: implemented FFmpeg subprocess for 720p transcoding (fixes #6)`
- Appending `(fixes #ID)` links your code directly to the Kanban board, providing clear audit evidence.

### 5. Commit Validity
*   **Valid Commits (✅)**: Code modifications, configuration changes, updates to tests, documentation (`README.md`, `HOW_TO_WORK.md`), or addition of required project assets.
*   **Invalid Commits (❌ - Immediate Failure)**: Empty commits, single-character modifications (gaming the commit history), auto-generated spam, or duplicated commits.

---

## 💻 Local Workspace Setup

### 1. Prerequisites
- **Python 3.10+**
- **Docker & Docker Compose** (for Kafka and PostgreSQL)
- **FFmpeg** installed on your system PATH

### 2. Setting Up Virtual Environment
Create a virtual environment to manage dependencies locally. **Never** commit this folder to Git (pre-configured in `.gitignore`).

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (Command Prompt):
.venv\Scripts\activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running Lint and Tests
To verify code formatting and syntax validity before committing:

```bash
# Run flake8 syntax linter
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Verify formatting check
black --check .

# Run test suite
pytest
```

---

## 🚀 Automatically Create GitHub Issues

We have written an automation script to create the 16 issues directly on your GitHub repository.

1. Generate a **GitHub Personal Access Token (classic or fine-grained)** with `repo` scopes.
2. Run the script:

```bash
# Dry run: view what issues will look like without publishing
python instructions/create_issues.py --dry-run

# Create the issues on your repository (replace with your token)
python instructions/create_issues.py --token YOUR_GITHUB_PERSONAL_ACCESS_TOKEN
```

If you prefer to create them manually, you can find the detailed issue specifications in [instructions/github_issues.md](file:///C:/Users/hello/Desktop/infotact/infotact/instructions/github_issues.md).

---

## 🐳 Running the Full Ecosystem with Docker Compose

The `docker-compose.yml` orchestrates **four services**: Zookeeper, Kafka, PostgreSQL, and the Analytics Consumer.

### Quick Start (single command)
```bash
# Build images and start all services in the background
docker compose up --build -d
```

### Verify all containers are running
```bash
docker compose ps
```

Expected output:
```
NAME                  STATUS
zookeeper             Up
kafka                 Up
postgres              Up
analytics_consumer    Up
```

### Check consumer logs (live)
```bash
docker compose logs -f consumer
```

### Send a test analytics event
With Kafka and the consumer running, publish a test `play` event:
```bash
# Install kcat (formerly kafkacat) or use docker exec
docker exec -it kafka bash -c \
  'echo "{\"video_id\":\"vid_001\",\"event\":\"play\",\"timestamp\":\"2026-01-01T00:00:00Z\"}" | \
   kafka-console-producer.sh --broker-list localhost:9092 --topic video-analytics'
```

### Verify the database record
```bash
docker exec -it postgres psql -U infotact -d infotactdb \
  -c "SELECT * FROM video_metrics;"
```

You should see `total_views = 1` for `vid_001`.

### Environment Variables

| Variable        | Default        | Description                   |
|-----------------|----------------|-------------------------------|
| `KAFKA_BROKERS` | `localhost:9092` | Kafka bootstrap address      |
| `DB_HOST`       | `localhost`    | PostgreSQL host               |
| `DB_PORT`       | `5432`         | PostgreSQL port               |
| `DB_NAME`       | `infotactdb`   | Database name                 |
| `DB_USER`       | `infotact`     | Database user                 |
| `DB_PASSWORD`   | `infotactpwd`  | Database password             |

### Stopping services
```bash
# Stop containers (keeps data volumes)
docker compose down

# Stop AND remove volumes (wipes database)
docker compose down -v
```
