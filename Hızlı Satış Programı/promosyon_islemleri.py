# promosyon_islemleri.py
# Promosyon ekleme, listeleme, durum değiştirme ile ilgili
# kullanıcı etkileşimlerini yönetir.
# v2: BOGO ve BuyXGetYFree promosyon türleri için arayüz güncellemeleri yapıldı.

import arayuz_yardimcilari as ui
import promosyon_veritabani as promo_db_ops
import urun_islemleri as product_handlers  # Ürün seçmek için
import urun_veritabani as product_db_ops  # Ürün ID'si ile isim getirmek için
from hatalar import DatabaseError, DuplicateEntryError, UserInputError
from decimal import Decimal, InvalidOperation
from rich.console import Console
from rich.table import Table
import datetime

console = ui.console

# === Yardımcı Fonksiyon: Promosyon Listesi Gösterme ===

# ***** BU FONKSİYON GÜNCELLENDİ (Farklı promosyon türlerini gösterme) *****


def display_promotion_list(promotions, title="Promosyon Listesi"):
    """Verilen promosyon listesini tablo olarak gösterir."""
    if not promotions:
        console.print(
            f">>> {title} için gösterilecek promosyon yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    # Koşul ve İndirim sütunlarını birleştirip "Detay" yapalım
    headers = ["ID", "Ad", "Ürün", "Detay", "Başlangıç", "Bitiş", "Durum"]
    table.add_column(headers[0], style="dim", justify="right")
    table.add_column(headers[1], style="cyan", min_width=20)
    table.add_column(headers[2], style="green", min_width=15)  # Ürün Adı
    table.add_column(headers[3], style="white", min_width=30)  # Detay
    table.add_column(headers[4], style="dim",
                     justify="center")  # Başlangıç Tarihi
    table.add_column(headers[5], style="dim", justify="center")  # Bitiş Tarihi
    table.add_column(headers[6], justify="center")  # Durum

    for promo in promotions:
        status = "[green]Aktif[/]" if promo.get(
            'is_active') else "[red]Pasif[/]"
        product_name = promo.get(
            'product_name', f"ID:{promo.get('product_id')}")
        promo_type = promo.get('promotion_type')
        detail_str = ""

        if promo_type == 'quantity_discount':
            req_qty = promo.get('required_quantity', '?')
            disc_amount = promo.get('discount_amount', 0)
            detail_str = f"{req_qty} adet alana [bold yellow]{disc_amount:.2f} TL[/] indirim"
        elif promo_type == 'bogo':  # Buy One Get One
            free_prod_name = promo.get('free_product_name')
            if free_prod_name:  # Farklı ürün bedava
                detail_str = f"1 adet alana 1 adet [bold blue]{free_prod_name}[/] bedava"
            else:  # Aynı ürün bedava
                detail_str = f"1 adet alana 1 adet [bold blue](Aynı Ürün)[/] bedava"
        elif promo_type == 'buy_x_get_y_free':
            req_qty = promo.get('required_bogo_quantity', '?')
            free_qty = promo.get('free_quantity', '?')
            free_prod_name = promo.get('free_product_name')
            if free_prod_name:  # Farklı ürün bedava
                 detail_str = f"{req_qty} adet alana {free_qty} adet [bold blue]{free_prod_name}[/] bedava"
            else:  # Aynı ürün bedava
                 detail_str = f"{req_qty} adet alana {free_qty} adet [bold blue](Aynı Ürün)[/] bedava"
        else:
            detail_str = "[red]Bilinmeyen Tür[/]"

        start_date = promo.get('start_date')
        end_date = promo.get('end_date')
        start_date_str = start_date.strftime(
            '%d-%m-%Y') if isinstance(start_date, (datetime.date, datetime.datetime)) else "-"
        end_date_str = end_date.strftime(
            '%d-%m-%Y') if isinstance(end_date, (datetime.date, datetime.datetime)) else "-"

        table.add_row(
            str(promo.get('promotion_id', '-')),
            promo.get('name', '-'),
            product_name,
            detail_str,  # Güncellenmiş detay
            start_date_str,
            end_date_str,
            status
        )
    console.print(table)
    console.print(f"\nToplam {len(promotions)} promosyon listelendi.")

# === Handler Fonksiyonları ===

# ***** BU FONKSİYON GÜNCELLENDİ (Promosyon türü seçme ve ilgili alanları isteme) *****


def handle_add_promotion(connection):
    """Yeni promosyon ekleme işlemini yönetir."""
    console.print("\n--- Yeni Promosyon Ekle ---", style="bold blue")
    try:
        name = ui.get_non_empty_input("Promosyon Adı (*): ")
        description = input("Açıklama (isteğe bağlı): ").strip() or None

        # Promosyon Türünü Seçtir
        promo_types = {
            '1': 'quantity_discount',
            '2': 'bogo',
            '3': 'buy_x_get_y_free'
        }
        console.print("\nPromosyon Türünü Seçin:")
        console.print(" [1]: Miktar İndirimi (X adet alana Y TL indirim)")
        console.print(" [2]: Bir Alana Bir Bedava (BOGO)")
        console.print(" [3]: X Alana Y Bedava")
        while True:
            type_choice = input("Seçiminiz (1-3): ").strip()
            if type_choice in promo_types:
                promotion_type = promo_types[type_choice]
                break
            else:
                console.print(">>> Geçersiz seçim!", style="red")

        console.print(
            f"\n[dim]Promosyonun uygulanacağı ana ürünü seçin ({promotion_type}):[/]")
        selected_product = product_handlers._find_product_for_management(
            connection, "Ana Ürün Barkodu/Adı: ")
        if not selected_product:
            console.print(
                ">>> Ürün seçilmediği için promosyon ekleme iptal edildi.", style="yellow")
            return None
        product_id = selected_product.get('product_id')
        product_name = selected_product.get('name')
        console.print(f"   -> Ana Ürün: [cyan]{product_name}[/]")

        # Tür'e göre parametreleri al
        required_quantity = None
        discount_amount = None
        required_bogo_quantity = None
        free_quantity = None
        free_product_id = None
        free_product_name = "(Aynı Ürün)"  # Varsayılan

        if promotion_type == 'quantity_discount':
            required_quantity = ui.get_positive_int_input(
                "İndirim için Gerekli Minimum Miktar: ", allow_zero=False)
            discount_amount = ui.get_positive_decimal_input(
                "Uygulanacak İndirim Tutarı (TL): ", allow_zero=False)
        elif promotion_type == 'bogo':
            required_bogo_quantity = 1  # BOGO için alınan miktar 1'dir
            free_quantity = 1  # BOGO için bedava miktar 1'dir
            if ui.get_yes_no_input("Bedava verilecek ürün ana üründen farklı mı?"):
                console.print("[dim]Bedava verilecek ürünü seçin:[/]")
                free_selected_product = product_handlers._find_product_for_management(
                    connection, "Bedava Ürün Barkodu/Adı: ")
                if not free_selected_product:
                     console.print(
                         ">>> Bedava ürün seçilmediği için iptal edildi.", style="yellow")
                     return None
                free_product_id = free_selected_product.get('product_id')
                free_product_name = free_selected_product.get('name')
                console.print(
                     f"   -> Bedava Ürün: [cyan]{free_product_name}[/]")
            # else: free_product_id None kalır (aynı ürün)
        elif promotion_type == 'buy_x_get_y_free':
            required_bogo_quantity = ui.get_positive_int_input(
                "Bedava için Alınması Gereken Miktar (X): ", allow_zero=False)
            free_quantity = ui.get_positive_int_input(
                "Bedava Verilecek Miktar (Y): ", allow_zero=False)
            if ui.get_yes_no_input("Bedava verilecek ürün ana üründen farklı mı?"):
                console.print("[dim]Bedava verilecek ürünü seçin:[/]")
                free_selected_product = product_handlers._find_product_for_management(
                    connection, "Bedava Ürün Barkodu/Adı: ")
                if not free_selected_product:
                     console.print(
                         ">>> Bedava ürün seçilmediği için iptal edildi.", style="yellow")
                     return None
                free_product_id = free_selected_product.get('product_id')
                free_product_name = free_selected_product.get('name')
                console.print(
                     f"   -> Bedava Ürün: [cyan]{free_product_name}[/]")
            # else: free_product_id None kalır (aynı ürün)

        start_date = ui.get_date_input(
            "Başlangıç Tarihi (GG-AA-YYYY, boş bırakılırsa hemen başlar)")
        end_date = ui.get_date_input(
            "Bitiş Tarihi (GG-AA-YYYY, boş bırakılırsa süresiz)")

        if start_date and end_date and start_date > end_date:
            console.print(
                "[bold red]HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.[/]")
            return None

        # Onay al
        console.print("\n--- Promosyon Özeti ---")
        console.print(f" Ad: {name}")
        console.print(f" Açıklama: {description or '-'}")
        console.print(f" Tür: {promotion_type}")
        console.print(f" Ana Ürün: {product_name} (ID: {product_id})")
        if promotion_type == 'quantity_discount':
            console.print(f" Koşul: {required_quantity} adet alana")
            console.print(f" İndirim: {discount_amount:.2f} TL")
        elif promotion_type in ['bogo', 'buy_x_get_y_free']:
            console.print(f" Koşul: {required_bogo_quantity} adet alana")
            console.print(
                f" Bedava: {free_quantity} adet {free_product_name}")

        start_date_str = start_date.strftime(
            '%d-%m-%Y') if start_date else "Hemen"
        end_date_str = end_date.strftime('%d-%m-%Y') if end_date else "Süresiz"
        console.print(f" Geçerlilik: {start_date_str} - {end_date_str}")

        if ui.get_yes_no_input("\nBu promosyon eklensin mi?"):
            new_promo_id = promo_db_ops.add_promotion(
                connection, name, description, promotion_type, product_id,
                required_quantity, discount_amount,
                required_bogo_quantity, free_quantity, free_product_id,
                start_date, end_date
            )
            # Başarı mesajı add_promotion içinde veriliyor.
            return new_promo_id
        else:
            console.print("Promosyon ekleme iptal edildi.", style="yellow")
            return None

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
        return None
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
        return None
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Promosyon Ekleme): {e}", style="bold red")
        console.print_exception(show_locals=False)  # Detaylı hata için
        return None


def handle_list_promotions(connection):
    """Promosyonları listeleme işlemini yönetir."""
    console.print("\n--- Promosyon Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input(
            "Pasif promosyonlar da gösterilsin mi?")
        promotions = promo_db_ops.list_all_promotions(
            connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        display_promotion_list(promotions, title=f"{status_text} Promosyonlar")
    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")


def handle_toggle_promotion_status(connection):
    """Bir promosyonun aktif/pasif durumunu değiştirir."""
    console.print("\n--- Promosyon Aktif/Pasif Yap ---", style="bold blue")
    try:
        # Önce listeyi gösterelim, kullanıcı ID ile seçsin
        promotions = promo_db_ops.list_all_promotions(
            connection, include_inactive=True)
        if not promotions:
            console.print(">>> Henüz tanımlı promosyon yok.", style="yellow")
            return

        display_promotion_list(promotions, title="Tüm Promosyonlar")

        while True:
            promo_id_str = input(
                "Durumu değiştirilecek Promosyon ID'sini girin (İptal için 0): ").strip()
            if promo_id_str == '0':
                console.print("İşlem iptal edildi.", style="yellow")
                return
            if promo_id_str.isdigit():
                promo_id = int(promo_id_str)
                # Seçilen ID listede var mı kontrol et
                selected_promo = next(
                    (p for p in promotions if p.get('promotion_id') == promo_id), None)
                if selected_promo:
                     break  # Geçerli ID bulundu
                else:
                     console.print(
                         f">>> Geçersiz Promosyon ID: {promo_id}", style="red")
            else:
                console.print(">>> Lütfen geçerli bir ID girin.", style="red")

        # Seçilen promosyonun bilgilerini al
        promo_name = selected_promo.get('name')
        is_active = selected_promo.get('is_active')
        current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
        action_text = "Pasif" if is_active else "Aktif"
        prompt = f">>> '{promo_name}' (ID: {promo_id}) şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

        if ui.get_yes_no_input(prompt):
            success = False
            if is_active:
                success = promo_db_ops.deactivate_promotion(
                    connection, promo_id)
            else:
                success = promo_db_ops.reactivate_promotion(
                    connection, promo_id)
            # Başarı/hata mesajları DB fonksiyonlarında veriliyor.
        else:
            console.print("İşlem iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")

# TODO: handle_update_promotion fonksiyonu eklenebilir.
