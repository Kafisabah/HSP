# db_config.py
# Bu dosya, config.ini dosyasındaki bilgileri okuyarak
# MySQL veritabanına bağlantı kurmayı sağlar.

import mysql.connector
from mysql.connector import Error, errorcode
import configparser  # config.ini dosyasını okumak için
import os  # Dosya yolunu bulmak için
from rich import print as rprint  # Renkli mesajlar için


def connect_db():
    """
    config.ini dosyasından okunan bilgilerle MySQL veritabanına bağlanmayı dener.
    Başarılı olursa bağlantı nesnesini, olmazsa None döndürür.
    """

    # Bu dosyanın bulunduğu dizini al
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # config.ini dosyasının tam yolunu oluştur
    config_path = os.path.join(base_dir, 'config.ini')

    # config.ini dosyasını okumak için bir nesne oluştur
    config = configparser.ConfigParser()
    db_config = {}  # Okunan ayarları saklamak için boş bir sözlük

    try:
        # config.ini dosyasını oku (UTF-8 karakterleri destekle)
        # Eğer dosya okunamadıysa veya boşsa, FileNotFoundError hatası ver.
        if not config.read(config_path, encoding='utf-8'):
            raise FileNotFoundError(
                f"Yapılandırma dosyası bulunamadı: {config_path}")

        # [mysql] bölümündeki ayarları oku
        # Eğer bir ayar bulunamazsa, varsayılan bir değer kullan (fallback)
        db_config['host'] = config.get('mysql', 'host', fallback='localhost')
        db_config['user'] = config.get('mysql', 'user', fallback='root')
        db_config['password'] = config.get('mysql', 'password', fallback='')
        db_config['database'] = config.get(
            'mysql', 'database', fallback='market_pos_db')

    except FileNotFoundError as fnf_err:
        rprint(f"[bold red]HATA:[/bold red] {fnf_err}")
        return None
    except configparser.NoSectionError:
        rprint(
            f"[bold red]HATA:[/bold red] Yapılandırma dosyasında [mysql] bölümü bulunamadı: {config_path}")
        return None
    except configparser.NoOptionError as noe_err:
        rprint(
            f"[bold red]HATA:[/bold red] Yapılandırma dosyasında gerekli bir seçenek eksik ({noe_err.option}): {config_path}")
        return None
    except Exception as e:
        rprint(
            f"[bold red]HATA:[/bold red] Yapılandırma dosyası okunurken beklenmedik hata: {e}")
        return None

    # Veritabanına bağlanmayı dene
    try:
        # Okunan ayarları kullanarak bağlantıyı kur
        # Sözlüğü direkt parametre olarak ver
        connection = mysql.connector.connect(**db_config)

        # Bağlantı başarılıysa
        if connection.is_connected():
            # Başarı mesajını ana programda verelim, burada sessiz kalalım.
            # rprint("MySQL veritabanına başarıyla bağlanıldı.", style="green")
            return connection  # Bağlantı nesnesini döndür
        else:
            # Bu durum genellikle connect() hata fırlattığı için pek oluşmaz
            rprint(
                "[bold yellow]UYARI:[/bold yellow] Bağlantı nesnesi alındı ama bağlantı aktif değil?")
            return None
    except Error as e:
        # Bağlantı sırasında bir hata olursa
        rprint(f"[bold red]MySQL BAĞLANTI HATASI:[/bold red] {e}")
        # Hata koduna göre daha detaylı bilgi ver (opsiyonel)
        if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            rprint(
                "[bold yellow]>>>[/bold yellow] Veritabanı kullanıcı adı veya şifresi hatalı olabilir (config.ini kontrol edin).")
        elif e.errno == errorcode.ER_BAD_DB_ERROR:
            rprint(
                f"[bold yellow]>>>[/bold yellow] Veritabanı '{db_config.get('database')}' bulunamadı.")
        return None  # Hata durumunda None döndür


# Bu dosya doğrudan çalıştırıldığında test amaçlı bağlantı dener.
# Normal kullanımda bu kısım çalışmaz.
if __name__ == '__main__':
    rprint("Veritabanı bağlantısı test ediliyor...")
    conn = connect_db()
    if conn and conn.is_connected():
        rprint("[bold green]Test Bağlantısı Başarılı![/bold green]")
        conn.close()
        rprint("Test bağlantısı kapatıldı.")
    else:
        rprint("[bold red]Test Bağlantısı Başarısız![/bold red]")
