import subprocess
from unittest.mock import patch
from worker.ffmpeg_worker import transcode_video

@patch("subprocess.run")
@patch("os.path.exists")
@patch("os.path.getsize")
def test_transcode_video_subprocess_failure(mock_getsize, mock_exists, mock_run):
    """Simulate subprocess.run raising CalledProcessError to ensure transcode_video handles errors gracefully."""
    # Setup mocks: input file exists and size >0
    mock_exists.return_value = True
    mock_getsize.return_value = 1000
    # Configure subprocess.run to raise an error
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd="ffmpeg",
        output="",
        stderr="Invalid data found when processing input"
    )
    result = transcode_video(
        input_path="dummy_input.mp4",
        output_dir="dummy_output",
        video_id="test_video_error"
    )
    # The function should catch the error and return False
    assert result is False
    # Ensure subprocess.run was called at least once
    assert mock_run.called
