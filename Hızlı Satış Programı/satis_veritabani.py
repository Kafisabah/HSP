# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime
from veritabani_islemleri import veritabani_baglan
from hatalar import VeritabaniHatasi, VeriEklemeHatasi

# --- Satış Kaydı Ekleme ---


def satis_ekle(kullanici_id, toplam_tutar, odeme_yontemi, musteri_id=None, toplam_indirim=0, odenen_tutar=None, para_ustu=0, fis_no=None, notlar=None):
    """'satislar' tablosuna yeni bir satış ana kaydı ekler ve eklenen kaydın ID'sini döndürür."""
    conn = None
    try:
        conn = veritabani_baglan()
        cursor = conn.cursor()

        # Eğer ödenen tutar belirtilmemişse, toplam tutar kadar ödendiğini varsayalım
        if odenen_tutar is None:
            odenen_tutar = toplam_tutar - toplam_indirim

        sql = """
        INSERT INTO satislar
        (satis_tarihi, musteri_id, kullanici_id, toplam_tutar, toplam_indirim, odenen_tutar, para_ustu, odeme_yontemi, fis_no, notlar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            datetime.now(),
            musteri_id,
            kullanici_id,
            toplam_tutar,
            toplam_indirim,
            odenen_tutar,
            para_ustu,
            odeme_yontemi,
            fis_no,
            notlar
        )
        cursor.execute(sql, params)
        conn.commit()
        satis_id = cursor.lastrowid
        print(f"Satış kaydı başarıyla eklendi (Satış ID: {satis_id}).")
        return satis_id
    except sqlite3.Error as e:
        if conn:
            conn.rollback()  # Hata durumunda işlemi geri al
        raise VeriEklemeHatasi(
            f"Satış kaydı eklenirken veritabanı hatası: {e}")
    finally:
        if conn:
            conn.close()

# --- Satış Detayı Ekleme ---


def satis_detayi_ekle(satis_id, urun_id, miktar, birim_fiyat, toplam_fiyat, indirim_tutari=0):
    """'satis_detaylari' tablosuna satılan bir ürünün detayını ekler."""
    conn = None
    try:
        conn = veritabani_baglan()
        cursor = conn.cursor()
        sql = """
        INSERT INTO satis_detaylari
        (satis_id, urun_id, miktar, birim_fiyat, toplam_fiyat, indirim_tutari)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (satis_id, urun_id, miktar, birim_fiyat,
                  toplam_fiyat, indirim_tutari)
        cursor.execute(sql, params)
        conn.commit()
        # print(f"Satış detayı eklendi (Satış ID: {satis_id}, Ürün ID: {urun_id}).") # Çok fazla log üretmemesi için kapalı
        return cursor.lastrowid
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        # Bu hatayı doğrudan göstermek yerine, çağıran fonksiyonda yönetmek daha iyi olabilir.
        # print(f"Satış detayı eklenirken veritabanı hatası: {e}")
        raise VeriEklemeHatasi(
            f"Satış detayı eklenirken veritabanı hatası (Satış ID: {satis_id}, Ürün ID: {urun_id}): {e}")
    finally:
        if conn:
            conn.close()

# --- Toplu Satış Detayı Ekleme ---


def toplu_satis_detayi_ekle(satis_id, sepet_urunleri):
    """
    Verilen satış ID'si için sepet ürünleri listesindeki tüm ürünleri
    'satis_detaylari' tablosuna tek bir bağlantı ve transaction içinde ekler.

    Args:
        satis_id (int): İlişkilendirilecek satışın ID'si.
        sepet_urunleri (list): Her biri aşağıdaki anahtarları içeren sözlüklerden oluşan liste:
            'urun_id' (int): Satılan ürünün ID'si.
            'miktar' (int): Satılan miktar.
            'birim_fiyat' (float): Satış anındaki birim fiyat.
            'toplam_fiyat' (float): Miktar * birim_fiyat.
            'indirim_tutari' (float, optional): Ürüne özel indirim tutarı (varsayılan 0).
    """
    conn = None
    try:
        conn = veritabani_baglan()
        cursor = conn.cursor()
        # Verileri hazırlama
        eklenecek_detaylar = []
        for urun in sepet_urunleri:
            eklenecek_detaylar.append((
                satis_id,
                urun['urun_id'],
                urun['miktar'],
                urun['birim_fiyat'],
                urun['toplam_fiyat'],
                urun.get('indirim_tutari', 0)  # İndirim yoksa 0
            ))

        # SQL sorgusu
        sql = """
        INSERT INTO satis_detaylari
        (satis_id, urun_id, miktar, birim_fiyat, toplam_fiyat, indirim_tutari)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        # executemany ile toplu ekleme
        cursor.executemany(sql, eklenecek_detaylar)
        conn.commit()
        print(
            f"{len(eklenecek_detaylar)} adet satış detayı başarıyla eklendi (Satış ID: {satis_id}).")
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()  # Hata durumunda tüm detay eklemelerini geri al
        raise VeriEklemeHatasi(
            f"Toplu satış detayı eklenirken veritabanı hatası (Satış ID: {satis_id}): {e}")
    finally:
        if conn:
            conn.close()


# --- Test Amaçlı Çalıştırma ---
if __name__ == "__main__":
    print("satis_veritabani modülü test ediliyor...")
    try:
        # Örnek bir satış ekleyelim (kullanici_id=1 varsayalım)
        # Gerçek uygulamada kullanıcı ID'si giriş yapan kullanıcıdan alınmalı.
        # Müşteri ID'si opsiyonel.
        ornek_satis_id = satis_ekle(
            kullanici_id=1,
            toplam_tutar=150.75,
            odeme_yontemi="Nakit",
            musteri_id=None,  # Misafir satış
            toplam_indirim=10.0,
            odenen_tutar=150.0,
            para_ustu=9.25,
            notlar="Test satışı"
        )

        if ornek_satis_id:
            print(
                f"\nÖrnek satış başarıyla eklendi. Satış ID: {ornek_satis_id}")

            # Bu satışa ait detayları ekleyelim
            # Gerçek uygulamada bu bilgiler satış sepetinden gelecek.
            # Ürün ID'leri ve fiyatları veritabanınızdaki gerçek değerlere göre ayarlayın.
            ornek_sepet = [
                {'urun_id': 1, 'miktar': 2, 'birim_fiyat': 25.0,
                    'toplam_fiyat': 50.0, 'indirim_tutari': 5.0},
                {'urun_id': 3, 'miktar': 1, 'birim_fiyat': 110.75,
                    'toplam_fiyat': 110.75, 'indirim_tutari': 5.0}
            ]

            # Tek tek ekleme (eski yöntem, artık toplu kullanılacak)
            # satis_detayi_ekle(ornek_satis_id, 1, 2, 25.0, 50.0, 5.0)
            # satis_detayi_ekle(ornek_satis_id, 3, 1, 110.75, 110.75, 5.0)

            # Toplu ekleme
            toplu_satis_detayi_ekle(ornek_satis_id, ornek_sepet)

            print("\nÖrnek satış detayları eklendi.")

    except (VeritabaniHatasi, VeriEklemeHatasi) as e:
        print(f"\nTest sırasında bir hata oluştu: {e}")
