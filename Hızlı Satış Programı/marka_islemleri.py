# marka_islemleri.py
# Marka ekleme, listeleme, durum değiştirme ve seçme ile ilgili
# kullanıcı etkileşimlerini yönetir.

import arayuz_yardimcilari as ui
import marka_veritabani as brand_db_ops
from hatalar import DatabaseError, DuplicateEntryError, UserInputError
from rich.console import Console
from rich.table import Table

console = ui.console

# === Yardımcı Fonksiyon: Marka Listesi Gösterme ===


def display_brand_list(brands, title="Marka Listesi"):
    """Verilen marka listesini tablo olarak gösterir."""
    if not brands:
        console.print(
            f">>> {title} için gösterilecek marka yok.", style="yellow")
        return

    console.print(f"\n--- {title} ---", style="bold blue")
    table = Table(title=title, show_header=True,
                  header_style="magenta", border_style="blue")
    headers = ["No", "ID", "Marka Adı", "Durum"]
    table.add_column(headers[0], style="dim", justify="right", width=4)
    table.add_column(headers[1], style="dim", justify="right")
    table.add_column(headers[2], style="cyan", min_width=20)
    table.add_column(headers[3], justify="center")

    for i, brand in enumerate(brands, start=1):
        status = "[green]Aktif[/]" if brand.get(
            'is_active') else "[red]Pasif[/]"
        table.add_row(
            f"{i}.",
            str(brand.get('brand_id', '-')),
            brand.get('name', '-'),
            status
        )
    console.print(table)
    console.print(f"\nToplam {len(brands)} marka listelendi.")

# === Handler Fonksiyonları ===


def handle_add_brand(connection):
    """Yeni marka ekleme işlemini yönetir."""
    console.print("\n--- Yeni Marka Ekle ---", style="bold blue")
    try:
        name = ui.get_non_empty_input("Marka Adı: ")
        new_brand_id = brand_db_ops.add_brand(connection, name)
        # Başarı mesajı add_brand içinde veriliyor.
        # Eklenen markanın ID'sini döndür (select_brand içinde kullanılabilir)
        return new_brand_id
    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
        return None
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
        return None
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Marka Ekleme): {e}", style="bold red")
        return None


def handle_list_brands(connection):
    """Markaları listeleme işlemini yönetir."""
    console.print("\n--- Marka Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input(
            "Pasif markalar da gösterilsin mi?")
        brands = brand_db_ops.list_all_brands(
            connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        display_brand_list(brands, title=f"{status_text} Markalar")
    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")


def handle_toggle_brand_status(connection):
    """Bir markanın aktif/pasif durumunu değiştirir."""
    console.print("\n--- Marka Aktif/Pasif Yap ---", style="bold blue")
    try:
        search_term = ui.get_non_empty_input(
            "Durumu değiştirilecek Markanın Adını girin: ")
        brands = brand_db_ops.get_brands_by_name_like(
            connection, search_term, only_active=False)  # Aktif/Pasif ara

        if not brands:
            console.print(
                f">>> '{search_term}' ile eşleşen marka bulunamadı.", style="yellow")
            return

        selected_brand = None
        if len(brands) == 1:
            selected_brand = brands[0]
        else:
            console.print(
                f"\n>>> '{search_term}' ile eşleşen birden fazla marka bulundu:")
            display_brand_list(brands, title="Eşleşen Markalar")
            while True:
                prompt = f"İşlem yapılacak markanın No (1-{len(brands)}, İptal için 0): "
                choice_num = ui.get_positive_int_input(prompt, allow_zero=True)
                if choice_num == 0:
                    console.print("İşlem iptal edildi.", style="yellow")
                    return
                elif 1 <= choice_num <= len(brands):
                    selected_brand = brands[choice_num - 1]
                    break
                else:
                    console.print(f">>> Geçersiz numara!", style="red")

        if selected_brand:
            brand_id = selected_brand.get('brand_id')
            brand_name = selected_brand.get('name')
            is_active = selected_brand.get('is_active')
            current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
            action_text = "Pasif" if is_active else "Aktif"
            prompt = f">>> '{brand_name}' şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

            if ui.get_yes_no_input(prompt):
                success = False
                if is_active:
                    success = brand_db_ops.deactivate_brand(
                        connection, brand_id)
                else:
                    success = brand_db_ops.reactivate_brand(
                        connection, brand_id)
                # Başarı/hata mesajları DB fonksiyonlarında veriliyor.
            else:
                console.print("İşlem iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")

# === Marka Seçme Fonksiyonu (Ürün Ekleme/Güncelleme için) ===


def select_brand(connection, prompt_message="Marka Adı: ", allow_none=False):
    """
    Kullanıcıdan marka seçmesini veya yeni marka eklemesini ister.
    Ürün ekleme/güncelleme sırasında kullanılır. Marka seçimi zorunludur.
    Args:
        allow_none (bool): Kullanıcının marka seçmemesine izin ver (False olmalı).
    Returns:
        int: Seçilen veya yeni eklenen markanın ID'si. Hata veya iptal durumunda None.
    """
    if allow_none:  # Bu fonksiyon marka seçimi zorunlu olduğu için allow_none'u desteklemiyor
        console.print(
            "[bold red]Hata: select_brand fonksiyonu allow_none=True ile çağrılamaz.[/]")
        return None

    while True:
        search_term = ui.get_non_empty_input(prompt_message)
        try:
            brands = brand_db_ops.get_brands_by_name_like(
                connection, search_term, only_active=True)  # Sadece aktifleri ara

            if not brands:
                console.print(
                    f">>> '{search_term}' ile eşleşen aktif marka bulunamadı.", style="yellow")
                if ui.get_yes_no_input("Yeni marka eklemek ister misiniz?"):
                    new_brand_id = handle_add_brand(connection)
                    if new_brand_id:
                        return new_brand_id  # Yeni eklenen markanın ID'sini döndür
                    else:
                        console.print(
                            ">>> Marka eklenemedi, lütfen tekrar deneyin.", style="yellow")
                        continue  # Tekrar marka adı sormaya dön
                else:
                    console.print(
                        "Marka seçimi zorunludur. Lütfen geçerli bir marka adı girin veya yeni ekleyin.", style="yellow")
                    continue  # Tekrar marka adı sormaya dön

            elif len(brands) == 1:
                selected_brand = brands[0]
                brand_id = selected_brand.get('brand_id')
                brand_name = selected_brand.get('name')
                console.print(
                    f">>> Marka seçildi: {brand_name} (ID: {brand_id})", style="green")
                return brand_id  # Bulunan tek markanın ID'sini döndür

            else:  # Birden fazla marka bulundu
                console.print(
                    f"\n>>> '{search_term}' ile eşleşen birden fazla aktif marka bulundu:")
                display_brand_list(brands, title="Eşleşen Markalar")
                while True:
                    select_prompt = f"Seçilecek markanın No (1-{len(brands)}, Yeni Ekle: Y, İptal: 0): "
                    choice_input = input(select_prompt).strip()
                    if choice_input == '0':
                        console.print(
                            "Marka seçimi iptal edildi. Lütfen tekrar deneyin.", style="yellow")
                        break  # İç döngüden çık, ana arama döngüsüne dön
                    elif choice_input.upper() == 'Y':
                        new_brand_id = handle_add_brand(connection)
                        if new_brand_id:
                            return new_brand_id
                        else:
                            console.print(
                                ">>> Marka eklenemedi, lütfen listeden seçin veya tekrar deneyin.", style="yellow")
                            # İç döngüye devam et, listeden seçmeyi bekle
                            continue
                    elif choice_input.isdigit():
                        choice_num = int(choice_input)
                        if 1 <= choice_num <= len(brands):
                            selected_brand = brands[choice_num - 1]
                            brand_id = selected_brand.get('brand_id')
                            brand_name = selected_brand.get('name')
                            console.print(
                                f">>> Marka seçildi: {brand_name} (ID: {brand_id})", style="green")
                            return brand_id  # Seçilen markanın ID'sini döndür
                        else:
                            console.print(f">>> Geçersiz numara!", style="red")
                    else:
                        console.print(">>> Geçersiz giriş!", style="red")
                # İç döngüden çıkıldıysa (iptal veya hata), ana arama döngüsüne devam et
                continue

        except DatabaseError as e:
            console.print(
                f">>> VERİTABANI HATASI (Marka Arama/Seçme): {e}", style="bold red")
            # Ciddi hata, işlemi sonlandırabiliriz.
            return None
        except Exception as e:
            console.print(
                f">>> BEKLENMEDİK HATA (Marka Arama/Seçme): {e}", style="bold red")
            return None
