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
"""

import json
import sys
from datetime import datetime, timedelta
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


if __name__ == "__main__":
    if "--ozet" in sys.argv:
        raise SystemExit(ozet())
    if "--bayatlik" in sys.argv:
        raise SystemExit(bayatlik())
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    raise SystemExit(yaz(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])))
