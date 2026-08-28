"""
cek.py — OVERNIGHT boru hattının 1. adımı.

Girdi:  bir tarih (YYYY-MM-DD)
Çıktı:  ham/{tarih}.json — nba_api'den gelen işlenmemiş veri

Kullanım:
    python3 cek.py 2026-01-02
    python3 cek.py 2026-01-02 --force   (ham dosya varsa bile yeniden çek)

Mimari kural: TÜM nba_api çağrıları bu dosyada kalır. NBA'nın stats API'sini
değiştirmesi (V2 uç noktalarının bu sezon için boş dönmesi gibi) burada tek
dosyayı değiştirerek çözülür; boru hattının geri kalanı ham JSON'un şeklini
bilmez.

Bilinen durum (2026-01-02 ile doğrulandı, bkz. overnight-teknik-sartname.md):
- ScoreboardV2, PlayerGameLogs, LeagueGameLog: 2025-26 sezonu için çalışıyor.
- BoxScoreTraditionalV2, BoxScoreAdvancedV2, PlayByPlayV2: 2025-26 sezonu için
  boş dönüyor (NBA tarafında kapatılmış). Bunların yerine V3 sürümleri kullanılıyor.
- BoxScoreSummaryV2: sadece GameSummary/GameInfo/LineScore/LastMeeting alanları
  dolu geliyor; OtherStats (en büyük fark, lider değişimi), Officials, InactivePlayers,
  SeasonSeries bu sezon için boş. En büyük fark / lider değişimi play-by-play'den
  (V3, her olayda anlık skor taşıyor) hesaplanacak. Kadro dışı oyuncular
  BoxScoreTraditionalV3'teki "comment" alanından (örn. "DND - Injury/Illness")
  çıkarılacak. Hakem bilgisi için çalışan bir kaynak yok; gerçek türleri
  listesinde (şartname bölüm 4) zaten yer almadığından bu boşluk boru hattını
  etkilemiyor.
- LeagueStandingsV3 KULLANILMIYOR: tarih parametresi almıyor, her zaman
  o anki GÜNCEL puan durumunu döndürüyor — geçmiş bir tarih için çekilse
  bile. Geriye dönük kalibrasyonda (9. adım) bu, her gecede o gecenin değil
  bugünün puan durumunu yazardı; sessiz ve tehlikeli bir hata. Onun yerine
  LeagueGameLog (date_to_nullable=hedef tarih, dahil) kullanılıyor — takım
  başına o tarihe kadar oynanmış her maçın sonucu geliyor, derece ve seri
  (galibiyet/mağlubiyet serisi) buradan hesaplanabiliyor. Konferans/lig
  sırası ve seri, ham veriden değil gercekler.py'de hesaplanacak.

Tarih kesimi tuzağı: PlayerGameLogs'taki date_to_nullable parametresi VERİLEN
GÜNÜ DAHİL EDİYOR. Hedef gecenin oyuncu sapmaları o geceden ÖNCEKİ maçlarla
hesaplanmalı, o yüzden burada date_to olarak hedef tarihin BİR GÜN ÖNCESİ
gönderiliyor. LeagueGameLog'da ise tam tersi istiyoruz — hedef gecenin kendi
maçları da derece/seriye dahil olmalı, o yüzden orada date_to hedef tarihin
KENDİSİ. Bu, hesapla.py'nin doğru çalışması için kritik.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from nba_api.stats.endpoints import (
    scoreboardv2,
    boxscoretraditionalv3,
    boxscoreadvancedv3,
    boxscoresummaryv2,
    playbyplayv3,
    leaguegamelog,
    playergamelogs,
)

HAM_DIZIN = Path(__file__).parent / "ham"
ISTEK_ARASI_BEKLEME_SN = 0.6

# stats.nba.com düzenli olarak zaman aşımı ve 5xx veriyor. Tek bir
# hıçkırık bütün sabahı düşürmemeli: sistem kimse başında olmadan
# çalışacak (projenin üçüncü pazarlıksız kuralı). Gerçek olay
# (2026-08-26): tek bir ReadTimeout `cek.py`yi düşürdü, `yayin.py uret`
# çöktü, gece hiç üretilmedi.
# nba_api varsayılanı 30 sn. Yeniden deneme eklenince bu çok pahalı
# oluyor: 46 çağrılık bir gecede hepsi düşerse 4×30sn × 46 = 103 dakika,
# oysa iş 45 dakikada kesiliyor — yani dayanıklılık ekleyeyim derken
# işi zaman aşımından öldürecek bir tasarım çıkmıştı.
# 15 sn fazlasıyla cömert (NBA normalde 1-3 sn'de cevaplıyor) ve
# 3 denemeyle en kötü durum ~39 dakikaya iniyor.
# ÖLÇÜM (2026-08-27): stats.nba.com bağlantıyı 26 saniye açık tutup
# düşürdü — hem GitHub koşucusundan hem de geliştirme makinesinden. Yani
# IP engeli değil, API'nin kendisi dönemsel olarak tıkalı. Eski politika
# (3 deneme, 2+4 sn bekleme, 15 sn zaman aşımı) toplam ~50 saniye
# dayanıyordu; bu tür bir tıkanmayı atlatmaya yetmiyor.
ISTEK_ZAMAN_ASIMI_SN = 20
YENIDEN_DENEME = 4
DENEME_ARASI_TABAN_SN = 5.0

# Sabrın SINIRI da olmalı. Tek çağrının kötü senaryosu ~115 sn; 46 çağrı
# körlemesine bu kadar beklerse iş 60 dakikalık tavanı aşar ve GitHub onu
# yarıda keser — o zaman ne veri olur ne düzgün hata. Bu bütçe, TOPLAM
# yeniden-deneme beklemesini sınırlıyor: aşılınca yeniden deneme durur,
# iş hızlı ve TEMİZ düşer. Bir sonraki zaman slotu (04:00, 05:30 ve
# Vercel) zaten yeniden deneyecek — asıl dayanıklılık orada.
TOPLAM_BEKLEME_BUTCESI_SN = 900.0
_toplam_beklenen = {"sn": 0.0}


def yeniden_deneme_butcesini_sifirla():
    """Her çekim başında bütçe sıfırlanır (testler ve arka arkaya
    çağrılar birbirinin bütçesini yemesin)."""
    _toplam_beklenen["sn"] = 0.0


def _dayanikli(ad, fn):
    """Ağ çağrısını üstel bekleyerek yeniden dener.

    Sadece AĞ hatalarında tekrar denenir; veri hatası (bozuk JSON,
    beklenmeyen şema) tekrar denemeyle düzelmez ve hemen yukarı
    fırlatılır — yoksa gerçek bir bozulma dört kez maskelenir."""
    import requests
    son_hata = None
    for deneme in range(1, YENIDEN_DENEME + 1):
        basladi = time.monotonic()
        try:
            return fn()
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError) as e:
            son_hata = e
            # Bütçe SADECE uykuyu değil, boşa geçen zaman aşımını da
            # sayıyor. Sadece uyku sayılsaydı 46 çağrının zaman aşımları
            # tek başına 60 dakikalık iş tavanını aşardı — bütçe var ama
            # koruduğu şeyi korumaz olurdu.
            _toplam_beklenen["sn"] += time.monotonic() - basladi
            if deneme == YENIDEN_DENEME:
                break
            bekle = DENEME_ARASI_TABAN_SN * (2 ** (deneme - 1))
            if _toplam_beklenen["sn"] + bekle > TOPLAM_BEKLEME_BUTCESI_SN:
                print(f"    {ad}: toplam yeniden-deneme bütçesi doldu "
                      f"({TOPLAM_BEKLEME_BUTCESI_SN:.0f} sn) — bir sonraki "
                      f"zaman slotuna bırakılıyor")
                break
            _toplam_beklenen["sn"] += bekle
            print(f"    {ad}: ağ hatası ({type(e).__name__}), {bekle:.0f} sn sonra "
                  f"yeniden denenecek ({deneme}/{YENIDEN_DENEME - 1})")
            time.sleep(bekle)
    raise RuntimeError(f"{ad}: {YENIDEN_DENEME} denemede de alınamadı — {son_hata}")


def sezon_kodu(tarih: datetime) -> str:
    """2026-01-02 -> '2025-26'. NBA sezonu ekimde başlar."""
    if tarih.month >= 10:
        baslangic_yili = tarih.year
    else:
        baslangic_yili = tarih.year - 1
    return f"{baslangic_yili}-{str(baslangic_yili + 1)[2:]}"


def gece_mac_idlerini_al(tarih_str: str) -> list[str]:
    ham = _dayanikli(f"scoreboard {tarih_str}",
                     lambda: scoreboardv2.ScoreboardV2(game_date=tarih_str, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    satirlar = ham["resultSets"][0]["rowSet"]
    basliklar = ham["resultSets"][0]["headers"]
    id_index = basliklar.index("GAME_ID")
    return ham, [satir[id_index] for satir in satirlar]


def mac_verisi_cek(game_id: str) -> dict:
    veri = {}

    veri["box_traditional"] = _dayanikli(f"box_traditional {game_id}",
        lambda: boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    veri["box_advanced"] = _dayanikli(f"box_advanced {game_id}",
        lambda: boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    veri["box_summary"] = _dayanikli(f"box_summary {game_id}",
        lambda: boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    veri["play_by_play"] = _dayanikli(f"play_by_play {game_id}",
        lambda: playbyplayv3.PlayByPlayV3(game_id=game_id, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    return veri


def sonraki_mac_tarihleri(sezon: str, tarih_str: str) -> dict:
    """Hedef geceden SONRAKİ ilk maç tarihi, takım koduna göre.

    "Bu gece Türk oyuncu sahada yoktu, ... bir sonraki maçına X'te
    çıkıyor" satırı için gerekli. Projenin temel kuralı gereği bu tarih
    uydurulamaz, veriden gelmek zorunda — tek bir LeagueGameLog çağrısı
    (date_from = ertesi gün) sezonun kalanını verir, takım başına en
    erken tarihi alıyoruz. Ham dosyaya sadece bu küçük eşleme yazılıyor,
    tüm log değil (dosya boyutu).
    """
    ertesi_gun = (datetime.strptime(tarih_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    ham = _dayanikli("sonraki_maclar", lambda: leaguegamelog.LeagueGameLog(
        season=sezon, date_from_nullable=ertesi_gun, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    kume = ham["resultSets"][0]
    basliklar = kume["headers"]
    i_takim = basliklar.index("TEAM_ABBREVIATION")
    i_tarih = basliklar.index("GAME_DATE")
    en_erken: dict = {}
    for satir in kume["rowSet"]:
        kod, gun = satir[i_takim], satir[i_tarih][:10]
        if kod not in en_erken or gun < en_erken[kod]:
            en_erken[kod] = gun
    return en_erken


# Kırpılmış ham kopya — depoya GİREN tek ham veri.
#
# NEDEN: tam ham gece başına ~19MB, depoya giremez (.gitignore'da). Ama
# hem testlerin hem YAYIN KAPISININ box score'a ihtiyacı var. Yayın işi
# ayrı bir koşucuda checkout'la başlıyor; orada `ham/` hiç oluşmuyor ve
# kapı doğrulamayı tazeleyemiyordu — kural yerelde geçerli, üretimde
# değil. Bu gerçek bir arıza oldu (2026-08-27, CI'da testler düştü).
#
# Kırpılmış kopya SADECE doğrulamanın okuduğu iki bloğu taşıyor;
# gece başına ~240KB. Bir sezon ~40MB — kabul edilebilir bedel.
KIRPILMIS_DIZIN = Path(__file__).parent / "test_verisi" / "ham"
KIRPILMIS_MAC_ALANLARI = ("box_traditional", "box_summary")


# `oyuncu_ortalama` gece başına ~4.6MB (bütün ligin sezon ortalamaları)
# ve doğrulama onu HİÇ okumuyor — dışarıda bırakılınca kırpılmış kopya
# 5MB'dan ~250KB'a düşüyor.
KIRPILMIS_DISLANAN = ("oyuncu_ortalama",)


def gzip_yaz(tarih_str, cikti):
    """Tam ham verinin sıkıştırılmış kopyası — DEPOYA GİREN taşıyıcı.

    NBA servisi GitHub koşucusunu IP bazlı engelliyor (bkz. şartname,
    "Çözülmemiş engel"). Gece verisi yerelden çekilip bu biçimde depoya
    konuyor; koşucu NBA'e hiç gitmeden üretim yapabiliyor.

    Neden kırpılmış kopya yetmiyor: onda `oyuncu_ortalama` yok ve
    Yükselen/Düşen ile oyuncu kartı onsuz kurulamıyor. Gzip'li tam kopya
    20MB → 1,7MB; 30 gecelik nefes alanı ~50MB tutuyor."""
    import gzip
    HAM_DIZIN.mkdir(exist_ok=True)
    hedef = HAM_DIZIN / f"{tarih_str}.json.gz"
    ham = json.dumps(cikti, ensure_ascii=False).encode("utf-8")
    hedef.write_bytes(gzip.compress(ham, 6))
    print(f"Yazıldı: {hedef} ({len(gzip.compress(ham, 6)) // 1024} KB, sıkıştırılmış tam kopya)")


def kirpilmis_yaz(tarih_str, cikti):
    kirpik = {k: v for k, v in cikti.items()
              if k != "maclar" and k not in KIRPILMIS_DISLANAN}
    kirpik["_not"] = ("Kırpılmış ham kopya — doğrulamanın ve testlerin "
                      "okuduğu bloklar. cek.py üretiyor, elle düzenlenmez.")
    kirpik["maclar"] = {
        gid: {a: mac[a] for a in KIRPILMIS_MAC_ALANLARI if a in mac}
        for gid, mac in cikti["maclar"].items()
    }
    KIRPILMIS_DIZIN.mkdir(parents=True, exist_ok=True)
    hedef = KIRPILMIS_DIZIN / f"{tarih_str}.json"
    hedef.write_text(json.dumps(kirpik, ensure_ascii=False))
    print(f"Yazıldı: {hedef} ({hedef.stat().st_size // 1024} KB, kırpılmış)")
    return hedef


# ---------------------------------------------------------------------------
# HAM VERİ OKUMA — tek kapı
# ---------------------------------------------------------------------------
#
# Ham dosya üç biçimde bulunabiliyor ve okuyanın hangisi olduğunu
# bilmesi gerekmiyor:
#   ham/{tarih}.json      tam kopya (yerelde, depoya girmiyor — ~20MB)
#   ham/{tarih}.json.gz   tam kopyanın sıkıştırılmışı (~1.7MB, DEPOYA GİRER)
#   test_verisi/ham/...   kırpılmış kopya (~0.4MB, oyuncu_ortalama YOK)
#
# Sıkıştırılmış biçim, NBA servisinin GitHub koşucusunu engellemesi
# yüzünden var: gece verisi yerelden çekilip depoya konuyor, koşucu da
# NBA'e hiç gitmeden üretim yapabiliyor. Kırpılmış kopya doğrulama için
# yeterli ama Yükselen/Düşen ve oyuncu kartı `oyuncu_ortalama` istiyor —
# o yüzden asıl taşıyıcı gzip'li TAM kopya.
def ham_yolu(tarih_str, kok=None):
    """Var olan ham dosyanın yolu (öncelik: tam > gzip > kırpılmış)."""
    k = Path(kok) if kok else Path(__file__).parent
    for aday in (k / "ham" / f"{tarih_str}.json",
                 k / "ham" / f"{tarih_str}.json.gz",
                 k / "test_verisi" / "ham" / f"{tarih_str}.json"):
        if aday.exists():
            return aday
    return None


def ham_metni(tarih_str, kok=None):
    """Ham verinin METNİ — biçimden bağımsız. Yoksa FileNotFoundError."""
    yol = ham_yolu(tarih_str, kok)
    if yol is None:
        raise FileNotFoundError(
            f"{tarih_str}: ham veri yok (ham/*.json, ham/*.json.gz ya da "
            f"test_verisi/ham/*.json bekleniyordu)")
    if yol.suffix == ".gz":
        import gzip
        return gzip.decompress(yol.read_bytes()).decode("utf-8")
    return yol.read_text(encoding="utf-8")


def ham_oku(tarih_str, kok=None):
    return json.loads(ham_metni(tarih_str, kok))


def cek(tarih_str: str, zorla: bool = False) -> Path:
    yeniden_deneme_butcesini_sifirla()
    hedef_dosya = HAM_DIZIN / f"{tarih_str}.json"
    if hedef_dosya.exists() and not zorla:
        print(f"{hedef_dosya} zaten var, atlanıyor (--force ile yeniden çek).")
        return hedef_dosya

    tarih = datetime.strptime(tarih_str, "%Y-%m-%d")
    sezon = sezon_kodu(tarih)
    onceki_gun = (tarih - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"{tarih_str} için çekiliyor (sezon {sezon})...")

    scoreboard_ham, mac_idleri = gece_mac_idlerini_al(tarih_str)
    print(f"  {len(mac_idleri)} maç bulundu: {mac_idleri}")

    puan_durumu = _dayanikli("puan_durumu", lambda: leaguegamelog.LeagueGameLog(
        season=sezon, date_to_nullable=tarih_str, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    oyuncu_ortalama = _dayanikli("oyuncu_ortalama", lambda: playergamelogs.PlayerGameLogs(
        season_nullable=sezon, date_to_nullable=onceki_gun, timeout=ISTEK_ZAMAN_ASIMI_SN).get_dict())
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    sonraki_maclar = sonraki_mac_tarihleri(sezon, tarih_str)
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    maclar = {}
    for game_id in mac_idleri:
        print(f"  maç {game_id} çekiliyor...")
        maclar[game_id] = mac_verisi_cek(game_id)

    cikti = {
        "tarih": tarih_str,
        "cekildi": datetime.utcnow().isoformat() + "Z",
        "sezon": sezon,
        "oyuncu_ortalama_kesim_tarihi": onceki_gun,
        "scoreboard": scoreboard_ham,
        "puan_durumu": puan_durumu,
        "oyuncu_ortalama": oyuncu_ortalama,
        "sonraki_maclar": sonraki_maclar,
        "maclar": maclar,
    }

    HAM_DIZIN.mkdir(exist_ok=True)
    hedef_dosya.write_text(json.dumps(cikti, ensure_ascii=False, indent=2))
    print(f"Yazıldı: {hedef_dosya}")
    gzip_yaz(tarih_str, cikti)
    kirpilmis_yaz(tarih_str, cikti)
    return hedef_dosya


if __name__ == "__main__":
    ayristirici = argparse.ArgumentParser()
    ayristirici.add_argument("tarih", help="YYYY-MM-DD")
    ayristirici.add_argument("--force", action="store_true")
    args = ayristirici.parse_args()

    try:
        datetime.strptime(args.tarih, "%Y-%m-%d")
    except ValueError:
        sys.exit(f"Geçersiz tarih: {args.tarih} (YYYY-MM-DD bekleniyor)")

    cek(args.tarih, zorla=args.force)
