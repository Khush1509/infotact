import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def transcode_video(input_path, output_dir, video_id):
    """
    Placeholder for Week 2: Subprocess FFmpeg Transcoding Worker.
    This function will transcode an input video file to 720p and 480p,
    and extract a thumbnail at the 5-second mark using the subprocess module.
    """
    logger.info(f"Starting transcoding process for video: {video_id}")
    
    # Check if FFmpeg is installed
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("FFmpeg not found in system PATH. Cannot perform transcoding.")
        return False

    os.makedirs(output_dir, exist_ok=True)
    
    # 720p output target path
    output_720p = os.path.join(output_dir, f"{video_id}_720p.mp4")
    # 480p output target path
    output_480p = os.path.join(output_dir, f"{video_id}_480p.mp4")
    # Thumbnail output path
    thumbnail_path = os.path.join(output_dir, f"{video_id}_thumbnail.png")

    logger.info(f"Input file: {input_path}")
    logger.info(f"Target outputs: 720p -> {output_720p}, 480p -> {output_480p}, thumbnail -> {thumbnail_path}")

    # Simulated subprocess commands that will be implemented in Week 2:
    # 1. 720p: ffmpeg -i input.mp4 -vf scale=-2:720 -c:v libx264 -crf 23 -preset fast output_720p.mp4
    # 2. 480p: ffmpeg -i input.mp4 -vf scale=-2:480 -c:v libx264 -crf 23 -preset fast output_480p.mp4
    # 3. Thumbnail: ffmpeg -ss 00:00:05 -i input.mp4 -vframes 1 thumbnail.png

    return True
