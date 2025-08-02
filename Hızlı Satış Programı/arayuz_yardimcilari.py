# arayuz_yardimcilari.py
# Kullanıcı arayüzü ile ilgili yardımcı fonksiyonları içerir.
# ... (Önceki versiyon notları) ...
# v47: display_z_report fonksiyonu eklendi.
# v51: display_order_suggestion_report fonksiyonu eklendi.

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel  # Z Raporu için eklendi
from rich.text import Text  # Z Raporu için eklendi
import datetime

# === Konsol Nesnesi ===
console = Console()

# === Girdi Alma Fonksiyonları ===
# ... (Tüm get_* fonksiyonları - değişiklik yok) ...


def get_non_empty_input(prompt):
    """Kullanıcıdan boş olmayan bir metin girdisi alır."""
    while True:
        console.print(prompt, style="bold", end="")
        user_input = input().strip()
        if user_input:
            return user_input
        else:
            console.print(
                ">>> HATA: Bu alan boş bırakılamaz!", style="bold red")


def get_numeric_input(prompt):
    """Kullanıcıdan sadece rakamlardan oluşan, boş olmayan bir metin girdisi alır (Barkod için)."""
    while True:
        console.print(prompt, style="bold", end="")
        user_input = input().strip()
        if not user_input:
            console.print(
                ">>> HATA: Bu alan boş bırakılamaz.", style="bold red")
            continue
        if user_input.isdigit():
            return user_input
        else:
            console.print(
                ">>> HATA: Barkod sadece rakamlardan oluşmalıdır.", style="bold red")


def get_positive_int_input(prompt, allow_zero=False):
    """
    Kullanıcıdan pozitif bir tam sayı alır.
    """
    while True:
        try:
            console.print(prompt, style="bold", end="")
            user_input_str = input().strip()
            if not user_input_str:
                console.print(">>> HATA: Lütfen bir sayı girin.",
                              style="bold red")
                continue

            user_input_int = int(user_input_str)
            if user_input_int > 0:
                return user_input_int
            elif allow_zero and user_input_int == 0:
                return user_input_int
            else:
                error_msg = ">>> HATA: Lütfen 0 veya daha büyük bir tam sayı girin." if allow_zero else ">>> HATA: Lütfen 0'dan büyük bir tam sayı girin."
                console.print(error_msg, style="bold red")
        except ValueError:
            console.print(
                ">>> HATA: Geçersiz giriş. Lütfen sadece tam sayı girin.", style="bold red")


def get_yes_no_input(prompt):
    """Kullanıcıdan Evet/Hayır (E/H) girdisi alır."""
    while True:
        console.print(
            prompt + " [bold green](E)[/]vet / [bold red](H)[/]ayır: ", end="")
        user_input = input().strip().upper()
        if user_input == 'E':
            return True
        elif user_input == 'H':
            return False
        else:
            console.print(
                ">>> Geçersiz giriş. Lütfen sadece 'E' veya 'H' girin.", style="bold red")


def get_positive_decimal_input(prompt, allow_zero=False):
    """Kullanıcıdan pozitif bir ondalık sayı (Decimal) alır."""
    while True:
        try:
            console.print(prompt, style="bold", end="")
            user_input_str = input().strip().replace(',', '.')
            if not user_input_str:
                console.print(">>> HATA: Lütfen bir sayı girin.",
                              style="bold red")
                continue
            user_input_decimal = Decimal(user_input_str)
            if user_input_decimal > Decimal('0'):
                return user_input_decimal
            elif allow_zero and user_input_decimal == Decimal('0'):
                return user_input_decimal
            elif user_input_decimal < Decimal('0'):
                console.print(
                    ">>> HATA: Lütfen 0 veya daha büyük bir sayı girin.", style="bold red")
            elif not allow_zero and user_input_decimal == Decimal('0'):
                console.print(
                    ">>> HATA: Lütfen 0'dan büyük bir sayı girin.", style="bold red")

        except InvalidOperation:
            console.print(
                ">>> HATA: Geçersiz sayı formatı. Lütfen geçerli bir sayı girin (örn: 12.50).", style="bold red")
        except Exception as e:
            console.print(f">>> Beklenmedik hata: {e}", style="bold red")


def get_date_input(prompt):
    """
    Kullanıcıdan DD-MM-YYYY formatında tarih alır veya boş girdi (None) kabul eder.
    """
    while True:
        console.print(
            prompt + " [dim](GG-AA-YYYY, boş bırakılabilir):[/] ", style="bold", end="")
        date_str = input().strip()
        if not date_str:
            return None
        try:
            valid_date = datetime.datetime.strptime(
                date_str, '%d-%m-%Y').date()
            return valid_date
        except ValueError:
            console.print(
                ">>> HATA: Geçersiz tarih formatı. Lütfen GG-AA-YYYY formatında girin (örn: 22-04-2025) veya boş bırakın.", style="bold red")


def get_optional_decimal_input(prompt, current_value):
    """Kullanıcıdan ondalık sayı alır, boş bırakılırsa mevcut değeri döndürür."""
    while True:
        try:
            display_value = f"{current_value:.2f}" if current_value is not None else "-"
            console.print(
                f"{prompt} [{display_value}]: ", style="bold", end="")
            user_input_str = input().strip()
            if not user_input_str:
                return current_value
            new_decimal = Decimal(user_input_str.replace(',', '.'))
            if new_decimal < 0:
                console.print(">>> HATA: Değer negatif olamaz.",
                              style="bold red")
                continue
            return new_decimal
        except InvalidOperation:
            console.print(">>> HATA: Geçersiz sayı formatı.", style="bold red")
        except Exception as e:
            console.print(f">>> Beklenmedik hata: {e}", style="bold red")


def get_optional_int_input(prompt, current_value):
    """Kullanıcıdan tam sayı alır, boş bırakılırsa mevcut değeri döndürür."""
    while True:
        try:
            display_value = str(
                current_value) if current_value is not None else "-"
            if current_value == 0:
                display_value = "0"

            console.print(
                f"{prompt} [{display_value}]: ", style="bold", end="")
            user_input_str = input().strip()
            if not user_input_str:
                return current_value
            new_int = int(user_input_str)
            return new_int
        except ValueError:
            console.print(
                ">>> HATA: Geçersiz giriş. Lütfen sadece tam sayı girin.", style="bold red")
        except Exception as e:
            console.print(f">>> Beklenmedik hata: {e}", style="bold red")


def get_optional_string_input(prompt, current_value):
    """Kullanıcıdan metin alır, boş bırakılırsa mevcut değeri döndürür."""
    current_display = current_value if current_value is not None else ""
    console.print(f"{prompt} [{current_display}]: ", style="bold", end="")
    user_input = input().strip()
    return user_input if user_input else current_value


def calculate_price_with_kdv(price_before_kdv, kdv_rate):
    """KDV Hariç Fiyat ve Orandan KDV Dahil Fiyatı hesaplar."""
    try:
        price_before = Decimal(price_before_kdv)
        rate = Decimal(kdv_rate)
        if price_before < 0 or rate < 0:
            return None
        price_with = price_before * (Decimal('1') + rate / Decimal('100'))
        return price_with.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (TypeError, InvalidOperation, ValueError):
        return None


def collect_payments(sale_subtotal: Decimal, payment_methods: tuple, selected_customer_id: int | None, discount_amount: Decimal = Decimal('0.00'), promotion_discount: Decimal = Decimal('0.00')):
    """
    Kullanıcıdan, satış toplamı (indirimler düşülmüş) karşılanana kadar birden fazla ödeme alır.
    Args:
        sale_subtotal (Decimal): Sepetin indirimsiz ara toplamı.
        payment_methods (tuple): Geçerli ödeme yöntemleri.
        selected_customer_id (int | None): Seçili müşteri ID'si (Veresiye için).
        discount_amount (Decimal): Satışa uygulanan manuel/kupon indirim tutarı.
        promotion_discount (Decimal): Satışa uygulanan otomatik promosyon indirim tutarı.
    Returns:
        tuple: (payments_list_for_db, total_paid_input) veya (None, None)
    """
    payments_list_for_db = []
    total_discount = discount_amount + promotion_discount
    amount_to_pay = sale_subtotal - total_discount
    if amount_to_pay < Decimal('0.00'):
        amount_to_pay = Decimal('0.00')

    remaining_amount = amount_to_pay
    total_paid_input = Decimal('0.00')

    console.print("\n--- Ödeme Alma ---", style="bold blue")
    console.print(f"Sepet Ara Toplamı: [dim]{sale_subtotal:.2f} TL[/]")
    if discount_amount > Decimal('0.00'):
        console.print(
            f"İndirim/Kupon    : [bold magenta]-{discount_amount:.2f} TL[/]")
    if promotion_discount > Decimal('0.00'):
        console.print(
            f"Promosyon İndirimi: [bold magenta]-{promotion_discount:.2f} TL[/]")
    console.print(f"Ödenecek Tutar   : [bold yellow]{amount_to_pay:.2f} TL[/]")

    while remaining_amount > Decimal('0.00'):
        console.print(
            f"\nKalan Ödenecek: [bold yellow]{remaining_amount:.2f} TL[/]")
        console.print("Ödeme Yöntemleri:", style="bold")
        for i, method in enumerate(payment_methods, start=1):
            console.print(f"[yellow]{i}:[/] {method}")
        console.print("[yellow]0:[/] Ödemeyi İptal Et")

        method_choice = get_positive_int_input(
            "Ödeme yöntemi seçin: ", allow_zero=True)

        if method_choice == 0:
            console.print("\nÖdeme işlemi iptal edildi.", style="yellow")
            return None, None

        if not (1 <= method_choice <= len(payment_methods)):
            console.print(">>> Geçersiz seçim.", style="red")
            continue

        selected_method = payment_methods[method_choice - 1]

        if selected_method == "Veresiye" and selected_customer_id is None:
            console.print(
                ">>> HATA: Veresiye işlemi için önce satışa bir müşteri bağlamanız gerekmektedir!", style="bold red")
            console.print(
                ">>> Lütfen başka bir ödeme yöntemi seçin veya işlemi iptal edip müşteri bağlayın.", style="yellow")
            continue

        while True:
            prompt = f"{selected_method} Tutar (Kalan: {remaining_amount:.2f}): "
            amount_paid_this_method = get_positive_decimal_input(
                prompt, allow_zero=False)

            if selected_method != "Nakit" and amount_paid_this_method > remaining_amount:
                console.print(
                    f">>> HATA: {selected_method} ile kalan tutardan ({remaining_amount:.2f} TL) fazla ödeme yapılamaz.", style="red")
                continue

            if amount_paid_this_method > 0:
                break

        payments_list_for_db.append(
            {'method': selected_method, 'amount': amount_paid_this_method})
        total_paid_input += amount_paid_this_method
        remaining_amount -= amount_paid_this_method
        console.print(
            f">>> {selected_method} ile {amount_paid_this_method:.2f} TL alındı.", style="green")

        if remaining_amount <= Decimal('0.00'):
            break

    return payments_list_for_db, total_paid_input

# === Gösterim Fonksiyonları ===
# ... (display_cart, display_customer_list, display_customer_list_detailed, display_customer_balance, display_customer_details, display_customer_ledger, display_product_list, display_daily_sales_summary, display_top_products_report, display_purchase_summary, display_supplier_list, display_sale_details_for_confirmation, display_user_list, display_profit_loss_report, display_stock_report, display_category_list, display_customer_coupons, print_receipt, display_suspended_sales_list, display_expiry_report, display_z_report, display_simplified_menu fonksiyonları - değişiklik yok) ...


def display_cart(cart):
    """
    Sepet içeriğini 'rich.table' ile tablo formatında gösterir ve ara toplamı döndürür.
    """
    console.print("\n--- Sepet İçeriği ---", style="bold blue")
    if not cart:
        console.print(">>> Sepetiniz şu anda boş.", style="yellow")
        return Decimal('0.00')
    else:
        subtotal = Decimal('0.00')
        table = Table(title="Sepet", show_header=True,
                      header_style="bold magenta", border_style="dim blue")
        table.add_column("No", style="dim", width=4, justify="right")
        table.add_column("Ürün Adı", style="cyan", no_wrap=False, min_width=25)
        table.add_column("Miktar", justify="right", style="green")
        table.add_column("Birim Fiyat (TL)", justify="right", style="yellow")
        table.add_column("Toplam (TL)", justify="right", style="bold yellow")
        for i, item in enumerate(cart, start=1):
            item_total = item['price_at_sale'] * item['quantity']
            table.add_row(
                str(i), item['name'], str(item['quantity']),
                f"{item['price_at_sale']:.2f}", f"{item_total:.2f}"
            )
            subtotal += item_total
        console.print(table)
        console.print(
            f"\n{'Ara Toplam:':>55} [bold yellow]{subtotal:>12.2f} TL[/]")
        return subtotal


def display_customer_list(customer_list, title="Müşteri Listesi"):
    """
    Verilen müşteri listesini (ID, Ad, Aktiflik) tablo olarak gösterir.
    """
    if not customer_list:
        console.print(
            f">>> {title} için gösterilecek müşteri yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="blue", border_style="blue")
    table.add_column("No", style="dim", justify="right", width=4)
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Ad Soyad", style="cyan", min_width=20)
    table.add_column("Durum", justify="center")

    for i, cust in enumerate(customer_list, start=1):
        if len(cust) < 3:
            continue
        cust_id, cust_name, is_active = cust
        status = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
        table.add_row(f"{i}.", str(cust_id), cust_name, status)
    console.print(table)


def display_customer_list_detailed(customers, title="Müşteri Listesi"):
    """Verilen müşteri listesini (detaylı, puan dahil) tablo olarak gösterir."""
    if not customers:
        console.print(
            f">>> {title} için gösterilecek müşteri yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["ID", "Ad Soyad", "Telefon",
               "E-posta", "Bakiye (TL)", "Puan", "Durum"]
    table.add_column(headers[0], style="dim", justify="right")
    table.add_column(headers[1], style="cyan", min_width=20)
    table.add_column(headers[2], style="green")
    table.add_column(headers[3], style="yellow")
    table.add_column(headers[4], justify="right")
    table.add_column(headers[5], justify="right", style="bold blue")
    table.add_column(headers[6], justify="center")

    for cust in customers:
        balance = cust.get('balance', Decimal('0.00'))
        loyalty_points = cust.get('loyalty_points', 0)
        balance_style = "red" if balance > Decimal(
            '0.00') else "green" if balance < Decimal('0.00') else "dim"
        balance_str = f"[{balance_style}]{balance:.2f}[/]"
        points_str = str(loyalty_points) if loyalty_points is not None else "0"
        status = "[green]Aktif[/]" if cust.get(
            'is_active') else "[red]Pasif[/]"
        table.add_row(
            str(cust.get('customer_id', '-')), cust.get('name', '-'),
            cust.get('phone', '-') or "-", cust.get('email', '-') or "-",
            balance_str,
            points_str,
            status
        )
    console.print(table)
    console.print(f"\nToplam {len(customers)} müşteri listelendi.")


def display_customer_balance(customer_name, balance):
    """Müşterinin adını ve mevcut bakiyesini gösterir."""
    if balance is None:
        console.print(
            f">>> [yellow]Müşteri '{customer_name}' için bakiye bilgisi alınamadı.[/]")
        return

    balance_style = "bold red" if balance > Decimal('0.00') else "bold green"
    balance_text = f"{balance:.2f} TL Borç" if balance > Decimal(
        '0.00') else f"{abs(balance):.2f} TL Alacak" if balance < Decimal('0.00') else "0.00 TL (Borç Yok)"
    console.print(
        f"\n[cyan]{customer_name}[/] Mevcut Bakiye: [{balance_style}]{balance_text}[/]")


def display_customer_details(customer_data):
    """Müşterinin detaylı bilgilerini (puan dahil) gösterir."""
    if not customer_data:
        console.print(">>> Gösterilecek müşteri detayı yok.", style="yellow")
        return

    console.print("\n--- Müşteri Detayları ---", style="bold blue")
    console.print(f" ID           : {customer_data.get('customer_id', '-')}")
    console.print(f" Ad Soyad     : {customer_data.get('name', '-')}")
    console.print(f" Telefon      : {customer_data.get('phone', '-') or '-'}")
    console.print(f" E-posta      : {customer_data.get('email', '-') or '-'}")
    console.print(
        f" Adres        : {customer_data.get('address', '-') or '-'}")
    balance = customer_data.get('balance')
    if balance is not None:
        balance_style = "bold red" if balance > Decimal(
            '0.00') else "bold green"
        balance_text = f"{balance:.2f} TL Borç" if balance > Decimal(
            '0.00') else f"{abs(balance):.2f} TL Alacak" if balance < Decimal('0.00') else "0.00 TL (Borç Yok)"
        console.print(f" Bakiye       : [{balance_style}]{balance_text}[/]")
    else:
        console.print(" Bakiye       : -")
    loyalty_points = customer_data.get('loyalty_points')
    points_str = str(loyalty_points) if loyalty_points is not None else "0"
    console.print(f" Sadakat Puanı: [blue]{points_str}[/]")
    status = "[green]Aktif[/]" if customer_data.get(
        'is_active') else "[red]Pasif[/]"
    console.print(f" Durum        : {status}")


def display_customer_ledger(customer_name, ledger_entries, current_balance):
    """
    Müşterinin hesap ekstresini tablo olarak gösterir.
    """
    console.print(
        f"\n--- {customer_name} Hesap Ekstresi ---", style="bold blue")

    if not ledger_entries:
        console.print(
            ">>> Bu müşteri için hesap hareketi bulunmamaktadır.", style="yellow")
    else:
        table = Table(title=f"{customer_name} Hesap Hareketleri", show_header=True,
                      header_style="magenta", border_style="blue")
        table.add_column("Tarih", style="dim", width=19)
        table.add_column("İşlem Türü", style="cyan", width=10)
        table.add_column("Açıklama", style="white", min_width=30)
        table.add_column("Borç (TL)", style="red", justify="right")
        table.add_column("Alacak (TL)", style="green", justify="right")

        for entry in ledger_entries:
            date_str = entry['date'].strftime(
                '%d-%m-%Y %H:%M:%S') if entry['date'] else '???'
            debit_str = f"{entry['debit']:.2f}" if entry['debit'] is not None else ""
            credit_str = f"{entry['credit']:.2f}" if entry['credit'] is not None else ""
            table.add_row(
                date_str, entry['type'], entry['description'],
                debit_str, credit_str
            )
        console.print(table)

    display_customer_balance(customer_name + " (Güncel)", current_balance)


def display_product_list(products, title="Ürün Listesi"):
    """Verilen ürün listesini (sözlük listesi) tablo olarak gösterir."""
    if not products:
        console.print(
            f">>> {title} için gösterilecek ürün yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["No", "ID", "Barkod", "Ürün Adı", "Marka", "Kategori",  # Marka eklendi
               "KDV H.", "KDV%", "Satış F.", "Stok", "Min. Stok", "Durum"]
    table.add_column(headers[0], style="dim", justify="right", width=4)
    table.add_column(headers[1], style="dim", justify="right")
    table.add_column(headers[2], style="cyan")
    table.add_column(headers[3], style="green", min_width=20)
    table.add_column(headers[4], style="blue", min_width=15)  # Marka sütunu
    table.add_column(headers[5], style="magenta",
                     min_width=15)  # Kategori sütunu
    table.add_column(headers[6], style="blue", justify="right")  # KDV H.
    table.add_column(headers[7], style="blue", justify="right")  # KDV%
    table.add_column(headers[8], style="yellow", justify="right")  # Satış F.
    table.add_column(headers[9], style="blue", justify="right")  # Stok
    table.add_column(headers[10], style="dim", justify="right")  # Min Stok
    table.add_column(headers[11], justify="center")  # Durum

    for i, p_dict in enumerate(products, start=1):
        status = "[green]Aktif[/]" if p_dict.get(
            'is_active') else "[red]Pasif[/]"
        price_b_kdv = p_dict.get('price_before_kdv')
        kdv_rate = p_dict.get('kdv_rate')
        selling_price = p_dict.get('selling_price')
        stock = p_dict.get('stock')
        min_stock = p_dict.get('min_stock_level', 2)
        brand_name = p_dict.get('brand_name') or "-"  # Marka adını al
        category_name = p_dict.get('category_name') or "-"

        price_before_kdv_str = f"{price_b_kdv:.2f}" if price_b_kdv is not None else "-"
        kdv_rate_str = f"{kdv_rate:.2f}" if kdv_rate is not None else "-"
        selling_price_str = f"{selling_price:.2f}" if selling_price is not None else "-"
        stock_str = str(stock) if stock is not None else "-"
        min_stock_str = str(min_stock) if min_stock is not None else "-"

        stock_style = "blue"
        stock_warning = ""
        if stock is not None:
            if stock < 0:  # Eksi stok kontrolü
                stock_style = "bold white on red"
                stock_warning = " [bold white on red](EKSİ STOK!)[/]"
            elif stock == 0:
                stock_style = "bold red"
                stock_warning = " [bold red](STOK 0!)[/]"
            elif stock <= min_stock:
                stock_style = "bold yellow"
                stock_warning = " [bold yellow](KRİTİK!)[/]"

        stock_display = f"[{stock_style}]{stock_str}[/]{stock_warning}"

        table.add_row(
            f"{i}.", str(p_dict.get('product_id', '-')),
            p_dict.get('barcode', '-') or "-", p_dict.get('name', '-'),
            brand_name,  # Marka adını ekle
            category_name,
            price_before_kdv_str, kdv_rate_str, selling_price_str,
            stock_display,
            min_stock_str, status
        )
    console.print(table)
    console.print(f"\nToplam {len(products)} ürün listelendi.")


def display_daily_sales_summary(summary_data, start_date=None, end_date=None):
    """
    Günlük satış özetini tablo olarak gösterir.
    """
    date_range_str = "Tüm Zamanlar"
    if start_date and end_date:
        date_range_str = f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}"
    elif start_date:
        date_range_str = f"{start_date.strftime('%d-%m-%Y')} Sonrası"
    elif end_date:
        date_range_str = f"{end_date.strftime('%d-%m-%Y')} Öncesi"

    console.print(
        f"\n--- Günlük Satış Özeti ({date_range_str}) ---", style="bold blue")

    if not summary_data:
        console.print(
            f">>> Belirtilen kriterlerde ({date_range_str}) satış bulunmamaktadır.", style="yellow")
        return

    table = Table(title=f"Günlük Satış Özeti ({date_range_str})", show_header=True,
                  header_style="magenta", border_style="blue")
    table.add_column("Tarih", style="cyan", width=12)
    table.add_column("Toplam İşlem", style="green", justify="right")
    table.add_column("Günlük Toplam Tutar (TL)",
                     style="bold yellow", justify="right")

    grand_total = Decimal('0.00')
    grand_count = 0

    for row in summary_data:
        sale_day, count, daily_total = row
        day_str = sale_day.strftime(
            '%d-%m-%Y') if isinstance(sale_day, datetime.date) else str(sale_day)
        count_str = str(count) if count is not None else "0"
        total_str = f"{daily_total:.2f}" if daily_total is not None else "0.00"
        table.add_row(day_str, count_str, total_str)
        if daily_total is not None:
            grand_total += daily_total
        if count is not None:
            grand_count += count

    console.print(table)
    console.print(f"\n[bold]Rapor Genel Toplam İşlem: {grand_count}[/]")
    console.print(f"[bold]Rapor Genel Toplam Ciro : {grand_total:.2f} TL[/]")


def display_top_products_report(report_data, report_type="quantity", limit=10, start_date=None, end_date=None):
    """
    En çok satan veya en çok ciro yapan ürünler raporunu tablo olarak gösterir.
    """
    if report_type == "quantity":
        title_suffix = "En Çok Satan Ürünler (Adet)"
        last_column_header = "Toplam Satış Adedi"
        value_style = "bold green"
    elif report_type == "value":
        title_suffix = "En Çok Ciro Yapan Ürünler"
        last_column_header = "Toplam Ciro (TL)"
        value_style = "bold yellow"
    else:
        console.print(">>> HATA: Geçersiz rapor tipi.", style="red")
        return

    date_range_str = "Tüm Zamanlar"
    if start_date and end_date:
        date_range_str = f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}"
    elif start_date:
        date_range_str = f"{start_date.strftime('%d-%m-%Y')} Sonrası"
    elif end_date:
        date_range_str = f"{end_date.strftime('%d-%m-%Y')} Öncesi"

    main_title = f"{title_suffix} ({date_range_str})"
    console.print(f"\n--- {main_title} ---", style="bold blue")

    if not report_data:
        console.print(
            f">>> Belirtilen kriterlere uygun satış kaydı veya ürün bulunamadı.", style="yellow")
        return

    table = Table(title=f"İlk {len(report_data)} Ürün", show_header=True,
                  header_style="magenta", border_style="blue")
    table.add_column("Sıra", style="dim", justify="right")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Barkod", style="cyan")
    table.add_column("Ürün Adı", style="green", min_width=25)
    table.add_column(last_column_header, style=value_style, justify="right")

    for i, prod_data in enumerate(report_data, start=1):
        if len(prod_data) < 4:
            continue
        prod_id, barcode, name, value = prod_data
        value_str = f"{value:.2f}" if report_type == "value" and value is not None else str(
            value) if value is not None else "-"
        table.add_row(f"{i}.", str(prod_id), barcode or "-", name, value_str)

    console.print(table)


def display_purchase_summary(items_list):
    """Alış listesindeki ürünleri özet olarak tablo ile gösterir."""
    if not items_list:
        console.print(">>> Alış listesi boş.", style="yellow")
        return

    console.print("Alınan Ürünler:")
    table = Table(show_header=True, header_style="blue",
                  border_style="dim blue")
    table.add_column("Barkod", style="cyan")
    table.add_column("Ürün Adı", style="green")
    table.add_column("Miktar", justify="right")
    table.add_column("Maliyet/Birim (TL)", justify="right", style="yellow")
    table.add_column("Toplam Maliyet (TL)",
                     justify="right", style="bold yellow")

    total_cost = Decimal('0.00')
    for item in items_list:
        cost_display = f"{item['cost_price']:.2f}" if item['cost_price'] is not None else "-"
        item_total_cost = Decimal('0.00')
        if item['cost_price'] is not None:
            try:
                item_total_cost = item['quantity'] * item['cost_price']
                total_cost += item_total_cost
            except:
                item_total_cost = Decimal('0.00')
        item_total_cost_display = f"{item_total_cost:.2f}" if item[
            'cost_price'] is not None else "-"
        table.add_row(
            item.get('barcode', '-'), item['name'], str(item['quantity']),
            cost_display, item_total_cost_display
        )
    console.print(table)
    console.print(f"\n[bold]Alış Toplam Maliyeti: {total_cost:.2f} TL[/]")


def display_supplier_list(suppliers, title="Tedarikçi Listesi"):
    """Verilen tedarikçi listesini tablo olarak gösterir."""
    if not suppliers:
        console.print(
            f">>> {title} için gösterilecek tedarikçi yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["No", "ID", "Tedarikçi Adı",
               "İlgili Kişi", "Telefon", "E-posta", "Durum"]
    table.add_column(headers[0], style="dim", justify="right", width=4)
    table.add_column(headers[1], style="dim", justify="right")
    table.add_column(headers[2], style="cyan", min_width=20)
    table.add_column(headers[3], style="white")
    table.add_column(headers[4], style="green")
    table.add_column(headers[5], style="yellow")
    table.add_column(headers[6], justify="center")

    for i, s in enumerate(suppliers, start=1):
        if isinstance(s, dict):
            supplier_id = s.get('supplier_id', '-')
            name = s.get('name', '-')
            contact = s.get('contact_person', '-') or "-"
            phone = s.get('phone', '-') or "-"
            email = s.get('email', '-') or "-"
            is_active = s.get('is_active', False)
        elif isinstance(s, tuple) and len(s) >= 6:
            supplier_id = s[0]
            name = s[1]
            contact = s[2] or "-"
            phone = s[3] or "-"
            email = s[4] or "-"
            is_active = s[5]
        else:
            continue

        status = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
        table.add_row(f"{i}.", str(supplier_id), name,
                      contact, phone, email, status)

    console.print(table)
    console.print(f"\nToplam {len(suppliers)} tedarikçi listelendi.")


def display_sale_details_for_confirmation(sale_details):
    """İade onayı için satış detaylarını gösterir."""
    if not sale_details or not sale_details.get('header') or not sale_details.get('items'):
        console.print(">>> Gösterilecek satış detayı yok.", style="yellow")
        return

    header = sale_details['header']
    items = sale_details['items']
    sale_id = header.get('sale_id')
    customer_id = header.get('customer_id')
    total_amount = header.get('total_amount')
    status = header.get('status')
    discount = header.get('discount_amount', Decimal('0.00'))
    promo_discount = header.get(
        'promotion_discount', Decimal('0.00'))  # Promosyon indirimi
    coupon_id = header.get('applied_customer_coupon_id')
    promo_id = header.get('applied_promotion_id')  # Promosyon ID

    console.print(
        f"\n--- İade Edilecek Satış Detayları (ID: {sale_id}) ---", style="bold yellow")
    console.print(f"Müşteri ID: {customer_id if customer_id else 'Yok'}")
    console.print(f"Toplam Tutar (İndirimli): {total_amount:.2f} TL")
    if discount > Decimal('0.00'):
        console.print(f"Uygulanan İndirim/Kupon: {discount:.2f} TL")
    if promo_discount > Decimal('0.00'):
        console.print(
            f"Uygulanan Promosyon İnd.: {promo_discount:.2f} TL (ID: {promo_id if promo_id else '?'})")
    if coupon_id:
        console.print(f"Kullanılan Kupon ID: {coupon_id}")
    console.print(f"Durum: {status}")

    if items:
        table = Table(title="İade Edilecek Ürünler",
                      show_header=True, header_style="blue")
        table.add_column("Ürün ID", style="dim")
        table.add_column("Ürün Adı", style="cyan")
        table.add_column("Miktar", justify="right")
        table.add_column("Birim Fiyat (TL)", justify="right")
        for item in items:
            pid, name, qty, price = item
            table.add_row(str(pid), name, str(qty), f"{price:.2f}")
        console.print(table)
    else:
        console.print(">>> Bu satışa ait ürün bulunamadı.", style="yellow")


def display_user_list(users, title="Kullanıcı Listesi"):
    """Verilen kullanıcı listesini tablo olarak gösterir."""
    if not users:
        console.print(
            f">>> {title} için gösterilecek kullanıcı yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["ID", "Kullanıcı Adı", "Ad Soyad", "Rol", "Durum"]
    table.add_column(headers[0], style="dim", justify="right")
    table.add_column(headers[1], style="cyan", min_width=15)
    table.add_column(headers[2], style="green", min_width=20)
    table.add_column(headers[3], style="blue")
    table.add_column(headers[4], justify="center")

    for user in users:
        status = "[green]Aktif[/]" if user.get(
            'is_active') else "[red]Pasif[/]"
        table.add_row(
            str(user.get('user_id', '-')), user.get('username', '-'),
            user.get('full_name', '-') or "-", user.get('role', '-'), status
        )
    console.print(table)
    console.print(f"\nToplam {len(users)} kullanıcı listelendi.")


def display_profit_loss_report(report_data, start_date=None, end_date=None):
    """
    Kâr/Zarar raporunu tablo olarak gösterir.
    """
    date_range_str = "Tüm Zamanlar"
    if start_date and end_date:
        date_range_str = f"{start_date.strftime('%d-%m-%Y')} - {end_date.strftime('%d-%m-%Y')}"
    elif start_date:
        date_range_str = f"{start_date.strftime('%d-%m-%Y')} Sonrası"
    elif end_date:
        date_range_str = f"{end_date.strftime('%d-%m-%Y')} Öncesi"

    console.print(
        f"\n--- Kâr/Zarar Raporu ({date_range_str}) ---", style="bold blue")
    console.print(
        "[dim](Maliyetler, ürünlerin son alış fiyatlarına göre tahmin edilmiştir)[/]")

    if not report_data:
        console.print(
            f">>> Belirtilen kriterlerde ({date_range_str}) kâr/zarar hesaplanacak satış bulunamadı.", style="yellow")
        return

    table = Table(title=f"Ürün Bazlı Tahmini Kâr/Zarar ({date_range_str})", show_header=True,
                  header_style="magenta", border_style="blue")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Barkod", style="cyan")
    table.add_column("Ürün Adı", style="green", min_width=25)
    table.add_column("Satış Adedi", style="blue", justify="right")
    table.add_column("Toplam Ciro (TL)", style="yellow", justify="right")
    table.add_column("Tahmini Maliyet (TL)", style="red", justify="right")
    table.add_column("Tahmini Kâr (TL)", style="bold green", justify="right")

    grand_total_revenue = Decimal('0.00')
    grand_total_cost = Decimal('0.00')
    grand_total_profit = Decimal('0.00')

    for row_dict in report_data:
        revenue = row_dict.get('total_revenue', Decimal('0.00'))
        cost = row_dict.get('total_estimated_cost', Decimal('0.00'))
        profit = row_dict.get('estimated_profit', Decimal('0.00'))
        profit_style = "bold green" if profit > 0 else "bold red" if profit < 0 else "dim"
        table.add_row(
            str(row_dict.get('product_id', '-')
                ), row_dict.get('barcode', '-') or "-",
            row_dict.get('name', '-'), str(row_dict.get('total_quantity', 0)),
            f"{revenue:.2f}", f"{cost:.2f}", f"[{profit_style}]{profit:.2f}[/]"
        )
        grand_total_revenue += revenue
        grand_total_cost += cost
        grand_total_profit += profit

    console.print(table)
    console.print("-" * 80, style="dim")
    console.print(
        f"[bold]Rapor Genel Toplam Ciro    : {grand_total_revenue:.2f} TL[/]")
    console.print(
        f"[bold]Rapor Genel Toplam Maliyet : {grand_total_cost:.2f} TL[/]")
    grand_profit_style = "bold green" if grand_total_profit > 0 else "bold red" if grand_total_profit < 0 else "dim"
    console.print(
        f"[bold]Rapor Genel Tahmini Kâr    : [{grand_profit_style}]{grand_total_profit:.2f} TL[/]")


def display_stock_report(stock_data, threshold=None, include_inactive=False, only_critical=False):
    """
    Stok raporunu tablo olarak gösterir (marka adı dahil).
    """
    title = "Stok Raporu"
    if only_critical:
        title = "Kritik Stok Raporu (Stoğu Min. Seviye Altında Olanlar)"
    else:
        if threshold is not None:
            title += f" (Stok <= {threshold})"
        if include_inactive:
            title += " (Pasifler Dahil)"
        else:
            title += " (Sadece Aktifler)"

    console.print(f"\n--- {title} ---", style="bold blue")

    if not stock_data:
        console.print(
            ">>> Rapor kriterlerine uygun ürün bulunamadı.", style="yellow")
        return

    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Barkod", style="cyan")
    table.add_column("Ürün Adı", style="green", min_width=30)
    table.add_column("Marka", style="blue", min_width=15)  # Yeni sütun
    table.add_column("Mevcut Stok", style="bold blue", justify="right")
    table.add_column("Min. Stok", style="dim", justify="right")
    table.add_column("Durum", justify="center")

    for row in stock_data:
        prod_id = row.get('product_id')
        barcode = row.get('barcode')
        name = row.get('name')
        brand_name = row.get('brand_name') or "-"  # Marka adını al
        stock = row.get('stock')
        min_stock = row.get('min_stock_level', 2)
        is_active = row.get('is_active')

        stock_str = str(stock) if stock is not None else "-"
        min_stock_str = str(min_stock) if min_stock is not None else "-"
        status_str = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"

        stock_style = "blue"
        row_style = None
        if stock is not None:
            if stock < 0:  # Eksi stok kontrolü
                stock_style = "bold white on red"
                row_style = "white on red"  # Tüm satırı vurgula
            elif stock == 0:
                stock_style = "bold red"
                row_style = "red"
            elif stock <= min_stock:
                stock_style = "bold yellow"
                row_style = "yellow"
            elif not only_critical and threshold is not None and stock <= threshold:
                stock_style = "bold magenta"

        stock_display = f"[{stock_style}]{stock_str}[/]"

        table.add_row(
            str(prod_id), barcode or "-", name, brand_name,  # Marka adını ekle
            stock_display, min_stock_str, status_str,
            style=row_style
        )

    console.print(table)
    console.print(f"\nToplam {len(stock_data)} ürün listelendi.")


def display_category_list(categories, title="Kategori Listesi"):
    """Verilen kategori listesini tablo olarak gösterir."""
    if not categories:
        console.print(
            f">>> {title} için gösterilecek kategori yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["No", "ID", "Kategori Adı", "Açıklama", "Durum"]
    table.add_column(headers[0], style="dim", justify="right", width=4)
    table.add_column(headers[1], style="dim", justify="right")
    table.add_column(headers[2], style="cyan", min_width=20)
    table.add_column(headers[3], style="white", min_width=30)
    table.add_column(headers[4], justify="center")

    for i, cat in enumerate(categories, start=1):
        status = "[green]Aktif[/]" if cat.get('is_active') else "[red]Pasif[/]"
        table.add_row(
            f"{i}.",
            str(cat.get('category_id', '-')),
            cat.get('name', '-'),
            cat.get('description', '-') or "-",
            status
        )
    console.print(table)
    console.print(f"\nToplam {len(categories)} kategori listelendi.")


def display_customer_coupons(coupons, customer_name):
    """Verilen müşteri kupon listesini tablo olarak gösterir."""
    title = f"{customer_name} Kullanılabilir Kuponları"
    console.print(f"\n--- {title} ---", style="bold blue")

    if not coupons:
        return

    table = Table(title=title, show_header=True,
                  header_style="cyan", border_style="blue")
    headers = ["No", "Kupon ID", "Kupon Kodu", "Açıklama",
               "İndirim", "Min. Harcama", "Son Geçerlilik"]
    table.add_column(headers[0], style="dim", justify="right", width=4)
    table.add_column(headers[1], style="dim", justify="right")
    table.add_column(headers[2], style="bold magenta")
    table.add_column(headers[3], style="white", min_width=25)
    table.add_column(headers[4], style="bold green", justify="right")
    table.add_column(headers[5], style="yellow", justify="right")
    table.add_column(headers[6], style="dim", justify="center")

    for i, coupon in enumerate(coupons, start=1):
        discount_str = ""
        discount_type = coupon.get('discount_type')
        discount_value = coupon.get('discount_value')
        if discount_type == 'percentage':
            discount_str = f"%{discount_value:.0f}"
        elif discount_type == 'fixed_amount':
            discount_str = f"{discount_value:.2f} TL"

        min_purchase_str = f"{coupon.get('min_purchase_amount', 0):.2f} TL"
        expiry_date_str = coupon.get('expiry_date').strftime(
            '%d-%m-%Y') if coupon.get('expiry_date') else "Süresiz"

        table.add_row(
            f"{i}.",
            str(coupon.get('customer_coupon_id', '-')),
            coupon.get('coupon_code', '-'),
            coupon.get('description', '-') or "-",
            discount_str,
            min_purchase_str,
            expiry_date_str
        )
    console.print(table)
    console.print(
        f"\nToplam {len(coupons)} adet kullanılabilir kupon listelendi.")


def print_receipt(cart, sale_subtotal, payments_list, total_paid, change_due, store_name="MAĞAZA", customer_name=None, discount_amount=Decimal('0.00'), coupon_code=None, promotion_discount=Decimal('0.00'), promotion_name=None):
    """
    Basit bir satış fişini ekrana yazdırır (indirim ve promosyon bilgisi dahil).
    Args:
        sale_subtotal (Decimal): Sepetin indirimsiz ara toplamı.
        discount_amount (Decimal): Uygulanan manuel/kupon indirim tutarı.
        coupon_code (str | None): Kullanılan kuponun kodu.
        promotion_discount (Decimal): Uygulanan otomatik promosyon indirim tutarı (TL karşılığı).
        promotion_name (str | None): Uygulanan son promosyonun adı (veya genel bir metin).
    """
    receipt_width = 40
    console.print("\n" + "=" * receipt_width, style="dim")
    if store_name:
        console.print(f"{store_name:^{receipt_width}}", style="bold cyan")
    console.print(f"{'*** SATIŞ FİŞİ ***':^{receipt_width}}",
                  style="bold white on blue")
    console.print(
        f" Tarih: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    if customer_name:
        console.print(f" Müşteri: {customer_name}")
    console.print("-" * receipt_width, style="dim")

    if cart:
        console.print(" Ürünler:")
        table = Table(show_header=True, header_style="bold blue",
                      show_lines=False, padding=(0, 1), box=None, width=receipt_width-2)
        table.add_column("Ad", style="cyan", no_wrap=True, ratio=5)
        table.add_column("Mx Fyt", justify="right", style="dim", ratio=3)
        table.add_column("Tutar", justify="right", style="bold", ratio=2)
        for item in cart:
            item_total = item['price_at_sale'] * item['quantity']
            mx_fyt = f"{item['quantity']}x{item['price_at_sale']:.2f}"
            table.add_row(item['name'], mx_fyt, f"{item_total:.2f}")
        console.print(table)
        console.print("-" * receipt_width, style="dim")
        console.print(
            f"{'ARA TOPLAM:':<{receipt_width-18}} [bold]{sale_subtotal:>14.2f} TL[/]")

    if discount_amount > Decimal('0.00'):
        coupon_text = f" ({coupon_code})" if coupon_code else ""
        console.print(
            f"{'İNDİRİM'+coupon_text+':':<{receipt_width-18}} [bold magenta]-{discount_amount:>13.2f} TL[/]")

    if promotion_discount > Decimal('0.00'):
        promo_text = " (Promosyon)"  # Genel bir ifade
        console.print(
            f"{'PROMOSYON'+promo_text+':':<{receipt_width-18}} [bold magenta]-{promotion_discount:>13.2f} TL[/]")

    if discount_amount > Decimal('0.00') or promotion_discount > Decimal('0.00'):
        console.print("-" * receipt_width, style="dim")

    final_total = sale_subtotal - discount_amount - promotion_discount
    console.print(
        f"{'GENEL TOPLAM:':<{receipt_width-18}} [bold yellow]{final_total:>14.2f} TL[/]")
    console.print("-" * receipt_width, style="dim")

    if payments_list:
        console.print(" Ödemeler:")
        for payment in payments_list:
            console.print(
                f"  [green]{payment['method']:<15}:[/] {payment['amount']:>{receipt_width-20}.2f} TL")
        console.print("-" * receipt_width, style="dim")

    console.print(
        f"{'TOPLAM ÖDENEN:':<{receipt_width-18}} [bold]{total_paid:>14.2f} TL[/]")
    if change_due > Decimal('0.00'):
        console.print(
            f"{'PARA ÜSTÜ:':<{receipt_width-18}} [bold green]{change_due:>14.2f} TL[/]")

    console.print("=" * receipt_width, style="dim")
    console.print(f"{'Teşekkür Ederiz!':^{receipt_width}}", style="italic")
    console.print("=" * receipt_width + "\n", style="dim")


def display_suspended_sales_list(suspended_sales):
    """Askıdaki satışları (ID, ürün sayısı, ilk ürün) tablo olarak gösterir."""
    console.print("\n--- Askıdaki Satışlar ---", style="bold blue")
    if not suspended_sales:
        console.print(
            ">>> Askıda bekleyen satış bulunmamaktadır.", style="yellow")
        return False
    table = Table(show_header=True, header_style="magenta",
                  border_style="blue")
    table.add_column("Askı ID", style="cyan", justify="right")
    table.add_column("Ürün Sayısı", style="green", justify="right")
    table.add_column("İlk Ürün", style="white")
    table.add_column("Toplam Tutar", style="yellow", justify="right")
    for sale_id, cart_items in suspended_sales.items():
        item_count = len(cart_items)
        first_item_name = cart_items[0]['name'] if item_count > 0 else "-"
        total_amount = sum(item['price_at_sale'] * item['quantity']
                           for item in cart_items)
        table.add_row(str(sale_id), str(item_count),
                      first_item_name, f"{total_amount:.2f} TL")
    console.print(table)
    return True


def display_expiry_report(report_data, days_threshold):
    """SKT'si yaklaşan veya geçmiş ürünleri tablo olarak gösterir."""
    title = f"SKT Raporu (Bugün veya Sonraki {days_threshold} Gün İçinde Sona Erenler)"
    console.print(f"\n--- {title} ---", style="bold red")

    if not report_data:
        console.print(
            f">>> Belirtilen kriterlere uygun SKT kaydı bulunamadı.", style="yellow")
        return

    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="red")
    headers = ["Alış ID", "Ürün ID", "Ürün Adı",
               "Marka", "Miktar", "SKT", "Kalan Gün"]
    table.add_column(headers[0], style="dim", justify="right")
    table.add_column(headers[1], style="dim", justify="right")
    table.add_column(headers[2], style="cyan", min_width=25)
    table.add_column(headers[3], style="blue", min_width=15)
    table.add_column(headers[4], style="green", justify="right")
    table.add_column(headers[5], style="bold red", justify="center")
    table.add_column(headers[6], style="bold yellow", justify="right")

    today = datetime.date.today()

    for item in report_data:
        expiry_date = item.get('expiry_date')
        if isinstance(expiry_date, datetime.datetime):
            expiry_date = expiry_date.date()

        remaining_days = (expiry_date - today).days if expiry_date else None
        expiry_date_str = expiry_date.strftime(
            '%d-%m-%Y') if expiry_date else "Belirsiz"
        remaining_days_str = str(
            remaining_days) if remaining_days is not None else "-"
        row_style = None
        if remaining_days is not None:
            if remaining_days < 0:
                remaining_days_str = f"[bold white on red]GEÇMİŞ ({abs(remaining_days)} gün)[/]"
                row_style = "white on red"
            elif remaining_days == 0:
                remaining_days_str = "[bold yellow]BUGÜN![/]"
                row_style = "yellow"

        table.add_row(
            str(item.get('purchase_id', '-')),
            str(item.get('product_id', '-')),
            item.get('product_name', '-'),
            item.get('brand_name', '-') or "-",
            str(item.get('quantity', '-')),
            expiry_date_str,
            remaining_days_str,
            style=row_style
        )

    console.print(table)
    console.print(f"\nToplam {len(report_data)} adet SKT kaydı listelendi.")


def display_z_report(report_data):
    """Hesaplanan Z Raporu verilerini formatlı bir şekilde gösterir."""
    if not report_data:
        console.print("[bold red]HATA: Z Raporu verileri alınamadı.[/]")
        return

    # Başlık ve Genel Bilgiler
    title = Text(f"Z RAPORU - Vardiya ID: {report_data.get('shift_id', '?')}",
                 style="bold white on blue", justify="center")
    start_time_str = report_data.get('start_time', '?').strftime(
        '%d-%m-%Y %H:%M:%S') if isinstance(report_data.get('start_time'), datetime.datetime) else '?'
    end_time_str = report_data.get('end_time', '?').strftime(
        '%d-%m-%Y %H:%M:%S') if isinstance(report_data.get('end_time'), datetime.datetime) else '?'
    # Kullanıcı bilgilerini de ekleyelim (vardiya_islemleri'nde report_data'ya eklenmeli)
    user_info = f"Kullanıcı: {report_data.get('username', '?')} ({report_data.get('full_name', '?')})"
    date_info = f"Başlangıç: {start_time_str} | Bitiş: {end_time_str}"

    console.print(Panel(Text(user_info + "\n" + date_info, justify="center"),
                  title=title, border_style="blue", expand=False))

    # Satış Özeti Tablosu
    sales_table = Table(title="Satış Özeti", show_header=False,
                        border_style="dim blue", box=None, padding=(0, 1), expand=True)
    sales_table.add_column("Kalem", style="cyan", width=30)
    sales_table.add_column("Tutar (TL)", style="yellow", justify="right")

    sales_table.add_row(
        "Nakit Satışlar", f"{report_data.get('cash_sales', 0):.2f}")
    sales_table.add_row("Kredi Kartı Satışları",
                        f"{report_data.get('card_sales', 0):.2f}")
    sales_table.add_row("Veresiye Satışlar",
                        f"{report_data.get('veresiye_sales', 0):.2f}")
    sales_table.add_section()
    sales_table.add_row("[bold]Toplam Satış (İndirimli)[/]",
                        f"[bold]{report_data.get('total_sales', 0):.2f}[/]")
    sales_table.add_row("İndirim/Kupon Toplamı",
                        f"{report_data.get('total_discount', 0):.2f}")
    sales_table.add_row("Promosyon İndirimi Toplamı",
                        f"{report_data.get('total_promotion_discount', 0):.2f}")

    # Müşteri Ödemeleri Tablosu
    payments_table = Table(title="Alınan Müşteri Ödemeleri", show_header=False,
                           border_style="dim blue", box=None, padding=(0, 1), expand=True)
    payments_table.add_column("Kalem", style="cyan", width=30)
    payments_table.add_column("Tutar (TL)", style="yellow", justify="right")
    payments_table.add_row("Nakit Müşteri Ödemeleri",
                           f"{report_data.get('cash_payments_received', 0):.2f}")
    payments_table.add_row("Kredi Kartı Müşteri Ödemeleri",
                           f"{report_data.get('card_payments_received', 0):.2f}")
    payments_table.add_section()
    total_payments = report_data.get(
        'cash_payments_received', 0) + report_data.get('card_payments_received', 0)
    payments_table.add_row("[bold]Toplam Alınan Ödeme[/]",
                           f"[bold]{total_payments:.2f}[/]")

    # Kasa Hesaplama Tablosu
    cash_table = Table(title="Kasa Hesabı", show_header=False,
                       border_style="dim blue", box=None, padding=(0, 1), expand=True)
    cash_table.add_column("Kalem", style="cyan", width=30)
    cash_table.add_column("Tutar (TL)", style="yellow", justify="right")
    cash_table.add_row("Başlangıç Kasası",
                       f"{report_data.get('starting_cash', 0):.2f}")
    cash_table.add_row("(+) Nakit Satışlar",
                       f"{report_data.get('cash_sales', 0):.2f}")
    cash_table.add_row("(+) Alınan Nakit Ödemeler",
                       f"{report_data.get('cash_payments_received', 0):.2f}")
    cash_table.add_section()
    cash_table.add_row("[bold]Beklenen Nakit Kasa[/]",
                       f"[bold]{report_data.get('expected_cash', 0):.2f}[/]")
    cash_table.add_row("Sayılan Nakit Kasa",
                       f"{report_data.get('ending_cash_counted', 0):.2f}")
    cash_table.add_section()
    difference = report_data.get('calculated_difference', 0)
    diff_style = "green" if difference == 0 else "yellow" if difference > 0 else "bold red"
    diff_text = f"[{diff_style}]{difference:.2f}[/]"
    cash_table.add_row("[bold]Kasa Farkı[/]", diff_text)

    # Tabloları alt alta yazdır
    console.print(sales_table)
    console.print(payments_table)
    console.print(cash_table)


def display_simplified_menu(logged_in_user=None, quick_buttons_info=None):
    """
    Sadeleştirilmiş POS menüsünü gösterir.
    Args:
        logged_in_user (dict | None): Giriş yapmış kullanıcı bilgileri.
        quick_buttons_info (dict | None): Hızlı buton bilgilerini içeren sözlük {key: product_name}.
    """
    user_display = f"Kullanıcı: {logged_in_user['username']} ({logged_in_user['role']})" if logged_in_user else "Giriş Yapılmadı"
    is_admin = logged_in_user and logged_in_user.get('role') == 'admin'

    console.print("\n╭─────────────────────────────────────────╮",
                  style="bold cyan")
    console.print(
        f"│ [bold white on blue]           Market POS           [/] │", style="bold cyan")
    console.print(f"│ [dim]{user_display:<40}[/] │", style="bold cyan")

    if quick_buttons_info:
        console.print(
            "├───────────── Hızlı Butonlar ───────────┤", style="bold cyan")
        button_lines = []
        line = "│"
        max_line_width = 41
        current_line_len = 1
        for key, name in quick_buttons_info.items():
            display_name = name[:10] + ".." if len(name) > 10 else name
            button_text = f" [green]{key}[/]: {display_name} "
            text_len = len(key) + 2 + len(display_name) + 1
            if current_line_len + text_len <= max_line_width:
                line += button_text
                current_line_len += text_len
            else:
                line += " " * (max_line_width - current_line_len + 1) + "│"
                button_lines.append(line)
                line = "│" + button_text
                current_line_len = 1 + text_len
        line += " " * (max_line_width - current_line_len + 1) + "│"
        button_lines.append(line)
        for bline in button_lines:
            console.print(bline, style="cyan")

    # Vardiya İşlemleri
    console.print("├───────────── Vardiya İşlemleri ────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow] V1[/]: Vardiya Başlat                  │", style="cyan")
    console.print(
        "│ [yellow] V0[/]: Vardiya Bitir / Z Raporu       │", style="cyan")

    console.print("├───────────── Satış İşlemleri ──────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow] 1[/]: Sepete Ürün Ekle                 │", style="cyan")
    console.print(
        "│ [yellow] 2[/]: Sepeti Göster                   │", style="cyan")
    console.print(
        "│ [yellow] 3[/]: Sepetten Ürün Sil               │", style="cyan")
    console.print(
        "│ [yellow] 4[/]: Sepeti Boşalt                   │", style="cyan")
    console.print(
        "│ [yellow] 5[/]: Satışı Tamamla                  │", style="cyan")
    console.print(
        "│ [yellow] 6[/]: Satış İptali / İade            │", style="cyan")
    console.print(
        "│ [yellow] 7[/]: Fiyat Sorgula                   │", style="cyan")
    console.print(
        "│ [yellow] 8[/]: Satışı Askıya Al                │", style="cyan")
    console.print(
        "│ [yellow] 9[/]: Askıdaki Satışı Çağır           │", style="cyan")
    console.print("├───────────── Müşteri İşlemleri ────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]10[/]: Yeni Müşteri Ekle               │", style="cyan")
    console.print(
        "│ [yellow]11[/]: Müşterileri Listele             │", style="cyan")
    console.print(
        "│ [yellow]12[/]: Müşteri Güncelle                │", style="cyan")
    console.print(
        "│ [yellow]13[/]: Müşteri Ödeme Al                │", style="cyan")
    console.print(
        "│ [yellow]14[/]: Müşteri Hesap Ekstresi          │", style="cyan")
    console.print(
        "│ [yellow]15[/]: Müşteri Kuponlarını Görüntüle   │", style="cyan")
    console.print(
        "│ [yellow]16[/]: Müşteri Aktif/Pasif Yap        │", style="cyan")
    console.print("├───────────── Ürün İşlemleri ───────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]17[/]: Yeni Ürün Ekle                  │", style="cyan")
    console.print(
        "│ [yellow]18[/]: Ürünleri Listele                │", style="cyan")
    console.print(
        "│ [yellow]19[/]: Ürün Güncelle                   │", style="cyan")
    console.print(
        "│ [yellow]20[/]: Stok Girişi / Alış Kaydı        │", style="cyan")
    console.print(
        "│ [yellow]21[/]: Stok Sayım/Düzeltme (Manuel)   │", style="cyan")
    console.print(
        "│ [yellow]22[/]: Ürün Aktif/Pasif Yap           │", style="cyan")
    console.print("├───────────── Marka İşlemleri ──────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]23[/]: Yeni Marka Ekle                 │", style="cyan")
    console.print(
        "│ [yellow]24[/]: Markaları Listele               │", style="cyan")
    console.print(
        "│ [yellow]25[/]: Marka Aktif/Pasif Yap          │", style="cyan")
    console.print("├───────────── Kategori İşlemleri ─────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]26[/]: Yeni Kategori Ekle              │", style="cyan")
    console.print(
        "│ [yellow]27[/]: Kategorileri Listele            │", style="cyan")
    console.print(
        "│ [yellow]28[/]: Kategori Güncelle               │", style="cyan")
    console.print(
        "│ [yellow]29[/]: Kategori Aktif/Pasif Yap       │", style="cyan")
    console.print("├───────────── Promosyon İşlemleri ──────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]30[/]: Yeni Promosyon Ekle             │", style="cyan")
    console.print(
        "│ [yellow]31[/]: Promosyonları Listele           │", style="cyan")
    console.print(
        "│ [yellow]32[/]: Promosyon Aktif/Pasif Yap      │", style="cyan")
    console.print("├───────────── Tedarikçi İşlemleri ──────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]33[/]: Yeni Tedarikçi Ekle              │", style="cyan")
    console.print(
        "│ [yellow]34[/]: Tedarikçileri Listele            │", style="cyan")
    console.print(
        "│ [yellow]35[/]: Tedarikçi Güncelle              │", style="cyan")
    console.print(
        "│ [yellow]36[/]: Tedarikçi Aktif/Pasif Yap       │", style="cyan")
    console.print("├───────────── Raporlar ─────────────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]37[/]: Günlük Satış Özeti             │", style="cyan")
    console.print(
        "│ [yellow]38[/]: En Çok Satanlar (Adet)        │", style="cyan")
    console.print(
        "│ [yellow]39[/]: En Çok Ciro Yapanlar (Tutar)   │", style="cyan")
    console.print(
        "│ [yellow]40[/]: Stok Raporu                    │", style="cyan")
    console.print(
        "│ [yellow]41[/]: Kâr/Zarar Raporu (Tahmini)    │", style="cyan")
    console.print(
        "│ [yellow]42[/]: SKT Raporu                     │", style="cyan")
    console.print("├───────────── Hesap İşlemleri ──────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow]43[/]: Şifre Değiştir                 │", style="cyan")
    if is_admin:
        console.print(
            "├───────────── Yönetim ──────────────────┤", style="bold cyan")
        console.print(
            "│ [yellow]44[/]: Yeni Kullanıcı Ekle            │", style="cyan")
        console.print(
            "│ [yellow]45[/]: Kullanıcıları Listele           │", style="cyan")
        console.print(
            "│ [yellow]46[/]: Kullanıcı Güncelle             │", style="cyan")
        console.print(
            "│ [yellow]47[/]: Kullanıcı Aktif/Pasif Yap      │", style="cyan")
    console.print("├─────────────────────────────────────────┤",
                  style="bold cyan")
    console.print(
        "│ [yellow] 0[/]: Çıkış                           │", style="cyan")
    console.print("╰─────────────────────────────────────────╯",
                  style="bold cyan")

# ***** YENİ FONKSİYON: Sipariş Önerisi Raporu Gösterimi *****


def display_order_suggestion_report(report_data):
    """Sipariş öneri listesini tablo olarak gösterir."""
    title = "Sipariş Önerisi Raporu (Kritik Stok)"
    console.print(f"\n--- {title} ---", style="bold blue")
    console.print(
        "[dim](Tahmini Tükenme: Son iki alış arasındaki gün sayısı)[/]")

    if not report_data:
        console.print(
            ">>> Sipariş önerilecek ürün bulunmamaktadır.", style="yellow")
        return

    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["Barkod", "Ürün Adı", "Mevcut Stok", "Min. Stok",
               "Son Tedarikçi", "Son Alış F. (TL)", "Tahmini Tükenme (Gün)"]
    table.add_column(headers[0], style="cyan")
    table.add_column(headers[1], style="green", min_width=25)
    table.add_column(headers[2], style="bold red",
                     justify="right")  # Mevcut Stok
    table.add_column(headers[3], style="dim", justify="right")      # Min. Stok
    table.add_column(headers[4], style="blue", min_width=20)      # Tedarikçi
    # Son Alış F.
    table.add_column(headers[5], style="yellow", justify="right")
    table.add_column(headers[6], style="magenta",
                     justify="right")  # Tükenme Süresi

    for item in report_data:
        last_cost_str = f"{item['last_cost']:.2f}" if item['last_cost'] is not None else "-"
        days_lasted_str = str(
            item['days_lasted']) if item['days_lasted'] is not None else "-"
        table.add_row(
            item.get('barcode') or "-",
            item.get('name', '-'),
            str(item.get('current_stock', '-')),
            str(item.get('min_stock_level', '-')),
            item.get('last_supplier', '-') or "-",
            last_cost_str,
            days_lasted_str
        )

    console.print(table)
    console.print(
        f"\nToplam {len(report_data)} ürün için sipariş önerisi listelendi.")
# ***** YENİ FONKSİYON SONU *****

# === Diğer UI fonksiyonları ... ===
