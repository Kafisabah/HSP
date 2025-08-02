# kullanici_islemleri.py
# Kullanıcı ekleme, listeleme, güncelleme, durum değiştirme, giriş yapma
# ve şifre değiştirme ile ilgili kullanıcı etkileşimlerini yönetir.
# v2: handle_change_password fonksiyonu eklendi.
# v3: Hashing/verification logic consolidated using bcrypt.
#     DB functions called correctly. AuthenticationError handled.

import arayuz_yardimcilari as ui
import kullanici_veritabani as user_db_ops
# AuthenticationError import edildi
from hatalar import DatabaseError, DuplicateEntryError, UserInputError, AuthenticationError
from rich.console import Console
from rich.table import Table
import bcrypt  # bcrypt kullanılacak
import getpass  # Şifreleri gizli almak için

console = ui.console

# === Yardımcı Fonksiyon: Şifre Hashleme ===


def hash_password(password):
    """Verilen şifreyi bcrypt ile hashler."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password  # byte olarak döndür

# === Yardımcı Fonksiyon: Şifre Doğrulama ===


def verify_password(plain_password, hashed_password_from_db):
    """Girilen şifre ile veritabanından gelen hashlenmiş şifreyi karşılaştırır."""
    password_bytes = plain_password.encode('utf-8')
    # Veritabanından gelen hash'in bytes olduğundan emin olalım
    if isinstance(hashed_password_from_db, str):
        # Eğer DB'den string geliyorsa (eski kayıtlar?), byte'a çevir
        hashed_password_bytes = hashed_password_from_db.encode('utf-8')
    elif isinstance(hashed_password_from_db, bytes):
        hashed_password_bytes = hashed_password_from_db
    else:
        # Beklenmeyen tip, doğrulama başarısız olsun
        return False

    try:
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except ValueError:
        # Genellikle hash geçersiz formatta ise bu hata alınır
        console.print("[red]HATA: Veritabanındaki şifre formatı geçersiz.[/]")
        return False


# === Handler Fonksiyonları ===

def handle_login(connection):
    """Kullanıcı giriş işlemini yönetir."""
    console.print("\n--- Kullanıcı Girişi ---", style="bold blue")
    while True:
        username = ui.get_non_empty_input("Kullanıcı Adı: ")
        password = getpass.getpass("Şifre: ")

        try:
            # Kullanıcıyı DB'den al (hash dahil)
            user_data = user_db_ops.get_user_by_username(connection, username)

            if user_data:
                if not user_data.get('is_active'):  # Önce aktif mi kontrol et
                     console.print(
                         f"[bold red]>>> Kullanıcı hesabı '{username}' pasif durumda.[/]")
                else:
                    stored_hash = user_data.get('password_hash')
                    if stored_hash and verify_password(password, stored_hash):
                        console.print(f"\n[bold green]Giriş başarılı! Hoş geldiniz, {user_data.get('full_name', username)}.[/]")
                        # Şifre hash'ini döndürme, sadece gerekli bilgileri döndür
                        user_info = {
                               'user_id': user_data['user_id'],
                               'username': username,
                               'full_name': user_data['full_name'],
                               'role': user_data['role'],
                               'password_hash': stored_hash  # Şifre değiştirme için sakla
                           }
                        return user_info
                    else:
                          console.print("[bold red]>>> Hatalı şifre![/]")
            else:
                console.print(f"[bold red]>>> Kullanıcı adı '{username}' bulunamadı.[/]")

            if not ui.get_yes_no_input("Tekrar denemek ister misiniz?"):
                console.print("Giriş işlemi iptal edildi.", style="yellow")
                return None  # Giriş başarısız veya iptal edildi

        except DatabaseError as e:
            console.print(f">>> VERİTABANI HATASI (Giriş): {e}", style="bold red")
            return None
        except AuthenticationError as e:  # Bu hata artık DB katmanından gelmeyecek ama yakalayalım
            console.print(f"[bold red]>>> Kimlik Doğrulama Hatası: {e}[/]")
        except Exception as e:
            console.print(f">>> BEKLENMEDİK HATA (Giriş): {e}", style="bold red")
            return None


def handle_add_user(connection):
    """Yeni kullanıcı ekleme işlemini yönetir (Admin yetkisiyle)."""
    console.print("\n--- Yeni Kullanıcı Ekle ---", style="bold blue")
    try:
        username = ui.get_non_empty_input("Kullanıcı Adı (*): ")
        while True:
            password = getpass.getpass("Şifre (*): ")
            if not password:
                console.print(">>> HATA: Şifre boş bırakılamaz!", style="red")
                continue
            password_confirm = getpass.getpass("Şifre (Tekrar) (*): ")
            if password == password_confirm:
                break
            else:
                console.print("[bold red]>>> Şifreler eşleşmiyor! Lütfen tekrar girin.[/]")

        full_name = input("Ad Soyad (isteğe bağlı): ").strip() or None
        role = 'user'
        if ui.get_yes_no_input("Bu kullanıcı 'admin' yetkisine sahip olsun mu?"):
            role = 'admin'

        # Şifreyi hashle
        password_hash = hash_password(password)  # bcrypt hash (bytes)

        # Veritabanına hash'i gönder
        new_user_id = user_db_ops.add_user(connection, username, password_hash, full_name, role)
        # Başarı mesajı add_user içinde veriliyor.

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Kullanıcı Ekleme): {e}", style="bold red")


def handle_list_users(connection):
    """Kullanıcıları listeleme işlemini yönetir (Admin yetkisiyle)."""
    console.print("\n--- Kullanıcı Listesi ---", style="bold blue")
    try:
        show_inactive = ui.get_yes_no_input("Pasif kullanıcılar da gösterilsin mi?")
        users = user_db_ops.list_all_users(connection, include_inactive=show_inactive)
        status_text = "Tüm" if show_inactive else "Aktif"
        ui.display_user_list(users, title=f"{status_text} Kullanıcılar")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI (Listeleme): {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Listeleme): {e}", style="bold red")


def handle_update_user(connection):
    """Mevcut bir kullanıcıyı güncelleme işlemini yönetir (Admin yetkisiyle, şifre hariç)."""
    console.print("\n--- Kullanıcı Güncelle ---", style="bold blue")
    try:
        search_term = ui.get_non_empty_input("Güncellenecek Kullanıcının Adını girin: ")
        # list_all_users şifre hash'ini getirmiyor, bu yüzden sorun yok
        users = user_db_ops.list_all_users(connection, include_inactive=True)
        matching_users = [u for u in users if search_term.lower() in u.get('username', '').lower()]

        if not matching_users:
            console.print(f">>> '{search_term}' ile eşleşen kullanıcı bulunamadı.", style="yellow")
            return

        selected_user = None
        if len(matching_users) == 1:
            selected_user = matching_users[0]
            console.print(f">>> Kullanıcı bulundu: {selected_user.get('username')}", style="green")
        else:
            console.print(f"\n>>> '{search_term}' ile eşleşen birden fazla kullanıcı bulundu:")
            ui.display_user_list(matching_users, title="Eşleşen Kullanıcılar")
            while True:
                prompt = f"İşlem yapılacak kullanıcının No (1-{len(matching_users)}, İptal için 0): "
                choice_num = ui.get_positive_int_input(prompt, allow_zero=True)
                if choice_num == 0:
                    console.print("İşlem iptal edildi.", style="yellow")
                    return
                elif 1 <= choice_num <= len(matching_users):
                    selected_user = matching_users[choice_num - 1]
                    break
                else:
                    console.print(f">>> Geçersiz numara!", style="red")

        if selected_user:
            user_id = selected_user.get('user_id')
            current_username = selected_user.get('username')
            current_full_name = selected_user.get('full_name')
            current_role = selected_user.get('role')

            console.print("\n--- Mevcut Bilgiler ---")
            console.print(f" ID: {user_id}\n Kullanıcı Adı: {current_username}\n Ad Soyad: {current_full_name or '-'}\n Rol: {current_role}")
            console.print("--- Yeni Bilgiler (Değiştirmek istemediklerinizi boş bırakın, Şifre buradan değiştirilemez) ---", style="dim")

            new_username = ui.get_optional_string_input("Yeni Kullanıcı Adı", current_username)
            if not new_username:
                console.print(">>> HATA: Kullanıcı adı boş bırakılamaz.", style="red")
                return
            new_full_name = ui.get_optional_string_input("Yeni Ad Soyad", current_full_name)

            new_role = current_role
            change_role = ui.get_yes_no_input(f"Rolü değiştirmek istiyor musunuz? (Mevcut: {current_role})")
            if change_role:
                if ui.get_yes_no_input("Yeni rol 'admin' mi olsun? (Hayır = 'user')"):
                     new_role = 'admin'
                else:
                     new_role = 'user'

            # Veritabanını güncelle (sadece detaylar)
            success = user_db_ops.update_user_details(
                connection, user_id, new_username, new_full_name, new_role
            )
            # Başarı/hata mesajı DB fonksiyonunda veriliyor.

    except (DuplicateEntryError, ValueError) as e:
        console.print(f">>> HATA: {e}", style="bold red")
    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Kullanıcı Güncelleme): {e}", style="bold red")


def handle_toggle_user_status(connection, current_user_id):
    """Bir kullanıcının aktif/pasif durumunu değiştirir (Admin yetkisiyle)."""
    console.print("\n--- Kullanıcı Aktif/Pasif Yap ---", style="bold blue")
    try:
        search_term = ui.get_non_empty_input("Durumu değiştirilecek Kullanıcının Adını girin: ")
        users = user_db_ops.list_all_users(connection, include_inactive=True)
        matching_users = [u for u in users if search_term.lower() in u.get('username', '').lower()]

        if not matching_users:
            console.print(f">>> '{search_term}' ile eşleşen kullanıcı bulunamadı.", style="yellow")
            return

        selected_user = None
        if len(matching_users) == 1:
            selected_user = matching_users[0]
        else:
            console.print(f"\n>>> '{search_term}' ile eşleşen birden fazla kullanıcı bulundu:")
            ui.display_user_list(matching_users, title="Eşleşen Kullanıcılar")
            while True:
                prompt = f"İşlem yapılacak kullanıcının No (1-{len(matching_users)}, İptal için 0): "
                choice_num = ui.get_positive_int_input(prompt, allow_zero=True)
                if choice_num == 0:
                    console.print("İşlem iptal edildi.", style="yellow")
                    return
                elif 1 <= choice_num <= len(matching_users):
                    selected_user = matching_users[choice_num - 1]
                    break
                else:
                    console.print(f">>> Geçersiz numara!", style="red")

        if selected_user:
            user_id_to_toggle = selected_user.get('user_id')
            username_to_toggle = selected_user.get('username')
            is_active = selected_user.get('is_active')

            if user_id_to_toggle == current_user_id and is_active:
                console.print("[bold red]HATA: Kendi hesabınızı pasif yapamazsınız![/]")
                return

            current_status_text = "[green]Aktif[/]" if is_active else "[red]Pasif[/]"
            action_text = "Pasif" if is_active else "Aktif"
            prompt = f">>> '{username_to_toggle}' şu an {current_status_text}. [bold]{action_text}[/] yapılsın mı?"

            if ui.get_yes_no_input(prompt):
                success = False
                if is_active:
                    success = user_db_ops.deactivate_user(connection, user_id_to_toggle)
                else:
                    success = user_db_ops.reactivate_user(connection, user_id_to_toggle)
            else:
                console.print("İşlem iptal edildi.", style="yellow")

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI: {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA: {e}", style="bold red")

# ***** BU FONKSİYON GÜNCELLENDİ (bcrypt ve DB çağrısı düzeltildi) *****

def handle_change_password(connection, logged_in_user):
    """Giriş yapmış kullanıcının kendi şifresini değiştirmesini sağlar."""
    console.print("\n--- Şifre Değiştir ---", style="bold blue")
    if not logged_in_user:
        console.print("[red]HATA: Şifre değiştirmek için giriş yapmış olmalısınız.[/]")
        return

    user_id = logged_in_user.get('user_id')
    username = logged_in_user.get('username')
    # Girişte alınan hash'i kullanmak yerine, DB'den güncel hash'i alalım
    # Bu, başka bir oturumda şifre değiştirilmişse sorun olmasını engeller.
    try:
        user_data_from_db = user_db_ops.get_user_by_id(connection, user_id)
        if not user_data_from_db:
            console.print(f"[red]HATA: Kullanıcı (ID: {user_id}) bilgileri veritabanından alınamadı.[/]")
            return
        current_hash_from_db = user_data_from_db.get('password_hash')
        if not current_hash_from_db:
            console.print(f"[red]HATA: Kullanıcı (ID: {user_id}) için mevcut şifre bilgisi bulunamadı.[/]")
            return

    except DatabaseError as e:
        console.print(f">>> VERİTABANI HATASI (Mevcut Şifre Alma): {e}", style="bold red")
        return
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Mevcut Şifre Alma): {e}", style="bold red")
        return

    try:
        # 1. Mevcut Şifreyi Doğrula
        while True:
            current_password_input = getpass.getpass("Mevcut Şifrenizi Girin: ")
            if not current_password_input:
                console.print("[yellow]Şifre değiştirme iptal edildi.[/]")
                return
            if verify_password(current_password_input, current_hash_from_db):  # DB'den alınan hash ile doğrula
                break
            else:
                console.print("[bold red]>>> Mevcut şifre hatalı![/]")
                if not ui.get_yes_no_input("Tekrar denemek ister misiniz?"):
                    console.print("[yellow]Şifre değiştirme iptal edildi.[/]")
                    return

        # 2. Yeni Şifreyi Al ve Doğrula
        while True:
            new_password = getpass.getpass("Yeni Şifre: ")
            if not new_password:
                console.print(">>> HATA: Yeni şifre boş olamaz!", style="red")
                continue
            new_password_confirm = getpass.getpass("Yeni Şifre (Tekrar): ")
            if new_password == new_password_confirm:
                if verify_password(new_password, current_hash_from_db):  # Yeni şifrenin eskiyle aynı olup olmadığını kontrol et
                    console.print("[yellow]>>> Yeni şifre mevcut şifreyle aynı olamaz![/]")
                    continue
                break
            else:
                console.print("[bold red]>>> Yeni şifreler eşleşmiyor! Lütfen tekrar girin.[/]")

        # 3. Yeni Şifreyi Hashle
        new_password_hash = hash_password(new_password)  # bcrypt hash (bytes)

        # 4. Veritabanını Güncelle (Sadece yeni hash gönderilir)
        success = user_db_ops.update_user_password(connection, user_id, new_password_hash)

        if success:
            # Başarı mesajı DB fonksiyonunda veriliyor.
            # Oturumdaki hash'i de güncelleyelim
            logged_in_user['password_hash'] = new_password_hash
        else:
            # Hata mesajı DB fonksiyonunda verilmeli (örn. Kullanıcı bulunamadı)
            console.print("[bold red]>>> Şifre güncellenirken bir hata oluştu.[/]")

    except (DatabaseError, ValueError) as e:  # AuthenticationError artık burada yakalanmaz
        console.print(f">>> HATA (Şifre Değiştirme): {e}", style="bold red")
    except Exception as e:
        console.print(f">>> BEKLENMEDİK HATA (Şifre Değiştirme): {e}", style="bold red")
# ***** YENİ FONKSİYON SONU *****
