# vardiya_veritabani.py
# Vardiyalarla (shifts) ilgili veritabanı işlemlerini içerir.
# v2: get_shift_customer_payments_summary fonksiyonu aktifleştirildi.

from mysql.connector import Error, errorcode
from decimal import Decimal
import datetime
from hatalar import DatabaseError, DuplicateEntryError
from rich import print as rprint
import arayuz_yardimcilari as ui  # console nesnesi için

# console nesnesini alalım
try:
    console = ui.console
except AttributeError:
    from rich.console import Console
    console = Console()
    rprint("[yellow]Uyarı: arayuz_yardimcilari modülünde 'console' nesnesi bulunamadı, burada oluşturuldu.[/]")


# === Vardiya Başlatma ===

def start_shift(connection, user_id, starting_cash=None):
    """
    Belirtilen kullanıcı için yeni bir vardiya başlatır.
    Kullanıcının zaten aktif bir vardiyası varsa hata verir.
    Args:
        user_id (int): Vardiyayı başlatan kullanıcı ID'si.
        starting_cash (Decimal, optional): Vardiya başı kasa nakiti. Defaults to None.
    Returns:
        int: Başarıyla başlatılırsa yeni vardiya ID'si, yoksa None.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Vardiya başlatmak için aktif bağlantı gerekli.")

    cursor = None
    try:
        cursor = connection.cursor()

        # Kullanıcının aktif vardiyası var mı kontrol et
        sql_check = "SELECT shift_id FROM shifts WHERE user_id = %s AND is_active = TRUE AND end_time IS NULL"
        cursor.execute(sql_check, (user_id,))
        active_shift = cursor.fetchone()
        if active_shift:
            rprint(
                f"[bold yellow]Uyarı: Bu kullanıcının (ID: {user_id}) zaten aktif bir vardiyası (ID: {active_shift[0]}) var.[/]")
            return None

        # Yeni vardiya kaydını ekle
        sql_insert = """INSERT INTO shifts
                        (user_id, start_time, starting_cash, is_active)
                        VALUES (%s, %s, %s, TRUE)"""
        start_time = datetime.datetime.now()
        params = (user_id, start_time, starting_cash)
        cursor.execute(sql_insert, params)
        connection.commit()
        new_shift_id = cursor.lastrowid
        rprint(
            f"[bold green]>>> Kullanıcı ID {user_id} için yeni vardiya (ID: {new_shift_id}) başarıyla başlatıldı.[/]")
        return new_shift_id
    except Error as e:
        raise DatabaseError(f"Vardiya başlatma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Aktif Vardiyayı Getirme ===


def get_active_shift(connection, user_id):
    """
    Belirtilen kullanıcının şu anda aktif olan vardiyasını getirir.
    Args:
        user_id (int): Kullanıcı ID'si.
    Returns:
        dict: Aktif vardiya bilgileri (sözlük) veya None.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Aktif vardiya getirmek için bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # Kullanıcı bilgilerini de alalım (Z raporu için)
        sql = """SELECT s.*, u.username, u.full_name
                 FROM shifts s
                 JOIN users u ON s.user_id = u.user_id
                 WHERE s.user_id = %s AND s.is_active = TRUE AND s.end_time IS NULL"""
        cursor.execute(sql, (user_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"Aktif vardiya getirme hatası (Kullanıcı ID: {user_id}): {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Vardiya Bitirme ===


def end_shift(connection, shift_id, ending_cash=None, total_sales=None, cash_sales=None, card_sales=None, veresiye_sales=None, cash_payments=None, card_payments=None, difference=None, notes=None):
    """
    Belirtilen vardiyayı bitirir ve hesaplanan özet bilgileri kaydeder.
    Args:
        shift_id (int): Bitirilecek vardiya ID'si.
        ending_cash (Decimal, optional): Vardiya sonu sayılan kasa nakiti.
        total_sales (Decimal, optional): Vardiya toplam satış (indirimli).
        cash_sales (Decimal, optional): Vardiya nakit satışları.
        card_sales (Decimal, optional): Vardiya kart satışları.
        veresiye_sales (Decimal, optional): Vardiya veresiye satışları.
        cash_payments (Decimal, optional): Vardiyada alınan nakit müşteri ödemeleri.
        card_payments (Decimal, optional): Vardiyada alınan kart müşteri ödemeleri.
        difference (Decimal, optional): Hesaplanan kasa farkı.
        notes (str, optional): Vardiya notları.
    Returns:
        bool: Başarılı olursa True, değilse False.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Vardiya bitirmek için aktif bağlantı gerekli.")

    cursor = None
    try:
        cursor = connection.cursor()
        end_time = datetime.datetime.now()
        sql = """UPDATE shifts SET
                    end_time = %s,
                    ending_cash = %s,
                    total_sales = %s,
                    cash_sales = %s,
                    card_sales = %s,
                    veresiye_sales = %s,
                    cash_payments_received = %s,
                    card_payments_received = %s,
                    calculated_difference = %s,
                    notes = %s,
                    is_active = FALSE
                 WHERE shift_id = %s AND is_active = TRUE AND end_time IS NULL"""
        params = (end_time, ending_cash, total_sales, cash_sales, card_sales,
                  veresiye_sales, cash_payments, card_payments, difference, notes, shift_id)
        cursor.execute(sql, params)

        if cursor.rowcount == 1:
            connection.commit()
            rprint(
                f"[bold green]>>> Vardiya (ID: {shift_id}) başarıyla bitirildi.[/]")
            return True
        else:
            rprint(
                f"[bold red]HATA: Aktif vardiya (ID: {shift_id}) bulunamadı veya zaten bitirilmiş.[/]")
            return False
    except Error as e:
        raise DatabaseError(
            f"Vardiya bitirme hatası (ID: {shift_id}): {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Vardiya Detayı Getirme ===


def get_shift_by_id(connection, shift_id):
    """Verilen ID'ye sahip vardiyanın tüm detaylarını getirir (kullanıcı adı dahil)."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Vardiya detayı getirmek için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = """SELECT s.*, u.username, u.full_name
                 FROM shifts s
                 JOIN users u ON s.user_id = u.user_id
                 WHERE s.shift_id = %s"""
        cursor.execute(sql, (shift_id,))
        return cursor.fetchone()
    except Error as e:
        raise DatabaseError(
            f"Vardiya detayı getirme hatası (ID: {shift_id}): {e}") from e
    finally:
        if cursor:
            cursor.close()

# === Vardiya Özeti Hesaplama Fonksiyonları (Z Raporu için) ===


def get_shift_sales_summary(connection, shift_id):
    """Belirli bir vardiyadaki satışların özetini (ödeme türüne göre) hesaplar."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Vardiya satış özeti için aktif bağlantı gerekli.")
    cursor = None
    summary = {
        'total_sales': Decimal('0.00'),
        'cash_sales': Decimal('0.00'),
        'card_sales': Decimal('0.00'),
        'veresiye_sales': Decimal('0.00'),
        'total_discount': Decimal('0.00'),
        'total_promotion_discount': Decimal('0.00')
    }
    try:
        cursor = connection.cursor(dictionary=True)

        sql_sales = """SELECT
                           SUM(total_amount) as total_sales_amount,
                           SUM(discount_amount) as total_discount_amount,
                           SUM(promotion_discount) as total_promo_discount
                       FROM sales
                       WHERE shift_id = %s AND status = 'completed'"""
        cursor.execute(sql_sales, (shift_id,))
        sales_data = cursor.fetchone()
        if sales_data:
            summary['total_sales'] = sales_data.get(
                'total_sales_amount') or Decimal('0.00')
            summary['total_discount'] = sales_data.get(
                'total_discount_amount') or Decimal('0.00')
            summary['total_promotion_discount'] = sales_data.get(
                'total_promo_discount') or Decimal('0.00')

        payment_amount_col = 'amount_paid'  # Kendi şemanıza göre doğrulandı
        sql_payments = f"""SELECT payment_method, SUM({payment_amount_col}) as total_paid
                          FROM payments pay
                          JOIN sales s ON pay.sale_id = s.sale_id
                          WHERE s.shift_id = %s AND s.status = 'completed'
                          GROUP BY payment_method"""
        cursor.execute(sql_payments, (shift_id,))
        payments_data = cursor.fetchall()
        for payment in payments_data:
            method = payment.get('payment_method')
            total_paid = payment.get('total_paid') or Decimal('0.00')
            if method == 'Nakit':
                summary['cash_sales'] = total_paid
            elif method == 'Kredi Kartı':
                summary['card_sales'] = total_paid
            elif method == 'Veresiye':
                summary['veresiye_sales'] = total_paid

        return summary
    except Error as e:
        raise DatabaseError(
            f"Vardiya satış özeti alma hatası (Shift ID: {shift_id}): {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_shift_customer_payments_summary(connection, shift_id):
    """Belirli bir vardiyada alınan müşteri ödemelerinin özetini (ödeme türüne göre) hesaplar."""
    if not connection or not connection.is_connected():
        raise DatabaseError(
            "Vardiya müşteri ödeme özeti için aktif bağlantı gerekli.")
    cursor = None
    summary = {
        'cash_payments_received': Decimal('0.00'),
        'card_payments_received': Decimal('0.00')
    }
    try:
        cursor = connection.cursor(dictionary=True)
        cust_payment_amount_col = 'amount'  # customer_payments'daki tutar sütunu
        sql = f"""SELECT payment_method, SUM({cust_payment_amount_col}) as total_received
                 FROM customer_payments
                 WHERE shift_id = %s
                 GROUP BY payment_method"""
        cursor.execute(sql, (shift_id,))
        payments_data = cursor.fetchall()
        for payment in payments_data:
            method = payment.get('payment_method')
            total_received = payment.get('total_received') or Decimal('0.00')
            if method == 'Nakit':
                summary['cash_payments_received'] = total_received
            elif method == 'Kredi Kartı':
                summary['card_payments_received'] = total_received

        return summary

    except Error as e:
        if 'customer_payments.shift_id' in str(e):
            console.print(
                f"[yellow]Uyarı: Müşteri ödeme özeti alınamadı. 'customer_payments' tablosunda 'shift_id' sütunu bulunmuyor olabilir.[/]")
            return summary
        else:
            raise DatabaseError(
                f"Vardiya müşteri ödeme özeti alma hatası (Shift ID: {shift_id}): {e}") from e
    finally:
        if cursor:
            cursor.close()
