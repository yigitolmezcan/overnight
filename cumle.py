"""
TEK CÜMLE KURMA KATMANI.

Kullanıcı kararı (mimari birleştirme turu): "Sızıntıların hepsi şablondan
geliyor. Sebep: kodda altı ayrı metin üretim yolu var — normal şablon,
Mutlaka bil şablonu, brief şablonu, düşük-rozet dalı, yedek dal, LLM
sonrası onarım. Her kural altısında ayrı ayrı uygulanıyor ve sürekli
birinde unutuluyor."

Bu modül o altı yolu TEK kaynağa indiriyor. Ürüne çıkan HER cümle
buradan geçer. İki katmanlı koruma var:

  1. OLGU KAPILARI (`*_konusulabilir`) — bir olgunun cümleye girmeye
     hakkı var mı? Eşikler burada TEK kez tanımlı: sıralama, derece,
     seri, fark, performans. Bir çağıran eşiği unutamaz çünkü eşiği
     hiç görmüyor; sadece kapıya soruyor.

  2. SON KAPI (`_gecir`) — kurulan cümle mekanik yasaklardan geçiyor
     mu? Yasakların tanımı dogrula.py'de KALIYOR (tek tanım), burada
     sadece ÜRETİM ANINDA uygulanıyor. Bir kurucu bir kuralı
     unutursa cümle yayına çıkmadan burada düşer.

Kritik tasarım kararı: kapı katmanın İÇİNDE, çağıranın elinde değil.
Eski mimaride her çağıran kuralları kendi uyguluyordu, bir yolda
uygulanıp diğerinde unutuluyordu — bütün sızıntıların tek sebebi buydu.
"""

import re

from dogrula import (
    yasakli_yukle,
    t4_yasakli_ifade,
    t4b_terim_varyanti,
    t4c_puan_baglami,
    t4d_kok_kaliplari,
    t4e_takim_kodu,
    t4f_konferans_ozel_ad,
    t_fiil_cekimi,
    t_turkce_yazim,
    t15_istatistik_seri_sebebi,
    t21_iyelik_eki_tamponu,
    t22_kucuk_fark_rakami,
    t23_mimari_kural_ihlalleri,
    kelime_say,
    ASGARI_KELIME,
    BRIEF_SKOR_FARK_ESIGI,
    sesli_biter_mi,
    sayi_eki as dogrula_sayi_eki,
    OZET_CUMLE,
    OZET_KELIME_ALT,
)

# ---------------------------------------------------------------------------
# EŞİKLER — TEK KAYNAK. Başka hiçbir dosyada bu sayılar tekrar edilmez.
# ---------------------------------------------------------------------------

SIRALAMA_ZIRVE = 3          # sıralama SADECE ilk 3 için anlamlı
SEZON_GUVENILIR_MAC = 10    # bu maç sayısının altında derece/seri/sıra susar
SERI_ESIGI = 4              # "üst üste" ancak 4+ maçlık seride
GERI_DONUS_ESIGI = 10       # bu farkın altındaki açık "geri dönüş" değil
FARK_ESIGI = 20             # bu farkın altında fark RAKAMI hiç anılmaz
LIDER_DEGISIM_ESIGI = 15    # maç geneli toplamı; alt kırılım HİÇ anılmaz

# İstatistik → (eşik, birim, DOĞRU FİİL). "toplamak" SADECE ribaund fiili;
# sayı "atılır", asist "dağıtılır" — fiil-isim uyumsuzluğu ("36 sayı topladı")
# burada yapısal olarak imkânsız, çünkü fiil istatistiğe bağlı.
# Kullanıcı kuralı (asist fiili): SADECE "N asist yaptı" ve "N asistle
# oynadı" serbest. "asist verdi / dağıttı / üretti / kaydetti" yasak —
# yasağın tanımı config/yasakli.json kok_kaliplari'nda, burada sadece
# doğru fiil üretiliyor.
PERFORMANS_ESIKLERI = [
    ("sayi", 30, "sayı", "attı"),
    ("rib", 15, "ribaund", "topladı"),
    ("ast", 10, "asist", "yaptı"),   # "dağıttı/verdi/üretti" yasak (kullanıcı kuralı)
]

# Cümle bütçesi — katman başına en fazla kaç cümle (kullanıcı kararı).
SEVIYE_BUTCE = {"mutlaka": 3, "degerse": 2, "gec": 1}
DUSUK_DEGER_ESIGI = 6.0   # bu rozetin altı "gec" katmanı (hesapla.py ile AYNI sınır)

_YASAKLI_CACHE = None


def _yasakli():
    global _YASAKLI_CACHE
    if _YASAKLI_CACHE is None:
        _YASAKLI_CACHE = yasakli_yukle()
    return _YASAKLI_CACHE


# ---------------------------------------------------------------------------
# EK ÜRETİMİ — ünlü uyumu. Hardcode edilmiş ek ("'nin", "'yi") YASAK;
# her ek buradan üretilir (gerçek üretim bug'ları: "Edwards'nin",
# "Doğu'nın", "Wizards'yi" — üçü de ayrı yerde hardcode edilmişti).
# ---------------------------------------------------------------------------

_IYUUO = str.maketrans({"İ": "i", "I": "ı"})
_SESLI = "aeıiuüoö"


def _son_unlu(ad):
    kucuk = ad.translate(_IYUUO).lower()
    return kucuk, next((c for c in reversed(kucuk) if c in _SESLI), None)


# Ünlü-sonu kararı TEK KAYNAKTAN: dogrula.sesli_biter_mi. Burada bir
# kopya tutmak, kurucunun doğru yazdığını denetleyicinin reddetmesine
# yol açıyordu (gerçek arıza: "Curry'nin" üretildi, T21 reddetti).
_sesli_biter_mi = sesli_biter_mi


def belirtme_eki(ad):
    """-ı/-i/-u/-ü, sesliyle bitende 'y' tamponu ("Lakers'ı", "Utah'yı")."""
    # UYUM SESE GÖRE. `sesli_biter_mi` hem tampon gerekip gerekmediğini
    # hem uyumu belirleyen SESİ döndürüyor (sessiz 'e', okunan 'y' vb.).
    sesli_biter, son_ses = _sesli_biter_mi(ad)
    if not son_ses:
        _, son_ses = _son_unlu(ad)
    ek = {"a": "ı", "ı": "ı", "e": "i", "i": "i", "o": "u", "u": "u", "ö": "ü", "ü": "ü"}.get(son_ses, "i")
    tampon = "y" if sesli_biter else ""
    return f"{tampon}{ek}"


def lik_eki(ad):
    """-lik/-lık/-luk/-lük — ünlü uyumu ("55 sayılık", "12 ribaundluk",
    "12 asistlik"). Hardcode "lik" gerçek üretim bug'ıydı."""
    _, unlu = _son_unlu(ad)
    return {"a": "lık", "ı": "lık", "e": "lik", "i": "lik",
            "o": "luk", "u": "luk", "ö": "lük", "ü": "lük"}.get(unlu, "lik")


def yonelme_eki(ad):
    """-a/-e, sesliyle bitende 'y' tamponu ("Denver'a", "Miami'ye").

    Düz sonuç cümlesinin "kaybeden özne" iskeleti için gerekti:
    "Utah, Denver'a evinde kaybetti"."""
    kucuk, unlu = _son_unlu(ad)
    ek = "a" if unlu in ("a", "ı", "o", "u") else "e"
    tampon = "y" if kucuk and kucuk[-1] in _SESLI else ""
    return f"{tampon}{ek}"


def iyelik_eki(ad):
    """-ın/-in/-un/-ün, sesliyle bitende 'n' tamponu ("Doğu'nun",
    "Edwards'ın"). DİKKAT: belirtme ekindeki 'y' tamponuyla karıştırma."""
    sesli_biter, son_ses = _sesli_biter_mi(ad)
    if not son_ses:
        _, son_ses = _son_unlu(ad)
    ek = {"a": "ın", "ı": "ın", "e": "in", "i": "in", "o": "un", "u": "un", "ö": "ün", "ü": "ün"}.get(son_ses, "in")
    tampon = "n" if sesli_biter else ""
    return f"{tampon}{ek}"


# ---------------------------------------------------------------------------
# OLGU KAPILARI — bir olgunun konuşulmaya hakkı var mı?
# ---------------------------------------------------------------------------


def derece_konusulabilir(kazanan_derece):
    """Galibiyet-mağlubiyet rekoru, sıra, seri — hepsinin ön şartı.
    Sezon başında (10 maç altı) hiçbiri anlamlı değil."""
    kd = kazanan_derece or {}
    return bool(kd.get("sezon_guvenilir"))


def siralama_konusulabilir(sira, kazanan_derece=None):
    """Kullanıcı kararı: sıralama SADECE ilk 3 için anlamlı. "13. sıraya
    oturdu" / "10. sıraya oturdu" hiçbir şey anlatmıyor — okuyucu için
    bir sıra ancak zirveyse haberdir. (Play-in hattını GEÇME de anlamlı
    olurdu ama onu tespit etmek bir önceki günün puan durumunu
    gerektiriyor, o veri pipeline'da yok — yokluğunda susmak doğru
    davranış.)"""
    if sira is None:
        return False
    if kazanan_derece is not None and not derece_konusulabilir(kazanan_derece):
        return False
    return sira <= SIRALAMA_ZIRVE


def galibiyet_serisi_konusulabilir(seri, kazanan_derece, seri_haber):
    """Kullanıcı kararı: lig liderinin galibiyet serisi haber DEĞİL —
    iyi takımın kazanmaya devam etmesi beklenen şey. `seri_haber`
    (kalip_secici.seri_haber_degeri_mi) bu sürpriz ayrımını zaten
    yapıyor; eski kodda seri adayları bu bayrağı kontrol etmeyi
    unutuyordu, gerçek sızıntı buydu."""
    if not seri or not seri_haber:
        return False
    if not derece_konusulabilir(kazanan_derece):
        return False
    return seri.get("uzunluk", 0) >= SERI_ESIGI


def maglup_anilabilir(mac, ad):
    """Kaybeden takımın oyuncusu anılabilir mi?

    İki kullanıcı kuralı TEK mekanizmada:
      (a) "Mağlup tarafta ..." kalıbı bir gecede EN FAZLA BİR KEZ,
      (b) sadece GERÇEKTEN dikkat çekici bir performans için.

    Hakkı, kaybeden tarafta gecenin en yüksek GmSc'li KİLOMETRE TAŞINI
    barındıran maç ve o oyuncu alır; kararı gece_kalip_plani veriyor,
    burada sadece uygulanıyor. Bilerek `False` varsayılanı: izni kimse
    hesaplamadıysa susulur (sessizlik varsayılan)."""
    izinli = (mac or {}).get("maglup_anilabilir_ad")
    return bool(izinli) and izinli == ad


def performans_konusulabilir(oyuncu):
    """Eşiği geçen istatistiği ve DOĞRU fiilini döner, yoksa None."""
    if not oyuncu:
        return None
    for alan, esik, birim, fiil in PERFORMANS_ESIKLERI:
        deger = oyuncu.get(alan, 0)
        if deger >= esik:
            return deger, birim, fiil
    return None


def fark_rakami_konusulabilir(fark):
    return bool(fark) and fark >= FARK_ESIGI


# ---------------------------------------------------------------------------
# SON KAPI — kurulan her cümle buradan geçer.
# ---------------------------------------------------------------------------

# Yasakların TANIMI dogrula.py'de; burada sadece üretim anında uygulanıyor.
# Hepsi metin-yalnız testler (gerçek/ham_mac gerektirmeyenler).
_METIN_KAPILARI = [
    ("T4d", t4d_kok_kaliplari),
    ("T4b", t4b_terim_varyanti),
    ("T4c", t4c_puan_baglami),
    ("T4e", t4e_takim_kodu),
    ("T4f", t4f_konferans_ozel_ad),
    ("T10", t_fiil_cekimi),
    ("T12", t_turkce_yazim),
    ("T15", t15_istatistik_seri_sebebi),
    ("T21", t21_iyelik_eki_tamponu),
    ("T22", t22_kucuk_fark_rakami),
    ("T23", t23_mimari_kural_ihlalleri),
]


def _gecir(metin):
    """Cümleyi mekanik yasaklardan geçirir. Geçerse cümleyi, geçmezse
    None döner — çağıran None'ı "bu cümle yok" olarak ele alır ve
    sessizce atlar (sessizlik varsayılan). Böylece bir kurucu bir
    kuralı unutsa bile yasaklı metin yayına ÇIKAMAZ."""
    if not metin:
        return None
    if not t4_yasakli_ifade(metin, _yasakli())[0]:
        return None
    for _, test in _METIN_KAPILARI:
        if not test(metin)[0]:
            return None
    return metin


def gerekce(metin):
    """Teşhis için: cümle neden düştü? (Üretimde kullanılmıyor, testler
    ve hata ayıklama için.)"""
    sebepler = []
    gecti, detay = t4_yasakli_ifade(metin, _yasakli())
    if not gecti:
        sebepler.append(f"T4: {detay}")
    for ad, test in _METIN_KAPILARI:
        gecti, detay = test(metin)
        if not gecti:
            sebepler.append(f"{ad}: {detay}")
    return sebepler


# ---------------------------------------------------------------------------
# CÜMLE KURUCULAR — ürüne çıkan her cümlenin tek kaynağı.
# Hepsi `_gecir`den geçer; hepsi None dönebilir (= bu cümle yok).
# ---------------------------------------------------------------------------


def sonuc(mac, kanca=None, kanca_kisa=None):
    """CÜMLE1 (zorunlu): kim kimi kaç kaç yendi. `kanca` verilirse
    (eşiği geçen bir olgudan türemiş kısa bir önek) cümlenin başına
    eklenir; yoksa düz sonuç. Fark rakamı ASLA yazılmaz (skor zaten
    farkı taşıyor); en büyük fark SADECE fiil seçimine yansır."""
    k, y = mac["kazanan_adi"], mac["kaybeden_adi"]
    ek = belirtme_eki(y)
    skor = f"{mac['buyuk']}-{mac['kucuk']}"
    if kanca:
        # Önek cümlenin BAŞINA geliyor — ilk harf büyütülür (gerçek
        # üretim bug'ı: "sürpriz bir sonuçla Milwaukee..." küçük harfle
        # başlamıştı; önekler cümle ortası için yazıldığı halde cümle
        # başında kullanılıyor).
        kanca = kanca[0].upper() + kanca[1:]
        # Telefon ekranı kuralı: başlık en fazla 10 kelime. Kancalı biçim
        # tam takım adları ve skorla birlikte sık sık 13-15 kelimeye
        # çıkıyor. Kancayı ATMAK yanlış çözüm — başlığın en güçlü olguyu
        # kullanması ayrı bir kural. Onun yerine SONUÇ KISMI kademeli
        # sadeleşiyor: önce skor düşer (skor zaten kartın tepesinde ve
        # başlıkta tekrarı T25'i de ihlal ediyordu), yetmezse takım adları
        # kısa şehir biçimine iner.
        kk = (kanca_kisa[0].upper() + kanca_kisa[1:]) if kanca_kisa else kanca
        ky, kyek = mac.get("kaybeden_kisa", y), belirtme_eki(mac.get("kaybeden_kisa", y))
        for aday in (
            f"{kanca} {k}, {y}'{ek} {skor} yendi.",
            f"{kanca} {k}, {y}'{ek} yendi.",
            f"{kk} {k}, {y}'{ek} yendi.",
            f"{kk} {mac.get('kazanan_kisa', k)}, {ky}'{kyek} yendi.",
        ):
            if len(aday.split()) <= 10:
                return _gecir(aday)
        return _gecir(f"{kk} {mac.get('kazanan_kisa', k)}, {ky}'{kyek} yendi.")
    if mac.get("en_buyuk_fark_gecede_mi"):
        return _gecir(f"{k} {mac['ev_dep']} {y}'{ek} {skor} ezdi.")
    return _gecir(f"{k} {mac['ev_dep']} {y}'{ek} {skor} yendi.")


def an(mac, olgu, kancada_kullanildi=False):
    """CÜMLE2 adayı: maçı belirleyen an. Kancada zaten anlatıldıysa
    tekrar edilmez."""
    if kancada_kullanildi:
        return None
    ka = olgu.get("karar_ani")
    if ka and ka.get("oyuncu"):
        return _gecir(f"Maçı belirleyen basketi, bitime {ka['saniye_kalan']:.1f} "
                      f"saniye kala {ka['oyuncu']} attı.")
    if olgu.get("uzatma"):
        return _gecir(f"{mac['kazanan_adi']}, maçı uzatmada kazandı.")
    if olgu.get("en_buyuk_geri_donus", 0) >= GERI_DONUS_ESIGI:
        return _gecir(f"{mac['kazanan_adi']}, {olgu['en_buyuk_geri_donus']} sayılık farktan dönerek kazandı.")
    return None


def performans(mac, en_iyi_oyuncu, en_iyi_ad):
    """CÜMLE2/3 adayı: maçın en iyi performansı — SADECE eşiği geçiyorsa
    (T14 kuralı). Kaybeden taraftaysa "Mağlup tarafta" çerçevesiyle
    girer (T17: kaybeden oyuncu cümlenin öznesi olamaz)."""
    ifade = performans_konusulabilir(en_iyi_oyuncu)
    if not ifade:
        return None
    deger, birim, fiil = ifade
    kazanan_tarafta = en_iyi_oyuncu.get("takim") == mac["kazanan_kod"]
    if not kazanan_tarafta and not maglup_anilabilir(mac, en_iyi_ad):
        # Gece izni yok ya da başka bir oyuncuya ait — maç zaten
        # kaybedilmiş, sıradan bir performans için susulur.
        return None
    onek = "" if kazanan_tarafta else "Mağlup tarafta "
    return _gecir(f"{onek}{en_iyi_ad} {deger} {birim} {fiil}.")


def kazananin_en_iyisi(mac, oyuncu):
    """Kaybedenin performansı anılacaksa ÖNCE kazananınki anılır
    (kullanıcı kuralı: "Mağlup tarafta X..." tek başına cümle olamaz)."""
    if not oyuncu:
        return None
    return _gecir(f"{oyuncu['oyuncu']} {oyuncu['sayi']} sayı attı.")


def kaybedenin_kilometresi(mac, gercekler, en_iyi_ad):
    """Mağlup tarafta, gecenin en iyi performansından DAHA BÜYÜK bir
    kilometre taşı varsa onu anan cümle.

    Gerçek üretim bug'ı (2025-10-23 DEN-GSW): Aaron Gordon 50 sayı attı
    ama kaybeden taraftaydı; metin sadece kazananın en iyisini (Curry,
    42) andı ve 50 sayılık maç hiç geçmedi. T24 bunu "aynı eşiği daha
    yüksek GmSc ile geçen oyuncu anılmalı" diye yakalıyordu.

    T17 ile çelişmiyor: kaybedenin oyuncusu SONUÇ iddiasının öznesi
    olamaz ("Jokić'in gecesinde GSW kazandı" yasak), ama kendi
    performansının öznesi olabilir — "Mağlup tarafta X 50 sayı attı"
    çerçevesi zaten bunun için var (bkz. `performans`)."""
    if not gercekler:
        return None
    adaylar = [g["veri"] for g in gercekler if g["tur"] == "kilometre" and g["veri"].get("oyuncu")]
    if not adaylar:
        return None
    en_iyi_kilo = max(adaylar, key=lambda k: k.get("gmsc", 0))
    ad = en_iyi_kilo["oyuncu"]
    if ad == en_iyi_ad:
        return None
    if oyuncunun_takimi(gercekler, ad) == mac["kazanan_kod"]:
        return None
    if not maglup_anilabilir(mac, ad):
        return None
    oyuncu = oyuncu_bul(gercekler, ad)
    ifade = performans_konusulabilir(oyuncu)
    if not ifade:
        return None
    deger, birim, fiil = ifade
    return _gecir(f"Mağlup tarafta {ad} {deger} {birim} {fiil}.")


def neden_onemli(mac, olgu):
    """Mutlaka bil'in tek satırlık gerekçesi. Öncelik: lig liderliği >
    ilk-3 sırası > haber değeri olan seri > maçın kendisi.

    Kullanıcı kararı: derece SON ÇARE cümlesi ("sezonu 21-11 yaptı")
    TAMAMEN kaldırıldı. Erken sezonda diğer her şey boş olduğu için
    zincir HER ZAMAN oraya düşüyordu — en çok sızan cümle oydu.
    Hiçbir şey uygulanamıyorsa maçın kendisine dayanılır."""
    kd = olgu.get("kazanan_derece") or {}
    if derece_konusulabilir(kd):
        if kd.get("lig_sira") == 1:
            c = _gecir(f"{mac['kazanan_adi']} lig liderliğini sürdürdü.")
            if c:
                return c
        if siralama_konusulabilir(kd.get("konferans_sira"), kd):
            c = _gecir(f"{mac['kazanan_adi']}, konferansta {kd['konferans_sira']}. sıraya yükseldi.")
            if c:
                return c
        if galibiyet_serisi_konusulabilir(olgu.get("kazanan_seri"), kd, olgu.get("kazanan_seri_haber")):
            c = _gecir(f"{mac['kazanan_adi']}, {olgu['kazanan_seri']['uzunluk']} maçlık galibiyet serisini sürdürdü.")
            if c:
                return c
    if olgu.get("uzatma"):
        return _gecir(f"{mac['kazanan_adi']}, maçı uzatmada kazandı.")
    _ka = olgu.get("karar_ani") or {}
    if _ka.get("oyuncu"):
        return _gecir(f"{mac['kazanan_adi']}, maçı son saniyede "
                      f"{_ka['oyuncu']}'{iyelik_eki(_ka['oyuncu'])} basketiyle kazandı.")
    if olgu.get("en_buyuk_geri_donus", 0) >= GERI_DONUS_ESIGI:
        return _gecir(f"{mac['kazanan_adi']}, {olgu['en_buyuk_geri_donus']} sayılık farktan döndü.")
    if olgu.get("en_buyuk_fark_gecede_mi"):
        return _gecir(f"{mac['kazanan_adi']}, gecenin en farklı galibiyetini aldı.")
    # Kullanıcı kararı (sessizlik varsayılan): söylenecek bir şey yoksa
    # SUSULUR. Eski son çare ("X kazandı.") başlığın totolojik tekrarıydı
    # — hiçbir şey katmıyordu, alanı doldurmak için vardı.
    return None


# Kullanıcı kararı: bir oyuncu iki ayrı cümlede tekrar edemez — kanca
# oyuncuyu zaten anıyorsa istatistikleri TEK ifadede birleşir
# ("LeBron James'in 28 sayı ve 12 asistlik gecesinde ..."), ardından
# ayrı bir "LeBron James 12 asist ..." cümlesi KURULMAZ.
# Birleşik ifade için eşik, tek başına cümle kurmaktan daha düşük —
# zaten anılan bir oyuncunun yanına yazılıyor, ayrı cümleyi hak
# etmesi gerekmiyor.
_BIRLESIK_ESIKLER = [("sayi", 20, "sayı"), ("rib", 10, "ribaund"), ("ast", 10, "asist")]


def _gece_ifadesi(kilo, en_iyi_oyuncu):
    """P kancasındaki "... gecesinde" ifadesinin içi."""
    if not en_iyi_oyuncu or en_iyi_oyuncu.get("oyuncu") != kilo.get("oyuncu"):
        return f"{kilo['sayi']} sayılık"
    parcalar = [f"{en_iyi_oyuncu[a]} {b}" for a, e, b in _BIRLESIK_ESIKLER if en_iyi_oyuncu.get(a, 0) >= e]
    if len(parcalar) <= 1:
        return f"{kilo['sayi']} sayı" + lik_eki("sayı")
    # Türkçe sıralama: "a, b ve c" — ikiden fazlada araya virgül girer.
    govde = ", ".join(parcalar[:-1]) + " ve " + parcalar[-1]
    return govde + lik_eki(parcalar[-1])


def oyuncu_bul(gercekler, ad):
    if not ad:
        return None
    return next(
        (g["veri"] for g in gercekler if g["tur"] == "oyuncu_stat" and g["veri"]["oyuncu"] == ad),
        None,
    )


# İSKELET LİSTESİNDEN BAŞLIK — hem şablon yedeği hem LLM'in taklit
# ettiği referans. İkisi de aynı listeye uyuyor (T31), yoksa LLM
# reddedildiğinde devreye giren şablon kuralı ihlal ediyordu: gerçek
# arıza (27 Aralık) — "New York Knicks deplasmanda Atlanta Hawks'ı
# 128-125 yendi." iskelet dışı olduğu için işaretlendi.
BASLIK_CEYREK_ADI = {1: "ilk", 2: "ikinci", 3: "üçüncü", 4: "son"}
BASLIK_SON_SANIYE = 24.0      # karar anı bu kadar kalmışsa "son saniye"
BASLIK_GERI_DONUS = 10        # kapatılan açık bu kadarsa "farktan dönüp"
BASLIK_PERFORMANS = 30        # tek adamın taşıdığı maç eşiği


def baslik_iskeletinden(mac, olgu, en_iyi_ad=None, en_iyi_sayi=None):
    """Veriye göre iskelet seçip doldurur.

    SEÇİM SIRAYLA DEĞİL GÜÇLE. İlk uyan iskeleti almak yanlış sonuç
    veriyordu: Jokić'in 55 sayılık gecesinde başlık 10 sayılık bir geri
    dönüşü anlatıyordu (ölçüldü). Her aday bir ağırlık alıyor, en güçlüsü
    kazanıyor; doğrulamadan geçemeyen aday bir sonrakine bırakıyor.
    Sıfat, niteleme, uydurma detay yok — yalnız veri."""
    olgu = olgu or {}
    k, y = mac["kazanan_adi"], mac["kaybeden_adi"]
    ek = belirtme_eki(y)
    adaylar = []   # (agirlik, metin)

    karar = olgu.get("karar_ani") or {}
    kalan = karar.get("saniye_kalan")
    if kalan is not None and kalan <= BASLIK_SON_SANIYE:
        # Son saniye ne kadar sonsa hikâye o kadar güçlü.
        adaylar.append((100 - kalan, f"{k}, {y}'{ek} son saniyede devirdi."))

    acik = olgu.get("en_buyuk_geri_donus") or 0
    if acik >= BASLIK_GERI_DONUS:
        adaylar.append((acik * 4, f"{k}, {acik} sayılık farktan dönüp {y}'{ek} yendi."))

    kopma = olgu.get("kopma_ani") or {}
    if kopma.get("periyot"):
        ceyrek = BASLIK_CEYREK_ADI.get(kopma["periyot"], f"{kopma['periyot']}.")
        adaylar.append((45, f"{k}, {y}'{ek} {ceyrek} çeyrekte kopardı."))

    # T24 KORUMASI: aynı maçta DAHA YÜKSEK GmSc'li bir kilometre sahibi
    # varsa (tipik olarak kaybeden tarafta) kazananın daha küçük
    # performansını başlığa taşımak "en iyisi anılmalı" kuralını çiğner.
    # Bu koruma eski başlık kurucusunda vardı, iskelete taşınmamıştı ve
    # yayın kapısı 23 Ekim'i durdurdu: başlık Curry'yi anıyordu, oysa
    # aynı maçta Gordon daha yüksek GmSc ile eşiği geçmişti.
    _kilo = (olgu.get("en_iyi_kilometre") or {}).get("oyuncu")
    _kilo_baskasi = bool(_kilo) and _kilo != en_iyi_ad
    if en_iyi_ad and (en_iyi_sayi or 0) >= BASLIK_PERFORMANS and not _kilo_baskasi:
        adaylar.append(((en_iyi_sayi - 20) * 4,
                        f"{en_iyi_ad}'{iyelik_eki(en_iyi_ad)} {en_iyi_sayi} sayısıyla "
                        f"{k}, {y}'{ek} yendi."))

    for _agirlik, metin in sorted(adaylar, key=lambda x: -x[0]):
        gecen = _gecir(metin)
        if gecen:
            return gecen

    # SON ÇARE — düz skor. Yer iddiası YALNIZ doğruyken: `ev_dep`
    # kazananın nerede oynadığı, ev sahibiyse "deplasmanında" yanlış olur.
    if mac.get("ev_dep") == "deplasmanda":
        m = _gecir(f"{k}, {y} deplasmanında {mac['buyuk']}-{mac['kucuk']} kazandı.")
        if m:
            return m
    return _gecir(f"{k}, {y}'{ek} {mac['buyuk']}-{mac['kucuk']} yendi.")


def sonuc_alternatif(mac):
    """Gövde başlığın KOPYASI olamaz — aynı sonucu farklı ifadeyle
    kurar (başlık "X deplasmanda Y'yi A-B yendi", gövde "X, Y
    karşısında A-B kazandı")."""
    return _gecir(
        f"{mac['kazanan_adi']}, {mac['kaybeden_adi']} karşısında {mac['buyuk']}-{mac['kucuk']} kazandı."
    )


def kanca_oneki(kanca_harf, olgu, mac, en_iyi_oyuncu=None):
    """CÜMLE1'in başına eklenecek kısa önek — SADECE eşiği geçen bir
    olgu varsa. Hiçbir kanca hak edilmiyorsa None (düz sonuç cümlesi).

    Kullanıcı kararı: "E" (yıldız yokluğu) kancası KALDIRILDI — bir
    oyuncunun yokluğu maçın sonucuyla ilgili bir olgu değil, kabul
    edilen üç içerik türünden (Sonuç/An/Performans) hiçbirine girmiyor
    ("Nembhard'sız sahaya çıkan Indiana..." sızıntısı buradan geliyordu).
    "B" (konferans sıralaması) da kaldırıldı — sıralama artık sadece
    ilk 3 için ve sadece neden_onemli'de anılıyor."""
    olgu = olgu or {}
    kd = olgu.get("kazanan_derece") or {}
    y, ek = mac["kaybeden_adi"], belirtme_eki(mac["kaybeden_adi"])

    if kanca_harf == "A":
        if olgu.get("uzatma"):
            return "uzatmaya giden maçta"
        ka = olgu.get("karar_ani")
        if ka and ka.get("oyuncu"):
            return (f"bitime {ka['saniye_kalan']:.1f} saniye kala "
                    f"{ka['oyuncu']}'{iyelik_eki(ka['oyuncu'])} basketiyle")
        if olgu.get("fark", 99) <= 2:
            return "nefes kesen bir maçta"
        return None
    if kanca_harf == "S" and olgu.get("surpriz_sonuc"):
        return "sürpriz bir sonuçla"
    if kanca_harf == "Z" and olgu.get("zirve_maci") and derece_konusulabilir(kd):
        konf = kd.get("konferans") or ""
        return f"{konf}'{iyelik_eki(konf)} zirvesinde" if konf else None
    if kanca_harf == "P":
        kilo = olgu.get("en_iyi_kilometre")
        if kilo:
            return f"{kilo['oyuncu']}'{iyelik_eki(kilo['oyuncu'])} {_gece_ifadesi(kilo, en_iyi_oyuncu)} gecesinde"
        return None
    if kanca_harf == "C" and galibiyet_serisi_konusulabilir(
        olgu.get("kazanan_seri"), kd, olgu.get("kazanan_seri_haber")
    ):
        return "son maçlarında formda olan"
    if kanca_harf == "D" and derece_konusulabilir(kd) and kd.get("lig_sira") == 1:
        return "lig lideri"
    if kanca_harf == "F" and olgu.get("lider_degisim", 0) >= LIDER_DEGISIM_ESIGI:
        return f"liderliğin {olgu['lider_degisim']} kez el değiştirdiği maçta"
    return None



# ---------------------------------------------------------------------------
# MUTLAKA BİL — başlık / neden önemli / gövde, OLGU TEKRARI OLMADAN.
#
# Kullanıcı kararı: "Başlıkta veya neden-önemli'de geçen bir olgu gövdede
# tekrar edilemez. Gövde başlığın devamıdır, kopyası değil." Bunu sağlamak
# için üç alan TEK yerde, ortak bir `kullanilan` kümesiyle kuruluyor —
# ayrı ayrı kurulduklarında aynı olguyu seçmeleri kaçınılmazdı.
#
# Başlık önceliği (kullanıcı sırası): kilometre taşı → maçı bitiren an →
# geri dönüş → sürpriz sonuç → DÜZ SKOR (son çare, ilk seçenek değil).
# ---------------------------------------------------------------------------

BASLIK_ONCELIK = ("kilometre", "an", "geri_donus", "surpriz")


def oyuncunun_takimi(gercekler, ad):
    """Oyuncunun takım kodu — `oyuncu_stat` gerçeğinden. Bilinmiyorsa None."""
    v = oyuncu_bul(gercekler, ad)
    return (v or {}).get("takim")


def _baslik_oneki(mac, olgu, en_iyi_oyuncu, gercekler=None):
    """(kind, önek) — en güçlü olgudan başlayarak. Hiçbiri yoksa (None, None).

    KAZANAN TAKIM KURALI (gerçek üretim bug'ı, 2025-10-23 DEN-GSW):
    başlığın kancası KAYBEDEN takımın oyuncusundan seçilince cümle
    "Nikola Jokić'in ... gecesinde Golden State, Denver'ı yendi" oluyor —
    kaybedenin oyuncusu kazanılan maçın öznesi. T17'nin tam olarak
    yasakladığı şey. O gecede kaybeden tarafta hem 50 sayılık bir maç
    (Gordon) hem bir triple-double (Jokić) vardı, ikisi de kazananın 42
    sayılık maçından (Curry) daha "büyük" göründü ve kanca oraya gitti.
    Çözüm veri katmanında: kilometre kancası SADECE kazananın oyuncusu
    olabilir. Kaybedenin performansı gövdede anılmaya devam ediyor —
    susturulmuyor, sadece cümlenin öznesi yapılmıyor."""
    kilo = olgu.get("en_iyi_kilometre")
    if kilo and kilo.get("oyuncu"):
        takim = oyuncunun_takimi(gercekler or [], kilo["oyuncu"])
        if takim is None or takim == mac["kazanan_kod"]:
            ad = f"{kilo['oyuncu']}'{iyelik_eki(kilo['oyuncu'])}"
            # İki biçim: tam (birleşik istatistik) ve KISA (tek istatistik).
            # Başlık 10 kelimeyi aşarsa kısası kullanılıyor — kancayı
            # tamamen atmaktansa daraltmak doğru, başlığın en güçlü olguyu
            # taşıması ayrı bir kural.
            return ("kilometre",
                    f"{ad} {_gece_ifadesi(kilo, en_iyi_oyuncu)} gecesinde",
                    f"{ad} {kilo['sayi']} sayı{lik_eki('sayı')} gecesinde")
    ka = olgu.get("karar_ani")
    if ka and ka.get("oyuncu"):
        _tam = (f"bitime {ka['saniye_kalan']:.1f} saniye kala "
                f"{ka['oyuncu']}'{iyelik_eki(ka['oyuncu'])} basketiyle")
        return "an", _tam, _tam
    if olgu.get("uzatma"):
        return "an", "uzatmaya giden maçta", "uzatmaya giden maçta"
    if olgu.get("en_buyuk_geri_donus", 0) >= GERI_DONUS_ESIGI:
        return "geri_donus", f"{olgu['en_buyuk_geri_donus']} sayılık farktan dönen", f"{olgu['en_buyuk_geri_donus']} sayılık farktan dönen"
    if olgu.get("surpriz_sonuc"):
        return "surpriz", "sürpriz bir sonuçla", "sürpriz bir sonuçla"
    return None, None, None


def _olgu_cumleleri(mac, olgu, en_iyi_oyuncu, en_iyi_ad, gercekler=None):
    """Gövdede/neden-önemli'de kullanılabilecek (kind, cümle) çiftleri,
    güçten zayıfa. Hepsi olgu kapılarından ve son kapıdan geçmiş."""
    kd = olgu.get("kazanan_derece") or {}
    c = []
    ka = olgu.get("karar_ani")
    if ka and ka.get("oyuncu"):
        c.append(("an", _gecir(f"Maçı belirleyen basketi, bitime {ka['saniye_kalan']:.1f} "
                               f"saniye kala {ka['oyuncu']} attı.")))
    elif olgu.get("uzatma"):
        c.append(("an", _gecir(f"{mac['kazanan_adi']}, maçı uzatmada kazandı.")))
    if olgu.get("en_buyuk_geri_donus", 0) >= GERI_DONUS_ESIGI:
        c.append(("geri_donus", _gecir(f"{mac['kazanan_adi']}, {olgu['en_buyuk_geri_donus']} sayılık farkı eritti.")))
    c.append(("performans", performans(mac, en_iyi_oyuncu, en_iyi_ad)))
    c.append(("kaybeden_performans", kaybedenin_kilometresi(mac, gercekler, en_iyi_ad)))
    if derece_konusulabilir(kd):
        if kd.get("lig_sira") == 1:
            c.append(("derece", _gecir(f"{mac['kazanan_adi']} lig liderliğini sürdürdü.")))
        if siralama_konusulabilir(kd.get("konferans_sira"), kd):
            c.append(("siralama", _gecir(f"{mac['kazanan_adi']}, konferansta {kd['konferans_sira']}. sıraya yükseldi.")))
        if galibiyet_serisi_konusulabilir(olgu.get("kazanan_seri"), kd, olgu.get("kazanan_seri_haber")):
            c.append(("seri", _gecir(f"{mac['kazanan_adi']}, {olgu['kazanan_seri']['uzunluk']} maçlık galibiyet serisini sürdürdü.")))
    return [(k, m) for k, m in c if m]


# "neden önemli" SADECE bağlam olgularından beslenir (lig liderliği,
# ilk-3 sırası, haber değeri olan seri). Maçın kendi olguları (an, geri
# dönüş, performans) GÖVDEYE aittir — "neden önemli" alanına bir
# performans koymak alanın anlamını bozuyordu.
NEDEN_ONCELIK = ("derece", "siralama", "seri")
# Bu üçü AYNI AİLE: biri kullanıldığında diğerleri de tüketilmiş sayılır
# ("lig liderliğini sürdürdü" + "konferansta 1. sıraya yükseldi" aynı
# şeyi iki kez söylüyordu).
_BAGLAM_AILESI = {"derece", "siralama", "seri"}


def mutlaka_metni(gercekler, ham_mac, olgu, en_iyi_ad, takim_adi_fn, kisa=False):
    """Mutlaka bil'in üç alanı — hiçbir olgu iki alanda birden geçmez.

    GÖVDE ALANI (`ozet`/`ozet_kisa`) DEVRE DIŞI, SİLİNMEDİ (kullanıcı
    kararı: "geri dönmek gerekirse dursun"). Burada üretilmeye devam
    ediyor ama yaz.py taslağa yalnız `baslik` ve `neden_onemli` yazıyor,
    derle.py de gövdeyi hiç okumuyor. Geri dönmek için yaz.py'deki iki
    alanlık sözlüğe `ozet`i eklemek yeterli."""
    olgu = olgu or {}
    mac = mac_baglami(gercekler, ham_mac, olgu, takim_adi_fn)
    en_iyi = oyuncu_bul(gercekler, en_iyi_ad)
    kullanilan = set()

    # 1) BAŞLIK — İSKELET LİSTESİNDEN (kullanıcı kararı). Şablon yolu ile
    #    LLM yolu AYNI listeye uyuyor; yoksa LLM reddedildiğinde devreye
    #    giren şablon T31'i ihlal ediyordu (gerçek arıza, 27 Aralık).
    #    Hangi iskeletin doğru olduğuna VERİ karar veriyor.
    baslik = baslik_iskeletinden(mac, olgu, en_iyi_ad,
                                 (en_iyi or {}).get("sayi"))
    # Başlıkta kullanılan olgu, alt satırda tekrar edilmesin.
    karar = olgu.get("karar_ani") or {}
    if karar.get("saniye_kalan") is not None and karar["saniye_kalan"] <= BASLIK_SON_SANIYE:
        kullanilan.add("karar_ani")
    if (olgu.get("en_buyuk_geri_donus") or 0) >= BASLIK_GERI_DONUS:
        kullanilan.add("geri_donus")
    if en_iyi_ad and ((en_iyi or {}).get("sayi") or 0) >= BASLIK_PERFORMANS:
        kullanilan.add("performans")

    havuz = _olgu_cumleleri(mac, olgu, en_iyi, en_iyi_ad, gercekler)

    # 2) NEDEN ÖNEMLİ — kalanlardan, tercih sırasıyla.
    neden = None
    for tercih in NEDEN_ONCELIK:
        for k, m in havuz:
            if k == tercih and k not in kullanilan:
                neden = m
                kullanilan |= _BAGLAM_AILESI
                break
        if neden:
            break

    # 3) GÖVDE — geri kalanlar, bütçe kadar.
    # Kullanıcı kararı (tutarlılık turu): gövde SABİT hedefe yaklaşmalı —
    # 4 cümle / 55+ kelime. Eskiden sadece üst sınır vardı, gövde tek
    # olguyla 5 kelimede kalabiliyordu. Artık kalan olgular kelime
    # tabanına ulaşana kadar sırayla ekleniyor.
    hedef_cumle = OZET_CUMLE if not kisa else SEVIYE_BUTCE["degerse"]
    kalanlar = [m for k, m in havuz if k not in kullanilan]
    # Gövde ARTIK sonucu tekrar etmiyor. Eskiden ilk cümle her zaman
    # sonucun başka sözcüklerle kurulmuş hâliydi ("X, Y karşısında A-B
    # kazandı") — başlık zaten skoru taşıdığı için aynı sayılar iki kez
    # geçiyordu (kullanıcı bildirimi: "111-99 başlıkta ve gövdede").
    # Elde hiç olgu yoksa sonuç cümlesi SON ÇARE olarak kalıyor; boş
    # gövde göndermektense tekrar etmek yeğ.
    govde = [] if kalanlar else [sonuc_alternatif(mac) or sonuc(mac)]
    for m in kalanlar:
        if len(govde) >= hedef_cumle:
            break
        govde.append(m)
    # Hâlâ kısaysa: elde başka olgu yok demektir — mekanik şablon
    # UYDURAMAZ, kısa kalır ve doğrulayıcı bunu işaretler (sessizlik
    # varsayılan; boşluğu doldurmak için olgu icat etmek yasak).

    obj = {"baslik": baslik, ("ozet_kisa" if kisa else "ozet"): " ".join(govde), "muzip": False}
    # Alan ya DOLU ya HİÇ YOK — boş string yazmak doğrulayıcıya "bu alan
    # var ama boş" diye görünüyordu ve her sezon başı gecesinde sahte bir
    # T6 reddi üretiyordu. Söylenecek bağlam olgusu yoksa alan çıkmaz.
    if neden and neden.strip():
        obj["neden_onemli"] = neden
    return obj


def brief_adaylari(mac, olgu, en_iyi_oyuncu, en_iyi_ad):
    """[(kind, metin, guc), ...] — güçten bağımsız, EKLENME sırasıyla.

    `guc`, o türün BÜYÜKLÜĞÜ: 20 sayılık geri dönüş 14 sayılıktan
    güçlü, 32 sayı 28'den güçlü. Gece çapında atama bunu kullanıyor —
    bir türü, o türde en güçlü değere sahip maç alıyor (kullanıcı
    kuralı). Eskiden türü ROZETİ yüksek maç kapıyordu ve daha zayıf bir
    olgu daha güçlüsünü bloke edebiliyordu."""
    return _brief_adaylari(mac, olgu, en_iyi_oyuncu, en_iyi_ad)


def brief_satiri(mac, olgu, en_iyi_oyuncu, en_iyi_ad, haric_kindler=None):
    """"30 saniyede gece" satırı — (kind, metin). Skor HİÇ yazılmaz
    (T19). Gerçek bir olgu yoksa None: brief sabit 5 satır değil,
    dürüst içerik kadar satır."""
    haric = haric_kindler or set()
    adaylar = [(kind, metin) for kind, metin, _ in
               _brief_adaylari(mac, olgu, en_iyi_oyuncu, en_iyi_ad)]

    for kind, metin in adaylar:
        if kind in haric:
            continue
        gecen = _gecir(metin)
        if gecen:
            return kind, gecen
    return None, None


# ---------------------------------------------------------------------------
# MAÇ AKIŞI — SABİT KALIPLAR
# ---------------------------------------------------------------------------
#
# KULLANICI KARARI: bu satırlar LLM'e HİÇ gitmez. Kalıplar burada sabit;
# model ne görür ne üretir. "Bu kalıplar dışında cümle üretilmez; yeni
# olay tipi gerekirse buraya eklenir, model uydurmaz."
#
# Her satır: (cumle, detay). `detay` küçük gri alt satır, yoksa None.
# Girdi doğrudan `akis_olay` gerçeğinin verisi — hiçbir sayı burada
# hesaplanmıyor, yalnız biçimleniyor.

def _akis_takim(kod, ad_fn):
    return ad_fn(kod) if ad_fn else kod


def akis_kaliplari(olay, ad_fn=None):
    """[(kalip_id, cumle, detay)] — o olay için TÜM uygun kalıplar.

    HER TİPE BİRDEN FAZLA KALIP (kullanıcı kararı): okuyucu tipi değil
    CÜMLEYİ görüyor. Tip çeşitliliği sağlandıktan sonra bile "X skoru
    eşitledi" gecede üç blokta geçiyordu (ölçüldü, 27 Aralık).
    Kalıplar SABİT — LLM üretmiyor, seçimi derle.py yapıyor (gece çapında
    en az kullanılmış kalıp önce).

    Sayı ekleri `dogrula.sayi_eki` ile: "17'e" yanlış, "17'ye" doğru —
    ek sayının OKUNUŞUNA uyar. Canlıya çıkmıştı."""
    t = olay.get("tip")
    ev, dep = olay.get("ev_skor"), olay.get("dep_skor")
    skor = f"{ev}–{dep}"
    takim = _akis_takim(olay.get("takim"), ad_fn)
    n = olay.get("sayi")
    oyuncu = olay.get("oyuncu")
    fark = abs(olay.get("fark", 0) or 0)
    k = []

    if t == "ceyrek_sonu":
        if olay.get("basa_bas") or not takim:
            k.append(("ceyrek_basabas", "Skor başa baş gitti", skor))
            k.append(("ceyrek_denk", "Çeyrek denk geçti", skor))
        else:
            k.append(("ceyrek_onde", f"{takim} önde kapadı", skor))
            k.append(("ceyrek_lehine", f"Çeyrek {takim} lehine bitti", skor))
            if fark:
                k.append(("ceyrek_farkla",
                          f"{takim} {fark} sayı önde bitirdi", skor))
    elif t == "devre_farki":
        k.append(("devre_onde", f"{takim} {n} sayı önde", skor))
        k.append(("devre_fark", f"Devrede fark {n}", skor))
        k.append(("devre_girdi", f"Devreye {takim} {n} sayı önde girdi", skor))
    elif t == "ceyrek_ustunlugu":
        rakip = olay.get("rakip_sayi")
        onde = ((olay.get("fark", 0) > 0 and olay.get("takim") == olay.get("ev_kod"))
                or (olay.get("fark", 0) < 0 and olay.get("takim") != olay.get("ev_kod")))
        yon = "çıktı" if onde else "indi"
        detay = f"fark {fark}'{dogrula_sayi_eki(fark)} {yon}" if fark else "skor eşitlendi"
        k.append(("ust_aldi", f"{takim} çeyreği {n}-{rakip} aldı", detay))
        k.append(("ust_ustun", f"{takim} o çeyrekte {n}-{rakip} üstün geldi", detay))
        k.append(("ust_oldu", f"Çeyrek {n}-{rakip} {takim}'{iyelik_eki(takim)} oldu", detay))
    elif t == "en_buyuk_fark":
        k.append(("fark_cikardi",
                  f"{takim} farkı {n}'{dogrula_sayi_eki(n)} çıkardı", "en büyük fark"))
        k.append(("fark_cikti",
                  f"Fark {n}'{dogrula_sayi_eki(n)} çıktı", f"{takim} önde"))
        k.append(("fark_onu", f"{takim} önü {n} sayıya çıkardı", "en büyük fark"))
    elif t == "sayi_serisi":
        k.append(("seri_gitti", f"{takim} {n}-0 gitti", f"fark {fark}"))
        k.append(("seri_arka", f"{takim} arka arkaya {n} sayı buldu", f"fark {fark}"))
        # Ayrılma hâli ("Boston'dan") ayrı bir ek; iyelik ekiyle
        # kurulunca "Boston'undan" gibi bozuk bir biçim çıkıyordu.
        # Ekten kaçınan bir kalıp seçildi.
        k.append(("seri_yapti", f"{takim} seriyi {n}-0 yaptı", f"fark {fark}"))
    elif t == "esitlik":
        if takim:
            k.append(("esit_esitledi", f"{takim} skoru eşitledi", skor))
            k.append(("esit_kapatti", f"{takim} farkı kapattı", skor))
            k.append(("esit_yakaladi", f"{takim} beraberliği yakaladı", skor))
        else:
            k.append(("esit_duz", "Skor eşitlendi", skor))
    elif t == "liderlik":
        # İddia yalnız gerçekten kesinse: sonradan beraberlik olduysa
        # "bir daha değişmedi" maçın kapandığını ima ediyor ve yanıltıyor.
        detay = (f"{skor} · liderlik bir daha değişmedi"
                 if olay.get("kesin", True) else skor)
        if oyuncu:
            k.append(("lider_basket",
                      f"{oyuncu}'{iyelik_eki(oyuncu)} basketiyle öne geçti", detay))
            k.append(("lider_cevirdi", f"{oyuncu} skoru çevirdi", detay))
            # DÖRDÜNCÜ KALIP. "Liderlik" artık her şekilde kritik yuvayı
            # dolduruyor; üç kalıp x iki limit = altı kapasite yoğun
            # gecede yetmiyordu (23 Aralık).
            k.append(("lider_gecirdi", f"{oyuncu} takımını öne geçirdi", detay))
            if takim:
                k.append(("lider_ile", f"{takim}, {oyuncu} ile öne geçti", detay))
        elif takim:
            k.append(("lider_takim", f"{takim} öne geçti", detay))
    elif t == "karar_ani":
        if oyuncu:
            k.append(("karar_basket", f"{oyuncu}'{iyelik_eki(oyuncu)} basketi",
                      f"{skor} · maçı bitirdi"))
            k.append(("karar_sonsoz", f"Son sözü {oyuncu} söyledi", skor))
            k.append(("karar_bitirdi", f"Maçı {oyuncu} bitirdi", skor))
        elif takim:
            k.append(("karar_takim", f"{takim} son sayıyı buldu",
                      f"{skor} · maçı bitirdi"))
    elif t == "kopus":
        k.append(("kopus_actik", f"{takim} farkı {n}'{dogrula_sayi_eki(n)} açtı", skor))
        k.append(("kopus_uzaklasti", f"{takim} bir daha yakalatmadı", skor))
        k.append(("kopus_kopardi", f"{takim} maçı burada kopardı", skor))
    elif t == "rakip_yaklasti":
        k.append(("yaklasti_kadar", f"{takim} farkı {n} sayıya kadar indirdi", skor))
        k.append(("yaklasti_enyakin", f"{takim} en fazla {n} sayıya yaklaştı", skor))
        k.append(("yaklasti_duser", f"Fark {n} sayıya kadar düştü", f"{takim} yaklaştı"))
    elif t == "fark_korundu":
        k.append(("korundu_altina",
                  f"Fark bir daha {n}'{dogrula_sayi_eki(n, 'iyelik')} altına inmedi", None))
        k.append(("korundu_inilmedi",
                  f"{n} sayının altına bir daha inilmedi", None))
    elif t == "en_etkili":
        parca = [f"{olay.get('sayi')} sayı"]
        if olay.get("ribaund"):
            parca.append(f"{olay['ribaund']} ribaund")
        if olay.get("asist"):
            parca.append(f"{olay['asist']} asist")
        ist = ", ".join(parca)
        k.append(("etkili_duz", f"{oyuncu} {ist}", "maçın en etkilisi"))
        k.append(("etkili_oncikti", f"{oyuncu} {ist} ile öne çıktı", None))
        k.append(("etkili_enler", f"Maçın en etkilisi {oyuncu}", ist))
        # DÖRDÜNCÜ KALIP. "En etkili" satırı T14 yüzünden neredeyse her
        # blokta zorunlu; yoğun gecede yedi blok oluyor ve üç kalıp x iki
        # limit = altı kapasite yetmiyordu (18 Aralık: etkili_duz 3 kez).
        k.append(("etkili_kisa", f"{oyuncu} öne çıktı", ist))

    return [(kid, _gecir(c) or c, d) for kid, c, d in k if c]


def akis_satiri(olay, ad_fn=None):
    """(cumle, detay) — ilk kalıp. Geriye dönük uyumluluk için duruyor;
    seçim artık derle.py'de kalıp sayacıyla yapılıyor."""
    k = akis_kaliplari(olay, ad_fn)
    return (k[0][1], k[0][2]) if k else (None, None)


AKIS_TIPLERI = ("ceyrek_sonu", "devre_farki", "ceyrek_ustunlugu", "en_buyuk_fark",
                "sayi_serisi", "esitlik", "liderlik", "karar_ani",
                "fark_korundu", "en_etkili", "rakip_yaklasti", "kopus")


def brief_duz_sonuc(mac):
    """Tür bulamayan maç için düz sonuç cümlesi — SKORSUZ.

    Kullanıcı kuralı: bir maç cümle hakkını türe takıldığı için
    kaybetmesin.

    SKOR YAZILMIYOR, iki sebeple. (1) T19: brief satırında final skor,
    fark haber değeri eşiğini geçmedikçe gereksiz — ölçüldü, 152-150
    biten maçta bu cümle doğrulamada işaretlendi. (2) Satırın hemen
    altında skor ZATEN yazıyor; tekrarlamak yer kaplayıp bilgi
    eklemiyor. Cümlenin kattığı şey skor değil, KİMİN kazandığı:
    şeritte "ATL 150 - CHI 152" yazıyor, kazananı okuyucu iki sayıyı
    karşılaştırarak buluyordu."""
    return _gecir(_duz_iskelet(mac, 0) or "")


# DÜZ SONUÇ İSKELETLERİ. Tek kalıp vardı ve tekrar yasağı KANCA TÜRÜNE
# bakıyordu; düz sonuç cümleleri o yasağın dışında kaldığı için art arda
# diziliyorlardı. 22 Aralık gecesinde yedi satırın beşi aynı iskeletteydi
# ("X, Y'i yendi."). Kullanıcı kuralı: aynı gecede aynı iskelet en fazla
# İKİ kez; üçüncüden itibaren başka bir iskelet.
#
# Hepsi ŞABLON — LLM çağrısı yok, ek maliyet yok. Hepsi yalnız skor
# olgusundan türüyor: kazanan/kaybeden, ev-deplasman ve fark. Uydurma
# yok; "farkı korudu" gibi maçın akışına dair bir iddia BİLEREK yok,
# onu final skorundan doğrulayamayız.
DUZ_ISKELET_SAYISI = 5


def dogrula_fark_esigi():
    """T22'nin eşiği — tek kaynak. Kural değişirse cümle kurucu da uyar."""
    from dogrula import FARK_RAKAMI_ESIGI
    return FARK_RAKAMI_ESIGI


def _duz_iskelet(mac, no):
    """no numaralı düz sonuç iskeleti — uygun değilse None."""
    k, y = mac["kazanan_adi"], mac["kaybeden_adi"]
    ek = belirtme_eki(y)
    evde = mac.get("ev_dep") == "evinde"          # KAZANAN evinde mi
    fark = mac.get("fark") or 0
    if no == 0:
        return f"{k}, {y}'{ek} yendi."
    if no == 1:
        return (f"{k}, {y}'{ek} evinde yendi." if evde
                else f"{k}, {y} deplasmanında kazandı.")
    if no == 2:
        # Özne DEĞİŞİYOR: cümle kaybedenden kuruluyor.
        yk = yonelme_eki(k)
        return (f"{y}, deplasmanda {k}'{yk} kaybetti." if evde
                else f"{y}, evinde {k}'{yk} kaybetti.")
    if no == 3:
        # T22: 20'nin altındaki fark rakamla anılmıyor (skor zaten
        # kartta yazılı). Eşiğin altında bu iskeleti hiç kurmuyoruz —
        # kurup doğrulamada elemek aynı sonucu daha dolambaçlı verirdi.
        if not fark or fark < dogrula_fark_esigi():
            return None
        return f"{k}, {y} karşısında {fark} sayı{lik_eki('sayı')} farkla kazandı."
    if no == 4:
        # SKOR yalnız fark haber değeri eşiğini geçtiğinde (T19). Altında
        # kalırsa cümle doğrulamada elenir ve maç susardı.
        if fark < BRIEF_SKOR_FARK_ESIGI:
            return None
        b, kc = mac.get("buyuk"), mac.get("kucuk")
        if not b or not kc:
            return None
        return (f"{k}, evinde {y}'{ek} {b}-{kc} yendi." if evde
                else f"{k}, {y} deplasmanında {b}-{kc} kazandı.")
    return None


def brief_duz_sonuc_secim(mac, sayac, ust_sinir=2):
    """(metin, iskelet_no) — gecede az kullanılmış iskeleti seçer.

    `sayac`: {iskelet_no: kaç kez kullanıldı} — çağıran gece boyunca
    taşıyor. Bir iskelet `ust_sinir` kez kullanıldıysa atlanıyor.
    Hepsi dolarsa temel iskelete dönülüyor: tekrar, sessizlikten iyidir.
    """
    for no in range(DUZ_ISKELET_SAYISI):
        if sayac.get(no, 0) >= ust_sinir:
            continue
        metin = _duz_iskelet(mac, no)
        if not metin:
            continue
        gecen = _gecir(metin)
        if gecen:
            return gecen, no
    return _gecir(_duz_iskelet(mac, 0) or ""), 0


def _brief_adaylari(mac, olgu, en_iyi_oyuncu, en_iyi_ad):
    k, y = mac["kazanan_adi"], mac["kaybeden_adi"]
    ek = belirtme_eki(y)
    kd = olgu.get("kazanan_derece") or {}
    adaylar = []

    if olgu.get("surpriz_sonuc"):
        adaylar.append(("surpriz", f"Sürpriz bir sonuçla {k}, {y}'{ek} yendi.", olgu.get("fark", 0)))
    ifade = performans_konusulabilir(en_iyi_oyuncu)
    if ifade and en_iyi_oyuncu.get("takim") == mac["kazanan_kod"]:
        # T24 kapısı: brief TEK satır, iki oyuncuyu birden anamaz. Aynı
        # maçta daha yüksek GmSc'li bir kilometre sahibi varsa (tipik
        # olarak KAYBEDEN tarafta — o yüzden buraya aday olamıyor),
        # kazananın daha küçük performansını brief'e taşımak "en iyisi
        # anılmalı" kuralını çiğniyor. Böyle bir durumda performans
        # adayı HİÇ kurulmaz; brief o maç için başka bir olguya
        # (uzatma, geri dönüş) düşer. Gerçek üretim bug'ı: 2025-10-23
        # GSW-DEN'de brief "Curry 42 sayı attı" diyordu, aynı maçta
        # Gordon 50 sayı atmıştı.
        _kilo = olgu.get("en_iyi_kilometre") or {}
        _daha_iyisi_var = bool(_kilo.get("oyuncu")) and _kilo["oyuncu"] != en_iyi_ad
        if not _daha_iyisi_var:
            deger, birim, fiil = ifade
            adaylar.append(("performans", f"{en_iyi_ad}, {y} karşısında {deger} {birim} {fiil}.", deger))
    if olgu.get("en_buyuk_geri_donus", 0) >= GERI_DONUS_ESIGI:
        adaylar.append(("geri_donus", f"{k}, {olgu['en_buyuk_geri_donus']} sayılık farktan dönüp {y}'{ek} geçti.", olgu["en_buyuk_geri_donus"]))
    _ka = olgu.get("karar_ani") or {}
    if _ka.get("oyuncu"):
        adaylar.append(("son_saniye",
                        f"{k}, son saniyede {_ka['oyuncu']}'{iyelik_eki(_ka['oyuncu'])} "
                        f"basketiyle {y}'{ek} geçti.",
                        100 - float(_ka.get("saniye_kalan") or 0)))
    if olgu.get("uzatma"):
        adaylar.append(("uzatma", f"{k}, {y}'{ek} uzatmada geçti.", 1))
    if galibiyet_serisi_konusulabilir(olgu.get("kazanan_seri"), kd, olgu.get("kazanan_seri_haber")):
        adaylar.append(("seri", f"{k}, {y}'{ek} yenerek {olgu['kazanan_seri']['uzunluk']} maçlık galibiyet serisini sürdürdü.", olgu["kazanan_seri"]["uzunluk"]))
    if siralama_konusulabilir(kd.get("konferans_sira"), kd):
        adaylar.append(("siralama", f"{k}, {y}'{ek} yenerek konferansta {kd['konferans_sira']}. sıraya yükseldi.", 30 - kd["konferans_sira"]))
    return adaylar


# ---------------------------------------------------------------------------
# ORKESTRA — bir maçın gövdesini kurar. Bütçe katmandan gelir.
# ---------------------------------------------------------------------------


# Takım kodu → kısa (şehir) ad. Lakabı atarak türetmek güvenilir değil:
# "Portland Trail Blazers"ın lakabı iki kelime, "San Antonio"nun şehri iki
# kelime. derle.TAKIM_KISA ile aynı tablo — orada görüntü için, burada
# başlık kısaltması için gerekiyor.
TAKIM_KISA = {
    "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte",
    "CHI": "Chicago", "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver",
    "DET": "Detroit", "GSW": "Golden State", "HOU": "Houston", "IND": "Indiana",
    "LAC": "LA Clippers", "LAL": "Los Angeles", "MEM": "Memphis", "MIA": "Miami",
    "MIL": "Milwaukee", "MIN": "Minnesota", "NOP": "New Orleans", "NYK": "New York",
    "OKC": "Oklahoma City", "ORL": "Orlando", "PHI": "Philadelphia", "PHX": "Phoenix",
    "POR": "Portland", "SAC": "Sacramento", "SAS": "San Antonio", "TOR": "Toronto",
    "UTA": "Utah", "WAS": "Washington",
}


def mac_baglami(gercekler, ham_mac, olgu, takim_adi_fn, kisa_ad_fn=None):
    kisa_ad_fn = kisa_ad_fn or (lambda kod: TAKIM_KISA.get(kod, kod))
    """Cümle kurucuların ihtiyaç duyduğu ortak sözlük."""
    skor = next(g for g in gercekler if g["tur"] == "skor")["veri"]
    kaybeden_kod = skor["dep"] if skor["kazanan"] == skor["ev"] else skor["ev"]
    return {
        "kazanan_kod": skor["kazanan"],
        "kaybeden_kod": kaybeden_kod,
        "kazanan_adi": takim_adi_fn(skor["kazanan"], ham_mac),
        "kaybeden_adi": takim_adi_fn(kaybeden_kod, ham_mac),
        # Kısa (şehir) biçim — başlık 10 kelimeyi aşarsa devreye giriyor.
        "kazanan_kisa": kisa_ad_fn(skor["kazanan"]) if kisa_ad_fn else takim_adi_fn(skor["kazanan"], ham_mac),
        "kaybeden_kisa": kisa_ad_fn(kaybeden_kod) if kisa_ad_fn else takim_adi_fn(kaybeden_kod, ham_mac),
        "ev_dep": "evinde" if skor["kazanan"] == skor["ev"] else "deplasmanda",
        "buyuk": max(skor["ev_skor"], skor["dep_skor"]),
        "kucuk": min(skor["ev_skor"], skor["dep_skor"]),
        "fark": abs(skor["ev_skor"] - skor["dep_skor"]),
        "en_buyuk_fark_gecede_mi": (olgu or {}).get("en_buyuk_fark_gecede_mi", False),
        # Gece çapında TEK: "Mağlup tarafta ..." kalıbını kullanma hakkı
        # olan oyuncunun adı (yoksa None). Kararı gece_kalip_plani veriyor.
        "maglup_anilabilir_ad": (olgu or {}).get("maglup_anilabilir_ad"),
    }


def govde(gercekler, ham_mac, olgu, en_iyi_ad, kanca_harf, seviye, takim_adi_fn):
    """Bir maçın metni. Bütçe (kullanıcı kararı):
        mutlaka → 3 cümle: Sonuç + An + Performans
        degerse → 2 cümle: Sonuç + (Performans varsa o, yoksa An)
        gec     → 1 cümle: SADECE sonuç

    TEK istisna: T14 eşiğini geçen performans "gec" katmanında bile
    kısa bir ek olarak girer — "en iyi performans mutlaka anılır"
    kuralı bütçe kısıtını ezer (kullanıcının önceki tur kararı)."""
    olgu = olgu or {}
    mac = mac_baglami(gercekler, ham_mac, olgu, takim_adi_fn)
    butce = SEVIYE_BUTCE[seviye]

    en_iyi_oyuncu = None
    if en_iyi_ad:
        en_iyi_oyuncu = next(
            (g["veri"] for g in gercekler if g["tur"] == "oyuncu_stat" and g["veri"]["oyuncu"] == en_iyi_ad),
            None,
        )

    onek = kanca_oneki(kanca_harf, olgu, mac, en_iyi_oyuncu) if butce > 1 else None
    # Kanca oyuncuyu zaten andıysa ayrıca performans cümlesi kurulmaz
    # (gerçek üretim bug'ı: "LeBron James'in 28 sayılık gecesinde ...
    # LeBron James 12 asist verdi." — aynı oyuncu iki cümlede).
    kilo_ = olgu.get("en_iyi_kilometre") or {}
    oyuncu_kancada = bool(
        onek and kanca_harf == "P" and en_iyi_oyuncu
        and kilo_.get("oyuncu") == en_iyi_oyuncu.get("oyuncu")
    )
    cumleler = [sonuc(mac, onek) or sonuc(mac)]
    kalan = butce - 1

    perf = None if oyuncu_kancada else performans(mac, en_iyi_oyuncu, en_iyi_ad)
    # Kaybedenin performansı anılacaksa kazananınki ONDAN ÖNCE gelir.
    perf_onculu = None
    if perf and perf.startswith("Mağlup tarafta"):
        kazanan_oyuncu = max(
            (g["veri"] for g in gercekler if g["tur"] == "oyuncu_stat" and g["veri"]["takim"] == mac["kazanan_kod"]),
            key=lambda d: d.get("sayi", 0),
            default=None,
        )
        perf_onculu = kazananin_en_iyisi(mac, kazanan_oyuncu)

    if kalan <= 0:
        # "Bunları geç" — tek cümle, TEK istisna eşiği geçen performans.
        return " ".join([cumleler[0]] + ([perf] if perf else []))

    an_cumlesi = an(mac, olgu, kancada_kullanildi=(onek is not None and kanca_harf in ("A", "F")))

    # Bütçe darsa performans önceliklidir (T14 zorunluluğu), an düşer.
    if perf and kalan < 2:
        if perf_onculu and kalan >= 1:
            cumleler.append(perf_onculu)
        cumleler.append(perf)
    else:
        if an_cumlesi and kalan > 0:
            cumleler.append(an_cumlesi)
            kalan -= 1
        if perf and kalan > 0:
            if perf_onculu and kalan >= 2:
                cumleler.append(perf_onculu)
                kalan -= 1
            cumleler.append(perf)
    return " ".join(c for c in cumleler if c)
