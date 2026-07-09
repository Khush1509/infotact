import unittest.mock


def test_track_analytics_kafka_send(client):
    """Verify that analytics endpoint forwards payload to Kafka producer."""
    # Replace the real producer with a mock
    app = client.application
    mock_producer = unittest.mock.Mock()
    app.kafka_producer = mock_producer
    payload = {
        "video_id": "test-video-99",
        "event": "play",
        "timestamp": "2026-06-17T11:15:00Z",
    }
    response = client.post("/analytics/track", json=payload)
    assert response.status_code == 200
    # Ensure the producer's send method was called with the payload
    mock_producer.send.assert_called_once_with(payload)


    """
    Test analytics endpoint with valid payload
    """
    payload = {
        "video_id": "test-video-99",
        "event": "play",
        "timestamp": "2026-06-17T11:15:00Z",
    }
    response = client.post("/analytics/track", json=payload)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "success"
    assert json_data["data_received"]["event"] == "play"


def test_track_analytics_invalid(client):
    """
    Test analytics endpoint with missing parameters
    """
    payload = {
        "video_id": "test-video-99"
        # missing event and timestamp
    }
    response = client.post("/analytics/track", json=payload)
    assert response.status_code == 400
