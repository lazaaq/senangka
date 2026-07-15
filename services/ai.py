import os
import requests
from services.utils import logger

OPENROUTER_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

def generate_ai_reply(session_history, system_prompt):
    """
    Generate response from AI using OpenRouter.
    session_history: List of {"role": "user"|"assistant", "content": "..."}
    system_prompt: System instructions for the bot.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    
    # If API key is empty or placeholder, return a friendly mock response to facilitate local testing
    if not api_key or api_key == "PLACEHOLDER_OPENROUTER_API_KEY":
        last_message = session_history[-1]["content"] if session_history else ""
        logger.warning("[MOCK] Generating AI reply. OpenRouter API Key is missing or placeholder.")
        
        last_message_lower = last_message.lower()
        if "halo" in last_message_lower or "hi" in last_message_lower or "p" in last_message_lower:
            return "Halo! Selamat datang di Senangka. Ada yang bisa kami bantu hari ini? Kami menyediakan berbagai olahan semangka segar organik!"
        elif "produk" in last_message_lower or "menu" in last_message_lower or "jual" in last_message_lower:
            return "Kami menawarkan produk segar berikut:\n1. Jus Semangka Murni - Rp 15.000\n2. Semangka Potong Segar - Rp 10.000\n3. Smoothie Semangka Mint - Rp 20.000\n4. Salad Buah Semangka Spesial - Rp 25.000\n\nAda yang ingin Anda pesan?"
        elif "harga" in last_message_lower:
            return "Berikut daftar harga produk kami:\n- Jus Semangka Murni: Rp 15.000\n- Semangka Potong Segar: Rp 10.000\n- Smoothie Semangka Mint: Rp 20.000\n- Salad Buah Semangka: Rp 25.000"
        else:
            return f"Terima kasih atas pesan Anda! (Simulasi Bot: API Key OpenRouter belum dikonfigurasi. Pesan Anda: '{last_message}')"

    # Assemble messages payload: prepend the system prompt
    messages = [{"role": "system", "content": system_prompt}] + session_history
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/lazaaq/senangka", # Site URL for OpenRouter analytics
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
        
        # Check for HTTP errors
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
                logger.error(f"OpenRouter error response content: {e.response.text}")
        except Exception:
            pass
        return None
    except Exception as e:
        logger.error(f"Unexpected error calling OpenRouter API: {e}")
        return None
