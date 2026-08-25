"""
kalibrasyon.py — boru hattının 9. adımı.

Elde ne kadar gece varsa hepsini toplu okur ve şunları çıkarır:
gecenin en yüksek rozeti, rozet dağılımı, katman dağılımı.

LLM ÇAĞIRMAZ, AĞA ÇIKMAZ. Sadece `skor/*.json` okunuyor — yani maliyet
sıfır ve istendiği kadar tekrar çalıştırılabilir.

Ne işe yarar:
1. "Kötünün iyisi" eşiğinin kayan yüzdeliği buradan beslenir. Sabit bir
   eşik ("8.5 üstü Mutlaka bil") sakin gecelerde bölümü boş bırakıyor;
   dağılım bilinirse eşik yüzdelik olarak konabilir.
2. Formülün gerçekten AYIRT EDİP ETMEDİĞİ ilk kez toplu görülür. Aynı
   gecede beş maçın aynı rozeti alması (2025-10-22) tek gecede fark
   edilmişti; dağılım bunu sistematik olarak gösterir.

    python3 kalibrasyon.py            # özet tablo
    python3 kalibrasyon.py --csv      # gece başına satır, elektronik tabloya
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parent
SKOR_DIZIN = KOK / "skor"

# yaz.MUTLAKA_ESIGI ile aynı olmalı; oradan içe aktarmak yerine burada
# tekrar tanımlamak yaz.py'yi (ve anthropic bağımlılığını) yüklememek
# için — bu betik ağa çıkmayan, bağımsız bir ölçüm aracı.
MUTLAKA_ESIGI = 8.5
KOVALAR = [(0, 2), (2, 4), (4, 6), (6, 7), (7, 8), (8, 8.5), (8.5, 9), (9, 11)]


def geceleri_oku():
    geceler = []
    for dosya in sorted(SKOR_DIZIN.glob("*.json")):
        if dosya.stem == "latest":
            continue
        veri = json.loads(dosya.read_text(encoding="utf-8"))
        maclar = veri.get("maclar") or []
        if not maclar:
            continue
        rozetler = sorted((m["rozet"] for m in maclar), reverse=True)
        geceler.append({
            "tarih": dosya.stem,
            "mac_sayisi": len(maclar),
            "rozetler": rozetler,
            "en_yuksek": rozetler[0],
            "medyan": statistics.median(rozetler),
            "yayilim": round(rozetler[0] - rozetler[-1], 2),
            "katmanlar": Counter(m.get("katman", "?") for m in maclar),
            # Ayrım ölçüsü: aynı rozeti paylaşan en kalabalık grup.
            # 1 ise her maç ayrı; büyükse formül o gece ayırt edememiş.
            "en_cok_tekrar": Counter(round(r, 2) for r in rozetler).most_common(1)[0][1],
        })
    return geceler


def kova_adi(r):
    for alt, ust in KOVALAR:
        if alt <= r < ust:
            return f"{alt}–{ust}"
    return "?"


def ozet(geceler):
    if not geceler:
        print("skor/ boş — önce hesapla.py ile gece üret.")
        return 1

    print(f"KALİBRASYON — {len(geceler)} gece, "
          f"{sum(g['mac_sayisi'] for g in geceler)} maç\n")

    print("GECE BAŞINA")
    print(f"{'tarih':<12}{'maç':>4}{'en yüksek':>11}{'medyan':>8}{'yayılım':>9}"
          f"{'aynı rozet':>11}  katmanlar")
    for g in geceler:
        k = " ".join(f"{ad}:{n}" for ad, n in sorted(g["katmanlar"].items()))
        isaret = "  <-- ayrım zayıf" if g["en_cok_tekrar"] >= 3 else ""
        print(f"{g['tarih']:<12}{g['mac_sayisi']:>4}{g['en_yuksek']:>11.2f}"
              f"{g['medyan']:>8.2f}{g['yayilim']:>9.2f}{g['en_cok_tekrar']:>11}  {k}{isaret}")

    enler = sorted(g["en_yuksek"] for g in geceler)
    print(f"\nGECENİN EN YÜKSEK ROZETİ — dağılım")
    print(f"  en düşük {enler[0]:.2f} · medyan {statistics.median(enler):.2f} · "
          f"en yüksek {enler[-1]:.2f}")
    for etiket, yuzde in (("%25", 0.25), ("%50", 0.50), ("%75", 0.75), ("%90", 0.90)):
        i = min(int(len(enler) * yuzde), len(enler) - 1)
        print(f"  {etiket:>4} yüzdelik: {enler[i]:.2f}")
    kalan = sum(1 for e in enler if e >= MUTLAKA_ESIGI)
    print(f"  sabit eşiği ({MUTLAKA_ESIGI}) geçen gece: {kalan}/{len(enler)} "
          f"(%{100*kalan//len(enler)}) — kalan gecelerde 'Mutlaka bil' boş kalır")

    print(f"\nTÜM MAÇLARIN ROZET DAĞILIMI")
    tum = [r for g in geceler for r in g["rozetler"]]
    kovalar = Counter(kova_adi(r) for r in tum)
    for alt, ust in KOVALAR:
        ad = f"{alt}–{ust}"
        n = kovalar.get(ad, 0)
        cubuk = "█" * round(40 * n / max(len(tum), 1))
        print(f"  {ad:>9} {n:>4}  {cubuk}")

    print(f"\nKATMAN DAĞILIMI (tüm maçlar)")
    katman = Counter()
    for g in geceler:
        katman.update(g["katmanlar"])
    for ad, n in katman.most_common():
        print(f"  {ad:<8}{n:>5}  %{100*n//len(tum)}")

    zayif = [g for g in geceler if g["en_cok_tekrar"] >= 3]
    print(f"\nAYRIM GÜCÜ")
    print(f"  aynı rozeti 3+ maçın paylaştığı gece: {len(zayif)}/{len(geceler)}")
    if zayif:
        for g in zayif:
            print(f"    {g['tarih']}: {g['en_cok_tekrar']} maç aynı rozette")
    print(f"  gece içi ortalama yayılım: "
          f"{statistics.mean(g['yayilim'] for g in geceler):.2f} puan")
    return 0


def csv_yaz(geceler):
    print("tarih,mac_sayisi,en_yuksek,medyan,yayilim,en_cok_tekrar," +
          ",".join(sorted({k for g in geceler for k in g["katmanlar"]})))
    katman_adlari = sorted({k for g in geceler for k in g["katmanlar"]})
    for g in geceler:
        print(f"{g['tarih']},{g['mac_sayisi']},{g['en_yuksek']},{g['medyan']},"
              f"{g['yayilim']},{g['en_cok_tekrar']}," +
              ",".join(str(g["katmanlar"].get(k, 0)) for k in katman_adlari))
    return 0


if __name__ == "__main__":
    geceler = geceleri_oku()
    raise SystemExit(csv_yaz(geceler) if "--csv" in sys.argv else ozet(geceler))
