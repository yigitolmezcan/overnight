"""
gercekler.py — OVERNIGHT boru hattının 3. adımı.

Girdi:  ham/{tarih}.json
Çıktı:  gercek/{tarih}.json — atomik, doğrulanmış olgular

Bu modülün TEK işi: box score, play-by-play ve maç geçmişinden metin
üreticinin kullanabileceği yapısal kayıtlar çıkarmak. Türkçe cümle
üretmez — sadece veri taşır.

Cömertlik kuralı: bu modülün başarısızlık modu "yanlış gerçek üretmek"
değil, "yeterince gerçek üretmemek". Doğrulayıcı (dogrula.py) metindeki
her sayıyı ve ismi burada üretilen kayıtlara karşı arayacak; kayıt yoksa
cümle reddedilir. O yüzden her maç için mümkün olan her açıdan kayıt
çıkarılır, kullanılıp kullanılmayacağına yazı üretici karar verir.

Yapısal kural: `tur: "an"` kaydı SADECE `an_uret()` fonksiyonundan
çıkar ve bu fonksiyon play-by-play'in `period`/`clock` alanlarını
zorunlu kılar (yoksa AssertionError). Kodda başka hiçbir yer "an" türü
bir sözlük elle kurmaz. Bu, sistemin son saniye / son hücum gibi anları
uydurmasını yapısal olarak imkânsız kılan tek mekanizma.

Bilinen kapsam dışı:
- `seri` (galibiyet/mağlubiyet serisi): LeagueGameLog'dan hesaplanıyor,
  cek.py bunun için ekstra bir uç noktaya ihtiyaç duymadı — ayrıntı için
  şartname bölüm 2'ye bak.
- Tam "kadro dışı" listesi eksik: BoxScoreTraditionalV3'ün `comment`
  alanı sadece DNP/DND (aktif kadroda olup oynamayan) oyuncuları
  yakalıyor. Maça hiç dahil edilmemiş, tamamen "inactive" işaretli
  oyuncular (örn. dinlendirilen yıldızlar) box score'da hiç görünmüyor
  ve bu veri kaynağından çıkarılamıyor — bkz. bu adımın kabul testi
  raporu.
"""

import json
import re
from datetime import datetime
from pathlib import Path

# nba_api.stats.static.players YEREL/paket-içi bir tablo (ağ çağrısı
# YOK) — cek.py'nin "tüm nba_api ÇAĞRILARI (canlı istek) tek dosyada
# kalır" kuralı bunu kapsamıyor, salt-okunur bir referans veri kümesi.
# Kullanım amacı: box score V3 uç noktaları (BoxScoreTraditionalV3 vb.)
# oyuncu adlarını AKSANSIZ döndürüyor ("Sengun", "Doncic", "Jokic") —
# gerçek üretim bug'ı: bu isimler hiç düzeltilmeden "gercekler"e, oradan
# da yayınlanan metne sızıyordu ("Alperen Sengun" gibi). Statik oyuncu
# tablosu AYNI kişiyi doğru aksanla taşıyor ("Nikola Jokić") — personId
# üzerinden eşleştirip düzeltiyoruz.
from nba_api.stats.static import players as _nba_statik_oyuncular

HAM_DIZIN = Path(__file__).parent / "ham"
GERCEK_DIZIN = Path(__file__).parent / "gercek"
CONFIG_DIZIN = Path(__file__).parent / "config"

_DOGRU_AD_CACHE = None

# nba_api'nin statik tablosu Slav kökenli aksanları çoğunlukla doğru
# taşıyor ("Nikola Jokić", "Luka Dončić", "Nikola Vučević") ama
# TÜRKÇE karakterleri KORUMUYOR — personId 1630578 için tablonun
# kendisi de "Alperen Sengun" döndürüyor (gerçek üretim bug'ı: statik
# tabloya güvenmek Şengün'ü düzeltmiyordu). Bu yüzden Türkçe isimler
# için elle tutulan bir üst-düzeltme katmanı var; kaynak zaten
# config/turk_oyuncular.json (Türkler bölümü için de kullanılıyor).
_TURKCE_AD_DUZELTME_CACHE = None


def _turkce_ad_duzeltmelerini_yukle():
    global _TURKCE_AD_DUZELTME_CACHE
    if _TURKCE_AD_DUZELTME_CACHE is None:
        dosya = Path(__file__).parent / "config" / "turk_oyuncular.json"
        _TURKCE_AD_DUZELTME_CACHE = {}
        if dosya.exists():
            for o in json.loads(dosya.read_text()).get("oyuncular", []):
                _TURKCE_AD_DUZELTME_CACHE[_katla_ascii(o["ad"])] = o["ad"]
    return _TURKCE_AD_DUZELTME_CACHE


def gmsc(s):
    """Hollinger Game Score. s: box score istatistik sözlüğü (V3 alan adlarıyla)."""
    return (
        s["points"]
        + 0.4 * s["fieldGoalsMade"]
        - 0.7 * s["fieldGoalsAttempted"]
        - 0.4 * (s["freeThrowsAttempted"] - s["freeThrowsMade"])
        + 0.7 * s["reboundsOffensive"]
        + 0.3 * s["reboundsDefensive"]
        + s["steals"]
        + 0.7 * s["assists"]
        + 0.7 * s["blocks"]
        - 0.4 * s["foulsPersonal"]
        - s["turnovers"]
    )


def _katla_ascii(ad):
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", ad) if not unicodedata.combining(c)).lower()


# Kullanıcı kararı: kadro dışı bir oyuncu ancak oynasaydı sonucu
# değiştirebilecek biriyse anılır — config/yildizlar.json'da olmalı YA DA
# son 10 maçta ortalama 25+ dakika oynamış olmalı. Bu kontrol FACT
# seviyesinde uygulanır (kadro_disi_gerceklerini_uret) — kanca, niteleyici
# ya da LLM'in hiçbiri, filtrelenmiş bir ismi zaten hiç göremez.
KADRO_DISI_DAKIKA_ESIGI = 25
KADRO_DISI_SON_MAC_SAYISI = 10
_YILDIZLAR_KATLANMIS_CACHE = None


def _yildizlar_katlanmis_yukle():
    global _YILDIZLAR_KATLANMIS_CACHE
    if _YILDIZLAR_KATLANMIS_CACHE is None:
        dosya = CONFIG_DIZIN / "yildizlar.json"
        _YILDIZLAR_KATLANMIS_CACHE = set()
        if dosya.exists():
            for o in json.loads(dosya.read_text()).get("oyuncular", []):
                _YILDIZLAR_KATLANMIS_CACHE.add(_katla_ascii(o["ad"]))
    return _YILDIZLAR_KATLANMIS_CACHE


def _normal_sezon_satirlari(oyuncu_ortalama_ham):
    """ham/{tarih}.json'daki 'oyuncu_ortalama' (PlayerGameLogs) çağrısı
    SeasonType filtrelemiyor — gerçek üretim bug'ı (21 Ekim, sezonun İLK
    gecesi): Ousmane Dieng'in "son 10 maçta 25+ dakika" ortalaması
    hazırlık sezonu (preseason) maçlarından geliyordu, çünkü kadro dışı
    filtresi "veri var" sanıp geçirdi — oysa o veri bu SEZONA ait değildi.
    NBA GAME_ID'nin ilk üç hanesi maç türünü kodluyor: "001" hazırlık
    sezonu, "002" normal sezon (bkz. gerçek maçların hepsindeki
    "0022500XXX" kalıbı). Bu fonksiyon SADECE normal sezon satırlarını
    döner — hazırlık sezonu verisi "veri yok" ile AYNI muameleyi görür."""
    rs = oyuncu_ortalama_ham["resultSets"][0]
    idx = {h: i for i, h in enumerate(rs["headers"])}
    return [row for row in rs["rowSet"] if str(row[idx["GAME_ID"]]).startswith("002")], idx


def oyuncu_son10_dakika_ortalamasi(oyuncu_ortalama_ham):
    """Satırlar GAME_DATE'e göre azalan sırada gelir (en yeni maç ilk
    sırada) — bu yüzden her oyuncu için ilk KADRO_DISI_SON_MAC_SAYISI
    satır, bu geceden ÖNCEKİ son N NORMAL SEZON maçının dakika
    ortalamasını verir (hazırlık sezonu hariç, bkz. _normal_sezon_satirlari).
    {player_id: ortalama_dakika} döner."""
    rows, idx = _normal_sezon_satirlari(oyuncu_ortalama_ham)
    dakikalar_by_id = {}
    for row in rows:
        pid = row[idx["PLAYER_ID"]]
        dakikalar_by_id.setdefault(pid, []).append(row[idx["MIN"]])
    return {
        pid: sum(dks[:KADRO_DISI_SON_MAC_SAYISI]) / len(dks[:KADRO_DISI_SON_MAC_SAYISI])
        for pid, dks in dakikalar_by_id.items()
        if dks
    }


def _dogru_oyuncu_adi(person_id, yedek_ad):
    global _DOGRU_AD_CACHE
    if _DOGRU_AD_CACHE is None:
        _DOGRU_AD_CACHE = {p["id"]: p["full_name"] for p in _nba_statik_oyuncular.get_players()}
    aday = _DOGRU_AD_CACHE.get(person_id, yedek_ad)
    turkce_duzeltme = _turkce_ad_duzeltmelerini_yukle().get(_katla_ascii(aday))
    return turkce_duzeltme or aday

# Nadiren değişir (yalnızca takım taşınması/genişlemede) — sezon başı
# config'e taşınabilir, şimdilik burada sabit.
KONFERANS = {
    "ATL": "Doğu", "BOS": "Doğu", "BKN": "Doğu", "CHA": "Doğu", "CHI": "Doğu",
    "CLE": "Doğu", "DET": "Doğu", "IND": "Doğu", "MIA": "Doğu", "MIL": "Doğu",
    "NYK": "Doğu", "ORL": "Doğu", "PHI": "Doğu", "TOR": "Doğu", "WAS": "Doğu",
    "DAL": "Batı", "DEN": "Batı", "GSW": "Batı", "HOU": "Batı", "LAC": "Batı",
    "LAL": "Batı", "MEM": "Batı", "MIN": "Batı", "NOP": "Batı", "OKC": "Batı",
    "PHX": "Batı", "POR": "Batı", "SAC": "Batı", "SAS": "Batı", "UTA": "Batı",
}

KILOMETRE_ESIKLERI = [
    # 40+ sayı — kullanıcı kararı: "8 oyuncuda görüldü" tipi bağlam çok
    # değerli ama 50+/olağanüstü eşikler nadiren tetikleniyor. 40+ daha
    # sık düşen bir eşik, bu yüzden ayrı — bağlamı NBA tarihi değil, O
    # OYUNCUNUN BU SEZONU (bkz. _sezon_sayisi_baglam_uret, gerçekten
    # doğrulanabilir tek veri kaynağımız: ham/{tarih}.json'daki
    # oyuncu_ortalama, zaten çekiliyor, yeni bir nba_api çağrısı gerekmedi).
    ("40_sayi", lambda s: s["points"] >= 40),
    ("50_sayi", lambda s: s["points"] >= 50),
    ("20_ribaund", lambda s: s["reboundsTotal"] >= 20),
    ("10_uclu", lambda s: s["threePointersMade"] >= 10),
    ("5_blok", lambda s: s["blocks"] >= 5),
    (
        "triple_double",
        lambda s: sum(
            1
            for v in (
                s["points"],
                s["reboundsTotal"],
                s["assists"],
                s["steals"],
                s["blocks"],
            )
            if v >= 10
        )
        >= 3,
    ),
    # "Olağanüstü" kademe — bunlar sadece "dikkat çekici" değil, NBA'de
    # nadiren görülen eşikler. Kullanıcı kararı: bu eşiği geçen bir
    # performans için metin "tarihte nadir" türünden bir çerçeve
    # kurabilsin diye (bkz. dogrula.py T18) ayrı işaretleniyor —
    # OLAGANUSTU_KILOMETRE_ESIKLERI kümesinde tutulan isimler bunlar.
    # 80+ sayı — kullanıcı düzeltmesi: Adebayo'nun 83 sayılık gecesi
    # "60+ sayı" eşiğiyle anlatılıyordu, bu performansı küçültüyordu.
    # Kilometre seçimi geçilen EN YÜKSEK eşiği almalı — 80+ ayrı, daha
    # üst bir eşik (bkz. _KILOMETRE_ONCELIK, 60_sayi'den ÖNCE gelir).
    ("80_sayi", lambda s: s["points"] >= 80),
    ("60_sayi", lambda s: s["points"] >= 60),
    ("25_ribaund", lambda s: s["reboundsTotal"] >= 25),
    ("20_asist", lambda s: s["assists"] >= 20),
    ("15_uclu", lambda s: s["threePointersMade"] >= 15),
    (
        "quadruple_double",
        lambda s: sum(
            1
            for v in (
                s["points"],
                s["reboundsTotal"],
                s["assists"],
                s["steals"],
                s["blocks"],
            )
            if v >= 10
        )
        >= 4,
    ),
    # 50+ sayı VE triple-double birlikte — ikisi ayrı ayrı zaten
    # "50_sayi"/"triple_double" olarak kayıtlı ama BİRLİKTE olmaları
    # tek tek toplamlarından çok daha nadir bir başarı (kullanıcı
    # örneği: Jokić 56/16/15 — 56 sayı tek başına "60_sayi" eşiğini
    # geçmediği için OLAĞANÜSTÜ sayılmıyordu, ama 50+ sayılı bir
    # triple-double kendi başına NBA tarihinde çok az oyuncunun
    # başardığı bir şey; bu yüzden ayrı bir eşik).
    (
        "50_triple_double",
        lambda s: s["points"] >= 50
        and sum(
            1
            for v in (
                s["points"],
                s["reboundsTotal"],
                s["assists"],
                s["steals"],
                s["blocks"],
            )
            if v >= 10
        )
        >= 3,
    ),
]

# T18'in "doğrulanamaz kayıt iddiası" yasağını KOŞULLU olarak gevşetmesi
# için — bu isimlerden biri bir oyuncunun kilometre gerçeğinde varsa,
# o oyuncu için "tarihte nadir/olağanüstü" türü bir çerçeve METNİ
# (KESİN bir sıra/rekor numarası DEĞİL — "ikinci en yüksek skor" gibi
# bir iddia hâlâ gerçek bir all-time veritabanı gerektirir, bizde yok)
# doğrulanmış sayılır.
OLAGANUSTU_KILOMETRE_ESIKLERI = {
    "80_sayi", "60_sayi", "25_ribaund", "20_asist", "15_uclu", "quadruple_double", "50_triple_double",
}

# Kullanıcı düzeltmesi (2. tur): "baglam" bir CÜMLE değil, YAPISAL VERİ
# tutmalı — model kendi cümlesini kursun, biz sadece doğrulanmış sayıyı
# versin. İlk sürümde burada hazır cümleler vardı ve model onları neredeyse
# birebir kopyalıyordu ("bir avuç oyuncunun başarabildiği bir şey" —
# kullanıcının kendi örnek cümlesinin kopyası). Somut sayı belirsiz
# övgüden daha güçlü ("altıncı kez" > "bir avuç oyuncu").
#
# Sayılar WebSearch ile doğrulandı (2024-25 sezonu sonuna kadar, düzenli
# sezon — bu pipeline'ın ürettiği geceler bu tarihten SONRAKİ fiktif/test
# geceleri olabilir, o yüzden "ondan önce N oyuncu" gibi bu geceden ÖNCEKİ
# durumu anlatan bir çerçeve kullanılmalı, kesin bir "bu N'inci kez"
# iddiası değil — aynı gecede/pipeline'da başka bir maç aynı eşiği
# geçmiş olabilir, elimizde o karşılaştırmayı yapacak bir sayaç yok).
#
# 25_ribaund ve 20_asist için baglam KASITLI OLARAK None: WebSearch
# kaynakları bu iki eşik için ya birbiriyle çelişiyordu (25+ ribaund:
# "29 kez" denen toplam, oyuncu bazlı dökümle uyuşmuyordu) ya da tam bu
# eşiğe (20+) karşılık gelen temiz bir sayı bulunamadı (kaynaklar 22+
# eşiğini kullanıyor). Doğrulanamayan bir sayı yayınlamaktansa hiç sayı
# vermemek — model bu ikisi için sistem promptundaki NİTELİKSEL (sayısız)
# çerçeveye düşer.
TARIHSEL_BAGLAM = {
    "80_sayi": {
        "olcek": "nba_tarihi", "tur": "80+ sayı",
        "ondan_once_oyuncu_sayisi": 2, "ondan_once_kez_sayisi": 2,
        "not": "WebSearch ile doğrulandı (2026-08-20), NBA tarihinde SADECE üç kez: Wilt Chamberlain (100, 1962), Kobe Bryant (81, 2006), ve bu eşiği geçen üçüncü oyuncu her kimse. Bu geceki performans üçüncüsü olabilir, o durumda ondan ÖNCEKİ iki oyuncu (Chamberlain, Bryant) sayılır.",
    },
    "60_sayi": {
        "olcek": "nba_tarihi", "tur": "60+ sayı",
        "ondan_once_oyuncu_sayisi": 38, "ondan_once_kez_sayisi": 93,
        "not": "2024-25 sezonu sonuna kadar, düzenli sezon",
    },
    "25_ribaund": None,
    "20_asist": None,
    "15_uclu": {
        "olcek": "nba_tarihi", "tur": "15+ üçlük",
        "ondan_once_oyuncu_sayisi": 0, "ondan_once_kez_sayisi": 0,
        "not": "gerçek NBA rekoru 14 (Klay Thompson, 2018), bu eşik daha önce HİÇ geçilmedi, geçilirse 'ilk kez' iddiası doğru olur",
    },
    "quadruple_double": {
        "olcek": "nba_tarihi", "tur": "quadruple-double",
        "ondan_once_oyuncu_sayisi": 4, "ondan_once_kez_sayisi": 4,
        "not": "resmi istatistik döneminde (1973-74 sonrası), steals/blocks öncesi dönem hesaba katılamıyor",
    },
    "50_triple_double": {
        "olcek": "nba_tarihi", "tur": "50+ sayılık triple-double",
        "ondan_once_oyuncu_sayisi": 8, "ondan_once_kez_sayisi": 17,
        "not": "2024-25 sezonu sonuna kadar (Jokić ve Dončić dahil)",
    },
}


# Kullanıcı düzeltmesi (3. tur): "8 oyuncuda görüldü" tipi bağlam çok
# değerli ama NBA-tarihi eşikleri (yukarıdaki TARIHSEL_BAGLAM) nadiren
# tetikleniyor. Daha sık düşen eşikler için de doğrulanabilir bir sayı
# üretilebilir — ama NBA tarihi değil, OYUNCUNUN BU SEZONU üzerinden:
# ham/{tarih}.json'daki "oyuncu_ortalama" (PlayerGameLogs, sezonun bu
# geceden ÖNCEKİ tüm maçları) zaten çekiliyor, yeni bir nba_api çağrısı
# GEREKMEDİ — sadece yeni bir işleme adımı. "Kariyerinde kaçıncı"
# (çoklu-sezon geçmişi) ve "franchise tarihinde kaçıncı" (takımın
# tüm-zamanlar arşivi) KASITLI OLARAK YOK — ikisi de bu pipeline'ın
# çekmediği, çok daha ağır bir veri kaynağı gerektiriyor (çoklu sezon
# oyuncu günlüğü / takım tüm-zamanlar arşivi), doğrulanamayan bir sayı
# yayınlamaktansa hiç yayınlamamak.
def sezon_sikligi_baglam_uret(player_id, esik_puan, sezon_sayilari_by_player_id):
    gecmis = sezon_sayilari_by_player_id.get(player_id)
    if gecmis is None:
        return None
    # Kullanıcı kararı (sezon başı susma kuralı): oyuncunun bu sezon
    # ondan önceki maç sayısı 10'un altındaysa "bu sezon önce N kez"
    # türü bir sıklık iddiası anlamsız — sezonun 3. maçında "önce 0 kez
    # geçmemişti" demek komik bir kesinlik izlenimi veriyor.
    if len(gecmis) < SEZON_ACILISI_TAZE_MAC_SAYISI:
        return None
    kac_kez = sum(1 for p in gecmis if p >= esik_puan)
    return {
        "olcek": "oyuncu_sezonu", "tur": f"{esik_puan}+ sayı",
        "bu_sezon_once_kac_kez": kac_kez,
        "not": "bu geceden önceki sezon maçları (PlayerGameLogs)",
    }


def sezon_sayilari_cikart(oyuncu_ortalama_ham):
    """ham/{tarih}.json'daki 'oyuncu_ortalama' (PlayerGameLogs) çıktısını
    {player_id: [PTS, PTS, ...]} sözlüğüne indirger — kilometre
    gerçeklerinin "bu sezon kaçıncı kez" bağlamı için. SADECE normal
    sezon (hazırlık sezonu hariç, bkz. _normal_sezon_satirlari) —
    aksi halde "bu sezon önce N kez" hazırlık maçlarını da sayardı."""
    rows, idx = _normal_sezon_satirlari(oyuncu_ortalama_ham)
    sonuc = {}
    for row in rows:
        pid = row[idx["PLAYER_ID"]]
        sonuc.setdefault(pid, []).append(row[idx["PTS"]])
    return sonuc


class GercekUretici:
    """Bir maç için sıralı, benzersiz id'lerle gerçek biriktirir."""

    def __init__(self):
        self.kayitlar = []
        self._sayac = 0

    def ekle(self, tur, veri, kaynak, guven):
        self._sayac += 1
        self.kayitlar.append(
            {
                "id": f"f{self._sayac}",
                "tur": tur,
                "veri": veri,
                "kaynak": kaynak,
                "guven": guven,
            }
        )
        return self.kayitlar[-1]["id"]

    def an_uret(self, action, gid, ekstra_veri):
        """`an` türü gerçeğin TEK üretim yolu. period/clock zorunlu."""
        assert "period" in action and action["period"] is not None
        assert "clock" in action and action["clock"]
        veri = {
            "periyot": action["period"],
            "saat": action["clock"],
            **ekstra_veri,
        }
        return self.ekle(
            "an", veri, f"PlayByPlayV3:{gid}:{action['actionNumber']}", "kesin"
        )


def clock_saniye(clock_str):
    """'PT01M23.40S' -> periyottaki kalan saniye (83.4)."""
    m = re.match(r"PT(\d+)M([\d.]+)S", clock_str)
    dakika, saniye = int(m.group(1)), float(m.group(2))
    return dakika * 60 + saniye


def takim_kimlik_haritasi(bt):
    """box_traditional'dan {team_id: tricode} ve ev/dep tricode döner."""
    return {
        bt["homeTeamId"]: bt["homeTeam"]["teamTricode"],
        bt["awayTeamId"]: bt["awayTeam"]["teamTricode"],
    }, bt["homeTeam"]["teamTricode"], bt["awayTeam"]["teamTricode"]


# ---------------------------------------------------------------------------
# Maç seviyesi gerçek üreticileri
# ---------------------------------------------------------------------------


def skor_gercegi_uret(g, gid, bt):
    ev = bt["homeTeam"]
    dep = bt["awayTeam"]
    ev_skor = int(ev["statistics"]["points"])
    dep_skor = int(dep["statistics"]["points"])
    kazanan = ev["teamTricode"] if ev_skor > dep_skor else dep["teamTricode"]
    g.ekle(
        "skor",
        {
            "ev": ev["teamTricode"],
            "dep": dep["teamTricode"],
            "ev_skor": ev_skor,
            "dep_skor": dep_skor,
            "kazanan": kazanan,
            "fark": abs(ev_skor - dep_skor),
        },
        f"BoxScoreTraditionalV3:{gid}",
        "kesin",
    )
    return ev["teamTricode"], dep["teamTricode"], ev_skor, dep_skor, kazanan


def periyot_sonu_skorlari(actions):
    """[(periyot, ev_kumulatif, dep_kumulatif, saat_etiketi), ...] period sonu markerları."""
    sonuclar = []
    for a in actions:
        if a["actionType"] == "period" and a["subType"] == "end":
            sonuclar.append(
                (a["period"], int(a["scoreHome"]), int(a["scoreAway"]))
            )
    return sonuclar


def ceyrek_gerceklerini_uret(g, gid, actions, ev_kod, dep_kod):
    periyotlar = periyot_sonu_skorlari(actions)
    onceki_ev, onceki_dep = 0, 0
    for periyot, ev_kum, dep_kum in periyotlar:
        ev_ceyrek = ev_kum - onceki_ev
        dep_ceyrek = dep_kum - onceki_dep
        g.ekle(
            "ceyrek",
            {
                "periyot": periyot,
                "ev": ev_kod,
                "dep": dep_kod,
                "ev_ceyrek_sayisi": ev_ceyrek,
                "dep_ceyrek_sayisi": dep_ceyrek,
                "kumulatif_ev": ev_kum,
                "kumulatif_dep": dep_kum,
                "kumulatif_fark": ev_kum - dep_kum,
            },
            f"PlayByPlayV3:{gid}:periyot{periyot}sonu",
            "kesin",
        )
        onceki_ev, onceki_dep = ev_kum, dep_kum
    return periyotlar


def oyuncu_stat_gerceklerini_uret(g, gid, bt):
    """Sahaya çıkan HERKES için. Kapsam kuralı burada — box her zaman tam olmalı."""
    uretilenler = []
    for taraf in ("homeTeam", "awayTeam"):
        takim = bt[taraf]
        for p in takim["players"]:
            dk = p["statistics"]["minutes"]
            if not dk:
                continue  # oynamadı — kadro_disi tarafında ele alınıyor
            s = p["statistics"]
            veri = {
                "oyuncu": _dogru_oyuncu_adi(p['personId'], f"{p['firstName']} {p['familyName']}"),
                "id": p["personId"],
                "takim": takim["teamTricode"],
                "dk": dk,
                "sayi": s["points"],
                "rib": s["reboundsTotal"],
                "ast": s["assists"],
                "cal": s["steals"],
                "blk": s["blocks"],
                "tk": s["turnovers"],
                "fg": f"{s['fieldGoalsMade']}/{s['fieldGoalsAttempted']}",
                "uc": f"{s['threePointersMade']}/{s['threePointersAttempted']}",
                "sut": f"{s['freeThrowsMade']}/{s['freeThrowsAttempted']}",
                "arti_eksi": s["plusMinusPoints"],
            }
            gid_kaynak = f"BoxScoreTraditionalV3:{gid}:{p['personId']}"
            g.ekle("oyuncu_stat", veri, gid_kaynak, "kesin")
            uretilenler.append((p["personId"], veri, s))
    return uretilenler


def takim_stat_gerceklerini_uret(g, gid, bt):
    for taraf in ("homeTeam", "awayTeam"):
        takim = bt[taraf]
        s = takim["statistics"]
        g.ekle(
            "takim_stat",
            {
                "takim": takim["teamTricode"],
                "isabet": f"{s['fieldGoalsMade']}/{s['fieldGoalsAttempted']}",
                "uclu": f"{s['threePointersMade']}/{s['threePointersAttempted']}",
                "serbest": f"{s['freeThrowsMade']}/{s['freeThrowsAttempted']}",
                "oreb": s["reboundsOffensive"],
                "dreb": s["reboundsDefensive"],
                "rib": s["reboundsTotal"],
                "ast": s["assists"],
                "cal": s["steals"],
                "blk": s["blocks"],
                "tk": s["turnovers"],
                "pf": s["foulsPersonal"],
                "sayi": s["points"],
            },
            f"BoxScoreTraditionalV3:{gid}:{takim['teamTricode']}",
            "kesin",
        )


def kadro_disi_gerceklerini_uret(g, gid, bt, son10_dakika_by_id=None):
    son10_dakika_by_id = son10_dakika_by_id or {}
    yildizlar = _yildizlar_katlanmis_yukle()
    for taraf in ("homeTeam", "awayTeam"):
        takim = bt[taraf]
        for p in takim["players"]:
            if not p["comment"]:
                continue
            oyuncu_adi = _dogru_oyuncu_adi(p['personId'], f"{p['firstName']} {p['familyName']}")
            # Kullanıcı kararı: haber değeri yoksa (yıldız değil VE
            # rotasyonda değil) kadro dışı bir isim hiçbir metinde geçmez.
            yildiz_mi = _katla_ascii(oyuncu_adi) in yildizlar
            rotasyonda_mi = son10_dakika_by_id.get(p["personId"], 0) >= KADRO_DISI_DAKIKA_ESIGI
            if not (yildiz_mi or rotasyonda_mi):
                continue
            g.ekle(
                "kadro_disi",
                {
                    "oyuncu": oyuncu_adi,
                    "id": p["personId"],
                    "takim": takim["teamTricode"],
                    "aciklama": p["comment"].strip(),
                },
                f"BoxScoreTraditionalV3:{gid}:{p['personId']}",
                "kesin",
            )


def oyuncu_ceyrek_gerceklerini_uret(g, gid, actions, oyuncu_isimleri):
    """Play-by-play'den oyuncu başına periyot içi sayı dağılımı."""
    dagilim = {}  # (personId, period) -> sayi
    for a in actions:
        personId = a.get("personId")
        if not personId or personId == 0:
            continue
        periyot = a["period"]
        anahtar = (personId, periyot)
        if a["actionType"] == "Made Shot" and a.get("shotResult") == "Made":
            dagilim[anahtar] = dagilim.get(anahtar, 0) + a["shotValue"]
        elif a["actionType"] == "Free Throw" and "MISS" not in a["description"]:
            dagilim[anahtar] = dagilim.get(anahtar, 0) + 1

    for (personId, periyot), sayi in sorted(dagilim.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if sayi <= 0 or personId not in oyuncu_isimleri:
            continue
        g.ekle(
            "oyuncu_ceyrek",
            {
                "oyuncu": oyuncu_isimleri[personId],
                "id": personId,
                "periyot": periyot,
                "sayi": sayi,
            },
            f"PlayByPlayV3:{gid}:turetilmis",
            "turetilmis",
        )


def kilometre_gerceklerini_uret(g, gid, oyuncu_stat_ham, sezon_sayilari_by_player_id=None):
    sezon_sayilari_by_player_id = sezon_sayilari_by_player_id or {}
    for personId, veri, s in oyuncu_stat_ham:
        for esik_adi, kural in KILOMETRE_ESIKLERI:
            if kural(s):
                if esik_adi == "40_sayi":
                    baglam = sezon_sikligi_baglam_uret(personId, 40, sezon_sayilari_by_player_id)
                else:
                    baglam = TARIHSEL_BAGLAM.get(esik_adi)
                g.ekle(
                    "kilometre",
                    {
                        "oyuncu": veri["oyuncu"],
                        "id": personId,
                        "esik": esik_adi,
                        "sayi": s["points"],
                        "rib": s["reboundsTotal"],
                        "ast": s["assists"],
                        # Kullanıcı kuralı: bir maçta birden fazla aynı
                        # eşik varsa (ör. iki triple-double) metin EN
                        # YÜKSEK GmSc'liyi anar — seçim buna dayanıyor.
                        "gmsc": round(gmsc(s), 2),
                        "baglam": baglam,
                    },
                    f"BoxScoreTraditionalV3:{gid}:{personId}",
                    "turetilmis",
                )


def an_gerceklerini_uret(g, gid, actions, isim_haritasi):
    """Cömert: klutch skor değişimleri, lider değişimleri, teknik/flagrant faul."""
    son_fark = 0
    son_bilinen_ev, son_bilinen_dep = 0, 0
    for a in actions:
        if a["scoreHome"] == "" or a["scoreAway"] == "":
            skor_var = False
        else:
            skor_var = True
            son_bilinen_ev, son_bilinen_dep = int(a["scoreHome"]), int(a["scoreAway"])

        # Son 2 dakikada (herhangi bir periyotta, uzatma dahil) sayı üreten oyunlar
        if skor_var and a["actionType"] in ("Made Shot", "Free Throw"):
            if a["actionType"] == "Made Shot" and a.get("shotResult") != "Made":
                pass
            elif a["actionType"] == "Free Throw" and "MISS" in a["description"]:
                pass
            else:
                saniye_kalan = clock_saniye(a["clock"])
                if saniye_kalan <= 120:
                    g.an_uret(
                        a,
                        gid,
                        {
                            "tur_alt": "klutch_sayi",
                            "oyuncu": isim_haritasi.get(a.get("personId"), a.get("playerName", "")),
                            "aciklama": a["description"],
                            "skor_ev": son_bilinen_ev,
                            "skor_dep": son_bilinen_dep,
                            "fark": son_bilinen_ev - son_bilinen_dep,
                        },
                    )

        # Lider değişimleri (tüm maç boyu)
        if skor_var:
            yeni_fark = son_bilinen_ev - son_bilinen_dep
            if son_fark != 0 and yeni_fark != 0 and (son_fark > 0) != (yeni_fark > 0):
                g.an_uret(
                    a,
                    gid,
                    {
                        "tur_alt": "lider_degisimi",
                        "aciklama": a["description"],
                        "skor_ev": son_bilinen_ev,
                        "skor_dep": son_bilinen_dep,
                        "fark": yeni_fark,
                    },
                )
            if yeni_fark != 0:
                son_fark = yeni_fark

        # Teknik faul / flagrant / ihraç — her zaman haber değeri taşır
        if a["actionType"] == "Foul" and a["subType"] in (
            "Technical",
            "Flagrant Type 1",
            "Flagrant Type 2",
        ):
            g.an_uret(
                a,
                gid,
                {
                    "tur_alt": "disiplin",
                    "oyuncu": isim_haritasi.get(a.get("personId"), a.get("playerName", "")),
                    "aciklama": a["description"],
                    "detay": a["subType"],
                },
            )


# ---------------------------------------------------------------------------
# MAÇ AKIŞI — dört satırlık olay dizisi
# ---------------------------------------------------------------------------
#
# KULLANICI KARARI: Mutlaka bil / Göz at'ta dört cümlelik serbest anlatı
# kalktı. Serbest üretim sürekli ve HER SEFERİNDE BAŞKA bir sınıftan
# patlıyordu: uydurma detay ("yumuşak dokunuşla bıraktığı şut" — veride
# öyle bir şey yok), kılık değiştirmiş yasak ifade, bozuk deyim, kopuk
# anlatı. Kural eklemek çözmüyor; model sonsuz sayıda yanlış yapabilir,
# biz yalnız gördüğümüzü yasaklayabiliriz.
#
# Akış satırları LLM'E HİÇ GİTMEZ. Buradan, sabit kalıplarla, doğrudan
# veriden üretilirler. Bu yüzden olaylar GERÇEK KAYDI olarak yazılıyor:
# projenin değişmez kuralı, yayınlanan her sayı ve adın bir gercekler
# kaydına dayanmasıdır. Cümleye çevirme işi cumle.py'de, seçme işi
# derle.py'de; burada yalnız OLAY ve VERİSİ var.
AKIS_SERI_ASGARI = 8       # "N-0 gitti" için en az sayı
AKIS_BASA_BAS = 3          # çeyrek sonunda bu fark "başa baş" sayılır
AKIS_DEVRE_FARK = 10       # devrede bu farktan büyükse ayrı satır
AKIS_SON_SANIYE = 60.0     # "Son" etiketi eşiği (periyot 4+)


def _akis_zaman(periyot, saniye_kalan, ceyrek_sonu=False):
    """('1Ç', None) / ('Devre', None) / ('4Ç', '2:38') / ('Son', '0:04')"""
    if ceyrek_sonu and periyot == 2:
        return "Devre", None
    if ceyrek_sonu and periyot >= 4:
        # "4Ç" etiketi, aynı çeyreğin "Son 0:06" satırından SONRA
        # geldiğinde sıra bozuk görünüyordu (ölçüldü, ORL-DEN). Çeyreğin
        # sonu maçın da sonu — etiket bunu söylesin.
        return "Maç sonu", None
    if ceyrek_sonu:
        return f"{periyot}Ç", None
    if periyot >= 4 and saniye_kalan is not None and saniye_kalan <= AKIS_SON_SANIYE:
        etiket = "Son"
    elif periyot > 4:
        etiket = f"U{periyot - 4}"
    else:
        etiket = f"{periyot}Ç"
    if saniye_kalan is None:
        return etiket, None
    dk, sn = divmod(int(saniye_kalan), 60)
    return etiket, f"{dk}:{sn:02d}"


def akis_gercekleri_uret(g, gid, actions, ev_kod, dep_kod, kazanan, ceyrek_veri):
    """Akış olaylarını `akis_olay` kaydı olarak yazar.

    Her kayıt: {tip, periyot, saniye_kalan, zaman, saat, takim, oyuncu,
    sayi, ev_skor, dep_skor, fark}. Cümle KURULMUYOR — kalıp cumle.py'de,
    seçim derle.py'de."""
    seri = []   # (periyot, saniye, ev, dep, aksiyon)
    for a in actions:
        if a.get("scoreHome") in ("", None) or a.get("scoreAway") in ("", None):
            continue
        seri.append((a["period"], clock_saniye(a["clock"]),
                     int(a["scoreHome"]), int(a["scoreAway"]), a))
    if not seri:
        return

    kaynak = f"PlayByPlayV3:{gid}:akis"

    def yaz(tip, periyot, saniye, ev, dep, **ek):
        etiket, saat = _akis_zaman(periyot, saniye, ek.pop("ceyrek_sonu", False))
        veri = {
            "tip": tip, "periyot": periyot, "saniye_kalan": saniye,
            "zaman": etiket, "saat": saat,
            "ev_skor": ev, "dep_skor": dep, "fark": ev - dep,
        }
        veri.update(ek)
        g.ekle("akis_olay", veri, kaynak, "turetilmis")

    # --- 1) ÇEYREK SONLARI -------------------------------------------------
    # Kümülatif skor `ceyrek` gerçeğinde zaten hesaplı; oradan okuyoruz ki
    # aynı sayı iki yerde iki türlü çıkmasın.
    for c in sorted(ceyrek_veri, key=lambda x: x["periyot"]):
        if c["periyot"] >= 4:
            continue                      # son çeyreğin sonu = maç sonu
        ev, dep = c["kumulatif_ev"], c["kumulatif_dep"]
        onde = ev_kod if ev > dep else (dep_kod if dep > ev else None)
        yaz("ceyrek_sonu", c["periyot"], None, ev, dep,
            ceyrek_sonu=True, takim=onde,
            basa_bas=abs(ev - dep) <= AKIS_BASA_BAS)
        if c["periyot"] == 2 and abs(ev - dep) >= AKIS_DEVRE_FARK:
            yaz("devre_farki", 2, None, ev, dep, ceyrek_sonu=True,
                takim=onde, sayi=abs(ev - dep))

    # --- 2) ÇEYREK ÜSTÜNLÜĞÜ ----------------------------------------------
    # "Boston çeyreği 29-13 aldı · fark 4'e indi" — geri dönüşü olmayan
    # maçta akışın taşıyıcısı bu oluyor.
    for c in sorted(ceyrek_veri, key=lambda x: x["periyot"]):
        # 1. ÇEYREK HARİÇ: orada çeyrek skoru = kümülatif skor, yani
        # "çeyreği 31-23 aldı" ile "31-23 önde kapadı" aynı bilgi.
        if c["periyot"] == 1:
            continue
        ev_c, dep_c = c["ev_ceyrek_sayisi"], c["dep_ceyrek_sayisi"]
        if abs(ev_c - dep_c) < AKIS_SERI_ASGARI:
            continue
        ustun = ev_kod if ev_c > dep_c else dep_kod
        yaz("ceyrek_ustunlugu", c["periyot"], None,
            c["kumulatif_ev"], c["kumulatif_dep"], ceyrek_sonu=True,
            takim=ustun, ev_kod=ev_kod,
            sayi=max(ev_c, dep_c), rakip_sayi=min(ev_c, dep_c))

    # --- 3) EN BÜYÜK FARK --------------------------------------------------
    en_ev = max(seri, key=lambda x: x[2] - x[3])
    en_dep = max(seri, key=lambda x: x[3] - x[2])
    for periyot, saniye, ev, dep, _a in (en_ev, en_dep):
        fark = abs(ev - dep)
        if fark < AKIS_SERI_ASGARI:
            continue
        yaz("en_buyuk_fark", periyot, saniye, ev, dep,
            takim=(ev_kod if ev > dep else dep_kod), sayi=fark)

    # --- 4) SAYI SERİSİ (N-0) ---------------------------------------------
    # Tek tarafın kesintisiz sayı ürettiği en uzun aralık.
    en_iyi_seri = None
    i = 0
    while i < len(seri) - 1:
        _, _, ev0, dep0, _ = seri[i]
        j = i + 1
        ev_art = dep_art = 0
        while j < len(seri):
            _, _, ev1, dep1, _ = seri[j]
            de, dd = ev1 - ev0, dep1 - dep0
            if de > 0 and dd > 0:
                break
            ev_art, dep_art = de, dd
            j += 1
        uzunluk = max(ev_art, dep_art)
        if uzunluk >= AKIS_SERI_ASGARI and (en_iyi_seri is None or uzunluk > en_iyi_seri[0]):
            son = seri[j - 1]
            en_iyi_seri = (uzunluk, son, ev_art > dep_art)
        i = max(j - 1, i + 1)
    if en_iyi_seri:
        uzunluk, (periyot, saniye, ev, dep, _a), ev_mi = en_iyi_seri
        yaz("sayi_serisi", periyot, saniye, ev, dep,
            takim=(ev_kod if ev_mi else dep_kod), sayi=uzunluk)

    # --- 5) LİDER DEĞİŞİMLERİ: eşitlik, son liderlik, karar anı -----------
    onceki_fark = 0
    esitlikler, liderlikler = [], []
    for periyot, saniye, ev, dep, a in seri:
        fark = ev - dep
        if fark == 0 and onceki_fark != 0:
            esitlikler.append((periyot, saniye, ev, dep, a))
        elif fark != 0 and onceki_fark != 0 and (fark > 0) != (onceki_fark > 0):
            liderlikler.append((periyot, saniye, ev, dep, a))
        onceki_fark = fark

    if esitlikler:
        periyot, saniye, ev, dep, a = esitlikler[-1]
        yaz("esitlik", periyot, saniye, ev, dep,
            takim=a.get("teamTricode"))

    if liderlikler:
        periyot, saniye, ev, dep, a = liderlikler[-1]
        # Son liderlik değişimi KAZANANA aitse "liderlik bir daha
        # değişmedi" doğru; değilse bu satır kurulmaz.
        onde = ev_kod if ev > dep else dep_kod
        if onde == kazanan:
            yaz("liderlik", periyot, saniye, ev, dep,
                takim=onde,
                oyuncu=_dogru_oyuncu_adi(a.get("personId"), a.get("playerName") or ""))

    # --- 6) KARAR ANI: son sayı, fark küçükse -----------------------------
    # SKORU DEĞİŞTİREN SON AKSİYON — dizideki son kayıt değil. Periyot
    # sonu işaretleri de skor taşıyor ama oyuncusu yok; onu alınca satır
    # " son sayıyı buldu" diye adsız çıkıyordu (ölçüldü, 27 Aralık).
    son_sayi = None
    onceki = None
    for kayit in seri:
        if onceki is not None and (kayit[2], kayit[3]) != (onceki[2], onceki[3]):
            if kayit[4].get("personId"):
                son_sayi = kayit
        onceki = kayit
    if son_sayi is not None:
        son_periyot, son_saniye, son_ev, son_dep, son_a = son_sayi
        if abs(son_ev - son_dep) <= 5:
            yaz("karar_ani", son_periyot, son_saniye, son_ev, son_dep,
                takim=son_a.get("teamTricode"),
                oyuncu=_dogru_oyuncu_adi(son_a.get("personId"),
                                         son_a.get("playerName") or ""))

    # --- 7) FARK KORUNDU ---------------------------------------------------
    # `fark_serisi.esik_sonrasi_hic_asilmadi` ile AYNI hesap; burada
    # tekrarlamak yerine en yüksek aşılmamış eşiği okuyoruz.
    son_alti = {}
    for esik in (10, 15, 20):
        altinda = [x for x in seri if abs(x[2] - x[3]) < esik]
        if altinda:
            son = altinda[-1]
            # Son çeyreğin ortasından önce kapandıysa anlamlı.
            if son[0] <= 3 or (son[0] == 4 and son[1] >= 360):
                son_alti[esik] = son
    if son_alti:
        esik = max(son_alti)
        periyot, saniye, ev, dep, _a = son_alti[esik]
        yaz("fark_korundu", periyot, saniye, ev, dep, sayi=esik)


def fark_serisi_gercegi_uret(g, gid, actions, ev_kod, dep_kod, kazanan):
    """Maç boyu fark eğrisinden türetilmiş özet: en büyük fark, lider
    değişim sayısı, kapatılan en büyük açık, eşik geçişleri, kopma anı."""
    seri = []  # (periyot, saniye_kalan_periyotta, ev, dep)
    for a in actions:
        if a["scoreHome"] == "" or a["scoreAway"] == "":
            continue
        seri.append((a["period"], clock_saniye(a["clock"]), int(a["scoreHome"]), int(a["scoreAway"])))

    if not seri:
        return

    en_buyuk_ev_fark = max(seri, key=lambda x: x[2] - x[3])
    en_buyuk_dep_fark = max(seri, key=lambda x: x[3] - x[2])

    son_periyot = max(p for p, _, _, _ in seri)

    lider_degisim_sayisi = 0
    son_periyot_lider_degisimi = 0
    ilk_lider = None
    son_fark_isareti = 0
    son_periyot_fark_isareti = 0
    kazananin_en_kotu_ani = 0  # kazananın gördüğü en büyük (rakip lehine) açık
    for periyot, saniye, ev, dep in seri:
        fark = ev - dep
        if ilk_lider is None and fark != 0:
            ilk_lider = ev_kod if fark > 0 else dep_kod
        if fark != 0:
            isaret = 1 if fark > 0 else -1
            if son_fark_isareti != 0 and isaret != son_fark_isareti:
                lider_degisim_sayisi += 1
            son_fark_isareti = isaret

            # Aynı sayaç, SADECE maçın son periyodu için — "son çeyreği N
            # lider değişimiyle geçti" gibi bir cümle kurulabilsin diye.
            # Bunsuz, yazı üreticinin tek erişebildiği sayı maç GENELİNDEKİ
            # toplamdı ve bunu yanlışlıkla "sadece son çeyrekte" diye
            # yazdığı oldu (gerçekte doğru olay ama yanlış periyoda
            # atfedilmiş bir sayıydı).
            if periyot == son_periyot:
                if son_periyot_fark_isareti != 0 and isaret != son_periyot_fark_isareti:
                    son_periyot_lider_degisimi += 1
                son_periyot_fark_isareti = isaret

        kazanan_fark = fark if kazanan == ev_kod else -fark
        if kazanan_fark < kazananin_en_kotu_ani:
            kazananin_en_kotu_ani = kazanan_fark

    esik_gecisleri = {}
    for esik in (5, 8, 10, 15, 20):
        son_altina_dusme = None
        for periyot, saniye, ev, dep in seri:
            if abs(ev - dep) < esik:
                son_altina_dusme = (periyot, saniye)
        if son_altina_dusme:
            esik_gecisleri[str(esik)] = {
                "periyot": son_altina_dusme[0],
                "saniye_kalan": son_altina_dusme[1],
            }

    # Kopma anı: 3. çeyrek veya sonrasında fark >=20 olan ilk an, ve o andan
    # itibaren geride kalan taraf maç sonuna kadar 10+ sayılık bir seri
    # yapıp toparlanmadıysa. Kademeli kural, sert kesme yok (bkz. değer
    # skoru formülü bölüm 3, Y bileşeni).
    kopma_ani = None
    for i, (periyot, saniye, ev, dep) in enumerate(seri):
        if periyot >= 3 and abs(ev - dep) >= 20:
            en_yakin_sonrasi = min(
                (abs(e2 - d2) for _, _, e2, d2 in seri[i:]), default=abs(ev - dep)
            )
            if en_yakin_sonrasi >= 10:
                kopma_ani = {
                    "periyot": periyot,
                    "saniye_kalan": saniye,
                    "fark": ev - dep,
                    "taraf": ev_kod if ev > dep else dep_kod,
                }
            break

    g.ekle(
        "fark_serisi",
        {
            "en_buyuk_ev_farki": en_buyuk_ev_fark[2] - en_buyuk_ev_fark[3],
            "en_buyuk_dep_farki": en_buyuk_dep_fark[3] - en_buyuk_dep_fark[2],
            "lider_degisim_sayisi": lider_degisim_sayisi,
            "son_periyot_lider_degisimi": son_periyot_lider_degisimi,
            "ilk_lider": ilk_lider,
            "kazanan_en_buyuk_acigi": abs(kazananin_en_kotu_ani),
            "baski_altinda_hic_kalmadi": kazananin_en_kotu_ani == 0,
            "esik_sonrasi_hic_asilmadi": esik_gecisleri,
            "kopma_ani": kopma_ani,
        },
        f"PlayByPlayV3:{gid}:turetilmis",
        "turetilmis",
    )


# ---------------------------------------------------------------------------
# Puan durumu / derece / seri — LeagueGameLog'dan
# ---------------------------------------------------------------------------

# Kullanıcı düzeltmesi (25 Aralık gecesi): "sezonu galibiyetle açtı"
# niteleyicisi 31 maçlık bir sezonun 31. gecesinde de tetikleniyordu —
# gerçek bir gerçek (GSW sezonun ilk maçını gerçekten kazandı) ama
# Aralık ayında bunu haber gibi sunmak yanıltıcı, 2+ aylık bayat bir
# trivia. Bu niteleyici SADECE sezonun ilk birkaç haftasında (toplam
# maç sayısı bu eşiğin altındayken) "taze" sayılmalı.
SEZON_ACILISI_TAZE_MAC_SAYISI = 10


def puan_durumu_hesapla(oyun_gunlugu_ham, tarih_str):
    rows = oyun_gunlugu_ham["resultSets"][0]["rowSet"]
    headers = oyun_gunlugu_ham["resultSets"][0]["headers"]
    idx = {h: i for i, h in enumerate(headers)}

    takim_maclari = {}
    for r in rows:
        kod = r[idx["TEAM_ABBREVIATION"]]
        takim_maclari.setdefault(kod, []).append(r)

    kayitlar = {}
    for kod, maclar in takim_maclari.items():
        maclar_sirali = sorted(maclar, key=lambda r: r[idx["GAME_DATE"]])
        w = sum(1 for r in maclar_sirali if r[idx["WL"]] == "W")
        l = sum(1 for r in maclar_sirali if r[idx["WL"]] == "L")

        seri_tur = maclar_sirali[-1][idx["WL"]]
        seri_uzunluk = 0
        for r in reversed(maclar_sirali):
            if r[idx["WL"]] == seri_tur:
                seri_uzunluk += 1
            else:
                break

        # Maç ÖNCESİ seri — bugünkü maç hariç son N. "N maç aradan sonra
        # kazanan" niteleyicisi bunu gerektiriyor: bugün kazandıysa ve
        # maç öncesi mağlubiyet serisi vardıysa, o serinin uzunluğu.
        onceki_maclar = maclar_sirali[:-1]
        onceki_seri_tur, onceki_seri_uzunluk = None, 0
        if onceki_maclar:
            onceki_seri_tur = onceki_maclar[-1][idx["WL"]]
            for r in reversed(onceki_maclar):
                if r[idx["WL"]] == onceki_seri_tur:
                    onceki_seri_uzunluk += 1
                else:
                    break

        # Ev sahası kaydı — MATCHUP alanı "TAK vs. RAK" (ev) ya da
        # "TAK @ RAK" (deplasman) formatında. "Sahasındaki namağlup
        # unvanı" ve "iç sahada oynadığı N. maçı" bunu gerektiriyor.
        ev_maclari = [r for r in maclar_sirali if "vs." in r[idx["MATCHUP"]]]
        ev_w = sum(1 for r in ev_maclari if r[idx["WL"]] == "W")
        ev_l = sum(1 for r in ev_maclari if r[idx["WL"]] == "L")

        kayitlar[kod] = {
            "takim": kod,
            "galibiyet": w,
            "maglubiyet": l,
            "kazanma_yuzdesi": w / (w + l) if (w + l) else 0,
            "konferans": KONFERANS.get(kod),
            "seri_tur": "galibiyet" if seri_tur == "W" else "maglubiyet",
            "seri_uzunluk": seri_uzunluk,
            "onceki_seri_tur": "galibiyet" if onceki_seri_tur == "W" else ("maglubiyet" if onceki_seri_tur == "L" else None),
            "onceki_seri_uzunluk": onceki_seri_uzunluk,
            "sezon_ilk_mac_sonucu": "galibiyet" if maclar_sirali[0][idx["WL"]] == "W" else "maglubiyet",
            "ev_galibiyet": ev_w,
            "ev_maglubiyet": ev_l,
            "ev_mac_sayisi": len(ev_maclari),
            "bu_mac_evde_mi": "vs." in maclar_sirali[-1][idx["MATCHUP"]],
        }

    # Sıralama: kazanma yüzdesine göre (eşitlikte galibiyet sayısı)
    lig_sira = sorted(
        kayitlar.values(), key=lambda k: (-k["kazanma_yuzdesi"], -k["galibiyet"])
    )
    for i, k in enumerate(lig_sira, start=1):
        k["lig_sira"] = i

    for konferans in ("Doğu", "Batı"):
        konferans_takimlari = [
            k for k in lig_sira if k["konferans"] == konferans
        ]
        for i, k in enumerate(konferans_takimlari, start=1):
            k["konferans_sira"] = i

    return kayitlar


def derece_ve_seri_gerceklerini_uret(g, gid, ev_kod, dep_kod, puan_durumu):
    # Kullanıcı kararı (sezon başı susma kuralı): bir takımın oynadığı maç
    # sayısı SEZON_ACILISI_TAZE_MAC_SAYISI'nın (10) altındaysa derece
    # (konferans/lig sırası) ve seri anlamsız — kimin favori olduğunu,
    # kimin "zirvede" olduğunu, kimin "namağlup" kaldığını 1-9 maçlık bir
    # örneklemle söyleyemeyiz. Fact seviyesinde susturuluyor: konferans_sira/
    # lig_sira güvenilir değilse None, "seri" faktı hiç üretilmez — hem
    # kancalar (zirve/D/S) hem niteleyiciler hem LLM'e giden kompakt
    # gerçekler bu susmayı otomatik miras alır.
    for kod in (ev_kod, dep_kod):
        kayit = puan_durumu.get(kod)
        if not kayit:
            continue
        oynanan = kayit["galibiyet"] + kayit["maglubiyet"]
        guvenilir = oynanan >= SEZON_ACILISI_TAZE_MAC_SAYISI
        g.ekle(
            "derece",
            {
                "takim": kod,
                "galibiyet": kayit["galibiyet"],
                "maglubiyet": kayit["maglubiyet"],
                "derece_metni": f"{kayit['galibiyet']}-{kayit['maglubiyet']}",
                "konferans": kayit["konferans"],
                "konferans_sira": kayit["konferans_sira"] if guvenilir else None,
                "lig_sira": kayit["lig_sira"] if guvenilir else None,
                "sezon_guvenilir": guvenilir,
                # "N maç aradan sonra kazanan" — bugün kazandıysa VE
                # maç öncesi mağlubiyet serisindeyse anlamlı.
                "onceki_seri_tur": kayit["onceki_seri_tur"],
                "onceki_seri_uzunluk": kayit["onceki_seri_uzunluk"],
                "sezon_ilk_mac_sonucu": kayit["sezon_ilk_mac_sonucu"],
                # Ev sahası kaydı — "sahasındaki namağlup unvanı" /
                # "iç sahada oynadığı N. maçı" için.
                "ev_galibiyet": kayit["ev_galibiyet"],
                "ev_maglubiyet": kayit["ev_maglubiyet"],
                "ev_mac_sayisi": kayit["ev_mac_sayisi"],
                "bu_mac_evde_mi": kayit["bu_mac_evde_mi"],
            },
            "LeagueGameLog:turetilmis",
            "turetilmis",
        )
        if kayit["seri_uzunluk"] >= 2 and guvenilir:
            g.ekle(
                "seri",
                {
                    "takim": kod,
                    "tur": kayit["seri_tur"],
                    "uzunluk": kayit["seri_uzunluk"],
                },
                "LeagueGameLog:turetilmis",
                "turetilmis",
            )


# ---------------------------------------------------------------------------
# Gece seviyesi gerçekler
# ---------------------------------------------------------------------------


def gece_gerceklerini_uret(mac_ozetleri):
    """mac_ozetleri: [{gid, ev, dep, ev_skor, dep_skor, en_skorer, en_skorer_sayi,
                        en_yuksek_ceyrek_takim, en_yuksek_ceyrek_sayi, en_yuksek_ceyrek_no,
                        en_iyi_performans_oyuncu, en_iyi_performans_sayi}, ...]"""
    g = GercekUretici()

    farklar = [abs(m["ev_skor"] - m["dep_skor"]) for m in mac_ozetleri]
    yakin = sum(1 for f in farklar if f <= 5)
    farkli = sum(1 for f in farklar if f >= 20)

    g.ekle(
        "gece_ozet",
        {
            "toplam_mac": len(mac_ozetleri),
            "yakin_biten_mac_sayisi": yakin,
            "farkli_biten_mac_sayisi": farkli,
        },
        "turetilmis:gece",
        "turetilmis",
    )

    en_skorer = max(mac_ozetleri, key=lambda m: m["en_skorer_sayi"])
    en_dusuk_en_skorer = min(mac_ozetleri, key=lambda m: m["en_skorer_sayi"])
    g.ekle(
        "gece_en_skorerler",
        {
            "mac_basina_en_skorerler": [
                {
                    "mac_id": m["gid"],
                    "oyuncu": m["en_skorer"],
                    "sayi": m["en_skorer_sayi"],
                }
                for m in mac_ozetleri
            ],
            "gecenin_en_skoreri": en_skorer["en_skorer"],
            "gecenin_en_skoreri_sayi": en_skorer["en_skorer_sayi"],
            "en_dusuk_en_skorer_mac_id": en_dusuk_en_skorer["gid"],
            "en_dusuk_en_skorer_oyuncu": en_dusuk_en_skorer["en_skorer"],
            "en_dusuk_en_skorer_sayi": en_dusuk_en_skorer["en_skorer_sayi"],
        },
        "turetilmis:gece",
        "turetilmis",
    )

    en_ceyrek = max(mac_ozetleri, key=lambda m: m["en_yuksek_ceyrek_sayi"])
    g.ekle(
        "gece_en_yuksek_ceyrek",
        {
            "mac_id": en_ceyrek["gid"],
            "takim": en_ceyrek["en_yuksek_ceyrek_takim"],
            "periyot": en_ceyrek["en_yuksek_ceyrek_no"],
            "sayi": en_ceyrek["en_yuksek_ceyrek_sayi"],
        },
        "turetilmis:gece",
        "turetilmis",
    )

    en_iyi = max(mac_ozetleri, key=lambda m: m["en_iyi_performans_sayi"])
    g.ekle(
        "gece_en_iyi_bireysel",
        {
            "oyuncu": en_iyi["en_iyi_performans_oyuncu"],
            "mac_id": en_iyi["gid"],
            "sayi": en_iyi["en_iyi_performans_sayi"],
        },
        "turetilmis:gece",
        "turetilmis",
    )

    return g.kayitlar


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------


def mac_isle(gid, m, puan_durumu, sezon_sayilari_by_player_id=None, son10_dakika_by_id=None):
    g = GercekUretici()
    bt = m["box_traditional"]["boxScoreTraditional"]
    actions = m["play_by_play"]["game"]["actions"]

    ev_kod, dep_kod, ev_skor, dep_skor, kazanan = skor_gercegi_uret(g, gid, bt)

    ceyrek_gerceklerini_uret(g, gid, actions, ev_kod, dep_kod)

    oyuncu_stat_ham = oyuncu_stat_gerceklerini_uret(g, gid, bt)
    isim_haritasi = {pid: veri["oyuncu"] for pid, veri, _ in oyuncu_stat_ham}

    takim_stat_gerceklerini_uret(g, gid, bt)
    kadro_disi_gerceklerini_uret(g, gid, bt, son10_dakika_by_id)
    oyuncu_ceyrek_gerceklerini_uret(g, gid, actions, isim_haritasi)
    kilometre_gerceklerini_uret(g, gid, oyuncu_stat_ham, sezon_sayilari_by_player_id)
    an_gerceklerini_uret(g, gid, actions, isim_haritasi)
    fark_serisi_gercegi_uret(g, gid, actions, ev_kod, dep_kod, kazanan)
    # Akış olayları ÇEYREK gerçeklerinden sonra üretilmeli: kümülatif
    # skorları oradan okuyor, aynı sayı iki yerde iki türlü çıkmasın.
    akis_gercekleri_uret(
        g, gid, actions, ev_kod, dep_kod, kazanan,
        [k["veri"] for k in g.kayitlar if k["tur"] == "ceyrek"])
    derece_ve_seri_gerceklerini_uret(g, gid, ev_kod, dep_kod, puan_durumu)

    # Gece özeti için özet bilgiler
    en_skorer_veri = max(oyuncu_stat_ham, key=lambda t: t[1]["sayi"])
    ceyrekler = [k for k in g.kayitlar if k["tur"] == "ceyrek"]
    en_yuksek_ceyrek = max(
        ceyrekler,
        key=lambda k: max(k["veri"]["ev_ceyrek_sayisi"], k["veri"]["dep_ceyrek_sayisi"]),
    )
    if en_yuksek_ceyrek["veri"]["ev_ceyrek_sayisi"] >= en_yuksek_ceyrek["veri"]["dep_ceyrek_sayisi"]:
        eyc_takim = ev_kod
        eyc_sayi = en_yuksek_ceyrek["veri"]["ev_ceyrek_sayisi"]
    else:
        eyc_takim = dep_kod
        eyc_sayi = en_yuksek_ceyrek["veri"]["dep_ceyrek_sayisi"]

    ozet = {
        "gid": gid,
        "ev": ev_kod,
        "dep": dep_kod,
        "ev_skor": ev_skor,
        "dep_skor": dep_skor,
        "en_skorer": en_skorer_veri[1]["oyuncu"],
        "en_skorer_sayi": en_skorer_veri[1]["sayi"],
        "en_yuksek_ceyrek_takim": eyc_takim,
        "en_yuksek_ceyrek_sayi": eyc_sayi,
        "en_yuksek_ceyrek_no": en_yuksek_ceyrek["veri"]["periyot"],
        "en_iyi_performans_oyuncu": en_skorer_veri[1]["oyuncu"],
        "en_iyi_performans_sayi": en_skorer_veri[1]["sayi"],
    }

    return g.kayitlar, ozet


def gercekler_uret(tarih_str, zorla=False):
    hedef_dosya = GERCEK_DIZIN / f"{tarih_str}.json"
    if hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden üret).")
        return hedef_dosya

    import cek
    ham = cek.ham_oku(tarih_str)

    puan_durumu = puan_durumu_hesapla(ham["puan_durumu"], tarih_str)
    sezon_sayilari_by_player_id = sezon_sayilari_cikart(ham["oyuncu_ortalama"])
    son10_dakika_by_id = oyuncu_son10_dakika_ortalamasi(ham["oyuncu_ortalama"])

    maclar = {}
    mac_ozetleri = []
    for gid, m in ham["maclar"].items():
        kayitlar, ozet = mac_isle(gid, m, puan_durumu, sezon_sayilari_by_player_id, son10_dakika_by_id)
        maclar[gid] = kayitlar
        mac_ozetleri.append(ozet)

    gece_gercekleri = gece_gerceklerini_uret(mac_ozetleri)

    cikti = {
        "tarih": tarih_str,
        "uretildi": datetime.utcnow().isoformat() + "Z",
        "maclar": maclar,
        "gece_gercekleri": gece_gercekleri,
    }

    GERCEK_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya}")

    toplam = sum(len(v) for v in maclar.values()) + len(gece_gercekleri)
    print(f"Toplam gerçek sayısı: {toplam} ({len(maclar)} maç + gece özeti)")
    return hedef_dosya


if __name__ == "__main__":
    import argparse

    ayristirici = argparse.ArgumentParser()
    ayristirici.add_argument("tarih", help="YYYY-MM-DD")
    ayristirici.add_argument("--force", action="store_true")
    args = ayristirici.parse_args()
    gercekler_uret(args.tarih, zorla=args.force)
