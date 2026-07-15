import os
from datetime import datetime
from services.utils import read_json, write_json, normalize_phone, logger

# Path to sessions file
SESSIONS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions.json'))
MAX_HISTORY_LENGTH = 12  # Keep last 12 messages (approx. 6 interaction turns)

def _ensure_session(sessions, phone_number):
    """Ensure a session entry exists for the phone number."""
    if phone_number not in sessions:
        sessions[phone_number] = {
            "history": [],
            "menu_state": "start",
            "order_data": {},
            "last_active": datetime.now().isoformat()
        }

def get_session(phone_number):
    """
    Retrieve session data for a given phone number.
    Returns a dict with 'history', 'menu_state', 'order_data', 'last_active'.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    _ensure_session(sessions, phone_number)
    write_json(SESSIONS_FILE, sessions)
    return sessions[phone_number]

def get_state(phone_number):
    """
    Return the current menu state and order data for the user.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    if phone_number in sessions:
        return {
            "menu_state": sessions[phone_number].get("menu_state", "start"),
            "order_data": sessions[phone_number].get("order_data", {})
        }
    return {"menu_state": "start", "order_data": {}}

def set_state(phone_number, menu_state, order_data=None):
    """
    Set the current menu state (and optionally order_data) for the user.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    _ensure_session(sessions, phone_number)
    sessions[phone_number]["menu_state"] = menu_state
    if order_data is not None:
        sessions[phone_number]["order_data"] = order_data
    sessions[phone_number]["last_active"] = datetime.now().isoformat()
    write_json(SESSIONS_FILE, sessions)
    logger.info(f"State set to '{menu_state}' for {phone_number}")

def add_message_to_session(phone_number, role, content):
    """
    Add a message to the user's session history.
    role must be 'user' or 'assistant'.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)
    _ensure_session(sessions, phone_number)

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
    Clear session history, state, and order data for a given phone number.
    """
    phone_number = normalize_phone(phone_number)
    sessions = read_json(SESSIONS_FILE)

    sessions[phone_number] = {
        "history": [],
        "menu_state": "start",
        "order_data": {},
        "last_active": datetime.now().isoformat()
    }
    write_json(SESSIONS_FILE, sessions)
    logger.info(f"Cleared session for {phone_number}")
    return True
