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

import json
import unicodedata
from pathlib import Path

from hesapla import gmsc
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
    "LAC": "LA Clippers", "LAL": "LA Lakers", "MEM": "Memphis", "MIA": "Miami",
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
        "isim": _dogru_oyuncu_adi(p["personId"], f"{p['firstName']} {p['familyName']}".strip()),
        "takim": takim_kodu,
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


def _box_score(ham_mac, metin="", kaybeden_kod=None):
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
            },
        }

    ev_taraf, dep_taraf = taraf(ev), taraf(dep)

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

    return {"ev": ev_taraf, "dep": dep_taraf, "wtf": wtf}


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
        o.pop("gmsc", None)
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


def derle(tarih_str):
    gercek_gece = _yukle(GERCEK_DIZIN, tarih_str)
    skor_gece = _yukle(SKOR_DIZIN, tarih_str)
    taslak = _yukle(TASLAK_DIZIN, tarih_str)
    ham = _yukle(HAM_DIZIN, tarih_str)
    turk_oyunculari = _turk_oyunculari_yukle()

    plan = gece_kalip_plani(tarih_str, gercek_gece, ham, skor_gece)
    rozet_by_gid = {m["mac_id"]: m for m in skor_gece["maclar"]}
    taslak_maclar = taslak["maclar"]

    sira = sorted(rozet_by_gid.keys(), key=lambda g: -rozet_by_gid[g]["rozet"])
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

    # ---- brief ----
    brief = []
    for b in taslak.get("brief", []):
        hedef = b.get("hedef_mac")
        kanca_gerekce = plan.get(hedef, {}).get("kanca_gerekce", "")
        brief.append({
            "metin": b["metin"],
            "hedef_id": mutlaka_id_by_gid.get(hedef, f"a-{hedef}"),
            "icon": _brief_ikonu(kanca_gerekce),
        })

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
            "kisa": i > 0,
            "mac": f"{_takim_adi(mutlaka_skor['ev'])} — {_takim_adi(mutlaka_skor['dep'])}",
            "skor": f"{mutlaka_skor['ev_skor']}–{mutlaka_skor['dep_skor']}",
            "rozet": mutlaka_skor["rozet"],
            "baslik": mv.get("baslik", ""),
            "neden_onemli": mv.get("neden_onemli", ""),
            "ozet": ozet_metni,
            "box": _box_score(ham["maclar"][gid], tum_metin, kaybeden_kod),
        })

    # ---- gecenin beşi ----
    gecenin_besi = _gecenin_besi(ham, gercek_gece, mutlaka_id_by_gid, rozet_by_gid)

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
            "box": _box_score(ham["maclar"][gid], v.get("gec_satiri", ""), kaybeden_kod),
        }
        if skor_bilgi["katman"] in ("mutlaka", "ikinci"):
            degerse_bak.append(girdi)
        else:
            diger.append(girdi)

    # ---- türkler ----
    turkler = _turkler(ham, turk_oyunculari, mutlaka_id_by_gid, rozet_by_gid)

    return {
        "tarih": tarih_str,
        "uretildi": taslak.get("uretildi", ""),
        "mac_sayisi": len(rozet_by_gid),
        "bars": bars,
        "brief": brief,
        "mutlaka": mutlaka,
        "gecenin_besi": gecenin_besi,
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
