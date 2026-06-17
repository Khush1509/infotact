import io

def test_index_route(client):
    """
    Test that the root route responds with running status.
    """
    response = client.get('/')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'running'

def test_upload_chunk_basic(client):
    """
    Test upload of a file chunk.
    """
    data = {
        'video_id': 'test-uuid-1234',
        'chunk_index': 0,
        'total_chunks': 3,
        'file': (io.BytesIO(b"dummy chunk content"), 'chunk.bin')
    }
    response = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'processing'
    assert 'received successfully' in json_data['message']
