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

# Şablona düşme alarmı için (bkz. uret): eşik ve hesap tek yerde durur.
import yaz

KOK = Path(__file__).resolve().parent
DURUM_DOSYASI = KOK / "config" / "yayin_durumu.json"
SABLON_HTML = KOK / "overnight_v17.html"
SITE_DIZIN = KOK / "site"
DIST_DIZIN = KOK / "dist"

# Sıradaki geceyi ararken en fazla kaç gün ileri bakılır. NBA takviminde
# maçsız en uzun boşluk All-Star arası (~5 gün); 30 bol bol yeter ve
# sezon bittiğinde döngünün sonsuza gitmesini engeller.
ILERI_BAKMA_SINIRI = 30

# Kullanıcı kuralı: bu sayıdan az maç oynanan ARŞİV gecesi yayınlanmaz.
# Gerekçe ürünün kendi vaadi: "10 maç oynandı, üçünü bilmen yeter."
# Tek maçlık bir sayfa gece özeti değil, tek bir maç raporu — triyaj
# yapacak bir şey yok. Gerçek sezona geçildiğinde bu eşik 0'a çekilecek:
# o zaman gece ne ise o yayınlanır, çünkü okuyucu zaten o geceyi merak
# ederek geliyor.
ASGARI_MAC_SAYISI = 3

# İki mod var, durum dosyasındaki "mod" alanı seçiyor:
#
#   "arsiv" — geçmiş sezondan KRONOLOJİK gece. Sıra imleciyle ilerler,
#             3'ten az maçlı geceleri atlar, emekli geceleri atlar.
#             Sezon başlayana kadarki mod.
#
#   "canli" — DÜN GECE. Sıra yok, atlama yok: o gece kaç maç oynandıysa
#             yayınlanır (kullanıcı kuralı — okuyucu zaten o geceyi
#             merak ederek geliyor, triyaj vaadi tek maçta da geçerli).
#             Maç oynanmadıysa hiçbir şey yapılmaz, önceki gece kalır.
#
# Sezon başı susma kuralı İKİ MODDA DA aynı çalışır: o kural veri
# katmanında (gercekler.sezon_guvenilir), burada bir karşılığı yok.
MOD_ARSIV, MOD_CANLI = "arsiv", "canli"

# Türkiye yıl boyu UTC+3 (yaz saati yok). İş 05:30 UTC'de koşuyor, yani
# 08:30 TSİ — o saatte bir önceki NBA gecesi çoktan bitmiş oluyor.
TSI_FARKI_SAAT = 3


def durum_oku():
    return json.loads(DURUM_DOSYASI.read_text(encoding="utf-8"))


def durum_yaz(d):
    DURUM_DOSYASI.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _gun_ekle(tarih_str, n):
    return (datetime.strptime(tarih_str, "%Y-%m-%d") + timedelta(days=n)).strftime("%Y-%m-%d")


def dun_gece():
    """Canlı modun hedefi: TSİ'ye göre dünün tarihi.

    NBA maçları ABD akşamı oynanıp TSİ'nin sabaha karşısında biter; iş
    08:30 TSİ'de koştuğu için "dün" doğru gecedir. Hesap UTC'den
    değil TSİ'den yapılıyor — koşucu UTC'de ve gün sınırına yakın
    saatlerde ikisi ayrışabilir."""
    tsi = datetime.utcnow() + timedelta(hours=TSI_FARKI_SAAT)
    return (tsi - timedelta(days=1)).strftime("%Y-%m-%d")


def sonraki_gece(d):
    """Yayınlanacak bir sonraki arşiv gecesi, ya da None (sezon bitti).

    Kronolojik olarak ilerler; atlanacaklar listesindeki geceleri ve maç
    oynanmayan günleri geçer. Maç var mı kontrolü SADECE ScoreboardV2'ye
    dokunuyor (ucuz), tam çekim yapmıyor."""
    import cek

    if d.get("mod") == MOD_CANLI:
        # Canlı mod: sıra yok, dün gece. Zaten yayınlandıysa tekrar
        # üretilmez (iş gün içinde ikinci kez tetiklenirse diye).
        aday = dun_gece()
        if aday in d["yayinlanan"]:
            return None
        _, mac_idleri = cek.gece_mac_idlerini_al(aday)
        if not mac_idleri:
            print(f"  {aday}: maç oynanmamış — yayın yok, önceki gece kalıyor.")
            return None
        # Maç eşiği UYGULANMAZ (kullanıcı kuralı): gece ne ise o.
        print(f"  {aday}: {len(mac_idleri)} maç (canlı mod, eşik uygulanmıyor)")
        return aday

    # Sıra imlecinden ilerler, "en son yayınlanan"dan DEĞİL. İkisi
    # normalde aynı; ayrıldıkları tek durum VİTRİN gecesi: sırayla
    # ilgisi olmayan, elle seçilmiş bir gece yayınlandığında (ör. site
    # ilk kez paylaşılırken dolu bir gece istendi) imleç yerinde kalır
    # ve ertesi gün kronoloji kaldığı yerden devam eder.
    son = d.get("sira_imleci") or (d["yayinlanan"][-1] if d["yayinlanan"] else _gun_ekle(d["sezon_baslangici"], -1))
    atla = set(d["atlanan"]) | set(d["yayinlanan"]) | set(d.get("engellenen", []))
    # VERİSİ ÇEKİLEMEYEN GECE SİSTEMİ DURDURMAZ (kullanıcı kuralı).
    # NBA servisi GitHub koşucusunu IP bazlı engelliyor; bir geceye
    # ulaşılamayınca eskiden bütün iş çöküyor ve sıra ORADA duruyordu.
    # Artık o gece atlanıp bir sonrakine geçiliyor, atlananlar da
    # `ulasilamayan` listesinde toplanıp çağırana bildiriliyor.
    ulasilamayan = []
    for i in range(1, ILERI_BAKMA_SINIRI + 1):
        aday = _gun_ekle(son, i)
        if aday > d["sezon_bitisi"]:
            break
        if aday in atla:
            continue
        # ÖNCE DEPODAKİ VERİ. Ham veri elimizdeyse NBA'e hiç sorulmuyor —
        # servis GitHub koşucusunu engellediği için o çağrı orada zaten
        # düşüyor ve gece boşuna atlanıyordu. Yerelden çekilip depoya
        # konmuş bir gece koşucudan sorunsuz üretilebilmeli.
        yerel = cek.ham_yolu(aday, KOK)
        if yerel is not None:
            try:
                mac_idleri = list(cek.ham_oku(aday, KOK).get("maclar") or {})
            except Exception as hata:
                ulasilamayan.append((aday, f"ham okunamadı: {type(hata).__name__}"))
                continue
            if len(mac_idleri) >= ASGARI_MAC_SAYISI:
                if ulasilamayan:
                    d["_ulasilamayan"] = ulasilamayan
                return aday
            print(f"  {aday}: {len(mac_idleri)} maç (depodan) — eşiğin altında, atlanıyor.")
            continue
        try:
            _, mac_idleri = cek.gece_mac_idlerini_al(aday)
        except Exception as hata:
            # Ağ/engel hatası. Gece BAŞARISIZ diye işaretlenmiyor —
            # veri yarın gelebilir; sadece bu koşuda atlanıyor.
            ulasilamayan.append((aday, f"{type(hata).__name__}: {str(hata)[:80]}"))
            print(f"  {aday}: veri alınamadı ({type(hata).__name__}) — atlanıyor.")
            continue
        if len(mac_idleri) >= ASGARI_MAC_SAYISI:
            if ulasilamayan:
                d["_ulasilamayan"] = ulasilamayan
            return aday
        if mac_idleri:
            print(f"  {aday}: {len(mac_idleri)} maç — eşiğin ({ASGARI_MAC_SAYISI}) altında, atlanıyor.")
    # Hiçbir aday bulunamadı. SEBEP ÖNEMLİ: sezon gerçekten bitti mi,
    # yoksa hiçbirine ulaşamadık mı? İkisi aynı şey değil ve aynı
    # sessizlikle geçilemez.
    if ulasilamayan:
        d["_ulasilamayan"] = ulasilamayan
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
    ulasilamayan = d.pop("_ulasilamayan", [])
    if ulasilamayan:
        # SESSİZ KALMIYOR: atlanan geceler kayda geçiyor. Bir gecenin
        # verisine ulaşılamaması normal bir "gece yok" durumu DEĞİL,
        # altyapı arızası — bildirilmezse sıra sessizce eriyor.
        print(f"UYARI: {len(ulasilamayan)} gecenin verisine ulaşılamadı, atlandı:")
        for gun, sebep in ulasilamayan:
            print(f"  - {gun}: {sebep}")

    if tarih is None:
        if ulasilamayan:
            # Sezon bitmedi; hiçbir geceye ULAŞILAMADI. İki durum
            # birbirine karıştırılamaz.
            print("ÜRETİLECEK GECE BULUNAMADI — sebep veri erişimi, sezon sonu değil.")
            return 3
        print("Sezonda yayınlanacak gece kalmadı.")
        return 0

    print(f"Sıradaki arşiv gecesi: {tarih}")
    py = sys.executable

    # HAM VERİ ZATEN DEPODAYSA NBA'E HİÇ GİDİLMİYOR.
    # 52 gecelik ham veri tam da bunun için gzipli olarak depoya
    # konmuştu; ama bu adım koşulsuz `cek.py` çağırıyordu ve koşucu her
    # gece NBA'e gidiyordu. NBA, GitHub'ın (Azure) IP bloğunu engelliyor:
    # istek ReadTimeout'a düşüyor, dört deneme de başarısız oluyor ve
    # gece hiç üretilmiyor — depoda o gecenin verisi hazır dururken.
    # Ölçüldü (29 Ağustos, gerçek koşu): 2025-12-23 için iki üretim
    # denemesi de `scoreboard 2025-12-23: 4 denemede de alınamadı` ile
    # düştü, oysa ham/2025-12-23.json.gz depoda duruyordu.
    # Geçit `cek.ham_yolu`: .json, .json.gz ve test kopyasını birden
    # tanıyor — üretimin başka yerlerinde kullanılan geçidin aynısı.
    import cek as _cek
    if _cek.ham_yolu(tarih) is not None:
        print(f"Ham veri depoda hazır ({_cek.ham_yolu(tarih).name}) — NBA'e gidilmiyor.")
    else:
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

    # ŞABLONA DÜŞME ALARMI (kullanıcı kuralı): "Sessizce şablona düşmek
    # kabul edilebilir bir sonuç değil." Mutlaka bil maçlarının yarısından
    # fazlası şablona düştüyse iş BAŞARISIZ. Gece 'hazır' olarak
    # işaretlenmiş halde kalıyor — üretim boşa gitmesin, kararı insan
    # versin; ama iş kırmızı yanıyor ve atanmış issue açılıyor.
    alarm, oran, mesaj = yaz.sablon_alarmi(taslak.get("rapor") or {})
    print(mesaj)
    if alarm:
        # ÇIKIŞ KODU 2, 1 DEĞİL. Üretim işi ağ hatasına karşı üç kez
        # deniyor; 1 dönseydi döngü tekrar denerdi, `uret` ikinci turda
        # "zaten hazır gece var" deyip 0 dönerdi ve alarm sessizce
        # yutulurdu. 2 = "tekrar deneme, işi düşür".
        print("ÜRETİM BAŞARISIZ SAYILIYOR — LLM metni yayına çıkmıyor.")
        return 2
    return 0


def _siteyi_kur(tarih, kok_da=True):
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

    # PAYLAŞIM ÖNİZLEMESİ. Tarama botları JS koşturmuyor, o yüzden meta
    # etiketleri HTML'in içine yazılıyor ve her gecenin kendi dosyası
    # oluyor (/2025-12-22). Paylaşılan link o gecenin görselini gösteriyor.
    og_gorsel = _og_uret(tarih)
    yeni = _meta_doldur(yeni, tarih, veri[tarih], og_gorsel)

    SITE_DIZIN.mkdir(exist_ok=True)
    # Hem son gece (kök) hem kendi adresi. cleanUrls açık: 2025-12-22.html
    # dosyası /2025-12-22 adresinden servis ediliyor (bkz. vercel.json).
    if kok_da:
        (SITE_DIZIN / "index.html").write_text(yeni, encoding="utf-8")
    (SITE_DIZIN / f"{tarih}.html").write_text(yeni, encoding="utf-8")
    # Yayınlanmakta olan gece duruma HENÜZ yazılmamış olabilir; listeye
    # onu da katıyoruz (bkz. _gunleri_yaz).
    _gunleri_yaz(ayrica=tarih)
    return len(yeni.encode("utf-8"))


SITE_ADRESI = "https://overnight-yigit8.vercel.app"


def arsiv_sayfalari():
    """Yayınlanmış HER gecenin kendi sayfasını yeniden kurar.

    Oklar gecelerin arasında geziyor; sayfası olmayan bir geceye giden
    ok 404 verir. Bu komut geriye dönük eksikleri kapatıyor ve tasarım
    değiştiğinde bütün arşivi tazeliyor. Kök (index.html) SON gecede
    kalıyor — arşiv sayfaları onu ezmiyor."""
    d = durum_oku()
    gunler = sorted(set(d.get("yayinlanan") or []))
    son = (d.get("yayinlanan") or [None])[-1]
    kuruldu, atlanan = [], []
    for t in gunler:
        if not (DIST_DIZIN / f"{t}.json").exists():
            atlanan.append(t)
            continue
        _siteyi_kur(t, kok_da=(t == son))
        kuruldu.append(t)
    print(f"Arşiv sayfası: {len(kuruldu)} gece kuruldu"
          + (f", {len(atlanan)} atlandı (dist yok): {atlanan}" if atlanan else ""))
    return kuruldu


def _og_uret(tarih):
    """og/{tarih}.png üretir ve site/og/ altına kopyalar.

    Üretim başarısız olursa yayın DURMUYOR: görselsiz bir gece,
    yayınlanmamış bir geceden iyidir. Hata kayda geçiyor."""
    try:
        import og_uret
        kaynak = og_uret.uret(tarih)
        hedef_dizin = SITE_DIZIN / "og"
        hedef_dizin.mkdir(parents=True, exist_ok=True)
        (hedef_dizin / kaynak.name).write_bytes(kaynak.read_bytes())
        return f"/og/{kaynak.name}"
    except Exception as hata:
        print(f"UYARI: paylaşım görüntüsü üretilemedi ({type(hata).__name__}: {hata})")
        return ""


def _meta_doldur(html, tarih, dist, og_gorsel):
    """og:/twitter: etiketlerini bu geceye göre doldurur."""
    from derle import _tarih_tr
    baslik = f"OVERNIGHT — {_tarih_tr(tarih)} gecesi"
    mac = dist.get("mac_sayisi") or 0
    aciklama = f"Konuşan box score. {mac} maç oynandı."
    adres = f"{SITE_ADRESI}/{tarih}"
    gorsel = f"{SITE_ADRESI}{og_gorsel}" if og_gorsel else ""
    degerler = {
        "og:title": baslik, "twitter:title": baslik,
        "og:description": aciklama, "twitter:description": aciklama,
        "og:url": adres, "og:image": gorsel, "twitter:image": gorsel,
    }
    for ad, deger in degerler.items():
        nitelik = "name" if ad.startswith("twitter:") else "property"
        desen = rf'(<meta {nitelik}="{re.escape(ad)}" content=")[^"]*(">)'
        html, sayi = re.subn(desen, lambda m: m.group(1) + _kacir(deger) + m.group(2), html, count=1)
        if sayi != 1:
            raise RuntimeError(f"Meta etiketi bulunamadı: {ad}")
    # <title> de geceye göre — sekmede ve paylaşımda aynı ad görünsün.
    html = re.sub(r"<title>.*?</title>", f"<title>{_kacir(baslik)}</title>", html, count=1, flags=re.S)
    return html


def _kacir(metin):
    return (str(metin).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def _gunleri_yaz(ayrica=None):
    """site/gunler.json — yayınlanmış gecelerin listesi.

    Oklar bu dosyayı okuyor. Liste sayfaların İÇİNDE olsaydı yeni gece
    çıktığında bütün eski sayfaların yeniden yazılması gerekirdi.

    `ayrica`: HENÜZ duruma yazılmamış ama yayınlanmakta olan gece.
    SIRALAMA KUSURUYDU: `yayinla` önce `_siteyi_kur` çağırıyor (o da
    burayı çağırıyor), duruma eklemeyi SONRA yapıyordu. Liste o anda
    yayınlanan geceyi henüz içermiyor, dosya eksik yazılıyor ve gece
    arşivde hiç görünmüyordu — "sonraki gece ›" oku ona ulaşamıyordu.
    Ölçüldü: 22 Aralık'ta da, 23 Aralık'ta da liste geceyi atladı."""
    d = durum_oku()
    gunler = sorted(set((d.get("yayinlanan") or []) + ([ayrica] if ayrica else [])))
    SITE_DIZIN.mkdir(exist_ok=True)
    (SITE_DIZIN / "gunler.json").write_text(
        json.dumps(gunler, ensure_ascii=False), encoding="utf-8")
    return gunler


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
    "T26",  # karar anı oyuncu adı olmadan anıldı
    "T27",  # "Mağlup tarafta" gece kuralı (GECE kapsamlı)
)


def _ham_metni(tarih):
    """Ham veri — tam kopya varsa o, yoksa depodaki kırpılmış kopya.

    `ham/` depoya girmiyor (gece başına ~19MB) ve yayın işi ayrı bir
    koşucuda checkout'la başlıyor: orada tam ham HİÇ yok. Kırpılmış kopya
    (cek.py üretiyor, ~250KB) doğrulamanın okuduğu blokları taşıyor, o
    yüzden kapı canlıda da yerelde olduğu gibi çalışıyor."""
    import cek
    return cek.ham_metni(tarih, KOK)


def _isaretleri_tazele(tarih, isaretli):
    """Şablona düşmüş alanların gerekçelerini GÜNCEL kurallarla yeniden
    hesaplar. Kural değişince eski rapor yanlış karar verdiriyordu."""
    if not isaretli:
        return isaretli
    try:
        import dogrula as _dog
        from kalip_secici import gece_maglup_izni
        gercek_gece = json.loads((KOK / "gercek" / f"{tarih}.json").read_text(encoding="utf-8"))
        ham = json.loads(_ham_metni(tarih))
        skor_gece = json.loads((KOK / "skor" / f"{tarih}.json").read_text(encoding="utf-8"))
    except Exception as e:
        # Eski raporla devam — kapı GEVŞEMEZ (donmuş gerekçe kalır, en
        # fazla haksız yere bloke eder). Ama sessiz kalmıyor: bu satır
        # olmadan "kural yerelde var, üretimde yok" farkı görünmezdi.
        print(f"UYARI: {tarih} doğrulaması tazelenemedi ({e}) — "
              f"üretim anındaki gerekçelerle devam ediliyor.")
        return isaretli
    yasakli = _dog.yasakli_yukle()
    izin = gece_maglup_izni(gercek_gece["maclar"])
    en_iyi = {m["mac_id"]: m.get("en_iyi_performans") for m in skor_gece["maclar"]}
    yeni = []
    for i in isaretli:
        gid = i.get("mac_id")
        if gid not in gercek_gece["maclar"]:
            yeni.append(i)
            continue
        sonuc = _dog.mac_metnini_dogrula(
            i.get("metin", {}), gercek_gece["maclar"][gid], ham["maclar"][gid], 0,
            yasakli, en_iyi_performans=en_iyi.get(gid), sablon=True,
            maglup_izinli_ad=izin.get(gid),
        )
        gerekce = list(sonuc.get("gerekce", []))
        for alan, ad in sonuc.get("alanlar", {}).items():
            for test, (gecti, detay) in ad.get("testler", {}).items():
                if not gecti:
                    gerekce.append(f"{alan}/{test}: {detay}")
        if gerekce:
            yeni.append({**i, "gerekce": gerekce})
    return yeni


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
    # Rapordaki gerekçeler ÜRETİM ANINDA dondu. Bir kural o günden sonra
    # değiştiyse (18 Aralık: T14 daraltıldı) kapı artık geçerli olmayan
    # bir gerekçeyle geceyi bloke ediyordu. "Hangi alan şablona düştü"
    # bilgisi metinden geri hesaplanamaz — o rapordan gelir; ama
    # gerekçeler HER ZAMAN güncel kurallarla yeniden üretilir.
    isaretli = _isaretleri_tazele(tarih, isaretli)
    engel = []
    for i in isaretli:
        gerekce = " ".join(i.get("gerekce", []))
        vurulan = {t for t in ENGELLEYICI_TESTLER if t + ":" in gerekce or t + "/" in gerekce}
        if vurulan:
            engel.append({**i, "engelleyen": sorted(vurulan)})
    engel.extend(_gece_kapsamli_engeller(tarih, taslak))
    return engel


def _gece_kapsamli_engeller(tarih, taslak):
    """GECE kapsamlı kurallar (şu an T27) — bir maça değil gecenin
    TAMAMINA bakan kurallar.

    Boşluk: kapı yalnızca `sablon_isaretli`e bakıyordu, yani maç bazlı
    doğrulama sonuçlarına. Gece kapsamlı bir ihlal (aynı kalıbın iki
    maçta kullanılması) hiçbir maçın raporunda görünmediği için kapıdan
    sessizce geçiyordu — LLM'in yazdığı cümleler için hiç uygulanmıyordu."""
    # DİKKAT: burada `gece_dogrula` ÇAĞIRMIYORUZ, çünkü o ham veri
    # istiyor ve `ham/` depoda YOK (gece başına ~20MB, .gitignore'da).
    # Yayın işi ayrı bir koşucuda checkout'la başlıyor; ham orada hiç
    # oluşmuyor. gece_dogrula çağırsaydık her yayında sessizce istisnaya
    # düşer ve T27 canlıda HİÇ çalışmazdı — kural yerelde var, üretimde
    # yok. T27'nin ham'a ihtiyacı yok: taslak + gerçekler yetiyor.
    try:
        from dogrula import t27_maglup_gece_kurali
        from kalip_secici import gece_maglup_izni
        gercek_gece = json.loads((KOK / "gercek" / f"{tarih}.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    t27 = t27_maglup_gece_kurali(taslak, gece_maglup_izni(gercek_gece["maclar"]))
    if t27.get("gecti", True):
        return []
    return [{
        "mac_id": ", ".join(t27.get("maclar", [])),
        "alan": "gece",
        "gerekce": [f"T27: 'Mağlup tarafta' kalıbı {len(t27.get('maclar', []))} maçta "
                    f"kullanıldı; hakkı olmayan maçlar: {t27.get('izinsiz') or 'yok'}"],
        "engelleyen": ["T27"],
    }]


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
    # Vitrin gecesi sırayı ilerletmez — kronoloji kaldığı yerden devam eder.
    if not hazir.get("vitrin"):
        d["sira_imleci"] = tarih
    d["hazir"] = None
    d["son_yayin"] = {**hazir, "yayinlandi": datetime.utcnow().isoformat() + "Z"}
    durum_yaz(d)
    print(f"YAYINDA: {tarih} · site/index.html {boyut:,} bayt · toplam {len(d['yayinlanan'])} gece")
    return 0


def tazele():
    """Yayındaki geceyi yeniden derleyip siteyi güncelle — sıra ilerlemez.

    Bir yapılandırma ya da tasarım değişikliği (ör. Türk oyuncu listesi)
    yayındaki gecenin metnini de etkilediğinde gerekiyor: `yayinla`
    sıradaki geceye geçerdi, oysa istenen aynı gecenin tazelenmesi."""
    d = durum_oku()
    if not d["yayinlanan"]:
        print("Yayında gece yok — tazelenecek bir şey yok.")
        return 0
    tarih = d["yayinlanan"][-1]
    # Gerçek hata: tazele SADECE dist'i sayfaya gömüyordu, dist'i yeniden
    # DERLEMİYORDU. Taslak metni değiştikten (yeni kural, yeniden üretim)
    # sonra "tazele" eski metni sessizce yeniden yayınlıyordu — adı
    # tazeleme, işi kopyalama. Derleme burada.
    _kos([sys.executable, "derle.py", tarih])
    boyut = _siteyi_kur(tarih)
    print(f"TAZELENDİ: {tarih} · site/index.html {boyut:,} bayt")
    return 0


def durum():
    d = durum_oku()
    print(f"Mod                    : {d.get('mod', MOD_ARSIV)}")
    print(f"Yayınlanan gece sayısı : {len(d['yayinlanan'])}")
    print(f"Doğrulamada takılan    : {len(d.get('engellenen', []))}")
    engel = d.get("son_engel")
    if engel:
        print(f"Son takılan gece       : {engel['tarih']} (Mutlaka bil doğrulamadan geçmedi)")
    print(f"Şu an yayında          : {d['yayinlanan'][-1] if d['yayinlanan'] else '(henüz yok)'}")
    print(f"Sıra imleci            : {d.get('sira_imleci') or '(sezon başı)'}")
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


def mod_degistir(yeni_mod=None):
    """Arşiv ↔ canlı geçişi. Sezon başlayınca tek komut:
    `python3 yayin.py canli`"""
    d = durum_oku()
    eski = d.get("mod", MOD_ARSIV)
    d["mod"] = yeni_mod
    durum_yaz(d)
    print(f"Mod: {eski} → {yeni_mod}")
    if yeni_mod == MOD_CANLI:
        print(f"Sıradaki hedef: {dun_gece()} (dün gece)")
        print("Maç sayısı eşiği artık uygulanmıyor; sıra imleci kullanılmıyor.")
        print()
        print("DİKKAT — zamanlayıcıyı da güncelle:")
        print("  .github/workflows/uret.yml içindeki '0 2' ve '0 4' cron")
        print("  satırları ARŞİV modu içindir (05:00 ve 07:00 TSİ). Canlı")
        print("  modda o saatte maçlar bitmemiş olur; ikisini sil, geriye")
        print("  '30 5' (08:30 TSİ) kalsın ve telafi için '0 6' ile '30 6'")
        print("  eklensin.")
    else:
        print(f"Sıra imlecinden devam edecek: {d.get('sira_imleci')}")
    return 0


KOMUTLAR = {
    "uret": uret,
    "canli": lambda: mod_degistir(MOD_CANLI),
    "arsiv": lambda: mod_degistir(MOD_ARSIV),
    "yayinla": yayinla,
    "durum": durum,
    "sonraki": lambda: print(sonraki_gece(durum_oku())) or 0,
    "engelleri_temizle": engelleri_temizle,
    "tazele": tazele,
    # DİKKAT: "arsiv" adı ZATEN mod değiştirmede kullanılıyor; sayfa
    # kurma komutu ayrı adla duruyor, yoksa mod komutunu sessizce ezerdi.
    "sayfalar": arsiv_sayfalari,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in KOMUTLAR:
        print(f"Kullanım: python3 yayin.py [{' | '.join(KOMUTLAR)}]")
        raise SystemExit(1)
    raise SystemExit(KOMUTLAR[sys.argv[1]]())
