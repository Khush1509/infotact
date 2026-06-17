# Infotact Internship Project - 16 GitHub Issues Checklist

This document contains the detailed specifications for the 16 GitHub issues that must be populated in the repository's Kanban board. Every issue corresponds to a specific technical task in the 4-week engineering roadmap.

---

## Issue 1: [CI/CD] Project Structure Setup and Github Actions CI
**Labels**: `week-1`, `cicd`, `setup`

### Description
Initialize the Python project structure and configure GitHub Actions CI for code quality checking. This serves as the engineering baseline for the repository.

### Tasks
- [ ] Create Python packages for web app (`app/`), worker (`worker/`), consumer (`consumer/`), and tests (`tests/`).
- [ ] Create `.gitignore` to prevent virtual environments (`.venv/`), environment secrets (`.env`), Python caches (`__pycache__/`), and video files from being checked into Git.
- [ ] Configure `requirements.txt` containing all necessary third-party libraries (`Flask`, `pytest`, `flake8`, `black`, etc.).
- [ ] Create a GitHub Actions workflow `.github/workflows/python-app.yml` that triggers on every push and PR to run `flake8` syntax checks, `black` style validation, and `pytest`.

### Acceptance Criteria
- Code layout exists with appropriate `__init__.py` files.
- Pushing to GitHub successfully triggers the CI pipeline.
- The CI pipeline runs linting and passes without errors.

---

## Issue 2: [Flask] Initialize Flask Application Boilerplate
**Labels**: `week-1`, `flask`, `boilerplate`

### Description
Create a basic Flask web server boilerplate, configure general settings, and set up local file storage configurations.

### Tasks
- [ ] Set up the entry point for Flask inside `app/__init__.py`.
- [ ] Create a config class in `app/config.py` that reads settings from environment variables (e.g., `UPLOAD_FOLDER` path, `MAX_CONTENT_LENGTH` set to 100MB limit).
- [ ] Implement a root route (`/`) in `app/routes.py` returning JSON with app status (`{"status": "running"}`).
- [ ] Verify the development server can spin up locally using a virtual environment.

### Acceptance Criteria
- Accessing `http://localhost:5000/` returns a successful JSON status page.
- Maximum payload limit of 100MB is successfully enforced by Flask configuration.

---

## Issue 3: [Flask] Implement Chunked Video Upload Endpoint
**Labels**: `week-1`, `flask`, `upload`

### Description
Create the Flask API endpoint `/api/upload` that handles large video uploads in chunks to prevent server memory overflow. Assign a unique UUID to each video asset.

### Tasks
- [ ] Create `/api/upload` endpoint accepting `POST` requests.
- [ ] Read multipart/form-data containing `video_id` (UUID), `chunk_index`, `total_chunks`, and the file binary.
- [ ] Generate a unique UUID if no `video_id` is passed.
- [ ] Implement a folder writing system where chunk pieces are temporarily saved.
- [ ] Merge the chunks sequentially when the final chunk is received and verify the integrity of the uploaded `.mp4` file.

### Acceptance Criteria
- Large files can be split into chunks (e.g. 5MB chunks) and uploaded sequentially without the Flask process running out of RAM.
- The final merged file is saved successfully in the simulated storage folder under its UUID name.

---

## Issue 4: [Testing] Write Unit Tests for Chunked Uploads and Storage
**Labels**: `week-1`, `testing`, `upload`

### Description
Write automated unit tests using `pytest` to verify that chunked video uploads function correctly and files are persisted as expected.

### Tasks
- [ ] Setup `tests/conftest.py` with pytest fixtures for the Flask test client.
- [ ] Write unit tests in `tests/test_upload.py` to check the root route.
- [ ] Write tests that simulate a multi-chunk upload request using mock binary data.
- [ ] Verify that final files are correctly merged and storage directories are cleaned up after test completion.

### Acceptance Criteria
- Executing `pytest` locally passes all tests.
- Upload tests check boundary conditions (e.g. missing file chunk, invalid chunk index).

---

## Issue 5: [Worker] Implement Asynchronous Background Task Queue
**Labels**: `week-2`, `worker`, `asynchronous`

### Description
Implement a lightweight asynchronous background processing mechanism in Python to queue transcoding tasks without blocking the Flask API requests.

### Tasks
- [ ] Create a threading-based task queue or background worker system within the Python codebase.
- [ ] Create a shared queue state where upload events insert a transcoding job.
- [ ] Implement worker threads that run concurrently in the background listening to the job queue.
- [ ] Link the Flask upload endpoint to automatically insert a transcoding job into the queue upon successful file merge.

### Acceptance Criteria
- When a video finishes uploading, the API response is returned immediately.
- The background thread starts processing the video asynchronously in the background.

---

## Issue 6: [Worker] Implement FFmpeg Command Invocation Module
**Labels**: `week-2`, `worker`, `ffmpeg`

### Description
Create a utility class/module in `worker/ffmpeg_worker.py` that interfaces with the FFmpeg command-line tool using Python's `subprocess` module.

### Tasks
- [ ] Install FFmpeg locally on the machine and confirm it is available in the system PATH.
- [ ] Write Python code utilizing `subprocess.run` to call FFmpeg CLI commands.
- [ ] Implement logging to capture FFmpeg standard output (stdout) and standard error (stderr).
- [ ] Add exception handling to identify if FFmpeg is missing or fails due to a corrupted video file.

### Acceptance Criteria
- The Python code can check for FFmpeg availability on startup.
- Invoking the module executes the external FFmpeg CLI binary and handles return codes correctly.

---

## Issue 7: [Worker] Add Multi-Resolution Transcoding and Thumbnail Extraction
**Labels**: `week-2`, `worker`, `ffmpeg`

### Description
Configure the FFmpeg subprocess worker to convert uploaded video files into 720p and 480p standard Web formats, and extract a preview thumbnail.

### Tasks
- [ ] Build the FFmpeg command to scale the video to 720p resolution and output it to the simulated storage folder.
- [ ] Build the FFmpeg command to scale the video to 480p resolution and output it.
- [ ] Write an FFmpeg command to capture a single frame at the 5-second mark of the video and save it as a `.png` thumbnail.
- [ ] Ensure output files are systematically named using the video asset's unique UUID.

### Acceptance Criteria
- Running a transcoding task produces three output assets: `uuid_720p.mp4`, `uuid_480p.mp4`, and `uuid_thumbnail.png`.
- The outputs are valid, playable video/image files.

---

## Issue 8: [Testing] Test FFmpeg Worker and Subprocess Execution
**Labels**: `week-2`, `testing`, `worker`

### Description
Create unit tests to validate the FFmpeg subprocess worker, mocking external CLI dependencies to ensure testing remains independent of system tools.

### Tasks
- [ ] Create `tests/test_worker.py`.
- [ ] Write tests that mock Python's `subprocess.run` to ensure correct commands and flags are passed to FFmpeg.
- [ ] Write integration tests that run the worker on a small, valid dummy video to verify successful local execution.
- [ ] Confirm error-handling tests catch failed subprocess calls gracefully.

### Acceptance Criteria
- Run `pytest` and confirm all worker-related mock/integration tests pass.
- Tests verify standard scaling filters (`-vf scale=-2:720`) are configured in the mock command arguments.

---

## Issue 9: [Docker] Configure Docker Compose for Apache Kafka
**Labels**: `week-3`, `docker`, `kafka`

### Description
Set up the Apache Kafka event-streaming broker locally using Docker Compose to establish an event pipeline.

### Tasks
- [ ] Write a `docker-compose.yml` file configuring Zookeeper and Apache Kafka services.
- [ ] Expose Kafka port `9092` to allow external connections from the Flask application.
- [ ] Set up the advertised listeners inside Docker variables to ensure the Python client can connect to the broker.
- [ ] Launch the containers and verify that Kafka is running and healthy.

### Acceptance Criteria
- Run `docker compose up -d` and verify both Zookeeper and Kafka containers are active.
- Verify communication with the broker is functional.

---

## Issue 10: [Kafka] Implement Kafka Producer Client Service
**Labels**: `week-3`, `kafka`, `producer`

### Description
Create a reusable Kafka Producer service inside the Flask application using Python libraries to publish events to a specific topic.

### Tasks
- [ ] Add `confluent-kafka` or equivalent to `requirements.txt`.
- [ ] Create a configuration setup in the Flask app to connect to the Kafka broker bootstrap address.
- [ ] Write a helper class/function that serializes Python dictionary objects into JSON strings.
- [ ] Initialize the Producer client and write a function to publish messages to the `video-analytics` topic with error callbacks.

### Acceptance Criteria
- The application can establish a persistent connection to Kafka on startup.
- Invoking the producer successfully pushes a test payload without blocking execution.

---

## Issue 11: [Flask] Add JSON Event Tracking Endpoint
**Labels**: `week-3`, `flask`, `analytics`

### Description
Implement a Flask endpoint `/analytics/track` designed to receive event payloads logging user actions on video assets.

### Tasks
- [ ] Write a route for `/analytics/track` accepting `POST` requests.
- [ ] Enforce payload schema validation (require: `video_id`, `event`, `timestamp`).
- [ ] Accept specific standard event types: `play`, `pause`, `buffer`, `complete`.
- [ ] Return standard error responses for malformed payloads.

### Acceptance Criteria
- POST request to `/analytics/track` with invalid parameters returns a `400 Bad Request` code.
- POST request with valid format returns `200 OK` indicating the request was processed.

---

## Issue 12: [Kafka] Publish Analytics Events to Kafka Topic
**Labels**: `week-3`, `kafka`, `analytics`

### Description
Integrate the Flask analytics endpoint with the Kafka Producer client to push real-time user engagement events to the message broker.

### Tasks
- [ ] Connect `/analytics/track` endpoint logic with the Kafka Producer service.
- [ ] Extract the request body data and serialize it to JSON.
- [ ] Publish the message payload to the `video-analytics` Kafka topic asynchronously.
- [ ] Write tests in `tests/test_analytics.py` verifying request forwarding logic and mock producer assertions.

### Acceptance Criteria
- Sending valid payloads to `/analytics/track` publishes them directly to Kafka.
- Running the automated test suite validates the integration.

---

## Issue 13: [Database] Set Up PostgreSQL Database & Database Schema
**Labels**: `week-4`, `docker`, `database`

### Description
Incorporate a PostgreSQL database container in the local Docker Compose configuration and define the table schema to store aggregated video metrics.

### Tasks
- [ ] Add a `db` service running the `postgres` image inside `docker-compose.yml`.
- [ ] Expose database port `5432` and persist data using local Docker volumes.
- [ ] Design a SQL schema for storing analytics (e.g. `video_metrics` table with fields: `video_id`, `total_views`, `total_buffers`, `total_playtime`).
- [ ] Write a script/migration file to automatically initialize the schema if tables do not exist.

### Acceptance Criteria
- Launching Docker Compose provisions a running database service.
- The schema is initialized correctly and tables are ready for querying.

---

## Issue 14: [Kafka] Implement Standalone Kafka Consumer Script
**Labels**: `week-4`, `kafka`, `consumer`

### Description
Create a standalone Python consumer daemon script (`consumer.py`) that runs continuously in the background, listening to the `video-analytics` Kafka topic.

### Tasks
- [ ] Create a script inside `consumer/analytics_consumer.py`.
- [ ] Configure the consumer to join the `analytics-group` consumer group.
- [ ] Write a polling loop that queries Kafka for new messages every few seconds.
- [ ] Implement error handling for disconnection, network failures, or unparseable messages.

### Acceptance Criteria
- Running `python consumer/analytics_consumer.py` initializes a persistent connection.
- The consumer prints logs indicating it is active and polling the Kafka topic.

---

## Issue 15: [Database] Aggregate and Persist Analytics Data
**Labels**: `week-4`, `database`, `consumer`

### Description
Implement logic in the Kafka consumer script to aggregate incoming video event payloads and update the PostgreSQL database.

### Tasks
- [ ] Write database connection code in the consumer using `psycopg2`.
- [ ] Implement an aggregation mechanism: parse incoming JSON message payloads (like `play` or `buffer`).
- [ ] Write SQL upsert queries to increment view counts (`total_views`) or buffer counts (`total_buffers`) based on the incoming events.
- [ ] Ensure database transactions are handled and closed safely.

### Acceptance Criteria
- Publishing multiple events (e.g., 5 `play` events for `video_1`) results in the database record for `video_1` incrementing `total_views` to `5`.
- Database operations are efficient and robust against race conditions.

---

## Issue 16: [Docker] Complete Ecosystem Integration & Comprehensive Documentation
**Labels**: `week-4`, `docker`, `docs`

### Description
Finalize the orchestration of the entire ecosystem using Docker Compose and write comprehensive setup documentation in the README.

### Tasks
- [ ] Complete the unified `docker-compose.yml` defining Flask application, celery/background worker, Kafka, Zookeeper, and PostgreSQL services.
- [ ] Configure environment variables to wire all components together (API -> Kafka, Consumer -> Kafka/Postgres).
- [ ] Update `README.md` with step-by-step instructions on spinning up the container ecosystem, configuring local settings, running lint checks, and testing the end-to-end flow.

### Acceptance Criteria
- Running a single `docker compose up --build` command launches the entire project pipeline.
- End-to-end flow is fully documented in `README.md` and verification commands work correctly.
