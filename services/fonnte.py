import os
import requests
from services.utils import logger, normalize_phone

FONNTE_API_URL = "https://api.fonnte.com/send"

def send_whatsapp_message(target, message, media_url=None, filename=None):
    """
    Send a WhatsApp message (text or media) via Fonnte API.
    target: The recipient's phone number.
    message: The text content of the message.
    media_url: Optional URL of an image, video, audio, or document file.
    filename: Optional custom filename for media attachments.
    """
    target = normalize_phone(target)
    token = os.getenv("FONNTE_TOKEN", "")
    
    if not token or token == "PLACEHOLDER_FONNTE_TOKEN":
        logger.warning(f"[MOCK] Sending WhatsApp message to {target}: {message}" + 
                       (f" with media: {media_url}" if media_url else ""))
        return {
            "status": True,
            "message": "Mock send success (placeholder token detected)",
            "mock": True
        }
        
    headers = {
        "Authorization": token
    }
    payload = {
        "target": target,
        "message": message,
        "countryCode": "62"
    }
    
    if media_url:
        payload["url"] = media_url
        if filename:
            payload["filename"] = filename
            
    try:
        logger.info(f"Sending WhatsApp message to {target} via Fonnte API...")
        response = requests.post(FONNTE_API_URL, headers=headers, data=payload, timeout=10)
        
        # Check if request succeeded
        response.raise_for_status()
        result = response.json()
        
        # Fonnte typically returns {"status": true, ...} or {"status": false, ...}
        if result.get("status"):
            logger.info(f"WhatsApp message successfully sent to {target}")
        else:
            logger.warning(f"Fonnte API returned failure status for {target}: {result}")
            
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error sending WhatsApp message via Fonnte to {target}: {e}")
        return {
            "status": False,
            "reason": f"HTTP request failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error sending WhatsApp message via Fonnte to {target}: {e}")
        return {
            "status": False,
            "reason": f"Unexpected error: {str(e)}"
        }
