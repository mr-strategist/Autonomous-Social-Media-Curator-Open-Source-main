import os
import time
import logging

logger = logging.getLogger(__name__)

def safe_remove_db_file(file_path: str, max_retries: int = 3, wait_time: int = 1) -> bool:
    """Safely remove a database file with retries"""
    for i in range(max_retries):
        try:
            if os.path.exists(file_path):
                time.sleep(wait_time)  # Wait before attempting deletion
                os.remove(file_path)
                logger.info(f"Successfully removed {file_path}")
                return True
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"Failed to remove {file_path} after {max_retries} attempts: {str(e)}")
                return False
            time.sleep(wait_time * 2)  # Double wait time between retries
    return False 