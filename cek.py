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


def sezon_kodu(tarih: datetime) -> str:
    """2026-01-02 -> '2025-26'. NBA sezonu ekimde başlar."""
    if tarih.month >= 10:
        baslangic_yili = tarih.year
    else:
        baslangic_yili = tarih.year - 1
    return f"{baslangic_yili}-{str(baslangic_yili + 1)[2:]}"


def gece_mac_idlerini_al(tarih_str: str) -> list[str]:
    sb = scoreboardv2.ScoreboardV2(game_date=tarih_str)
    ham = sb.get_dict()
    satirlar = ham["resultSets"][0]["rowSet"]
    basliklar = ham["resultSets"][0]["headers"]
    id_index = basliklar.index("GAME_ID")
    return ham, [satir[id_index] for satir in satirlar]


def mac_verisi_cek(game_id: str) -> dict:
    veri = {}

    veri["box_traditional"] = boxscoretraditionalv3.BoxScoreTraditionalV3(
        game_id=game_id
    ).get_dict()
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    veri["box_advanced"] = boxscoreadvancedv3.BoxScoreAdvancedV3(
        game_id=game_id
    ).get_dict()
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    veri["box_summary"] = boxscoresummaryv2.BoxScoreSummaryV2(
        game_id=game_id
    ).get_dict()
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    veri["play_by_play"] = playbyplayv3.PlayByPlayV3(game_id=game_id).get_dict()
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
    ham = leaguegamelog.LeagueGameLog(
        season=sezon, date_from_nullable=ertesi_gun
    ).get_dict()
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


def cek(tarih_str: str, zorla: bool = False) -> Path:
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

    puan_durumu = leaguegamelog.LeagueGameLog(
        season=sezon, date_to_nullable=tarih_str
    ).get_dict()
    time.sleep(ISTEK_ARASI_BEKLEME_SN)

    oyuncu_ortalama = playergamelogs.PlayerGameLogs(
        season_nullable=sezon, date_to_nullable=onceki_gun
    ).get_dict()
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
