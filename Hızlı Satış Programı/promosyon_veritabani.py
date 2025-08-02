# promosyon_veritabani.py
# Promosyonlarla ilgili veritabanı işlemlerini içerir.
# v2: BOGO ve BuyXGetYFree promosyon türleri için sütunlar eklendi.
# v3: add_promotion ve update_promotion fonksiyonlarında, ilgili türe ait olmayan
#     NOT NULL sütunlara varsayılan değer (0) ataması eklendi.

from mysql.connector import Error, errorcode
from decimal import Decimal
import datetime
from hatalar import DatabaseError, DuplicateEntryError
from rich import print as rprint

# === Promosyon Ekleme ===

# ***** BU FONKSİYON GÜNCELLENDİ (Varsayılan değer ataması eklendi) *****


def add_promotion(connection, name, description, promotion_type, product_id,
                  required_quantity=None, discount_amount=None,  # quantity_discount için
                  # bogo/buy_x_get_y için
                  required_bogo_quantity=None, free_quantity=None, free_product_id=None,
                  start_date=None, end_date=None):
    """Veritabanına yeni bir promosyon ekler."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Promosyon eklemek için aktif bağlantı gerekli.")
    if not all([name, promotion_type, product_id]):
        raise ValueError("Promosyon adı, türü ve ürün ID'si boş olamaz.")

    # Tür'e göre gerekli alanları kontrol et ve diğerlerine varsayılan ata
    db_required_quantity = 0  # Varsayılan
    db_discount_amount = Decimal('0.00')  # Varsayılan
    db_required_bogo_quantity = 0  # Varsayılan
    db_free_quantity = 0  # Varsayılan

    if promotion_type == 'quantity_discount':
        if not required_quantity or not discount_amount:
            raise ValueError(
                "'quantity_discount' türü için gerekli miktar ve indirim tutarı belirtilmelidir.")
        if required_quantity <= 0 or discount_amount <= 0:
            raise ValueError(
                "Gerekli miktar ve indirim tutarı 0'dan büyük olmalıdır.")
        db_required_quantity = required_quantity
        db_discount_amount = discount_amount
        # Diğer alanlar None kalacak (DB'de NULL olacak)
        free_product_id = None
    elif promotion_type in ['bogo', 'buy_x_get_y_free']:
        if not required_bogo_quantity or not free_quantity:
            raise ValueError(
                f"'{promotion_type}' türü için alınması gereken miktar ve bedava verilecek miktar belirtilmelidir.")
        if required_bogo_quantity <= 0 or free_quantity <= 0:
            raise ValueError(
                "Alınması gereken miktar ve bedava verilecek miktar 0'dan büyük olmalıdır.")
        db_required_bogo_quantity = required_bogo_quantity
        db_free_quantity = free_quantity
        # free_product_id None olabilir
    else:
        raise ValueError(f"Geçersiz promosyon türü: {promotion_type}")

    cursor = None
    try:
        cursor = connection.cursor()
        sql = """INSERT INTO promotions
                 (name, description, promotion_type, product_id,
                  required_quantity, discount_amount,
                  required_bogo_quantity, free_quantity, free_product_id,
                  start_date, end_date, is_active)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)"""
        params = (name, description, promotion_type, product_id,
                  db_required_quantity, db_discount_amount,  # DB'ye gönderilecek değerler
                  # DB'ye gönderilecek değerler
                  db_required_bogo_quantity, db_free_quantity, free_product_id,
                  start_date, end_date)
        cursor.execute(sql, params)
        connection.commit()
        new_promo_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Promosyon '{name}' başarıyla eklendi (ID: {new_promo_id}).[/]")
        return new_promo_id
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Promosyon adı '{name}' zaten kayıtlı!") from e
        elif e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            if 'fk_promotion_product' in str(e):
                 raise DatabaseError(
                     f"Belirtilen ürün ID ({product_id}) bulunamadı.") from e
            elif 'fk_promotion_free_product' in str(e):
                 raise DatabaseError(f"Belirtilen bedava ürün ID ({free_product_id}) bulunamadı.") from e
            else:
                 raise DatabaseError(f"Referans hatası (Ürün veya Bedava Ürün): {e}") from e
        # 1048 hatasını burada yakalamaya gerek yok, yukarıdaki mantıkla engellenmeli.
        # elif e.errno == 1048: # Column cannot be null
        #     raise DatabaseError(f"Veritabanı hatası: Gerekli bir alan boş bırakılmış olamaz. Hata: {e}") from e
        else:
            raise DatabaseError(f"Promosyon ekleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Promosyon Listeleme ===


def list_all_promotions(connection, include_inactive=False):
    """
    Veritabanındaki promosyonları listeler (ürün ve bedava ürün adları ile birlikte).
    Returns:
        list: Promosyon bilgilerini içeren sözlük listesi.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Promosyonları listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = """SELECT
                    pr.promotion_id, pr.name, pr.description, pr.promotion_type,
                    pr.product_id, p.name as product_name,
                    pr.required_quantity, pr.discount_amount,
                    pr.required_bogo_quantity, pr.free_quantity,
                    pr.free_product_id, fp.name as free_product_name, -- Bedava ürün adı
                    pr.start_date, pr.end_date, pr.is_active
                 FROM promotions pr
                 JOIN products p ON pr.product_id = p.product_id
                 LEFT JOIN products fp ON pr.free_product_id = fp.product_id -- Bedava ürün için join
              """
        if not include_inactive:
            sql += " WHERE pr.is_active = TRUE"
        sql += " ORDER BY pr.name ASC"
        cursor.execute(sql)
        results = cursor.fetchall()
        return results
    except Error as e:
        raise DatabaseError(f"Promosyonları listeleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Aktif Promosyonları Getirme (Ürüne Göre) ===


def get_active_promotions_for_product(connection, product_id):
    """
    Belirli bir ürün için şu anda aktif ve geçerli olan promosyonları getirir.
    Args:
        product_id (int): Ürün ID'si.
    Returns:
        list: Geçerli promosyon bilgilerini içeren sözlük listesi.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Aktif promosyonları getirmek için bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        today = datetime.date.today()
        sql = """SELECT
                    promotion_id, name, description, promotion_type, product_id,
                    required_quantity, discount_amount,
                    required_bogo_quantity, free_quantity, free_product_id
                 FROM promotions
                 WHERE product_id = %s
                   AND is_active = TRUE
                   AND (start_date IS NULL OR start_date <= %s)
                   AND (end_date IS NULL OR end_date >= %s)
              """
        params = (product_id, today, today)
        cursor.execute(sql, params)
        results = cursor.fetchall()
        return results
    except Error as e:
        raise DatabaseError(f"Ürün (ID: {product_id}) için aktif promosyonları getirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Promosyon Getirme (ID ile) ===

def get_promotion_by_id(connection, promotion_id):
    """Verilen ID'ye sahip promosyonu tüm bilgileriyle getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Promosyon getirmek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = """SELECT
                    pr.promotion_id, pr.name, pr.description, pr.promotion_type,
                    pr.product_id, p.name as product_name,
                    pr.required_quantity, pr.discount_amount,
                    pr.required_bogo_quantity, pr.free_quantity,
                    pr.free_product_id, fp.name as free_product_name, -- Bedava ürün adı
                    pr.start_date, pr.end_date, pr.is_active
                 FROM promotions pr
                 JOIN products p ON pr.product_id = p.product_id
                 LEFT JOIN products fp ON pr.free_product_id = fp.product_id -- Bedava ürün için join
                 WHERE pr.promotion_id = %s"""
        cursor.execute(sql, (promotion_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(f"Promosyon (ID: {promotion_id}) getirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


# === Promosyon Güncelleme ===
# ***** BU FONKSİYON GÜNCELLENDİ (Varsayılan değer ataması eklendi) *****
def update_promotion(connection, promotion_id, name, description, promotion_type, product_id,
                     required_quantity=None, discount_amount=None,  # quantity_discount için
                     required_bogo_quantity=None, free_quantity=None, free_product_id=None,  # bogo/buy_x_get_y için
                     start_date=None, end_date=None):
    """Verilen ID'ye sahip promosyonu günceller."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Promosyon güncellemek için aktif bağlantı gerekli.")
    if not all([name, promotion_type, product_id]):
        raise ValueError("Promosyon adı, türü ve ürün ID'si boş olamaz.")

    # Tür'e göre gerekli alanları kontrol et ve diğerlerine varsayılan ata
    db_required_quantity = 0  # Varsayılan
    db_discount_amount = Decimal('0.00')  # Varsayılan
    db_required_bogo_quantity = 0  # Varsayılan
    db_free_quantity = 0  # Varsayılan

    if promotion_type == 'quantity_discount':
        if not required_quantity or not discount_amount:
            raise ValueError("'quantity_discount' türü için gerekli miktar ve indirim tutarı belirtilmelidir.")
        if required_quantity <= 0 or discount_amount <= 0:
            raise ValueError("Gerekli miktar ve indirim tutarı 0'dan büyük olmalıdır.")
        db_required_quantity = required_quantity
        db_discount_amount = discount_amount
        # Diğer alanlar None kalacak (DB'de NULL olacak)
        free_product_id = None
    elif promotion_type in ['bogo', 'buy_x_get_y_free']:
        if not required_bogo_quantity or not free_quantity:
            raise ValueError(f"'{promotion_type}' türü için alınması gereken miktar ve bedava verilecek miktar belirtilmelidir.")
        if required_bogo_quantity <= 0 or free_quantity <= 0:
            raise ValueError("Alınması gereken miktar ve bedava verilecek miktar 0'dan büyük olmalıdır.")
        db_required_bogo_quantity = required_bogo_quantity
        db_free_quantity = free_quantity
        # free_product_id None olabilir
    else:
        raise ValueError(f"Geçersiz promosyon türü: {promotion_type}")

    cursor = None
    try:
        cursor = connection.cursor()
        # İsim kontrolü (kendisi hariç)
        sql_check = "SELECT promotion_id FROM promotions WHERE LOWER(name) = LOWER(%s) AND promotion_id != %s"
        cursor.execute(sql_check, (name, promotion_id))
        if cursor.fetchone():
            raise DuplicateEntryError(f"Başka bir promosyonda '{name}' adı zaten kullanılıyor!")

        sql = """UPDATE promotions SET
                    name = %s, description = %s, promotion_type = %s, product_id = %s,
                    required_quantity = %s, discount_amount = %s,
                    required_bogo_quantity = %s, free_quantity = %s, free_product_id = %s,
                    start_date = %s, end_date = %s
                 WHERE promotion_id = %s"""
        params = (name, description, promotion_type, product_id,
                  db_required_quantity, db_discount_amount,  # DB'ye gönderilecek değerler
                  db_required_bogo_quantity, db_free_quantity, free_product_id,  # DB'ye gönderilecek değerler
                  start_date, end_date, promotion_id)
        cursor.execute(sql, params)
        if cursor.rowcount == 0:
            return False  # Bulunamadı veya bilgiler aynı
        else:
            connection.commit()
            rprint(f"[bold green]>>> Promosyon (ID: {promotion_id}) başarıyla güncellendi.[/]")
            return True
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(f"Promosyon adı '{name}' zaten mevcut!") from e
        elif e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            if 'fk_promotion_product' in str(e):
                 raise DatabaseError(f"Belirtilen ürün ID ({product_id}) bulunamadı.") from e
            elif 'fk_promotion_free_product' in str(e):
                 raise DatabaseError(f"Belirtilen bedava ürün ID ({free_product_id}) bulunamadı.") from e
            else:
                 raise DatabaseError(f"Referans hatası (Ürün veya Bedava Ürün): {e}") from e
        # elif e.errno == 1048: # Column cannot be null
        #     raise DatabaseError(f"Veritabanı hatası: Gerekli bir alan boş bırakılmış olamaz. Hata: {e}") from e
        else:
            if not isinstance(e, DuplicateEntryError):
                 raise DatabaseError(f"Promosyon (ID: {promotion_id}) güncelleme hatası: {e}") from e
            else:
                 raise e
    finally:
        if cursor:
            cursor.close()

# === Promosyon Durum Değiştirme ===


def deactivate_promotion(connection, promotion_id):
    """Verilen ID'ye sahip promosyonu pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Promosyon pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE promotions SET is_active = FALSE WHERE promotion_id = %s AND is_active = TRUE"
        cursor.execute(sql, (promotion_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Promosyon (ID: {promotion_id}) pasif yapıldı.[/]")
            return True
        else:
            rprint(f"[yellow]>>> Promosyon (ID: {promotion_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Promosyon (ID: {promotion_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def reactivate_promotion(connection, promotion_id):
    """Verilen ID'ye sahip promosyonu aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Promosyon aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE promotions SET is_active = TRUE WHERE promotion_id = %s AND is_active = FALSE"
        cursor.execute(sql, (promotion_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(f"[bold green]>>> Promosyon (ID: {promotion_id}) aktif yapıldı.[/]")
            return True
        else:
            rprint(f"[yellow]>>> Promosyon (ID: {promotion_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(f"Promosyon (ID: {promotion_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
