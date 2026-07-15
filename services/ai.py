import os
import requests
from services.utils import logger
from services.menu import MAIN_MENU

OPENROUTER_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

def generate_ai_reply(session_history, system_prompt):
    """
    Generate response from AI using OpenRouter.
    session_history: List of {"role": "user"|"assistant", "content": "..."}
    system_prompt: System instructions for the bot.

    NOTE: AI is only called for initial greetings and free-form questions.
    All structured menu interactions are handled locally by services/menu.py.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

    # Placeholder / missing key: return mock main menu
    if not api_key or api_key == "PLACEHOLDER_OPENROUTER_API_KEY":
        logger.warning("[MOCK] OpenRouter API Key is missing. Returning MAIN_MENU as mock response.")
        return MAIN_MENU

    # Assemble messages payload
    messages = [{"role": "system", "content": system_prompt}] + session_history

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/lazaaq/senangka",
        "X-Title": "Senangka WhatsApp Chatbot",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }

    try:
        logger.info(f"Calling OpenRouter API using model: {model}...")
        response = requests.post(OPENROUTER_COMPLETIONS_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            ai_reply = result["choices"][0]["message"]["content"].strip()
            logger.info("Successfully received AI reply from OpenRouter")
            return ai_reply
        else:
            logger.error(f"OpenRouter API response missing 'choices': {result}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error calling OpenRouter API: {e}")
        try:
            if e.response is not None:
                logger.error(f"OpenRouter error response: {e.response.text}")
        except Exception:
            pass
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling OpenRouter API: {e}")
        return None
