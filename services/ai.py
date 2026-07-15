import os
import requests
import re
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
        last_user_msg = session_history[-1]["content"].strip() if session_history else ""
        logger.warning("[MOCK] Generating AI reply. OpenRouter API Key is missing or placeholder.")
        
        # Extract previous assistant response to track state
        prev_assistant_msg = ""
        for msg in reversed(session_history[:-1]):
            if msg["role"] == "assistant":
                prev_assistant_msg = msg["content"]
                break
                
        # Definition of common menu templates
        main_menu = """🍉 *Selamat datang di Senangka!* 🍉
Kami menyediakan buah nangka kupas segar dan olahan nangka premium yang manis, tebal, dan harum.

Untuk respon lebih cepat, mohon balas dengan *ANGKA* saja ya (cukup ketik nomor pilihan Kakak):
1. Lihat Katalog Produk Nangka
2. Info Pengiriman & Ongkir
3. Hubungi Admin (Bantuan)"""

        katalog_menu = """🍉 *Katalog Produk Senangka* 🍉

1. Nangka Grade A - Rp 50.000 (Kupas tebal & ekstra manis)
2. Nangka Grade B - Rp 45.000 (Konsumsi harian keluarga)
3. Nangka Madu - Rp 60.000 (Rasa legit wangi madu)
4. Tekam Yellow Malaysia (J33) - Rp 65.000 (Tekstur renyah premium)
5. Nangka Kiloan Fresh - Rp 35.000 (Cocok untuk campuran es)
6. Nangka Kiloan Beku - Rp 35.000 (Praktis disimpan lebih lama)
7. Pie Nangka Mini - Rp 30.000 (Isi 5 pcs renyah gurih)
8. Pie Nangka Besar - Rp 85.000 (Porsi 6-8 orang)

Untuk respon lebih cepat, mohon balas dengan *ANGKA* produk yang ingin Kakak ketahui:
0. Kembali ke Menu Utama"""

        # Reset command or starting state
        if last_user_msg.lower() in ["reset", "/reset", "mulai ulang"] or not prev_assistant_msg:
            return main_menu
            
        # State Machine parsing
        if "Selamat datang di Senangka!" in prev_assistant_msg:
            # User is in Main Menu
            if last_user_msg == "1":
                return katalog_menu
            elif last_user_msg == "2":
                return """🚛 *Informasi Pengiriman & Ongkir* 🚛
- Pengiriman setiap hari pukul 09.00 - 17.00 WIB.
- Ongkir flat Rp 10.000 untuk dalam kota.
- *PROMO*: Gratis ongkir untuk pembelian minimal 3 pack!

Untuk respon lebih cepat, mohon balas dengan *ANGKA* saja:
0. Kembali ke Menu Utama"""
            elif last_user_msg == "3":
                return """📞 *Hubungi Admin* 📞
Kakak bisa langsung chat Admin kami di WhatsApp nomor *628123456789* untuk pertanyaan mendesak atau custom order.

Untuk respon lebih cepat, mohon balas dengan *ANGKA* saja:
0. Kembali ke Menu Utama"""
            else:
                return f"Pilihan tidak valid Kak. Silakan balas dengan *ANGKA* pilihan yang benar.\n\n" + main_menu
                
        elif "Katalog Produk Senangka" in prev_assistant_msg:
            # User is in Product Catalog
            if last_user_msg == "0":
                return main_menu
                
            products_map = {
                "1": ("Nangka Grade A", 50000, "Nangka kupas Grade A manis & tebal. Porsi 500g."),
                "2": ("Nangka Grade B", 45000, "Nangka kupas manis standar harian. Porsi 500g."),
                "3": ("Nangka Madu", 60000, "Nangka Madu legit wangi. Porsi 500g."),
                "4": ("Tekam Yellow Malaysia (J33)", 65000, "Varietas J33 renyah manis premium. Porsi 500g."),
                "5": ("Nangka Kiloan Fresh", 35000, "Nangka kiloan segar untuk campuran es."),
                "6": ("Nangka Kiloan Beku", 35000, "Nangka kiloan beku praktis."),
                "7": ("Pie Nangka Mini", 30000, "Pie isi 5 pcs cocok buat ngemil."),
                "8": ("Pie Nangka Besar", 85000, "Pie nangka jumbo untuk 6-8 orang.")
            }
            
            if last_user_msg in products_map:
                name, price, desc = products_map[last_user_msg]
                price_formatted = f"Rp {price:,}".replace(",", ".")
                return f"""🛍️ *Detail Produk: {name}*
💵 Harga: *{price_formatted}*
📝 Deskripsi: {desc}

Untuk respon lebih cepat, mohon balas dengan *ANGKA* jumlah yang ingin Kakak pesan:
1. Beli 1 pack/porsi
2. Beli 2 pack/porsi
3. Beli 3 pack/porsi (Diskon/Gratis Ongkir!)
0. Kembali ke Katalog"""
            else:
                return f"Nomor produk tidak terdaftar Kak. Silakan pilih nomor 1 sampai 8.\n\n" + katalog_menu
                
        elif "Detail Produk:" in prev_assistant_msg:
            # User is selecting quantity
            if last_user_msg == "0":
                return katalog_menu
                
            # Extract product name
            prod_match = re.search(r"Detail Produk:\s*(.+)", prev_assistant_msg)
            product_name = prod_match.group(1).strip() if prod_match else "Produk Nangka"
            
            qty_map = {"1": 1, "2": 2, "3": 3}
            if last_user_msg in qty_map:
                qty = qty_map[last_user_msg]
                price = 50000
                if "Nangka Grade B" in product_name: price = 45000
                elif "Nangka Madu" in product_name: price = 60000
                elif "Tekam Yellow" in product_name: price = 65000
                elif "Kiloan" in product_name: price = 35000
                elif "Pie Nangka Mini" in product_name: price = 30000
                elif "Pie Nangka Besar" in product_name: price = 85000
                
                total = price * qty
                total_formatted = f"Rp {total:,}".replace(",", ".")
                
                return f"""📝 *Ringkasan Pesanan*
- Menu: *{product_name}*
- Jumlah: *{qty} porsi/pack*
- Total Harga: *{total_formatted}*

Untuk melanjutkan pengisian data pengiriman, mohon balas dengan *ANGKA*:
1. Lanjutkan Pemesanan
0. Batal & Kembali ke Katalog"""
            else:
                return f"Pilihan jumlah tidak valid. Silakan balas dengan *ANGKA* 1, 2, atau 3 (atau 0 untuk kembali):\n\n" + prev_assistant_msg

        elif "Ringkasan Pesanan" in prev_assistant_msg:
            # User is confirming to fill delivery data
            if last_user_msg == "1":
                return "Silakan ketik *Nama Lengkap* Kakak untuk keperluan pengiriman:"
            elif last_user_msg == "0":
                return katalog_menu
            else:
                return f"Pilihan tidak valid Kak.\n\n" + prev_assistant_msg
                
        elif "keperluan pengiriman:" in prev_assistant_msg:
            # User just sent their name, now ask for address
            return f"Terima kasih Kak *{last_user_msg}*. Sekarang, silakan ketik *Alamat Lengkap Pengiriman* Kakak (Jalan, Nomor Rumah, Kecamatan/Kota):"
            
        elif "Alamat Lengkap Pengiriman" in prev_assistant_msg:
            # User just sent their address, show final confirmation
            # Retrieve name from history (2 messages back)
            name = "Pelanggan"
            for idx in range(len(session_history) - 1, -1, -1):
                if idx > 0 and "keperluan pengiriman:" in session_history[idx-1]["content"]:
                    name = session_history[idx]["content"]
                    break
                    
            return f"""✅ *Konfirmasi Akhir Pesanan*
- Penerima: *{name}*
- Alamat: *{last_user_msg}*
- Status Pembayaran: *COD (Bayar di Tempat)*

Mohon balas dengan *ANGKA* saja untuk menyelesaikan:
1. Konfirmasi & Kirim Pesanan ke Admin
0. Batalkan Pesanan"""

        elif "Konfirmasi Akhir Pesanan" in prev_assistant_msg:
            if last_user_msg == "1":
                return "🎉 *Pesanan Kakak Berhasil Terkonfirmasi!* 🎉\n\nAdmin kami akan segera menghubungi Kakak dalam beberapa menit untuk konfirmasi pengiriman. Terima kasih banyak telah berbelanja di Senangka! 🍉"
            elif last_user_msg == "0":
                return "Pesanan Kakak telah dibatalkan.\n\n" + main_menu
            else:
                return f"Pilihan tidak valid Kak.\n\n" + prev_assistant_msg
                
        # Default fallback to Main Menu
        return main_menu

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
