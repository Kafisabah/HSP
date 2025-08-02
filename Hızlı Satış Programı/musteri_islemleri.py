# musteri_islemleri.py
# Müşteri ekleme, listeleme, güncelleme, ödeme alma, ekstre gösterme,
# durum değiştirme ve kupon işlemleri ile ilgili kullanıcı etkileşimlerini yönetir.
# v28: Kupon işlemleri eklendi (handle_view_customer_coupons).
# v46: handle_customer_payment fonksiyonuna active_shift_id parametresi eklendi.
# v49: Müşteri işlemleri için loglama eklendi.
# v50: handle_customer_payment fonksiyonuna customer_payment_methods parametresi eklendi.

import arayuz_yardimcilari as ui
import musteri_veritabani as customer_db_ops
import loglama  # Loglama için import edildi
from hatalar import DatabaseError, DuplicateEntryError, UserInputError
from decimal import Decimal
from rich.console import Console
from rich.table import Table

console = ui.console

# === Yardımcı Fonksiyon: Müşteri Bul/Seç (Yönetim için) ===


def find_customer(connection, prompt_message, allow_none=False, only_active=True):
    """
    Yönetim işlemleri için müşteri arar ve seçtirir.
    Args:
        allow_none (bool): Seçim yapılmamasına izin ver.
        only_active (bool): Sadece aktif müşterileri mi ara.
    Returns:
        tuple: (customer_id, customer_name, is_active) veya (None, None, None)
    """
    while True:
        search_term = input(f"{prompt_message} (İptal için 0): ").strip()
        if search_term == '0':
            if allow_none:
                console.print("Müşteri seçilmedi.", style="dim")
                return None, None, None
            else:
                console.print("İşlem iptal edildi.", style="yellow")
                return None, None, None

        if not search_term and allow_none:  # Boş bırakılırsa ve izinliyse
            console.print("Müşteri seçilmedi.", style="dim")
            return None, None, None
        elif not search_term and not allow_none:
            console.print(
                ">>> Lütfen bir arama terimi girin veya iptal için 0 girin.", style="red")
            continue

        customer_list = []
        try:
            is_phone = search_term.isdigit() or '+' in search_term
            if is_phone:
                cust = customer_db_ops.get_customer_by_phone(
                    connection, search_term, only_active=only_active)
                if cust:
                    customer_list = [cust]  # Tek elemanlı liste yap
            # Telefonla bulunamazsa veya telefon değilse isimle ara
            if not customer_list:
                customer_list = customer_db_ops.get_customers_by_name_like(
                    connection, search_term, only_active=only_active)

            if not customer_list:
                console.print(
                    f">>> '{search_term}' ile eşleşen {'aktif' if only_active else ''} müşteri bulunamadı.", style="yellow")
                if not ui.get_yes_no_input("Tekrar aramak ister misiniz?"):
                    return None, None, None
                else:
                    continue  # Tekrar arama döngüsüne dön

            elif len(customer_list) == 1:
                cust_id, cust_name, is_active_flag = customer_list[0]
                status_text = "[green]Aktif[/]" if is_active_flag else "[red]Pasif[/]"
                console.print(
                    f">>> Müşteri bulundu: {cust_name} (ID: {cust_id}) {status_text}", style="green")
                return cust_id, cust_name, is_active_flag

            else:  # Birden fazla müşteri bulundu
                console.print(
                    f"\n>>> '{search_term}' ile eşleşen birden fazla müşteri bulundu:")
                # display_customer_list arayuz_yardimcilari içinde
                ui.display_customer_list(
                    customer_list, title="Eşleşen Müşteriler")
                while True:
                    select_prompt = f"Seçilecek müşteri No (1-{len(customer_list)}, İptal için 0): "
                    select_no = ui.get_positive_int_input(
                        select_prompt, allow_zero=True)
                    if select_no == 0:
                        console.print(
                            "Müşteri seçimi iptal edildi.", style="yellow")
                        break  # İç döngüden çık, ana arama döngüsüne dön
                    elif 1 <= select_no <= len(customer_list):
                        cust_id, cust_name, is_active_flag = customer_list[select_no - 1]
                        status_text = "[green]Aktif[/]" if is_active_flag else "[red]Pasif[/]"
                        console.print(
                            f">>> Müşteri seçildi: {cust_name} (ID: {cust_id}) {status_text}", style="green")
                        return cust_id, cust_name, is_active_flag
                    else:
                        console.print(">>> Geçersiz numara!", style="red")
                # İç döngüden çıkıldıysa (iptal), ana arama döngüsüne devam et
                continue

        except DatabaseError as e:
            console.print(
                f">>> VERİTABANI HATASI (Müşteri Arama): {e}", style="bold red")
            return None, None, None  # Ciddi hata, çık
        except Exception as e:
            console.print(
                f">>> BEKLENMEDİK HATA (Müşteri Arama): {e}", style="bold red")
            return None, None, None  # Ciddi hata, çık


# === Handler Fonksiyonları ===

def handle_add_customer(connection, current_user_id):
    """Yeni müşteri ekleme işlemini yönetir ve loglar."""
    console.print("\n--- Yeni Müşteri Ekle ---", style="bold blue")
    new_customer_id = None
    customer_name_for_log = None
    try:
        name = ui.get_non_empty_input("Müşteri Adı Soyadı (*): ")
        customer_name_for_log = name
        phone = input("Telefon: ").strip() or None
        email = input("E-posta: ").strip() or None
        address = input("Adres: ").strip() or None
        new_customer_id = customer_db_ops.add_customer(
            connection, name, phone, email, address)
        if new_customer_id:
            log_details = f"Müşteri ID: {new_customer_id}, Ad: {name}"
            loglama.log_activity(connection, current_user_id,
                                 loglama.LOG_ACTION_CUSTOMER_ADD, log_details)

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Müşteri Ekleme): {e}", style="bold red")


def handle_list_customers(connection):
    """Müşterileri listeleme işlemini yönetir."""
    console.print("\n--- Müşteri Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input(
            "Pasif müşteriler de gösterilsin mi?")
        customers = customer_db_ops.get_all_customers_detailed(
            connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        ui.display_customer_list_detailed(
            customers, title=f"{status_text} Müşteriler")
    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")


def handle_update_customer(connection, current_user_id):
    """Mevcut bir müşteriyi güncelleme işlemini yönetir ve loglar."""
    console.print("\n--- Müşteri Güncelle ---", style="bold blue")
    customer_id, customer_name, _ = find_customer(
        connection, "Güncellenecek Müşterinin Adı/Tel: ", only_active=False)
    if customer_id is None:
        console.print("Güncellenecek müşteri seçilmedi.", style="yellow")
        return

    try:
        current_data = customer_db_ops.get_customer_by_id(
            connection, customer_id)
        if not current_data:
            console.print(
                f">>> Müşteri (ID: {customer_id}) bulunamadı.", style="red")
            return

        current_name = current_data.get('name')
        current_phone = current_data.get('phone')
        current_email = current_data.get('email')
        current_address = current_data.get('address')

        console.print("\n--- Mevcut Bilgiler ---")
        console.print(
            f" ID: {customer_id}\n Ad Soyad: {current_name}\n Telefon: {current_phone or '-'}\n E-posta: {current_email or '-'}\n Adres: {current_address or '-'}")
        console.print(
            "--- Yeni Bilgiler (Değiştirmek istemediklerinizi boş bırakın) ---", style="dim")

        new_name = ui.get_optional_string_input("Yeni Ad Soyad", current_name)
        if not new_name:
            console.print(
                ">>> HATA: Müşteri adı boş bırakılamaz.", style="red")
            return
        new_phone = ui.get_optional_string_input("Yeni Telefon", current_phone)
        new_email = ui.get_optional_string_input("Yeni E-posta", current_email)
        new_address = ui.get_optional_string_input(
            "Yeni Adres", current_address)

        changes_made = (new_name != current_name or
                        new_phone != current_phone or
                        new_email != current_email or
                        new_address != current_address)

        if not changes_made:
            console.print("[yellow]>>> Hiçbir değişiklik yapılmadı.[/]")
            return

        success = customer_db_ops.update_customer(
            connection, customer_id, new_name, new_phone, new_email, new_address
        )

        if success and changes_made:
            log_details = f"Müşteri ID: {customer_id}, Yeni Ad: {new_name}"
            loglama.log_activity(connection, current_user_id,
                                 loglama.LOG_ACTION_CUSTOMER_UPDATE, log_details)

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Müşteri Güncelleme): {e}", style="bold red")

# ***** BU FONKSİYON GÜNCELLENDİ (customer_payment_methods parametresi eklendi) *****


def handle_customer_payment(connection, active_shift_id=None, current_user_id=None, customer_payment_methods=None):
    """Müşteriden ödeme alma işlemini yönetir ve loglar."""
    if customer_payment_methods is None:
        # Eğer ödeme yöntemleri gelmediyse, varsayılan bir liste kullanabilir veya hata verebiliriz.
        # Şimdilik hata verelim, çünkü bu bilgi ana programdan gelmeli.
        console.print(
            "[bold red]HATA: Müşteri ödeme yöntemleri belirtilmedi![/]")
        return

    console.print("\n--- Müşteri Ödeme Al ---", style="bold blue")
    customer_id, customer_name, _ = find_customer(
        connection, "Ödeme yapacak Müşterinin Adı/Tel: ", only_active=True)
    if customer_id is None:
        console.print(
            "Müşteri seçilmediği için ödeme alınamadı.", style="yellow")
        return

    try:
        current_balance = customer_db_ops.get_customer_balance(
            connection, customer_id)
        ui.display_customer_balance(customer_name, current_balance)

        if current_balance is None:
            console.print(f">>> Müşteri bakiyesi alınamadı.", style="red")
            return
        elif current_balance <= Decimal('0.00'):
            console.print(f">>> Bu müşterinin borcu bulunmuyor.",
                          style="yellow")
            return

        if not customer_payment_methods:  # Parametre olarak gelen liste boşsa
            console.print(
                ">>> HATA: Müşteri ödemesi için geçerli yöntem tanımlanmamış!", style="red")
            return

        console.print("\nÖdeme Yöntemleri:", style="bold")
        pay_method_map = {}
        # Parametreyi kullan
        for i, method in enumerate(customer_payment_methods, start=1):
            console.print(f"[yellow]{i}:[/] {method}")
            pay_method_map[str(i)] = method
        console.print("[yellow]0:[/] İptal")

        selected_pay_method = None
        while True:
            pay_method_choice = input(
                f"Ödeme yöntemi seçin (1-{len(customer_payment_methods)}, 0:İptal): ").strip()
            if pay_method_choice == '0':
                console.print(
                    "Ödeme yöntemi seçimi iptal edildi.", style="yellow")
                return
            elif pay_method_choice in pay_method_map:
                selected_pay_method = pay_method_map[pay_method_choice]
                break
            else:
                console.print(">>> Geçersiz seçim.", style="red")

        max_payment = current_balance
        payment_amount = ui.get_positive_decimal_input(
            f"{selected_pay_method} ile Ödenecek Tutar (Max: {max_payment:.2f}): ", allow_zero=False
        )
        if payment_amount > max_payment:
            console.print(
                f">>> HATA: Ödeme miktarı ({payment_amount:.2f}) müşterinin borcundan ({max_payment:.2f}) fazla olamaz!", style="red")
            return

        payment_notes = input("Ödeme Notu (isteğe bağlı): ").strip() or None

        if ui.get_yes_no_input(f">>> {customer_name} isimli müşteriden {payment_amount:.2f} TL ({selected_pay_method}) ödeme alınsın mı?"):
            payment_id = customer_db_ops.record_customer_payment(
                connection, customer_id, payment_amount, selected_pay_method, payment_notes, active_shift_id
            )
            if payment_id:
                log_details = f"Müşteri ID: {customer_id}, Ödeme ID: {payment_id}, Tutar: {payment_amount:.2f}, Yöntem: {selected_pay_method}"
                loglama.log_activity(
                    connection, current_user_id, loglama.LOG_ACTION_CUSTOMER_PAYMENT, log_details)

                new_balance = customer_db_ops.get_customer_balance(
                    connection, customer_id)
                ui.display_customer_balance(
                    customer_name + " (Yeni Bakiye)", new_balance)
        else:
            console.print("Ödeme alma işlemi iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Müşteri Ödeme): {e}", style="bold red")
    except ValueError as ve:
        console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Müşteri Ödeme): {e}", style="bold red")


def handle_customer_ledger(connection):
    """Müşteri hesap ekstresi görüntüleme işlemini yönetir."""
    console.print("\n--- Müşteri Hesap Ekstresi ---", style="bold blue")
    customer_id, customer_name, _ = find_customer(
        connection, "Ekstresi görüntülenecek Müşterinin Adı/Tel: ", only_active=False)
    if customer_id is None:
        console.print(
            "Müşteri seçilmediği için ekstre görüntülenemedi.", style="yellow")
        return

    try:
        console.print("\n(İsteğe bağlı) Ekstre için tarih aralığı girin:")
        start_date = ui.get_date_input("Başlangıç Tarihi")
        end_date = ui.get_date_input("Bitiş Tarihi")
        if start_date and end_date and start_date > end_date:
            console.print(
                ">>> HATA: Başlangıç tarihi, bitiş tarihinden sonra olamaz.", style="bold red")
            return

        ledger_entries = customer_db_ops.get_customer_ledger(
            connection, customer_id, start_date, end_date)
        current_balance = customer_db_ops.get_customer_balance(
            connection, customer_id)
        ui.display_customer_ledger(
            customer_name, ledger_entries, current_balance)

    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Hesap Ekstresi): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Hesap Ekstresi): {e}", style="bold red")


def handle_toggle_customer_status(connection, current_user_id):
    """Bir müşterinin aktif/pasif durumunu değiştirir ve loglar."""
    console.print("\n--- Müşteri Aktif/Pasif Yap ---", style="bold blue")
    customer_id, customer_name, is_active = find_customer(
        connection, "Durumu değiştirilecek Müşterinin Adı/Tel: ", only_active=False)
    if customer_id is None:
        console.print("İşlem yapılacak müşteri seçilmedi.", style="yellow")
        return

    try:
        current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
        action_text = "Pasif" if is_active else "Aktif"
        prompt = f">>> '{customer_name}' şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

        if ui.get_yes_no_input(prompt):
            success = False
            if is_active:
                success = customer_db_ops.deactivate_customer(
                    connection, customer_id)
                new_status = "Pasif"
            else:
                success = customer_db_ops.reactivate_customer(
                    connection, customer_id)
                new_status = "Aktif"

            if success:
                log_details = f"Müşteri ID: {customer_id}, Ad: {customer_name}, Yeni Durum: {new_status}"
                loglama.log_activity(
                    connection, current_user_id, loglama.LOG_ACTION_CUSTOMER_STATUS_CHANGE, log_details)

        else:
            console.print("İşlem iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")


def handle_view_customer_coupons(connection):
    """Müşterinin kullanılabilir kuponlarını görüntüleme işlemini yönetir."""
    console.print("\n--- Müşteri Kuponlarını Görüntüle ---", style="bold blue")
    customer_id, customer_name, _ = find_customer(
        connection, "Kuponları görüntülenecek Müşterinin Adı/Tel: ", only_active=True)
    if customer_id is None:
        console.print(
            "Müşteri seçilmediği için kuponlar görüntülenemedi.", style="yellow")
        return

    try:
        coupons = customer_db_ops.get_customer_available_coupons(
            connection, customer_id)
        if not coupons:
            console.print(
                f">>> '{customer_name}' için kullanılabilir kupon bulunmamaktadır.", style="yellow")
        else:
            ui.display_customer_coupons(coupons, customer_name)
    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Kupon Görüntüleme): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Kupon Görüntüleme): {e}", style="bold red")
