"""
yaz.py — OVERNIGHT boru hattının 6. adımı.

Girdi:  gerçek/{tarih}.json + skor/{tarih}.json + ham/{tarih}.json
Çıktı:  taslak/{tarih}.json — LLM metni (veya reddedilen alanlar için
        şablon modu çıktısı)

Mimari (kullanıcı notlarına göre):

1. Örnek metin taklit ettirilmez. `sistem_prompt()`, dil kılavuzunun
   kural bölümünü (Bölüm 1) BİREBİR gömer ama örnek gece metnini
   (Bölüm 2) hiç göndermez — model örnek cümleleri (`"hava atışı oldu"`
   gibi) asla görmüyor, sadece kuralları görüyor. Ayrıca açıkça
   yasaklanıyor: bu dokümandaki hiçbir ifade tekrar kullanılamaz.

2. Bütün metin üretimi GÜÇLÜ modelle (`GUCLU_MODEL`) yapılıyor, MAÇ
   BAŞINA ayrı çağrıyla:
   - Grup A: "mutlaka" DIŞINDAKİ her maçın `gec_satiri`'si kendi tek
     çağrısında üretilir (`grup_a_uret_tekli`) — daha önce 9 maç TEK
     çağrıda toplu üretiliyordu, ama Sonnet'in adaptive thinking'i
     böyle büyük bir yanıtta bütçeyi tüketip metin bırakmıyordu (ve
     zorla küçültülünce kalite düşüyordu). Maç başına ayrı çağrı hem
     bütçe sorununu çözüyor hem de her maça tam dikkat ayırıyor.
     `brief` (30 saniyede gece, 5 satır) ayrı ve küçük bir çağrıda
     üretiliyor (`brief_uret`).
   - Grup B: SADECE "mutlaka" katmanındaki maçın `baslik` +
     `neden_onemli` + `ozet`'i — gecenin tek yüksek-sesli metni.
   - Muziplik bütçesi (Grup A içinde en fazla 2, gece toplamında en
     fazla 3) maç başına ayrı çağrılar arasında SIRAYLA takip edilir —
     her çağrıya "kalan pay" bildirilir.
   - Gözden geçirme (`grup_a_gozden_gecir`): Grup A çıktısı üzerinden
     ikinci bir Sonnet çağrısı geçiyor ama bu çağrının CİLALAMA yetkisi
     yok — sadece "anlamlı mı" sorusuna REDDET/kabul cevabı verir.
     Reddedilen maç bir kez daha, sıfırdan üretilir.

3. Ret oranı ölçülür (`son_rapor.ret_orani`) — boru hattının sağlık
   göstergesi. Şablon moduna düşen alan sayısı da ayrıca raporlanıyor.

4. Model seçimi: TÜM üretim güçlü modelle (`GUCLU_MODEL`) yapılıyor.
   Daha önce ucuz model (`UCUZ_MODEL`) Grup A'da kullanılıyordu ama
   dokuz maçlık bir gecede gerçek Türkçe kusurları ("kaybış",
   "puanık", anlamsız cümleler) üretti — kullanıcı kararı bunu tersine
   çevirdi: metin kalitesi maliyetten önce gelir. `UCUZ_MODEL` sadece
   "Bunları geç" kelime bütçesi aşıldığında mekanik cümle kısaltma
   için hâlâ kullanılıyor (bkz. `gec_tier_butcesini_uygula`) — o iş
   yaratıcı yazım değil, tek cümleye sıkıştırma.

5. Şablon modu (`sablon_uret`) — iki deneme de doğrulamayı geçemezse
   devreye giriyor. Tamamen `gercekler`den kurulur, LLM kullanmaz,
   dogrula.py'yi HER ZAMAN geçer (sadece alan değerlerinden oluştuğu
   için T1/T2 otomatik sağlanır).

Ayrıca "Bunları geç" bölümüne TOPLAM 220 kelime bütçesi var (bkz.
`gec_tier_butcesini_uygula`) — satır başına sabit bir uzunluk sınırı
yerine, sakin bir gecede 9 maçın hepsi 3 cümle yazarsa "geç" bölümü
sayfanın en uzun kısmı olur ve triyaj vaadini bozar. Bütçe aşılırsa
EN DÜŞÜK ROZETLİ maçlardan başlayarak kısaltma isteniyor.

6. Prompt caching + maliyet raporu. Sistem promptu (dil kılavuzunun
   Bölüm 1'i) gece boyunca hiç değişmiyor — `llm_cagir()` bunu
   `cache_control: ephemeral` ile işaretliyor, aynı gecedeki art arda
   çağrılar (Grup A, Grup B, kelime bütçesi kısaltmaları) sistem
   promptunu tekrar tekrar tam fiyata ödemek yerine bir kez yazıp
   ucuza okuyor. Her `yaz()` çalıştırması sonunda gerçek girdi/çıktı/
   önbellek token sayılarını ve tahmini dolar maliyetini yazdırıyor
   (`kullanim_raporu()`) — gece başına gerçek maliyeti görmek için.

NOT: Bu ortamda ANTHROPIC_API_KEY tanımlı değil — `llm_cagir()` gerçek
bir API anahtarıyla çalışacak şekilde yazıldı ama bu oturumda
çalıştırılamadı. Kabul testi için bkz. konuşmadaki açıklama.
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

from dogrula import (
    mac_metnini_dogrula,
    brief_metnini_dogrula,
    yasakli_yukle,
    kelime_say,
    ASGARI_KELIME,
    cumle_say,
    ALAN_UZUNLUK_ADI,
    EN_IYI_PERFORMANS_ESIKLERI,
    UST_USTE_ESIGI,
    GERI_DONUS_ESIGI,
    LIDER_DEGISIM_ESIGI,
    UST_USTE_DESENI,
)
from kalip_secici import (
    yildizlar_yukle,
    olgulari_hesapla,
    kademe_hesapla,
    gece_kanca_ata,
    gece_niteleyici_ata,
    GALIBIYET_SAYISI_YUVARLAK,
    PLAY_IN_ARALIGI,
)
from hesapla import takim_kalitesi_hesapla
import cumle

BUYUK_FARK_ESIGI_TEK_CUMLE = 20  # kullanıcı kararı (2. tur): fark 20+
# olmadıkça sayısal olarak hiç anılmaz — kalip_secici.FARK_ESIGI (20)
# ile AYNI eşik, iki ayrı bar olmasın. Bu eşiği geçtiğinde bile ayrı
# bir "rakibine N sayı fark attı" cümlesi kurulmuyor, TEK cümlenin
# fiiline yansıyor ("ezdi").

KOK = Path(__file__).parent
GERCEK_DIZIN = KOK / "gercek"
HAM_DIZIN = KOK / "ham"
SKOR_DIZIN = KOK / "skor"
TASLAK_DIZIN = KOK / "taslak"

UCUZ_MODEL = "claude-haiku-4-5"
GUCLU_MODEL = "claude-sonnet-5"

# $/1M token, 2026-08-14 itibarıyla (bkz. platform.claude.com/docs/pricing).
# Sonnet 5'in tanıtım fiyatı 2026-08-31'de bitiyor, listeye tarih notu düştük
# ki fiyat değiştiğinde burası fark edilip güncellensin.
FIYATLANDIRMA = {
    UCUZ_MODEL: {"girdi": 1.00, "cikti": 5.00},
    GUCLU_MODEL: {"girdi": 2.00, "cikti": 10.00},  # tanıtım fiyatı, 2026-08-31'e kadar geçerli — sonrası 3.00/15.00
}
# Prompt caching kabaca çarpanları: yazma ~1.25x taban girdi fiyatı (5dk TTL),
# okuma ~0.1x taban girdi fiyatı.
CACHE_YAZMA_CARPANI = 1.25
CACHE_OKUMA_CARPANI = 0.10
# Anthropic Message Batches API: girdi+çıktı (ve önbellek) fiyatı standart
# senkron fiyatın YARISI — istek sayısından bağımsız, tek isteklik bir
# batch bile bu indirimi alır. Karşılığında gecikme var (dakikalar-saatler,
# garanti yok) — "acele yok" olan toplu/gece-öncesi üretim için doğru takas.
BATCH_INDIRIM = 0.5

# ---------------------------------------------------------------------------
# Günlük harcama tavanı (canlı yayın için — kullanıcı kuralı)
# ---------------------------------------------------------------------------
# Kullanıcı kuralı: "Günlük harcama $0.30'u aşarsa o gün şablon moduna
# düşsün." Tavan TEK boğaz noktasında (`llm_cagir`) uygulanıyor — üretim
# yolları çoğaldıkça kuralın bir yolda unutulması mümkün olmasın diye
# (aynı gerekçe cumle.py'deki `_gecir` kapısında da var).
#
# Tavan ORTAM DEĞİŞKENİNDEN gelir (GUNLUK_BUTCE_USD). Tanımlı değilse
# tavan YOKTUR — elle çalıştırmalarda davranış hiç değişmiyor, sadece
# zamanlanmış yayın işi tavanı koyuyor.
#
# Kontrol çağrıdan ÖNCE yapılıyor ve bir çağrılık pay ayrılıyor: aksi
# halde tavanı aşan çağrı zaten yapılmış oluyordu ve tavan "aşıldıktan
# sonra haber veren" bir sayaçtan ibaret kalıyordu.
TAHMINI_CAGRI_USD = 0.10
BUTCE_DURUMU = {"asildi": False, "tavan": None}


class ButceAsildi(RuntimeError):
    """Günlük harcama tavanına ulaşıldı — bu alan şablona düşecek.

    `_grup_b_dongu` her istisnayı yakalayıp zengin şablon fallback'ine
    geçtiği için ayrıca ele alınması gerekmiyor; tavan devreye girdiğinde
    gecenin kalanı kendiliğinden şablonla üretilir."""


def _butce_tavani():
    ham = os.environ.get("GUNLUK_BUTCE_USD", "").strip()
    if not ham:
        return None
    try:
        return float(ham)
    except ValueError:
        print(f"UYARI: GUNLUK_BUTCE_USD okunamadı ({ham!r}) — tavan uygulanmıyor.")
        return None

GEC_TIER_KELIME_BUTCESI = 220
MAX_DENEME = 2  # doğrulama başarısız olursa en fazla bu kadar yeniden dene
# Grup B (Mutlaka bil) — gecede EN FAZLA 3 metin (8.5+ rozet), en
# yüksek rozetli tam anlatı diğerleri kısa (bkz. MUTLAKA_ESIGI/
# MUTLAKA_MAX_MAC). Kullanıcı
# kararı: önce 2'den 5'e çıkarıldı, sonra maliyet araştırması (25 Aralık
# $0.70'e mal oldu, her BAŞARISIZ deneme de tam fiyat ödüyor + adaptive
# thinking bütçesi harcıyor) sonrasında 3'e indirildi — uzunluk onarımı
# bu sınırdan MUAF (ayrı, ucuz ve neredeyse hep işe yarayan bir döngü).
MAX_DENEME_GRUP_B = 3
# Kullanıcı kararı (canlıya alma turu): bir gecede LLM'e giden "Mutlaka
# bil" maçı sayısı. Üçü birden göndermek maliyeti üçe katlıyordu ve
# 2./3. maç zaten KISA anlatı — şablonun en iyi olduğu yer. Sadece en
# yüksek rozetli maç LLM'den geçiyor, kalanı şablondan. Normal sezonda
# yeniden 3'e çıkarılabilir; tek yerden değişsin diye sabit.
MUTLAKA_LLM_MAC_SAYISI = int(os.environ.get("MUTLAKA_LLM_MAC_SAYISI", "1"))
UZUNLUK_ONARIM_MAX_TUR = 5
PARALEL_ISCI_SAYISI = 6  # Grup A maçları eşzamanlı üretilirken kaç iş parçacığı


MUTLAKA_ESIGI = 8.5
MUTLAKA_MAX_MAC = 3


def _mutlaka_ve_diger(skor_gece):
    """Formül dokümanı (overnight-deger-skoru-v2-1.md, §5 Katmanlar)
    baştan beri şunu söylüyordu: rozeti 8.5+ olan HER maç Mutlaka bil'e
    girer, en fazla 3 — hiçbiri geçmezse en yüksek olan yine girer. Kod
    bir ara turda bunu YANLIŞLIKLA "her zaman tek maç"a indirmişti
    (kullanıcı düzeltmesi: 25 Aralık'ta Knicks-Cavaliers 126-124, iki
    oyuncu 34'er sayı, 8.99 rozetle bile "Bunları geç"e düşüyordu —
    doğrudan bu regresyonun sonucu). Kural geri getirildi: 8.5+ olan
    EN FAZLA 3 maç sırayla girer, biri bile geçmiyorsa tek en yüksek
    maç girer. Maliyet kontrolü ARTIK burada değil, tiered uzunlukta
    (bkz. yaz_hibrit — sadece #1 tam anlatı, #2/#3 kısa)."""
    tum_maclar = sorted(skor_gece["maclar"], key=lambda m: -m["rozet"])
    if not tum_maclar:
        return [], []
    esigi_gecen = [m for m in tum_maclar if m["rozet"] >= MUTLAKA_ESIGI][:MUTLAKA_MAX_MAC]
    mutlaka = esigi_gecen if esigi_gecen else [tum_maclar[0]]
    mutlaka_idleri = {m["mac_id"] for m in mutlaka}
    diger = [m for m in tum_maclar if m["mac_id"] not in mutlaka_idleri]
    return mutlaka, diger


# ---------------------------------------------------------------------------
# Sistem promptu
# ---------------------------------------------------------------------------


KUTUPHANE_DOSYASI = KOK / "overnight-kalip-kutuphanesi.md"


def _kutuphane_metni():
    return KUTUPHANE_DOSYASI.read_text()


def _bolum_al(metin, baslangic_basligi, bitis_basligi):
    b = metin.index(baslangic_basligi)
    e = metin.index(bitis_basligi) if bitis_basligi else len(metin)
    return metin[b:e].strip()


def kalip_iskeleti():
    """Bölüm 1 — evrensel iskelet (CÜMLE1/CÜMLE2 şablonu). Artık uzun
    kural anlatımlarının (eski `dil_kilavuzu_kurallari`) YERİNE geçiyor
    — kullanıcı kararı: model "ne anlatayım" sorusunu çözmüyor, iskelet
    ve malzeme (kanca + niteleyici + örnek) veriliyor, o sadece cümleyi
    kuruyor.

    "Örnek:" bloğu BİLEREK dışlanıyor — o blok Türk ligi arşivinden
    ("Trabzonspor", "Tofaş", "Haftanın açılışında") birebir, sadece
    İSKELETİ göstermek için kalmış ama "Haftanın açılışında" tam olarak
    yasaklı haftalık çerçeve kalıbı (bkz. Bölüm 7). Modelin görmemesi
    gereken bir örnek gece metnini asla göstermeme ilkesiyle aynı
    gerekçe — soyut şablon kalır, somut Türk ligi içeriği kalkar."""
    tam = _bolum_al(_kutuphane_metni(), "## 1. Evrensel iskelet", "## 2. Kanca bankası")
    ornek_basi = tam.index("Örnek:")
    ornek_sonu = tam.index("Çeşitlilik iskeletten")
    return tam[:ornek_basi].strip() + "\n\n" + tam[ornek_sonu:].strip()


def kanca_bankasi_metni(harf):
    """Bölüm 2'den TEK bir kanca kategorisinin (harf) açılış cümle
    örneklerini döner — modele sadece SEÇİLMİŞ kategori gönderiliyor,
    bütün banka değil (token israfı + seçim özgürlüğü modelde kalmasın
    diye)."""
    metin = _kutuphane_metni()
    bolum = _bolum_al(metin, "## 2. Kanca bankası", "**Kural:** aynı gecede")
    baslik_regex = re.compile(rf"### {re.escape(harf)} — ([^\n]+)\n((?:> .*\n?)+)")
    m = baslik_regex.search(bolum)
    if not m:
        return ""
    return m.group(2).strip()


def one_cikma_fiilleri_listesi():
    metin = _kutuphane_metni()
    bolum = _bolum_al(metin, "### Öne çıkma fiilleri", "Aynı gecede aynı fiil")
    satirlar = [l.lstrip("> ").strip() for l in bolum.splitlines() if l.strip().startswith(">")]
    return [f.strip() for satir in satirlar for f in satir.split("·")]


def ornekler_yukle():
    """Bölüm 6 — kanca harfine göre gruplanmış örnek cümleler.
    {harf: [(kademe, metin), ...]}"""
    metin = _kutuphane_metni()
    bolum = _bolum_al(metin, "## 6. NBA'e uyarlanmış örnekler", "## 7.")
    ornekler = {}
    for blok in re.finditer(r"\*\*(\w+) — kanca (\w)[^\n*]*\*\*\n((?:> .*\n?)+)", bolum):
        kademe, harf, govde = blok.group(1), blok.group(2), blok.group(3)
        metin_ornek = " ".join(l.lstrip("> ").strip() for l in govde.splitlines() if l.strip())
        ornekler.setdefault(harf, []).append((kademe, metin_ornek))
    return ornekler


def sistem_prompt():
    return f"""Sen OVERNIGHT sitesi için NBA gece özeti yazan bir editörsün. Türkçe yazıyorsun.

Her metin, editörün dört yıllık arşivinden çıkarılmış TEK bir evrensel
iskelete oturur — sen bu iskeleti icat etmiyorsun, sana veriliyor. Senin
tek işin: sana verilen kancayı, niteleyicileri ve gerçekleri bu iskelete
doğru cümlelerle yerleştirmek.

{kalip_iskeleti()}

TERİM VE DİL KURALLARI (kısa, pazarlıksız):
- "sayı" kullan, "puan" ASLA kullanma (puan sadece lig sıralaması — "puan durumu").
- "basket" kullan, "sepet" ASLA kullanma (sepet fiziksel pota, basket sayı atışı).
- Duyulan geçmiş zaman (-mış/-miş/-muş/-müş) YASAK. Bilinen geçmiş zaman (-dı/-di/-du/-dü) ZORUNLU.
- Takım adı: cümledeki İLK anışta tam şehir/takım adı ("Milwaukee Bucks"
  ya da "Milwaukee"), İKİNCİ anıştan itibaren takma ad ("Bucks")
  kullanılabilir. Üç harfli kod (MIL gibi) ASLA kullanma.
- Sana verilen `gercekler` DIŞINDA hiçbir sayı, isim veya olay yazma —
  bilmediğin bir şeyi yazma, sıkıcı olmak yanlış olmaktan iyidir.
- Sana verilen niteleyici/kanca listesinin DIŞINDA olgu uydurma — sadece
  sana bildirilen ve gerçeklerde karşılığı olan şeyleri kullan.
- "Double-double"/"triple-double" SADECE oyuncunun sayı/ribaund/asist/
  çalma/blok kategorilerinden GERÇEKTEN 2'sinde (double-double) ya da
  3'ünde (triple-double) 10 veya üzeri varsa yazılır — saymadan yazma.
  "30 sayı, 7 asist" double-double DEĞİLDİR (asist 10'un altında).
- "Kariyer rekoru", "sezon rekoru", "franchise/kulüp/takım rekoru",
  "ilk kez", "en yüksek", "tarihte", "kariyerinin en iyi..." gibi
  ifadeler SADECE bu maçta bir "kilometre" gerçeği OLAĞANÜSTÜ bir
  eşiği (60+ sayı, 25+ ribaund, 20+ asist, 15+ üçlük, quadruple-double,
  50+ sayılık bir triple-double) gösteriyorsa yazılabilir — göstermiyorsa
  YASAK, uyduruyorsun demektir (gerçek üretim bug'ı: "Pascal Siakam ...
  kariyer rekorunu kırdı" denmişti, oysa gerçek kariyer rekoru çok daha
  yüksekti). Bu eşiği geçen bir performans varsa ÇERÇEVEYİ KULLAN, sıkıcı
  bir cümleye sığdırma — ama KESİN BİR SIRA/RANK NUMARASI ASLA verme
  ("tarihin ikinci en yüksek skoru", "3. en iyi performans" gibi) — bunu
  doğrulayacak bir all-time sıralama kaynağımız yok, sıra iddiası
  kilometre eşiği geçilse BİLE her zaman uydurma sayılır. Bu kilometre
  gerçeğinde bir "baglam" alanı VARSA — YAPISAL VERİ, hazır bir cümle
  DEĞİL, bu SAYILARI KENDİ CÜMLENLE anlat. İki türü var, "olcek" alanına
  bak:
  - "olcek": "nba_tarihi" — tur adı, "ondan_once_oyuncu_sayisi" ve
    "ondan_once_kez_sayisi" taşır. TERCİH EDİLEN çerçeve: oyuncuyu
    listenin İÇİNE koy ("bu eşiği geçen 9. oyuncu oldu" gibi,
    ondan_once_oyuncu_sayisi+1) — "sadece 8 oyuncuda görüldü" gibi
    edilgen/mesafeli bir ifadeden daha güçlü. "ondan_once_kez_sayisi"
    0'sa bu eşik daha önce HİÇ geçilmemiş demektir, "ilk kez" diyebilirsin.
  - "olcek": "oyuncu_sezonu" — bu OYUNCUNUN bu SEZONUDUR, NBA tarihi
    değil (ör. "40+ sayı" eşiği) — "bu_sezon_once_kac_kez" taşır (ör.
    "bu sezon ondan önce 3 kez 40+ sayı atmıştı"). Bunu "NBA tarihinde"
    diye ANLATMA — bu oyuncuya ve bu sezona özel bir sayı, all-time bir
    iddia değil.
  Sayı somut, belirsiz övgüden ("bir avuç oyuncu") daha güçlüdür — varsa
  SAYIYI KULLAN. DİKKAT: "tur" alanındaki eşik adı ("60+ sayı" gibi) bir
  KATEGORİ ETİKETİDİR, oyuncunun O MAÇTA gerçekten ürettiği bir sayı
  DEĞİL — gerçek üretim bug'ı: model "Adebayo 3. çeyrekte attığı serbest
  atışla 60 sayıya ulaştı" diye UYDURMUŞTU (60, eşik etiketiydi, maçın
  hiçbir anında gerçekleşen bir olay değildi — oyuncunun asıl sayısı
  83'tü). Eşik etiketindeki çıplak sayıyı ASLA bir oyun-içi olay/an gibi
  anlatma ("X sayıya ulaştı" gibi) — SADECE "ondan_once_oyuncu_sayisi"/
  "ondan_once_kez_sayisi"/"bu_sezon_once_kac_kez" rakamlarını, oyuncunun
  GERÇEK maç istatistiğine (`oyuncu_stat` gerçeğindeki `sayi`) bağlı bir
  cümlede kullan (ör. "bu eşiği ondan önce sadece 38 oyuncu geçmişti"),
  eşiğin kendi sayısını (60) tekrar etme. "baglam" alanı yoksa (ya da
  null'sa) NİTELİKSEL, sayısız
  bir çerçeve yaz ("tarihte nadir görülen bir eşiği geçti" gibi), sayı
  UYDURMA.
- TEPKİ CÜMLESİ — dar ve eşiğe bağlı bir izin (hüküm katmanının küçük bir
  öncüsü, geniş hali sonra gelecek). Şu anki dil resmi/memur gibi kalıyor
  ("...performans, ... olması nedeniyle öne çıktı"). Şu şartlar hepsi
  sağlanıyorsa KISA bir tepki cümlesi kurabilirsin:
  - SADECE bu maçta bir "kilometre" gerçeği varsa (50+ sayı, triple-double,
    20+ ribaund, 15+ asist, 10+ üçlük, 5+ blok gibi eşiklerden biri) —
    kilometre gerçeği yoksa tepki cümlesi de yok.
  - Gecede EN FAZLA BİR KEZ (muziplik kotasıyla aynı mantık — kıt bir
    kaynak, her fırsatta harcama).
  - Tepki bir OLGUYA bağlı kalmalı ("56 sayıyla triple-double yaptı" gibi
    somut bir şeye), oyuncunun KARAKTERİ hakkında yorum OLAMAZ ("agresif
    bir adam", "asla pes etmiyor" gibi kişilik değerlendirmesi YASAK).
  - Küfür ve abartılı argo YASAK — "çıldırdı", "durdurulamadı", "tek
    başına bitirdi" düzeyinde kal, bunun ötesine geçme.
  Örnek: "Jokić çıldırdı, 56 sayıyla triple-double yaptı, bunu NBA
  tarihinde ondan önce beş kişi başarmıştı." Bu bir İSTİSNA, varsayılan
  değil — kilometre gerçeği yoksa ya da bu gece başka bir maçta zaten
  kullandıysan sade/betimleyici dile dön.
- "Doğu"/"Batı" konferans adları özel isimdir, büyük harfle başlar
  ("Doğu'da 9-8" — "doğu'da" değil).
- "Taşımak/getirmek" gibi fiillerin NESNESİ SKORDUR, takım değil —
  gerçek üretim bug'ı: "...üçlüğü Minnesota'yı 115-115'e taşıdı" bozuk
  bir cümle (bir takım bir sayıya "taşınamaz"). Doğrusu: "...üçlüğüyle
  skoru 115-115'e getirdi" ya da "Minnesota, ... üçlüğüyle farkı
  kapattı" — takım CÜMLENİN ÖZNESİ olur, SKOR nesnesi olur, takım
  nesne olamaz.
- Sadece istenen JSON şemasına uygun yanıt ver. Şema dışında hiçbir
  metin, açıklama, markdown kod bloğu işareti yazma — saf JSON.

OVERNIGHT telefonda, yatakta, uyanır uyanmaz okunuyor — hiçbir alan
ekranda kaydırma gerektirmemeli. Her alanın kendi sıkı kelime/cümle
sınırı var (aşağıdaki talimatlarda belirtiliyor); sınıra ulaşmak için
gereksiz ikinci bir sayı/ayrıntı ekleme, aşırı hassas zaman damgası
("45.7 saniye kala" yerine çoğu zaman "son dakikada" yeter) kullanma,
aynı bilgiyi iki cümlede tekrarlama.

Yasaklı ifadeler (klişeler, register hataları, renk lakabı, koç adıyla
takım anma, haftalık çerçeve gibi) ayrıca mekanik olarak denetlenecek —
bunlardan olabildiğince kaçın. En sık tekrarlanan somut hatalar:

- "sergiledi", "kaydetti", "elde etti", "gerçekleştirdi", "imza attı"
  YASAK (fiil şişirmesi) — düz "attı", "yaptı", "üretti" kullan.
- Skor fark rakamını (ör. "2 sayı farkla") 20'nin ALTINDA hiç yazma —
  skor zaten kartta yazılı, okuyucu farkı kendisi görüyor. 20+ bir fark
  varsa bile ayrı bir cümle kurma, kelime seçimine yansıt.
- "açığı kapattı" YASAK → "farktan döndü" / "farkı eritti" de.
- "farkı açtı" YASAK → "farkı yükseltti" / "farkı çıkardı" de.
- "çeyreği kazandı" YASAK → o çeyreğin skorunu/üstünlüğünü anlat,
  "kazandı" fiiliyle bağlama.
- "geri getirmek" YASAK (basketbolda yanlış kullanım).
- "ribaund" kelimesini HER ZAMAN "d" ile yaz — "ribaunt" YAZIM HATASI.
- UZUN TİRE (—) YASAK, hiçbir alanda kullanma — virgül veya nokta kullan
  ("Jokić çıldırdı — 56 sayı attı" DEĞİL, "Jokić çıldırdı, 56 sayı attı").
- SEZON BAŞI SUSMA KURALI: "derece" faktöründe "sezon_guvenilir": false
  görürsen (takım 10 maçın altında), o takımın galibiyet-mağlubiyet
  rekoru ("1-0'a yükseldi", "0-1'e düştü", "sezona 1-0 başladı" — hiçbir
  biçimde, rakamla ya da rakamsız), konferans/lig sırası, "zirve maçı"
  ya da "sürpriz sonuç" çerçevesi, galibiyet/mağlubiyet serisi, ya da
  "bu sezon önce N kez" türü bir sıklık iddiası YAZILMAZ — 1-9 maçlık
  bir örneklemle kimin favori/lider/namağlup olduğu bilinemez. Bu
  durumda metin maçın KENDİSİNE dayanır: skor, performans, maçın nasıl
  kazanıldığı, geri dönüş, son saniye.
- SESSİZLİK VARSAYILAN (mimari kural): hiçbir maçın slotu yok, her cümle
  hak ederek girer. Gövde/özet en fazla şu üç şeyi anlatır — maçın en
  iyi performansı (T14 eşiğini geçiyorsa), maçı belirleyen bir an (son
  saniye/geri dönüş/uzatma), kilometre taşı. Bunlardan HİÇBİRİ yoksa
  metin TEK cümlede kalır — bu bir eksiklik değil, doğru davranış.
  "Washington, Brooklyn'i 119-99 yendi." tek başına yeterli bir metindir,
  zorla bir niteleyici/ikinci cümle uydurma.
- Bir maçta AYNI kilometre eşiğini birden fazla oyuncu geçmişse (ör. iki
  triple-double) SADECE en yüksek GmSc'li olanı an. Gerçeklerdeki
  "kilometre" kayıtlarının "gmsc" alanı bunu söylüyor — düşük olanı
  anmak REDDEDİLİR.
- Lider değişimi SADECE maç geneli toplamı 15+'sa anılır, ve SADECE genel
  toplam olarak — "son periyotta liderlik 5 kez el değişti" gibi bir alt
  kırılım HİÇBİR ZAMAN yazılmaz (maç geneli iyi bile olsa, bir periyoda
  indirgemek gürültü). Doğru kalıp: "Liderliğin N kez el değiştirdiği
  maçta..." — "N lider değişimli maçta" gibi bir sıfat bileşiği YASAK,
  bozuk Türkçe.
- "Toplamak" SADECE ribaund için kullanılır ("14 ribaund topladı").
  Sayı için HER ZAMAN "attı" ("36 sayı attı" — "36 sayı topladı" DEĞİL).
  Asist için "verdi"/"üretti" kullanılır, "topladı" değil.
- Konferans/lig sıralaması SADECE ilk 3 için anılır — "10. sıraya
  oturdu", "13. sıraya oturdu" gibi bir sıra hiçbir şey anlatmıyor,
  YAZILMAZ.
- Bir takımın galibiyet-mağlubiyet rekoru ("sezonu 21-11 yaptı",
  "7-31 yaptı") HİÇBİR ZAMAN yazılmaz — ne başlıkta, ne gövdede, ne
  "neden önemli" satırında.
- Bir oyuncunun YOKLUĞU / kadro dışı olması HİÇBİR ZAMAN yazılmaz
  ("X'siz sahaya çıkan", "X olmadan oynayan") — kabul edilen üç içerik
  türünden hiçbirine girmiyor. Bu olgu zaten sana verilmiyor.
- Bir galibiyet serisi ancak SÜRPRİZSE anılır. Lig lideri ya da güçlü
  bir takımın serisi BEKLENEN, haber değil — "üst üste 4. galibiyetini
  alan lig lideri" YAZILMAZ.
- Galibiyet sayısı SADECE yuvarlak eşiklerde (10/20/30/40/50) ya da lig
  liderliğinde anılır — "23. galibiyetini aldı" gibi rastgele bir sayı
  YAZILMAZ.
- Çeyrek üstünlüğü SADECE maçı gerçekten belirlediyse (son çeyrekte,
  15+ sayılık) anılır — 1./2./3. çeyrekteki bir üstünlük sonrasında
  erimiş olabilir, "belirledi" denemez.
- "Üst üste"/"art arda"/"ardışık"/"arka arkaya" bir seriyi anlatmak
  için SADECE seri 4+ maçsa kullanılır. 3 maçlık ya da daha kısa bir
  seri (galibiyet ya da mağlubiyet) HİÇ BİR KELİMEYLE "art arda/ardışık"
  diye anılmaz. DİKKAT: "ikinci galibiyetini aldı" gibi bir kaçış yolu da
  YASAK — "N. galibiyetini alan" ifadesindeki N, takımın GERÇEK sezon
  galibiyet toplamı olmak ZORUNDA (gerçek üretim bug'ı: Washington
  9-24'ken "ikinci galibiyetini alan Wizards" yazılmıştı — 2 maçlık
  seriyi sezon toplamı gibi göstermiş). Kısa bir seriyi (2 maç)
  anlatmak istiyorsan sadece sonucu düz söyle, sıra numarası verme.
  SÖZ DİZİMİ: "üst üste"/"art arda" HER ZAMAN sıra sayısından ÖNCE
  gelir — "üst üste 5. galibiyetini aldı" DOĞRU, "5. galibiyetini art
  arda aldı" YANLIŞ sıfat sıralaması.
  BİR GECEDE "üst üste"/"art arda"/"ardışık"/"arka arkaya" kalıbı EN
  FAZLA BİR KEZ kullanılır — hangi takım/yön (galibiyet ya da
  mağlubiyet) olursa olsun, gece genelinde bu kalıp ikinci kez
  görünüyorsa YAZMA, düz sonuçla bitir.
- "N sayıyla/asistle/ribaundla oynadı" YASAK (fiil yavan) → "attığı N
  sayıyla öne çıktı" gibi bir kullanım tercih et.
- "final oynadı" YASAK (final = şampiyonluk maçı, maç sonunu böyle
  anlatma) → "çekişmeli bitti", "son ana kadar sürdü" gibi bir ifade
  kullan.
- Gazete manşeti klişesi YASAK: "güldürdü", "gülümsetti", "sevindirdi",
  "üç puanı hanesine yazdırdı", "gol oldu" (basketbolda gol yok),
  "zafere taşıdı", "mutlu etti" — Türk spor gazeteciliğinin yerleşik
  kalıpları, OVERNIGHT'ın sesine yakışmıyor. Onun yerine oyuncu-taşıma
  fiilleri kullan: "sırtladı", "taşıdı", "sürükledi", "tek başına
  bitirdi", "omuzladı".
"""


# ---------------------------------------------------------------------------
# Maç başına kompakt gerçek paketi (prompt token bütçesi için)
# ---------------------------------------------------------------------------

# "gec"/"ikinci" katmanı grup çağrısında YOĞUN türler (an, oyuncu_ceyrek)
# dışlanıyor — tek cümlelik/kısa metin için gerek yok, token israfı.
GRUP_A_ONEMLI_TURLER = {
    "skor", "ceyrek", "derece", "seri", "kadro_disi", "kilometre", "fark_serisi",
}


# ---------------------------------------------------------------------------
# Grup B girdi filtresi — maliyetin asıl kaynağı
# ---------------------------------------------------------------------------
# Ölçüm (2026-01-28, HOU-SAS): Grup B promptu 21.535 girdi token'ı
# gönderiyordu ve bunun 14.228'i "Maç verisi" bloğuydu — maçın TÜM 103
# gerçek kaydı, filtresiz. Dökümü:
#   oyuncu_stat    24 kalem  %30  (sahaya çıkan HER oyuncu, iki takım)
#   oyuncu_ceyrek  46 kalem  %28  (oyuncu × çeyrek sayı kırılımı)
#   an             22 kalem  %26  (play-by-play'den her "an")
#   kalan 9 tür     9 kalem  %16
# Model bunların çoğunu kullanamaz: 4 cümlelik bir gövde en fazla 2-3
# oyuncu anar, çeyrek kırılımını TAKIM düzeyinde kullanır (`ceyrek`
# kaydı zaten var), ve "an"lardan sadece kararı vereni.
#
# DİKKAT — bu filtre SADECE modele GÖNDERİLENİ kısar. Doğrulayıcı
# (dogrula.py) her zaman TAM `gercekler` listesiyle çalışır, o yüzden
# izlenebilirlik testleri (T1/T2) zayıflamıyor: model daha az şey
# görüyor, ama yazdığı her şey yine tam listeye karşı denetleniyor.
GRUP_B_OYUNCU_SAYISI = 8   # en çok sayı atan 8 oyuncu (iki takım toplamı)
GRUP_B_AN_SAYISI = 6
# Bir "an"ın anılmaya değmesi için maçın O ANDA yakın olması gerekiyor.
# Fark bu eşiğin üstündeyken atılan basket sonucu etkilemez.
AN_YAKIN_FARK = 5
# ...ve geç olması gerekiyor: son periyot ya da uzatma.
AN_SON_PERIYOT = 4
# Tamamı gönderilen türler: hepsi küçük ve doğrudan anlatıya giriyor.
GRUP_B_TAM_TURLER = {
    "skor", "ceyrek", "derece", "fark_serisi", "takim_stat", "kilometre",
    "surpriz", "geri_donus", "uzatma", "seri", "gece_ozeti",
}


def grup_b_gercekleri(gercekler, en_iyi_performans=None):
    """Grup B'ye gidecek gerçek alt kümesi (bkz. yukarıdaki döküm).

    `oyuncu_ceyrek` HİÇ gönderilmiyor — takım düzeyi çeyrek akışı zaten
    `ceyrek` kaydında var ve gövde oyuncu-çeyrek kırılımını kullanmıyor.
    `en_iyi_performans` oyuncusu, sayısı düşük olsa bile HER ZAMAN
    listeye giriyor: T14 onun anılmasını şart koşuyor, göndermezsek
    model anamaz ve her seferinde reddedilir."""
    secili, oyuncular, anlar = [], [], []
    for f in gercekler:
        t = f["tur"]
        if t == "oyuncu_ceyrek":
            continue
        if t == "oyuncu_stat":
            oyuncular.append(f)
        elif t == "an":
            anlar.append(f)
        elif t in GRUP_B_TAM_TURLER:
            secili.append(f)
    anlar = _onemli_anlar(anlar)
    oyuncular.sort(key=lambda f: -f["veri"].get("sayi", 0))
    tutulan = oyuncular[:GRUP_B_OYUNCU_SAYISI]
    if en_iyi_performans and not any(f["veri"]["oyuncu"] == en_iyi_performans for f in tutulan):
        eksik = next((f for f in oyuncular if f["veri"]["oyuncu"] == en_iyi_performans), None)
        if eksik:
            tutulan.append(eksik)
    return secili + tutulan + anlar[:GRUP_B_AN_SAYISI]


def _onemli_anlar(anlar):
    """Sonucu ETKİLEYEN anlar — en geç olanlar değil.

    Kullanıcı bildirimi (gerçek üretim bug'ı): Spurs-Rockets özetinde
    Capela'nın smacı anıldı ve cümle "skoru etkilemese de" diyerek kendi
    kendini çürüttü. Sebebi buradaydı: `an` kayıtları önem sırasına göre
    değil, EN GEÇ olana göre seçiliyordu. Maç 12 sayı farkla biterken son
    saniyede atılan bir basket "en geç" olduğu için listenin başına
    geçiyordu.

    Ölçüt iki koşullu: maç o anda YAKIN olmalı (|fark| <= 5) VE an geç
    olmalı (son periyot ya da uzatma). Lider değişimi kendi başına
    sonucu etkiler — o kayıtlarda fark zaten sıfıra yakın, ama şartı
    açıkça yazmak niyeti belgeliyor.

    `disiplin` (teknik faul vb.) hiç girmiyor: sayı olayı değil,
    "maçı belirleyen an" anlatısına ait değil.
    """
    uygun = []
    for f in anlar:
        v = f["veri"]
        alt = v.get("tur_alt")
        if alt == "disiplin":
            continue
        periyot = v.get("periyot", 0)
        if periyot < AN_SON_PERIYOT:
            continue
        if alt == "lider_degisimi":
            uygun.append(f)
            continue
        fark = v.get("fark")
        if fark is not None and abs(fark) <= AN_YAKIN_FARK:
            uygun.append(f)
    # Geç olan önce — eşit önemdeyse maçın sonuna yakın olan daha anlamlı.
    uygun.sort(key=lambda f: (-f["veri"].get("periyot", 0), f["veri"].get("saat", "")))
    return uygun


def kompakt_gercekler(gercekler, sadece_turler=None):
    if sadece_turler:
        secili = [g for g in gercekler if g["tur"] in sadece_turler]
        # en skorer + en yüksek GmSc'li oyuncu_stat'ları da ekle (isim
        # geçebilsin diye) — hepsini değil, en fazla 6 tanesini.
        oyuncular = sorted(
            (g for g in gercekler if g["tur"] == "oyuncu_stat"),
            key=lambda g: g["veri"]["sayi"],
            reverse=True,
        )[:6]
        secili += oyuncular
    else:
        secili = gercekler
    # Kullanıcı kararı (mimari birleştirme turu): "kadro_disi" gerçekleri
    # LLM'e HİÇ GÖSTERİLMEZ. Bir oyuncunun yokluğu, kabul edilen üç
    # içerik türünden (Sonuç / Maçı belirleyen an / En iyi performans)
    # hiçbirine girmiyor — model bu olguyu görürse kullanıyor
    # ("Nembhard'sız sahaya çıkan Indiana..." sızıntısı tam olarak
    # buradan geldi; şablon tarafı kapalıydı, LLM tarafı açıktı).
    # Gerçek `gercek/{tarih}.json`'da KALIYOR (veri katmanı eksilmiyor),
    # sadece metin üretimine girmiyor.
    return [
        {"id": g["id"], "tur": g["tur"], "veri": g["veri"]}
        for g in secili
        if g["tur"] != "kadro_disi"
    ]


# ---------------------------------------------------------------------------
# LLM çağrısı
# ---------------------------------------------------------------------------


# Bir `yaz()` çalıştırması boyunca biriken token kullanımı — rapor için.
# Sistem promptu HER ÇAĞRIDA birebir aynı (dil kılavuzunun Bölüm 1'i, gece
# içinde hiç değişmiyor) — bu yüzden önbelleklemeye uygun: aşağıdaki
# cache_control ile işaretlenip Grup A + Grup B + bütçe kısaltma
# çağrılarının hepsinde tekrar tekrar ödenmek yerine bir kez yazılıp
# ucuza okunuyor.
KULLANIM_TAKIBI = []


def _yaniti_ayikla(metin):
    """Ham model metnini (kod bloğu işaretleri / önsöz olası) JSON'a
    çevirir. Hem senkron (`llm_cagir`) hem batch (`_batch_calistir`)
    yolunda aynı ayıklama mantığı kullanılsın diye ortak fonksiyona
    çıkarıldı."""
    metin = metin.strip()
    metin = re.sub(r"^```(json)?|```$", "", metin, flags=re.MULTILINE).strip()
    try:
        return json.loads(metin)
    except json.JSONDecodeError:
        # Model bazen JSON'dan ÖNCE düz metin bir önsöz yazıyor (aynı
        # cümleyi önce nesir, sonra JSON olarak tekrar ediyor) — kod
        # bloğu işareti yoksa yukarıdaki temizlik hiçbir şey yapmıyor
        # ve json.loads baştaki düz metne takılıyor. İlk "{" ile son
        # "}" arasını almak, önsözü atlayıp gerçek JSON nesnesini
        # yakalıyor (gerçek üretim bug'ı — 4 maçta art arda aynı
        # şekilde başarısız oldu, rastgele bir ağ hatası değildi).
        ilk = metin.find("{")
        son = metin.rfind("}")
        if ilk == -1 or son == -1 or son < ilk:
            raise
        return json.loads(metin[ilk : son + 1])


def llm_cagir(model, sistem, kullanici_mesaji, max_tokens=2000, output_config=None, effort=None):
    """Gerçek Anthropic API çağrısı (senkron — messages.create). Ret
    oranı düşük tekli üretimler (Grup A tek maç onarımı, gec_tier bütçe
    kısaltması, gözden geçirme) için kullanılır. Gece geneli toplu
    üretim için bkz. `yaz_batch` (Message Batches API, %50 indirimli).

    `effort` verilmezse ("low"|"medium"|"high"|"xhigh"|"max") adaptive
    thinking varsayılan davranışıyla çalışır. Kullanıcı kararı: Grup
    B'de (Mutlaka bil) 60-70 kelimelik bir metin için adaptive thinking
    7-11 bin ÇIKTI token'ı harcıyordu — gerçek üretim maliyetinin asıl
    kaynağı buydu, görünen metin değil. DİKKAT (gerçek üretim bug'ı):
    Sonnet 5'te `thinking.type.enabled` (sabit budget_tokens) DESTEKLENMİYOR
    — API "thinking.type.adaptive ve output_config.effort kullan" diyor.
    Thinking her zaman adaptive kalıyor, sadece effort seviyesi onun ne
    kadar harcayacağını kısıtlıyor."""
    # Bütçe kapısı EN BAŞTA — anthropic'i içe aktarmadan ve istemciyi
    # kurmadan önce. Sırası önemli: istemci kurulumu ANTHROPIC_API_KEY
    # yoksa kendi hatasını fırlatıyor ve bütçe kapısının hiç çalışmadığı
    # bir ortamda (ör. anahtarsız CI test adımı) o hata bütçe hatasını
    # maskeliyordu. Tavan zaten "hiç çağrı yapma" kararı; çağrı için
    # gereken hiçbir şeyi hazırlamaya gerek yok.
    tavan = _butce_tavani()
    if tavan is not None:
        BUTCE_DURUMU["tavan"] = tavan
        harcanan = simdiye_kadarki_maliyet()
        if harcanan + TAHMINI_CAGRI_USD > tavan:
            BUTCE_DURUMU["asildi"] = True
            raise ButceAsildi(
                f"Günlük tavan ${tavan:.2f}; şu ana kadar ${harcanan:.4f} harcandı, "
                f"bir çağrılık pay (${TAHMINI_CAGRI_USD:.2f}) sığmıyor. Şablona düşülüyor."
            )

    import anthropic

    istemci = anthropic.Anthropic()  # ANTHROPIC_API_KEY ortam değişkeninden okur
    ekstra = {}
    if output_config or effort:
        ekstra["output_config"] = {**(output_config or {}), **({"effort": effort} if effort else {})}
    # `kullanici_mesaji` bir liste ise: SON parça hariç hepsi önbelleğe
    # alınır. Önbellek önek üzerinden çalıştığı için değişmeyen kısım
    # (maç verisi) önde, denemeden denemeye değişen kısım (talimatlar +
    # önceki hata listesi) sonda olmalı — bkz. grup_b_prompt_kur.
    if isinstance(kullanici_mesaji, (list, tuple)):
        parcalar = [p for p in kullanici_mesaji if p]
        icerik = []
        for i, parca in enumerate(parcalar):
            blok = {"type": "text", "text": parca}
            if i < len(parcalar) - 1:
                blok["cache_control"] = {"type": "ephemeral"}
            icerik.append(blok)
    else:
        icerik = kullanici_mesaji

    yanit = istemci.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": sistem,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": icerik}],
        **ekstra,
    )

    # Çıktı token'ının ne kadarı DÜŞÜNME, ne kadarı görünen metin?
    # `usage` bunu ayırmıyor; blokların karakter uzunluğundan oranlıyoruz.
    # Tam token sayısı değil ama israfın büyüklüğünü göstermeye yeter —
    # ve asıl sorulan bu: 70 kelimelik bir paragraf için kaç bin token
    # düşünmeye gidiyor.
    _dusunme_krk = sum(len(getattr(b, "thinking", "") or "") for b in yanit.content if b.type == "thinking")
    _metin_krk = sum(len(getattr(b, "text", "") or "") for b in yanit.content if b.type == "text")
    _toplam_krk = _dusunme_krk + _metin_krk
    _cikti = yanit.usage.output_tokens
    KULLANIM_TAKIBI.append(
        {
            "model": model,
            "girdi": yanit.usage.input_tokens,
            "cikti": _cikti,
            "cache_yazma": getattr(yanit.usage, "cache_creation_input_tokens", 0) or 0,
            "cache_okuma": getattr(yanit.usage, "cache_read_input_tokens", 0) or 0,
            "dusunme_krk": _dusunme_krk,
            "metin_krk": _metin_krk,
            "dusunme_token_tahmini": round(_cikti * _dusunme_krk / _toplam_krk) if _toplam_krk else 0,
            "effort": effort,
        }
    )

    # Claude Sonnet 5'te thinking varsayılan olarak açık (thinking parametresi
    # verilmezse adaptive çalışıyor) — bu yüzden content[0] her zaman metin
    # bloğu olmayabilir, önce bir ThinkingBlock gelebilir. İlk "text" tipli
    # bloğu bulmak gerekiyor, körlemesine content[0] almak yerine.
    metin_bloklari = [b for b in yanit.content if b.type == "text"]
    if not metin_bloklari:
        raise RuntimeError(
            f"Yanıtta hiç metin bloğu yok (stop_reason={yanit.stop_reason}, "
            f"muhtemelen max_tokens thinking'e gitti, max_tokens'ı artır)"
        )
    return _yaniti_ayikla(metin_bloklari[0].text)


def _maliyet_hesapla(kayitlar):
    """Kayıt listesinin maliyeti — LİSTEYİ SIFIRLAMAZ.

    `kullanim_raporu` sıfırlıyor (gece sonu raporu için doğru), ama
    bütçe tavanı üretimin ORTASINDA okumak zorunda; sıfırlayan bir
    fonksiyonla tavan kontrolü sayacı silerdi."""
    if not kayitlar:
        return {"toplam_maliyet_usd": 0.0, "cagri_sayisi": 0, "detay": []}

    toplam_maliyet = 0.0
    toplam_girdi = toplam_cikti = toplam_cache_yazma = toplam_cache_okuma = 0

    for kayit in kayitlar:
        fiyat = FIYATLANDIRMA.get(kayit["model"])
        if fiyat is None:
            continue
        girdi_fiyat = fiyat["girdi"] / 1_000_000
        cikti_fiyat = fiyat["cikti"] / 1_000_000
        indirim = BATCH_INDIRIM if kayit.get("batch") else 1.0
        maliyet = indirim * (
            kayit["girdi"] * girdi_fiyat
            + kayit["cikti"] * cikti_fiyat
            + kayit["cache_yazma"] * girdi_fiyat * CACHE_YAZMA_CARPANI
            + kayit["cache_okuma"] * girdi_fiyat * CACHE_OKUMA_CARPANI
        )
        toplam_maliyet += maliyet
        toplam_girdi += kayit["girdi"]
        toplam_cikti += kayit["cikti"]
        toplam_cache_yazma += kayit["cache_yazma"]
        toplam_cache_okuma += kayit["cache_okuma"]

    return {
        "cagri_sayisi": len(kayitlar),
        "girdi_token": toplam_girdi,
        "cikti_token": toplam_cikti,
        "cache_yazma_token": toplam_cache_yazma,
        "cache_okuma_token": toplam_cache_okuma,
        "toplam_maliyet_usd": round(toplam_maliyet, 4),
    }


def simdiye_kadarki_maliyet():
    """Bu çalıştırmada şu ana kadar harcanan (sayaç silinmeden)."""
    return _maliyet_hesapla(KULLANIM_TAKIBI)["toplam_maliyet_usd"]


def kullanim_raporu():
    """Bu çalıştırmada harcanan token ve tahmini maliyet — gece başına
    gerçek maliyeti görmek için. `KULLANIM_TAKIBI`'ni okuyup sıfırlar."""
    rapor = _maliyet_hesapla(KULLANIM_TAKIBI)
    rapor["butce_asildi"] = BUTCE_DURUMU["asildi"]
    KULLANIM_TAKIBI.clear()
    return rapor


# ---------------------------------------------------------------------------
# Şablon modu — LLM'siz, her zaman geçer
# ---------------------------------------------------------------------------


_IYUUO_CEVIRI_YAZ = str.maketrans({"İ": "i", "I": "ı"})


def _belirtme_eki(ad):
    """Belirtme hali eki (-ı/-i/-u/-ü, ünsüzle biten kelimede; sesli ile
    bitende 'y' tamponu) — ünlü uyumuna göre. Gerçek üretim bug'ı:
    sablon_uret_mutlaka'da 'Washington Wizards'yi' gibi yanlış ek
    hardcode edilmişti ('Wizards' ünsüzle bitiyor VE son ünlüsü 'a' —
    doğrusu 'Wizards'ı')."""
    son = ad.translate(_IYUUO_CEVIRI_YAZ).lower()
    son_harf = son[-1] if son else ""
    sesli = "aeıiuüoö"
    son_unlu = next((c for c in reversed(son) if c in sesli), None)
    ek_by_unlu = {"a": "ı", "ı": "ı", "e": "i", "i": "i", "o": "u", "u": "u", "ö": "ü", "ü": "ü"}
    ek = ek_by_unlu.get(son_unlu, "i")
    tampon = "y" if son_harf in sesli else ""
    return f"{tampon}{ek}"


def _iyelik_eki(ad):
    """İyelik/tamlayan eki (-ın/-in/-un/-ün) — ünlü uyumuna göre, sesli
    ile bitende 'n' tamponu (belirtme ekindeki 'y' tamponuyla KARIŞTIRMA,
    ayrı bir ek). Kullanıcı düzeltmesi: P kancasında bu ek hardcoded
    "'nin" idi — ünsüzle biten İngilizce soyadlarında ('Edwards'nin')
    yanlış çıkıyordu, doğrusu 'Edwards'ın'. Ek üretimi artık HER YERDE
    bu ortak fonksiyona bağlı, ikinci bir hardcode riski kalmasın diye."""
    son = ad.translate(_IYUUO_CEVIRI_YAZ).lower()
    son_harf = son[-1] if son else ""
    sesli = "aeıiuüoö"
    son_unlu = next((c for c in reversed(son) if c in sesli), None)
    ek_by_unlu = {"a": "ın", "ı": "ın", "e": "in", "i": "in", "o": "un", "u": "un", "ö": "ün", "ü": "ün"}
    ek = ek_by_unlu.get(son_unlu, "in")
    tampon = "n" if son_harf in sesli else ""
    return f"{tampon}{ek}"


def _takim_adi_koddan(kod, ham_mac):
    """Şablon modu doğrulamadan muaf olsa da kendi içinde kurallara
    uymalı — takım kodu değil tam ad (kullanıcı düzeltmesi: 'CHI evinde
    kazandı' gibi cümleler yayına çıkmıştı)."""
    if ham_mac is None:
        return kod
    bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    for taraf in ("homeTeam", "awayTeam"):
        if bt[taraf]["teamTricode"] == kod:
            return f"{bt[taraf]['teamCity']} {bt[taraf]['teamName']}"
    return kod


def _sablon_takim_adi(v, ham_mac):
    return _takim_adi_koddan(v["kazanan"], ham_mac)


# ---------------------------------------------------------------------------
# TEK CÜMLE KATMANINA KÖPRÜ (kullanıcı kararı — mimari birleştirme turu).
# Cümle kurma, eşikler ve yasak uygulaması artık TAMAMEN cumle.py'de.
# Buradaki fonksiyonlar sadece eski çağıranların imzasını koruyan ince
# sarmalayıcılar — hiçbiri kendi kuralını uygulamıyor, hepsi aynı
# katmandan geçiyor. "Kural bir yolda uygulanıp diğerinde unutuluyor"
# sorununun yapısal çözümü bu: uygulanacak kural artık burada YOK.
# ---------------------------------------------------------------------------


def _seviye_belirle(rozet, katman=None):
    if katman == "mutlaka":
        return "mutlaka"
    if rozet is not None and rozet < cumle.DUSUK_DEGER_ESIGI:
        return "gec"
    return "degerse"


def _mac_cumleleri_uret(gercekler, ham_mac, olgu, en_iyi_performans, kanca_harf, seviye):
    return cumle.govde(
        gercekler, ham_mac, olgu, en_iyi_performans, kanca_harf, seviye, _takim_adi_koddan
    )


def sablon_uret(gercekler, ham_mac=None, en_iyi_performans=None, ikinci_cumle=None, kanca_harf=None, olgu=None, rozet=None):
    """Grup A / "Bunları geç" metni. Artık sadece bir köprü: seviyeyi
    rozetten türetip cumle.govde'ye devrediyor. `ikinci_cumle` parametresi
    KULLANILMIYOR (imza geriye dönük uyumluluk için duruyor) — ikinci
    cümle bankası kaldırıldı, bütçe artık cumle katmanında."""
    return _mac_cumleleri_uret(
        gercekler, ham_mac, olgu, en_iyi_performans, kanca_harf, _seviye_belirle(rozet)
    )


# ---------------------------------------------------------------------------
# Mutlaka bil — ZENGİN mekanik şablon (LLM YOK). Grup B iki denemede de
# kurallara takılırsa artık `sablon_uret`in tek cümlelik ortak şablonuna
# DEĞİL, buraya düşer. Kullanıcı kararı: "Denver evinde kazandı" gecenin
# EN ÖNEMLİ maçı için kabul edilemez — Jokić'in 56/16/15'lik gecesi ya
# da Adebayo'nun 83 sayılık (kaynak verisi şüpheli olsa da) gecesi böyle
# yayınlanamaz. Dört cümle, olgu VARSA doldurulur, yoksa atlanır — kuru
# ama her zaman gerçek gerçeklerden, hiç uydurma yok.
# ---------------------------------------------------------------------------


def _baglam_cumlesi(baglam):
    """gercekler.TARIHSEL_BAGLAM / sezon_sikligi_baglam_uret'teki yapısal
    veriden tek cümle kurar (mekanik, LLM yok) — kullanıcı düzeltmesi:
    baglam artık bir cümle değil sayı taşıyor, cümleyi burada KOD kuruyor.
    İki "olcek" var: nba_tarihi (tüm NBA tarihi, statik/doğrulanmış) ve
    oyuncu_sezonu (bu oyuncunun bu sezonu, ham/{tarih}.json'daki
    oyuncu_ortalama'dan dinamik hesaplanmış — bkz. gercekler.py)."""
    if not baglam:
        return None
    if baglam.get("olcek") == "oyuncu_sezonu":
        kac = baglam["bu_sezon_once_kac_kez"]
        if kac == 0:
            return f"Bu, bu sezon {baglam['tur']} eşiğine ulaştığı ilk gece oldu."
        return f"Bu sezon bu eşiğe ({baglam['tur']}) ondan önce {kac} kez ulaşmıştı."
    if baglam["ondan_once_kez_sayisi"] == 0:
        return f"Bu, NBA tarihinde {baglam['tur']} eşiğinin geçildiği ilk an oldu."
    # Kullanıcı düzeltmesi: "sadece N oyuncuda görüldü" (edilgen, mesafeli)
    # yerine oyuncuyu doğrudan listenin İÇİNE koyan bir sıra iddiası daha
    # doğal ve daha güçlü — "9. oyuncu oldu" gibi. DİKKAT: bu KESİN bir
    # all-time sıra iddiası değil (T18'in yasakladığı tür) — bu eşiği
    # geçen oyuncuların KAÇINCISI olduğu, doğrulanmış oyuncu SAYISINDAN
    # (ondan_once_oyuncu_sayisi) türetilen basit bir aritmetik, gerçek bir
    # kaynak (WebSearch ile doğrulanmış sayı) taşıyor.
    return f"Bu eşiği ({baglam['tur']}) geçen {baglam['ondan_once_oyuncu_sayisi'] + 1}. oyuncu oldu."


def sablon_uret_mutlaka(gercekler, ham_mac, olgu, en_iyi_performans=None, kisa=False):
    """Mutlaka bil'in mekanik şablonu. Artık tamamen cumle.mutlaka_metni'ye
    köprü — başlık/neden-önemli/gövde ORADA tek yerde, ortak bir
    "kullanılan olgu" kümesiyle kuruluyor, böylece aynı olgu iki alanda
    birden geçemiyor."""
    return cumle.mutlaka_metni(
        gercekler, ham_mac, olgu, en_iyi_performans, _takim_adi_koddan, kisa=kisa
    )


def _neden_onemli_uret(olgu, kazanan_adi, gercekler=None, ham_mac=None):
    """Mutlaka bil'in tek satırlık gerekçesi — cumle.neden_onemli'ye
    köprü. Derece son-çare cümlesi ("sezonu 21-11 yaptı") ve ilk-3
    dışı sıralama iddiası ORADA kapalı, burada tekrar kural yok."""
    if gercekler is None:
        return ""
    mac = cumle.mac_baglami(gercekler, ham_mac, olgu, _takim_adi_koddan)
    return cumle.neden_onemli(mac, olgu or {}) or ""


# ---------------------------------------------------------------------------
# Brief ("30 saniyede gece") — ZENGİN mekanik şablon (LLM YOK). Kullanıcı
# kararı: eski şablon `sablon_uret(...).split(".")[0]` üzerinden HEP
# "X evinde Y-Z kazandı" üretiyordu — skoru asla atlamıyordu, T19'un
# "brief'te skor gereksiz" kuralını sistematik ihlal ediyordu (11
# gecelik toplu üretimde 8 kez). Burada skor HİÇ yazılmıyor — gerçek
# kayıtlardan en güçlü TEK olgu seçilip tek cümle kuruluyor.
#
# İkinci kullanıcı düzeltmesi (25 Aralık gecesi): eski öncelik sırası
# ("çeyrekte kurduğu üstünlükle kazandı" neredeyse HER maçta uygulanabilir
# olduğu için) beş satırın üçünü aynı kalıba düşürüyordu — kod tarafından
# üretildiği için gece çapında dedup da yoktu. İki düzeltme: (1) tüm
# adaylar `_brief_adaylari` ile (kind, metin) listesine çıkarıldı, kesin
# öncelik sırasıyla (kullanıcı sırası): sürpriz sonuç > kilometre taşı >
# geri dönüş > son saniye basketi > seri (4+) > büyük fark > sıralama >
# çeyrek üstünlüğü (SON ÇARE). (2) `gece_brief_ata` gece çapında aynı
# kind'ı iki kez kullanmıyor (kalıp_secici'deki niteleyici dedup'ıyla aynı
# desen). Hiçbir olgu yoksa uydurma bir "üstünlük" cümlesi kurulmaz,
# düz "{kazanan} {skor} kazandı" ile biter.
# ---------------------------------------------------------------------------


def sablon_uret_brief(gid, gercekler, ham_mac, olgu, en_iyi_performans=None, haric_kindler=None):
    """"30 saniyede gece" satırı — cumle.brief_satiri'ye köprü. Gerçek
    bir olgu yoksa None döner: brief sabit 5 satır değil, dürüst içerik
    kadar satır (kullanıcı kararı). Eski `_brief_adaylari` bankası
    kaldırıldı — aday listesi artık cumle katmanında, tek kopya."""
    mac = cumle.mac_baglami(gercekler, ham_mac, olgu, _takim_adi_koddan)
    en_iyi_oyuncu = None
    if en_iyi_performans:
        en_iyi_oyuncu = next(
            (g["veri"] for g in gercekler if g["tur"] == "oyuncu_stat" and g["veri"]["oyuncu"] == en_iyi_performans),
            None,
        )
    kind, metin = cumle.brief_satiri(mac, olgu or {}, en_iyi_oyuncu, en_iyi_performans, haric_kindler)
    if metin is None:
        return None
    return {"metin": metin, "hedef_mac": gid, "muzip": False, "kind": kind}


def gece_brief_ata(kalip_plani, rozet_by_gid, brief_hedefleri, ham, en_iyi_performans_by_gid, gercek_gece):
    """Brief satırlarını gece çapında dedup ederek atar — rozeti yüksek
    maç önce hak eder. Aynı KIND iki maçta kullanılamaz. Gerçek bir
    olguya dayanamayan maç sözlükte HİÇ yer almaz (brief sabit 5 satır
    değil, dürüst içerik kadar satır). Kind bilgisi artık doğrudan
    cumle katmanından geliyor — eski sürüm aday bankasını İKİNCİ kez
    kurup metin eşleştirerek kind'ı geri buluyordu, o kopya kalktı."""
    kullanilan_kind = set()
    sonuc = {}
    for gid in sorted(brief_hedefleri, key=lambda g: -rozet_by_gid.get(g, 0)):
        obj = sablon_uret_brief(
            gid, gercek_gece["maclar"][gid], ham["maclar"][gid], kalip_plani[gid]["olgu_ham"],
            en_iyi_performans_by_gid.get(gid), haric_kindler=kullanilan_kind,
        )
        if obj is None:
            continue
        kullanilan_kind.add(obj.pop("kind"))
        sonuc[gid] = obj
    return sonuc


# ---------------------------------------------------------------------------
# Gece çapında muziplik bütçesi
# ---------------------------------------------------------------------------

MUZIP_BUTCESI_TOPLAM = 3
MUZIP_BUTCESI_GRUP_A = 2  # gecenin geri kalanı Grup B'ye (mutlaka maç) ayrılır


# ---------------------------------------------------------------------------
# Grup A — mutlaka dışı tüm maçlar + brief (tek çağrı, ucuz model)
# ---------------------------------------------------------------------------


def kalip_talimati_kur(kalip, ornekler_havuzu, alan_adi="gec_satiri", ekstra_cumle_izni=False, en_iyi_performans=None):
    """kalip: gece_kalip_plani()'nin bir maç için döndürdüğü sözlük.
    Kanca kategorisinin gerçek açılış cümleleri + o kategoriye ait 1-2
    örnek + o maç için dolabilen niteleyiciler + atanmış öne çıkma
    fiili — model artık "ne anlatayım" sorusunu çözmüyor, malzeme ona
    veriliyor."""
    harf = kalip["kanca_harf"]
    kanca_cumleleri = kanca_bankasi_metni(harf)
    varsayilan_h_kancasi = '  (H, doğrudan, kancasız: "[Kazanan], [yer] [Kaybeden]’i [skor] yendi.")'
    kanca_gosterim = kanca_cumleleri if kanca_cumleleri else varsayilan_h_kancasi

    ornekler = ornekler_havuzu.get(harf, [])[:2]
    ornek_satirlari = "\n".join(f'  "{m}"' for _, m in ornekler)
    ornek_metni = ornek_satirlari if ornekler else "  (bu kategori için örnek yok, iskelete sadık kal)"

    nitelik_satirlari = "\n".join("  - " + n for n in kalip["niteleyiciler"])
    nitelik_gosterim = nitelik_satirlari if kalip["niteleyiciler"] else "  (hiçbiri dolmadı — sonuç/derece ile sade bitir)"

    kademe_talimati = (
        "TAM OLARAK 2 cümle (CÜMLE1 + CÜMLE2) kur. Fazlası YOK."
        if kalip["kademe"] != "fakir"
        else "TAM OLARAK 2 cümle kur (fazlası YOK) ama CÜMLE2 sade kalsın (olay iddiası yok, sadece derece/seri gibi basit bir niteleyici)."
    )

    # CÜMLE2 şablonu ("[KAZANAN]'da [OYUNCU]...") YAPISAL OLARAK kazanan
    # tarafa kilitli — ama bu maçın en yüksek GmSc'li performansı
    # kaybeden tarafta olabilir ve eşiği geçiyorsa mutlaka anılması
    # gerekiyor (bkz. dogrula.py T14). Gerçek üretim bug'ı: kalıp
    # kütüphanesi entegre edilince bu talimat kazara düşmüştü, model
    # kaybedenin 30+ sayılık performansını hiç anmadı. İSKELETİ
    # BOZMADAN çözüm: kaybeden tarafın ismi kazanandan SONRA, kısa bir
    # ek cümle olarak eklenebilir — bu istisna, yoksa değil.
    en_iyi_talimat = (
        f"\nBu maçın istatistiksel olarak en etkili performansı {en_iyi_performans}. Kazanan "
        f"tarafta ise CÜMLE2'yi onun üzerinden kur (toplam yine 2 cümle). KAYBEDEN "
        f"taraftaysa CÜMLE2'yi yine kazanana göre kur, ama kısa bir ÜÇÜNCÜ cümle "
        f"ekleyip {en_iyi_performans}'i de an — bu durumda toplam TAM OLARAK 3 "
        f"cümle (2 değil 3, ama ASLA 4 değil). İskeletin tek istisnası budur, "
        f"kaybedeni hiç anmamak kabul edilmez.\n"
        if en_iyi_performans else ""
    )

    return f"""CÜMLE 1 için kanca kategorisi: {harf} — gerekçe: {kalip['kanca_gerekce']}
Bu kategorinin açılış kalıpları (birebir kopyalama, UYARLA):
{kanca_gosterim}

CÜMLE 2 için dolabilen niteleyiciler (SADECE bunlardan seç, uydurma):
{nitelik_gosterim}

Öne çıkma fiili (bu maç için atanmış, başka fiil kullanma): "{kalip['one_cikma_fiili']}"

Kademe: {kalip['kademe']} — {kademe_talimati}
{en_iyi_talimat}
Bu iki cümleyi birebir bu örnek gibi kur (kalıbı taklit et, İÇERİĞİ değil):
{ornek_metni}
"""


def grup_a_prompt_kur_tekli(gid, bilgi, ham, kalan_muzip_kotasi, kalip, ornekler_havuzu):
    ham_mac = ham["maclar"][gid]
    bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    paket = {
        "ev": f"{bt['homeTeam']['teamCity']} {bt['homeTeam']['teamName']}",
        "dep": f"{bt['awayTeam']['teamCity']} {bt['awayTeam']['teamName']}",
        "rozet": bilgi["rozet"],
        "gercekler": kompakt_gercekler(bilgi["gercekler"], GRUP_A_ONEMLI_TURLER),
    }
    kalip_talimati = kalip_talimati_kur(kalip, ornekler_havuzu, en_iyi_performans=bilgi.get("en_iyi_performans"))

    talimat = f"""Bu, gecenin "Bunları geç" katmanındaki bir maç. Tek
alan yaz: `gec_satiri` — sistem promptundaki EVRENSEL İSKELETE göre
(CÜMLE1 + CÜMLE2), aşağıdaki kanca/niteleyici/fiil malzemesiyle.

{kalip_talimati}
Takım adını cümledeki İLK anışta tam şehir/takım adıyla yaz, ikinci
anıştan itibaren takma ad kullanabilirsin — üç harfli kod (MIL gibi)
ASLA kullanma.

`muzip`: ölçülü muziplik kullandıysan true. Bu maç için en fazla
{kalan_muzip_kotasi} pay var (gecenin geri kalanı zaten kullanılmış
olabilir).

JSON şeması:
{{"gec_satiri": "...", "muzip": bool}}

Maç verisi:
{json.dumps(paket, ensure_ascii=False)}
"""
    return talimat


GRUP_A_MAX_TOKENS = 16000  # kalıp kütüphanesi entegrasyonuyla prompt
# büyüdü (kanca+niteleyici+örnek malzemesi) — 4000, 6000 VE 10000 aynı
# maçta (GSW-OKC, D kancası) ısrarla thinking bütçesini tüketti, hiç
# metin bırakmadı. grup_b_uret'in tavanından (12000) da yüksek —
# GSW-OKC özellikle direngen çıktı, cömert davranmak gerekiyor.


def grup_a_uret_tekli(gid, bilgi, ham, kalan_muzip_kotasi, kalip, ornekler_havuzu):
    prompt = grup_a_prompt_kur_tekli(gid, bilgi, ham, kalan_muzip_kotasi, kalip, ornekler_havuzu)
    return llm_cagir(GUCLU_MODEL, sistem_prompt(), prompt, max_tokens=GRUP_A_MAX_TOKENS)


# ---------------------------------------------------------------------------
# 30 saniyede gece — 5 kısa satır, ayrı ve küçük bir tek çağrı
# ---------------------------------------------------------------------------


def brief_prompt_kur(brief_hedefleri, maclar_kaynagi, ham, kalip_plani):
    paket = {}
    for gid in brief_hedefleri:
        bilgi = maclar_kaynagi[gid]
        ham_mac = ham["maclar"][gid]
        bt = ham_mac["box_traditional"]["boxScoreTraditional"]
        kalip = kalip_plani[gid]
        paket[gid] = {
            "ev": f"{bt['homeTeam']['teamCity']} {bt['homeTeam']['teamName']}",
            "dep": f"{bt['awayTeam']['teamCity']} {bt['awayTeam']['teamName']}",
            "gercekler": kompakt_gercekler(bilgi["gercekler"], GRUP_A_ONEMLI_TURLER),
            # Bu maçı benzersiz kılan malzeme — brief satırı bunu
            # kullanmalı, salt "X, Y'yi yendi" değil (kullanıcı
            # düzeltmesi: "işi özetlemek değil, OKUTMAK").
            "ilginc_detay_gerekcesi": kalip["kanca_gerekce"],
            "niteleyiciler": kalip["niteleyiciler"][:3],
        }
    n = len(brief_hedefleri)
    talimat = f"""TAM OLARAK {n} tane "30 saniyede gece" satırı yaz
(`brief`) — ne fazla ne eksik, aşağıda verilen {n} maçın HER BİRİ için
bir satır. Her satır en fazla 12 kelime, aşağıdaki maçlardan seçerek
(`hedef_mac` alanına o maçın id'sini yaz): {brief_hedefleri}

Her satır bir MANŞETTİR, özet değil. Kural:

1. SKORU YAZMA. Skor zaten hemen aşağıdaki kartta duruyor, brief'te
   tekrarı gürültü. TEK istisna: skorun kendisi haberse (mesela 20+
   sayılık bir fark) — o zaman fark bir sayı olarak geçebilir ama yine
   "kazandı" fiiliyle skor çifti (113-108 gibi) değil.
2. TEK fikir, TEK cümle, 10-12 kelime. "ilginc_detay_gerekcesi" ya da
   "niteleyiciler"den seç, o maçı benzersiz kılan TEK şeyi anlat.
3. Satırların HER BİRİ FARKLI şekilde kurulmalı — kimi oyuncu adıyla
   açsın, kimi olayla, kimi takımla, kimi bir çelişki/zıtlıkla. Aynı
   cümle iskeleti ("[Takım], [Takım2]'yı [nasıl] yendi") İKİ satırda
   kullanılamaz — kanca kuralının brief'e uygulanmış hâli.
4. Sonuçsuz, ne olduğu belirsiz bir ara-maç detayı YASAK ("farkı
   16'ya çıkardı" gibi — bu neyin haberi olduğunu söylemiyor).

Hedeflenen tip (yapı çeşitliliğine dikkat et, birebir kopyalama):
"Giannis bitime 4.7 saniye kala smaçla bitirdi, Milwaukee 16 sayıdan
döndü." / "Cleveland son çeyreği 25-11 aldı, Denver farkı koruyamadı."
/ "Trae Young yoktu, Jalen Johnson triple-double yaptı." / "Avdija 34
sayı ve 11 asistle Portland'ı sırtladı." / "Play-in hattında yan yana
duran iki takımın maçını Chicago aldı."

Takım adını HER ZAMAN tam şehir/takım adıyla yaz — üç harfli kod
(MIL gibi) ASLA kullanma, sana sadece referans için verildi.

JSON şeması:
{{"brief": [{{"metin": "...", "hedef_mac": "<mac_id>", "muzip": bool}}, ...]}}

Maç verileri:
{json.dumps(paket, ensure_ascii=False)}
"""
    return talimat


def brief_uret(brief_hedefleri, maclar_kaynagi, ham, kalip_plani):
    prompt = brief_prompt_kur(brief_hedefleri, maclar_kaynagi, ham, kalip_plani)
    return llm_cagir(GUCLU_MODEL, sistem_prompt(), prompt, max_tokens=8000)


# ---------------------------------------------------------------------------
# Grup B — tek "mutlaka" maçı (tek çağrı, güçlü model)
# ---------------------------------------------------------------------------


def mutlaka_talimati_kur(kalip, ornekler_havuzu, en_iyi_performans=None):
    """"Mutlaka bil" KENDİ iskeletini kullanır — "Bunları geç"in iki
    cümlelik CÜMLE1+CÜMLE2 kalıbı DEĞİL. Kullanıcı düzeltmesi: gecenin
    en önemli maçı bu katı kalıba sıkıştırılınca gecenin en değerli
    ayrıntıları (son saniye basketi, büyük geri dönüş) metinden
    düşüyordu. Burada kanca+niteleyici hâlâ MALZEME ama akışı model
    dört-beş cümlelik bir anlatıya kendisi kurar."""
    harf = kalip["kanca_harf"]
    kanca_cumleleri = kanca_bankasi_metni(harf)
    kanca_gosterim = kanca_cumleleri if kanca_cumleleri else "  (kancasız, doğrudan sonuçla başla)"

    nitelik_satirlari = "\n".join("  - " + n for n in kalip["niteleyiciler"])
    nitelik_gosterim = nitelik_satirlari if kalip["niteleyiciler"] else "  (hiçbiri dolmadı)"

    en_iyi_talimat = (
        f"\nBu maçın istatistiksel olarak en etkili performansı {en_iyi_performans} — "
        f"gövdede mutlaka an, istatistiğiyle birlikte.\n"
        if en_iyi_performans else ""
    )

    return f"""Kanca kategorisi: {harf} — gerekçe: {kalip['kanca_gerekce']}
Bu kategorinin açılış kalıpları (ilham için, birebir kopyalama):
{kanca_gosterim}

Dolabilen niteleyiciler (gövdede kullanılabilir, uydurma):
{nitelik_gosterim}
{en_iyi_talimat}
Gerçeklerde bir "an" kaydı (`tur: "an"`) varsa ve maçı bitiren/kararı
belirleyen bir basketse (özellikle son periyotun son 24 saniyesinde),
bunu MUTLAKA gövdeye taşı — kim attı, ne zaman, nasıl (smaç/üçlük/
layup). Bu, "Mutlaka bil"in var olma sebebi: kutu skorda görünmeyen
sahne.
"""


def grup_b_prompt_kur(gid, gercekler, ham_mac, kalan_muzip_kotasi, kalip, ornekler_havuzu, en_iyi_performans=None, onceki_hatalar=None, kisa=False, ust_uste_kullanildi_mi=False):
    mutlaka_talimati = mutlaka_talimati_kur(kalip, ornekler_havuzu, en_iyi_performans)
    ust_uste_uyarisi = (
        '\nDİKKAT: "üst üste"/"art arda"/"ardışık"/"arka arkaya" kalıbı bu gece BAŞKA BİR MAÇTA ZATEN '
        "kullanıldı — bu maçta KULLANMA, bir seri anlatacaksan sıra numarası vermeden düz anlat.\n"
        if ust_uste_kullanildi_mi else ""
    )
    onceki_hata_talimati = ""
    if onceki_hatalar:
        # Gerçek üretim bug'ı: Grup B'nin 5 denemeye çıkarılması (bkz.
        # kullanıcı kararı) tek başına yetmiyordu — model her denemede
        # KÖRLEMESİNE yeniden üretiyor, aynı hatayı tekrar tekrar
        # yapabiliyordu. Önceki reddedilme gerekçesi açıkça verilmezse
        # ekstra deneme hakkı boşa gidiyor.
        liste = "\n".join(f"- {h}" for h in onceki_hatalar)
        onceki_hata_talimati = f"""
ÖNCEKİ DENEMEN REDDEDİLDİ. Sebep(ler):
{liste}
Bu hataları AYNEN TEKRARLAMA — yukarıdaki her maddeyi düzelterek yeniden yaz.
"""
    # Kullanıcı kararı (Mutlaka bil 3 maça çıktı): rozeti 8.5+ olan EN
    # FAZLA 3 maç "Mutlaka bil"e girer, ama maliyeti kontrol etmek için
    # sadece EN YÜKSEK rozetli tam anlatı alır — 2. ve 3. maçlar KISA
    # anlatı (`ozet_kisa`, `ozet`den daha sıkı bir sınır).
    if kisa:
        govde_alani = "ozet_kisa"
        govde_talimati = """- `ozet_kisa`: TAM OLARAK 2-3 cümlelik KISA bir gövde, 30-45
  KELİME (ALT SINIR DA ZORUNLU — 30 kelimenin altı reddedilir). Bu maç "Mutlaka bil"e girdi ama gecenin EN önemlisi değil —
  tam anlatı değil, maçı belirleyen 1-2 olguyu (nasıl bitti, kim öne
  çıktı) kısaca anlat. Dört-bilgili tam gövde YAZMA, bu alan onun
  KISALTILMIŞI değil, baştan KISA bir tür."""
    else:
        govde_alani = "ozet"
        govde_talimati = """- `ozet`: TAM OLARAK 4 CÜMLE, 55-75 KELİME. Hem alt hem üst sınır
  ZORUNLU — 4 cümleden az/çok ya da 55 kelimenin altı REDDEDİLİR. Aynı
  bölümdeki metinler aynı ağırlıkta olmalı (kullanıcı kuralı): kısa
  kalıyorsan bir olgu daha ekle, uzunsa kıs.
  Dört bilgiyi taşı: nasıl başladı (erken durum, TEK detay yeter —
  "16 sayıya kadar taşıdı" gibi ikinci bir sayı gerekmez) → nerede
  döndü (kritik an, TEK cümle) → kim bitirdi (kararı belirleyen oyun/
  oyuncu — saniyeyi ver ama "45.7 saniye kala" yerine "son dakikada"
  gibi kabaca yeter) → kim öne çıktı (en iyi performans). `ozet`,
  `baslik`'ın kopyası değil DEVAMIDIR — aynı bilgiyi iki kez, iki
  farklı cümlede söyleme.
  BİR CÜMLEYE 3+ AYRI BİLGİ TIKIŞTIRMA — gerçek üretim bug'ı: "Son
  periyotta serbest atışlarla sayısını 83'e taşıyan X, 43 dakikada
  20/43 şutla 9 ribaund ve 5 çalma topladı" tek cümlede DÖRT ayrı
  bilgiyi (nasıl 83'e ulaştı / dakika / şut yüzdesi / ribaund-çalma)
  boğuyordu, cümle okunaksızlaşıyordu. Gerekirse "en iyi performans"
  beat'ini TEK cümle yerine gövdenin son İKİ cümlesine yay (toplam
  yine 4'ü geçmeden) — biri performansın KENDİSİ (sayı/ribaund/
  asist), biri varsa performansın içindeki ÇARPICI bir alt-gerçek
  (ör. "83 sayının 36'sı serbest atıştan geldi" gibi, `oyuncu_stat`
  taki `ft`/`serbest` alanından hesaplanabilirse). TEK bir cümle asla
  3'ten fazla ayrı sayı/olgu taşımasın."""

    tanim = (
        'Bu gecenin "Mutlaka bil" maçlarından biri, ama EN ÖNEMLİSİ DEĞİL — kısa geçilecek.'
        if kisa else
        'Bu gecenin EN önemli "Mutlaka bil" maçı — gecenin sesi burada, tam anlatı hak ediyor.'
    )
    talimat = f"""{tanim} "Bunları geç" bölümündeki maçlardan FARKLI bir
iskelet kullanır: kısa iki cümle değil, maçın akışını anlatan bir
gövde. Üç alan yaz:

OVERNIGHT telefonda, yatakta, uyanır uyanmaz okunuyor — hiçbir alan
ekranda kaydırma gerektirmemeli. Bu yüzden üçü de SIKI bir uzunluk
sınırına bağlı:

- `baslik`: tek satır, fiil içerir, EN FAZLA 10 KELİME — maçı
  BELİRLEYEN TEK ŞEYİ söyle (ör. "X, son saniye basketiyle Y'yi
  yendi"). Gereksiz ayrıntı ekleme, tek bir çarpıcı gerçek yeter.
- `neden_onemli`: tek cümle, en fazla 15 kelime — `baslik`'ta
  SÖYLENMEMİŞ bir şey söyle (sıralama, seri, gece içindeki yeri gibi
  SONUCUN ANLAMI). `baslik` ne dediyse `neden_onemli` onu başka
  kelimelerle TEKRAR ETMEZ — yeni bilgi taşır.
{govde_talimati}

SAYI TEKRARI YASAK: `baslik` ya da `neden_onemli` içinde geçen bir SAYI
(skor "111-99", "16 sayılık fark", "2. sıra") gövdede TEKRAR EDİLMEZ.
Başlık skoru zaten söylüyorsa gövde skoru yeniden yazmaz; gövde başka
şey anlatır. Bu kural artık makine tarafından denetleniyor, ihlal eden
metin reddediliyor.

GENEL KURAL — AYNI OLGU İKİ KEZ GEÇEMEZ: `baslik`, `neden_onemli` ve
gövde ({govde_alani}) ayrı ayrı okunmuyor, TEK bir kart olarak okunuyor.
Bir kilometre/bağlam gerçeğini (ör. "ondan önce NBA tarihinde sadece N
oyuncu başardı") HANGİ ALANDA kullandıysan, DİĞER ALANDA TEKRARLAMA —
gerçek üretim bug'ı: aynı cümle hem `neden_onemli`de hem gövdenin
sonunda ayrı ayrı çıkmıştı. Bu gerçeği SADECE BİR alanda kullan.

{mutlaka_talimati}
Takım adını cümledeki İLK anışta tam şehir/takım adıyla yaz, ikinci
anıştan itibaren takma ad kullanabilirsin — üç harfli kod ASLA kullanma.

`muzip`: ölçülü muziplik kullandıysan true. Bu maç için en fazla
{kalan_muzip_kotasi} pay var (gecenin geri kalanı zaten kullanılmış
olabilir).

DİKKAT: Bir geri dönüşten bahsedeceksen KAÇ SAYILIK olduğunu MUTLAKA
yaz — "farktan dönerek yendi" tek başına hiçbir şey söylemiyor, 4
sayılık fark da 16 sayılık fark da o cümleye sığar. Sayı elinde:
`fark_serisi.kazanan_en_buyuk_acigi` = kazananın kapattığı en büyük açık.

DİKKAT: `fark_serisi` gerçeğinde İKİ ayrı lider değişim sayısı var —
`lider_degisim_sayisi` MAÇ GENELİ toplamı, `son_periyot_lider_degisimi`
SADECE son çeyrek/periyot içindekiler. "Son çeyreği N lider
değişimiyle geçti" gibi bir cümle kuracaksan `son_periyot_lider_degisimi`yi
kullan — maç geneli sayıyı son çeyreğe atfetme.
{ust_uste_uyarisi}{onceki_hata_talimati}
JSON şeması:
{{"baslik": "...", "neden_onemli": "...", "{govde_alani}": "...", "muzip": bool}}
"""
    # Maç verisi promptun BAŞINA alındı ve ayrı bir parça olarak dönüyor.
    # Sebep: önbellek ÖNEK (prefix) üzerinden çalışır. Blok sondayken
    # önündeki talimatlar her denemede değiştiği için (önceki hata listesi
    # ekleniyor) hiçbir şey önbellekten okunamıyordu — 14 bin token her
    # denemede tam fiyat ödeniyordu. Şimdi büyük ve DEĞİŞMEYEN kısım
    # önde: aynı maçın onarım denemeleri onu önbellekten okuyor.
    mac_verisi = (
        "Maç verisi:\n"
        + json.dumps(kompakt_gercekler(grup_b_gercekleri(gercekler, en_iyi_performans)), ensure_ascii=False)
        + "\n"
    )
    return mac_verisi, talimat


# Ölçüldü (2025-10-23, aynı maç, aynı prompt):
#   effort=medium → 6543 çıktı token, görünen metin 631 karakter (~%97'si
#                   faturalanan ama DÖNMEYEN düşünme), $0.1256, 71 sn
#   effort=low    → 2289 çıktı token, görünen metin 616 karakter,
#                   $0.0831, 27 sn — gövde 58 kelime (hedef aralıkta)
# Yani düşük effort metni kısaltmıyor, sadece düşünme israfını kesiyor.
# Ama low tek başına riskli: daha önce Jokić maçında 3 denemede de aynı
# T18 hatasını tekrarlamıştı. Bu yüzden KADEMELİ: ilk deneme low (çağrıların
# çoğu ilk denemede kabul ediliyor), doğrulamadan dönen onarım denemeleri
# medium (hatayı görüp düzeltmesi gereken yer orası).
GRUP_B_EFFORT = "medium"          # onarım denemeleri
GRUP_B_EFFORT_ILK = "low"         # ilk deneme
GRUP_B_MAX_TOKENS = 10000  # effort=medium'da thinking payı dalgalanıyor — 6000 bazen tamamen thinking'e gidip metin bırakmıyordu (max_tokens hatası), pay artırıldı
GRUP_B_MAX_TOKENS_KISA = 7000  # kısa gövde (2-3 cümle, 45 kelime) hedefi daha düşük ama aynı effort=medium dalgalanma riski var — GRUP_B_MAX_TOKENS'tan biraz düşük tutuldu, aşırı düşürülmedi


def grup_b_uret(gid, gercekler, ham_mac, kalan_muzip_kotasi, kalip, ornekler_havuzu, en_iyi_performans=None, onceki_hatalar=None, kisa=False, ust_uste_kullanildi_mi=False):
    prompt = grup_b_prompt_kur(gid, gercekler, ham_mac, kalan_muzip_kotasi, kalip, ornekler_havuzu, en_iyi_performans, onceki_hatalar, kisa=kisa, ust_uste_kullanildi_mi=ust_uste_kullanildi_mi)
    # Eskiden adaptive thinking (effort belirtilmeden) + max_tokens=12000
    # kullanılıyordu — ölçüm gösterdi ki bu, kısa bir JSON için bile
    # 7-11 bin çıktı token'ı harcıyor (gerçek maliyetin asıl kaynağı).
    # DİKKAT: Sonnet 5 sabit thinking budget_tokens'ı DESTEKLEMİYOR —
    # tek kontrol noktası output_config.effort (bkz. llm_cagir). Kalite
    # düşerse GRUP_B_EFFORT yükseltilecek (kullanıcı kararı: "önce ölç").
    return llm_cagir(
        GUCLU_MODEL, sistem_prompt(), prompt,
        max_tokens=(GRUP_B_MAX_TOKENS_KISA if kisa else GRUP_B_MAX_TOKENS),
        effort=(GRUP_B_EFFORT if onceki_hatalar else GRUP_B_EFFORT_ILK),
    )


# ---------------------------------------------------------------------------
# Grup A gözden geçirme — Haiku üretir, Sonnet tek çağrıda düzeltir
# ---------------------------------------------------------------------------
#
# Karşılaştırma turu şunu gösterdi: tüm geceyi Sonnet'e yazdırmak (Grup
# A'da 9 maç birden) hem pahalı hem de kaliteyi iyileştirmiyor — thinking
# payı dağılıyor, kısaltmalara yaslanıyor. Grup A artık maç başına ayrı
# Sonnet çağrısıyla üretiliyor (bkz. grup_a_uret_tekli), ama bu ayrı bir
# QA katmanının değerini düşürmüyor — tek başına üretimden kaçan bir
# tökezlemeyi ikinci bir okuma yakalayabilir. Kullanıcının düzeltmesi:
# gözden geçiricinin CİLALAMA yetkisi yok, sadece REDDETME yetkisi var.
# Önceki sürüm "yazılı"→"yazan" gibi gramer düzeltmeleri yaparak
# anlamsız bir cümleyi ("11 sayı yazan Cavaliers baskısı" gibi) düzgün
# GÖRÜNÜR hale getirmişti — bu, hiç gözden geçirmemekten daha kötü,
# çünkü artık doğrulayıcıdan geçen bir saçmalık var. Türkçe akıcılık
# yargısı mekanik olarak taklit edilemiyor, o yüzden model kendi
# yargısına güvenemediği her cümlede REDDET diyecek ve o maç yeniden
# üretilecek — polişleme yok, ya olduğu gibi kalır ya da baştan yazılır.

GOZDEN_GECIRME_TALIMATI = """Aşağıda bir gecenin "Bunları geç" bölümündeki {n} maç metni var.

Her metin için TEK soru: "Bu cümle bir Türk okuyucuya anlamlı geliyor
mu?" Gelmiyorsa, garip/bozuk/anlaşılmaz duruyorsa DÜZELTMEYE ÇALIŞMA —
o metnin karşılığına sadece "REDDET" yaz. Cilalama yetkin yok, sadece
kabul veya ret.

Yalnızca şu türde KÜÇÜK ve KESİN hatalarda düzeltme yapabilirsin (bunun
dışında ya aynen bırak ya da REDDET de):
- Yazım hatası (özellikle ğ/ş/ı/ç/ö/ü harflerinin düşmesi)
- Terim tablosuna uymayan kelime (örn. "üçlü-dubl" yerine
  "triple-double" — karşılığı olmayan ve Türkçe yazımı da doğal
  durmayan terimler İngilizce kalır)
- Aynı takımın metin içinde hem tam adıyla hem kısaltmayla geçmesi

KESİNLİKLE DEĞİŞTİRME: hiçbir sayı, isim, sonuç, olgu. Metin zaten
sorunsuzsa AYNEN bırak.

Metinler (maç id -> metin):
{metinler_json}

JSON şeması: {{"<mac_id>": "düzeltilmiş metin VEYA aynen bırakılan metin VEYA \\"REDDET\\"", ...}}
— HER id için bir satır, hiçbirini atlama.
"""


def grup_a_gozden_gecir(gec_satiri_by_gid):
    prompt = GOZDEN_GECIRME_TALIMATI.format(
        n=len(gec_satiri_by_gid),
        metinler_json=json.dumps(gec_satiri_by_gid, ensure_ascii=False),
    )
    return llm_cagir(GUCLU_MODEL, sistem_prompt(), prompt, max_tokens=16000)


# ---------------------------------------------------------------------------
# "Bunları geç" kelime bütçesi
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Hedefli uzunluk onarımı — kör yeniden üretim yerine
# ---------------------------------------------------------------------------
#
# İlk sürümde bir alan HERHANGİ bir sebeple reddedilince doğrudan şablon
# moduna düşülüyordu. Ama üç brief satırı sırf 13 kelimeyken (sınır 12)
# reddedildi — "30 saniyede gece" sayfanın en çok okunan bölümü, orada
# kuru şablon metin en istemediğimiz şey. Bir cümleyi kısaltmak sıfırdan
# yazmaktan çok daha güvenilir bir iş; SADECE uzunluk (T6) başarısızsa
# reddedilen taslağı geri gönderip "bunu kısalt" diyoruz.

UZUNLUK_ACIKLAMA = {
    "brief_metin": "en fazla 12 kelime, tek cümle",
    "baslik": "tek satır",
    "neden_onemli": "en fazla 15 kelime, tek cümle",
    "ozet": "TAM 4 cümle, 55-75 kelime",
    "ozet_kisa": "2-3 cümle, 30-45 kelime",
    "gec_satiri": "en fazla 3 cümle",
}


def sadece_uzunluk_mu_basarisiz(testler):
    """testler: alan_dogrula()'nın döndürdüğü {'T1': (bool, detay), ...}.
    T6 başarısız VE başka hiçbir test başarısız değilse True — bu
    durumda kısaltma denemeye değer, başka bir hata varsa (uydurma
    sayı, yasaklı ifade) kısaltmak o hatayı çözmez."""
    if testler.get("T6", (True, None))[0]:
        return False  # T6 zaten geçmiş, onarılacak bir şey yok
    return all(gecti for ad, (gecti, _) in testler.items() if ad != "T6")


def uzunluk_onar(model, json_alan_adi, reddedilen_metin, gercekler, sadece_turler=None, max_tokens=500, aciklama_anahtari=None):
    aciklama = UZUNLUK_ACIKLAMA.get(aciklama_anahtari or json_alan_adi, "daha kısa")
    prompt = f"""Şu metni KISALT — {aciklama} sınırına indir. Anlamı,
doğruluğu ve kazananı koru; gerçekler dışına çıkma, yeni bir şey
ekleme, SADECE kısalt.

Metin: "{reddedilen_metin}"

Maç verisi:
{json.dumps(kompakt_gercekler(gercekler, sadece_turler), ensure_ascii=False)}

JSON şeması: {{"{json_alan_adi}": "..."}}
"""
    yanit = llm_cagir(model, sistem_prompt(), prompt, max_tokens=max_tokens)
    return yanit.get(json_alan_adi)


def gec_tier_butcesini_uygula(gec_maclar_metin, gec_maclar_rozet, gercek_by_gid, ham, yasakli, haber_skorlari):
    """Toplam kelime > 220 ise en düşük rozetli maçlardan başlayarak
    kısaltma ister (gec_satiri'yi tek cümleye indirmeye zorlar).
    Kısaltılan metin YENİDEN doğrulanır (kazananı hâlâ söylüyor mu vb.)."""
    toplam = sum(kelime_say(m["gec_satiri"]) for m in gec_maclar_metin.values())
    if toplam <= GEC_TIER_KELIME_BUTCESI:
        return gec_maclar_metin, False

    sira = sorted(gec_maclar_metin.keys(), key=lambda gid: gec_maclar_rozet[gid])
    for gid in sira:
        if toplam <= GEC_TIER_KELIME_BUTCESI:
            break
        eski = gec_maclar_metin[gid]["gec_satiri"]
        eski_kelime = kelime_say(eski)

        prompt = f"""Şu metni TEK CÜMLEYE indir, kazananı ve en az bir
sayıyı mutlaka koru, gerçekler dışına çıkma:

"{eski}"

Maç verisi:
{json.dumps(kompakt_gercekler(gercek_by_gid[gid], GRUP_A_ONEMLI_TURLER), ensure_ascii=False)}

JSON şeması: {{"gec_satiri": "..."}}
"""
        try:
            yanit = llm_cagir(UCUZ_MODEL, sistem_prompt(), prompt, max_tokens=300)
            yeni = yanit["gec_satiri"]
        except Exception:
            continue

        sonuc = mac_metnini_dogrula(
            {"gec_satiri": yeni}, gercek_by_gid[gid], ham["maclar"][gid],
            haber_skorlari.get(gid, 0), yasakli,
        )
        if sonuc["kabul"]:
            gec_maclar_metin[gid]["gec_satiri"] = yeni
            toplam += kelime_say(yeni) - eski_kelime

    return gec_maclar_metin, True


# ---------------------------------------------------------------------------
# Kalıp planı — gece başına BİR KEZ, tüm maçlar için kanca/kademe/
# niteleyici/öne-çıkma-fiili ataması (kalip_secici.py'nin sarmalayıcısı)
# ---------------------------------------------------------------------------


def gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece):
    yildizlar = yildizlar_yukle()
    kalite_ort, kalite_sirali = takim_kalitesi_hesapla(ham["puan_durumu"], tarih_str)
    rozet_by_gid = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}

    olgu_by_gid = {}
    for gid in gercek_gece["maclar"]:
        olgu_by_gid[gid] = olgulari_hesapla(
            gercek_gece["maclar"][gid], ham["maclar"][gid], haber_skoru=0,
            yildizlar=yildizlar, kalite_ort=kalite_ort, kalite_sirali=kalite_sirali,
        )

    atama = gece_kanca_ata(olgu_by_gid, yildizlar)
    kanca_harf_by_gid = {gid: harf for gid, (harf, _) in atama.items()}
    nitelik_by_gid = gece_niteleyici_ata(olgu_by_gid, rozet_by_gid, kanca_harf_by_gid)

    # Kullanıcı kararı (mimari değişikliği): "ezdi" fiili gece çapında
    # KIT bir kaynak — aynı gecede 20+ farklı her maça "ezdi" demek
    # anlamsız, o zaman hiçbiri "ezmiş" gibi durmuyor. SADECE gecenin
    # EN BÜYÜK farkı bu fiili alır (ve o fark yine de 20+ olmalı).
    en_buyuk_fark_gid = max(olgu_by_gid, key=lambda g: olgu_by_gid[g].get("fark", 0), default=None)
    for gid, olgu in olgu_by_gid.items():
        olgu["en_buyuk_fark_gecede_mi"] = (
            gid == en_buyuk_fark_gid and olgu.get("fark", 0) >= BUYUK_FARK_ESIGI_TEK_CUMLE
        )

    # Öne çıkma fiili de aynı gecede tekrar edemez (Bölüm 4 kuralı) —
    # rozet sırasına göre kütüphaneden sırayla atanıyor.
    fiiller = one_cikma_fiilleri_listesi()
    sira = sorted(olgu_by_gid.keys(), key=lambda g: -rozet_by_gid[g])
    fiil_by_gid = {gid: fiiller[i % len(fiiller)] for i, gid in enumerate(sira)}

    plan = {}
    for gid in gercek_gece["maclar"]:
        olgu = olgu_by_gid[gid]
        kademe, olgular = kademe_hesapla(olgu)
        kanca_harf, kanca_gerekce = atama[gid]
        plan[gid] = {
            "kademe": kademe,
            "olgular": olgular,
            "kanca_harf": kanca_harf,
            "kanca_gerekce": kanca_gerekce,
            "niteleyiciler": nitelik_by_gid[gid],
            "one_cikma_fiili": fiil_by_gid[gid],
            # Şablon modu (sablon_uret_mutlaka) LLM kullanmadan bu ham
            # olguları doğrudan cümleye döküyor — tekrar hesaplamamak
            # için burada da taşınıyor.
            "olgu_ham": olgu,
        }
    return plan


# ---------------------------------------------------------------------------
# Rapor metrikleri — ret oranı TEK BAŞINA yanıltıcı (kullanıcı kararı):
# yeniden üretimde düzelen bir ret sistemin ÇALIŞTIĞINI gösterir, bozuk
# olduğunu değil. Asıl sağlık göstergesi şablona düşen oranı (kaç alan
# HİÇBİR ŞEKİLDE kabul edilemeyip son çareye düştü).
# ---------------------------------------------------------------------------

_T_NUMARASI_DESENI = re.compile(r"\bT(\d+[a-z]?)\b")


def _rapor_metrikleri_hesapla(rapor):
    sablon_orani = round(rapor["sablon_moduna_dusen"] / rapor["toplam_alan"], 3) if rapor["toplam_alan"] else 0.0

    # İki denemede de reddedilen alan sayısı: aynı (mac_id, yer) için
    # hem deneme=0 hem deneme=1 rapor["detay"]'de görünüyorsa, o alan
    # HER İKİ şansını da tüketip şablona düşmüş demektir.
    denemeler_by_anahtar = {}
    for d in rapor.get("detay", []):
        anahtar = (d.get("mac_id"), d.get("yer", ""))
        denemeler_by_anahtar.setdefault(anahtar, set()).add(d.get("deneme"))
    iki_denemede_reddedilen = sum(1 for denemeler in denemeler_by_anahtar.values() if {0, 1} <= denemeler)

    test_sayaci = {}
    for d in rapor.get("detay", []):
        for g in d.get("gerekce", []):
            for m in _T_NUMARASI_DESENI.finditer(g):
                anahtar = f"T{m.group(1)}"
                test_sayaci[anahtar] = test_sayaci.get(anahtar, 0) + 1
    en_cok_tetikleyen = sorted(test_sayaci.items(), key=lambda kv: -kv[1])[:3]

    return {
        "sablon_orani": sablon_orani,
        "iki_denemede_reddedilen": iki_denemede_reddedilen,
        "en_cok_tetikleyen_testler": en_cok_tetikleyen,
    }


def _grup_a_mac_isle(gid, bilgi, ham, kalip_plani, ornekler_havuzu, yasakli, haber_skorlari, ikinci_cumle=None):
    """Bir Grup A maçının TAM deneme döngüsünü çalıştırır ve LOKAL bir
    sonuç sözlüğü döner — paylaşılan `rapor`/`taslak_maclar`'a yazmaz.
    ThreadPoolExecutor ile paralel çağrılabilmesi için böyle: birden
    fazla iş parçacığı aynı anda çalışırken paylaşılan bir sözlüğe
    `.append`/`+= 1` yapmak veri yarışına (race condition) açık olurdu.
    Ana iş parçacığı `as_completed` ile tüm sonuçları TEK TEK, sırayla
    birleştiriyor.

    Muzip bütçesi burada TAKİP EDİLMİYOR (her çağrıya tam kota
    bildiriliyor) — paralel çalışırken sıralı takip imkânsız, batch
    modundaki gibi SONRADAN `_muzip_butcesini_sonradan_uygula` ile
    düzeltiliyor."""
    gercekler = bilgi["gercekler"]
    ham_mac = ham["maclar"][gid]
    deneme = 0
    kabul_edildi = False
    metin_obj = None
    lokal_detay = []
    ilk_denemede_kabul = False

    while deneme < MAX_DENEME and not kabul_edildi:
        try:
            aday = grup_a_uret_tekli(gid, bilgi, ham, MUZIP_BUTCESI_GRUP_A, kalip_plani[gid], ornekler_havuzu)
        except Exception as e:
            aday = None
            print(f"Grup A çağrısı başarısız ({gid}, {type(e).__name__}: {e!r}).")
        if aday is None:
            break
        sonuc = mac_metnini_dogrula(
            aday, gercekler, ham_mac, haber_skorlari.get(gid, 0), yasakli,
            en_iyi_performans=bilgi.get("en_iyi_performans"),
        )
        if sonuc["kabul"]:
            if deneme == 0:
                ilk_denemede_kabul = True
            metin_obj = aday
            kabul_edildi = True
        else:
            lokal_detay.append({"mac_id": gid, "deneme": deneme, "gerekce": sonuc["gerekce"], "reddedilen_taslak": aday})
            testler = sonuc["alanlar"].get("gec_satiri", {}).get("testler", {})
            if sadece_uzunluk_mu_basarisiz(testler):
                try:
                    kisaltilmis = uzunluk_onar(
                        GUCLU_MODEL, "gec_satiri", aday["gec_satiri"], gercekler, GRUP_A_ONEMLI_TURLER
                    )
                    onarilmis = {**aday, "gec_satiri": kisaltilmis}
                    onarim_sonucu = mac_metnini_dogrula(
                        onarilmis, gercekler, ham_mac, haber_skorlari.get(gid, 0), yasakli,
                        en_iyi_performans=bilgi.get("en_iyi_performans"),
                    )
                    if onarim_sonucu["kabul"]:
                        metin_obj = onarilmis
                        kabul_edildi = True
                except Exception:
                    pass
                break
            deneme += 1

    sablon_dusen = False
    sablon_isaretli = []
    if not kabul_edildi:
        kalip = kalip_plani[gid]
        metin_obj = {
            "gec_satiri": sablon_uret(
                gercekler, ham_mac, bilgi.get("en_iyi_performans"), ikinci_cumle,
                kanca_harf=kalip["kanca_harf"], olgu=kalip["olgu_ham"], rozet=bilgi.get("rozet"),
            ),
            "muzip": False,
        }
        sablon_dusen = True
        _gecici_rapor = {}
        _sablon_isaretle(_gecici_rapor, gid, "gec_satiri", metin_obj, gercekler, ham_mac, bilgi.get("en_iyi_performans"), yasakli)
        sablon_isaretli = _gecici_rapor.get("sablon_isaretli", [])

    return {
        "gid": gid, "metin_obj": metin_obj, "detay": lokal_detay,
        "ilk_denemede_kabul": ilk_denemede_kabul, "sablon_dusen": sablon_dusen,
        "sablon_isaretli": sablon_isaretli,
        "toplam_alan": 1,
    }


def _uzunluk_onar_dongu(aday, sonuc, gercekler, ham_mac, haber_skoru, yasakli, en_iyi_performans):
    """SADECE T6'dan (uzunluk) başarısız alanları TEKRAR TEKRAR kısaltır
    — tek seferlik değil, ta ki geçene ya da UZUNLUK_ONARIM_MAX_TUR
    tükenene kadar. Kullanıcı kararı: 'sadece uzunluktan dolayı şablona
    düşmek yasak — uzun bir metin kısaltılabilir bir metindir.'
    Döner: (guncel_aday, guncel_sonuc, sadece_uzunluk_sorunu_kaldi_mi)."""
    guncel, guncel_sonuc = dict(aday), sonuc
    for _ in range(UZUNLUK_ONARIM_MAX_TUR):
        uzun_alanlar, icerik_sorunu_var = [], False
        for alan, alan_sonuc in guncel_sonuc["alanlar"].items():
            if alan not in ALAN_UZUNLUK_ADI or alan_sonuc["gecti"]:
                continue
            if sadece_uzunluk_mu_basarisiz(alan_sonuc["testler"]):
                uzun_alanlar.append(alan)
            else:
                icerik_sorunu_var = True
        if icerik_sorunu_var or not uzun_alanlar:
            return guncel, guncel_sonuc, (not icerik_sorunu_var) and bool(uzun_alanlar)
        for alan in uzun_alanlar:
            try:
                guncel[alan] = uzunluk_onar(GUCLU_MODEL, alan, guncel[alan], gercekler, max_tokens=2000)
            except Exception:
                return guncel, guncel_sonuc, True  # onarım çağrısı başarısız — yine de sadece uzunluk sorunu
        guncel_sonuc = mac_metnini_dogrula(
            guncel, gercekler, ham_mac, haber_skoru, yasakli, en_iyi_performans=en_iyi_performans,
        )
        if guncel_sonuc["kabul"]:
            return guncel, guncel_sonuc, False
    return guncel, guncel_sonuc, True


def _metnin_tum_alanlari(d):
    return " ".join(v for v in d.values() if isinstance(v, str))


def _ust_uste_kontrolcusu_kur(gece_durumu):
    """`gece_durumu` — {"kullanildi": bool} biçiminde DIŞARIDAN paylaşılan
    tek bir mutable sözlük (Grup A şablonları zaten kullandıysa True ile
    başlar). SADECE OKUR, YAZMAZ — bir aday birden çok kez kontrol
    edilebiliyor (ör. uzunluk onarımından önce/sonra), "kullanıldı"
    işaretini burada koymak kendi onarılmış halini reddeden bir
    kısır döngü yaratıyordu (gerçek üretim bug'ı, kod incelemesinde
    yakalandı). İşaretleme çağıran kodda, maç GERÇEKTEN kabul
    edildikten SONRA yapılır (bkz. yaz_hibrit)."""
    def kontrol(aday):
        if aday is None:
            return True, None
        varsa = bool(UST_USTE_DESENI.search(_metnin_tum_alanlari(aday)))
        if varsa and gece_durumu["kullanildi"]:
            return False, "gece_capinda: 'üst üste/art arda' kalıbı bu gece zaten kullanıldı, tekrar edilemez"
        return True, None
    return kontrol


def _grup_b_dongu(gid, gercekler, ham_mac, kalip, ornekler_havuzu, en_iyi_performans, yasakli, haber_skoru, olgu, uret_fn, ekstra_red_kontrolu=None):
    """Grup B'nin (Mutlaka bil) TAM deneme döngüsü — SADECE yaz()'ın
    senkron akışı için (batch modu kendi toplu-istek mantığını kullanır,
    bkz. yaz_batch). uret_fn(onceki_hatalar_veya_None) -> aday sözlüğü;
    kalan_muzip gibi sabit parametreler çağıranın closure'ında.
    `ekstra_red_kontrolu(aday) -> (bool_ok, sebep_veya_None)` verilirse,
    normal doğrulama geçse BİLE bu kontrol de geçmeli — kullanıcı
    kararı: "üst üste/art arda" gibi gece-çapında bir kalıp Grup A
    şablonlarında zaten kullanıldıysa Grup B'de TEKRAR kullanılmasın,
    mac_metnini_dogrula'nın tek-maçlık kapsamı bunu tek başına
    göremiyor.
    Döner: (metin_obj, kabul_edildi, toplam_alan, ilk_denemede_kabul,
    detay_listesi)."""
    deneme = 0
    kabul_edildi = False
    aday = None
    onceki_hatalar = []
    detay = []
    toplam_alan = 0
    ilk_denemede_kabul = False

    while deneme < MAX_DENEME_GRUP_B and not kabul_edildi:
        _onceki_kayit_sayisi = len(KULLANIM_TAKIBI)
        try:
            aday = uret_fn(onceki_hatalar if onceki_hatalar else None)
        except Exception as e:
            print(f"Grup B çağrısı başarısız ({gid}, {type(e).__name__}: {e!r}).")
            break
        # Kullanıcı kararı: her Grup B denemesinin gerçek token maliyeti
        # görünür olsun — başarısız bir deneme de tam fiyat ödüyor.
        for _k in KULLANIM_TAKIBI[_onceki_kayit_sayisi:]:
            print(
                f"[Grup B {gid} deneme {deneme}] girdi={_k['girdi']} çıktı={_k['cikti']} "
                f"cache_yazma={_k['cache_yazma']} cache_okuma={_k['cache_okuma']}"
            )

        toplam_alan += 1
        sonuc = mac_metnini_dogrula(
            aday, gercekler, ham_mac, haber_skoru, yasakli, en_iyi_performans=en_iyi_performans,
        )
        ekstra_ok, ekstra_sebep = (True, None) if ekstra_red_kontrolu is None else ekstra_red_kontrolu(aday)
        if sonuc["kabul"] and ekstra_ok:
            if deneme == 0:
                ilk_denemede_kabul = True
            return aday, True, toplam_alan, ilk_denemede_kabul, detay

        gerekce = list(sonuc["gerekce"] or [])
        if not ekstra_ok:
            gerekce.append(ekstra_sebep)
        detay.append({"mac_id": gid, "deneme": deneme, "gerekce": gerekce, "reddedilen_taslak": aday})
        onceki_hatalar = gerekce

        if not sonuc["kabul"]:
            _onceki_kayit_sayisi = len(KULLANIM_TAKIBI)
            onarilmis, onarim_sonucu, sadece_uzunluk_kaldi = _uzunluk_onar_dongu(
                aday, sonuc, gercekler, ham_mac, haber_skoru, yasakli, en_iyi_performans,
            )
            for _k in KULLANIM_TAKIBI[_onceki_kayit_sayisi:]:
                print(
                    f"[Grup B {gid} deneme {deneme} — uzunluk onarımı] girdi={_k['girdi']} çıktı={_k['cikti']} "
                    f"cache_yazma={_k['cache_yazma']} cache_okuma={_k['cache_okuma']}"
                )
            ekstra_ok2, ekstra_sebep2 = (True, None) if ekstra_red_kontrolu is None else ekstra_red_kontrolu(onarilmis)
            if onarim_sonucu["kabul"] and ekstra_ok2:
                return onarilmis, True, toplam_alan, ilk_denemede_kabul, detay
        else:
            sadece_uzunluk_kaldi = False
        if sadece_uzunluk_kaldi and ekstra_ok2:
            # Kullanıcı kararı: SADECE uzunluktan asla şablona düşme —
            # onarım turları tükendiyse bile GERÇEK (biraz uzun kalmış
            # olabilir) metni kabul et, deneme döngüsünü burada bitir.
            # `ekstra_ok2` şart: uzunluk sorunu tek başına kalsa bile
            # gece-çapında bir çakışma (ör. "üst üste" tekrarı) varsa bu
            # kaçış yolu devreye girmez.
            return onarilmis, True, toplam_alan, ilk_denemede_kabul, detay

        deneme += 1

    return None, False, toplam_alan, ilk_denemede_kabul, detay


def _brief_kismi_birlestir(yeni_brief, mevcut_brief, sadece_gidler):
    """Brief TEK bir çağrıda TÜM satırları birden üretiyor — kısmi
    üretimde hedeflenen maç brief'te de varsa, o çağrı TÜM satırları
    yeniden yazar (gerçek üretim bug'ı: sadece bir maç hedeflenmişken
    5 satırın 5'i de değişmişti). Burada, hedef_mac'i sadece_gidler'de
    OLMAYAN her satır mevcut dosyadaki hâliyle geri konuyor — sadece
    hedeflenen maça ait satır(lar) yeni üretimden kalıyor. Eşleştirme
    POZİSYONA değil hedef_mac değerine göre (model sırayı değiştirebilir)."""
    mevcut_by_hedef = {b.get("hedef_mac"): b for b in mevcut_brief}
    sonuc = []
    for satir in yeni_brief:
        hedef = satir.get("hedef_mac")
        if hedef in sadece_gidler:
            sonuc.append(satir)
        elif hedef in mevcut_by_hedef:
            sonuc.append(mevcut_by_hedef[hedef])
        else:
            sonuc.append(satir)  # mevcut'ta karşılığı yoksa yeni üretim kalsın
    return sonuc


def _rapor_yazdir(tarih_str, rapor):
    metrikler = _rapor_metrikleri_hesapla(rapor)
    rapor["sablon_orani"] = metrikler["sablon_orani"]
    rapor["iki_denemede_reddedilen"] = metrikler["iki_denemede_reddedilen"]
    rapor["en_cok_tetikleyen_testler"] = metrikler["en_cok_tetikleyen_testler"]

    print(f"[{tarih_str}] Şablona düşen: %{metrikler['sablon_orani']*100:.1f} ({rapor['sablon_moduna_dusen']}/{rapor['toplam_alan']})")
    print(f"[{tarih_str}] İki denemede de reddedilen alan: {metrikler['iki_denemede_reddedilen']}")
    if metrikler["en_cok_tetikleyen_testler"]:
        liste = ", ".join(f"{ad} ({n}x)" for ad, n in metrikler["en_cok_tetikleyen_testler"])
        print(f"[{tarih_str}] En çok tetikleyen testler: {liste}")
    if metrikler["sablon_orani"] > 0.20:
        print(f"[{tarih_str}] UYARI: şablona düşen oran %20'nin üstünde — muhtemel sebep gercekler.py'nin eksik üretmesi ya da bir kuralın aşırı sıkı olması.")

    k = rapor["kullanim"]
    if k["cagri_sayisi"]:
        print(
            f"[{tarih_str}] Token: {k['girdi_token']} girdi + {k['cikti_token']} çıktı + "
            f"{k['cache_yazma_token']} önbellek-yazma + {k['cache_okuma_token']} önbellek-okuma "
            f"({k['cagri_sayisi']} çağrı) — tahmini maliyet: ${k['toplam_maliyet_usd']:.4f}"
        )

    _sablon_isaretli_yazdir(tarih_str, rapor)


# ---------------------------------------------------------------------------
# Şablon çıktısı da doğrulayıcıdan geçer. Kullanıcı kararı (dogrula.py
# --hepsi denetiminin ortaya çıkardığı kör nokta): şablonlar "güvenilir,
# deterministik" varsayımıyla hiç doğrulanmıyordu, ama üç düzeltme
# turunun büyük kısmı ("40'e yükseltti", nesnesiz "ezdi", aynı gecede iki
# "üst üste" vb.) tam da şablon kodundaki hatalardı — hepsi gözle
# bulundu, doğrulayıcı hiçbirini yakalamadı. Kural: şablon metni üretilir
# → doğrulayıcıdan geçirilir → geçerse öylece kalır, geçmezse YİNE DE
# yayınlanır (şablon son çare, asla boş kalmaz) ama rapora İŞARETLENİR.
# ---------------------------------------------------------------------------


def _sablon_isaretle(rapor, gid, alan_etiketi, metin_obj, gercekler, ham_mac, en_iyi_performans, yasakli):
    """`metin_obj` (gec_satiri sözlüğü veya mutlaka'nın baslik/ozet/
    ozet_kisa/neden_onemli sözlüğü) mac_metnini_dogrula'dan geçirilir.
    Yayını ASLA engellemez — sadece kabul edilmezse rapor["sablon_isaretli"]'ye
    ekler, metin_obj değişmeden geri döner."""
    # sablon=True: uzunluk ALT sınırları uygulanmaz (kullanıcı kuralı —
    # şablon kendi doğal uzunluğunda kalır), ama olgu/dil/atıf testleri
    # aynen uygulanır. Şablon çıktısının doğrulanması hâlâ ZORUNLU;
    # muaf olan tek şey "daha uzun yaz" baskısı.
    sonuc = mac_metnini_dogrula(metin_obj, gercekler, ham_mac, 0, yasakli,
                                en_iyi_performans=en_iyi_performans, sablon=True)
    if not sonuc["kabul"]:
        rapor.setdefault("sablon_isaretli", []).append({
            "mac_id": gid, "alan": alan_etiketi, "gerekce": sonuc["gerekce"], "metin": metin_obj,
        })
    return metin_obj


def _brief_isaretle(rapor, gid, brief_ogesi, gercekler, ham_mac, yasakli):
    sonuc = brief_metnini_dogrula(brief_ogesi, gercekler, ham_mac, 0, yasakli)
    if not sonuc["kabul"]:
        rapor.setdefault("sablon_isaretli", []).append({
            "mac_id": gid, "alan": "brief", "gerekce": sonuc["gerekce"], "metin": brief_ogesi.get("metin"),
        })
    return brief_ogesi


def _sablon_isaretli_yazdir(tarih_str, rapor):
    isaretli = rapor.get("sablon_isaretli") or []
    if not isaretli:
        print(f"[{tarih_str}] Şablon doğrulaması: tüm şablon metinleri kurallardan geçti.")
        return
    print(f"[{tarih_str}] Şablon doğrulaması: {len(isaretli)} alan işaretlendi (yine de yayınlandı, şablon son çare):")
    for kayit in isaretli:
        print(f"  - maç {kayit['mac_id']} [{kayit['alan']}]: {'; '.join(kayit['gerekce'])}")
        print(f"    metin: {kayit['metin']}")


# ---------------------------------------------------------------------------
# Şablon-SADECE üretim — HİÇ LLM çağrısı yok, tamamen mekanik. Kullanıcı
# kararı: "şablon zeminini bana ayrıca göster" — ürünün en kötü hâli,
# hiçbir üretim başarısız olmasa bile bu kaliteye düşebileceğini
# göstermek için. `--sadece-sablon` CLI bayrağıyla çağrılır.
# ---------------------------------------------------------------------------


def yaz_sablon(tarih_str, zorla=False, dosya_soneki="-sablon"):
    """Kullanıcı kararı (radikal küçültme turu): LLM tamamen devre dışı,
    bu fonksiyon artık VARSAYILAN üretim yolu (`dosya_soneki=""` ile
    `taslak/{tarih}.json`a yazar — CLI'daki varsayılan çağrı böyle yapar).
    `--sadece-sablon` bayrağı hâlâ eski önizleme davranışını (`-sablon`
    sonekiyle ayrı dosya) korur, geriye dönük uyumluluk için.

    Tüm maç metinleri TEK katmandan geçer: `_mac_cumleleri_uret` (bkz.
    yukarıda) — eski `sablon_uret`/`sablon_uret_mutlaka` çifti burada
    KULLANILMIYOR (hâlâ dormant hibrit/LLM yolunda mevcutlar, "kod
    kalsın" kararıyla silinmedi, ama iki ayrı kural seti tutmanın
    getirdiği sızıntı riski bu yolda artık yok)."""
    hedef_dosya = TASLAK_DIZIN / f"{tarih_str}{dosya_soneki}.json"
    if hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden yaz).")
        return hedef_dosya

    gercek_gece = json.loads((GERCEK_DIZIN / f"{tarih_str}.json").read_text())
    ham = json.loads((HAM_DIZIN / f"{tarih_str}.json").read_text())
    skor_gece = json.loads((SKOR_DIZIN / f"{tarih_str}.json").read_text())

    yasakli = yasakli_yukle()
    mutlaka, diger = _mutlaka_ve_diger(skor_gece)
    en_iyi_performans_by_gid = {m["mac_id"]: m.get("en_iyi_performans") for m in skor_gece["maclar"]}
    rozet_by_gid = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}
    katman_by_gid = {m["mac_id"]: m["katman"] for m in skor_gece["maclar"]}
    kalip_plani = gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece)
    uretim_rapor = {}

    mutlaka_gidleri = {m["mac_id"] for m in mutlaka}
    diger_hedef_sayisi = max(0, 5 - len(mutlaka_gidleri))
    brief_hedefleri = list(mutlaka_gidleri) + [m["mac_id"] for m in diger[:diger_hedef_sayisi]]

    taslak_maclar = {}
    for m in diger:
        gid = m["mac_id"]
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        seviye = "degerse" if katman_by_gid[gid] in ("mutlaka", "ikinci") else "gec"
        taslak_maclar[gid] = {
            "gec_satiri": _mac_cumleleri_uret(
                gercekler, ham_mac, kalip_plani[gid]["olgu_ham"], en_iyi_performans_by_gid.get(gid),
                kalip_plani[gid]["kanca_harf"], seviye,
            ),
            "muzip": False,
        }
        _sablon_isaretle(uretim_rapor, gid, "gec_satiri", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans_by_gid.get(gid), yasakli)

    # DİKKAT — mimari kural: "Mutlaka bil" şablonu TEK yerde kurulur
    # (cumle.mutlaka_metni). Burada bir zamanlar ayrı, elle yazılmış bir
    # başlık/gövde kopyası vardı; `yaz_hibrit` ise sablon_uret_mutlaka'yı
    # çağırıyordu. İki yol zamanla ayrıştı ve bu yol kazanan-takım kancası
    # ile boş-alan kurallarını almadı — ÜRETİLEN METİN yola göre farklı
    # çıkıyordu (gerçek bug: 2025-10-23'te bu yol T17'yi ihlal eden bir
    # başlık kuruyordu, hibrit yol kurmuyordu). Tek çağrıya indirildi.
    for gid in mutlaka_gidleri:
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        taslak_maclar[gid] = sablon_uret_mutlaka(
            gercekler, ham_mac, kalip_plani[gid]["olgu_ham"],
            en_iyi_performans_by_gid.get(gid),
        )
        _sablon_isaretle(uretim_rapor, gid, "mutlaka", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans_by_gid.get(gid), yasakli)

    brief_by_gid = gece_brief_ata(kalip_plani, rozet_by_gid, brief_hedefleri, ham, en_iyi_performans_by_gid, gercek_gece)
    taslak_brief = [brief_by_gid[gid] for gid in brief_hedefleri if gid in brief_by_gid]
    for obj in taslak_brief:
        gid = obj["hedef_mac"]
        _brief_isaretle(uretim_rapor, gid, obj, gercek_gece["maclar"][gid], ham["maclar"][gid], yasakli)

    cikti = {
        "tarih": tarih_str,
        "uretildi": datetime.utcnow().isoformat() + "Z",
        "maclar": taslak_maclar,
        "brief": taslak_brief,
        "rapor": {
            "uretim_modu": "sablon", "kullanim": {"cagri_sayisi": 0, "toplam_maliyet_usd": 0.0},
            "sablon_isaretli": uretim_rapor.get("sablon_isaretli", []),
        },
    }

    TASLAK_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya} (SADECE şablon, LLM çağrısı yok, maliyet $0.00)")
    _sablon_isaretli_yazdir(tarih_str, uretim_rapor)
    return hedef_dosya


# ---------------------------------------------------------------------------
# Hibrit üretim — VARSAYILAN mod. Kullanıcı kararı: "Mutlaka bil" gecenin
# TEK asıl-değerli metni, geri kalanı (Bunları geç, brief) için LLM'in
# katkısı marjinal ama maliyeti tam fiyat. Sadece Grup B LLM çağırır;
# Grup A ve brief mekanik şablondan (bkz. sablon_uret / sablon_uret_brief).
# Türkler ve Gecenin beşi zaten hiçbir modda LLM kullanmıyor (derle.py
# doğrudan box score'dan hesaplıyor) — bu yüzden burada ayrıca ele
# alınmıyor.
# ---------------------------------------------------------------------------


def yaz_hibrit(tarih_str, zorla=False):
    hedef_dosya = TASLAK_DIZIN / f"{tarih_str}.json"
    if hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden yaz).")
        return hedef_dosya

    yasakli = yasakli_yukle()
    gercek_gece = json.loads((GERCEK_DIZIN / f"{tarih_str}.json").read_text())
    ham = json.loads((HAM_DIZIN / f"{tarih_str}.json").read_text())
    skor_gece = json.loads((SKOR_DIZIN / f"{tarih_str}.json").read_text())

    mutlaka, diger = _mutlaka_ve_diger(skor_gece)
    en_iyi_performans_by_gid = {m["mac_id"]: m.get("en_iyi_performans") for m in skor_gece["maclar"]}
    rozet_by_gid = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}
    kalip_plani = gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece)
    ornekler_havuzu = ornekler_yukle()

    mutlaka_gidleri = [m["mac_id"] for m in mutlaka]
    diger_hedef_sayisi = max(0, 5 - len(mutlaka_gidleri))
    brief_hedefleri = mutlaka_gidleri + [m["mac_id"] for m in diger[:diger_hedef_sayisi]]

    rapor = {"toplam_alan": 0, "ilk_denemede_kabul": 0, "sablon_moduna_dusen": 0, "detay": [], "sablon_isaretli": []}

    # ---- Grup A — şablon, LLM YOK ----
    taslak_maclar = {}
    for m in diger:
        gid = m["mac_id"]
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        taslak_maclar[gid] = {
            "gec_satiri": sablon_uret(
                gercekler, ham_mac, en_iyi_performans_by_gid.get(gid), None,
                kanca_harf=kalip_plani[gid]["kanca_harf"], olgu=kalip_plani[gid]["olgu_ham"], rozet=rozet_by_gid.get(gid),
            ),
            "muzip": False,
        }
        _sablon_isaretle(rapor, gid, "gec_satiri", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans_by_gid.get(gid), yasakli)

    # ---- brief — şablon, LLM YOK (kullanıcı kararı: kaliteye bakılıp sonra karar verilecek) ----
    brief_by_gid = gece_brief_ata(kalip_plani, rozet_by_gid, brief_hedefleri, ham, en_iyi_performans_by_gid, gercek_gece)
    taslak_brief = [brief_by_gid[gid] for gid in brief_hedefleri if gid in brief_by_gid]
    for obj in taslak_brief:
        gid = obj["hedef_mac"]
        _brief_isaretle(rapor, gid, obj, gercek_gece["maclar"][gid], ham["maclar"][gid], yasakli)

    # ---- Grup B (mutlaka) — GERÇEK LLM, tam deneme+onarım+zengin-şablon-fallback zinciri ----
    # Kullanıcı kararı: Mutlaka bil'e 8.5+ olan en fazla 3 maç girer,
    # ama maliyeti kontrol etmek için SADECE en yüksek rozetli (mutlaka[0])
    # tam anlatı alır — 2./3. maç (kisa=True) kısa anlatı.
    kalan_muzip = MUZIP_BUTCESI_TOPLAM
    # "üst üste/art arda" bir gecede EN FAZLA BİR KEZ — Grup A
    # şablonları zaten kullandıysa Grup B bunu bilerek başlar.
    gece_ust_uste_durumu = {"kullanildi": bool(UST_USTE_DESENI.search(_metnin_tum_alanlari(
        {gid2: m2.get("gec_satiri", "") for gid2, m2 in taslak_maclar.items()}
    )))}
    ust_uste_kontrol = _ust_uste_kontrolcusu_kur(gece_ust_uste_durumu)
    for i, m in enumerate(mutlaka):
        gid = m["mac_id"]
        kisa = i > 0
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        en_iyi_performans = en_iyi_performans_by_gid.get(gid)

        # Rozet sırasına göre ilk MUTLAKA_LLM_MAC_SAYISI maç LLM'e gider,
        # gerisi doğrudan şablondan — LLM çağrısı bile yapılmaz.
        if i >= MUTLAKA_LLM_MAC_SAYISI:
            taslak_maclar[gid] = sablon_uret_mutlaka(gercekler, ham_mac, kalip_plani[gid]["olgu_ham"], en_iyi_performans, kisa=kisa)
            _sablon_isaretle(rapor, gid, "mutlaka", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans, yasakli)
            if UST_USTE_DESENI.search(_metnin_tum_alanlari(taslak_maclar[gid])):
                gece_ust_uste_durumu["kullanildi"] = True
            continue

        metin_obj, kabul_edildi, toplam_alan, ilk_denemede_kabul, detay = _grup_b_dongu(
            gid, gercekler, ham_mac, kalip_plani[gid], ornekler_havuzu, en_iyi_performans, yasakli,
            0, kalip_plani[gid]["olgu_ham"],
            uret_fn=lambda onceki_hatalar, kisa=kisa: grup_b_uret(
                gid, gercekler, ham_mac, kalan_muzip, kalip_plani[gid], ornekler_havuzu, en_iyi_performans, onceki_hatalar, kisa=kisa,
                ust_uste_kullanildi_mi=gece_ust_uste_durumu["kullanildi"],
            ),
            ekstra_red_kontrolu=ust_uste_kontrol,
        )
        rapor["toplam_alan"] += toplam_alan
        rapor["detay"].extend(detay)
        if ilk_denemede_kabul:
            rapor["ilk_denemede_kabul"] += 1

        if kabul_edildi:
            taslak_maclar[gid] = metin_obj
        else:
            taslak_maclar[gid] = sablon_uret_mutlaka(gercekler, ham_mac, kalip_plani[gid]["olgu_ham"], en_iyi_performans, kisa=kisa)
            rapor["sablon_moduna_dusen"] += 1
            _sablon_isaretle(rapor, gid, "mutlaka", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans, yasakli)
        # Kabul edilen (LLM ya da şablon) metin "üst üste/art arda"
        # kullandıysa gece durumunu güncelle — SONRAKİ Grup B maçı bunu
        # tekrar edemesin.
        if UST_USTE_DESENI.search(_metnin_tum_alanlari(taslak_maclar[gid])):
            gece_ust_uste_durumu["kullanildi"] = True

    rapor["ret_orani"] = round(
        1 - (rapor["ilk_denemede_kabul"] / rapor["toplam_alan"]) if rapor["toplam_alan"] else 0, 3
    )
    rapor["uretim_modu"] = "hibrit"
    rapor["kullanim"] = kullanim_raporu()

    cikti = {
        "tarih": tarih_str,
        "uretildi": datetime.utcnow().isoformat() + "Z",
        "maclar": taslak_maclar,
        "brief": taslak_brief,
        "rapor": rapor,
    }

    TASLAK_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya} (hibrit — sadece Mutlaka bil LLM kullandı)")
    _rapor_yazdir(tarih_str, rapor)

    return hedef_dosya


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------


def yaz(tarih_str, zorla=False, haber_skorlari=None, sadece_gidler=None):
    """sadece_gidler verilirse (bir gid iterable'ı) SADECE o maçlar
    yeniden üretilir — kullanıcı kararı: "bir kural değiştiğinde tüm
    geceyi değil, etkilenen 2-3 maçı üret; diğerlerinin metni dosyada
    aynen kalsın." Mevcut bir taslak/{tarih}.json ZORUNLU (kısmi üretim
    onun üstüne bindirilir, sıfırdan kurulmaz). Bu modda "Bunları geç"
    kelime bütçesi ATLANIR — o adım rozete göre TÜM geceyi yeniden
    dengeleyebilir, dokunulmayan maçların metnini de değiştirebilirdi."""
    hedef_dosya = TASLAK_DIZIN / f"{tarih_str}.json"
    sadece_gidler = set(sadece_gidler) if sadece_gidler else None

    if sadece_gidler:
        if not hedef_dosya.exists():
            raise FileNotFoundError(
                f"{hedef_dosya} yok — kısmi üretim (sadece_gidler) mevcut bir taslak dosyası üzerine "
                f"bindirilir, önce tüm geceyi bir kez üretmek gerekir."
            )
        mevcut = json.loads(hedef_dosya.read_text())
    elif hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden yaz).")
        return hedef_dosya
    else:
        mevcut = None

    haber_skorlari = haber_skorlari or {}
    yasakli = yasakli_yukle()

    gercek_gece = json.loads((GERCEK_DIZIN / f"{tarih_str}.json").read_text())
    ham = json.loads((HAM_DIZIN / f"{tarih_str}.json").read_text())
    skor_gece = json.loads((SKOR_DIZIN / f"{tarih_str}.json").read_text())

    mutlaka, diger = _mutlaka_ve_diger(skor_gece)
    rozet_by_gid = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}
    en_iyi_performans_by_gid = {m["mac_id"]: m.get("en_iyi_performans") for m in skor_gece["maclar"]}

    # ---- Kalıp seçimi (kalip_secici.py) — kanca/kademe/niteleyici KOD
    # tarafından, gece başına BİR KEZ, tüm maçlar arasında tekrar
    # yasağı gözetilerek seçiliyor. Model artık bu seçimi yapmıyor.
    kalip_plani = gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece)
    ornekler_havuzu = ornekler_yukle()

    rapor = {"toplam_alan": 0, "ilk_denemede_kabul": 0, "sablon_moduna_dusen": 0, "detay": []}
    if sadece_gidler:
        rapor["kismi_uretim"] = sorted(sadece_gidler)

    # ---- Grup A ----
    gec_maclar = {
        m["mac_id"]: {
            "rozet": m["rozet"],
            "gercekler": gercek_gece["maclar"][m["mac_id"]],
            "en_iyi_performans": en_iyi_performans_by_gid.get(m["mac_id"]),
        }
        for m in diger
        if sadece_gidler is None or m["mac_id"] in sadece_gidler
    }
    # brief için TÜM maçlar (mutlaka dahil) — kaynak, doğrulama ve
    # şablon geri düşüşü buradan besleniyor.
    maclar_kaynagi = {
        m["mac_id"]: {
            "rozet": m["rozet"],
            "gercekler": gercek_gece["maclar"][m["mac_id"]],
            "en_iyi_performans": en_iyi_performans_by_gid.get(m["mac_id"]),
        }
        for m in skor_gece["maclar"]
    }

    # Gecenin en iyi maçı (mutlaka) "30 saniyede gece"de İLK SIRADA
    # olmak zorunda — "gecenin 30 saniyesi" bölümü sadece brief'i
    # okuyan birinin gecenin maçını kaçırmaması gerekiyor (kullanıcı
    # düzeltmesi: ilk sürüm mutlaka'yı brief havuzundan tamamen
    # dışlıyordu çünkü brief_hedefleri sadece "diger"den besleniyordu).
    mutlaka_gidleri = [m["mac_id"] for m in mutlaka]
    diger_hedef_sayisi = max(0, 5 - len(mutlaka_gidleri))
    brief_hedefleri = mutlaka_gidleri + [m["mac_id"] for m in diger[:diger_hedef_sayisi]]

    # Rozetten bağımsız olay eşikleri: bir maç top-5 rozete girmese bile
    # kilometre taşı bir performans (triple-double, 50+ sayı, kariyer
    # rekoru — bkz. "kilometre" gerçek türü) ya da yüksek haber skoru
    # (ciddi sakatlık, ihraç vb.) taşıyorsa "30 saniyede gece"de yer
    # almalı. En düşük rozetli brief hedefinin yerini alır.
    def _olay_esigini_asiyor_mu(gid):
        gercekler = gercek_gece["maclar"][gid]
        kilometre_var = any(f["tur"] == "kilometre" for f in gercekler)
        return kilometre_var or haber_skorlari.get(gid, 0) >= 6

    olay_adaylari = [
        m["mac_id"] for m in diger
        if m["mac_id"] not in brief_hedefleri and _olay_esigini_asiyor_mu(m["mac_id"])
    ]
    if olay_adaylari:
        degistirilebilir = sorted(brief_hedefleri, key=lambda g: rozet_by_gid[g])
        for olay_gid in olay_adaylari:
            if not degistirilebilir:
                break
            cikarilan = degistirilebilir.pop(0)
            brief_hedefleri[brief_hedefleri.index(cikarilan)] = olay_gid

    taslak_maclar = {}
    taslak_brief = []

    # Grup A — maçlar birbirinden BAĞIMSIZ (her biri kendi promptu,
    # kendi doğrulaması) — PARALEL_ISCI_SAYISI kadar iş parçacığıyla
    # eşzamanlı üretiliyor (kullanıcı kararı: sıralı üretim 10 maçlık
    # bir gecede gereksiz yere dakikalar sürüyordu). Muzip bütçesi bu
    # yüzden SONRADAN uygulanıyor (bkz. _muzip_butcesini_sonradan_uygula).
    with ThreadPoolExecutor(max_workers=PARALEL_ISCI_SAYISI) as havuz:
        gelecekler = {
            havuz.submit(
                _grup_a_mac_isle, gid, bilgi, ham, kalip_plani, ornekler_havuzu, yasakli, haber_skorlari,
                None,
            ): gid
            for gid, bilgi in gec_maclar.items()
        }
        for gelecek in as_completed(gelecekler):
            sonuc = gelecek.result()
            rapor["toplam_alan"] += sonuc["toplam_alan"]
            rapor["detay"].extend(sonuc["detay"])
            if sonuc["ilk_denemede_kabul"]:
                rapor["ilk_denemede_kabul"] += 1
            if sonuc["sablon_dusen"]:
                rapor["sablon_moduna_dusen"] += 1
            rapor.setdefault("sablon_isaretli", []).extend(sonuc.get("sablon_isaretli", []))
            taslak_maclar[sonuc["gid"]] = sonuc["metin_obj"]

    # ---- Grup A gözden geçirme (ikinci Sonnet çağrısı, sadece ret yetkisi) ----
    # Şablona düşenleri (metnin kaynağı gerçek üretim değil, deterministik
    # kalıp) gözden geçirmeye sokmaya gerek yok — zaten her zaman doğru.
    # Ayırt etmenin yolu: o maçın gec_satiri'si sablon_uret()'in üreteceği
    # metinle birebir aynıysa, o zaten şablon demektir.
    gozden_gecirme_oncesi_sonrasi = []
    gec_satiri_havuzu = {
        gid: taslak_maclar[gid]["gec_satiri"]
        for gid in gec_maclar
        if gid in taslak_maclar and taslak_maclar[gid]["gec_satiri"] != sablon_uret(
            gec_maclar[gid]["gercekler"], ham["maclar"][gid], gec_maclar[gid].get("en_iyi_performans"), None,
            kanca_harf=kalip_plani[gid]["kanca_harf"], olgu=kalip_plani[gid]["olgu_ham"], rozet=rozet_by_gid.get(gid),
        )
    }

    if gec_satiri_havuzu:
        try:
            sonuclar = grup_a_gozden_gecir(gec_satiri_havuzu)
        except Exception as e:
            sonuclar = {}
            print(f"Gözden geçirme çağrısı başarısız ({type(e).__name__}: {e!r}), üretilen metinler değişmeden kalıyor.")

        for gid, hukum in sonuclar.items():
            if gid not in gec_satiri_havuzu:
                continue
            eski = gec_satiri_havuzu[gid]

            if hukum == "REDDET":
                # Gözden geçirici cilalamıyor, sadece reddediyor — reddedilen
                # maç TEK SEFER daha, sıfırdan, yeni bir Sonnet çağrısıyla
                # üretilir. O da anlamsız çıkarsa (doğrulayıcı bunu mekanik
                # olarak ölçemez, sadece gerçek/kurallara uygunluk ölçer)
                # elimizde başka bir güvenlik ağı yok, üretimi olduğu gibi
                # bırakıyoruz — şablona düşürmek burada aşırı tepki olur,
                # çünkü ret sebebi akıcılık, olgu değil.
                try:
                    yeniden = grup_a_uret_tekli(gid, gec_maclar[gid], ham, MUZIP_BUTCESI_GRUP_A, kalip_plani[gid], ornekler_havuzu)
                    sonuc = mac_metnini_dogrula(
                        yeniden, gec_maclar[gid]["gercekler"], ham["maclar"][gid],
                        haber_skorlari.get(gid, 0), yasakli,
                        en_iyi_performans=gec_maclar[gid].get("en_iyi_performans"),
                    )
                except Exception as e:
                    yeniden = None
                    sonuc = None
                    print(f"Reddedilen maç yeniden üretilemedi ({gid}, {type(e).__name__}: {e!r}).")

                yeni_metin = yeniden["gec_satiri"] if yeniden else eski
                gozden_gecirme_oncesi_sonrasi.append({
                    "mac_id": gid, "oncesi": eski, "sonrasi": f"[REDDEDİLDİ, yeniden üretildi] {yeni_metin}",
                    "uygulandi": bool(sonuc and sonuc["kabul"]),
                })
                if yeniden and sonuc and sonuc["kabul"]:
                    taslak_maclar[gid] = {**taslak_maclar[gid], **yeniden}
                continue

            duzeltilmis = hukum
            if duzeltilmis == eski:
                continue
            aday_duzeltilmis = {**taslak_maclar[gid], "gec_satiri": duzeltilmis}
            sonuc = mac_metnini_dogrula(
                aday_duzeltilmis, gec_maclar[gid]["gercekler"], ham["maclar"][gid],
                haber_skorlari.get(gid, 0), yasakli,
            )
            gozden_gecirme_oncesi_sonrasi.append({
                "mac_id": gid, "oncesi": eski, "sonrasi": duzeltilmis, "uygulandi": sonuc["kabul"],
            })
            if sonuc["kabul"]:
                taslak_maclar[gid] = aday_duzeltilmis

    rapor["gozden_gecirme"] = gozden_gecirme_oncesi_sonrasi

    brief_yeniden_uret = sadece_gidler is None or bool(set(brief_hedefleri) & sadece_gidler)
    if not brief_yeniden_uret:
        taslak_brief = mevcut["brief"]
    else:
        try:
            brief_ham = brief_uret(brief_hedefleri, maclar_kaynagi, ham, kalip_plani)
        except Exception as e:
            brief_ham = None
            print(f"Brief çağrısı başarısız ({type(e).__name__}: {e!r}), her satır şablon moduna düşecek.")

        for i, sira_gid in enumerate(brief_hedefleri):
            if brief_ham and i < len(brief_ham.get("brief", [])):
                aday = brief_ham["brief"][i]
            else:
                aday = None
            # Modele "aşağıdaki maçlardan seçerek yaz" dendiği için brief[i]
            # ile brief_hedefleri[i] SIRAYLA eşleşmek zorunda değil — model
            # kendi `hedef_mac` alanını yazıyor. Doğrulama pozisyona göre
            # değil, modelin bildirdiği hedef_mac'e göre yapılmalı; yoksa
            # model brief[0]'da farklı bir maçtan bahsedince o maçın
            # isimleri/sayıları YANLIŞ maçın gerçeklerine karşı denetlenip
            # yanlış pozitif üretiyor (gerçek üretim bug'ı, bkz. commit notu).
            hedef_gid = aday.get("hedef_mac") if aday else None
            if hedef_gid not in maclar_kaynagi:
                hedef_gid = sira_gid
            rapor["toplam_alan"] += 1
            gecti = False
            if aday is not None:
                sonuc = brief_metnini_dogrula(
                    aday, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid],
                    haber_skorlari.get(hedef_gid, 0), yasakli,
                )
                gecti = sonuc["kabul"]
                if not gecti:
                    rapor["detay"].append({"mac_id": hedef_gid, "deneme": 0, "gerekce": sonuc["gerekce"], "yer": f"brief[{i}]", "reddedilen_taslak": aday})
                    if sadece_uzunluk_mu_basarisiz(sonuc["testler"]):
                        try:
                            kisaltilmis = uzunluk_onar(
                                GUCLU_MODEL, "metin", aday["metin"],
                                gercek_gece["maclar"][hedef_gid], GRUP_A_ONEMLI_TURLER,
                                aciklama_anahtari="brief_metin",
                            )
                            onarilmis = {**aday, "metin": kisaltilmis}
                            onarim_sonucu = brief_metnini_dogrula(
                                onarilmis, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid],
                                haber_skorlari.get(hedef_gid, 0), yasakli,
                            )
                            if onarim_sonucu["kabul"]:
                                aday = onarilmis
                                gecti = True
                        except Exception:
                            pass
            else:
                rapor["detay"].append({"mac_id": hedef_gid, "deneme": 0, "gerekce": ["model bu maç için brief üretmedi"], "yer": f"brief[{i}]"})
            if gecti:
                rapor["ilk_denemede_kabul"] += 1
                taslak_brief.append(aday)
            else:
                rapor["sablon_moduna_dusen"] += 1
                sablon_brief = sablon_uret_brief(
                    hedef_gid, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid],
                    kalip_plani[hedef_gid]["olgu_ham"], maclar_kaynagi[hedef_gid].get("en_iyi_performans"),
                )
                if sablon_brief is not None:
                    taslak_brief.append(sablon_brief)
                    _brief_isaretle(rapor, hedef_gid, sablon_brief, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid], yasakli)

        if sadece_gidler is not None:
            taslak_brief = _brief_kismi_birlestir(taslak_brief, mevcut["brief"], sadece_gidler)

    # ---- Grup B (mutlaka) ----
    # MAX_DENEME_GRUP_B (5) deneme hakkı + her denemede önceki ret
    # gerekçesi modele geri bildiriliyor (kullanıcı kararı: gecenin TEK
    # metni, maliyeti birkaç sent, körlemesine yeniden üretmek yerine
    # neyin yanlış gittiğini bilerek düzeltsin) + uzunluk hatası ASLA
    # şablona düşürmez (bkz. _uzunluk_onar_dongu). Şablona sadece
    # GERÇEK bir İÇERİK sorunu (uydurma sayı, yasaklı ifade vb.) 5
    # denemeyi de tükettiğinde düşülür — o zaman da artık `sablon_uret`
    # DEĞİL, olgulardan mekanik kuran zengin `sablon_uret_mutlaka`.
    # Grup A paralel üretildiği için muzip kotası artık SONRADAN
    # uygulanıyor (bkz. _muzip_butcesini_sonradan_uygula yukarıda) —
    # burada modele her zaman tam bütçe bildiriliyor.
    kalan_muzip = MUZIP_BUTCESI_TOPLAM
    for i, m in enumerate(mutlaka):
        gid = m["mac_id"]
        kisa = i > 0
        if sadece_gidler is not None and gid not in sadece_gidler:
            continue  # kısmi üretim: bu maç hedeflenmedi, mevcut metni aynen kalacak (aşağıda birleştiriliyor)
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        en_iyi_performans = en_iyi_performans_by_gid.get(gid)

        metin_obj, kabul_edildi, toplam_alan, ilk_denemede_kabul, detay = _grup_b_dongu(
            gid, gercekler, ham_mac, kalip_plani[gid], ornekler_havuzu, en_iyi_performans, yasakli,
            haber_skorlari.get(gid, 0), kalip_plani[gid]["olgu_ham"],
            uret_fn=lambda onceki_hatalar, kisa=kisa: grup_b_uret(
                gid, gercekler, ham_mac, kalan_muzip, kalip_plani[gid], ornekler_havuzu, en_iyi_performans, onceki_hatalar, kisa=kisa,
            ),
        )
        rapor["toplam_alan"] += toplam_alan
        rapor["detay"].extend(detay)
        if ilk_denemede_kabul:
            rapor["ilk_denemede_kabul"] += 1

        if kabul_edildi:
            taslak_maclar[gid] = metin_obj
        else:
            taslak_maclar[gid] = sablon_uret_mutlaka(gercekler, ham_mac, kalip_plani[gid]["olgu_ham"], en_iyi_performans, kisa=kisa)
            rapor["sablon_moduna_dusen"] += 1
            _sablon_isaretle(rapor, gid, "mutlaka", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans, yasakli)

    # Grup A paralel üretildiği için muzip kotası sıralı takip edilemedi
    # (bkz. _grup_a_mac_isle) — Grup A + Grup B'nin TAMAMI toplandıktan
    # SONRA, TEK seferde uygulanıyor.
    _muzip_butcesini_sonradan_uygula(taslak_maclar, {m["mac_id"] for m in mutlaka}, rozet_by_gid)

    # ---- "Bunları geç" kelime bütçesi ----
    # Kısmi üretimde ATLANIR — bu adım rozete göre TÜM geceyi yeniden
    # dengeler, dokunulmayan maçların metnini de kısaltabilirdi (kullanıcı
    # kararı: "diğerlerinin metni dosyada aynen kalsın").
    butce_uygulandi = False
    if sadece_gidler is None:
        gec_gid_listesi = [gid for gid in taslak_maclar if gid not in [m["mac_id"] for m in mutlaka]]
        gec_metin_alt_kume = {gid: taslak_maclar[gid] for gid in gec_gid_listesi}
        gec_metin_alt_kume, butce_uygulandi = gec_tier_butcesini_uygula(
            gec_metin_alt_kume, rozet_by_gid, gercek_gece["maclar"], ham, yasakli, haber_skorlari
        )
        taslak_maclar.update(gec_metin_alt_kume)

    rapor["ret_orani"] = round(
        1 - (rapor["ilk_denemede_kabul"] / rapor["toplam_alan"]) if rapor["toplam_alan"] else 0, 3
    )
    rapor["kelime_butcesi_uygulandi"] = butce_uygulandi
    rapor["kullanim"] = kullanim_raporu()

    # Kısmi üretim: hedeflenmeyen her maçın metni mevcut dosyadan AYNEN
    # kopyalanır — sadece_gidler'deki maçlar üstüne yazılmış olur.
    if sadece_gidler is not None:
        nihai_maclar = dict(mevcut["maclar"])
        nihai_maclar.update(taslak_maclar)
        taslak_maclar = nihai_maclar

    cikti = {
        "tarih": tarih_str,
        "uretildi": datetime.utcnow().isoformat() + "Z",
        "maclar": taslak_maclar,
        "brief": taslak_brief,
        "rapor": rapor,
    }

    TASLAK_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya}" + (f" (kısmi: {sorted(sadece_gidler)})" if sadece_gidler else ""))
    _rapor_yazdir(tarih_str, rapor)

    return hedef_dosya


# ---------------------------------------------------------------------------
# Toplu (batch) üretim — Anthropic Message Batches API, %50 indirimli
# ---------------------------------------------------------------------------
#
# `yaz()` maç başına AYRI ve SENKRON çağrı yapıyor (gerçek zamanlı yayın
# için tasarlandı — gece biter bitmez taslak hazır olmalı). `yaz_batch()`
# ise "acele yok, ucuz olsun" senaryosu için: bir gecenin TÜM Grup A
# maçlarını + brief'i + Grup B'yi TEK bir Message Batches isteğinde
# gönderir, toplu sonucu bekler, doğrular; başarısız kalanları bir
# sonraki TURDA yine toplu olarak yeniden dener (en fazla MAX_DENEME tur).
#
# Kasıtlı basitleştirmeler (yaz()'a göre):
#   1. Hedefli uzunluk onarımı (`uzunluk_onar`) YOK — herhangi bir sebeple
#      reddedilen alan bütünüyle yeniden üretilir. Daha az örnek-verimli
#      ama çok daha basit ve hâlâ doğru (aynı mekanik doğrulayıcılardan
#      geçmek zorunda).
#   2. Grup A "gözden geçirme" (ikinci Sonnet okuması, akıcılık kontrolü)
#      YOK — mekanik doğrulayıcılar (T1-T19) birincil güvenlik ağı olarak
#      kalıyor, akıcılık ikinci katmanı atlanıyor. Maliyet/karmaşıklık
#      takası, kullanıcıya açıkça bildirilmeli.
#   3. Muzip bütçesi ÖNCEDEN değil SONRADAN uygulanıyor — batch'teki tüm
#      istekler AYNI ANDA gönderildiği için kota sırayla takip edilemez;
#      bunun yerine tüm gece toplandıktan sonra muzip:true olan alanlar
#      rozete göre elenir (en düşük rozetliden başlayarak kota aşımı
#      kadarı sıfırlanır) — T7 testinin production'da zaten beklediği
#      "kota aşılırsa en düşükler sıfırlanır" davranışının SONRADAN hâli.
#   4. "Bunları geç" kelime bütçesi ve şablon modu SENKRON kalıyor (ucuz
#      Haiku çağrıları, batch'e değmez) — mevcut `gec_tier_butcesini_uygula`
#      ve `sablon_uret` aynen kullanılıyor.


def _batch_istek_kur(custom_id, model, sistem, kullanici_mesaji, max_tokens):
    return {
        "custom_id": custom_id,
        "params": {
            "model": model,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": kullanici_mesaji}],
        },
    }


def _batch_calistir(istekler, bekleme_sn=15, zaman_asimi_sn=7200):
    """istekler: [(custom_id, model, sistem, kullanici_mesaji, max_tokens), ...]
    Döner: {custom_id: ayiklanmis_json_veya_None}. Kullanım BATCH indirimiyle
    KULLANIM_TAKIBI'ne işleniyor. Batch bitene kadar bloklanarak bekler
    (poll) — "acele yok" varsayımıyla, bu fonksiyon dakikalar sürebilir."""
    import time as _time
    import anthropic

    if not istekler:
        return {}

    istemci = anthropic.Anthropic()
    cid_model = {cid: model for cid, model, *_ in istekler}
    batch_istekleri = [
        _batch_istek_kur(cid, model, sistem, mesaj, mt) for cid, model, sistem, mesaj, mt in istekler
    ]
    batch = istemci.messages.batches.create(requests=batch_istekleri)
    print(f"  Batch gönderildi: {batch.id} ({len(batch_istekleri)} istek)")

    baslangic = _time.time()
    while True:
        durum = istemci.messages.batches.retrieve(batch.id)
        if durum.processing_status == "ended":
            break
        if _time.time() - baslangic > zaman_asimi_sn:
            raise TimeoutError(f"Batch {batch.id} {zaman_asimi_sn}s içinde bitmedi (durum: {durum.processing_status})")
        _time.sleep(bekleme_sn)
    print(f"  Batch tamamlandı: {batch.id}")

    sonuclar = {}
    for kayit in istemci.messages.batches.results(batch.id):
        cid = kayit.custom_id
        if kayit.result.type != "succeeded":
            sonuclar[cid] = None
            print(f"  Batch isteği başarısız ({cid}): {kayit.result.type}")
            continue
        yanit = kayit.result.message
        KULLANIM_TAKIBI.append({
            "model": cid_model.get(cid, yanit.model),
            "girdi": yanit.usage.input_tokens,
            "cikti": yanit.usage.output_tokens,
            "cache_yazma": getattr(yanit.usage, "cache_creation_input_tokens", 0) or 0,
            "cache_okuma": getattr(yanit.usage, "cache_read_input_tokens", 0) or 0,
            "batch": True,
        })
        metin_bloklari = [b for b in yanit.content if b.type == "text"]
        if not metin_bloklari:
            sonuclar[cid] = None
            continue
        try:
            sonuclar[cid] = _yaniti_ayikla(metin_bloklari[0].text)
        except json.JSONDecodeError:
            sonuclar[cid] = None
    return sonuclar


def _muzip_butcesini_sonradan_uygula(taslak_maclar, mutlaka_gidleri, rozet_by_gid):
    """yaz()'daki sıralı kota takibinin (kalan_muzip_kotasi) batch
    modunda karşılığı yok — tüm istekler aynı anda gönderiliyor. Bunun
    yerine gece TOPLANDIKTAN SONRA muzip:true olan alanlar rozete göre
    elenir: Grup A içinde en fazla MUZIP_BUTCESI_GRUP_A, gece toplamında
    en fazla MUZIP_BUTCESI_TOPLAM kalır; kota aşımı en düşük rozetliden
    sıfırlanır (T7'nin beklediğiyle aynı nihai durum, farklı sırayla
    ulaşılıyor)."""
    grup_a_muzipler = sorted(
        (gid for gid in taslak_maclar if gid not in mutlaka_gidleri and taslak_maclar[gid].get("muzip")),
        key=lambda g: rozet_by_gid.get(g, 0),
    )
    for gid in grup_a_muzipler[: max(0, len(grup_a_muzipler) - MUZIP_BUTCESI_GRUP_A)]:
        taslak_maclar[gid]["muzip"] = False

    tum_muzipler = sorted(
        (gid for gid in taslak_maclar if taslak_maclar[gid].get("muzip")),
        key=lambda g: rozet_by_gid.get(g, 0),
    )
    for gid in tum_muzipler[: max(0, len(tum_muzipler) - MUZIP_BUTCESI_TOPLAM)]:
        taslak_maclar[gid]["muzip"] = False


def yaz_batch(tarih_str, zorla=False, haber_skorlari=None, sadece_gidler=None):
    """sadece_gidler için bkz. yaz()'ın docstring'i — aynı kısmi üretim
    sözleşmesi burada da geçerli."""
    hedef_dosya = TASLAK_DIZIN / f"{tarih_str}.json"
    sadece_gidler = set(sadece_gidler) if sadece_gidler else None

    if sadece_gidler:
        if not hedef_dosya.exists():
            raise FileNotFoundError(
                f"{hedef_dosya} yok — kısmi üretim (sadece_gidler) mevcut bir taslak dosyası üzerine "
                f"bindirilir, önce tüm geceyi bir kez üretmek gerekir."
            )
        mevcut = json.loads(hedef_dosya.read_text())
    elif hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden yaz).")
        return hedef_dosya
    else:
        mevcut = None

    haber_skorlari = haber_skorlari or {}
    yasakli = yasakli_yukle()

    gercek_gece = json.loads((GERCEK_DIZIN / f"{tarih_str}.json").read_text())
    ham = json.loads((HAM_DIZIN / f"{tarih_str}.json").read_text())
    skor_gece = json.loads((SKOR_DIZIN / f"{tarih_str}.json").read_text())

    mutlaka, diger = _mutlaka_ve_diger(skor_gece)
    mutlaka_gidleri = [m["mac_id"] for m in mutlaka]
    kisa_by_gid = {gid: (i > 0) for i, gid in enumerate(mutlaka_gidleri)}
    rozet_by_gid = {m["mac_id"]: m["rozet"] for m in skor_gece["maclar"]}
    en_iyi_performans_by_gid = {m["mac_id"]: m.get("en_iyi_performans") for m in skor_gece["maclar"]}

    kalip_plani = gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece)
    ornekler_havuzu = ornekler_yukle()

    rapor = {"toplam_alan": 0, "ilk_denemede_kabul": 0, "sablon_moduna_dusen": 0, "detay": []}
    if sadece_gidler:
        rapor["kismi_uretim"] = sorted(sadece_gidler)

    gec_maclar = {
        m["mac_id"]: {
            "rozet": m["rozet"],
            "gercekler": gercek_gece["maclar"][m["mac_id"]],
            "en_iyi_performans": en_iyi_performans_by_gid.get(m["mac_id"]),
        }
        for m in diger
        if sadece_gidler is None or m["mac_id"] in sadece_gidler
    }
    maclar_kaynagi = {
        m["mac_id"]: {
            "rozet": m["rozet"],
            "gercekler": gercek_gece["maclar"][m["mac_id"]],
            "en_iyi_performans": en_iyi_performans_by_gid.get(m["mac_id"]),
        }
        for m in skor_gece["maclar"]
    }

    diger_hedef_sayisi = max(0, 5 - len(mutlaka_gidleri))
    brief_hedefleri = mutlaka_gidleri + [m["mac_id"] for m in diger[:diger_hedef_sayisi]]

    def _olay_esigini_asiyor_mu(gid):
        gercekler = gercek_gece["maclar"][gid]
        kilometre_var = any(f["tur"] == "kilometre" for f in gercekler)
        return kilometre_var or haber_skorlari.get(gid, 0) >= 6

    olay_adaylari = [
        m["mac_id"] for m in diger
        if m["mac_id"] not in brief_hedefleri and _olay_esigini_asiyor_mu(m["mac_id"])
    ]
    if olay_adaylari:
        degistirilebilir = sorted(brief_hedefleri, key=lambda g: rozet_by_gid[g])
        for olay_gid in olay_adaylari:
            if not degistirilebilir:
                break
            cikarilan = degistirilebilir.pop(0)
            brief_hedefleri[brief_hedefleri.index(cikarilan)] = olay_gid

    taslak_maclar = {}
    bekleyen_gec = dict(gec_maclar)
    bekleyen_mutlaka = {
        m["mac_id"]: m for m in mutlaka
        if sadece_gidler is None or m["mac_id"] in sadece_gidler
    }
    brief_yeniden_uret = sadece_gidler is None or bool(set(brief_hedefleri) & sadece_gidler)
    brief_tamamlandi = not brief_yeniden_uret
    brief_aday_listesi = None
    # Grup B'nin önceki tur(lar)daki ret gerekçesi — batch modunda da
    # körlemesine yeniden üretmesin diye (bkz. kullanıcı kararı, yaz()'daki
    # aynı mekanizma). Batch MAX_DENEME turuna bağlı kaldığı için sync
    # kadar (5) deneme hakkı yok, ama en azından kör değil.
    grup_b_hatalar_by_gid = {}
    grup_b_son_aday_by_gid = {}

    for tur in range(MAX_DENEME):
        istekler = []

        for gid, bilgi in bekleyen_gec.items():
            prompt = grup_a_prompt_kur_tekli(gid, bilgi, ham, MUZIP_BUTCESI_GRUP_A, kalip_plani[gid], ornekler_havuzu)
            istekler.append((f"gecA_{gid}", GUCLU_MODEL, sistem_prompt(), prompt, GRUP_A_MAX_TOKENS))

        if not brief_tamamlandi:
            prompt = brief_prompt_kur(brief_hedefleri, maclar_kaynagi, ham, kalip_plani)
            istekler.append(("brief", GUCLU_MODEL, sistem_prompt(), prompt, 8000))

        for gid in bekleyen_mutlaka:
            en_iyi_performans = en_iyi_performans_by_gid.get(gid)
            prompt = grup_b_prompt_kur(
                gid, gercek_gece["maclar"][gid], ham["maclar"][gid], MUZIP_BUTCESI_TOPLAM,
                kalip_plani[gid], ornekler_havuzu, en_iyi_performans, grup_b_hatalar_by_gid.get(gid),
                kisa=kisa_by_gid.get(gid, False),
            )
            # Batch yolu tek parça metin bekliyor — grup_b_prompt_kur artık
            # (maç verisi, talimat) ikilisi döndürüyor, burada birleştiriliyor.
            # Önbellek kazancı batch'te zaten geçerli değil (istekler
            # birbirinden bağımsız kuyruklanıyor), sıra da önemsiz.
            istekler.append((f"grupB_{gid}", GUCLU_MODEL, sistem_prompt(), "".join(prompt), 12000))

        if not istekler:
            break

        print(f"[{tarih_str}] batch turu {tur + 1}/{MAX_DENEME} — {len(istekler)} istek")
        sonuclar = _batch_calistir(istekler)

        for gid in list(bekleyen_gec.keys()):
            aday = sonuclar.get(f"gecA_{gid}")
            bilgi = bekleyen_gec[gid]
            ham_mac = ham["maclar"][gid]
            if aday is None:
                rapor["detay"].append({"mac_id": gid, "deneme": tur, "gerekce": ["batch isteği başarısız / boş yanıt"]})
                continue
            rapor["toplam_alan"] += 1
            sonuc = mac_metnini_dogrula(
                aday, bilgi["gercekler"], ham_mac, haber_skorlari.get(gid, 0), yasakli,
                en_iyi_performans=bilgi.get("en_iyi_performans"),
            )
            if sonuc["kabul"]:
                if tur == 0:
                    rapor["ilk_denemede_kabul"] += 1
                taslak_maclar[gid] = aday
                del bekleyen_gec[gid]
            else:
                rapor["detay"].append({"mac_id": gid, "deneme": tur, "gerekce": sonuc["gerekce"], "reddedilen_taslak": aday})

        if not brief_tamamlandi:
            brief_ham = sonuclar.get("brief")
            if brief_ham and brief_ham.get("brief"):
                brief_aday_listesi = brief_ham["brief"]
                brief_tamamlandi = True
            elif tur == MAX_DENEME - 1:
                brief_tamamlandi = True  # son turda da yoksa aşağıda satır satır şablona düşecek

        for gid in list(bekleyen_mutlaka.keys()):
            aday = sonuclar.get(f"grupB_{gid}")
            gercekler = gercek_gece["maclar"][gid]
            ham_mac = ham["maclar"][gid]
            en_iyi_performans = en_iyi_performans_by_gid.get(gid)
            if aday is None:
                rapor["detay"].append({"mac_id": gid, "deneme": tur, "gerekce": ["batch isteği başarısız / boş yanıt"]})
                continue
            rapor["toplam_alan"] += 1
            sonuc = mac_metnini_dogrula(
                aday, gercekler, ham_mac, haber_skorlari.get(gid, 0), yasakli,
                en_iyi_performans=en_iyi_performans,
            )
            if sonuc["kabul"]:
                if tur == 0:
                    rapor["ilk_denemede_kabul"] += 1
                taslak_maclar[gid] = aday
                del bekleyen_mutlaka[gid]
            else:
                rapor["detay"].append({"mac_id": gid, "deneme": tur, "gerekce": sonuc["gerekce"], "reddedilen_taslak": aday})
                grup_b_hatalar_by_gid[gid] = sonuc["gerekce"]
                grup_b_son_aday_by_gid[gid] = (aday, sonuc)

        if not bekleyen_gec and not bekleyen_mutlaka and brief_tamamlandi:
            break

    # ---- kalan Grup A / Grup B alanları şablona düşer ----
    for gid, bilgi in bekleyen_gec.items():
        taslak_maclar[gid] = {
            "gec_satiri": sablon_uret(
                bilgi["gercekler"], ham["maclar"][gid], bilgi.get("en_iyi_performans"), None,
                kanca_harf=kalip_plani[gid]["kanca_harf"], olgu=kalip_plani[gid]["olgu_ham"], rozet=rozet_by_gid.get(gid),
            ),
            "muzip": False,
        }
        rapor["sablon_moduna_dusen"] += 1
        _sablon_isaretle(rapor, gid, "gec_satiri", taslak_maclar[gid], bilgi["gercekler"], ham["maclar"][gid], bilgi.get("en_iyi_performans"), yasakli)

    for gid in bekleyen_mutlaka:
        gercekler = gercek_gece["maclar"][gid]
        ham_mac = ham["maclar"][gid]
        en_iyi_performans = en_iyi_performans_by_gid.get(gid)
        # Şablona düşmeden ÖNCE son ret SADECE uzunluktan mıydı diye
        # bak — öyleyse mekanik onarımla kurtarmayı dene (kullanıcı
        # kararı: uzunluktan asla şablona düşülmez). Batch modu sync
        # kadar deneme hakkına sahip değil ama en azından bu son çare
        # denenmeden şablona atlamıyor.
        kurtarildi = False
        if gid in grup_b_son_aday_by_gid:
            son_aday, son_sonuc = grup_b_son_aday_by_gid[gid]
            onarilmis, onarim_sonucu, sadece_uzunluk_kaldi = _uzunluk_onar_dongu(
                son_aday, son_sonuc, gercekler, ham_mac, haber_skorlari.get(gid, 0), yasakli, en_iyi_performans,
            )
            if onarim_sonucu["kabul"] or sadece_uzunluk_kaldi:
                taslak_maclar[gid] = onarilmis
                kurtarildi = True
        if not kurtarildi:
            # Gerçek bir İÇERİK sorunu var — mekanik onarım çözemez.
            # `sablon_uret` DEĞİL, olgulardan mekanik kuran ZENGİN
            # `sablon_uret_mutlaka` (kullanıcı kararı: "Denver evinde
            # kazandı" gecenin en önemli maçı için kabul edilemez).
            taslak_maclar[gid] = sablon_uret_mutlaka(gercekler, ham_mac, kalip_plani[gid]["olgu_ham"], en_iyi_performans, kisa=kisa_by_gid.get(gid, False))
            rapor["sablon_moduna_dusen"] += 1
            _sablon_isaretle(rapor, gid, "mutlaka", taslak_maclar[gid], gercekler, ham_mac, en_iyi_performans, yasakli)

    _muzip_butcesini_sonradan_uygula(taslak_maclar, set(mutlaka_gidleri), rozet_by_gid)

    # ---- brief satır satır doğrulama + şablon düşüşü ----
    if not brief_yeniden_uret:
        taslak_brief = mevcut["brief"]
    else:
        taslak_brief = []
        for i, sira_gid in enumerate(brief_hedefleri):
            aday = brief_aday_listesi[i] if brief_aday_listesi and i < len(brief_aday_listesi) else None
            hedef_gid = aday.get("hedef_mac") if aday else None
            if hedef_gid not in maclar_kaynagi:
                hedef_gid = sira_gid
            rapor["toplam_alan"] += 1
            gecti = False
            if aday is not None:
                sonuc = brief_metnini_dogrula(
                    aday, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid],
                    haber_skorlari.get(hedef_gid, 0), yasakli,
                )
                gecti = sonuc["kabul"]
                if not gecti:
                    rapor["detay"].append({"mac_id": hedef_gid, "deneme": 0, "gerekce": sonuc["gerekce"], "yer": f"brief[{i}]", "reddedilen_taslak": aday})
            else:
                rapor["detay"].append({"mac_id": hedef_gid, "deneme": 0, "gerekce": ["model bu maç için brief üretmedi"], "yer": f"brief[{i}]"})
            if gecti:
                rapor["ilk_denemede_kabul"] += 1
                taslak_brief.append(aday)
            else:
                rapor["sablon_moduna_dusen"] += 1
                sablon_brief = sablon_uret_brief(
                    hedef_gid, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid],
                    kalip_plani[hedef_gid]["olgu_ham"], maclar_kaynagi[hedef_gid].get("en_iyi_performans"),
                )
                if sablon_brief is not None:
                    taslak_brief.append(sablon_brief)
                    _brief_isaretle(rapor, hedef_gid, sablon_brief, gercek_gece["maclar"][hedef_gid], ham["maclar"][hedef_gid], yasakli)

        if sadece_gidler is not None:
            taslak_brief = _brief_kismi_birlestir(taslak_brief, mevcut["brief"], sadece_gidler)

    # ---- "Bunları geç" kelime bütçesi — senkron, ucuz model, aynen yaz()'daki gibi ----
    # Kısmi üretimde ATLANIR (bkz. yaz()'daki aynı gerekçe).
    butce_uygulandi = False
    if sadece_gidler is None:
        gec_gid_listesi = [gid for gid in taslak_maclar if gid not in mutlaka_gidleri]
        gec_metin_alt_kume = {gid: taslak_maclar[gid] for gid in gec_gid_listesi}
        gec_metin_alt_kume, butce_uygulandi = gec_tier_butcesini_uygula(
            gec_metin_alt_kume, rozet_by_gid, gercek_gece["maclar"], ham, yasakli, haber_skorlari
        )
        taslak_maclar.update(gec_metin_alt_kume)

    rapor["ret_orani"] = round(
        1 - (rapor["ilk_denemede_kabul"] / rapor["toplam_alan"]) if rapor["toplam_alan"] else 0, 3
    )
    rapor["kelime_butcesi_uygulandi"] = butce_uygulandi
    rapor["uretim_modu"] = "batch"
    rapor["kullanim"] = kullanim_raporu()

    if sadece_gidler is not None:
        nihai_maclar = dict(mevcut["maclar"])
        nihai_maclar.update(taslak_maclar)
        taslak_maclar = nihai_maclar

    cikti = {
        "tarih": tarih_str,
        "uretildi": datetime.utcnow().isoformat() + "Z",
        "maclar": taslak_maclar,
        "brief": taslak_brief,
        "rapor": rapor,
    }

    TASLAK_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya}" + (f" (kısmi: {sorted(sadece_gidler)})" if sadece_gidler else ""))
    _rapor_yazdir(tarih_str, rapor)

    return hedef_dosya


if __name__ == "__main__":
    import argparse

    ayristirici = argparse.ArgumentParser()
    ayristirici.add_argument("tarih", help="YYYY-MM-DD")
    ayristirici.add_argument("--force", action="store_true")
    ayristirici.add_argument("--batch", action="store_true", help="Message Batches API ile %%50 indirimli, yavaş üretim — SADECE geçmişi toplu doldururken kullan (--tam ile birlikte)")
    ayristirici.add_argument("--tam", action="store_true", help="TÜM alanlar LLM (Grup A + brief + Mutlaka bil) — varsayılan hibrit modun yerine")
    ayristirici.add_argument("--sadece", default=None, help="Virgülle ayrılmış mac_id listesi — SADECE bu maçları yeniden üret, gerisi dosyada aynen kalır (--tam ile birlikte)")
    ayristirici.add_argument("--sadece-sablon", action="store_true", help="HİÇ LLM çağırma — tüm geceyi mekanik şablonla üret (bedava, API anahtarı gerektirmez)")
    args = ayristirici.parse_args()

    # Kullanıcı kararı (radikal küçültme turu): LLM tamamen devre dışı,
    # HİÇ API çağrısı yapılmaz — maliyet her zaman $0.00. Şablon-sadece
    # üretim artık VARSAYILAN yol (eskiden --sadece-sablon ile ayrı bir
    # önizleme dosyasına yazıyordu, şimdi doğrudan taslak/{tarih}.json'a
    # yazıyor). --tam/--hibrit/--batch bayrakları KOD OLARAK duruyor
    # ("kod kalsın, sonra geri açabiliriz") ama kasıtlı olarak artık
    # çağrılmıyor — LLM'i geri açmak isteyen biri bu bayrakları elle
    # kullanabilir, ama ANTHROPIC_API_KEY kontrolü hâlâ orada.
    # Kullanıcı kararı (bu tur, önceki "sadece şablon" kararı GERİ ALINDI):
    # "En iyi çıktılarımız LLM'den geliyor." VARSAYILAN yeniden HİBRİT —
    # Mutlaka bil LLM, gerisi şablon. Şablon-sadece mod --sadece-sablon
    # ile hâlâ erişilebilir (bedava, API anahtarı gerektirmez).
    if args.sadece_sablon:
        yaz_sablon(args.tarih, zorla=args.force, dosya_soneki="")
        raise SystemExit(0)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY tanımlı değil. yaz.py gerçek bir API anahtarı "
            "gerektirir (--sadece-sablon bayrağı anahtarsız, bedava çalışır)."
        )

    sadece_gidler = [g.strip() for g in args.sadece.split(",")] if args.sadece else None

    if args.tam and args.batch:
        yaz_batch(args.tarih, zorla=args.force, sadece_gidler=sadece_gidler)
    elif args.tam:
        yaz(args.tarih, zorla=args.force, sadece_gidler=sadece_gidler)
    else:
        # VARSAYILAN: hibrit — sadece Mutlaka bil LLM kullanır.
        yaz_hibrit(args.tarih, zorla=args.force)
