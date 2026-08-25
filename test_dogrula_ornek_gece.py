"""
Tek seferlik test betiği — dogrula.py'nin kabul testi.

dil kılavuzundaki (overnight-dil-kilavuzu-ve-ornek-gece.md) elle
doğrulanmış örnek gece metnini taslak biçimine çevirip dogrula.py'den
geçirir. yaz.py henüz yazılmadığı için bu taslak elle transkribe edildi.

Kullanım: python3 test_dogrula_ornek_gece.py
"""

import json

from dogrula import gece_dogrula

TARIH = "2026-01-02"

GID = {
    "CHA-MIL": "0022500481",
    "DEN-CLE": "0022500478",
    "MEM-LAL": "0022500485",
    "ORL-CHI": "0022500480",
    "SAC-PHX": "0022500483",
    "POR-NOP": "0022500482",
    "ATL-NYK": "0022500479",
    "OKC-GSW": "0022500484",
    "SAS-IND": "0022500476",
    "BKN-WAS": "0022500477",
}

TASLAK = {
    "maclar": {
        GID["CHA-MIL"]: {
            "baslik": "Milwaukee 16 sayı geriden döndü, maçı 1 sayıyla bitirdi.",
            "neden_onemli": "Gecenin tek çekişmeli maçıydı; Giannis 30-10 yaptı.",
            "ozet": (
                "Charlotte ilk çeyreği 38-24 önde kapattı; fark ikinci çeyreğin başında "
                "16'ya kadar çıktı. Hornets o çeyrekte 22 sayıda kalınca fark 9'a indi. "
                "Üçüncü çeyreğe kadar önde giden Hornets son 12 dakikayı 35-30 kaybetti "
                "ve maçı 1 sayı farkla verdi. Giannis Antetokounmpo 30 sayı 10 ribaundla "
                "bitirdi; Milwaukee 15-20'ye yükseldi, Charlotte 11-23'te kaldı."
            ),
            "muzip": False,
        },
        GID["DEN-CLE"]: {
            "ozet": (
                "Denver üçüncü çeyrekte 38 sayı attı ve 9 öne geçti. Son bölümde vitesi "
                "artıran Cleveland maçı çevirdi; Denver son çeyrekte 11 sayıda kaldı. "
                "Jamal Murray 34 attı, yetmedi."
            ),
            "muzip": False,
        },
        GID["MEM-LAL"]: {
            "ozet": (
                "Üçüncü çeyrek 96-96 bitti. Lakers son 12 dakikayı 32-25 alıp kazandı, "
                "Dončić 34 attı. Batı'da beşinci sıra korundu: 21-11."
            ),
            "muzip": False,
        },
        GID["ORL-CHI"]: {
            "ozet": (
                "Orlando son çeyreğe 4 sayı önde girdi ama o çeyrekte 19 sayıda kaldı; "
                "Chicago 30 atıp maçı aldı. Banchero'nun 31 sayısı yetmedi. Chicago tam "
                "ortada duruyor: 17-17."
            ),
            "muzip": False,
        },
        GID["SAC-PHX"]: {
            "ozet": (
                "Baştan sona Phoenix kontrolünde geçti. Booker 33 attı. Sacramento 8-27 "
                "ile Batı'nın dibinde."
            ),
            "muzip": True,
        },
        GID["POR-NOP"]: {
            "ozet": (
                "New Orleans maça \"bu kez olacak gibi\" başladı — ilk çeyrek 37 sayı — "
                "ama sonraki iki çeyrekte toplam 38 bulabildi. Gecenin en iyi bireysel "
                "performansı buradan çıktı: Deni Avdija 34 sayı, 11 asist, 7 ribaundla "
                "oynadı ve Portland'ı taşıdı. Zion'un 35 sayısı yetmedi; New Orleans 8-28."
            ),
            "muzip": True,
        },
        GID["ATL-NYK"]: {
            "ozet": (
                "Atlanta üç çeyrekte New York'a 24 fark attı. New York son çeyrekte 29 "
                "sayı atıp farkı 12'ye indirdi ama iş işten geçmişti. Brunson 24 attı, "
                "Hukporti 16 ribaund aldı."
            ),
            "muzip": False,
        },
        GID["OKC-GSW"]: {
            "ozet": (
                "Maçın kırılma anı hava atışı oldu. Gilgeous-Alexander 28 dakikada 30 "
                "attı, Holmgren 15 sayı 15 ribaund 4 blok yaptı. OKC 30-5."
            ),
            "muzip": True,
        },
        GID["SAS-IND"]: {
            "ozet": (
                "Spurs favori olduğu maçı ikinci çeyrekte attığı 41 sayıyla kopardı; "
                "Indiana üçüncü çeyrekte bir kez yaklaştı ama son çeyrekte fark kalıcı "
                "olarak açıldı. Indiana ligin en kötü derecesiyle tanking'e devam "
                "ediyor: 6-29."
            ),
            "muzip": False,
        },
        GID["BKN-WAS"]: {
            "ozet": (
                "İddiasız maçta Wizards rahat kazandı. Maçın en skoreri Champagnie'nin "
                "attığı 20 sayı, gecenin on maçındaki en düşük \"en skorer\" performansı "
                "oldu."
            ),
            "muzip": False,
        },
    },
    "brief": [
        {"metin": "Milwaukee 16 sayılık farkı kapattı, maçı 1 sayıyla aldı.", "hedef_mac": GID["CHA-MIL"], "muzip": False},
        {"metin": "Cleveland son çeyreği 25-11 alarak Denver'ı devirdi.", "hedef_mac": GID["DEN-CLE"], "muzip": False},
        {"metin": "Oklahoma City sezonun 30. galibiyetini aldı; Golden State eksikti.", "hedef_mac": GID["OKC-GSW"], "muzip": False},
        {"metin": "Lakers üçüncü çeyrek sonunda berabereydi, son 12 dakikayı aldı.", "hedef_mac": GID["MEM-LAL"], "muzip": False},
        {"metin": "Indiana 29. yenilgisini aldı: 6-29.", "hedef_mac": GID["SAS-IND"], "muzip": False},
    ],
}


def main():
    gercek_gece = json.loads(open(f"gercek/{TARIH}.json").read())
    import os as _os
    _tam = _os.path.join("ham", f"{TARIH}.json")
    _yol = _tam if _os.path.exists(_tam) else _os.path.join("test_verisi", "ham", f"{TARIH}.json")
    ham = json.loads(open(_yol).read())
    skor_gece = json.loads(open(f"skor/{TARIH}.json").read())

    sonuc = gece_dogrula(TASLAK, gercek_gece, ham, skor_gece)

    print("=== MAÇLAR ===")
    isim_ters = {v: k for k, v in GID.items()}
    for gid, mac_sonuc in sonuc["maclar"].items():
        durum = "KABUL" if mac_sonuc["kabul"] else "RET"
        print(f"{isim_ters[gid]:10s} {durum}")
        if not mac_sonuc["kabul"]:
            for g in mac_sonuc["gerekce"]:
                print(f"    - {g}")

    print()
    print("=== BRIEF ===")
    for i, b in enumerate(sonuc["brief"]):
        durum = "KABUL" if b["kabul"] else "RET"
        print(f"[{i}] {durum}")
        if not b["kabul"]:
            for g in b["gerekce"]:
                print(f"    - {g}")

    print()
    print("=== T7 (muziplik) ===", sonuc["t7"])
    print()
    print("GECE GENELİ:", "KABUL" if sonuc["kabul"] else "RET")


if __name__ == "__main__":
    main()
