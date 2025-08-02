# veritabani_islemleri.py
# Satış, iade, raporlama gibi genel veritabanı işlemlerini içerir.
# ... (Önceki versiyon notları) ...
# v49: finalize_sale ve process_sale_return fonksiyonlarına user_id parametresi ve loglama eklendi.
# v52: finalize_sale fonksiyonundaki INSERT INTO sales sorgusundan user_id sütunu kaldırıldı.

from mysql.connector import Error
from decimal import Decimal, InvalidOperation
import datetime
# DuplicateEntryError eklendi
from hatalar import DatabaseError, SaleIntegrityError, DuplicateEntryError
from rich import print as rprint  # rprint'i import ettiğimizden emin olalım
import urun_veritabani as product_db_ops  # Stok güncelleme için
import musteri_veritabani as customer_db_ops  # Bakiye, puan, kupon için
import arayuz_yardimcilari as ui  # console nesnesi için
import loglama  # Loglama için import edildi

# console nesnesini alalım
try:
    console = ui.console
except AttributeError:
    from rich.console import Console
    console = Console()
    console.print(
        "[yellow]Uyarı: arayuz_yardimcilari modülünde 'console' nesnesi bulunamadı, burada oluşturuldu.[/]")


# === Satış İşlemleri ===

# ***** BU FONKSİYON GÜNCELLENDİ (user_id sütunu INSERT sorgusundan kaldırıldı) *****
def finalize_sale(connection, cart: list, sale_subtotal: Decimal, customer_id: int | None, payments: list,
                  applied_coupon_id: int | None, discount_amount: Decimal,
                  applied_promotion_id: int | None, promotion_discount: Decimal,
                  free_items_for_stock: list = None, shift_id: int | None = None, user_id: int | None = None):  # user_id loglama için hala parametre olarak kalıyor
    """
    Satış işlemini (başlık, kalemler, ödemeler) veritabanına kaydeder ve loglar.
    Stokları düşürür (hem satılan hem bedava verilenler için),
    müşteri bakiyesini/puanını günceller, kuponu kullanır, promosyonu kaydeder, vardiya ID'sini ekler.
    Tek bir transaction içinde yapar.
    Args:
        user_id (int | None): İşlemi yapan kullanıcı ID'si (loglama için).
        ... (diğer parametreler) ...
    Returns:
        int: Başarılı olursa kaydedilen satışın ID'si, yoksa None.
    """
    if not cart:
        raise ValueError("Satışı tamamlamak için sepette ürün olmalıdır.")
    if not payments:
        raise ValueError("Satışı tamamlamak için ödeme bilgisi gereklidir.")
    if not connection or not connection.is_connected():
        raise DatabaseError("Satışı tamamlamak için aktif bağlantı gerekli.")
    if user_id is None:
        # Loglama için user_id hala gerekli, bu yüzden kontrol kalsın.
        raise ValueError("Loglama için kullanıcı ID'si gereklidir.")

    cursor = None
    sale_id = None
    final_total_amount = sale_subtotal - discount_amount - promotion_discount
    if final_total_amount < Decimal('0.00'):
        final_total_amount = Decimal('0.00')

    try:
        cursor = connection.cursor()

        # 1. Satış Başlığını (sales) Ekle
        # ***** DEĞİŞİKLİK BURADA: SQL sorgusundan user_id kaldırıldı *****
        sql_insert_sale = """
            INSERT INTO sales (customer_id, shift_id, total_amount, discount_amount, promotion_discount, applied_customer_coupon_id, applied_promotion_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'completed')
            """
        # ***** DEĞİŞİKLİK BURADA: Parametrelerden user_id (3. sıradaki) kaldırıldı *****
        sale_params = (customer_id, shift_id, final_total_amount,
                       discount_amount, promotion_discount, applied_coupon_id, applied_promotion_id)
        cursor.execute(sql_insert_sale, sale_params)
        sale_id = cursor.lastrowid
        if not sale_id:
            raise DatabaseError("Yeni satış ID'si alınamadı!")

        # 2. Satış Kalemlerini (sale_items) Ekle ve Stokları Düşür (Satılan Ürünler)
        sql_insert_item = """
            INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale)
            VALUES (%s, %s, %s, %s)
            """
        sql_update_stock = """
            UPDATE products SET stock = stock - %s WHERE product_id = %s
            """
        product_details_for_log = []  # Log için ürün detayları
        for item in cart:
            item_params = (sale_id, item['product_id'],
                           item['quantity'], item['price_at_sale'])
            cursor.execute(sql_insert_item, item_params)
            stock_params = (item['quantity'], item['product_id'])
            cursor.execute(sql_update_stock, stock_params)
            if cursor.rowcount == 0:
                raise SaleIntegrityError(
                    f"Stok düşürme hatası: Ürün ID {item['product_id']} bulunamadı veya stok yetersiz!")
            product_details_for_log.append(
                f"({item['product_id']}:{item['quantity']})")

        # 2.1 Stokları Düşür (Bedava Verilen Ürünler - Promosyon)
        free_product_details_for_log = []  # Log için bedava ürün detayları
        if free_items_for_stock:
            for free_item in free_items_for_stock:
                free_product_id = free_item.get('product_id')
                free_quantity = free_item.get('quantity')
                if free_product_id and free_quantity and free_quantity > 0:
                    stock_params = (free_quantity, free_product_id)
                    cursor.execute(sql_update_stock, stock_params)
                    if cursor.rowcount == 0:
                        raise SaleIntegrityError(
                            f"Promosyonlu bedava ürün stok düşürme hatası: Ürün ID {free_product_id} bulunamadı veya stok yetersiz!")
                    else:
                        rprint(
                            f"[dim]Promosyon: {free_quantity} adet (ID: {free_product_id}) stoğu düşüldü.[/]")
                        free_product_details_for_log.append(
                            f"({free_product_id}:{free_quantity} Bedava)")

        # 3. Ödemeleri (payments) Ekle
        # Bu sütun adı payments tablosunda doğru varsayılıyor
        payment_amount_column_name = 'amount_paid'
        sql_insert_payment = f"""
            INSERT INTO payments (sale_id, payment_method, {payment_amount_column_name})
            VALUES (%s, %s, %s)
            """
        total_paid_amount = Decimal('0.00')
        is_veresiye = False
        veresiye_amount = Decimal('0.00')
        payment_details_for_log = []  # Log için ödeme detayları
        for i, payment in enumerate(payments):
            try:
                if not isinstance(payment, dict):
                    raise TypeError(
                        f"Ödeme listesindeki {i+1}. öğe bir sözlük değil: {payment}")
                payment_value = payment.get('amount')
                payment_method = payment.get('method')
                if payment_value is None:
                    raise ValueError(
                        f"Ödeme listesindeki {i+1}. öğede ({payment_method}) 'amount' anahtarı bulunamadı.")
                if payment_method is None:
                    raise ValueError(
                        f"Ödeme listesindeki {i+1}. öğede 'method' anahtarı bulunamadı.")

                pay_params = (sale_id, payment_method, payment_value)
                cursor.execute(sql_insert_payment, pay_params)
                total_paid_amount += payment_value
                payment_details_for_log.append(
                    f"{payment_method}:{payment_value:.2f}")
                if payment_method == 'Veresiye':
                    is_veresiye = True
                    veresiye_amount = payment_value
            except (TypeError, ValueError, KeyError) as payment_err:
                raise ValueError(
                    f"Ödeme işlenirken hata (Öğe {i+1}: {payment}): {payment_err}") from payment_err
            except Error as db_payment_err:
                # Ödeme eklerken DB hatası olursa yakala (örn: amount_paid sütunu yoksa)
                if 'amount_paid' in str(db_payment_err).lower() and 'unknown column' in str(db_payment_err).lower():
                     raise DatabaseError(
                         f"'payments' tablosunda 'amount_paid' sütunu bulunamadı veya adı farklı.") from db_payment_err
                else:
                     raise DatabaseError(f"Ödeme kaydı sırasında veritabanı hatası: {db_payment_err}") from db_payment_err

        # 4. Müşteri İşlemleri (varsa)
        if customer_id:
            if is_veresiye:
                if not customer_db_ops.update_customer_balance(connection, customer_id, veresiye_amount):
                    raise SaleIntegrityError(
                        f"Müşteri (ID: {customer_id}) veresiye bakiye güncelleme hatası!")
            points_to_add = 0
            try:
                # TODO: config.ini'den puan katsayısını okuyacak mekanizma eklenebilir.
                # Şimdilik sabit bırakalım.
                config_points_per_tl = Decimal('0.1')  # Örnek değer
                points_to_add = int(sale_subtotal * config_points_per_tl)
            except (ValueError, InvalidOperation):
                points_to_add = 0
            if points_to_add > 0:
                if not customer_db_ops.add_loyalty_points(connection, customer_id, points_to_add, f"Satış ID: {sale_id}"):
                    rprint(
                        f"[yellow]Uyarı: Müşteri (ID: {customer_id}) için sadakat puanı eklenemedi.[/]")
            if applied_coupon_id:
                if not customer_db_ops.use_customer_coupon(connection, applied_coupon_id, sale_id):
                    raise SaleIntegrityError(
                        f"Kullanılan kupon (ID: {applied_coupon_id}) durumu güncellenemedi!")

        # 5. Her şey yolundaysa COMMIT
        connection.commit()

        # 6. Loglama (Commit sonrası)
        log_details = (
            f"Satış ID: {sale_id}, Müşteri ID: {customer_id if customer_id else 'Yok'}, "
            f"Tutar: {final_total_amount:.2f}, Ödemeler: [{', '.join(payment_details_for_log)}], "
            f"İndirim: {discount_amount:.2f}, Kupon ID: {applied_coupon_id if applied_coupon_id else 'Yok'}, "
            f"Promo İnd: {promotion_discount:.2f}, Promo ID: {applied_promotion_id if applied_promotion_id else 'Yok'}, "
            f"Ürünler: [{', '.join(product_details_for_log)}]"
            f"{', Bedava: [' + ', '.join(free_product_details_for_log) + ']' if free_product_details_for_log else ''}"
        )
        loglama.log_activity(connection, user_id,  # Loglama için user_id hala kullanılıyor
                             loglama.LOG_ACTION_SALE_COMPLETE, log_details)

        return sale_id

    except (Error, SaleIntegrityError, DatabaseError, ValueError, TypeError) as e:
        error_type = type(e).__name__
        console.print(
            f"\n[bold red]>>> {error_type} (Satış Tamamlama):[/] {e}", style="bold red")
        console.print("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        # Hata durumunda loglama (isteğe bağlı)
        # loglama.log_activity(connection, user_id, "SATIS_HATA", f"Hata: {e}")
        return None
    except Exception as genel_hata:
        console.print(
            f"\n[bold red]>>> BEKLENMEDİK PROGRAM HATASI (Satış Tamamlama):[/] {genel_hata}", style="bold red")
        console.print("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        # Hata durumunda loglama (isteğe bağlı)
        # loglama.log_activity(connection, user_id, "SATIS_BEKLENMEDIK_HATA", f"Hata: {genel_hata}")
        return None
    finally:
        if cursor:
            cursor.close()

# === Satış İade İşlemleri ===
# ... (get_sale_details_for_return, process_sale_return fonksiyonları aynı) ...

def get_sale_details_for_return(connection, sale_id):
    """İade işlemi için satış başlık ve kalem bilgilerini getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Satış detayı almak için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # user_id'yi sales tablosundan okumaya çalışıyor, eğer yoksa hata verebilir.
        # Şimdilik bu sorguyu değiştirmedik, hata verirse burayı da düzenleriz.
        sql_header = """SELECT sale_id, customer_id, shift_id,
                               total_amount, discount_amount, promotion_discount,
                               applied_customer_coupon_id, applied_promotion_id, status
                        FROM sales WHERE sale_id = %s"""  # user_id okuması kaldırıldı (eğer DB'de yoksa)
        cursor.execute(sql_header, (sale_id,))
        sale_header = cursor.fetchone()

        if not sale_header:
            rprint(f">>> HATA: Satış ID {sale_id} bulunamadı.", style="red")
            return None
        if sale_header['status'] == 'returned':
            rprint(
                f">>> HATA: Satış ID {sale_id} zaten iade edilmiş.", style="red")
            return None
        if sale_header['status'] != 'completed':
            rprint(
                f">>> HATA: Sadece 'tamamlanmış' satışlar iade edilebilir (Durum: {sale_header['status']}).", style="red")
            return None

        sql_items = """SELECT si.product_id, p.name, si.quantity, si.price_at_sale
                       FROM sale_items si
                       JOIN products p ON si.product_id = p.product_id
                       WHERE si.sale_id = %s"""
        cursor.execute(sql_items, (sale_id,))
        sale_items = cursor.fetchall()
        # Eğer sale_items tuple yerine dict dönüyorsa bu satır çalışır
        # sale_items_tuples = [(item['product_id'], item['name'], item['quantity'], item['price_at_sale']) for item in sale_items]
        # Eğer tuple dönüyorsa:
        sale_items_tuples = sale_items  # Doğrudan ata

        # Müşteri bilgisini de ekleyelim (loglama vb. için lazım olabilir)
        sale_header['user_id'] = None  # user_id artık okunmadığı için None atıyoruz
        try:
            # Satışı yapan kullanıcıyı loglardan bulmaya çalışalım (opsiyonel)
            cursor_log = connection.cursor()
            log_sql = """SELECT user_id FROM activity_logs
                         WHERE action_type = %s AND details LIKE %s
                         ORDER BY timestamp DESC LIMIT 1"""
            log_params = (loglama.LOG_ACTION_SALE_COMPLETE,
                          f"Satış ID: {sale_id}%")
            cursor_log.execute(log_sql, log_params)
            log_result = cursor_log.fetchone()
            if log_result:
                sale_header['user_id'] = log_result[0]
            cursor_log.close()
        except Error as log_err:
            rprint(f"[dim]İade: Satışı yapan kullanıcı loglardan alınamadı ({log_err})[/dim]")

        return {'header': sale_header, 'items': sale_items_tuples}

    except Error as e:
        # user_id sorgudan kaldırıldığı için user_id ile ilgili hata vermemeli artık
        raise DatabaseError(
            f"Satış (ID: {sale_id}) detayı alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def process_sale_return(connection, sale_id, sale_details, reason=None, notes=None, user_id: int | None = None):  # user_id loglama için
    """
    Satış iade işlemini gerçekleştirir ve loglar: Stokları geri alır, bakiyeyi günceller,
    satış ve ödeme durumlarını günceller, iade kaydı oluşturur.
    Tek bir transaction içinde yapar.
    Args:
        user_id (int | None): İşlemi yapan kullanıcı ID'si (loglama için).
        ... (diğer parametreler) ...
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Satış iadesi için aktif bağlantı gerekli.")
    if not sale_details or 'header' not in sale_details or 'items' not in sale_details:
        raise ValueError("İade için geçerli satış detayı gerekli.")
    if user_id is None:
        raise ValueError("Loglama için kullanıcı ID'si gereklidir.")

    header = sale_details['header']
    items = sale_details['items']
    customer_id = header.get('customer_id')
    return_amount = header.get('total_amount', Decimal('0.00'))
    used_coupon_id = header.get('applied_customer_coupon_id')
    # original_user_id = header.get('user_id') # Bu bilgi artık header'da olmayabilir, loglama için user_id kullanılıyor

    cursor = None
    return_id = None
    try:
        cursor = connection.cursor()

        # 1. İade Kaydını (returns) Oluştur
        # returns tablosunda da user_id sütunu olmayabilir, varsa eklemek gerek.
        # Şimdilik user_id'yi returns'e eklemediğimizi varsayalım.
        sql_insert_return = """
            INSERT INTO returns (original_sale_id, customer_id, return_amount, reason, notes)
            VALUES (%s, %s, %s, %s, %s)
            """
        return_params = (sale_id, customer_id, return_amount, reason, notes)
        # Eğer returns tablosunda user_id varsa:
        # sql_insert_return = """
        #    INSERT INTO returns (original_sale_id, user_id, customer_id, return_amount, reason, notes)
        #    VALUES (%s, %s, %s, %s, %s, %s)
        #    """
        # return_params = (sale_id, user_id, customer_id, return_amount, reason, notes)
        cursor.execute(sql_insert_return, return_params)
        return_id = cursor.lastrowid
        if not return_id:
            raise DatabaseError("Yeni iade ID'si alınamadı!")

        # 2. Stokları Geri Yükle
        sql_update_stock = "UPDATE products SET stock = stock + %s WHERE product_id = %s"
        product_details_for_log = []
        for item_tuple in items:
            # item_tuple'ın (product_id, name, quantity, price_at_sale) formatında olduğunu varsayıyoruz
            if len(item_tuple) >= 3: # En az 3 eleman varsa
                product_id, _, quantity = item_tuple[:3]  # Sadece ilk 3 elemanı al
                stock_params = (quantity, product_id)
                cursor.execute(sql_update_stock, stock_params)
                product_details_for_log.append(f"({product_id}:{quantity})")  # Log için sadece ID ve miktar yeterli
            else:
                 rprint(
                     f"[red]HATA: İade edilecek ürün bilgisi eksik: {item_tuple}[/]")

        # 3. Müşteri Bakiyesini Güncelle
        if customer_id and return_amount > Decimal('0.00'):
            if not customer_db_ops.update_customer_balance(connection, customer_id, -return_amount):
                raise SaleIntegrityError(
                    f"Müşteri (ID: {customer_id}) iade bakiye güncelleme hatası!")

        # 4. Kullanılan Kuponu Tekrar Kullanılabilir Yap
        if used_coupon_id:
            if not customer_db_ops.unuse_customer_coupon(connection, used_coupon_id):
                rprint(
                    f"[yellow]Uyarı: İade edilen satışta kullanılan kupon (ID: {used_coupon_id}) tekrar kullanılabilir yapılamadı.[/]")

        # 5. Orijinal Satışın Durumunu 'returned' Yap
        sql_update_sale_status = "UPDATE sales SET status = 'returned' WHERE sale_id = %s"
        cursor.execute(sql_update_sale_status, (sale_id,))
        if cursor.rowcount == 0:
            raise SaleIntegrityError(
                f"Orijinal satış (ID: {sale_id}) durumu güncellenemedi!")

        # 6. Orijinal Ödemelerin Durumunu 'returned' Yap
        sql_update_payment_status = "UPDATE payments SET status = 'returned' WHERE sale_id = %s"
        try:
            cursor.execute(sql_update_payment_status, (sale_id,))
        except Error as payment_err:
            if 'status' in str(payment_err).lower() and 'unknown column' in str(payment_err).lower():
                rprint(
                    f"[yellow]Uyarı: Ödeme durumu güncellenemedi ('payments' tablosunda 'status' sütunu olmayabilir).[/]")
            else:
                raise DatabaseError(
                    f"Ödeme durumu güncelleme hatası: {payment_err}") from payment_err

        # 7. Her şey yolundaysa COMMIT
        connection.commit()
        rprint(
            f"[bold green]>>> Satış (ID: {sale_id}) başarıyla iade edildi (İade ID: {return_id}). Stoklar ve bakiye güncellendi.[/]")

        # 8. Loglama (Commit sonrası)
        log_details = (
            f"İade ID: {return_id}, Orijinal Satış ID: {sale_id}, Müşteri ID: {customer_id if customer_id else 'Yok'}, "
            f"Tutar: {return_amount:.2f}, Sebep: {reason or '-'}"
            f"İade Edilen Ürünler: [{', '.join(product_details_for_log)}]"
        )
        loglama.log_activity(connection, user_id,  # İşlemi yapan user_id loglanır
                             loglama.LOG_ACTION_SALE_RETURN, log_details)

        return return_id

    except (Error, SaleIntegrityError, DatabaseError, ValueError, TypeError) as e:
        error_type = type(e).__name__
        console.print(
            f"\n[bold red]>>> {error_type} (Satış İadesi):[/] {e}", style="bold red")
        console.print("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        # Hata loglaması eklenebilir
        # loglama.log_activity(connection, user_id, "SATIS_IADE_HATA", f"Satış ID: {sale_id}, Hata: {e}")
        return None
    except Exception as genel_hata:
        console.print(
            f"\n[bold red]>>> BEKLENMEDİK PROGRAM HATASI (Satış İadesi):[/] {genel_hata}", style="bold red")
        console.print("[yellow]Değişiklikler geri alınıyor...[/yellow]")
        if connection:
            connection.rollback()
        # Hata loglaması eklenebilir
        # loglama.log_activity(connection, user_id, "SATIS_IADE_BEKLENMEDIK_HATA", f"Satış ID: {sale_id}, Hata: {genel_hata}")
        return None
    finally:
        if cursor:
            cursor.close()

# === Raporlama Fonksiyonları ===
# ... (get_daily_sales_summary, get_top_selling_products_by_quantity, get_top_selling_products_by_value, get_profit_loss_report_data, get_expiry_report_data fonksiyonları aynı) ...

def get_daily_sales_summary(connection, start_date=None, end_date=None):
    """Günlük satış özetini (işlem sayısı, toplam tutar) getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Raporlama için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = """SELECT DATE(sale_date) as sale_day, COUNT(*) as count, SUM(total_amount) as daily_total
                 FROM sales
                 WHERE status = 'completed' """
        params = []
        if start_date:
            sql += " AND sale_date >= %s "
            params.append(start_date)
        if end_date:
            end_date_inclusive = end_date + datetime.timedelta(days=1)
            sql += " AND sale_date < %s "
            params.append(end_date_inclusive)

        sql += " GROUP BY DATE(sale_date) ORDER BY sale_day DESC"
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"Günlük satış özeti alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_top_selling_products_by_quantity(connection, limit=10, start_date=None, end_date=None):
    """Belirtilen tarih aralığında en çok satan ürünleri (adet bazında) getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Raporlama için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = """SELECT
                    p.product_id, p.barcode, p.name, SUM(si.quantity) as total_quantity
                 FROM sale_items si
                 JOIN products p ON si.product_id = p.product_id
                 JOIN sales s ON si.sale_id = s.sale_id
                 WHERE s.status = 'completed' """
        params = []
        if start_date:
            sql += " AND s.sale_date >= %s "
            params.append(start_date)
        if end_date:
            end_date_inclusive = end_date + datetime.timedelta(days=1)
            sql += " AND s.sale_date < %s "
            params.append(end_date_inclusive)

        sql += " GROUP BY p.product_id, p.barcode, p.name ORDER BY total_quantity DESC LIMIT %s"
        params.append(limit)
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(
            f"En çok satan ürün (adet) raporu hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_top_selling_products_by_value(connection, limit=10, start_date=None, end_date=None):
    """Belirtilen tarih aralığında en çok ciro yapan ürünleri getirir."""
    if not connection or not connection.is_connected():
        raise DatabaseError("Raporlama için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor()
        sql = """SELECT
                    p.product_id, p.barcode, p.name,
                    SUM(si.quantity * si.price_at_sale) as total_value
                 FROM sale_items si
                 JOIN products p ON si.product_id = p.product_id
                 JOIN sales s ON si.sale_id = s.sale_id
                 WHERE s.status = 'completed' """
        params = []
        if start_date:
            sql += " AND s.sale_date >= %s "
            params.append(start_date)
        if end_date:
            end_date_inclusive = end_date + datetime.timedelta(days=1)
            sql += " AND s.sale_date < %s "
            params.append(end_date_inclusive)

        sql += " GROUP BY p.product_id, p.barcode, p.name ORDER BY total_value DESC LIMIT %s"
        params.append(limit)
        cursor.execute(sql, params)
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(
            f"En çok ciro yapan ürün raporu hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_profit_loss_report_data(connection, start_date=None, end_date=None):
    """
    Belirtilen tarih aralığı için ürün bazlı tahmini kâr/zarar verilerini hesaplar.
    Maliyet, ürünün son alış fiyatına göre tahmin edilir.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("Raporlama için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = """
            SELECT
                si.product_id,
                p.barcode,
                p.name,
                SUM(si.quantity) AS total_quantity,
                SUM(si.quantity * si.price_at_sale) AS total_revenue,
                (SELECT cost_price
                 FROM purchase_items pi
                 JOIN purchases pu ON pi.purchase_id = pu.purchase_id
                 WHERE pi.product_id = si.product_id AND pi.cost_price IS NOT NULL
                 ORDER BY pu.purchase_date DESC, pi.purchase_item_id DESC
                 LIMIT 1) AS last_cost_price
            FROM sale_items si
            JOIN products p ON si.product_id = p.product_id
            JOIN sales s ON si.sale_id = s.sale_id
            WHERE s.status = 'completed'
        """
        params = []
        if start_date:
            sql += " AND s.sale_date >= %s "
            params.append(start_date)
        if end_date:
            end_date_inclusive = end_date + datetime.timedelta(days=1)
            sql += " AND s.sale_date < %s "
            params.append(end_date_inclusive)

        sql += " GROUP BY si.product_id, p.barcode, p.name"
        sql += " ORDER BY p.name ASC"

        cursor.execute(sql, params)
        report_data = cursor.fetchall()

        for row in report_data:
            total_quantity = row.get('total_quantity', 0)
            total_revenue = row.get('total_revenue', Decimal('0.00'))
            last_cost = row.get('last_cost_price')
            estimated_cost = Decimal('0.00')
            if last_cost is not None and total_quantity > 0:
                try:
                    estimated_cost = total_quantity * last_cost
                except (TypeError, InvalidOperation):
                    estimated_cost = Decimal('0.00')
            estimated_profit = total_revenue - estimated_cost
            row['total_estimated_cost'] = estimated_cost
            row['estimated_profit'] = estimated_profit

        return report_data

    except Error as e:
        raise DatabaseError(f"Kâr/Zarar raporu alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()


def get_expiry_report_data(connection, days_threshold):
    """
    SKT'si bugün veya belirtilen gün sayısı içinde dolacak olan
    alış kalemlerini getirir.
    Args:
        days_threshold (int): Kaç gün sonrasına kadar kontrol edileceği.
    Returns:
        list: İlgili bilgileri içeren sözlük listesi.
    """
    if not connection or not connection.is_connected():
        raise DatabaseError("SKT raporu için aktif bağlantı gerekli.")
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=days_threshold)

        sql = """
            SELECT
                pi.purchase_id,
                pi.product_id,
                p.name as product_name,
                b.name as brand_name,
                pi.quantity,
                pi.expiry_date
            FROM purchase_items pi
            JOIN products p ON pi.product_id = p.product_id
            LEFT JOIN brands b ON p.brand_id = b.brand_id
            WHERE pi.expiry_date IS NOT NULL
              AND pi.expiry_date <= %s
            ORDER BY pi.expiry_date ASC, p.name ASC
        """
        cursor.execute(sql, (end_date,))
        return cursor.fetchall()
    except Error as e:
        raise DatabaseError(f"SKT raporu verisi alma hatası: {e}") from e
    finally:
        if cursor:
            cursor.close()
