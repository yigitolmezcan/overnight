"""
derle.py — OVERNIGHT boru hattının 7. adımı.

Girdi:  gercek/{tarih}.json + skor/{tarih}.json + taslak/{tarih}.json +
        ham/{tarih}.json + config/turk_oyuncular.json
Çıktı:  dist/{tarih}.json — overnight_v17.html'in fetch ile okuduğu tek
        dosya. Tasarım/HTML/CSS'e dokunmuyor, SADECE veri üretiyor.

İlke: burada da "sadece gerçeklerde olan yayınlanır" kuralı geçerli —
demodaki bazı bölümlerin (Gecenin notları'ndaki editoryal etiketler,
Geniş açı'daki gün-be-gün karşılaştırma, sakatlık haberi bayrağı)
karşılığı olan bir üretim adımı YOK — bu bölümler için veri
UYDURULMUYOR, JSON'da o anahtar hiç yazılmıyor / boş dönüyor ve HTML
tarafı o bölümü veri yoksa gizliyor.
"""

import colorsys
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from hesapla import gmsc, siralama_anahtari
from yaz import gece_kalip_plani, _mutlaka_ve_diger
from kalip_secici import _KILOMETRE_ONCELIK
from gercekler import _dogru_oyuncu_adi
import cumle


def _katla(ad):
    return "".join(c for c in unicodedata.normalize("NFKD", ad) if not unicodedata.combining(c)).lower()

KOK = Path(__file__).parent
GERCEK_DIZIN = KOK / "gercek"
SKOR_DIZIN = KOK / "skor"
TASLAK_DIZIN = KOK / "taslak"
HAM_DIZIN = KOK / "ham"
CONFIG_DIZIN = KOK / "config"
DIST_DIZIN = KOK / "dist"

# NBA takım kodu -> tam şehir+ad. box_traditional'dan da türetilebilir
# ama gece bazlı tekrar tekrar okumak yerine burada sabit tutmak daha
# basit — kodlar sabit (takım taşınması/yeniden adlandırma NBA'de son
# derece nadir, olursa elle güncellenir).
TAKIM_ADI = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}


# Kısa (şehir) ad — "Houston 118–112 Dallas" gibi tek satırlık skorlar
# için. Lakabı atarak türetmek güvenilir değil: "Portland Trail Blazers"
# lakabı İKİ kelime, "San Antonio Spurs" şehri iki kelime. Tablo elle
# yazıldı, 30 sabit değer.
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


# Takım renkleri — kart sekmesindeki 2px çizgi ve takım adının yanındaki
# ince şerit için. Logo YOK (kullanıcı kararı), renk şeridi kimliği
# taşıyor. Koyu zeminde okunur tonlar seçildi (BKN siyah yerine gri,
# SAS gümüş korunmuş).
TAKIM_RENK = {
    "ATL": "#E03A3E", "BOS": "#12A05C", "BKN": "#8A8F98", "CHA": "#4B36A8",
    "CHI": "#CE1141", "CLE": "#B3123F", "DAL": "#2E7BC4", "DEN": "#FEC524",
    "DET": "#E0384A", "GSW": "#2E6BD6", "HOU": "#CE1141", "IND": "#F2C230",
    "LAC": "#D2434A", "LAL": "#8B62D9", "MEM": "#6C8CC7", "MIA": "#C0304A",
    "MIL": "#1E9E5A", "MIN": "#3B7FD4", "NOP": "#B4975A", "NYK": "#F58426",
    "OKC": "#31A8E0", "ORL": "#1E8FD5", "PHI": "#3A8DDE", "PHX": "#B08BE8",
    "POR": "#E03A3E", "SAC": "#8A5FC7", "SAS": "#C4CED4", "TOR": "#CE1141",
    "UTA": "#3E7A5E", "WAS": "#3B7FD4",
}


def _yukle(dizin, tarih_str):
    # Ham veri TEK KAPIDAN okunuyor (cek.ham_oku): tam, gzip'li ya da
    # kırpılmış kopya — çağıranın hangisi olduğunu bilmesi gerekmiyor.
    if dizin == HAM_DIZIN:
        import cek
        return cek.ham_oku(tarih_str)
    dosya = dizin / f"{tarih_str}.json"
    if not dosya.exists():
        raise FileNotFoundError(f"{dosya} yok — önce ilgili boru hattı adımı çalıştırılmalı")
    return json.loads(dosya.read_text())


def _turk_oyunculari_yukle():
    dosya = CONFIG_DIZIN / "turk_oyuncular.json"
    if not dosya.exists():
        return []
    return json.loads(dosya.read_text()).get("oyuncular", [])


def _oyuncu_satiri(p, takim_kodu):
    s = p["statistics"]

    def dk(sn):
        return sn.split(":")[0] if ":" in sn else sn

    fg_yuzde = None
    if s["fieldGoalsAttempted"] >= 8 and s["fieldGoalsAttempted"] > 0:
        fg_yuzde = s["fieldGoalsMade"] / s["fieldGoalsAttempted"]

    return {
        # `id` oyuncu kartını açmak için: üç giriş de (saha, gecenin beşi
        # kartı, kutu skor tablosu) dist'teki `oyuncular` haritasına bu
        # anahtarla bakıyor.
        "id": p["personId"],
        "isim": _dogru_oyuncu_adi(p["personId"], f"{p['firstName']} {p['familyName']}".strip()),
        "takim": takim_kodu,
        # İlk beş / yedek ayrımı BoxScoreTraditionalV3'te zaten var:
        # ilk beşin `position` alanı dolu ("G"/"F"/"C"), yedeklerin boş.
        # Ek çağrı gerekmiyor.
        "ilk_bes": bool(p.get("position")),
        "min": dk(s["minutes"]),
        "pts": s["points"],
        "reb": s["reboundsTotal"],
        "ast": s["assists"],
        "stl": s["steals"],
        "blk": s["blocks"],
        "to": s["turnovers"],
        "fga": s["fieldGoalsAttempted"],
        "fta": s["freeThrowsAttempted"],
        "3pa": s["threePointersAttempted"],
        "fg": f"{s['fieldGoalsMade']}/{s['fieldGoalsAttempted']}",
        "3p": f"{s['threePointersMade']}/{s['threePointersAttempted']}",
        "ft": f"{s['freeThrowsMade']}/{s['freeThrowsAttempted']}",
        "pm": f"{'+' if s['plusMinusPoints'] >= 0 else ''}{int(s['plusMinusPoints'])}",
        "pm_ham": s["plusMinusPoints"],
        # "cold" — mekanik eşik (8+ şut denemesi, %25 altı isabet),
        # editoryal yorum değil, doğrudan görüntülenen sayılardan türer.
        "cold": fg_yuzde is not None and fg_yuzde <= 0.25,
    }


# Kullanıcı kararı (kutu skor tasarımı): kutu skor artık dipnot değil,
# ikinci ana bölüm. Üç işaretleme mekanik eşiklerden türer, editoryal
# yorum değil — (1) metinde geçen oyuncunun satırı, (2) aykırı istatistik
# (gerçekten nadir bir sayı), (3) kaybedenin en iyisi.
_AYKIRI_ESIKLERI = [
    (lambda s: s["fta"] >= 15, lambda s: f"{s['ft']} serbest atış"),
    (lambda s: s["to"] >= 8, lambda s: f"{s['to']} top kaybı"),
    (lambda s: s["3pa"] >= 15, lambda s: f"{s['3p']} üçlük denemesi"),
    (lambda s: s["blk"] >= 6, lambda s: f"{s['blk']} blok"),
    (lambda s: s["stl"] >= 6, lambda s: f"{s['stl']} top çalma"),
    (lambda s: s["pts"] >= 50, lambda s: f"{s['pts']} sayı"),
    (lambda s: s["reb"] >= 20, lambda s: f"{s['reb']} ribaund"),
    (lambda s: s["ast"] >= 15, lambda s: f"{s['ast']} asist"),
    (lambda s: abs(s["pm_ham"]) >= 35, lambda s: f"{s['pm']} +/-"),
    (lambda s: s["fga"] >= 10 and s["fg"].split("/")[0] == "0", lambda s: f"{s['fg']} saha içi"),
]


# Hangi ALAN aykırı — kartta o hücre sarı boyanacak (satırın tamamı değil).
_AYKIRI_ALAN = {
    0: "ft", 1: "to", 2: "3p", 3: "blk", 4: "stl",
    5: "pts", 6: "reb", 7: "ast", 8: "pm", 9: "fg",
}


def _aykiri_isaretle(oyuncu):
    """(aykırı_mı, hangi_alan) — alan adı kartta hücreyi işaretlemek için."""
    for i, (kosul, _) in enumerate(_AYKIRI_ESIKLERI):
        if kosul(oyuncu):
            return True, _AYKIRI_ALAN[i]
    return False, None


def _wtf_istatistigi_bul(ev_taraf, dep_taraf):
    """WTF = KARŞILAŞTIRMA (kullanıcı tanımı): bir sayının BAŞKA bir sayı
    yanında absürt durması. Tek başına bir etiket-değer çifti
    ("Jokić: 14/16 serbest atış") WTF DEĞİLDİR.

    Doğru örnek: "Adebayo tek başına 43 serbest atış denedi.
    Washington'ın tamamı 19."

    Karşılaştırma kurulamıyorsa None döner — boş bırakmak yanlış
    çıkarmaktan iyidir (kullanıcı kuralı)."""
    adaylar = []

    def topla(taraf, alan):
        return sum(o[alan] for o in taraf["oyuncular"])

    for benim, rakip in ((ev_taraf, dep_taraf), (dep_taraf, ev_taraf)):
        rakip_adi = rakip["takim"]
        benim_pts = topla(benim, "pts")
        # (1) Bir oyuncu, RAKİP TAKIMIN TAMAMINDAN fazla yapmış.
        for alan, esik, ad, fiil in (
            ("fta", 10, "serbest atış", "denedi"),
            ("3pa", 10, "üçlük", "denedi"),
            ("reb", 15, "ribaund", "aldı"),
        ):
            rakip_toplam = topla(rakip, alan)
            for o in benim["oyuncular"]:
                if o[alan] >= esik and o[alan] > rakip_toplam:
                    adaylar.append((
                        o[alan] - rakip_toplam,
                        f"{o['isim']} tek başına {o[alan]} {ad} {fiil}. "
                        f"{rakip_adi}'{cumle.iyelik_eki(rakip_adi)} tamamı {rakip_toplam}.",
                    ))
        # (2) Bir oyuncu, KENDİ TAKIMININ sayılarının en az %40'ını atmış.
        # Yüzde sayısı cümle SONUNDA — Türkçede sayıya gelen iyelik eki
        # okunuşa göre değişiyor ("42'si" ama "40'ı"), ekten kaçınmak
        # yanlış ek üretmekten güvenli.
        if benim_pts:
            for o in benim["oyuncular"]:
                pay = o["pts"] / benim_pts
                if o["pts"] >= 30 and pay >= 0.40:
                    adaylar.append((
                        int(pay * 100),
                        f"{o['isim']} {o['pts']} sayı attı. "
                        f"{benim['takim']}'{cumle.iyelik_eki(benim['takim'])} toplamı {benim_pts} — "
                        f"tek kişiden yüzde {int(pay * 100)}.",
                    ))

    if not adaylar:
        return None
    return max(adaylar, key=lambda x: x[0])[1]


def _ceyrek_serisi(gercekler, ev_kod):
    """([ev çeyrekleri], [deplasman çeyrekleri]) — periyot sırasına göre.

    Uzatma varsa listeye sadece oynanan uzatmalar ekleniyor (U1, U2 ...);
    başlıkları arayüz üretiyor. Veri yoksa iki boş liste döner ve şerit
    hiç çizilmez — uydurulmuş çeyrek yayına çıkmaz."""
    if not gercekler:
        return [], []
    kayitlar = sorted(
        (f["veri"] for f in gercekler if f["tur"] == "ceyrek"),
        key=lambda v: v["periyot"],
    )
    if not kayitlar:
        return [], []
    ev, dep = [], []
    for v in kayitlar:
        # `ev`/`dep` alanları kaydın kendi içinde; ev_kod ile eşleşmezse
        # taraflar ters bağlanmış olur, o yüzden kayda göre yerleştiriyoruz.
        if v.get("ev") == ev_kod:
            ev.append(v["ev_ceyrek_sayisi"])
            dep.append(v["dep_ceyrek_sayisi"])
        else:
            ev.append(v["dep_ceyrek_sayisi"])
            dep.append(v["ev_ceyrek_sayisi"])
    return ev, dep


def _box_score(ham_mac, metin="", kaybeden_kod=None, gercekler=None):
    bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    ev, dep = bt["homeTeam"], bt["awayTeam"]
    metin_katlanmis = _katla(metin or "")

    def taraf(takim):
        oyuncular = []
        for p in takim["players"]:
            if not p["statistics"]["minutes"]:
                continue
            satir = _oyuncu_satiri(p, takim["teamTricode"])
            satir["_gmsc"] = gmsc(p["statistics"])
            oyuncular.append(satir)
        oyuncular.sort(key=lambda o: -o["pts"])
        for o in oyuncular:
            o["gecti_mi"] = _katla(o["isim"].split()[-1]) in metin_katlanmis or _katla(o["isim"]) in metin_katlanmis
            o["aykiri"], o["aykiri_alan"] = _aykiri_isaretle(o)
        toplam = takim["statistics"]
        kod = takim["teamTricode"]
        oynamayanlar = [
            _dogru_oyuncu_adi(p["personId"], f"{p['firstName']} {p['familyName']}".strip())
            for p in takim["players"]
            if not p["statistics"]["minutes"] and p.get("comment")
        ]
        return {
            "takim": f"{takim['teamCity']} {takim['teamName']}",
            "kod": kod,
            "renk": TAKIM_RENK.get(kod, "#7E8794"),
            "skor": toplam["points"],
            "oynamayanlar": oynamayanlar,
            "oyuncular": oyuncular,
            "toplam": {
                "pts": toplam["points"], "reb": toplam["reboundsTotal"], "ast": toplam["assists"],
                "stl": toplam["steals"], "blk": toplam["blocks"], "to": toplam["turnovers"],
                "fg": f"{toplam['fieldGoalsMade']}/{toplam['fieldGoalsAttempted']}",
                "3p": f"{toplam['threePointersMade']}/{toplam['threePointersAttempted']}",
                "ft": f"{toplam['freeThrowsMade']}/{toplam['freeThrowsAttempted']}",
                # Ribaund ÜÇE ayrıldı (kullanıcı kararı): hücum ribaundu
                # iradeyi, savunma ribaundu rakibin isabetsizliğini
                # gösteriyor. Toplam da kalıyor — okuyucu toplamayla
                # uğraşmasın.
                "oreb": toplam["reboundsOffensive"],
                "dreb": toplam["reboundsDefensive"],
            },
        }

    ev_taraf, dep_taraf = taraf(ev), taraf(dep)
    # Çeyrek şeridi (kullanıcı kararı): skor bloğunun ALTINDA kendi
    # şeridinde. Kaynak `gercek`teki `ceyrek` kayıtları — ham verideki
    # LineScore alanları bu veri setinde boş geliyor.
    # TOPLAM SÜTUNU YOK: büyük skor zaten yukarıda.
    ev_taraf["ceyrek"], dep_taraf["ceyrek"] = _ceyrek_serisi(gercekler, ev_taraf["kod"])
    kilit = _kilit_istatistik(ham_mac, ev_taraf, dep_taraf)
    # Kritik anlar: çeyrek şeridinin ALTINDA, sekmelerden bağımsız (iki
    # takımı birden gösteriyor). Hak etmeyen maçta None → hiç çizilmez.
    kritik = _kritik_anlar(ham_mac, ev_taraf, dep_taraf)

    # Kullanıcı kuralı (son tur): işaret SADECE her sekmenin İLK
    # satırında. Ember çizgi kazanan takımın ilk satırında, mavi çizgi
    # kaybeden takımın ilk satırında. GmSc kriteri tamamen kalktı —
    # satırlar sayıya göre sıralı olduğu için ilk satır zaten o takımın
    # en çok sayı atanı; okuyucu kalanı kendi değerlendirir.
    tum = ev_taraf["oyuncular"] + dep_taraf["oyuncular"]
    for o in tum:
        o["gecti_mi"] = False
        o.pop("kaybedenin_en_iyisi", None)
        o.pop("_gmsc", None)
    kazanan_taraf, kaybeden_taraf = (
        (ev_taraf, dep_taraf) if ev_taraf["skor"] >= dep_taraf["skor"] else (dep_taraf, ev_taraf)
    )
    if kazanan_taraf["oyuncular"]:
        kazanan_taraf["oyuncular"][0]["gecti_mi"] = True
    if kaybeden_taraf["oyuncular"]:
        kaybeden_taraf["oyuncular"][0]["kaybedenin_en_iyisi"] = True

    # Kullanıcı kararı (geri alındı): tablo HER ZAMAN sayıya göre sıralı
    # kalır, işaretli oyuncu yerinden oynatılmaz. En üste taşıma denendi
    # ama en çok sayı atanın ikinci sıraya düşmesi tuhaf duruyordu;
    # işaret zaten satırın solundaki renk çizgisiyle görünüyor.

    wtf = _wtf_istatistigi_bul(ev_taraf, dep_taraf)

    return {"ev": ev_taraf, "dep": dep_taraf, "wtf": wtf, "kilit": kilit,
            "kritik": kritik}


def _takim_adi(kod):
    return TAKIM_ADI.get(kod, kod)


# Kullanıcı düzeltmesi: "Gecenin beşi" GmSc'ye göre düz bir liste değil,
# MEVKİYE göre bir takım olmalı — bölümün adı zaten bir takım vaat
# ediyor. En iyi iki guard, en iyi iki forward, en iyi center — GmSc'si
# daha yüksek bir oyuncunun bu yüzden elenmesi kabul. Bir mevkide
# yeterli oyuncu yoksa en yüksek GmSc'den tamamlanır.
GECENIN_BESI_SLOTLARI = ["G", "G", "F", "F", "C"]


# Kilometre eşiği → dayandığı istatistik alanı. None = birden fazla
# istatistiğe dayanıyor (triple-double gibi), hepsi kartta görünür.
_ESIK_ALANI = {
    "80_sayi": "pts", "60_sayi": "pts", "50_sayi": "pts", "40_sayi": "pts",
    "25_ribaund": "reb", "20_ribaund": "reb", "20_asist": "ast",
    "15_uclu": "3p", "10_uclu": "3p", "5_blok": "blk",
}
# Gecenin beşi kartında GÖRÜNEN istatistikler (büyük satır + ikincil satır).
_KARTTA_GORUNEN = {"pts", "reb", "ast", "3p", "fg", "ft", "min"}

_ESIK_OKUNUR = {
    "80_sayi": "80+ sayı", "60_sayi": "60+ sayı", "50_sayi": "50+ sayı", "40_sayi": "40+ sayı",
    "25_ribaund": "25+ ribaund", "20_ribaund": "20+ ribaund", "20_asist": "20+ asist",
    "15_uclu": "15+ üçlük", "10_uclu": "10+ üçlük", "5_blok": "5+ blok",
    "triple_double": "triple-double", "quadruple_double": "quadruple-double",
    "50_triple_double": "50+ sayılık triple-double",
}


# ---------------------------------------------------------------------------
# OYUNCU KARTI
# ---------------------------------------------------------------------------
#
# Kutu skor "bu gece 35 attı" diyor. Kart "bu 35, onun normalinin %39
# üstünde" diyor. Katılan şey BAĞLAM — kutu skorun asla veremediği şey.
#
# O gece OYNAYAN HER oyuncu için kart açılabiliyor, sadece öne çıkanlar
# için değil. Sezon verisi olmayan oyuncuda (sezonun ilk maçları)
# "sezon bağlamı" bölümü hiç kurulmuyor; kart iki bölümle kalıyor —
# uydurma ortalama yazmaktansa bölümü hiç çizmemek.
#
# Veri PlayerGameLogs'ta zaten var (Yükselen/Düşen aynı kaynaktan
# besleniyor), ek API çağrısı yok.
_POZISYON_ADI = {"G": "Guard", "F": "Forward", "C": "Center"}


def _oyuncu_kartlari(ham, tarih_str):
    """{personId: kart} — o gece oynayan her oyuncu."""
    gecmis = _oyuncu_gecmisi(ham)
    kartlar = {}
    for gid, hm in (ham.get("maclar") or {}).items():
        try:
            bt = hm["box_traditional"]["boxScoreTraditional"]
        except (KeyError, TypeError):
            continue
        ev, dep = bt["homeTeam"], bt["awayTeam"]
        # KISA (şehir) ad: kart başlığında tam ad iki satıra sarıyor ve
        # 118 oyuncu için dosyada gereksiz yer kaplıyor.
        skor_metni = (f"{TAKIM_KISA.get(ev['teamTricode'], ev['teamTricode'])} "
                      f"{ev['statistics']['points']} – "
                      f"{TAKIM_KISA.get(dep['teamTricode'], dep['teamTricode'])} "
                      f"{dep['statistics']['points']}")
        saat = _tsi_baslama(hm, tarih_str)
        for takim in (ev, dep):
            kod = takim["teamTricode"]
            for p in takim["players"]:
                st = p["statistics"]
                if not st["minutes"]:
                    continue
                pid = p["personId"]
                satir = _oyuncu_satiri(p, kod)
                kart = {
                    "id": pid,
                    "isim": satir["isim"],
                    "pos": _POZISYON_ADI.get(p.get("position") or "", ""),
                    "takim": f"{takim['teamCity']} {takim['teamName']}",
                    "takim_kod": kod,
                    "renk": TAKIM_RENK.get(kod, "#7E8794"),
                    "mac_skor": skor_metni,
                    "saat": saat,
                    "bu_gece": {
                        "pts": satir["pts"], "reb": satir["reb"], "ast": satir["ast"],
                        "min": satir["min"], "fg": satir["fg"], "3p": satir["3p"],
                        "ft": satir["ft"], "stl": satir["stl"], "blk": satir["blk"],
                        "to": satir["to"], "pm": satir["pm"],
                    },
                }
                onceki = gecmis.get(pid) or []
                if onceki:
                    sezon_ort = sum(x["sayi"] for x in onceki) / len(onceki)
                    son5 = onceki[-(FORM_MAC_SAYISI - 1):] + [
                        {"sayi": st["points"], "tarih": "bu gece"}]
                    son5_ort = sum(x["sayi"] for x in son5) / len(son5)
                    gosterilen = round(sezon_ort, 1)
                    son5_gosterilen = round(son5_ort, 1)
                    kart["sezon"] = {
                        "sezon_ort": gosterilen,
                        "son5_ort": son5_gosterilen,
                        # Yüzde EKRANDA YAZAN iki sayıdan türüyor. Ham
                        # değerlerden hesaplansaydı kart kendi içinde
                        # çelişirdi: "0.7 → 0.8" yazıp "%20" demek gibi
                        # (okuyucunun hesabı %14). Ölçüldü, 4 oyuncuda.
                        "yuzde": round((son5_gosterilen - gosterilen) / gosterilen * 100, 1)
                        if gosterilen else 0.0,
                        "son5": [{"sayi": x["sayi"],
                                  "ust": x["sayi"] > gosterilen,
                                  "bu_gece": x.get("tarih") == "bu gece"} for x in son5],
                    }
                kartlar[str(pid)] = kart
    return kartlar


def _gecenin_besi(ham, gercek_gece, id_by_gid, skor_by_gid):
    """Kullanıcı kararı (kart turu): ana sayfada sadece isim + mevki
    görünecek, ayrıntı karta taşınacak. Bu yüzden her oyuncu için kartın
    ihtiyacı olan HER ŞEY burada üretiliyor: tam istatistik satırı,
    hangi maçta oynadığı, o maçın skoru ve kart id'si (maça atlamak
    için), ve listeye girme sebebi."""
    aday = []
    for gid, ham_mac in ham["maclar"].items():
        bt = ham_mac["box_traditional"]["boxScoreTraditional"]
        ev, dep = bt["homeTeam"], bt["awayTeam"]
        mac_adi = f"{_takim_adi(ev['teamTricode'])} — {_takim_adi(dep['teamTricode'])}"
        mac_skor = f"{ev['statistics']['points']}–{dep['statistics']['points']}"
        # Gecenin beşi kartının üçüncü satırı için kompakt biçim
        # (kullanıcı kararı): "Golden State 125–120 San Antonio" —
        # kazanan önce, şehir adları (takım lakabı olmadan) sığsın diye.
        _ep, _dp = ev["statistics"]["points"], dep["statistics"]["points"]
        _kaz, _kay = (ev, dep) if _ep >= _dp else (dep, ev)
        # Takım KODU kullanılıyor: şehir adlarıyla ("Golden State 125–120
        # San Antonio") üçüncü satır 375px ekranda ikincil istatistiklerin
        # üstüne biniyordu. Satırın sarmalanmaması ve yazının okunur
        # kalması (10.5px) ancak bu kısaltmayla birlikte mümkün.
        mac_kisa = f"{_kaz['teamTricode']} {max(_ep, _dp)}–{min(_ep, _dp)} {_kay['teamTricode']}"
        kilo_by_oyuncu = {}
        for f in gercek_gece["maclar"].get(gid, []):
            if f["tur"] == "kilometre":
                kilo_by_oyuncu.setdefault(f["veri"]["oyuncu"], []).append(f["veri"].get("esik"))
        for taraf in (ev, dep):
            for p in taraf["players"]:
                st = p["statistics"]
                if not st["minutes"]:
                    continue
                satir = _oyuncu_satiri(p, taraf["teamTricode"])
                satir.update({
                    "pos": p.get("position") or "—",
                    "gmsc": gmsc(st),
                    "renk": TAKIM_RENK.get(taraf["teamTricode"], "#7E8794"),
                    # Ana sayfadaki satırın sağ ucu için tam takım adı
                    # (kullanıcı kuralı: kısaltma değil, "Houston Rockets").
                    "takim_adi": _takim_adi(taraf["teamTricode"]),
                    "mac": mac_adi,
                    "mac_skor": mac_skor,
                    "mac_kisa": mac_kisa,
                    "mac_id": id_by_gid.get(gid, f"a-{gid}"),
                    "_kilo": kilo_by_oyuncu.get(satir["isim"], []),
                })
                aday.append(satir)
    aday.sort(key=lambda o: -o["gmsc"])

    kullanilmis = set()
    slot_gid = {}
    mevki_eslesti = set()
    for slot_i, pos in enumerate(GECENIN_BESI_SLOTLARI):
        for i, o in enumerate(aday):
            if i not in kullanilmis and o["pos"] == pos:
                slot_gid[slot_i] = i
                kullanilmis.add(i)
                mevki_eslesti.add(slot_i)
                break
    for slot_i in range(len(GECENIN_BESI_SLOTLARI)):
        if slot_i in slot_gid:
            continue
        for i, o in enumerate(aday):
            if i not in kullanilmis:
                slot_gid[slot_i] = i
                kullanilmis.add(i)
                break

    # Gecenin uçları — "listeye girme sebebi" için.
    en_pts = max((o["pts"] for o in aday), default=0)
    en_reb = max((o["reb"] for o in aday), default=0)
    en_ast = max((o["ast"] for o in aday), default=0)

    sonuc = []
    for i in sorted(slot_gid):
        o = aday[slot_gid[i]]
        sebep = None
        o_kilo_var = bool(o["_kilo"])
        if o["_kilo"]:
            # En etkileyici eşiği seç — listedeki ilkini değil (5+ blok,
            # 38 sayının önüne geçiyordu).
            en_iyi = min(o["_kilo"], key=lambda k: _KILOMETRE_ONCELIK.index(k)
                         if k in _KILOMETRE_ONCELIK else 99)
            sebep = _ESIK_OKUNUR.get(en_iyi, en_iyi)
        elif o["pts"] == en_pts and en_pts:
            sebep = "gecenin en çok sayı atanı"
        elif o["reb"] == en_reb and en_reb:
            sebep = "gecenin en çok ribaund alanı"
        elif o["ast"] == en_ast and en_ast:
            sebep = "gecenin en çok asist dağıtanı"
        elif i in mevki_eslesti:
            # Listeye giriş sebebi zaten bu: mevkisinde gecenin en yüksek
            # GmSc'li oyuncusu. Boş bırakmaktansa doğru olanı yaz.
            sebep = "mevkisinde gecenin en iyisi"
        o.pop("_kilo", None)
        # GmSc siliniyor ama ÖNCE saklanıyor: renk çakışması çözümü
        # "düşük GmSc'li kayar" kuralına göre karar veriyor.
        o["_gmsc"] = o.pop("gmsc", 0)
        o["sebep"] = sebep
        # Kart etiketi (ad yanındaki küçük işaret) SADECE gerçek bir
        # kilometre taşı varsa çıkar — kullanıcı kararı: "varsa küçük bir
        # işaret". Uzun açıklamalar (mevki/gece lideri) etiket değil,
        # onlar `sebep` alanında kalıyor.
        # Kullanıcı kuralı: bir kilometre etiketi, dayandığı istatistik
        # kartta GÖRÜNMÜYORSA ya sayıyı kendi içinde taşır ("5 BLOK") ya
        # da hiç çıkmaz. Kartta görünenler: sayı/ribaund/asist (büyük
        # satır) ve dakika/FG/3P/FA (ikincil satır). Blok ve çalma
        # görünmüyor — onlara dayanan etiket sayısını kendi yazar.
        o["etiket"] = None
        if o_kilo_var and sebep:
            # Kullanıcı kararı (b şıkkı): dayandığı istatistik kartta
            # GÖRÜNMÜYORSA etiket HİÇ çıkmaz. (a) şıkkı denendi — blok
            # sütunu ikincil satıra eklenince satır 375px'te beş oyuncuda
            # birden taşıyordu (en fazla 31px) ve sığdırmak için puntoyu
            # 10px'in altına indirmek gerekiyordu. Sayısı görünmeyen
            # etiket yerine hiç etiket olmaması tercih edildi.
            alan = _ESIK_ALANI.get(en_iyi)
            if alan is None or alan in _KARTTA_GORUNEN:
                o["etiket"] = sebep
        # Ana sayfadaki kompakt satır için hazır alanlar (istatistik yok).
        o["num"], o["unit"] = o["pts"], "pts"
        o["st"] = f"{o['reb']} REB · {o['ast']} AST"
        sonuc.append(o)
    # Renk çakışması: sahada üç oyuncunun ikisi mor olduğunda üçü aynı
    # takımdanmış gibi duruyordu (18 Aralık: Dončić, DeRozan, LeBron).
    renk_cakismasini_coz(sonuc)
    for o in sonuc:
        o.pop("_gmsc", None)
    return sonuc


def _turkler(ham, turk_oyunculari, id_by_gid=None, skor_by_gid=None):
    """Türk oyuncularının o geceki durumu.

    NBA API isimleri aksansız döner ("Alperen Sengun") — düz karşılaştırma
    hiçbir zaman eşleşmiyordu (gerçek üretim bug'ı). Aksan-katlanmış
    karşılaştırma kullanılıyor.

    Dönen her kayıt `oynadi` taşır:
      True  → tam istatistik + maçın kartına atlamak için mac_id
      False → takımı o gece OYNADI ama oyuncu sahaya çıkmadı
    Takımı hiç maç yapmadıysa oyuncu listeye HİÇ girmez — "oynamadı"
    demek yanlış olurdu, ortada maç yok.
    """
    id_by_gid = id_by_gid or {}
    isim_by_takim = {_katla(o["ad"]): o["takim"] for o in turk_oyunculari}
    if not isim_by_takim:
        return []
    ad_by_katlanmis = {_katla(o["ad"]): o["ad"] for o in turk_oyunculari}

    oynayan_takimlar = set()
    bulunanlar = {}
    for gid, ham_mac in ham["maclar"].items():
        bt = ham_mac["box_traditional"]["boxScoreTraditional"]
        ev, dep = bt["homeTeam"], bt["awayTeam"]
        ev_p, dep_p = ev["statistics"]["points"], dep["statistics"]["points"]
        kaz, kay = (ev, dep) if ev_p >= dep_p else (dep, ev)
        mac_kisa = (f"{TAKIM_KISA.get(kaz['teamTricode'], kaz['teamTricode'])} "
                    f"{max(ev_p, dep_p)}–{min(ev_p, dep_p)} "
                    f"{TAKIM_KISA.get(kay['teamTricode'], kay['teamTricode'])}")
        for taraf in (ev, dep):
            oynayan_takimlar.add(taraf["teamTricode"])
            for p in taraf["players"]:
                katlanmis = _katla(f"{p['firstName']} {p['familyName']}".strip())
                if katlanmis not in isim_by_takim:
                    continue
                if not p["statistics"]["minutes"]:
                    continue
                satir = _oyuncu_satiri(p, taraf["teamTricode"])
                satir.update({
                    "oynadi": True,
                    "renk": TAKIM_RENK.get(taraf["teamTricode"], "#7E8794"),
                    "takim_adi": _takim_adi(taraf["teamTricode"]),
                    "mac_kisa": mac_kisa,
                    "mac_id": id_by_gid.get(gid, f"a-{gid}"),
                })
                bulunanlar[katlanmis] = satir

    sonuc = list(bulunanlar.values())
    # Takımı oynamış ama kendisi sahaya çıkmamış olanlar.
    for katlanmis, kod in isim_by_takim.items():
        if katlanmis in bulunanlar or kod not in oynayan_takimlar:
            continue
        sonuc.append({
            "isim": ad_by_katlanmis[katlanmis], "takim": kod, "oynadi": False,
            "takim_adi": _takim_adi(kod), "renk": TAKIM_RENK.get(kod, "#7E8794"),
        })
    # Oynayanlar önce, sonra ada göre — sıra geceden geceye zıplamasın.
    sonuc.sort(key=lambda o: (not o["oynadi"], o["isim"]))
    return sonuc


_AYLAR_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
# Ay adlarının bulunma hâli eki, ünlü uyumu + son ünsüz sertliğine göre.
# Tablo elle yazıldı: on iki sabit kelime için genel ek üretecini
# çağırmaktan daha az kırılgan ve gözle doğrulanabilir.
_AY_BULUNMA = {"Ocak": "ta", "Şubat": "ta", "Mart": "ta", "Nisan": "da",
               "Mayıs": "ta", "Haziran": "da", "Temmuz": "da", "Ağustos": "ta",
               "Eylül": "de", "Ekim": "de", "Kasım": "da", "Aralık": "ta"}


def _tarih_tr(iso, bulunma=False):
    from datetime import datetime as _dt
    g = _dt.strptime(iso, "%Y-%m-%d")
    ay = _AYLAR_TR[g.month - 1]
    if bulunma:
        return f"{g.day} {ay}'{_AY_BULUNMA[ay]}"
    return f"{g.day} {ay}"


def _ve_listesi(adlar):
    if len(adlar) == 1:
        return adlar[0]
    return ", ".join(adlar[:-1]) + " ve " + adlar[-1]


def _turkler_bekleyen(ham, turk_oyunculari):
    """O gece sahaya Türk oyuncu çıkmadıysa bölümün en altında görünecek
    satır: kimler ve bir sonraki maç ne zaman.

    Kullanıcı kuralı gereği tarih uydurulmaz — `ham["sonraki_maclar"]`
    yoksa (eski ham dosyalarda yok) cümle tarihsiz kurulur. En yakın
    maçı olan takımın oyuncuları anılır; sezonu bitmiş (ileride maçı
    olmayan) takımların oyuncuları listeye girmez.
    """
    if not turk_oyunculari:
        return None
    sonraki = ham.get("sonraki_maclar") or {}
    adaylar = [(sonraki[o["takim"]], o["ad"]) for o in turk_oyunculari if sonraki.get(o["takim"])]
    if not adaylar:
        isimler = [o["ad"].split()[-1] for o in turk_oyunculari][:2]
        return {"isimler": isimler, "tarih": None,
                "metin": "Bu gece Türk oyuncu sahaya çıkmadı."}
    # Oyuncuları KENDİ sonraki maç tarihlerine göre grupla. Eskiden
    # sadece en erken tarihe sahip olanlar anılıyordu ve diğerleri
    # cümleden düşüyordu (liste iki kişiye inince Bona her seferinde
    # kayboluyordu). Herkes anılır, ama tarih uydurulmaz — kimin maçı
    # ne zamansa o yazılır.
    tarihe_gore = {}
    for gun, ad in sorted(adaylar):
        tarihe_gore.setdefault(gun, []).append(ad.split()[-1])
    parcalar = [f"{_ve_listesi(adlar)} {_tarih_tr(gun, bulunma=True)}"
                for gun, adlar in sorted(tarihe_gore.items())]
    en_erken = min(tarihe_gore)
    tum_isimler = [ad for adlar in tarihe_gore.values() for ad in adlar]
    if len(parcalar) == 1:
        cumle = f"{parcalar[0]} sahaya çıkıyor."
    else:
        cumle = f"{', '.join(parcalar)} sahaya çıkıyor."
    return {
        "isimler": tum_isimler,
        "tarih": _tarih_tr(en_erken, bulunma=True),
        "metin": f"Bu gece Türk oyuncu sahaya çıkmadı. {cumle}",
    }


def _why_metni(kalip_girdisi):
    """archwhy/why-inline etiketi — okuyucuya gösterilen kısa gerekçe.
    Kanca 'H' (doğrudan, kancasız) olduğunda kanca_gerekce İÇSEL bir
    açıklama ("tüm uygun kategoriler kullanıldı") — okuyucuya değil
    koda hitap ediyor, UI'da gösterilmemeli. O durumda ilk niteleyici
    varsa o kullanılır, o da yoksa etiket boş kalır (UI gizler)."""
    if kalip_girdisi.get("kanca_harf") != "H":
        return kalip_girdisi.get("kanca_gerekce", "")
    niteleyiciler = kalip_girdisi.get("niteleyiciler") or []
    return niteleyiciler[0] if niteleyiciler else ""


def _brief_ikonu(gerekce_metni):
    gerekce_metni = (gerekce_metni or "").lower()
    if "geri dönüş" in gerekce_metni or "farktan" in gerekce_metni:
        return "comeback"
    if "yıldız yokluğu" in gerekce_metni:
        return "absence"
    if "seri" in gerekce_metni:
        return "streak"
    if "sıra" in gerekce_metni or "konferans" in gerekce_metni:
        return "standings"
    return "default"


# Maçın TSİ başlama saati.
#
# Kaynak: BoxScoreSummaryV2 → GameSummary → GAME_STATUS_TEXT ("5:00 pm ET").
# BİTİŞ SAATİ NBA VERİSİNDE YOK ve tahmin EDİLMİYOR — "doğrulanmamış
# cümle yayınlanmaz" kuralı saatler için de geçerli. Başlama saati
# gecenin akışını zaten veriyor.
#
# Saat dilimi ZoneInfo ile çevriliyor, sabit fark eklenerek DEĞİL: ABD
# yaz saati (mart–kasım) NBA sezonuna denk geliyor ve fark kışın 8,
# yazın 7 saat. Sabit +8 yazsaydık ekim ve nisan maçları bir saat kayardı.
_ET = "America/New_York"
_TSI = "Europe/Istanbul"


def _tsi_baslama_dt(ham_mac, tarih_str):
    """TSİ başlama ANI (datetime) — çevrilemezse None.

    TAM AN gerekiyor, saat dizesi değil: gece takvim gününü aşıyor.
    TSİ 23:30'da başlayan maç gecenin İLKİ, 06:00'da başlayan KAPANIŞI.
    Sıralama "HH:MM" dizesine göre yapıldığında 23:30 en sona düşüyordu
    ve "1290 dakika" gibi bir süre çıkıyordu — sistem 23:30 ile 02:00
    arasını 21,5 saat sanıyordu (gerçekte 2,5 saat).
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        return None
    try:
        gs = next(rs for rs in ham_mac["box_summary"]["resultSets"]
                  if rs["name"] == "GameSummary")
        ham = dict(zip(gs["headers"], gs["rowSet"][0])).get("GAME_STATUS_TEXT", "")
        m = re.match(r"\s*(\d{1,2}):(\d{2})\s*([ap])m", str(ham), re.I)
        if not m:
            return None
        saat, dk, yarim = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        if yarim == "p" and saat != 12:
            saat += 12
        if yarim == "a" and saat == 12:
            saat = 0
        gun = datetime.strptime(tarih_str, "%Y-%m-%d")
        et = gun.replace(hour=saat, minute=dk, tzinfo=ZoneInfo(_ET))
        # ET tarihi NBA'in maç günü; TSİ karşılığı kendiliğinden doğru
        # takvim gününe düşüyor (15:30 ET → 23:30 aynı gün, 18:00 ET →
        # 02:00 ertesi gün). Kural bu yüzden koda ayrıca yazılmıyor.
        return et.astimezone(ZoneInfo(_TSI))
    except Exception:
        return None


def _tsi_baslama(ham_mac, tarih_str):
    """'01:00' — gösterim için. Sıralama ASLA buna göre yapılmaz."""
    an = _tsi_baslama_dt(ham_mac, tarih_str)
    return an.strftime("%H:%M") if an else None


def _sure_metni(dakika):
    """"6,5 saat" — "1290 dakika" bir insana hiçbir şey söylemiyordu."""
    if not dakika or dakika <= 0:
        return None
    saat = dakika / 60
    if saat < 1:
        return f"{int(round(dakika))} dakika"
    tam = round(saat * 2) / 2          # yarım saate yuvarla
    metin = f"{tam:.1f}".replace(".0", "").replace(".", ",")
    return f"{metin} saat"


# ---------------------------------------------------------------------------
# KİLİT İSTATİSTİK — maçın NEDEN kazanıldığını söyleyen tek takım farkı.
# ---------------------------------------------------------------------------
#
# Metin maçın hikâyesini anlatıyor ama sebebini anlatmıyor: "36 asiste
# karşı 20 asist" maçın sebebini veriyor ve hiçbir cümlede geçmiyor.
#
# WTF İstatistiği ile KARIŞTIRILMAMALI: WTF oyuncu düzeyinde ve absürt
# ("tek başına 43 serbest atış"), kilit istatistik TAKIM düzeyinde ve
# açıklayıcı. Farklı işler, ikisi bir arada durabilir.
#
# (alan, okunur ad, eşik, çok_olan_kazanır)
KILIT_ESIKLERI = [
    ("reb",   "ribaund",              15, True),
    ("oreb",  "hücum ribaundu",        8, True),
    ("3pm",   "üçlük",                 8, True),
    ("ast",   "asist",                12, True),
    ("to",    "top kaybı",             8, False),   # AZ olan kazanır
    ("fta",   "serbest atış denemesi", 15, True),
    ("pts2c", "ikinci şans sayısı",    15, True),
    ("paint", "boyalı alan sayısı",    20, True),
]


# ---------------------------------------------------------------------------
# KRİTİK ANLAR — maçı kimin kazandırdığını söyleyen tek istatistik.
# ---------------------------------------------------------------------------
#
# Kutu skorda görünmüyor: NBA'in kendi sitesinde ayrı sayfaya gömülü,
# başka yerde hiç yok. "Son 5 dakikada Curry 11, Booker 2 sayı attı"
# 38'e 33'ten çok daha fazlasını anlatıyor.
#
# TANIM (NBA'in standart clutch tanımı): son 5 dakika VE varsa
# uzatmaların tamamı İÇİNDE, farkın 5 sayı ve altında OLDUĞU süre.
# Maçın son 5 dakikası değil — fark 12'ye çıktıysa o dakikalar
# sayılmaz, tekrar 4'e inerse yeniden saymaya başlar.
KRITIK_SON_DAKIKA = 5
KRITIK_FARK = 5
# Tek görünürlük kuralı. 26 farkla biten maçta kritik süre sıfırdır,
# bölüm hiç açılmaz. "Final farkı ≤5" gibi bir ek koşul YOK: uzatmaya
# gidip 12 farkla biten maçta da kritik anlar yaşanmıştır.
KRITIK_ASGARI_SURE_SN = 120
KRITIK_OYUNCU_SAYISI = 2
# Satır ancak GERÇEKTEN sayı üreten oyuncu için kuruluyor (kullanıcı
# kuralı). Düşük ya da sıfır sayılı satır bilgi taşımıyor: bloğun
# vaadi "maçı kim kazandırdı", "kim oradaydı" değil. Eşiği geçen tek
# oyuncu varsa tek satır çıkar; hiç yoksa blok hiç görünmez.
KRITIK_ASGARI_SAYI = 4

_SAAT_DESENI = re.compile(r"PT(\d+)M([\d.]+)S")


def _pbp_saniye(saat):
    """"PT02M38.00S" → periyotta KALAN saniye."""
    m = _SAAT_DESENI.match(str(saat or ""))
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def _mac_saniyesi(periyot, kalan):
    """Maç başından itibaren GEÇEN saniye. Çeyrek 12 dk, uzatma 5 dk."""
    if periyot <= 4:
        return (periyot - 1) * 720 + (720 - kalan)
    return 4 * 720 + (periyot - 5) * 300 + (300 - kalan)


# Kritik pencerenin başlangıcı: 4. çeyreğin bitimine 5 dakika kala.
KRITIK_BASLANGIC_SN = 3 * 720 + (720 - KRITIK_SON_DAKIKA * 60)


# ---------------------------------------------------------------------------
# MAÇ AKIŞI — dört satırın seçimi
# ---------------------------------------------------------------------------
#
# Olaylar gercekler.py'de üretiliyor, cümleleri cumle.py'de sabit
# kalıplarla kuruluyor. Burada YALNIZ SEÇİM var (kullanıcı kuralları):
#   - her maçtan 4 satır (az olay varsa 3)
#   - kronolojik sıra
#   - biri MUTLAKA kritik an olsun (ember): son saniye basketi,
#     liderliğin son kez değiştiği an, ya da kopma anı
#   - aynı olay tipi bir maçta iki kez kullanılmaz
# KATMANA GÖRE SATIR SAYISI (kullanıcı kararı). Üç katman görsel olarak
# da ayrışmalı; akış hiyerarşiyi bozmamalı, güçlendirmeli:
#   Mutlaka bil → başlık + 4 satır
#   Göz at      → başlık + 2 satır  (kritik an + bir bağlam satırı)
#   Bunları geç → tek satır, akış YOK
# Dört satırla "Göz at" bloğu "Mutlaka bil" ağırlığına çıkıyor ve katman
# farkı kayboluyordu.
AKIS_SATIR_SAYISI = 4
AKIS_GOZAT_SATIR = 2
# TABAN İKİ SATIR. Şekil modelinde yuvalar hikâyenin parçası; üçü
# dolmadığında bloğu tamamen boş bırakmak, iki satırlık TUTARLI bir
# hikâyeyi çöpe atmak demek (ölçüldü: üç blok bu yüzden akışsız kaldı).
AKIS_ASGARI_SATIR = 2
# Kritik an adaylığı — önce gelen kazanır.
AKIS_KRITIK_SIRASI = ("karar_ani", "liderlik", "sayi_serisi", "en_buyuk_fark")
# Kritik dışında kalan satırlar için tercih sırası. Maçın şekline göre
# hangisinin bulunacağı değişiyor; liste yalnız ÖNCELİK veriyor.
AKIS_DOLGU_SIRASI = ("ceyrek_sonu", "ceyrek_ustunlugu", "esitlik",
                     "devre_farki", "en_buyuk_fark", "sayi_serisi",
                     "fark_korundu", "en_etkili")


def _akis_sirasi(o):
    """Kronolojik anahtar. Çeyrek sonlarında saat yok — periyodun SONU
    sayılıyor (saniye_kalan=0), yoksa çeyrek sonu o çeyrekteki anların
    önüne düşerdi."""
    # AYNI SANİYEDE İKİ OLAY olabiliyor (eşitlik ve hemen ardından karar
    # basketi ikisi de 0:06'da). Toplam skor eşitlikte ayırıcı: sayı
    # artmışsa o olay sonradır (ölçüldü, 27 Aralık ORL-DEN).
    return (o.get("periyot") or 0, -(o.get("saniye_kalan") or 0),
            (o.get("ev_skor") or 0) + (o.get("dep_skor") or 0))


AKIS_KALIP_LIMITI = 2       # aynı CÜMLE KALIBI gecede en fazla bu kadar
# GERİ DÖNÜŞ eşiği: kazananın bir ara düştüğü açık bu kadarsa maç bir
# "geri dönüş" hikâyesidir.
AKIS_DONUS_ESIGI = 12       # kazananın düştüğü açık (kullanıcı: 12+)
AKIS_KOPMA_ESIGI = 12       # fark bir noktadan sonra bunun altına inmediyse
AKIS_KRITIK_FARK_TAVANI = 15   # fark bunu geçtikten sonra hiçbir olay kritik olamaz
AKIS_SON_DK_SANIYE = 60.0      # "son 1 dakika"
AKIS_SON_DK_FARK = 3           # ya da fark bu kadarsa: son saniye maçı


# ---------------------------------------------------------------------------
# MAÇ ŞEKLİ VE SABİT YUVALAR
# ---------------------------------------------------------------------------
#
# KÖK SEBEP (kullanıcı teşhisi): satırlar BAĞIMSIZ seçiliyordu. Her olay
# kendi puanıyla seçilip zamana göre diziliyordu; hiçbir yerde "bu maçın
# hikâyesi ne" modeli yoktu. Sonuç: satırlar tek tek doğru, birlikte
# saçma —
#   "New York farkı 18'e çıkardı" → "New York skoru eşitledi"
#   (ikisi de doğru; ilkinde NY önde, ikincisinde geriden eşitliyor)
#   kritik işaret 108-108 beraberliğinde, oysa maç 13 farkla bitti.
#
# ÇÖZÜM: blok kurulmadan önce maçın ŞEKLİ belirleniyor; her şeklin SABİT
# YUVALARI var ve olaylar o yuvalara yerleşiyor. Bu tek kural dört şeyi
# birden çözüyor: kronoloji (yuvalar sıralı), son satırın sonucu
# açıklaması (4. yuva öyle tanımlı), kritik anın doğruluğu (şeklin kendi
# tanımından geliyor, ayrı kural yok) ve ardışık çelişki (yuvalar
# birbirini takip ediyor, aynı durumu iki kez anlatamaz).
#
# Yuva bir SORGU: (tip, filtre). Karşılığı yoksa yuva boş kalır; blok
# AKIS_ASGARI_SATIR'ın altına düşerse çizilmez.
# Değişmez denetiminin tanı kaydı — sadece rapor için, ürüne girmiyor.
SON_DENETIM = {}
DENETIM_LOG = []

AKIS_SEKILLERI = ("geri_donus", "son_saniye", "kopma", "bastan_sona")


def _akis_sekli(gercekler, olaylar, skor):
    """Maçın şekli. ÖNCELİK SIRASI SABİT (kullanıcı kuralı) — bir maç
    birden fazla şekle uyabilir, İLK UYAN seçilir:

      1. SON SANİYE — son 1 dakikada liderlik değişti ya da fark <= 3
      2. GERİ DÖNÜŞ — kazanan bir ara 12+ geride kaldı
      3. KOPMA      — fark bir noktadan sonra 12'nin altına inmedi
      4. BAŞTAN SONA— kazanan hiç geride kalmadı

    Öncesinde öncelik yoktu ve son saniyede biten bir maç "geri dönüş"e
    düşüyordu: 26 Aralık Utah-Detroit 131-129 son saniyede bitti ama
    kritik işaret 3. çeyreğe kaydı."""
    fs = next((f["veri"] for f in gercekler if f["tur"] == "fark_serisi"), {}) or {}
    fark = abs((skor or {}).get("fark") or 0)
    tipler = {o["tip"] for o in olaylar}

    son_dk = any(o["tip"] in ("liderlik", "esitlik", "karar_ani")
                 and (o.get("periyot") or 0) >= 4
                 and (o.get("saniye_kalan") or 999) <= AKIS_SON_DK_SANIYE
                 for o in olaylar)
    if son_dk or fark <= AKIS_SON_DK_FARK:
        return "son_saniye"
    if (fs.get("kazanan_en_buyuk_acigi") or 0) >= AKIS_DONUS_ESIGI:
        return "geri_donus"
    esik = (fs.get("esik_sonrasi_hic_asilmadi") or {}).get(str(AKIS_KOPMA_ESIGI))
    if fs.get("kopma_ani") or esik or fark >= AKIS_KOPMA_ESIGI:
        return "kopma"
    return "bastan_sona"


def _yuva_planla(sekil, kazanan, kaybeden):
    """[(yuva_adi, [(tip, filtre), ...], kritik_mi)] — şeklin sabit yuvaları."""
    K = lambda o: o.get("takim") == kazanan
    Y = lambda o: o.get("takim") == kaybeden
    H = lambda o: True
    ilk_yari = lambda o: (o.get("periyot") or 0) <= 2
    son_ceyrek = lambda o: (o.get("periyot") or 0) >= 4

    if sekil == "geri_donus":
        return [
            ("kaybedenin_farki", [("en_buyuk_fark", Y)], False),
            # Dönüşün başı: kazananın çeyrek üstünlüğü ya da serisi.
            # İkisi de öne geçişten ÖNCE değilse devre satırı kullanılıyor —
            # dönüşün başladığı yer orası sayılır.
            ("donusun_basi", [("ceyrek_ustunlugu", K), ("sayi_serisi", K),
                              ("devre_farki", H),
                              ("ceyrek_sonu", lambda o: o.get("periyot") == 2)], False),
            # ÖNE GEÇİŞ bir LİDERLİK DEĞİŞİMİ olmalı. Eşitliği yedek
            # olarak kabul etmek, 12 farkla biten bir maçta beraberliği
            # "maçın belirlendiği an" diye işaretliyordu (28 Ocak).
            # Liderlik olayı yoksa yuva boş kalıyor ve kritik işaret
            # sonuç satırına düşüyor.
            ("one_gecis", [("liderlik", K)], True),
            ("sonuc", [("karar_ani", H), ("fark_korundu", H), ("kopus", H),
                       ("en_etkili", H),
                       ("ceyrek_ustunlugu", K)], False),
        ]
    if sekil == "son_saniye":
        return [
            ("devre", [("devre_farki", H), ("ceyrek_sonu", lambda o: o.get("periyot") == 2)], False),
            # LİDERLİK ZİNCİRİ: "X eşitledi" satırı, öncesinde rakibin öne
            # geçtiği gösterilmeden kullanılamaz (kullanıcı kuralı).
            # Bu yuva önce liderlik değişimini arıyor; çeyrek özeti yedek.
            ("liderlik_degisimi", [("liderlik", H),
                                   ("ceyrek_sonu", lambda o: o.get("periyot") == 3)], False),
            ("son_donus", [("liderlik", son_ceyrek), ("esitlik", son_ceyrek),
                           ("esitlik", H)], False),
            ("karar", [("karar_ani", H), ("liderlik", lambda o: o.get("kazanan_mi")),
                       ("esitlik", H)], True),
        ]
    if sekil == "kopma":
        return [
            ("erken", [("ceyrek_sonu", lambda o: o.get("periyot") == 1),
                       ("devre_farki", H)], False),
            # KRİTİK AN HER ŞEKİLDE AYNI TANIM: kazananın SON KEZ öne
            # geçtiği an (kullanıcı kuralı 3). Kopma şeklinde de öyle —
            # farkı sonradan büyüten seriler kritik olamaz. Liderlik
            # değişimi yoksa (kazanan hiç geride kalmadıysa) kopuş anı.
            ("kopma", [("liderlik", lambda o: K(o) and o.get("kazanan_mi")),
                       ("kopus", H), ("sayi_serisi", K),
                       ("ceyrek_ustunlugu", K)], True),
            ("kapanmadi", [("fark_korundu", H), ("kopus", H),
                           ("en_buyuk_fark", K),
                           ("ceyrek_sonu", lambda o: o.get("periyot") == 3)], False),
            ("en_etkili", [("en_etkili", H), ("ceyrek_ustunlugu", K)], False),
        ]
    # baştan sona
    return [
        ("erken_ustunluk", [("ceyrek_sonu", lambda o: o.get("periyot") == 1),
                            ("sayi_serisi", K)], False),
        ("devre", [("devre_farki", H), ("ceyrek_sonu", lambda o: o.get("periyot") == 2)], False),
        ("rakip_yaklasti", [("rakip_yaklasti", H), ("esitlik", H)], False),
        # KAZANAN HİÇ GERİDE KALMADIYSA kritik an, rakibin son kez farkı
        # 5'in altına indirdiği andan SONRAKİ ilk kopuştur (kullanıcı).
        ("kopus", [("liderlik", lambda o: K(o) and o.get("kazanan_mi")),
                   ("kopus", H), ("fark_korundu", H), ("en_etkili", H)], True),
    ]


def _mac_akisi(gercekler, en_iyi_performans=None, satir_sayisi=AKIS_SATIR_SAYISI,
               kalip_sayaci=None, anilan_metin=None):
    """[{tip, kalip, zaman, saat, cumle, detay, kritik, sekil}]

    Satırlar artık bağımsız seçilmiyor: maçın ŞEKLİ belirleniyor, olaylar
    o şeklin SABİT YUVALARINA yerleşiyor (bkz. yukarıdaki not)."""
    olaylar = [f["veri"] for f in gercekler if f["tur"] == "akis_olay"]
    if not olaylar:
        return []
    skor = next((f["veri"] for f in gercekler if f["tur"] == "skor"), {}) or {}
    kazanan = skor.get("kazanan")
    kaybeden = skor.get("dep") if kazanan == skor.get("ev") else skor.get("ev")

    # "Maçın en etkilisi" olayı — oyuncu istatistiği akış olayı değil.
    if en_iyi_performans:
        st = next((f["veri"] for f in gercekler
                   if f["tur"] == "oyuncu_stat"
                   and f["veri"].get("oyuncu") == en_iyi_performans), None)
        if st:
            son = max(olaylar, key=_akis_sirasi)
            olaylar.append({
                "tip": "en_etkili", "periyot": son.get("periyot") or 4,
                "saniye_kalan": 0.0, "zaman": "Son", "saat": None,
                "ev_skor": son.get("ev_skor"), "dep_skor": son.get("dep_skor"),
                "fark": son.get("fark"), "oyuncu": en_iyi_performans,
                "sayi": st.get("sayi"), "ribaund": st.get("rib"),
                "asist": st.get("ast"),
            })

    # DEĞİŞMEZ 1 için takım alanı: bazı olay tipleri (fark_korundu gibi)
    # takım taşımıyor. Skorun işaretinden türetiliyor — gerçekleri
    # yeniden üretmeye gerek yok, eski geceler de kapsanıyor.
    for _o in olaylar:
        if not _o.get("takim") and _o["tip"] != "en_etkili":
            _f = _o.get("fark")
            if _f:
                _o["takim"] = skor.get("ev") if _f > 0 else skor.get("dep")

    sekil = _akis_sekli(gercekler, olaylar, skor)
    plan = _yuva_planla(sekil, kazanan, kaybeden)
    plan_secenek = [(y, sec) for y, sec, _k in plan]

    # YUVALAR ZAMAN PENCERESİYLE DOLUYOR. Önce KRİTİK yuva sabitleniyor,
    # sonra soldakiler ondan ÖNCE, sağdakiler ondan SONRA olacak şekilde
    # dolduruluyor. Bu, kronolojiyi kurgudan değil YAPIDAN alıyor.
    # Eskiden yuvalar soldan sağa doldurulup sonra sırayı bozanlar
    # atılıyordu; çeyrek ÖZETİ (çeyreğin sonuna düşer) bir sonraki
    # yuvanın önünü kesiyor ve kritik satır boş kalıyordu (ölçüldü,
    # 26 Aralık: Utah'ın öne geçtiği an elendi).
    def _sec(secenekler, alt, ust, kullanilan):
        for tip, filtre in secenekler:
            adaylar = [o for o in olaylar
                       if o["tip"] == tip and filtre(o) and id(o) not in kullanilan]
            if tip != "en_etkili":
                if alt is not None:
                    adaylar = [o for o in adaylar if _akis_sirasi(o) > alt]
                if ust is not None:
                    adaylar = [o for o in adaylar if _akis_sirasi(o) < ust]
            if adaylar:
                # Pencere içinde en GEÇ olan: karara yakın olan daha çok
                # şey anlatıyor.
                return max(adaylar, key=_akis_sirasi)
        return None

    kullanilan = set()
    yerlesim = [None] * len(plan)

    def _sinirlar(i):
        alt = ust = None
        for j in range(i - 1, -1, -1):
            if yerlesim[j] is not None and yerlesim[j]["tip"] != "en_etkili":
                alt = _akis_sirasi(yerlesim[j]); break
        for j in range(i + 1, len(plan)):
            if yerlesim[j] is not None and yerlesim[j]["tip"] != "en_etkili":
                ust = _akis_sirasi(yerlesim[j]); break
        return alt, ust

    kritik_i = next((i for i, (_, _, k) in enumerate(plan) if k), 0)
    sira = [kritik_i] + [i for i in range(len(plan)) if i != kritik_i]
    for i in sira:
        _yuva, secenekler, _k = plan[i]
        alt, ust = _sinirlar(i)
        secilen = _sec(secenekler, alt, ust, kullanilan)
        if secilen is not None:
            kullanilan.add(id(secilen))
            yerlesim[i] = secilen

    temiz = [(plan[i][0], yerlesim[i], plan[i][2])
             for i in range(len(plan)) if yerlesim[i] is not None]

    # LİDERLİK ZİNCİRİ (kullanıcı kuralı 4): "X eşitledi" satırı,
    # öncesinde rakibin öne geçtiği gösterilmeden kullanılamaz. Bilgi
    # yanlış değil ama zincir eksik kalıyor — okuyucu rakibin ne zaman
    # öne geçtiğini göremiyor.
    # Önce ZAYIF bir satırı (çeyrek özeti) liderlik değişimiyle
    # değiştirmeye çalışıyoruz; olmazsa eşitlik satırı düşüyor.
    ZAYIF = ("ceyrek_sonu", "devre_farki", "ceyrek_ustunlugu")
    for i, (_y, o, _k) in enumerate(temiz):
        if o["tip"] != "esitlik":
            continue
        if any(x[1]["tip"] == "liderlik" for x in temiz[:i]):
            continue
        yerine = None
        for j in range(i - 1, -1, -1):
            if temiz[j][2] or temiz[j][1]["tip"] not in ZAYIF:
                continue
            alt = _akis_sirasi(temiz[j - 1][1]) if j > 0 else None
            ust = _akis_sirasi(o)
            aday = [x for x in olaylar
                    if x["tip"] == "liderlik" and id(x) not in kullanilan
                    and (alt is None or _akis_sirasi(x) > alt)
                    and _akis_sirasi(x) < ust]
            if aday:
                yerine = (j, max(aday, key=_akis_sirasi))
                break
        if yerine:
            j, yeni_o = yerine
            kullanilan.add(id(yeni_o))
            temiz[j] = (temiz[j][0], yeni_o, temiz[j][2])
        else:
            temiz[i] = None
    temiz = [x for x in temiz if x is not None]

    # EN İYİ PERFORMANS KARTTA ANILMALI (T14). Başlık ve alt satır onu
    # anmıyorsa akış anmak zorunda; yoksa yayın kapısı geceyi durduruyor.
    # Şekil modeline geçerken bu güvence düşmüştü (22 Aralık).
    if en_iyi_performans and anilan_metin is not None:
        _soyad = en_iyi_performans.strip().split()[-1].lower()
        _var = _soyad in (anilan_metin or "").lower() or any(
            _soyad in (x[1].get("oyuncu") or "").lower() for x in temiz)
        _etkili = next((o for o in olaylar if o["tip"] == "en_etkili"), None)
        if not _var and _etkili is not None:
            for _i in range(len(temiz) - 1, -1, -1):
                if not temiz[_i][2]:            # kritik satırı bozma
                    temiz[_i] = (temiz[_i][0], _etkili, False)
                    break
            else:
                temiz.append(("en_etkili", _etkili, False))

    if len(temiz) > satir_sayisi:
        # Fazlalık: kritik olmayan yuvalardan SONDAN atılıyor — ilk
        # yuvalar hikâyenin kurulumu.
        kritik_var = [i for i, (_, _, k) in enumerate(temiz) if k]
        atilabilir = [i for i in range(len(temiz)) if i not in kritik_var]
        while len(temiz) > satir_sayisi and atilabilir:
            temiz.pop(atilabilir.pop(-1))
    if len(temiz) < min(AKIS_ASGARI_SATIR, satir_sayisi):
        return []

    # ==================================================================
    # BLOK DEĞİŞMEZLERİ (kullanıcı kararı)
    # ==================================================================
    # Olay tipi başına kural DEĞİL, blok başına değişmez. Blok kurulur,
    # dört değişmez denetlenir; bozan satır atılır ve yerine sıradaki
    # aday gelir. Yeni bir olay tipi eklendiğinde ayrıca kural yazmak
    # gerekmiyor — denetim zaten çalışıyor.
    #
    #  1. HER SATIR DURUMU TAŞIR — cümle kimin önde olduğunu söylemeli.
    #     Skor çifti tek başına yetmez. ("Devrede fark 13" ✗)
    #  2. ARDIŞIK SATIRLAR AYNI OLAY OLAMAZ — aynı zaman damgası, aynı
    #     oyuncu, ya da aynı skor değişiminin iki parçası (serbest atış
    #     çifti gibi).
    #  3. BLOK KAZANANLA BİTER — son satır kazananın lehine olmalı.
    #     "Maçın en etkilisi" kaybeden taraftansa sona konulamaz.
    #  4. SKOR DİZİSİ İLERLER — her satırın skoru bir öncekinden ileri.
    #
    # Dördü sağlanamıyorsa blok 3'e, gerekirse 2 satıra iner. EKSİK
    # SATIR, YANLIŞ SATIRDAN İYİDİR.
    _kisa = lambda kod: cumle.TAKIM_KISA.get(kod, kod)
    _sayac = {1: 0, 2: 0, 3: 0, 4: 0}
    _onarim = {1: 0}          # DEĞİŞMEZ 1: elenmeden kalıp değiştirildi
    _sn = {"sekil": sekil, "sayac": _sayac, "onarim": _onarim, "elenen": 0,
           "kurulan": len(temiz), "takimlar": (skor.get("ev"), skor.get("dep")),
           "satir_sayisi": satir_sayisi}
    SON_DENETIM.clear(); SON_DENETIM.update(_sn); DENETIM_LOG.append(_sn)

    def _durum_tasiyor(o, cml):
        if o["tip"] == "en_etkili":
            return True                      # oyuncu özeti, durum iddiası değil
        d = (cml or "").lower()
        if "başa baş" in d or "eşitle" in d or "denk" in d or "beraberl" in d:
            return True
        return any(_kisa(k).lower() in d for k in (kazanan, kaybeden) if k)

    def _ayni_olay(a, b):
        pa, pb = a.get("periyot"), b.get("periyot")
        sa, sb = a.get("saniye_kalan"), b.get("saniye_kalan")
        if a.get("oyuncu") and a.get("oyuncu") == b.get("oyuncu"):
            return True                      # aynı oyuncu iki satırda
        if pa == pb and sa is not None and sb is not None:
            if abs(sa - sb) < 10:            # aynı ya da bitişik an
                return True
        if (a.get("ev_skor"), a.get("dep_skor")) == (b.get("ev_skor"), b.get("dep_skor")):
            return True
        return False

    def _kazanan_lehine(o):
        if o["tip"] == "en_etkili":
            st = next((f["veri"] for f in gercekler
                       if f["tur"] == "oyuncu_stat"
                       and f["veri"].get("oyuncu") == o.get("oyuncu")), None)
            return bool(st) and st.get("takim") == kazanan
        if o.get("takim"):
            return o["takim"] == kazanan
        ev_onde = (o.get("ev_skor") or 0) > (o.get("dep_skor") or 0)
        return (kazanan == (skor.get("ev") if ev_onde else skor.get("dep")))

    def _toplam(o):
        return (o.get("ev_skor") or 0) + (o.get("dep_skor") or 0)

    zorla = {}          # id(olay) -> kalip_id (DEĞİŞMEZ 1 onarımı)

    def _denetle(secim):
        """(ihlal_index, degismez_no) ya da (None, None).

        DEĞİŞMEZ 1'de satır hemen elenmiyor: önce aynı olayın durumu
        taşıyan başka bir kalıbı deneniyor. Eleme son çare — game
        winner gibi satırlar sırf cümle biçimi yüzünden düşmesin."""
        for i, (_y, o, _k) in enumerate(secim):
            if _durum_tasiyor(o, _kalip_metni(o)):
                continue
            uygun = next((kid for kid, c, _d in cumle.akis_kaliplari(o, _kisa)
                          if _durum_tasiyor(o, c)), None)
            if uygun is not None:
                if zorla.get(id(o)) != uygun:
                    _onarim[1] += 1           # onarıldı, satır kalıyor
                zorla[id(o)] = uygun
                continue
            return i, 1
        for i in range(len(secim) - 1):
            if _ayni_olay(secim[i][1], secim[i + 1][1]):
                # Kritik satır korunur, komşusu elenir.
                return (i if not secim[i][2] else i + 1), 2
        if secim and not _kazanan_lehine(secim[-1][1]):
            return len(secim) - 1, 3
        for i in range(1, len(secim)):
            if secim[i][1]["tip"] == "en_etkili" or secim[i - 1][1]["tip"] == "en_etkili":
                continue
            if _toplam(secim[i][1]) <= _toplam(secim[i - 1][1]):
                return (i if not secim[i][2] else i - 1), 4
        return None, None

    def _kalip_metni(o):
        ad = cumle.akis_kaliplari(o, _kisa)
        if id(o) in zorla:
            return next((c for kid, c, _d in ad if kid == zorla[id(o)]), ad[0][1])
        for kid, c, _d in ad:
            if kid not in _blok and (kalip_sayaci or {}).get(kid, 0) < AKIS_KALIP_LIMITI:
                return c
        return ad[0][1] if ad else ""

    _blok = set()
    yasak = set()            # elenen olaylar geri gelmesin (sonsuz döngü)
    guvenlik = 0
    while guvenlik < 12:
        guvenlik += 1
        i, no = _denetle(temiz)
        if i is None:
            break
        _sayac[no] += 1
        _sn["elenen"] += 1
        _dusen = temiz.pop(i)
        yasak.add(id(_dusen[1]))
        # Yerine sıradaki aday: aynı yuvanın seçeneklerinden, pencereye
        # uyan bir başkası.
        alt = _akis_sirasi(temiz[i - 1][1]) if i > 0 else None
        ust = _akis_sirasi(temiz[i][1]) if i < len(temiz) else None
        yeni = None
        for _tip, _filtre in dict(plan_secenek).get(_dusen[0], []):
            ad = [x for x in olaylar if x["tip"] == _tip and _filtre(x)
                  and id(x) not in kullanilan and id(x) not in yasak
                  and (alt is None or _akis_sirasi(x) > alt)
                  and (ust is None or _akis_sirasi(x) < ust)]
            if ad:
                yeni = max(ad, key=_akis_sirasi)
                break
        if yeni is None:
            # Yuvanın kendi tipleri tükendiyse pencereye uyan HERHANGİ
            # bir kullanılmamış olay — blok gereksiz yere kısalmasın.
            # Blokta zaten bulunan tipler en sona düşüyor.
            _var = {x[1]["tip"] for x in temiz}
            genis = [x for x in olaylar
                     if id(x) not in kullanilan and id(x) not in yasak
                     and x["tip"] != "en_etkili"
                     and (alt is None or _akis_sirasi(x) > alt)
                     and (ust is None or _akis_sirasi(x) < ust)]
            if genis:
                yeni = min(genis, key=lambda x: (x["tip"] in _var, -_akis_sirasi(x)[0]))
        if yeni is not None:
            kullanilan.add(id(yeni))
            temiz.insert(i, (_dusen[0], yeni, _dusen[2]))
        elif _dusen[2] and temiz:
            temiz[-1] = (temiz[-1][0], temiz[-1][1], True)   # kritik kaybolmasın
        if len(temiz) < min(AKIS_ASGARI_SATIR, satir_sayisi):
            break

    satirlar = []
    for yuva, o, kritik in temiz:
        adaylar = cumle.akis_kaliplari(o, lambda k: cumle.TAKIM_KISA.get(k, k))
        if not adaylar:
            continue
        if id(o) in zorla:
            # DEĞİŞMEZ 1 bu satırın kalıbını sabitledi — çeşitlilik
            # sayacı bunu bozamaz.
            kid, c, det = next(x for x in adaylar if x[0] == zorla[id(o)])
        else:
            uygun = [x for x in adaylar if x[0] not in _blok
                     and (kalip_sayaci or {}).get(x[0], 0) < AKIS_KALIP_LIMITI]
            havuz = uygun or [x for x in adaylar if x[0] not in _blok] or adaylar
            kid, c, det = min(havuz, key=lambda x: ((kalip_sayaci or {}).get(x[0], 0),
                                                    adaylar.index(x)))
        _blok.add(kid)
        if kalip_sayaci is not None:
            kalip_sayaci[kid] = kalip_sayaci.get(kid, 0) + 1
        satirlar.append({
            "tip": o["tip"], "kalip": kid, "yuva": yuva, "sekil": sekil,
            "zaman": o.get("zaman"), "saat": o.get("saat"),
            "cumle": c, "detay": det, "kritik": kritik,
        })
    # ---- KRİTİK AN: KARAR ANI, "SON OLAY" DEĞİL ----------------------
    # Kurallar (kullanıcı), sırayla:
    #  1. Maçı bitiren basket varsa kritik HER ZAMAN odur — şekil ne
    #     olursa olsun, öncesinde ne yaşanmış olursa olsun. Bu kural
    #     diğer bütün kritik an kurallarının ÜSTÜNDE.
    #  2. Yoksa: kazananın SON KEZ öne geçtiği an.
    #  3. Kazanan hiç geride kalmadıysa: rakibin son kez farkı 5'in
    #     altına indirdiği andan sonraki ilk kopuş.
    #  4. Fark 15'i geçtikten sonraki hiçbir olay kritik olamaz — orası
    #     çöp zaman (27 Aralık MIN-BKN: "fark 21" kritik işaretlenmişti).
    if satirlar:
        _fark15_sonrasi = None
        for o in sorted(olaylar, key=_akis_sirasi):
            if abs(o.get("fark") or 0) > AKIS_KRITIK_FARK_TAVANI:
                _fark15_sonrasi = _akis_sirasi(o)
                break

        def _uygun_kritik(i):
            o = temiz[i][1]
            if o["tip"] == "karar_ani":
                return True          # 1. kural tavanı da aşar
            # Tavanı AŞAN olayın kendisi de kritik olamaz: maç orada
            # zaten kopmuş oluyor, sonrası çöp zaman.
            if _fark15_sonrasi is not None and _akis_sirasi(o) >= _fark15_sonrasi:
                return False
            return True

        _sec_i = None
        for _oncelik in ("karar_ani", "liderlik", "kopus"):
            for i, (_y, o, _k) in enumerate(temiz):
                if o["tip"] != _oncelik:
                    continue
                if _oncelik == "liderlik" and not o.get("kazanan_mi", True):
                    continue          # kaybedenin öne geçişi karar anı değil
                if not _uygun_kritik(i):
                    continue
                _sec_i = i
            if _sec_i is not None:
                break
        if _sec_i is None:
            # Hiçbiri yoksa tavanı aşmayan SON satır.
            for i in range(len(temiz) - 1, -1, -1):
                if _uygun_kritik(i):
                    _sec_i = i
                    break
        for i, r in enumerate(satirlar):
            r["kritik"] = (i == _sec_i)
        if not any(r["kritik"] for r in satirlar):
            satirlar[-1]["kritik"] = True
    return satirlar


def _kritik_anlar(ham_mac, ev_taraf, dep_taraf):
    """Kritik süre + o sürede en çok sayı üreten iki oyuncu, yoksa None.

    Sayı hesabı SKOR FARKINDAN türetiliyor, olay tipinden değil: kaçan
    serbest atışlarda `scoreHome`/`scoreAway` boş geliyor ve "Free Throw"
    olayının kendisi isabetli mi belli değil. İki ardışık skorun farkı
    ise her durumda doğru — o olayda kaç sayı geldiğini birebir verir.

    Farkın ≤5 olup olmadığı olayın ÖNCESİNDEKİ duruma bakılarak
    ölçülüyor: 6 farkla atılan üçlük kritik değildir, farkı 3'e indirmiş
    olması bunu değiştirmez.
    """
    try:
        olaylar = ham_mac["play_by_play"]["game"]["actions"]
    except (KeyError, TypeError):
        return None
    if not olaylar:
        return None

    ev_kod, dep_kod = ev_taraf["kod"], dep_taraf["kod"]
    # PBP'de yalnız soyadı var ("B. Brown"); tam ad kutu skordan
    # personId ile geliyor.
    ad_by_id, kod_by_id = {}, {}
    try:
        bt = ham_mac["box_traditional"]["boxScoreTraditional"]
        for takim in (bt["homeTeam"], bt["awayTeam"]):
            for p in takim["players"]:
                ad_by_id[p["personId"]] = _dogru_oyuncu_adi(
                    p["personId"], f"{p['firstName']} {p['familyName']}".strip())
                kod_by_id[p["personId"]] = takim["teamTricode"]
    except (KeyError, TypeError):
        return None

    sure_sn = 0.0
    ev_puan = dep_puan = 0
    sayilar, denemeler, isabetler = {}, {}, {}
    ev_s = dep_s = 0
    onceki_t = None
    son_t = None

    for olay in olaylar:
        kalan = _pbp_saniye(olay.get("clock"))
        if kalan is None:
            continue
        t = _mac_saniyesi(olay.get("period", 1), kalan)
        son_t = t
        yeni_ev = int(olay["scoreHome"]) if str(olay.get("scoreHome") or "").strip() else ev_s
        yeni_dep = int(olay["scoreAway"]) if str(olay.get("scoreAway") or "").strip() else dep_s

        if t >= KRITIK_BASLANGIC_SN:
            # Sayaç pencerenin BAŞINDAN işler — ilk olay 5:00'dan birkaç
            # saniye sonraysa aradaki süre de kritiktir.
            if onceki_t is None:
                onceki_t = KRITIK_BASLANGIC_SN
            # Fark, olayın ÖNCESİNDEKİ duruma göre. Hem süre hem sayı
            # aynı koşula bağlı: 6 farkla atılan basket kritik değildir.
            if abs(ev_s - dep_s) <= KRITIK_FARK:
                sure_sn += max(0.0, t - onceki_t)
                ev_puan += yeni_ev - ev_s
                dep_puan += yeni_dep - dep_s
                kisi = olay.get("personId") or 0
                if kisi:
                    kazanc = (yeni_ev - ev_s) + (yeni_dep - dep_s)
                    if kazanc > 0:
                        sayilar[kisi] = sayilar.get(kisi, 0) + kazanc
                    if olay.get("isFieldGoal") == 1:
                        denemeler[kisi] = denemeler.get(kisi, 0) + 1
                        if olay.get("shotResult") == "Made":
                            isabetler[kisi] = isabetler.get(kisi, 0) + 1
            onceki_t = max(onceki_t, t)
        ev_s, dep_s = yeni_ev, yeni_dep

    # Son olaydan maçın bitişine kadarki dilim (skor değişmediği için
    # olay yazılmamış olabilir).
    if onceki_t is not None and son_t is not None and abs(ev_s - dep_s) <= KRITIK_FARK:
        sure_sn += max(0.0, son_t - onceki_t)

    if sure_sn < KRITIK_ASGARI_SURE_SN or not sayilar:
        return None

    kazanan_kod = ev_kod if ev_taraf["skor"] >= dep_taraf["skor"] else dep_kod

    def anahtar(kisi):
        d = denemeler.get(kisi, 0)
        yuzde = isabetler.get(kisi, 0) / d if d else 0.0
        return (-sayilar[kisi], -yuzde, ad_by_id.get(kisi, ""))

    esigi_gecen = {k: v for k, v in sayilar.items() if v >= KRITIK_ASGARI_SAYI}
    if not esigi_gecen:
        return None
    secilenler = sorted(esigi_gecen, key=anahtar)[:KRITIK_OYUNCU_SAYISI]
    oyuncular = [{
        "isim": ad_by_id.get(k, ""),
        "takim": kod_by_id.get(k, ""),
        "sayi": sayilar[k],
        "fg": f"{isabetler.get(k, 0)}/{denemeler.get(k, 0)}",
        "kazanan": False,
    } for k in secilenler if ad_by_id.get(k)]
    if not oyuncular:
        return None
    # Ember vurgu EN FAZLA BİR satırda: kazanan takımın en çok sayı
    # üreten oyuncusu. İki satır da kazanan taraftan olduğunda ikisini
    # birden boyamak vurguyu tamamen yok ediyor.
    for o in oyuncular:
        if o["takim"] == kazanan_kod:
            o["kazanan"] = True
            break

    dk, sn = divmod(int(round(sure_sn)), 60)
    if ev_puan == dep_puan:
        skor, onde = f"{ev_puan}-{dep_puan}", None
    elif ev_puan > dep_puan:
        skor, onde = f"{ev_puan}-{dep_puan}", ev_kod
    else:
        skor, onde = f"{dep_puan}-{ev_puan}", dep_kod

    return {
        "sure_sn": int(round(sure_sn)),
        "sure": f"{dk}:{sn:02d}",
        "skor": skor,
        "onde": onde,
        "ev_puan": ev_puan,
        "dep_puan": dep_puan,
        "oyuncular": oyuncular,
    }


def _kilit_degerleri(taraf, digerleri):
    """Bir takımın kilit istatistik alanları. `digerleri` OtherStats satırı."""
    t = taraf["toplam"]
    yapilan = lambda kesir: int(str(kesir).split("/")[0]) if "/" in str(kesir) else 0
    denenen = lambda kesir: int(str(kesir).split("/")[1]) if "/" in str(kesir) else 0
    return {
        "reb": t["reb"], "oreb": t["oreb"], "ast": t["ast"], "to": t["to"],
        "3pm": yapilan(t["3p"]), "fta": denenen(t["ft"]),
        "pts2c": (digerleri or {}).get("PTS_2ND_CHANCE"),
        "paint": (digerleri or {}).get("PTS_PAINT"),
    }


def kilit_istatistik_adi(ham_mac):
    """Bu maçın kilit istatistiğinin ADI, yoksa None.

    ÜRETİM ANINDA gerekiyor: metin yazılırken hangi olgunun kilit
    istatistik kutusuna çıkacağı biliniyorsa, o olgu metinden çıkarılmalı
    (dogrula.t30). Hesap TEK KAYNAK — aşağıdaki _kilit_istatistik ile
    aynı fonksiyonu çağırıyor, ölçüt kopyalanmıyor.

    Sadece kutu TOPLAMLARI gerektiği için hafif bir taraf sözlüğü
    kuruluyor; tam _box_score'a (oyuncu satırları, renkler, çeyrekler)
    gerek yok."""
    try:
        bt = ham_mac["box_traditional"]["boxScoreTraditional"]
    except (KeyError, TypeError):
        return None

    def hafif(takim):
        t = takim["statistics"]
        return {
            "kod": takim["teamTricode"],
            "toplam": {
                "reb": t["reboundsTotal"], "oreb": t["reboundsOffensive"],
                "ast": t["assists"], "to": t["turnovers"],
                "3p": f"{t['threePointersMade']}/{t['threePointersAttempted']}",
                "ft": f"{t['freeThrowsMade']}/{t['freeThrowsAttempted']}",
            },
        }

    kilit = _kilit_istatistik(ham_mac, hafif(bt["homeTeam"]), hafif(bt["awayTeam"]))
    return (kilit or {}).get("ad")


def _kilit_istatistik(ham_mac, ev_taraf, dep_taraf):
    """Eşiği aşan TEK istatistik, yoksa None.

    MAÇ BAŞINA EN FAZLA BİR TANE (kullanıcı kararı). Birden fazla eşik
    aşılıyorsa "en büyük aykırılık" seçiliyor — ham fark DEĞİL, farkın
    kendi eşiğine ORANI. Ham farkla karşılaştırmak ölçekleri birbirine
    karıştırırdı: boyalı alanda 21 sayılık fark eşiği ancak geçerken,
    asistte 13'lük fark eşiği çoktan aşıyor.

    Hiçbiri aşılmazsa None döner ve bölüm HİÇ ÇİZİLMEZ — boş yer kalmaz."""
    try:
        rs = next(x for x in ham_mac["box_summary"]["resultSets"]
                  if x["name"] == "OtherStats")
        by_kod = {dict(zip(rs["headers"], r))["TEAM_ABBREVIATION"]:
                  dict(zip(rs["headers"], r)) for r in rs["rowSet"]}
    except Exception:
        by_kod = {}
    ev = _kilit_degerleri(ev_taraf, by_kod.get(ev_taraf["kod"]))
    dep = _kilit_degerleri(dep_taraf, by_kod.get(dep_taraf["kod"]))

    en_iyi = None
    for alan, ad, esik, cok_kazanir in KILIT_ESIKLERI:
        a, b = ev.get(alan), dep.get(alan)
        if a is None or b is None:
            continue          # veri yoksa uydurma yok
        fark = abs(a - b)
        if fark < esik:
            continue
        oran = fark / esik
        if en_iyi is None or oran > en_iyi["_oran"] or (
                oran == en_iyi["_oran"] and fark > en_iyi["fark"]):
            # YÖN: kazanan taraf istatistiğe göre belirleniyor, maçın
            # sonucuna göre DEĞİL. Maçı kazanan takım bu kategoriyi
            # kaybetmiş olabilir; o zaman ember kutu kaybedenin olur.
            ev_kazandi = (a > b) if cok_kazanir else (a < b)
            en_iyi = {
                "ad": ad, "fark": fark, "_oran": oran,
                "kutular": [
                    {"kod": ev_taraf["kod"], "deger": a, "kazandi": ev_kazandi},
                    {"kod": dep_taraf["kod"], "deger": b, "kazandi": not ev_kazandi},
                ],
            }
    if en_iyi:
        en_iyi.pop("_oran")
    return en_iyi


# ---------------------------------------------------------------------------
# TAKIM RENGİ ÇAKIŞMASI
# ---------------------------------------------------------------------------
#
# Gerçek sorun (18 Aralık): gecenin beşi sahasında Dončić, DeRozan ve
# LeBron vardı. Lakers ve Sacramento ikisi de mor — üçü aynı takımdanmış
# gibi duruyordu. Ayrıca sahada kimin hangi takımda olduğu HİÇ yazmıyordu.
#
# Çözüm iki parçalı ve ikisi de gerekli: RENK güzelleştirir, KOD belirtir.
# Kod her oyuncuda var (çakışma olsun olmasın); renk sadece çakışınca
# değişiyor ve değişince halka takımın ASIL rengini gösteriyor.
#
# 30 takım var; mor bugün çakıştı, MAVİ çok daha sık çakışacak
# (DAL, ORL, OKC, MIN, MEM, CHA).

# Eşikler: iki renk "yakın" sayılıyorsa ton farkı VE parlaklık farkı
# birlikte küçük demektir. Sadece tona bakmak yetmiyor — açık mavi ile
# lacivert aynı tonda ama gözde karışmıyor.
TON_ESIGI = 32.0        # derece (0-360)
PARLAKLIK_ESIGI = 0.20  # 0-1
DOYGUNLUK_ESIGI = 0.25  # bu farkın üstünde renkler zaten ayırt ediliyor


def _hsl(hex_renk):
    h = hex_renk.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)  # (ton, parlaklık, doygunluk)


def _renkler_yakin_mi(a, b):
    ha, la, sa = _hsl(a)
    hb, lb, sb = _hsl(b)
    # Doygunluğu çok düşük iki renk (griler) tonu ne olursa olsun yakındır.
    if sa < 0.12 and sb < 0.12:
        return abs(la - lb) < PARLAKLIK_ESIGI
    # DOYGUNLUK tek başına ayırt edici. Gri (#9EA2A6) ile Dallas mavisi
    # (#2E7BC4) hesaplanan TONU birbirine yakın çıkıyor — grinin tonu
    # zaten anlamsız — ve parlaklıkları da yakın olunca "çakışıyor"
    # sanılıyordu. Gerçek üretim sonucu: HOU kırmızıdan griye kaydıktan
    # sonra DAL da boşuna lacivert oluyordu. Göz bu ikisini karıştırmaz.
    if abs(sa - sb) > DOYGUNLUK_ESIGI:
        return False
    ton_farki = abs(ha - hb) * 360
    ton_farki = min(ton_farki, 360 - ton_farki)   # dairesel
    return ton_farki < TON_ESIGI and abs(la - lb) < PARLAKLIK_ESIGI


def takim_renk_secenekleri():
    try:
        ham = json.loads((CONFIG_DIZIN / "takim_renkleri.json").read_text(encoding="utf-8"))
        return ham["takimlar"]
    except Exception:
        return {kod: [renk] for kod, renk in TAKIM_RENK.items()}


def renk_cakismasini_coz(oyuncular):
    """Aynı listedeki oyunculara çakışmayan renk atar.

    `oyuncular`: [{"takim": kod, "_gmsc": float, ...}] — sıra önemli DEĞİL,
    karar GmSc'ye göre veriliyor: yüksek GmSc'li oyuncu takımının birincil
    rengini korur, DÜŞÜK olan sıradaki renge geçer (kullanıcı kuralı).

    Her oyuncuya iki alan yazılır:
      renk       — ekranda kullanılacak renk
      asil_renk  — takımın birincil rengi; farklıysa halka bunu gösterir
    """
    secenekler = takim_renk_secenekleri()
    # Karar TAKIM düzeyinde: aynı takımın iki oyuncusu aynı rengi almalı.
    # İlk sürüm oyuncu düzeyinde karar veriyordu ve LeBron ile Dončić
    # (ikisi de LAL) farklı renk alıyordu — çakışmayı çözerken takım
    # kimliğini bozuyordu.
    takim_gmsc = {}
    for o in oyuncular:
        kod = o.get("takim")
        takim_gmsc[kod] = max(takim_gmsc.get(kod, 0), o.get("_gmsc") or 0)
    # Yüksek GmSc'li takım birincil rengini korur, düşük olan kayar.
    sirali_takimlar = sorted(takim_gmsc, key=lambda k: -takim_gmsc[k])
    kullanilan = []
    renk_by_takim = {}
    for kod in sirali_takimlar:
        liste = secenekler.get(kod) or [TAKIM_RENK.get(kod, "#7E8794")]
        asil = liste[0]
        secilen = next((aday for aday in liste
                        if not any(_renkler_yakin_mi(aday, k) for k in kullanilan)), None)
        # Hepsi çakışıyorsa birincil kalır: yanlış renk göstermektense
        # çakışmayı kabul ediyoruz — KOD zaten her oyuncuda yazılı.
        if secilen is None:
            secilen = asil
        kullanilan.append(secilen)
        renk_by_takim[kod] = (secilen, asil)
    for o in oyuncular:
        secilen, asil = renk_by_takim[o.get("takim")]
        o["renk"] = secilen
        o["asil_renk"] = asil
        o["renk_degisti"] = secilen != asil
    return oyuncular


# ---------------------------------------------------------------------------
# YÜKSELEN / DÜŞEN
# ---------------------------------------------------------------------------
#
# "Avdija yanıyor, 5 maçtır" gerçek bir muhabbet ve hiçbir yerde karşılığı
# yoktu. Bu bölüm onu veriyor.
#
# ÖLÇÜT sadece "çok sayı atmak" DEĞİL, son 5 maç ortalamasının SEZON
# ortalamasını ne kadar aştığı. Hep 28 atan biri listeye girmiyor, çünkü
# normali o — böylece sürpriz isimler çıkıyor.
#
# Veri PlayerGameLogs'ta zaten var (ham["oyuncu_ortalama"]), yeni API
# çağrısı yok. Loglar bu gecenin ÖNCESİNDE bitiyor, o yüzden son 5 maç =
# bu gecenin kutu skoru + logdan son 4 maç.
FORM_MAC_SAYISI = 5
FORM_LISTE_UZUNLUGU = 5
# ANLAMLILIK EŞİĞİ — "2 sayı ortalayan yedekler listeyi doldurmasın"
# (kullanıcı kuralı). Bu iş önce 25 DAKİKA şartıyla yapılıyordu; ölçüm
# gösterdi ki dakika yanlış vekil: %25 + tutarlılık kapılarını geçen 455
# oyuncunun 395'ini TEK BAŞINA dakika eliyordu (21 gecede düşen listesi
# gece başına 2.5 satır, 4 gece tamamen boş). Elenenler arasında Keldon
# Johnson (12.6 → 8.0) ve Julian Champagnie (11.1 → 5.4) gibi gerçek
# düşüşler vardı; kalanlar 18-23 dakika oynayan rotasyon oyuncuları.
#
# Doğru vekil SAYI: liste zaten SAYI formunu anlatıyor.
#   Düşen  → SEZON ortalaması eşiği geçmeli (önce anlamlı mıydı?)
#   Yükselen → SON 5 ortalaması eşiği geçmeli (şimdi anlamlı mı?)
# Yükselene sezon eşiği konulamaz: bölümün bütün anlamı düşük sezon
# ortalamasından patlayanı bulmak (Carrington 8.0 → 17.6, %120).
DUSEN_ASGARI_SEZON_SAYI = 10.0
YUKSELEN_ASGARI_SON5_SAYI = 10.0

# ÖLÇÜT MUTLAK FARK DEĞİL, YÜZDE DEĞİŞİM (kullanıcı kuralı).
#
# Gerçek üretim arızası (2025-12-21): Anthony Edwards "Düşen"deydi —
# 11-15-40-26-24, sezon 27.4, son5 23.2, mutlak fark 4.2. Ama 27.4
# ortalayan birinde 4.2 = %15, yani gürültü. 10 ortalayan biri 5.8'e
# düşse yine 4.2 fark eder ve o %42, gerçek çöküş. Mutlak fark çok sayı
# atanları haksız yere Düşen'e sokuyor, az atanların gerçek düşüşünü
# kaçırıyordu.
# HAVUZ TÜM LİG. Eskiden yalnız o gece OYNAYAN oyuncular arasından
# seçiliyordu; NBA'de her gece takımların üçte biri oynadığı için havuz
# her sabah bambaşka oluyor ve liste iki günde bir sıfırlanıyordu.
# Avdija dün listedeydi, ertesi gün oynamadığı için düşüyordu — formu
# değişmediği halde. "Kim yanıyor" sorusunun cevabı takip edilebilir
# olmalı (kullanıcı kuralı).
# Bayatlık ölçütü buna karşılık: son maçı bu kadar günden eskiyse
# oyuncu listeden düşer. Ölçü noktası GÜNLÜĞÜN EN SON GÜNÜ — gecenin
# TSİ etiketi ABD maç tarihinden bir gün ileride, ondan sayarsak
# pencere sessizce 4 güne inerdi.
FORM_BAYATLIK_GUN = 5

FORM_YUZDE_ESIGI = 25.0

# TUTARLILIK ŞARTI: son 5 maçın en az DÖRDÜ aynı yönde olmalı.
# Edwards'ın ortasındaki 40 sayılık maç dalgalanmayı düşüş gibi
# gösteriyordu; dört maç aynı yönde değilse bu bir eğilim değil.
FORM_AYNI_YON_ASGARI = 4


def _dakikayi_coz(ham):
    """'34:12' ya da 34.2 -> 34.2"""
    if ham is None:
        return 0.0
    if isinstance(ham, (int, float)):
        return float(ham)
    metin = str(ham)
    if ":" in metin:
        parca = metin.split(":")
        try:
            return int(parca[0]) + int(parca[1]) / 60
        except ValueError:
            return 0.0
    try:
        return float(metin)
    except ValueError:
        return 0.0


def _oyuncu_gecmisi(ham):
    """{oyuncu_id: [{tarih, sayi, dakika, rakip}, ...]} — eskiden yeniye."""
    try:
        rs = ham["oyuncu_ortalama"]["resultSets"][0]
    except Exception:
        return {}
    h = {ad: i for i, ad in enumerate(rs["headers"])}
    gerekli = ("PLAYER_ID", "GAME_DATE", "PTS", "MIN", "MATCHUP")
    if any(k not in h for k in gerekli):
        return {}
    gecmis = {}
    for satir in rs["rowSet"]:
        pid = satir[h["PLAYER_ID"]]
        gecmis.setdefault(pid, []).append({
            "tarih": str(satir[h["GAME_DATE"]])[:10],
            "sayi": satir[h["PTS"]] or 0,
            "dakika": _dakikayi_coz(satir[h["MIN"]]),
            "rakip": _rakip_kisalt(satir[h["MATCHUP"]]),
        })
    for pid in gecmis:
        gecmis[pid].sort(key=lambda x: x["tarih"])
    return gecmis


def _rakip_kisalt(matchup):
    """'GSW vs. PHX' / 'GSW @ PHX' -> 'PHX'"""
    metin = str(matchup or "")
    for ayirac in (" vs. ", " @ "):
        if ayirac in metin:
            return metin.split(ayirac)[1].strip()
    return ""


def _gun(metin):
    """'2025-12-19' -> date. Bozuk/eksik değerde None."""
    import datetime as _datetime
    try:
        return _datetime.date.fromisoformat(str(metin)[:10])
    except Exception:
        return None


_KUNYE_ONBELLEK = {}


def _gunluk_kunye(ham, pid):
    """{isim, takim} — lig günlüğünden, o gece OYNAMAMIŞ oyuncular için.

    Kutu skorda olmayan oyuncunun adını başka yerden okuyamıyoruz;
    günlükte PLAYER_NAME ve TEAM_ABBREVIATION zaten var. Oyuncunun EN
    SON satırı kullanılıyor — sezon içinde takım değiştirmişse güncel
    takımı görünsün."""
    anahtar = id(ham)
    tablo = _KUNYE_ONBELLEK.get(anahtar)
    if tablo is None:
        tablo = {}
        try:
            rs = ham["oyuncu_ortalama"]["resultSets"][0]
            h = {ad: i for i, ad in enumerate(rs["headers"])}
            for satir in rs["rowSet"]:
                tablo[satir[h["PLAYER_ID"]]] = {
                    "isim": satir[h["PLAYER_NAME"]] or "",
                    "takim": satir[h["TEAM_ABBREVIATION"]] or "",
                    "tarih": str(satir[h["GAME_DATE"]])[:10],
                }
        except Exception:
            tablo = {}
        _KUNYE_ONBELLEK.clear()
        _KUNYE_ONBELLEK[anahtar] = tablo
    return tablo.get(pid, {"isim": "", "takim": ""})


def _formda_listeler(ham, bt_by_gid, gecenin_oyunculari):
    """(yukselen, dusen) — her biri en fazla FORM_LISTE_UZUNLUGU satır.

    HAVUZ TÜM LİG (kullanıcı kararı). `gecenin_oyunculari` yalnız bu
    gece oynayanları verir; o gece oynamamış bir oyuncu da listede
    kalabilir. Ölçüt takvim günü değil, oyuncunun KENDİ son 5 maçı.
    Bayatlık FORM_BAYATLIK_GUN ile sınırlı.

    `gecenin_oyunculari`: [{"id","isim","takim","pos","sayi","dakika",
    "_gmsc","rakip"}] — bu geceki satır buradan geliyor ve dizide EMBER
    işaretleniyor (`bu_gece`). Oynamamış oyuncunun dizisinde hiçbir kutu
    ember olmuyor, son maç nötr renkte kalıyor."""
    gecmis = _oyuncu_gecmisi(ham)
    bu_gece_by_id = {o["id"]: o for o in gecenin_oyunculari}
    # Ölçü noktası: günlükteki EN SON maç günü. Gecenin TSİ etiketinden
    # saymak herkese bir gün ekliyordu (bkz. FORM_BAYATLIK_GUN notu).
    tum_tarihler = [x["tarih"] for lst in gecmis.values() for x in lst]
    referans = _gun(max(tum_tarihler)) if tum_tarihler else None
    adaylar = []
    for pid, onceki in gecmis.items():
        if not onceki:
            continue                      # sezon ortalaması yoksa kıyas yok
        o = bu_gece_by_id.get(pid)
        sezon_ort = sum(x["sayi"] for x in onceki) / len(onceki)
        if o:
            # Son 5 = bu gece + logdan son 4.
            son5 = onceki[-(FORM_MAC_SAYISI - 1):] + [{
                "tarih": "bu gece", "sayi": o["sayi"],
                "dakika": o["dakika"], "rakip": o["rakip"],
            }]
        else:
            # BU GECE OYNAMADI. Son 5 maçı doğrudan günlükten; bayatsa
            # listeden düşüyor — "kim yanıyor" sorusu iki hafta önceki
            # formla cevaplanamaz.
            son5 = onceki[-FORM_MAC_SAYISI:]
            son_gun = _gun(onceki[-1]["tarih"])
            if referans is None or son_gun is None:
                continue
            if (referans - son_gun).days > FORM_BAYATLIK_GUN:
                continue
        if len(son5) < FORM_MAC_SAYISI:
            continue                      # 5 maçı dolmayan için "form" denmez
        son5_ort = sum(x["sayi"] for x in son5) / len(son5)
        # Yüzde değişim ve kaç maçın aynı yönde olduğu — ölçüt bunlar.
        # Kıyas EKRANDA YAZAN (yuvarlanmış) değerlerle: satır "sezon 21.1
        # → 25.0" yazıp yüzdeyi ham değerlerden hesaplarsa okuyucunun
        # kendi hesabıyla tutmuyor.
        sezon_gosterilen = round(sezon_ort, 1)
        son5_gosterilen = round(son5_ort, 1)
        yuzde = (((son5_gosterilen - sezon_gosterilen) / sezon_gosterilen * 100)
                 if sezon_gosterilen else 0.0)
        ust_sayisi = sum(1 for x in son5 if x["sayi"] > sezon_gosterilen)
        alt_sayisi = sum(1 for x in son5 if x["sayi"] < sezon_gosterilen)
        # Her maç oyuncunun KENDİ sezon ortalamasının üstünde mi?
        # Çıplak sayı bir şey ifade etmiyor: 24 sayı iyi mi kötü mü,
        # oyuncunun normalini bilmeden söylenemez. Kıyas EKRANDA YAZAN
        # değerle yapılıyor (yuvarlanmış) — yoksa satır "sezon 21.1"
        # derken 21 sayılık maç yeşil görünebilirdi.
        # Ad/takım: oynamamış oyuncu için günlükten okunuyor.
        kunye = _gunluk_kunye(ham, pid)
        adaylar.append({
            "id": pid,
            "isim": (o or {}).get("isim") or kunye["isim"],
            "takim": (o or {}).get("takim") or kunye["takim"],
            "pos": (o or {}).get("pos", ""),
            # Renk çakışmasında öncelik: bu gece oynayan önde gelsin,
            # kendi maçının rengini korusun.
            "_gmsc": (o or {}).get("_gmsc") or 0,
            # Balonda rakip KOD değil okunur ad ("47 sayı · Toronto"):
            # üç harfli kod balonun tek bilgi taşıyan yarısıydı ve
            # okunması için kod bilmek gerekiyordu.
            "son5": [{"sayi": x["sayi"],
                      "rakip": cumle.TAKIM_KISA.get(x["rakip"], x["rakip"]),
                      "bu_gece": bool(o) and x["tarih"] == "bu gece",
                      "ust": x["sayi"] > sezon_gosterilen} for x in son5],
            "son5_ort": round(son5_ort, 1),
            "sezon_ort": round(sezon_ort, 1),
            "fark": round(son5_ort - sezon_ort, 1),
            "yuzde": round(yuzde, 1),
            "ust_sayisi": ust_sayisi,
            "alt_sayisi": alt_sayisi,
            "son5_dakika": round(sum(x["dakika"] for x in son5) / len(son5), 1),
        })
    # Sıralama da seçim de YÜZDEYE göre. Eşiği geçmeyen ve son 5 maçın
    # en az dördü aynı yönde olmayan aday listeye HİÇ girmiyor.
    yukselen = sorted(
        [a for a in adaylar
         if a["yuzde"] >= FORM_YUZDE_ESIGI
         and a["ust_sayisi"] >= FORM_AYNI_YON_ASGARI
         and a["son5_ort"] >= YUKSELEN_ASGARI_SON5_SAYI],
        key=lambda a: -a["yuzde"])[:FORM_LISTE_UZUNLUGU]
    dusen = sorted(
        [a for a in adaylar
         if a["yuzde"] <= -FORM_YUZDE_ESIGI
         and a["alt_sayisi"] >= FORM_AYNI_YON_ASGARI
         and a["sezon_ort"] >= DUSEN_ASGARI_SEZON_SAYI],
        key=lambda a: a["yuzde"])[:FORM_LISTE_UZUNLUGU]
    # Renk çakışması her iki listede AYRI AYRI çözülüyor — listeler
    # birbirinden bağımsız okunuyor.
    return renk_cakismasini_coz(yukselen), renk_cakismasini_coz(dusen)


# ---------------------------------------------------------------------------
# SIRALAMA HAREKETİ
# ---------------------------------------------------------------------------
#
# Sitede sıralama diye bir şey yoktu. Sabah bakan biri için en pratik
# bilgilerden biri: gece bitince kim yükseldi, kim düştü. Metin bunu
# söyleyemiyor çünkü tek maçın metni tüm ligin hareketini anlatamaz.
#
# SADECE YER DEĞİŞTİREN takımlar görünüyor; hareket yoksa bölüm hiç
# çıkmıyor — "sakin gece" ve "kilit istatistik" ile aynı ilke.
#
# DİKKAT: sıralama uç noktasında tarih filtresi YOK. Gece ÖNCESİ
# sıralama, oyun günlüğünden o günün maçları çıkarılarak hesaplanıyor —
# `derece` ve `seri` için de aynı yöntem kullanılıyor (gercekler.py).
SIRALAMA_FORM_MAC = 10
# Sezonun ilk günlerinde sıralama anlamsız: iki maç oynamış takımlar
# arasında "3. sıraya yükseldi" demek gürültü. Bölüm ancak sezonun
# 5. gününden SONRA çıkıyor (kullanıcı kararı). Arşiv geceleri sezon
# ortasından geldiği için bu eşiği zaten geçiyor.
SIRALAMA_ASGARI_GUN = 5


def _gunluk_satirlari(oyun_gunlugu, kadar_tarih=None):
    """LeagueGameLog satırlarını (isteğe bağlı) tarihe kadar süzer.
    `kadar_tarih` VERİLİRSE o gün HARİÇ tutulur (gece öncesi durumu)."""
    rs = oyun_gunlugu["resultSets"][0]
    i = {ad: n for n, ad in enumerate(rs["headers"])}
    satirlar = rs["rowSet"]
    if kadar_tarih:
        satirlar = [r for r in satirlar if str(r[i["GAME_DATE"]])[:10] < kadar_tarih]
    return {"resultSets": [{"headers": rs["headers"], "rowSet": satirlar}]}, i


def _son_form(oyun_gunlugu, kod, adet=SIRALAMA_FORM_MAC):
    """[{g, rakip, skor}, ...] — ESKİDEN YENİYE, sonuncusu bu geceki maç.

    Kutucuk artık sadece renk değil: dokununca rakibi ve skoru söylüyor
    (kullanıcı kuralı). Rakibin skoru AYNI maçın karşı satırından
    okunuyor — günlükte her maç iki kez, iki takım için yazılı."""
    rs = oyun_gunlugu["resultSets"][0]
    i = {ad: n for n, ad in enumerate(rs["headers"])}
    # Maç kimliği → o maçtaki takım/skor çiftleri.
    skor_by_mac = {}
    if "GAME_ID" in i:
        for r in rs["rowSet"]:
            skor_by_mac.setdefault(r[i["GAME_ID"]], {})[r[i["TEAM_ABBREVIATION"]]] = r[i["PTS"]]
    maclar = sorted((r for r in rs["rowSet"] if r[i["TEAM_ABBREVIATION"]] == kod),
                    key=lambda r: str(r[i["GAME_DATE"]])[:10])
    cikti = []
    for r in maclar[-adet:]:
        # "OKC vs. HOU" / "GSW @ LAL" → rakip kodu
        parcalar = str(r[i["MATCHUP"]]).replace(" vs. ", " @ ").split(" @ ")
        rakip_kod = parcalar[-1].strip() if len(parcalar) == 2 else ""
        bizim = r[i["PTS"]]
        rakip_skor = (skor_by_mac.get(r[i["GAME_ID"]], {}).get(rakip_kod)
                      if "GAME_ID" in i else None)
        cikti.append({
            "g": r[i["WL"]] == "W",
            "rakip": TAKIM_KISA.get(rakip_kod, rakip_kod),
            "skor": f"{bizim}-{rakip_skor}" if rakip_skor is not None else "",
        })
    return cikti


def _siralama_hareketi(ham, tarih_str, gece_takimlari):
    """Yer değiştiren takımlar. Hareket yoksa boş liste -> bölüm çıkmaz."""
    from gercekler import puan_durumu_hesapla
    gunluk = ham.get("puan_durumu")
    if not gunluk or not gece_takimlari:
        return []
    # Sezonun kaçıncı OYUN GÜNÜ? Takvim günü değil, gerçekten maç
    # oynanan gün sayısı — lig arası günler sayılmasın.
    try:
        rs = gunluk["resultSets"][0]
        i = {ad: n for n, ad in enumerate(rs["headers"])}
        oyun_gunleri = {str(r[i["GAME_DATE"]])[:10] for r in rs["rowSet"]}
        gecilen = len({g for g in oyun_gunleri if g <= tarih_str})
    except Exception:
        return []
    if gecilen <= SIRALAMA_ASGARI_GUN:
        return []
    try:
        once_ham, _ = _gunluk_satirlari(gunluk, kadar_tarih=tarih_str)
        once = puan_durumu_hesapla(once_ham, tarih_str)
        sonra = puan_durumu_hesapla(gunluk, tarih_str)
    except Exception:
        return []
    satirlar = []
    for kod in gece_takimlari:
        a, b = once.get(kod), sonra.get(kod)
        if not a or not b:
            continue
        eski, yeni = a.get("konferans_sira"), b.get("konferans_sira")
        if not eski or not yeni or eski == yeni:
            continue          # yer değiştirmeyen takım görünmüyor
        satirlar.append({
            "takim": kod,
            "takim_adi": _takim_adi(kod),
            "eski": eski,
            "yeni": yeni,
            # Pozitif = YÜKSELDİ (sıra numarası küçüldü).
            "degisim": eski - yeni,
            "konferans": b.get("konferans"),
            "form": _son_form(gunluk, kod),
        })
    # Çok yükselen en üstte, çok düşen en altta. Eşitlikte YENİ SIRA
    # belirleyici (üst sıradaki önce) — yoksa aynı miktarda oynayan
    # takımların dizilişi rastgele görünüyordu.
    satirlar.sort(key=lambda x: (-x["degisim"], x["yeni"]))
    # Takım rengi KULLANILMIYOR (kullanıcı kararı: küçük dikdörtgenler
    # kalktı), o yüzden çakışma çözümü de çağrılmıyor — kullanılmayan
    # alan üretmiyoruz. Kural duruyor; renk geri gelirse tek satır.
    return satirlar


# ---------------------------------------------------------------------------
# "AYRICA" — kilometre taşları, akışın DIŞINDA
# ---------------------------------------------------------------------------
#
# "Sen uyurken" MAÇLARI sıralıyor ve sırası rozete bağlı. Triple-double
# ise bir OYUNCU haberi — maçın izlenmeye değer olup olmamasıyla ilgisi
# yok. İkisini tek listede karıştırmak, ya rozet sıralamasını bozuyordu
# ya da haberi tamamen düşürüyordu (2.45 rozetli maçtaki Cade Cunningham
# triple-double'ı kesim çizgisinin altında kalıyordu).
#
# Çözüm: kilometre taşları akıştan çıkıp bölümün altına, kendi satırına
# alındı. Rozetle de saatle de ilgisi yok.
AYRICA_EN_FAZLA = 3

# Kilometre eşiği → (okunur ifade, fiil). Fiil istatistiğe göre:
# sayı/üçlük ATILIR, ribaund TOPLANIR, asist ve blok YAPILIR.
# ("asist verdi/dağıttı" yasak — bkz. config/yasakli.json.)
_AYRICA_FIIL = {
    "sayi": "attı", "uclu": "attı", "ribaund": "topladı",
    "asist": "yaptı", "blok": "yaptı",
}


# Eşik birimi → (kutu skor alanı, okunur birim). Kilometre kaydı sadece
# sayı/ribaund/asist taşıyor; blok ve üçlük için kutu skora bakılıyor,
# yoksa "5+ blok" gibi eşik metni yazılırdı — oysa gerçek değer elimizde.
_AYRICA_ALAN = {
    "sayi": ("pts", "sayı"), "uclu": ("3pm", "üçlük"), "ribaund": ("reb", "ribaund"),
    "asist": ("ast", "asist"), "blok": ("blk", "blok"),
}


def _ayrica_ifadesi(kilo, kutu):
    """'triple-double yaptı' / '43 sayı attı' — gerçek değer yazılır."""
    esik = kilo.get("esik") or ""
    okunur = _ESIK_OKUNUR.get(esik, esik.replace("_", " "))
    if "double" in esik:
        return f"{okunur} yaptı"
    birim = esik.split("_", 1)[1] if "_" in esik else ""
    alan, birim_okunur = _AYRICA_ALAN.get(birim, (None, birim))
    fiil = _AYRICA_FIIL.get(birim, "yaptı")
    deger = (kutu or {}).get(alan) if alan else None
    if isinstance(deger, int):
        return f"{deger} {birim_okunur} {fiil}"
    return f"{okunur} {fiil}"


def _ayrica_satiri(gercek_gece, ham, brief):
    """[{isim, ifade, takim}, ...] — en fazla AYRICA_EN_FAZLA, en NADİR olanlar.

    Akışta cümlesi olan bir oyuncu buraya TEKRAR girmiyor: aynı haberi
    iki kez okutmak bölümü uzatmaktan başka bir şey yapmaz."""
    anilan = " ".join(b.get("metin", "") for b in brief if b.get("metin"))
    kod_by_oyuncu, kutu_by_oyuncu = {}, {}
    for gid, hm in (ham.get("maclar") or {}).items():
        bt = hm["box_traditional"]["boxScoreTraditional"]
        for taraf in (bt["homeTeam"], bt["awayTeam"]):
            for p in taraf["players"]:
                ad = _dogru_oyuncu_adi(
                    p["personId"], f"{p['firstName']} {p['familyName']}".strip())
                kod_by_oyuncu[ad] = taraf["teamTricode"]
                st = p["statistics"]
                kutu_by_oyuncu[ad] = {
                    "pts": st["points"], "reb": st["reboundsTotal"],
                    "ast": st["assists"], "blk": st["blocks"],
                    "3pm": st["threePointersMade"],
                }
    adaylar = []
    for gid, kayitlar in (gercek_gece.get("maclar") or {}).items():
        for f in kayitlar:
            if f["tur"] != "kilometre":
                continue
            kilo = f["veri"]
            ad = kilo.get("oyuncu")
            if not ad:
                continue
            soyad = ad.strip().split()[-1]
            if soyad.lower() in anilan.lower():
                continue          # akışta zaten anıldı
            esik = kilo.get("esik")
            nadirlik = (_KILOMETRE_ONCELIK.index(esik)
                        if esik in _KILOMETRE_ONCELIK else 99)
            adaylar.append({
                "isim": ad,
                "ifade": _ayrica_ifadesi(kilo, kutu_by_oyuncu.get(ad)),
                "takim": TAKIM_KISA.get(kod_by_oyuncu.get(ad, ""), kod_by_oyuncu.get(ad, "")),
                "_nadirlik": nadirlik,
                "_gmsc": kilo.get("gmsc", 0),
            })
    # En NADİR olanlar önce; eşitlikte GmSc.
    adaylar.sort(key=lambda a: (a["_nadirlik"], -(a["_gmsc"] or 0)))
    secilen = adaylar[:AYRICA_EN_FAZLA]
    for a in secilen:
        a.pop("_nadirlik", None)
        a.pop("_gmsc", None)
    return secilen


def derle(tarih_str):
    gercek_gece = _yukle(GERCEK_DIZIN, tarih_str)
    skor_gece = _yukle(SKOR_DIZIN, tarih_str)
    taslak = _yukle(TASLAK_DIZIN, tarih_str)
    ham = _yukle(HAM_DIZIN, tarih_str)
    turk_oyunculari = _turk_oyunculari_yukle()

    plan = gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece)
    rozet_by_gid = {m["mac_id"]: m for m in skor_gece["maclar"]}
    # Akıştaki "maçın en etkilisi" satırı için — oyuncu istatistiği akış
    # olayı değil, oyuncu_stat gerçeğinden geliyor.
    en_iyi_performans_by_gid = {m["mac_id"]: m.get("en_iyi_performans")
                                for m in skor_gece["maclar"]}
    # GECE ÇAPINDA kalıp sayacı — aynı cümle kalıbı iki kezden fazla
    # kullanılmasın. Tip sayacı KALKTI: tip artık maçın şekline göre
    # sabit yuvalardan geliyor, çeşitlilik için oynatılamaz.
    _akis_kalip_sayaci = {}
    taslak_maclar = taslak["maclar"]

    # Aynı anahtar (hesapla.siralama_anahtari) — rozet eşitliğinde dram
    # ve final farkı karar veriyor, sıralama iki koşuda da aynı çıkıyor.
    sira = sorted(rozet_by_gid.keys(),
                  key=lambda g: siralama_anahtari(rozet_by_gid[g]))
    # Kullanıcı kararı: Mutlaka bil'e 8.5+ olan en fazla 3 maç girer
    # (yaz._mutlaka_ve_diger ile AYNI mantık — tek kaynak, iki ayrı
    # eşik tanımı olmasın). Her biri kendi "g-mutlaka-{i}" id'sini alır,
    # id-0 gecenin en yüksek rozetlisi ve tam anlatı taşır.
    mutlaka_liste, _ = _mutlaka_ve_diger(skor_gece)
    mutlaka_gidleri = [m["mac_id"] for m in mutlaka_liste]
    mutlaka_id_by_gid = {gid: f"g-mutlaka-{i}" for i, gid in enumerate(mutlaka_gidleri)}

    # ---- night strip (bars) ----
    bars = []
    for i, gid in enumerate(sorted(rozet_by_gid.keys(), key=lambda g: rozet_by_gid[g].get("mac_id", g))):
        skor_bilgi = rozet_by_gid[gid]
        bars.append({
            "sira": i + 1,
            "mac": f"{_takim_adi(skor_bilgi['ev'])} — {_takim_adi(skor_bilgi['dep'])}",
            "rozet": skor_bilgi["rozet"],
            "id": mutlaka_id_by_gid.get(gid, f"a-{gid}"),
        })

    # ---- "Sen uyurken" (eski adı: 30 saniyede gece) ----
    # Sıralama artık ROZETE göre değil, TSİ BAŞLAMA SAATİNE göre: gece
    # gerçekten bir gece gibi, akış hâlinde okunsun (kullanıcı kararı).
    # İÇERİK KURALI DEĞİŞMEDİ: bir maç ancak gerçek bir olguya
    # dayanabiliyorsa satır alıyor; o eleme yaz.py'de yapılıyor.
    # Kullanıcı kararı (B seçeneği): gecenin BÜTÜN maçları satır alıyor,
    # ama CÜMLE sadece anlatacak bir olgusu olana veriliyor. Diğerleri
    # yalnızca saat + skor gösteriyor.
    #
    # Neden böyle: bölüm kendini KRONOLOJİ olarak sunuyordu ama 10 maçın
    # 3'ünü gösteriyordu, akış eksik hissettiriyordu. Her maça cümle
    # yazmak ise dolgu üretmek olurdu ("Sacramento, Portland'ı yendi"
    # bir bilgi değil). Skor bir OLGU, uydurma değil — o yüzden cümlesiz
    # satır kuralı çiğnemiyor.
    _brief_metin = {}
    for b in taslak.get("brief", []):
        hedef = b.get("hedef_mac")
        if hedef:
            _brief_metin[hedef] = b["metin"]
    brief = []
    for gid in rozet_by_gid:
        bilgi = rozet_by_gid.get(gid) or {}
        ham_mac = ham["maclar"].get(gid)
        kanca_gerekce = plan.get(gid, {}).get("kanca_gerekce", "")
        metin = _brief_metin.get(gid, "")
        brief.append({
            "metin": metin,
            "anlatili": bool(metin),
            "hedef_id": mutlaka_id_by_gid.get(gid, f"a-{gid}"),
            "icon": _brief_ikonu(kanca_gerekce) if metin else "default",
            "saat": _tsi_baslama(ham_mac, tarih_str) if ham_mac else None,
            # Sıralama ANI'na göre; "HH:MM" dizesi gece yarısını aşan
            # akışta 23:30'u en sona atıyordu.
            "_an": _tsi_baslama_dt(ham_mac, tarih_str) if ham_mac else None,
            "_gid": gid,
            "rozet": bilgi.get("rozet"),
            # Üç biçim, üç farklı yer için — ölçüldü (375px içerik
            # sütunu 252px, masaüstü 577px):
            #   kod       "DEN 101 – HOU 115"                  1.07 satır
            #   şehir     7 satırın 4'ü sarmalanıyor
            #   tam ad    "Denver Nuggets 101 – Houston …"     3.54 satır
            # Yani tam ad MOBİLDE SIĞMIYOR. Cümlesiz satırda skor tek
            # tanım olduğu için orada mümkün olan en okunur biçim
            # kullanılıyor: masaüstünde tam ad, mobilde şehir.
            # Cümleli satırda takımlar zaten cümlede geçiyor, orada kod
            # yeterli — aynı adı iki kez yazmak gereksiz.
            "skor": (f"{bilgi['ev']} {bilgi['ev_skor']} – "
                     f"{bilgi['dep']} {bilgi['dep_skor']}") if bilgi else "",
            "skor_tam": (f"{_takim_adi(bilgi['ev'])} {bilgi['ev_skor']} – "
                         f"{_takim_adi(bilgi['dep'])} {bilgi['dep_skor']}") if bilgi else "",
        })
    # Saati olmayan satır sona: uydurma saat yazmaktansa sırayı bozmamak.
    # Anahtar TAM AN — takvim günü değişimi burada hesaba katılıyor.
    _uzak = datetime.max
    brief.sort(key=lambda x: (x["_an"] is None,
                              x["_an"].replace(tzinfo=None) if x["_an"] else _uzak))
    if brief:
        # "gecenin maçı" en yüksek rozetli maç — anlatısı olsun olmasın,
        # gecenin en iyisi odur.
        # "gecenin maçı" da aynı anahtarla: iki maç aynı rozeti aldığında
        # listede önce gelen değil, DRAMI yüksek olan seçiliyor.
        _sirali_gid = {g: i for i, g in enumerate(sira)}
        _en_yuksek = min(brief, key=lambda x: _sirali_gid.get(x["_gid"], 10**6))
        for i, x in enumerate(brief):
            # Etiket SADECE hak edene. Öncelik: gecenin maçı > ilki > kapanış.
            if x is _en_yuksek:
                x["etiket"], x["one_cikan"] = "gecenin maçı", True
            # SAATİ BİLİNMEYEN MAÇ UÇ ETİKETİ ALAMAZ. "Gecenin ilki" ve
            # "kapanış" birer ZAMAN iddiası; saati olmayan satır listenin
            # sonuna konuyor (uydurma saat yazmamak için) ama bu onu
            # gecenin son maçı yapmıyor. Gerçek arıza (26 Aralık): NBA
            # servisi bir maçın başlama saati yerine 'Final' döndürdü,
            # satır sona düştü ve "kapanış" rozetini aldı — bilmediğimiz
            # bir şeyi iddia ediyorduk.
            elif i == 0 and x["_an"] is not None:
                x["etiket"], x["one_cikan"] = "gecenin ilki", False
            elif i == len(brief) - 1 and x["_an"] is not None:
                x["etiket"], x["one_cikan"] = "kapanış", False
            else:
                x["etiket"], x["one_cikan"] = "", False
    for x in brief:
        x.pop("_gid", None)         # yalnız sıralama içindi
    ayrica = _ayrica_satiri(gercek_gece, ham, brief)
    anlar = [x["_an"] for x in brief if x["_an"]]
    saatli = [x["saat"] for x in brief if x["saat"]]
    _dakika = (int((anlar[-1] - anlar[0]).total_seconds() // 60)
               if len(anlar) > 1 else None)
    for x in brief:
        x.pop("_an", None)          # JSON'a datetime yazılmaz
    brief_ozet = {
        "ilk": saatli[0] if saatli else None,
        "son": saatli[-1] if saatli else None,
        "mac": len(brief),
        "anlatili": sum(1 for x in brief if x["anlatili"]),
        # DİKKAT: "son", gecenin BİTİŞİ değil son maçın BAŞLAMA saati.
        # Bitiş saati veride yok ve uydurulmuyor.
        "dakika": _dakika,
        "sure": _sure_metni(_dakika),
    }

    # ---- mutlaka bil (liste — id-0 tam anlatı, diğerleri kısa) ----
    mutlaka = []
    for i, gid in enumerate(mutlaka_gidleri):
        mv = taslak_maclar.get(gid, {})
        mutlaka_skor = rozet_by_gid[gid]
        ozet_metni = mv.get("ozet") or mv.get("ozet_kisa", "")
        tum_metin = " ".join([mv.get("baslik", ""), mv.get("neden_onemli", ""), ozet_metni])
        kaybeden_kod = plan.get(gid, {}).get("olgu_ham", {}).get("kaybeden")
        mutlaka.append({
            "id": mutlaka_id_by_gid[gid],
            # Yayın kapısı bloğu maç kimliğinden buluyor (akış satırlarını
            # okumak için). Blok id'si sıra numarası taşıyor, maç kimliği
            # değil — eşleşme için ayrı alan gerekti.
            "mac_id": gid,
            "kisa": i > 0,
            "mac": f"{_takim_adi(mutlaka_skor['ev'])} — {_takim_adi(mutlaka_skor['dep'])}",
            "skor": f"{mutlaka_skor['ev_skor']}–{mutlaka_skor['dep_skor']}",
            "rozet": mutlaka_skor["rozet"],
            "baslik": mv.get("baslik", ""),
            "neden_onemli": mv.get("neden_onemli", ""),
            # PARAGRAF GÖVDESİ KALKTI (kullanıcı kararı). Yerine maç
            # akışı geliyor: dört satır, tamamen şablon, LLM'e hiç
            # uğramıyor. Alan `ozet` boş bırakılmıyor, HİÇ yazılmıyor —
            # boş string oluşturucuda "gövde var ama sessiz" gibi
            # görünürdü.
            "akis": _mac_akisi(gercek_gece["maclar"][gid],
                               en_iyi_performans_by_gid.get(gid),
                               kalip_sayaci=_akis_kalip_sayaci,
                               anilan_metin=" ".join(
                                   [mv.get("baslik", ""), mv.get("neden_onemli", "")])),
            "box": _box_score(ham["maclar"][gid], tum_metin, kaybeden_kod, gercek_gece["maclar"][gid]),
            # Sol ray rengi: KAZANAN takımın rengi (aşağıda çakışma
            # çözümünden geçiyor).
            "kazanan_kod": (mutlaka_skor["ev"]
                            if mutlaka_skor["ev_skor"] >= mutlaka_skor["dep_skor"]
                            else mutlaka_skor["dep"]),
        })

    # Sol ray rengi — çakışma kuralı burada da geçerli (kullanıcı
    # kuralı): aynı gecede iki kazanan yakın renkteyse DÜŞÜK rozetli
    # olan kendi ikincil rengine geçiyor. Öncelik ölçütü GmSc değil
    # ROZET; `renk_cakismasini_coz` sıralamayı `_gmsc` alanından
    # okuduğu için rozet oraya yazılıyor.
    _ray = [{"takim": m["kazanan_kod"], "_gmsc": m["rozet"]} for m in mutlaka]
    renk_cakismasini_coz(_ray)
    for m, r in zip(mutlaka, _ray):
        m["ray_renk"] = r["renk"]
        m["ray_asil"] = r["asil_renk"]
        m["ray_degisti"] = r["renk_degisti"]

    # ---- gecenin beşi ----
    gecenin_besi = _gecenin_besi(ham, gercek_gece, mutlaka_id_by_gid, rozet_by_gid)

    # ---- yükselen / düşen ----
    # Bu gece OYNAYAN her oyuncu aday; oynamayan iki listede de yok.
    _gece_oyunculari = []
    for _gid, _hm in ham["maclar"].items():
        _bt = _hm["box_traditional"]["boxScoreTraditional"]
        _ev, _dep = _bt["homeTeam"], _bt["awayTeam"]
        for _taraf, _rakip in ((_ev, _dep), (_dep, _ev)):
            for _p in _taraf["players"]:
                _st = _p["statistics"]
                if not _st["minutes"]:
                    continue
                _gece_oyunculari.append({
                    "id": _p["personId"],
                    "isim": _dogru_oyuncu_adi(
                        _p["personId"], f"{_p['firstName']} {_p['familyName']}".strip()),
                    "takim": _taraf["teamTricode"],
                    "pos": _p.get("position") or "",
                    "sayi": _st["points"],
                    "dakika": _dakikayi_coz(_st["minutes"]),
                    "rakip": _rakip["teamTricode"],
                    "_gmsc": gmsc(_st),
                })
    yukselen, dusen = _formda_listeler(ham, None, _gece_oyunculari)

    # ---- sıralama hareketi ----
    _gece_takimlari = sorted({o["takim"] for o in _gece_oyunculari})
    siralama = _siralama_hareketi(ham, tarih_str, _gece_takimlari)

    # ---- değerse bak (rozet 6.0+, "mutlaka" olarak seçilmemiş) / bunları geç ----
    # Kullanıcı düzeltmesi: hesapla.py baştan beri üç katman üretiyordu
    # (mutlaka/ikinci/gec) ama sayfada iki bölüm vardı — 126-124 biten,
    # Doğu'nun 2. sırasındaki takımın kazandığı, iki oyuncunun 34'er sayı
    # attığı bir maç "Bunları geç"te duruyordu. Üçüncü bölüm eklendi.
    # DİKKAT: "katman" bir EŞİK sınıflandırması — birden fazla maç
    # "mutlaka" eşiğini (rozet>=8.5) geçebilir, ama sadece EN YÜKSEĞİ
    # gerçek "Mutlaka bil" olur (bkz. yaz._mutlaka_ve_diger). Katmanı
    # "mutlaka" olan ama seçilmeyen bir maç (gerçek üretim bug'ı: ilk
    # sürüm bunu "ikinci" değil diye "Bunları geç"e düşürüyordu) da
    # "Değerse bak"ı hak eder — sadece "gec" katmanı "Bunları geç"te kalır.
    degerse_bak = []
    diger = []
    for gid in sira:
        if gid in mutlaka_id_by_gid:
            continue
        skor_bilgi = rozet_by_gid[gid]
        v = taslak_maclar.get(gid, {})
        kaybeden_kod = plan.get(gid, {}).get("olgu_ham", {}).get("kaybeden")
        girdi = {
            "id": f"a-{gid}",
            "mac": f"{_takim_adi(skor_bilgi['ev'])} — {_takim_adi(skor_bilgi['dep'])}",
            "skor": f"{skor_bilgi['ev_skor']}–{skor_bilgi['dep_skor']}",
            "rozet": skor_bilgi["rozet"],
            "why": _why_metni(plan.get(gid, {})),
            "metin": v.get("gec_satiri", ""),
            "box": _box_score(ham["maclar"][gid], v.get("gec_satiri", ""), kaybeden_kod, gercek_gece["maclar"][gid]),
        }
        girdi["kazanan_kod"] = (skor_bilgi["ev"]
                               if skor_bilgi["ev_skor"] >= skor_bilgi["dep_skor"]
                               else skor_bilgi["dep"])
        if skor_bilgi["katman"] in ("mutlaka", "ikinci"):
            # AKIŞ "Göz at"ta da var (kullanıcı kararı: iki bölümde de
            # paragraf kalktı). "Bunları geç" tek satırlık kalıyor —
            # orada zaten anlatı yok.
            girdi["akis"] = _mac_akisi(gercek_gece["maclar"][gid],
                                       en_iyi_performans_by_gid.get(gid),
                                       satir_sayisi=AKIS_GOZAT_SATIR,
                                       kalip_sayaci=_akis_kalip_sayaci,
                                       anilan_metin=v.get("gec_satiri", ""))
            degerse_bak.append(girdi)
        else:
            diger.append(girdi)

    # SOL RAY "Göz at"ta da var (blok zemini kullanıcı kararı). Renk
    # çakışması burada da çözülüyor — aynı gecede yakın renkli iki
    # kazanan varsa düşük rozetli kendi ikincil rengine geçiyor.
    _ray_g = [{"takim": m["kazanan_kod"], "_gmsc": m["rozet"]} for m in degerse_bak]
    renk_cakismasini_coz(_ray_g)
    for m, r in zip(degerse_bak, _ray_g):
        m["ray_renk"] = r["renk"]

    # ---- türkler ----
    turkler = _turkler(ham, turk_oyunculari, mutlaka_id_by_gid, rozet_by_gid)

    return {
        "tarih": tarih_str,
        "uretildi": taslak.get("uretildi", ""),
        "mac_sayisi": len(rozet_by_gid),
        "bars": bars,
        "brief": brief,
        "brief_ozet": brief_ozet,
        "brief_ayrica": ayrica,
        "mutlaka": mutlaka,
        "gecenin_besi": gecenin_besi,
        # Oyuncu kartları: üç giriş de (gecenin beşi sahası, gecenin beşi
        # kartı, kutu skor tablosu) BU haritayı okuyor — tek bileşen,
        # tek veri.
        "oyuncular": _oyuncu_kartlari(ham, tarih_str),
        "yukselen": yukselen,
        "dusen": dusen,
        "siralama": siralama,
        "degerse_bak": degerse_bak,
        "diger": diger,
        "turkler": turkler,
        # Bölüm en alta ancak HİÇ KİMSE sahaya çıkmadıysa düşer. Biri
        # oynayıp diğeri oynamadıysa bölüm üstte kalır ve oynamayan
        # "OYNAMADI" satırıyla aynı blokta görünür.
        "turkler_bekleyen": None if any(t.get("oynadi") for t in turkler) else _turkler_bekleyen(ham, turk_oyunculari),
        # Aşağıdaki iki bölümün üretim tarafı henüz YOK (bkz. modül
        # docstring'i) — HTML bu anahtarlar boşsa ilgili bölümü gizler.
        "gecenin_notlari": [],
        "genis_aci": None,
    }


def yaz_dosya(tarih_str, latest=True):
    veri = derle(tarih_str)
    DIST_DIZIN.mkdir(exist_ok=True)
    metin = json.dumps(veri, ensure_ascii=False, indent=2)
    hedef = DIST_DIZIN / f"{tarih_str}.json"
    hedef.write_text(metin)
    print(f"Yazıldı: {hedef}")
    if latest:
        (DIST_DIZIN / "latest.json").write_text(metin)
        print(f"Yazıldı: {DIST_DIZIN / 'latest.json'} (en güncel gece işaretçisi)")
    return hedef


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Kullanım: python3 derle.py <tarih YYYY-MM-DD>")
        sys.exit(1)
    yaz_dosya(sys.argv[1])
