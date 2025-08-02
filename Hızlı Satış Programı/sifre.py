# sifre_sifirla.py
# Belirtilen kullanıcının şifresini bcrypt ile yeniden hashleyerek sıfırlar.
# DİKKAT: Bu betik mevcut şifreyi sormaz, doğrudan sıfırlama yapar.

import db_config1  # Veritabanı bağlantısı için
import kullanici_islemleri as user_handlers  # hash_password fonksiyonu için
from mysql.connector import Error
import getpass


def reset_password():
    """Kullanıcıdan bilgileri alıp şifreyi sıfırlar."""
    print("--- Kullanıcı Şifresi Sıfırlama ---")

    connection = None
    cursor = None
    try:
        # Veritabanına bağlan
        connection = db_config1.connect_db()
        if not (connection and connection.is_connected()):
            print("!!! HATA: Veritabanına bağlanılamadı.")
            return

        # Kullanıcı adını al
        username = input("Şifresi sıfırlanacak kullanıcı adı: ").strip()
        if not username:
            print("Kullanıcı adı boş bırakılamaz.")
            return

        # Yeni şifreyi al
        new_password = getpass.getpass("Yeni şifre: ")
        if not new_password:
            print("Yeni şifre boş bırakılamaz.")
            return
        new_password_confirm = getpass.getpass("Yeni şifre (Tekrar): ")
        if new_password != new_password_confirm:
            print("Şifreler eşleşmiyor!")
            return

        # Yeni şifreyi hashle
        try:
            new_password_hash = user_handlers.hash_password(new_password)
        except Exception as hash_err:
            print(f"HATA: Şifre hashlenirken sorun oluştu: {hash_err}")
            return

        # Veritabanını güncelle
        cursor = connection.cursor()
        sql_update = "UPDATE users SET password_hash = %s WHERE username = %s"
        # password_hash'in bytes olduğundan emin olalım
        params = (new_password_hash, username)
        cursor.execute(sql_update, params)

        if cursor.rowcount == 0:
            print(
                f"HATA: Kullanıcı adı '{username}' bulunamadı veya şifre güncellenemedi.")
        else:
            connection.commit()
            print(
                f"[+] Kullanıcı '{username}' için şifre başarıyla sıfırlandı.")

    except Error as db_err:
        print(f"Veritabanı Hatası: {db_err}")
        if connection:
            connection.rollback()  # Hata durumunda geri al
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("Veritabanı bağlantısı kapatıldı.")


if __name__ == "__main__":
    reset_password()
