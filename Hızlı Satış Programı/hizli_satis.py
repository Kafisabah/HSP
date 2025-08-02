# hizli_satis.py
# Bu dosya, sadeleştirilmiş Market POS uygulamasının ana giriş noktasıdır.
# ... (Önceki versiyon notları) ...
# v59: Rapor limitleri için config.ini'den varsayılan değer okuma eklendi.
# v61 (Bu versiyon): Başlangıçtaki sessiz kapanma sorununu bulmak için DEBUG print ifadeleri eklendi.

# --- DEBUG: Modül importları başlıyor ---
import math
from mysql.connector import Error
import datetime
import copy
from rich.table import Table
from rich.console import Console
import os
import configparser  # Yapılandırma için eklendi
import sys
from decimal import Decimal, ROUND_HALF_UP
from hatalar import DatabaseError, DuplicateEntryError, SaleIntegrityError, UserInputError, AuthenticationError
import veri_aktarim
import loglama
import vardiya_veritabani as shift_db_ops
import vardiya_islemleri as shift_handlers
import promosyon_veritabani as promo_db_ops
import promosyon_islemleri as promo_handlers
import marka_islemleri as brand_handlers
import kategori_islemleri as category_handlers
import musteri_islemleri as customer_handlers
import kullanici_veritabani as user_db_ops
import kullanici_islemleri as user_handlers
import tedarikci_islemleri as supplier_handlers
import veritabani_islemleri as sale_db_ops
import urun_islemleri as product_handlers
import arayuz_yardimcilari as ui
import musteri_veritabani as customer_db_ops
import urun_veritabani as product_db_ops
import db_config
print("DEBUG: Modül importları başlıyor...")

print("DEBUG: Modül importları tamamlandı.")

# Ana konsol nesnesini arayuz_yardimcilari'ndan al
try:
    print("DEBUG: Arayüz konsolu alınıyor...")
    console = ui.console
    print("DEBUG: Arayüz konsolu alındı.")
except Exception as e:
    print(f"DEBUG: Arayüz konsolu alınırken HATA: {e}")
    # Hata durumunda basit bir konsol oluştur
    console = Console()

# --- Yardımcı Fonksiyon: Yapılandırmayı Oku ---


def _get_config():
    """config.ini dosyasını okur ve config nesnesini döndürür."""
    print("DEBUG: _get_config fonksiyonu çağrıldı.")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.ini')
    config = configparser.ConfigParser(interpolation=None)
    read_ok = config.read(config_path, encoding='utf-8')
    if not read_ok:
        console.print(
            f"[yellow]Uyarı: Yapılandırma dosyası okunamadı: {config_path}. Varsayılan değerler kullanılabilir.[/]")
    print(
        f"DEBUG: _get_config fonksiyonu tamamlandı. Okuma başarılı mı: {bool(read_ok)}")
    return config

# === Yardımcı Fonksiyonlar ===
# ... (find_and_select_product_for_cart, _handle_customer_selection_for_sale fonksiyonları aynı kalır) ...


def find_and_select_product_for_cart(connection):
    """Sepete eklemek için ürün arar ve seçtirir."""
    user_input = ui.get_non_empty_input(
        "Eklenecek Ürünün Barkodunu veya Adını girin: ")
    product_list = []
    product_dict = None
    try:
        if user_input.isdigit():
            product_dict = product_db_ops.get_product_by_barcode(
                connection, user_input, only_active=True)
            if product_dict:
                product_list = [product_dict]
        if not product_list: product_list = product_db_ops.get_products_by_name_like(
            connection, user_input, only_active=True)
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI (Arama): {e}", style="bold red"); return None
    if not product_list: console.print(f"\n>>> '{user_input}' ile eşleşen aktif ürün bulunamadı.", style="yellow"); return None
    selected_product_dict = None
    if len(product_list) == 1:
        selected_product_dict = product_list[0]
        product_name = selected_product_dict.get('name', '?'); product_stock = selected_product_dict.get(
            'stock'); min_stock = selected_product_dict.get('min_stock_level', 2)
        stock_warning = ""
        if product_stock is not None:
            if product_stock < 0:
                stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"
            elif product_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"
            elif product_stock <= min_stock:
                stock_warning = " [bold yellow](KRİTİK STOK!)[/]"
        console.print(
            f"\n>>> Ürün bulundu: [cyan]{product_name}[/]{stock_warning}")
    else:
        console.print(
            f"\n>>> '{user_input}' ile eşleşen birden fazla aktif ürün bulundu:")
        select_table = Table(show_header=False, box=None)
        select_table.add_column("No", style="dim")
        select_table.add_column("Ad", style="cyan"); select_table.add_column(
            "Fiyat", style="yellow"); select_table.add_column("Stok", style="green")
        for i, p in enumerate(product_list, 1):
            stock = p.get('stock')
            min_stock = p.get('min_stock_level', 2); stock_display = str(
                stock) if stock is not None else "-"; stock_style = "green"
            if stock is not None:
                if stock < 0:
                    stock_style = "bold white on red"; stock_display = f"[{stock_style}]{stock} (EKSİ!)[/]"
                elif stock == 0: stock_style = "bold red"; stock_display = f"[{stock_style}]{stock} (0!)[/]"
                elif stock <= min_stock:
                    stock_style = "bold yellow"; stock_display = f"[{stock_style}]{stock} (Kritik!)[/]"
                else: stock_display = f"[{stock_style}]{stock}[/]"
            select_table.add_row(f"{i}.", p.get(
                'name', '?'), f"{p.get('selling_price', 0):.2f} TL", stock_display)
        console.print(select_table)
        while True:
            prompt = f"Seçiminiz (1-{len(product_list)}, İptal için 0): "
            choice_num = ui.get_positive_int_input(prompt, allow_zero=True)
            if choice_num == 0:
                console.print("İptal edildi.", style="yellow"); selected_product_dict = None; break
            elif 1 <= choice_num <= len(product_list):
                selected_product_dict = product_list[choice_num - 1]
                product_name = selected_product_dict.get('name', '?'); product_stock = selected_product_dict.get(
                    'stock'); min_stock = selected_product_dict.get('min_stock_level', 2); stock_warning = ""
                if product_stock is not None:
                    if product_stock < 0:
                        stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"
                    elif product_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"
                    elif product_stock <= min_stock:
                        stock_warning = " [bold yellow](KRİTİK STOK!)[/]"
                console.print(f"\n>>> Seçilen: [cyan]{product_name}[/]{stock_warning}"); break
            else:
                console.print(f">>> Geçersiz numara!", style="red")
    if selected_product_dict:
        # Ürünün tüm bilgilerini içeren sözlüğü döndür
        return selected_product_dict  # Önceki tuple yerine dict döndür
    else:
        return None


def _handle_customer_selection_for_sale(connection, prompt_message="Müşteri Adı veya Telefon No: "):
    """Satış sırasında müşteri seçme veya ekleme işlemini yönetir."""
    while True:
        console.print(
            "\nMüşteri İşlemi: [A]ra / [Y]eni Ekle / [V]azgeç? ", end="")
        cust_choice = input().strip().upper()
        if cust_choice == 'A':
            search_term = ui.get_non_empty_input(prompt_message)
            try:
                cust_list = []
                is_phone = search_term.isdigit() or '+' in search_term
                if is_phone:
                    # DB fonksiyonu tuple döner (id, name, is_active)
                    cust = customer_db_ops.get_customer_by_phone(
                        connection, search_term, only_active=True)
                    if cust: cust_list = [cust]  # Tek elemanlı liste
                else:  # Telefon değilse isimle ara
                    cust_list = customer_db_ops.get_customers_by_name_like(
                        connection, search_term, only_active=True)

                if not cust_list:
                    console.print(
                        ">>> Aktif müşteri bulunamadı.", style="yellow")
                    if not ui.get_yes_no_input("Tekrar aramak veya yeni eklemek ister misiniz? (E: Tekrar Dene / H: Vazgeç)"):
                        return None, None  # Vazgeçildi
                    else: continue  # Tekrar dene
                elif len(cust_list) == 1:
                    # Tuple'dan al
                    customer_id, customer_name, _ = cust_list[0]
                    console.print(
                        f">>> Müşteri seçildi: {customer_name} (ID: {customer_id})", style="green")
                    return customer_id, customer_name
                else:  # Birden fazla bulundu
                    console.print(
                        "\n--- Birden Fazla Aktif Müşteri Bulundu ---")
                    # display_customer_list tuple listesi bekliyor
                    ui.display_customer_list(
                        cust_list, title="Eşleşen Müşteriler")
                    while True:
                        select_prompt = f"Satışa bağlanacak müşteri No (1-{len(cust_list)}, İptal: 0): "
                        select_no = ui.get_positive_int_input(
                            select_prompt, allow_zero=True)
                        if select_no == 0:
                            console.print(
                                "Müşteri seçimi iptal edildi.", style="yellow")
                            break  # İç döngüden çık, ana seçime dön
                        elif 1 <= select_no <= len(cust_list):
                            customer_id, customer_name, _ = cust_list[select_no - 1]
                            console.print(
                                f">>> Müşteri seçildi: {customer_name} (ID: {customer_id})", style="green")
                            return customer_id, customer_name
                        else:
                            console.print(">>> Geçersiz numara!", style="red")
                    continue  # İç döngüden çıkıldı (iptal), ana seçime dön
            except DatabaseError as e:
                console.print(
                    f">>> VERİTABANI HATASI (Müşteri Arama): {e}", style="bold red")
                return None, None  # Hata, çık
        elif cust_choice == 'Y':
            console.print(
                "\n--- Yeni Müşteri Ekle (Satış İçin) ---", style="bold blue")
            # handle_add_customer'ı doğrudan çağırmak yerine burada ekleyelim
            try:
                name = ui.get_non_empty_input("Müşteri Adı Soyadı (*): ")
                phone = input("Telefon: ").strip() or None
                email = input("E-posta: ").strip() or None
                address = input("Adres: ").strip() or None
                # add_customer ID döner
                new_customer_id = customer_db_ops.add_customer(
                    connection, name, phone, email, address)
                if new_customer_id:
                    # Başarı mesajı DB fonksiyonunda veriliyor
                    return new_customer_id, name  # ID ve ismi döndür
                else:  # Ekleme başarısız olduysa (örn. duplicate)
                    continue  # Tekrar müşteri işlemi sor
            except DuplicateEntryError as e:
                 console.print(f">>> HATA: {e}", style="bold red")
                 continue  # Tekrar müşteri işlemi sor
            except DatabaseError as e:
                 console.print(
                     f">>> VERİTABANI HATASI (Müşteri Ekleme): {e}", style="bold red")
                 return None, None  # Hata, çık
            except Exception as e:
                 console.print(
                     f">>> BEKLENMEDİK HATA (Müşteri Ekleme): {e}", style="bold red")
                 return None, None  # Hata, çık
        elif cust_choice == 'V':
            console.print("Müşteri işlemi iptal edildi.", style="yellow")
            return None, None  # Vazgeçildi
        else:
            console.print(">>> Geçersiz seçim (A, Y, V).", style="red")


# === Ana Uygulama Fonksiyonu ===
def main():
    """Ana uygulama fonksiyonu - Giriş ve Menü Döngüsü"""
    print("DEBUG: main() fonksiyonu başladı.")  # DEBUG
    console.print("Market POS (Hızlı Satış) Başlatılıyor...",
                  style="bold green")

    print("DEBUG: Veritabanına bağlanılıyor...")  # DEBUG
    connection = None  # Önce None ata
    try:
        connection = db_config.connect_db()
        if not (connection and connection.is_connected()):
            console.print("!!! KRİTİK HATA: Veritabanına bağlanılamadı.",
                          style="bold red")
            sys.exit(1)  # Bağlantı yoksa çık
        print("DEBUG: Veritabanı bağlantısı başarılı.")  # DEBUG
        console.print("Veritabanı bağlantısı başarılı!", style="green")
    except Exception as db_conn_err:
        print(f"DEBUG: Veritabanı bağlantı HATASI: {db_conn_err}")  # DEBUG
        console.print(
            f"!!! KRİTİK HATA: Veritabanına bağlanırken hata oluştu: {db_conn_err}", style="bold red")
        sys.exit(1)  # Bağlantı hatasında çık

    print("DEBUG: Kullanıcı girişi yapılıyor...")  # DEBUG
    logged_in_user = None
    try:
        logged_in_user = user_handlers.handle_login(connection)
    except (DatabaseError, AuthenticationError) as login_err:
        print(f"DEBUG: Giriş hatası (DB/Auth): {login_err}")  # DEBUG
        console.print(f"\n[bold red]GİRİŞ HATASI: {login_err}[/]")
        logged_in_user = None
    except Exception as login_err:
        print(f"DEBUG: Giriş sırasında beklenmedik hata: {login_err}")  # DEBUG
        console.print(
            f"\n[bold red]GİRİŞ SIRASINDA KRİTİK HATA: {login_err}[/]")
        logged_in_user = None

    if logged_in_user is None:
        print("DEBUG: Giriş başarısız, programdan çıkılıyor.")  # DEBUG
        if connection and connection.is_connected():
            connection.close()
            print("DEBUG: Veritabanı bağlantısı kapatıldı (giriş başarısız).")  # DEBUG
        sys.exit(1)
    print(f"DEBUG: Giriş başarılı: {logged_in_user.get('username')}")  # DEBUG

    current_user_id = logged_in_user.get('user_id')
    user_role = logged_in_user.get('role', '').lower()  # Rolü küçük harfle al

    # Yetki setleri (küçük harfle)
    YONETICI_VE_USTU = ['yonetici', 'admin']
    TUM_KULLANICILAR = ['kasiyer', 'yonetici', 'admin']

    print("DEBUG: Aktif vardiya kontrol ediliyor...")  # DEBUG
    active_shift_id = None
    try:
        active_shift_data = shift_db_ops.get_active_shift(
            connection, current_user_id)
        if active_shift_data:
            active_shift_id = active_shift_data.get('shift_id')
            start_time = active_shift_data.get('start_time')
            start_time_str = start_time.strftime(
                '%d-%m-%Y %H:%M:%S') if start_time else '?'
            console.print(
                f"[bold yellow]Aktif Vardiya Bulundu (ID: {active_shift_id}, Başlangıç: {start_time_str}).[/]")
        else:
            console.print(
                "[dim]Aktif vardiya bulunmuyor. Satış yapmadan önce vardiya başlatmanız önerilir.[/]")
        print("DEBUG: Aktif vardiya kontrolü tamamlandı.")  # DEBUG
    except DatabaseError as e:
        print(f"DEBUG: Aktif vardiya kontrol hatası: {e}")  # DEBUG
        console.print(f"[red]Aktif vardiya kontrolü sırasında hata: {e}[/]")

    # Yapılandırmayı oku
    print("DEBUG: Yapılandırma okunuyor...")  # DEBUG
    config = _get_config()
    PAYMENT_METHODS = ("Nakit", "Kredi Kartı", "Veresiye")  # Varsayılan
    CUSTOMER_PAYMENT_METHODS = ("Nakit", "Kredi Kartı")  # Varsayılan
    STORE_NAME = "Varsayılan Market"  # Varsayılan
    DEFAULT_REPORT_LIMIT = 10  # Varsayılan

    try:
        if config.has_section('general'):
            print("DEBUG: [general] bölümü okunuyor...")  # DEBUG
            if config.has_option('general', 'payment_methods'):
                methods_str = config.get('general', 'payment_methods')
                PAYMENT_METHODS = tuple(m.strip()
                                        for m in methods_str.split(',') if m.strip())
                CUSTOMER_PAYMENT_METHODS = tuple(
                    p for p in PAYMENT_METHODS if p != "Veresiye")
                print(f"DEBUG: Ödeme yöntemleri: {PAYMENT_METHODS}")  # DEBUG
            if config.has_option('general', 'store_name'):
                STORE_NAME = config.get(
                    'general', 'store_name', fallback=STORE_NAME)
                print(f"DEBUG: Mağaza adı: {STORE_NAME}")  # DEBUG
            if config.has_option('general', 'default_report_limit'):
                try:
                    DEFAULT_REPORT_LIMIT = config.getint(
                        'general', 'default_report_limit', fallback=10)
                    # DEBUG
                    print(
                        f"DEBUG: Varsayılan rapor limiti: {DEFAULT_REPORT_LIMIT}")
                except ValueError:
                    console.print(
                        "[yellow]Uyarı: config.ini'deki 'default_report_limit' geçersiz, varsayılan (10) kullanılıyor.[/]")
                    DEFAULT_REPORT_LIMIT = 10
        else:
             print("DEBUG: [general] bölümü bulunamadı.")  # DEBUG
    except Exception as e:
        print(f"DEBUG: Genel ayarlar okunurken hata: {e}")  # DEBUG
        console.print(
            f"Uyarı: Genel ayarlar okunurken hata ({e}). Varsayılanlar kullanılacak.", style="yellow")

    # Hızlı butonları oku
    print("DEBUG: Hızlı butonlar okunuyor...")  # DEBUG
    quick_button_barcodes = {}
    quick_button_products = {}
    quick_button_menu_info = {}
    try:
        if config.has_section('quick_buttons'):
            print("DEBUG: [quick_buttons] bölümü okunuyor...")  # DEBUG
            quick_button_barcodes = dict(config.items('quick_buttons'))
            barcodes_to_fetch = list(quick_button_barcodes.values())
            if barcodes_to_fetch:
                # DEBUG
                print(
                    f"DEBUG: Hızlı buton barkodları alınıyor: {barcodes_to_fetch}")
                try:
                    fetched_products = product_db_ops.get_products_by_barcodes(
                        connection, barcodes_to_fetch)
                    products_by_barcode = {
                        p['barcode']: p for p in fetched_products}
                    for key, barcode in quick_button_barcodes.items():
                        product_data = products_by_barcode.get(barcode)
                        if product_data:
                            quick_button_products[key] = product_data
                            quick_button_menu_info[key] = product_data.get(
                                'name', '?')
                        else:
                            console.print(
                                f"[yellow]Uyarı: Hızlı buton '{key}' için tanımlanan barkod ({barcode}) bulunamadı veya ürün pasif.[/]")
                    # DEBUG
                    print(
                        f"DEBUG: Hızlı buton ürünleri: {list(quick_button_products.keys())}")
                except DatabaseError as db_err:
                    print(f"DEBUG: Hızlı buton DB hatası: {db_err}")  # DEBUG
                    console.print(
                        f"[red]HATA: Hızlı buton ürünleri veritabanından alınırken hata: {db_err}[/]")
                except Exception as e:
                    print(f"DEBUG: Hızlı buton işleme hatası: {e}")  # DEBUG
                    console.print(
                        f"[red]HATA: Hızlı buton ürünleri işlenirken hata: {e}[/]")
            else:
                 print("DEBUG: Hızlı buton barkodu tanımlanmamış.")  # DEBUG
        else:
             print("DEBUG: [quick_buttons] bölümü bulunamadı.")  # DEBUG
    except Exception as e:
        print(f"DEBUG: Hızlı buton ayarları okunurken hata: {e}")  # DEBUG
        console.print(
            f"Uyarı: Hızlı buton ayarları okunurken hata ({e}).", style="yellow")

    console.print(f"Mağaza Adı: [bold cyan]{STORE_NAME}[/]")
    console.print(
        f"Satış Ödeme Yöntemleri: [blue]{', '.join(PAYMENT_METHODS)}[/]")
    if not CUSTOMER_PAYMENT_METHODS:
        console.print(
            "[bold yellow]Uyarı: Müşteri ödemesi almak için geçerli yöntem bulunamadı.[/]")
    if quick_button_menu_info:
        console.print("Hızlı Butonlar Aktif!", style="green")

    cart = []
    suspended_sales = {}
    suspended_sale_id_counter = 1

    print("DEBUG: Ana menü döngüsü başlıyor...")  # DEBUG
    while True:
        suspend_count = len(suspended_sales)
        suspend_info = f" [Askıda:{suspend_count}]" if suspend_count > 0 else ""
        shift_info = f" [Vardiya:{active_shift_id}]" if active_shift_id else " [Vardiya Yok]"
        ui.display_simplified_menu(logged_in_user, quick_button_menu_info)
        console.print(
            f"İşlem Seçin veya Barkod Okutun [Sepet:{len(cart)}]{suspend_info}{shift_info}: ", style="bold magenta", end="")
        choice = input().strip().lower()
        print(f"DEBUG: Kullanıcı seçimi: {choice}")  # DEBUG

        try:
            # --- Hızlı Buton / Barkod / Temel İşlemler ---
            if choice in quick_button_products:
                 # ... (Hızlı Buton Kodu - Değişiklik Yok) ...
                 product_data = quick_button_products[choice]
                 product_id = product_data.get('product_id'); barcode = product_data.get('barcode'); product_name = product_data.get('name'); selling_price = product_data.get(
                     'selling_price'); product_stock = product_data.get('stock'); min_stock = product_data.get('min_stock_level', 2); stock_warning = ""; stock_style = "blue"
                 if product_stock is not None:
                     if product_stock < 0:
                         stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"; stock_style = "bold white on red"
                     elif product_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"; stock_style = "bold red"
       # hizli_satis.py
# Bu dosya, sadeleştirilmiş Market POS uygulamasının ana giriş noktasıdır.
# ... (Önceki versiyon notları) ...
# v59: Rapor limitleri için config.ini'den varsayılan değer okuma eklendi.
# v61 (Bu versiyon): Başlangıçtaki sessiz kapanma sorununu bulmak için DEBUG print ifadeleri eklendi.
# v62 (Bu versiyon): v61'deki olası girinti hataları düzeltildi.

# --- DEBUG: Modül importları başlıyor ---
print("DEBUG: Modül importları başlıyor...")
import db_config
import urun_veritabani as product_db_ops
import musteri_veritabani as customer_db_ops
import arayuz_yardimcilari as ui
import urun_islemleri as product_handlers
import veritabani_islemleri as sale_db_ops
import tedarikci_islemleri as supplier_handlers
import kullanici_islemleri as user_handlers
import kullanici_veritabani as user_db_ops
import musteri_islemleri as customer_handlers
import kategori_islemleri as category_handlers
import marka_islemleri as brand_handlers
import promosyon_islemleri as promo_handlers
import promosyon_veritabani as promo_db_ops
import vardiya_islemleri as shift_handlers
import vardiya_veritabani as shift_db_ops
import loglama
import veri_aktarim

from hatalar import DatabaseError, DuplicateEntryError, SaleIntegrityError, UserInputError, AuthenticationError
from decimal import Decimal, ROUND_HALF_UP
import sys
import configparser # Yapılandırma için eklendi
import os
from rich.console import Console
from rich.table import Table
import copy
import datetime
from mysql.connector import Error
import math
print("DEBUG: Modül importları tamamlandı.")

# Ana konsol nesnesini arayuz_yardimcilari'ndan al
try:
    print("DEBUG: Arayüz konsolu alınıyor...")
    console = ui.console
    print("DEBUG: Arayüz konsolu alındı.")
except Exception as e:
    print(f"DEBUG: Arayüz konsolu alınırken HATA: {e}")
    # Hata durumunda basit bir konsol oluştur
    console = Console()

# --- Yardımcı Fonksiyon: Yapılandırmayı Oku ---
def _get_config():
    """config.ini dosyasını okur ve config nesnesini döndürür."""
    print("DEBUG: _get_config fonksiyonu çağrıldı.")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.ini')
    config = configparser.ConfigParser(interpolation=None)
    read_ok = config.read(config_path, encoding='utf-8')
    if not read_ok:
        # console nesnesi burada henüz tanımlanmamış olabilir, standart print kullan
        print(f"[UYARI] Yapılandırma dosyası okunamadı: {config_path}. Varsayılan değerler kullanılabilir.")
    print(f"DEBUG: _get_config fonksiyonu tamamlandı. Okuma başarılı mı: {bool(read_ok)}")
    return config

# === Yardımcı Fonksiyonlar ===
def find_and_select_product_for_cart(connection):
    """Sepete eklemek için ürün arar ve seçtirir."""
    user_input = ui.get_non_empty_input(
        "Eklenecek Ürünün Barkodunu veya Adını girin: ")
    product_list = []
    product_dict = None
    try:
        if user_input.isdigit():
            product_dict = product_db_ops.get_product_by_barcode(
                connection, user_input, only_active=True)
            if product_dict:
                product_list = [product_dict]
        if not product_list:
            product_list = product_db_ops.get_products_by_name_like(
                connection, user_input, only_active=True)
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI (Arama): {e}", style="bold red")
        return None
    if not product_list:
        console.print(f"\n>>> '{user_input}' ile eşleşen aktif ürün bulunamadı.", style="yellow")
        return None

    selected_product_dict = None
    if len(product_list) == 1:
        selected_product_dict = product_list[0]
        product_name = selected_product_dict.get('name', '?')
        product_stock = selected_product_dict.get('stock')
        min_stock = selected_product_dict.get('min_stock_level', 2)
        stock_warning = ""
        if product_stock is not None:
            if product_stock < 0:
                stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"
            elif product_stock == 0:
                stock_warning = " [bold red](STOK 0!)[/]"
            elif product_stock <= min_stock:
                stock_warning = " [bold yellow](KRİTİK STOK!)[/]"
        console.print(
            f"\n>>> Ürün bulundu: [cyan]{product_name}[/]{stock_warning}")
    else:
        console.print(
            f"\n>>> '{user_input}' ile eşleşen birden fazla aktif ürün bulundu:")
        select_table = Table(show_header=False, box=None)
        select_table.add_column("No", style="dim")
        select_table.add_column("Ad", style="cyan")
        select_table.add_column("Fiyat", style="yellow")
        select_table.add_column("Stok", style="green")
        for i, p in enumerate(product_list, 1):
            stock = p.get('stock')
            min_stock = p.get('min_stock_level', 2)
            stock_display = str(stock) if stock is not None else "-"
            stock_style = "green"
            if stock is not None:
                if stock < 0:
                    stock_style = "bold white on red"
                    stock_display = f"[{stock_style}]{stock} (EKSİ!)[/]"
                elif stock == 0:
                    stock_style = "bold red"
                    stock_display = f"[{stock_style}]{stock} (0!)[/]"
                elif stock <= min_stock:
                    stock_style = "bold yellow"
                    stock_display = f"[{stock_style}]{stock} (Kritik!)[/]"
                else:
                    stock_display = f"[{stock_style}]{stock}[/]"
            select_table.add_row(f"{i}.", p.get('name', '?'), f"{p.get('selling_price', 0):.2f} TL", stock_display)
        console.print(select_table)
        while True:
            prompt = f"Seçiminiz (1-{len(product_list)}, İptal için 0): "
            choice_num = ui.get_positive_int_input(prompt, allow_zero=True)
            if choice_num == 0:
                console.print("İptal edildi.", style="yellow")
                selected_product_dict = None
                break
            elif 1 <= choice_num <= len(product_list):
                selected_product_dict = product_list[choice_num - 1]
                product_name = selected_product_dict.get('name', '?')
                product_stock = selected_product_dict.get('stock')
                min_stock = selected_product_dict.get('min_stock_level', 2)
                stock_warning = ""
                if product_stock is not None:
                    if product_stock < 0:
                        stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"
                    elif product_stock == 0:
                        stock_warning = " [bold red](STOK 0!)[/]"
                    elif product_stock <= min_stock:
                        stock_warning = " [bold yellow](KRİTİK STOK!)[/]"
                console.print(f"\n>>> Seçilen: [cyan]{product_name}[/]{stock_warning}")
                break
            else:
                console.print(f">>> Geçersiz numara!", style="red")

    if selected_product_dict:
        # Ürünün tüm bilgilerini içeren sözlüğü döndür
        return selected_product_dict
    else:
        return None


def _handle_customer_selection_for_sale(connection, prompt_message="Müşteri Adı veya Telefon No: "):
    """Satış sırasında müşteri seçme veya ekleme işlemini yönetir."""
    while True:
        console.print(
            "\nMüşteri İşlemi: [A]ra / [Y]eni Ekle / [V]azgeç? ", end="")
        cust_choice = input().strip().upper()
        if cust_choice == 'A':
            search_term = ui.get_non_empty_input(prompt_message)
            try:
                cust_list = []
                is_phone = search_term.isdigit() or '+' in search_term
                if is_phone:
                    # DB fonksiyonu tuple döner (id, name, is_active)
                    cust = customer_db_ops.get_customer_by_phone(
                        connection, search_term, only_active=True)
                    if cust: cust_list = [cust] # Tek elemanlı liste
                else: # Telefon değilse isimle ara
                    cust_list = customer_db_ops.get_customers_by_name_like(
                        connection, search_term, only_active=True)

                if not cust_list:
                    console.print(
                        ">>> Aktif müşteri bulunamadı.", style="yellow")
                    if not ui.get_yes_no_input("Tekrar aramak veya yeni eklemek ister misiniz? (E: Tekrar Dene / H: Vazgeç)"):
                        return None, None # Vazgeçildi
                    else: continue # Tekrar dene
                elif len(cust_list) == 1:
                    customer_id, customer_name, _ = cust_list[0] # Tuple'dan al
                    console.print(f">>> Müşteri seçildi: {customer_name} (ID: {customer_id})", style="green")
                    return customer_id, customer_name
                else: # Birden fazla bulundu
                    console.print(
                        "\n--- Birden Fazla Aktif Müşteri Bulundu ---")
                    # display_customer_list tuple listesi bekliyor
                    ui.display_customer_list(cust_list, title="Eşleşen Müşteriler")
                    while True:
                        select_prompt = f"Satışa bağlanacak müşteri No (1-{len(cust_list)}, İptal: 0): "
                        select_no = ui.get_positive_int_input(
                            select_prompt, allow_zero=True)
                        if select_no == 0:
                            console.print("Müşteri seçimi iptal edildi.", style="yellow")
                            break # İç döngüden çık, ana seçime dön
                        elif 1 <= select_no <= len(cust_list):
                            customer_id, customer_name, _ = cust_list[select_no - 1]
                            console.print(f">>> Müşteri seçildi: {customer_name} (ID: {customer_id})", style="green")
                            return customer_id, customer_name
                        else:
                            console.print(">>> Geçersiz numara!", style="red")
                    continue # İç döngüden çıkıldı (iptal), ana seçime dön
            except DatabaseError as e:
                console.print(f">>> VERİTABANI HATASI (Müşteri Arama): {e}", style="bold red")
                return None, None # Hata, çık
        elif cust_choice == 'Y':
            console.print(
                "\n--- Yeni Müşteri Ekle (Satış İçin) ---", style="bold blue")
            # handle_add_customer'ı doğrudan çağırmak yerine burada ekleyelim
            try:
                name = ui.get_non_empty_input("Müşteri Adı Soyadı (*): ")
                phone = input("Telefon: ").strip() or None
                email = input("E-posta: ").strip() or None
                address = input("Adres: ").strip() or None
                # add_customer ID döner
                new_customer_id = customer_db_ops.add_customer(
                    connection, name, phone, email, address)
                if new_customer_id:
                    # Başarı mesajı DB fonksiyonunda veriliyor
                    return new_customer_id, name # ID ve ismi döndür
                else: # Ekleme başarısız olduysa (örn. duplicate)
                    continue # Tekrar müşteri işlemi sor
            except DuplicateEntryError as e:
                 console.print(f">>> HATA: {e}", style="bold red")
                 continue # Tekrar müşteri işlemi sor
            except DatabaseError as e:
                 console.print(f">>> VERİTABANI HATASI (Müşteri Ekleme): {e}", style="bold red")
                 return None, None # Hata, çık
            except Exception as e:
                 console.print(f">>> BEKLENMEDİK HATA (Müşteri Ekleme): {e}", style="bold red")
                 return None, None # Hata, çık
        elif cust_choice == 'V':
            console.print("Müşteri işlemi iptal edildi.", style="yellow")
            return None, None # Vazgeçildi
        else:
            console.print(">>> Geçersiz seçim (A, Y, V).", style="red")


# === Ana Uygulama Fonksiyonu ===
def main():
    """Ana uygulama fonksiyonu - Giriş ve Menü Döngüsü"""
    print("DEBUG: main() fonksiyonu başladı.") # DEBUG
    console.print("Market POS (Hızlı Satış) Başlatılıyor...",
                  style="bold green")

    print("DEBUG: Veritabanına bağlanılıyor...") # DEBUG
    connection = None # Önce None ata
    try:
        connection = db_config.connect_db()
        if not (connection and connection.is_connected()):
            console.print("!!! KRİTİK HATA: Veritabanına bağlanılamadı.",
                          style="bold red")
            sys.exit(1) # Bağlantı yoksa çık
        print("DEBUG: Veritabanı bağlantısı başarılı.") # DEBUG
        console.print("Veritabanı bağlantısı başarılı!", style="green")
    except Exception as db_conn_err:
        print(f"DEBUG: Veritabanı bağlantı HATASI: {db_conn_err}") # DEBUG
        console.print(f"!!! KRİTİK HATA: Veritabanına bağlanırken hata oluştu: {db_conn_err}", style="bold red")
        sys.exit(1) # Bağlantı hatasında çık

    print("DEBUG: Kullanıcı girişi yapılıyor...") # DEBUG
    logged_in_user = None
    try:
        logged_in_user = user_handlers.handle_login(connection)
    except (DatabaseError, AuthenticationError) as login_err:
        print(f"DEBUG: Giriş hatası (DB/Auth): {login_err}") # DEBUG
        console.print(f"\n[bold red]GİRİŞ HATASI: {login_err}[/]")
        logged_in_user = None
    except Exception as login_err:
        print(f"DEBUG: Giriş sırasında beklenmedik hata: {login_err}") # DEBUG
        console.print(
            f"\n[bold red]GİRİŞ SIRASINDA KRİTİK HATA: {login_err}[/]")
        logged_in_user = None

    if logged_in_user is None:
        print("DEBUG: Giriş başarısız, programdan çıkılıyor.") # DEBUG
        if connection and connection.is_connected():
            connection.close()
            print("DEBUG: Veritabanı bağlantısı kapatıldı (giriş başarısız).") # DEBUG
        sys.exit(1)
    print(f"DEBUG: Giriş başarılı: {logged_in_user.get('username')}") # DEBUG

    current_user_id = logged_in_user.get('user_id')
    user_role = logged_in_user.get('role', '').lower() # Rolü küçük harfle al

    # Yetki setleri (küçük harfle)
    YONETICI_VE_USTU = ['yonetici', 'admin']
    TUM_KULLANICILAR = ['kasiyer', 'yonetici', 'admin']

    print("DEBUG: Aktif vardiya kontrol ediliyor...") # DEBUG
    active_shift_id = None
    try:
        active_shift_data = shift_db_ops.get_active_shift(
            connection, current_user_id)
        if active_shift_data:
            active_shift_id = active_shift_data.get('shift_id')
            start_time = active_shift_data.get('start_time')
            start_time_str = start_time.strftime(
                '%d-%m-%Y %H:%M:%S') if start_time else '?'
            console.print(
                f"[bold yellow]Aktif Vardiya Bulundu (ID: {active_shift_id}, Başlangıç: {start_time_str}).[/]")
        else:
            console.print(
                "[dim]Aktif vardiya bulunmuyor. Satış yapmadan önce vardiya başlatmanız önerilir.[/]")
        print("DEBUG: Aktif vardiya kontrolü tamamlandı.") # DEBUG
    except DatabaseError as e:
        print(f"DEBUG: Aktif vardiya kontrol hatası: {e}") # DEBUG
        console.print(f"[red]Aktif vardiya kontrolü sırasında hata: {e}[/]")

    # Yapılandırmayı oku
    print("DEBUG: Yapılandırma okunuyor...") # DEBUG
    config = _get_config()
    PAYMENT_METHODS = ("Nakit", "Kredi Kartı", "Veresiye") # Varsayılan
    CUSTOMER_PAYMENT_METHODS = ("Nakit", "Kredi Kartı") # Varsayılan
    STORE_NAME = "Varsayılan Market" # Varsayılan
    DEFAULT_REPORT_LIMIT = 10 # Varsayılan

    try:
        if config.has_section('general'):
            print("DEBUG: [general] bölümü okunuyor...") # DEBUG
            if config.has_option('general', 'payment_methods'):
                methods_str = config.get('general', 'payment_methods')
                PAYMENT_METHODS = tuple(m.strip() for m in methods_str.split(',') if m.strip())
                CUSTOMER_PAYMENT_METHODS = tuple(p for p in PAYMENT_METHODS if p != "Veresiye")
                print(f"DEBUG: Ödeme yöntemleri: {PAYMENT_METHODS}") # DEBUG
            if config.has_option('general', 'store_name'):
                STORE_NAME = config.get('general', 'store_name', fallback=STORE_NAME)
                print(f"DEBUG: Mağaza adı: {STORE_NAME}") # DEBUG
            # ***** YENİ: Rapor limitini oku *****
            if config.has_option('general', 'default_report_limit'):
                try:
                    DEFAULT_REPORT_LIMIT = config.getint('general', 'default_report_limit', fallback=10)
                    print(f"DEBUG: Varsayılan rapor limiti: {DEFAULT_REPORT_LIMIT}") # DEBUG
                except ValueError:
                    console.print("[yellow]Uyarı: config.ini'deki 'default_report_limit' geçersiz, varsayılan (10) kullanılıyor.[/]")
                    DEFAULT_REPORT_LIMIT = 10
        else:
             print("DEBUG: [general] bölümü bulunamadı.") # DEBUG
    except Exception as e:
        print(f"DEBUG: Genel ayarlar okunurken hata: {e}") # DEBUG
        console.print(f"Uyarı: Genel ayarlar okunurken hata ({e}). Varsayılanlar kullanılacak.", style="yellow")

    # Hızlı butonları oku
    print("DEBUG: Hızlı butonlar okunuyor...") # DEBUG
    quick_button_barcodes = {}
    quick_button_products = {}
    quick_button_menu_info = {}
    try:
        if config.has_section('quick_buttons'):
            print("DEBUG: [quick_buttons] bölümü okunuyor...") # DEBUG
            quick_button_barcodes = dict(config.items('quick_buttons'))
            barcodes_to_fetch = list(quick_button_barcodes.values())
            if barcodes_to_fetch:
                print(f"DEBUG: Hızlı buton barkodları alınıyor: {barcodes_to_fetch}") # DEBUG
                try:
                    fetched_products = product_db_ops.get_products_by_barcodes(
                        connection, barcodes_to_fetch)
                    products_by_barcode = {
                        p['barcode']: p for p in fetched_products}
                    for key, barcode in quick_button_barcodes.items():
                        product_data = products_by_barcode.get(barcode)
                        if product_data:
                            quick_button_products[key] = product_data
                            quick_button_menu_info[key] = product_data.get('name', '?')
                        else:
                            console.print(f"[yellow]Uyarı: Hızlı buton '{key}' için tanımlanan barkod ({barcode}) bulunamadı veya ürün pasif.[/]")
                    print(f"DEBUG: Hızlı buton ürünleri: {list(quick_button_products.keys())}") # DEBUG
                except DatabaseError as db_err:
                    print(f"DEBUG: Hızlı buton DB hatası: {db_err}") # DEBUG
                    console.print(
                        f"[red]HATA: Hızlı buton ürünleri veritabanından alınırken hata: {db_err}[/]")
                except Exception as e:
                    print(f"DEBUG: Hızlı buton işleme hatası: {e}") # DEBUG
                    console.print(f"[red]HATA: Hızlı buton ürünleri işlenirken hata: {e}[/]")
            else:
                 print("DEBUG: Hızlı buton barkodu tanımlanmamış.") # DEBUG
        else:
             print("DEBUG: [quick_buttons] bölümü bulunamadı.") # DEBUG
    except Exception as e:
        print(f"DEBUG: Hızlı buton ayarları okunurken hata: {e}") # DEBUG
        console.print(f"Uyarı: Hızlı buton ayarları okunurken hata ({e}).", style="yellow")


    console.print(f"Mağaza Adı: [bold cyan]{STORE_NAME}[/]")
    console.print(
        f"Satış Ödeme Yöntemleri: [blue]{', '.join(PAYMENT_METHODS)}[/]")
    if not CUSTOMER_PAYMENT_METHODS:
        console.print(
            "[bold yellow]Uyarı: Müşteri ödemesi almak için geçerli yöntem bulunamadı.[/]")
    if quick_button_menu_info:
        console.print("Hızlı Butonlar Aktif!", style="green")

    cart = []
    suspended_sales = {}
    suspended_sale_id_counter = 1

    print("DEBUG: Ana menü döngüsü başlıyor...") # DEBUG
    while True:
        suspend_count = len(suspended_sales)
        suspend_info = f" [Askıda:{suspend_count}]" if suspend_count > 0 else ""
        shift_info = f" [Vardiya:{active_shift_id}]" if active_shift_id else " [Vardiya Yok]"
        ui.display_simplified_menu(logged_in_user, quick_button_menu_info)
        console.print(
            f"İşlem Seçin veya Barkod Okutun [Sepet:{len(cart)}]{suspend_info}{shift_info}: ", style="bold magenta", end="")
        choice = input().strip().lower()
        print(f"DEBUG: Kullanıcı seçimi: {choice}") # DEBUG

        try:
            # --- Hızlı Buton / Barkod / Temel İşlemler ---
            if choice in quick_button_products:
                 # ... (Hızlı Buton Kodu) ...
                 product_data = quick_button_products[choice]
                 product_id = product_data.get('product_id'); barcode = product_data.get('barcode'); product_name = product_data.get('name'); selling_price = product_data.get(
                     'selling_price'); product_stock = product_data.get('stock'); min_stock = product_data.get('min_stock_level', 2); stock_warning = ""; stock_style = "blue"
                 if product_stock is not None:
                     if product_stock < 0:
                         stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"; stock_style = "bold white on red"
                     elif product_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"; stock_style = "bold red"
                     elif product_stock <= min_stock:
                         stock_warning = " [bold yellow](KRİTİK STOK!)[/]"; stock_style = "bold yellow"
                 quantity = 0
                 while True:
                     prompt = f"'{product_name}' için Miktar (Stok: [{stock_style}]{product_stock if product_stock is not None else '?'}[/]{stock_warning}) [Varsayılan: 1]: "
                     quantity_str = input(prompt).strip()
                     if not quantity_str:
                         quantity = 1; break
                     try: quantity_val = int(quantity_str);
                     if quantity_val > 0:
                         quantity = quantity_val; break
                     else: console.print(">>> HATA: Miktar 0'dan büyük olmalıdır.", style="red")
                     except ValueError:
                         console.print(">>> HATA: Geçersiz sayı.", style="red")
                 if quantity > 0:
                     found_in_cart = False
                     for item in cart:
                         if item['product_id'] == product_id:
                             item['quantity'] += quantity; console.print(f">>> Miktar artırıldı: {product_name} - Yeni Miktar: {item['quantity']}", style="green"); found_in_cart = True; break
                     if not found_in_cart: cart_item = {'product_id': product_id, 'barcode': barcode, 'name': product_name, 'price_at_sale': selling_price, 'quantity': quantity}; cart.append(
                         cart_item); console.print(f">>> Sepete Eklendi: {product_name} ({quantity} adet)", style="green")

            elif choice.isdigit() and not choice == '0' and choice not in [str(i) for i in range(1, 51)]: # Menü no değilse barkod
                # ... (Barkod Okuma Kodu) ...
                console.print(f"Barkod ({choice}) aranıyor...", style="dim")
                try:
                    barcode_product = product_db_ops.get_product_by_barcode(
                        connection, choice, only_active=True)
                    if barcode_product:
                        p_id = barcode_product.get('product_id')
                        p_name = barcode_product.get('name'); p_price = barcode_product.get('selling_price'); p_stock = barcode_product.get(
                            'stock'); p_min_stock = barcode_product.get('min_stock_level', 2); stock_warning = ""; stock_style = "blue"
                        if p_stock is not None:
                            if p_stock < 0:
                                stock_warning = f" [bold white on red](EKSİ STOK: {p_stock})[/]"; stock_style = "bold white on red"
                            elif p_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"; stock_style = "bold red"
                            elif p_stock <= p_min_stock:
                                stock_warning = " [bold yellow](KRİTİK STOK!)[/]"; stock_style = "bold yellow"
                        console.print(
                            f">>> Ürün Bulundu: [cyan]{p_name}[/]{stock_warning}")
                        quantity = 0
                        while True:
                            prompt = f"'{p_name}' için Miktar (Stok: [{stock_style}]{p_stock if p_stock is not None else '?'}[/]{stock_warning}) [Varsayılan: 1]: "; quantity_str = input(
                                prompt).strip()
                            if not quantity_str:
                                quantity = 1; break
                            try: quantity_val = int(quantity_str);
                            if quantity_val > 0:
                                quantity = quantity_val; break
                            else: console.print(">>> HATA: Miktar 0'dan büyük olmalıdır.", style="red")
                            except ValueError:
                                console.print(
                                    ">>> HATA: Geçersiz sayı.", style="red")
                        if quantity > 0:
                            found = False
                            for item in cart:
                                if item['product_id'] == p_id:
                                    item['quantity'] += quantity; console.print(f">>> Miktar artırıldı: {p_name} - Yeni Miktar: {item['quantity']}", style="green"); found = True; break
                            if not found: cart_item = {'product_id': p_id, 'barcode': choice, 'name': p_name, 'price_at_sale': p_price, 'quantity': quantity}; cart.append(
                                cart_item); console.print(f">>> Sepete Eklendi: {p_name} ({quantity} adet)", style="green")
                    else:
                        console.print(
                            f">>> Barkod ({choice}) ile eşleşen aktif ürün bulunamadı.", style="yellow")
                except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Barkod Arama): {e}", style="bold red")
                except Exception as e:
                    console.print(
                        f">>> BEKLENMEDİK HATA (Barkod Arama): {e}", style="bold red")

            elif choice == '0': # Çıkış
                # ... (Çıkış Kodu) ...
                if cart:
                    if ui.get_yes_no_input(">>> Sepette ürün var. İptal edip çıkılsın mı?"):
                        console.print("\nSatış iptal edildi. Programdan çıkılıyor...", style="yellow"); break
                    else: console.print("Çıkış iptal edildi.", style="yellow"); continue
                else:
                    if active_shift_id:
                        console.print("[bold yellow]Uyarı: Aktif bir vardiyanız var. Çıkmadan önce bitirmeniz önerilir (V0).[/]")
                        if not ui.get_yes_no_input("Yine de çıkmak istiyor musunuz?"):
                            continue
                    console.print("\nProgramdan çıkılıyor...", style="bold"); break

            # --- MENÜ SEÇENEKLERİ ---
            elif choice == 'v1': # Vardiya Başlat
                started_shift_id = shift_handlers.handle_start_shift(connection, current_user_id)
                if started_shift_id: active_shift_id = started_shift_id
            elif choice == 'v0': # Vardiya Bitir
                shift_handlers.handle_end_shift(connection, current_user_id)
                check_shift = shift_db_ops.get_active_shift(connection, current_user_id)
                if not check_shift: active_shift_id = None
            elif choice == '1': # Sepete Ürün Ekle (Menüden)
                selected_product_info = find_and_select_product_for_cart(connection)
                if selected_product_info:
                    product_id = selected_product_info.get('product_id')
                    barcode = selected_product_info.get('barcode')
                    product_name = selected_product_info.get('name')
                    selling_price = selected_product_info.get('selling_price')
                    product_stock = selected_product_info.get('stock')
                    min_stock = selected_product_info.get('min_stock_level', 2)
                    stock_warning = ""
                    stock_style = "blue"
                    if product_stock is not None:
                        if product_stock < 0: stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"; stock_style="bold white on red"
                        elif product_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"; stock_style="bold red"
                        elif product_stock <= min_stock: stock_warning = " [bold yellow](KRİTİK STOK!)[/]"; stock_style="bold yellow"

                    quantity = 0
                    while True:
                        prompt = f"'{product_name}' için Miktar (Stok: [{stock_style}]{product_stock if product_stock is not None else '?'}[/]{stock_warning}) [Varsayılan: 1]: "
                        quantity_val = ui.get_positive_int_input(prompt, allow_zero=False)
                        if quantity_val > 0:
                            quantity = quantity_val
                            break

                    if quantity > 0:
                        found_in_cart = False
                        for item in cart:
                            if item['product_id'] == product_id:
                                item['quantity'] += quantity
                                console.print(f"\n>>> Miktar artırıldı: {product_name} - Yeni Miktar: {item['quantity']}", style="green")
                                found_in_cart = True
                                break
                        if not found_in_cart:
                            cart_item = {
                                'product_id': product_id, 'barcode': barcode, 'name': product_name,
                                'price_at_sale': selling_price, 'quantity': quantity
                            }
                            cart.append(cart_item)
                            console.print(f"\n>>> Sepete Eklendi: {product_name} ({quantity} adet)", style="green")
            elif choice == '2': # Sepeti Göster
                ui.display_cart(cart)
            elif choice == '3': # Sepetten Sil
                if not cart: console.print(">>> Sepet zaten boş.", style="yellow")
                else:
                    ui.display_cart(cart)
                    console.print("-" * 70, style="dim")
                    while True:
                        prompt = f"Silinecek No (1-{len(cart)}, İptal: 0): "
                        choice_to_remove = ui.get_positive_int_input(prompt, allow_zero=True)
                        if choice_to_remove == 0: console.print("İptal edildi.", style="yellow"); break
                        elif 1 <= choice_to_remove <= len(cart):
                            index_to_remove = choice_to_remove - 1
                            removed_item = cart.pop(index_to_remove)
                            console.print(f"\n>>> '{removed_item['name']}' silindi.", style="green")
                            break
                        else: console.print(f">>> Geçersiz numara!", style="red")
            elif choice == '4': # Sepeti Boşalt
                if not cart: console.print(">>> Sepet zaten boş.", style="yellow")
                else:
                    if ui.get_yes_no_input(">>> Sepet tamamen silinsin mi?"):
                        cart.clear()
                        console.print("\n>>> Sepet boşaltıldı.", style="green")
                    else: console.print("İptal edildi.", style="yellow")
            elif choice == '5': # Satışı Tamamla
                 if not cart: console.print(">>> Sepet boş. Tamamlanacak satış yok.", style="yellow")
                 elif active_shift_id is None: console.print("[bold red]HATA: Satışı tamamlamak için önce vardiya başlatmalısınız (V1).[/]")
                 else: # Satış tamamlama mantığı
                     sale_subtotal = ui.display_cart(cart)
                     console.print("-" * 70, style="dim")
                     selected_customer_id, selected_customer_name = _handle_customer_selection_for_sale(connection, "Satış yapılacak Müşteri Adı veya Telefon No: ")
                     discount_amount_applied = Decimal('0.00')
                     applied_coupon_id = None
                     applied_coupon_code = None
                     available_coupons = []
                     if selected_customer_id:
                         try:
                             available_coupons = customer_db_ops.get_customer_available_coupons(connection, selected_customer_id)
                         except DatabaseError as e: console.print(f"[yellow]Uyarı: Müşteri kuponları alınırken hata: {e}[/]")

                     if discount_amount_applied == Decimal('0.00') and not available_coupons:
                          console.print("[dim]Uygulanacak indirim veya kullanılabilir kupon yok.[/dim]")
                     elif ui.get_yes_no_input("\nİndirim veya Kupon uygulamak ister misiniz?"):
                         while True:
                             console.print("\nİndirim/Kupon Seçenekleri:\n [M]anuel İndirim (Tutar veya Yüzde)")
                             if available_coupons: console.print(" [K]ullanılabilir Kupon Seç")
                             console.print(" [V]azgeç")
                             discount_choice = input("Seçiminiz (M/K/V): ").strip().upper()
                             if discount_choice == 'M':
                                 console.print("İndirim Türü: [T]utar (TL) / [Y]üzde (%) ? ", end="")
                                 type_choice = input().strip().upper()
                                 if type_choice == 'T':
                                     discount_value = ui.get_positive_decimal_input("İndirim Tutarı (TL): ", allow_zero=False)
                                     if discount_value is not None and discount_value >= sale_subtotal:
                                         console.print(f"[bold red]HATA: İndirim tutarı ({discount_value:.2f} TL) sepet toplamından ({sale_subtotal:.2f} TL) büyük veya eşit olamaz.[/]")
                                         continue
                                     if discount_value is not None:
                                         discount_amount_applied = discount_value
                                         applied_coupon_id = None; applied_coupon_code = None
                                         console.print(f"[green]Manuel Tutar İndirimi ({discount_amount_applied:.2f} TL) uygulandı.[/]")
                                         break
                                 elif type_choice == 'Y':
                                     discount_percent = ui.get_positive_decimal_input("İndirim Yüzdesi (%): ", allow_zero=False)
                                     if discount_percent is not None and discount_percent >= 100:
                                         console.print("[bold red]HATA: İndirim yüzdesi 100'den küçük olmalıdır.[/]")
                                         continue
                                     if discount_percent is not None:
                                         discount_amount_applied = (sale_subtotal * (discount_percent / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                                         applied_coupon_id = None; applied_coupon_code = None
                                         console.print(f"[green]Manuel Yüzde İndirimi (%{discount_percent:.0f} -> {discount_amount_applied:.2f} TL) uygulandı.[/]")
                                         break
                                 else: console.print("[red]Geçersiz indirim türü (T veya Y).[/]"); continue
                             elif discount_choice == 'K' and available_coupons:
                                 ui.display_customer_coupons(available_coupons, selected_customer_name)
                                 while True:
                                     coupon_num_str = input(f"Kullanılacak Kupon No (1-{len(available_coupons)}, İptal: 0): ").strip()
                                     if coupon_num_str == '0': console.print("[yellow]Kupon seçimi iptal edildi.[/]"); break
                                     if coupon_num_str.isdigit():
                                         coupon_num = int(coupon_num_str)
                                         if 1 <= coupon_num <= len(available_coupons):
                                             selected_coupon = available_coupons[coupon_num - 1]
                                             min_purchase = selected_coupon.get('min_purchase_amount', Decimal('0.00'))
                                             if sale_subtotal < min_purchase:
                                                 console.print(f"[bold red]HATA: Bu kuponu kullanmak için minimum {min_purchase:.2f} TL harcama gereklidir (Sepet Toplamı: {sale_subtotal:.2f} TL).[/]"); continue
                                             coupon_discount_type = selected_coupon.get('discount_type')
                                             coupon_discount_value = selected_coupon.get('discount_value')
                                             temp_discount = Decimal('0.00')
                                             if coupon_discount_type == 'fixed_amount': temp_discount = coupon_discount_value
                                             elif coupon_discount_type == 'percentage': temp_discount = (sale_subtotal * (coupon_discount_value / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                                             if temp_discount >= sale_subtotal:
                                                 console.print(f"[bold red]HATA: Kupon indirimi ({temp_discount:.2f} TL) sepet toplamından ({sale_subtotal:.2f} TL) büyük veya eşit olamaz.[/]"); continue

                                             discount_amount_applied = temp_discount
                                             applied_coupon_id = selected_coupon.get('customer_coupon_id')
                                             applied_coupon_code = selected_coupon.get('coupon_code')
                                             console.print(f"[green]Kupon '{applied_coupon_code}' ({discount_amount_applied:.2f} TL İndirim) uygulandı.[/]")
                                             break # Kupon seçimi başarılı, iç döngüden çık
                                         else: console.print("[red]Geçersiz kupon numarası.[/]")
                                     else: console.print("[red]Lütfen geçerli bir numara girin.[/]")
                                 if applied_coupon_id: break # İndirim/Kupon seçim döngüsünden çık
                             elif discount_choice == 'V':
                                 console.print("[yellow]İndirim/Kupon uygulanmadı.[/]")
                                 discount_amount_applied = Decimal('0.00')
                                 applied_coupon_id = None; applied_coupon_code = None
                                 break
                             else: console.print("[red]Geçersiz seçim (M, K veya V).[/]")
                     else: # İndirim/Kupon sorma sorusuna Hayır dendi
                          discount_amount_applied = Decimal('0.00')
                          applied_coupon_id = None; applied_coupon_code = None

                     # Otomatik Promosyon Kontrolü
                     applied_promotion_id = None
                     total_promotion_discount = Decimal('0.00')
                     applied_promotion_name = None
                     free_items_for_stock = [] # Bedava verilen ürünlerin stoktan düşülmesi için
                     applied_promos_summary = [] # Kullanıcıya gösterilecek özet
                     processed_product_ids_for_promo = set() # Bir ürün için sadece en iyi bir promosyonu uygula

                     try:
                         for item_index, item in enumerate(cart):
                             product_id = item['product_id']
                             if product_id in processed_product_ids_for_promo: continue # Bu ürün için zaten promosyon uygulandıysa atla

                             quantity_in_cart = item['quantity']
                             price_at_sale = item['price_at_sale']
                             active_promos = promo_db_ops.get_active_promotions_for_product(connection, product_id)
                             best_promo_found = None
                             best_promo_discount_value = Decimal('-1.00') # En iyi indirimi bulmak için

                             for promo in active_promos:
                                 promo_type = promo['promotion_type']
                                 current_promo_discount_value = Decimal('0.00')
                                 applies = False

                                 if promo_type == 'quantity_discount':
                                     if quantity_in_cart >= promo['required_quantity']:
                                         current_promo_discount_value = promo['discount_amount']
                                         applies = True
                                 elif promo_type in ['bogo', 'buy_x_get_y_free']:
                                     req_qty = promo.get('required_bogo_quantity', 1)
                                     if quantity_in_cart >= req_qty:
                                         free_qty_per_promo = promo['free_quantity']
                                         num_promotions = quantity_in_cart // req_qty
                                         total_free_qty = num_promotions * free_qty_per_promo
                                         if total_free_qty > 0:
                                             free_prod_id_for_price = promo.get('free_product_id') or product_id
                                             # Bedava ürünün fiyatını al (stok düşme ve indirim hesaplama için)
                                             free_item_price = price_at_sale # Varsayılan (aynı ürünse)
                                             if free_prod_id_for_price != product_id:
                                                  try:
                                                      free_prod_data = product_db_ops.get_product_by_id(connection, free_prod_id_for_price)
                                                      if free_prod_data: free_item_price = free_prod_data.get('selling_price', Decimal('0.00'))
                                                      else: free_item_price = Decimal('0.00') # Fiyat alınamazsa
                                                  except: free_item_price = Decimal('0.00') # Hata olursa
                                             current_promo_discount_value = total_free_qty * free_item_price
                                             applies = True

                                 # Bu promosyon uygulanabiliyorsa ve öncekinden daha iyiyse seç
                                 if applies and current_promo_discount_value > best_promo_discount_value:
                                     best_promo_discount_value = current_promo_discount_value
                                     best_promo_found = promo

                             # En iyi promosyon bulunduysa uygula
                             if best_promo_found:
                                 processed_product_ids_for_promo.add(product_id) # Bu ürünü işlendi olarak işaretle
                                 current_promo_id = best_promo_found['promotion_id']
                                 current_promo_name = best_promo_found['name']
                                 promo_type = best_promo_found['promotion_type']
                                 current_promo_discount = Decimal('0.00')
                                 promo_summary_text = f"Promosyon: {current_promo_name} ({promo_type}) - Ürün: {item['name']}"

                                 if promo_type == 'quantity_discount':
                                     current_promo_discount = best_promo_found['discount_amount']
                                     promo_summary_text += f" ({best_promo_found['required_quantity']} adet alındı, {current_promo_discount:.2f} TL İndirim)"
                                 elif promo_type in ['bogo', 'buy_x_get_y_free']:
                                     free_qty_per_promo = best_promo_found['free_quantity']
                                     req_qty = best_promo_found.get('required_bogo_quantity', 1)
                                     num_promotions = quantity_in_cart // req_qty
                                     total_free_qty = num_promotions * free_qty_per_promo
                                     free_prod_id = best_promo_found.get('free_product_id') or product_id

                                     if total_free_qty > 0:
                                         # İndirim hesaplaması için fiyatı tekrar al (yukarıda yapıldı)
                                         free_item_price = price_at_sale
                                         if free_prod_id != product_id:
                                              try:
                                                  free_prod_data = product_db_ops.get_product_by_id(connection, free_prod_id)
                                                  if free_prod_data: free_item_price = free_prod_data.get('selling_price', Decimal('0.00'))
                                                  else: free_item_price = Decimal('0.00')
                                              except: free_item_price = Decimal('0.00')

                                         current_promo_discount = total_free_qty * free_item_price
                                         # Stoktan düşülecek bedava ürünleri listeye ekle
                                         found_free = False
                                         for free_stock_item in free_items_for_stock:
                                             if free_stock_item['product_id'] == free_prod_id:
                                                 free_stock_item['quantity'] += total_free_qty
                                                 found_free = True; break
                                         if not found_free:
                                             free_items_for_stock.append({'product_id': free_prod_id, 'quantity': total_free_qty})

                                         # Bedava ürünün adını al (varsa)
                                         free_prod_name_display = "(Aynı Ürün)"
                                         if free_prod_id != product_id:
                                              try:
                                                   free_prod_data_name = product_db_ops.get_product_by_id(connection, free_prod_id)
                                                   if free_prod_data_name: free_prod_name_display = free_prod_data_name.get('name', f'ID:{free_prod_id}')
                                                   else: free_prod_name_display = f'ID:{free_prod_id}'
                                              except: free_prod_name_display = f'ID:{free_prod_id}'

                                         promo_summary_text += f" ({req_qty} adet alındı, {total_free_qty} adet {free_prod_name_display} Bedava - İndirim Karşılığı: {current_promo_discount:.2f} TL)"
                                     else: # Koşul sağlandı ama bedava ürün yoksa (miktar 0 ise)
                                         promo_summary_text += " (Koşul sağlandı ancak bedava ürün miktarı 0)"
                                         current_promo_id = None # Uygulanmış sayma
                                         current_promo_name = None

                                 # Toplam promosyon indirimini ve özeti güncelle
                                 if current_promo_discount > 0:
                                     total_promotion_discount += current_promo_discount
                                     applied_promos_summary.append(promo_summary_text)
                                     # Son uygulanan promosyonun ID ve adını sakla (fişte göstermek için basit yaklaşım)
                                     applied_promotion_id = current_promo_id
                                     applied_promotion_name = current_promo_name

                     except DatabaseError as e: console.print(f"[yellow]Uyarı: Otomatik promosyon kontrolü sırasında veritabanı hatası: {e}[/]")
                     except Exception as e: console.print(f"[yellow]Uyarı: Otomatik promosyon kontrolü sırasında beklenmedik hata: {e}[/]")

                     # Uygulanan promosyonları göster
                     if applied_promos_summary:
                         console.print(f"\n[bold green]>>> Otomatik Promosyon(lar) Uygulandı:[/]");
                     for summary in applied_promos_summary: console.print(f"   -> {summary}")

                     # Ödeme Al
                     payments_list, total_paid_input = ui.collect_payments(sale_subtotal, PAYMENT_METHODS, selected_customer_id, discount_amount_applied, total_promotion_discount)

                     if payments_list is not None: # Ödeme iptal edilmediyse
                         final_total_after_discount = sale_subtotal - discount_amount_applied - total_promotion_discount
                         if final_total_after_discount < Decimal('0.00'): final_total_after_discount = Decimal('0.00')

                         change_due = total_paid_input - final_total_after_discount
                         if change_due < Decimal('0.00'): change_due = Decimal('0.00') # Para üstü negatif olamaz

                         console.print("\nSatış veritabanına kaydediliyor...", style="italic")
                         try:
                             # Satışı kaydet
                             saved_sale_id = sale_db_ops.finalize_sale(
                                 connection=connection,
                                 cart=cart,
                                 sale_subtotal=sale_subtotal,
                                 customer_id=selected_customer_id,
                                 payments=payments_list,
                                 applied_coupon_id=applied_coupon_id,
                                 discount_amount=discount_amount_applied,
                                 applied_promotion_id=applied_promotion_id,
                                 promotion_discount=total_promotion_discount,
                                 free_items_for_stock=free_items_for_stock, # Bedava ürünleri gönder
                                 shift_id=active_shift_id,
                                 user_id=current_user_id
                             )
                             if saved_sale_id:
                                 if change_due > Decimal('0.00'):
                                     console.print(f"\n>>> Para Üstü: [bold green]{change_due:.2f} TL[/]")
                                 # Fişi yazdır
                                 ui.print_receipt(cart, sale_subtotal, payments_list, total_paid_input, change_due, STORE_NAME, selected_customer_name, discount_amount_applied, applied_coupon_code, total_promotion_discount, applied_promotion_name)
                                 cart.clear() # Sepeti temizle
                                 console.print(f"\n[bold green]Satış (ID: {saved_sale_id}) başarıyla tamamlandı.[/]")
                             else: # finalize_sale None döndürdüyse (hata oluştuysa)
                                 console.print(">>> Satış kaydedilemedi. Sepet korundu.", style="bold red")
                         except Exception as finalize_error:
                             console.print(f"\n>>> SATIŞ KAYDI HATASI: {finalize_error}", style="bold red")
                             console.print("[yellow]Sepet korundu.[/]")
            elif choice == '6': # Satış İptali / İade
                 if user_role in TUM_KULLANICILAR: # Kasiyer ve üstü
                     console.print("\n--- Satış İptali / İade ---", style="bold blue")
                     try:
                         sale_id_to_return = ui.get_positive_int_input("İptal/İade edilecek Satış Fişi Numarası (ID): ", allow_zero=False)
                         sale_details = sale_db_ops.get_sale_details_for_return(connection, sale_id_to_return)
                         if sale_details is None: pass # Hata mesajı DB fonksiyonunda verildi
                         else:
                             ui.display_sale_details_for_confirmation(sale_details)
                             if ui.get_yes_no_input(f"\n>>> Satış ID {sale_id_to_return} iade edilsin mi? (Stoklar geri alınacak, bakiye güncellenecek)"):
                                 reason = input("İade Sebebi (isteğe bağlı): ").strip() or None
                                 notes = input("İade Notları (isteğe bağlı): ").strip() or None
                                 return_id = sale_db_ops.process_sale_return(connection, sale_id_to_return, sale_details, reason, notes, current_user_id)
                                 # Başarı/hata mesajı DB fonksiyonunda veriliyor
                             else: console.print("İade işlemi iptal edildi.", style="yellow")
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Satış İadesi): {e}", style="bold red")
                     except ValueError as ve: console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Satış İadesi): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '7': # Fiyat Sorgula
                 product_handlers.handle_price_check(connection)
            elif choice == '8': # Satışı Askıya Al
                 if not cart: console.print(">>> Askıya alınacak ürün sepeti boş.", style="yellow")
                 else:
                     if ui.get_yes_no_input("Mevcut sepet askıya alınsın mı?"):
                         suspend_id = suspended_sale_id_counter
                         suspended_sales[suspend_id] = cart[:] # Sepetin kopyasını sakla
                         suspended_sale_id_counter += 1
                         cart.clear() # Mevcut sepeti temizle
                         console.print(f"\n[green]>>> Satış [bold cyan]ID {suspend_id}[/] ile askıya alındı.[/]")
                     else: console.print("Askıya alma işlemi iptal edildi.", style="yellow")
            elif choice == '9': # Askıdaki Satışı Çağır
                 if not suspended_sales: console.print(">>> Askıda bekleyen satış bulunmamaktadır.", style="yellow")
                 else:
                     if ui.display_suspended_sales_list(suspended_sales):
                         while True:
                             recall_id_str = input("Çağrılacak Askı ID'sini girin (İptal için 0): ").strip()
                             if recall_id_str == '0': console.print("İşlem iptal edildi.", style="yellow"); break
                             if recall_id_str.isdigit():
                                 recall_id = int(recall_id_str)
                                 if recall_id in suspended_sales:
                                     if cart: # Mevcut sepette ürün varsa uyar
                                         if not ui.get_yes_no_input(f">>> Mevcut sepette {len(cart)} ürün var. Bu sepet silinip askıdaki (ID: {recall_id}) satış çağrılsın mı?"):
                                             console.print("Askıdaki satışı çağırma iptal edildi.", style="yellow")
                                             break # İç döngüden çık
                                     # Mevcut sepeti temizle ve askıdakini yükle
                                     cart = suspended_sales.pop(recall_id)
                                     console.print(f"\n[green]>>> Askıdaki Satış (ID: {recall_id}) geri çağrıldı.[/]")
                                     ui.display_cart(cart) # Yeni sepeti göster
                                     break # İç döngüden çık
                                 else: console.print(f">>> Geçersiz Askı ID: {recall_id}", style="red")
                             else: console.print(">>> Lütfen geçerli bir ID girin.", style="red")
            # --- Müşteri İşlemleri ---
            elif choice == '10': customer_handlers.handle_add_customer(connection, current_user_id)
            elif choice == '11': # Müşteri Listele
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_list_customers(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '12': # Müşteri Güncelle
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_update_customer(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '13': # Müşteri Ödeme Al
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_customer_payment(connection, active_shift_id, current_user_id, CUSTOMER_PAYMENT_METHODS)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '14': # Hesap Ekstresi
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_customer_ledger(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '15': # Kupon Görüntüle
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_view_customer_coupons(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '16': # Müşteri Durum
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_toggle_customer_status(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Ürün İşlemleri ---
            elif choice == '17': # Yeni Ürün
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_add_product(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '18': # Ürün Listele
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_list_products(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '19': # Ürün Güncelle
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_update_product(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '20': # Stok Girişi
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_stock_input(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '21': # Stok Düzeltme
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_stock_adjustment(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '22': # Ürün Durum
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_toggle_product_status(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '23': # Etiket Yazdır
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_print_shelf_label(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '24': # CSV Export
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_export_products(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '25': # CSV Import
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_import_products(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Marka İşlemleri ---
            elif choice == '26': # Yeni Marka
                 if user_role in YONETICI_VE_USTU: brand_handlers.handle_add_brand(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '27': # Marka Listele
                 if user_role in YONETICI_VE_USTU: brand_handlers.handle_list_brands(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '28': # Marka Durum
                 if user_role in YONETICI_VE_USTU: brand_handlers.handle_toggle_brand_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Kategori İşlemleri ---
            elif choice == '29': # Yeni Kategori
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_add_category(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '30': # Kategori Listele
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_list_categories(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '31': # Kategori Güncelle
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_update_category(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '32': # Kategori Durum
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_toggle_category_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Promosyon İşlemleri ---
            elif choice == '33': # Yeni Promosyon
                 if user_role in YONETICI_VE_USTU: promo_handlers.handle_add_promotion(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '34': # Promosyon Listele
                 if user_role in YONETICI_VE_USTU: promo_handlers.handle_list_promotions(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '35': # Promosyon Durum
                 if user_role in YONETICI_VE_USTU: promo_handlers.handle_toggle_promotion_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Tedarikçi İşlemleri ---
            elif choice == '36': # Yeni Tedarikçi
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_add_supplier(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '37': # Tedarikçi Listele
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_list_suppliers(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '38': # Tedarikçi Güncelle
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_update_supplier(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '39': # Tedarikçi Durum
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_toggle_supplier_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Raporlar ---
            elif choice == '40': # Günlük Satış
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- Günlük Satış Özeti Raporu ---", style="bold blue")
                     try:
                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             summary_data = sale_db_ops.get_daily_sales_summary(connection, start_date, end_date)
                             ui.display_daily_sales_summary(summary_data, start_date, end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Günlük Özet): {e}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Günlük Özet): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '41': # En Çok Satan (Adet)
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- En Çok Satan Ürünler (Adet) ---", style="bold blue")
                     try:
                         limit_prompt = f"Listelenecek ürün sayısı [Varsayılan: {DEFAULT_REPORT_LIMIT}]: "
                         limit_str = input(limit_prompt).strip()
                         limit = DEFAULT_REPORT_LIMIT # Varsayılanı ata
                         if limit_str.isdigit() and int(limit_str) > 0:
                             limit = int(limit_str) # Kullanıcı girdiyse onu kullan

                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             report_data = sale_db_ops.get_top_selling_products_by_quantity(connection, limit, start_date, end_date)
                             ui.display_top_products_report(report_data, report_type="quantity", limit=limit, start_date=start_date, end_date=end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Rapor): {e}", style="bold red")
                     except ValueError: console.print(">>> HATA: Geçersiz limit değeri.", style="red") # Sayısal olmayan girdi için
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Rapor): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '42': # En Çok Ciro Yapanlar
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- En Çok Ciro Yapan Ürünler ---", style="bold blue")
                     try:
                         limit_prompt = f"Listelenecek ürün sayısı [Varsayılan: {DEFAULT_REPORT_LIMIT}]: "
                         limit_str = input(limit_prompt).strip()
                         limit = DEFAULT_REPORT_LIMIT
                         if limit_str.isdigit() and int(limit_str) > 0:
                             limit = int(limit_str)

                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             report_data = sale_db_ops.get_top_selling_products_by_value(connection, limit, start_date, end_date)
                             ui.display_top_products_report(report_data, report_type="value", limit=limit, start_date=start_date, end_date=end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Rapor): {e}", style="bold red")
                     except ValueError: console.print(">>> HATA: Geçersiz limit değeri.", style="red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Rapor): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '43': # Stok Raporu
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- Stok Raporu ---", style="bold blue")
                     try:
                         include_inactive = ui.get_yes_no_input("Pasif ürünler de dahil edilsin mi?")
                         filter_choice = 0
                         console.print("Stok Filtreleme Seçenekleri:\n [1] Tümünü Göster\n [2] Sadece Stoğu Kritik Seviyede Olanlar (Min. Stok Altı)\n [3] Stoğu Belirli Bir Seviyenin Altında Olanlar")
                         while True:
                             f_choice = input("Filtre seçin (1-3) [Varsayılan: 1]: ").strip()
                             if not f_choice: filter_choice = 1; break
                             if f_choice.isdigit() and 1 <= int(f_choice) <= 3: filter_choice = int(f_choice); break
                             else: console.print(">>> Geçersiz seçim (1, 2 veya 3 girin).", style="red")
                         stock_threshold = None
                         only_critical = False
                         if filter_choice == 2: only_critical = True
                         elif filter_choice == 3: stock_threshold = ui.get_positive_int_input("Stok eşiği (bu değer ve altı gösterilecek): ", allow_zero=True)

                         stock_data = product_db_ops.get_stock_report_data(connection, stock_threshold, include_inactive, only_critical)
                         ui.display_stock_report(stock_data, stock_threshold, include_inactive, only_critical)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Stok Raporu): {e}", style="bold red")
                     except ValueError as ve: console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Stok Raporu): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '44': # Kâr/Zarar
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- Kâr/Zarar Raporu (Tahmini) ---", style="bold blue")
                     try:
                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             report_data = sale_db_ops.get_profit_loss_report_data(connection, start_date, end_date)
                             ui.display_profit_loss_report(report_data, start_date, end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Kâr/Zarar Raporu): {e}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Kâr/Zarar Raporu): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '45': # SKT Raporu
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- SKT Raporu ---", style="bold red")
                     try:
                         days = ui.get_positive_int_input("Kaç gün sonrasına kadar olan SKT'ler listelensin? (örn: 30): ", allow_zero=True)
                         report_data = sale_db_ops.get_expiry_report_data(connection, days)
                         ui.display_expiry_report(report_data, days)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (SKT Raporu): {e}", style="bold red")
                     except ValueError as ve: console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (SKT Raporu): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Hesap İşlemleri ---
            elif choice == '46': # Şifre Değiştir
                 user_handlers.handle_change_password(connection, logged_in_user)
            # --- Yönetim ---
            elif choice == '47': # Yeni Kullanıcı
                 if user_role == 'admin': user_handlers.handle_add_user(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '48': # Kullanıcı Listele
                 if user_role == 'admin': user_handlers.handle_list_users(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '49': # Kullanıcı Güncelle
                 if user_role == 'admin': user_handlers.handle_update_user(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '50': # Kullanıcı Durum
                 if user_role == 'admin': user_handlers.handle_toggle_user_status(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Geçersiz Seçim ---
            else:
                console.print("\n>>> Geçersiz seçim veya barkod!", style="bold red")

            # İşlem sonrası bekleme (isteğe bağlı)
            # input("\nDevam etmek için Enter'a basın...") # Her adımdan sonra bekletir
            ui.pause_and_clear(bekle=False, sure=0.5) # Kısa bir bekleme yapıp temizle

        except KeyboardInterrupt:
            console.print("\n>>> Ctrl+C algılandı. Programdan çıkılıyor...", style="bold yellow")
            break
        except DatabaseError as db_err:
            console.print(f"\n>>> BEKLENMEDİK VERİTABANI HATASI: {db_err}", style="bold red")
            input("Devam etmek için Enter'a basın...")
        except Exception as main_loop_error:
            console.print("\n>>> BEKLENMEDİK PROGRAM HATASI!", style="bold red")
            console.print_exception(show_locals=False) # Hata detayını göster
            input("Devam etmek için Enter'a basın...")

    # Program Sonu
    print("DEBUG: Ana döngüden çıkıldı.") # DEBUG
    if connection and connection.is_connected():
        try:
            connection.close()
            print("DEBUG: Veritabanı bağlantısı başarıyla kapatıldı.") # DEBUG
        except Error as e:
            print(f"DEBUG: Veritabanı kapatılırken hata: {e}") # DEBUG
            console.print(f"Veritabanı kapatılırken hata: {e}", style="red")
    print("DEBUG: Program sonlandırılıyor.") # DEBUG


# === Programın Başlangıç Noktası ===
if __name__ == "__main__":
    print("DEBUG: Program __main__ bloğundan başlatılıyor.") # DEBUG
    try:
        main()
    except ImportError as imp_err:
        print(f"\n!!! KRİTİK HATA: Gerekli bir kütüphane bulunamadı: {imp_err}")
        missing_module = str(imp_err).split("'")[-2]
        if missing_module in ['db_config', 'urun_veritabani', 'urun_islemleri', 'musteri_veritabani', 'musteri_islemleri', 'tedarikci_veritabani', 'tedarikci_islemleri', 'kullanici_veritabani', 'kullanici_islemleri', 'kategori_veritabani', 'kategori_islemleri', 'marka_veritabani', 'marka_islemleri', 'promosyon_veritabani', 'promosyon_islemleri', 'vardiya_veritabani', 'vardiya_islemleri', 'loglama', 'veri_aktarim', 'yazdirma_islemleri', 'arayuz_girdi', 'arayuz_gosterim', 'arayuz_yardimcilari', 'hatalar']:
             print(f">>> '{missing_module}.py' dosyasının veya ilgili modülün proje klasöründe olduğundan emin olun.")
        elif 'getpass' in str(imp_err): print(">>> 'getpass' modülü standart Python ile gelir, kurulumda bir sorun olabilir.")
        else: print(">>> Lütfen 'pip install mysql-connector-python rich bcrypt' komutunu çalıştırın.")
    except Exception as final_error:
        print("\n>>> PROGRAMDA ÖNGÖRÜLEMEYEN KRİTİK HATA!")
        print(f"Hata Detayı: {final_error}")
        import traceback
        traceback.print_exc()
    finally:
        print("DEBUG: Program sonu.") # En sona bir debug mesajı

                    elif product_stock <= min_stock:
                         stock_warning = " [bold yellow](KRİTİK STOK!)[/]"; stock_style = "bold yellow" quantity = 0
                while True:
                     prompt = f"'{product_name}' için Miktar (Stok: [{stock_style}]{product_stock if product_stock is not None else '?'}[/]{stock_warning}) [Varsayılan: 1]: "
                     quantity_str = input(prompt).strip()
                     if not quantity_str:
                         quantity = 1; break
                 try: quantity_val = int(quantity_str);
                    if quantity_val > 0:
                         quantity = quantity_val; break
                    else: console.print(">>> HATA: Miktar 0'dan büyük olmalıdır.", style="red")
                 except ValueError:
                         console.print(">>> HATA: Geçersiz sayı.", style="red")
                    if quantity > 0:
                     found_in_cart = False
                     for item in cart:
                         if item['product_id'] == product_id:
                             item['quantity'] += quantity; console.print(f">>> Miktar artırıldı: {product_name} - Yeni Miktar: {item['quantity']}", style="green"); found_in_cart = True; break
                     if not found_in_cart: cart_item = {'product_id': product_id, 'barcode': barcode, 'name': product_name, 'price_at_sale': selling_price, 'quantity': quantity}; cart.append(
                         cart_item); console.print(f">>> Sepete Eklendi: {product_name} ({quantity} adet)", style="green")

            elif choice.isdigit() and not choice == '0' and choice not in [str(i) for i in range(1, 51)]: # Menü no değilse barkod
                # ... (Barkod Okuma Kodu - Değişiklik Yok) ...
                console.print(f"Barkod ({choice}) aranıyor...", style="dim")
                try:
                    barcode_product = product_db_ops.get_product_by_barcode(
                        connection, choice, only_active=True)
                    if barcode_product:
                        p_id = barcode_product.get('product_id')
                        p_name = barcode_product.get('name'); p_price = barcode_product.get('selling_price'); p_stock = barcode_product.get(
                            'stock'); p_min_stock = barcode_product.get('min_stock_level', 2); stock_warning = ""; stock_style = "blue"
                        if p_stock is not None:
                            if p_stock < 0:
                                stock_warning = f" [bold white on red](EKSİ STOK: {p_stock})[/]"; stock_style = "bold white on red"
                            elif p_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"; stock_style = "bold red"
                            elif p_stock <= p_min_stock:
                                stock_warning = " [bold yellow](KRİTİK STOK!)[/]"; stock_style = "bold yellow"
                        console.print(
                            f">>> Ürün Bulundu: [cyan]{p_name}[/]{stock_warning}")
                        quantity = 0
                        while True:
                            prompt = f"'{p_name}' için Miktar (Stok: [{stock_style}]{p_stock if p_stock is not None else '?'}[/]{stock_warning}) [Varsayılan: 1]: "; quantity_str = input(
                                prompt).strip()
                            if not quantity_str:
                                quantity = 1; break
                            try: quantity_val = int(quantity_str);
                            if quantity_val > 0:
                                quantity = quantity_val; break
                            else: console.print(">>> HATA: Miktar 0'dan büyük olmalıdır.", style="red")
                            except ValueError:
                                console.print(
                                    ">>> HATA: Geçersiz sayı.", style="red")
                        if quantity > 0:
                            found = False
                            for item in cart:
                                if item['product_id'] == p_id:
                                    item['quantity'] += quantity; console.print(f">>> Miktar artırıldı: {p_name} - Yeni Miktar: {item['quantity']}", style="green"); found = True; break
                            if not found: cart_item = {'product_id': p_id, 'barcode': choice, 'name': p_name, 'price_at_sale': p_price, 'quantity': quantity}; cart.append(
                                cart_item); console.print(f">>> Sepete Eklendi: {p_name} ({quantity} adet)", style="green")
                    else:
                        console.print(
                            f">>> Barkod ({choice}) ile eşleşen aktif ürün bulunamadı.", style="yellow")
                except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Barkod Arama): {e}", style="bold red")
                except Exception as e:
                    console.print(
                        f">>> BEKLENMEDİK HATA (Barkod Arama): {e}", style="bold red")

            elif choice == '0': # Çıkış
                # ... (Çıkış Kodu - Değişiklik Yok) ...
                if cart:
                    if ui.get_yes_no_input(">>> Sepette ürün var. İptal edip çıkılsın mı?"):
                        console.print("\nSatış iptal edildi. Programdan çıkılıyor...", style="yellow"); break
                    else: console.print("Çıkış iptal edildi.", style="yellow"); continue
                else:
                    if active_shift_id:
                        console.print("[bold yellow]Uyarı: Aktif bir vardiyanız var. Çıkmadan önce bitirmeniz önerilir (V0).[/]")
                        if not ui.get_yes_no_input("Yine de çıkmak istiyor musunuz?"):
                            continue
                    console.print("\nProgramdan çıkılıyor...", style="bold"); break

            # --- MENÜ SEÇENEKLERİ ---
            # ... (Diğer menü seçenekleri ve yetki kontrolleri aynı kalır) ...
            elif choice == 'v1': # Vardiya Başlat
                started_shift_id = shift_handlers.handle_start_shift(connection, current_user_id)
                if started_shift_id: active_shift_id = started_shift_id
            elif choice == 'v0': # Vardiya Bitir
                shift_handlers.handle_end_shift(connection, current_user_id)
                # Vardiyanın bittiğini doğrula
                check_shift = shift_db_ops.get_active_shift(connection, current_user_id)
                if not check_shift: active_shift_id = None
            elif choice == '1': # Sepete Ürün Ekle (Menüden)
                selected_product_info = find_and_select_product_for_cart(connection)
                if selected_product_info:
                    product_id = selected_product_info.get('product_id')
                    barcode = selected_product_info.get('barcode')
                    product_name = selected_product_info.get('name')
                    selling_price = selected_product_info.get('selling_price')
                    product_stock = selected_product_info.get('stock')
                    min_stock = selected_product_info.get('min_stock_level', 2)
                    stock_warning = ""
                    stock_style = "blue"
                    if product_stock is not None:
                        if product_stock < 0: stock_warning = f" [bold white on red](EKSİ STOK: {product_stock})[/]"; stock_style="bold white on red"
                        elif product_stock == 0: stock_warning = " [bold red](STOK 0!)[/]"; stock_style="bold red"
                        elif product_stock <= min_stock: stock_warning = " [bold yellow](KRİTİK STOK!)[/]"; stock_style="bold yellow"

                    quantity = 0
                    while True:
                        prompt = f"'{product_name}' için Miktar (Stok: [{stock_style}]{product_stock if product_stock is not None else '?'}[/]{stock_warning}) [Varsayılan: 1]: "
                        # Miktarı doğrudan ui.get_positive_int_input ile isteyelim
                        quantity_val = ui.get_positive_int_input(prompt, allow_zero=False) # 0'a izin verme
                        if quantity_val > 0:
                            quantity = quantity_val
                            break
                        # else: get_positive_int_input zaten hata verir

                    if quantity > 0:
                        found_in_cart = False
                        for item in cart:
                            if item['product_id'] == product_id:
                                item['quantity'] += quantity
                                console.print(f"\n>>> Miktar artırıldı: {product_name} - Yeni Miktar: {item['quantity']}", style="green")
                                found_in_cart = True
                                break
                        if not found_in_cart:
                            cart_item = {
                                'product_id': product_id, 'barcode': barcode, 'name': product_name,
                                'price_at_sale': selling_price, 'quantity': quantity
                            }
                            cart.append(cart_item)
                            console.print(f"\n>>> Sepete Eklendi: {product_name} ({quantity} adet)", style="green")
            elif choice == '2': # Sepeti Göster
                ui.display_cart(cart)
            elif choice == '3': # Sepetten Sil
                if not cart: console.print(">>> Sepet zaten boş.", style="yellow")
                else:
                    ui.display_cart(cart)
                    console.print("-" * 70, style="dim")
                    while True:
                        prompt = f"Silinecek No (1-{len(cart)}, İptal: 0): "
                        choice_to_remove = ui.get_positive_int_input(prompt, allow_zero=True)
                        if choice_to_remove == 0: console.print("İptal edildi.", style="yellow"); break
                        elif 1 <= choice_to_remove <= len(cart):
                            index_to_remove = choice_to_remove - 1
                            removed_item = cart.pop(index_to_remove)
                            console.print(f"\n>>> '{removed_item['name']}' silindi.", style="green")
                            break
                        else: console.print(f">>> Geçersiz numara!", style="red")
            elif choice == '4': # Sepeti Boşalt
                if not cart: console.print(">>> Sepet zaten boş.", style="yellow")
                else:
                    if ui.get_yes_no_input(">>> Sepet tamamen silinsin mi?"):
                        cart.clear()
                        console.print("\n>>> Sepet boşaltıldı.", style="green")
                    else: console.print("İptal edildi.", style="yellow")
            elif choice == '5': # Satışı Tamamla
                 if not cart: console.print(">>> Sepet boş. Tamamlanacak satış yok.", style="yellow")
                 elif active_shift_id is None: console.print("[bold red]HATA: Satışı tamamlamak için önce vardiya başlatmalısınız (V1).[/]")
                 else: # Satış tamamlama mantığı
                     sale_subtotal = ui.display_cart(cart)
                     console.print("-" * 70, style="dim")
                     selected_customer_id, selected_customer_name = _handle_customer_selection_for_sale(connection, "Satış yapılacak Müşteri Adı veya Telefon No: ")
                     discount_amount_applied = Decimal('0.00')
                     applied_coupon_id = None
                     applied_coupon_code = None
                     available_coupons = []
                     if selected_customer_id:
                         try:
                             available_coupons = customer_db_ops.get_customer_available_coupons(connection, selected_customer_id)
                         except DatabaseError as e: console.print(f"[yellow]Uyarı: Müşteri kuponları alınırken hata: {e}[/]")

                     if discount_amount_applied == Decimal('0.00') and not available_coupons:
                          console.print("[dim]Uygulanacak indirim veya kullanılabilir kupon yok.[/dim]")
                     elif ui.get_yes_no_input("\nİndirim veya Kupon uygulamak ister misiniz?"):
                         while True:
                             console.print("\nİndirim/Kupon Seçenekleri:\n [M]anuel İndirim (Tutar veya Yüzde)")
                             if available_coupons: console.print(" [K]ullanılabilir Kupon Seç")
                             console.print(" [V]azgeç")
                             discount_choice = input("Seçiminiz (M/K/V): ").strip().upper()
                             if discount_choice == 'M':
                                 console.print("İndirim Türü: [T]utar (TL) / [Y]üzde (%) ? ", end="")
                                 type_choice = input().strip().upper()
                                 if type_choice == 'T':
                                     discount_value = ui.get_positive_decimal_input("İndirim Tutarı (TL): ", allow_zero=False)
                                     if discount_value is not None and discount_value >= sale_subtotal:
                                         console.print(f"[bold red]HATA: İndirim tutarı ({discount_value:.2f} TL) sepet toplamından ({sale_subtotal:.2f} TL) büyük veya eşit olamaz.[/]")
                                         continue
                                     if discount_value is not None:
                                         discount_amount_applied = discount_value
                                         applied_coupon_id = None; applied_coupon_code = None
                                         console.print(f"[green]Manuel Tutar İndirimi ({discount_amount_applied:.2f} TL) uygulandı.[/]")
                                         break
                                 elif type_choice == 'Y':
                                     discount_percent = ui.get_positive_decimal_input("İndirim Yüzdesi (%): ", allow_zero=False)
                                     if discount_percent is not None and discount_percent >= 100:
                                         console.print("[bold red]HATA: İndirim yüzdesi 100'den küçük olmalıdır.[/]")
                                         continue
                                     if discount_percent is not None:
                                         discount_amount_applied = (sale_subtotal * (discount_percent / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                                         applied_coupon_id = None; applied_coupon_code = None
                                         console.print(f"[green]Manuel Yüzde İndirimi (%{discount_percent:.0f} -> {discount_amount_applied:.2f} TL) uygulandı.[/]")
                                         break
                                 else: console.print("[red]Geçersiz indirim türü (T veya Y).[/]"); continue
                             elif discount_choice == 'K' and available_coupons:
                                 ui.display_customer_coupons(available_coupons, selected_customer_name)
                                 while True:
                                     coupon_num_str = input(f"Kullanılacak Kupon No (1-{len(available_coupons)}, İptal: 0): ").strip()
                                     if coupon_num_str == '0': console.print("[yellow]Kupon seçimi iptal edildi.[/]"); break
                                     if coupon_num_str.isdigit():
                                         coupon_num = int(coupon_num_str)
                                         if 1 <= coupon_num <= len(available_coupons):
                                             selected_coupon = available_coupons[coupon_num - 1]
                                             min_purchase = selected_coupon.get('min_purchase_amount', Decimal('0.00'))
                                             if sale_subtotal < min_purchase:
                                                 console.print(f"[bold red]HATA: Bu kuponu kullanmak için minimum {min_purchase:.2f} TL harcama gereklidir (Sepet Toplamı: {sale_subtotal:.2f} TL).[/]"); continue
                                             coupon_discount_type = selected_coupon.get('discount_type')
                                             coupon_discount_value = selected_coupon.get('discount_value')
                                             temp_discount = Decimal('0.00')
                                             if coupon_discount_type == 'fixed_amount': temp_discount = coupon_discount_value
                                             elif coupon_discount_type == 'percentage': temp_discount = (sale_subtotal * (coupon_discount_value / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                                             if temp_discount >= sale_subtotal:
                                                 console.print(f"[bold red]HATA: Kupon indirimi ({temp_discount:.2f} TL) sepet toplamından ({sale_subtotal:.2f} TL) büyük veya eşit olamaz.[/]"); continue

                                             discount_amount_applied = temp_discount
                                             applied_coupon_id = selected_coupon.get('customer_coupon_id')
                                             applied_coupon_code = selected_coupon.get('coupon_code')
                                             console.print(f"[green]Kupon '{applied_coupon_code}' ({discount_amount_applied:.2f} TL İndirim) uygulandı.[/]")
                                             break # Kupon seçimi başarılı, iç döngüden çık
                                         else: console.print("[red]Geçersiz kupon numarası.[/]")
                                     else: console.print("[red]Lütfen geçerli bir numara girin.[/]")
                                 if applied_coupon_id: break # İndirim/Kupon seçim döngüsünden çık
                             elif discount_choice == 'V':
                                 console.print("[yellow]İndirim/Kupon uygulanmadı.[/]")
                                 discount_amount_applied = Decimal('0.00')
                                 applied_coupon_id = None; applied_coupon_code = None
                                 break
                             else: console.print("[red]Geçersiz seçim (M, K veya V).[/]")
                     else: # İndirim/Kupon sorma sorusuna Hayır dendi
                          discount_amount_applied = Decimal('0.00')
                          applied_coupon_id = None; applied_coupon_code = None

                     # Otomatik Promosyon Kontrolü
                     applied_promotion_id = None
                     total_promotion_discount = Decimal('0.00')
                     applied_promotion_name = None
                     free_items_for_stock = [] # Bedava verilen ürünlerin stoktan düşülmesi için
                     applied_promos_summary = [] # Kullanıcıya gösterilecek özet
                     processed_product_ids_for_promo = set() # Bir ürün için sadece en iyi bir promosyonu uygula

                     try:
                         for item_index, item in enumerate(cart):
                             product_id = item['product_id']
                             if product_id in processed_product_ids_for_promo: continue # Bu ürün için zaten promosyon uygulandıysa atla

                             quantity_in_cart = item['quantity']
                             price_at_sale = item['price_at_sale']
                             active_promos = promo_db_ops.get_active_promotions_for_product(connection, product_id)
                             best_promo_found = None
                             best_promo_discount_value = Decimal('-1.00') # En iyi indirimi bulmak için

                             for promo in active_promos:
                                 promo_type = promo['promotion_type']
                                 current_promo_discount_value = Decimal('0.00')
                                 applies = False

                                 if promo_type == 'quantity_discount':
                                     if quantity_in_cart >= promo['required_quantity']:
                                         current_promo_discount_value = promo['discount_amount']
                                         applies = True
                                 elif promo_type in ['bogo', 'buy_x_get_y_free']:
                                     req_qty = promo.get('required_bogo_quantity', 1)
                                     if quantity_in_cart >= req_qty:
                                         free_qty_per_promo = promo['free_quantity']
                                         num_promotions = quantity_in_cart // req_qty
                                         total_free_qty = num_promotions * free_qty_per_promo
                                         if total_free_qty > 0:
                                             free_prod_id_for_price = promo.get('free_product_id') or product_id
                                             # Bedava ürünün fiyatını al (stok düşme ve indirim hesaplama için)
                                             free_item_price = price_at_sale # Varsayılan (aynı ürünse)
                                             if free_prod_id_for_price != product_id:
                                                  try:
                                                      free_prod_data = product_db_ops.get_product_by_id(connection, free_prod_id_for_price)
                                                      if free_prod_data: free_item_price = free_prod_data.get('selling_price', Decimal('0.00'))
                                                      else: free_item_price = Decimal('0.00') # Fiyat alınamazsa
                                                  except: free_item_price = Decimal('0.00') # Hata olursa
                                             current_promo_discount_value = total_free_qty * free_item_price
                                             applies = True

                                 # Bu promosyon uygulanabiliyorsa ve öncekinden daha iyiyse seç
                                 if applies and current_promo_discount_value > best_promo_discount_value:
                                     best_promo_discount_value = current_promo_discount_value
                                     best_promo_found = promo

                             # En iyi promosyon bulunduysa uygula
                             if best_promo_found:
                                 processed_product_ids_for_promo.add(product_id) # Bu ürünü işlendi olarak işaretle
                                 current_promo_id = best_promo_found['promotion_id']
                                 current_promo_name = best_promo_found['name']
                                 promo_type = best_promo_found['promotion_type']
                                 current_promo_discount = Decimal('0.00')
                                 promo_summary_text = f"Promosyon: {current_promo_name} ({promo_type}) - Ürün: {item['name']}"

                                 if promo_type == 'quantity_discount':
                                     current_promo_discount = best_promo_found['discount_amount']
                                     promo_summary_text += f" ({best_promo_found['required_quantity']} adet alındı, {current_promo_discount:.2f} TL İndirim)"
                                 elif promo_type in ['bogo', 'buy_x_get_y_free']:
                                     free_qty_per_promo = best_promo_found['free_quantity']
                                     req_qty = best_promo_found.get('required_bogo_quantity', 1)
                                     num_promotions = quantity_in_cart // req_qty
                                     total_free_qty = num_promotions * free_qty_per_promo
                                     free_prod_id = best_promo_found.get('free_product_id') or product_id

                                     if total_free_qty > 0:
                                         # İndirim hesaplaması için fiyatı tekrar al (yukarıda yapıldı)
                                         free_item_price = price_at_sale
                                         if free_prod_id != product_id:
                                              try:
                                                  free_prod_data = product_db_ops.get_product_by_id(connection, free_prod_id)
                                                  if free_prod_data: free_item_price = free_prod_data.get('selling_price', Decimal('0.00'))
                                                  else: free_item_price = Decimal('0.00')
                                              except: free_item_price = Decimal('0.00')

                                         current_promo_discount = total_free_qty * free_item_price
                                         # Stoktan düşülecek bedava ürünleri listeye ekle
                                         found_free = False
                                         for free_stock_item in free_items_for_stock:
                                             if free_stock_item['product_id'] == free_prod_id:
                                                 free_stock_item['quantity'] += total_free_qty
                                                 found_free = True; break
                                         if not found_free:
                                             free_items_for_stock.append({'product_id': free_prod_id, 'quantity': total_free_qty})

                                         # Bedava ürünün adını al (varsa)
                                         free_prod_name_display = "(Aynı Ürün)"
                                         if free_prod_id != product_id:
                                              try:
                                                   free_prod_data_name = product_db_ops.get_product_by_id(connection, free_prod_id)
                                                   if free_prod_data_name: free_prod_name_display = free_prod_data_name.get('name', f'ID:{free_prod_id}')
                                                   else: free_prod_name_display = f'ID:{free_prod_id}'
                                              except: free_prod_name_display = f'ID:{free_prod_id}'

                                         promo_summary_text += f" ({req_qty} adet alındı, {total_free_qty} adet {free_prod_name_display} Bedava - İndirim Karşılığı: {current_promo_discount:.2f} TL)"
                                     else: # Koşul sağlandı ama bedava ürün yoksa (miktar 0 ise)
                                         promo_summary_text += " (Koşul sağlandı ancak bedava ürün miktarı 0)"
                                         current_promo_id = None # Uygulanmış sayma
                                         current_promo_name = None

                                 # Toplam promosyon indirimini ve özeti güncelle
                                 if current_promo_discount > 0:
                                     total_promotion_discount += current_promo_discount
                                     applied_promos_summary.append(promo_summary_text)
                                     # Son uygulanan promosyonun ID ve adını sakla (fişte göstermek için basit yaklaşım)
                                     applied_promotion_id = current_promo_id
                                     applied_promotion_name = current_promo_name

                     except DatabaseError as e: console.print(f"[yellow]Uyarı: Otomatik promosyon kontrolü sırasında veritabanı hatası: {e}[/]")
                     except Exception as e: console.print(f"[yellow]Uyarı: Otomatik promosyon kontrolü sırasında beklenmedik hata: {e}[/]")

                     # Uygulanan promosyonları göster
                     if applied_promos_summary:
                         console.print(f"\n[bold green]>>> Otomatik Promosyon(lar) Uygulandı:[/]");
                     for summary in applied_promos_summary: console.print(f"   -> {summary}")

                     # Ödeme Al
                     payments_list, total_paid_input = ui.collect_payments(sale_subtotal, PAYMENT_METHODS, selected_customer_id, discount_amount_applied, total_promotion_discount)

                     if payments_list is not None: # Ödeme iptal edilmediyse
                         final_total_after_discount = sale_subtotal - discount_amount_applied - total_promotion_discount
                         if final_total_after_discount < Decimal('0.00'): final_total_after_discount = Decimal('0.00')

                         change_due = total_paid_input - final_total_after_discount
                         if change_due < Decimal('0.00'): change_due = Decimal('0.00') # Para üstü negatif olamaz

                         console.print("\nSatış veritabanına kaydediliyor...", style="italic")
                         try:
                             # Satışı kaydet
                             saved_sale_id = sale_db_ops.finalize_sale(
                                 connection=connection,
                                 cart=cart,
                                 sale_subtotal=sale_subtotal,
                                 customer_id=selected_customer_id,
                                 payments=payments_list,
                                 applied_coupon_id=applied_coupon_id,
                                 discount_amount=discount_amount_applied,
                                 applied_promotion_id=applied_promotion_id,
                                 promotion_discount=total_promotion_discount,
                                 free_items_for_stock=free_items_for_stock, # Bedava ürünleri gönder
                                 shift_id=active_shift_id,
                                 user_id=current_user_id
                             )
                             if saved_sale_id:
                                 if change_due > Decimal('0.00'):
                                     console.print(f"\n>>> Para Üstü: [bold green]{change_due:.2f} TL[/]")
                                 # Fişi yazdır
                                 ui.print_receipt(cart, sale_subtotal, payments_list, total_paid_input, change_due, STORE_NAME, selected_customer_name, discount_amount_applied, applied_coupon_code, total_promotion_discount, applied_promotion_name)
                                 cart.clear() # Sepeti temizle
                                 console.print(f"\n[bold green]Satış (ID: {saved_sale_id}) başarıyla tamamlandı.[/]")
                             else: # finalize_sale None döndürdüyse (hata oluştuysa)
                                 console.print(">>> Satış kaydedilemedi. Sepet korundu.", style="bold red")
                         except Exception as finalize_error:
                             console.print(f"\n>>> SATIŞ KAYDI HATASI: {finalize_error}", style="bold red")
                             console.print("[yellow]Sepet korundu.[/]")
            elif choice == '6': # Satış İptali / İade
                 if user_role in TUM_KULLANICILAR: # Kasiyer ve üstü
                     console.print("\n--- Satış İptali / İade ---", style="bold blue")
                     try:
                         sale_id_to_return = ui.get_positive_int_input("İptal/İade edilecek Satış Fişi Numarası (ID): ", allow_zero=False)
                         sale_details = sale_db_ops.get_sale_details_for_return(connection, sale_id_to_return)
                         if sale_details is None: pass # Hata mesajı DB fonksiyonunda verildi
                         else:
                             ui.display_sale_details_for_confirmation(sale_details)
                             if ui.get_yes_no_input(f"\n>>> Satış ID {sale_id_to_return} iade edilsin mi? (Stoklar geri alınacak, bakiye güncellenecek)"):
                                 reason = input("İade Sebebi (isteğe bağlı): ").strip() or None
                                 notes = input("İade Notları (isteğe bağlı): ").strip() or None
                                 return_id = sale_db_ops.process_sale_return(connection, sale_id_to_return, sale_details, reason, notes, current_user_id)
                                 # Başarı/hata mesajı DB fonksiyonunda veriliyor
                             else: console.print("İade işlemi iptal edildi.", style="yellow")
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Satış İadesi): {e}", style="bold red")
                     except ValueError as ve: console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Satış İadesi): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '7': # Fiyat Sorgula
                 product_handlers.handle_price_check(connection)
            elif choice == '8': # Satışı Askıya Al
                 if not cart: console.print(">>> Askıya alınacak ürün sepeti boş.", style="yellow")
                 else:
                     if ui.get_yes_no_input("Mevcut sepet askıya alınsın mı?"):
                         suspend_id = suspended_sale_id_counter
                         suspended_sales[suspend_id] = cart[:] # Sepetin kopyasını sakla
                         suspended_sale_id_counter += 1
                         cart.clear() # Mevcut sepeti temizle
                         console.print(f"\n[green]>>> Satış [bold cyan]ID {suspend_id}[/] ile askıya alındı.[/]")
                     else: console.print("Askıya alma işlemi iptal edildi.", style="yellow")
            elif choice == '9': # Askıdaki Satışı Çağır
                 if not suspended_sales: console.print(">>> Askıda bekleyen satış bulunmamaktadır.", style="yellow")
                 else:
                     if ui.display_suspended_sales_list(suspended_sales):
                         while True:
                             recall_id_str = input("Çağrılacak Askı ID'sini girin (İptal için 0): ").strip()
                             if recall_id_str == '0': console.print("İşlem iptal edildi.", style="yellow"); break
                             if recall_id_str.isdigit():
                                 recall_id = int(recall_id_str)
                                 if recall_id in suspended_sales:
                                     if cart: # Mevcut sepette ürün varsa uyar
                                         if not ui.get_yes_no_input(f">>> Mevcut sepette {len(cart)} ürün var. Bu sepet silinip askıdaki (ID: {recall_id}) satış çağrılsın mı?"):
                                             console.print("Askıdaki satışı çağırma iptal edildi.", style="yellow")
                                             break # İç döngüden çık
                                     # Mevcut sepeti temizle ve askıdakini yükle
                                     cart = suspended_sales.pop(recall_id)
                                     console.print(f"\n[green]>>> Askıdaki Satış (ID: {recall_id}) geri çağrıldı.[/]")
                                     ui.display_cart(cart) # Yeni sepeti göster
                                     break # İç döngüden çık
                                 else: console.print(f">>> Geçersiz Askı ID: {recall_id}", style="red")
                             else: console.print(">>> Lütfen geçerli bir ID girin.", style="red")
            # --- Müşteri İşlemleri ---
            elif choice == '10': customer_handlers.handle_add_customer(connection, current_user_id)
            elif choice == '11': # Müşteri Listele
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_list_customers(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '12': # Müşteri Güncelle
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_update_customer(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '13': # Müşteri Ödeme Al
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_customer_payment(connection, active_shift_id, current_user_id, CUSTOMER_PAYMENT_METHODS)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '14': # Hesap Ekstresi
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_customer_ledger(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '15': # Kupon Görüntüle
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_view_customer_coupons(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '16': # Müşteri Durum
                 if user_role in YONETICI_VE_USTU: customer_handlers.handle_toggle_customer_status(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Ürün İşlemleri ---
            elif choice == '17': # Yeni Ürün
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_add_product(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '18': # Ürün Listele
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_list_products(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '19': # Ürün Güncelle
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_update_product(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '20': # Stok Girişi
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_stock_input(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '21': # Stok Düzeltme
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_stock_adjustment(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '22': # Ürün Durum
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_toggle_product_status(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '23': # Etiket Yazdır
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_print_shelf_label(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '24': # CSV Export
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_export_products(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '25': # CSV Import
                 if user_role in YONETICI_VE_USTU: product_handlers.handle_import_products(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Marka İşlemleri ---
            elif choice == '26': # Yeni Marka
                 if user_role in YONETICI_VE_USTU: brand_handlers.handle_add_brand(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '27': # Marka Listele
                 if user_role in YONETICI_VE_USTU: brand_handlers.handle_list_brands(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '28': # Marka Durum
                 if user_role in YONETICI_VE_USTU: brand_handlers.handle_toggle_brand_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Kategori İşlemleri ---
            elif choice == '29': # Yeni Kategori
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_add_category(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '30': # Kategori Listele
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_list_categories(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '31': # Kategori Güncelle
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_update_category(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '32': # Kategori Durum
                 if user_role in YONETICI_VE_USTU: category_handlers.handle_toggle_category_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Promosyon İşlemleri ---
            elif choice == '33': # Yeni Promosyon
                 if user_role in YONETICI_VE_USTU: promo_handlers.handle_add_promotion(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '34': # Promosyon Listele
                 if user_role in YONETICI_VE_USTU: promo_handlers.handle_list_promotions(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '35': # Promosyon Durum
                 if user_role in YONETICI_VE_USTU: promo_handlers.handle_toggle_promotion_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Tedarikçi İşlemleri ---
            elif choice == '36': # Yeni Tedarikçi
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_add_supplier(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '37': # Tedarikçi Listele
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_list_suppliers(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '38': # Tedarikçi Güncelle
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_update_supplier(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '39': # Tedarikçi Durum
                 if user_role in YONETICI_VE_USTU: supplier_handlers.handle_toggle_supplier_status(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Raporlar ---
            elif choice == '40': # Günlük Satış
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- Günlük Satış Özeti Raporu ---", style="bold blue")
                     try:
                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             summary_data = sale_db_ops.get_daily_sales_summary(connection, start_date, end_date)
                             ui.display_daily_sales_summary(summary_data, start_date, end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Günlük Özet): {e}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Günlük Özet): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '41': # En Çok Satan (Adet)
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- En Çok Satan Ürünler (Adet) ---", style="bold blue")
                     try:
                         # Varsayılan limiti göstererek iste
                         limit_prompt = f"Listelenecek ürün sayısı [Varsayılan: {DEFAULT_REPORT_LIMIT}]: "
                         limit = ui.get_positive_int_input(limit_prompt, allow_zero=False) # Kullanıcı yine de girmeli
                         if limit <= 0 : limit = DEFAULT_REPORT_LIMIT # Geçersizse varsayılanı kullan (aslında get_positive_int_input bunu engeller)

                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             report_data = sale_db_ops.get_top_selling_products_by_quantity(connection, limit, start_date, end_date)
                             ui.display_top_products_report(report_data, report_type="quantity", limit=limit, start_date=start_date, end_date=end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Rapor): {e}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Rapor): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '42': # En Çok Ciro Yapanlar
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- En Çok Ciro Yapan Ürünler ---", style="bold blue")
                     try:
                         # Varsayılan limiti göstererek iste
                         limit_prompt = f"Listelenecek ürün sayısı [Varsayılan: {DEFAULT_REPORT_LIMIT}]: "
                         limit = ui.get_positive_int_input(limit_prompt, allow_zero=False)
                         if limit <= 0 : limit = DEFAULT_REPORT_LIMIT

                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             report_data = sale_db_ops.get_top_selling_products_by_value(connection, limit, start_date, end_date)
                             ui.display_top_products_report(report_data, report_type="value", limit=limit, start_date=start_date, end_date=end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Rapor): {e}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Rapor): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '43': # Stok Raporu
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- Stok Raporu ---", style="bold blue")
                     try:
                         include_inactive = ui.get_yes_no_input("Pasif ürünler de dahil edilsin mi?")
                         filter_choice = 0
                         console.print("Stok Filtreleme Seçenekleri:\n [1] Tümünü Göster\n [2] Sadece Stoğu Kritik Seviyede Olanlar (Min. Stok Altı)\n [3] Stoğu Belirli Bir Seviyenin Altında Olanlar")
                         while True:
                             f_choice = input("Filtre seçin (1-3) [Varsayılan: 1]: ").strip()
                             if not f_choice: filter_choice = 1; break
                             if f_choice.isdigit() and 1 <= int(f_choice) <= 3: filter_choice = int(f_choice); break
                             else: console.print(">>> Geçersiz seçim (1, 2 veya 3 girin).", style="red")
                         stock_threshold = None
                         only_critical = False
                         if filter_choice == 2: only_critical = True
                         elif filter_choice == 3: stock_threshold = ui.get_positive_int_input("Stok eşiği (bu değer ve altı gösterilecek): ", allow_zero=True)

                         stock_data = product_db_ops.get_stock_report_data(connection, stock_threshold, include_inactive, only_critical)
                         ui.display_stock_report(stock_data, stock_threshold, include_inactive, only_critical)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Stok Raporu): {e}", style="bold red")
                     except ValueError as ve: console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Stok Raporu): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '44': # Kâr/Zarar
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- Kâr/Zarar Raporu (Tahmini) ---", style="bold blue")
                     try:
                         console.print("\n(İsteğe bağlı) Rapor için tarih aralığı girin:")
                         start_date = ui.get_date_input("Başlangıç Tarihi")
                         end_date = ui.get_date_input("Bitiş Tarihi")
                         if start_date and end_date and start_date > end_date: console.print(">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
                         else:
                             report_data = sale_db_ops.get_profit_loss_report_data(connection, start_date, end_date)
                             ui.display_profit_loss_report(report_data, start_date, end_date)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (Kâr/Zarar Raporu): {e}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (Kâr/Zarar Raporu): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '45': # SKT Raporu
                 if user_role in YONETICI_VE_USTU:
                     console.print("\n--- SKT Raporu ---", style="bold red")
                     try:
                         days = ui.get_positive_int_input("Kaç gün sonrasına kadar olan SKT'ler listelensin? (örn: 30): ", allow_zero=True)
                         report_data = sale_db_ops.get_expiry_report_data(connection, days)
                         ui.display_expiry_report(report_data, days)
                     except DatabaseError as e: console.print(f">>> VERİTABANI HATASI (SKT Raporu): {e}", style="bold red")
                     except ValueError as ve: console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
                     except Exception as e: console.print(f">>> BEKLENMEDİK HATA (SKT Raporu): {e}", style="bold red")
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Hesap İşlemleri ---
            elif choice == '46': # Şifre Değiştir
                 user_handlers.handle_change_password(connection, logged_in_user)
            # --- Yönetim ---
            elif choice == '47': # Yeni Kullanıcı
                 if user_role == 'admin': user_handlers.handle_add_user(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '48': # Kullanıcı Listele
                 if user_role == 'admin': user_handlers.handle_list_users(connection)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '49': # Kullanıcı Güncelle
                 if user_role == 'admin': user_handlers.handle_update_user(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            elif choice == '50': # Kullanıcı Durum
                 if user_role == 'admin': user_handlers.handle_toggle_user_status(connection, current_user_id)
                 else: console.print("[bold red]HATA: Bu işlem için yetkiniz bulunmamaktadır.[/]")
            # --- Geçersiz Seçim ---
            else:
                console.print("\n>>> Geçersiz seçim veya barkod!", style="bold red")

            # İşlem sonrası bekleme (isteğe bağlı)
            # input("\nDevam etmek için Enter'a basın...") # Her adımdan sonra bekletir
            ui.pause_and_clear(bekle=False, sure=0.5) # Kısa bir bekleme yapıp temizle

        except KeyboardInterrupt:
            console.print("\n>>> Ctrl+C algılandı. Programdan çıkılıyor...", style="bold yellow")
            break
        except DatabaseError as db_err:
            console.print(f"\n>>> BEKLENMEDİK VERİTABANI HATASI: {db_err}", style="bold red")
            input("Devam etmek için Enter'a basın...")
        except Exception as main_loop_error:
            console.print("\n>>> BEKLENMEDİK PROGRAM HATASI!", style="bold red")
            console.print_exception(show_locals=False) # Hata detayını göster
            input("Devam etmek için Enter'a basın...")

    # Program Sonu
    print("DEBUG: Ana döngüden çıkıldı.") # DEBUG
    if connection and connection.is_connected():
        try:
            connection.close()
            print("DEBUG: Veritabanı bağlantısı başarıyla kapatıldı.") # DEBUG
        except Error as e:
            print(f"DEBUG: Veritabanı kapatılırken hata: {e}") # DEBUG
            console.print(f"Veritabanı kapatılırken hata: {e}", style="red")
    print("DEBUG: Program sonlandırılıyor.") # DEBUG


# === Programın Başlangıç Noktası ===
if __name__ == "__main__":
    print("DEBUG: Program __main__ bloğundan başlatılıyor.") # DEBUG
    try:
        main()
    except ImportError as imp_err:
        print(f"\n!!! KRİTİK HATA: Gerekli bir kütüphane bulunamadı: {imp_err}")
        missing_module = str(imp_err).split("'")[-2]
        if missing_module in ['db_config', 'urun_veritabani', 'urun_islemleri', 'musteri_veritabani', 'musteri_islemleri', 'tedarikci_veritabani', 'tedarikci_islemleri', 'kullanici_veritabani', 'kullanici_islemleri', 'kategori_veritabani', 'kategori_islemleri', 'marka_veritabani', 'marka_islemleri', 'promosyon_veritabani', 'promosyon_islemleri', 'vardiya_veritabani', 'vardiya_islemleri', 'loglama', 'veri_aktarim', 'yazdirma_islemleri', 'arayuz_girdi', 'arayuz_gosterim', 'arayuz_yardimcilari', 'hatalar']:
             print(f">>> '{missing_module}.py' dosyasının veya ilgili modülün proje klasöründe olduğundan emin olun.")
        elif 'getpass' in str(imp_err): print(">>> 'getpass' modülü standart Python ile gelir, kurulumda bir sorun olabilir.")
        else: print(">>> Lütfen 'pip install mysql-connector-python rich bcrypt' komutunu çalıştırın.")
    except Exception as final_error:
        print("\n>>> PROGRAMDA ÖNGÖRÜLEMEYEN KRİTİK HATA!")
        print(f"Hata Detayı: {final_error}")
        import traceback
        traceback.print_exc()
    finally:
        print("DEBUG: Program sonu.") # En sona bir debug mesajı