# kullanici_veritabani.py
# Kullanıcılarla ilgili veritabanı işlemlerini içerir.
# v2: update_user_password fonksiyonu eklendi.
# v3: Hashing/verification logic removed, reverted to storing bcrypt hash directly.
#     Salt column is no longer used by the code.

from mysql.connector import Error, errorcode
# AuthenticationError import edildi
from hatalar import DatabaseError, DuplicateEntryError, AuthenticationError
from rich import print as rprint

# === Kullanıcı Ekleme ===


def add_user(connection, username, password_hash: bytes, full_name=None, role='user'):
    """Veritabanına yeni bir kullanıcı ekler (bcrypt hash'i ile)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kullanıcı eklemek için aktif bağlantı gerekli.")
    if not username or not password_hash:
        raise ValueError("Kullanıcı adı ve şifre hash'i boş olamaz.")
    if role not in ['admin', 'user']:
        raise ValueError(
            "Geçersiz kullanıcı rolü. 'admin' veya 'user' olmalıdır.")

    cursor = None
    try:
        cursor = connection.cursor()

        # Kullanıcı adı kontrolü
        sql_check = "SELECT user_id FROM users WHERE username = %s"
        cursor.execute(sql_check, (username,))
        if cursor.fetchone():
            raise DuplicateEntryError(
                f"Kullanıcı adı '{username}' zaten mevcut!")

        # Kullanıcıyı ekle (password_hash doğrudan kaydedilir)
        # Salt sütunu artık kullanılmıyor, DB şemasından kaldırılabilir.
        sql_insert = """INSERT INTO users
                        (username, password_hash, full_name, role, is_active)
                        VALUES (%s, %s, %s, %s, TRUE)"""
        # password_hash'in bytes olduğundan emin olalım (bcrypt bytes döndürür)
        params = (username, password_hash, full_name, role)
        cursor.execute(sql_insert, params)
        connection.commit()
        new_user_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Kullanıcı '{username}' başarıyla eklendi (ID: {new_user_id}).[/]")
        return new_user_id
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Kullanıcı adı '{username}' zaten mevcut!") from e
        else:
            raise DatabaseError(f"Kullanıcı ekleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Kullanıcı Getirme ===


def get_user_by_username(connection, username):
    """Verilen kullanıcı adına sahip kullanıcıyı getirir (aktif/pasif farketmez, şifre hash'i dahil)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kullanıcı aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # Şifre hash'ini de alalım (doğrulama için)
        sql = "SELECT user_id, username, password_hash, full_name, role, is_active FROM users WHERE username = %s"
        cursor.execute(sql, (username,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"Kullanıcı adı ('{username}') ile arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_user_by_id(connection, user_id):
    """Verilen ID'ye sahip kullanıcıyı getirir (şifre hash'i dahil)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kullanıcı aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT user_id, username, password_hash, full_name, role, is_active FROM users WHERE user_id = %s"
        cursor.execute(sql, (user_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"Kullanıcı ID ({user_id}) ile arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Kullanıcı Listeleme ===


def list_all_users(connection, include_inactive=False):
    """Veritabanındaki kullanıcıları listeler (şifre hariç)."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Kullanıcıları listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT user_id, username, full_name, role, is_active FROM users"
        if not include_inactive:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY username ASC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Kullanıcıları listeleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Kullanıcı Güncelleme (Detaylar) ===


def update_user_details(connection, user_id, new_username, new_full_name, new_role):
    """Kullanıcının detaylarını günceller (şifre hariç)."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Kullanıcı güncellemek için aktif bağlantı gerekli.")
    if not new_username:
        raise ValueError("Yeni kullanıcı adı boş olamaz.")
    if new_role not in ['admin', 'user']:
        raise ValueError("Geçersiz rol.")

    cursor = None
    try:
        cursor = connection.cursor()
        sql_check = "SELECT user_id FROM users WHERE username = %s AND user_id != %s"
        cursor.execute(sql_check, (new_username, user_id))
        if cursor.fetchone():
            raise DuplicateEntryError(
                f"Kullanıcı adı '{new_username}' zaten başka bir kullanıcı tarafından kullanılıyor!")

        sql_update = """UPDATE users SET
                        username = %s, full_name = %s, role = %s
                        WHERE user_id = %s"""
        params = (new_username, new_full_name, new_role, user_id)
        cursor.execute(sql_update, params)
        if cursor.rowcount == 0:
            return False
        else:
            connection.commit()
            rprint(
                f"[bold green]>>> Kullanıcı (ID: {user_id}) detayları başarıyla güncellendi.[/]")
            return True
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Kullanıcı adı '{new_username}' zaten mevcut!") from e
        else:
            if not isinstance(e, DuplicateEntryError):
                raise DatabaseError(
                    f"Kullanıcı (ID: {user_id}) güncelleme hatası: {e}") from e
            else:
                raise e
    finally:
        if cursor:
            cursor.close()

# === Kullanıcı Şifre Güncelleme ===

# ***** BU FONKSİYON GÜNCELLENDİ (Sadece hash'i günceller) *****

def update_user_password(connection, user_id, new_password_hash: bytes):
    """
    Kullanıcının veritabanındaki şifre hash'ini günceller.
    Doğrulama bu fonksiyonda yapılmaz, çağıran yerde yapılmalıdır.
    Args:
        user_id (int): Şifresi güncellenecek kullanıcı ID'si.
        new_password_hash (bytes): Kaydedilecek yeni şifre hash'i (bcrypt).
    Returns:
        bool: Güncelleme başarılıysa True, değilse False.
    Raises:
        DatabaseError: Veritabanı hatası durumunda.
        ValueError: Parametreler eksikse.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Şifre güncellemek için aktif bağlantı gerekli.")
    if not user_id or not new_password_hash:
        raise ValueError("Kullanıcı ID ve yeni şifre hash'i boş olamaz.")

    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE users SET password_hash = %s WHERE user_id = %s"
        cursor.execute(sql, (new_password_hash, user_id))

        if cursor.rowcount == 1:
            connection.commit()
            # Başarı mesajı çağıran fonksiyonda verilecek
            return True
        else:
            # Kullanıcı bulunamadı
            raise DatabaseError(f"Şifre güncellenemedi: Kullanıcı (ID: {user_id}) bulunamadı.")
            # return False # Veya sadece False döndür
    except Error as e:
        raise DatabaseError(f"Kullanıcı (ID: {user_id}) şifre güncelleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
# ***** FONKSİYON GÜNCELLENDİ SONU *****


# === Kullanıcı Durum Değiştirme ===

def deactivate_user(connection, user_id):
    """Verilen ID'ye sahip kullanıcıyı pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kullanıcı pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE users SET is_active = FALSE WHERE user_id = %s AND is_active = TRUE"
        cursor.execute(sql, (user_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Kullanıcı (ID: {user_id}) pasif yapıldı.[/]")
            return True
        else:
            rprint(f"[yellow]>>> Kullanıcı (ID: {user_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Kullanıcı (ID: {user_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def reactivate_user(connection, user_id):
    """Verilen ID'ye sahip kullanıcıyı aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kullanıcı aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE users SET is_active = TRUE WHERE user_id = %s AND is_active = FALSE"
        cursor.execute(sql, (user_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Kullanıcı (ID: {user_id}) aktif yapıldı.[/]")
            return True
        else:
            rprint(f"[yellow]>>> Kullanıcı (ID: {user_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Kullanıcı (ID: {user_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
