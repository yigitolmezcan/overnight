"""
bulten.py — yayınlanan gecenin özetini abonelere yollar.

Kullanıcı kuralı: "Mail vitrin, site asıl yer." O yüzden mailde box
score YOK — sadece gecenin tarihi, "30 saniyede gece" satırları,
"Mutlaka bil" başlıkları ve siteye giden bağlantı.

Yayın işinin ARDINDAN çalışır ve `yayin.py yayinla` gerçekten yeni bir
gece yayınladıysa gönderir. Site değişmediyse mail de gitmez (kullanıcı
kuralı) — yoksa aynı gece için ikinci kez mail giderdi.

    python3 bulten.py gonder [--prova adres@ornek.com]

--prova: listeye hiç dokunmadan TEK adrese yollar, kurulum testi için.
"""

import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
from base64 import urlsafe_b64encode
from pathlib import Path

KOK = Path(__file__).resolve().parent
DURUM = KOK / "config" / "yayin_durumu.json"
DIST = KOK / "dist"

# ADRES TEK KAYNAKTAN (bkz. site_adresi.py).
sys.path.insert(0, str(Path(__file__).parent))
from site_adresi import site_adresi
SITE = site_adresi()
GONDEREN = os.environ.get("GONDEREN_ADRES", "OVERNIGHT <onboarding@resend.dev>")
# Cevap adresi: gönderen adresiyle aynı kutu. Gizlilik metninde ve
# koşullarda verdiğimiz iletişim adresi de bu.
CEVAP_ADRES = os.environ.get("CEVAP_ADRESI", "gece@overnightnba.com")
GIZLI = os.environ.get("ABONE_GIZLI_ANAHTAR", "")
RESEND = os.environ.get("RESEND_API_KEY", "")
# Abone listesi depoda DEĞİL (adresler git geçmişine yazılmasın diye) —
# api/_ortak.js ile aynı Upstash kümesinden okunuyor.
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "").rstrip("/")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
REDIS_ANAHTAR = "overnight:aboneler"


def aboneleri_getir():
    """Onaylı abone adresleri (SMEMBERS). Ağ hatası burada YUTULMAZ —
    liste okunamadıysa 'abone yok' diye sessizce geçmek, gönderilmemiş
    bir bülteni başarılı göstermek olurdu."""
    istek = urllib.request.Request(
        REDIS_URL,
        data=json.dumps(["SMEMBERS", REDIS_ANAHTAR]).encode(),
        headers={"Authorization": f"Bearer {REDIS_TOKEN}",
                 "Content-Type": "application/json",
                 "User-Agent": "overnight/1.0 (+https://overnightnba.com)"},
        method="POST",
    )
    with urllib.request.urlopen(istek, timeout=30) as y:
        return json.loads(y.read()).get("result") or []

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _tarih_tr(iso):
    y, a, g = iso.split("-")
    return f"{int(g)} {AYLAR[int(a) - 1]} {y}"


def _cikis_bagi(adres):
    """api/cikis.js ile AYNI token — HMAC(gizli, 'cikis:adres')."""
    tk = hmac.new(GIZLI.encode(), f"cikis:{adres}".encode(), hashlib.sha256).digest()
    e = urlsafe_b64encode(adres.encode()).decode().rstrip("=")
    return f"{SITE}/api/cikis?e={e}&t={urlsafe_b64encode(tk).decode().rstrip('=')}"


def _kacis(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def mail_govdesi(veri, cikis_bag):
    tarih = _tarih_tr(veri["tarih"])
    # DÜZ PARAGRAF, TABLO DEĞİL. Tablo düzeni Gmail'in sınıflandırıcısı
    # için kampanya işareti.
    brief = "".join(
        f'<p style="margin:0 0 9px;font-size:15px;line-height:1.55">{_kacis(b["metin"])}</p>'
        for b in veri.get("brief", [])
    )
    mutlaka = "".join(
        f'<p style="margin:0 0 10px;font-size:15px;line-height:1.55"><strong>{_kacis(m["baslik"])}</strong>'
        + (f'<br><span style="color:#666;font-size:14px">{_kacis(m["mac"])} · {_kacis(m["skor"])}</span>' if m.get("mac") else "")
        + "</p>"
        for m in veri.get("mutlaka", [])
    )
    turk = ""
    for t in veri.get("turkler", []):
        # OYNAMAYAN OYUNCU MAİLE GİRMEZ. Listede kadroda olup sahaya
        # çıkmayan isim de duruyor (sitede "bu gece oynamadı" satırı
        # oluyor) ve istatistik alanları hiç yok — mail üretimi
        # KeyError ile çöküyordu.
        if t.get("oynadi") is False or "pts" not in t:
            continue
        turk += (f'<p style="margin:0 0 6px;font-size:15px"><strong>{_kacis(t["isim"])}</strong> '
                 f'<span style="color:#666">{t["pts"]} sayı · {t["reb"]} ribaund · {t["ast"]} asist</span></p>')

    def _baslik(metin):
        # Turuncu, büyük harf, geniş aralıklı başlık = pazarlama dili.
        # Düz kalın başlık kişisel maile benziyor.
        return f'<p style="margin:22px 0 8px;font-size:15px"><strong>{metin}</strong></p>'

    # Mail HTML'i TAM BİR BELGE olarak kuruluyor:
    #   - <meta charset>: bazı istemciler MIME başlığı yerine belgedeki
    #     bildirimi okuyor; olmayınca Türkçe karakterler bozuluyor.
    #   - Açık zemin AÇIKÇA yazılıyor: zemin tanımlanmazsa koyu temadaki
    #     istemciler (Gmail/Apple Mail karanlık mod) kendi koyu zeminini
    #     koyuyor ve koyu metin okunmaz hâle geliyor.
    #   - color-scheme/supported-color-schemes: istemciye "bu mail açık
    #     temaya göre tasarlandı, ters çevirme" demenin standart yolu.
    #
    # DÜZEN NEDEN SADE: ilk gönderim Gmail'de "Tanıtımlar" sekmesine
    # düştü ve o sekme telefonda BİLDİRİM ÜRETMİYOR — sabah bülteninin
    # bütün anlamı o bildirimde. Kampanya işaretleri kaldırıldı:
    # gri zemin üstünde beyaz çerçeveli kart, turuncu CTA düğmesi,
    # tablo düzeni ve büyük harf turuncu başlıklar. Kalan şey düz bir
    # belge — kişisel bir e-posta neye benziyorsa o.
    return f"""<!doctype html><html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>OVERNIGHT — {tarih}</title>
</head>
<body style="margin:0;padding:20px 16px;background:#FFFFFF;color:#1a1a1a;-webkit-text-size-adjust:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<div style="max-width:560px">
  <p style="margin:0 0 16px;font-size:15px;line-height:1.55">{tarih} gecesi {veri.get('mac_sayisi', 0)} maç oynandı.</p>

  {_baslik("30 saniyede gece") + brief if brief else ''}
  {_baslik("Mutlaka bil") + mutlaka if mutlaka else ''}
  {_baslik("Türkler") + turk if turk else ''}

  <p style="margin:22px 0 26px;font-size:15px">Kutu skorlar ve gecenin tamamı:
    <a href="{SITE}/" style="color:#C2560A">{SITE.replace('https://', '')}</a></p>

  <p style="color:#999;font-size:12px;line-height:1.6;margin:0;border-top:1px solid #E6E8EB;padding-top:12px">
    Bu maili OVERNIGHT'a abone olduğun için alıyorsun.<br>
    <a href="{cikis_bag}" style="color:#999">Abonelikten çık</a>
  </p>
</div>
</body></html>"""


def mail_metni(veri, cikis_bag):
    satir = [f"OVERNIGHT — {_tarih_tr(veri['tarih'])} gecesi",
             f"{veri.get('mac_sayisi', 0)} maç oynandı. Molasız, reklamsız özet.", ""]
    if veri.get("brief"):
        satir += ["30 SANİYEDE GECE"] + [f"- {b['metin']}" for b in veri["brief"]] + [""]
    if veri.get("mutlaka"):
        satir += ["MUTLAKA BİL"] + [f"- {m['baslik']}" for m in veri["mutlaka"]] + [""]
    satir += [f"Gecenin tamamı: {SITE}/", "", f"Abonelikten çık: {cikis_bag}"]
    return "\n".join(satir)


def _resend(kime, konu, html, metin, cikis_bag=None):
    # LIST-UNSUBSCRIBE: Gmail ve Yahoo toplu gönderende bu başlığı ŞART
    # koşuyor; olmayan gönderen spam'e düşüyor. Tek tıkla çıkış
    # (One-Click) için POST biçimi de bildiriliyor. Gövdedeki çıkış
    # bağlantısı yerine geçmiyor, ona EK.
    basliklar = {}
    if cikis_bag:
        basliklar["List-Unsubscribe"] = f"<{cikis_bag}>"
        basliklar["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    # REPLY-TO: cevaplanabilir bir adres olması hem okuyucu için doğru
    # (bir hata görürse yazabilsin) hem de gönderen itibarına olumlu
    # katkı — cevaplanamayan gönderen daha kötü puanlanıyor.
    govde = {"from": GONDEREN, "to": [kime], "subject": konu,
             "reply_to": CEVAP_ADRES, "html": html, "text": metin}
    if basliklar:
        govde["headers"] = basliklar
    istek = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(govde).encode(),
        # User-Agent şart (bkz. uyari.py): Cloudflare varsayılan
        # Python imzasını 403 ile geri çeviriyor.
        headers={"Authorization": f"Bearer {RESEND}",
                 "Content-Type": "application/json",
                 "User-Agent": "overnight/1.0 (+https://overnightnba.com)"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(istek, timeout=30) as y:
            return json.loads(y.read())
    except urllib.error.HTTPError as e:
        # Resend'in mesajını yutma: yalnız HTTP kodu görülünce sebebi
        # anlamak için ayrı koşu gerekiyor (bir kez oldu, 403).
        try:
            neden = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            neden = "(gövde okunamadı)"
        raise RuntimeError(f"Resend HTTP {e.code} — {neden}") from None


def gonder(prova_adresi=None):
    ayarlar = (("RESEND_API_KEY", RESEND), ("ABONE_GIZLI_ANAHTAR", GIZLI),
               ("SITE_ADRESI", SITE),
               ("UPSTASH_REDIS_REST_URL", REDIS_URL),
               ("UPSTASH_REDIS_REST_TOKEN", REDIS_TOKEN))
    eksik = [a for a, v in ayarlar if not v]
    # "Henüz kurulmadı" ile "kurulu ama bozuk" AYRI şeyler.
    # Hiçbiri tanımlı değilse bülten daha kurulmamıştır: bu bir HATA
    # değil, iş başarıyla biter. Aksi halde bülten kurulana kadar her
    # sabah "yayın işi başarısız" bildirimi gider ve gerçek hatalar bu
    # gürültünün içinde kaybolur — site yayınlanmış olmasına rağmen.
    if len(eksik) == len(ayarlar):
        print("Bülten henüz kurulmamış (hiçbir ayar tanımlı değil) — "
              "site yayınlandı, mail gönderilmedi. Kurulum için bkz. KURULUM.md.")
        return 0
    if eksik:
        print(f"Bülten ayarları EKSİK: {', '.join(eksik)} — gönderim yapılmadı. "
              f"Bazı ayarlar tanımlı, bazıları değil; bu bir yapılandırma hatası.")
        return 1

    durum = json.loads(DURUM.read_text(encoding="utf-8"))
    if not durum["yayinlanan"]:
        print("Yayınlanmış gece yok — mail gönderilmiyor.")
        return 0
    tarih = durum["yayinlanan"][-1]

    # Kullanıcı kuralı: site yayınlanmadıysa mail de gitmesin. Aynı gece
    # için ikinci kez gönderim de olmasın.
    son = durum.get("son_bulten")
    if son == tarih and not prova_adresi:
        print(f"{tarih} için bülten zaten gönderilmiş — tekrar gönderilmiyor.")
        return 0

    veri = json.loads((DIST / f"{tarih}.json").read_text(encoding="utf-8"))
    konu = f"OVERNIGHT — {_tarih_tr(tarih)} gecesi"

    if prova_adresi:
        alicilar = [prova_adresi]
        print(f"PROVA: sadece {prova_adresi} adresine gönderiliyor, liste kullanılmıyor.")
    else:
        alicilar = aboneleri_getir()

    if not alicilar:
        print("Onaylı abone yok — gönderilecek kimse yok.")
        return 0

    basarili, basarisiz = 0, []
    for adres in alicilar:
        cikis = _cikis_bagi(adres)
        try:
            _resend(adres, konu, mail_govdesi(veri, cikis),
                    mail_metni(veri, cikis), cikis_bag=cikis)
            basarili += 1
        except Exception as e:
            basarisiz.append(f"{adres}: {e}")

    print(f"Gönderildi: {basarili}/{len(alicilar)}")
    for h in basarisiz:
        print(f"  BAŞARISIZ {h}")

    if not prova_adresi and basarili:
        durum["son_bulten"] = tarih
        DURUM.write_text(json.dumps(durum, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Tek bir adres bile başarısızsa iş BAŞARISIZ biter — kullanıcı
    # kuralı: gönderim başarısız olursa bildirim gelsin.
    return 1 if basarisiz else 0


if __name__ == "__main__":
    prova = None
    if "--prova" in sys.argv:
        prova = sys.argv[sys.argv.index("--prova") + 1]
    raise SystemExit(gonder(prova))
