# yazdirma_islemleri.py
# Etiket ve fiş formatlama gibi yazdırma ile ilgili işlemleri içerir.

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from decimal import Decimal
import datetime

# Ana konsol nesnesini alalım (arayuz_yardimcilari'ndan import etmek yerine burada da tanımlayabiliriz)
# Veya arayuz_yardimcilari'nı import edip oradaki console'u kullanabiliriz.
# Şimdilik burada tanımlayalım, bağımlılığı azaltmak için.
console = Console()


def format_shelf_label(product_data):
    """
    Verilen ürün bilgilerini raf etiketi formatında metin olarak düzenler ve konsola yazdırır.
    Args:
        product_data (dict): Ürün bilgilerini içeren sözlük. Gerekli anahtarlar:
            'name', 'barcode', 'price_before_kdv', 'selling_price',
            'previous_selling_price', 'last_updated'
    """
    if not product_data:
        console.print("[bold red]Hata: Etiket için ürün verisi bulunamadı.[/]")
        return

    # --- Etiket Verilerini Hazırlama ---
    product_name = product_data.get('name', "N/A")
    barcode = product_data.get('barcode', "N/A")
    price_excl_vat = product_data.get('price_before_kdv')
    price_incl_vat = product_data.get('selling_price')
    prev_price = product_data.get('previous_selling_price')
    last_updated = product_data.get('last_updated')

    # Fiyatları formatla
    price_excl_vat_str = f"{price_excl_vat:.2f} TL" if isinstance(
        price_excl_vat, Decimal) else "N/A"
    price_incl_vat_str = f"{price_incl_vat:.2f} TL" if isinstance(
        price_incl_vat, Decimal) else "N/A"
    prev_price_str = f"{prev_price:.2f} TL" if isinstance(
        prev_price, Decimal) else None  # Eğer önceki fiyat yoksa gösterme

    # Tarihi formatla
    last_updated_str = last_updated.strftime('%d.%m.%Y %H:%M') if isinstance(
        last_updated, datetime.datetime) else "N/A"

    # --- Etiket Metnini Oluşturma ---
    label_content = f"[bold cyan]{product_name}[/]\n\n"
    label_content += f"KDV Hariç: [yellow]{price_excl_vat_str}[/]\n"
    label_content += f"[bold]KDV Dahil: [bold green]{price_incl_vat_str}[/][/]\n"
    if prev_price_str and prev_price != price_incl_vat:  # Önceki fiyat varsa ve farklıysa göster
        label_content += f"[dim]Önceki Fiyat: [strike]{prev_price_str}[/][/]\n"
    label_content += f"\nBarkod: [dim]{barcode}[/]\n"
    label_content += f"Güncelleme: [dim]{last_updated_str}[/]"

    # --- Panelle Etiketi Gösterme ---
    console.print(Panel(Text(label_content, justify="left"),
                  title="Raf Etiketi Önizleme", border_style="blue", expand=False))

# Gelecekte buraya başka formatlama fonksiyonları eklenebilir (örn: format_grocery_label)


# === Test Amaçlı Çalıştırma ===
if __name__ == "__main__":
    # Örnek veri ile test edelim
    ornek_urun = {
        'name': "Örnek Ürün Adı Çok Uzun Olabilir Deneme",
        'barcode': "1234567890123",
        'price_before_kdv': Decimal('84.75'),
        'selling_price': Decimal('100.00'),
        'previous_selling_price': Decimal('95.50'),
        'last_updated': datetime.datetime.now()
    }
    ornek_urun_fiyat_degismemis = {
        'name': "Fiyatı Değişmeyen Ürün",
        'barcode': "9876543210987",
        'price_before_kdv': Decimal('50.00'),
        'selling_price': Decimal('60.00'),
        'previous_selling_price': Decimal('60.00'),  # Aynı fiyat
        'last_updated': datetime.datetime(2024, 4, 20, 10, 30)
    }
    ornek_urun_onceki_fiyat_yok = {
        'name': "Yeni Eklenen Ürün",
        'barcode': "1122334455667",
        'price_before_kdv': Decimal('10.00'),
        'selling_price': Decimal('12.00'),
        'previous_selling_price': None,  # Önceki fiyat yok
        'last_updated': datetime.datetime(2025, 4, 25, 9, 0)
    }

    console.print("\n--- Etiket Formatlama Testi ---")
    format_shelf_label(ornek_urun)
    print("-" * 30)
    format_shelf_label(ornek_urun_fiyat_degismemis)
    print("-" * 30)
    format_shelf_label(ornek_urun_onceki_fiyat_yok)
    print("-" * 30)
    format_shelf_label(None)  # Hata durumu testi
