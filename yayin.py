"""
yayin.py — OVERNIGHT boru hattının 8. adımı: zamanlama ve yayın.

Şartnamedeki plan: "Zamanlanmış görev 08:30 TSİ, yayın 09:00. Hata olursa
e-posta. Ücretsiz barındırma, sunucu yok, veritabanı yok."

İki komut, iki ayrı zamanlanmış iş:

    python3 yayin.py uret      # 08:30 TSİ — sıradaki arşiv gecesini üretir
    python3 yayin.py yayinla   # 09:00 TSİ — hazır geceyi siteye gömer

Neden İKİ adım? 08:30'da üretip 09:00'da yayınlamak arada yarım saatlik
bir tampon bırakıyor. Üretim başarısız olursa 09:00 işi ortada hazır bir
gece bulamaz ve HİÇBİR ŞEY YAPMAZ — site sessizce boşalmaz, bir önceki
gece yayında kalır (kullanıcı kuralı). Tek adımda yapsaydık başarısız bir
üretim doğrudan siteyi etkilerdi.

Durum tek bir dosyada: config/yayin_durumu.json. Veritabanı yok; depo
zaten sürüm geçmişini tutuyor, yayın durumu da oraya commit ediliyor.

Gece seçimi: sezon başından itibaren KRONOLOJİK. Düzeltme turlarında
kullandığımız geceler atlanıyor — o gecelere kurallar defalarca elle
uyduruldu, sistemin gerçek performansını yansıtmıyorlar.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

KOK = Path(__file__).resolve().parent
DURUM_DOSYASI = KOK / "config" / "yayin_durumu.json"
SABLON_HTML = KOK / "overnight_v17.html"
SITE_DIZIN = KOK / "site"
DIST_DIZIN = KOK / "dist"

# Sıradaki geceyi ararken en fazla kaç gün ileri bakılır. NBA takviminde
# maçsız en uzun boşluk All-Star arası (~5 gün); 30 bol bol yeter ve
# sezon bittiğinde döngünün sonsuza gitmesini engeller.
ILERI_BAKMA_SINIRI = 30


def durum_oku():
    return json.loads(DURUM_DOSYASI.read_text(encoding="utf-8"))


def durum_yaz(d):
    DURUM_DOSYASI.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _gun_ekle(tarih_str, n):
    return (datetime.strptime(tarih_str, "%Y-%m-%d") + timedelta(days=n)).strftime("%Y-%m-%d")


def sonraki_gece(d):
    """Yayınlanacak bir sonraki arşiv gecesi, ya da None (sezon bitti).

    Kronolojik olarak ilerler; atlanacaklar listesindeki geceleri ve maç
    oynanmayan günleri geçer. Maç var mı kontrolü SADECE ScoreboardV2'ye
    dokunuyor (ucuz), tam çekim yapmıyor."""
    import cek

    son = d["yayinlanan"][-1] if d["yayinlanan"] else _gun_ekle(d["sezon_baslangici"], -1)
    atla = set(d["atlanan"]) | set(d["yayinlanan"]) | set(d.get("engellenen", []))
    for i in range(1, ILERI_BAKMA_SINIRI + 1):
        aday = _gun_ekle(son, i)
        if aday > d["sezon_bitisi"]:
            return None
        if aday in atla:
            continue
        _, mac_idleri = cek.gece_mac_idlerini_al(aday)
        if mac_idleri:
            return aday
    return None


def _kos(komut, ortam=None):
    """Boru hattı adımını ayrı süreçte çalıştır.

    Ayrı süreç, çünkü adımlar birbirinin modül düzeyi durumunu (üretim
    sayaçları, önbellekler) miras almasın — zamanlanmış işte bir gecenin
    artığı sonrakine sızmamalı."""
    print(f"$ {' '.join(komut)}", flush=True)
    sonuc = subprocess.run(komut, cwd=KOK, env={**os.environ, **(ortam or {})})
    if sonuc.returncode != 0:
        raise RuntimeError(f"Adım başarısız: {' '.join(komut)} (çıkış kodu {sonuc.returncode})")


def uret():
    """08:30 işi — sıradaki geceyi baştan sona üretir ve 'hazır' işaretler."""
    d = durum_oku()
    if d.get("hazir"):
        print(f"Zaten hazır bir gece var ({d['hazir']['tarih']}), yeniden üretilmiyor.")
        return 0

    tarih = sonraki_gece(d)
    if tarih is None:
        print("Sezonda yayınlanacak gece kalmadı.")
        return 0

    print(f"Sıradaki arşiv gecesi: {tarih}")
    py = sys.executable

    _kos([py, "cek.py", tarih])
    _kos([py, "gercekler.py", tarih])
    _kos([py, "hesapla.py", tarih])

    # Kullanıcı kuralı: hibrit varsayılan, günlük tavan aşılırsa o gün
    # şablona düşer. Tavanı yaz.py içindeki tek boğaz noktası uyguluyor
    # (llm_cagir); burada sadece değeri geçiriyoruz. Anahtar yoksa
    # (yerel deneme, secret tanımsız) doğrudan şablon moduna geçiyoruz —
    # yarıda kalan bir üretim yerine bedava ve geçerli bir gece.
    tavan = os.environ.get("GUNLUK_BUTCE_USD", "1.00")
    if os.environ.get("ANTHROPIC_API_KEY"):
        _kos([py, "yaz.py", tarih], ortam={"GUNLUK_BUTCE_USD": tavan})
    else:
        print("ANTHROPIC_API_KEY yok — gece şablon modunda üretiliyor (bedava).")
        _kos([py, "yaz.py", tarih, "--sadece-sablon"])

    _kos([py, "derle.py", tarih])

    taslak = json.loads((KOK / "taslak" / f"{tarih}.json").read_text(encoding="utf-8"))
    kullanim = taslak.get("rapor", {}).get("kullanim", {})
    d["hazir"] = {
        "tarih": tarih,
        "uretildi": datetime.utcnow().isoformat() + "Z",
        "mod": taslak.get("rapor", {}).get("uretim_modu", "bilinmiyor"),
        "maliyet_usd": kullanim.get("toplam_maliyet_usd", 0.0),
        "butce_asildi": bool(kullanim.get("butce_asildi")),
        "sablona_dusen_alan": taslak.get("rapor", {}).get("sablon_moduna_dusen", 0),
    }
    durum_yaz(d)
    print(f"\nHAZIR: {tarih} · mod={d['hazir']['mod']} · maliyet=${d['hazir']['maliyet_usd']:.4f}")
    if d["hazir"]["butce_asildi"]:
        print("UYARI: günlük bütçe tavanına ulaşıldı, gecenin kalanı şablonla üretildi.")
    return 0


def _siteyi_kur(tarih):
    """Tasarım dosyasını alıp o gecenin verisini gömerek site/index.html üretir.

    Tasarım dosyası (overnight_v17.html) DEĞİŞMİYOR — geliştirme kopyası
    olarak duruyor, içinde örnek geceler gömülü. Yayın kopyası ondan
    türetiliyor ve sadece yayındaki geceyi taşıyor (dosya ~185KB yerine
    ~60KB oluyor ve arşiv gecesi seçici kendiliğinden gizleniyor)."""
    sablon = SABLON_HTML.read_text(encoding="utf-8")
    veri = {tarih: json.loads((DIST_DIZIN / f"{tarih}.json").read_text(encoding="utf-8"))}
    gomulu = json.dumps(veri, ensure_ascii=False, separators=(",", ":"))
    yeni, n = re.subn(
        r'(<script id="gomulu-veri" type="application/json">).*?(</script>)',
        lambda m: m.group(1) + gomulu.replace("\\", "\\\\") + m.group(2),
        sablon,
        flags=re.S,
    )
    if n != 1:
        raise RuntimeError(f"Gömülü veri bloğu bulunamadı ({n} eşleşme) — tasarım dosyası bozulmuş.")
    SITE_DIZIN.mkdir(exist_ok=True)
    (SITE_DIZIN / "index.html").write_text(yeni, encoding="utf-8")
    return len(yeni.encode("utf-8"))


# Yayını DURDURAN testler: gerçeğe ve dile dair olanlar. Uzunluk (T6)
# ve benzeri biçim işaretleri raporlanır ama yayını durdurmaz.
#
# Ayrım kasıtlı ve kuralın kendi ifadesinden geliyor: "Doğrulanmamış
# cümle yayına çıkmaz" YANLIŞLIK hakkında, KISALIK hakkında değil.
# Mimarinin ilkesi zaten "sessizlik varsayılan" — kısa kalan bir şablon
# cümlesi doğru davranış, yanlış bir atıf değil. Ayrıca "gecede tek maç
# LLM'e gider" kuralıyla 2. ve 3. Mutlaka bil maçı HER ZAMAN şablondan
# geliyor; uzunluk işareti yayını durdursaydı hiçbir gece çıkamazdı.
ENGELLEYICI_TESTLER = (
    "T1",   # sayı izlenebilirliği
    "T2",   # özel ad izlenebilirliği
    "T3",   # an iddiası
    "T13",  # atıf doğruluğu
    "T14",  # en iyi performans anılmadı
    "T17",  # kaybeden takım oyuncusu cümlenin öznesi
    "T20",  # sezon başı susma kuralı
    "T23",  # mimari kural ihlali
    "T24",  # kilometre taşının sahibi yanlış
)


def yayin_engelleri(tarih):
    """Bu gecenin yayına çıkmasını engelleyen bulgular (boşsa temiz).

    Projenin ilk pazarlıksız kuralı: "Doğrulanmamış cümle yayına çıkmaz."
    Şablon çıktısı üretimde İŞARETLENİYOR ama yine de dosyaya yazılıyor
    ("şablon son çare") — bu, elle gözden geçirilen bir akışta doğruydu.
    Canlı ve kimsenin bakmadığı bir akışta değil: işaretli metin sessizce
    yayına çıkar. O yüzden kapı burada.

    Kapı SADECE 'Mutlaka bil' alanlarına bakıyor — sayfanın en görünür ve
    en iddialı metni orası. Geçilecek maçların tek satırlık şablon
    cümlesinde işaret varsa gece yine de yayınlanır; orada susmak zaten
    kabul edilebilir bir sonuç."""
    taslak = json.loads((KOK / "taslak" / f"{tarih}.json").read_text(encoding="utf-8"))
    isaretli = taslak.get("rapor", {}).get("sablon_isaretli", [])
    engel = []
    for i in isaretli:
        gerekce = " ".join(i.get("gerekce", []))
        vurulan = {t for t in ENGELLEYICI_TESTLER if t + ":" in gerekce or t + "/" in gerekce}
        if vurulan:
            engel.append({**i, "engelleyen": sorted(vurulan)})
    return engel


def yayinla():
    """09:00 işi — hazır gece varsa siteye gömer. Yoksa hiçbir şey yapmaz."""
    d = durum_oku()
    hazir = d.get("hazir")
    if not hazir:
        print("Hazır gece yok — site olduğu gibi kalıyor (bir önceki gece yayında).")
        return 0

    tarih = hazir["tarih"]

    if os.environ.get("YAYIN_KAPISI", "1") != "0":
        engeller = yayin_engelleri(tarih)
        if engeller:
            print(f"YAYINLANMADI: {tarih} — Mutlaka bil metni doğrulamadan geçmedi "
                  f"({len(engeller)} işaretli alan). Site değişmiyor, bir önceki gece yayında.")
            for e in engeller:
                print(f"  - {e.get('mac_id', '?')}: {'; '.join(e.get('gerekce', []))[:200]}")
            d["hazir"] = None
            # 'atlanan'a KARIŞTIRMIYORUZ: atlanan = bilerek emekli
            # edilmiş geceler, engellenen = doğrulamadan geçemediği için
            # ertelenmiş geceler. Ayrı durunca, bütçe ya da bir kural
            # değiştiğinde engellenenler topluca geri alınabilir
            # (`python3 yayin.py engelleri_temizle`).
            d["engellenen"] = sorted(set(d.get("engellenen", [])) | {tarih})
            d["son_engel"] = {"tarih": tarih, "sebep": engeller,
                              "zaman": datetime.utcnow().isoformat() + "Z"}
            durum_yaz(d)
            # Çıkış kodu 0: bu bir ÇÖKME değil, kuralın çalışması. İş
            # başarısız sayılırsa her sabah "hata" e-postası gelir ve
            # gerçek hatalar bu gürültünün içinde kaybolur.
            return 0

    boyut = _siteyi_kur(tarih)
    d["yayinlanan"].append(tarih)
    d["hazir"] = None
    d["son_yayin"] = {**hazir, "yayinlandi": datetime.utcnow().isoformat() + "Z"}
    durum_yaz(d)
    print(f"YAYINDA: {tarih} · site/index.html {boyut:,} bayt · toplam {len(d['yayinlanan'])} gece")
    return 0


def durum():
    d = durum_oku()
    print(f"Yayınlanan gece sayısı : {len(d['yayinlanan'])}")
    print(f"Doğrulamada takılan    : {len(d.get('engellenen', []))}")
    engel = d.get("son_engel")
    if engel:
        print(f"Son takılan gece       : {engel['tarih']} (Mutlaka bil doğrulamadan geçmedi)")
    print(f"Şu an yayında          : {d['yayinlanan'][-1] if d['yayinlanan'] else '(henüz yok)'}")
    print(f"Üretilmiş, bekliyor    : {d['hazir']['tarih'] if d.get('hazir') else '(yok)'}")
    print(f"Atlanan (ayarlı) gece  : {len(d['atlanan'])}")
    son = d.get("son_yayin")
    if son:
        print(f"Son yayın              : {son['tarih']} · {son['mod']} · ${son.get('maliyet_usd', 0):.4f}")
    return 0


def engelleri_temizle():
    """Doğrulamada takılan geceleri yeniden sıraya al.

    Bütçe tavanı ya da bir dil kuralı değiştiğinde, o yüzden takılmış
    geceler tekrar denenebilsin diye. Bilerek emekli edilen geceler
    (`atlanan`) bundan etkilenmez."""
    d = durum_oku()
    kac = len(d.get("engellenen", []))
    d["engellenen"] = []
    d["son_engel"] = None
    durum_yaz(d)
    print(f"{kac} gece yeniden sıraya alındı.")
    return 0


KOMUTLAR = {
    "uret": uret,
    "yayinla": yayinla,
    "durum": durum,
    "sonraki": lambda: print(sonraki_gece(durum_oku())) or 0,
    "engelleri_temizle": engelleri_temizle,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in KOMUTLAR:
        print(f"Kullanım: python3 yayin.py [{' | '.join(KOMUTLAR)}]")
        raise SystemExit(1)
    raise SystemExit(KOMUTLAR[sys.argv[1]]())
