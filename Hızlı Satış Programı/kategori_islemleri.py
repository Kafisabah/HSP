# kategori_islemleri.py
# Kategori ekleme, listeleme, güncelleme, durum değiştirme ve seçme
# ile ilgili kullanıcı etkileşimlerini yönetir.
# v2: select_category fonksiyonundaki hatalı veritabanı çağrısı düzeltildi.

import arayuz_yardimcilari as ui
import kategori_veritabani as category_db_ops
from hatalar import DatabaseError, DuplicateEntryError
from rich.console import Console
from rich.table import Table

console = ui.console

# === Handler Fonksiyonları ===


def handle_add_category(connection):
    """Yeni kategori ekleme işlemini yönetir."""
    console.print("\n--- Yeni Kategori Ekle ---", style="bold blue")
    try:
        name = ui.get_non_empty_input("Kategori Adı (*): ")
        description = input("Açıklama (isteğe bağlı): ").strip() or None
        new_category_id = category_db_ops.add_category(
            connection, name, description)
        # Başarı mesajı DB fonksiyonunda veriliyor.
        return new_category_id  # Eklenen ID'yi döndür
    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
        return None
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
        return None
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Kategori Ekleme): {e}", style="bold red")
        return None


def handle_list_categories(connection):
    """Kategorileri listeleme işlemini yönetir."""
    console.print("\n--- Kategori Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input(
            "Pasif kategoriler de gösterilsin mi?")
        categories = category_db_ops.list_all_categories(
            connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        ui.display_category_list(
            categories, title=f"{status_text} Kategoriler")
    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")


def handle_update_category(connection):
    """Mevcut bir kategoriyi güncelleme işlemini yönetir."""
    console.print("\n--- Kategori Güncelle ---", style="bold blue")
    # Güncellenecek kategoriyi bul/seç
    category_id, category_name, _ = select_category(
        connection, "Güncellenecek Kategorinin Adı: ", allow_none=False, only_active=False)
    if category_id is None:
        console.print("Güncellenecek kategori seçilmedi.", style="yellow")
        return

    try:
        # Mevcut açıklama bilgisi lazım olabilir, tekrar çekelim
        current_data = None  # TODO: get_category_by_id fonksiyonu eklenebilir DB'ye
        # Şimdilik açıklamayı tekrar soralım
        console.print(f"Seçilen Kategori: {category_name} (ID: {category_id})")
        console.print(
            "--- Yeni Bilgiler (Değiştirmek istemediklerinizi boş bırakın) ---", style="dim")

        new_name = ui.get_optional_string_input(
            "Yeni Kategori Adı", category_name)
        if not new_name:  # İsim boş bırakılamaz
            console.print(
                ">>> HATA: Kategori adı boş bırakılamaz.", style="red")
            return
        # Mevcut açıklamayı alamadığımız için optional yerine normal input kullanalım
        new_description = input(
            "Yeni Açıklama (isteğe bağlı): ").strip() or None

        # Veritabanını güncelle
        success = category_db_ops.update_category(
            connection, category_id, new_name, new_description
        )
        # Başarı/hata mesajı DB fonksiyonunda veriliyor.

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Kategori Güncelleme): {e}", style="bold red")


def handle_toggle_category_status(connection):
    """Bir kategorinin aktif/pasif durumunu değiştirir."""
    console.print("\n--- Kategori Aktif/Pasif Yap ---", style="bold blue")
    # Durumu değiştirilecek kategoriyi bul/seç (aktif/pasif hepsi)
    category_id, category_name, is_active = select_category(
        connection, "Durumu değiştirilecek Kategorinin Adı: ", allow_none=False, only_active=False)
    if category_id is None:
        console.print("İşlem yapılacak kategori seçilmedi.", style="yellow")
        return

    try:
        current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
        action_text = "Pasif" if is_active else "Aktif"
        prompt = f">>> '{category_name}' şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

        if ui.get_yes_no_input(prompt):
            success = False
            if is_active:
                success = category_db_ops.deactivate_category(
                    connection, category_id)
            else:
                success = category_db_ops.reactivate_category(
                    connection, category_id)
            # Başarı/hata mesajları DB fonksiyonlarında veriliyor.
        else:
            console.print("İşlem iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")


# === Kategori Seçme Fonksiyonu (Ürün Ekleme/Güncelleme için) ===

# ***** BU FONKSİYON GÜNCELLENDİ (list_categories -> list_all_categories) *****
def select_category(connection, prompt_message="Kategori Adı: ", allow_none=False, only_active=True):
    """
    Kullanıcıdan kategori seçmesini veya yeni kategori eklemesini ister.
    Args:
        allow_none (bool): Kullanıcının kategori seçmemesine izin ver (örn. ürün güncellerken).
        only_active (bool): Sadece aktif kategorileri mi listele/seç.
    Returns:
        int: Seçilen veya yeni eklenen kategorinin ID'si.
             Eğer allow_none=True ise ve kullanıcı boş bırakırsa None döner.
             Hata veya iptal durumunda None döner.
    """
    while True:
        search_term = input(
            f"{prompt_message} ([Y]eni Ekle, [B]oş Bırak): ").strip()

        if allow_none and not search_term:
            console.print("[dim]Kategori seçilmedi.[/]")
            return None  # Boş bırakıldı

        if search_term.upper() == 'Y':
            new_category_id = handle_add_category(connection)
            if new_category_id:
                return new_category_id
            else:
                console.print(
                    ">>> Kategori eklenemedi, lütfen tekrar deneyin.", style="yellow")
                continue  # Tekrar kategori sormaya dön

        if not search_term:  # Boş bırakıldı ama allow_none=False ise
            console.print(
                ">>> Lütfen bir kategori adı girin, [Y]eni ekleyin veya [B]oş bırakın.", style="red")
            continue

        try:
            # Arama yap
            categories = category_db_ops.get_categories_by_name_like(
                connection, search_term, only_active=only_active)

            if not categories:
                console.print(
                    f">>> '{search_term}' ile eşleşen {'aktif' if only_active else ''} kategori bulunamadı.", style="yellow")
                if ui.get_yes_no_input("Yeni kategori eklemek veya tekrar aramak ister misiniz? (E: Yeni/Tekrar Dene / H: İptal)"):
                    continue  # Tekrar kategori sormaya dön
                else:
                    if allow_none:
                         console.print("[dim]Kategori seçilmedi.[/]")
                         return None
                    else:
                        console.print("Kategori seçimi iptal edildi.", style="yellow")
                        return None

            elif len(categories) == 1:
                selected = categories[0]
                category_id = selected.get('category_id')
                category_name = selected.get('name')
                is_active_flag = selected.get('is_active')
                status_text = "[green]Aktif[/]" if is_active_flag else "[red]Pasif[/]"
                console.print(f">>> Kategori seçildi: {category_name} (ID: {category_id}) {status_text}", style="green")
                return category_id  # Bulunan tek kategorinin ID'sini döndür

            else:  # Birden fazla kategori bulundu
                console.print(f"\n>>> '{search_term}' ile eşleşen birden fazla kategori bulundu:")
                # display_category_list arayuz_yardimcilari içinde
                ui.display_category_list(categories, title="Eşleşen Kategoriler")
                while True:
                    select_prompt = f"Seçilecek kategori No (1-{len(categories)}, Yeni Ekle: Y, İptal: 0): "
                    choice_input = input(select_prompt).strip()
                    if choice_input == '0':
                        console.print("Kategori seçimi iptal edildi.", style="yellow")
                        break  # İç döngüden çık, ana arama döngüsüne dön
                    elif choice_input.upper() == 'Y':
                        new_category_id = handle_add_category(connection)
                        if new_category_id:
                            return new_category_id
                        else:
                            console.print(">>> Kategori eklenemedi, lütfen listeden seçin veya tekrar deneyin.", style="yellow")
                            continue
                    elif choice_input.isdigit():
                        choice_num = int(choice_input)
                        if 1 <= choice_num <= len(categories):
                            selected = categories[choice_num - 1]
                            category_id = selected.get('category_id')
                            category_name = selected.get('name')
                            is_active_flag = selected.get('is_active')
                            status_text = "[green]Aktif[/]" if is_active_flag else "[red]Pasif[/]"
                            console.print(f">>> Kategori seçildi: {category_name} (ID: {category_id}) {status_text}", style="green")
                            return category_id  # Seçilen kategorinin ID'sini döndür
                        else:
                            console.print(f">>> Geçersiz numara!", style="red")
                    else:
                        console.print(">>> Geçersiz giriş!", style="red")
                continue  # İç döngüden çıkıldıysa (iptal), ana arama döngüsüne devam et

        except DatabaseError as e:
            console.print(f">>> VERİTABANI HATASI (Kategori Arama/Seçme): {e}", style="bold red")
            return None  # Ciddi hata, çık
        except Exception as e:
            console.print(f">>> BEKLENMEDİK HATA (Kategori Arama/Seçme): {e}", style="bold red")
            return None  # Ciddi hata, çık
