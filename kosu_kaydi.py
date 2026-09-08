"""
kosu_kaydi.py — her zamanlanmış koşu, sonucu ne olursa olsun iz bıraksın.

Kullanıcı kuralı: "İş her koştuğunda başarılı da olsa bir kayıt bıraksın,
böylece 'çalıştı mı' sorusunu bir daha tahmin etmeyelim."

Sorun şuydu: iş HİÇ tetiklenmediğinde hiçbir yerde iz kalmıyordu. Hata
bildirimi de çalışmıyordu, çünkü bildirim işin İÇİNDE — iş başlamazsa
bildirim de başlamaz. Bu dosya o boşluğu kapatmıyor (tetiklenmeyen iş
kayıt da bırakamaz) ama şunu sağlıyor: kayıt varsa iş çalışmıştır,
kayıt yoksa çalışmamıştır. Belirsizlik kalkıyor.

    python3 kosu_kaydi.py <is_adi> <sonuc> [not]
    python3 kosu_kaydi.py --ozet          # son koşular
    python3 kosu_kaydi.py --bayatlik      # kaç gündür yayın yok
    python3 kosu_kaydi.py --tetikleme     # yayın işi her sabah KAÇTA tetiklendi
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent
KAYIT = KOK / "config" / "kosu_kaydi.json"
DURUM = KOK / "config" / "yayin_durumu.json"
# Bu kadar gün yayın olmazsa bir şey ters demektir. Arşiv modunda her gün
# yayın bekliyoruz; 2 gün pay, gecikmeler ve maçsız günler için.
BAYATLIK_ESIGI_GUN = 2
SON_N_KAYIT = 60


def _oku():
    if not KAYIT.exists():
        return {"_aciklama": "Zamanlanmış işlerin koşu kaydı. Her koşu, sonucu "
                             "ne olursa olsun buraya bir satır yazar. Kayıt yoksa "
                             "iş hiç tetiklenmemiştir.", "kosular": []}
    return json.loads(KAYIT.read_text(encoding="utf-8"))


def yaz(is_adi, sonuc, not_=""):
    d = _oku()
    d["kosular"].append({
        "zaman": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "is": is_adi,
        "sonuc": sonuc,
        "not": not_,
    })
    # Dosya sonsuza kadar büyümesin — son N koşu yeter.
    d["kosular"] = d["kosular"][-SON_N_KAYIT:]
    KAYIT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"koşu kaydı: {is_adi} → {sonuc}" + (f" ({not_})" if not_ else ""))
    return 0


def ozet():
    d = _oku()
    if not d["kosular"]:
        print("HİÇ KOŞU KAYDI YOK — zamanlanmış iş hiç tetiklenmemiş.")
        return 0
    print(f"Son {min(15, len(d['kosular']))} koşu:")
    for k in d["kosular"][-15:]:
        print(f"  {k['zaman']}  {k['is']:<10} {k['sonuc']:<10} {k.get('not','')}")
    return 0


def bayatlik():
    """Kaç gündür yayın yok? Zamanlayıcı sessizce durursa bunu yakalar."""
    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    son = (durum.get("son_yayin") or {}).get("yayinlandi")
    if not son:
        print("Hiç yayın yapılmamış.")
        return 0
    gecen = datetime.utcnow() - datetime.fromisoformat(son.rstrip("Z"))
    gun = gecen.days + gecen.seconds / 86400
    print(f"Son yayından bu yana: {gun:.1f} gün (eşik {BAYATLIK_ESIGI_GUN})")
    if gun > BAYATLIK_ESIGI_GUN:
        print("BAYAT")
        return 1
    return 0


# ---------------------------------------------------------------------------
# TETİKLEME SAATİ ÖLÇÜMÜ
#
# "Site kaçta çıkıyor" sorusunun cevabı bu dosyadaki kayıttan OKUNMAZ:
# buradaki damga işin BİTİŞİNE yakın atılıyor, ölçmek istediğimiz şey ise
# BAŞLAMA anı. İkisi arasında koşu süresi var (canlı doğrulama tek başına
# 5 dakikaya kadar bekleyebiliyor). Doğru kaynak GitHub'ın kendi kaydı:
# her koşunun `run_started_at` alanı.
# ---------------------------------------------------------------------------

TSI = timezone(timedelta(hours=3))          # Türkiye UTC+3, yaz saati yok
HEDEF_SAAT = 9                              # yayın 09:00 TSİ


def _jeton():
    """GITHUB_TOKEN: ortamdan, yoksa .env'den. Değeri EKRANA YAZILMAZ."""
    import os
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    dosya = KOK / ".env"
    if dosya.exists():
        for satir in dosya.read_text(encoding="utf-8").splitlines():
            if satir.startswith("GITHUB_TOKEN="):
                return satir.split("=", 1)[1].strip()
    return None


def tetikleme(gun_sayisi=7, depo="yigitolmezcan/overnight"):
    """Son N günün yayın tetiklemeleri: saat kaçta, hedefe göre kaç dakika."""
    import urllib.request

    jeton = _jeton()
    if not jeton:
        print("GITHUB_TOKEN yok (ortamda da .env'de de) — ölçüm yapılamıyor.")
        return 1
    istek = urllib.request.Request(
        f"https://api.github.com/repos/{depo}/actions/workflows/yayinla.yml"
        f"/runs?per_page=100",
        headers={"Authorization": f"Bearer {jeton}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "overnight-olcum"})
    with urllib.request.urlopen(istek, timeout=30) as cevap:
        kosular = json.load(cevap).get("workflow_runs", [])
    if not kosular:
        print("Hiç koşu kaydı yok.")
        return 1

    gunler = {}
    for k in kosular:
        t = datetime.fromisoformat(
            k["run_started_at"].replace("Z", "+00:00")).astimezone(TSI)
        gunler.setdefault(t.date().isoformat(), []).append((t, k["event"]))

    print(f"Yayın işi tetikleme saatleri (TSİ, hedef {HEDEF_SAAT:02d}:00)")
    print("gün          ilk tetikleme  sapma    kaynak            o gün toplam")
    sapmalar = []
    for gun in sorted(gunler)[-gun_sayisi:]:
        satir = sorted(gunler[gun])
        t, olay = satir[0]
        hedef = t.replace(hour=HEDEF_SAAT, minute=0, second=0, microsecond=0)
        sapma = (t - hedef).total_seconds() / 60
        sapmalar.append(sapma)
        print(f"{gun}   {t.strftime('%H:%M:%S')}     {sapma:>+6.0f} dk  "
              f"{olay:16}  {len(satir)} koşu")
    if sapmalar:
        print(f"\nson {len(sapmalar)} gün ortalama sapma: "
              f"{sum(sapmalar) / len(sapmalar):+.1f} dk  "
              f"(en iyi {min(sapmalar):+.0f}, en kötü {max(sapmalar):+.0f})")
    return 0


if __name__ == "__main__":
    if "--ozet" in sys.argv:
        raise SystemExit(ozet())
    if "--bayatlik" in sys.argv:
        raise SystemExit(bayatlik())
    if "--tetikleme" in sys.argv:
        raise SystemExit(tetikleme())
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(yaz(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])))
