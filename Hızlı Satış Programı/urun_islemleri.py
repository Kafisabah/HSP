# urun_islemleri.py
# Ürün yönetimi, stok girişi ve veri aktarımı ile ilgili kullanıcı etkileşimlerini yönetir.
# ... (Önceki versiyon notları) ...
# v53: Etiket yazdırma için handle_print_shelf_label eklendi.
# v54: CSV içe/dışa aktarma için handle_export_products ve handle_import_products eklendi.
# v58: handle_add_product fonksiyonu config.ini'den default_min_stock okuyacak şekilde güncellendi.
# v60 (Bu versiyon): handle_add_product fonksiyonu config.ini'den default_kdv_rate okuyacak şekilde güncellendi.

import arayuz_yardimcilari as ui
import urun_veritabani as product_db_ops
import tedarikci_islemleri as supplier_handlers
import kategori_islemleri as category_handlers
import marka_islemleri as brand_handlers
import loglama
import yazdirma_islemleri as print_handlers
import veri_aktarim
import os
from hatalar import DatabaseError, DuplicateEntryError, SaleIntegrityError, UserInputError
from decimal import Decimal, InvalidOperation
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import datetime
import configparser # Yapılandırma okumak için eklendi

# arayuz_yardimcilari içinde tanımlı console'u kullanalım
console = ui.console

# --- Yardımcı Fonksiyon: Yapılandırmayı Oku ---
def _get_config():
    """config.ini dosyasını okur ve config nesnesini döndürür."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config.ini')
    config = configparser.ConfigParser(interpolation=None)
    if not config.read(config_path, encoding='utf-8'):
        rprint(f"[yellow]Uyarı: Yapılandırma dosyası okunamadı: {config_path}. Varsayılan değerler kullanılabilir.[/]")
    return config

# === Yardımcı Fonksiyon: Ürün Bul/Seç (Yönetim için) ===
# ... (_find_product_for_management fonksiyonu aynı kalır) ...
def _find_product_for_management(connection, prompt_message):
    """
    Yönetim işlemleri (güncelleme, durum değiştirme, etiket basma) için ürün arar ve seçtirir.
    Aktif/Pasif tüm ürünleri arar. Seçilen ürünün tam bilgisini (sözlük) döndürür.
    """
    while True:
        user_input = ui.get_non_empty_input(prompt_message)
        product_list = []
        product_dict = None
        try:
            # ID ile ara
            if user_input.isdigit():
                try:
                     product_dict = product_db_ops.get_product_by_id(
                         connection, int(user_input))
                     if product_dict:
                         product_list = [product_dict]
                except DatabaseError: pass # ID ile bulunamazsa devam

            # Barkod ile ara (eğer ID ile bulunamadıysa ve girdi sayısal ise)
            if not product_list and user_input.isdigit():
                product_dict = product_db_ops.get_product_by_barcode(
                    connection, user_input, only_active=False) # Aktif olmayanları da ara
                if product_dict:
                    product_list = [product_dict]

            # İsim ile ara (eğer önceki adımlarda bulunamadıysa)
            if not product_list:
                product_list = product_db_ops.get_products_by_name_like(
                    connection, user_input, only_active=False) # Aktif olmayanları da ara

            # Sonuçları değerlendir
            if not product_list:
                console.print(
                    f">>> '{user_input}' ile eşleşen ürün bulunamadı.", style="yellow")
                if not ui.get_yes_no_input("Tekrar aramak ister misiniz?"):
                    return None
                else: continue # Tekrar arama döngüsüne dön

            elif len(product_list) == 1:
                found_product = product_list[0]
                console.print(
                    f">>> Ürün bulundu: {found_product.get('name','?')} (ID: {found_product.get('product_id','?')}, Durum: {'Aktif' if found_product.get('is_active') else 'Pasif'})", style="green")
                # Emin olmak için tam veriyi ID ile çekelim (get_product_by_id zaten bunu yapıyor)
                return found_product # Bulunan sözlüğü doğrudan döndür

            else: # Birden fazla sonuç
                console.print(
                    f"\n>>> '{user_input}' ile eşleşen birden fazla ürün bulundu:")
                select_table = Table(show_header=True, header_style="blue", border_style="blue") # Başlık ekleyelim
                select_table.add_column("No", style="dim")
                select_table.add_column("ID", style="dim")
                select_table.add_column("Ad", style="cyan")
                select_table.add_column("Marka", style="magenta")
                select_table.add_column("Stok", style="green")
                select_table.add_column("Durum", style="dim")
                # Numaralandırarak göster
                [select_table.add_row(
                    f"{i}.",
                    str(p.get('product_id', '?')),
                    p.get('name', '?'),
                    p.get('brand_name', '-') or "-", # None ise '-' yap
                    str(p.get('stock', '?')),
                    "[green]Aktif[/]" if p.get('is_active') else "[red]Pasif[/]"
                ) for i, p in enumerate(product_list, 1)]
                console.print(select_table)

                # Kullanıcıdan seçim iste
                while True:
                    prompt = f"İşlem yapılacak ürünün No (1-{len(product_list)}, İptal için 0): "
                    choice_num = ui.get_positive_int_input(
                        prompt, allow_zero=True)
                    if choice_num == 0:
                        console.print("İşlem iptal edildi.", style="yellow")
                        return None # Ana fonksiyona None döndür
                    elif 1 <= choice_num <= len(product_list):
                        selected_product_dict = product_list[choice_num - 1]
                        console.print(
                            f">>> Seçilen: {selected_product_dict.get('name','?')} (ID: {selected_product_dict.get('product_id','?')})", style="green")
                        # Seçilen ürünün tam verisini döndür
                        return selected_product_dict
                    else:
                        console.print(f">>> Geçersiz numara!", style="red")
        except DatabaseError as e:
            console.print(f">>> VERİTABANI HATASI (Ürün Arama): {e}", style="bold red")
            return None # Hata durumunda None döndür
        except Exception as e:
            console.print(f">>> BEKLENMEDİK HATA (Ürün Arama): {e}", style="bold red")
            return None # Hata durumunda None döndür

# === Handler Fonksiyonları ===

# ***** BU FONKSİYON GÜNCELLENDİ *****
def handle_add_product(connection, current_user_id):
    """Yeni ürün ekleme işlemini yönetir ve loglar."""
    console.print("\n--- Yeni Ürün Ekle ---", style="bold blue")
    new_product_id = None
    product_name_for_log = None
    try:
        barcode = ui.get_numeric_input("Barkod: ")
        name = ui.get_non_empty_input("Ürün Adı: "); product_name_for_log = name
        brand_id = brand_handlers.select_brand(
            connection, prompt_message="Marka Adı: ", allow_none=False) # Marka seçimi zorunlu
        if brand_id is None:
            console.print(">>> Marka seçimi yapılamadığı için ürün ekleme iptal edildi.", style="yellow")
            return

        price_before_kdv = ui.get_positive_decimal_input("KDV Hariç Fiyat: ", allow_zero=False)

        # Varsayılan KDV oranını config'den oku
        config = _get_config()
        try:
            kdv_rate_default = config.getfloat('general', 'default_kdv_rate', fallback=10.0)
        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            kdv_rate_default = 10.0 # Hata olursa veya ayar yoksa %10 kullan
            rprint(f"[yellow]Uyarı: config.ini'den 'default_kdv_rate' okunamadı veya geçersiz. Varsayılan değer (%{kdv_rate_default:.1f}) kullanılıyor.[/]")

        # Kullanıcıdan KDV oranını iste, varsayılanı göster
        # get_optional_decimal_input boş bırakılırsa mevcut değeri (burada default) döndürür
        kdv_rate = ui.get_optional_decimal_input(f"KDV Oranı (%) [{kdv_rate_default:.1f}]", Decimal(str(kdv_rate_default)))
        if kdv_rate is None or kdv_rate < 0: # Geçersiz giriş veya negatifse varsayılana dön
            kdv_rate = Decimal(str(kdv_rate_default))

        price_with_kdv = ui.calculate_price_with_kdv(
            price_before_kdv, kdv_rate)
        if price_with_kdv is None:
            console.print(">>> HATA: KDV Dahil fiyat hesaplanamadı!", style="red")
            return

        console.print(f"Hesaplanan KDV Dahil Fiyat: [yellow]{price_with_kdv:.2f} TL[/]")
        while True:
            selling_price = ui.get_positive_decimal_input(
                "Satış Fiyatı (KDV Dahil): ", allow_zero=False)
            # Yuvarlama farklarına karşı küçük bir tolerans eklenebilir (örn: 0.001)
            if selling_price < price_with_kdv - Decimal('0.001'):
                console.print(f">>> HATA: Satış fiyatı ({selling_price:.2f}), KDV Dahil fiyattan ({price_with_kdv:.2f} TL) düşük olamaz!", style="red")
            else:
                break

        stock = ui.get_positive_int_input(
            "Başlangıç Stok Adedi: ", allow_zero=True)

        # Varsayılan min stok seviyesini config'den oku
        try:
            min_stock_level_default = config.getint('general', 'default_min_stock', fallback=2)
        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            min_stock_level_default = 2
            rprint(f"[yellow]Uyarı: config.ini'den 'default_min_stock' okunamadı veya geçersiz. Varsayılan değer ({min_stock_level_default}) kullanılıyor.[/]")

        # Kullanıcıdan min stok seviyesini iste, varsayılanı göster
        min_stock_level = ui.get_optional_int_input(f"Minimum Stok Seviyesi [{min_stock_level_default}]", min_stock_level_default)
        if min_stock_level is None or min_stock_level < 0:
            min_stock_level = min_stock_level_default # Geçersizse veya boşsa varsayılana dön

        category_id = category_handlers.select_category(connection, allow_none=True) # Kategori seçimi opsiyonel

        new_product_id = product_db_ops.add_product(
            connection, barcode, name, brand_id, price_before_kdv, kdv_rate, selling_price, stock, category_id, min_stock_level)

        if new_product_id:
            log_details = f"Ürün ID: {new_product_id}, Ad: {name}, Barkod: {barcode}"
            loglama.log_activity(connection, current_user_id, loglama.LOG_ACTION_PRODUCT_ADD, log_details)

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Ürün Ekleme): {e}", style="bold red")
        console.print_exception(show_locals=False) # Detaylı hata göster

# ... (handle_list_products, handle_update_product, handle_stock_input, handle_toggle_product_status, handle_price_check, handle_stock_adjustment, handle_print_shelf_label, handle_export_products, handle_import_products fonksiyonları aynı kalır) ...
def handle_list_products(connection):
    """Ürünleri listeleme işlemini yönetir."""
    console.print("\n--- Ürün Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input("Pasif ürünler de gösterilsin mi?")
        products = product_db_ops.list_all_products(
            connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        ui.display_product_list(products, title=f"{status_text} Ürünler")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")

def handle_update_product(connection, current_user_id):
    """Mevcut bir ürünü güncelleme işlemini yönetir ve loglar."""
    console.print("\n--- Ürün Güncelle ---", style="bold blue")
    product_data = _find_product_for_management(
        connection, "Güncellenecek ürünün Barkodunu veya Adını girin: ")
    if not product_data:
        return

    # Mevcut verileri al
    current_id = product_data.get('product_id')
    current_barcode = product_data.get('barcode') # Barkod güncellenmiyor ama bilgi için
    current_name = product_data.get('name')
    current_brand_id = product_data.get('brand_id')
    current_brand_name = product_data.get('brand_name')
    current_category_id = product_data.get('category_id')
    current_category_name = product_data.get('category_name')
    current_price_before_kdv = product_data.get('price_before_kdv')
    current_kdv_rate = product_data.get('kdv_rate')
    current_selling_price = product_data.get('selling_price')
    current_previous_selling_price = product_data.get('previous_selling_price')
    current_stock = product_data.get('stock')
    current_min_stock_level = product_data.get('min_stock_level')
    is_active = product_data.get('is_active')
    last_updated = product_data.get('last_updated')

    console.print("\n--- Mevcut Bilgiler ---")
    price_b_kdv_display = f"{current_price_before_kdv:.2f}" if current_price_before_kdv is not None else "-"
    kdv_rate_display = f"{current_kdv_rate:.2f}" if current_kdv_rate is not None else "-"
    selling_price_display = f"{current_selling_price:.2f}" if current_selling_price is not None else "-"
    prev_price_display = f"{current_previous_selling_price:.2f} TL" if current_previous_selling_price is not None else "-"
    stock_display = str(current_stock) if current_stock is not None else "?"
    min_stock_display = str(current_min_stock_level) if current_min_stock_level is not None else "?"
    brand_display = f"{current_brand_name} (ID: {current_brand_id})" if current_brand_id else "Yok"
    category_display = f"{current_category_name} (ID: {current_category_id})" if current_category_id else "Yok"
    status_display = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
    last_updated_display = last_updated.strftime('%d.%m.%Y %H:%M') if isinstance(last_updated, (datetime.datetime, datetime.date)) else "-"

    console.print(f" ID: {current_id}\n Barkod: {current_barcode}\n Ad: {current_name}\n Marka: {brand_display}\n Kategori: {category_display}")
    console.print(f" KDV Hariç Fiyat: {price_b_kdv_display} TL\n KDV Oranı (%): {kdv_rate_display}\n Satış Fiyatı: {selling_price_display} TL\n Önceki Satış Fiyatı: {prev_price_display}")
    console.print(f" Stok: {stock_display}\n Min. Stok: {min_stock_display}\n Durum: {status_display}\n Son Güncelleme: {last_updated_display}")

    console.print("--- Yeni Bilgiler (Değiştirmek istemediklerinizi boş bırakın) ---", style="dim")

    try:
        # Barkod güncellenmez
        final_name = ui.get_optional_string_input("Yeni Ad", current_name)
        if not final_name:
            console.print(">>> HATA: Ürün adı boş bırakılamaz.", style="red")
            return

        # Marka seçimi
        final_brand_id = current_brand_id
        if ui.get_yes_no_input(f"Markayı değiştirmek istiyor musunuz? (Mevcut: {brand_display})"):
            newly_selected_brand_id = brand_handlers.select_brand(
                connection, prompt_message="Yeni Marka Adı: ", allow_none=False) # Zorunlu seçmeli
            if newly_selected_brand_id is None:
                console.print(">>> Marka seçimi yapılamadığı için güncelleme iptal edildi.", style="yellow")
                return
            final_brand_id = newly_selected_brand_id

        # Kategori seçimi
        final_category_id = current_category_id
        if ui.get_yes_no_input(f"Kategoriyi değiştirmek istiyor musunuz? (Mevcut: {category_display})"):
            # None (kategorisiz) seçime izin verelim
            newly_selected_cat_id = category_handlers.select_category(
                connection, prompt_message="Yeni Kategori Adı: ", allow_none=True)
            final_category_id = newly_selected_cat_id

        final_price_before_kdv = ui.get_optional_decimal_input("Yeni KDV Hariç Fiyat", current_price_before_kdv)
        final_kdv_rate = ui.get_optional_decimal_input("Yeni KDV Oranı (%)", current_kdv_rate)

        # Yeni KDV dahil fiyatı hesapla ve kontrol et
        new_price_with_kdv = ui.calculate_price_with_kdv(
            final_price_before_kdv, final_kdv_rate)
        if new_price_with_kdv is None:
            console.print(">>> HATA: Yeni KDV Dahil fiyat hesaplanamadı!", style="red")
            return
        console.print(f"Hesaplanan Yeni KDV Dahil Fiyat: [yellow]{new_price_with_kdv:.2f} TL[/]")

        # Yeni satış fiyatını al ve kontrol et
        while True:
            final_selling_price = ui.get_optional_decimal_input(
                "Yeni Satış Fiyatı", current_selling_price)
            if final_selling_price is None: # Boş bırakılırsa mevcutu kullan
                final_selling_price = current_selling_price
            # Yuvarlama farklarına karşı küçük bir tolerans
            if final_selling_price < new_price_with_kdv - Decimal('0.001'):
                console.print(f">>> HATA: Yeni satış fiyatı ({final_selling_price:.2f}), yeni KDV Dahil fiyattan ({new_price_with_kdv:.2f} TL) düşük olamaz!", style="red")
            else:
                break

        # Stok ve Min Stok
        final_stock = ui.get_optional_int_input("Yeni Stok Adedi", current_stock)
        if final_stock is None: # Boş bırakılırsa mevcutu kullan
            final_stock = current_stock

        final_min_stock_level = ui.get_optional_int_input("Yeni Min. Stok Seviyesi", current_min_stock_level)
        # final_min_stock_level None olabilir, DB fonksiyonu None alırsa DB'deki değeri korur

        # Değişiklik kontrolü
        changes_made = (
            final_name != current_name or
            final_brand_id != current_brand_id or
            final_category_id != current_category_id or
            final_price_before_kdv != current_price_before_kdv or
            final_kdv_rate != current_kdv_rate or
            final_selling_price != current_selling_price or
            final_stock != current_stock or
            # final_min_stock_level None olabilir, karşılaştırma dikkatli yapılmalı
            (final_min_stock_level is not None and final_min_stock_level != current_min_stock_level)
        )

        if not changes_made:
            console.print("[yellow]>>> Hiçbir değişiklik yapılmadı.[/]")
            return

        # Güncelleme işlemini çağır
        success = product_db_ops.update_product(
            connection, current_id, final_name, final_brand_id, final_category_id,
            final_price_before_kdv, final_kdv_rate, final_selling_price,
            final_stock, final_min_stock_level # None gönderilebilir
        )

        # Loglama
        if success and changes_made:
            log_details = f"Ürün ID: {current_id}, Yeni Ad: {final_name}"
            changed_fields = []
            # Hangi alanların değiştiğini loga ekleyebiliriz (opsiyonel)
            if final_selling_price != current_selling_price:
                changed_fields.append(f"Fiyat:{current_selling_price}->{final_selling_price}")
            if final_stock != current_stock:
                changed_fields.append(f"Stok:{current_stock}->{final_stock}")
            # Diğer alanlar da eklenebilir...
            if changed_fields:
                log_details += f" ({', '.join(changed_fields)})"
            loglama.log_activity(connection, current_user_id, loglama.LOG_ACTION_PRODUCT_UPDATE, log_details)
        elif not success and changes_made: # Değişiklik yapıldı ama DB güncellenmediyse (örn. DB hatası)
            # Hata mesajı DB katmanında zaten veriliyor olmalı
            pass
        elif not success and not changes_made: # Değişiklik yoktu ve DB fonksiyonu False döndü (beklenen durum)
            pass


    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Ürün Güncelleme): {e}", style="bold red")
        console.print_exception(show_locals=False)

def handle_stock_input(connection, current_user_id):
    """Stok Girişi / Alış Kaydı işlemini yönetir ve loglar."""
    console.print("\n--- Stok Girişi / Alış Kaydı ---", style="bold blue")
    purchase_info = {}
    items_list_for_db = []
    items_list_for_summary = []
    purchase_id = None
    try:
        # Tedarikçi Seçimi
        console.print("\n-- Tedarikçi Bilgisi --", style="dim")
        selected_supplier_id, selected_supplier_name, _ = supplier_handlers.select_supplier(
            connection, "Tedarikçi Adı/Tel: ", allow_none=False, only_active=True)
        if selected_supplier_id is None:
            console.print(">>> Tedarikçi seçilmediği için stok girişi iptal edildi.", style="yellow")
            return
        purchase_info['supplier_id'] = selected_supplier_id

        # Fatura Bilgileri
        console.print("\n-- Fatura/İrsaliye Bilgileri --", style="dim")
        purchase_info['invoice_number'] = input(
            "Fatura/İrsaliye No (isteğe bağlı): ").strip() or None
        purchase_info['notes'] = input(
            "Alış Notları (isteğe bağlı): ").strip() or None

        # Ürün Ekleme Döngüsü
        while True:
            console.print("\n-- Alış Listesine Ürün Ekle --", style="dim")
            # Ürün bul/seç (pasifler dahil, çünkü pasif ürüne stok girilebilir)
            selected_product_data = _find_product_for_management(
                connection, "Alınan Ürün Barkodu veya Adı (Bitirmek için '0'): ")

            if not selected_product_data:
                 # Kullanıcı 0 girdiyse veya arama iptal edildiyse
                 if not items_list_for_db: # Eğer liste boşsa tamamen çık
                     console.print(">>> Hiç ürün eklenmedi. Alış kaydı iptal edildi.", style="yellow")
                     return
                 else: # Listede ürün varsa döngüden çıkıp özete git
                     break

            product_id = selected_product_data.get('product_id')
            product_barcode = selected_product_data.get('barcode')
            product_name = selected_product_data.get('name')
            brand_name = selected_product_data.get('brand_name')
            current_stock = selected_product_data.get('stock')
            min_stock = selected_product_data.get('min_stock_level', 2)
            is_active = selected_product_data.get('is_active')

            # Stok durumu mesajı
            stock_status_msg = ""
            if not is_active:
                stock_status_msg = " [red](Pasif)[/]"
            elif current_stock is not None:
                if current_stock < 0: stock_status_msg = f" [bold white on red](EKSİ STOK: {current_stock})[/]"
                elif current_stock == 0: stock_status_msg = " [bold red](STOK 0!)[/]"
                elif current_stock <= min_stock: stock_status_msg = " [bold yellow](KRİTİK STOK!)[/]"

            console.print(f"   -> Seçilen: {product_name} ({brand_name or 'Markasız'}) (Mevcut Stok: {current_stock if current_stock is not None else '?'}){stock_status_msg}")

            # Miktar Al
            quantity = ui.get_positive_int_input(
                f"   -> Alınan Miktar ({product_name}): ", allow_zero=False)

            # Maliyet Al (Son maliyeti göstererek)
            last_cost_price = product_db_ops.get_last_cost_price(
                connection, product_id)
            cost_price_prompt = f"   -> Birim Alış Fiyatı (TL) "
            if last_cost_price is not None:
                cost_price_prompt += f"[Son: {last_cost_price:.2f}, Boş bırakırsanız bu kullanılır]: "
            else:
                cost_price_prompt += "[Daha önce alınmamış, boş bırakılabilir]: "

            cost_price = None
            while True: # Maliyet girdisini doğrula
                try:
                    cost_price_str = input(cost_price_prompt).strip().replace(',', '.')
                    if not cost_price_str: # Boş bırakıldıysa
                        if last_cost_price is not None:
                            cost_price = last_cost_price
                            console.print(f"   -> [dim]Son alış fiyatı ({cost_price:.2f} TL) kullanıldı.[/]")
                        else:
                            cost_price = None # Maliyet girilmedi (DB'de NULL olacak)
                            console.print("   -> [dim]Alış fiyatı girilmedi.[/]")
                        break # Döngüden çık
                    cost_price = Decimal(cost_price_str) # Decimal'e çevir
                    if cost_price < 0:
                        console.print(">>> HATA: Maliyet negatif olamaz.", style="yellow")
                    else:
                        break # Geçerli maliyet, döngüden çık
                except InvalidOperation:
                    console.print(">>> HATA: Geçersiz sayı formatı.", style="yellow")

            # SKT Al
            expiry_date = ui.get_date_input(f"   -> Son Kullanma Tarihi ({product_name})")

            # Listelere Ekle
            items_list_for_db.append({'product_id': product_id, 'quantity': quantity,
                                     'cost_price': cost_price, 'expiry_date': expiry_date})
            items_list_for_summary.append(
                {'barcode': product_barcode, 'name': product_name, 'quantity': quantity, 'cost_price': cost_price})
            console.print(
                f"   -> [green]{product_name} ({quantity} adet) alış listesine eklendi.[/]")

        # Ürün ekleme döngüsü bitti, özeti göster ve onayla
        if items_list_for_db:
            console.print("\n--- Alış Özeti ---", style="bold")
            supplier_display = selected_supplier_name or "Belirtilmedi"
            supplier_id_display = f"(ID: {selected_supplier_id})" if selected_supplier_id else ""
            console.print(f"Tedarikçi: {supplier_display} {supplier_id_display}", style="cyan")
            console.print(f"Fatura No: {purchase_info.get('invoice_number') or '-'}", style="cyan")
            if purchase_info.get('notes'):
                console.print(f"Notlar: {purchase_info.get('notes')}", style="cyan")

            ui.display_purchase_summary(items_list_for_summary)

            if ui.get_yes_no_input("\nBu alış kaydını onaylıyor musunuz? (Stoklar güncellenecektir)"):
                try:
                    purchase_id = product_db_ops.record_purchase(
                        connection, purchase_info, items_list_for_db)
                    if purchase_id:
                        log_details = f"Alış ID: {purchase_id}, Tedarikçi ID: {selected_supplier_id}, Ürün Sayısı: {len(items_list_for_db)}"
                        loglama.log_activity(connection, current_user_id, loglama.LOG_ACTION_STOCK_PURCHASE, log_details)
                    else:
                        # Hata mesajı DB katmanında veriliyor olmalı
                        console.print(">>> Alış kaydı yapılamadı.", style="red")
                except (DatabaseError, SaleIntegrityError, ValueError) as db_err:
                    # Hata mesajı zaten DB katmanında veya burada yakalanan try bloğunda veriliyor.
                    pass
                except Exception as e:
                    console.print(f">>> BEKLENMEDİK HATA (Alış Kaydı): {e}", style="bold red")
            else:
                console.print("Alış kaydı iptal edildi.", style="yellow")

    except UserInputError: # _find_product_for_management içinde 0 girilirse
         if not items_list_for_db: # Liste hala boşsa
             console.print("Alış listesine ürün eklenmedi, işlem iptal edildi.", style="yellow")
         # Eğer listede ürün varsa, UserInputError'dan sonra özete devam eder (yukarıdaki if items_list_for_db bloğu çalışır)
    except Exception as e:
        console.print(f">>> STOK GİRİŞİ SIRASINDA BEKLENMEDİK HATA: {e}", style="bold red")
        console.print_exception(show_locals=False)

def handle_toggle_product_status(connection, current_user_id):
    """Bir ürünün aktif/pasif durumunu değiştirir ve loglar."""
    console.print("\n--- Ürün Aktif/Pasif Yap ---", style="bold blue")
    product_data = _find_product_for_management(
        connection, prompt_message="Durumu değiştirilecek Ürünün Barkodunu veya Adını girin: ")
    if not product_data:
        return

    product_id = product_data.get('product_id')
    product_name = product_data.get('name')
    is_active = product_data.get('is_active')

    current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
    action_text = "Pasif" if is_active else "Aktif"
    prompt = f">>> '{product_name}' şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

    if ui.get_yes_no_input(prompt):
        try:
            success = False
            new_status = ""
            if is_active:
                success = product_db_ops.deactivate_product(connection, product_id)
                new_status = "Pasif"
            else:
                success = product_db_ops.reactivate_product(connection, product_id)
                new_status = "Aktif"

            if success:
                log_details = f"Ürün ID: {product_id}, Ad: {product_name}, Yeni Durum: {new_status}"
                loglama.log_activity(connection, current_user_id, loglama.LOG_ACTION_PRODUCT_STATUS_CHANGE, log_details)
            # else: Hata mesajı DB fonksiyonunda veriliyor

        except DatabaseError as e:
            console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
        except Exception as e:
            console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")
    else:
        console.print("İşlem iptal edildi.", style="yellow")

def handle_price_check(connection):
    """Kullanıcıdan alınan barkod veya isme göre ürünün fiyatını sorgular ve gösterir."""
    console.print("\n--- Fiyat Sorgula ---", style="bold blue")
    while True:
        user_input = ui.get_non_empty_input(
            "Fiyatı sorgulanacak Ürünün Barkodunu veya Adını girin (Çıkmak için '0'): ")
        if user_input == '0':
            console.print("Fiyat sorgulama iptal edildi.", style="yellow")
            break

        product_list = []
        product_dict = None
        try:
            # Önce barkodla ara
            if user_input.isdigit():
                product_dict = product_db_ops.get_product_by_barcode(connection, user_input, only_active=True) # Sadece aktif

            # Barkodla bulunamazsa isimle ara
            if not product_dict:
                product_list = product_db_ops.get_products_by_name_like(connection, user_input, only_active=True) # Sadece aktif
            elif product_dict:
                product_list = [product_dict] # Tek elemanlı liste yap

            # Sonuçları değerlendir
            if not product_list:
                console.print(f">>> '{user_input}' ile eşleşen aktif ürün bulunamadı.", style="yellow")
            elif len(product_list) == 1:
                found_product = product_list[0]
                name = found_product.get('name', '?')
                brand = found_product.get('brand_name')
                price = found_product.get('selling_price', None)
                brand_text = f" ({brand})" if brand else ""
                if price is not None:
                    console.print(f"\n>>> [cyan]{name}[/]{brand_text} - Satış Fiyatı: [bold yellow]{price:.2f} TL[/]")
                else:
                    console.print(f"\n>>> [cyan]{name}[/]{brand_text} için fiyat bilgisi bulunamadı.", style="yellow")
            else: # Birden fazla bulundu
                console.print(
                    f"\n>>> '{user_input}' ile eşleşen birden fazla aktif ürün bulundu:")
                select_table = Table(show_header=True, header_style="blue")
                select_table.add_column("No", style="dim")
                select_table.add_column("Ad", style="cyan")
                select_table.add_column("Marka", style="magenta")
                select_table.add_column("Fiyat", style="yellow")
                # Numaralandırarak göster
                [select_table.add_row(
                    f"{i}.",
                    p.get('name', '?'),
                    p.get('brand_name', '-') or "-",
                    f"{p.get('selling_price',0):.2f} TL"
                 ) for i, p in enumerate(product_list, 1)]
                console.print(select_table)
                while True: # Seçim iste
                    prompt = f"Fiyatı gösterilecek No (1-{len(product_list)}, İptal için 0): "
                    choice_num = ui.get_positive_int_input(prompt, allow_zero=True)
                    if choice_num == 0:
                        console.print("Seçim iptal edildi.", style="yellow")
                        break # İç döngüden çık
                    elif 1 <= choice_num <= len(product_list):
                        selected_product = product_list[choice_num - 1]
                        name = selected_product.get('name', '?')
                        brand = selected_product.get('brand_name')
                        price = selected_product.get('selling_price', None)
                        brand_text = f" ({brand})" if brand else ""
                        if price is not None:
                            console.print(f"\n>>> [cyan]{name}[/]{brand_text} - Satış Fiyatı: [bold yellow]{price:.2f} TL[/]")
                        else:
                            console.print(f"\n>>> [cyan]{name}[/]{brand_text} için fiyat bilgisi bulunamadı.", style="yellow")
                        break # İç döngüden çık
                    else:
                        console.print(f">>> Geçersiz numara!", style="red")
        except DatabaseError as e:
            console.print(f">>> VERİTABANI HATASI (Fiyat Sorgulama): {e}", style="bold red")
            break # Hata durumunda ana döngüden çık
        except Exception as e:
            console.print(f">>> BEKLENMEDİK HATA (Fiyat Sorgulama): {e}", style="bold red")
            break # Hata durumunda ana döngüden çık

def handle_stock_adjustment(connection, current_user_id):
    """Kullanıcıdan ürün seçmesini ve yeni stok miktarını girmesini isteyerek stoğu günceller ve loglar."""
    console.print("\n--- Stok Sayım / Düzeltme ---", style="bold blue")
    product_data = _find_product_for_management(
        connection, "Stoğu düzeltilecek ürünün Barkodunu veya Adını girin: ")
    if not product_data:
        return

    product_id = product_data.get('product_id')
    product_name = product_data.get('name')
    current_stock = product_data.get('stock')
    current_stock_display = current_stock if current_stock is not None else 'Bilinmiyor'

    console.print(f"\nSeçilen Ürün: [cyan]{product_name}[/]")
    console.print(f"Mevcut Sistem Stoğu: [yellow]{current_stock_display}[/]")

    while True:
        try:
            new_stock_str = input(
                "Yeni (Sayılan) Stok Miktarını Girin: ").strip()
            if not new_stock_str:
                console.print(">>> HATA: Stok miktarı boş bırakılamaz.", style="red")
                continue
            new_stock_level = int(new_stock_str)
            # Negatif stok girişi yapılabilir mi? Şimdilik izin verelim.
            break
        except ValueError:
            console.print(">>> HATA: Geçersiz giriş. Lütfen bir tam sayı girin.", style="red")

    if ui.get_yes_no_input(f">>> '{product_name}' stoğu {current_stock_display} -> {new_stock_level} olarak güncellensin mi?"):
        try:
            success = product_db_ops.set_stock_level(
                connection, product_id, new_stock_level)
            if success:
                log_details = f"Ürün ID: {product_id}, Ad: {product_name}, Eski Stok: {current_stock_display}, Yeni Stok: {new_stock_level}"
                loglama.log_activity(connection, current_user_id, loglama.LOG_ACTION_STOCK_ADJUSTMENT, log_details)
            # else: Hata mesajı DB fonksiyonunda veriliyor
        except DatabaseError as e:
            console.print(f">>> VERİTABANI HATASI (Stok Ayarlama): {e}", style="bold red")
        except Exception as e:
            console.print(f">>> BEKLENMEDİK HATA (Stok Ayarlama): {e}", style="bold red")
    else:
        console.print("Stok güncelleme işlemi iptal edildi.", style="yellow")

def handle_print_shelf_label(connection, current_user_id):
    """Kullanıcıdan ürün seçmesini ve formatlanmış raf etiketini göstermesini sağlar."""
    console.print("\n--- Raf Etiketi Yazdır ---", style="bold blue")
    product_data = _find_product_for_management(
        connection, "Etiketi yazdırılacak ürünün Barkodunu veya Adını girin: ")
    if not product_data:
        console.print("Etiket yazdırmak için ürün seçilmedi.", style="yellow")
        return

    product_id = product_data.get('product_id')
    try:
        # Etiketi yazdırma işlemi için yazdirma_islemleri modülünü kullan
        print_handlers.format_shelf_label(product_data)
        # Başarılı yazdırma loglanabilir (opsiyonel)
        # log_details = f"Ürün ID: {product_id}, Ad: {product_data.get('name', '?')}"
        # loglama.log_activity(connection, current_user_id, "ETIKET_YAZDIRMA", log_details)

    except AttributeError:
        # Eğer yazdirma_islemleri modülünde format_shelf_label fonksiyonu yoksa
        console.print(
            "[bold red]HATA: Etiket formatlama fonksiyonu ('format_shelf_label') 'yazdirma_islemleri.py' dosyasında bulunamadı.[/]")
    except DatabaseError as e: # get_product_by_id hatası (gerçi _find_product_for_management zaten bulmuştu)
        console.print(f">>> VERİTABANI HATASI (Etiket Verisi Alma): {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Etiket Yazdırma): {e}", style="bold red")
        console.print_exception(show_locals=False)

def handle_export_products(connection, current_user_id):
    """Ürünleri CSV dosyasına aktarma işlemini yönetir."""
    console.print("\n--- Ürünleri CSV Dosyasına Aktar ---", style="bold blue")
    default_filename = f"urun_listesi_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    filename = ui.get_optional_string_input(
        "Kaydedilecek dosya adı", default_filename)
    if not filename:
        console.print("[red]HATA: Dosya adı boş bırakılamaz.[/]")
        return

    if not filename.lower().endswith(".csv"):
        filename += ".csv"

    console.print(f"Ürünler '{filename}' dosyasına aktarılıyor...")
    try:
        success = veri_aktarim.export_products_to_csv(connection, filename)
        # Başarı/hata mesajı export_products_to_csv içinde veriliyor.
        # if success:
        #    loglama.log_activity(connection, current_user_id, "URUN_DISA_AKTAR", f"Dosya: {filename}")
    except Exception as e:
        # veri_aktarim içindeki hatalar zaten orada yakalanıyor ama ne olur ne olmaz
        console.print(
            f"[bold red]Dışa aktarma sırasında beklenmedik bir hata oluştu: {e}[/]")

def handle_import_products(connection, current_user_id):
    """Ürünleri CSV dosyasından içe aktarma işlemini yönetir."""
    console.print("\n--- Ürünleri CSV Dosyasından İçe Aktar ---",
                  style="bold blue")
    console.print(
        "[yellow]UYARI: Bu işlem mevcut ürünleri güncelleyebilir veya yeni ürün ekleyebilir.[/]")
    console.print("[dim]CSV dosyasının başlıkları şu sırada olmalıdır:[/]")
    console.print(f"[dim]{';'.join(veri_aktarim.CSV_HEADERS)}[/]")
    console.print("[dim]Ayırıcı olarak noktalı virgül (;) kullanılmalıdır.[/]")
    console.print("[dim]Sayısal alanlardaki (Fiyat, Stok vb.) TL, % gibi ifadeler ve boşluklar otomatik temizlenmeye çalışılacaktır.[/]")
    console.print("[dim]Ondalık ayracı olarak virgül (,) veya nokta (.) kullanabilirsiniz.[/]")


    filename = ui.get_non_empty_input(
        "İçe aktarılacak CSV dosyasının adını girin")

    if not filename.lower().endswith(".csv"):
        filename += ".csv"

    if not os.path.exists(filename):
        console.print(f"[bold red]HATA: '{filename}' dosyası bulunamadı![/]")
        return

    if ui.get_yes_no_input(f"'{filename}' dosyasından ürünler içe aktarılsın mı?"):
        try:
            # İçe aktarma fonksiyonunu çağır
            added, updated, skipped = veri_aktarim.import_products_from_csv(
                connection, filename)
            # Özet mesajı import_products_from_csv içinde veriliyor.
            # loglama.log_activity(connection, current_user_id, "URUN_ICE_AKTAR", f"Dosya: {filename}, E:{added}, G:{updated}, A:{skipped}")

        except Exception as e:
            console.print(
                f"[bold red]İçe aktarma sırasında beklenmedik bir hata oluştu: {e}[/]")
            console.print_exception(show_locals=False)
    else:
        console.print("İçe aktarma işlemi iptal edildi.", style="yellow")
