import os
from datetime import datetime
from services.utils import read_json, write_json, logger

INVOICES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'invoices'))
INVOICES_DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'invoices.json'))

# Ensure invoices directory exists
os.makedirs(INVOICES_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────
# Invoice Number Generator
# ─────────────────────────────────────────────────────────────────

def _next_invoice_number():
    """Generate a sequential invoice number: INV-YYYYMMDD-XXXX."""
    data = read_json(INVOICES_DATA)
    today = datetime.now().strftime("%Y%m%d")
    seq = 1
    for inv_no in data.keys():
        if inv_no.startswith(f"INV-{today}-"):
            try:
                seq = max(seq, int(inv_no.split("-")[3]) + 1)
            except (IndexError, ValueError):
                pass
    return f"INV-{today}-{seq:04d}"


# ─────────────────────────────────────────────────────────────────
# PDF Invoice Generation
# ─────────────────────────────────────────────────────────────────

def _draw_line(pdf, y=None, lw=0.3):
    """Draw a horizontal divider line."""
    if y is None:
        y = pdf.get_y()
    pdf.set_line_width(lw)
    pdf.line(15, y, 195, y)


def generate_invoice_pdf(phone_number, order_data):
    """
    Generate a PDF invoice for the confirmed order.

    Args:
        phone_number (str): Customer's WhatsApp number.
        order_data (dict): Order data from session state.

    Returns:
        tuple: (invoice_number, pdf_filepath) or (None, None) on error.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        logger.error("fpdf2 not installed. Run: pip install fpdf2")
        return None, None

    try:
        invoice_number = _next_invoice_number()
        now = datetime.now()
        date_str = now.strftime("%d %B %Y").replace(
            "January", "Januari").replace("February", "Februari").replace(
            "March", "Maret").replace("April", "April").replace(
            "May", "Mei").replace("June", "Juni").replace(
            "July", "Juli").replace("August", "Agustus").replace(
            "September", "September").replace("October", "Oktober").replace(
            "November", "November").replace("December", "Desember")
        time_str = now.strftime("%H:%M WIB")

        customer_name = order_data.get("customer_name", "Pelanggan")
        address = order_data.get("address", "-")
        product_name = order_data.get("product_name", "Produk Nangka")
        quantity = order_data.get("quantity", 1)
        unit_price = order_data.get("price", 0)
        subtotal = order_data.get("total", 0)
        ongkir = 10000 if quantity < 3 else 0
        grand_total = subtotal + ongkir

        # ── Build PDF ──────────────────────────────────────────────
        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(15, 15, 15)
        pdf.set_auto_page_break(auto=True, margin=15)

        # ── Header Banner ──
        pdf.set_fill_color(34, 139, 34)           # Forest green
        pdf.rect(0, 0, 210, 38, style='F')

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_y(8)
        pdf.cell(0, 10, "SENANGKA", align="L", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 5, "Toko Nangka Segar & Olahan Premium", align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, "WA: +62 812-3456-789  |  senangka.id", align="L", new_x="LMARGIN", new_y="NEXT")

        # "INVOICE" label on the right side of header
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_y(12)
        pdf.cell(0, 10, "INVOICE", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_y(24)
        pdf.cell(0, 5, f"No. {invoice_number}", align="R")

        # ── Reset color & move below header ──
        pdf.set_text_color(40, 40, 40)
        pdf.set_y(46)

        # ── Invoice Meta Box ──
        pdf.set_fill_color(245, 245, 245)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.set_font("Helvetica", "", 9)

        col_w = 87
        # Left column — customer info
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w, 6, "KEPADA:", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_x(15)
        pdf.set_y(pdf.get_y() + 6)
        pdf.cell(col_w, 6, f"Nama  : {customer_name}", border=0)
        pdf.set_x(15)
        pdf.set_y(pdf.get_y() + 6)
        # Wrap long address
        pdf.multi_cell(col_w, 6, f"Alamat: {address}", border=0)
        addr_end_y = pdf.get_y()
        pdf.set_x(15)
        pdf.cell(col_w, 6, f"WA    : {phone_number}", border=0)
        pdf.set_y(pdf.get_y() + 6)

        # Right column — invoice details
        detail_y = 46
        pdf.set_xy(112, detail_y)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w, 6, "DETAIL INVOICE:", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(112, detail_y + 6)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_w, 6, f"Tanggal  : {date_str}", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(112)
        pdf.cell(col_w, 6, f"Jam      : {time_str}", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(112)
        pdf.cell(col_w, 6, f"Pembayaran: COD (Bayar di Tempat)", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(112)
        pdf.cell(col_w, 6, f"Status   : Menunggu Pengiriman", border=0)

        # ── Order Table ──
        table_y = max(pdf.get_y(), addr_end_y) + 12
        pdf.set_y(table_y)

        _draw_line(pdf, lw=0.5)
        pdf.set_y(pdf.get_y() + 2)

        # Table header
        pdf.set_fill_color(34, 139, 34)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        col_no = 10
        col_item = 80
        col_qty = 20
        col_price = 32
        col_sub = 33

        pdf.cell(col_no,  8, "No",         border=0, align="C", fill=True)
        pdf.cell(col_item, 8, "Nama Produk", border=0, align="L", fill=True)
        pdf.cell(col_qty,  8, "Qty",        border=0, align="C", fill=True)
        pdf.cell(col_price, 8, "Harga Satuan", border=0, align="R", fill=True)
        pdf.cell(col_sub,  8, "Subtotal",   border=0, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")

        # Table row
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(40, 40, 40)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_fill_color(250, 250, 250)
        pdf.cell(col_no,   8, "1",                              border=0, align="C", fill=True)
        pdf.cell(col_item, 8, product_name,                     border=0, align="L", fill=True)
        pdf.cell(col_qty,  8, str(quantity),                    border=0, align="C", fill=True)
        pdf.cell(col_price, 8, f"Rp {unit_price:,}".replace(",", "."), border=0, align="R", fill=True)
        pdf.cell(col_sub,  8, f"Rp {subtotal:,}".replace(",", "."),   border=0, align="R", fill=True,
                 new_x="LMARGIN", new_y="NEXT")

        # Ongkir row (if any)
        if ongkir > 0:
            pdf.cell(col_no + col_item + col_qty, 8, "Ongkos Kirim", border=0, align="R", fill=False)
            pdf.cell(col_price, 8, "", border=0)
            pdf.cell(col_sub, 8, f"Rp {ongkir:,}".replace(",", "."), border=0, align="R",
                     new_x="LMARGIN", new_y="NEXT")

        _draw_line(pdf, lw=0.5)
        pdf.set_y(pdf.get_y() + 2)

        # ── Grand Total ──
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(34, 139, 34)
        pdf.cell(0, 8, f"TOTAL PEMBAYARAN:  Rp {grand_total:,}".replace(",", "."), align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(40, 40, 40)

        pdf.set_y(pdf.get_y() + 4)
        _draw_line(pdf, lw=0.3)
        pdf.set_y(pdf.get_y() + 6)

        # ── Payment Instructions ──
        pdf.set_fill_color(255, 253, 231)   # Light yellow
        pdf.set_draw_color(220, 200, 0)
        start_y = pdf.get_y()
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "CARA PEMBAYARAN (COD - Bayar di Tempat):", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        instructions = [
            "1. Pesanan akan dikirim oleh kurir Senangka ke alamat yang telah Kakak berikan.",
            "2. Siapkan uang tunai sejumlah TOTAL PEMBAYARAN di atas saat kurir tiba.",
            "3. Serahkan pembayaran kepada kurir dan terima produk Kakak.",
            "4. Simpan invoice ini sebagai bukti pesanan yang sah.",
        ]
        for line in instructions:
            pdf.set_x(15)
            pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")
        box_end_y = pdf.get_y() + 2
        pdf.rect(13, start_y - 2, 184, box_end_y - start_y + 4)

        # ── Footer ──
        pdf.set_y(pdf.get_y() + 10)
        _draw_line(pdf, lw=0.5)
        pdf.set_y(pdf.get_y() + 4)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 5, "Terima kasih telah berbelanja di Senangka! Produk segar kami dipilih dengan cinta.", align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, f"Invoice digenerate otomatis pada {date_str} pukul {time_str}", align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, f"No. Referensi: {invoice_number}", align="C")

        # ── Save PDF ──
        pdf_filename = f"{invoice_number}.pdf"
        pdf_path = os.path.join(INVOICES_DIR, pdf_filename)
        pdf.output(pdf_path)

        # ── Persist invoice record ──
        invoices = read_json(INVOICES_DATA)
        invoices[invoice_number] = {
            "phone": phone_number,
            "customer_name": customer_name,
            "address": address,
            "product_name": product_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
            "ongkir": ongkir,
            "grand_total": grand_total,
            "pdf_file": pdf_filename,
            "created_at": now.isoformat(),
            "status": "confirmed"
        }
        write_json(INVOICES_DATA, invoices)

        logger.info(f"Invoice {invoice_number} generated: {pdf_path}")
        return invoice_number, pdf_path

    except Exception as e:
        logger.error(f"Failed to generate invoice PDF: {e}")
        return None, None
