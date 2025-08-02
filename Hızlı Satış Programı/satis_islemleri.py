# -*- coding: utf-8 -*-
import urun_veritabani as uv
import satis_veritabani as sv
# import musteri_veritabani as mv # Müşteri seçimi ileride eklenebilir
from arayuz_yardimcilari import (
    metin_iste,
    sayi_iste,
    float_iste,
    evet_hayir_sor,
    liste_goster_ve_sec,
    pause_and_clear,
    clear_screen
)
from hatalar import KayitBulunamadiHatasi, VeritabaniHatasi, VeriEklemeHatasi

# --- Satış Sepeti Yönetimi ---
sepet = []  # Satış sepetini tutacak liste (program çalıştığı sürece aktif)


def sepeti_temizle():
    """Satış sepetini boşaltır."""
    global sepet
    sepet = []


def sepete_ekle(urun, miktar):
    """Verilen ürünü belirtilen miktarda sepete ekler veya mevcut miktarı günceller."""
    global sepet
    # Stok kontrolü
    if urun['stok_miktari'] < miktar:
        print(
            f"Uyarı: '{urun['urun_adi']}' için yeterli stok yok (Mevcut: {urun['stok_miktari']}, İstenen: {miktar}).")
        # İsteğe bağlı olarak eklemeyi engelleyebilir veya devam edilebilir. Şimdilik devam edelim.
        # return False

    # Ürün sepette zaten var mı kontrol et
    for item in sepet:
        if item['urun_id'] == urun['id']:
            # Stok yeterliyse miktarı artır
            yeni_miktar = item['miktar'] + miktar
            if urun['stok_miktari'] < yeni_miktar:
                print(
                    f"Uyarı: '{urun['urun_adi']}' için yeterli stok yok (Mevcut: {urun['stok_miktari']}, Sepetteki + İstenen: {yeni_miktar}). Miktar artırılamadı.")
                return False  # Miktarı artırma

            item['miktar'] = yeni_miktar
            item['toplam_fiyat'] = round(yeni_miktar * item['birim_fiyat'], 2)
            print(
                f"'{urun['urun_adi']}' ürününün miktarı güncellendi (Yeni Miktar: {yeni_miktar}).")
            return True  # Güncelleme yapıldı

    # Ürün sepette yoksa yeni olarak ekle
    sepet_ogesi = {
        'urun_id': urun['id'],
        'urun_adi': urun['urun_adi'],
        'barkod': urun.get('barkod', 'Yok'),
        'miktar': miktar,
        'birim_fiyat': urun['satis_fiyati'],
        'toplam_fiyat': round(miktar * urun['satis_fiyati'], 2),
        'stok_kontrol': urun['stok_miktari']  # Satış anında stok kontrolü için
    }
    sepet.append(sepet_ogesi)
    print(f"'{urun['urun_adi']}' ({miktar} adet) sepete eklendi.")
    return True  # Ekleme yapıldı


def sepet_urun_sil(urun_id):
    """Verilen ID'ye sahip ürünü sepetten siler."""
    global sepet
    for i, item in enumerate(sepet):
        if item['urun_id'] == urun_id:
            silinen_urun_adi = item['urun_adi']
            del sepet[i]
            print(f"'{silinen_urun_adi}' sepetten silindi.")
            return True
    print(f"ID={urun_id} olan ürün sepette bulunamadı.")
    return False


def sepet_urun_miktar_guncelle(urun_id, yeni_miktar):
    """Sepetteki ürünün miktarını günceller."""
    global sepet
    if yeni_miktar <= 0:
        print("Miktar 0 veya daha küçük olamaz. Ürünü silmek için 'S' seçeneğini kullanın.")
        return False

    for item in sepet:
        if item['urun_id'] == urun_id:
            # Stok kontrolü
            urun_db = uv.urun_getir(urun_id)  # En güncel stok için DB'den oku
            if urun_db['stok_miktari'] < yeni_miktar:
                print(
                    f"Uyarı: '{item['urun_adi']}' için yeterli stok yok (Mevcut: {urun_db['stok_miktari']}, İstenen: {yeni_miktar}). Miktar güncellenemedi.")
                return False

            item['miktar'] = yeni_miktar
            item['toplam_fiyat'] = round(yeni_miktar * item['birim_fiyat'], 2)
            print(
                f"'{item['urun_adi']}' ürününün miktarı {yeni_miktar} olarak güncellendi.")
            return True
    print(f"ID={urun_id} olan ürün sepette bulunamadı.")
    return False


def sepeti_goster():
    """Mevcut sepet içeriğini ve toplam tutarı ekrana basar."""
    clear_screen()
    print("--- Güncel Sepet ---")
    if not sepet:
        print("Sepetiniz boş.")
        print("-" * 40)
        return 0.0  # Toplam tutar 0

    toplam_tutar = 0.0
    print(f"{'ID':<5} {'Barkod':<15} {'Ürün Adı':<25} {'Miktar':<8} {'Birim F.':<10} {'Toplam F.':<10}")
    print("-" * 75)
    for item in sepet:
        print(f"{item['urun_id']:<5} {item['barkod']:<15} {item['urun_adi']:<25} {item['miktar']:<8} {item['birim_fiyat']:<10.2f} {item['toplam_fiyat']:<10.2f}")
        toplam_tutar += item['toplam_fiyat']
    print("-" * 75)
    toplam_tutar = round(toplam_tutar, 2)
    print(f"{'Genel Toplam:':>65} {toplam_tutar:>10.2f}")
    print("-" * 75)
    return toplam_tutar

# --- Ürün Arama ve Ekleme ---


def urun_ara_ve_sepete_ekle():
    """Kullanıcıdan barkod veya ürün adı alarak ürünü bulur ve sepete ekler."""
    while True:
        girdi = metin_iste(
            "Barkodu okutun veya ürün ID'sini girin (Listelemek için 'L', Çıkış 'Q'):", zorunlu=True).strip()

        if girdi.upper() == 'Q':
            return False  # Satış ekranına geri dön
        elif girdi.upper() == 'L':
            # Ürünleri listele ve seçtir (urun_islemleri'ndeki gibi)
            print("Ürün Listesi (Arama yapmak için isim veya barkod girin):")
            # urun_islemleri'ndeki listeleme fonksiyonunu burada kullanmak yerine
            # benzer bir mantıkla doğrudan ürünleri çekip listeleyelim.
            arama_terimi = metin_iste(
                "Aranacak ürün adı/barkod (hepsi için Enter):", zorunlu=False)
            try:
                urunler_db = uv.tum_urunleri_getir(
                    arama_terimi=arama_terimi, sirala_by='urun_adi')
                if not urunler_db:
                    print("Arama kriterine uygun ürün bulunamadı.")
                    continue

                liste_verisi = []
                for u in urunler_db:
                    liste_verisi.append({
                        'id': u['id'],
                        'display': f"{u['id']}: {u['urun_adi']} (Stok: {u['stok_miktari']}, Fiyat: {u['satis_fiyati']})"
                    })

                secilen_urun_liste = liste_goster_ve_sec(
                    liste_verisi, etiket_kolonu='display', id_kolonu='id', baslik="Sepete Eklemek İçin Ürün Seçin:", zorunlu=False)

                if secilen_urun_liste:
                    urun_id = secilen_urun_liste['id']
                    # Seçilen ürünün tam bilgisini tekrar alalım
                    try:
                        urun = uv.urun_getir(urun_id)
                        miktar = sayi_iste(
                            f"'{urun['urun_adi']}' için miktar:", min_deger=1, varsayilan=1)
                        sepete_ekle(urun, miktar)
                        return True  # Ürün eklendi, ana döngüye dön
                    except KayitBulunamadiHatasi:
                        print(f"Hata: ID={urun_id} olan ürün bulunamadı.")
                    except Exception as e:
                        print(f"Ürün getirilirken hata: {e}")
                else:
                    print("Ürün seçilmedi.")
                    # Ana döngüye devam et (yeni barkod/ID sormak için)

            except VeritabaniHatasi as e:
                print(f"Ürünler listelenirken hata: {e}")
            continue  # Listeleme sonrası ana döngüye devam

        # Girilen değer ID mi yoksa Barkod mu?
        urun = None
        try:
            # Önce ID olarak deneyelim
            if girdi.isdigit():
                urun_id = int(girdi)
                try:
                    urun = uv.urun_getir(urun_id)
                except KayitBulunamadiHatasi:
                    # ID ile bulunamadıysa barkod olarak arayalım
                    try:
                        urun = uv.urun_getir_by_barkod(girdi)
                    except KayitBulunamadiHatasi:
                        print(
                            f"ID veya Barkod '{girdi}' ile eşleşen ürün bulunamadı.")
                        continue  # Yeni girdi iste
            else:
                # ID değilse doğrudan barkod olarak arayalım
                try:
                    urun = uv.urun_getir_by_barkod(girdi)
                except KayitBulunamadiHatasi:
                    print(f"Barkod '{girdi}' ile eşleşen ürün bulunamadı.")
                    continue  # Yeni girdi iste

            # Ürün bulunduysa miktar iste ve sepete ekle
            if urun:
                miktar = sayi_iste(
                    f"'{urun['urun_adi']}' için miktar:", min_deger=1, varsayilan=1)
                sepete_ekle(urun, miktar)
                return True  # Ürün eklendi, ana döngüye dön

        except VeritabaniHatasi as e:
            print(f"Ürün aranırken veritabanı hatası: {e}")
        except ValueError:
            print("Geçersiz ID formatı.")
        except Exception as e:
            print(f"Beklenmedik bir hata oluştu: {e}")
            # Ana döngüye devam et

# --- Ödeme İşlemleri ---


def odeme_al(toplam_tutar):
    """Ödeme yöntemini seçtirir, nakit ise ödenen tutarı alır ve para üstünü hesaplar."""
    print("\n--- Ödeme ---")
    odeme_yontemleri = [
        {'id': 'Nakit', 'display': 'Nakit'},
        {'id': 'Kredi Kartı', 'display': 'Kredi Kartı'},
        # Diğer yöntemler eklenebilir...
        {'id': 'İptal', 'display': 'Satışı İptal Et'}
    ]

    secilen_yontem_liste = liste_goster_ve_sec(
        odeme_yontemleri, etiket_kolonu='display', id_kolonu='id', baslik="Ödeme Yöntemi Seçin:", zorunlu=True)
    odeme_yontemi = secilen_yontem_liste['id']

    if odeme_yontemi == 'İptal':
        return None  # Satış iptal edildi

    odenen_tutar = toplam_tutar  # Kredi kartı veya diğerlerinde varsayılan
    para_ustu = 0.0

    if odeme_yontemi == 'Nakit':
        while True:
            odenen = float_iste(
                f"Ödenen Nakit Tutar (Toplam: {toplam_tutar:.2f}):", zorunlu=True, min_deger=toplam_tutar)
            if odenen is not None:
                odenen_tutar = round(odenen, 2)
                para_ustu = round(odenen_tutar - toplam_tutar, 2)
                print(f"Para Üstü: {para_ustu:.2f}")
                break
            else:
                # float_iste zaten hata mesajı verir.
                pass  # Tekrar sor

    return {
        'odeme_yontemi': odeme_yontemi,
        'odenen_tutar': odenen_tutar,
        'para_ustu': para_ustu
    }

# --- Satış Tamamlama ---


def satis_tamamla(aktif_kullanici_id, odeme_bilgileri):
    """Satışı veritabanına kaydeder ve stokları günceller."""
    global sepet
    if not sepet:
        print("Hata: Sepet boş, satış tamamlanamaz.")
        return False

    toplam_tutar = sum(item['toplam_fiyat'] for item in sepet)
    toplam_tutar = round(toplam_tutar, 2)
    # Şu an için genel indirim yok, ileride eklenebilir.
    toplam_indirim = 0.0

    # Müşteri seçimi ileride eklenebilir
    musteri_id = None

    # Stok Kontrolü (Son kez)
    yetersiz_stok_var = False
    for item in sepet:
        try:
            urun_db = uv.urun_getir(item['urun_id'])
            if urun_db['stok_miktari'] < item['miktar']:
                print(
                    f"HATA: Satış tamamlanamıyor! '{item['urun_adi']}' için yeterli stok yok (Mevcut: {urun_db['stok_miktari']}, İstenen: {item['miktar']}).")
                yetersiz_stok_var = True
        except (KayitBulunamadiHatasi, VeritabaniHatasi) as e:
            print(
                f"HATA: Stok kontrolü sırasında '{item['urun_adi']}' ürünü alınamadı: {e}")
            yetersiz_stok_var = True

    if yetersiz_stok_var:
        print("Lütfen sepetteki ürün miktarlarını güncelleyin veya ürünü çıkarın.")
        return False  # Satışı tamamlama

    # 1. Ana Satış Kaydını Ekle
    try:
        satis_id = sv.satis_ekle(
            kullanici_id=aktif_kullanici_id,
            toplam_tutar=toplam_tutar,
            odeme_yontemi=odeme_bilgileri['odeme_yontemi'],
            musteri_id=musteri_id,
            toplam_indirim=toplam_indirim,
            odenen_tutar=odeme_bilgileri['odenen_tutar'],
            para_ustu=odeme_bilgileri['para_ustu'],
            # fis_no eklenebilir
        )
    except VeriEklemeHatasi as e:
        print(f"Hata: Satış ana kaydı oluşturulamadı: {e}")
        return False
    except Exception as e:
        print(f"Satış kaydı sırasında beklenmedik hata: {e}")
        return False

    # 2. Satış Detaylarını Toplu Ekle
    try:
        # satis_veritabani'na göndereceğimiz sepet formatını ayarlayalım
        detay_listesi = []
        for item in sepet:
            detay_listesi.append({
                'urun_id': item['urun_id'],
                'miktar': item['miktar'],
                'birim_fiyat': item['birim_fiyat'],
                'toplam_fiyat': item['toplam_fiyat'],
                'indirim_tutari': 0  # Ürün bazlı indirim şimdilik yok
            })
        sv.toplu_satis_detayi_ekle(satis_id, detay_listesi)
    except VeriEklemeHatasi as e:
        print(f"Hata: Satış detayları kaydedilemedi: {e}")
        # !!! Bu durumda ana satış kaydı oluştu ama detaylar yok. Manuel düzeltme gerekir.
        # İdeal olarak transaction yönetimi ile bu durum engellenmeli.
        print("!!! DİKKAT: Satış ana kaydı oluştu ancak detaylar eklenemedi. Veritabanı tutarsız olabilir!")
        return False  # Satış tamamlanmadı gibi davranalım şimdilik
    except Exception as e:
        print(f"Satış detayları kaydı sırasında beklenmedik hata: {e}")
        return False

    # 3. Stokları Güncelle
    stok_guncelleme_hatasi = False
    for item in sepet:
        try:
            # Satılan miktar kadar stoğu azalt (-miktar)
            uv.stok_guncelle(item['urun_id'], -item['miktar'])
        except (VeritabaniHatasi, KayitBulunamadiHatasi) as e:
            print(
                f"Hata: '{item['urun_adi']}' ürününün stoğu güncellenemedi: {e}")
            stok_guncelleme_hatasi = True
        except Exception as e:
            print(
                f"Stok güncelleme sırasında beklenmedik hata ({item['urun_adi']}): {e}")
            stok_guncelleme_hatasi = True

    if stok_guncelleme_hatasi:
        print("!!! DİKKAT: Satış kaydedildi ancak bazı ürünlerin stokları güncellenemedi. Lütfen stokları manuel kontrol edin!")
        # Satış başarılı kabul edilebilir ama uyarı verilmeli.

    print("\nSatış başarıyla tamamlandı!")
    # Fiş yazdırma vb. işlemler burada tetiklenebilir.
    sepeti_temizle()  # Yeni satış için sepeti boşalt
    return True


# --- Hızlı Satış Ana Ekranı ---
def hizli_satis_ekrani(aktif_kullanici_id):
    """Hızlı satış işlemlerinin yapıldığı ana döngü."""
    sepeti_temizle()  # Başlangıçta sepetin boş olduğundan emin ol

    while True:
        toplam = sepeti_goster()  # Her adımda sepeti göster

        print("\n--- Seçenekler ---")
        print("1. Ürün Ekle/Bul (Barkod/ID/Listele)")
        if sepet:  # Sepet boş değilse göster
            print("2. Miktar Değiştir")
            print("3. Ürün Sil")
            print("O. Ödeme Yap ve Satışı Tamamla")
        print("Q. Satış Ekranından Çık (Sepet İptal Olur)")

        secim = metin_iste("Seçiminiz:", zorunlu=True).upper()

        if secim == '1':
            urun_ara_ve_sepete_ekle()
            # Ekranı hemen temizlemeden önce mesajların görünmesi için kısa bekleme
            pause_and_clear(bekle=False)  # Sadece ekranı temizle
        elif secim == '2' and sepet:
            urun_id_str = metin_iste(
                "Miktarını değiştirmek istediğiniz ürünün ID'si:", zorunlu=True)
            if urun_id_str.isdigit():
                urun_id = int(urun_id_str)
                yeni_miktar = sayi_iste("Yeni miktar:", min_deger=1)
                if yeni_miktar is not None:
                    sepet_urun_miktar_guncelle(urun_id, yeni_miktar)
            else:
                print("Geçersiz ID formatı.")
            pause_and_clear(bekle=True)
        elif secim == '3' and sepet:
            urun_id_str = metin_iste(
                "Sepetten silmek istediğiniz ürünün ID'si:", zorunlu=True)
            if urun_id_str.isdigit():
                urun_id = int(urun_id_str)
                sepet_urun_sil(urun_id)
            else:
                print("Geçersiz ID formatı.")
            pause_and_clear(bekle=True)
        elif secim == 'O' and sepet:
            odeme_bilgileri = odeme_al(toplam)
            if odeme_bilgileri:  # Ödeme iptal edilmediyse
                if satis_tamamla(aktif_kullanici_id, odeme_bilgileri):
                    # Satış başarılı, döngüden çık veya yeni satışa başla
                    print("\nYeni satışa hazırlanıyor...")
                    pause_and_clear(bekle=True, sure=3)
                    # Yeni satış için döngü devam ediyor, sepet zaten temizlendi.
                else:
                    # Satış tamamlanamadı, ekranda kal, kullanıcı tekrar deneyebilir
                    print(
                        "Satış tamamlanamadı. Lütfen sepeti kontrol edin veya tekrar deneyin.")
                    pause_and_clear(bekle=True)
            else:
                print("Ödeme iptal edildi.")
                pause_and_clear(bekle=True)
        elif secim == 'Q':
            if sepet:
                if evet_hayir_sor("Sepette ürünler var. Çıkmak istediğinize emin misiniz? Sepet iptal olacak."):
                    print("Satış ekranından çıkılıyor, sepet iptal edildi.")
                    sepeti_temizle()
                    break  # Döngüden çık
                else:
                    print("Çıkma işlemi iptal edildi.")
                    pause_and_clear(bekle=True)
            else:
                print("Satış ekranından çıkılıyor.")
                break  # Döngüden çık
        else:
            print("Geçersiz seçim.")
            pause_and_clear(bekle=True)


# --- Test Amaçlı Çalıştırma ---
if __name__ == "__main__":
    # Bu dosya doğrudan çalıştırıldığında test amaçlı ekranı açar.
    # Gerçek uygulamada bu fonksiyon ana dosya (hizli_satis.py) üzerinden çağrılacaktır.
    print("Hızlı Satış Ekranı Test Modu")
    # Test için varsayılan kullanıcı ID'si 1 kullanalım
    hizli_satis_ekrani(aktif_kullanici_id=1)
