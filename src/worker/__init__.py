"""Background Transcoding Worker Package for infotact project."""
import queue
import threading
import logging
from .ffmpeg_worker import transcode_video

logger = logging.getLogger(__name__)

# Shared queue for transcoding jobs
transcoding_queue = queue.Queue()

# Thread management
_workers = []
_workers_lock = threading.Lock()


def worker_loop():
    logger.info("Transcoding background worker thread started.")
    while True:
        try:
            job = transcoding_queue.get()
            if job is None:
                break
            input_path, output_dir, video_id = job
            logger.info(f"Processing transcoding job for video: {video_id}")
            try:
                transcode_video(input_path, output_dir, video_id)
            except Exception as e:
                logger.error(f"Error during async transcoding of {video_id}: {str(e)}")
            finally:
                transcoding_queue.task_done()
        except Exception as e:
            logger.error(f"Error in background worker loop: {str(e)}")


def start_workers(num_workers=1):
    """
    Start the background daemon worker threads if not already running.
    """
    with _workers_lock:
        global _workers
        # Clean up dead threads
        _workers = [w for w in _workers if w.is_alive()]
        while len(_workers) < num_workers:
            t = threading.Thread(target=worker_loop, daemon=True)
            t.start()
            _workers.append(t)
        logger.info(f"Background worker threads running: {len(_workers)}")


def queue_transcoding_job(input_path, output_dir, video_id):
    """
    Add a transcoding task to the queue and ensure worker threads are active.
    """
    start_workers()
    transcoding_queue.put((input_path, output_dir, video_id))
    logger.info(f"Queued transcoding task for video: {video_id}")
