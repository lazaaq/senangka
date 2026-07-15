import os
import json
import logging
import fcntl
from contextlib import contextmanager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("senangka_bot")

@contextmanager
def lock_file(file_path):
    """
    Context manager to lock a file using fcntl for process-safe access.
    Creates the file and writes '{}' or '[]' depending on extension/initial state if it doesn't exist.
    """
    # Ensure directory exists
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
        
    # Check if we need to create it
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            # If it's products.json, initialize as empty list, otherwise empty dict
            if file_path.endswith("products.json"):
                f.write('[]')
            else:
                f.write('{}')
            
    f = open(file_path, 'r+')
    try:
        # Acquire an exclusive lock (blocking)
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield f
    finally:
        # Release lock and close
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()

def read_json(file_path, default_value=None):
    """
    Read JSON from file safely with locking.
    """
    if default_value is None:
        default_value = [] if file_path.endswith("products.json") else {}
        
    try:
        with lock_file(file_path) as f:
            f.seek(0)
            content = f.read().strip()
            if not content:
                return default_value
            return json.loads(content)
    except Exception as e:
        logger.error(f"Error reading JSON from {file_path}: {e}")
        return default_value

def write_json(file_path, data):
    """
    Write JSON to file safely with locking.
    """
    try:
        with lock_file(file_path) as f:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        return True
    except Exception as e:
        logger.error(f"Error writing JSON to {file_path}: {e}")
        return False

def normalize_phone(phone):
    """
    Normalize phone number to international format without + (e.g. 628123456789)
    Indonesian phone numbers:
    - 0812... -> 62812...
    - +62812... -> 62812...
    - 62812... -> 62812...
    """
    if not phone:
        return ""
        
    # Remove any non-digits
    phone = "".join(filter(str.isdigit, str(phone)))
    
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    elif phone.startswith("62"):
        pass
    else:
        # Default fallback
        if len(phone) >= 9 and len(phone) <= 13:
            phone = "62" + phone
            
    return phone
