import os
import uuid
from flask import Blueprint, request, jsonify, current_app

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return jsonify({"status": "running", "message": "Infotact Video Transcoding API"})


@bp.route("/api/upload", methods=["POST"])
def upload_chunk():
    """
    Placeholder endpoint for Week 1: Chunked Video Upload API
    """
    video_id = request.form.get("video_id") or str(uuid.uuid4())
    chunk_index = request.form.get("chunk_index", type=int)
    total_chunks = request.form.get("total_chunks", type=int)
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file chunk provided"}), 400

    # Ensure upload folder exists
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)

    # In Week 1, the intern will implement chunk assembly here.
    # We will simulate successful storage.
    file_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"], f"{video_id}_chunk_{chunk_index}"
    )
    file.save(file_path)

    return jsonify(
        {
            "message": f"Chunk {chunk_index}/{total_chunks} received successfully",
            "video_id": video_id,
            "status": "processing" if chunk_index < total_chunks - 1 else "completed",
        }
    )


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
