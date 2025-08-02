# loglama.py
# Kullanıcı ve sistem aktivitelerini loglama işlemlerini yönetir.

from mysql.connector import Error
import datetime
from hatalar import DatabaseError
# rich.print kullanmayalım, loglama sessiz olmalı veya standart log kütüphanesi kullanılmalı.
# Şimdilik hata durumunda standart print kullanalım.
# from rich import print as rprint

# === Log Eylem Türleri (Sabitler) ===
# Bu sabitleri kullanarak kod içinde tutarlılığı sağlarız.
LOG_ACTION_LOGIN_SUCCESS = "KULLANICI_GIRIS_BASARILI"
LOG_ACTION_LOGIN_FAIL = "KULLANICI_GIRIS_HATALI"
LOG_ACTION_SHIFT_START = "VARDIYA_BASLAT"
LOG_ACTION_SHIFT_END = "VARDIYA_BITIR"
LOG_ACTION_SALE_COMPLETE = "SATIS_TAMAMLAMA"
LOG_ACTION_SALE_RETURN = "SATIS_IADE"
LOG_ACTION_PRODUCT_ADD = "URUN_EKLEME"
LOG_ACTION_PRODUCT_UPDATE = "URUN_GUNCELLEME"
LOG_ACTION_PRODUCT_STATUS_CHANGE = "URUN_DURUM_DEGISTIRME"
LOG_ACTION_STOCK_ADJUSTMENT = "STOK_DUZELTME"
LOG_ACTION_STOCK_PURCHASE = "STOK_ALIS_KAYDI"
LOG_ACTION_CUSTOMER_ADD = "MUSTERI_EKLEME"
LOG_ACTION_CUSTOMER_UPDATE = "MUSTERI_GUNCELLEME"
LOG_ACTION_CUSTOMER_PAYMENT = "MUSTERI_ODEME_ALMA"
LOG_ACTION_CUSTOMER_STATUS_CHANGE = "MUSTERI_DURUM_DEGISTIRME"
LOG_ACTION_CATEGORY_ADD = "KATEGORI_EKLEME"
LOG_ACTION_CATEGORY_UPDATE = "KATEGORI_GUNCELLEME"
LOG_ACTION_CATEGORY_STATUS_CHANGE = "KATEGORI_DURUM_DEGISTIRME"
LOG_ACTION_BRAND_ADD = "MARKA_EKLEME"
LOG_ACTION_BRAND_STATUS_CHANGE = "MARKA_DURUM_DEGISTIRME"
LOG_ACTION_PROMOTION_ADD = "PROMOSYON_EKLEME"
LOG_ACTION_PROMOTION_STATUS_CHANGE = "PROMOSYON_DURUM_DEGISTIRME"
LOG_ACTION_USER_ADD = "YENI_KULLANICI_EKLEME"  # Admin işlemi
LOG_ACTION_USER_UPDATE = "KULLANICI_GUNCELLEME"  # Admin işlemi
LOG_ACTION_USER_STATUS_CHANGE = "KULLANICI_DURUM_DEGISTIRME"  # Admin işlemi
LOG_ACTION_PASSWORD_CHANGE = "SIFRE_DEGISTIRME"
# ... Diğer eylemler eklenebilir ...

# === Log Kaydetme Fonksiyonu ===


def log_activity(connection, user_id: int, action_type: str, details: str = None):
    """
    Yapılan bir işlemi activity_logs tablosuna kaydeder.
    Args:
        connection: Aktif veritabanı bağlantısı.
        user_id (int): İşlemi yapan kullanıcının ID'si.
        action_type (str): Yapılan işlemin türü (yukarıdaki sabitlerden biri).
        details (str, optional): İşlemle ilgili ek detaylar. Defaults to None.
    Returns:
        bool: Log kaydı başarılıysa True, değilse False.
    """
    if not connection or not connection.is_connected():
        print("HATA (Loglama): Log kaydetmek için aktif veritabanı bağlantısı gerekli.")
        return False
    if not user_id or not action_type:
        print("HATA (Loglama): Kullanıcı ID ve eylem türü boş olamaz.")
        return False

    cursor = None
    try:
        cursor = connection.cursor()
        sql = """INSERT INTO activity_logs
                 (user_id, action_type, details, timestamp)
                 VALUES (%s, %s, %s, %s)"""
        timestamp = datetime.datetime.now()
        params = (user_id, action_type, details, timestamp)
        cursor.execute(sql, params)

        # ÖNEMLİ: Loglama işlemi genellikle ana işlemin bir parçası olarak
        # aynı transaction içinde yapılmalı ve ana işlemle birlikte commit edilmelidir.
        # Ancak, bu fonksiyonu çağıran yerlerde transaction yönetimi karmaşıklaşabilir.
        # Şimdilik her log kaydını ayrı ayrı commit edelim.
        # Performans veya veri bütünlüğü açısından kritik olursa bu yaklaşım gözden geçirilebilir.
        connection.commit()
        return True
    except Error as e:
        # Loglama hatası kritik olmamalı, programın çalışmasını engellememeli.
        # Hatayı konsola yazdırıp False dönelim.
        print(
            f"HATA (Loglama): Log kaydedilemedi. UserID: {user_id}, Eylem: {action_type}, Detay: {details}. Hata: {e}")
        # connection.rollback() burada yapılmamalı, çünkü bu ayrı bir işlem.
        return False
    except Exception as ex:
        print(f"BEKLENMEDİK HATA (Loglama): {ex}")
        return False
    finally:
        if cursor:
            cursor.close()
