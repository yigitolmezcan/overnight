"""
dogrula.py — OVERNIGHT boru hattının 5. adımı.

Girdi:  taslak/{tarih}.json (yaz.py çıktısı) + gerçek/{tarih}.json + ham/{tarih}.json
Çıktı:  kabul / ret + gerekçe (her metin alanı için)

Şartname bölüm 5'teki T1-T8 testlerini birebir uygular. Bir metin alanı
(baslik, neden_onemli, ozet, gec_satiri, brief metni) bu testlerden
BİRİNİ bile geçemezse reddedilir.

Bu modül `yaz.py`'den (6. adım, henüz yazılmadı) ÖNCE test edildi —
dil kılavuzundaki elle doğrulanmış örnek gece metni (bkz.
overnight-dil-kilavuzu-ve-ornek-gece.md) `dogrula_gece_dosyasi.py`
betiğiyle taslak biçimine çevrilip buradan geçirildi; hepsi kabul etti.
Kasten bozulmuş cümleler de ayrıca test edildi; hepsi reddedildi.
Bkz. o test betiğinin çıktısı — bu dosyanın kendisi test verisi
taşımaz, sadece kuralları uygular.
"""

import json
import re
import unicodedata
from pathlib import Path

from gercekler import clock_saniye, OLAGANUSTU_KILOMETRE_ESIKLERI

GERCEK_DIZIN = Path(__file__).parent / "gercek"
HAM_DIZIN = Path(__file__).parent / "ham"
SKOR_DIZIN = Path(__file__).parent / "skor"
TASLAK_DIZIN = Path(__file__).parent / "taslak"
CONFIG_DIZIN = Path(__file__).parent / "config"

# ---------------------------------------------------------------------------
# T1 — Sayı izlenebilirliği
# ---------------------------------------------------------------------------

# Basketbolun sabit zaman kelimeleri — bir "gerçek" değil, kuralın kendisi
# (çeyrek 12 dakika, "son 5 dakika" / "son 2 dakika" clutch pencereleri).
# Bunlar her zaman serbest, hangi maç olursa olsun aynı.
YAPISAL_GUVENLI_SAYILAR = {"2", "5", "12"}


def sayilari_cikar(metin):
    # Kullanıcı düzeltmesi: "Philadelphia 76ers" gibi bir takım adındaki
    # "76" T1'e çıplak bir sayı iddiası gibi görünüyordu (gerçek üretim
    # bug'ı — "76ers"/"Sixers" diye anılan Philadelphia, hiç kaybetmediği
    # bir "76" istatistiği "uydurmuş" gibi reddediliyordu). Bir rakam
    # dizisi HEMEN ARDINDAN bir harfle devam ediyorsa (boşluksuz, "76ers"
    # gibi) bu bir istatistik değil, özel adın PARÇASI — negative
    # lookahead ile dışlanıyor. Gerçek istatistikler her zaman boşluk/
    # noktalama ile biter ("150-129", "23 sayı" gibi), bu değişmiyor.
    return re.findall(r"\d+(?:[.,]\d+)?(?!\w)", metin)


# Bu alanlar "X/Y" biçiminde (isabet/deneme) — iki tarafı da ayrı ayrı
# alıntılanabilir olmalı ("10/20 saha" gibi), o yüzden parçalanıyor.
BOLUNECEK_ALANLAR = {"fg", "uc", "sut", "isabet", "uclu", "serbest"}


def tum_alan_degerlerini_topla(gercekler):
    """Her gerçeğin `veri` sözlüğündeki tüm sayısal alan değerlerini
    toplar. Dize alanlar KENDİ BÜTÜNÜYLE geçerli (örn. "15-20" derece
    dizesi metinde birebir öyle geçmeli), ama İÇİNDEKİ SAYILARA rastgele
    bölünmez — ilk denemede bu yüzden gerçek bir hata çıktı: "dk": "33:45"
    gibi bir dakika damgası, uydurma bir "45 sayı" iddiasını yanlışlıkla
    geçerli kılıyordu. Sadece BOLUNECEK_ALANLAR'daki "X/Y" isabet
    alanları bilerek ikiye bölünüyor, çünkü oralarda her iki taraf da
    (isabet VE deneme sayısı) ayrı ayrı gerçek bir alıntı olabilir."""
    degerler = set()

    def gez(anahtar, deger):
        if isinstance(deger, bool):
            return
        if isinstance(deger, (int, float)):
            degerler.add(str(deger))
            if isinstance(deger, float) and deger == int(deger):
                degerler.add(str(int(deger)))
        elif isinstance(deger, str):
            degerler.add(deger)
            if anahtar in BOLUNECEK_ALANLAR:
                degerler.update(re.findall(r"\d+", deger))
        elif isinstance(deger, dict):
            for k, v in deger.items():
                gez(k, v)
        elif isinstance(deger, list):
            for v in deger:
                gez(None, v)

    for g in gercekler:
        for k, v in g.get("veri", {}).items():
            gez(k, v)
    return degerler


def turetilmis_sayilar(gercekler):
    """T1 beyaz listesi: iki skorun farkı, çeyrek toplamları, derece
    dizeleri. "Çeyrek toplamları" tek bir sabit çift (yarılar) değil —
    ilk denemede sadece 1+2. ve 3+4. çeyreği topluyordum, ama "sonraki
    iki çeyrekte toplam 38" gibi bir cümle 2+3. çeyreği (ortadaki iki
    çeyrek) topluyor. Bunu genel tuttuk: mevcut periyotların ARDIŞIK
    HER ikili ve üçlü kombinasyonunun toplamı beyaz listede."""
    turetilmis = set()
    ev_ceyrek, dep_ceyrek = {}, {}
    for g in gercekler:
        if g["tur"] == "ceyrek":
            p = g["veri"]["periyot"]
            ev_ceyrek[p] = g["veri"]["ev_ceyrek_sayisi"]
            dep_ceyrek[p] = g["veri"]["dep_ceyrek_sayisi"]

    periyotlar = sorted(ev_ceyrek.keys())
    for uzunluk in (2, 3):
        for i in range(len(periyotlar) - uzunluk + 1):
            pencere = periyotlar[i : i + uzunluk]
            if pencere != list(range(pencere[0], pencere[0] + uzunluk)):
                continue  # ardışık olmayan periyotları atla (örn. uzatma arası)
            turetilmis.add(str(sum(ev_ceyrek[p] for p in pencere)))
            turetilmis.add(str(sum(dep_ceyrek[p] for p in pencere)))

    # "an" gerçeklerinin saati ("saat": "PT00M04.70S" gibi ISO 8601 süre
    # biçiminde) kalan saniyeye çevrilip beyaz listeye ekleniyor. Bu
    # olmadan "4.7 saniye kala" gibi TAM DOĞRU bir alıntı (gerçek
    # play-by-play'den, Giannis'in 4.7 saniye kalayken attığı alley-oop
    # smacı) sırf "4.7" hiçbir alanda literal olarak durmadığı için
    # reddediliyordu — saat verisi bir ISO 8601 dizesinin içinde,
    # hesaplanmadan okunamıyor.
    for g in gercekler:
        if g["tur"] == "an" and "saat" in g.get("veri", {}):
            saniye = clock_saniye(g["veri"]["saat"])
            turetilmis.add(str(saniye))
            turetilmis.add(f"{saniye:.1f}")
            turetilmis.add(str(int(saniye)))

    return turetilmis


# "60+" gibi bir eşik ETİKETİ (bkz. gercekler.TARIHSEL_BAGLAM /
# sezon_sikligi_baglam_uret'in "tur" alanı) çıplak bir istatistik
# iddiası DEĞİL, KATEGORİ adı — model bunu "60+ sayı eşiğini ondan
# önce NBA tarihinde sadece 38 oyuncu geçmişti" gibi TALİMATLA
# istenen bir cümlede kullanıyor (bkz. sistem promptu). Hemen
# ardından "+" gelen bir sayı HER ZAMAN eşik etiketidir, gerçek bir
# oyuncu istatistiği asla "+" ile yazılmaz — T1'den muaf.
ESIK_ETIKETI_DESENI = re.compile(r"\d+(?:[.,]\d+)?(?=\+)")


def t1_sayi_izlenebilirligi(metin, gercekler):
    gecerli = tum_alan_degerlerini_topla(gercekler) | turetilmis_sayilar(gercekler) | YAPISAL_GUVENLI_SAYILAR
    esik_etiketleri = set(ESIK_ETIKETI_DESENI.findall(metin))
    sorunlu = [sayi for sayi in sayilari_cikar(metin) if sayi not in gecerli and sayi not in esik_etiketleri]
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T2 — Özel ad izlenebilirliği
# ---------------------------------------------------------------------------

# Cümle başında büyük harfle başlayan ama isim OLMAYAN, sık geçen
# kelimeler. Tam bir Türkçe ayrıştırıcı değiliz — bu kaba liste, test
# ettiğimiz örnek metinlerdeki yanlış pozitifleri gidermek için
# genişletildi ve genişlemeye açık.
ISIM_DISI_BUYUK_HARFLI = {
    "Bu", "Ama", "Ve", "O", "Maç", "Takım", "Son", "İlk", "İkinci",
    "Üçüncü", "Dördüncü", "Gecenin", "Sonunda", "Sonra", "Ancak",
    "Fakat", "Yine", "Böylece", "Batı", "Doğu", "Ligin", "Sezon",
    "Sezonun", "Neden", "Önemli", "Baştan", "İddiasız", "Maçın",
    "Iddiasiz", "Spurs",
    # "NBA" — gercekler.py'nin OLAĞANÜSTÜ kilometre gerçeklerine eklenen
    # "baglam" alanı ("NBA tarihinde sadece bir avuç oyuncu...") modelin
    # bu kelimeyi AYNEN kullanması talimatıyla veriliyor (bkz. sistem
    # promptu) — sabit, doğrulanabilir bir lig adı, oyuncu/takım gibi
    # kaynağa ihtiyaç duyan bir özel ad değil.
    "NBA",
    # Yapısal lig terimleri (oyuncu/takım adı değil):
    "Konferans", "Konferansı", "Konferansı'nın", "Konferansın",
    # Cümle başında rastgele büyük harfli, isim OLMAYAN sık kelimeler —
    # retorik soru-cevap gibi üsluplarda ("...yetti mi? Hayır.") ortaya
    # çıkıyor. Genel bir cümle-sınırı farkındalığı yerine gözlenen
    # örnekler elle eklendi.
    "Hayır", "Evet",
}


def _ascii_katla(s):
    """Aksan/özel harfleri ASCII'ye indirger — 'Dončić' -> 'Doncic'.
    Türkçe metin için KULLANILMAZ (ı/ş/ğ/ü/ö/ç burada kaybolur), sadece
    yabancı oyuncu adlarının olası ASCII yazımını da geçerli saymak
    için — modelin "Dončić" yerine "Doncic" yazması gerçek bir üretim
    bug'ı olarak görüldü, isim listede yoktu diye reddedildi."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _kelime_varyantlarini_ekle(kelimeler, kelime):
    temiz = kelime.strip(".,'’")
    adaylar = {temiz}
    # OZEL_AD_REGEX apostrofta duruyor (Türkçe iyelik ekini ayırmak
    # için, bkz. o fonksiyonun docstring'i) — ama "De'Aaron" gibi
    # apostrofu isminin PARÇASI olan oyuncularda bu yüzden regex ismi
    # İKİYE bölüyor: "De" ve "Aaron". İlk sürüm sadece apostroftan
    # ÖNCEKİ kökü ekliyordu ("De") — ama "Day'Ron Sharpe" gibi bir
    # isimde SONRAKİ parça da ("Ron") ayrı bir aday kelime olarak
    # regex'e yakalanıyor ve listede yoksa yanlış pozitif üretiyor
    # (gerçek üretim bug'ı). Her iki parçayı da eklemek gerekiyor.
    for ayrac in ("'", "’"):
        if ayrac in temiz:
            for parca in temiz.split(ayrac):
                if parca:
                    adaylar.add(parca)
    for aday in list(adaylar):
        adaylar.add(_ascii_katla(aday))
    kelimeler.update(adaylar)


def gecerli_isim_kelimeleri(gercekler, ham_mac):
    kelimeler = set()
    for g in gercekler:
        if g["tur"] in ("oyuncu_stat", "kadro_disi"):
            for kelime in g["veri"]["oyuncu"].split():
                _kelime_varyantlarini_ekle(kelimeler, kelime)
    bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    for taraf in ("homeTeam", "awayTeam"):
        ad = bt[taraf]["teamCity"] + " " + bt[taraf]["teamName"]
        for kelime in ad.split():
            _kelime_varyantlarini_ekle(kelimeler, kelime)
        kelimeler.add(bt[taraf]["teamTricode"])
    return kelimeler


# `[^\W\d_]` = Unicode harf (rakam/altçizgi hariç \w) — Türkçe'ye özgü
# karakter listesi elle yazmak yerine bunu kullanıyoruz, yoksa "Dončić"
# gibi Türkçe alfabesinde olmayan bir harf (č) taşıyan isimler yarıda
# kesiliyordu ("Don" olarak yakalanıp yanlış pozitif üretiyordu).
# Apostrof \w'ye dahil değil, o yüzden regex "Zion'un" → "Zion",
# "Batı'da" → "Batı" gibi Türkçe iyelik/hâl eklerinde doğal olarak
# duruyor. Tire dahil edildi — "Gilgeous-Alexander" tek aday olarak
# yakalanmalı. Büyük harfle başlama kontrolü regex yerine Python'da
# yapılıyor (Unicode-farkında `str.isupper()` daha güvenilir).
OZEL_AD_REGEX = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")


def t2_ozel_ad_izlenebilirligi(metin, gercekler, ham_mac):
    """Cümle BAŞINDAKİ büyük harfli kelime özel ad kontrolüne girmez —
    Türkçede her cümle büyük harfle başlar, bu yüzden "Hayır.", "Ev
    sahibi...", "Favori..." gibi sıradan kelimeler isim sanılıp gecenin
    en çok okunan bölümünü (brief satırları) şablona düşürüyordu. Üç
    kez aynı türde yanlış pozitif elle stopword'e eklendi — kalıcı
    çözüm cümle sınırını tanımak. Cümle İÇİNDE geçen büyük harfli bir
    kelime hâlâ tam güçle kontrol ediliyor; gerçek özel adlar zaten
    metin boyunca birden fazla yerde geçer, sadece cümle başında
    kalmaz."""
    gecerli = gecerli_isim_kelimeleri(gercekler, ham_mac)
    cumleler = cumlelere_ayir(metin)

    sorunlu = []
    for cumle in cumleler:
        if not cumle.strip():
            continue
        kelimeler = OZEL_AD_REGEX.findall(cumle)
        for i, kelime in enumerate(kelimeler):
            if i == 0:
                continue  # cümle başı — kontrol dışı
            if kelime[0].isupper() and kelime not in gecerli and kelime not in ISIM_DISI_BUYUK_HARFLI:
                sorunlu.append(kelime)
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T3 — An iddiası
# ---------------------------------------------------------------------------

AN_KALIP_REGEX = re.compile(
    r"son saniye|son hücum|galibiyet basketi|uzatmaya götüren|bitime \d+ saniye",
    re.IGNORECASE,
)


def t3_an_iddiasi(metin, gercekler):
    if not AN_KALIP_REGEX.search(metin):
        return (True, None)

    an_gercekleri = [g for g in gercekler if g["tur"] == "an"]
    if not an_gercekleri:
        return (False, "an iddiası var ama hiç 'an' gerçeği yok")

    periyotlar = [g["veri"]["periyot"] for g in gercekler if "periyot" in g.get("veri", {})]
    son_periyot = max(periyotlar, default=4)

    for g in an_gercekleri:
        if g["veri"]["periyot"] >= son_periyot and clock_saniye(g["veri"]["saat"]) <= 120:
            return (True, None)

    return (False, "an iddiası var ama son 2 dakikada 'an' gerçeği yok")


# ---------------------------------------------------------------------------
# T4 — Yasaklı ifade
# ---------------------------------------------------------------------------


def yasakli_yukle():
    ham = json.loads((CONFIG_DIZIN / "yasakli.json").read_text())
    # Şartname T4'ü başlangıçta sadece klişeler + yapay zekâ tikleriyle
    # tanımlamıştı. Sonradan eklendi: karşılığı olan İngilizce terimler
    # ("dunk" gibi), fiil şişirmesi kökleri ("kaydet-" gibi — artık ÇIPLAK
    # KÖK, "kaydetti" gibi sabit çekim değil, çünkü "Holmgren 15 ribaund
    # kaydetti" hiçbir testten geçmeden yayına çıkmıştı ve tek bir çekimi
    # yasaklamak yetersizdi) ve register listesi ("suretiyle" gibi resmi
    # yazışma dili kalıntıları). Çok-kelimeli, araya ek kelime girebilen
    # kalıplar (bkz. "kok_kaliplari") ayrı bir regex testinde (T4d).
    return (
        ham["klise"] + ham["yapay_zeka_tiki"] + ham["ingilizce_terim"]
        + ham["fiil_sismesi"] + ham.get("register", [])
    )


def yasakli_kok_kaliplari_yukle():
    ham = json.loads((CONFIG_DIZIN / "yasakli.json").read_text())
    return [
        (kalip["aciklama"], re.compile(kalip["desen"], re.IGNORECASE))
        for kalip in ham.get("kok_kaliplari", [])
    ]


def t4_yasakli_ifade(metin, yasakli_liste):
    metin_kucuk = metin.lower()
    bulunan = [ifade for ifade in yasakli_liste if ifade.lower() in metin_kucuk]
    return (len(bulunan) == 0, bulunan or None)


def t4d_kok_kaliplari(metin):
    bulunan = []
    for aciklama, desen in yasakli_kok_kaliplari_yukle():
        for eslesme in desen.finditer(metin):
            bulunan.append(f"'{eslesme.group(0)}' ({aciklama})")
    return (len(bulunan) == 0, bulunan or None)


# ---------------------------------------------------------------------------
# Konferans adı özel ad — "Doğu"/"Batı" büyük harfle başlamalı
# ---------------------------------------------------------------------------
#
# Gerçek üretim hatası: "ikisi de doğu'da 9-8 sıradaydı" — konferans adı
# (Doğu Konferansı / Batı Konferansı) özel ad, küçük harfle başlayamaz.

KONFERANS_ADI_REGEX = re.compile(r"\b(doğu|batı)\b", re.IGNORECASE)


def t4f_konferans_ozel_ad(metin):
    bulunan = [
        m.group(0)
        for m in KONFERANS_ADI_REGEX.finditer(metin)
        if not m.group(0)[0].isupper()
    ]
    return (len(bulunan) == 0, bulunan or None)


# ---------------------------------------------------------------------------
# Takım kodu yasağı — okuyucuya sadece tam şehir/takım adı çıkar, kod
# (MIL, CHA gibi) asla. Kadro/gerçek verisinde kod dolaşır ama metne
# sızmamalı.
# ---------------------------------------------------------------------------

NBA_TAKIM_KODLARI = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
    "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
}

TAKIM_KODU_REGEX = re.compile(r"\b[A-ZÇĞİÖŞÜ]{3}\b")


def t4e_takim_kodu(metin):
    bulunan = [k for k in TAKIM_KODU_REGEX.findall(metin) if k in NBA_TAKIM_KODLARI]
    return (len(bulunan) == 0, bulunan or None)


# ---------------------------------------------------------------------------
# İngilizce kalacak terimlerin varyantları — "üçlü-dublsü" gibi
# ---------------------------------------------------------------------------
#
# Not: karakter-benzerliğine dayalı genel bir bulanık eşleştirme burada
# İŞE YARAMAZ — "üçlü-dubl" ile "triple-double" harf düzeyinde neredeyse
# hiç ortak karakter taşımıyor (biri Türkçe kökten, biri İngilizce),
# SequenceMatcher gibi bir araç ikisini benzemez bulur. Gerçek benzerlik
# harflerde değil, ÇEVİRİDE — "üçlü" triple'ın, "dubl/çift" double'ın
# çevirisi olduğu için birleşimleri "triple-double"ın bozuk bir çevirisi
# oluyor. O yüzden burada her korunan terim için, o terimi Türkçeye
# çevirmeye çalışan BİLİNEN kalıpları arıyoruz — genel bir benzerlik
# skoru değil, hedefli bir desen listesi.
TERIM_VARYANT_DESENLERI = {
    "triple-double": re.compile(
        r"üçlü[\s-]?(dubl\w*|dabıl\w*|çift\w*)|tripıl\s*dabıl\w*|üç\s*lü\s*çift\w*",
        re.IGNORECASE,
    ),
    "double-double": re.compile(
        r"çift[\s-]?çift\w*|dabıl[\s-]?dabıl\w*|dubl[\s-]?dubl\w*",
        re.IGNORECASE,
    ),
    "alley-oop": re.compile(r"sokak\s*arası\s*(top|basket)|ara\s*sokak", re.IGNORECASE),
    "pick and roll": re.compile(r"seç\s*ve\s*yuvarlan|al\s*ve\s*yuvarlan|perdele[a-zçğıöşü]*\s*ve\s*yuvarlan", re.IGNORECASE),
    "play-in": re.compile(r"oyuna\s*giriş\s*(turu|maçı)?", re.IGNORECASE),
    "garbage time": re.compile(r"çöp\s*zaman", re.IGNORECASE),
}


def t4b_terim_varyanti(metin):
    bulunan = []
    for terim, desen in TERIM_VARYANT_DESENLERI.items():
        for eslesme in desen.finditer(metin):
            bulunan.append(f"'{eslesme.group(0)}' ({terim} yerine İngilizce hâliyle yazılmalı)")
    return (len(bulunan) == 0, bulunan or None)


# ---------------------------------------------------------------------------
# "Puan" — sadece "puan durumu" bağlamında serbest, oyuncu/takım sayısı
# için her zaman yasak ("sayı" kullanılmalı — bkz. dil kılavuzu).
# ---------------------------------------------------------------------------

PUAN_ISTISNA_REGEX = re.compile(r"puan\s+durum\w*", re.IGNORECASE)
PUAN_KOK_REGEX = re.compile(r"\bpuan\w*", re.IGNORECASE)


def t4c_puan_baglami(metin):
    temiz = PUAN_ISTISNA_REGEX.sub("", metin)
    bulunan = PUAN_KOK_REGEX.findall(temiz)
    return (len(bulunan) == 0, bulunan or None)


# ---------------------------------------------------------------------------
# Fiil çekimi — duyulan/aktarılan geçmiş zaman (-mış) yasak
# ---------------------------------------------------------------------------

DUYULAN_GECMIS_REGEX = re.compile(
    r"\b[^\W\d_]+(mış|miş|muş|müş)\b", re.IGNORECASE
)


def t_fiil_cekimi(metin):
    """Duyulan geçmiş zaman ("-mış") yasak — her cümle doğrulanmış bir
    kayıttan geliyor, "bana söylendi" izlenimi veren bir çekime yer yok.
    Bilinen geçmiş zaman ("-dı") zorunlu."""
    sorunlu = [m.group(0) for m in DUYULAN_GECMIS_REGEX.finditer(metin)]
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# Türkçe karakter düşürme — "mağlubiyet" yerine "maglubiyet"
# ---------------------------------------------------------------------------
#
# Modeller ğ/ş/ı/ç/ö/ü harflerini düşürmeye eğilimli — bir kere gerçek
# üretimde gördük ("maglubiyetini"), tekrar edecek. Sık geçen spor
# terimleri için BOZUK (Türkçe karaktersiz) hâli metinde geçiyorsa
# reddediyoruz — doğru yazılmış hâl (içinde gerçek ğ/ş/ı/ç/ö/ü olan)
# bu kontrole hiç takılmıyor.
TURKCE_TERIM_KOKLERI = [
    "mağlubiyet", "mağlup", "galibiyet", "ribaund", "asist",
    "çeyrek", "üçlük", "sayı",
]
_TR_ASCII_DONUSUM = str.maketrans("ğşıçöüĞŞİÇÖÜ", "gsicouGSICOU")


def t_turkce_yazim(metin):
    sorunlu = []
    for kok in TURKCE_TERIM_KOKLERI:
        bozuk_kok = kok.translate(_TR_ASCII_DONUSUM)
        if bozuk_kok == kok:
            continue  # kökte düşecek özel karakter yok, kontrol gereksiz
        desen = re.compile(rf"\b{re.escape(bozuk_kok)}[^\W\d_]*", re.IGNORECASE)
        for m in desen.finditer(metin):
            bulunan = m.group(0)
            if any(c in bulunan for c in "ğşıçöüĞŞİÇÖÜ"):
                continue  # aslında doğru yazılmış, yanlış pozitif önlendi
            sorunlu.append(bulunan)
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T5 — Kazanan
# ---------------------------------------------------------------------------


def t5_kazanan(tum_metin, gercekler, ham_mac):
    skor = next((g for g in gercekler if g["tur"] == "skor"), None)
    if skor is None:
        return (False, "skor gerçeği yok")
    kazanan_kod = skor["veri"]["kazanan"]
    bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    isimler = [kazanan_kod]
    for taraf in ("homeTeam", "awayTeam"):
        if bt[taraf]["teamTricode"] == kazanan_kod:
            isimler += [bt[taraf]["teamCity"], bt[taraf]["teamName"]]
    bulundu = any(isim in tum_metin for isim in isimler)
    return (bulundu, None if bulundu else f"kazanan ({kazanan_kod}) metinde geçmiyor")


# ---------------------------------------------------------------------------
# T6 — Uzunluk
# ---------------------------------------------------------------------------

FIIL_SONEKLERI = (
    "dı", "di", "du", "dü", "tı", "ti", "tu", "tü",
    "yor", "acak", "ecek", "mış", "miş", "muş", "müş",
    "ır", "ir", "ur", "ür", "er", "ar", "kaldı", "aldı", "verdi",
)


def kelime_say(metin):
    return len(metin.split())


# NBA oyuncu adlarında sık geçen kısaltmalar — "Porter Jr." gibi bir isim,
# sonundaki nokta cümle sonu sanılıp ikiye bölünmesin diye korunuyor.
CUMLE_SONU_OLMAYAN_KISALTMALAR = ("Jr", "Sr", "St", "vs", "örn", "bkz")


def cumlelere_ayir(metin):
    """Metni cümlelere ayırır. Dört hata bulundu ve düzeltildi:
    1. "4.7 saniye kala" gibi bir ondalık sayı, içindeki nokta yüzünden
       İKİ cümle sayılıyordu ("4" ve "7 saniye kala" diye bölünüyordu).
    2. "Porter Jr. 'ın pasından..." gibi bir isim sonundaki kısaltma
       noktası da cümle sonu sanılıyordu.
    3. İlk iki düzeltmenin yan etkisi: "(?<!\\d)" koşulu SADECE önünde
       rakam olan noktaları değil, "111-99. Sonraki cümle" gibi normal
       bir cümle sonu noktasını da (sayıyla biten her cümle!) atlıyordu
       — oysa ondalık sayı olması için noktanın hem ÖNÜNDE hem
       ARDINDA rakam olması gerekir, sadece önünde değil. Bu, T2'nin
       cümle-başı muafiyetini bozuyordu: sayıyla biten her cümleden
       sonraki kelime hâlâ "cümle içi" sayılıp yanlışlıkla özel ad
       kontrolüne giriyordu.
    4. Gerçek üretim bug'ı (dogrula.py --hepsi denetimi yakaladı): "1.
       çeyrekte 11 sayı üstünlük kuran..." gibi bir SIRA SAYISI ("1.",
       "3. periyotta" gibi) hem önü hem ardı rakam olmadığı için 1-2
       koşuluna girmiyordu, YANLIŞLIKLA cümle sonu sayılıp metni "1" ve
       "çeyrekte..." diye ikiye bölüyordu — dört gerçek cümlelik bir
       metin "5 cümle" görünüp T6'dan (uzunluk) yanlışlıkla reddediliyordu.
       Türkçede bir sıra sayısının ARDINDAN KÜÇÜK harfle devam etmesi
       (gerçek cümle başları büyük harfle başlar) aynı cümlenin sürdüğünü
       gösterir — bu durumda da nokta cümle sonu sayılmaz."""
    korunmus = metin.strip()
    for kisaltma in CUMLE_SONU_OLMAYAN_KISALTMALAR:
        korunmus = re.sub(rf"\b{kisaltma}\.", kisaltma + "\x00", korunmus)

    parcalar = []
    son = 0
    for m in re.finditer(r"[.!?]+", korunmus):
        onceki = korunmus[m.start() - 1] if m.start() > 0 else ""
        sonraki = korunmus[m.end()] if m.end() < len(korunmus) else ""
        if onceki.isdigit() and sonraki.isdigit():
            continue  # gerçek ondalık sayı ("4.7") — cümle sonu değil
        if onceki.isdigit():
            sonraki_kelime = korunmus[m.end():m.end() + 30].lstrip()
            if sonraki_kelime and sonraki_kelime[0].islower():
                continue  # sıra sayısı ("1. çeyrekte") — cümle sonu değil
        parcalar.append(korunmus[son : m.start()])
        son = m.end()
    parcalar.append(korunmus[son:])

    return [p.replace("\x00", ".").strip() for p in parcalar if p.strip()]


def cumle_say(metin):
    return len(cumlelere_ayir(metin))


# Alan başına ASGARİ kelime sayısı — gerçek üretim bug'ı: t6_uzunluk
# SADECE üst sınır kontrol ediyordu, boş bir metin ("") her üst sınırı
# vakumsal olarak geçiyordu (0 <= sınır her zaman doğru) ve hiçbir
# başka test (T1-T19) boş metinde ihlal bulamadığı için TAMAMEN BOŞ
# alanlar "kabul" görüp yayına çıktı (11 gecelik toplu üretimde
# onlarca maç). Şablon modunun var olma sebebi buydu — boş üretim
# ASLA sessizce geçmemeli, reddedilip şablona düşmeli.
ASGARI_KELIME = {
    "baslik": 3, "neden_onemli": 3, "ozet": 55, "ozet_kisa": 30, "gec_satiri": 4, "brief_metin": 3,
}


def t6_uzunluk(alan_adi, metin, sablon=False):
    """`sablon=True` → ALT sınırlar denetlenmez, ÜST sınırlar denetlenir.

    Kullanıcı kuralı: "55-75 kelime kuralı şablona uygulanmasın. O kural
    sadece LLM çıktısı için — şablon kendi doğal uzunluğunda kalsın."
    Gerekçe mimaride zaten var: şablon katmanının varsayılanı SUSMAK.
    Söyleyecek doğrulanmış olgusu yoksa iki cümlede bırakması DOĞRU
    davranış; alt sınır onu olmayan bir olguyu uydurmaya zorlardı. Üst
    sınırlar (başlık 10 kelime, telefon ekranı) şablonda da geçerli —
    onlar uydurma değil, taşma kuralı.
    """
    asgari = 1 if sablon else ASGARI_KELIME.get(alan_adi, 1)
    if kelime_say(metin) < asgari:
        return False, f"boş/çok kısa metin ({kelime_say(metin)} kelime, asgari {asgari})"
    if not metin.strip():
        return False, "boş metin"
    if alan_adi == "brief_metin":
        return kelime_say(metin) <= 12, None
    if alan_adi == "baslik":
        tek_satir = "\n" not in metin.strip()
        son_kelime = re.sub(r"[.!?]+$", "", metin.strip()).split()[-1].lower()
        fiil_var = any(son_kelime.endswith(ek) for ek in FIIL_SONEKLERI)
        # Telefon ekranı kuralı (kullanıcı kararı): başlık en fazla 10
        # kelime, kaydırma gerektirmemeli.
        kisa = kelime_say(metin) <= 10
        gecti = tek_satir and fiil_var and kisa
        if gecti:
            return True, None
        sorunlar = []
        if not tek_satir:
            sorunlar.append("tek satır değil")
        if not fiil_var:
            sorunlar.append("fiil kuralı sağlanmadı")
        if not kisa:
            sorunlar.append(f"{kelime_say(metin)} kelime (sınır 10)")
        return False, ", ".join(sorunlar)
    if alan_adi == "neden_onemli":
        gecti = kelime_say(metin) <= 15
        return gecti, None if gecti else f"{kelime_say(metin)} kelime (sınır 15)"
    if alan_adi == "ozet":
        # Kullanıcı kararı (tutarlılık turu): "Mutlaka bil" gövdesi için
        # SABİT hedef — 4 cümle, 55-75 kelime. Eskiden sadece ÜST sınır
        # denetleniyordu, bu yüzden aynı bölümdeki metinler farklı
        # ağırlıkta çıkıyordu (Denver-Lakers 3 kısa cümle, Orlando-Dallas
        # belirgin şekilde daha uzun). ALT SINIR da zorunlu: çok kısa
        # kalan metin bir olgu daha eklemek zorunda.
        cumle_sayisi = cumle_say(metin)
        kelime_sayisi = kelime_say(metin)
        if sablon:
            gecti = kelime_sayisi <= OZET_KELIME_UST
            return gecti, None if gecti else f"{kelime_sayisi} kelime (üst sınır {OZET_KELIME_UST})"
        gecti = cumle_sayisi == OZET_CUMLE and OZET_KELIME_ALT <= kelime_sayisi <= OZET_KELIME_UST
        if gecti:
            return True, None
        return False, (f"{cumle_sayisi} cümle / {kelime_sayisi} kelime "
                       f"(hedef {OZET_CUMLE} cümle / {OZET_KELIME_ALT}-{OZET_KELIME_UST} kelime)")
    if alan_adi == "ozet_kisa":
        # Kullanıcı kararı (Mutlaka bil 3 maça çıktı): en yüksek rozetli
        # maç TAM anlatı (yukarıdaki "ozet"), 2. ve 3. maçlar KISA anlatı
        # — maliyeti kontrol etmek için, "ozet"ten daha sıkı bir sınır.
        cumle_sayisi = cumle_say(metin)
        kelime_sayisi = kelime_say(metin)
        if sablon:
            gecti = kelime_sayisi <= 45
            return gecti, None if gecti else f"{kelime_sayisi} kelime (üst sınır 45)"
        gecti = 2 <= cumle_sayisi <= 3 and OZET_KISA_KELIME_ALT <= kelime_sayisi <= 45
        if gecti:
            return True, None
        return False, (f"{cumle_sayisi} cümle / {kelime_sayisi} kelime "
                       f"(hedef 2-3 cümle / {OZET_KISA_KELIME_ALT}-45 kelime)")
    if alan_adi == "gec_satiri":
        gecti = cumle_say(metin) <= 3
        return gecti, None if gecti else f"{cumle_say(metin)} cümle (sınır 3)"
    return True, None


# ---------------------------------------------------------------------------
# Brief satırı — final skor gürültüsü. Kural (kullanıcı): skor kartta
# zaten duruyor, brief'te tekrarlamak gürültü — TEK istisna skorun
# kendisi haberse (kalip_secici.FARK_ESIGI ile aynı eşik, 20+ sayı fark).
# ---------------------------------------------------------------------------

BRIEF_SKOR_FARK_ESIGI = 20


def t19_brief_skor_gurultusu(alan_adi, metin, gercekler):
    if alan_adi != "brief_metin":
        return True, None
    skor = next((f for f in gercekler if f["tur"] == "skor"), None)
    if not skor:
        return True, None
    v = skor["veri"]
    buyuk, kucuk = max(v["ev_skor"], v["dep_skor"]), min(v["ev_skor"], v["dep_skor"])
    fark = buyuk - kucuk
    if fark >= BRIEF_SKOR_FARK_ESIGI:
        return True, None
    desen = re.compile(rf"\b{buyuk}\s*-\s*{kucuk}\b|\b{kucuk}\s*-\s*{buyuk}\b")
    if desen.search(metin):
        return False, f"final skor ({buyuk}-{kucuk}) brief'te gereksiz — fark ({fark}) haber değeri eşiğinin altında (<{BRIEF_SKOR_FARK_ESIGI})"
    return True, None


# ---------------------------------------------------------------------------
# T20 — Sezon başı susma kuralı
# ---------------------------------------------------------------------------
#
# Kullanıcı kararı: "Ekim-Kasım için sezon öncesi beklenti verisi" borcu.
# Bir takım 10 maçın altındaysa (derece faktöründeki "sezon_guvenilir":
# false) derece/sıralama, sürpriz sonuç, zirve maçı ve seri iddiaları
# anlamsız — 1-9 maçlık bir örneklemle kimin favori/lider olduğu
# bilinemez. Fact seviyesinde zaten susturulmuş olmaları (gercekler.py/
# kalip_secici.py) şablonları/kancaları korur, ama LLM serbest metinde
# aynı iddiayı ham "derece" faktöründeki galibiyet/mağlubiyet sayılarından
# kendi kelimeleriyle yeniden kurabilir — bu test o kaçışı yakalar.

DERECE_ERKEN_DESENI = re.compile(
    r"\d+\s*-\s*\d+\s*'?\s*(a|e|ya|ye)\s+(yükseldi|düştü)|"
    r"sezona\s+\d+\s*-\s*\d+\s+başladı|"
    r"sezonu\s+\d+\s*-\s*\d+\s+yaptı|"
    r"namağlup|"
    r"lig\s+lideri|"
    r"konferansta\s+\d+\.\s*s[ıi]raya?",
    re.IGNORECASE,
)
SURPRIZ_ZIRVE_ERKEN_DESENI = re.compile(r"sürpriz|zirve", re.IGNORECASE)
SERI_ERKEN_DESENI = re.compile(
    r"maçlık\s+(galibiyet|mağlubiyet)\s+serisi|maç\s+aradan\s+sonra", re.IGNORECASE
)
SEZON_ICI_SIKLIK_ERKEN_DESENI = re.compile(
    r"bu\s+sezon\s+(ondan\s+önce\s+)?(hiç|ilk\s+kez|önce\s+\d+\s+kez)", re.IGNORECASE
)


def t20_sezon_acilisi_susma(metin, gercekler):
    derece_facts = [f["veri"] for f in gercekler if f["tur"] == "derece"]
    erken_var = any(not d.get("sezon_guvenilir", True) for d in derece_facts)
    if not erken_var:
        return True, None
    sorunlu = []
    if DERECE_ERKEN_DESENI.search(metin) or UST_USTE_DESENI.search(metin):
        sorunlu.append("derece/sıralama/'üst üste' iddiası — takımlardan biri 10 maçın altında, sezon_guvenilir=false")
    if SURPRIZ_ZIRVE_ERKEN_DESENI.search(metin):
        sorunlu.append("sürpriz/zirve çerçevesi — takımlardan biri 10 maçın altında")
    if SERI_ERKEN_DESENI.search(metin):
        sorunlu.append("seri iddiası — takımlardan biri 10 maçın altında")
    if SEZON_ICI_SIKLIK_ERKEN_DESENI.search(metin):
        sorunlu.append("sezon içi sıklık iddiası ('bu sezon önce N kez') — güvenilir örneklem yok")
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T21 — İyelik eki 'n' tamponu sadece sesli harfle biten kelimede
# ---------------------------------------------------------------------------
#
# Kullanıcı kararı: "Anthony Edwards'nin" → "Edwards'ın". 'n' tamponu
# ("'nin/'nın/'nun/'nün") SADECE sesli harfle biten kelimede doğrudur
# ("Doğu'nun", "Batı'nın") — ünsüzle biten bir kelimede ("Edwards")
# tampon YANLIŞ, doğrusu tamponsuz ek ("Edwards'ın"). Ek üretimi artık
# `_iyelik_eki` ortak fonksiyonuna bağlı (yaz.py), bu test kaçan
# herhangi bir hardcode'u mekanik olarak yakalar.

_SESLI_HARFLER = set("aeıioöuüAEIİOÖUÜ")
IYELIK_TAMPON_DESENI = re.compile(r"(\w+)'(nin|nın|nun|nün)\b")


def t21_iyelik_eki_tamponu(metin):
    sorunlu = []
    for m in IYELIK_TAMPON_DESENI.finditer(metin):
        kelime = m.group(1)
        if kelime and kelime[-1] not in _SESLI_HARFLER:
            sorunlu.append(f"'{kelime}'{m.group(2)}' — 'n' tamponu sadece sesli harfle biten kelimede kullanılır, '{kelime}' ünsüzle bitiyor")
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T22 — Küçük skor farkı rakamla anılmaz
# ---------------------------------------------------------------------------
#
# Kullanıcı kararı (bir önceki turda sistem promptuna eklenmişti ama HİÇ
# mekanik denetimi yoktu — geriye dönük test denetiminde bulundu): "2 sayı
# farkla yendi" gibi bir skor farkı rakamı, fark 20'nin altındaysa hiç
# yazılmaz — skor zaten kartta yazılı, okuyucu farkı kendisi görüyor.

FARK_RAKAMI_DESENI = re.compile(r"(\d+)\s*sayı(?:lık)?\s*fark(?:la|ıyla|le|ıyle|le)?\b", re.IGNORECASE)
FARK_RAKAMI_ESIGI = 20


def t22_kucuk_fark_rakami(metin):
    sorunlu = []
    for m in FARK_RAKAMI_DESENI.finditer(metin):
        sayi = int(m.group(1))
        if sayi < FARK_RAKAMI_ESIGI:
            sorunlu.append(f"'{m.group(0)}' — {sayi} sayılık fark {FARK_RAKAMI_ESIGI}'nin altında, skor zaten kartta yazılı, rakamla anılmaz")
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T23 — Mimari kural ihlalleri (sessizlik varsayılan turu)
# ---------------------------------------------------------------------------

# Kullanıcı kararı: "toplamak" SADECE ribaund fiilidir. Eski desen sadece
# "N sayı topladı" kalıbını yakalıyordu; "topladığı ivme", "30 sayı ve 10
# ribaund topladı" gibi varyantlar sızdı. Yeni kural: "topla-" kökünün
# HER kullanımı, aynı cümlede "ribaund" geçmiyorsa reddedilir.
TOPLA_KOKU_DESENI = re.compile(r"\btopla(dı|yarak|dığı|dığında|r|mış|nan)\w*", re.IGNORECASE)
RIBAUND_DESENI = re.compile(r"ribaund", re.IGNORECASE)
BASKA_ISTATISTIK_DESENI = re.compile(r"\bsayı\w*|\basist\w*", re.IGNORECASE)
ALT_PERIYOT_DESENI = re.compile(r"son\s+periyot\w*|son\s+çeyrek\w*|\d\.\s*çeyrek\w*|\d\.\s*periyot\w*", re.IGNORECASE)
LIDER_KELIME_DESENI = re.compile(r"lider\w*\s+değiş\w*|el\s+değiş\w*", re.IGNORECASE)
LIDER_DEGISIM_BOZUK_SIFAT_DESENI = re.compile(r"\d+\s*lider\s+değişimli", re.IGNORECASE)
FARKLA_EZDI_YENDI_DESENI = re.compile(r"\d+\s*-\s*\d+\s*(\'?lik)?\s*farkla\s*(ezdi|yendi)", re.IGNORECASE)
SIRALAMA_IDDIASI_DESENI = re.compile(r"konferansta\s+(\d+)\.\s*s[ıi]ra", re.IGNORECASE)


def t24_en_iyi_kilometre_sahibi(metin, gercekler):
    """Kullanıcı kuralı: bir maçta AYNI kilometre eşiğini birden fazla
    oyuncu geçmişse, metin SADECE en yüksek GmSc'li olanı anabilir.
    Gerçek üretim bug'ı (12 Kasım, SAS-GSW): Wembanyama 31/15/10
    triple-double yapmışken metin Castle'ın 23/10/10'unu andı."""
    kilometreler = [f["veri"] for f in gercekler if f["tur"] == "kilometre"]
    if len(kilometreler) < 2:
        return True, None
    by_esik = {}
    for k in kilometreler:
        by_esik.setdefault(k["esik"], []).append(k)
    sorunlu = []
    for esik, liste in by_esik.items():
        if len(liste) < 2:
            continue
        en_iyi = max(liste, key=lambda k: k.get("gmsc", 0))
        # Kuralın amacı "en iyisi ANILMALI" — daha zayıf oyuncunun hiç
        # anılmaması değil. En iyisi metinde zaten geçiyorsa ikisinin
        # birlikte anılması DOĞRU sonuçtur ve reddedilmez. (Gerçek
        # üretim bug'ı: 2025-10-23 GSW-DEN'de metin hem Curry'yi hem
        # daha yüksek GmSc'li Gordon'ı anıyordu, T24 yine de reddetti.)
        en_iyi_soyad = en_iyi["oyuncu"].strip().split()[-1]
        if en_iyi_soyad.lower() in metin.lower():
            continue
        for k in liste:
            if k is en_iyi:
                continue
            soyad = k["oyuncu"].strip().split()[-1]
            if soyad.lower() in metin.lower():
                sorunlu.append(
                    f"'{k['oyuncu']}' ({esik}) anıldı ama aynı maçta '{en_iyi['oyuncu']}' "
                    f"daha yüksek GmSc ile aynı eşiği geçti — en iyisi anılmalı"
                )
    return (len(sorunlu) == 0, sorunlu or None)


def t23_mimari_kural_ihlalleri(metin):
    sorunlu = []
    for cumle in cumlelere_ayir(metin):
        m = TOPLA_KOKU_DESENI.search(cumle)
        if not m:
            continue
        # Fiilden ÖNCEKİ kısma bakılır: fiil hangi istatistiği yönetiyor?
        # "30 sayı ve 10 ribaund topladı" — fiil sayıyı da kapsıyor, YANLIŞ.
        # "10 ribaund topladı" — sadece ribaund, DOĞRU.
        # "topladığı ivme" — hiç istatistik yok, soyut kullanım, YANLIŞ.
        onceki = cumle[: m.start()]
        if BASKA_ISTATISTIK_DESENI.search(onceki):
            sorunlu.append(
                f"'{m.group(0)}' — 'toplamak' SADECE ribaund fiilidir, aynı cümlede sayı/asist de "
                f"bu fiile bağlanmış; sayı 'atılır', asist 'verilir'"
            )
        elif not RIBAUND_DESENI.search(onceki):
            sorunlu.append(
                f"'{m.group(0)}' — 'toplamak' SADECE ribaund fiilidir, burada ribaunda bağlı değil"
            )
    # Lider değişimi ALT KIRILIMI: bir çeyrek/periyot referansı VE bir
    # "lider/el değiştirdi" ifadesi AYNI cümlede geçiyorsa (sırası önemli
    # değil — "son periyotta X kez el değiştirdi" ya da "liderlik 22 kez
    # el değiştirdi, son periyotta bu sayı 5'e çıktı" ikisi de yakalanır).
    for cumle in cumlelere_ayir(metin):
        if ALT_PERIYOT_DESENI.search(cumle) and LIDER_KELIME_DESENI.search(cumle):
            sorunlu.append(f"lider değişimi ALT KIRILIMI ('{cumle.strip()}') hiçbir zaman yazılmaz — sadece maç geneli toplamı, 15+ ise")
    if LIDER_DEGISIM_BOZUK_SIFAT_DESENI.search(metin):
        sorunlu.append("'N lider değişimli maçta' bozuk sıfat bileşiği — doğrusu 'Liderliğin N kez el değiştirdiği maçta'")
    if FARKLA_EZDI_YENDI_DESENI.search(metin):
        sorunlu.append("skor verilmişken 'farkla ezdi/yendi' demek gereksiz — skor zaten farkı taşıyor")
    for m in SIRALAMA_IDDIASI_DESENI.finditer(metin):
        n = int(m.group(1))
        if not (n <= 3 or 6 <= n <= 11):
            sorunlu.append(f"'{m.group(0)}' — sıralama SADECE ilk 3'e girme/çıkma veya play-in bandında (6-11) anılır")
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# Tek bir metin alanını doğrula (T1,T2,T3,T4,T6)
# ---------------------------------------------------------------------------


def alan_dogrula(alan_adi, metin, gercekler, ham_mac, yasakli_liste, sablon=False):
    testler = {}
    testler["T1"] = t1_sayi_izlenebilirligi(metin, gercekler)
    testler["T2"] = t2_ozel_ad_izlenebilirligi(metin, gercekler, ham_mac)
    testler["T3"] = t3_an_iddiasi(metin, gercekler)
    testler["T4"] = t4_yasakli_ifade(metin, yasakli_liste)
    testler["T6"] = t6_uzunluk(alan_adi, metin, sablon=sablon)
    testler["T10"] = t_fiil_cekimi(metin)
    testler["T11"] = t4b_terim_varyanti(metin)
    testler["T12"] = t_turkce_yazim(metin)
    testler["T4c"] = t4c_puan_baglami(metin)
    testler["T4d"] = t4d_kok_kaliplari(metin)
    testler["T4e"] = t4e_takim_kodu(metin)
    testler["T4f"] = t4f_konferans_ozel_ad(metin)
    testler["T13"] = t13_atif_dogrulugu(metin, gercekler, ham_mac)
    testler["T15"] = t15_istatistik_seri_sebebi(metin)
    testler["T16"] = t16_haber_degeri_esigi(metin, gercekler, ham_mac)
    testler["T17"] = t17_kaybeden_ozne(metin, gercekler, ham_mac)
    testler["T18"] = t18_cift_cift_dogru(metin, gercekler)
    testler["T19"] = t19_brief_skor_gurultusu(alan_adi, metin, gercekler)
    testler["T20"] = t20_sezon_acilisi_susma(metin, gercekler)
    testler["T21"] = t21_iyelik_eki_tamponu(metin)
    testler["T22"] = t22_kucuk_fark_rakami(metin)
    testler["T23"] = t23_mimari_kural_ihlalleri(metin)
    testler["T24"] = t24_en_iyi_kilometre_sahibi(metin, gercekler)
    gecti = all(sonuc[0] for sonuc in testler.values())
    return gecti, testler


# ---------------------------------------------------------------------------
# T13 — Atıf doğruluğu: bir sayı/olay doğru takıma/oyuncuya bağlanmış mı
# ---------------------------------------------------------------------------
#
# Gerçek üretim hatası: "neden_onemli" alanı "CHA, 16 sayılık açığı
# kapatıp son anda kaybederek..." dedi — oysa 16 sayılık farktan dönen
# ve maçı kazanan MIL'di, CHA geride kalan taraftı. T1 (sayı var mı) ve
# T5 (kazanan geçiyor mu) ikisi de bunu YAKALAYAMADI çünkü ikisi de
# "kime ait" sorusuna bakmıyor. Şimdilik SADECE geri dönüş/fark
# iddialarını kapsıyor — bu, gerçek bug'ın kapsamı ve gercekler
# kaydından (fark_serisi + skor) mekanik olarak doğrulanabilen tek vaka.
# Çeyrek üstünlüğü ve "en yüksek performans" atfı, ayrı ve daha geniş
# bir doğal dil analizi gerektiriyor — bkz. dogrula.py'deki not, bu
# doküman bilerek dar kapsamlı tutuldu (yanlış negatiften iyi, ama
# aşırı geniş bir desen de yanlış pozitif üretebilir).

GERI_DONUS_DESENI = re.compile(
    r"aç[ıi]\w*\s+kapat\w*|fark[ıi]?\w*\s*(?:tan|dan)?\s*(dön\w*|eri\w*)|geri\s+dön\w*",
    re.IGNORECASE,
)
SERI_DESENI = re.compile(r"galibiyet\w*\s+serisi\w*|mağlubiyet\w*\s+serisi\w*", re.IGNORECASE)
SONUC_IDDIASI_DESENI = re.compile(
    r"öne\s+geçirdi|galibiyet\w*\s+getirdi|maçı\s+bitirdi|galip\s+getirdi|zaferi?\s+getirdi|kazandırdı",
    re.IGNORECASE,
)
OLUMSUZLUK_REGEX = re.compile(r"\b(yetmedi|olmadı|başaramadı|kalmadı|edemedi|çeviremedi|bulamadı)\b", re.IGNORECASE)
# Kullanıcı düzeltmesi: bir OT maçında kaybeden taraf gerçekten "farktan
# döner" ama sadece BERABERLİĞE/uzatmaya ulaşır, maçı kazanmaz — bu
# GERÇEK ve doğru bir atıf, T13'ün "kaybedene atfedilmiş = her zaman
# hata" varsayımı bu durumda yanlış pozitif üretiyordu (25 Aralık,
# Minnesota'nın Denver'a karşı son çeyrek geri dönüşü — uzatmaya
# gittiler, Minnesota kazanmadı ama gerçekten farktan döndü). "Berabere/
# eşitle/uzatmaya" ya da eşit bir skor (115-115 gibi) yakınlarda geçiyorsa
# bu bir ZAFER iddiası değil, sadece PARİTEYE ulaşma açıklaması sayılır.
PARITE_REGEX = re.compile(r"berabere|eşitle\w*|uzatmaya|\b(\d+)-\1\b", re.IGNORECASE)
# "150'ye ulaşan Bam Adebayo" gibi — bir SAYI + ulaşma/taşıma fiili +
# hemen ardından bir özel ad (oyuncu adayı).
TAKIM_SKORU_OYUNCUYA_DESENI = re.compile(
    r"(\d+)'(?:y?[aeı])\s+(?:ulaş|taşı|çıkar)\w*\s+"
    r"([A-ZÇĞİÖŞÜ][\wçğıöşüİ'’.-]*(?:\s+[A-ZÇĞİÖŞÜ][\wçğıöşüİ'’.-]*){0,3})"
)


def _takim_aliaslari(ham_mac, kod):
    bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    for taraf in ("homeTeam", "awayTeam"):
        t = bt[taraf]
        if t["teamTricode"] == kod:
            sehir, ad = t.get("teamCity"), t.get("teamName")
            # "Şehir Ad" BİLEŞİK adı da ayrıca eklenir — "Indiana
            # Pacers'ı" gibi çok kelimeli bir addan ek SADECE son
            # kelimeye ("Pacers") yapışıyor. Sadece "Indiana" ve
            # "Pacers"ı ayrı adaylar olarak tutmak, "Indiana"yı EKSİZ
            # (özne gibi) bırakıyordu — en yakın-aday araması gerçek
            # nesneyi ("Indiana Pacers'ı") değil şehir adını seçip
            # yanlış özneye atıf yapıyordu (gerçek üretim bug'ı: "üst
            # üste ikinci galibiyet" San Antonio yerine Indiana'ya
            # atfedilip eşik testinden yanlışlıkla geçmişti). Bileşik
            # alias en_uzun_by_pos'ta aynı pozisyonda kısasını ELER.
            bilesik = f"{sehir} {ad}" if sehir and ad else None
            return {a for a in (t["teamTricode"], sehir, ad, bilesik) if a}
    return {kod}


IYELIK_EKI_REGEX = re.compile(r"^['’]?(n[iuüı]n|[iuüı]n|nun|nün)\b", re.IGNORECASE)

# Yan cümle sınırı — "X kazandı VE [rakibin] mağlubiyet serisini
# çıkardı" gibi çok yan-cümleli bir cümlede önceki yan cümlenin öznesi
# (X), SONRAKİ yan cümledeki farklı/elenmiş bir öznenin (rakip) yerine
# geçmemeli. Gerçek bug: "Oklahoma City ... kazandı ve mağlubiyet
# serisini 4'e çıkardı" cümlesinde OKC kazanan taraf, ama "mağlubiyet
# serisi" örtük öznesi rakip — cümlenin TAMAMINA bakmak yerine sadece
# İÇİNDE BULUNULAN yan cümleye bakmak bu belirsiz durumda hiç
# atfetmemeyi (boş dönmeyi) sağlıyor, yanlış atfetmek yerine.
#
# Virgül BİLEREK sınır sayılmıyor — Türkçede "Charlotte, 16 sayılık
# farktan dönerek kazandı" gibi cümlelerde özne virgülden SONRAKİ
# ulaç/katılma cümlesini de yönetir; virgülü sınır saymak öznenin
# kendisini arama penceresinin dışına atıyordu (gerçek üretim bug'ı —
# doğru tespit edilmiş bir vaka bu yüzden yanlışlıkla kaçırıldı).
CUMLE_ICI_SINIR_REGEX = re.compile(r"\b(ve|ama|ancak|fakat|ise)\b|;")


def _son_yan_cumleyi_al(cumle, pozisyon):
    en_son_sinir = None
    for m in CUMLE_ICI_SINIR_REGEX.finditer(cumle[:pozisyon]):
        en_son_sinir = m.end()
    return cumle[en_son_sinir:pozisyon] if en_son_sinir is not None else cumle[:pozisyon]


# Belirtme hali (accusative) — "Denver'ı yendi" cümlesinde Denver
# NESNE, özne değil. "Cleveland, Denver'ı ... yenerek üst üste üçüncü
# galibiyetini aldı" cümlesinde Denver'a en yakın olan taraf odur ama
# cümlenin gerçek öznesi Cleveland — nesne ekini de iyelik eki gibi
# atlamak gerekiyor (gerçek üretim bug'ı: "üst üste" iddiası yanlışlıkla
# nesneye, Denver'a, atfedildi).
NESNE_EKI_REGEX = re.compile(r"^['’]?(y?[ıiuü])\b", re.IGNORECASE)
OZNE_DISI_EKLER = (IYELIK_EKI_REGEX, NESNE_EKI_REGEX)


def _en_yakin_ozne_takim(cumle, pozisyon, aliaslar_by_etiket):
    """pozisyon'dan ÖNCE geçen, GRAMER OLARAK ÖZNE olması muhtemel en
    yakın takımın etiketini döner (aliaslar_by_etiket: {etiket:
    {alias, ...}}), ya da None. Cümledeki İLK takıma bakmak yanlış —
    "Charlotte farkı açtı ama Milwaukee bu farktan döndü" gibi
    iki-özneli bir cümlede geri dönüşün gerçek öznesi fiile en yakın
    (Milwaukee), cümlenin ilk kelimesi değil (gerçek üretim bug'ı —
    ilk sürüm Charlotte'u öznesi sanıp doğru yazılmış bir cümleyi
    reddetti). Ama en yakın olan da tuzaklı olabilir: iyelik eki
    ("Charlotte'UN farkını") ya da belirtme hali eki ("Denver'ı
    yenerek") almış bir aday cümlenin öznesi DEĞİL — atlanır, bir
    önceki adaya bakılır. Arama SADECE içinde bulunulan yan cümleyle
    sınırlı (bkz. _son_yan_cumleyi_al)."""
    oncesi = _son_yan_cumleyi_al(cumle, pozisyon)
    adaylar = []  # (pozisyon, etiket, eslesme_sonu)
    for etiket, aliaslar in aliaslar_by_etiket.items():
        for alias in aliaslar:
            for m in re.finditer(re.escape(alias), oncesi, re.IGNORECASE):
                adaylar.append((m.start(), etiket, m.end()))
    # Aynı pozisyonda birden fazla aday olabilir — takım kodu (CHA) tam
    # şehir adının (Charlotte) İÇİNDE de bir alt dize olarak eşleşiyor
    # ("CHA" ⊂ "Charlotte"), aynı başlangıç pozisyonunda ama daha kısa.
    # Kısa eşleşmeyi elde tutarsak ek kontrolü yanlış yerden bakıyor
    # (gerçek üretim bug'ı) — aynı pozisyondaki KISA eşleşmeleri
    # tamamen ELE, sadece en uzunu kalsın.
    en_uzun_by_pos = {}
    for pos, etiket, bitis in adaylar:
        mevcut = en_uzun_by_pos.get(pos)
        if mevcut is None or (bitis - pos) > (mevcut[1] - pos):
            en_uzun_by_pos[pos] = (etiket, bitis)
    adaylar = [(pos, etiket, bitis) for pos, (etiket, bitis) in en_uzun_by_pos.items()]
    adaylar.sort(key=lambda a: -a[0])
    for pos, etiket, bitis in adaylar:
        sonrasi = oncesi[bitis : bitis + 6]
        if any(desen.match(sonrasi) for desen in OZNE_DISI_EKLER):
            continue
        return etiket
    return None


def _en_yakin_onceki_takim(cumle, pozisyon, aliaslar_a, aliaslar_b):
    return _en_yakin_ozne_takim(cumle, pozisyon, {"a": aliaslar_a, "b": aliaslar_b})


def t13_atif_dogrulugu(metin, gercekler, ham_mac):
    skor_gercegi = next((f for f in gercekler if f["tur"] == "skor"), None)
    if skor_gercegi is None:
        return True, None
    kazanan = skor_gercegi["veri"]["kazanan"]
    ev, dep = skor_gercegi["veri"]["ev"], skor_gercegi["veri"]["dep"]
    kaybeden = dep if kazanan == ev else ev

    kazanan_aliaslari = _takim_aliaslari(ham_mac, kazanan)
    kaybeden_aliaslari = _takim_aliaslari(ham_mac, kaybeden)

    sorunlu = []
    for cumle in cumlelere_ayir(metin):
        m = GERI_DONUS_DESENI.search(cumle)
        if m:
            # Olumsuzluk kontrolü: "New York'un geri dönüşe yetmedi" gibi
            # bir cümle bir geri dönüş İDDİA ETMİYOR, tam tersini
            # söylüyor — teşebbüsün YETERSİZ kaldığını. Fiilden hemen
            # sonra bir olumsuzluk kelimesi geçiyorsa bu cümle atıf
            # kontrolünün kapsamı dışında (gerçek üretim bug'ı — "geri
            # dönüşe yetmedi" cümlesi başarılı bir geri dönüş gibi
            # okunup yanlışlıkla reddedildi).
            sonrasi_pencere = cumle[m.end() : m.end() + 30]
            if OLUMSUZLUK_REGEX.search(sonrasi_pencere):
                continue
            taraf = _en_yakin_onceki_takim(cumle, m.start(), kazanan_aliaslari, kaybeden_aliaslari)
            if taraf == "b":
                genis_pencere = cumle[m.end() : m.end() + 60]
                if PARITE_REGEX.search(genis_pencere):
                    continue
                sorunlu.append(f"geri dönüş kaybedene atfedilmiş: '{cumle.strip()}'")

    # Bir cümle iki takımın da serisinden bahsedebilir ("Atlanta galibiyet
    # serisini sürdürürken New York mağlubiyet serisine girdi") — bu
    # YANLIŞ DEĞİL. Öznesini bulmanın doğru yolu cümlenin TAMAMINA değil,
    # "X serisi" ifadesinden HEMEN ÖNCE geçen en yakın takım adına
    # bakmak (ilk sürüm cümledeki HERHANGİ bir takımı eşleştiriyordu ve
    # bu, doğru atfedilmiş cümleleri de reddediyordu — gerçek bug).
    seri_gercekleri = {f["veri"]["takim"]: f["veri"]["tur"] for f in gercekler if f["tur"] == "seri"}
    aliaslar_by_kod = {kod: _takim_aliaslari(ham_mac, kod) for kod in seri_gercekleri}
    for cumle in cumlelere_ayir(metin):
        for m in SERI_DESENI.finditer(cumle):
            # "tur" gercekler.py'de ASCII yazımla saklanıyor ("maglubiyet",
            # ğ'siz — bir kod/enum değeri, ekrana yazılan metin değil).
            # Metindeki cümle Türkçe yazımla geçer ("mağlubiyet") — ikisini
            # karşılaştırmadan önce aynı yazıma indirmek gerekiyor.
            bulunan_tip = "galibiyet" if m.group(0).lower().startswith("gal") else "maglubiyet"
            en_yakin_kod = _en_yakin_ozne_takim(cumle, m.start(), aliaslar_by_kod)
            if en_yakin_kod is None:
                continue
            beklenen = seri_gercekleri[en_yakin_kod]
            if bulunan_tip != beklenen:
                beklenen_okunur = "mağlubiyet" if beklenen == "maglubiyet" else "galibiyet"
                sorunlu.append(f"seri türü ters: '{cumle.strip()}' ({en_yakin_kod} aslında {beklenen_okunur} serisinde)")

    # Takım skoru bir OYUNCUYA atfedilemez — gerçek üretim bug'ı: "Son
    # dakikada serbest atışlarla 150'ye ulaşan Bam Adebayo" — 150
    # TAKIMIN skoru, Adebayo'nun kendi sayısı değildi (83'tü). "X'e
    # ulaşan/taşıyan/çıkaran <Oyuncu>" kalıbında X bir takımın final
    # skoruna eşitse ama o oyuncunun kendi 'sayi' istatistiğine eşit
    # DEĞİLSE, takım skoru oyuncuya yanlış atfedilmiş demektir.
    ev_skor, dep_skor = skor_gercegi["veri"]["ev_skor"], skor_gercegi["veri"]["dep_skor"]
    oyuncu_stat_by_isim = {f["veri"]["oyuncu"]: f["veri"] for f in gercekler if f["tur"] == "oyuncu_stat"}
    for m in TAKIM_SKORU_OYUNCUYA_DESENI.finditer(metin):
        sayi = int(m.group(1))
        if sayi not in (ev_skor, dep_skor):
            continue
        aday_ad = m.group(2).strip()
        en_yakin_oyuncu = next((o for o in oyuncu_stat_by_isim if aday_ad.startswith(o) or o.startswith(aday_ad)), None)
        if en_yakin_oyuncu is None:
            continue
        oyuncu_sayi = oyuncu_stat_by_isim[en_yakin_oyuncu].get("sayi")
        if oyuncu_sayi != sayi:
            sorunlu.append(
                f"'{m.group(0)}' — {sayi} takımın final skoru, {en_yakin_oyuncu}'nin kendi sayısı "
                f"{oyuncu_sayi} — takım skoru oyuncuya atfedilmiş"
            )

    # Kullanıcı kararı: bir oyuncunun eylemi "takımını öne geçirdi",
    # "galibiyeti getirdi", "maçı bitirdi" gibi bir SONUÇ iddiası
    # taşıyorsa, o oyuncu KAZANAN takımda olmak zorunda — kaybeden bir
    # oyuncu maçı kazandıramaz. Gerçek üretim bug'ı: Houston 125-124
    # KAYBETTİĞİ halde "Şengün ... bir basketle takımını öne geçirdi"
    # yazılmıştı — Şengün'ün basketi maçı GEÇİCİ olarak öne taşımıştı,
    # OKC hemen ardından yeniden öne geçip maçı kazandı; "öne geçirdi"
    # okuyucuya kalıcı/belirleyici bir izlenim veriyor, yanıltıcı.
    for cumle in cumlelere_ayir(metin):
        for m in SONUC_IDDIASI_DESENI.finditer(cumle):
            oncesi = cumle[: m.start()]
            en_yakin_oyuncu, en_yakin_pos = None, -1
            for isim in oyuncu_stat_by_isim:
                pos = oncesi.rfind(isim)
                if pos > en_yakin_pos:
                    en_yakin_pos, en_yakin_oyuncu = pos, isim
            if en_yakin_oyuncu is None:
                continue
            if oyuncu_stat_by_isim[en_yakin_oyuncu].get("takim") == kaybeden:
                sorunlu.append(
                    f"'{m.group(0)}' sonuç iddiası ama en yakın oyuncu '{en_yakin_oyuncu}' kaybeden takımda ({kaybeden}): '{cumle.strip()}'"
                )

    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T17 — Kaybeden takımın oyuncusu cümlenin öznesi olarak BAŞLAYAMAZ
# ---------------------------------------------------------------------------
#
# "Kural: en yüksek performans anılıyorsa, kazanandan başlanır" —
# kaybeden bir oyuncu anılabilir ama hikayenin girişi/öznesi olamaz.
# Mekanik test: cümle DOĞRUDAN kaybeden takımın bir oyuncusunun
# adıyla başlıyorsa reddet (isim cümle başında geçtiği için T2'nin
# kapsamı dışında kalıyor — o sadece uydurma adları yakalar, bu ayrı
# bir kural: gerçek ama yanlış yerde bir isim).


KARSIN_RAGMEN_REGEX = re.compile(r"\b(karşın|rağmen)\b", re.IGNORECASE)


def t17_kaybeden_ozne(metin, gercekler, ham_mac):
    skor_gercegi = next((f for f in gercekler if f["tur"] == "skor"), None)
    if skor_gercegi is None:
        return True, None
    kazanan = skor_gercegi["veri"]["kazanan"]
    ev, dep = skor_gercegi["veri"]["ev"], skor_gercegi["veri"]["dep"]
    kaybeden = dep if kazanan == ev else ev
    kaybeden_oyuncular = {
        f["veri"]["oyuncu"] for f in gercekler
        if f["tur"] == "oyuncu_stat" and f["veri"].get("takim") == kaybeden
    }
    if not kaybeden_oyuncular:
        return True, None

    sorunlu = []
    for cumle in cumlelere_ayir(metin):
        parca = cumle.strip()
        for oyuncu in kaybeden_oyuncular:
            # \b kullanılmıyor — "Jaren Jackson Jr." gibi noktayla biten
            # isimlerde noktadan sonra boşluk geldiğinde iki taraf da
            # \w-dışı olduğu için \b eşleşmiyordu (gerçek üretim bug'ı).
            # Düz startswith + ardından harf/rakam OLMAMASI yeterli.
            if parca.lower().startswith(oyuncu.lower()):
                sonrasi = parca[len(oyuncu) :]
                if not sonrasi or not sonrasi[0].isalnum():
                    # Kullanıcı düzeltmesi: "X'in N sayısına karşın Y, ..."
                    # gibi bir ZITLIK cümlesinde kaybedenin adı cümle
                    # başında geçse de gerçek özne/kahraman KAZANANDIR (Y)
                    # — T17'nin niyeti kaybedeni hikâyenin merkezine
                    # koymamak, bu kalıpta ise tam tersi oluyor: kazananı
                    # öne çıkarmak için kaybedenin adı bir referans noktası
                    # olarak kullanılıyor. "karşın"/"rağmen" bağlacı yan
                    # cümlede (ilk ~60 karakter) geçiyorsa güvenli sayılır.
                    if KARSIN_RAGMEN_REGEX.search(sonrasi[:60]):
                        continue
                    sorunlu.append(f"'{oyuncu}' (kaybeden {kaybeden}) cümle öznesi: '{parca}'")
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T18 — türetilmiş iddia sınıfı: sayılardan çıkarsanan ama sayı olmayan iddialar
# ---------------------------------------------------------------------------
#
# Gerçek üretim hatası #1: "Shai Gilgeous-Alexander 30 sayı, 7 asistle
# double-double yaptı" — ama gerçek istatistiği 30 sayı, 1 ribaund, 7
# asist; SADECE bir kategori 10'un üzerinde, double-double değil. T1
# bunu yakalayamaz çünkü "double-double" bir SAYI değil, sayılardan
# türetilmiş bir İDDİA.
#
# Gerçek üretim hatası #2: "Pascal Siakam ... kariyer rekorunu kırdı" —
# Siakam'ın kariyer rekoru 40'ın üzerinde, bu tamamen uydurma. Aynı
# sınıfın daha tehlikeli bir üyesi: gercekler.py hattında "kariyer
# rekoru / sezon rekoru / franchise rekoru / ilk kez / en yüksek /
# tarihte" türünden bir iddiayı doğrulayacak kayıt YOKTU — o yüzden
# bu kalıplar eşiğe bakılmaksızın reddediliyordu.
#
# Kullanıcı düzeltmesi (11 gecelik toplu üretim): bu, GERÇEKTEN
# olağanüstü bir performansı (60+ sayı, 25+ ribaund, quadruple-double
# gibi) da metinden dışlıyordu — "tarihte nadir" çerçevesi tam da bu
# tür geceler için var olma sebebi. Çözüm KAYIT EKLEMEK oldu:
# gercekler.py artık bu üstün eşikler için de "kilometre" gerçeği
# üretiyor (bkz. OLAGANUSTU_KILOMETRE_ESIKLERI). Bu sınıftaki bir
# gerçek maçta VARSA "tarihte/kariyer rekoru/ilk kez/en yüksek" gibi
# NİTELEYİCİ ifadeler serbest. AMA kesin bir SIRA/RANK iddiası
# ("tarihin ikinci en yüksek skoru", "3. en iyi performans") hâlâ HER
# ZAMAN reddedilir — bunu doğrulamak gerçek bir all-time sıralama
# veritabanı gerektirir, elimizde öyle bir kaynak yok.

CIFT_CIFT_DESENI = re.compile(r"\b(double-double|triple-double)\b", re.IGNORECASE)
CIFT_CIFT_KATEGORILER = ("sayi", "rib", "ast", "cal", "blk")
CIFT_CIFT_ESIK = {"double-double": 2, "triple-double": 3}

DOGRULANAMAZ_REKOR_DESENI = re.compile(
    r"kariyer\s+rekor\w*|sezon\s+rekor\w*|franchise\s+rekor\w*|"
    r"kulüp\s+rekor\w*|takım\s+rekor\w*|ilk\s+kez|tarihte|"
    r"kariyerinin\s+en\s+iyi\w*|en\s+yüksek\w*",
    re.IGNORECASE,
)

# Kesin sıra/rank iddiası — kilometre gerçeği olsa BİLE asla doğrulanamaz
# (gerçek bir all-time sıralama veritabanı gerektirir).
SIRA_IDDIASI_DESENI = re.compile(
    r"(en\s+yüksek|en\s+iyi)\s+\w*(inci|ıncı|üncü|uncu)\w*|"
    r"\d+\s*\.\s*(en\s+yüksek|en\s+iyi)|"
    r"tarihin\s+\w*(inci|ıncı|üncü|uncu)\w*",
    re.IGNORECASE,
)
# Kullanıcı düzeltmesi: eski desen çıplak "\d+\. sırada" da yakalıyordu —
# bu, "Denver, konferansta 3. sırada" gibi TAMAMEN doğrulanabilir bir
# GÜNCEL STANDINGS iddiasını (derece gerçeğinden gelen konferans_sira)
# "tarihin 2. en yüksek skoru" gibi doğrulanamaz bir ALL-TIME rekor
# iddiasıyla aynı kefeye koyuyordu — ikisi apayrı şeyler, biri elimizdeki
# veriyle doğrulanabilir, öbürü değil. "sırada" alternatifi kaldırıldı;
# geriye kalan iki alternatif (en yüksek/en iyi N'inci, tarihin N'inci)
# zaten gerçekten doğrulanamaz olan sınıfı kapsıyor.


def t18_cift_cift_dogru(metin, gercekler):
    sorunlu = []

    for m in SIRA_IDDIASI_DESENI.finditer(metin):
        sorunlu.append(
            f"'{m.group(0)}' kesin sıra/rank iddiası — all-time sıralama veritabanımız yok, "
            f"hiçbir kilometre kaydı bunu doğrulayamaz, HER ZAMAN reddedilir"
        )

    olaganustu_var = any(
        f["tur"] == "kilometre" and f["veri"].get("esik") in OLAGANUSTU_KILOMETRE_ESIKLERI
        for f in gercekler
    )
    if not olaganustu_var:
        for m in DOGRULANAMAZ_REKOR_DESENI.finditer(metin):
            sorunlu.append(
                f"'{m.group(0)}' doğrulanamaz kayıt/üstünlük iddiası — bu maçta hiçbir "
                f"oyuncu olağanüstü kilometre eşiğini (60+ sayı, 25+ ribaund, 20+ asist, "
                f"15+ üçlük, quadruple-double, 50+ sayılık triple-double) geçmedi, iddia kaynaksız"
            )

    oyuncu_stat = {f["veri"]["oyuncu"]: f["veri"] for f in gercekler if f["tur"] == "oyuncu_stat"}
    if oyuncu_stat:
        for cumle in cumlelere_ayir(metin):
            m = CIFT_CIFT_DESENI.search(cumle)
            if not m:
                continue
            iddia = m.group(1).lower()
            # cümledeki oyuncu adaylarını bul — en yakın (iddiaya en yakın
            # başlayan) oyuncu adı öznedir.
            en_yakin_oyuncu, en_yakin_pos = None, -1
            for oyuncu in oyuncu_stat:
                am = re.search(re.escape(oyuncu), cumle, re.IGNORECASE)
                if am and am.start() > en_yakin_pos and am.start() < m.start():
                    en_yakin_pos, en_yakin_oyuncu = am.start(), oyuncu
            if en_yakin_oyuncu is None:
                continue
            s = oyuncu_stat[en_yakin_oyuncu]
            cift_sayisi = sum(1 for k in CIFT_CIFT_KATEGORILER if s.get(k, 0) >= 10)
            if cift_sayisi < CIFT_CIFT_ESIK[iddia]:
                sorunlu.append(
                    f"'{en_yakin_oyuncu}' için '{iddia}' iddiası yanlış — gerçek istatistik "
                    f"sayı={s.get('sayi')}, rib={s.get('rib')}, ast={s.get('ast')}, "
                    f"cal={s.get('cal')}, blk={s.get('blk')} ({cift_sayisi} kategori 10+)"
                )
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# T15 — Sebep-sonuç mantık hatası: bir maçlık istatistik bir SEZON
# GENELİ sonucun (galibiyet/mağlubiyet serisi) "sebebi" gösterilemez
# ---------------------------------------------------------------------------
#
# Gerçek üretim hatası: "Day'Ron Sharpe 14 sayı 9 ribaundla mağlubiyet
# serisini üçe çıkardı" — bir oyuncunun TEK maçlık istatistiği takımın
# SEZON GENELİ serisinin nedeni olarak sunulmuş, oysa seri takımın
# sonucundan (galip/mağlup) türer, bir oyuncunun sayı/ribaund/asist
# çizgisinden değil. Ölçek karışıklığı — doğru olgular, yanlış
# bağlantı.

SEBEP_SONUC_DESENI = re.compile(
    r"\d+\s*(sayı|ribaund|asist|blok|top\s*çalma)\w*(la|le)\b"
    r"[^.!?]{0,40}?"
    r"(seri\w*\s+\w*|galibiyet\w*\s+serisi\w*|mağlubiyet\w*\s+serisi\w*)",
    re.IGNORECASE,
)


def t15_istatistik_seri_sebebi(metin):
    bulunan = [m.group(0) for m in SEBEP_SONUC_DESENI.finditer(metin)]
    return (len(bulunan) == 0, bulunan or None)


# ---------------------------------------------------------------------------
# T16 — Haber değeri eşikleri: doğru ama önemsiz olgular anılmasın
# ---------------------------------------------------------------------------
#
# Dil kılavuzu Bölüm 1 modele "bu eşiklerin altını anma" diyor ama
# talimat tek başına güvenilmez — mekanik olarak ölçülebilen üç eşik
# burada da denetleniyor: geri dönüş büyüklüğü, lider değişim sayısı,
# "üst üste" iddiasının gerçek seri uzunluğu. Sadece TALİMATLA
# BIRAKILIRSA modelin "10 sayının altı da ilginç" diye yazma riski var
# — bu üçü mekanik olarak ölçülebildiği için doğrulayıcıya da girdi.

LIDER_DEGISIM_ESIGI = 15
GERI_DONUS_ESIGI = 10
UST_USTE_ESIGI = 4  # kullanıcı düzeltmesi: 3 maçlık bir seri "seri" sayılmıyor,
# bir gecede aynı niteleyicinin (seri) sık sık tetiklenip tekdüzeliğe yol
# açması da bunu destekledi — eşik yükselince zaten daha az maç bu
# niteleyiciye uygun olacak, tekrar riski azalır.

LIDER_DEGISIM_SAYI_DESENI = re.compile(r"(\d+)\s*lider\s+değişim", re.IGNORECASE)
UST_USTE_DESENI = re.compile(
    r"üst\s+üste|art\s+arda|ardışık|arka\s+arka(ya)?|peş\s+peşe", re.IGNORECASE
)


def t16_haber_degeri_esigi(metin, gercekler, ham_mac):
    sorunlu = []

    for m in LIDER_DEGISIM_SAYI_DESENI.finditer(metin):
        sayi = int(m.group(1))
        if sayi < LIDER_DEGISIM_ESIGI:
            sorunlu.append(f"'{m.group(0)}' haber değeri eşiğinin altında (<{LIDER_DEGISIM_ESIGI})")

    for m in GERI_DONUS_DESENI.finditer(metin):
        cumle_baslangic = metin.rfind(".", 0, m.start()) + 1
        cumle_parcasi = metin[cumle_baslangic : m.start() + 40]
        sayilar = re.findall(r"\d+", cumle_parcasi)
        if sayilar and max(int(s) for s in sayilar) < GERI_DONUS_ESIGI:
            sorunlu.append(f"'{m.group(0)}' civarındaki geri dönüş {GERI_DONUS_ESIGI} sayının altında")

    if UST_USTE_DESENI.search(metin):
        seri_gercekleri = {f["veri"]["takim"]: f["veri"]["uzunluk"] for f in gercekler if f["tur"] == "seri"}
        # gercekler.py SADECE uzunluk>=2 olan serileri "seri" gerçeği
        # olarak kaydediyor (bkz. derece_ve_seri_gerceklerini_uret) —
        # yani bir takımın bu gerçek listesinde HİÇ kaydı yoksa, o
        # takımın serisi kesinlikle 2'nin altında (taze galibiyet/
        # mağlubiyet, henüz "seri" değil). "Üst üste" 3+ gerektirdiği
        # için kayıt yokluğu da eşiğin altında sayılmalı — yoksa bir
        # takımın YENİ kazandığı ama seriye dönüşmemiş galibiyetini
        # "üst üste" diye uydurmak bu testten kaçardı.
        skor_gercegi = next((f for f in gercekler if f["tur"] == "skor"), None)
        bilinen_takimlar = {skor_gercegi["veri"]["ev"], skor_gercegi["veri"]["dep"]} if skor_gercegi else set()
        aliaslar_by_bilinen = {kod: _takim_aliaslari(ham_mac, kod) for kod in bilinen_takimlar}
        for m in UST_USTE_DESENI.finditer(metin):
            en_yakin_kod = _en_yakin_ozne_takim(metin, m.start(), aliaslar_by_bilinen)
            if en_yakin_kod is None:
                continue
            uzunluk = seri_gercekleri.get(en_yakin_kod, 1)
            if uzunluk < UST_USTE_ESIGI:
                sorunlu.append(
                    f"'üst üste' iddiası ({en_yakin_kod}, seri uzunluğu {uzunluk}) "
                    f"{UST_USTE_ESIGI} eşiğinin altında"
                )

    sorunlu += _galibiyet_sirasi_dogrula(metin, gercekler, ham_mac)
    return (len(sorunlu) == 0, sorunlu or None)


# ---------------------------------------------------------------------------
# "N. galibiyetini alan" — N, takımın GERÇEK sezon galibiyet sayısıyla
# eşleşmek zorunda.
# ---------------------------------------------------------------------------
#
# Gerçek üretim hatası: "İkinci galibiyetini alan Wizards" — Washington
# o gece 9-24'tü, "ikinci" hiçbir şeye karşılık gelmiyordu. 2 maçlık
# seri yasağından ("üst üste" T16'da zaten reddediliyor) kaçarken model
# seriyi SEZON TOPLAMI GİBİ görünen bir ifadeyle ("N. galibiyeti")
# kaçırmıştı — iki farklı ölçek (seri uzunluğu vs. sezon galibiyet
# sayısı) birbirine karışmış. "galibiyet_sayisi_yuvarlak" niteleyicisi
# doğru N'yi (kd['galibiyet']) veriyor ama model bunun dışında da
# serbestçe "N. galibiyet" yazabiliyordu — artık mekanik doğrulanıyor.

_GALIBIYET_SIRA_BIRLER = {
    1: "birinci", 2: "ikinci", 3: "üçüncü", 4: "dördüncü", 5: "beşinci",
    6: "altıncı", 7: "yedinci", 8: "sekizinci", 9: "dokuzuncu",
}
_GALIBIYET_SIRA_ONLAR_CARDINAL = {
    1: "on", 2: "yirmi", 3: "otuz", 4: "kırk", 5: "elli", 6: "altmış", 7: "yetmiş", 8: "seksen",
}
_GALIBIYET_SIRA_ONLAR_ORDINAL = {
    1: "onuncu", 2: "yirminci", 3: "otuzuncu", 4: "kırkıncı", 5: "ellinci",
    6: "altmışıncı", 7: "yetmişinci", 8: "sekseninci",
}


def _galibiyet_sira_kelimesi(n):
    if n == 1:
        return "ilk"
    onlar, birler = divmod(n, 10)
    if onlar == 0:
        return _GALIBIYET_SIRA_BIRLER.get(birler)
    if birler == 0:
        return _GALIBIYET_SIRA_ONLAR_ORDINAL.get(onlar)
    if onlar not in _GALIBIYET_SIRA_ONLAR_CARDINAL or birler not in _GALIBIYET_SIRA_BIRLER:
        return None
    return f"{_GALIBIYET_SIRA_ONLAR_CARDINAL[onlar]} {_GALIBIYET_SIRA_BIRLER[birler]}"


# NBA sezonu 82 maç — kelime->sayı sözlüğü bu aralık için üretiliyor.
_GALIBIYET_SIRA_KELIME_TERS = {}
for _n in range(1, 83):
    _kelime = _galibiyet_sira_kelimesi(_n)
    if _kelime:
        _GALIBIYET_SIRA_KELIME_TERS[_kelime] = _n
del _n, _kelime

_GALIBIYET_SIRA_DESENI = re.compile(
    r"(?:(\d{1,2})\.|(" + "|".join(re.escape(k) for k in sorted(_GALIBIYET_SIRA_KELIME_TERS, key=len, reverse=True)) + r"))"
    r"\s+galibiyet\w*\s+(?:al\w*|kazan\w*)",
    re.IGNORECASE,
)


def _galibiyet_sirasi_dogrula(metin, gercekler, ham_mac):
    if not _GALIBIYET_SIRA_DESENI.search(metin):
        return []
    derece_by_takim = {f["veri"]["takim"]: f["veri"]["galibiyet"] for f in gercekler if f["tur"] == "derece"}
    if not derece_by_takim:
        return []
    skor_gercegi = next((f for f in gercekler if f["tur"] == "skor"), None)
    bilinen_takimlar = {skor_gercegi["veri"]["ev"], skor_gercegi["veri"]["dep"]} if skor_gercegi else set()
    aliaslar_by_bilinen = {kod: _takim_aliaslari(ham_mac, kod) for kod in bilinen_takimlar}

    sorunlu = []
    for m in _GALIBIYET_SIRA_DESENI.finditer(metin):
        # "üst üste üçüncü galibiyetini aldı" — burada sıra numarası
        # SERİ İÇİNDEKİ konumu anlatır (üst üste 3.), sezon toplamını
        # DEĞİL. Bu kalıp zaten UST_USTE_DESENI ile ayrı doğrulanıyor
        # (seri uzunluğuna karşı) — burada tekrar sezon toplamına karşı
        # denetlenirse yanlış pozitif üretir (gerçek üretim bug'ı).
        oncesi = metin[max(0, m.start() - 20) : m.start()]
        if UST_USTE_DESENI.search(oncesi):
            continue
        if m.group(1):
            n = int(m.group(1))
        else:
            # Python'un str.lower()'ı "İ"yi doğru çevirmiyor ("İ" -> "i̇",
            # iki karakterli bileşik) — "İkinci" gibi büyük harfle
            # başlayan bir ordinal kelimenin sözlük eşleşmesini
            # bozuyordu (gerçek üretim bug'ı, aynı sınıf T_yokluk_eki
            # düzeltmesiyle — bkz. kalip_secici._IYUUO_CEVIRI).
            kelime = m.group(2).translate(str.maketrans({"İ": "i", "I": "ı"})).lower()
            n = _GALIBIYET_SIRA_KELIME_TERS.get(kelime)
        if n is None:
            continue
        en_yakin_kod = _en_yakin_ozne_takim(metin, m.start(), aliaslar_by_bilinen)
        if en_yakin_kod is None:
            # "İkinci galibiyetini alan Wizards" gibi ortaç yapılarında
            # özne (takım adı) ordinal ifadenin ÖNCESİNDE değil
            # SONRASINDA gelir — geriye bakan arama bulamaz, cümle
            # sonuna kadar ileri de bakılmalı (gerçek üretim bug'ı: bu
            # yapı test edilmeden geçseydi asıl bug hiç yakalanmazdı).
            cumle_sonu = re.search(r"[.!?]", metin[m.end():])
            sinir = m.end() + (cumle_sonu.start() if cumle_sonu else len(metin) - m.end())
            sonrasi = metin[m.end():sinir]
            en_yakin_pos = None
            for etiket, aliaslar in aliaslar_by_bilinen.items():
                for alias in aliaslar:
                    am = re.search(re.escape(alias), sonrasi, re.IGNORECASE)
                    if am and (en_yakin_pos is None or am.start() < en_yakin_pos):
                        en_yakin_pos, en_yakin_kod = am.start(), etiket
        if en_yakin_kod is None:
            continue
        gercek_galibiyet = derece_by_takim.get(en_yakin_kod)
        if gercek_galibiyet is not None and gercek_galibiyet != n:
            sorunlu.append(
                f"'{m.group(0)}' iddiası yanlış — {en_yakin_kod}'nin gerçek sezon "
                f"galibiyet sayısı {gercek_galibiyet}, metindeki {n} değil"
            )
    return sorunlu


# ---------------------------------------------------------------------------
# Bir maçın tüm metnini doğrula (T1-T6, T8; T5 birleşik metne bakar)
# ---------------------------------------------------------------------------

ALAN_UZUNLUK_ADI = {
    "baslik": "baslik",
    "neden_onemli": "neden_onemli",
    "ozet": "ozet",
    "ozet_kisa": "ozet_kisa",
    "gec_satiri": "gec_satiri",
}


# Mutlaka bil gövde hedefi (kullanıcı kararı) — TEK KAYNAK.
OZET_CUMLE = 4
OZET_KELIME_ALT = 55
OZET_KELIME_UST = 75
OZET_KISA_KELIME_ALT = 30

EN_IYI_PERFORMANS_ESIKLERI = {"sayi": 30, "rib": 15, "ast": 10}


def _esigi_geciyor_mu(gercekler, en_iyi_performans):
    """En iyi performansın KENDİSİ bir haber değeri eşiğini geçiyor mu
    (30+ sayı, 15+ ribaund, 10+ asist). Geçmiyorsa T14 hiç devreye
    girmemeli — "sıradan bir maçta sade bitir" kuralı, 24 sayı 6
    ribaundluk vasat bir gecenin zorla cümleye sokulmasını önlüyor."""
    kayit = next(
        (f["veri"] for f in gercekler if f["tur"] == "oyuncu_stat" and f["veri"]["oyuncu"] == en_iyi_performans),
        None,
    )
    if kayit is None:
        return True  # kayıt bulunamadıysa eşik varsayımı yapmadan zorunlu tut
    return (
        kayit.get("sayi", 0) >= EN_IYI_PERFORMANS_ESIKLERI["sayi"]
        or kayit.get("rib", 0) >= EN_IYI_PERFORMANS_ESIKLERI["rib"]
        or kayit.get("ast", 0) >= EN_IYI_PERFORMANS_ESIKLERI["ast"]
    )


def t14_en_iyi_performans_anildi(tum_metin, en_iyi_performans, gercekler):
    """Kural: bir maçın hikaye metni, o maçın en yüksek GmSc'li
    performansını SADECE o performans kendisi bir haber değeri
    eşiğini geçiyorsa anmalı — kaybeden taraftan bir isim ancak
    ondan SONRA gelebilir (bkz. Lakers-Memphis bug'ı: kazanan tarafın
    34 sayılık en iyi performansı hiç geçmedi, kaybedenin 25 sayılık
    oyuncusu anıldı). Eşiğin altındaki vasat bir performans için bu
    zorunluluk kalkar — "sıradan maçta sade bitir" kuralı bunu ezer,
    yoksa model her sıradan gecede zorla bir isim sıkıştırıyordu
    (gerçek üretim bug'ı — ret oranını gereksiz şişirdi). `en_iyi_
    performans` verilmemişse test sessizce geçer."""
    if not en_iyi_performans or not tum_metin:
        return True, None
    if not _esigi_geciyor_mu(gercekler, en_iyi_performans):
        return True, None
    soyad = en_iyi_performans.strip().split()[-1]
    if soyad.lower() in tum_metin.lower():
        return True, None
    return False, en_iyi_performans


def mac_metnini_dogrula(metin, gercekler, ham_mac, haber_skoru, yasakli_liste, en_iyi_performans=None, sablon=False):
    sonuc = {"alanlar": {}, "gerekce": []}
    # DİKKAT: "and v" filtresi kaldırıldı — önceki hâli BOŞ bir alanı
    # (v == "") doğrulama kapsamının tamamen DIŞINA atıyordu, yani boş
    # metin hiçbir testten geçmeden "kabul" görüyordu (gerçek üretim
    # bug'ı: 11 gecelik toplu üretimde onlarca "gec_satiri" tamamen boş
    # yayınlandı). Alan `metin` sözlüğünde MEVCUTSA (anahtar var), boş
    # bile olsa doğrulamadan geçmeli — T6'daki asgari kelime kontrolü
    # onu şimdi doğru şekilde reddedecek.
    dolu_alanlar = {k: v for k, v in metin.items() if k in ALAN_UZUNLUK_ADI}

    hepsi_gecti = True
    for alan, deger in dolu_alanlar.items():
        gecti, testler = alan_dogrula(ALAN_UZUNLUK_ADI[alan], deger, gercekler, ham_mac, yasakli_liste, sablon=sablon)
        sonuc["alanlar"][alan] = {"gecti": gecti, "testler": testler}
        if not gecti:
            hepsi_gecti = False
            for tur, (t_gecti, detay) in testler.items():
                if not t_gecti:
                    sonuc["gerekce"].append(f"{alan}/{tur}: {detay}")

    tum_metin = " ".join(dolu_alanlar.values())
    if tum_metin:
        gecti5, detay5 = t5_kazanan(tum_metin, gercekler, ham_mac)
        sonuc["alanlar"]["T5"] = {"gecti": gecti5, "detay": detay5}
        if not gecti5:
            hepsi_gecti = False
            sonuc["gerekce"].append(f"T5: {detay5}")

        gecti14, detay14 = t14_en_iyi_performans_anildi(tum_metin, en_iyi_performans, gercekler)
        sonuc["alanlar"]["T14"] = {"gecti": gecti14, "detay": detay14}
        if not gecti14:
            hepsi_gecti = False
            sonuc["gerekce"].append(f"T14: en iyi performans ({detay14}) hiç anılmadı")

    muzip = metin.get("muzip", False)
    gecti8 = not (haber_skoru >= 6 and muzip)
    sonuc["alanlar"]["T8"] = {"gecti": gecti8}
    if not gecti8:
        hepsi_gecti = False
        sonuc["gerekce"].append("T8: haber_skoru>=6 iken muzip:true")

    sonuc["kabul"] = hepsi_gecti
    return sonuc


def brief_metnini_dogrula(brief_ogesi, gercekler, ham_mac, haber_skoru, yasakli_liste):
    metin = brief_ogesi.get("metin", "")
    gecti, testler = alan_dogrula("brief_metin", metin, gercekler, ham_mac, yasakli_liste)
    gerekce = [f"{tur}: {detay}" for tur, (t_gecti, detay) in testler.items() if not t_gecti]

    muzip = brief_ogesi.get("muzip", False)
    if haber_skoru >= 6 and muzip:
        gecti = False
        gerekce.append("T8: haber_skoru>=6 iken muzip:true")

    return {"kabul": gecti, "gerekce": gerekce, "testler": testler}


# ---------------------------------------------------------------------------
# T7 — Gece çapında muziplik sayacı
# ---------------------------------------------------------------------------


def t7_muziplik_sayaci(muzip_kayitlari):
    """muzip_kayitlari: [{'yer': str, 'mac_id': str|None, 'rozet': float}]
    Rozeti en düşük maçlardan başlayarak sıfırlanacakları döner."""
    if len(muzip_kayitlari) <= 3:
        return True, []
    rozetsiz = [k for k in muzip_kayitlari if k.get("rozet") is None]
    rozetli_sirali = sorted((k for k in muzip_kayitlari if k.get("rozet") is not None), key=lambda k: k["rozet"])
    sira = rozetli_sirali + rozetsiz
    sifirlanacak = sira[: len(muzip_kayitlari) - 3]
    return False, sifirlanacak


# ---------------------------------------------------------------------------
# Gece çapında orkestrasyon
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# T9 — Gece içi tekrar yasağı
# ---------------------------------------------------------------------------

OZEL_AD_KELIME_REGEX = re.compile(r"[^\W\d_]+")

# Basketbolda zamanı anlatmanın tek doğal yolu bu kelimeler — "üçüncü
# çeyrekte", "son dakikayı" gibi öbekler bir üslup tercihi değil, zorunlu
# kelime dağarcığı. T9 bunları tekrar sayımına katmıyor; ilk denemede
# katıyordu ve dil kılavuzunun kendi elle yazılmış örnek gecesini bile
# yanlışlıkla reddetti.
YAPISAL_ZAMAN_ONEK = {"ilk", "ikinci", "üçüncü", "dördüncü", "son", "bu", "o"}
YAPISAL_ZAMAN_ISIM = {
    "çeyrek", "çeyreği", "çeyrekte", "çeyreğe",
    "periyot", "periyotta",
    "dakika", "dakikayı", "dakikada", "dakikanın",
    "saniye", "saniyeyi", "saniyede", "saniyenin",
    "bölüm", "bölümü", "bölümde",
}


def _yapisal_zaman_ifadesi_mi(oybek_kelimeleri):
    if len(oybek_kelimeleri) != 2:
        return False
    onek, isim = (k.lower() for k in oybek_kelimeleri)
    return onek in YAPISAL_ZAMAN_ONEK and isim in YAPISAL_ZAMAN_ISIM


# Kaba kök sökücü — tam bir Türkçe morfolojik analiz DEĞİL, sadece T9'un
# "aynı öbek, farklı çekim" kaçırma riskini azaltmak için en yaygın ek
# kalıplarını sondan kırpar (uzun ekler önce, kısa stem'i yutmasın diye
# minimum 3 harf kalma şartı var). Gerçek bug: "mağlubiyete gömdü" ve
# "yenilgiye gömdü" aynı gecede iki ayrı metinde geçti ama tam eşleşme
# aradığı için T9 yakalamadı — kelimeler farklı ("mağlubiyet"/"yenilgi"
# eş anlamlı ama farklı kök, kök sökme bunu çözemez, o register
# yasağıyla ayrıca engellendi) ama "gömdü" gibi ortak fiillerin farklı
# çekimlerini (gömdü/gömerek/gömülü) tek köke indirmek T9'un asıl işi.
_KOK_SUFIKSLER = sorted(
    [
        "lerinden", "larından", "dığında", "tığında", "yordu", "ıyordu", "iyordu",
        "uyordu", "üyordu", "erek", "arak", "ecek", "acak", "meli", "malı",
        "miş", "mış", "müş", "muş", "ler", "lar", "dan", "den", "tan", "ten",
        "nın", "nin", "nun", "nün", "ının", "inin", "unun", "ünün",
        "ın", "in", "un", "ün", "na", "ne", "ya", "ye", "da", "de", "ta", "te",
        "yı", "yi", "yu", "yü", "dı", "di", "du", "dü", "tı", "ti", "tu", "tü",
        "ip", "ıp", "up", "üp", "yor", "ı", "i", "u", "ü", "e", "a",
    ],
    key=len,
    reverse=True,
)


def _kaba_kok(kelime):
    k = kelime.lower()
    for suf in _KOK_SUFIKSLER:
        if k.endswith(suf) and len(k) - len(suf) >= 3:
            return k[: -len(suf)]
    return k


def _tekrar_adaylari(metin, n):
    """metin içindeki n-kelimelik öbekleri döner — içinde sayı veya
    büyük harfle başlayan kelime (isim olasılığı) geçenler ve yapısal
    zaman ifadeleri ("üçüncü çeyrekte" gibi) HARİÇ. Karşılaştırma kaba
    kök üzerinden yapılır (bkz. _kaba_kok) ki "gömdü"/"gömerek" gibi
    farklı çekimler aynı tekrar sayılsın."""
    kelimeler = OZEL_AD_KELIME_REGEX.findall(metin)
    adaylar = []
    for i in range(len(kelimeler) - n + 1):
        oybek = kelimeler[i : i + n]
        if any(k[0].isupper() for k in oybek):
            continue
        if _yapisal_zaman_ifadesi_mi(oybek):
            continue
        adaylar.append(" ".join(_kaba_kok(k) for k in oybek))
    return adaylar


def t9_gece_ici_tekrar(metin_by_yer):
    """Bir sözcük öbeği (2+ kelime) gece boyunca birden fazla FARKLI
    metinde geçiyorsa yakalar — adlar (büyük harfli kelime içeren
    öbekler) ve sayı geçen öbekler (istatistik ifadeleri) hariç."""
    gorulen = {}  # oybek -> set(yer)
    for yer, metin in metin_by_yer.items():
        if not metin:
            continue
        for n in (2, 3):
            for oybek in _tekrar_adaylari(metin, n):
                gorulen.setdefault(oybek, set()).add(yer)

    tekrarlar = {oybek: sorted(yerler) for oybek, yerler in gorulen.items() if len(yerler) >= 2}
    return (len(tekrarlar) == 0, tekrarlar or None)


def _gece_metinlerini_topla(taslak):
    metin_by_yer = {}
    for gid, metin in taslak.get("maclar", {}).items():
        for alan in ALAN_UZUNLUK_ADI:
            if metin.get(alan):
                metin_by_yer[f"{gid}:{alan}"] = metin[alan]
    for i, brief_ogesi in enumerate(taslak.get("brief", [])):
        if brief_ogesi.get("metin"):
            metin_by_yer[f"brief[{i}]"] = brief_ogesi["metin"]
    return metin_by_yer


def gece_dogrula(taslak, gercek_gece, ham, skor_gece, haber_skorlari=None):
    """taslak: {'maclar': {gid: metin_obj}, 'brief': [brief_obj, ...]}
    haber_skorlari: {gid: int} — henüz kurulmamış bir mekanizmadan
    gelecek; verilmezse her maç için 0 varsayılır."""
    haber_skorlari = haber_skorlari or {}
    yasakli_liste = yasakli_yukle()
    rozetler = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}

    sonuc = {"maclar": {}, "brief": [], "t7": None, "kabul": True}

    muzip_kayitlari = []

    en_iyi_performans_by_gid = {m["mac_id"]: m.get("en_iyi_performans") for m in skor_gece["maclar"]}

    for gid, metin in taslak.get("maclar", {}).items():
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        haber_skoru = haber_skorlari.get(gid, 0)
        mac_sonucu = mac_metnini_dogrula(
            metin, gercekler, ham_mac, haber_skoru, yasakli_liste,
            en_iyi_performans=en_iyi_performans_by_gid.get(gid),
        )
        sonuc["maclar"][gid] = mac_sonucu
        if not mac_sonucu["kabul"]:
            sonuc["kabul"] = False
        for alan in ALAN_UZUNLUK_ADI:
            if metin.get("muzip") and metin.get(alan):
                muzip_kayitlari.append({"yer": f"{gid}:{alan}", "mac_id": gid, "rozet": rozetler.get(gid)})
                break  # maç başına bir kez say (muzip tek bayrak, alan başına değil)

    for i, brief_ogesi in enumerate(taslak.get("brief", [])):
        gid = brief_ogesi.get("hedef_mac")
        gercekler = gercek_gece["maclar"].get(gid, [])
        ham_mac = ham["maclar"].get(gid)
        haber_skoru = haber_skorlari.get(gid, 0)
        if ham_mac is None:
            brief_sonuc = {"kabul": False, "gerekce": ["hedef_mac ham veride yok"]}
        else:
            brief_sonuc = brief_metnini_dogrula(brief_ogesi, gercekler, ham_mac, haber_skoru, yasakli_liste)
        sonuc["brief"].append(brief_sonuc)
        if not brief_sonuc["kabul"]:
            sonuc["kabul"] = False
        if brief_ogesi.get("muzip"):
            muzip_kayitlari.append({"yer": f"brief[{i}]", "mac_id": gid, "rozet": rozetler.get(gid)})

    t7_gecti, sifirlanacak = t7_muziplik_sayaci(muzip_kayitlari)
    sonuc["t7"] = {"gecti": t7_gecti, "toplam_muzip": len(muzip_kayitlari), "sifirlanacak": sifirlanacak}
    if not t7_gecti:
        sonuc["kabul"] = False

    t9_gecti, tekrarlar = t9_gece_ici_tekrar(_gece_metinlerini_topla(taslak))
    sonuc["t9"] = {"gecti": t9_gecti, "tekrarlar": tekrarlar}
    if not t9_gecti:
        sonuc["kabul"] = False

    return sonuc


def _kayitli_gece_test_et(tarih, ham_json=False, sessiz=False):
    """API çağrısı YAPMADAN, daha önce üretilip taslak/{tarih}.json'a
    yazılmış metni güncel kurallarla yeniden doğrular — kural
    değişikliklerini (yeni eşik, yeni yasaklı ifade) para harcamadan,
    eski çıktılar üzerinde deneyebilmek için. Kullanıcı kararı: bir kural
    değiştiğinde ÖNCE bu çalıştırılmalı — yeni üretim SADECE "üretici
    artık daha iyi yazıyor mu" sorusu için gerekli, "yeni kural neyi
    yakalıyor" sorusu bununla, bedavaya ve anında cevaplanır."""
    taslak = json.loads((TASLAK_DIZIN / f"{tarih}.json").read_text())
    gercek_gece = json.loads((GERCEK_DIZIN / f"{tarih}.json").read_text())
    ham = json.loads((HAM_DIZIN / f"{tarih}.json").read_text())
    skor_gece = json.loads((SKOR_DIZIN / f"{tarih}.json").read_text())

    sonuc = gece_dogrula(taslak, gercek_gece, ham, skor_gece)

    if ham_json:
        print(json.dumps(sonuc, ensure_ascii=False, indent=2))
        return sonuc

    toplam = len(sonuc["maclar"]) + len(sonuc["brief"])
    red_sayisi = sum(1 for m in sonuc["maclar"].values() if not m["kabul"])
    red_sayisi += sum(1 for b in sonuc["brief"] if not b["kabul"])
    if not sessiz:
        print(f"{tarih}: {toplam - red_sayisi}/{toplam} kabul (mevcut kurallarla YENİDEN doğrulandı, API çağrısı yok)\n")

        for gid, mac_sonucu in sonuc["maclar"].items():
            if not mac_sonucu["kabul"]:
                print(f"[RET] maç {gid}")
                for g in mac_sonucu["gerekce"]:
                    print(f"       {g}")
        for i, brief_sonucu in enumerate(sonuc["brief"]):
            if not brief_sonucu["kabul"]:
                print(f"[RET] brief[{i}]")
                for g in brief_sonucu["gerekce"]:
                    print(f"       {g}")

        if not sonuc["t7"]["gecti"]:
            print(f"[RET] T7 — muziplik sınırı aşıldı: {sonuc['t7']}")
        if not sonuc["t9"]["gecti"]:
            print(f"[RET] T9 — gece içi tekrar: {sonuc['t9']['tekrarlar']}")

    return sonuc


_T_NUMARASI_DESENI = re.compile(r"\bT(\d+[a-z]?)\b")


def _kayitli_geceler_toplu_test_et(tarihler):
    """Birden fazla kayıtlı geceyi tek seferde yeniden doğrular ve
     agregatif olarak en çok tetikleyen 3 testi + kabul oranını basar —
    "bir kural değiştiğinde önce çevrimdışı doğrula" iş akışının ana
    aracı."""
    toplam_alan = toplam_kabul = 0
    test_sayaci = {}
    for tarih in tarihler:
        sonuc = _kayitli_gece_test_et(tarih, sessiz=True)
        for gid, mac_sonucu in sonuc["maclar"].items():
            toplam_alan += 1
            if mac_sonucu["kabul"]:
                toplam_kabul += 1
            else:
                for g in mac_sonucu["gerekce"]:
                    for m in _T_NUMARASI_DESENI.finditer(g):
                        anahtar = f"T{m.group(1)}"
                        test_sayaci[anahtar] = test_sayaci.get(anahtar, 0) + 1
        for brief_sonucu in sonuc["brief"]:
            toplam_alan += 1
            if brief_sonucu["kabul"]:
                toplam_kabul += 1
            else:
                for g in brief_sonucu["gerekce"]:
                    for m in _T_NUMARASI_DESENI.finditer(g):
                        anahtar = f"T{m.group(1)}"
                        test_sayaci[anahtar] = test_sayaci.get(anahtar, 0) + 1
        durum = "TAMAM" if sonuc["kabul"] else "RET VAR"
        print(f"  {tarih}: {durum}")

    print(f"\n{len(tarihler)} gece, {toplam_alan} alan, {toplam_kabul}/{toplam_alan} güncel kurallarla kabul")
    en_cok = sorted(test_sayaci.items(), key=lambda kv: -kv[1])[:3]
    if en_cok:
        print("En çok tetikleyen testler: " + ", ".join(f"{ad} ({n}x)" for ad, n in en_cok))
    else:
        print("Hiçbir test tetiklenmedi — tüm kayıtlı geceler güncel kurallarla da geçiyor.")


if __name__ == "__main__":
    import argparse

    ayristirici = argparse.ArgumentParser(
        description="Kayıtlı taslak/{tarih}.json dosyalarını güncel dogrula.py kurallarıyla, "
        "API çağrısı yapmadan yeniden doğrular. Bir kural/eşik/yasaklı ifade değiştiğinde "
        "yeni üretim yapmadan ÖNCE bu çalıştırılmalı."
    )
    ayristirici.add_argument("tarih", nargs="*", help="YYYY-MM-DD (birden fazla verilebilir) — taslak/{tarih}.json zaten var olmalı")
    ayristirici.add_argument("--hepsi", action="store_true", help="taslak/ altındaki TÜM geceleri test et")
    ayristirici.add_argument("--ham-json", action="store_true", help="Özet yerine ham JSON çıktısı ver (tek tarih için)")
    args = ayristirici.parse_args()

    if args.hepsi:
        _TARIH_DESENI = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        tarihler = sorted(p.stem for p in TASLAK_DIZIN.glob("*.json") if _TARIH_DESENI.match(p.stem))
    else:
        tarihler = args.tarih

    if not tarihler:
        raise SystemExit("En az bir tarih ver, ya da --hepsi kullan.")

    if len(tarihler) == 1 and not args.hepsi:
        _kayitli_gece_test_et(tarihler[0], ham_json=args.ham_json)
    else:
        _kayitli_geceler_toplu_test_et(tarihler)
