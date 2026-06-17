from unittest.mock import patch
from worker.ffmpeg_worker import transcode_video


@patch("subprocess.run")
def test_transcode_video_signature(mock_run):
    """
    Test the basic flow of the transcode_video function.
    """
    # Mock ffmpeg version check success
    mock_run.return_value.returncode = 0

    result = transcode_video(
        input_path="dummy_input.mp4",
        output_dir="dummy_output",
        video_id="test_id_5678",
    )
    # The function should invoke mock_run for the version check
    assert mock_run.called
    assert result is True
