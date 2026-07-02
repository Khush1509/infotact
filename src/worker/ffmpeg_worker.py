import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FFmpegWorker:
    """
    Utility class that interfaces with the FFmpeg command-line tool.
    """
    def __init__(self):
        self.ffmpeg_available = self._check_and_add_ffmpeg_path()
        if not self.ffmpeg_available:
            logger.warning("FFmpeg not found during initialization.")

    def _check_and_add_ffmpeg_path(self):
        """
        Ensure ffmpeg is in PATH. If not, look in common WinGet locations
        and dynamically append them to the environment variables.
        """
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Append WinGet path additions
        paths_to_check = [
            r"C:\Users\hello\AppData\Local\Microsoft\WinGet\Links",
            r"C:\Users\hello\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
        ]
        for path in paths_to_check:
            if os.path.exists(path) and path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")

        # Re-verify availability
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def execute_command(self, cmd):
        """
        Execute an FFmpeg command, capturing stdout and stderr,
        and raising an exception if it fails or if the file is corrupted.
        """
        if not self.ffmpeg_available:
            raise RuntimeError("FFmpeg is not available on the system.")

        logger.info(f"Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logger.debug(f"Command stdout: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed with exit code {e.returncode}")
            logger.error(f"FFmpeg stderr:\n{e.stderr}")
            if "Invalid data found when processing input" in e.stderr or "moov atom not found" in e.stderr or "corrupt" in e.stderr.lower():
                raise ValueError(f"Corrupted video file or invalid format. Details: {e.stderr}")
            raise RuntimeError(f"FFmpeg process failed. Details: {e.stderr}")
        except FileNotFoundError:
            logger.error("FFmpeg executable not found.")
            raise RuntimeError("FFmpeg executable not found.")
        except Exception as e:
            logger.error(f"Unexpected error executing FFmpeg: {str(e)}")
            raise RuntimeError(f"Unexpected error: {str(e)}")

    def transcode_video(self, input_path, output_dir, video_id):
        """
        Transcode an input video file to 720p and 480p standard web formats,
        and extract a thumbnail at the 5-second mark using the subprocess module.
        """
        logger.info(f"Starting transcoding process for video: {video_id}")

        if not self.ffmpeg_available:
            logger.error("FFmpeg not found in system PATH. Cannot perform transcoding.")
            return False

        if not os.path.exists(input_path):
            logger.error(f"Input file not found: {input_path}")
            return False

        os.makedirs(output_dir, exist_ok=True)

        # Systematic output names using UUID
        output_720p = os.path.join(output_dir, f"{video_id}_720p.mp4")
        output_480p = os.path.join(output_dir, f"{video_id}_480p.mp4")
        thumbnail_path = os.path.join(output_dir, f"{video_id}_thumbnail.png")

        logger.info(f"Input file: {input_path}")
        logger.info(
            f"Target outputs: 720p -> {output_720p}, 480p -> {output_480p}, "
            f"thumbnail -> {thumbnail_path}"
        )

        try:
            # 1. 720p transcode: scale to 720p
            cmd_720p = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "scale=-2:720",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                output_720p
            ]
            self.execute_command(cmd_720p)

            # 2. 480p transcode: scale to 480p
            cmd_480p = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "scale=-2:480",
                "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                output_480p
            ]
            self.execute_command(cmd_480p)

            # 3. Thumbnail extraction: capture a single frame at the 5-second mark
            cmd_thumb = [
                "ffmpeg", "-y", "-ss", "00:00:05", "-i", input_path,
                "-vframes", "1",
                thumbnail_path
            ]
            self.execute_command(cmd_thumb)

        except (ValueError, RuntimeError) as e:
            logger.error(f"Transcoding failed: {str(e)}")
            return False

        # Verify that the expected assets were produced and are non-empty
        assets = [output_720p, output_480p, thumbnail_path]
        for asset in assets:
            if not os.path.exists(asset) or os.path.getsize(asset) == 0:
                logger.error(f"Transcoding verification failed. Missing or empty asset: {asset}")
                return False

        logger.info("Transcoding and thumbnail extraction completed successfully.")
        return True


# Initialize worker on startup to check for FFmpeg availability
_worker = FFmpegWorker()

def transcode_video(input_path, output_dir, video_id):
    """
    Wrapper function for backwards compatibility.
    """
    return _worker.transcode_video(input_path, output_dir, video_id)
