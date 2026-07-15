import os
from services.utils import logger
from services.session import get_state, set_state
from services.fonnte import send_whatsapp_message
from services.order import get_all_products

# Static message templates
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

Balas dengan *ANGKA* saja:
0. Kembali ke Menu Utama"""

HUBUNGI_ADMIN = """📞 *Hubungi Admin* 📞
Kakak bisa langsung chat Admin kami di WhatsApp *628123456789* untuk pertanyaan mendesak atau custom order.

Balas dengan *ANGKA* saja:
0. Kembali ke Menu Utama"""

INVALID_CHOICE = "Pilihan tidak valid Kak. Silakan ketik *ANGKA* yang sesuai."

def get_katalog_menu():
    """Build product catalog list dynamically from database."""
    products = get_all_products()
    text = "🍉 *Katalog Produk Senangka* 🍉\n\n"
    for i, p in enumerate(products, 1):
        price_formatted = f"Rp {p.get('price', 0):,}".replace(",", ".")
        text += f"{i}. *{p.get('name')}* - {price_formatted}\n"
        text += f"   _{p.get('description')}_\n\n"
    text += "Mohon balas dengan *ANGKA* produk yang ingin Kakak ketahui:\n0. Kembali ke Menu Utama"
    return text

def _format_price(amount):
    return f"Rp {amount:,}".replace(",", ".")

def process_message(phone_number, message_text):
    """
    Main local message router. Handles all structured menu interactions
    WITHOUT calling AI, based on explicit session state.

    Returns a reply string if the message is handled locally,
    or None to let the AI handle it (free-form questions, initial greeting).
    """
    message_text = message_text.strip()
    state_data = get_state(phone_number)
    current_state = state_data.get("menu_state", "start")
    order_data = state_data.get("order_data", {})

    # ─────────────────────────────────────────────────────────────────
    # TEXT INPUT STATES — handled locally regardless of digit/non-digit
    # ─────────────────────────────────────────────────────────────────

    if current_state == "name_input":
        # Store name and ask for address
        order_data["customer_name"] = message_text
        set_state(phone_number, "address_input", order_data)
        return f"Terima kasih Kak *{message_text}*! 😊\nSekarang, silakan ketik *Alamat Lengkap Pengiriman* Kakak (Jalan, Nomor Rumah, Kecamatan/Kota):"

    if current_state == "address_input":
        # Store address and show final confirmation
        order_data["address"] = message_text
        name = order_data.get("customer_name", "Pelanggan")
        product_name = order_data.get("product_name", "Produk")
        quantity = order_data.get("quantity", 1)
        total = order_data.get("total", 0)
        set_state(phone_number, "final_confirm", order_data)
        return f"""✅ *Konfirmasi Akhir Pesanan*
- Penerima: *{name}*
- Alamat: *{message_text}*
- Pesanan: *{product_name} x{quantity}*
- Total Bayar: *{_format_price(total)}*
- Pembayaran: *COD (Bayar di Tempat)*

Mohon balas dengan *ANGKA* saja:
1. Konfirmasi & Kirim Pesanan ke Admin ✅
0. Batalkan Pesanan ❌"""

    # ─────────────────────────────────────────────────────────────────
    # DIGIT-ONLY STATES — only process if message is a number
    # ─────────────────────────────────────────────────────────────────

    if not message_text.isdigit():
        # Non-digit, not a text-collection state → let AI handle it
        # Also reset state so AI re-shows main menu
        set_state(phone_number, "start", {})
        return None

    # ── STATE: start (brand-new or after reset) ──
    if current_state == "start":
        set_state(phone_number, "main_menu")
        return MAIN_MENU

    # ── STATE: main_menu ──
    if current_state == "main_menu":
        if message_text == "1":
            set_state(phone_number, "catalog")
            return get_katalog_menu()
        elif message_text == "2":
            set_state(phone_number, "info_ongkir")
            return INFO_ONGKIR
        elif message_text == "3":
            set_state(phone_number, "hubungi_admin")
            return HUBUNGI_ADMIN
        else:
            return INVALID_CHOICE + "\n\n" + MAIN_MENU

    # ── STATE: info_ongkir ──
    if current_state == "info_ongkir":
        if message_text == "0":
            set_state(phone_number, "main_menu")
            return MAIN_MENU
        else:
            return "Balas dengan *0* untuk kembali ke Menu Utama."

    # ── STATE: hubungi_admin ──
    if current_state == "hubungi_admin":
        if message_text == "0":
            set_state(phone_number, "main_menu")
            return MAIN_MENU
        else:
            return "Balas dengan *0* untuk kembali ke Menu Utama."

    # ── STATE: catalog ──
    if current_state == "catalog":
        if message_text == "0":
            set_state(phone_number, "main_menu")
            return MAIN_MENU
        products = get_all_products()
        idx = int(message_text) - 1
        if 0 <= idx < len(products):
            p = products[idx]
            promo_text = f"\n🎁 *Promo*: {p['promo']}" if p.get("promo") else ""
            set_state(phone_number, "detail", {"product_id": p["id"], "product_name": p["name"], "price": p["price"]})
            return f"""🛍️ *Detail Produk: {p['name']}*
💵 Harga: *{_format_price(p['price'])}*
📝 {p.get('description', '')}{promo_text}

Mohon balas dengan *ANGKA* jumlah yang ingin Kakak pesan:
1. Beli 1 pack/porsi
2. Beli 2 pack/porsi
3. Beli 3 pack/porsi (Gratis Ongkir! 🎉)
0. Kembali ke Katalog"""
        else:
            return f"Nomor produk tidak terdaftar Kak. Silakan pilih 1–{len(products)}.\n\n" + get_katalog_menu()

    # ── STATE: detail (selecting quantity) ──
    if current_state == "detail":
        if message_text == "0":
            set_state(phone_number, "catalog")
            return get_katalog_menu()
        qty_map = {"1": 1, "2": 2, "3": 3}
        if message_text in qty_map:
            qty = qty_map[message_text]
            price = order_data.get("price", 0)
            product_name = order_data.get("product_name", "Produk")
            total = price * qty
            new_order = {**order_data, "quantity": qty, "total": total}
            set_state(phone_number, "order_summary", new_order)
            return f"""📝 *Ringkasan Pesanan*
- Menu: *{product_name}*
- Jumlah: *{qty} porsi/pack*
- Total Harga: *{_format_price(total)}*

Mohon balas dengan *ANGKA*:
1. Lanjutkan Pemesanan (Isi Data Pengiriman)
0. Batal & Kembali ke Katalog"""
        else:
            return "Pilihan tidak valid Kak. Balas dengan *ANGKA* 1, 2, atau 3 (atau 0 untuk kembali)."

    # ── STATE: order_summary ──
    if current_state == "order_summary":
        if message_text == "1":
            set_state(phone_number, "name_input", order_data)
            return "Silakan ketik *Nama Lengkap* Kakak untuk keperluan pengiriman:"
        elif message_text == "0":
            set_state(phone_number, "catalog")
            return get_katalog_menu()
        else:
            return "Pilihan tidak valid Kak. Balas dengan *1* untuk lanjutkan atau *0* untuk batal."

    # ── STATE: final_confirm ──
    if current_state == "final_confirm":
        if message_text == "1":
            name = order_data.get("customer_name", "Pelanggan")
            product_name = order_data.get("product_name", "Produk")
            qty = order_data.get("quantity", 1)
            address = order_data.get("address", "-")
            total = order_data.get("total", 0)
            ongkir = 10000 if qty < 3 else 0
            grand_total = total + ongkir

            # Reset state before generating invoice
            set_state(phone_number, "start", {})

            # Generate PDF invoice
            from services.invoice import generate_invoice_pdf
            invoice_number, pdf_path = generate_invoice_pdf(phone_number, order_data)

            # Build confirmation text message
            conf_msg = f"""🎉 *Pesanan Berhasil Dikonfirmasi!* 🎉

Halo Kak *{name}*, terima kasih telah berbelanja di *Senangka*! 🍉

📋 *Ringkasan Pesanan:*
- Produk : {product_name} x{qty}
- Alamat : {address}
- Subtotal: {_format_price(total)}
- Ongkir  : {_format_price(ongkir) if ongkir > 0 else 'GRATIS (min. 3 pack)'}
- *Total  : {_format_price(grand_total)}*

💳 Pembayaran: *COD (Bayar di Tempat)*
Kurir kami akan segera menghubungi Kakak untuk konfirmasi jadwal pengiriman.

Invoice PDF telah kami kirimkan. Simpan sebagai bukti pesanan ya Kak! 😊

Ketik pesan apa saja untuk kembali ke Menu Utama."""

            # Send PDF invoice via Fonnte if generated successfully
            if invoice_number and pdf_path:
                app_url = os.getenv("APP_URL", "").rstrip("/")
                if app_url and "YOUR_VPS_IP" not in app_url:
                    pdf_url = f"{app_url}/invoice/{invoice_number}.pdf"
                    send_whatsapp_message(
                        phone_number,
                        f"📄 *Invoice #{invoice_number}*\nBerikut invoice pesanan Kakak:",
                        media_url=pdf_url,
                        filename=f"Invoice-Senangka-{invoice_number}.pdf"
                    )
                    logger.info(f"Invoice PDF sent to {phone_number}: {pdf_url}")
                else:
                    logger.warning("APP_URL not configured. PDF invoice generated but not sent via WhatsApp.")

            return conf_msg

        elif message_text == "0":
            set_state(phone_number, "main_menu", {})
            return "Pesanan dibatalkan. Kembali ke Menu Utama.\n\n" + MAIN_MENU
        else:
            return "Pilihan tidak valid Kak. Balas dengan *1* untuk konfirmasi atau *0* untuk batal."

    # ── Fallback: unknown state, reset and show main menu ──
    logger.warning(f"Unknown menu_state '{current_state}' for {phone_number}. Resetting to main_menu.")
    set_state(phone_number, "main_menu")
    return MAIN_MENU
