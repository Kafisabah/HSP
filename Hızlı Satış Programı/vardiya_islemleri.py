# vardiya_islemleri.py
# Vardiya başlatma, bitirme ve Z Raporu ile ilgili
# kullanıcı etkileşimlerini yönetir.
# v2: handle_end_shift fonksiyonuna Z Raporu hesaplamaları eklendi.
# v3: handle_end_shift fonksiyonuna Sipariş Önerisi Raporu eklendi.

import arayuz_yardimcilari as ui
import vardiya_veritabani as shift_db_ops
import urun_veritabani as product_db_ops  # Sipariş önerisi için eklendi
from hatalar import DatabaseError, UserInputError
from decimal import Decimal, InvalidOperation
from rich.console import Console
from rich.table import Table
import datetime

console = ui.console

# === Handler Fonksiyonları ===
# ... (handle_start_shift fonksiyonu - değişiklik yok) ...


def handle_start_shift(connection, user_id):
    """Yeni vardiya başlatma işlemini yönetir."""
    console.print("\n--- Vardiya Başlat ---", style="bold blue")

    try:
        active_shift = shift_db_ops.get_active_shift(connection, user_id)
        if active_shift:
            console.print(
                f"[bold yellow]Uyarı: Zaten aktif bir vardiyanız (ID: {active_shift.get('shift_id')}) bulunmaktadır.[/]")
            # Aktif vardiyanın ID'sini döndürelim ki ana programda kullanılabilsin
            return active_shift.get('shift_id')

        starting_cash = None
        if ui.get_yes_no_input("Vardiya başı kasa miktarını girmek ister misiniz?"):
            starting_cash = ui.get_positive_decimal_input(
                "Başlangıç Kasa Tutarı (Nakit): ", allow_zero=True)

        new_shift_id = shift_db_ops.start_shift(
            connection, user_id, starting_cash)

        if new_shift_id:
            console.print("[green]Yeni vardiya başarıyla başlatıldı.[/]")
            return new_shift_id
        else:
            # Başlatılamadıysa (örn. başka aktif vardiya varsa ve ID dönmediyse)
            # Zaten uyarı mesajı DB katmanında veriliyor olabilir.
            # console.print("[red]Vardiya başlatılamadı.[/]")
            return None

    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Vardiya Başlatma): {e}", style="bold red")
        return None
    except ValueError as ve:
        console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
        return None
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Vardiya Başlatma): {e}", style="bold red")
        return None


# ***** BU FONKSİYON GÜNCELLENDİ (Sipariş Önerisi Raporu çağrısı eklendi) *****
def handle_end_shift(connection, user_id):
    """Aktif vardiyayı bitirme, Z Raporu ve Sipariş Önerisi Raporu alma işlemini yönetir."""
    console.print("\n--- Vardiya Bitir / Raporlar ---", style="bold blue")

    try:
        # Kullanıcının aktif vardiyasını bul
        active_shift = shift_db_ops.get_active_shift(connection, user_id)
        if not active_shift:
            console.print(
                "[bold yellow]Bitirilecek aktif bir vardiyanız bulunmuyor.[/]")
            return

        shift_id = active_shift.get('shift_id')
        start_time = active_shift.get('start_time')
        starting_cash_db = active_shift.get(
            'starting_cash') or Decimal('0.00')  # None ise 0 kabul et

        console.print(f"Aktif Vardiya ID: {shift_id}")
        console.print(
            f"Başlangıç Zamanı: {start_time.strftime('%d-%m-%Y %H:%M:%S') if start_time else 'Bilinmiyor'}")
        console.print(f"Başlangıç Kasası: {starting_cash_db:.2f} TL")

        # Vardiya sonu sayılan nakit miktarını sor
        ending_cash_counted = ui.get_positive_decimal_input(
            "Vardiya Sonu Sayılan Kasa Tutarı (Nakit): ", allow_zero=True)

        # --- Z Raporu Hesaplamaları ---
        console.print("\n[dim]Vardiya özeti (Z Raporu) hesaplanıyor...[/]")
        sales_summary = shift_db_ops.get_shift_sales_summary(
            connection, shift_id)
        customer_payments_summary = shift_db_ops.get_shift_customer_payments_summary(
            connection, shift_id)

        total_sales_calculated = sales_summary.get(
            'total_sales', Decimal('0.00'))
        cash_sales_calculated = sales_summary.get(
            'cash_sales', Decimal('0.00'))
        card_sales_calculated = sales_summary.get(
            'card_sales', Decimal('0.00'))
        veresiye_sales_calculated = sales_summary.get(
            'veresiye_sales', Decimal('0.00'))
        cash_payments_received = customer_payments_summary.get(
            'cash_payments_received', Decimal('0.00'))
        card_payments_received = customer_payments_summary.get(
            'card_payments_received', Decimal('0.00'))
        total_discount_calculated = sales_summary.get(
            'total_discount', Decimal('0.00'))
        total_promo_discount_calculated = sales_summary.get(
            'total_promotion_discount', Decimal('0.00'))

        expected_cash = starting_cash_db + cash_sales_calculated + cash_payments_received
        calculated_difference = ending_cash_counted - expected_cash

        # --- Z Raporu Gösterimi ---
        console.print("\n--- Vardiya Özeti (Z Raporu) ---", style="bold cyan")
        report_data = {
            "shift_id": shift_id,
            "start_time": start_time,
            "end_time": datetime.datetime.now(),  # Bitiş zamanı olarak şimdiki zaman
            "user_id": user_id,
            "username": active_shift.get('username', '?'),
            "full_name": active_shift.get('full_name', '?'),
            "starting_cash": starting_cash_db,
            "cash_sales": cash_sales_calculated,
            "card_sales": card_sales_calculated,
            "veresiye_sales": veresiye_sales_calculated,
            "total_sales": total_sales_calculated,
            "cash_payments_received": cash_payments_received,
            "card_payments_received": card_payments_received,
            "total_discount": total_discount_calculated,
            "total_promotion_discount": total_promo_discount_calculated,
            "expected_cash": expected_cash,
            "ending_cash_counted": ending_cash_counted,
            "calculated_difference": calculated_difference
        }
        ui.display_z_report(report_data)

        # --- Sipariş Önerisi Raporu ---
        console.print("\n[dim]Sipariş önerisi raporu oluşturuluyor...[/]")
        try:
            suggestion_data = product_db_ops.get_order_suggestion_data(
                connection)
            if suggestion_data:
                # Raporu göstermek için arayuz_yardimcilari'ndaki fonksiyonu çağır
                ui.display_order_suggestion_report(suggestion_data)
            else:
                console.print(
                    "[green]Sipariş önerilecek kritik stoklu ürün bulunmamaktadır.[/]")
        except DatabaseError as suggestion_err:
            console.print(
                f">>> SİPARİŞ ÖNERİ RAPORU HATASI: {suggestion_err}", style="bold red")
        except Exception as suggestion_ex:
            console.print(
                f">>> BEKLENMEDİK HATA (Sipariş Önerisi): {suggestion_ex}", style="bold red")

        # --- Vardiya Bitirme Onayı ---
        notes = input("\nVardiya Notları (isteğe bağlı): ").strip() or None

        if ui.get_yes_no_input(f"\nVardiya {shift_id} bitirilsin ve Z Raporu özeti kaydedilsin mi?"):
            success = shift_db_ops.end_shift(
                connection, shift_id, ending_cash_counted,
                total_sales_calculated, cash_sales_calculated, card_sales_calculated,
                veresiye_sales_calculated, cash_payments_received, card_payments_received,
                calculated_difference, notes
            )
            # Başarı/hata mesajı DB fonksiyonunda veriliyor.
            # Vardiya bitince ana programdaki active_shift_id'nin None yapılması gerekiyor.
            # Bu fonksiyonun bir değer döndürmesi veya ana programın kontrol etmesi lazım.
            # Şimdilik ana program kontrol ediyor (hizli_satis.py'da v0 sonrası kontrol var).
        else:
            console.print("Vardiya bitirme işlemi iptal edildi.",
                          style="yellow")

    except DatabaseError as e:
        console.print(
            f">>> VERİTABANI HATASI (Vardiya Bitirme): {e}", style="bold red")
    except ValueError as ve:
        console.print(f">>> GİRİŞ HATASI: {ve}", style="bold red")
    except Exception as e:
        console.print(
            f">>> BEKLENMEDİK HATA (Vardiya Bitirme): {e}", style="bold red")
        console.print_exception(show_locals=False)
