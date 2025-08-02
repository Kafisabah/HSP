# tedarikci_veritabani.py
# Tedarikçilerle ilgili veritabanı işlemlerini içerir.
# v15: Aktif/Pasif yapma fonksiyonları eklendi. Arama fonksiyonları güncellendi.

from mysql.connector import Error, errorcode
from hatalar import DatabaseError, DuplicateEntryError
from rich import print as rprint

# === Tedarikçi Ekleme ===
def add_supplier(connection, name, contact=None, phone=None, email=None, address=None):
    """Yeni bir tedarikçi ekler."""
    # (Fonksiyon içeriği öncekiyle aynı - değişiklik yok)
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi eklemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = """INSERT INTO suppliers
                 (name, contact_person, phone, email, address, is_active)
                 VALUES (%s, %s, %s, %s, %s, TRUE)"""
        params = (name, contact, phone, email, address)
        cursor.execute(sql, params)
        connection.commit()
        new_supplier_id = cursor.lastrowid
        rprint(f"[bold green]>>> Tedarikçi '{name}' başarıyla eklendi (ID: {new_supplier_id}).[/]")
        return new_supplier_id
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            error_field = "Ad, Telefon veya E-posta"
            if 'phone' in e.msg: error_field = "Telefon"
            elif 'email' in e.msg: error_field = "E-posta"
            elif 'name' in e.msg: error_field = "Ad"
            raise DuplicateEntryError(f"Tedarikçi {error_field} zaten kayıtlı olabilir.") from e
        else:
            raise DatabaseError(f"Tedarikçi ekleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Tedarikçi Arama/Getirme ===
def get_supplier_by_id(connection, supplier_id):
    """Verilen ID'ye sahip tedarikçiyi tüm bilgileriyle getirir (aktif/pasif farketmez)."""
    # (Fonksiyon içeriği öncekiyle aynı - değişiklik yok)
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(buffered=True)
        sql = """SELECT supplier_id, name, contact_person, phone, email, address, is_active
                 FROM suppliers WHERE supplier_id = %s"""
        cursor.execute(sql, (supplier_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(f"ID ({supplier_id}) ile tedarikçi arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# ***** BU FONKSİYON GÜNCELLENDİ (only_active parametresi eklendi) *****
def get_supplier_by_phone(connection, phone, only_active=True):
    """
    Verilen telefon numarasına sahip tedarikçiyi getirir.
    (ID, Ad) bilgilerini döndürür.
    Args:
        connection: Aktif veritabanı bağlantısı.
        phone (str): Aranacak telefon numarası.
        only_active (bool): True ise sadece aktif tedarikçileri arar.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi aramak için aktif bağlantı gerekli.")
    if not phone:
        return None
    cursor = None
    try:
        cursor = connection.cursor(buffered=True)
        sql = """
            SELECT supplier_id, name, is_active -- is_active eklendi
            FROM suppliers
            WHERE phone = %s
            """
        params = [phone]
        if only_active:
            sql += " AND is_active = TRUE"
        # sql += " LIMIT 1" # Telefon unique olduğu için limite gerek yok

        cursor.execute(sql, params)
        return cursor.fetchone() # (id, ad, is_active) tuple'ı veya None
    except Error as e:
        raise DatabaseError(f"Telefon ({phone}) ile tedarikçi arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# ***** BU FONKSİYON GÜNCELLENDİ (only_active parametresi eklendi) *****
def get_suppliers_by_name_like(connection, search_term, only_active=True):
    """
    Verilen isim parçasını içeren tedarikçileri arar.
    (ID, Ad, is_active) bilgilerini içeren liste döndürür.
     Args:
        connection: Aktif veritabanı bağlantısı.
        search_term (str): Aranacak isim parçası.
        only_active (bool): True ise sadece aktif tedarikçileri arar.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(buffered=True)
        sql = """
            SELECT supplier_id, name, is_active -- is_active eklendi
            FROM suppliers
            WHERE LOWER(name) LIKE LOWER(%s)
            """
        pattern = f"%{search_term}%"
        params = [pattern]
        if only_active:
            sql += " AND is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql, params)
        return cursor.fetchall() # [(id, ad, is_active), ...] listesi
    except Error as e:
        raise DatabaseError(f"Tedarikçi ismi ('{search_term}') ile arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Tedarikçi Listeleme ===
def list_all_suppliers(connection, include_inactive=False):
    """Veritabanındaki tedarikçileri listeler."""
    # (Fonksiyon içeriği öncekiyle aynı - değişiklik yok)
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçileri listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(buffered=True)
        sql = """SELECT supplier_id, name, contact_person, phone, email, is_active
                 FROM suppliers"""
        if not include_inactive:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Tedarikçileri listeleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Tedarikçi Güncelleme ===
def update_supplier(connection, supplier_id, name, contact=None, phone=None, email=None, address=None):
    """Verilen ID'ye sahip tedarikçinin bilgilerini günceller."""
    # (Fonksiyon içeriği öncekiyle aynı - değişiklik yok)
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi güncellemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = """UPDATE suppliers SET
                    name = %s, contact_person = %s, phone = %s,
                    email = %s, address = %s
                 WHERE supplier_id = %s"""
        params = (name, contact, phone, email, address, supplier_id)
        cursor.execute(sql, params)
        if cursor.rowcount == 0:
            return False
        else:
            connection.commit()
            rprint(f"[bold green]>>> Tedarikçi (ID: {supplier_id}) başarıyla güncellendi.[/]")
            return True
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            error_field = "Ad, Telefon veya E-posta"
            if 'phone' in e.msg: error_field = "Telefon"
            elif 'email' in e.msg: error_field = "E-posta"
            elif 'name' in e.msg: error_field = "Ad"
            raise DuplicateEntryError(f"Güncellenen Tedarikçi {error_field} başka bir kayıtta mevcut.") from e
        else:
            raise DatabaseError(f"Tedarikçi (ID: {supplier_id}) güncelleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# ***** YENİ FONKSİYONLAR *****
def deactivate_supplier(connection, supplier_id):
    """Verilen ID'ye sahip tedarikçiyi pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        # Sadece aktif olanı pasif yap
        sql = "UPDATE suppliers SET is_active = FALSE WHERE supplier_id = %s AND is_active = TRUE"
        cursor.execute(sql, (supplier_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Tedarikçi (ID: {supplier_id}) pasif yapıldı.[/]")
            return True
        else:
            # Bulunamadı veya zaten pasifti
            rprint(f"[yellow]>>> Tedarikçi (ID: {supplier_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Tedarikçi (ID: {supplier_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

def reactivate_supplier(connection, supplier_id):
    """Verilen ID'ye sahip tedarikçiyi aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Tedarikçi aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        # Sadece pasif olanı aktif yap
        sql = "UPDATE suppliers SET is_active = TRUE WHERE supplier_id = %s AND is_active = FALSE"
        cursor.execute(sql, (supplier_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Tedarikçi (ID: {supplier_id}) aktif yapıldı.[/]")
            return True
        else:
            # Bulunamadı veya zaten aktifti
            rprint(f"[yellow]>>> Tedarikçi (ID: {supplier_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Tedarikçi (ID: {supplier_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
# ***** YENİ FONKSİYONLAR SONU *****
