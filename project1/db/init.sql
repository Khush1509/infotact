-- init.sql
-- Automatically executed by the postgres Docker container on first boot.
-- Creates the video_metrics table for analytics aggregation.

CREATE TABLE IF NOT EXISTS video_metrics (
    video_id       TEXT PRIMARY KEY,
    total_views    INTEGER     NOT NULL DEFAULT 0,
    total_buffers  INTEGER     NOT NULL DEFAULT 0,
    total_playtime REAL        NOT NULL DEFAULT 0.0,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
