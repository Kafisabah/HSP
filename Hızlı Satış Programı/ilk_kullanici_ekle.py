# ilk_kullanici_ekle.py
# Bu script SADECE BİR KEZ çalıştırılarak ilk admin kullanıcısını oluşturur.
# v3: hash_password fonksiyonu kullanici_veritabani.py ile tutarlı hale getirildi (dklen=64).

import db_config1
import hashlib
import os
from mysql.connector import Error
from rich import print as rprint


def hash_password(password, salt):
    """Verilen şifre ve salt ile PBKDF2 hash oluşturur (dklen=64)."""
    pwd_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    # ***** DÜZELTME: dklen=64 eklendi *****
    hashed = hashlib.pbkdf2_hmac(
        'sha256', pwd_bytes, salt_bytes, 100000, dklen=64)
    return hashed.hex()


def add_first_admin_user(username, password, full_name="Admin User", role="admin"):
    """Veritabanına ilk admin kullanıcısını ekler."""
    connection = None
    cursor = None
    try:
        connection = db_config1.connect_db()
        if not connection or not connection.is_connected():
            rprint("[bold red]HATA: Veritabanına bağlanılamadı![/]")
            return

        cursor = connection.cursor()

        # Kullanıcı zaten var mı diye kontrol et (SİLME ADIMINDAN SONRA BURASI ÇALIŞACAK)
        cursor.execute(
            "SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            rprint(f"[yellow]UYARI: '{username}' kullanıcısı zaten mevcut.[/]")
            # Eğer silme adımını atladıysanız veya hata olduysa, script burada durabilir.
            # Emin olmak için veritabanından manuel sildiyseniz sorun olmaz.
            return

        # Yeni salt oluştur
        salt = os.urandom(16).hex()
        # Şifreyi hashle (Düzeltilmiş fonksiyon ile)
        hashed_pw = hash_password(password, salt)

        # Kullanıcıyı ekle
        sql = """INSERT INTO users
                 (username, password_hash, password_salt, full_name, role, is_active)
                 VALUES (%s, %s, %s, %s, %s, TRUE)"""
        params = (username, hashed_pw, salt, full_name, role)
        cursor.execute(sql, params)
        connection.commit()
        rprint(
            f"[bold green]Başarılı: '{username}' kullanıcısı (rol: {role}) eklendi.[/]")

    except Error as e:
        rprint(f"[bold red]HATA (Kullanıcı Ekleme): {e}[/]")
        if connection:
            connection.rollback()
    except Exception as e:
        rprint(f"[bold red]BEKLENMEDİK HATA: {e}[/]")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    # --- BURAYI DÜZENLE ---
    admin_username = "admin"
    admin_password = "ibo123."  # Buraya kendi belirlediğiniz şifreyi yazın!
    # --- DÜZENLEME SONU ---

    # Kontrolü düzeltiyoruz, varsayılan şifreyle karşılaştırıyoruz
    if admin_password == "SENİN_GÜVENLİ_ŞİFREN":
        rprint("[bold red]Lütfen script içindeki `admin_password` değişkenini 'SENİN_GÜVENLİ_ŞİFREN' dışında bir şeyle değiştirin![/]")
    else:
        add_first_admin_user(admin_username, admin_password)
