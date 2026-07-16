# Infotact Solutions & Co. Internship Projects

This repository hosts the development projects for the Infotact Solutions & Co. internship. It is organized into distinct project directories, each representing a complete application stack.

---

## 📁 Repository Directory Structure

The repository is structured as follows:

```text
infotact/
├── project1/            # Media & Entertainment (OTT) - Video Transcoding & Analytics Pipeline
│   ├── src/             # Flask API & Worker application
│   ├── consumer/        # Kafka Analytics Consumer daemon
│   ├── README.md        # Detailed setup guide for Project 1
│   └── ...
└── project2/            # LegalTech Parsing Engine
    ├── legaltech_parser/# Django settings and root URL configuration
    ├── parser/          # Django App for contract analysis & secure PDF handling
    ├── README.md        # Detailed setup guide for Project 2
    └── ...
```

---

## 🏗️ Project Overviews

### 📹 [Project 1: OTT Video Transcoding & Analytics Pipeline](./project1)
A high-throughput video processing and analytics platform built with Flask, Apache Kafka, and PostgreSQL.
- **Chunked Video Uploads**: Handles large files cleanly.
- **FFmpeg Transcoding Worker**: Automatically generates 720p/480p transcoded copies and extracts a preview thumbnail.
- **Kafka Analytics Pipeline**: Streams user watch events (`play`, `pause`, `buffer`, etc.) through a message broker.
- **Consumer Aggregation**: Persists aggregated viewer statistics to a PostgreSQL database.

👉 [Go to Project 1 README](./project1/README.md)

---

### 📄 [Project 2: LegalTech Contract Parsing Engine](./project2)
An intelligent document analysis system built on Django 5.x, Django REST Framework, and PostgreSQL.
- **Secure PDF Upload API**: Validates incoming PDF documents against spoofed content-types and executes magic-byte verification (`%PDF-`).
- **Pluggable Storage System**: Supports secure local storage (with sanitized, UUID-prefixed file paths) or mock S3 storage backends.
- **Database Integrity**: Employs atomic transactions to ensure clean rolls back if any file in a batch upload fails verification.
- **Metadata Association**: Tracks file sizes, original names, and SHA-256 hashes for deduplication and logging.

👉 [Go to Project 2 README](./project2/README.md)
