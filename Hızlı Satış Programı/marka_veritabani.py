# marka_veritabani.py
# Markalarla ilgili veritabanı işlemlerini içerir.

from mysql.connector import Error, errorcode
from hatalar import DatabaseError, DuplicateEntryError
from rich import print as rprint

# === Marka Ekleme ===


def add_brand(connection, name):
    """Veritabanına yeni bir marka ekler."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Marka eklemek için aktif bağlantı gerekli.")
    if not name:
        raise ValueError("Marka adı boş olamaz.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "INSERT INTO brands (name, is_active) VALUES (%s, TRUE)"
        cursor.execute(sql, (name,))
        connection.commit()
        new_brand_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Marka '{name}' başarıyla eklendi (ID: {new_brand_id}).[/]")
        return new_brand_id
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Marka adı '{name}' zaten kayıtlı!") from e
        else:
            raise DatabaseError(f"Marka ekleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Marka Listeleme ===


def list_all_brands(connection, include_inactive=False):
    """
    Veritabanındaki markaları listeler.
    Returns:
        list: Marka bilgilerini içeren sözlük listesi.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Markaları listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT brand_id, name, is_active FROM brands"
        if not include_inactive:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Markaları listeleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Marka Durum Değiştirme ===


def deactivate_brand(connection, brand_id):
    """Verilen ID'ye sahip markayı pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Marka pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        # TODO: Bu markayı kullanan aktif ürün var mı kontrolü eklenebilir.
        # Şimdilik sadece durumu değiştiriyoruz.
        sql = "UPDATE brands SET is_active = FALSE WHERE brand_id = %s AND is_active = TRUE"
        cursor.execute(sql, (brand_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Marka (ID: {brand_id}) pasif yapıldı.[/]")
            return True
        else:
            rprint(
                f"[yellow]>>> Marka (ID: {brand_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Marka (ID: {brand_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def reactivate_brand(connection, brand_id):
    """Verilen ID'ye sahip markayı aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Marka aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE brands SET is_active = TRUE WHERE brand_id = %s AND is_active = FALSE"
        cursor.execute(sql, (brand_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Marka (ID: {brand_id}) aktif yapıldı.[/]")
            return True
        else:
            rprint(
                f"[yellow]>>> Marka (ID: {brand_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Marka (ID: {brand_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Marka Getirme (İsme Göre) ===


def get_brand_by_name(connection, name, only_active=True):
    """Verilen isme sahip markayı getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Marka aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT brand_id, name, is_active FROM brands WHERE LOWER(name) = LOWER(%s)"
        params = [name]
        if only_active:
            sql += " AND is_active = TRUE"
        cursor.execute(sql, params)
        return cursor.fetchone()  # Tek bir sonuç veya None döner
    except Error as e:
        raise DatabaseError(
            f"Marka adı ('{name}') ile arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_brands_by_name_like(connection, search_term, only_active=True):
    """Verilen isim parçasını içeren markaları arar."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Marka aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT brand_id, name, is_active FROM brands WHERE LOWER(name) LIKE LOWER(%s)"
        pattern = f"%{search_term}%"
        params = [pattern]
        if only_active:
            sql += " AND is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql, params)
        return cursor.fetchall()  # Liste döner
    except Error as e:
        raise DatabaseError(
            f"Marka adı ('{search_term}') ile arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
