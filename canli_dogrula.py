"""canli_dogrula.py — yayın işinin SON adımı: site gerçekten değişti mi?

Neden ayrı bir adım: 27 Ağustos 2026'da yayın işi kusursuz koştu, 21
Aralık'ı depoya yazdı, "success" dedi — ve site 20 Aralık'ta kaldı.
Vercel bot yazarlı commit'in dağıtımını reddediyordu (TEAM_ACCESS_REQUIRED)
ve bunu kimse görmedi, çünkü bütün denetimler DEPOYA bakıyordu.

Depo "yayınlandı" diyorsa yeterli değil; ölçüt OKUYUCUNUN GÖRDÜĞÜ sayfa.
Bu betik canlı siteyi çekip gömülü verideki tarihi okuyor ve beklenen
geceyle karşılaştırıyor.

Kullanım: python3 canli_dogrula.py <beklenen-tarih> [url]
Çıkış kodu 1 = site beklenen geceyi göstermiyor.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request

VARSAYILAN_URL = "https://overnight-yigit8.vercel.app/"
# Vercel dağıtımı birkaç dakika sürebiliyor; tek atışta "olmadı" demek
# yanlış alarm üretir. Toplam ~5 dakika bekleniyor.
DENEME = 10
DENEME_ARASI_SN = 30
ZAMAN_ASIMI_SN = 20

_GOMULU_DESENI = re.compile(
    r'<script id="gomulu-veri" type="application/json">(.*?)</script>', re.S)


def canli_tarih(url):
    """Sitenin ŞU AN gösterdiği gecenin tarihi, okunamazsa None."""
    istek = urllib.request.Request(url, headers={"User-Agent": "overnight-denetim"})
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as cevap:
        sayfa = cevap.read().decode("utf-8", "replace")
    eslesme = _GOMULU_DESENI.search(sayfa)
    if not eslesme:
        return None
    veri = json.loads(eslesme.group(1))
    if not veri:
        return None
    return sorted(veri.keys())[-1]


def dogrula(beklenen, url=VARSAYILAN_URL, deneme=DENEME, ara=DENEME_ARASI_SN):
    son_gorulen = None
    for i in range(1, deneme + 1):
        try:
            son_gorulen = canli_tarih(url)
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as hata:
            son_gorulen = f"okunamadı ({type(hata).__name__})"
        if son_gorulen == beklenen:
            print(f"CANLI: {url} → {beklenen} ({i}. denemede)")
            return True
        print(f"  {i}/{deneme}: site {son_gorulen!r}, beklenen {beklenen!r}")
        if i < deneme:
            time.sleep(ara)
    print(f"CANLIYA ÇIKMADI: depo {beklenen!r} diyor, site {son_gorulen!r} gösteriyor.")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Kullanım: python3 canli_dogrula.py <beklenen-tarih> [url]")
    hedef = sys.argv[1]
    adres = sys.argv[2] if len(sys.argv) > 2 else VARSAYILAN_URL
    raise SystemExit(0 if dogrula(hedef, adres) else 1)
