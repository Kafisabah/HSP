# tedarikci_islemleri.py
# Tedarikçi ekleme, listeleme, güncelleme, durum değiştirme ve seçme
# ile ilgili kullanıcı etkileşimlerini yönetir.
# v2: find_supplier fonksiyonu select_supplier olarak güncellendi,
#     bulunamadığında yeni ekleme seçeneği eklendi.
# v3: select_supplier fonksiyonunda tek sonuç bulunduğunda tuple index hatası düzeltildi.

import arayuz_yardimcilari as ui
import tedarikci_veritabani as supplier_db_ops
from hatalar import DatabaseError, DuplicateEntryError
from rich.console import Console
from rich.table import Table

console = ui.console

# === Yardımcı Fonksiyon: Tedarikçi Listesi Gösterme ===
# (display_supplier_list arayuz_yardimcilari.py içinde)

# === Handler Fonksiyonları ===


def handle_add_supplier(connection):
    """Yeni tedarikçi ekleme işlemini yönetir."""
    console.print("\n--- Yeni Tedarikçi Ekle ---", style="bold blue")
    try:
        name = ui.get_non_empty_input("Tedarikçi Adı (*): ")
        contact_person = input("İlgili Kişi: ").strip() or None
        phone = input("Telefon: ").strip() or None
        email = input("E-posta: ").strip() or None
        address = input("Adres: ").strip() or None
        new_supplier_id = supplier_db_ops.add_supplier(
            connection, name, contact_person, phone, email, address)
        # Başarı mesajı add_supplier içinde veriliyor.
        return new_supplier_id  # Eklenen ID'yi döndür
    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
        return None
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
        return None
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Tedarikçi Ekleme): {e}", style="bold red")
        return None


def handle_list_suppliers(connection):
    """Tedarikçileri listeleme işlemini yönetir."""
    console.print("\n--- Tedarikçi Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input(
            "Pasif tedarikçiler de gösterilsin mi?")
        suppliers = supplier_db_ops.list_all_suppliers(
            connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        # display_supplier_list arayuz_yardimcilari içinde
        ui.display_supplier_list(
            suppliers, title=f"{status_text} Tedarikçiler")
    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")


def handle_update_supplier(connection):
    """Mevcut bir tedarikçiyi güncelleme işlemini yönetir."""
    console.print("\n--- Tedarikçi Güncelle ---", style="bold blue")
    # Güncellenecek tedarikçiyi bul/seç
    supplier_id, supplier_name, _ = select_supplier(
        connection, "Güncellenecek tedarikçinin Adı/Tel: ", allow_none=True, only_active=False)
    if supplier_id is None:
        console.print("Güncellenecek tedarikçi seçilmedi.", style="yellow")
        return

    try:
        # Mevcut bilgileri al
        current_data = supplier_db_ops.get_supplier_by_id(
            connection, supplier_id)
        if not current_data:
            console.print(
                f">>> Tedarikçi (ID: {supplier_id}) bulunamadı.", style="red")
            return

        current_name = current_data.get('name')
        current_contact = current_data.get('contact_person')
        current_phone = current_data.get('phone')
        current_email = current_data.get('email')
        current_address = current_data.get('address')

        console.print("\n--- Mevcut Bilgiler ---")
        console.print(
            f" ID: {supplier_id}\n Ad: {current_name}\n İlgili Kişi: {current_contact or '-'}\n Telefon: {current_phone or '-'}\n E-posta: {current_email or '-'}\n Adres: {current_address or '-'}")
        console.print(
            "--- Yeni Bilgiler (Değiştirmek istemediklerinizi boş bırakın) ---", style="dim")

        # Yeni bilgileri al
        new_name = ui.get_optional_string_input("Yeni Ad", current_name)
        if not new_name:  # İsim boş bırakılamaz
            console.print(
                ">>> HATA: Tedarikçi adı boş bırakılamaz.", style="red")
            return
        new_contact = ui.get_optional_string_input(
            "Yeni İlgili Kişi", current_contact)
        new_phone = ui.get_optional_string_input("Yeni Telefon", current_phone)
        new_email = ui.get_optional_string_input("Yeni E-posta", current_email)
        new_address = ui.get_optional_string_input(
            "Yeni Adres", current_address)

        # Veritabanını güncelle
        success = supplier_db_ops.update_supplier(
            connection, supplier_id, new_name, new_contact, new_phone, new_email, new_address
        )
        # Başarı/hata mesajı DB fonksiyonunda veriliyor.

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Tedarikçi Güncelleme): {e}", style="bold red")


def handle_toggle_supplier_status(connection):
    """Bir tedarikçinin aktif/pasif durumunu değiştirir."""
    console.print("\n--- Tedarikçi Aktif/Pasif Yap ---", style="bold blue")
    # Durumu değiştirilecek tedarikçiyi bul/seç (aktif/pasif hepsi)
    supplier_id, supplier_name, is_active = select_supplier(
        connection, "Durumu değiştirilecek Tedarikçinin Adı/Tel: ", allow_none=True, only_active=False)
    if supplier_id is None:
        console.print("İşlem yapılacak tedarikçi seçilmedi.", style="yellow")
        return

    try:
        current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
        action_text = "Pasif" if is_active else "Aktif"
        prompt = f">>> '{supplier_name}' şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

        if ui.get_yes_no_input(prompt):
            success = False
            if is_active:
                success = supplier_db_ops.deactivate_supplier(
                    connection, supplier_id)
            else:
                success = supplier_db_ops.reactivate_supplier(
                    connection, supplier_id)
            # Başarı/hata mesajları DB fonksiyonlarında veriliyor.
        else:
            console.print("İşlem iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")

# ***** BU FONKSİYON GÜNCELLENDİ (len(suppliers) == 1 bloğu düzeltildi) *****


def select_supplier(connection, prompt_message="Tedarikçi Adı/Tel: ", allow_none=False, only_active=True):
    """
    Kullanıcıdan tedarikçi seçmesini veya yeni tedarikçi eklemesini ister.
    Args:
        allow_none (bool): Kullanıcının tedarikçi seçmemesine izin ver.
        only_active (bool): Sadece aktif tedarikçileri mi ara/seç.
    Returns:
        tuple: (supplier_id, supplier_name, is_active) veya (None, None, None)
               Eğer allow_none=True ise ve kullanıcı boş geçerse (None, None, None) döner.
               Hata veya iptal durumunda (None, None, None) döner.
    """
    while True:
        search_term = input(
            f"{prompt_message} ([Y]eni Ekle, [B]oş Bırak): ").strip()

        if allow_none and not search_term:
            console.print("Tedarikçi seçilmedi.", style="dim")
            return None, None, None  # Boş bırakıldı

        if search_term.upper() == 'Y':
            new_supplier_id = handle_add_supplier(connection)
            if new_supplier_id:
                new_supplier_data = supplier_db_ops.get_supplier_by_id(
                    connection, new_supplier_id)
                if new_supplier_data:
                     # get_supplier_by_id sözlük döndürür, .get() kullanabiliriz
                     return new_supplier_data.get('supplier_id'), new_supplier_data.get('name'), new_supplier_data.get('is_active')
                else:
                     console.print(
                         "[red]Hata: Yeni eklenen tedarikçi bilgileri alınamadı.[/]")
                     return None, None, None
            else:
                console.print(
                    ">>> Tedarikçi eklenemedi, lütfen tekrar deneyin.", style="yellow")
                continue

        if not search_term:
            console.print(">>> Tedarikçi seçimi zorunludur.", style="red")
            continue

        try:
            suppliers = []
            is_phone = any(char.isdigit() for char in search_term)
            if is_phone:
                suppliers = supplier_db_ops.get_suppliers_by_phone_like(
                    connection, search_term, only_active=only_active)
            if not suppliers:
                suppliers = supplier_db_ops.get_suppliers_by_name_like(
                    connection, search_term, only_active=only_active)

            if not suppliers:
                console.print(
                    f">>> '{search_term}' ile eşleşen {'aktif' if only_active else ''} tedarikçi bulunamadı.", style="yellow")
                if ui.get_yes_no_input("Yeni tedarikçi eklemek veya tekrar aramak ister misiniz? (E: Yeni/Tekrar Dene / H: İptal)"):
                    continue
                else:
                    return None, None, None

            elif len(suppliers) == 1:
                # Arama fonksiyonları tuple listesi döndürüyor, index ile erişelim
                selected_tuple = suppliers[0]
                supplier_id = selected_tuple[0]
                supplier_name = selected_tuple[1]
                is_active = selected_tuple[2]
                status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
                console.print(
                    f">>> Tedarikçi bulundu: {supplier_name} (ID: {supplier_id}) {status_text}", style="green")
                return supplier_id, supplier_name, is_active

            else:  # Birden fazla tedarikçi bulundu
                console.print(
                    f"\n>>> '{search_term}' ile eşleşen birden fazla tedarikçi bulundu:")
                # display_supplier_list tuple veya dict listesi alabilir
                ui.display_supplier_list(
                    suppliers, title="Eşleşen Tedarikçiler")
                while True:
                    select_prompt = f"Seçilecek tedarikçinin No (1-{len(suppliers)}, Yeni Ekle: Y, İptal: 0): "
                    choice_input = input(select_prompt).strip()
                    if choice_input == '0':
                        console.print(
                            "Tedarikçi seçimi iptal edildi.", style="yellow")
                        break
                    elif choice_input.upper() == 'Y':
                        new_supplier_id = handle_add_supplier(connection)
                        if new_supplier_id:
                            new_supplier_data = supplier_db_ops.get_supplier_by_id(
                                connection, new_supplier_id)
                            if new_supplier_data:
                                 return new_supplier_data.get('supplier_id'), new_supplier_data.get('name'), new_supplier_data.get('is_active')
                            else:
                                 console.print(
                                     "[red]Hata: Yeni eklenen tedarikçi bilgileri alınamadı.[/]")
                                 return None, None, None
                        else:
                            console.print(
                                ">>> Tedarikçi eklenemedi, lütfen listeden seçin veya tekrar deneyin.", style="yellow")
                            continue
                    elif choice_input.isdigit():
                        choice_num = int(choice_input)
                        if 1 <= choice_num <= len(suppliers):
                            # Seçilen tuple'ı al
                            selected_tuple = suppliers[choice_num - 1]
                            supplier_id = selected_tuple[0]
                            supplier_name = selected_tuple[1]
                            is_active = selected_tuple[2]
                            status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
                            console.print(
                                f">>> Tedarikçi seçildi: {supplier_name} (ID: {supplier_id}) {status_text}", style="green")
                            return supplier_id, supplier_name, is_active
                        else:
                            console.print(f">>> Geçersiz numara!", style="red")
                    else:
                        console.print(">>> Geçersiz giriş!", style="red")
                continue

        except DatabaseError as e:
            console.print(
                f">>> VERİTABANI HATASI (Tedarikçi Arama/Seçme): {e}", style="bold red")
            return None, None, None
        except Exception as e:
            console.print(
                f">>> BEKLENMEDİK HATA (Tedarikçi Arama/Seçme): {e}", style="bold red")
            return None, None, None
