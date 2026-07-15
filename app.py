import os
import threading
from collections import deque
from flask import Flask, request, jsonify, render_template_string, send_file, abort
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from services.utils import logger, normalize_phone, read_json
from services.session import get_session, add_message_to_session, clear_session
from services.ai import generate_ai_reply
from services.fonnte import send_whatsapp_message
from services.prompt import get_system_prompt

app = Flask(__name__)

# Thread-safe cache to keep track of processed message IDs (deduplication)
PROCESSED_MESSAGE_IDS = deque(maxlen=1000)
processed_ids_lock = threading.Lock()

def is_duplicate_message(msg_id):
    """
    Check if a message ID was recently processed to prevent double-replies or double menu state transitions.
    """
    if not msg_id:
        return False
    with processed_ids_lock:
        if msg_id in PROCESSED_MESSAGE_IDS:
            return True
        PROCESSED_MESSAGE_IDS.append(msg_id)
        return False


# File Paths
CONFIG_FILE   = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'config.json'))
PRODUCTS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'products.json'))
SESSIONS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'sessions.json'))
INVOICES_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'invoices.json'))
INVOICES_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), 'invoices'))
os.makedirs(INVOICES_DIR, exist_ok=True)

@app.route('/')
def home():
    """
    Status dashboard page. Provides a visual status check of the chatbot,
    its configurations, database records, and active sessions.
    """
    config = read_json(CONFIG_FILE)
    products = read_json(PRODUCTS_FILE)
    sessions = read_json(SESSIONS_FILE)
    invoices = read_json(INVOICES_FILE)

    fonnte_configured = bool(os.getenv("FONNTE_TOKEN")) and os.getenv("FONNTE_TOKEN") != "PLACEHOLDER_FONNTE_TOKEN"
    openrouter_configured = bool(os.getenv("OPENROUTER_API_KEY")) and os.getenv("OPENROUTER_API_KEY") != "PLACEHOLDER_OPENROUTER_API_KEY"
    openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    app_url = os.getenv("APP_URL", "")

    # Standard modern dark/light styling dashboard
    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ config.get('bot_name', 'Senangka Bot') }} - Dashboard Status</title>
        <style>
            :root {
                --primary: #10b981;
                --primary-dark: #059669;
                --bg: #f9fafb;
                --card-bg: #ffffff;
                --text: #111827;
                --text-muted: #6b7280;
                --border: #e5e7eb;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: var(--bg);
                color: var(--text);
                margin: 0;
                padding: 40px 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .container {
                max-width: 900px;
                width: 100%;
                background: var(--card-bg);
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05), 0 4px 6px -4px rgba(0,0,0,0.05);
                border: 1px solid var(--border);
            }
            .header {
                border-bottom: 2px solid var(--border);
                padding-bottom: 20px;
                margin-bottom: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            h1 {
                color: var(--primary-dark);
                margin: 0;
                font-size: 2.2rem;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.95rem;
                font-weight: 600;
                background: #ecfdf5;
                color: var(--primary-dark);
                padding: 6px 16px;
                border-radius: 9999px;
                border: 1px solid #a7f3d0;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 35px;
            }
            .card {
                background: var(--bg);
                border: 1px solid var(--border);
                padding: 24px;
                border-radius: 12px;
                transition: transform 0.2s;
            }
            .card:hover {
                transform: translateY(-2px);
            }
            .card h3 {
                margin: 0 0 12px 0;
                color: var(--text-muted);
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            .card-value {
                font-size: 1.8rem;
                font-weight: 800;
                color: var(--text);
                margin: 0;
            }
            .status-list {
                list-style: none;
                padding: 0;
                margin: 0;
            }
            .status-list li {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 8px;
                font-weight: 500;
            }
            .icon-ok { color: #10b981; }
            .icon-warn { color: #f59e0b; }
            
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                text-align: left;
                padding: 14px 16px;
                border-bottom: 1px solid var(--border);
            }
            th {
                background-color: var(--bg);
                color: var(--text-muted);
                font-weight: 600;
                font-size: 0.85rem;
                text-transform: uppercase;
            }
            tr:hover td {
                background-color: #fcfdfd;
            }
            code {
                background: #f3f4f6;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 0.85rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🍉 {{ config.get('bot_name', 'Senangka Bot') }}</h1>
                <div class="status-indicator">
                    <span style="display:inline-block; width:8px; height:8px; background:var(--primary); border-radius:50%;"></span>
                    Online
                </div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>Koneksi Gateway WhatsApp</h3>
                    <ul class="status-list">
                        <li>
                            {% if fonnte_configured %}
                                <span class="icon-ok">✓</span> Fonnte: Terhubung
                            {% else %}
                                <span class="icon-warn">⚠</span> Fonnte: Mode Simulasi
                            {% endif %}
                        </li>
                    </ul>
                </div>
                <div class="card">
                    <h3>Koneksi AI (OpenRouter)</h3>
                    <ul class="status-list">
                        <li>
                            {% if openrouter_configured %}
                                <span class="icon-ok">✓</span> AI: Siap
                            {% else %}
                                <span class="icon-warn">⚠</span> AI: Mode Simulasi
                            {% endif %}
                        </li>
                        <li style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px;">
                            Model: {{ openrouter_model }}
                        </li>
                    </ul>
                </div>
                <div class="card">
                    <h3>Statistik Database</h3>
                    <div style="display:flex; justify-content:space-between; margin-top:5px;">
                        <div>
                            <span style="font-size:1.4rem; font-weight:700;">{{ sessions|length }}</span>
                            <div style="font-size:0.75rem; color:var(--text-muted);">Sesi Aktif</div>
                        </div>
                        <div>
                            <span style="font-size:1.4rem; font-weight:700;">{{ products|length }}</span>
                            <div style="font-size:0.75rem; color:var(--text-muted);">Menu Aktif</div>
                        </div>
                        <div>
                            <span style="font-size:1.4rem; font-weight:700;">{{ invoices|length }}</span>
                            <div style="font-size:0.75rem; color:var(--text-muted);">Total Invoice</div>
                        </div>
                    </div>
                </div>
            </div>

            <h2 style="font-size:1.4rem; margin-top:40px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">🍉 Daftar Menu Produk</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Nama Menu</th>
                        <th>Harga</th>
                        <th>Stok</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in products %}
                    <tr>
                        <td><code>{{ p.id }}</code></td>
                        <td><strong>{{ p.name }}</strong><br><small style="color: var(--text-muted);">{{ p.description }}</small></td>
                        <td>Rp {{ "{:,}".format(p.price).replace(",", ".") }}</td>
                        <td>{{ p.stock }} porsi</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>

            <h2 style="font-size:1.4rem; margin-top:40px; border-bottom: 1px solid var(--border); padding-bottom: 10px;">🧾 Riwayat Invoice Pesanan</h2>
            {% if invoices %}
            <table>
                <thead>
                    <tr>
                        <th>No. Invoice</th>
                        <th>Pelanggan</th>
                        <th>Produk</th>
                        <th>Total</th>
                        <th>Tanggal</th>
                        <th>Invoice PDF</th>
                    </tr>
                </thead>
                <tbody>
                    {% for inv_no, inv in invoices.items() | sort(reverse=true) %}
                    <tr>
                        <td><code>{{ inv_no }}</code></td>
                        <td>{{ inv.customer_name }}<br><small style="color:var(--text-muted);">{{ inv.phone }}</small></td>
                        <td>{{ inv.product_name }} x{{ inv.quantity }}</td>
                        <td><strong>Rp {{ "{:,}".format(inv.grand_total).replace(",", ".") }}</strong></td>
                        <td><small>{{ inv.created_at[:10] }}</small></td>
                        <td>
                            {% if app_url and 'YOUR_VPS_IP' not in app_url %}
                            <a href="{{ app_url }}/invoice/{{ inv.pdf_file }}" target="_blank"
                               style="color:var(--primary-dark); font-weight:600;">⬇ Unduh</a>
                            {% else %}
                            <small style="color:var(--text-muted);">Set APP_URL di .env</small>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p style="color:var(--text-muted); margin-top:12px;">Belum ada invoice yang digenerate.</p>
            {% endif %}
        </div>
    </body>
    </html>
    """
    return render_template_string(
        html_template,
        config=config,
        products=products,
        sessions=sessions,
        invoices=invoices,
        fonnte_configured=fonnte_configured,
        openrouter_configured=openrouter_configured,
        openrouter_model=openrouter_model,
        app_url=app_url
    )

@app.route('/invoice/<filename>')
def serve_invoice(filename):
    """
    Serve a generated PDF invoice file.
    Only serves .pdf files that exist in the invoices directory.
    """
    if not filename.endswith('.pdf'):
        abort(404)
    filepath = os.path.join(INVOICES_DIR, filename)
    if not os.path.isfile(filepath):
        abort(404)
    return send_file(filepath, mimetype='application/pdf', as_attachment=True,
                     download_name=filename)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Fonnte incoming message Webhook endpoint.
    Parses sender details, retrieves/updates chat sessions, 
    queries OpenRouter for AI answers, and sends WhatsApp responses.
    """
    # Fonnte occasionally sends GET requests to verify webhook endpoint status
    if request.method == 'GET':
        return jsonify({"status": True, "message": "Fonnte Webhook URL is active"}), 200

    # Retrieve request body safely (supporting both JSON and Form parameters)
    data = None
    if request.is_json:
        data = request.get_json(silent=True)
    if not data:
        data = request.form if request.form else request.values
    if not data:
        data = {}

    sender = data.get("sender")
    incoming_msg = data.get("message")
    msg_id = data.get("id")
    msg_type = data.get("type", "text")
    
    # Fallback to message type tag if message is empty (e.g. user sends image without caption)
    if not incoming_msg and msg_type and msg_type != "text":
        incoming_msg = f"[{msg_type.upper()}]"
        
    if not sender or not incoming_msg:
        logger.warning("Incoming webhook request was rejected: 'sender' or 'message' field missing.")
        return jsonify({"status": False, "error": "Missing 'sender' or 'message' parameters"}), 400
        
    # Prevent reprocessing duplicate webhook requests from gateway retries
    if msg_id and is_duplicate_message(msg_id):
        logger.info(f"Duplicate message detected (ID: {msg_id}) from {sender}. Request ignored.")
        return jsonify({"status": True, "message": "Duplicate request ignored"}), 200
        
    sender = normalize_phone(sender)
    incoming_msg = incoming_msg.strip()
    
    logger.info(f"Incoming message from {sender}: '{incoming_msg}'")
    
    # 1. Handle Webhook Reset commands
    incoming_msg_lower = incoming_msg.lower()
    if incoming_msg_lower in ["/reset", "reset", "mulai ulang", "mulai dari awal"]:
        clear_session(sender)
        from services.session import set_state
        set_state(sender, "main_menu")
        config = read_json(CONFIG_FILE)
        welcome_msg = config.get("welcome_message", "Halo! Selamat datang di Senangka. Ada yang bisa kami bantu?")
        send_whatsapp_message(sender, welcome_msg)
        return jsonify({"status": True, "message": "Conversation session cleared and welcome sent"}), 200
        
    # 2. Add incoming message to session history
    add_message_to_session(sender, "user", incoming_msg)

    # 3. Attempt instant local routing (handles ALL menu states + text collection)
    from services.menu import process_message
    from services.session import set_state
    local_reply = process_message(sender, incoming_msg)

    if local_reply is not None:
        logger.info(f"Local menu router handled message for {sender}")
        ai_reply = local_reply
    else:
        # 4. AI path — only for initial greetings / free-form questions
        session_data = get_session(sender)
        history = session_data.get("history", [])
        system_prompt = get_system_prompt()
        ai_reply = generate_ai_reply(history, system_prompt)

        # After AI responds, always set state to main_menu (AI always returns main menu)
        if ai_reply:
            set_state(sender, "main_menu")

    if not ai_reply:
        logger.error(f"Could not retrieve AI response for phone number: {sender}")
        config = read_json(CONFIG_FILE)
        error_msg = config.get("error_message", "Maaf, saat ini kami sedang mengalami gangguan koneksi AI. Silakan coba sesaat lagi.")
        send_whatsapp_message(sender, error_msg)
        return jsonify({"status": False, "error": "AI completion failure"}), 500

    # 5. Append reply to session history
    add_message_to_session(sender, "assistant", ai_reply)

    # 6. Push the WhatsApp message back using Fonnte API
    fonnte_response = send_whatsapp_message(sender, ai_reply)

    return jsonify({
        "status": True,
        "message": "Webhook payload completed successfully",
        "fonnte_response": fonnte_response
    }), 200

if __name__ == '__main__':
    port = int(os.getenv("APP_PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
