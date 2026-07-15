import os
import re
from services.utils import read_json, logger
from services.session import get_session
from services.order import get_all_products

# Path to config file
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'config.json'))

# Static menu templates
MAIN_MENU = """🍉 *Selamat datang di Senangka!* 🍉
Buah nangka kupas segar dan olahan nangka premium yang manis, tebal, dan harum.

Untuk respon lebih cepat, mohon balas dengan *ANGKA* saja ya (cukup ketik nomor pilihan Kakak):
1. Lihat Katalog Produk Nangka
2. Info Pengiriman & Ongkir
3. Hubungi Admin (Bantuan)"""

INFO_ONGKIR = """🚛 *Informasi Pengiriman & Ongkir* 🚛
- Pengiriman setiap hari pukul 09.00 - 17.00 WIB.
- Ongkir flat Rp 10.000 untuk wilayah dalam kota.
- *PROMO*: Gratis ongkir untuk pembelian minimal 3 pack!

Untuk respon lebih cepat, mohon balas dengan *ANGKA* saja:
0. Kembali ke Menu Utama"""

HUBUNGI_ADMIN = """📞 *Hubungi Admin* 📞
Kakak bisa langsung chat Admin kami di WhatsApp nomor *628123456789* untuk pertanyaan mendesak atau custom order.

Untuk respon lebih cepat, mohon balas dengan *ANGKA* saja:
0. Kembali ke Menu Utama"""

def get_katalog_menu():
    """
    Generate product catalog list menu dynamically from database.
    """
    products = get_all_products()
    text = "🍉 *Katalog Produk Senangka* 🍉\n\n"
    for i, p in enumerate(products, 1):
        price_formatted = f"Rp {p.get('price', 0):,}".replace(",", ".")
        text += f"{i}. *{p.get('name')}* - {price_formatted}\n"
        text += f"   _{p.get('description')}_\n\n"
        
    text += "Untuk respon lebih cepat, mohon balas dengan *ANGKA* produk yang ingin Kakak ketahui:\n0. Kembali ke Menu Utama"
    return text

def process_numeric_message(phone_number, message_text):
    """
    Process input locally if it is a digit. 
    Bypasses AI call for speed and cost-saving.
    Returns the reply string if handled, or None if it needs AI handling.
    """
    message_text = message_text.strip()
    if not message_text.isdigit():
        return None
        
    session = get_session(phone_number)
    history = session.get("history", [])
    
    # Find last assistant message in history to determine menu state.
    # Exclude the very last message in history, which is the current user message.
    prev_assistant_msg = ""
    for msg in reversed(history[:-1]):
        if msg["role"] == "assistant":
            prev_assistant_msg = msg["content"]
            break
            
    # Default state if there is no previous assistant message
    if not prev_assistant_msg:
        return MAIN_MENU

    # 1. State: User is in MAIN MENU
    if "Selamat datang di Senangka!" in prev_assistant_msg:
        if message_text == "1":
            return get_katalog_menu()
        elif message_text == "2":
            return INFO_ONGKIR
        elif message_text == "3":
            return HUBUNGI_ADMIN
        else:
            return f"Pilihan tidak valid Kak. Silakan balas dengan *ANGKA* pilihan yang benar.\n\n" + MAIN_MENU

    # 2. State: User is in INFO ONGKIR or HUBUNGI ADMIN
    elif "Informasi Pengiriman & Ongkir" in prev_assistant_msg or "Hubungi Admin" in prev_assistant_msg:
        if message_text == "0":
            return MAIN_MENU
        else:
            return "Pilihan tidak valid Kak. Balas dengan *0* untuk kembali ke Menu Utama."

    # 3. State: User is in KATALOG MENU
    elif "Katalog Produk Senangka" in prev_assistant_msg:
        if message_text == "0":
            return MAIN_MENU
            
        products = get_all_products()
        idx = int(message_text) - 1
        if 0 <= idx < len(products):
            p = products[idx]
            name = p.get("name")
            price = p.get("price", 0)
            desc = p.get("description", "")
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
            return f"Nomor produk tidak terdaftar Kak. Silakan pilih nomor 1 sampai {len(products)}.\n\n" + get_katalog_menu()

    # 4. State: User is in PRODUCT DETAIL (selecting quantity)
    elif "Detail Produk:" in prev_assistant_msg:
        if message_text == "0":
            return get_katalog_menu()
            
        # Extract product name and strip markdown formatting (e.g. asterisks)
        prod_match = re.search(r"Detail Produk:\s*(.+)", prev_assistant_msg)
        product_name = prod_match.group(1).strip() if prod_match else ""
        product_name = product_name.replace("*", "").replace("_", "").strip()
        
        # Find product details to calculate price
        products = get_all_products()
        product = None
        for p in products:
            if p.get("name") == product_name:
                product = p
                break
                
        if not product:
            return "Terjadi kesalahan. Silakan balas dengan *0* untuk kembali ke Katalog."
            
        qty_map = {"1": 1, "2": 2, "3": 3}
        if message_text in qty_map:
            qty = qty_map[message_text]
            price = product.get("price", 0)
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
            return f"Pilihan jumlah tidak valid Kak. Silakan balas dengan *ANGKA* 1, 2, atau 3 (atau 0 untuk kembali):\n\n" + prev_assistant_msg

    # 5. State: User is in RINGKASAN PESANAN (confirming order)
    elif "Ringkasan Pesanan" in prev_assistant_msg:
        if message_text == "1":
            return "Silakan ketik *Nama Lengkap* Kakak untuk keperluan pengiriman:"
        elif message_text == "0":
            return get_katalog_menu()
        else:
            return f"Pilihan tidak valid Kak. Silakan balas dengan *ANGKA* 1 atau 0:\n\n" + prev_assistant_msg

    # 6. State: User is in KONFIRMASI AKHIR PESANAN (final approval)
    elif "Konfirmasi Akhir Pesanan" in prev_assistant_msg:
        if message_text == "1":
            return "🎉 *Pesanan Kakak Berhasil Terkonfirmasi!* 🎉\n\nAdmin kami akan segera menghubungi Kakak dalam beberapa menit untuk konfirmasi pengiriman. Terima kasih banyak telah berbelanja di Senangka! 🍉"
        elif message_text == "0":
            return "Pesanan Kakak telah dibatalkan.\n\n" + MAIN_MENU
        else:
            return f"Pilihan tidak valid Kak. Silakan balas dengan *ANGKA* 1 atau 0:\n\n" + prev_assistant_msg

    # Fallback to AI (None) if digit matches no specific state or occurs during text input steps (like name/address)
    return None
