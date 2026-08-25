"""
kalip_secici.py — OVERNIGHT'ın kanca/kademe/niteleyici SEÇİM motoru.

overnight-kalip-kutuphanesi.md'nin bölüm 2 (kanca bankası), 3 (niteleyici
bankası) ve 5'ini (zenginlik kademeleri) koda döker. Kullanıcı kararı:
seçimi artık MODEL DEĞİL KOD yapar — model sadece verilen iskelete,
kancaya ve niteleyicilere cümle kurar.

Bu dosya SADECE seçim yapar, metin üretmez. `yaz.py`'ye henüz
bağlanmadı — önce dağılımın mantıklı olduğu onaylanacak.
"""

import json
from pathlib import Path

from dogrula import (
    EN_IYI_PERFORMANS_ESIKLERI,
    GERI_DONUS_ESIGI,
    LIDER_DEGISIM_ESIGI,
    UST_USTE_ESIGI,
)
from hesapla import takim_kalitesi_hesapla, takim_kalite_puani
from gercekler import clock_saniye
import cumle

KOK = Path(__file__).parent
GERCEK_DIZIN = KOK / "gercek"
HAM_DIZIN = KOK / "ham"
SKOR_DIZIN = KOK / "skor"
CONFIG_DIZIN = KOK / "config"

FARK_ESIGI = 20  # "farklı galibiyet" — dil kılavuzu haber değeri tablosu
PLAY_IN_ARALIGI = (6, 11)  # konferans sırası — kabaca play-in bandı

# Seri haber değeri, takım kalitesine göre SÜRPRİZ olup olmadığına bağlı
# (kullanıcı düzeltmesi — kaybedenin mağlubiyet serisini kaldırınca
# ortaya çıkan aynalı hata: OKC gibi 30-5'lik bir takımın galibiyet
# serisi de "beklenen", haber değil). A_hesapla'nın kullandığı AYNI
# takım kalitesi yüzdeliği (0-10, geceden ÖNCEKİ sezon averajından)
# burada da kullanılıyor — iki ayrı kalite tanımı olmasın.
IYI_TAKIM_ESIGI = 7.0
KOTU_TAKIM_ESIGI = 3.0
REKOR_BOLGESI_ESIGI = 15  # BEKLENEN yönde bir seri sadece bu uzunlukta haber olur

# S = sürpriz sonuç, P = bireysel patlama — kullanıcı düzeltmesi (25 Aralık
# gecesi): eski A-H seti SADECE maçın nasıl bittiğini (drama) ve takım
# hikayelerini kapsıyordu, "bu SONUÇ ne kadar önemli" ve "bu gece bir
# oyuncu ne kadar olağanüstü bir şey yaptı" için hiç kategori yoktu.
# Somut örnekler: (1) ligin lideri 8 maçlık seri süren bir rakibe kaybetti
# ama formül bunu "fakir" işaretledi — sonucun kendi önemini ölçen hiçbir
# bileşen yoktu. (2) Jokić'in 56/16/15'lik gecesi hiçbir A-F kategorisine
# uymayınca G'ye (gece sırası) düştü, metin "Türkiye saatiyle gecenin en
# geç maçında" diye açıldı — gecenin asıl hikayesi zaman değil performanstı.
# P, G'nin ÖNÜNDE olmalı (kullanıcı kuralı: "bireysel patlama kancası
# zaman kancasının önünde olmalı").
# Z = zirve maçı — S'den (sürpriz sonuç) ayrı bir kavram (kullanıcı
# düzeltmesi, 2. tur): S artık SADECE kalite farkına dayalı gerçek
# sürprizler için, Z konferansın üst sıralarındaki iki takımın
# doğrudan çarpışması için — anlatım dili de ayrı ("sürpriz yenilgi"
# demek San Antonio gibi güçlü bir takım için yanlış).
KANCA_ONCELIK = ["A", "S", "Z", "P", "B", "C", "D", "F", "G", "H"]
# Kullanıcı kararı (radikal küçültme turu): "E" (yıldız yokluğu) kancası
# önceliklerden ÇIKARILDI — "Nembhard'sız sahaya çıkan Indiana..." gibi
# bir çerçeve artık kabul edilen üç içerik türünden (Sonuç/An/Performans)
# hiçbirine girmiyor; bir oyuncunun YOKLUĞU maçın SONUCUYLA ilgili bir
# olgu değil, bağlamsal bir not. kanca_degerlendir'deki "E" dalı KOD
# OLARAK duruyor (silinmedi), sadece artık hiç seçilmiyor.


# ---------------------------------------------------------------------------
# Yıldız kademeleri
# ---------------------------------------------------------------------------


def yildizlar_yukle():
    dosya = CONFIG_DIZIN / "yildizlar.json"
    if not dosya.exists():
        return {}
    ham = json.loads(dosya.read_text())
    import unicodedata

    def katla(s):
        return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()

    return {katla(o["ad"]): min(o["kuresel"], o["turkiye"]) for o in ham.get("oyuncular", [])}


def yildiz_kademesi(yildizlar, oyuncu_adi):
    import unicodedata

    def katla(s):
        return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()

    return yildizlar.get(katla(oyuncu_adi), 3)  # listede yoksa kademe 3 (varsayılan)


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def _fact(gercekler, tur):
    return [f for f in gercekler if f["tur"] == tur]


def _tek(gercekler, tur):
    l = _fact(gercekler, tur)
    return l[0]["veri"] if l else None


def _oyuncu_stat_listesi(gercekler):
    return [f["veri"] for f in gercekler if f["tur"] == "oyuncu_stat"]


def _tip_off_sirasi(ham_mac):
    bs = ham_mac["box_summary"]
    gs = next(rs for rs in bs["resultSets"] if rs["name"] == "GameSummary")
    row = gs["rowSet"][0]
    return dict(zip(gs["headers"], row))["GAME_SEQUENCE"]




def seri_haber_degeri_mi(kod, tur, uzunluk, kalite_ort, kalite_sirali):
    """Kural: bir seri, takım kalitesine göre SÜRPRİZ olduğunda haberdir
    (OLGU — kademeyi belirler). İyi takımın galibiyet serisi ya da kötü
    takımın mağlubiyet serisi BEKLENEN — olgu değil, ama niteleyici
    malzemesi olarak kalır (bkz. niteleyici_bankasi, "Üst üste N.
    galibiyetini alan" orada koşulsuz üretilir).

    İlk sürümün hatası: "6+ maçlık her seri kalite fark etmeksizin
    haber" istisnası yanlıştı — 8-28'lik bir takımın 6, 6-29'luk bir
    takımın 11 maç kaybetmesi sürprizin TAM TERSİ, beklenenin en saf
    hâli. Doğru istisna: BEKLENEN yöndeki bir seri ancak REKOR
    BÖLGESİNE (15+) yaklaşınca kendi başına haber olur — kalite ne
    olursa olsun 15 maçlık bir seri konuşulur. SÜRPRİZ yöndeki seriler
    zaten uzunluğa bakılmaksızın (3+) olgu."""
    if uzunluk < UST_USTE_ESIGI:
        return False
    kalite = takim_kalite_puani(kod, kalite_ort, kalite_sirali)
    surpriz = kalite < IYI_TAKIM_ESIGI if tur == "galibiyet" else kalite > KOTU_TAKIM_ESIGI
    if surpriz:
        return True
    return uzunluk >= REKOR_BOLGESI_ESIGI


# "Sürpriz sonuç" (S kancası + kademe olgusu) — kullanıcı düzeltmesi (2.
# tur): eski tanım üç ayrı tetikleyiciyi TEK bir "sürpriz" etiketinde
# topluyordu, ama bunlardan biri ("kaybeden lig lideri/ilk-3") aslında
# sürpriz DEĞİL — San Antonio (Batı'nın en iyilerinden biri) OKC'yi
# yendiğinde bu sürpriz değil, iki üst takımın maçı demek (bkz. ZİRVE
# MAÇI, aşağıda, ayrı bir kavram). Gerçek sürpriz SADECE kalite
# farkından doğar: kötü bir takım iyi bir takımı yendiyse. A
# bileşenindeki AYNI kalite eşikleri kullanılıyor (KOTU_TAKIM_ESIGI/
# IYI_TAKIM_ESIGI) — iki ayrı kalite tanımı olmasın diye.
def _surpriz_sonuc_belirle(kazanan_kalite, kaybeden_kalite):
    if kaybeden_kalite >= IYI_TAKIM_ESIGI and kazanan_kalite <= KOTU_TAKIM_ESIGI:
        return True, "belirgin şekilde kötü bir takım, belirgin şekilde iyi bir takımı yendi"
    return False, ""


# "Zirve maçı" (Z kancası + kademe olgusu) — YENİ, sürpriz sonuçtan
# ayrı bir kavram (kullanıcı düzeltmesi): konferansın üst sıralarındaki
# iki takım karşı karşıya geldiğinde bu bir SÜRPRİZ değil, iki güçlü
# takımın doğrudan çarpışması — anlatım dili de farklı olmalı
# ("sürpriz yenilgi" değil, "Batı'nın iki üst takımı karşı karşıya
# geldi" gibi).
def _zirve_maci_belirle(kazanan_derece, kaybeden_derece):
    kaz_sira = kazanan_derece.get("konferans_sira")
    kay_sira = kaybeden_derece.get("konferans_sira")
    if kaz_sira is None or kay_sira is None or kaz_sira > 3 or kay_sira > 3:
        return False, ""
    konferans = kazanan_derece.get("konferans") or kaybeden_derece.get("konferans") or ""
    return True, f"{konferans}'nın zirvesi ({kaz_sira}. ve {kay_sira}. sıralar)"


# Bir maçtaki EN etkileyici kilometre gerçeği — birden fazla eşik aynı
# oyuncu için birden geçerli olabilir (56 sayılık bir triple-double hem
# "50_sayi" hem "triple_double" hem "50_triple_double" olarak ayrı ayrı
# kayıtlıdır), P kancası ve brief için en güçlüsü seçilmeli.
_KILOMETRE_ONCELIK = [
    "80_sayi", "quadruple_double", "50_triple_double", "60_sayi", "25_ribaund", "20_asist", "15_uclu",
    "triple_double", "50_sayi", "20_ribaund", "10_uclu", "5_blok", "40_sayi",
]


def en_iyi_kilometre(kilometre_list):
    """Kullanıcı kuralı: bir maçta AYNI eşiği birden fazla oyuncu geçmişse
    (ör. iki triple-double) metin EN YÜKSEK GmSc'liyi anar. Eski sürüm
    sözlüğe son yazanı alıyordu — gerçek üretim bug'ı: SAS-GSW maçında
    Wembanyama 31/15/10 yapmışken metin Castle'ın 23/10/10'unu andı."""
    if not kilometre_list:
        return None
    by_esik = {}
    for k in kilometre_list:
        mevcut = by_esik.get(k["esik"])
        if mevcut is None or k.get("gmsc", 0) > mevcut.get("gmsc", 0):
            by_esik[k["esik"]] = k
    for esik in _KILOMETRE_ONCELIK:
        if esik in by_esik:
            return by_esik[esik]
    return max(kilometre_list, key=lambda k: k.get("gmsc", 0))


KARAR_ANI_ESIK_SANIYE = 24  # bitime bu kadar saniye kala/altında olan
# lider değişimi "karar anı" (son saniye basketi) sayılır.


def _karar_ani_bul(gercekler, ev_kod, kazanan_kod):
    """Maçı fiilen karara bağlayan son basket — son periyottaki EN SON
    lider değişimi "an"ı, eğer kazananı öne geçirdiyse VE bitime
    KARAR_ANI_ESIK_SANIYE içindeyse. A kancasının en güçlü sinyali
    (kullanıcı önceliği: son saniye basketi > 1-2 sayılık final >
    uzatma > lider değişimi)."""
    anlar = [f["veri"] for f in gercekler if f["tur"] == "an" and f["veri"].get("tur_alt") == "lider_degisimi"]
    if not anlar:
        return None
    son_periyot = max(a["periyot"] for a in anlar)
    aday = [a for a in anlar if a["periyot"] == son_periyot]
    if not aday:
        return None
    son_an = min(aday, key=lambda a: clock_saniye(a["saat"]))
    saniye_kalan = clock_saniye(son_an["saat"])
    if saniye_kalan > KARAR_ANI_ESIK_SANIYE:
        return None
    kazanan_onde_bu_anda = (son_an["fark"] > 0) == (kazanan_kod == ev_kod)
    if not kazanan_onde_bu_anda:
        return None
    return {"periyot": son_an["periyot"], "saniye_kalan": saniye_kalan, "aciklama": son_an["aciklama"]}


# ---------------------------------------------------------------------------
# Olgu hesaplama — bir maç için hesaplanabilir HER ŞEY
# ---------------------------------------------------------------------------


def olgulari_hesapla(gercekler, ham_mac, haber_skoru, yildizlar, kalite_ort, kalite_sirali):
    skor = _tek(gercekler, "skor")
    kazanan = skor["kazanan"]
    kaybeden = skor["dep"] if kazanan == skor["ev"] else skor["ev"]

    fs = _tek(gercekler, "fark_serisi") or {}
    derece_by_takim = {f["veri"]["takim"]: f["veri"] for f in _fact(gercekler, "derece")}
    seri_by_takim = {f["veri"]["takim"]: f["veri"] for f in _fact(gercekler, "seri")}
    kadro_disi = _fact(gercekler, "kadro_disi")
    kilometre = _fact(gercekler, "kilometre")
    oyuncu_stat = _oyuncu_stat_listesi(gercekler)
    ceyrekler = [f["veri"] for f in _fact(gercekler, "ceyrek")]

    kazanan_derece = derece_by_takim.get(kazanan, {})
    kaybeden_derece = derece_by_takim.get(kaybeden, {})
    kazanan_seri = seri_by_takim.get(kazanan)
    kaybeden_seri = seri_by_takim.get(kaybeden)
    kazanan_kadro_disi = [k["veri"] for k in kadro_disi if k["veri"]["takim"] == kazanan]
    kaybeden_kadro_disi = [k["veri"] for k in kadro_disi if k["veri"]["takim"] == kaybeden]

    fark = skor["fark"]
    uzatma = len(ceyrekler) > 4
    son_periyot_lider_degisim = fs.get("son_periyot_lider_degisimi", 0)

    kazanan_yildiz_yok = [
        k["oyuncu"] for k in kazanan_kadro_disi if yildiz_kademesi(yildizlar, k["oyuncu"]) <= 2
    ]

    en_yuksek_sayi = max((s.get("sayi", 0) for s in oyuncu_stat), default=0)
    triple_double_var = any(k["veri"]["esik"] == "triple_double" for k in kilometre)

    # Seri haber değeri — takım kalitesine göre sürpriz mi (kullanıcı
    # kuralı, bkz. seri_haber_degeri_mi docstring).
    kazanan_seri_haber = bool(kazanan_seri) and seri_haber_degeri_mi(
        kazanan, kazanan_seri["tur"], kazanan_seri["uzunluk"], kalite_ort, kalite_sirali
    )
    kaybeden_seri_haber = bool(kaybeden_seri) and seri_haber_degeri_mi(
        kaybeden, kaybeden_seri["tur"], kaybeden_seri["uzunluk"], kalite_ort, kalite_sirali
    )

    kazanan_kalite = takim_kalite_puani(kazanan, kalite_ort, kalite_sirali)
    kaybeden_kalite = takim_kalite_puani(kaybeden, kalite_ort, kalite_sirali)
    # Kullanıcı kararı (sezon başı susma kuralı): kalite verisi yokken
    # (her iki takım da 10 maçın altındaysa) kimin favori olduğunu
    # bilemeyiz — "sürpriz" iddiası iki takımın da güvenilir bir sezon
    # örneklemi olmasını gerektirir.
    if kazanan_derece.get("sezon_guvenilir") and kaybeden_derece.get("sezon_guvenilir"):
        surpriz_sonuc, surpriz_gerekce = _surpriz_sonuc_belirle(kazanan_kalite, kaybeden_kalite)
    else:
        surpriz_sonuc, surpriz_gerekce = False, ""
    zirve_maci, zirve_gerekce = _zirve_maci_belirle(kazanan_derece, kaybeden_derece)
    kilometre_veri = [k["veri"] for k in kilometre]
    en_iyi_kilometre_gercegi = en_iyi_kilometre(kilometre_veri)

    return {
        "kazanan": kazanan,
        "kaybeden": kaybeden,
        "ev": skor["ev"],
        "dep": skor["dep"],
        "fark": fark,
        "uzatma": uzatma,
        "en_buyuk_geri_donus": fs.get("kazanan_en_buyuk_acigi", 0),
        "lider_degisim": fs.get("lider_degisim_sayisi", 0),
        "son_periyot_lider_degisim": son_periyot_lider_degisim,
        "kazanan_derece": kazanan_derece,
        "kaybeden_derece": kaybeden_derece,
        "kazanan_seri": kazanan_seri,
        "kaybeden_seri": kaybeden_seri,
        "kazanan_seri_haber": kazanan_seri_haber,
        "kaybeden_seri_haber": kaybeden_seri_haber,
        "kazanan_kalite": kazanan_kalite,
        "kaybeden_kalite": kaybeden_kalite,
        "surpriz_sonuc": surpriz_sonuc,
        "surpriz_gerekce": surpriz_gerekce,
        "zirve_maci": zirve_maci,
        "zirve_gerekce": zirve_gerekce,
        "kazanan_kadro_disi": kazanan_kadro_disi,
        "kaybeden_kadro_disi": kaybeden_kadro_disi,
        "kazanan_yildiz_yok": kazanan_yildiz_yok,
        "kilometre": kilometre_veri,
        "en_iyi_kilometre": en_iyi_kilometre_gercegi,
        "triple_double_var": triple_double_var,
        "en_yuksek_sayi": en_yuksek_sayi,
        "en_iyi_bireysel_esik": [
            (s["oyuncu"], "sayi", s["sayi"]) for s in oyuncu_stat if s.get("sayi", 0) >= EN_IYI_PERFORMANS_ESIKLERI["sayi"]
        ] + [
            (s["oyuncu"], "rib", s["rib"]) for s in oyuncu_stat if s.get("rib", 0) >= EN_IYI_PERFORMANS_ESIKLERI["rib"]
        ] + [
            (s["oyuncu"], "ast", s["ast"]) for s in oyuncu_stat if s.get("ast", 0) >= EN_IYI_PERFORMANS_ESIKLERI["ast"]
        ],
        "haber_skoru": haber_skoru,
        "ceyrek_farklari": [
            {
                "periyot": c["periyot"],
                # DAİMA kazananın o çeyrekteki net üstünlüğü — ham ev-dep
                # farkı değil (kazanan deplasmandaysa ters işaretli çıkardı,
                # gerçek bug — bkz. commit notu).
                "fark": (c["ev_ceyrek_sayisi"] - c["dep_ceyrek_sayisi"]) * (1 if kazanan == c["ev"] else -1),
            }
            for c in ceyrekler
        ],
        "tip_off_sira": _tip_off_sirasi(ham_mac),
        "karar_ani": _karar_ani_bul(gercekler, skor["ev"], kazanan),
    }


# ---------------------------------------------------------------------------
# Kademe (bölüm 5) — SADECE 9 onaylı haber değeri olgusu sayılır.
# "Üst üste 2. galibiyet" / "galibiyet sayısını N'e yükseltti" gibi HER
# maçta hesaplanabilen şeyler olgu DEĞİL, niteleyici malzemesidir —
# kademeyi belirlemez (kullanıcı düzeltmesi: ilk sürüm 10 maçın 9'unu
# "zengin" işaretlemişti çünkü serbest atış/üçlük/haber_skoru gibi zayıf
# sinyalleri de sayıyordu).
# ---------------------------------------------------------------------------


def kademe_hesapla(olgu):
    olgular = []

    if olgu["en_buyuk_geri_donus"] >= GERI_DONUS_ESIGI:
        olgular.append(f"geri dönüş {olgu['en_buyuk_geri_donus']}")
    if olgu["lider_degisim"] >= LIDER_DEGISIM_ESIGI:
        olgular.append(f"lider değişim {olgu['lider_degisim']}")
    if olgu["uzatma"]:
        olgular.append("uzatma")
    elif olgu["fark"] <= 3 and olgu["son_periyot_lider_degisim"] >= 1:
        olgular.append("son hücumda belli oldu")
    # Seri, TAKIM KALİTESİNE göre sürprizse olgu (kullanıcı kuralı —
    # aynaya iki kez çarptık: önce kaybedenin mağlubiyet serisini
    # koşulsuz sayıp "kötü takım kaybetmeye devam ediyor"yu haber
    # saydık, düzeltince bu kez kazananın galibiyet serisini koşulsuz
    # sayıp "iyi takım kazanmaya devam ediyor"yu haber saydık — ikisi de
    # aynı hata, ters yönde. Kural artık simetrik: iyi takımın galibiyeti
    # ve kötü takımın mağlubiyeti beklenen, sayılmaz; tersi sürpriz,
    # sayılır; 6+ maçlık her seri kalite fark etmeksizin sayılır.
    if olgu["kazanan_seri_haber"]:
        olgular.append(f"kazananın {olgu['kazanan_seri']['uzunluk']} maçlık galibiyet serisi (sürpriz)")
    if olgu["kaybeden_seri_haber"]:
        olgular.append(f"kaybedenin {olgu['kaybeden_seri']['uzunluk']} maçlık mağlubiyet serisi (sürpriz)")
    # "30+ sayı" tek başına ayırt edici değil (neredeyse her gece biri
    # atıyor) — SADECE gerçekten nadir eşikler (kilometre gerçeği: 50+
    # sayı, triple-double, 20+ ribaund, 10+ üçlük, 5+ blok) sayılır.
    if olgu["kilometre"]:
        olgular.append(f"kilometre taşı: {', '.join(k['esik'] for k in olgu['kilometre'])}")
    if olgu["kazanan_yildiz_yok"]:
        olgular.append(f"yıldız yokluğu: {', '.join(olgu['kazanan_yildiz_yok'])}")
    if olgu.get("surpriz_sonuc"):
        olgular.append(f"sürpriz sonuç: {olgu['surpriz_gerekce']}")
    if olgu.get("zirve_maci"):
        olgular.append(f"zirve maçı: {olgu['zirve_gerekce']}")
    if _dogrudan_siralama_etkisi(olgu):
        olgular.append("doğrudan sıralama etkisi")
    if olgu["fark"] >= FARK_ESIGI:
        olgular.append(f"fark {olgu['fark']}")

    if len(olgular) == 0:
        return "fakir", olgular
    if len(olgular) == 1:
        return "orta", olgular
    return "zengin", olgular


def _dogrudan_siralama_etkisi(olgu):
    kd = olgu["kazanan_derece"]
    # Kullanıcı kararı (sezon başı susma kuralı): derece güvenilir
    # değilse ("sezon_guvenilir" False, <10 maç) bu olgu hiç sayılmaz —
    # aksi halde 1-0'lık bir takımın "namağlup"luğu yanlışlıkla maçı
    # "zengin" (yüksek haber değeri) tier'ine taşıyabilirdi.
    if not kd.get("sezon_guvenilir"):
        return False
    lig_sira = kd.get("lig_sira")
    namaglup = kd.get("maglubiyet") == 0
    esit_derece = kd.get("galibiyet") == olgu["kaybeden_derece"].get("galibiyet")
    kaz_sira = kd.get("konferans_sira")
    kay_sira = olgu["kaybeden_derece"].get("konferans_sira")
    play_in = (
        kaz_sira is not None
        and kay_sira is not None
        and PLAY_IN_ARALIGI[0] <= kaz_sira <= PLAY_IN_ARALIGI[1]
        and PLAY_IN_ARALIGI[0] <= kay_sira <= PLAY_IN_ARALIGI[1]
    )
    return lig_sira == 1 or namaglup or esit_derece or play_in


# ---------------------------------------------------------------------------
# Kanca uygunluğu + gücü (bölüm 2) — her kategori için (uygun_mu, güç, gerekçe)
# ---------------------------------------------------------------------------


def kanca_degerlendir(kategori, olgu):
    if kategori == "A":
        # Öncelik (kullanıcı kuralı): son saniye basketi > 1-2 sayılık
        # final > uzatma > lider değişimi. İlk sürüm bunu tersten
        # yapıyordu — MIL-CHA'da 1 sayılık final + son saniye basketi
        # varken zayıf "5 lider değişimi" sinyalini seçmişti.
        if olgu["karar_ani"]:
            ka = olgu["karar_ani"]
            guc = 4000 - ka["saniye_kalan"]
            return True, guc, f"maçı bitiren basket, bitime {ka['saniye_kalan']:.1f} saniye kala"
        if olgu["fark"] <= 2:
            guc = 3000 - olgu["fark"] * 100
            return True, guc, f"{olgu['fark']} sayılık farkla bitti"
        if olgu["uzatma"]:
            return True, 2000, "uzatma"
        if olgu["fark"] <= 3 and olgu["son_periyot_lider_degisim"] >= 1:
            guc = olgu["son_periyot_lider_degisim"] * 10 + max(0, 10 - olgu["fark"])
            # DİKKAT: el değiştiren LİDERLİKTİR, maç değil (kullanıcı
            # düzeltmesi — model "beş kez el değiştiren maç" gibi
            # hatalı bir ifade üretmişti çünkü bu gerekçe metni buna
            # zemin hazırlıyordu).
            return True, guc, f"son periyotta liderliğin {olgu['son_periyot_lider_degisim']} kez el değiştirdiği, {olgu['fark']} farkla biten maç"
        return False, 0, ""

    if kategori == "S":
        # Sürpriz sonuç — SADECE kalite farkına dayalı gerçek sürprizler
        # (bkz. _surpriz_sonuc_belirle). Güç, kalite farkıyla artar — ne
        # kadar büyük üst, o kadar güçlü kanca.
        if not olgu.get("surpriz_sonuc"):
            return False, 0, ""
        guc = 600
        kalite_farki = olgu["kaybeden_kalite"] - olgu["kazanan_kalite"]
        if kalite_farki > 0:
            guc += kalite_farki * 60
        return True, guc, f"sürpriz sonuç: {olgu['surpriz_gerekce']}"

    if kategori == "Z":
        # Zirve maçı — kullanıcı örneği: San Antonio (Batı'nın en
        # iyilerinden biri) OKC'yi (lig lideri) yendi; bu SÜRPRİZ değil,
        # iki üst takımın doğrudan çarpışması. Güç, iki takımın sırası
        # ne kadar üst (1'e ne kadar yakın) o kadar artar.
        if not olgu.get("zirve_maci"):
            return False, 0, ""
        kaz_sira = olgu["kazanan_derece"].get("konferans_sira", 3)
        kay_sira = olgu["kaybeden_derece"].get("konferans_sira", 3)
        guc = 500 - (kaz_sira + kay_sira) * 20
        return True, guc, f"zirve maçı: {olgu['zirve_gerekce']}"

    if kategori == "P":
        # Bireysel patlama — kullanıcı kuralı: bir oyuncunun olağanüstü
        # gecesi (kilometre eşiği geçmiş) zaman kancasının (G) ÖNÜNDE
        # değerlendirilmeli, hiçbir A-F kategorisine uymayan maçlar bile
        # "gecenin en geç maçında" gibi sıradan bir açılışa düşmesin.
        if not olgu.get("kilometre"):
            return False, 0, ""
        kilo = olgu.get("en_iyi_kilometre")
        # Gerçek üretim bug'ı: "en_yuksek_sayi" MAÇTAKİ herhangi bir
        # oyuncunun sayısıydı, kilometreyi geçen oyuncunun KENDİ sayısı
        # değil — bir maçta biri triple-double yaparken BAŞKA biri çok
        # sayı atmışsa güç yanlışlıkla şişiyordu. Somut örnek: Adebayo'nın
        # 83 sayılık (NBA tarihinde ikinci en yüksek) gecesi, aynı gece
        # başka bir maçta biri 41 sayı atarken bir üçüncüsü triple-double
        # yapınca (güce Adebayo'nunkiyle alakasız 41 ekleniyordu) kanca
        # yarışını kaybetmişti. Artık kilometreyi geçen oyuncunun KENDİ
        # sayısı kullanılıyor.
        guc = 300 + (kilo.get("sayi", 0) if kilo else 0)
        if olgu.get("triple_double_var"):
            guc += 200
        if kilo and kilo.get("baglam"):
            guc += 150  # olağanüstü + doğrulanmış tarihsel bağlamı olan performans en güçlüsü
        tur_adi = kilo["esik"] if kilo else "kilometre"
        return True, guc, f"bireysel performans: {tur_adi} eşiğini geçen {kilo['oyuncu'] if kilo else ''}".strip()

    if kategori == "B":
        kaz_sira = olgu["kazanan_derece"].get("konferans_sira")
        kay_sira = olgu["kaybeden_derece"].get("konferans_sira")
        if kaz_sira is None or kay_sira is None:
            return False, 0, ""
        play_in = PLAY_IN_ARALIGI[0] <= kaz_sira <= PLAY_IN_ARALIGI[1] and PLAY_IN_ARALIGI[0] <= kay_sira <= PLAY_IN_ARALIGI[1]
        yakin = abs(kaz_sira - kay_sira) <= 1
        if not (play_in or yakin):
            return False, 0, ""
        guc = 100 - abs(kaz_sira - kay_sira) * 10 - abs((kaz_sira + kay_sira) / 2 - 8.5)
        return True, guc, f"konferans sıraları {kaz_sira}-{kay_sira}"

    if kategori == "C":
        ks = olgu["kazanan_seri"]
        # SADECE sürprizse (kullanıcı kuralı) — iyi bir takımın galibiyet
        # serisi sürmesi beklenen, form/kanca hikayesi değil. Güç, hem
        # seri uzunluğuna hem "ne kadar az beklenen"e (kalite ne kadar
        # düşükse o kadar sürpriz) bağlı.
        if ks and ks.get("tur") == "galibiyet" and olgu["kazanan_seri_haber"]:
            surpriz_payi = max(0, IYI_TAKIM_ESIGI - olgu["kazanan_kalite"])
            guc = ks["uzunluk"] * 10 + surpriz_payi * 5
            return True, guc, f"kazananın {ks['uzunluk']} maçlık galibiyet serisi (takım kalitesi {olgu['kazanan_kalite']:.1f}/10, sürpriz)"
        return False, 0, ""

    if kategori == "D":
        kd = olgu["kazanan_derece"]
        # Kullanıcı kararı (sezon başı susma kuralı): "namağlup"/"eşit
        # derece" iddiaları da derece kadar güvenilirlik ister — 1-0'lık
        # bir takım teknik olarak "namağlup" ama bunu söylemek "1-0'a
        # yükseldi" demekle aynı hata. lig_sira zaten fact seviyesinde
        # None'a düşüyor (guvenilir değilse), namaglup/esit_derece için
        # burada ayrıca guard gerekiyor.
        if not kd.get("sezon_guvenilir"):
            return False, 0, ""
        lig_sira = kd.get("lig_sira")
        namaglup = kd.get("maglubiyet") == 0
        esit_derece = kd.get("galibiyet") == olgu["kaybeden_derece"].get("galibiyet")
        if lig_sira == 1:
            return True, 1000, "lig lideri"
        if namaglup:
            return True, 500, "namağlup"
        if esit_derece:
            return True, 100, "eşit derece"
        return False, 0, ""

    if kategori == "E":
        if not olgu["kazanan_yildiz_yok"]:
            return False, 0, ""
        # Güç = eksik yıldızın kademesi (1 en güçlü) + o maçta zaten
        # zengin bir hikaye varsa (triple-double, 30+) bonus — "7 kadro
        # dışı ama hiçbiri tanınmıyor" düşük güç alır, "1 yıldız yok +
        # triple-double" yüksek güç alır (kullanıcı düzeltmesi).
        en_yuksek_yildiz = min(
            _ham_yildiz_kademesi_cache.get(isim, 3) for isim in olgu["kazanan_yildiz_yok"]
        ) if _ham_yildiz_kademesi_cache else 3
        guc = (5 - en_yuksek_yildiz) * 100
        if olgu["triple_double_var"] or olgu["en_yuksek_sayi"] >= EN_IYI_PERFORMANS_ESIKLERI["sayi"]:
            guc += 50
        guc -= max(0, len(olgu["kazanan_kadro_disi"]) - len(olgu["kazanan_yildiz_yok"]) - 2) * 5
        return True, guc, f"yıldız yokluğu: {', '.join(olgu['kazanan_yildiz_yok'])}"

    if kategori == "F":
        if olgu["lider_degisim"] >= LIDER_DEGISIM_ESIGI:
            return True, olgu["lider_degisim"], f"lider değişim {olgu['lider_degisim']}"
        return False, 0, ""

    if kategori == "G":
        return True, 0, f"gece sırası {olgu['tip_off_sira']}"  # güç ataması sırasında yeniden hesaplanır (bkz. gece_kanca_ata)

    if kategori == "H":
        return True, 0, "her zaman uygun (kancasız)"

    raise ValueError(kategori)


# `E` için yıldız kademesi cache'i — kanca_degerlendir'in imzasını
# bozmadan yildizlar sözlüğüne erişmesi için modül düzeyinde tutuluyor,
# gece_kanca_ata çağrılmadan önce doldurulur.
_ham_yildiz_kademesi_cache = {}


# ---------------------------------------------------------------------------
# Niteleyici bankası (bölüm 3) — dolabilen niteleyici grupları
# ---------------------------------------------------------------------------


GALIBIYET_SAYISI_YUVARLAK = {10, 20, 30, 40, 50}  # kullanıcı kararı: SADECE bu beşi, 25/60/70 gibi ara değerler değil

_IYUUO_CEVIRI = str.maketrans({"İ": "i", "I": "ı"})


def _yokluk_eki(metin):
    """'-sız/-siz/-suz/-süz' ünlü uyumu — oyuncu adının SON ünlüsüne
    göre. Python'un str.lower()'ı Türkçe İ/I'yı doğru çevirmediği için
    (İ→i̇, I→i) önce elle çeviriyoruz. Gerçek üretim bug'ı: 'Young'siz'
    yazılmıştı, doğrusu 'Young'suz' (son ünlü 'u')."""
    son = metin.translate(_IYUUO_CEVIRI).lower()
    for ch in reversed(son):
        if ch in "aeıiuüoö":
            if ch in "aı":
                return "sız"
            if ch in "ei":
                return "siz"
            if ch in "ou":
                return "suz"
            if ch in "öü":
                return "süz"
    return "siz"

# Bir maçın KANCASI zaten belirli bir olguyu (ör. yıldız yokluğu)
# CÜMLE1'de kullandıysa, aynı olgudan türeyen niteleyici CÜMLE2'de bir
# daha kullanılamaz — gerçek üretim bug'ı: Atlanta satırı hem "Trae
# Young'ın oynamadığı maçta" (kanca E) hem "Trae Young'suz oynadığı
# maçı kazanan" (niteleyici) dedi, aynı olgu iki kez söylendi.
KANCA_NITELEYICI_CAKISMA = {
    "B": {"siralama_iddiasi"},
    "C": {"ust_uste_galibiyet"},
    "D": {"galibiyet_sayisi_yuvarlak"},
    "E": {"yildiz_yokluk", "kucuk_kadro_disi"},
}


def _niteleyici_adaylari(olgu):
    """LLM promptuna sunulan niteleyici menüsü — (kind, metin) çiftleri.

    Kullanıcı kararı (mimari birleştirme turu): bu banka YEDİNCİ kural
    kopyasıydı ve kullanıcının saydığı üç sızıntının da kaynağıydı —
    lig liderinin galibiyet serisi (seri_haber kontrolü yoktu), play-in
    bandındaki sıralama iddiası, kadro dışı ("Nembhard'sız") çerçevesi.
    Artık kendi eşiği YOK: hepsi cumle.py'nin kapılarından geçiyor.

    Banka ayrıca sert budandı — kabul edilen üç içerik türü (Sonuç / Maçı
    belirleyen an / En iyi performans) dışında kalan niteleyiciler
    (ev sahası serisi, iç saha maç sayısı, çeyrek üstünlüğü, yıldız
    yokluğu, ilk galibiyet, N maç aradan sonra) tamamen kaldırıldı."""
    n = []
    kd = olgu["kazanan_derece"] or {}

    if cumle.galibiyet_serisi_konusulabilir(
        olgu.get("kazanan_seri"), kd, olgu.get("kazanan_seri_haber")
    ):
        n.append(("ust_uste_galibiyet", f"Üst üste {olgu['kazanan_seri']['uzunluk']}. galibiyetini alan (kazanan)"))

    kayb_seri = olgu["kaybeden_seri"]
    if (
        kayb_seri
        and kayb_seri.get("tur") == "maglubiyet"
        and kayb_seri.get("uzunluk", 0) >= cumle.SERI_ESIGI
        and olgu.get("kaybeden_seri_haber")
        and cumle.derece_konusulabilir(kd)
    ):
        n.append(("ust_uste_maglubiyet", f"Üst üste {kayb_seri['uzunluk']}. mağlubiyetini alan (kaybeden)"))

    # Galibiyet sayısı SADECE yuvarlak eşikte (10/20/30/40/50) ya da lig
    # liderliğinde — ara değerler ("23. galibiyetini aldı") hiçbir şey
    # anlatmıyor. Yuvarlak eşiğin en küçüğü 10 olduğu için sezon
    # güvenilirliği otomatik sağlanıyor.
    if cumle.derece_konusulabilir(kd) and (
        kd.get("galibiyet") in GALIBIYET_SAYISI_YUVARLAK or kd.get("lig_sira") == 1
    ):
        n.append(("galibiyet_sayisi_yuvarlak", f"{kd['galibiyet']}. galibiyetini alan (kazanan)"))

    if olgu["en_buyuk_geri_donus"] >= cumle.GERI_DONUS_ESIGI:
        n.append(("genis_geri_donus", f"{olgu['en_buyuk_geri_donus']} sayıya kadar ulaşan farktan dönerek kazanan"))

    if cumle.siralama_konusulabilir(kd.get("konferans_sira"), kd):
        n.append(("siralama_iddiasi", f"geceyi konferansta {kd['konferans_sira']}. sırada kapatan"))

    return n


def niteleyici_bankasi(olgu):
    """Geriye dönük uyumluluk / tek maçlık önizleme için — düz metin
    listesi döner, kind etiketi olmadan. Gece çapında dedup için
    `_niteleyici_adaylari` + `gece_niteleyici_ata` kullanılmalı."""
    return [metin for _, metin in _niteleyici_adaylari(olgu)]


# ---------------------------------------------------------------------------
# Gece çapında kanca ataması — her kategori kendi EN GÜÇLÜ adayına gider
# ---------------------------------------------------------------------------


def gece_kanca_ata(maclar_olgu_by_gid, yildizlar):
    global _ham_yildiz_kademesi_cache
    _ham_yildiz_kademesi_cache = yildizlar

    atanmamis = set(maclar_olgu_by_gid.keys())
    atama = {}

    for kat in KANCA_ONCELIK:
        if kat == "H":
            continue
        if kat == "G":
            # G'nin gücü diğer maçlara göre (gece ortasından uzaklık)
            # hesaplanıyor — tüm sıralar elde olmalı.
            tum_siralar = [o["tip_off_sira"] for o in maclar_olgu_by_gid.values()]
            orta = (min(tum_siralar) + max(tum_siralar)) / 2
        adaylar = []
        for gid in atanmamis:
            olgu = maclar_olgu_by_gid[gid]
            uygun, guc, gerekce = kanca_degerlendir(kat, olgu)
            if kat == "G" and uygun:
                guc = abs(olgu["tip_off_sira"] - orta)
            if uygun:
                adaylar.append((guc, gid, gerekce))
        if not adaylar:
            continue
        adaylar.sort(key=lambda a: -a[0])
        guc, gid, gerekce = adaylar[0]
        atama[gid] = (kat, gerekce)
        atanmamis.discard(gid)

    for gid in atanmamis:
        atama[gid] = ("H", "tüm uygun kategoriler bu gece kullanıldı, doğrudan kancasız")

    return atama


# ---------------------------------------------------------------------------
# Niteleyici geçmişi — sezon genelinde en az kullanılanı tercih etmek
# için kalıcı sayaç (kullanıcı kararı: "eşit uygun adaylar arasında o
# sezon en az kullanılanı seç, ilk eşleşeni değil").
# ---------------------------------------------------------------------------

NITELEYICI_GECMISI_DOSYASI = CONFIG_DIZIN / "niteleyici_gecmisi.json"


def niteleyici_gecmisi_yukle():
    if not NITELEYICI_GECMISI_DOSYASI.exists():
        return {}
    return json.loads(NITELEYICI_GECMISI_DOSYASI.read_text())


def niteleyici_gecmisi_guncelle(kullanilan_kindler):
    gecmis = niteleyici_gecmisi_yukle()
    for kind in kullanilan_kindler:
        gecmis[kind] = gecmis.get(kind, 0) + 1
    NITELEYICI_GECMISI_DOSYASI.write_text(json.dumps(gecmis, ensure_ascii=False, indent=2))


# Kullanıcı düzeltmesi: "üst üste/art arda" DİL KALIBI (yön fark
# etmeksizin, galibiyet ya da mağlubiyet) bir gecede İKİ kez
# görünmemeli — okuyucu için ikisi de aynı üsluba benziyor. İki KIND
# ayrı olgular olsa da (biri galibiyet serisi, biri mağlubiyet serisi)
# AYNI dedup grubunda tutuluyor, biri kullanılınca ikisi de düşer.
_UST_USTE_KIND_GRUBU = {"ust_uste_galibiyet", "ust_uste_maglubiyet"}


def _kullanilana_ekle(kullanilan_kind, kind):
    kullanilan_kind.add(kind)
    if kind in _UST_USTE_KIND_GRUBU:
        kullanilan_kind |= _UST_USTE_KIND_GRUBU


def gece_niteleyici_ata(maclar_olgu_by_gid, rozet_by_gid, kanca_by_gid=None):
    """Her maç için niteleyici metin listesini döner. Gece çapında aynı
    KIND iki maçta kullanılamaz (kanca dedup'ıyla aynı mantık, rozeti
    yüksek maç önce hak eder — bir maça sunulan TÜM menü "kullanılmış"
    sayılır, tam olarak hangisinin metne gireceğini önceden bilemeyiz,
    ihtiyatlı taraf budur). Eşit uygun adaylar arasında sezon genelinde
    en az kullanılan kind öne alınır. `kanca_by_gid` verilirse, o maçın
    kancasıyla ÇAKIŞAN (aynı olguyu tekrar eden) niteleyici kind'ları
    o maç için hiç sunulmaz (bkz. KANCA_NITELEYICI_CAKISMA)."""
    gecmis = niteleyici_gecmisi_yukle()
    kullanilan_kind = set()
    sonuc = {}
    sira = sorted(maclar_olgu_by_gid.keys(), key=lambda g: -rozet_by_gid[g])
    for gid in sira:
        adaylar = _niteleyici_adaylari(maclar_olgu_by_gid[gid])
        kanca_harf = kanca_by_gid.get(gid) if kanca_by_gid else None
        cakisan = KANCA_NITELEYICI_CAKISMA.get(kanca_harf, set())
        musait = [(kind, metin) for kind, metin in adaylar if kind not in kullanilan_kind and kind not in cakisan]
        musait.sort(key=lambda kt: gecmis.get(kt[0], 0))
        for kind, _ in musait:
            _kullanilana_ekle(kullanilan_kind, kind)
        sonuc[gid] = [metin for _, metin in musait]
    niteleyici_gecmisi_guncelle(kullanilan_kind)
    return sonuc


# ---------------------------------------------------------------------------
# Önizleme CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ayristirici = argparse.ArgumentParser(description="Kanca/kademe/niteleyici dağılımını önizler, METİN ÜRETMEZ.")
    ayristirici.add_argument("tarih", help="YYYY-MM-DD")
    args = ayristirici.parse_args()

    gercek_gece = json.loads((GERCEK_DIZIN / f"{args.tarih}.json").read_text())
    ham = json.loads((HAM_DIZIN / f"{args.tarih}.json").read_text())
    skor_gece = json.loads((SKOR_DIZIN / f"{args.tarih}.json").read_text())
    rozet_by_gid = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}
    ev_dep_by_gid = {m["mac_id"]: (m["ev"], m["dep"], m["ev_skor"], m["dep_skor"]) for m in skor_gece["maclar"]}

    yildizlar = yildizlar_yukle()
    if not yildizlar:
        print("UYARI: config/yildizlar.json boş/yok — E kancası ve 'yıldız yokluğu' olgusu hiç tetiklenmeyecek.\n")

    kalite_ort, kalite_sirali = takim_kalitesi_hesapla(ham["puan_durumu"], args.tarih)

    olgu_by_gid = {}
    for gid in gercek_gece["maclar"]:
        olgu_by_gid[gid] = olgulari_hesapla(
            gercek_gece["maclar"][gid], ham["maclar"][gid], haber_skoru=0, yildizlar=yildizlar,
            kalite_ort=kalite_ort, kalite_sirali=kalite_sirali,
        )

    atama = gece_kanca_ata(olgu_by_gid, yildizlar)

    sira = sorted(olgu_by_gid.keys(), key=lambda g: -rozet_by_gid[g])
    kademe_dagilimi = {"fakir": 0, "orta": 0, "zengin": 0}
    for gid in sira:
        olgu = olgu_by_gid[gid]
        kademe, olgular = kademe_hesapla(olgu)
        kademe_dagilimi[kademe] += 1
        kanca, gerekce = atama[gid]
        ev, dep, ev_s, dep_s = ev_dep_by_gid[gid]
        nitelikler = niteleyici_bankasi(olgu)

        print(f"\n{'='*90}")
        print(f"{gid}  {ev} {ev_s}-{dep_s} {dep}  (rozet {rozet_by_gid[gid]})")
        print(f"  KADEME : {kademe} — olgular: {olgular or '(yok)'}")
        print(f"  KANCA  : {kanca} — {gerekce}")
        print(f"  NİTELEYİCİLER ({len(nitelikler)} dolu):")
        for n in nitelikler:
            print(f"    - {n}")
        if not nitelikler:
            print("    (hiçbiri dolmadı — sadece sonuç/derece anlatılabilir)")

    print(f"\n{'='*90}")
    print(f"KADEME DAĞILIMI: {kademe_dagilimi}")
