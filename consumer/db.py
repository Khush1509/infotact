"""db.py – PostgreSQL persistence layer for the analytics consumer.

Provides a connection factory and an upsert helper that increments
video metric counters (views, buffers, playtime) atomically.
"""

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

# ── Connection settings (override via environment variables) ──────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "infotactdb")
DB_USER = os.getenv("DB_USER", "infotact")
DB_PASSWORD = os.getenv("DB_PASSWORD", "infotactpwd")

log = logging.getLogger(__name__)

# ── DDL ────────────────────────────────────────────────────────────────────
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS video_metrics (
    video_id       TEXT PRIMARY KEY,
    total_views    INTEGER NOT NULL DEFAULT 0,
    total_buffers  INTEGER NOT NULL DEFAULT 0,
    total_playtime REAL    NOT NULL DEFAULT 0.0,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# ── Upsert SQL ─────────────────────────────────────────────────────────────
UPSERT_SQL = """
INSERT INTO video_metrics (video_id, total_views, total_buffers, total_playtime)
VALUES (%s, %s, %s, %s)
ON CONFLICT (video_id) DO UPDATE SET
    total_views    = video_metrics.total_views    + EXCLUDED.total_views,
    total_buffers  = video_metrics.total_buffers  + EXCLUDED.total_buffers,
    total_playtime = video_metrics.total_playtime + EXCLUDED.total_playtime,
    updated_at     = NOW();
"""


def get_connection():
    """Return a new psycopg2 connection.  Caller is responsible for closing."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
    )


def ensure_schema(conn):
    """Create the video_metrics table if it does not already exist."""
    with conn.cursor() as cur:
        cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    log.info("Database schema verified / created.")


def aggregate_event(conn, event_data: dict):
    """Parse an incoming event dict and upsert the corresponding metric row.

    Supported event types:
        - play      → increments total_views by 1
        - buffer    → increments total_buffers by 1
        - complete  → increments total_playtime by event duration (seconds)
        - pause     → no metric update (logged only)

    Args:
        conn:        An open psycopg2 connection.
        event_data:  Decoded JSON payload dict with keys
                     ``video_id``, ``event``, ``timestamp`` and optional
                     ``duration`` (float, seconds).
    """
    video_id = event_data.get("video_id")
    event = event_data.get("event")

    if not video_id or not event:
        log.warning("Skipping event — missing video_id or event field: %s", event_data)
        return

    delta_views = 0
    delta_buffers = 0
    delta_playtime = 0.0

    if event == "play":
        delta_views = 1
    elif event == "buffer":
        delta_buffers = 1
    elif event == "complete":
        delta_playtime = float(event_data.get("duration", 0))
    elif event == "pause":
        log.debug("Pause event for %s — no metric update.", video_id)
        return
    else:
        log.warning("Unknown event type '%s' for video %s — skipping.", event, video_id)
        return

    try:
        with conn.cursor() as cur:
            cur.execute(UPSERT_SQL, (video_id, delta_views, delta_buffers, delta_playtime))
        conn.commit()
        log.info("Upserted: video=%s event=%s views+%d buffers+%d playtime+%.1fs",
                 video_id, event, delta_views, delta_buffers, delta_playtime)
    except Exception as exc:
        conn.rollback()
        log.error("DB upsert failed for video %s: %s", video_id, exc)
        raise
