# musteri_veritabani.py
# Müşterilerle ilgili veritabanı işlemlerini içerir.
# v28: Kupon tanımlama ve müşteri kupon işlemleri eklendi.
# v46: record_customer_payment fonksiyonuna shift_id eklendi.
# v49: get_customer_available_coupons sorgusundaki expiry_date sütun adı ve durum kontrolü düzeltildi.
# v50: get_customer_ledger sorgusundaki payment_id sütun adı customer_payment_id olarak düzeltildi.

from mysql.connector import Error, errorcode
from decimal import Decimal
import datetime
from hatalar import DatabaseError, DuplicateEntryError
from rich import print as rprint
import arayuz_yardimcilari as ui  # console için

# console nesnesini alalım
try:
    console = ui.console
except AttributeError:
    from rich.console import Console
    console = Console()
    rprint("[yellow]Uyarı: arayuz_yardimcilari modülünde 'console' nesnesi bulunamadı, burada oluşturuldu.[/]")


# === Müşteri Ekleme ===
def add_customer(connection, name, phone=None, email=None, address=None):
    """Veritabanına yeni bir müşteri ekler."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Müşteri eklemek için aktif bağlantı gerekli.")
    if not name:
        raise ValueError("Müşteri adı boş olamaz.")
    cursor = None
    try:
        cursor = connection.cursor()
        if phone:
            sql_check_phone = "SELECT customer_id FROM customers WHERE phone = %s"
            cursor.execute(sql_check_phone, (phone,))
            if cursor.fetchone():
                 raise DuplicateEntryError(
                     f"Telefon numarası '{phone}' zaten başka bir müşteriye kayıtlı!")
        if email:
            sql_check_email = "SELECT customer_id FROM customers WHERE email = %s"
            cursor.execute(sql_check_email, (email,))
            if cursor.fetchone():
                 raise DuplicateEntryError(
                     f"E-posta adresi '{email}' zaten başka bir müşteriye kayıtlı!")

        sql = """INSERT INTO customers
                 (name, phone, email, address, balance, loyalty_points, is_active)
                 VALUES (%s, %s, %s, %s, 0.00, 0, TRUE)"""
        params = (name, phone, email, address)
        cursor.execute(sql, params)
        connection.commit()
        new_customer_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Müşteri '{name}' başarıyla eklendi (ID: {new_customer_id}).[/]")
        return new_customer_id
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Müşteri eklenemedi. Telefon veya E-posta zaten kayıtlı olabilir.") from e
        else:
            if not isinstance(e, DuplicateEntryError):
                 raise DatabaseError(f"Müşteri ekleme hatası: {e}") from e
            else:
                 raise e
    finally:
        if cursor:
            cursor.close()

# === Müşteri Arama/Getirme ===

def get_customer_by_id(connection, customer_id):
    """Verilen ID'ye sahip müşteriyi tüm bilgileriyle getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Müşteri aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT * FROM customers WHERE customer_id = %s"
        cursor.execute(sql, (customer_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"ID ({customer_id}) ile müşteri arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_customer_by_phone(connection, phone, only_active=True):
    """Verilen telefon numarasına sahip müşteriyi getirir (ID, Ad, Aktiflik)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Müşteri aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "SELECT customer_id, name, is_active FROM customers WHERE phone = %s"
        params = [phone]
        if only_active:
            sql += " AND is_active = TRUE"
        cursor.execute(sql, params)
        return cursor.fetchone()  # Tek kayıt veya None döner
    except Error as e:
        raise DatabaseError(
            f"Telefon ({phone}) ile müşteri arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_customers_by_name_like(connection, search_term, only_active=True):
    """Verilen isim parçasını içeren müşterileri arar (ID, Ad, Aktiflik)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Müşteri aramak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "SELECT customer_id, name, is_active FROM customers WHERE LOWER(name) LIKE LOWER(%s)"
        pattern = f"%{search_term}%"
        params = [pattern]
        if only_active:
            sql += " AND is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql, params)
        return cursor.fetchall()  # Liste döner
    except Error as e:
        raise DatabaseError(
            f"İsim ('{search_term}') ile müşteri arama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_all_customers_detailed(connection, include_inactive=False):
    """Tüm müşterilerin detaylı bilgilerini getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Müşterileri listelemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = "SELECT * FROM customers"
        if not include_inactive:
            sql += " WHERE is_active = TRUE"
        sql += " ORDER BY name ASC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Detaylı müşteri listesi alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Müşteri Güncelleme ===

def update_customer(connection, customer_id, new_name, new_phone=None, new_email=None, new_address=None):
    """Verilen ID'ye sahip müşterinin bilgilerini günceller."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Müşteri güncellemek için aktif bağlantı gerekli.")
    if not new_name:
        raise ValueError("Yeni müşteri adı boş olamaz.")
    cursor = None
    try:
        cursor = connection.cursor()
        if new_phone:
            sql_check_phone = "SELECT customer_id FROM customers WHERE phone = %s AND customer_id != %s"
            cursor.execute(sql_check_phone, (new_phone, customer_id))
            if cursor.fetchone():
                 raise DuplicateEntryError(f"Telefon numarası '{new_phone}' zaten başka bir müşteriye kayıtlı!")
        if new_email:
            sql_check_email = "SELECT customer_id FROM customers WHERE email = %s AND customer_id != %s"
            cursor.execute(sql_check_email, (new_email, customer_id))
            if cursor.fetchone():
                 raise DuplicateEntryError(f"E-posta adresi '{new_email}' zaten başka bir müşteriye kayıtlı!")

        sql = """UPDATE customers SET
                 name = %s, phone = %s, email = %s, address = %s
                 WHERE customer_id = %s"""
        params = (new_name, new_phone, new_email, new_address, customer_id)
        cursor.execute(sql, params)
        if cursor.rowcount == 0:
            return False
        else:
            connection.commit()
            rprint(
                f"[bold green]>>> Müşteri (ID: {customer_id}) başarıyla güncellendi.[/]")
            return True
    except Error as e:
        if e.errno == errorcode.ER_DUP_ENTRY:
            raise DuplicateEntryError(
                f"Müşteri güncellenemedi. Telefon veya E-posta zaten kayıtlı olabilir.") from e
        else:
            if not isinstance(e, DuplicateEntryError):
                 raise DatabaseError(f"Müşteri (ID: {customer_id}) güncelleme hatası: {e}") from e
            else:
                 raise e
    finally:
        if cursor:
            cursor.close()

# === Müşteri Bakiye İşlemleri ===

def get_customer_balance(connection, customer_id):
    """Müşterinin mevcut bakiyesini getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Bakiye sorgulamak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "SELECT balance FROM customers WHERE customer_id = %s"
        cursor.execute(sql, (customer_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        raise DatabaseError(
            f"Müşteri (ID: {customer_id}) bakiye sorgulama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def update_customer_balance(connection, customer_id, amount_change):
    """
    Müşterinin bakiyesini belirtilen miktar kadar günceller.
    Commit yapmaz, transaction içinde kullanılmalıdır.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Bakiye güncellemek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE customers SET balance = balance + %s WHERE customer_id = %s"
        cursor.execute(sql, (amount_change, customer_id))
        if cursor.rowcount == 0:
            return False
        return True
    except Error as e:
        raise DatabaseError(
            f"Müşteri (ID: {customer_id}) bakiye güncelleme hatası: {e}") from e
    finally:
        pass


def record_customer_payment(connection, customer_id, amount, payment_method, notes=None, shift_id=None):
    """
    Müşteriden alınan ödemeyi kaydeder ve bakiyesini günceller.
    Tek bir transaction içinde yapar.
    Args:
        shift_id (int, optional): Ödemenin alındığı vardiya ID'si. Defaults to None.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Müşteri ödemesi kaydetmek için aktif bağlantı gerekli.")
    if amount <= 0:
        raise ValueError("Ödeme miktarı pozitif olmalıdır.")

    cursor = None
    payment_id = None
    try:
        cursor = connection.cursor()

        # 1. Ödeme Kaydını Ekle (shift_id ile birlikte)
        sql_insert = """INSERT INTO customer_payments
                        (customer_id, shift_id, amount, payment_method, notes)
                        VALUES (%s, %s, %s, %s, %s)"""
        params = (customer_id, shift_id, amount, payment_method, notes)
        cursor.execute(sql_insert, params)
        payment_id = cursor.lastrowid
        if not payment_id:
            raise DatabaseError("Yeni müşteri ödeme ID'si alınamadı!")

        # 2. Müşteri Bakiyesini Güncelle (Alınan ödeme borcu azaltır -> negatif amount_change)
        if not update_customer_balance(connection, customer_id, -amount):
            raise SaleIntegrityError(f"Müşteri (ID: {customer_id}) ödeme sonrası bakiye güncelleme hatası!")

        # 3. Commit
        connection.commit()
        rprint(
            f"[bold green]>>> Müşteri (ID: {customer_id}) için {amount:.2f} TL ödeme (ID: {payment_id}, Yöntem: {payment_method}) başarıyla kaydedildi.[/]")
        return payment_id

    except (Error, SaleIntegrityError, DatabaseError, ValueError) as e:
        error_type = type(e).__name__
        console.print(
            f"\n[bold red]>>> {error_type} (Müşteri Ödeme Kaydı):[/] {e}", style="bold red")
        console.print("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        return None
    except Exception as genel_hata:
        console.print(
            f"\n[bold red]>>> BEKLENMEDİK PROGRAM HATASI (Müşteri Ödeme Kaydı):[/] {genel_hata}", style="bold red")
        console.print("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        return None
    finally:
        if cursor:
            cursor.close()

# musteri_veritabani.py
# ... (Dosyanın geri kalanı aynı) ...

# === Müşteri Bakiye İşlemleri ===
# ... (get_customer_balance, update_customer_balance, record_customer_payment fonksiyonları aynı) ...


# ***** BU FONKSİYON GÜNCELLENDİ (payment_id -> cust_payment_id) *****
def get_customer_ledger(connection, customer_id, start_date=None, end_date=None):
    """Müşterinin hesap hareketlerini (satışlar ve ödemeler) getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Hesap ekstresi için aktif bağlantı gerekli.")
    cursor = None
    ledger = []
    try:
        cursor = connection.cursor(dictionary=True)

        # Satışları (Borç) al
        sql_sales = """SELECT sale_id, sale_date as date, total_amount as debit, NULL as credit,
                       'Satış' as type, CONCAT('Fiş No: ', sale_id) as description
                       FROM sales
                       WHERE customer_id = %s AND status = 'completed' """
        params_sales = [customer_id]
        if start_date:
            sql_sales += " AND sale_date >= %s "
            params_sales.append(start_date)
        if end_date:
            end_date_inclusive = end_date + datetime.timedelta(days=1)
            sql_sales += " AND sale_date < %s "
            params_sales.append(end_date_inclusive)

        cursor.execute(sql_sales, params_sales)
        ledger.extend(cursor.fetchall())

        # Ödemeleri (Alacak) al
        # ***** DEĞİŞİKLİK BURADA: payment_id yerine doğru sütun adı cust_payment_id kullanıldı *****
        sql_payments = """SELECT cust_payment_id, payment_date as date, NULL as debit, amount as credit,
                          'Ödeme' as type, CONCAT(payment_method, ' - ', COALESCE(notes, '')) as description
                          FROM customer_payments
                          WHERE customer_id = %s """
        params_payments = [customer_id]
        if start_date:
            sql_payments += " AND payment_date >= %s "
            params_payments.append(start_date)
        if end_date:
            end_date_inclusive = end_date + datetime.timedelta(days=1)
            sql_payments += " AND payment_date < %s "
            params_payments.append(end_date_inclusive)

        cursor.execute(sql_payments, params_payments)
        ledger.extend(cursor.fetchall())

        # Tarihe göre sırala
        ledger.sort(key=lambda x: x['date']
                    if x['date'] else datetime.datetime.min)

        return ledger

    except Error as e:
        # Hatayı daha spesifik hale getirelim
        if 'cust_payment_id' in str(e) and 'Unknown column' in str(e):
            # Eğer 'cust_payment_id' de bilinmiyorsa, bu çok beklenmedik bir durum olur.
            raise DatabaseError(
                f"Müşteri (ID: {customer_id}) hesap ekstresi alınamadı. 'customer_payments' tablosunda 'cust_payment_id' sütunu bulunamadı? Veritabanı şemasını kontrol edin.") from e
        else:
            raise DatabaseError(
                f"Müşteri (ID: {customer_id}) hesap ekstresi alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# ... (Dosyanın geri kalanı aynı) ...# === Müşteri Durum Değiştirme ===
def deactivate_customer(connection, customer_id):
    """Verilen ID'ye sahip müşteriyi pasif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Müşteri pasifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE customers SET is_active = FALSE WHERE customer_id = %s AND is_active = TRUE"
        cursor.execute(sql, (customer_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(
                f"[bold green]>>> Müşteri (ID: {customer_id}) pasif yapıldı.[/]")
            return True
        else:
            rprint(
                f"[yellow]>>> Müşteri (ID: {customer_id}) bulunamadı veya zaten pasif.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Müşteri (ID: {customer_id}) pasifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def reactivate_customer(connection, customer_id):
    """Verilen ID'ye sahip müşteriyi aktif hale getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Müşteri aktifleştirme için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE customers SET is_active = TRUE WHERE customer_id = %s AND is_active = FALSE"
        cursor.execute(sql, (customer_id,))
        if cursor.rowcount == 1:
            connection.commit()
            rprint(
                f"[bold green]>>> Müşteri (ID: {customer_id}) aktif yapıldı.[/]")
            return True
        else:
            rprint(
                f"[yellow]>>> Müşteri (ID: {customer_id}) bulunamadı veya zaten aktif.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Müşteri (ID: {customer_id}) aktifleştirme hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Sadakat Puanı İşlemleri ===

def add_loyalty_points(connection, customer_id, points_to_add, reason=""):
    """Müşterinin sadakat puanını artırır."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Sadakat puanı eklemek için aktif bağlantı gerekli.")
    if points_to_add <= 0:
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        sql = "UPDATE customers SET loyalty_points = loyalty_points + %s WHERE customer_id = %s"
        cursor.execute(sql, (points_to_add, customer_id))
        if cursor.rowcount == 1:
            return True
        else:
            return False
    except Error as e:
        rprint(
            f"[yellow]Uyarı: Müşteri (ID: {customer_id}) sadakat puanı eklenirken hata: {e}[/]")
        return False
    finally:
        pass

# === Kupon İşlemleri ===

def get_customer_available_coupons(connection, customer_id):
    """Müşterinin kullanabileceği aktif kuponları getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kupon sorgulamak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        today = datetime.date.today()
        # Sorgudaki expiry_date cc tablosundan alınmalı
        # is_used yerine status='available' kontrolü eklendi (varsayım)
        sql = """SELECT
                    cc.customer_coupon_id, c.coupon_id, c.coupon_code, c.description,
                    c.discount_type, c.discount_value, c.min_purchase_amount,
                    cc.expiry_date
                 FROM customer_coupons cc
                 JOIN coupons c ON cc.coupon_id = c.coupon_id
                 WHERE cc.customer_id = %s
                   AND cc.status = 'available'
                   AND c.is_active = TRUE
                   AND (cc.expiry_date IS NULL OR cc.expiry_date >= %s)
                 ORDER BY cc.expiry_date ASC, c.coupon_id ASC """
        cursor.execute(sql, (customer_id, today))
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(
            f"Müşteri (ID: {customer_id}) kupon sorgulama hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def use_customer_coupon(connection, customer_coupon_id, sale_id):
    """Müşteri kuponunu kullanıldı olarak işaretler."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kupon kullanmak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        # is_used yerine status='used' olarak güncelleyelim
        sql = "UPDATE customer_coupons SET status = 'used', used_sale_id = %s, used_date = %s WHERE customer_coupon_id = %s AND status = 'available'"
        used_date = datetime.datetime.now()
        cursor.execute(sql, (sale_id, used_date, customer_coupon_id))
        if cursor.rowcount == 1:
            return True
        else:
            return False
    except Error as e:
        raise DatabaseError(
            f"Kupon (ID: {customer_coupon_id}) kullanma hatası: {e}") from e
    finally:
        pass


def unuse_customer_coupon(connection, customer_coupon_id):
    """Kullanılmış bir müşteri kuponunu tekrar kullanılabilir yapar (iade durumunda)."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Kuponu geri almak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        # status='available' olarak güncelleyelim
        sql = "UPDATE customer_coupons SET status = 'available', used_sale_id = NULL, used_date = NULL WHERE customer_coupon_id = %s AND status = 'used'"
        cursor.execute(sql, (customer_coupon_id,))
        if cursor.rowcount == 1:
            return True
        else:
            return False
    except Error as e:
        raise DatabaseError(
            f"Kupon (ID: {customer_coupon_id}) geri alma hatası: {e}") from e
    finally:
        pass
