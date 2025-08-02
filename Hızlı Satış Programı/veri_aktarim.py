# veri_aktarim.py
# Veri içe aktarma ve dışa aktarma işlemlerini yönetir (CSV, Excel vb.)
# v55: Hata importları eklendi, decimal dönüşüm sağlamlaştırıldı.

import csv
from decimal import Decimal, InvalidOperation
import datetime
from rich import print as rprint  # Kullanıcıya mesaj vermek için
# Gerekli hata sınıflarını import edelim
from hatalar import DatabaseError, DuplicateEntryError, SaleIntegrityError, UserInputError
import urun_veritabani as product_db_ops
import marka_veritabani as brand_db_ops
import kategori_veritabani as category_db_ops
import re  # Sayısal değerleri temizlemek için eklendi

# CSV Dosyası için kullanılacak standart başlıklar
CSV_HEADERS = [
    "Barkod", "UrunAdi", "Marka", "Kategori", "Stok",
    "KDVHaricSatisFiyati", "KDVOra", "KDVDahilSatisFiyati",
    "MinStok", "Aktif"
]


def _clean_numeric_string(num_str):
    """Sayısal string'i temizler (TL, %, boşluk vb. kaldırır, virgülü noktaya çevirir)."""
    if not isinstance(num_str, str):
        num_str = str(num_str)  # String değilse string'e çevir
    # Bilinen para birimleri, yüzde işareti ve boşlukları kaldır
    # Rakam, virgül, nokta dışındakileri sil
    cleaned = re.sub(r"[^\d,\.]", "", num_str)
    # Virgülü noktaya çevir (Decimal için)
    cleaned = cleaned.replace(',', '.')
    return cleaned


def export_products_to_csv(connection, filename="urun_listesi.csv"):
    """
    Mevcut ürün verilerini (belirlenen sütunlarla) bir CSV dosyasına aktarır.
    """
    try:
        products_data = product_db_ops.get_products_for_export(connection)
        if not products_data:
            rprint("[yellow]Dışa aktarılacak ürün bulunamadı.[/]")
            return False

        with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerow(CSV_HEADERS)

            for item in products_data:
                is_active_str = "Evet" if item.get('is_active') else "Hayir"
                row_data = [
                    item.get('barcode', ''),
                    item.get('name', ''),
                    item.get('brand_name', ''),
                    item.get('category_name', ''),
                    str(item.get('stock', '')),
                    # Ondalık ayracı Excel için virgül yapalım
                    str(item.get('price_before_kdv', '')).replace('.', ','),
                    str(item.get('kdv_rate', '')).replace('.', ','),
                    str(item.get('selling_price', '')).replace('.', ','),
                    str(item.get('min_stock_level', '')),
                    is_active_str
                ]
                writer.writerow(row_data)

        rprint(
            f"[bold green]>>> {len(products_data)} ürün başarıyla '{filename}' dosyasına aktarıldı.[/]")
        return True

    except FileNotFoundError:
        rprint(
            f"[bold red]HATA: '{filename}' dosyası oluşturulamadı veya yazılamadı. Klasör izinlerini kontrol edin.[/]")
        return False
    except IOError as e:
        rprint(
            f"[bold red]HATA: CSV dosyası yazılırken G/Ç hatası oluştu: {e}[/]")
        return False
    except DatabaseError as e:
        rprint(
            f"[bold red]HATA: Ürün verileri veritabanından alınırken hata: {e}[/]")
        return False
    except Exception as e:
        rprint(
            f"[bold red]HATA: CSV dışa aktarma sırasında beklenmedik hata: {e}[/]")
        return False


def import_products_from_csv(connection, filename):
    """
    Bir CSV dosyasından ürün verilerini okur ve veritabanına ekler veya günceller.
    """
    added_count = 0
    updated_count = 0
    skipped_count = 0
    processed_rows = 0

    try:
        with open(filename, mode='r', newline='', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=';')

            if not reader.fieldnames or any(h not in reader.fieldnames for h in CSV_HEADERS):
                rprint(
                    f"[bold red]HATA: CSV dosyasındaki başlıklar beklenenden farklı veya eksik![/]")
                rprint(f"[dim]Beklenen başlıklar: {';'.join(CSV_HEADERS)}[/]")
                rprint(
                    f"[dim]Dosyadaki başlıklar: {';'.join(reader.fieldnames if reader.fieldnames else [])}[/]")
                return 0, 0, 0

            rprint(f"'{filename}' dosyasından içe aktarma işlemi başlatıldı...")

            for row_num, row in enumerate(reader, start=2):
                processed_rows += 1
                try:
                    barcode = row.get(CSV_HEADERS[0], "").strip()
                    name = row.get(CSV_HEADERS[1], "").strip()
                    brand_name = row.get(CSV_HEADERS[2], "").strip() or None
                    category_name = row.get(CSV_HEADERS[3], "").strip() or None
                    # Sayısal değerleri almadan önce temizleyelim
                    stock_str = _clean_numeric_string(
                        row.get(CSV_HEADERS[4], "0"))
                    price_before_kdv_str = _clean_numeric_string(
                        row.get(CSV_HEADERS[5], "0"))
                    kdv_rate_str = _clean_numeric_string(
                        row.get(CSV_HEADERS[6], "0"))
                    selling_price_str = _clean_numeric_string(
                        row.get(CSV_HEADERS[7], "0"))
                    min_stock_str = _clean_numeric_string(
                        row.get(CSV_HEADERS[8], "0"))
                    is_active_str = row.get(
                        CSV_HEADERS[9], "Evet").strip().lower()

                    if not barcode:
                        rprint(
                            f"[yellow]Satır {row_num}: Barkod boş olduğu için atlandı.[/]")
                        skipped_count += 1
                        continue
                    if not name:
                        rprint(
                            f"[yellow]Satır {row_num}: Ürün Adı boş olduğu için atlandı (Barkod: {barcode}).[/]")
                        skipped_count += 1
                        continue

                    try:
                        stock = int(stock_str) if stock_str else 0
                        price_before_kdv = Decimal(
                            price_before_kdv_str) if price_before_kdv_str else Decimal('0.00')
                        kdv_rate = Decimal(
                            kdv_rate_str) if kdv_rate_str else Decimal('0.00')
                        selling_price = Decimal(
                            selling_price_str) if selling_price_str else Decimal('0.00')
                        # min_stock_str boş veya 0 olabilir, sorun değil
                        min_stock_level = int(
                            min_stock_str) if min_stock_str else 0
                        is_active = True if is_active_str == "evet" else False

                        if stock < 0:
                            stock = 0
                        if price_before_kdv < 0:
                            price_before_kdv = Decimal('0.00')
                        if kdv_rate < 0:
                            kdv_rate = Decimal('0.00')
                        if selling_price < 0:
                            selling_price = Decimal('0.00')
                        if min_stock_level < 0:
                            min_stock_level = 0

                    except (ValueError, InvalidOperation) as conversion_err:
                        # Temizlemeye rağmen hala hata varsa, format gerçekten bozuktur.
                        rprint(
                            f"[yellow]Satır {row_num}: Sayısal alanlarda geçersiz değer olduğu için atlandı (Barkod: {barcode}). Hata: {conversion_err}[/]")
                        skipped_count += 1
                        continue

                    brand_id = None
                    if brand_name:
                        brand_data = brand_db_ops.get_brand_by_name(
                            connection, brand_name)
                        if brand_data:
                            brand_id = brand_data.get('brand_id')
                        else:
                            rprint(
                                f"[yellow]Satır {row_num}: Marka '{brand_name}' bulunamadı. Markasız devam ediliyor.[/]")

                    category_id = None
                    if category_name:
                        category_data = category_db_ops.get_category_by_name(
                            connection, category_name)
                        if category_data:
                            category_id = category_data.get('category_id')
                        else:
                            rprint(
                                f"[yellow]Satır {row_num}: Kategori '{category_name}' bulunamadı. Kategorisiz devam ediliyor.[/]")

                    existing_product = product_db_ops.get_product_by_barcode(
                        connection, barcode, only_active=False)

                    if existing_product:
                        product_id = existing_product.get('product_id')
                        try:
                            # ***** DuplicateEntryError burada da yakalanmalı *****
                            updated = product_db_ops.update_product(
                                connection, product_id, name, brand_id, category_id,
                                price_before_kdv, kdv_rate, selling_price,
                                stock, min_stock_level
                            )
                            if updated:
                                current_db_active = existing_product.get(
                                    'is_active')
                                if is_active and not current_db_active:
                                    product_db_ops.reactivate_product(
                                        connection, product_id)
                                elif not is_active and current_db_active:
                                    product_db_ops.deactivate_product(
                                        connection, product_id)
                                updated_count += 1
                            else:
                                # update_product içinde hata yakalanmış olabilir veya bilgi aynıdır
                                # rprint(f"[dim]Satır {row_num}: Ürün (Barkod: {barcode}) güncellenmedi (Belki bilgi aynı?).[/dim]")
                                # Eğer bilgi aynıysa atlanmış saymayalım. Şimdilik bir şey yapma.
                                pass

                        # Hata yakalama güncellendi
                        except (DatabaseError, ValueError, DuplicateEntryError) as upd_err:
                            rprint(
                                f"[red]Satır {row_num}: Ürün (Barkod: {barcode}) güncellenirken HATA: {upd_err}[/]")
                            skipped_count += 1
                    else:
                        try:
                            # ***** DuplicateEntryError burada da yakalanmalı *****
                            new_id = product_db_ops.add_product(
                                connection, barcode, name, brand_id, price_before_kdv, kdv_rate, selling_price, stock, category_id, min_stock_level
                            )
                            if new_id:
                                if not is_active:
                                    product_db_ops.deactivate_product(
                                        connection, new_id)
                                added_count += 1
                            else:
                                rprint(
                                    f"[yellow]Satır {row_num}: Ürün (Barkod: {barcode}) eklenemedi (DB fonksiyonu ID döndürmedi).[/]")
                                skipped_count += 1
                        # Hata yakalama güncellendi
                        except (DatabaseError, ValueError, DuplicateEntryError) as add_err:
                            rprint(
                                f"[red]Satır {row_num}: Ürün (Barkod: {barcode}) eklenirken HATA: {add_err}[/]")
                            skipped_count += 1

                except KeyError as ke:  # Eğer CSV'de beklenen başlık yoksa
                    rprint(
                        f"[red]Satır {row_num}: CSV dosyasında beklenen '{ke}' başlığı bulunamadığı için işlenemedi.[/]")
                    skipped_count += 1
                except Exception as row_err:
                    # DuplicateEntryError artık burada yakalanmayacak, yukarıda yakalandı.
                    rprint(
                        f"[red]Satır {row_num}: İşlenirken beklenmedik hata: {row_err}[/]")
                    skipped_count += 1

        rprint("\n[bold]İçe Aktarma Tamamlandı![/]")
        rprint(f"  Toplam Okunan Satır (Başlık Hariç): {processed_rows}")
        rprint(f"  [green]Yeni Eklenen Ürün Sayısı    : {added_count}[/]")
        rprint(f"  [blue]Güncellenen Ürün Sayısı     : {updated_count}[/]")
        rprint(f"  [yellow]Atlanan Satır Sayısı        : {skipped_count}[/]")
        return added_count, updated_count, skipped_count

    except FileNotFoundError:
        rprint(f"[bold red]HATA: '{filename}' dosyası bulunamadı.[/]")
        return 0, 0, 0
    except IOError as e:
        rprint(
            f"[bold red]HATA: CSV dosyası okunurken G/Ç hatası oluştu: {e}[/]")
        return 0, 0, 0
    except Exception as e:
        rprint(
            f"[bold red]HATA: CSV içe aktarma sırasında beklenmedik hata: {e}[/]")
        import traceback
        traceback.print_exc()
        return 0, 0, processed_rows
