import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_and_add_ffmpeg_path():
    """
    Ensure ffmpeg is in PATH. If not, look in common WinGet locations
    and dynamically append them to the environment variables.
    """
    # 1. Quick check using 'ffmpeg -version'
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

    # 2. Append WinGet path additions
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


def transcode_video(input_path, output_dir, video_id):
    """
    Transcode an input video file to 720p and 480p standard web formats,
    and extract a thumbnail at the 5-second mark using the subprocess module.
    """
    logger.info(f"Starting transcoding process for video: {video_id}")

    if not check_and_add_ffmpeg_path():
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
        logger.info(f"Running command: {' '.join(cmd_720p)}")
        res_720p = subprocess.run(
            cmd_720p,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.debug(f"720p stdout: {res_720p.stdout}")

        # 2. 480p transcode: scale to 480p
        cmd_480p = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", "scale=-2:480",
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            output_480p
        ]
        logger.info(f"Running command: {' '.join(cmd_480p)}")
        res_480p = subprocess.run(
            cmd_480p,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.debug(f"480p stdout: {res_480p.stdout}")

        # 3. Thumbnail extraction: capture a single frame at the 5-second mark
        cmd_thumb = [
            "ffmpeg", "-y", "-ss", "00:00:05", "-i", input_path,
            "-vframes", "1",
            thumbnail_path
        ]
        logger.info(f"Running command: {' '.join(cmd_thumb)}")
        res_thumb = subprocess.run(
            cmd_thumb,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        logger.debug(f"Thumbnail stdout: {res_thumb.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed with exit code {e.returncode}")
        logger.error(f"FFmpeg stderr:\n{e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during transcoding: {str(e)}")
        return False

    # Verify that the expected assets were produced and are non-empty
    assets = [output_720p, output_480p, thumbnail_path]
    for asset in assets:
        if not os.path.exists(asset) or os.path.getsize(asset) == 0:
            logger.error(f"Transcoding verification failed. Missing or empty asset: {asset}")
            return False

    logger.info("Transcoding and thumbnail extraction completed successfully.")
    return True
