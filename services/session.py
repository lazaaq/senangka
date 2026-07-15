import os
from datetime import datetime
from services.utils import read_json, write_json, normalize_phone, logger

# Path to sessions file
SESSIONS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions.json'))
MAX_HISTORY_LENGTH = 12  # Keep last 12 messages (approx. 6 interaction turns)

def get_session(phone_number):
    """
    Retrieve session history for a given phone number.
    Returns a dict with 'history' (list) and 'last_active' (str).
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    
    if phone_number not in sessions:
        sessions[phone_number] = {
            "history": [],
            "last_active": datetime.now().isoformat()
        }
        write_json(SESSIONS_FILE, sessions)
        
    return sessions[phone_number]

def add_message_to_session(phone_number, role, content):
    """
    Add a message to the user's session history.
    role must be 'user' or 'assistant'.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    
    if phone_number not in sessions:
        sessions[phone_number] = {
            "history": [],
            "last_active": datetime.now().isoformat()
        }
        
    # Append message
    sessions[phone_number]["history"].append({
        "role": role,
        "content": content
    })
    
    # Trim history if it exceeds limit
    if len(sessions[phone_number]["history"]) > MAX_HISTORY_LENGTH:
        sessions[phone_number]["history"] = sessions[phone_number]["history"][-MAX_HISTORY_LENGTH:]
        
    # Update timestamp
    sessions[phone_number]["last_active"] = datetime.now().isoformat()
    
    write_json(SESSIONS_FILE, sessions)
    logger.info(f"Added message ({role}) to session for {phone_number}. Total messages: {len(sessions[phone_number]['history'])}")
    return sessions[phone_number]

def clear_session(phone_number):
    """
    Clear session history for a given phone number.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    
    if phone_number in sessions:
        sessions[phone_number] = {
            "history": [],
            "last_active": datetime.now().isoformat()
        }
        write_json(SESSIONS_FILE, sessions)
        logger.info(f"Cleared session history for {phone_number}")
    return True
