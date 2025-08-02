# kategori_veritabani.py
# Kategorilerle ilgili veritabanı işlemlerini içerir.
# v2: Sorgu sonuçlarının tam olarak okunması (fetchall) ve cursor kapatma kontrolü eklendi.

from mysql.connector import Error, errorcode
from hatalar import DatabaseError, DuplicateEntryError
from rich import print as rprint

# === Kategori Ekleme ===


def add_category(connection, name, description=None):
    """Veritabanına yeni bir kategori ekler."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kategori eklemek için aktif bağlantı gerekli.")
    if not name:
        raise ValueError("Kategori adı boş olamaz.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "INSERT INTO categories (name, description, is_active) VALUES (%s, %s, TRUE)"
        cursor.execute(sql, (name, description))
        connection.commit()
        new_category_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Kategori '{name}' başarıyla eklendi (ID: {new_category_id}).[/]")
        return new_category_id
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Kategori adı '{name}' zaten kayıtlı!") from e
        else:
            raise DatabaseError(f"Kategori ekleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Kategori Listeleme ===


def list_all_categories(connection, include_inactive=False):
    """
    Veritabanındaki kategorileri listeler.
    Returns:
        list: Kategori bilgilerini içeren sözlük listesi.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Kategorileri listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT category_id, name, description, is_active FROM categories"
        if not include_inactive:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql)
        results = cursor.fetchall()  # Tüm sonuçları al
        return results
    except Error as e:
        raise DatabaseError(f"Kategorileri listeleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()  # Cursor'ı kapat

# === Kategori Arama ===


def get_categories_by_name_like(connection, search_term, only_active=True):
    """Verilen isim parçasını içeren kategorileri arar."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kategori aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT category_id, name, description, is_active FROM categories WHERE LOWER(name) LIKE LOWER(%s)"
        pattern = f"%{search_term}%"
        params = [pattern]
        if only_active:
            sql += " AND is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql, params)
        results = cursor.fetchall()  # Tüm sonuçları al
        return results
    except Error as e:
        raise DatabaseError(
            f"Kategori adı ('{search_term}') ile arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()  # Cursor'ı kapat

# === Kategori Güncelleme ===


def update_category(connection, category_id, new_name, new_description=None):
    """Verilen ID'ye sahip kategorinin bilgilerini günceller."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Kategori güncellemek için aktif bağlantı gerekli.")
    if not new_name:
        raise ValueError("Yeni kategori adı boş olamaz.")
    cursor = None
    try:
        cursor = connection.cursor()
        # Önce isim kontrolü (kendisi hariç)
        sql_check = "SELECT category_id FROM categories WHERE LOWER(name) = LOWER(%s) AND category_id != %s"
        cursor.execute(sql_check, (new_name, category_id))
        existing = cursor.fetchone()
        # ÖNEMLİ: Check sorgusunun sonucunu okuduktan sonra cursor'ı tekrar kullanabiliriz.
        # Eğer fetchone() yerine fetchall() kullansaydık ve sonuçları işlemeseydik sorun olabilirdi.
        # fetchone() sonucu okuduğu için sorun olmaması gerekir ama garanti olması için
        # cursor.fetchall() ile kalanları (varsa) tüketebiliriz veya yeni cursor açabiliriz.
        # Şimdilik fetchone() yeterli görünüyor.

        if existing:
            raise DuplicateEntryError(
                f"Başka bir kategoride '{new_name}' adı zaten kullanılıyor!")

        sql_update = "UPDATE categories SET name = %s, description = %s WHERE category_id = %s"
        cursor.execute(sql_update, (new_name, new_description, category_id))
        if cursor.rowcount == 0:
            return False  # Bulunamadı veya bilgiler aynı
        else:
            connection.commit()
            rprint(
                f"[bold green]>>> Kategori (ID: {category_id}) başarıyla güncellendi.[/]")
            return True
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:  # Bu kontrol DB seviyesinde de var ama kodda da yakalamak iyi
            raise DuplicateEntryError(
                f"Kategori adı '{new_name}' zaten mevcut!") from e
        else:
            # DuplicateEntryError değilse genel hata ver
            if not isinstance(e, DuplicateEntryError):
                 raise DatabaseError(
                     f"Kategori (ID: {category_id}) güncelleme hatası: {e}") from e
            else:
                 raise e # DuplicateEntryError'ı tekrar fırlat

    finally:
        if cursor:
            cursor.close()

# === Kategori Durum Değiştirme ===


def deactivate_category(connection, category_id):
    """Verilen ID'ye sahip kategoriyi pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kategori pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        # TODO: Bu kategoriyi kullanan aktif ürün var mı kontrolü eklenebilir.
        sql = "UPDATE categories SET is_active = FALSE WHERE category_id = %s AND is_active = TRUE"
        cursor.execute(sql, (category_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Kategori (ID: {category_id}) pasif yapıldı.[/]")
            return True
        else:
            rprint(f"[yellow]>>> Kategori (ID: {category_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        # Ürünler tarafından referans alınma hatası (Foreign Key)
        if e.errno == errorcode.ER_ROW_IS_REFERENCED_2 or e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            rprint(f"[bold red]HATA: Bu kategori aktif ürünler tarafından kullanıldığı için pasif yapılamaz![/]")
            return False
        else:
            raise DatabaseError(f"Kategori (ID: {category_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def reactivate_category(connection, category_id):
    """Verilen ID'ye sahip kategoriyi aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kategori aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE categories SET is_active = TRUE WHERE category_id = %s AND is_active = FALSE"
        cursor.execute(sql, (category_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Kategori (ID: {category_id}) aktif yapıldı.[/]")
            return True
        else:
            rprint(f"[yellow]>>> Kategori (ID: {category_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Kategori (ID: {category_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
