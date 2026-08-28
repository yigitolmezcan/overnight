"""og_uret.py — gece başına paylaşım görüntüsü (1200x630 PNG).

Link paylaşıldığında çıkan önizleme. Her gece yayın adımında üretilip
`og/{tarih}.png` olarak kaydediliyor.

NEDEN TARAYICI YOK: HTML'i resme çevirmek için Playwright/Puppeteer
kurmak GitHub koşucusunda birkaç dakika ve ek kırılganlık demek. Tasarım
basit (düz zemin, bir degrade şerit, birkaç metin ve kutu), Pillow ile
doğrudan çizmek hem hızlı hem ağa hiç çıkmıyor. Fontlar depoda
(`fonts/`, OFL) — sistem fontuna güvenilemez, koşucuda yok.

Ölçüler referans tasarımın (600x315) iki katı.
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).parent
FONT_DIZIN = KOK / "fonts"
OG_DIZIN = KOK / "og"
ALAN_ADI = "overnight-yigit8.vercel.app"

G, Y = 1200, 630
ZEMIN = "#0A0D12"
INK = "#EDEFF2"
FAINT = "#5A6472"
EMBER = "#E8763A"
CIZGI = "#1A2230"
SOLUK_ZEMIN = "#232C39"
SOLUK_YAZI = "#6C7787"
SOLUK_AD = "#4C5665"

# Gece bandı — sayfadaki degradenin aynısı (koyu laciverten ember'a).
BANT = ["#0E1520", "#141C2A", "#1E2636", "#2E2A24", "#4A3520", "#E8763A"]
BANT_YUK = 8

KENAR_X, UST, ALT = 72, 60, 56


def _font(ad, boyut):
    return ImageFont.truetype(str(FONT_DIZIN / ad), boyut)


def _genislik(metin, font, aralik=0):
    if not metin:
        return 0
    return sum(font.getlength(k) for k in metin) + aralik * (len(metin) - 1)


def _yaz(ciz, xy, metin, font, renk, aralik=0):
    """Harf aralıklı metin. Pillow'da letter-spacing yok, harf harf
    çiziliyor — başlıktaki sıkı aralık ve mono etiketlerdeki geniş
    aralık tasarımın parçası."""
    x, y = xy
    for k in metin:
        ciz.text((x, y), k, font=font, fill=renk)
        x += font.getlength(k) + aralik
    return x


def _bant(ciz):
    n = len(BANT) - 1
    for x in range(G):
        t = x / (G - 1) * n
        i = min(int(t), n - 1)
        f = t - i
        a = tuple(int(BANT[i][j:j + 2], 16) for j in (1, 3, 5))
        b = tuple(int(BANT[i + 1][j:j + 2], 16) for j in (1, 3, 5))
        ciz.line([(x, 0), (x, BANT_YUK - 1)],
                 fill=tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3)))


AY = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
      "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUN = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def tarih_metni(tarih_str):
    from datetime import date
    y, a, g = (int(x) for x in tarih_str.split("-"))
    t = date(y, a, g)
    return f"{g} {AY[a - 1]} {y} · {GUN[t.weekday()]}"


def kisa_mac_adi(kod_ev, kod_dep):
    import cumle
    return (f"{cumle.TAKIM_KISA.get(kod_ev, kod_ev)} – "
            f"{cumle.TAKIM_KISA.get(kod_dep, kod_dep)}")


def satirlari_sec(skor_gece):
    """(parlak_iki, soluk_bir) — en yüksek iki maç ve en düşük maç.

    Amaç KONTRAST: üstte ne var, altta ne var. Sıralama vaadi böyle
    görünüyor. İki maçlık gecede üçüncü satır UYDURULMUYOR."""
    import hesapla
    maclar = sorted(skor_gece["maclar"], key=hesapla.siralama_anahtari)
    parlak = maclar[:2]
    soluk = maclar[-1] if len(maclar) >= 3 else None
    return parlak, soluk


def ciz(tarih_str, dist, skor_gece):
    img = Image.new("RGB", (G, Y), ZEMIN)
    ciz = ImageDraw.Draw(img)
    _bant(ciz)

    f_logo = _font("BricolageGrotesque.ttf", 40)
    f_baslik = _font("BricolageGrotesque.ttf", 76)
    f_tarih = _font("DMMono-Regular.ttf", 21)
    f_roz = _font("DMMono-Medium.ttf", 32)
    f_ad = _font("DMMono-Regular.ttf", 32)
    f_roz_s = _font("DMMono-Medium.ttf", 28)
    f_ad_s = _font("DMMono-Regular.ttf", 28)
    f_alt = _font("DMMono-Regular.ttf", 22)

    # --- künye ---
    y = UST
    x = _yaz(ciz, (KENAR_X, y), "OVER", f_logo, INK, -1.6)
    _yaz(ciz, (x, y), "NIGHT", f_logo, EMBER, -1.6)
    tm = tarih_metni(tarih_str).upper()
    tw = _genislik(tm, f_tarih, 2.7)
    _yaz(ciz, (G - KENAR_X - tw, y + 12), tm, f_tarih, FAINT, 2.7)

    # --- sabit marka satırı ---
    y += 44 + 44
    x = _yaz(ciz, (KENAR_X, y), "Konuşan ", f_baslik, INK, -3)
    x = _yaz(ciz, (x, y), "box score", f_baslik, EMBER, -3)
    _yaz(ciz, (x, y), ".", f_baslik, INK, -3)

    # --- maç satırları ---
    # Liste, başlığın altı ile alt şerit arasına DİKEYDE ORTALANIYOR.
    # Sabit bir üst boşluk verilseydi iki maçlık gecede altta kocaman
    # bir delik kalırdı (ölçüldü) — satır sayısı geceden geceye değişiyor.
    parlak, soluk = satirlari_sec(skor_gece)
    satirlar = [(m, False) for m in parlak] + ([(soluk, True)] if soluk else [])
    liste_yuk = sum((42 if sonuk else 46) + 22 for _, sonuk in satirlar) - 22
    ust_sinir = y + 96
    alt_sinir = Y - ALT
    y = ust_sinir + (alt_sinir - ust_sinir - liste_yuk) / 2
    for m, sonuk in satirlar:
        fr, fa = (f_roz_s, f_ad_s) if sonuk else (f_roz, f_ad)
        kutu_zemin = SOLUK_ZEMIN if sonuk else EMBER
        kutu_yazi = SOLUK_YAZI if sonuk else "#0A0603"
        ad_renk = SOLUK_AD if sonuk else INK
        kw, kh = 112, 46 if not sonuk else 42
        ciz.rectangle([KENAR_X, y, KENAR_X + kw, y + kh], fill=kutu_zemin)
        rz = f"{m['rozet']:.1f}"
        rw = _genislik(rz, fr)
        _yaz(ciz, (KENAR_X + (kw - rw) / 2, y + (kh - fr.size) / 2 - 4), rz, fr, kutu_yazi)
        ad = kisa_mac_adi(m["ev"], m["dep"])
        _yaz(ciz, (KENAR_X + kw + 28, y + (kh - fa.size) / 2 - 3), ad, fa, ad_renk, .3)
        y += kh + 22

    # --- alt şerit ---
    ay = Y - ALT
    ciz.line([(KENAR_X, ay), (G - KENAR_X, ay)], fill=CIZGI, width=1)
    sol = f"{dist.get('mac_sayisi', len(skor_gece['maclar']))} maç · sen uyurken oynandı"
    _yaz(ciz, (KENAR_X, ay + 20), sol, f_alt, FAINT, 1.2)
    sw = _genislik(ALAN_ADI, f_alt, 1.2)
    _yaz(ciz, (G - KENAR_X - sw, ay + 20), ALAN_ADI, f_alt, EMBER, 1.2)
    return img


def uret(tarih_str):
    dist = json.loads((KOK / "dist" / f"{tarih_str}.json").read_text(encoding="utf-8"))
    skor = json.loads((KOK / "skor" / f"{tarih_str}.json").read_text(encoding="utf-8"))
    OG_DIZIN.mkdir(exist_ok=True)
    hedef = OG_DIZIN / f"{tarih_str}.png"
    ciz(tarih_str, dist, skor).save(hedef, "PNG", optimize=True)
    print(f"Yazıldı: {hedef} ({hedef.stat().st_size // 1024} KB)")
    return hedef


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Kullanım: python3 og_uret.py YYYY-MM-DD")
    uret(sys.argv[1])
