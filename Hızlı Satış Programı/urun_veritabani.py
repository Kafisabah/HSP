# urun_veritabani.py
# Ürünlerle ilgili veritabanı işlemlerini içerir.
# ... (Önceki versiyon notları) ...
# v51: get_order_suggestion_data fonksiyonu eklendi.
# v53: Etiket basımı için get_product_details_for_label eklendi.
# v53: update_product fonksiyonu previous_selling_price'ı güncelleyecek şekilde düzenlendi.

from mysql.connector import Error, errorcode
from decimal import Decimal, InvalidOperation
from hatalar import DatabaseError, DuplicateEntryError, SaleIntegrityError
from rich import print as rprint
import datetime

# === Ürün Ekleme ===
# ... (add_product fonksiyonu - değişiklik yok, ancak yeni eklenen ürünlerde previous_selling_price NULL olacak) ...


def add_product(connection, barcode, name, brand_id: int, price_before_kdv: Decimal, kdv_rate: Decimal, selling_price: Decimal, stock: int, category_id: int = None, min_stock_level: int = 2):
    """Veritabanına yeni bir ürün ekler (marka, kategori ID'si ve min stok seviyesi ile)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün eklemek için aktif bağlantı gerekli.")
    if brand_id is None:  # Marka zorunlu
        raise ValueError("Marka ID'si boş olamaz.")
    if not name:
        raise ValueError("Ürün adı boş olamaz.")

    cursor = None
    try:
        cursor = connection.cursor()

        # 1. Benzersiz İsim Kontrolü (Case-insensitive)
        sql_check_name = "SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s)"
        cursor.execute(sql_check_name, (name,))
        existing_product = cursor.fetchone()
        if existing_product:
            raise DuplicateEntryError(f"Ürün adı '{name}' zaten mevcut!")

        # 2. Benzersiz Barkod Kontrolü (Veritabanı zaten yapıyor ama emin olmak için)
        sql_check_barcode = "SELECT product_id FROM products WHERE barcode = %s"
        cursor.execute(sql_check_barcode, (barcode,))
        existing_barcode = cursor.fetchone()
        if existing_barcode:
            raise DuplicateEntryError(f"Barkod ({barcode}) zaten kayıtlı!")

        # 3. Ürünü Ekle
        # previous_selling_price NULL olarak eklenecek
        sql_insert = """INSERT INTO products
                 (barcode, name, brand_id, category_id, price_before_kdv, kdv_rate,
                  selling_price, stock, is_active, min_stock_level, previous_selling_price)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, NULL)"""
        params = (barcode, name, brand_id, category_id, price_before_kdv, kdv_rate,
                  selling_price, stock, min_stock_level)
        cursor.execute(sql_insert, params)
        connection.commit()
        new_product_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Ürün '{name}' başarıyla eklendi (ID: {new_product_id}).[/]")
        return new_product_id
    except Error as e:
        if e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            if 'fk_product_brand' in e.msg:
                raise DatabaseError(
                    f"Belirtilen marka ID ({brand_id}) bulunamadı.") from e
            elif 'fk_product_category' in e.msg:
                raise DatabaseError(
                    f"Belirtilen kategori ID ({category_id}) bulunamadı.") from e
            else:
                raise DatabaseError(
                    f"Referans hatası (Marka veya Kategori): {e.msg}") from e
        else:
            if not isinstance(e, DuplicateEntryError):
                raise DatabaseError(f"Ürün ekleme hatası: {e}") from e
            else:
                raise e
    finally:
        if cursor:
            cursor.close()


# === Ürün Arama/Getirme ===
# ... (get_product_by_id, get_product_by_barcode, get_products_by_name_like, get_products_by_barcodes fonksiyonları - değişiklik yok) ...
def get_product_by_id(connection, product_id):
    """Verilen ID'ye sahip ürünü tüm bilgileriyle (kategori adı, marka adı ve min stok dahil) getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # previous_selling_price ve last_updated sütunlarını da seçelim
        sql = """SELECT
                    p.product_id, p.barcode, p.name, p.price_before_kdv, p.kdv_rate,
                    p.selling_price, p.stock, p.is_active, p.category_id, p.min_stock_level,
                    p.brand_id, b.name as brand_name,
                    c.name as category_name,
                    p.previous_selling_price, p.last_updated
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.category_id
                 LEFT JOIN brands b ON p.brand_id = b.brand_id
                 WHERE p.product_id = %s"""
        cursor.execute(sql, (product_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"ID ({product_id}) ile ürün arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_product_by_barcode(connection, barcode, only_active=True):
    """
    Verilen barkoda sahip ürünü getirir (kategori adı, marka adı ve min stok dahil).
    Returns:
        dict: Ürün bilgileri sözlüğü veya None.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # previous_selling_price ve last_updated sütunlarını da seçelim
        sql = """SELECT
                    p.product_id, p.barcode, p.name, p.price_before_kdv, p.kdv_rate,
                    p.selling_price, p.stock, p.is_active, p.category_id, p.min_stock_level,
                    p.brand_id, b.name as brand_name,
                    c.name as category_name,
                    p.previous_selling_price, p.last_updated
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.category_id
                 LEFT JOIN brands b ON p.brand_id = b.brand_id
                 WHERE p.barcode = %s"""
        params = [barcode]
        if only_active:
            sql += " AND p.is_active = TRUE"
        cursor.execute(sql, params)
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"Barkod ({barcode}) ile ürün arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_products_by_name_like(connection, search_term, only_active=True):
    """
    Verilen isim parçasını içeren ürünleri arar (kategori adı, marka adı ve min stok dahil).
    Returns:
        list: Bulunan ürünlerin bilgilerini içeren sözlük listesi veya boş liste.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # previous_selling_price ve last_updated sütunlarını da seçelim
        sql = """SELECT
                    p.product_id, p.barcode, p.name, p.price_before_kdv, p.kdv_rate,
                    p.selling_price, p.stock, p.is_active, p.category_id, p.min_stock_level,
                    p.brand_id, b.name as brand_name,
                    c.name as category_name,
                    p.previous_selling_price, p.last_updated
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.category_id
                 LEFT JOIN brands b ON p.brand_id = b.brand_id
                 WHERE LOWER(p.name) LIKE LOWER(%s)"""
        pattern = f"%{search_term}%"
        params = [pattern]
        if only_active:
            sql += " AND p.is_active = TRUE"
        sql += " ORDER BY p.name ASC"
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(
            f"İsim ('{search_term}') ile ürün arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_products_by_barcodes(connection, barcode_list):
    """
    Verilen barkod listesindeki AKTİF ürünlerin bilgilerini getirir.
    Hızlı butonlar için kullanılır.
    Args:
        barcode_list (list): Barkod string listesi.
    Returns:
        list: Bulunan aktif ürünlerin bilgilerini içeren sözlük listesi.
              Barkod sırası korunmaz, veritabanından geldiği gibi döner.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün aramak için aktif bağlantı gerekli.")
    if not barcode_list:
        return []

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        placeholders = ', '.join(['%s'] * len(barcode_list))
        # previous_selling_price ve last_updated sütunlarını da seçelim
        sql = f"""SELECT
                    p.product_id, p.barcode, p.name, p.price_before_kdv, p.kdv_rate,
                    p.selling_price, p.stock, p.is_active, p.category_id, p.min_stock_level,
                    p.brand_id, b.name as brand_name,
                    c.name as category_name,
                    p.previous_selling_price, p.last_updated
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.category_id
                 LEFT JOIN brands b ON p.brand_id = b.brand_id
                 WHERE p.barcode IN ({placeholders}) AND p.is_active = TRUE"""
        cursor.execute(sql, barcode_list)
        results = cursor.fetchall()
        return results
    except Error as e:
        raise DatabaseError(
            f"Barkod listesi ile ürün arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


# === Ürün Güncelleme ===

# ***** BU FONKSİYON GÜNCELLENDİ (previous_selling_price kaydı eklendi) *****
def update_product(connection, product_id, new_name, new_brand_id: int, new_category_id: int, new_price_before_kdv: Decimal, new_kdv_rate: Decimal, new_selling_price: Decimal, new_stock: int, new_min_stock_level: int = None):
    """
    Verilen ID'ye sahip ürünün bilgilerini günceller.
    Eğer satış fiyatı değişiyorsa, mevcut satış fiyatını 'previous_selling_price' sütununa kaydeder.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün güncellemek için aktif bağlantı gerekli.")
    if new_brand_id is None:
        raise ValueError("Marka ID'si boş olamaz.")
    if not new_name:
        raise ValueError("Ürün adı boş olamaz.")

    cursor = None
    try:
        cursor = connection.cursor()

        # 1. İsim kontrolü (kendisi hariç)
        sql_check_name = "SELECT product_id FROM products WHERE LOWER(name) = LOWER(%s) AND product_id != %s"
        cursor.execute(sql_check_name, (new_name, product_id))
        existing_product_name = cursor.fetchone()
        if existing_product_name:
            raise DuplicateEntryError(
                f"Başka bir üründe '{new_name}' adı zaten kullanılıyor!")

        # 2. Mevcut satış fiyatını al (önceki fiyat olarak kaydetmek için)
        sql_get_current_price = "SELECT selling_price FROM products WHERE product_id = %s"
        cursor.execute(sql_get_current_price, (product_id,))
        current_price_result = cursor.fetchone()
        current_selling_price = current_price_result[0] if current_price_result else None

        # 3. Önceki fiyatı belirle
        previous_price_to_save = None
        if current_selling_price is not None and new_selling_price != current_selling_price:
            # Eğer mevcut fiyat varsa ve yeni fiyat farklıysa, mevcut fiyatı önceki fiyat yap
            previous_price_to_save = current_selling_price
        elif current_selling_price is not None:
            # Eğer fiyat değişmiyorsa, DB'deki previous_selling_price'ı korumak için onu okuyalım
             sql_get_previous_price = "SELECT previous_selling_price FROM products WHERE product_id = %s"
             cursor.execute(sql_get_previous_price, (product_id,))
             prev_price_result = cursor.fetchone()
             previous_price_to_save = prev_price_result[0] if prev_price_result else None

        # 4. Güncelleme sorgusu (previous_selling_price sütunu eklendi)
        # last_updated sütunu DB tarafından otomatik güncellenir (ON UPDATE CURRENT_TIMESTAMP)
        sql_update = """UPDATE products SET
                    name = %s, brand_id = %s, category_id = %s,
                    price_before_kdv = %s, kdv_rate = %s,
                    selling_price = %s,
                    previous_selling_price = %s, -- Önceki fiyatı kaydet
                    stock = %s,
                    min_stock_level = %s
                 WHERE product_id = %s"""
        params = (new_name, new_brand_id, new_category_id,
                  new_price_before_kdv, new_kdv_rate, new_selling_price,
                  previous_price_to_save,  # Kaydedilecek önceki fiyat
                  new_stock, new_min_stock_level, product_id)
        cursor.execute(sql_update, params)

        if cursor.rowcount == 0:
            # Eğer hiç satır güncellenmediyse (örn. ID bulunamadı) False dön
            # Not: Eğer bilgiler aynıysa da rowcount 0 olabilir, ama bu durumda da işlem başarılı sayılabilir.
            # Emin olmak için önce ürünün varlığını kontrol etmek daha iyi olabilir, ama şimdilik böyle bırakalım.
            rprint(
                f"[yellow]Uyarı: Ürün (ID: {product_id}) bulunamadı veya bilgiler zaten aynıydı.[/]")
            return False
        else:
            connection.commit()
            rprint(
                f"[bold green]>>> Ürün (ID: {product_id}) başarıyla güncellendi.[/]")
            return True
    except Error as e:
        if e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            if 'fk_product_brand' in e.msg:
                raise DatabaseError(
                    f"Belirtilen marka ID ({new_brand_id}) bulunamadı.") from e
            elif 'fk_product_category' in e.msg:
                raise DatabaseError(
                    f"Belirtilen kategori ID ({new_category_id}) bulunamadı.") from e
            else:
                raise DatabaseError(
                    f"Referans hatası (Marka veya Kategori): {e.msg}") from e
        elif e.errno == errorcode.ER_TRUNCATED_WRONG_VALUE_FOR_FIELD and 'min_stock_level' in e.msg:
            raise ValueError(
                "Minimum stok seviyesi geçerli bir tam sayı olmalıdır.") from e
        else:
            if not isinstance(e, DuplicateEntryError):
                raise DatabaseError(
                    f"Ürün (ID: {product_id}) güncelleme hatası: {e}") from e
            else:
                raise e
    finally:
        if cursor:
            cursor.close()

# === Ürün Listeleme ===
# ... (list_all_products fonksiyonu - değişiklik yok) ...


def list_all_products(connection, include_inactive=False):
    """Veritabanındaki ürünleri listeler (kategori adı, marka adı ve min stok dahil)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürünleri listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # previous_selling_price ve last_updated sütunlarını da seçelim (listede göstermek için)
        sql = """SELECT
                    p.product_id, p.barcode, p.name, p.price_before_kdv, p.kdv_rate,
                    p.selling_price, p.stock, p.is_active, p.category_id, p.min_stock_level,
                    p.brand_id, b.name as brand_name,
                    c.name as category_name,
                    p.previous_selling_price, p.last_updated
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.category_id
                 LEFT JOIN brands b ON p.brand_id = b.brand_id
                 """
        if not include_inactive:
            sql += " WHERE p.is_active = TRUE"
        sql += " ORDER BY p.name ASC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Ürünleri listeleme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Stok ve Alış İşlemleri ===
# ... (increase_stock, record_purchase, get_last_cost_price fonksiyonları - değişiklik yok) ...


def increase_stock(connection, product_id, quantity_increase):
    """
    Belirtilen ürünün stoğunu verilen miktar kadar artırır.
    Commit yapmaz, transaction içinde kullanılmalıdır.
    """
    if quantity_increase <= 0:
        raise ValueError("Stoğa eklenecek miktar pozitif olmalıdır.")
    if not connection or not connection.is_connected():
        raise DatabaseError("Stok güncellemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE products SET stock = stock + %s WHERE product_id = %s"
        cursor.execute(sql, (quantity_increase, product_id))
        if cursor.rowcount == 0:
            return False
        return True
    except Error as e:
        raise DatabaseError(
            f"Ürün (ID: {product_id}) stok artırma hatası: {e}") from e
    finally:
        pass


def record_purchase(connection, purchase_info: dict, items_list: list):
    """
    Alış işlemini (başlık ve kalemler) veritabanına kaydeder ve stokları günceller.
    items_list içindeki her item'da 'expiry_date' (YYYY-MM-DD veya None) olabilir.
    Tek bir transaction içinde yapar.
    """
    if not items_list:
        raise ValueError("Alış kaydı için en az bir ürün girilmelidir.")
    if not connection or not connection.is_connected():
        raise DatabaseError("Stok girişi için aktif bağlantı gerekli.")
    cursor = None
    purchase_id = None
    try:
        cursor = connection.cursor()

        sql_insert_purchase = """
            INSERT INTO purchases (supplier_id, invoice_number, notes)
            VALUES (%s, %s, %s)
            """
        purchase_params = (
            purchase_info.get('supplier_id'), purchase_info.get(
                'invoice_number'), purchase_info.get('notes')
        )
        cursor.execute(sql_insert_purchase, purchase_params)
        purchase_id = cursor.lastrowid
        if not purchase_id:
            raise DatabaseError("Yeni alış ID'si alınamadı!")

        sql_insert_item = """
            INSERT INTO purchase_items (purchase_id, product_id, quantity, cost_price, expiry_date)
            VALUES (%s, %s, %s, %s, %s)
            """
        for item in items_list:
            expiry_date = item.get('expiry_date')
            item_params = (
                purchase_id, item['product_id'], item['quantity'], item.get(
                    'cost_price'),
                expiry_date
            )
            cursor.execute(sql_insert_item, item_params)

            if not increase_stock(connection, item['product_id'], item['quantity']):
                raise SaleIntegrityError(
                    f"Stok artırma hatası: Ürün ID {item['product_id']} bulunamadı!")

        connection.commit()
        rprint(
            f"[bold green]>>> Alış işlemi (ID: {purchase_id}) başarıyla kaydedildi ve stoklar güncellendi.[/]")
        return purchase_id
    except (Error, SaleIntegrityError, DatabaseError, ValueError) as e:
        error_type = type(e).__name__
        rprint(f"\n[bold red]>>> {error_type} (Alış Kaydı):[/bold red] {e}")
        rprint("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        return None
    except Exception as genel_hata:
        rprint(
            f"\n[bold red]>>> BEKLENMEDİK PROGRAM HATASI (Alış Kaydı):[/bold red] {genel_hata}")
        rprint("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        return None
    finally:
        if cursor:
            cursor.close()


def get_last_cost_price(connection, product_id):
    """
    Bir ürün için kaydedilmiş son geçerli (NULL olmayan) alış fiyatını getirir.
    Returns: Decimal veya None
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Son alış fiyatı için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = """
            SELECT pi.cost_price
            FROM purchase_items pi
            JOIN purchases p ON pi.purchase_id = p.purchase_id
            WHERE pi.product_id = %s AND pi.cost_price IS NOT NULL
            ORDER BY p.purchase_date DESC, pi.purchase_item_id DESC
            LIMIT 1
        """
        cursor.execute(sql, (product_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        print(
            f"[yellow]Uyarı: Ürün (ID: {product_id}) için son alış fiyatı alınamadı: {e}[/]")
        return None
    finally:
        if cursor:
            cursor.close()


# === Ürün Aktif/Pasif Yapma ===
# ... (deactivate_product, reactivate_product fonksiyonları - değişiklik yok) ...
def deactivate_product(connection, product_id):
    """Verilen ID'ye sahip ürünü pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE products SET is_active = FALSE WHERE product_id = %s AND is_active = TRUE"
        cursor.execute(sql, (product_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(
                f"[bold green]>>> Ürün (ID: {product_id}) pasif yapıldı.[/]")
            return True
        else:
            rprint(
                f"[yellow]>>> Ürün (ID: {product_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Ürün (ID: {product_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def reactivate_product(connection, product_id):
    """Verilen ID'ye sahip ürünü aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Ürün aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE products SET is_active = TRUE WHERE product_id = %s AND is_active = FALSE"
        cursor.execute(sql, (product_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(
                f"[bold green]>>> Ürün (ID: {product_id}) aktif yapıldı.[/]")
            return True
        else:
            rprint(
                f"[yellow]>>> Ürün (ID: {product_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Ürün (ID: {product_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


# === Stok Raporu ===
# ... (get_stock_report_data fonksiyonu - değişiklik yok) ...
def get_stock_report_data(connection, stock_threshold=None, include_inactive=False, only_critical=False):
    """
    Stok raporu için ürün verilerini getirir (marka adı dahil).
    Args:
        only_critical (bool): True ise sadece stoğu min_stock_level altında olanları getirir.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Stok raporu için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        params = []
        sql_query = """
            SELECT p.product_id, p.barcode, p.name, p.stock, p.min_stock_level, p.is_active,
                   b.name as brand_name
            FROM products p
            LEFT JOIN brands b ON p.brand_id = b.brand_id
            """
        where_clauses = []
        if not include_inactive:
            where_clauses.append("p.is_active = TRUE")

        if only_critical:
            # COALESCE ile min_stock_level NULL ise 0 kabul et
            where_clauses.append(
                "(p.stock <= COALESCE(p.min_stock_level, 0))")
        elif stock_threshold is not None:
            where_clauses.append("p.stock <= %s")
            params.append(stock_threshold)

        if where_clauses:
            sql_query += " WHERE " + " AND ".join(where_clauses)

        sql_query += " ORDER BY p.stock ASC, p.name ASC"

        cursor.execute(sql_query, params)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Stok raporu verisi alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


# === Stok Ayarlama ===
# ... (set_stock_level fonksiyonu - değişiklik yok) ...
def set_stock_level(connection, product_id, new_stock_level):
    """
    Bir ürünün stoğunu doğrudan belirtilen değere ayarlar.
    Args:
        product_id (int): Ürün ID'si.
        new_stock_level (int): Ayarlanacak yeni stok miktarı.
    Returns:
        bool: İşlem başarılıysa True, değilse False.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Stok ayarlamak için aktif bağlantı gerekli.")
    if new_stock_level < 0:
        pass
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE products SET stock = %s WHERE product_id = %s"
        cursor.execute(sql, (new_stock_level, product_id))
        if cursor.rowcount == 0:
            rprint(f"[red]HATA: Ürün (ID: {product_id}) bulunamadı.[/]")
            return False
        else:
            connection.commit()
            rprint(
                f"[bold green]>>> Ürün (ID: {product_id}) stoğu {new_stock_level} olarak ayarlandı.[/]")
            return True
    except Error as e:
        raise DatabaseError(
            f"Ürün (ID: {product_id}) stok ayarlama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


# === Sipariş Önerisi Verileri ===
# ... (get_order_suggestion_data fonksiyonu - değişiklik yok) ...
def get_order_suggestion_data(connection):
    """
    Minimum stok seviyesinin altına düşmüş aktif ürünler için sipariş öneri verilerini toplar.
    Veriler: barkod, ad, mevcut stok, min stok, son alış fiyatı, son tedarikçi, tahmini tükenme süresi (gün).
    Returns:
        list: Her ürün için bilgileri içeren sözlük listesi.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Sipariş önerisi için aktif bağlantı gerekli.")

    main_cursor = None
    suggestion_list = []

    try:
        main_cursor = connection.cursor(dictionary=True)
        sql_critical = """
            SELECT product_id, barcode, name, stock, min_stock_level
            FROM products
            WHERE is_active = TRUE AND stock <= COALESCE(min_stock_level, 0)
            ORDER BY name ASC
        """
        main_cursor.execute(sql_critical)
        critical_products = main_cursor.fetchall()
        main_cursor.close()
        main_cursor = None

        if not critical_products:
            return []

        for product in critical_products:
            product_id = product['product_id']
            suggestion = {
                'product_id': product_id,
                'barcode': product['barcode'],
                'name': product['name'],
                'current_stock': product['stock'],
                'min_stock_level': product['min_stock_level'],
                'last_cost': None,
                'last_supplier': None,
                'days_lasted': None
            }

            cursor = None
            try:
                cursor = connection.cursor(dictionary=True)

                sql_last_purchase = """
                    SELECT pi.cost_price, pu.supplier_id
                    FROM purchase_items pi
                    JOIN purchases pu ON pi.purchase_id = pu.purchase_id
                    WHERE pi.product_id = %s AND pi.cost_price IS NOT NULL
                    ORDER BY pu.purchase_date DESC, pi.purchase_item_id DESC
                    LIMIT 1
                """
                cursor.execute(sql_last_purchase, (product_id,))
                last_purchase_info = cursor.fetchone()

                if last_purchase_info:
                    suggestion['last_cost'] = last_purchase_info.get(
                        'cost_price')
                    last_supplier_id = last_purchase_info.get('supplier_id')
                    if last_supplier_id:
                        sql_supplier = "SELECT name FROM suppliers WHERE supplier_id = %s"
                        cursor.execute(sql_supplier, (last_supplier_id,))
                        supplier_result = cursor.fetchone()
                        if supplier_result:
                            suggestion['last_supplier'] = supplier_result.get(
                                'name')

                sql_purchase_dates = """
                    SELECT pu.purchase_date
                    FROM purchases pu
                    JOIN purchase_items pi ON pu.purchase_id = pi.purchase_id
                    WHERE pi.product_id = %s
                    ORDER BY pu.purchase_date DESC
                    LIMIT 2
                """
                cursor.execute(sql_purchase_dates, (product_id,))
                purchase_dates_result = cursor.fetchall()

                if len(purchase_dates_result) == 2:
                    date1 = purchase_dates_result[0]['purchase_date']
                    date2 = purchase_dates_result[1]['purchase_date']
                    if isinstance(date1, datetime.datetime) and isinstance(date2, datetime.datetime):
                        time_difference = date1.date() - date2.date()
                        suggestion['days_lasted'] = time_difference.days
                    elif isinstance(date1, datetime.date) and isinstance(date2, datetime.date):
                        time_difference = date1 - date2
                        suggestion['days_lasted'] = time_difference.days

                suggestion_list.append(suggestion)

            except Error as inner_e:
                rprint(
                    f"[yellow]Uyarı: Ürün ID {product_id} için öneri bilgisi alınırken hata: {inner_e}[/]")
            finally:
                if cursor:
                     cursor.close()

        return suggestion_list

    except Error as e:
        error_msg = str(e).lower()
        if 'unknown column' in error_msg:
            if "'cost_price'" in error_msg:
                 raise DatabaseError(
                     "Sipariş önerisi alınamadı. 'purchase_items' tablosunda 'cost_price' sütunu bulunamadı veya adı farklı.") from e
            if "'suppliers.name'" in error_msg:
                 raise DatabaseError("Sipariş önerisi alınamadı. 'suppliers' tablosunda 'name' sütunu bulunamadı veya adı farklı.") from e
        raise DatabaseError(f"Sipariş öneri verisi alma hatası: {e}") from e
    except Exception as genel_hata:
        raise DatabaseError(f"Sipariş öneri verisi işlenirken beklenmedik hata: {genel_hata}") from genel_hata
    finally:
        if main_cursor:
            try:
                 main_cursor.close()
            except Error:
                 pass

# ***** YENİ FONKSİYON: Etiket Verisi Getirme *****

def get_product_details_for_label(connection, product_id):
    """
    Etiket basımı için belirli bir ürünün gerekli tüm detaylarını getirir.
    (last_updated ve previous_selling_price dahil)
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Etiket verisi için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # Gerekli tüm sütunları seçtiğimizden emin olalım
        sql = """SELECT
                    product_id, barcode, name, price_before_kdv, kdv_rate,
                    selling_price, previous_selling_price, last_updated
                 FROM products
                 WHERE product_id = %s"""
        cursor.execute(sql, (product_id,))
        product_data = cursor.fetchone()
        if not product_data:
            raise DatabaseError(f"Ürün (ID: {product_id}) etiket verisi için bulunamadı.")
        return product_data
    except Error as e:
        raise DatabaseError(
            f"Ürün (ID: {product_id}) etiket verisi alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
# ***** YENİ FONKSİYON SONU *****
