import io
import os
import uuid
from flask import current_app


def test_index_route(client):
    """
    Test that the root route responds with running status.
    """
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "running"


def test_upload_chunk_basic(client):
    """
    Test upload of a file chunk.
    """
    data = {
        "video_id": "test-uuid-1234",
        "chunk_index": 0,
        "total_chunks": 3,
        "file": (io.BytesIO(b"dummy chunk content"), "chunk.bin"),
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "processing"
    assert "received" in json_data["message"]


def test_upload_single_chunk_generates_uuid(client):
    """
    Test that if no video_id is provided, a valid UUID is generated.
    """
    data = {
        "chunk_index": 0,
        "total_chunks": 2,
        "file": (io.BytesIO(b"first chunk"), "chunk.bin"),
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "processing"
    assert "video_id" in json_data
    # Assert that video_id is a valid UUID
    val = uuid.UUID(json_data["video_id"], version=4)
    assert str(val) == json_data["video_id"]


def test_upload_full_video_assembly(app, client):
    """
    Test a full multi-chunk upload where chunks are merged into a final file
    and temporary chunk directory is cleaned up.
    """
    video_id = str(uuid.uuid4())
    chunks = [
        b"First chunk payload.",
        b" Second chunk payload.",
        b" Third chunk payload."
    ]

    # Upload non-final chunks
    for idx, content in enumerate(chunks[:-1]):
        data = {
            "video_id": video_id,
            "chunk_index": idx,
            "total_chunks": len(chunks),
            "file": (io.BytesIO(content), f"chunk_{idx}.bin")
        }
        response = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["status"] == "processing"
        assert json_data["video_id"] == video_id

    # Upload final chunk
    final_idx = len(chunks) - 1
    data = {
        "video_id": video_id,
        "chunk_index": final_idx,
        "total_chunks": len(chunks),
        "file": (io.BytesIO(chunks[-1]), f"chunk_{final_idx}.bin")
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "completed"
    assert json_data["video_id"] == video_id

    # Verify that the final merged file exists and has correct contents
    upload_root = app.config["UPLOAD_FOLDER"]
    final_path = os.path.join(upload_root, f"{video_id}.mp4")
    assert os.path.exists(final_path)

    with open(final_path, "rb") as f:
        merged_content = f.read()
    assert merged_content == b"".join(chunks)

    # Verify that the temporary chunk directory was removed
    video_dir = os.path.join(upload_root, video_id)
    assert not os.path.exists(video_dir)


def test_upload_boundary_missing_file_chunk(client):
    """
    Test chunk upload with missing file chunk.
    """
    data = {
        "video_id": "test-boundary-uuid",
        "chunk_index": 0,
        "total_chunks": 3,
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data
    assert json_data["error"] == "No file chunk provided"


def test_upload_boundary_invalid_indices(client):
    """
    Test chunk upload with invalid non-integer index or total chunks.
    """
    data = {
        "video_id": "test-boundary-uuid",
        "chunk_index": "not-an-int",
        "total_chunks": 3,
        "file": (io.BytesIO(b"data"), "chunk.bin"),
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data

    data = {
        "video_id": "test-boundary-uuid",
        "chunk_index": 0,
        "total_chunks": "not-an-int",
        "file": (io.BytesIO(b"data"), "chunk.bin"),
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data


def test_upload_boundary_missing_chunks_during_assembly(client):
    """
    Test that if a chunk is skipped and the final chunk is uploaded,
    it returns 400 with a list of missing chunks.
    """
    video_id = str(uuid.uuid4())
    # Upload chunk 0
    data = {
        "video_id": video_id,
        "chunk_index": 0,
        "total_chunks": 3,
        "file": (io.BytesIO(b"first chunk"), "chunk.bin"),
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 200

    # Skip chunk 1, attempt to upload final chunk (index 2)
    data = {
        "video_id": video_id,
        "chunk_index": 2,
        "total_chunks": 3,
        "file": (io.BytesIO(b"final chunk"), "chunk.bin"),
    }
    response = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["error"] == "Missing chunks"
    assert json_data["missing_chunks"] == [1]
    assert json_data["status"] == "incomplete"
