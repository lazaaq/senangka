import os
from services.utils import read_json, logger

# Path to products file
PRODUCTS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'products.json'))

def get_all_products():
    """
    Retrieve all products from the JSON database.
    """
    return read_json(PRODUCTS_FILE)

def get_product_by_id(product_id):
    """
    Retrieve a specific product by its ID.
    """
    products = get_all_products()
    for p in products:
        if p.get("id") == product_id:
            return p
    return None

def search_products(keyword):
    """
    Search products by name or description.
    """
    products = get_all_products()
    if not keyword:
        return products
        
    keyword = keyword.lower()
    results = []
    for p in products:
        name = p.get("name", "").lower()
        desc = p.get("description", "").lower()
        if keyword in name or keyword in desc:
            results.append(p)
    return results

def format_product_list():
    """
    Format the product catalog into a clean WhatsApp-friendly message.
    """
    products = get_all_products()
    if not products:
        return "Maaf, saat ini katalog produk kami sedang kosong."
        
    text = "🍉 *Katalog Produk Segar - Senangka* 🍉\n\n"
    for i, p in enumerate(products, 1):
        name = p.get("name", "Produk")
        price = p.get("price", 0)
        desc = p.get("description", "")
        stock = p.get("stock", 0)
        
        # Format IDR price (e.g. 15000 -> 15.000)
        price_formatted = f"Rp {price:,}".replace(",", ".")
        
        text += f"{i}. *{name}*\n"
        text += f"   💵 Harga: *{price_formatted}*\n"
        text += f"   📝 Deskripsi: {desc}\n"
        text += f"   📦 Stok: {stock} porsi\n\n"
        
    text += "Untuk melakukan pemesanan, silakan ketik langsung pesanan Anda (contoh: *Pesan 2 Smoothie Semangka Mint*)."
    return text
