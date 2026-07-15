import os
import requests
from services.utils import logger, normalize_phone

FONNTE_API_URL = "https://api.fonnte.com/send"

def send_whatsapp_message(target, message, media_url=None, filename=None, file_path=None):
    """
    Send a WhatsApp message (text or media) via Fonnte API.
    target    : The recipient's phone number.
    message   : The text content / caption of the message.
    media_url : (fallback) URL of a file for Fonnte to fetch remotely.
    filename  : Custom filename for media attachments (e.g. 'Invoice-Senangka.pdf').
    file_path : (preferred) Absolute path to a local file. When provided, the file
                is uploaded directly as binary bytes (multipart/form-data), which is
                more reliable than sharing a public URL that Fonnte must fetch.
    """
    target = normalize_phone(target)
    token = os.getenv("FONNTE_TOKEN", "")
    
    if not token or token == "PLACEHOLDER_FONNTE_TOKEN":
        logger.warning(
            f"[MOCK] Sending WhatsApp message to {target}: {message}" +
            (f" | file_path: {file_path}" if file_path else "") +
            (f" | media_url: {media_url}" if media_url else "")
        )
        return {
            "status": True,
            "message": "Mock send success (placeholder token detected)",
            "mock": True
        }
        
    headers = {"Authorization": token}
    
    payload = {
        "target": target,
        "message": message,
        "countryCode": "62"
    }

    # ── Direct binary upload (preferred for PDF invoices) ──────────────────
    if file_path and os.path.isfile(file_path):
        resolved_filename = filename or os.path.basename(file_path)
        try:
            with open(file_path, "rb") as f:
                files = {
                    "file": (resolved_filename, f, "application/pdf")
                }
                logger.info(
                    f"Uploading file directly to Fonnte for {target}: "
                    f"{file_path} as '{resolved_filename}'"
                )
                response = requests.post(
                    FONNTE_API_URL,
                    headers=headers,
                    data=payload,
                    files=files,
                    timeout=30
                )
            response.raise_for_status()
            result = response.json()
            if result.get("status"):
                logger.info(f"File successfully sent to {target} via Fonnte (binary upload)")
            else:
                logger.warning(f"Fonnte binary upload returned failure for {target}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error during direct file upload to Fonnte for {target}: {e}")
            return {"status": False, "reason": f"Binary upload failed: {str(e)}"}

    # ── URL-based send (fallback) ───────────────────────────────────────────
    if media_url:
        payload["url"] = media_url
        if filename:
            payload["filename"] = filename
            
    try:
        logger.info(f"Sending WhatsApp message to {target} via Fonnte API...")
        response = requests.post(
            FONNTE_API_URL, headers=headers, data=payload, timeout=15
        )
        
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
