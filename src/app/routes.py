import os
import uuid
from flask import Blueprint, request, jsonify, current_app

try:
    from worker import queue_transcoding_job
except ImportError:
    from src.worker import queue_transcoding_job

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return jsonify({"status": "running", "message": "Infotact Video Transcoding API"})


@bp.route("/api/upload", methods=["POST"])
def upload_chunk():
    """
    Handle chunked video uploads.
    Expected form fields:
      - video_id (optional UUID string). If omitted, a new UUID is generated.
      - chunk_index (int): zero‑based index of this chunk.
      - total_chunks (int): total number of chunks for the video.
      - file: binary chunk payload.
    Chunks are stored temporarily under the configured UPLOAD_FOLDER in a subdirectory
    named after the video_id. When the final chunk arrives, all chunks are merged in order
    to reconstruct the original video file. The merged file is saved as <video_id>.mp4.
    """
    # Retrieve or generate a video identifier
    video_id = request.form.get("video_id") or str(uuid.uuid4())
    # Parse integer parameters safely
    try:
        chunk_index = int(request.form.get("chunk_index"))
        total_chunks = int(request.form.get("total_chunks"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid chunk_index or total_chunks"}), 400

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file chunk provided"}), 400

    # Prepare a dedicated directory for this video's chunks
    upload_root = current_app.config["UPLOAD_FOLDER"]
    video_dir = os.path.join(upload_root, video_id)
    os.makedirs(video_dir, exist_ok=True)

    # Save the incoming chunk
    chunk_path = os.path.join(video_dir, f"chunk_{chunk_index:05d}")  # zero‑pad for sorting
    file.save(chunk_path)

    # If this is the final chunk, attempt to assemble the full video
    if chunk_index == total_chunks - 1:
        # Verify that all expected chunks are present
        missing = []
        for i in range(total_chunks):
            expected_path = os.path.join(video_dir, f"chunk_{i:05d}")
            if not os.path.exists(expected_path):
                missing.append(i)
        if missing:
            return jsonify({
                "error": "Missing chunks",
                "missing_chunks": missing,
                "video_id": video_id,
                "status": "incomplete"
            }), 400
        # Assemble the final file
        final_path = os.path.join(upload_root, f"{video_id}.mp4")
        try:
            with open(final_path, "wb") as outfile:
                for i in range(total_chunks):
                    chunk_file = os.path.join(video_dir, f"chunk_{i:05d}")
                    with open(chunk_file, "rb") as infile:
                        outfile.write(infile.read())
        except Exception as e:
            return jsonify({"error": f"Failed to assemble video: {str(e)}"}), 500
        # Cleanup temporary chunk directory
        try:
            for i in range(total_chunks):
                os.remove(os.path.join(video_dir, f"chunk_{i:05d}"))
            os.rmdir(video_dir)
        except Exception:
            pass  # Non‑critical if cleanup fails
        # Queue background transcoding task
        queue_transcoding_job(final_path, upload_root, video_id)

        return jsonify({
            "message": "Upload complete and file assembled",
            "video_id": video_id,
            "file_path": final_path,
            "status": "completed",
        })
    else:
        # Not the final chunk – acknowledge receipt
        return jsonify({
            "message": f"Chunk {chunk_index + 1}/{total_chunks} received",
            "video_id": video_id,
            "status": "processing",
        })


@bp.route("/analytics/track", methods=["POST"])
def track_analytics():
    """
    Placeholder endpoint for Week 3: Kafka Message Broker Integration
    """
    data = request.get_json()
    if (
        not data
        or "video_id" not in data
        or "event" not in data
        or "timestamp" not in data
    ):
        return jsonify({"error": "Invalid analytics payload"}), 400

    # In Week 3, the intern will publish this payload to a Kafka topic.
    return jsonify(
        {
            "status": "success",
            "message": "Event queued for streaming",
            "data_received": data,
        }
    )
