"""
hesapla.py — OVERNIGHT boru hattının 4. adımı.

Girdi:  ham/{tarih}.json + config/yildizlar.json (+ varsa config/takim_beklenti.json)
Çıktı:  skor/{tarih}.json — her maç için bileşenler ve rozet

Formül dokümanı: overnight-deger-skoru-v2-1.md. Bu dosya o dokümanı
birebir uygular; buradaki değişkenler dokümandaki S/K/T/D/Y/F/G/A
isimleriyle bire bir eşleşiyor.

Kabul testi 2 Ocak 2026 (bkz. 00-BASLA-BURADAN.md): rozetlerin ondalığı
değil SIRALAMASI tutmalı. Dokümandaki bileşen puanları elle takdirdi;
burada veriden hesaplanıyor.

--- Bilerek basitleştirilen / eksik bırakılan yerler ---

1. **S bileşeni, clutch ağırlığını sadece SAYIYA uyguluyor.** Formül
   dokümanı "son 5 dakikada fark ≤5 iken üretilen sayı, asist ve top
   çalma ×1.5 sayılır" diyor. Play-by-play'de asist ve top çalma sadece
   serbest metin açıklamasında geçiyor ("Bridges Layup (Miller 1 AST)"),
   yapılandırılmış bir personId alanı yok — isimden oyuncuya eşleme
   yapmak (aynı soyadlı iki oyuncu ihtimali dahil) kırılgan olurdu. Sayı
   için bu sorun yok çünkü sayıyı üreten oyuncunun personId'si doğrudan
   olayın kendisinde. Asist/top çalma clutch ağırlığı eklenmedi.

2. **T (tarihilik) neredeyse her zaman 0.** Gerçek T, kariyer/franchise/
   lig rekoru geçmişine bakmayı gerektiriyor — elimizde o veritabanı yok.
   Sadece 50+ sayı gibi tek geceden anlaşılabilen bir eşiği T=6 sayıyoruz;
   gerisi editoryal kaldıraçla (bkz. formül dokümanı bölüm 6) elle
   eklenmeli. 2 Ocak gecesinin kalibrasyon tablosunda zaten hiçbir maçta
   T bileşeni yok — bu basitleştirme o geceyi etkilemiyor.

3. **A bileşeninin "takım kalitesi" yarısı** artık `config/takim_beklenti.json`
   ile karışıyor — `n/(n+20)` ağırlığıyla (n = takımın hedef geceden önce
   oynadığı maç sayısı) bu sezonun sayı averaj farkı ile sezon öncesi
   beklenti harmanlanıyor: n küçükken (sezon başı) beklenti baskın, n
   büyüdükçe bu sezonun gerçek verisi baskın olur. Gerçek bahis galibiyet
   hedefleri bulunamadı (bu ortamda canlı bahis-oranı verisine erişim
   yok) — KULLANICI KARARIYLA fallback olarak 2024-25 sezonu NET_RATING'i
   kullanıldı (kaynak: `config/takim_beklenti.json` içinde belgeli).
   Gerçek üretim bug'ı (2025-10-22, sezonun 2. gecesi): bu harman
   YOKKEN beş maç TAM OLARAK aynı rozeti (8.96) almıştı — n çok küçükken
   (1-2 maç) tüm takımların bu-sezon averajı gürültüden ayırt edilemez
   kalıyor, sonuç formül her takıma aynı "kalite puanı"nı veriyordu.

4. **A bileşeninin "sahadaki yıldız ağırlığı" yarısı**,
   `config/yildizlar.json`'da o takıma atanmış oyunculara bakıp
   oynayıp oynamadığını kontrol ediyor. Liste bugün BOŞ (kullanıcı
   dolduracak) — o yüzden bu terim şu an her maçta nötr (5.0) sabit
   dönüyor ve maçlar arası SIRALAMAYI etkilemiyor. Liste doldurulduğunda
   kod değişmeden çalışmaya başlayacak.

5. **Kadro dışı → A bağlantısı.** Bir yıldız o takımda box score'da hiç
   görünmüyorsa (kadro dışı, ne DNP ne DND — tamamen yok) veya DNP/DND
   ise "oynamadı" sayılır ve o takımın yıldız ağırlığından düşer. Ama bu
   da yildizlar.json boşken devre dışı — bkz. madde 4.
"""

import json
import math
import unicodedata
from datetime import datetime
from pathlib import Path

from gercekler import clock_saniye, periyot_sonu_skorlari, KONFERANS, _dogru_oyuncu_adi, gmsc

HAM_DIZIN = Path(__file__).parent / "ham"
SKOR_DIZIN = Path(__file__).parent / "skor"
CONFIG_DIZIN = Path(__file__).parent / "config"

KADEME_KATSAYI = {1: 1.20, 2: 1.08, 3: 0.95, 4: 0.80}
KADEME_AGIRLIK_A = {1: 10, 2: 7, 3: 4, 4: 2}  # A bileşeninde "yıldız ağırlığı" ölçeği


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _katla(ad):
    """Aksan/büyük-küçük harf farklarını yutan karşılaştırma anahtarı
    ('Dončić' == 'doncic') — kalip_secici.yildiz_kademesi ile aynı yöntem."""
    return "".join(c for c in unicodedata.normalize("NFKD", ad) if not unicodedata.combining(c)).lower()


def yildizlar_yukle():
    """DİKKAT: config/yildizlar.json numeric NBA personId İLE DEĞİL, ad+takım
    ile tutuluyor (kullanıcının verdiği gerçek şema). Bu fonksiyon eskiden
    `o["id"]` bekliyordu — dosyada hiç var olmayan bir alan, dolayısıyla
    hesapla.py 2026-01-02 dışındaki HİÇBİR tarihte (skor'u zaten önceden
    hesaplanmış olmayan) çalışmıyordu (gerçek üretim bug'ı — 2026-01-17/
    01-24 için ilk kez çalıştırılınca KeyError: 'id' ile ortaya çıktı).
    Artık kalip_secici.yildizlar_yukle ile aynı ad-katlama yöntemini
    kullanıyor, ama TAKIM bilgisini de taşıyor (A_hesapla için gerekli)."""
    dosya = CONFIG_DIZIN / "yildizlar.json"
    if not dosya.exists():
        return {}
    ham = json.loads(dosya.read_text())
    return {
        _katla(o["ad"]): {"ad": o["ad"], "takim": o["takim"], "kademe": min(o["kuresel"], o["turkiye"])}
        for o in ham.get("oyuncular", [])
    }


def kademe_bul(yildizlar, oyuncu_adi):
    kayit = yildizlar.get(_katla(oyuncu_adi))
    return kayit["kademe"] if kayit else 3  # listede yoksa "tanınan" varsayılan kademe


# ---------------------------------------------------------------------------
# Lig geneli GmSc dağılımı ve kişisel taban (PlayerGameLogs'tan)
# ---------------------------------------------------------------------------


def lig_gmsc_dagilimi_ve_kisisel_taban(oyuncu_ortalama_ham):
    """İki farklı dağılım döner:

    1. `mac_en_iyileri` — HER MAÇIN en iyi GmSc'si (573 maç ~ 573 sayı).
       S'nin "lig geneli yüzdelik" terimi buna karşı ölçülüyor. İlk
       denemede bunun yerine TÜM oyuncu-geceleri kullanılmıştı (~13 bin
       satır) — o dağılımın medyanı çok düşük (bench/DNP-yakını
       performanslarla dolu) olduğu için sıradan bir 30 sayılık gece bile
       %97+ yüzdelikte çıkıyor, S'yi doygunlaştırıyordu. Doğru soru "bu
       maçın en iyisi, DİĞER MAÇLARIN EN İYİLERİNE göre nerede duruyor" —
       20 sayılık bir maç-en-iyisi bu dağılımda gerçekten dipte kalıyor.
    2. `kisisel` — oyuncu başına GmSc geçmişi (kişisel z-skor için,
       değişmedi)."""
    rows = oyuncu_ortalama_ham["resultSets"][0]["rowSet"]
    headers = oyuncu_ortalama_ham["resultSets"][0]["headers"]
    idx = {h: i for i, h in enumerate(headers)}

    kisisel = {}  # player_id -> [gmsc, gmsc, ...]
    mac_en_iyisi = {}  # game_id -> en yüksek gmsc
    for r in rows:
        s = {
            "points": r[idx["PTS"]],
            "fieldGoalsMade": r[idx["FGM"]],
            "fieldGoalsAttempted": r[idx["FGA"]],
            "freeThrowsAttempted": r[idx["FTA"]],
            "freeThrowsMade": r[idx["FTM"]],
            "reboundsOffensive": r[idx["OREB"]],
            "reboundsDefensive": r[idx["DREB"]],
            "steals": r[idx["STL"]],
            "assists": r[idx["AST"]],
            "blocks": r[idx["BLK"]],
            "foulsPersonal": r[idx["PF"]],
            "turnovers": r[idx["TOV"]],
        }
        g = gmsc(s)
        kisisel.setdefault(r[idx["PLAYER_ID"]], []).append(g)
        gid = r[idx["GAME_ID"]]
        if g > mac_en_iyisi.get(gid, -999):
            mac_en_iyisi[gid] = g

    mac_en_iyileri = sorted(mac_en_iyisi.values())
    return mac_en_iyileri, kisisel


def yuzdelik(sirali_liste, deger):
    if not sirali_liste:
        return 0.5
    import bisect

    konum = bisect.bisect_left(sirali_liste, deger)
    return konum / len(sirali_liste)


# S bileşeninin GmSc'den 0-10'a taşıdığı yer burası. İki denemede iki
# farklı hata yaptım:
#   1) Düz "yüzdelik × 10": her iyi gece (30+ sayı) 9'un üstüne çıktı,
#      30 sayılık gece ile 55 sayılık gece ayrılamadı.
#   2) z-skoru + ortalamanın altını sıfırlamak: bu sefer sıfır noktası
#      "maç-en-iyileri dağılımının ORTALAMASI" oldu (26.4 GmSc) — ama o
#      ortalama zaten iyi bir gece demek, yani maç-en-iyilerinin YARISI
#      otomatik sıfır aldı (Dončić'in 34'ü S=0.18 çıktı).
#
# Doğrusu: gerçek 573 maçlık dağılımın YÜZDELİK ÇAPALARINA S değerlerini
# elle iğnelemek (kullanıcının verdiği tablo) ve aralarda doğrusal
# enterpolasyon yapmak. Alt uç (p0) sıfır değil ~0.3 — dip nefes alsın.
# Üst uç (p99.5 üstü) asimptotik olarak 10'a yaklaşır, hiç ulaşmaz —
# bu kısmı ilk denemeden aynen koruyoruz, o doğruydu.
LIG_CAPALAR = [
    (0.00, 0.3),
    (0.05, 1.0),
    (0.25, 3.0),
    (0.50, 4.5),
    (0.75, 6.0),
    (0.95, 8.0),
    (0.995, 9.5),
]


def lig_capa_degeri(deger, sirali_liste):
    """Değerin sırali_liste içindeki yüzdeliğini bulur, LIG_CAPALAR
    üzerinden 0-10'a enterpole eder. (skor, yüzdelik) döner."""
    pct = yuzdelik(sirali_liste, deger)

    if pct >= LIG_CAPALAR[-1][0]:
        # p99.5 üstü: asimptotik yaklaşım, değerin kendisini kullan
        # (yüzdelik burada artık ayırt edici değil — örneklemin en
        # üstündeki tek bir maç bile p99.8 okuyabilir).
        esik_deger = sirali_liste[min(int(len(sirali_liste) * 0.995), len(sirali_liste) - 1)]
        ekstra = max(deger - esik_deger, 0)
        return 9.5 + 0.5 * (1 - math.exp(-ekstra / 8)), pct

    for (p1, s1), (p2, s2) in zip(LIG_CAPALAR, LIG_CAPALAR[1:]):
        if p1 <= pct <= p2:
            t = (pct - p1) / (p2 - p1) if p2 > p1 else 0
            return s1 + t * (s2 - s1), pct

    return LIG_CAPALAR[0][1], pct


def kisisel_z_skoru(kisisel_gecmis, deger, lig_ortalama, lig_std):
    """Bulunan hata: az dakikalı, düşük varyanslı bir yedek oyuncu
    (örn. her gece 0-4 GmSc civarında oynayan biri) sıradan iyi bir
    gecede bile KENDİ dar dağılımına göre devasa bir z-skoru üretiyordu
    — 13 sayılık verimli bir gece, kendi ortalamasına göre "tarihi"
    görünüyordu ve Jamal Murray'nin 34 sayılık gecesini S'te geçti.
    Bu tam olarak formül dokümanının kendi örneğinin uyardığı hata
    ("Simons'ın 30'u... formül onu daha yukarı koyardı — tam tersi
    doğru"). Çare orada Y★'ye bırakılmış ama Y★ sadece BİLİNEN yıldızları
    düzeltiyor, az dakikalı/düşük varyanslı OYUNCULARIN varyans
    küçüklüğünden doğan bu spesifik çarpıtmayı değil.

    Buradaki düzeltme: kişisel varyansı, örneklem küçükse lig varyansına
    doğru çeken bir Bayesçi küçültme (n arttıkça kişisel varyans daha
    çok ağırlık kazanır, ama hiçbir zaman lig varyansının bir payını
    tamamen silmez — PRIOR_GUC sabiti bu payı belirliyor)."""
    PRIOR_GUC = 15
    n = len(kisisel_gecmis)
    lig_var = lig_std**2
    if n == 0:
        ortalama, var = lig_ortalama, lig_var
    else:
        ort_kisisel = sum(kisisel_gecmis) / n
        if n >= 2:
            var_kisisel = sum((x - ort_kisisel) ** 2 for x in kisisel_gecmis) / (n - 1)
        else:
            var_kisisel = lig_var
        var = (n * var_kisisel + PRIOR_GUC * lig_var) / (n + PRIOR_GUC)
        agirlik_ort = n / (n + 10)
        ortalama = agirlik_ort * ort_kisisel + (1 - agirlik_ort) * lig_ortalama
    std = math.sqrt(var) if var > 0 else 1.0
    return (deger - ortalama) / std


# ---------------------------------------------------------------------------
# S — Yıldız gecesi (oyuncu başına, maçın S'i = en yüksek oyuncu S'i)
# ---------------------------------------------------------------------------


def oyuncu_klutch_sayisi(actions, person_id, son_periyot):
    """Son periyotta (uzatma dahil), kalan süre <=5dk VE o anki fark <=5
    iken bu oyuncunun ürettiği sayı toplamı."""
    toplam = 0
    son_ev, son_dep = 0, 0
    for a in actions:
        if a["scoreHome"] != "" and a["scoreAway"] != "":
            son_ev, son_dep = int(a["scoreHome"]), int(a["scoreAway"])
        if a["period"] != son_periyot:
            continue
        if a.get("personId") != person_id:
            continue
        saniye_kalan = clock_saniye(a["clock"])
        if saniye_kalan > 300:
            continue
        if abs(son_ev - son_dep) > 5:
            continue
        if a["actionType"] == "Made Shot" and a.get("shotResult") == "Made":
            toplam += a["shotValue"]
        elif a["actionType"] == "Free Throw" and "MISS" not in a["description"]:
            toplam += 1
    return toplam


def esik_bonusu(s):
    bonus = 0.0
    if s["points"] >= 50:
        bonus += 0.5
    if sum(1 for v in (s["points"], s["reboundsTotal"], s["assists"], s["steals"], s["blocks"]) if v >= 10) >= 3:
        bonus += 0.5
    if s["reboundsTotal"] >= 20:
        bonus += 0.5
    if s["threePointersMade"] >= 10:
        bonus += 0.5
    if s["blocks"] >= 5:
        bonus += 0.5
    return min(bonus, 1.5)


def S_hesapla(bt, actions, son_periyot, lig_gmsc_sirali, kisisel_gmsc, yildizlar):
    """Hata bulundu: önceki sürüm her oyuncu için tam S'i hesaplayıp
    ARGMAX alıyordu ("kim en yüksek S alıyor"). Bu, az dakikalı/düşük
    varyanslı bir oyuncunun kişisel z-skorunun (varyans küçüklüğü
    yüzünden) şişip seçimi ele geçirmesine izin veriyordu — CHA–MIL'de
    Giannis'in 30/10'u yerine bir yedeğin 8 sayısı "maçın en iyisi"
    seçildi. Doğrusu: önce OBJEKTİF olarak maçın en iyi performansını
    (en yüksek clutch-ağırlıklı GmSc) bul, S'i SADECE o oyuncu için
    hesapla. Kişisel sapma hâlâ o oyuncunun S'ini yukarı/aşağı çekebilir
    — ama HANGİ oyuncunun temsil ettiğini artık belirleyemez."""
    lig_ort = sum(lig_gmsc_sirali) / len(lig_gmsc_sirali)
    lig_var = sum((x - lig_ort) ** 2 for x in lig_gmsc_sirali) / max(len(lig_gmsc_sirali) - 1, 1)
    lig_std = math.sqrt(lig_var) if lig_var > 0 else 1.0

    # Seçim ölçütü de Y★ kademesiyle ağırlıklı — yoksa bilinen bir
    # yıldızın çok-iyi-ama-en-verimli-değil gecesi, verimlilikte onu
    # geçen tanınmayan bir oyuncuya seçimi kaptırabilir. `yildizlar.json`
    # boşken bu ağırlık her oyuncu için aynı (0.95) olduğundan etkisiz —
    # doldurulunca devreye girer.
    en_iyi_agirlikli = None
    en_iyi_gmsc = None
    en_iyi_oyuncu_p = None
    for taraf in ("homeTeam", "awayTeam"):
        for p in bt[taraf]["players"]:
            if not p["statistics"]["minutes"]:
                continue
            clutch_sayi = oyuncu_klutch_sayisi(actions, p["personId"], son_periyot)
            gmsc_plus = gmsc(p["statistics"]) + 0.5 * clutch_sayi
            oyuncu_adi = f"{p['firstName']} {p['familyName']}"
            agirlikli = gmsc_plus * KADEME_KATSAYI[kademe_bul(yildizlar, oyuncu_adi)]
            if en_iyi_agirlikli is None or agirlikli > en_iyi_agirlikli:
                en_iyi_agirlikli = agirlikli
                en_iyi_gmsc = gmsc_plus
                en_iyi_oyuncu_p = p

    if en_iyi_oyuncu_p is None:
        return 0.0, None

    p = en_iyi_oyuncu_p
    s = p["statistics"]

    # Lig-çapalı taban: dağılımın gerçek yüzdeliklerine oturmuş, ölçüsü
    # önceden belli bir değer (bkz. LIG_CAPALAR).
    lig_deger, lig_pct = lig_capa_degeri(en_iyi_gmsc, lig_gmsc_sirali)

    # Kişisel sapma artık AYRI bir yüzdelik değil, lig-çapalı değeri
    # ±1.5 bandında düzelten bir terim — tanh ile bu bandın dışına
    # asla taşmıyor (ne kadar uç bir kişisel sapma olursa olsun).
    kisisel_z = kisisel_z_skoru(kisisel_gmsc.get(p["personId"], []), en_iyi_gmsc, lig_ort, lig_std)
    kisisel_duzeltme = 1.5 * math.tanh(kisisel_z / 2)

    bonus = esik_bonusu(s)

    s_ham = lig_deger + kisisel_duzeltme + bonus

    kademe = kademe_bul(yildizlar, f"{p['firstName']} {p['familyName']}")
    katsayi = KADEME_KATSAYI[kademe]
    if lig_pct >= 0.99:
        katsayi = max(katsayi, 1.00)  # elit performansta ceza kalkar

    s_final = min(max(s_ham * katsayi, 0), 10)
    # NOT: en_iyi_oyuncu burada sadece BU MAÇIN S bileşenini taşıyan
    # performans — "Gecenin Beşi" (gece/{tarih}.json) bambaşka, ayrı
    # bir liste ve derle.py'de GECE ÇAPINDA (tüm maçların oyuncuları
    # arasında) GmSc'ye göre kurulmalı, maç rozetine göre DEĞİL. 2 Ocak
    # 2026'da Avdija'nın 34/11/7'si (GmSc 32.6) Zion'un 35 sayısından
    # (GmSc 29.6) daha iyiydi ve maçını sadece 2. sıraya taşıdı — ama
    # Gecenin Beşi'nde 1. sırada olması gereken oydu. Bu ikisini
    # karıştırmak (maç rozetine göre oyuncu sıralamak) yanlış bir
    # listeye yol açar.
    # Aksan-düzeltilmiş ad kullanılmalı (bkz. gercekler._dogru_oyuncu_adi)
    # — gerçek üretim bug'ı: burası düzeltilmeden ASCII ad ("Alperen
    # Sengun") skor.json'a "en_iyi_performans" olarak yazılıyordu, ama
    # gercekler.py'deki oyuncu_stat kaydı zaten düzeltilmiş adı
    # ("Alperen Şengün") taşıyor — T14 ikisini metinde ARADIĞI için
    # (üretilen metin düzeltilmiş adı kullanıyor) hiçbir zaman eşleşmiyor,
    # Şengün en iyi performans olduğu HER maçta T14 sahte-pozitif reddi
    # veriyordu.
    return round(s_final, 2), _dogru_oyuncu_adi(p["personId"], f"{p['firstName']} {p['familyName']}")


# ---------------------------------------------------------------------------
# K — Kader / bahis (standings yakınlığı × ay katsayısı)
# ---------------------------------------------------------------------------

AY_KATSAYISI = {10: 0.20, 11: 0.30, 12: 0.45, 1: 0.60, 2: 0.70, 3: 0.85, 4: 1.00}


# Kullanıcı düzeltmesi: K sadece maç ÖNCESİ beklentiyi (standings
# yakınlığı) ölçüyordu — bir SONUCUN kendisinin ne kadar sarsıcı
# olduğunu ölçen hiçbir bileşen yoktu. Somut örnek: lig lideri OKC
# (26-5), 8 maçlık galibiyet serisi süren SAS'a Noel gecesi kaybetti —
# maç öncesi "kader" açısından sıradan (iki takım da farklı konferans
# bantlarında değil, play-in/playoff hattı yakınlığı yok), ama SONUÇ
# ligin o haftaki en önemli haberlerinden biriydi. K'ya sürpriz sonuç
# katkısı eklendi — üç bağımsız tetikleyici, biri bile yeterli:
#   1. kaybeden lig lideri (+5) ya da konferansta ilk 3'te (+3)
#   2. belirgin kalite farkında ALT takımın galibiyeti (kalite farkına
#      orantılı, en fazla +4) — takim_kalite_puani (0-10) A bileşeniyle
#      AYNI kaynak, iki ayrı kalite tanımı olmasın diye.
#   3. konferansta ilk 3'teki iki takımın karşılaşması (+2)
# Katkılar TOPLANIR (üçü birden tetiklenebilir) ama K yine de 10 ile
# sınırlı. Ay katsayısıyla ÇARPILMAZ (K taşıyıcısının geri kalanının
# aksine) — bir sonucun sarsıcılığı takvime göre küçülmez, Ekim'de
# lig liderinin kaybı da Nisan'daki kadar haber değeri taşır.
def surpriz_katkisi_hesapla(kazanan_kod, kaybeden_kod, puan_durumu, kalite_ort, kalite_sirali):
    """Ağırlıklar kalibre edildi (kullanıcı hedefi: OKC'nin — lig
    lideri, 26-5 — Noel gecesi SAS'a kaybı 6-7 rozet bandına gelsin).
    İlk deneme (+5/+3/+4/+2) K'yı 8.6'ya, rozeti 8.57'ye (mutlaka
    katmanına, İKİ maçın daha bulunduğu bir gecede ÜÇÜNCÜ "mutlaka"
    maça) taşımıştı — aşırı tepkiydi. Ayrıca formülün "zirve sönümlemesi"
    (bkz. formulu_uygula) SADECE C1 (en büyük taşıyıcı) S ya da T iken
    devreye giriyor — K hiç sönümlenmiyor, bu yüzden K'ya S/T'den DAHA
    TEDBİRLİ ağırlıklar vermek gerekiyor.

    Kullanıcı düzeltmesi (2. tur): "sürpriz" ve "zirve maçı" AYRI
    kavramlar, tek katkıda karıştırılmamalı. Eski sürüm "kaybeden lig
    lideri" ve "ikisi de ilk-3" tetikleyicilerini de "sürpriz" başlığı
    altında topluyordu — ama San Antonio (Batı'nın en iyilerinden biri,
    kalite 7.0) OKC'yi (lig lideri) yendiğinde bu SÜRPRİZ değil, iki üst
    takımın maçı. Artık iki ayrı fonksiyon: sürpriz SADECE gerçek bir
    kalite farkı varken (kalip_secici._surpriz_sonuc_belirle ile AYNI
    eşik/mantık), zirve SADECE ikisi de ilk-3'teyken tetikleniyor."""
    kazanan_kalite = takim_kalite_puani(kazanan_kod, kalite_ort, kalite_sirali)
    kaybeden_kalite = takim_kalite_puani(kaybeden_kod, kalite_ort, kalite_sirali)

    katki = 0.0
    # Sürpriz — SADECE belirgin bir kalite farkı varsa (aynı eşik:
    # kaybeden İYİ, kazanan KÖTÜ). Ungated bir "her pozitif farkta
    # orantılı katkı" ilk denemede San Antonio-OKC'yi yanlışlıkla
    # "sürpriz" sayıyordu (SAS kalite 7.0, KOTU eşiğinin (3.0) çok
    # üstünde — belirgin kalite farkı YOK).
    if kaybeden_kalite >= IYI_TAKIM_ESIGI and kazanan_kalite <= KOTU_TAKIM_ESIGI:
        kalite_farki = kaybeden_kalite - kazanan_kalite
        katki += 2.0 + min(2.0, kalite_farki * 0.4)

    kaz_sira = (puan_durumu.get(kazanan_kod) or {}).get("konferans_sira")
    kay_sira = (puan_durumu.get(kaybeden_kod) or {}).get("konferans_sira")
    if kaz_sira is not None and kay_sira is not None and kaz_sira <= 3 and kay_sira <= 3:
        katki += max(0.0, 7.0 - (kaz_sira + kay_sira) * 0.5)

    return min(katki, 10.0)


def K_hesapla(ev_kod, dep_kod, puan_durumu, ay, kazanan_kod=None, kaybeden_kod=None, kalite_ort=None, kalite_sirali=None):
    """İlk denemede sıralama POZİSYONUNA (6./10. sıraya kaç sıra
    uzaklıkta) bakıyordum. Sorun: sezonun ortasında sıralama henüz
    bunca az maçla sıkışık durur, sırf 10. sırada olmak (kim işgal
    ederse etsin) maksimum puan veriyordu — Brooklyn–Washington gibi
    ligin dibindeki bir maç bile bir taraf tesadüfen hatta yakın
    sıradaysa K=0'dan uzaklaşıyordu.

    Bunun yerine kazanma YÜZDESİ farkını 82 maçlık sezona yayıp
    "bu tempo sürerse kaç maç geride/önde biteceğiz" sorusuna
    çeviriyoruz. Bu, erken sezonda bile gerçek bir ayrım üretiyor:
    Brooklyn ve Washington'ın kazanma yüzdesi, hattaki takımdan
    tempoya vurulduğunda 13-16 maç eşdeğeri geride — sıra farkı
    küçük görünse bile. Doğrusal düşüş 8 maç eşdeğerinde sıfıra
    iniyor, yani "8+ maç geride" sınırı ayrı bir dallanma değil,
    bu eğrinin doğal sıfır noktası."""
    ay_k = AY_KATSAYISI.get(ay, 0.5)

    konferanslar = {}
    for kayit in puan_durumu.values():
        konferanslar.setdefault(kayit["konferans"], []).append(kayit)
    for liste in konferanslar.values():
        liste.sort(key=lambda k: k["konferans_sira"])

    def hat_yuzdeleri(konferans):
        liste = konferanslar.get(konferans, [])
        playoff = liste[5]["kazanma_yuzdesi"] if len(liste) > 5 else None
        playin = liste[9]["kazanma_yuzdesi"] if len(liste) > 9 else None
        return playoff, playin

    def yakinlik_puani(kod):
        kayit = puan_durumu.get(kod)
        if not kayit:
            return 0
        playoff_yzd, playin_yzd = hat_yuzdeleri(kayit["konferans"])
        adaylar = [abs(kayit["kazanma_yuzdesi"] - y) for y in (playoff_yzd, playin_yzd) if y is not None]
        if not adaylar:
            return 0
        gap_mac_esdegeri = min(adaylar) * 82
        return max(0, 10 - gap_mac_esdegeri * 1.25)

    # Ortalama, MAX değil: "kader" maçı iki takımın da bir şey için
    # oynamasıdır. Sadece bir taraf hattın üstündeyken öbür taraf
    # yarış dışıysa, tek taraf hatta yakın diye maç yüksek K almamalı.
    taban = (yakinlik_puani(ev_kod) + yakinlik_puani(dep_kod)) / 2
    K = taban * ay_k

    if kazanan_kod and kaybeden_kod and kalite_ort is not None and kalite_sirali is not None:
        K += surpriz_katkisi_hesapla(kazanan_kod, kaybeden_kod, puan_durumu, kalite_ort, kalite_sirali)

    return round(min(K, 10), 2)


# ---------------------------------------------------------------------------
# T — Tarihilik (bkz. modül başındaki not — kasıtlı olarak sınırlı)
# ---------------------------------------------------------------------------


def T_hesapla(bt):
    en_yuksek = 0
    for taraf in ("homeTeam", "awayTeam"):
        for p in bt[taraf]["players"]:
            if p["statistics"]["points"] >= 50:
                en_yuksek = max(en_yuksek, 6)
    return en_yuksek


# ---------------------------------------------------------------------------
# Y — Yakınlık (maç boyu)
# ---------------------------------------------------------------------------


def skor_serisi(actions):
    seri = []
    for a in actions:
        if a["scoreHome"] == "" or a["scoreAway"] == "":
            continue
        seri.append((a["period"], clock_saniye(a["clock"]), int(a["scoreHome"]), int(a["scoreAway"])))
    return seri


def elapsed_saniye(periyot, saniye_kalan):
    """Periyot + kalan saniyeyi, maç başından beri geçen toplam saniyeye
    çevirir. Normal periyot 720sn (12dk), uzatma 300sn (5dk)."""
    if periyot <= 4:
        return (periyot - 1) * 720 + (720 - saniye_kalan)
    return 4 * 720 + (periyot - 5) * 300 + (300 - saniye_kalan)


def Y_hesapla(seri, son_periyot, uzatma_var):
    """İlk denemede Y, çapa tablosundaki 6 basamağa (0,2,4,6,8,10)
    yuvarlanıyordu — sonuç, profili tamamen farklı dört maçın (baştan
    sona gerilimli bir maç ile son çeyreğe 8 farkla giren bir maç) aynı
    Y'yi almasıydı. Çapa tablosu ölçeği ANLATMAK içindi, hesap kuralı
    değildi.

    Bunun yerine maç boyunca farkı zaman ağırlıklı olarak entegre
    ediyoruz: her an için bir "yakınlık" değeri (fark küçüldükçe 1'e
    yaklaşan, büyüdükçe sönümlenen bir eğri) hesaplanıyor, ve bu değer
    maçın SONUNA yakın anlara çok daha fazla ağırlık verilerek
    ortalanıyor — tıpkı çapa tablosunun "son 5 dakika", "son çeyrek"
    diye iç içe pencereler tarif etmesi gibi, ama basamaksız."""
    if not seri:
        return 0.0

    toplam_sure = elapsed_saniye(*_son_nokta_konumu(seri))

    agirlikli_toplam = 0.0
    agirlik_toplami = 0.0
    for i in range(len(seri) - 1):
        periyot, saniye, ev, dep = seri[i]
        periyot2, saniye2, _, _ = seri[i + 1]
        t1 = elapsed_saniye(periyot, saniye)
        t2 = elapsed_saniye(periyot2, saniye2)
        sure = max(t2 - t1, 0)
        if sure == 0:
            continue
        fraksiyon = t1 / toplam_sure if toplam_sure else 0
        agirlik = fraksiyon ** 4
        yakinlik = math.exp(-abs(ev - dep) / 8)
        agirlikli_toplam += yakinlik * agirlik * sure
        agirlik_toplami += agirlik * sure

    y = 10 * (agirlikli_toplam / agirlik_toplami) if agirlik_toplami else 0.0

    if uzatma_var:
        y = max(y, 9.5)  # uzatmaya kalan maç zaten tanım gereği son anda çok yakındı

    return round(min(max(y, 0), 10), 2)


def _son_nokta_konumu(seri):
    periyot, saniye, _, _ = seri[-1]
    return periyot, saniye


# ---------------------------------------------------------------------------
# F — Final dramı
# ---------------------------------------------------------------------------


def F_hesapla(seri, son_periyot, uzatma_var):
    """Anchor tablosundaki "F=10: son saniye galibiyet basketi" ve
    "F=8: son 30 saniyede öne geçme" kelimenin tam anlamıyla bir OLAY
    gerektiriyor — sadece o an farkın küçük olması yetmez (maç zaten
    kazanılmışken atılan serbest atışlar da farkı küçük gösterebilir).
    Bu yüzden burada gerçek lider değişimi / eşitlenme anlarını
    (işaret değişimi) arıyoruz, tek bir anlık farkı değil."""
    son = [x for x in seri if x[0] == son_periyot]
    if not son:
        return 0

    degisim_anlari = []  # (saniye_kalan, yeni_fark)
    onceki_fark = None
    for _, saniye, ev, dep in son:
        yeni_fark = ev - dep
        if onceki_fark is not None:
            onceki_isaret = (onceki_fark > 0) - (onceki_fark < 0)
            yeni_isaret = (yeni_fark > 0) - (yeni_fark < 0)
            if onceki_isaret != yeni_isaret:
                degisim_anlari.append((saniye, yeni_fark))
        onceki_fark = yeni_fark

    if any(saniye <= 10 for saniye, _ in degisim_anlari):
        return 10  # son 10 saniyede lider değişti veya eşitlendi (uzatma dahil)

    if any(saniye <= 30 for saniye, _ in degisim_anlari):
        return 8  # son 30 saniyede öne geçildi

    son_1dk = [x for x in son if x[1] <= 60]
    if son_1dk and min(abs(e - d) for _, _, e, d in son_1dk) <= 3:
        return 6

    son_2dk = [x for x in son if x[1] <= 120]
    if son_2dk and min(abs(e - d) for _, _, e, d in son_2dk) <= 5:
        return 3

    return 0


# ---------------------------------------------------------------------------
# G — Geri dönüş
# ---------------------------------------------------------------------------


def G_hesapla(seri, kazanan_ev_mi):
    """İki düzeltme: (1) 10 sayının altındaki hiçbir açık "geri dönüş"
    sayılmıyor — Portland'ın ilk çeyrekte gördüğü 8 sayılık açık maçın
    normal seyriydi, geri dönüş değildi. (2) İlk yarıda (1-2. periyot)
    kapatılan açık yarı ağırlıkla sayılıyor — 1. çeyrekte 10 açığı
    kapatmakla son çeyrekte 10 açığı kapatmak aynı hikâye değil."""
    if not seri:
        return 0

    def agirlik(periyot):
        return 0.5 if periyot <= 2 else 1.0

    kazanan_en_kotu_agirlikli = 0  # kazananın gördüğü en büyük (ağırlıklı) açık
    kaybeden_en_iyi_toparlanma_agirlikli = 0

    for periyot, _, ev, dep in seri:
        fark = (ev - dep) if kazanan_ev_mi else (dep - ev)
        agirlikli_fark = fark * agirlik(periyot) if fark < 0 else fark
        if agirlikli_fark < kazanan_en_kotu_agirlikli:
            kazanan_en_kotu_agirlikli = agirlikli_fark
        agirlikli_toparlanma = -fark * agirlik(periyot) if -fark > 0 else -fark
        if agirlikli_toparlanma > kaybeden_en_iyi_toparlanma_agirlikli:
            kaybeden_en_iyi_toparlanma_agirlikli = agirlikli_toparlanma

    kazanan_acik = abs(kazanan_en_kotu_agirlikli)

    if kazanan_acik >= 20:
        return 10
    if kazanan_acik >= 15:
        return 8
    if kazanan_acik >= 10:
        return 6
    if kaybeden_en_iyi_toparlanma_agirlikli >= 20:
        return 6
    if kaybeden_en_iyi_toparlanma_agirlikli >= 10:
        return 3
    return 0


# ---------------------------------------------------------------------------
# A — Çekicilik
# ---------------------------------------------------------------------------


def takim_beklentisi_yukle():
    dosya = CONFIG_DIZIN / "takim_beklenti.json"
    if not dosya.exists():
        return {}
    return json.loads(dosya.read_text()).get("net_rating", {})


# n/(n+20) harmanında n bu değere ulaşınca beklenti payı ~1/3'e iner,
# n~60'a (sezonun ~3/4'ü) ulaşınca ~1/4'ün altına düşer — formül
# dokümanındaki "erken sezonda beklenti baskın, sezon ilerledikçe bu
# sezonun verisi baskın" tarifiyle eşleşen standart bir yumuşatma sabiti.
BEKLENTI_YUMUSATMA_N = 20


def takim_kalitesi_hesapla(oyun_gunlugu_ham, tarih_str):
    """Takım başına sayı averaj farkı — HEDEF GECEDEN ÖNCEKİ maçlarla,
    sezon öncesi beklentiyle (config/takim_beklenti.json) n/(n+20)
    ağırlığında harmanlanmış. Bu gecenin kendi sonucunu dışarıda
    bırakıyoruz, yoksa "takım kalitesi" kısmen bu gecenin sonucundan
    hesaplanmış olur (döngüsellik).

    Gerçek üretim bug'ı (2025-10-22, sezonun 2. gecesi): harman YOKKEN
    o gece oynayan takımların çoğu bu sezon HİÇ maç oynamamıştı (n=0),
    "kod not in ortalamalar" durumunda A_hesapla sabit 5.0 nötr puan
    veriyordu — sonuç beş farklı maç TAM OLARAK aynı rozeti (8.96) aldı.
    Artık n=0 olan bir takım nötr değil, GERÇEK sezon öncesi beklentisini
    (net rating) alıyor — takımlar arası ayrım sezon başında da kalıyor."""
    beklenti = takim_beklentisi_yukle()

    rows = oyun_gunlugu_ham["resultSets"][0]["rowSet"]
    headers = oyun_gunlugu_ham["resultSets"][0]["headers"]
    idx = {h: i for i, h in enumerate(headers)}

    farklar = {}
    for r in rows:
        if r[idx["GAME_DATE"]][:10] == tarih_str:
            continue
        kod = r[idx["TEAM_ABBREVIATION"]]
        farklar.setdefault(kod, []).append(r[idx["PLUS_MINUS"]])

    tum_kodlar = set(farklar) | set(beklenti)
    ortalamalar = {}
    for kod in tum_kodlar:
        oyunlar = farklar.get(kod, [])
        n = len(oyunlar)
        bu_sezon_ort = sum(oyunlar) / n if n else 0.0
        beklenti_deger = beklenti.get(kod, bu_sezon_ort if n else 0.0)
        agirlik = n / (n + BEKLENTI_YUMUSATMA_N)
        ortalamalar[kod] = agirlik * bu_sezon_ort + (1 - agirlik) * beklenti_deger

    sirali = sorted(ortalamalar.values())
    return ortalamalar, sirali


# "İyi"/"kötü" takım eşikleri — A bileşeni, K'daki sürpriz katkısı VE
# kalip_secici'nin sürpriz/zirve/seri-haber-değeri seçimi hep BU İKİ
# SABİTE bakar (kullanıcı kararı: iki ayrı kalite tanımı olmasın).
IYI_TAKIM_ESIGI = 7.0
KOTU_TAKIM_ESIGI = 3.0


def takim_kalite_puani(kod, ortalamalar, sirali):
    """0-10, geceden ÖNCEKİ sezon averaj sayı farkının lig içi
    yüzdeliği. Veri yoksa (yeni takım, ilk maç) nötr 5.0. Tek kaynak —
    A_hesapla VE K_hesapla'daki sürpriz katkısı VE kalip_secici'nin
    kanca/kademe seçimi hep BURAYA bakar, iki ayrı kalite tanımı
    olmasın diye (kullanıcı kararı)."""
    if kod not in ortalamalar or not sirali:
        return 5.0
    return yuzdelik(sirali, ortalamalar[kod]) * 10


def A_hesapla(ev_kod, dep_kod, ortalamalar, sirali, bt, yildizlar):
    def kalite_puani(kod):
        return takim_kalite_puani(kod, ortalamalar, sirali)

    takim_kalite = (kalite_puani(ev_kod) + kalite_puani(dep_kod)) / 2

    if not yildizlar:
        yildiz_agirligi = 5.0
    else:
        toplamlar = []
        herhangi_yildiz_var = False
        for taraf in ("homeTeam", "awayTeam"):
            takim = bt[taraf]
            # yildizlar artık personId değil AD-katlanmış anahtarla tutuluyor
            # (bkz. yildizlar_yukle) — eşleşme de oynayan oyuncuların
            # katlanmış tam adları üzerinden yapılmalı.
            oynayan_adlar = {
                _katla(f"{p['firstName']} {p['familyName']}")
                for p in takim["players"] if p["statistics"]["minutes"]
            }
            takim_yildizlari = [o for o in yildizlar.values() if o.get("takim") == takim["teamTricode"]]
            if not takim_yildizlari:
                continue
            herhangi_yildiz_var = True
            for o in takim_yildizlari:
                agirlik = KADEME_AGIRLIK_A[o["kademe"]]
                toplamlar.append(agirlik if _katla(o["ad"]) in oynayan_adlar else 0)
        yildiz_agirligi = (sum(toplamlar) / len(toplamlar)) if herhangi_yildiz_var else 5.0

    return round(0.5 * takim_kalite + 0.5 * yildiz_agirligi, 2)


# ---------------------------------------------------------------------------
# Ana formül
# ---------------------------------------------------------------------------


def formulu_uygula(S, K, T, Y, F, G, A):
    # 0. Dram terfisi
    # Kullanıcı kararı: F=8 ("son 30 saniyede öne geçildi") eskiden
    # sadece küçük bir çarpan katkısı (0.011/puan) alıyordu, taşıyıcı
    # statüsüne terfi etmiyordu — son hücumda belli olan bir maç
    # (Charlotte-Indiana, F=8) bu yüzden "Bunları geç"e düşmüştü. Eşik
    # F>=9'dan F>=8'e indirildi.
    if F >= 8 or G >= 8:
        D = max(F, G) - 2
        F_carpanda = 0
        G_carpanda = 0
    else:
        D = 0
        F_carpanda = F
        G_carpanda = G

    # 1. Taşıyıcılar
    tasiyicilar = sorted([S, K, T, D], reverse=True)
    C1, C2, C3 = tasiyicilar[0], tasiyicilar[1], tasiyicilar[2]
    taban = C1 + 0.30 * C2 + 0.10 * C3

    # 2. Çarpan
    carpan = 0.80 + 0.014 * Y + 0.011 * F_carpanda + 0.010 * G_carpanda + 0.013 * A
    carpan = min(max(carpan, 0.80), 1.28)

    # 3. Zirve sönümlemesi
    if C1 in (S, T) and C1 == max(S, T):
        k = min(max((C1 - 8.5) / 1.5, 0), 1)
    else:
        k = 0
    carpan_efektif = 1 + (carpan - 1) * (1 - k)

    # 4. Ham
    ham = taban * carpan_efektif

    # 5. Rozet
    if ham <= 8:
        rozet = ham
    else:
        rozet = 8 + 2 * (1 - math.exp(-(ham - 8) / 4))

    if rozet >= 8.5:
        katman = "mutlaka"
    elif rozet >= 6.0:
        katman = "ikinci"
    else:
        katman = "gec"

    return {
        "rozet": round(rozet, 2),
        "ham": round(ham, 2),
        "katman": katman,
        "tasiyicilar": {"S": S, "K": K, "T": T, "D": D},
        "yukselticiler": {"Y": Y, "F": F, "G": G, "A": A},
        "dram_terfi": D > 0,
    }


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------


def mac_hesapla(gid, m, ay, puan_durumu, lig_gmsc_sirali, kisisel_gmsc, yildizlar, takim_kalite_ort, takim_kalite_sirali):
    bt = m["box_traditional"]["boxScoreTraditional"]
    actions = m["play_by_play"]["game"]["actions"]

    ev_kod = bt["homeTeam"]["teamTricode"]
    dep_kod = bt["awayTeam"]["teamTricode"]
    ev_skor = bt["homeTeam"]["statistics"]["points"]
    dep_skor = bt["awayTeam"]["statistics"]["points"]
    kazanan_ev_mi = ev_skor > dep_skor

    periyotlar = periyot_sonu_skorlari(actions)
    son_periyot = max(p[0] for p in periyotlar) if periyotlar else 4
    uzatma_var = son_periyot > 4

    seri = skor_serisi(actions)

    S, en_iyi_oyuncu = S_hesapla(bt, actions, son_periyot, lig_gmsc_sirali, kisisel_gmsc, yildizlar)
    kazanan_kod = ev_kod if kazanan_ev_mi else dep_kod
    kaybeden_kod = dep_kod if kazanan_ev_mi else ev_kod
    K = K_hesapla(
        ev_kod, dep_kod, puan_durumu, ay,
        kazanan_kod=kazanan_kod, kaybeden_kod=kaybeden_kod,
        kalite_ort=takim_kalite_ort, kalite_sirali=takim_kalite_sirali,
    )
    T = T_hesapla(bt)

    Y = Y_hesapla(seri, son_periyot, uzatma_var)

    F = F_hesapla(seri, son_periyot, uzatma_var)
    G = G_hesapla(seri, kazanan_ev_mi)
    A = A_hesapla(ev_kod, dep_kod, takim_kalite_ort, takim_kalite_sirali, bt, yildizlar)

    sonuc = formulu_uygula(S, K, T, Y, F, G, A)
    sonuc["mac_id"] = gid
    sonuc["ev"] = ev_kod
    sonuc["dep"] = dep_kod
    sonuc["ev_skor"] = ev_skor
    sonuc["dep_skor"] = dep_skor
    sonuc["en_iyi_performans"] = en_iyi_oyuncu
    return sonuc


def hesapla(tarih_str, zorla=False):
    hedef_dosya = SKOR_DIZIN / f"{tarih_str}.json"
    if hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden hesapla).")
        return hedef_dosya

    ham = json.loads((HAM_DIZIN / f"{tarih_str}.json").read_text())
    yildizlar = yildizlar_yukle()

    ay = datetime.strptime(tarih_str, "%Y-%m-%d").month

    puan_durumu_ham = ham["puan_durumu"]
    from gercekler import puan_durumu_hesapla

    puan_durumu = puan_durumu_hesapla(puan_durumu_ham, tarih_str)

    lig_gmsc_sirali, kisisel_gmsc = lig_gmsc_dagilimi_ve_kisisel_taban(ham["oyuncu_ortalama"])
    takim_kalite_ort, takim_kalite_sirali = takim_kalitesi_hesapla(puan_durumu_ham, tarih_str)

    sonuclar = []
    for gid, m in ham["maclar"].items():
        sonuc = mac_hesapla(
            gid, m, ay, puan_durumu, lig_gmsc_sirali, kisisel_gmsc, yildizlar,
            takim_kalite_ort, takim_kalite_sirali,
        )
        sonuclar.append(sonuc)

    sonuclar.sort(key=lambda s: s["ham"], reverse=True)

    en_iyi = sonuclar[0]["rozet"] if sonuclar else 0
    cikti = {
        "tarih": tarih_str,
        "hesaplandi": datetime.utcnow().isoformat() + "Z",
        "en_iyi_skor": en_iyi,
        "maclar": sonuclar,
    }

    SKOR_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya}")
    return hedef_dosya


if __name__ == "__main__":
    import argparse

    ayristirici = argparse.ArgumentParser()
    ayristirici.add_argument("tarih", help="YYYY-MM-DD")
    ayristirici.add_argument("--force", action="store_true")
    args = ayristirici.parse_args()
    hesapla(args.tarih, zorla=args.force)
