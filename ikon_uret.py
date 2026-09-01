"""OVERNIGHT simgesi — üretici. `python3 ikon_uret.py` beş dosyayı da
sayfalar/ altına yeniden yazar. Tasarım değişirse buradan üretilir,
elle çizilmiş dosya yok.

OVERNIGHT simgesi — gece topu (referans C bloğu).

32x32'lik SVG ile AYNI geometri, PIL ile çiziliyor. 8 kat büyütüp
küçülterek kenar yumuşatma sağlanıyor (PIL'in kendi arc/ellipse'i
kenar yumuşatmıyor).
"""
import math
from PIL import Image, ImageDraw

ZEMIN = (10, 13, 18)          # #0A0D12
DURAK = [(0.00, (26, 34, 48)),   # #1A2230  alt / gece
         (0.45, (46, 42, 36)),   # #2E2A24
         (1.00, (232, 118, 58))] # #E8763A  üst / şafak
K = 8                          # süper örnekleme katsayısı

def _renk(t):
    t = max(0.0, min(1.0, t))
    for i in range(1, len(DURAK)):
        p0, c0 = DURAK[i - 1]; p1, c1 = DURAK[i]
        if t <= p1:
            k = (t - p0) / (p1 - p0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return DURAK[-1][1]

def ciz(boyut, yuvarlat=True):
    B = boyut * K
    s = B / 32.0                      # 32 birimlik tuvalden piksele
    im = Image.new("RGB", (B, B), ZEMIN)
    d = ImageDraw.Draw(im)

    # --- top: dikey degradeli daire ---
    # Degrade dairenin kendi kutusunda: alt (y=27) t=0, üst (y=5) t=1.
    ust, alt = 5 * s, 27 * s
    grad = Image.new("RGB", (1, B), ZEMIN)
    gp = grad.load()
    for y in range(B):
        gp[0, y] = _renk((alt - y) / (alt - ust)) if ust <= y <= alt else _renk(
            1.0 if y < ust else 0.0)
    grad = grad.resize((B, B))
    maske = Image.new("L", (B, B), 0)
    ImageDraw.Draw(maske).ellipse([5 * s, 5 * s, 27 * s, 27 * s], fill=255)
    im.paste(grad, (0, 0), maske)

    # --- dikiş: TEK dikey çizgi (yatay çizgi yok) ---
    # 1.6/32 kalınlık 16px'te 0.8 piksele düşüyor ve küçültmede eriyor
    # (ölçüldü: 16px'te dikişle top arasındaki ayrım 19, görünmüyor).
    # Küçük boyutlarda taban kalınlık: son görüntüde en az 1.25 piksel.
    kalinlik = max(1, round(1.6 * s), round(1.25 * K))
    d.line([(16 * s, 5 * s), (16 * s, 27 * s)], fill=ZEMIN, width=kalinlik)

    # --- iki yan kavis ---
    # Yarıçap 15, uçlar (8.2,8.2)-(8.2,23.8). Merkez kirişten
    # sqrt(15² - 7.8²) = 12.8125 uzakta.
    dx = math.sqrt(15 ** 2 - 7.8 ** 2)
    aci = math.degrees(math.atan2(7.8, dx))
    for merkez_x, bas, bit in ((8.2 - dx, -aci, aci),
                               (23.8 + dx, 180 - aci, 180 + aci)):
        kutu = [(merkez_x - 15) * s, (16 - 15) * s, (merkez_x + 15) * s, (16 + 15) * s]
        d.arc(kutu, bas, bit, fill=ZEMIN, width=kalinlik)

    # --- köşe yuvarlatma (sadece favicon; uygulama simgeleri tam kare,
    #     işletim sistemi kendi maskesini uyguluyor) ---
    if yuvarlat:
        yuv = Image.new("L", (B, B), 0)
        ImageDraw.Draw(yuv).rounded_rectangle([0, 0, B - 1, B - 1],
                                              radius=4 * s, fill=255)
        dis = Image.new("RGB", (B, B), ZEMIN)
        dis.paste(im, (0, 0), yuv)
        im = dis
    return im.resize((boyut, boyut), Image.LANCZOS)


def hepsini_uret(hedef="sayfalar"):
    """favicon.svg dışındaki dört dosyayı üretir (SVG kaynak dosya)."""
    import io as _io, struct
    from pathlib import Path
    h = Path(hedef)
    for ad, b in (("apple-touch-icon.png", 180), ("icon-192.png", 192),
                  ("icon-512.png", 512)):
        # ANA EKRAN SİMGELERİ TAM KARE: işletim sistemi kendi maskesini
        # uyguluyor, içeride yuvarlatırsak köşe iki kez kesiliyor.
        ciz(b, yuvarlat=False).save(h / ad)
        print(f"  {ad}  {b}x{b}")
    # ICO'yu ELLE kuruyoruz: PIL tek görüntüden küçültüyor ve 16px'te
    # dikiş eriyor (ölçüldü, ayrım 49 yerine 16). Her boyut kendi
    # çiziminden.
    boyutlar = (16, 32, 48)
    pngler = []
    for n in boyutlar:
        b = _io.BytesIO(); ciz(n, yuvarlat=True).save(b, format="PNG")
        pngler.append(b.getvalue())
    bas = struct.pack("<HHH", 0, 1, len(boyutlar))
    ofset = 6 + 16 * len(boyutlar)
    girdiler = b""
    for n, veri in zip(boyutlar, pngler):
        girdiler += struct.pack("<BBBBHHII", n, n, 0, 0, 1, 32, len(veri), ofset)
        ofset += len(veri)
    (h / "favicon.ico").write_bytes(bas + girdiler + b"".join(pngler))
    print("  favicon.ico  16/32/48")


if __name__ == "__main__":
    hepsini_uret()
