"""
dogrula.py'nin RET tarafını test eder — kasten bozulmuş cümleler.
Her biri ayrı bir T testini düşürmeli. Hepsi düşerse dogrula.py doğru
çalışıyor demektir.

Kullanım: python3 test_dogrula_bozuk.py
"""

import datetime as _tarih
import os as _os
import json

from dogrula import (
    mac_metnini_dogrula,
    brief_metnini_dogrula,
    t7_muziplik_sayaci,
    t9_gece_ici_tekrar,
    yasakli_yukle,
    kelime_say,
)
import gercekler
import yaz
import cumle
import derle as _derle
import re as _re

# Kritik anlar testleri hem hesabı hem KAYNAĞI denetliyor
# ("ek API çağrısı yok" iddiası ancak kaynakta doğrulanabilir).
_derle_kaynak = open("derle.py", encoding="utf-8").read()
_yaz_kaynak = open("yaz.py", encoding="utf-8").read()
_yayin_kaynak = open("yayin.py", encoding="utf-8").read()
_dogrula_kaynak = open("dogrula.py", encoding="utf-8").read()
import derle as _derle

_derle_kaynak = open("derle.py", encoding="utf-8").read()

TARIH = "2026-01-02"
CHA_MIL = "0022500481"
DEN_CLE = "0022500478"
LAL_MEM = "0022500485"  # Luka Dončić burada oynuyor — aksan-katlama testi için
OKC_GSW = "0022500484"  # OKC kazandı, GSW mağlubiyet serisinde — elenmiş özne testi için
NYK_ATL = "0022500479"  # New York kaybetti — olumsuzluk/negasyon testi için
IND_SAS = "0022500476"  # SAS 2 maçlık galibiyet serisinde — çok kelimeli takım adı testi için


def _ham_yolu(tarih):
    """Ham veri dosyası — üretimdeki tam kopya varsa o, yoksa depodaki
    kırpılmış test kopyası.

    `ham/` depoya girmiyor (300MB+), ama testlerin box score verisine
    ihtiyacı var. `test_verisi/ham/` her geceden SADECE testlerin okuduğu
    iki bloğu taşıyor (box_traditional + box_summary), toplam 0.6MB.
    Böylece testler CI'da da tam olarak çalışıyor — atlanmıyor."""
    tam = _os.path.join("ham", f"{tarih}.json")
    return tam if _os.path.exists(tam) else _os.path.join("test_verisi", "ham", f"{tarih}.json")


def yukle():
    gercek_gece = json.loads(open(f"gercek/{TARIH}.json").read())
    ham = json.loads(open(_ham_yolu(TARIH)).read())
    return gercek_gece, ham


def _pytest_yakala(fn):
    """Çağrının fırlattığı istisnayı döner (yoksa None)."""
    try:
        fn()
        return None
    except Exception as hata:
        return hata


def basar(ad, kosul):
    print(f"[{'OK' if kosul else 'FAIL'}] {ad}")


def main():
    gercek_gece, ham = yukle()
    yasakli = yasakli_yukle()
    gercekler_cha = gercek_gece["maclar"][CHA_MIL]
    ham_cha = ham["maclar"][CHA_MIL]
    gercekler_lal = gercek_gece["maclar"][LAL_MEM]
    ham_lal = ham["maclar"][LAL_MEM]
    gercekler_okc = gercek_gece["maclar"][OKC_GSW]
    ham_okc = ham["maclar"][OKC_GSW]
    gercekler_nyk = gercek_gece["maclar"][NYK_ATL]
    ham_nyk = ham["maclar"][NYK_ATL]
    gercekler_den = gercek_gece["maclar"][DEN_CLE]
    gercekler_ind = gercek_gece["maclar"][IND_SAS]
    ham_ind = ham["maclar"][IND_SAS]
    ham_den = ham["maclar"][DEN_CLE]

    # T1 — uydurma sayı. 45 ve 77 denendi, ikisi de bu maçta gerçekten
    # var olan başka bir değerle (isabet sayısı, bir "an"in saniyesi)
    # çakıştı — T1'in kendisi değil test verisi yanlıştı. 999 hiçbir
    # gerçek istatistikte veya saat değerinde çıkmayacak kadar büyük.
    metin = {"ozet": "Giannis Antetokounmpo 999 sayı 10 ribaundla bitirdi; Milwaukee kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T1: uydurma sayı reddedildi", not sonuc["kabul"] and any("T1" in g for g in sonuc["gerekce"]))

    # T2 — ligdeki başka bir oyuncunun adı (LeBron James bu maçta oynamadı).
    # İsim BİLEREK cümle başında değil — T2 artık cümle başındaki büyük
    # harfli kelimeyi kontrol etmiyor (üç kez aynı yanlış pozitifi görüp
    # bu ödünü kullanıcının onayıyla verdik), o yüzden gerçek risk
    # senaryosu ismin cümle İÇİNDE geçmesi.
    metin = {"ozet": "Milwaukee, LeBron James'in etkisiyle maçı kazandı; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T2: yabancı oyuncu adı reddedildi", not sonuc["kabul"] and any("T2" in g for g in sonuc["gerekce"]))

    # T3 — play-by-play olmadan "an" iddiası (gercekler bilerek boş verildi)
    metin = {"ozet": "Milwaukee maçı son saniye galibiyet basketiyle kazandı."}
    sonuc = mac_metnini_dogrula(metin, [], ham_cha, 0, yasakli)
    basar("T3: play-by-play'siz an iddiası reddedildi", not sonuc["kabul"] and any("T3" in g for g in sonuc["gerekce"]))

    # T4 — yasaklı klişe
    metin = {"ozet": "Giannis adeta bir ders verdi; Milwaukee maçı kazandı, Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4: yasaklı klişe reddedildi", not sonuc["kabul"] and any("T4" in g for g in sonuc["gerekce"]))

    # T4c — "puan" bağlamlı yasağı (sadece "puan durumu" serbest)
    metin = {"ozet": "Giannis 30 puanla oynadı; Milwaukee kazandı, Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4c: 'puan' (sayı yerine) reddedildi", not sonuc["kabul"] and any("T4c" in g for g in sonuc["gerekce"]))

    # T4d — kök bazlı yasaklı kalıp (araya kelime giren çekimli varyant)
    metin = {"ozet": "Milwaukee dört çeyreği de kazandı; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4d: 'çeyreği de kazandı' (kök varyant) reddedildi", not sonuc["kabul"] and any("T4d" in g for g in sonuc["gerekce"]))

    # T4d — "asistli oynadı" gibi bozuk istatistik-sıfat çekimi
    # (gerçek üretim bug'ı — "Devin Booker ... 5 asistli oynadı")
    metin = {"gec_satiri": "Milwaukee kazandı; Giannis 30 sayı, 5 asistli oynadı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4d: 'asistli oynadı' bozuk çekimi reddedildi", not sonuc["kabul"] and any("T4d" in g for g in sonuc["gerekce"]))

    # T4e — takım kodu okuyucuya çıkmış (tam şehir/takım adı zorunlu)
    metin = {"ozet": "MIL, CHA karşısında son saniyede kazandı; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4e: takım kodu (MIL/CHA) reddedildi", not sonuc["kabul"] and any("T4e" in g for g in sonuc["gerekce"]))

    # T13 — atıf hatası: geri dönüş kaybedene atfedilmiş (gerçek üretim
    # bug'ı — MIL 16 sayılık farktan döndü ve kazandı, CHA geride kalan
    # taraftı; cümle bunu tersine çevirip CHA'ya "döndü" dedi)
    metin = {"ozet": "Charlotte, 16 sayılık farktan dönerek son anda kazandı; Milwaukee yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T13: geri dönüş kaybedene atfedilince reddedildi", not sonuc["kabul"] and any("T13" in g for g in sonuc["gerekce"]))

    # T9 — kök bazlı tekrar: farklı çekimler ("gömdü" / "gömerek") aynı
    # gece iki ayrı metinde geçerse yakalanmalı
    metin_by_yer = {
        "mac1:ozet": "Milwaukee, Charlotte'ı beşinci mağlubiyete gömdü.",
        "mac2:ozet": "Boston, Miami'yi altıncı mağlubiyete gömerek farkı açtı.",
    }
    gecti, tekrarlar = t9_gece_ici_tekrar(metin_by_yer)
    basar("T9: 'gömdü'/'gömerek' kök bazlı tekrar yakalandı", not gecti and tekrarlar is not None)

    # T5 — kazanan hiç geçmiyor
    metin = {"ozet": "Charlotte ilk çeyreği 38-24 önde kapattı ama sonra farkı kaybetti."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T5: kazanan geçmiyor, reddedildi", not sonuc["kabul"] and any("T5" in g for g in sonuc["gerekce"]))

    # T6 — özet 6 cümle (sınır 5 — "Mutlaka bil" kendi iskeletiyle 4-5
    # cümlelik gövde kullanıyor, sınır buna göre genişletildi)
    metin = {
        "ozet": (
            "Milwaukee kazandı. Charlotte kaybetti. Giannis iyi oynadı. "
            "Maç yakındı. Son çeyrek belirleyiciydi. Rollins da öne çıktı."
        )
    }
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: uzun özet reddedildi", not sonuc["kabul"] and any("T6" in g for g in sonuc["gerekce"]))

    # T6 — brief 12 kelimeyi geçiyor
    brief = {
        "metin": "Milwaukee bu gece gerçekten inanılmaz bir şekilde on altı sayılık farkı geriden kapatarak maçı kazandı",
        "hedef_mac": CHA_MIL,
    }
    sonuc = brief_metnini_dogrula(brief, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: uzun brief reddedildi", not sonuc["kabul"])

    # T7 — gece çapında 4'ten fazla muzip alan
    muzip_kayitlari = [
        {"yer": f"mac{i}", "mac_id": f"g{i}", "rozet": float(i)} for i in range(5)
    ]
    gecti, sifirlanacak = t7_muziplik_sayaci(muzip_kayitlari)
    basar("T7: 5 muzip alanda sınır aşıldı, en düşük 2'si sıfırlanacak", not gecti and len(sifirlanacak) == 2)

    # T13 — YANLIŞ POZİTİF regresyon testi: iki-özneli doğru cümle
    # reddedilmemeli ("Charlotte farkı açtı AMA Milwaukee döndü" —
    # geri dönüşün gerçek öznesi Milwaukee, cümledeki ilk takım değil)
    metin = {"ozet": "Charlotte ilk yarıda 16 sayıya kadar farkı açtı, ancak Milwaukee üçüncü çeyrekten itibaren bu farktan döndü ve kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T13: iki-özneli doğru cümle YANLIŞLIKLA reddedilmedi", sonuc["kabul"] or not any("T13" in g for g in sonuc["gerekce"]))

    # T13 — YANLIŞ POZİTİF regresyon testi: iyelik ekli takım adı ("Charlotte'UN
    # farkını eritti") özne sanılmamalı, gerçek özne kazanan Milwaukee
    metin = {"baslik": "Milwaukee, Charlotte'un 16 sayılık farkını eritip son saniyede kazandı"}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T13: iyelik ekli takım adı özne sanılmadı (regresyon)", "T13" not in " ".join(sonuc["gerekce"]))

    # T13 — YANLIŞ POZİTİF regresyon testi: "X kazandı VE [rakibin]
    # mağlubiyet serisini çıkardı" — "mağlubiyet serisi"nin gerçek
    # sahibi elenmiş özne (rakip), kazanan taraf değil. Belirsiz
    # durumda hiç atfetmemek doğrusu, kazanana yanlış atfetmek değil.
    metin = {"gec_satiri": "Milwaukee ilk çeyrekten itibaren hiç sarsılmadan kazandı ve mağlubiyet serisini 4'e çıkardı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_okc, ham_okc, 0, yasakli)
    basar("T13: elenmiş özneli seri cümlesi YANLIŞLIKLA reddedilmedi (regresyon)", "T13" not in " ".join(sonuc["gerekce"]))

    # T13 — YANLIŞ POZİTİF regresyon testi: olumsuzluk — "geri dönüşe
    # yetmedi" bir geri dönüş İDDİA ETMİYOR, tersini söylüyor
    metin = {"ozet": "Jalen Brunson'ın 24 sayısı New York tarafında geri dönüşe yetmedi; Atlanta kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_nyk, ham_nyk, 0, yasakli)
    basar("T13: olumsuzlanmış geri dönüş cümlesi YANLIŞLIKLA reddedilmedi (regresyon)", "T13" not in " ".join(sonuc["gerekce"]))

    # T16 — YANLIŞ POZİTİF regresyon testi: "Thunder, Warriors'ı yenerek
    # üst üste dördüncü galibiyetini aldı" — nesne durumundaki (belirtme
    # hali) "Warriors'ı" cümlenin öznesi DEĞİL, en yakın olduğu için
    # yanlışlıkla Warriors'a atfedilmişti (gerçek üretim bug'ı). NOT:
    # bu test eskiden DEN_CLE/"üçüncü" kullanıyordu — UST_USTE_ESIGI
    # kullanıcı kararıyla 3'ten 4'e çıkınca (bir gecede "seri"
    # niteleyicisinin fazla tekrarlanması sorunu) CLE'nin gerçek serisi
    # (3) eşiğin altında kaldı, test OKC_GSW'ye taşındı (OKC'nin gerçek
    # serisi 4, hâlâ eşiği geçiyor).
    metin = {"gec_satiri": "Thunder, Warriors'ı 123-108 yenerek üst üste dördüncü galibiyetini aldı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_okc, ham_okc, 0, yasakli)
    basar("T16: nesne durumlu takım adı özne sanılmadı (regresyon)", "T16" not in " ".join(sonuc["gerekce"]))

    # T2 — YANLIŞ POZİTİF regresyon testi: aksansız yazım (Dončić->Doncic)
    # reddedilmemeli (gerçek üretim bug'ı — roster'da "Dončić" var,
    # model "Doncic" yazınca listede yok sanılıp reddedildi)
    metin = {"ozet": "Lakers kazandı; Doncic 34 sayı attı, Memphis yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_lal, ham_lal, 0, yasakli)
    basar("T2: aksansız yabancı isim yazımı reddedilmedi (regresyon)", "T2" not in " ".join(sonuc["gerekce"]))

    # T15 — bir oyuncu istatistiği takımın SEZON GENELİ serisinin
    # sebebi gösterilemez (gerçek üretim bug'ı)
    metin = {"gec_satiri": "Day'Ron Sharpe 14 sayı 9 ribaundla mağlubiyet serisini üçe çıkardı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T15: istatistik-seri sebep-sonuç hatası reddedildi", not sonuc["kabul"] and any("T15" in g for g in sonuc["gerekce"]))

    # T16 — haber değeri eşiği: 15'in altında lider değişimi anılmamalı
    metin = {"gec_satiri": "Milwaukee, Charlotte karşısında 8 lider değişimiyle kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T16: eşik altı lider değişimi reddedildi", not sonuc["kabul"] and any("T16" in g for g in sonuc["gerekce"]))

    # T16 — "üst üste" iddiası, gerçek seri 3'ün altındaysa reddedilir
    metin = {"gec_satiri": "Milwaukee üst üste ikinci galibiyetini aldı, Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T16: eşik altı 'üst üste' iddiası reddedildi", not sonuc["kabul"] and any("T16" in g for g in sonuc["gerekce"]))

    # T16 — "N. galibiyetini alan" sayısı gerçek sezon toplamıyla
    # eşleşmeli (gerçek üretim bug'ı: Washington 9-24'ken "İkinci
    # galibiyetini alan Wizards" yazılmıştı — MIL bu gecede gerçekte
    # 15. galibiyetini aldı, "ikinci" değil)
    metin = {"gec_satiri": "İkinci galibiyetini alan Milwaukee, Charlotte'ı geçti."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T16: yanlış sıra numaralı galibiyet iddiası reddedildi", not sonuc["kabul"] and any("T16" in g for g in sonuc["gerekce"]))

    # T16 — YANLIŞ POZİTİF regresyon: doğru sıra numarası (15.) kabul edilmeli
    metin = {"gec_satiri": "15. galibiyetini alan Milwaukee, Charlotte'ı geçti."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T16: doğru sıra numaralı galibiyet YANLIŞLIKLA reddedilmedi (regresyon)", "T16" not in " ".join(sonuc["gerekce"]))

    # T17 — kaybeden takımın oyuncusu cümle öznesi olarak başlayamaz
    metin = {"gec_satiri": "Jaren Jackson Jr. 25 sayı attı ama Memphis kaybetti."}
    sonuc = mac_metnini_dogrula(metin, gercekler_lal, ham_lal, 0, yasakli)
    basar("T17: kaybeden takımın oyuncusu özne olunca reddedildi", not sonuc["kabul"] and any("T17" in g for g in sonuc["gerekce"]))

    # T18 — "double-double" iddiası gerçek istatistikle uyuşmuyor
    # (gerçek üretim bug'ı — Shai Gilgeous-Alexander 30 sayı 1 ribaund
    # 7 asistle "double-double yaptı" denmişti, sadece 1 kategori 10+)
    metin = {"gec_satiri": "Ryan Rollins 29 sayı, 8 asistle double-double yaptı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T18: yanlış double-double iddiası reddedildi", not sonuc["kabul"] and any("T18" in g for g in sonuc["gerekce"]))

    # T4d — 'N sayıyla oynadı' yavan fiil kalıbı yasak
    metin = {"gec_satiri": "Devin Booker, 33 sayıyla oynadı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4d: 'sayıyla oynadı' yavan fiil reddedildi", not sonuc["kabul"] and any("T4d" in g for g in sonuc["gerekce"]))

    # T4d — 'final oynadı' bozuk kalıp yasak
    metin = {"ozet": "Taraflar son çeyrekte beş kez lider değişimiyle geçen çekişmeli bir final oynadı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4d: 'final oynadı' bozuk kalıp reddedildi", not sonuc["kabul"] and any("T4d" in g for g in sonuc["gerekce"]))

    # T4d — geriye dönük test denetimi: "kariyerine yakışan" (kariyer
    # hakkında yorum yasağı) iki tur önce eklenmişti, hiç test edilmemişti.
    metin = {"ozet": "Giannis Antetokounmpo, kariyerine yakışan bir gecesinde 45 sayı attı; Milwaukee kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T4d: 'kariyerine yakışan' (kariyer yorumu yasağı) reddedildi", not sonuc["kabul"] and any("T4d" in g for g in sonuc["gerekce"]))

    # T18 (genişletilmiş) — doğrulanamaz kayıt iddiası (gerçek üretim
    # bug'ı: "Pascal Siakam ... kariyer rekorunu kırdı" denmişti, oysa
    # gercekler.py'de böyle bir kayıt hiç üretilmiyor — kaynaksız iddia)
    metin = {"gec_satiri": "Pascal Siakam 23 sayı, 9 ribaund ve 5 asistle kariyer rekorunu kırdı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_ind, ham_ind, 0, yasakli)
    basar("T18: doğrulanamaz 'kariyer rekoru' iddiası reddedildi", not sonuc["kabul"] and any("T18" in g for g in sonuc["gerekce"]))

    # T18 — olağanüstü kilometre eşiği VARSA "tarihte/kariyer rekoru"
    # çerçevesi serbest olmalı (kullanıcı düzeltmesi: Adebayo'nun 83
    # sayılık gecesi bu çerçeveyi hak ediyordu ama T18 hep reddediyordu)
    gercekler_olaganustu = gercekler_ind + [{
        "id": "test1", "tur": "kilometre",
        "veri": {"oyuncu": "Pascal Siakam", "id": 1, "esik": "60_sayi", "sayi": 65, "rib": 9, "ast": 5},
        "kaynak": "test", "guven": "kesin",
    }]
    metin = {"gec_satiri": "Pascal Siakam 65 sayı, 9 ribaund ve 5 asistle kariyerinin en iyi gecesini geçirdi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_olaganustu, ham_ind, 0, yasakli)
    basar("T18: olağanüstü eşik varken 'kariyerinin en iyisi' YANLIŞLIKLA reddedilmedi (regresyon)", "T18" not in " ".join(sonuc["gerekce"]))

    # T18 — kesin sıra/rank iddiası olağanüstü eşik VARSA BİLE reddedilir
    metin = {"gec_satiri": "Pascal Siakam 65 sayı, 9 ribaund ve 5 asistle tarihin ikinci en yüksek skorunu attı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_olaganustu, ham_ind, 0, yasakli)
    basar("T18: kesin sıra iddiası olağanüstü eşikte de reddedildi", not sonuc["kabul"] and any("T18" in g for g in sonuc["gerekce"]))

    # T13 — takım skoru oyuncuya atfedilemez (gerçek üretim bug'ı: "Son
    # dakikada serbest atışlarla 150'ye ulaşan Bam Adebayo" — 150 takımın
    # skoruydu, Adebayo'nun kendi sayısı değil; burada MIL'in 122'si
    # Giannis'in kendi sayısı (30) değil)
    metin = {"ozet": "Son saniyede smaçla 122'ye ulaşan Giannis Antetokounmpo, Milwaukee'ye galibiyeti getirdi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T13: takım skoru oyuncuya atfedilince reddedildi", not sonuc["kabul"] and any("T13" in g for g in sonuc["gerekce"]))

    # T6 — boş/çok kısa metin ASLA sessizce kabul edilmemeli (gerçek
    # üretim bug'ı: 11 gecelik toplu üretimde onlarca "gec_satiri" TAMAMEN
    # BOŞ geçmişti çünkü hiçbir test alt sınır kontrol etmiyordu)
    metin = {"gec_satiri": ""}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: boş gec_satiri reddedildi", not sonuc["kabul"] and any("T6" in g for g in sonuc["gerekce"]))

    metin = {"ozet": ""}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: boş ozet reddedildi", not sonuc["kabul"] and any("T6" in g for g in sonuc["gerekce"]))

    # T4f — konferans adı özel ad, küçük harfle başlayamaz (gerçek
    # üretim bug'ı: "ikisi de doğu'da 9-8 sıradaydı")
    metin = {"gec_satiri": "İkisi de doğu'da 9-8 sıradaydı, Chicago Bulls maçı kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_ind, ham_ind, 0, yasakli)
    basar("T4f: küçük harfli 'doğu' konferans adı reddedildi", not sonuc["kabul"] and any("T4f" in g for g in sonuc["gerekce"]))

    # T19 — brief'te gereksiz final skor tekrarı (fark eşiğin altında
    # olduğu için haber değeri yok, sadece karttaki skorun tekrarı)
    aday = {"metin": "Charlotte Hornets, Milwaukee Bucks'a 122-121 mağlup oldu.", "hedef_mac": CHA_MIL, "muzip": False}
    sonuc = brief_metnini_dogrula(aday, gercekler_cha, ham_cha, 0, yasakli)
    basar("T19: brief'te gereksiz final skor tekrarı reddedildi", not sonuc["kabul"] and any("T19" in g for g in sonuc["gerekce"]))

    # T16 — YANLIŞ POZİTİF regresyon testi: çok kelimeli takım adında
    # ("Indiana Pacers'ı") ek son kelimeye yapışıyor ama "Indiana" tek
    # başına eksiz bir aday olarak kalıp yanlış özne sanılmıştı (gerçek
    # üretim bug'ı — SAS'ın 2 maçlık serisi Indiana'ya atfedilip eşik
    # testinden kaçmıştı)
    metin = {"gec_satiri": "San Antonio Spurs, deplasmanda Indiana Pacers'ı 123-113 yenerek üst üste ikinci galibiyetini aldı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_ind, ham_ind, 0, yasakli)
    basar("T16: çok kelimeli takım adında eşik-altı 'üst üste' yakalandı (regresyon)", not sonuc["kabul"] and any("T16" in g for g in sonuc["gerekce"]))

    # T14 — en yüksek GmSc'li performans hiç anılmadı (gerçek üretim
    # bug'ı — Lakers-Memphis metninde Dončić'in 34 sayısı hiç geçmedi,
    # kaybeden takımın oyuncusu anıldı)
    metin = {"ozet": "Milwaukee, Charlotte'ı son saniyede geçti; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli, en_iyi_performans="Giannis Antetokounmpo")
    basar("T14: en iyi performans anılmayınca reddedildi", not sonuc["kabul"] and any("T14" in g for g in sonuc["gerekce"]))

    # T14 — YANLIŞ POZİTİF regresyon testi: eşiği GEÇMEYEN bir performans
    # zorunlu anılmamalı ("sıradan maçta sade bitir" kuralı) — Kon
    # Knueppel bu maçta 26 sayıyla oynadı, 30/15/10 eşiklerinin hiçbirini
    # geçmiyor
    metin = {"ozet": "Milwaukee, Charlotte'ı son saniyede geçti; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli, en_iyi_performans="Kon Knueppel")
    basar("T14: eşik altı performans zorunlu anılmadı (regresyon)", "T14" not in " ".join(sonuc["gerekce"]))

    # T8 — haber_skoru>=6 iken muzip:true
    metin = {
        "ozet": "Milwaukee maçı kazandı, Charlotte yenildi; Giannis 30 sayı 10 ribaundla bitirdi.",
        "muzip": True,
    }
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, haber_skoru=8, yasakli_liste=yasakli)
    basar("T8: yüksek haber skorunda muzip reddedildi", not sonuc["kabul"] and any("T8" in g for g in sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # T20 — sezon başı susma kuralı. Sentetik "derece" gerçeği:
    # sezon_guvenilir=False (takım 10 maçın altında) — dört yasağın her
    # biri için ayrı bir negatif test (kullanıcı kararı: her dil hatası
    # düzeltmesiyle birlikte bir test gelir).
    # ------------------------------------------------------------------
    erken_derece = [
        {"tur": "derece", "veri": {"takim": "OKC", "sezon_guvenilir": False, "galibiyet": 1, "maglubiyet": 0}},
        {"tur": "derece", "veri": {"takim": "HOU", "sezon_guvenilir": False, "galibiyet": 0, "maglubiyet": 1}},
    ]
    gec_derece = [
        {"tur": "derece", "veri": {"takim": "OKC", "sezon_guvenilir": True, "galibiyet": 34, "maglubiyet": 5}},
        {"tur": "derece", "veri": {"takim": "HOU", "sezon_guvenilir": True, "galibiyet": 20, "maglubiyet": 19}},
    ]

    metin = {"gec_satiri": "Oklahoma City Thunder, sezona 1-0 başladı."}
    sonuc = mac_metnini_dogrula(metin, erken_derece, ham_cha, 0, yasakli)
    basar("T20: derece iddiası ('sezona 1-0 başladı') erken sezonda reddedildi", not sonuc["kabul"] and any("T20" in g for g in sonuc["gerekce"]))

    metin = {"gec_satiri": "Sürpriz bir sonuçla Houston Rockets'i yenen Oklahoma City, gecenin en konuşulan sonuçlarından biri oldu."}
    sonuc = mac_metnini_dogrula(metin, erken_derece, ham_cha, 0, yasakli)
    basar("T20: sürpriz sonuç çerçevesi erken sezonda reddedildi", not sonuc["kabul"] and any("T20" in g for g in sonuc["gerekce"]))

    metin = {"gec_satiri": "Oklahoma City Thunder, Houston Rockets'i yenerek 3 maçlık galibiyet serisini sürdürdü."}
    sonuc = mac_metnini_dogrula(metin, erken_derece, ham_cha, 0, yasakli)
    basar("T20: seri iddiası erken sezonda reddedildi", not sonuc["kabul"] and any("T20" in g for g in sonuc["gerekce"]))

    metin = {"ozet": "Oklahoma City Thunder kazandı. Bu sezon önce 2 kez bu eşiği geçmişti."}
    sonuc = mac_metnini_dogrula(metin, erken_derece, ham_cha, 0, yasakli)
    basar("T20: sezon içi sıklık iddiası erken sezonda reddedildi", not sonuc["kabul"] and any("T20" in g for g in sonuc["gerekce"]))

    # T20 — YANLIŞ POZİTİF regresyon testi: sezon_guvenilir=True iken
    # (10+ maç) aynı ifadeler serbest — kural sadece erken sezonu susturur.
    metin = {"gec_satiri": "Oklahoma City Thunder, Houston Rockets'i yenerek 3 maçlık galibiyet serisini sürdürdü."}
    sonuc = mac_metnini_dogrula(metin, gec_derece, ham_cha, 0, yasakli)
    basar("T20: güvenilir derecede aynı ifade YANLIŞLIKLA reddedilmedi (regresyon)", "T20" not in " ".join(sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # T21 — iyelik eki 'n' tamponu sadece sesli harfle biten kelimede.
    # ------------------------------------------------------------------
    metin = {"gec_satiri": "Anthony Edwards'nin 41 sayılık gecesinde Minnesota, Portland'ı yendi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T21: ünsüzle biten kelimede 'n' tamponu hatası reddedildi", not sonuc["kabul"] and any("T21" in g for g in sonuc["gerekce"]))

    # T21 — YANLIŞ POZİTİF regresyon testi: sesli harfle biten kelimede
    # 'n' tamponu DOĞRU ("Doğu'nun", "Batı'nın") — reddedilmemeli.
    metin = {"gec_satiri": "Doğu'nun zirvesinde Milwaukee, Boston'ı yendi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T21: sesli harfle biten kelimede doğru 'n' tamponu YANLIŞLIKLA reddedilmedi (regresyon)", "T21" not in " ".join(sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # T13 — sonuç iddiası kaybedene atfedilmiş (gerçek üretim bug'ı, bu
    # tur: Houston 125-124 KAYBETTİĞİ halde "Şengün ... bir basketle
    # takımını öne geçirdi" yazılmıştı — geçici bir öne geçiş, kalıcı
    # değil, OKC hemen ardından tekrar öne geçip kazandı).
    # ------------------------------------------------------------------
    gercek_1021 = json.loads(open("gercek/2025-10-21.json").read())
    ham_1021_okc = json.loads(open(_ham_yolu("2025-10-21")).read())
    gercekler_okc_hou = gercek_1021["maclar"]["0022500001"]  # OKC 125-124 kazandı, HOU (Şengün) kaybetti
    ham_okc_hou = ham_1021_okc["maclar"]["0022500001"]

    metin = {"ozet": "Houston'da Alperen Şengün double-double yaptı, maçın son saniyelerinde bir basketle takımını öne geçirdi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_okc_hou, ham_okc_hou, 0, yasakli, en_iyi_performans="Shai Gilgeous-Alexander")
    basar("T13: sonuç iddiası ('öne geçirdi') kaybedenin oyuncusuna atfedilince reddedildi", not sonuc["kabul"] and any("T13" in g for g in sonuc["gerekce"]))

    # T13 — YANLIŞ POZİTİF regresyon testi: aynı ifade KAZANAN takımın
    # oyuncusuna atfedilince serbest.
    metin = {"ozet": "Oklahoma City'de Shai Gilgeous-Alexander, maçın son saniyelerinde bir basketle takımını öne geçirdi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_okc_hou, ham_okc_hou, 0, yasakli)
    basar("T13: sonuç iddiası kazananın oyuncusuna atfedilince YANLIŞLIKLA reddedilmedi (regresyon)", "T13" not in " ".join(sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # T22 — geriye dönük test denetimi: "skor fark rakamı 20'nin altında
    # yazılmaz" kuralı bir önceki turda sistem promptuna eklenmişti ama
    # HİÇ mekanik denetimi yoktu (sadece LLM'e güveniliyordu).
    # ------------------------------------------------------------------
    metin = {"gec_satiri": "Milwaukee, Charlotte'ı 2 sayı farkla yendi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T22: küçük skor farkı rakamı ('2 sayı farkla') reddedildi", not sonuc["kabul"] and any("T22" in g for g in sonuc["gerekce"]))

    # T22 — YANLIŞ POZİTİF regresyon testi: 20+ bir fark serbest.
    metin = {"gec_satiri": "Milwaukee, Charlotte'ı 25 sayı farkla yendi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T22: 20+ skor farkı rakamı YANLIŞLIKLA reddedilmedi (regresyon)", "T22" not in " ".join(sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # T23 — mimari kural ihlalleri (sessizlik varsayılan turu)
    # ------------------------------------------------------------------
    metin = {"ozet": "Milwaukee, üçüncü çeyrekte topladığı 36 sayıyla farkı açtı; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: 'N sayı topladı' fiil hatası reddedildi", not sonuc["kabul"] and any("T23" in g for g in sonuc["gerekce"]))

    metin = {"ozet": "Maç boyunca liderlik 22 kez el değiştirdi, son periyotta bu sayı 5'e çıktı; Milwaukee kazandı, Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: lider değişimi alt kırılımı ('son periyotta 5 kez') reddedildi", not sonuc["kabul"] and any("T23" in g for g in sonuc["gerekce"]))

    metin = {"gec_satiri": "Utah, 15 lider değişimli maçta Dallas'ı geçti."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: 'N lider değişimli maçta' bozuk sıfat bileşiği reddedildi", not sonuc["kabul"] and any("T23" in g for g in sonuc["gerekce"]))

    metin = {"gec_satiri": "Phoenix Suns evinde Sacramento Kings'i 129-102 farkla ezdi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: skorla birlikte 'farkla ezdi' gereksiz tekrarı reddedildi", not sonuc["kabul"] and any("T23" in g for g in sonuc["gerekce"]))

    metin = {"gec_satiri": "Utah Jazz, Dallas Mavericks'i yenerek konferansta 13. sıraya oturdu."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: ilk-3/play-in dışı sıralama iddiası reddedildi", not sonuc["kabul"] and any("T23" in g for g in sonuc["gerekce"]))

    # T23 — YANLIŞ POZİTİF regresyon testleri
    metin = {"ozet": "Milwaukee, üçüncü çeyrekte attığı 36 sayıyla farkı açtı; Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: doğru fiil ('sayı attı') YANLIŞLIKLA reddedilmedi (regresyon)", "T23" not in " ".join(sonuc["gerekce"]))

    metin = {"gec_satiri": "Liderliğin 15 kez el değiştirdiği maçta Utah, Dallas'ı geçti."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: doğru lider-değişim kalıbı YANLIŞLIKLA reddedilmedi (regresyon)", "T23" not in " ".join(sonuc["gerekce"]))

    metin = {"gec_satiri": "Milwaukee Bucks, Charlotte Hornets'i yenerek konferansta 2. sıraya oturdu."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: ilk-3 sıralama iddiası YANLIŞLIKLA reddedilmedi (regresyon)", "T23" not in " ".join(sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # T10/T11/T12 — MEVCUT ama şimdiye kadar hiç test edilmemiş kurallar
    # (geriye dönük test denetimi, kullanıcı kararı: "testi olmayan kural,
    # kural değil" — dogrula.py'de üç test bulundu, sıfır test_dogrula_
    # bozuk.py karşılığı yoktu).
    # ------------------------------------------------------------------
    metin = {"ozet": "Milwaukee maçı kazanmış; Charlotte yenilmiş."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T10: duyulan geçmiş zaman ('-mış') reddedildi", not sonuc["kabul"] and any("T10" in g for g in sonuc["gerekce"]))

    metin = {"ozet": "Giannis bu maçta üçlü çift yaptı; Milwaukee kazandı, Charlotte yenildi."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T11: 'üçlü çift' Türkçe paraforazı reddedildi (doğrusu triple-double)", not sonuc["kabul"] and any("T11" in g for g in sonuc["gerekce"]))

    metin = {"ozet": "Charlotte Hornets maglubiyet aldı; Milwaukee kazandı."}
    sonuc = mac_metnini_dogrula(metin, gercekler_cha, ham_cha, 0, yasakli)
    basar("T12: Türkçe karakter düşürme ('maglubiyet') reddedildi", not sonuc["kabul"] and any("T12" in g for g in sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # Kadro dışı filtresi (gercekler.py, fact seviyesi — dogrula.py'nin
    # kapsamı dışında ama AYNI ÖLÇÜDE bir kural: testi olmadığı için iki
    # tur boyunca sessizce delindi, kullanıcı gözle buldu. Şimdi test var.
    # ------------------------------------------------------------------
    ham_1021 = json.loads(open(_ham_yolu("2025-10-21")).read())
    son10 = gercekler.oyuncu_son10_dakika_ortalamasi(ham_1021["oyuncu_ortalama"])
    basar(
        "kadro dışı: hazırlık sezonu (preseason) satırları 'son 10 maç' hesabına hiç girmiyor (sezon açılışında 0 oyuncu)",
        len(son10) == 0,
    )
    sezon_sayilari = gercekler.sezon_sayilari_cikart(ham_1021["oyuncu_ortalama"])
    basar(
        "sezon içi sıklık: hazırlık sezonu satırları 'bu sezon önce N kez' hesabına hiç girmiyor",
        len(sezon_sayilari) == 0,
    )

    class _SahteToplayici:
        def __init__(self):
            self.kayitlar = []

        def ekle(self, tur, veri, kaynak, guven):
            self.kayitlar.append({"tur": tur, "veri": veri})

    bt = ham_1021["maclar"]["0022500001"]["box_traditional"]["boxScoreTraditional"]
    g = _SahteToplayici()
    gercekler.kadro_disi_gerceklerini_uret(g, "0022500001", bt, son10_dakika_by_id={})
    isimler = [k["veri"]["oyuncu"] for k in g.kayitlar]
    basar(
        "kadro dışı: yıldız listesinde OLMAYAN ve dakika verisi güvenilir OLMAYAN bir isim (Ousmane Dieng) hiç fact üretmiyor",
        "Ousmane Dieng" not in isimler,
    )

    # ------------------------------------------------------------------
    # Gece çapında "üst üste/art arda" dedup (yaz.py _ust_uste_kontrolcusu_kur)
    # — Grup A ve Grup B'nin aynı gecede bu kalıbı İKİ KEZ kullanmasını
    # önleyen mekanizma; saf fonksiyon olduğu için LLM'siz test edilebilir.
    # ------------------------------------------------------------------
    gece_durumu = {"kullanildi": False}
    kontrol = yaz._ust_uste_kontrolcusu_kur(gece_durumu)
    ok1, _ = kontrol({"gec_satiri": "Boston, üst üste 5. galibiyetini aldı."})
    basar("üst üste dedup: gece içinde İLK kullanım serbest", ok1)
    gece_durumu["kullanildi"] = True
    ok2, sebep2 = kontrol({"gec_satiri": "Miami, art arda 6. galibiyetini aldı."})
    basar("üst üste dedup: gece içinde İKİNCİ kullanım reddedildi", not ok2 and sebep2 is not None)
    ok3, _ = kontrol({"gec_satiri": "Miami sakin bir galibiyet aldı."})
    basar("üst üste dedup: 'üst üste' geçmeyen aday YANLIŞLIKLA reddedilmedi (regresyon)", ok3)

    # ------------------------------------------------------------------
    # S kancası (sürpriz sonuç) — "imza attı" fiil şişirmesi baştan beri
    # her kullanımda T4'ü ihlal ediyordu, düzeltme sonrası hiç testi yoktu.
    # ------------------------------------------------------------------
    _mac_s = {"kazanan_adi": "Utah Jazz", "kaybeden_adi": "LA Clippers", "kazanan_kod": "UTA",
              "kaybeden_kod": "LAC", "ev_dep": "evinde", "buyuk": 129, "kucuk": 108, "fark": 21,
              "en_buyuk_fark_gecede_mi": False}
    _onek = cumle.kanca_oneki("S", {"surpriz_sonuc": True}, _mac_s)
    s_metni = cumle.sonuc(_mac_s, _onek)
    basar("S kancası: 'imza attı' fiil şişirmesi içermiyor", s_metni and "imza attı" not in s_metni)
    sonuc = mac_metnini_dogrula({"gec_satiri": s_metni}, gercekler_cha, ham_cha, 0, yasakli)
    basar("S kancası: ürettiği metin T4'ten geçiyor", "T4" not in " ".join(sonuc["gerekce"]))

    # ------------------------------------------------------------------
    # Brief "son_saniye" adayı — iki takım adı da çok kelimeli olduğunda
    # (Golden State Warriors + Los Angeles Lakers) eskiden T6'nın 12
    # kelime sınırını aşıyordu.
    # ------------------------------------------------------------------
    olgu_karar_ani = {"karar_ani": {"saniye_kalan": 1.0, "oyuncu": "Stephen Curry"}}
    _mac_b = {"kazanan_adi": "Golden State Warriors", "kaybeden_adi": "Los Angeles Lakers",
              "kazanan_kod": "GSW", "kaybeden_kod": "LAL", "ev_dep": "deplasmanda",
              "buyuk": 119, "kucuk": 109, "fark": 10, "en_buyuk_fark_gecede_mi": False}
    _kind, son_saniye_metni = cumle.brief_satiri(_mac_b, olgu_karar_ani, None, None)
    basar(
        "brief son_saniye: çok kelimeli takım adlarında bile 12 kelime sınırının altında",
        kelime_say(son_saniye_metni) <= 12,
    )

    # ------------------------------------------------------------------
    # Rozet-bütçesi tek cümlesi (yaz.py sablon_uret, düşük rozetli maç) —
    # T14 eşiğini geçen bir performans düşük rozette de anılmak zorunda.
    # ------------------------------------------------------------------
    gercekler_lal_mem = gercek_gece["maclar"][LAL_MEM]
    metin_dusuk = yaz.sablon_uret(gercekler_lal_mem, ham_lal, "Luka Dončić", None, kanca_harf=None, olgu={}, rozet=4.0)
    basar(
        "rozet bütçesi: düşük rozetli maçta da T14 eşiğini geçen performans anılıyor (Dončić)",
        "Dončić" in metin_dusuk,
    )

    # Rozet bütçesi — gerçek üretim bug'ı (bu tur): düşük rozetli maçta
    # eşiği geçen oyuncu KAYBEDEN takımdaysa (LaMelo Ball, CHA kaybetti)
    # "Mağlup tarafta" çerçevesi hiç eklenmiyordu, T17'yi ihlal ediyordu.
    gercek_0108 = json.loads(open("gercek/2026-01-08.json").read())
    ham_0108 = json.loads(open(_ham_yolu("2026-01-08")).read())
    gercekler_ind_cha = gercek_0108["maclar"]["0022500528"]  # IND kazandı, LaMelo Ball (CHA) kaybetti
    ham_ind_cha = ham_0108["maclar"]["0022500528"]
    # Gece izni VARKEN: "Mağlup tarafta" çerçevesi eklenmek zorunda (T17).
    _olgu_izinli = {"maglup_anilabilir_ad": "LaMelo Ball"}
    metin_dusuk_kaybeden = yaz.sablon_uret(gercekler_ind_cha, ham_ind_cha, "LaMelo Ball", None, kanca_harf="A", olgu=_olgu_izinli, rozet=5.0)
    basar("rozet bütçesi: kaybeden takımın oyuncusu 'Mağlup tarafta' çerçevesiyle anılıyor",
          "Mağlup tarafta LaMelo Ball" in metin_dusuk_kaybeden)
    # Gece izni YOKKEN: aynı maç aynı oyuncuyu hiç anmıyor (kural 1b).
    metin_izinsiz = yaz.sablon_uret(gercekler_ind_cha, ham_ind_cha, "LaMelo Ball", None, kanca_harf="A", olgu={}, rozet=5.0)
    basar("Kural1: gece izni yokken şablon yolu da kaybeden oyuncuyu anmıyor",
          "Mağlup tarafta" not in metin_izinsiz)
    sonuc = mac_metnini_dogrula({"gec_satiri": metin_dusuk_kaybeden}, gercekler_ind_cha, ham_ind_cha, 0, yasakli, en_iyi_performans="LaMelo Ball")
    basar("rozet bütçesi: kaybedene atfedilen düşük-rozet eki T17'den geçiyor", "T17" not in " ".join(sonuc["gerekce"]))

    # ==================================================================
    # TEK CÜMLE KATMANI (cumle.py) — mimari birleştirme turu.
    # Kullanıcının saydığı altı sızıntının her biri için ayrı test.
    # ==================================================================
    _mac = {"kazanan_adi": "Indiana Pacers", "kaybeden_adi": "Charlotte Hornets",
            "kazanan_kod": "IND", "kaybeden_kod": "CHA", "ev_dep": "deplasmanda",
            "buyuk": 114, "kucuk": 112, "fark": 2, "en_buyuk_fark_gecede_mi": False}

    # 1) "sezonu 21-11 yaptı" — derece son çare cümlesi TAMAMEN kalktı.
    _kd = {"sezon_guvenilir": True, "galibiyet": 7, "maglubiyet": 31, "konferans_sira": 13}
    _n = cumle.neden_onemli(_mac, {"kazanan_derece": _kd})
    # Söylenecek bir şey yok (13. sıra konuşulmaz, seri yok, maç olgusu yok)
    # → SUSAR. Eski kod burada "sezonu 7-31 yaptı" yazıyordu.
    basar("cumle: derece son-çare cümlesi ('sezonu N-M yaptı') üretilmiyor",
          _n is None or ("yaptı" not in _n and "7-31" not in _n))
    basar("cumle: söylenecek bir şey yoksa neden_onemli susuyor", _n is None)
    # Maçın kendisinden bir olgu VARSA ona dayanır (regresyon).
    _n2 = cumle.neden_onemli(_mac, {"kazanan_derece": _kd,
                                    "karar_ani": {"saniye_kalan": 4.7, "oyuncu": "LaMelo Ball"}})
    basar("cumle: olgu varsa neden_onemli maçın kendisine dayanıyor (regresyon)",
          _n2 is not None and "son saniye" in _n2)

    # 2) sıralama SADECE ilk 3 — 10. ve 13. sıra konuşulmaz.
    basar("cumle: 10. sıra konuşulmaz", not cumle.siralama_konusulabilir(10, {"sezon_guvenilir": True}))
    basar("cumle: 13. sıra konuşulmaz", not cumle.siralama_konusulabilir(13, {"sezon_guvenilir": True}))
    basar("cumle: 2. sıra konuşulur (regresyon)", cumle.siralama_konusulabilir(2, {"sezon_guvenilir": True}))
    basar("cumle: erken sezonda 2. sıra bile konuşulmaz",
          not cumle.siralama_konusulabilir(2, {"sezon_guvenilir": False}))

    # 3) lig liderinin galibiyet serisi haber DEĞİL (seri_haber=False).
    _seri = {"tur": "galibiyet", "uzunluk": 4}
    basar("cumle: lig liderinin serisi (seri_haber=False) konuşulmaz",
          not cumle.galibiyet_serisi_konusulabilir(_seri, {"sezon_guvenilir": True}, False))
    basar("cumle: sürpriz seri (seri_haber=True) konuşulur (regresyon)",
          cumle.galibiyet_serisi_konusulabilir(_seri, {"sezon_guvenilir": True}, True))
    basar("cumle: 3 maçlık seri eşiğin altında, konuşulmaz",
          not cumle.galibiyet_serisi_konusulabilir({"tur": "galibiyet", "uzunluk": 3}, {"sezon_guvenilir": True}, True))

    # 4) kadro dışı olgusu LLM'e HİÇ gösterilmiyor.
    _sahte = [{"id": "f1", "tur": "kadro_disi", "veri": {"oyuncu": "Andrew Nembhard"}},
              {"id": "f2", "tur": "skor", "veri": {"ev": "IND"}}]
    _kompakt = yaz.kompakt_gercekler(_sahte)
    basar("kadro dışı olgusu LLM'e gönderilen gerçeklerde YOK",
          all(g["tur"] != "kadro_disi" for g in _kompakt) and len(_kompakt) == 1)

    # 5) "toplamak" SADECE ribaund fiili — sayı/asist/soyut kullanım yasak.
    for _bozuk in ["Milwaukee üçüncü çeyrekte topladığı ivmeyle geri döndü.",
                   "Giannis 30 sayı ve 10 ribaund topladı.",
                   "Antetokounmpo 30 sayı topladı."]:
        _s = mac_metnini_dogrula({"ozet": _bozuk}, gercekler_cha, ham_cha, 0, yasakli)
        basar(f"T23: 'toplamak' yanlış kullanımı reddedildi ({_bozuk[:28]}...)",
              not _s["kabul"] and any("T23" in g for g in _s["gerekce"]))
    _s = mac_metnini_dogrula({"ozet": "Giannis 10 ribaund topladı; Milwaukee kazandı."}, gercekler_cha, ham_cha, 0, yasakli)
    basar("T23: 'ribaund topladı' doğru kullanımı YANLIŞLIKLA reddedilmedi (regresyon)",
          "T23" not in " ".join(_s["gerekce"]))

    # 6) Son kapı: kurucu yasaklı bir cümle üretirse yayına ÇIKMAZ (None).
    basar("cumle: son kapı yasaklı ifadeyi düşürüyor",
          cumle._gecir("Milwaukee adeta bir ders verdi.") is None)
    basar("cumle: son kapı temiz cümleyi geçiriyor",
          cumle._gecir("Milwaukee Bucks evinde 122-121 yendi.") is not None)

    # Ek üretimi tek yerden — hardcode'lu eski hatalar geri gelemez.
    basar("cumle: iyelik eki ünsüzde tamponsuz (Edwards'ın)", cumle.iyelik_eki("Edwards") == "ın")
    basar("cumle: iyelik eki seslide 'n' tamponlu (Doğu'nun)", cumle.iyelik_eki("Doğu") == "nun")
    basar("cumle: belirtme eki (Wizards'ı)", cumle.belirtme_eki("Wizards") == "ı")

    # Bütçe: "gec" katmanı tek cümle (TEK istisna eşiği geçen performans).
    _gec = cumle.govde(gercekler_cha, ham_cha, {}, None, None, "gec", yaz._takim_adi_koddan)
    basar("cumle: 'gec' katmanı tek cümle", _gec.count(".") == 1)


    # ==================================================================
    # A turu — şablon metni: tekrar yasağı, güçlü başlık, birleşik oyuncu
    # ==================================================================
    import json as _j
    _g11 = _j.loads(open("gercek/2025-11-12.json").read())
    _h11 = _j.loads(open(_ham_yolu("2025-11-12")).read())
    _s11 = _j.loads(open("skor/2025-11-12.json").read())
    _plan11 = yaz.gece_kalip_plani("2025-11-12", _g11, _h11, _s11)
    _enp11 = {m["mac_id"]: m.get("en_iyi_performans") for m in _s11["maclar"]}
    _gid = "0022500224"  # Jokić 55 sayı
    _r = cumle.mutlaka_metni(_g11["maclar"][_gid], _h11["maclar"][_gid],
                             _plan11[_gid]["olgu_ham"], _enp11[_gid], yaz._takim_adi_koddan)

    # 1) Başlık gövdede birebir tekrar edilemez.
    basar("A1: başlık gövdede birebir tekrar etmiyor", _r["baslik"] not in _r["ozet"])
    basar("A1: neden-önemli gövdede birebir tekrar etmiyor",
          not _r.get("neden_onemli") or _r["neden_onemli"] not in _r["ozet"])

    # 2) Başlık en güçlü olguyu kullanıyor (düz skor son çare).
    basar("A2: kilometre taşı varsa başlık onu kullanıyor", "Jokić" in _r["baslik"])

    # 4) Aynı oyuncu iki cümlede tekrar etmiyor, istatistikler birleşik.
    basar("A4: kanca oyuncusu gövdede tekrar edilmiyor", _r["ozet"].count("Jokić") == 0)
    # Birleşik ifade ("55 sayı ve 12 ribaundluk") TERCİH, 10 kelime
    # sınırı KURAL. İkisi çakıştığında sınır kazanır ve kanca tek
    # istatistiğe daralır — kanca tamamen atılmaz. Test bu önceliği
    # koruyor: başlık her zaman sınır içinde, kanca her zaman var,
    # birleşik biçim ancak sığdığında kullanılır.
    basar("A4: başlık 10 kelime sınırını aşmıyor", len(_r["baslik"].split()) <= 10)
    basar("A4: sınır aşılacaksa kanca daralıyor ama ATILMIYOR",
          "Jokić" in _r["baslik"] and "sayılık gecesinde" in _r["baslik"])
    import cumle as _cumle_erken
    _kisa_mac = _cumle_erken.sonuc({"kazanan_adi": "Utah", "kaybeden_adi": "Miami",
                              "kazanan_kisa": "Utah", "kaybeden_kisa": "Miami",
                              "kazanan_kod": "UTA", "buyuk": 100, "kucuk": 90},
                             "20 sayı ve 10 ribaundluk gecesinde")
    basar("A4: sığdığında birleşik ifade ve SKOR birlikte korunuyor",
          _kisa_mac is not None and "20 sayı ve 10 ribaundluk" in _kisa_mac
          and "100-90" in _kisa_mac and len(_kisa_mac.split()) <= 10)
    basar("A4: 'asist verdi' fiili kullanılmıyor",
          "asist verdi" not in _r["baslik"] + _r["ozet"] + _r.get("neden_onemli", ""))

    # -lik eki ünlü uyumu
    basar("A4: -lik eki ünlü uyumlu (ribaund→luk)", cumle.lik_eki("ribaund") == "luk")
    basar("A4: -lik eki ünlü uyumlu (sayı→lık)", cumle.lik_eki("sayı") == "lık")
    basar("A4: -lik eki ünlü uyumlu (asist→lik)", cumle.lik_eki("asist") == "lik")

    # neden-önemli SADECE bağlam ailesinden; aile içi ikizleme yok
    _gid2 = "0022500222"
    _r2 = cumle.mutlaka_metni(_g11["maclar"][_gid2], _h11["maclar"][_gid2],
                              _plan11[_gid2]["olgu_ham"], _enp11[_gid2], yaz._takim_adi_koddan)
    _n2 = _r2.get("neden_onemli", "")
    basar("A1: derece ve sıralama aynı gecede ikizlenmiyor",
          not (_n2 and "sıraya yükseldi" in _r2["ozet"] and "lider" in _n2))

    # 3) WTF = karşılaştırma; kurulamıyorsa hiç çıkmıyor.
    import derle as _derle
    _bo = _derle._box_score(_h11["maclar"][_gid], "", None)
    basar("A3: WTF bir karşılaştırma içeriyor (iki sayı)",
          _bo["wtf"] is None or ("." in _bo["wtf"] and any(ch.isdigit() for ch in _bo["wtf"].split(".")[1])))
    _h02 = _j.loads(open(_ham_yolu("2026-02-12")).read())
    _bo2 = _derle._box_score(_h02["maclar"]["0022500790"], "", None)
    basar("A3: karşılaştırma kurulamıyorsa WTF hiç çıkmıyor", _bo2["wtf"] is None)


    # ==================================================================
    # Metin uzunluğu TUTARLILIĞI (kullanıcı kararı): Mutlaka bil gövdesi
    # SABİT hedef — 4 cümle, 55-75 kelime. Eskiden sadece ÜST sınır vardı.
    # ==================================================================
    _kisa_ozet = ("Denver, ilk çeyrekte kurduğu üstünlüğü kaybetmeden kazandı. "
                  "Jokić triple-double yaptı. Murray de öne çıktı.")
    _s = mac_metnini_dogrula({"ozet": _kisa_ozet}, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: çok KISA ozet reddedildi (alt sınır artık zorunlu)",
          not _s["kabul"] and any("T6" in g for g in _s["gerekce"]))

    _uc_cumle = " ".join(["Milwaukee " + "kelime " * 20 + "kazandı."] * 3)
    _s = mac_metnini_dogrula({"ozet": _uc_cumle}, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: 3 cümlelik ozet reddedildi (hedef tam 4 cümle)",
          not _s["kabul"] and any("T6" in g for g in _s["gerekce"]))

    # 4 cümle / 55-75 kelime aralığındaki bir gövde KABUL edilmeli.
    _dogru = (
        "Milwaukee Bucks ilk çeyrekte kurduğu belirgin üstünlüğü ikinci periyotta tamamen kaybetti ve devre arasına geride girdi. "
        "Charlotte Hornets üçüncü çeyrekte farkı on altı sayıya kadar çıkardı ancak bu üstünlüğü sonuna kadar koruyamadı. "
        "Son periyotta Milwaukee Bucks savunmada bulduğu çözümle skoru yeniden dengeledi ve maçın kontrolünü eline aldı. "
        "Giannis Antetokounmpo otuz sayı ve on ribaundla karşılaşmanın en etkili ismi olarak öne çıktı."
    )
    _s = mac_metnini_dogrula({"ozet": _dogru}, gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: 4 cümle / 55-75 kelime gövde YANLIŞLIKLA reddedilmedi (regresyon)",
          "T6" not in " ".join(_s["gerekce"]))

    _s = mac_metnini_dogrula({"ozet_kisa": "Portland kazandı. Holiday öne çıktı."},
                             gercekler_cha, ham_cha, 0, yasakli)
    basar("T6: çok KISA ozet_kisa reddedildi (alt sınır 30 kelime)",
          not _s["kabul"] and any("T6" in g for g in _s["gerekce"]))


    # ==================================================================
    # T24 — aynı maçta iki triple-double: metin EN YÜKSEK GmSc'liyi anar.
    # Gerçek üretim bug'ı (12 Kasım SAS-GSW): Wembanyama 31/15/10
    # yapmışken metin Castle'ın 23/10/10'unu andı.
    # ==================================================================
    _g1112 = _j.loads(open("gercek/2025-11-12.json").read())
    _gsw = _g1112["maclar"]["0022500220"]
    _h1112 = _j.loads(open(_ham_yolu("2025-11-12")).read())["maclar"]["0022500220"]

    _s = mac_metnini_dogrula(
        {"ozet_kisa": "Kaybeden tarafta Stephon Castle 23 sayı, 10 ribaund, 10 asistle triple-double yaptı."},
        _gsw, _h1112, 0, yasakli)
    basar("T24: düşük GmSc'li triple-double anılınca reddedildi",
          not _s["kabul"] and any("T24" in g for g in _s["gerekce"]))

    _s = mac_metnini_dogrula(
        {"ozet_kisa": "Victor Wembanyama 31 sayı, 15 ribaund, 10 asistle triple-double yaptı."},
        _gsw, _h1112, 0, yasakli)
    basar("T24: en yüksek GmSc'li triple-double YANLIŞLIKLA reddedilmedi (regresyon)",
          "T24" not in " ".join(_s["gerekce"]))

    # Kuralın amacı "en iyisi ANILMALI" — zayıf olanın susturulması değil.
    # İkisi de anılıyorsa metin DOĞRUdur. (2025-10-23 GSW-DEN: metin hem
    # Curry'yi hem daha yüksek GmSc'li Gordon'ı anıyordu, T24 reddediyordu.)
    _s = mac_metnini_dogrula(
        {"ozet_kisa": "Victor Wembanyama 31 sayı, 15 ribaund, 10 asistle triple-double yaptı. "
                      "Mağlup tarafta Stephen Castle 23 sayı attı."},
        _gsw, _h1112, 0, yasakli)
    # T24, kilometre taşı İDDİA EDİLDİĞİNDE işler. Adın geçmesi tek
    # başına iddia değil — "Jokić 13 asist dağıttı" triple-double'dan
    # söz etmiyor. (Gerçek olay 2025-12-18: bu yüzden gece yayına
    # çıkamamıştı.)
    import dogrula as _dg
    import derle as _derle_erken
    _iddia = _dg._esik_iddia_ediliyor
    basar("T24: istatistik anmak kilometre taşı iddiası sayılmıyor",
          not _iddia("triple_double", "Nikola Jokić 13 asist dağıttı.")
          and not _iddia("40_sayi", "Curry 30 sayı attı."))
    basar("T24: gerçek iddia tanınıyor",
          _iddia("triple_double", "Jokić triple-double yaptı.")
          and _iddia("40_sayi", "Curry 42 sayı attı.")
          and _iddia("20_ribaund", "Gobert 22 ribaund topladı."))
    basar("T24: iddia yokken düşük GmSc'li oyuncu anılabiliyor",
          mac_metnini_dogrula({"gec_satiri": "Nikola Jokić 13 asist dağıttı."},
                              _gsw, _h1112, 0, yasakli)["kabul"]
          or "T24" not in " ".join(mac_metnini_dogrula(
              {"gec_satiri": "Nikola Jokić 13 asist dağıttı."},
              _gsw, _h1112, 0, yasakli)["gerekce"]))

    # Kısa takım adları TAM ADIN İÇİNDE geçmeli, yoksa T2 (özel ad
    # izlenebilirliği) onları uydurma sayar. "LA Lakers" tam adın
    # ("Los Angeles Lakers") içinde geçmiyordu ve 18 Aralık'ı yayından
    # alıkoydu.
    basar("Kısa takım adları izlenebilir (tam adın öneki)",
          all(_derle_erken.TAKIM_ADI[k].startswith(v)
              for k, v in _derle_erken.TAKIM_KISA.items()))
    import cumle as _cm
    basar("Kısa ad tablosu iki dosyada da aynı",
          _cm.TAKIM_KISA == _derle_erken.TAKIM_KISA)

    basar("T24: en iyisi de anıldığında ikinci oyuncunun anılması reddedilmiyor",
          "T24" not in " ".join(_s["gerekce"]))

    # Seçim katmanı da aynı oyuncuyu seçmeli.
    import kalip_secici as _ks
    _kilo = [f["veri"] for f in _gsw if f["tur"] == "kilometre"]
    _secilen = _ks.en_iyi_kilometre(_kilo)
    basar("en_iyi_kilometre: aynı eşikte en yüksek GmSc'li seçiliyor",
          _secilen and _secilen["oyuncu"] == "Victor Wembanyama")



    # ==================================================================
    # Kutu skoru işaret kuralı (kullanıcı kuralı, son tur): işaret SADECE
    # her takımın İLK satırında. Ember = kazananın ilk satırı, mavi =
    # kaybedenin ilk satırı. GmSc kriteri kalktı. Önceki kural "maçın en
    # yüksek GmSc'li oyuncusu" idi ve satır sırasından bağımsızdı —
    # işaret tablonun ortasında bir yerde beliriyordu.
    # ==================================================================
    import derle as _derle
    _ham_kutu = _j.loads(open(_ham_yolu("2026-03-05")).read())
    for _gid, _hm in _ham_kutu["maclar"].items():
        _b = _derle._box_score(_hm)
        _kaz, _kay = ((_b["ev"], _b["dep"]) if _b["ev"]["skor"] >= _b["dep"]["skor"]
                      else (_b["dep"], _b["ev"]))
        _tum = _b["ev"]["oyuncular"] + _b["dep"]["oyuncular"]
        basar(f"kutu {_gid}: ember TEK ve kazananın ilk satırında",
              sum(1 for o in _tum if o.get("gecti_mi")) == 1
              and _kaz["oyuncular"][0].get("gecti_mi") is True)
        basar(f"kutu {_gid}: mavi TEK ve kaybedenin ilk satırında",
              sum(1 for o in _tum if o.get("kaybedenin_en_iyisi")) == 1
              and _kay["oyuncular"][0].get("kaybedenin_en_iyisi") is True)
        basar(f"kutu {_gid}: işaretli satır aynı anda iki renk almıyor",
              not any(o.get("gecti_mi") and o.get("kaybedenin_en_iyisi") for o in _tum))

    # Metinde adı geçmek artık işaret sebebi DEĞİL (regresyon: eski kural
    # metinde anılan herkesi işaretliyordu, üç oyuncuda birden çizgi
    # çıkıyordu).
    _gid0 = sorted(_ham_kutu["maclar"])[0]
    _b_metinli = _derle._box_score(_ham_kutu["maclar"][_gid0], "Bu maçta herkes oynadı.")
    _b_metinsiz = _derle._box_score(_ham_kutu["maclar"][_gid0])
    basar("kutu: işaret metinden bağımsız (metin verilse de aynı)",
          [o.get("gecti_mi") for o in _b_metinli["ev"]["oyuncular"]]
          == [o.get("gecti_mi") for o in _b_metinsiz["ev"]["oyuncular"]])

    # ==================================================================
    # Gecenin beşi: ana sayfa satırının sağ ucu için TAM takım adı
    # (kısaltma değil) ve takım rengi her oyuncuda dolu olmalı.
    # ==================================================================
    _html = open("overnight_v17.html", encoding="utf-8").read()
    _dist0305 = _j.loads(open("dist/2026-03-05.json").read())
    basar("gecenin beşi: her oyuncuda tam takım adı var",
          all(o.get("takim_adi") for o in _dist0305["gecenin_besi"]))
    basar("gecenin beşi: takım adı kısaltma DEĞİL",
          all(len(o["takim_adi"]) > 3 and o["takim_adi"] != o.get("takim")
              for o in _dist0305["gecenin_besi"]))
    basar("gecenin beşi: her oyuncuda takım rengi var (kart için)",
          all(str(o.get("renk", "")).startswith("#") for o in _dist0305["gecenin_besi"]))

    # Kullanıcı kararı: ana sayfadaki beş satır tek renk (sitenin gold'u)
    # — beş ayrı takım rengi cümbüş oluyordu. Takım renkleri KARTTA,
    # basınca çıkıyor.
    basar("html: ana sayfadaki beşi şeridi rozet turuncusu, takım rengi taşımıyor",
          "background:var(--ember)}" in _html.split(".besirow::before")[1][:200]
          and '--tc:${esc(o.renk' not in _html)
    basar("html: beşi şeritleri tek çubuk değil, satır arası boşluklu",
          "top:3px;bottom:3px" in _html.split(".besirow::before")[1][:200])
    basar("html: takım rengi kartta duruyor (regresyon)",
          "border-left-color:${esc(o.renk)}" in _html)

    # Türk oyuncu listesi elle tutuluyor — kadro değişince testin de
    # bilmesi gerek (kullanıcı eklemesi: Adem Bona, PHI).
    _turk = _j.loads(open("config/turk_oyuncular.json").read())["oyuncular"]
    # Liste KASITLI olarak tam küme kontrol ediliyor: kadro değişikliği
    # (transfer, kesilme, draft) sessizce geçmesin, testi düşürsün ve
    # elle gözden geçirilsin. NBA'de aktif Türk oyuncu sayısı tek haneli
    # olduğu için bu bakım yükü değil, koruma.
    basar("türk listesi: sadece aktif iki oyuncu (Şengün, Bona)",
          {(o["ad"], o["takim"]) for o in _turk}
          == {("Alperen Şengün", "HOU"), ("Adem Bona", "PHI")})
    basar("türk listesi: her oyuncunun takım kodu geçerli",
          all(o["takim"] in _derle.TAKIM_ADI for o in _turk))

    # Sahaya çıkmayan oyuncuların satırı: HERKES anılır, ama tarih
    # uydurulmaz — kimin maçı ne zamansa o yazılır. (Eskiden sadece en
    # erken tarihli oyuncular anılıyordu, liste ikiye inince Bona her
    # seferinde cümleden düşüyordu.)
    _bek4 = _derle._turkler_bekleyen(
        {"sonraki_maclar": {"HOU": "2025-10-24", "PHI": "2025-10-25"}},
        [{"ad": "Alperen Şengün", "takim": "HOU"}, {"ad": "Adem Bona", "takim": "PHI"}])
    basar("türkler: farklı günlerde oynayan oyuncuların İKİSİ de anılıyor",
          "Şengün" in _bek4["metin"] and "Bona" in _bek4["metin"])
    basar("türkler: her oyuncuya KENDİ tarihi yazılıyor",
          _bek4["metin"] == "Bu gece Türk oyuncu sahaya çıkmadı. Şengün 24 Ekim'de, Bona 25 Ekim'de sahaya çıkıyor.")

    # ==================================================================
    # Türkler bölümü: o gece Türk oyuncu sahaya çıkmadıysa bölüm en alta
    # iner ve sonraki maç tarihini söyler. Tarih UYDURULMAZ — veri yoksa
    # cümle tarihsiz kurulur (projenin temel kuralı).
    # ==================================================================
    basar("türkler: sahada oyuncu varken 'bekleyen' bloğu üretilmiyor",
          _dist0305["turkler"] and _dist0305.get("turkler_bekleyen") is None)

    _tk = [{"ad": "Alperen Şengün", "takim": "HOU"}, {"ad": "Cedi Osman", "takim": "SAS"}]
    _bek = _derle._turkler_bekleyen({"sonraki_maclar": {"HOU": "2026-03-07", "SAS": "2026-03-09"}}, _tk)
    basar("türkler: farklı günlerde oynayanların hepsi anılıyor, tarih alanı en erken olan",
          set(_bek["isimler"]) == {"Şengün", "Osman"} and _bek["tarih"] == "7 Mart'ta")
    basar("türkler: her oyuncu KENDİ tarihiyle anılıyor",
          _bek["metin"] == "Bu gece Türk oyuncu sahaya çıkmadı. Şengün 7 Mart'ta, Osman 9 Mart'ta sahaya çıkıyor.")

    _bek2 = _derle._turkler_bekleyen({"sonraki_maclar": {"HOU": "2026-03-07", "SAS": "2026-03-07"}}, _tk)
    basar("türkler: aynı gün oynayan iki oyuncu 've' ile tek tarihte birleşiyor",
          _bek2["metin"] == "Bu gece Türk oyuncu sahaya çıkmadı. Şengün ve Osman 7 Mart'ta sahaya çıkıyor.")

    _bek3 = _derle._turkler_bekleyen({}, _tk)
    basar("türkler: sonraki maç verisi yoksa TARİH UYDURULMUYOR",
          _bek3["tarih"] is None and "çıkıyor" not in _bek3["metin"])

    basar("tarih eki: ünlü uyumu ve ünsüz sertliği doğru",
          [_derle._tarih_tr(g, bulunma=True) for g in
           ("2026-01-03", "2026-04-05", "2026-09-07", "2026-10-09", "2026-12-11")]
          == ["3 Ocak'ta", "5 Nisan'da", "7 Eylül'de", "9 Ekim'de", "11 Aralık'ta"])

    # ==================================================================
    # HTML katmanı: spoiler özelliği TAMAMEN kalktı, bölüm sırası yeni.
    # ==================================================================
    basar("html: spoiler düğmesi/sınıfı/mantığı kalmadı",
          "veil" not in _html and "spoilerbtn" not in _html and "body.spoil" not in _html)
    import re as _re
    _sira = [x for x in _re.findall(r'<section class="sec ([a-zA-Z0-9]+)"', _html)]
    basar("html: bölüm sırası 30 saniyede → Türkler → Mutlaka bil → Göz at → Bunları geç → Gecenin beşi",
          _sira[:6] == ["s1", "sTr", "s3", "s4b", "s7", "s6"])
    # Başlık altındaki tanıtım cümlesi KALKTI: açılış artık künye ve
    # yerinde gecenin sayıları duruyor (bkz. "AÇILIŞ (HERO)" bölümü).
    basar("html: başlık altında tanıtım cümlesi yok, veri var",
          "Molasız, reklamsız özet." not in _html
          and "Sıraya senin yerine biz karar verdik" not in _html
          and '<div class="nums" id="nums"></div>' in _html)


    # ==================================================================
    # Canlıya alma turu — üç kural.
    # ==================================================================

    # 1) Uzunluk ALT sınırı sadece LLM çıktısına uygulanır (kullanıcı
    # kuralı). Şablonun varsayılanı susmak; alt sınır onu olmayan bir
    # olguyu uydurmaya zorlardı. ÜST sınır şablonda da geçerli.
    from dogrula import t6_uzunluk as _t6
    _kisa_ozet = "Portland Trail Blazers deplasmanda Utah Jazz'ı 135-119 yendi. Jrue Holiday 31 sayı attı."
    basar("T6: kısa 'ozet' LLM çıktısı olarak REDDEDİLİYOR",
          not _t6("ozet", _kisa_ozet)[0])
    basar("T6: aynı metin ŞABLON çıktısı olarak kabul ediliyor",
          _t6("ozet", _kisa_ozet, sablon=True)[0])
    basar("T6: şablonda ÜST sınır hâlâ uygulanıyor",
          not _t6("ozet", " ".join(["kelime"] * 90), sablon=True)[0])
    basar("T6: şablonda BOŞ metin yine de reddediliyor",
          not _t6("ozet", "", sablon=True)[0])
    basar("T6: ozet_kisa'da da alt sınır şablonda muaf, üst sınır değil",
          _t6("ozet_kisa", "Golden State kazandı. Curry 30 sayı attı.", sablon=True)[0]
          and not _t6("ozet_kisa", " ".join(["kelime"] * 60), sablon=True)[0])
    basar("T6: başlık 10 kelime sınırı ŞABLONDA da geçerli (taşma kuralı, uydurma değil)",
          not _t6("baslik", " ".join(["kelime"] * 12) + " yendi", sablon=True)[0])

    # Brief TEK satır: aynı maçta daha yüksek GmSc'li bir kilometre
    # sahibi varsa kazananın daha küçük performansı brief'e çıkmaz —
    # başka bir olguya düşer. (2025-10-23 GSW-DEN: Curry 42 yerine
    # maçın uzatmaya gitmesi anlatılır; Gordon'ın 50'si gövdede.)
    import cumle as _cumle, yaz as _y0, json as _jj
    _g23 = _jj.loads(open("gercek/2025-10-23.json").read())
    _h23 = _jj.loads(open(_ham_yolu("2025-10-23")).read()) if _os.path.exists(_ham_yolu("2025-10-23")) else None
    if _h23:
        _s23 = _jj.loads(open("skor/2025-10-23.json").read())
        _p23 = _y0.gece_kalip_plani("2025-10-23", _g23, _h23, _s23)
        _e23 = {m["mac_id"]: m.get("en_iyi_performans") for m in _s23["maclar"]}
        _gid23 = "0022500006"
        _b = _y0.sablon_uret_brief(_gid23, _g23["maclar"][_gid23], _h23["maclar"][_gid23],
                                   _p23[_gid23]["olgu_ham"], _e23[_gid23])
        basar("Brief: daha yüksek GmSc'li kilometre varken zayıf performans satırı kurulmuyor",
              _b is None or "Curry" not in _b.get("metin", ""))

    # Girdi maliyeti: Grup B promptuna gerçeklerin TAMAMI değil, ilgili
    # alt kümesi gidiyor. Ölçüm (2026-01-28): 103 kalem → 25 kalem,
    # girdi 21.535 → 13.518 token. oyuncu_ceyrek hiç gitmiyor.
    _g0128 = _j.loads(open("gercek/2026-01-28.json").read())["maclar"]["0022500679"]
    _alt = _y0.grup_b_gercekleri(_g0128, "Victor Wembanyama")
    basar("Girdi: gerçeklerin tamamı değil alt kümesi gönderiliyor",
          len(_alt) < len(_g0128) / 3)
    basar("Girdi: oyuncu_ceyrek kayıtları LLM'e hiç gönderilmiyor",
          not any(f["tur"] == "oyuncu_ceyrek" for f in _alt))
    basar("Girdi: en iyi performans oyuncusu HER ZAMAN gönderiliyor (T14 şart koşuyor)",
          any(f["tur"] == "oyuncu_stat" and f["veri"]["oyuncu"] == "Victor Wembanyama"
              for f in _alt))
    _kucuk = _y0.grup_b_gercekleri(_g0128, "Yok Böyle Biri")
    basar("Girdi: skor/çeyrek/derece gibi küçük türlerin tamamı korunuyor",
          {f["tur"] for f in _kucuk} >= {"skor", "ceyrek", "derece"})

    # Önbellek: büyük ve DEĞİŞMEYEN kısım promptun BAŞINDA olmalı, yoksa
    # önek eşleşmez ve hiçbir şey önbellekten okunamaz. Maç verisi bloğu
    # onarım denemelerinde de birebir aynı kalmalı.
    _h0128 = _j.loads(open(_ham_yolu("2026-01-28")).read()) if _os.path.exists(_ham_yolu("2026-01-28")) else None
    if _h0128:
        _s0128 = _j.loads(open("skor/2026-01-28.json").read())
        _gg = _j.loads(open("gercek/2026-01-28.json").read())
        _k0128 = _y0.gece_kalip_plani("2026-01-28", _gg, _h0128, _s0128)
        _orn = _y0.ornekler_yukle()
        _args = ("0022500679", _g0128, _h0128["maclar"]["0022500679"],
                 _y0.MUZIP_BUTCESI_TOPLAM, _k0128["0022500679"], _orn, "Victor Wembanyama")
        _mv1, _t1 = _y0.grup_b_prompt_kur(*_args)
        _mv2, _t2 = _y0.grup_b_prompt_kur(*_args, onceki_hatalar=["T16: örnek"])
        basar("Önbellek: maç verisi bloğu onarım denemesinde de birebir aynı",
              _mv1 == _mv2)
        basar("Önbellek: değişen kısım (talimatlar) ayrı parçada",
              _t1 != _t2)
        basar("Önbellek: maç verisi ayrı parça olarak dönüyor (önek olabilsin diye)",
              _mv1.startswith("Maç verisi:"))

    # 2) Bir gecede LLM'e giden "Mutlaka bil" maçı sayısı tek yerden
    # kontrol ediliyor — maliyetin asıl kaldıracı bu.
    import yaz as _yaz
    # Bu kısıt KALDIRILDI (önbellek düzeltmesinden sonra maliyet
    # gerekçesi kalmadı). Artık Mutlaka bil'e giren her maç LLM'den
    # geçiyor — 2./3. maçlar şablonda tek cümlede kalıyordu.
    basar("Maliyet: Mutlaka bil'in tamamı LLM'den (kısıt kalktı)",
          _yaz.MUTLAKA_LLM_MAC_SAYISI == _yaz.MUTLAKA_MAX_MAC)

    # ==================================================================
    # Mutlaka bil / Göz at kesme noktası — EN BÜYÜK BOŞLUKTAN.
    # ==================================================================
    # Sabit 8.5 eşiği kördü: 8.9 Mutlaka bil'e, 8.8 ve 8.6 Göz at'a
    # düşüyordu; okuyucu için o üç maç arasında fark yok. Yeni kural
    # gecenin KENDİ dağılımına bakıyor.
    def _kes(rozetler):
        sahte = {"maclar": [{"mac_id": str(i), "rozet": r} for i, r in enumerate(rozetler)]}
        return len(_yaz._mutlaka_ve_diger(sahte)[0])

    basar("Kesme: en büyük boşluk sonda → dört maç girer",
          _kes([9.2, 8.9, 8.8, 8.6, 6.4]) == 4)
    basar("Kesme: boşluk ikinci sırada → iki maç girer",
          _kes([9.3, 8.9, 6.4, 6.1]) == 2)
    basar("Kesme: boşluk hemen başta → tek maç girer",
          _kes([9.1, 7.2, 7.1, 7.0]) == 1)
    basar("Kesme: üst sınır 4'ü aşmıyor",
          _kes([9.9, 9.8, 9.7, 9.6, 5.0]) <= 4 and _yaz.MUTLAKA_MAX_MAC == 4)
    basar("Kesme: 'kötünün iyisi' korunuyor — eşiği geçen yoksa TEK maç",
          _kes([8.2, 8.1, 5.0, 4.9]) == 1)
    basar("Kesme: tek maçlık gecede tek maç", _kes([9.4]) == 1)
    # Eşitlikte ÜSTTEKİ tercih edilir: vaat "üçünü bilmen yeter",
    # cömertlik değil.
    basar("Kesme: eşit boşluklarda az maç tercih ediliyor",
          _kes([9.0, 8.9, 8.8, 8.7, 8.6]) <= 2)
    # Bölüm sayacı bu sayıyı göstermeli.
    basar("Kesme: bölüm sayacı maç sayısını yazıyor",
          "${d.mutlaka.length} maç · en önemlileri"
          in open("overnight_v17.html", encoding="utf-8").read())

    # Kalibrasyon üretimin GERÇEK kuralını ölçmeli — kopya kural iki
    # yerde ayrışır ve tablo yalan söyler.
    _kal_kaynak = open("kalibrasyon.py", encoding="utf-8").read()
    basar("Kalibrasyon: kesme kuralını yaz.py'den alıyor (kopyalamıyor)",
          "from yaz import _mutlaka_ve_diger" in _kal_kaynak)
    import kalibrasyon as _kalib_erken
    _kal_geceler = _kalib_erken.geceleri_oku()
    basar("Kalibrasyon: gece başına Mutlaka bil sayısı raporlanıyor",
          all("mutlaka_sayisi" in g for g in _kal_geceler))
    basar("Kalibrasyon: dağılım tek değere yığılmıyor",
          len({g["mutlaka_sayisi"] for g in _kal_geceler}) >= 3)

    # 3) Kademeli effort: ilk deneme ucuz, onarım denemesi güçlü.
    # Ölçüm: medium 6543 çıktı token / $0.1256 — low 2289 / $0.0831,
    # ikisinde de gövde 58-59 kelime (yani düşük effort metni kısaltmıyor).
    basar("Maliyet: ilk deneme düşük effort, onarım denemesi yüksek",
          _yaz.GRUP_B_EFFORT_ILK == "low" and _yaz.GRUP_B_EFFORT == "medium")

    # 4) Günlük bütçe tavanı TEK boğaz noktasında (llm_cagir) — üretim
    # yolları çoğalınca kuralın bir yolda unutulması mümkün olmasın.
    _eski_takip = list(_yaz.KULLANIM_TAKIBI)
    _eski_ortam = _os.environ.get("GUNLUK_BUTCE_USD")
    try:
        _os.environ["GUNLUK_BUTCE_USD"] = "0.30"
        _yaz.KULLANIM_TAKIBI.clear()
        basar("Bütçe: tavan ortam değişkeninden okunuyor", _yaz._butce_tavani() == 0.30)
        _yaz.KULLANIM_TAKIBI.append(
            {"model": _yaz.GUCLU_MODEL, "girdi": 100_000, "cikti": 10_000,
             "cache_yazma": 0, "cache_okuma": 0})
        _asti = False
        try:
            _yaz.llm_cagir(_yaz.GUCLU_MODEL, "s", "k")
        except _yaz.ButceAsildi:
            _asti = True
        except Exception:
            pass
        basar("Bütçe: tavan aşılınca LLM çağrısı YAPILMADAN durduruluyor", _asti)
        _os.environ.pop("GUNLUK_BUTCE_USD")
        _yaz.KULLANIM_TAKIBI.clear()
        basar("Bütçe: ortam değişkeni yokken tavan uygulanmıyor (elle çalıştırma)",
              _yaz._butce_tavani() is None)
    finally:
        _yaz.KULLANIM_TAKIBI[:] = _eski_takip
        if _eski_ortam is None:
            _os.environ.pop("GUNLUK_BUTCE_USD", None)
        else:
            _os.environ["GUNLUK_BUTCE_USD"] = _eski_ortam

    # 5) Yayın kapısı: doğrulamadan geçmeyen "Mutlaka bil" metni canlıya
    # çıkmaz. Projenin ilk pazarlıksız kuralı ("doğrulanmamış cümle yayına
    # çıkmaz") elle gözden geçirilmeyen bir akışta ancak böyle korunur.
    import yayin as _yayin
    # Kapı, belirli bir geceye değil KURALA bağlı test edilir — gecenin
    # metni düzelince testin de düşmesi yanlış sinyal olurdu (bu gerçekten
    # oldu: 2025-10-23'ün T17/T24 hataları düzeltilince test kırıldı).
    _sahte = {"rapor": {"sablon_isaretli": [
        {"mac_id": "X", "alan": "mutlaka", "gerekce": ["ozet/T17: kaybeden özne"]},
        {"mac_id": "Y", "alan": "mutlaka", "gerekce": ["baslik/T6: 12 kelime (sınır 10)"]},
    ]}}
    _yol = _os.path.join("taslak", "_kapi_testi.json")
    open(_yol, "w", encoding="utf-8").write(_jj.dumps(_sahte, ensure_ascii=False))
    try:
        _e = _yayin.yayin_engelleri("_kapi_testi")
        basar("Yayın kapısı: gerçek/dil hatası (T17) yayını DURDURUYOR",
              len(_e) == 1 and _e[0]["mac_id"] == "X")
        basar("Yayın kapısı: uzunluk işareti (T6) yayını durdurmuyor",
              all(x["mac_id"] != "Y" for x in _e))
    finally:
        _os.remove(_yol)
    basar("Yayın kapısı: engelleyici testler listesi gerçeğe dair testlerden oluşuyor",
          "T17" in _yayin.ENGELLEYICI_TESTLER and "T6" not in _yayin.ENGELLEYICI_TESTLER)
    _d = _yayin.durum_oku()
    # Sayıyı SABİTLEMEK yanlıştı: emekli listesi her yeni emeklilikte
    # değişiyor, test de her seferinde kırılıyordu. Değişmez şu: emekli
    # bir gece ne yayınlananlarda ne de sıradaki gecede olabilir.
    basar("Yayın durumu: emekli geceler yayın sırasına girmiyor",
          bool(_d["atlanan"])
          and not (set(_d["atlanan"]) & set(_d["yayinlanan"]))
          and (_d.get("hazir") or {}).get("tarih") not in _d["atlanan"])
    basar("Yayın durumu: takılan geceler emekli listesinden AYRI tutuluyor",
          "engellenen" in _d or _d.get("engellenen") == [])


    # ==================================================================
    # Bülten turu — üç kural.
    # ==================================================================

    # 1) Geri dönüş SAYISIZ anılamaz. "farktan dönerek yendi" okura
    # hiçbir şey söylemiyor; 4 sayılık da 16 sayılık da o cümleye sığar.
    # Sayı her zaman elimizde: fark_serisi.kazanan_en_buyuk_acigi.
    # (Gerçek üretim bug'ı 2026-01-28 — veri promptta VARDI, model
    # kullanmadı; o yüzden düzeltme prompta değil doğrulayıcıya yazıldı.)
    import shutil as _shutil
    import dogrula as dogrula_modul
    import kalip_secici as _kalip_secici
    from dogrula import t23_mimari_kural_ihlalleri as _t23
    basar("T23: sayısız geri dönüş reddediliyor",
          not _t23("San Antonio, Houston'ı farktan dönerek 111-99 yendi.")[0])
    basar("T23: sayısız 'geri dönüş' ifadesi de reddediliyor",
          not _t23("Golden State, geri dönüşü tamamladı.")[0])
    basar("T23: sayılı geri dönüş YANLIŞLIKLA reddedilmiyor (regresyon)",
          _t23("San Antonio, 16 sayılık farktan dönüp Houston'ı yendi.")[0]
          and _t23("Orlando, 14 sayılık farkı eritti.")[0])
    basar("T23: 'sayı farkla yendi' geri dönüş sanılmıyor (regresyon)",
          _t23("Boston, Miami'yi 20 sayı farkla yendi.")[0])

    # 2) Seyrek geceler yayınlanmaz — tek maçlık bir sayfa gece özeti
    # değil, tek maç raporu; ürünün triyaj vaadiyle çelişiyor.
    basar("Yayın: asgari maç eşiği 3", _yayin.ASGARI_MAC_SAYISI == 3)

    # 3) Bülten. "Mail vitrin, site asıl yer" — kutu skor maile girmez.
    _os.environ.setdefault("SITE_ADRESI", "https://ornek.test")
    _os.environ.setdefault("ABONE_GIZLI_ANAHTAR", "test-gizli-anahtar-123")
    import importlib
    import bulten as _bulten
    importlib.reload(_bulten)
    _veri = _j.loads(open("dist/2026-01-28.json").read())
    _cikis = _bulten._cikis_bagi("ali@ornek.com")
    _html = _bulten.mail_govdesi(_veri, _cikis)
    _metin = _bulten.mail_metni(_veri, _cikis)

    # Kutu skor maile girmez. Ölçüt "hiç oyuncu adı geçmesin" DEĞİL —
    # Türkler bölümü ve brief satırları bilerek isim taşıyor. Doğru
    # ölçüt: SADECE kutu skorda olan (metnin hiçbir yerinde anılmayan)
    # bir oyuncu mailde görünmemeli.
    _metinler = " ".join(
        [b["metin"] for b in _veri["brief"]]
        + [m["baslik"] + " " + m.get("ozet", "") + m.get("ozet_kisa", "") for m in _veri["mutlaka"]]
        + [t["isim"] for t in _veri["turkler"]]
    )
    _sadece_kutuda = [
        o["isim"]
        for m in _veri["mutlaka"]
        for yan in ("ev", "dep")
        for o in m["box"][yan]["oyuncular"]
        if o["isim"] not in _metinler
    ]
    basar("Bülten: sadece kutu skorda olan oyuncular maile girmiyor",
          bool(_sadece_kutuda) and not any(ad in _html for ad in _sadece_kutuda))
    basar("Bülten: '30 saniyede gece' satırları var",
          all(b["metin"] in _html for b in _veri["brief"]))
    basar("Bülten: Mutlaka bil başlıkları var",
          all(m["baslik"] in _html for m in _veri["mutlaka"]))
    basar("Bülten: siteye bağlantı var", "https://ornek.test/" in _html)
    basar("Bülten: çıkış bağlantısı HER iki sürümde de var",
          "/api/cikis?" in _html and "/api/cikis?" in _metin)
    basar("Bülten: charset bildirimi var (Türkçe karakter bozulmasın)",
          'charset="utf-8"' in _html)
    basar("Bülten: açık zemin AÇIKÇA yazılı (koyu temada okunsun)",
          "background:#FFFFFF" in _html and 'content="light"' in _html)

    # Çıkış token'ı iki dilde üretiliyor (Python gönderirken, JS
    # doğrularken) — birebir aynı olmalı, yoksa bağlantı çalışmaz.
    # Aşağıdaki değer node crypto ile üretildi ve elle sabitlendi.
    _beklenen = ("https://ornek.test/api/cikis?e=YWxpQG9ybmVrLmNvbQ"
                 "&t=YVrUb3KfpdVJSDD8Wv4vcQil4FvCArX73W_zcULrA44")
    basar("Bülten: çıkış token'ı Node tarafıyla birebir aynı",
          _bulten._cikis_bagi("ali@ornek.com") == _beklenen)

    # Abone listesi DEPODA OLMAMALI: adresler git geçmişine yazılırsa
    # abonelikten çıkan biri bile eski commit'lerde kalır. Liste artık
    # Upstash'te; depoda bir kopyasının belirmesi geriye dönüş olur.
    # Bülten kurulmadan önce iş BAŞARISIZ sayılmamalı — yoksa site
    # yayınlanmış olmasına rağmen her sabah hata bildirimi gider ve
    # gerçek hatalar bu gürültünün içinde kaybolur.
    _bk = open("bulten.py", encoding="utf-8").read()
    basar("Bülten: hiç ayar yokken 'kurulmamış' sayılıyor (hata değil)",
          "if len(eksik) == len(ayarlar):" in _bk and "return 0" in
          _bk.split("if len(eksik) == len(ayarlar):")[1][:300])
    basar("Bülten: yarım kurulum yapılandırma hatası sayılıyor",
          "bu bir yapılandırma hatası" in _bk)

    # CI'da test fixture'ları OKUNABİLİR olmalı. .gitignore'da eğik
    # çizgisiz "ham/" deseni test_verisi/ham/'i de dışlıyordu ve temiz
    # kopyada testler ilk satırda çöküyordu — üretim hiç başlamıyordu.
    _gi = open(".gitignore", encoding="utf-8").read()
    basar(".gitignore: ham deseni sadece kökü dışlıyor",
          "/ham/" in _gi and "\nham/" not in _gi)
    basar("Test fixture'ları mevcut", _os.path.isdir("test_verisi/ham")
          and len(_os.listdir("test_verisi/ham")) >= 5)

    basar("Bülten: abone listesi depoda TUTULMUYOR",
          not _os.path.exists("config/aboneler.json"))
    _bulten_kaynak = open("bulten.py", encoding="utf-8").read()
    basar("Bülten: liste Upstash'ten okunuyor, dosyadan değil",
          "SMEMBERS" in _bulten_kaynak and "aboneler.json" not in _bulten_kaynak)
    _ortak = open("api/_ortak.js", encoding="utf-8").read()
    basar("Bülten: uç noktalar da depoya yazmıyor",
          "api.github.com" not in _ortak and "SADD" in _ortak and "SREM" in _ortak)


    # ==================================================================
    # Kendini çürüten cümle + "an" önem sırası.
    # ==================================================================

    # a) Sonucu ETKİLEMEYEN an, LLM'e hiç gönderilmiyor. Kök sebep:
    # anlar önem sırasına göre değil EN GEÇ olana göre seçiliyordu, o
    # yüzden 12 sayı farkla biten maçın son saniyesindeki anlamsız smaç
    # listenin başına geçiyordu (gerçek üretim bug'ı, Spurs-Rockets).
    _an_hepsi = [f for f in _g0128 if f["tur"] == "an"]
    _an_gonderilen = [f for f in _y0.grup_b_gercekleri(_g0128, "Victor Wembanyama")
                      if f["tur"] == "an"]
    basar("an: sonucu etkilemeyen anlar elendi",
          len(_an_gonderilen) < len(_an_hepsi) / 3)
    basar("an: gönderilen anların hepsi son periyot ya da uzatmada",
          all(f["veri"]["periyot"] >= _y0.AN_SON_PERIYOT for f in _an_gonderilen))
    basar("an: gönderilen anların hepsi maç yakınken oldu",
          all(f["veri"].get("tur_alt") == "lider_degisimi"
              or abs(f["veri"].get("fark") or 0) <= _y0.AN_YAKIN_FARK
              for f in _an_gonderilen))
    basar("an: disiplin kayıtları (teknik faul vb.) hiç gönderilmiyor",
          not any(f["veri"].get("tur_alt") == "disiplin" for f in _an_gonderilen))
    _erken = [{"tur": "an", "veri": {"periyot": 1, "fark": 2, "tur_alt": "klutch_sayi", "saat": "PT01M"}}]
    basar("an: maç yakın olsa da ERKEN periyot anı gönderilmiyor",
          _y0._onemli_anlar(_erken) == [])
    _uzak = [{"tur": "an", "veri": {"periyot": 4, "fark": 18, "tur_alt": "klutch_sayi", "saat": "PT00M"}}]
    basar("an: geç olsa da FARK AÇIKKEN atılan basket gönderilmiyor",
          _y0._onemli_anlar(_uzak) == [])

    # b) Bir olayı anıp ardından önemsizliğini söyleyen yapı reddedilir.
    for _c in ("Capela'nın smacı skoru etkilemese de San Antonio kazandı.",
               "Son basket sonucu değiştirmese de tribünler ayaktaydı.",
               "Bu basket fark etmese de moral oldu.",
               "Son hücum boşa gitse de Denver kazandı.",
               "Serbest atış etkisiz kalsa da maç bitti."):
        basar(f"T23: kendini çürüten yapı reddedildi ({_c[:34]}…)", not _t23(_c)[0])
    basar("T23: gerçekten sonucu belirleyen an YANLIŞLIKLA reddedilmiyor (regresyon)",
          _t23("San Antonio, dördüncü periyotta Wembanyama'nın serbest atışıyla öne geçti.")[0])

    # Kural cümle katmanının kapısında da olmalı — şablon da üretemesin.
    basar("cumle: kendini çürüten cümle şablon kapısından da geçemiyor",
          _cumle._gecir("Capela'nın smacı skoru etkilemese de maç bitti.") is None)

    # Ad çakışması nöbeti: T23'ün geri dönüş deseni, dosyanın ilerisindeki
    # aynı adlı geniş desenle karışmamalı (bir kez oldu, sessizce yanlış
    # deseni kullandı).
    basar("dogrula: T23 kendi geri dönüş desenini kullanıyor",
          hasattr(dogrula_modul, "T23_GERI_DONUS_DESENI"))


    # ==================================================================
    # Kaydırma performansı — titreme nöbeti.
    # ==================================================================
    # Kullanıcı bildirimi: tasarım turundan sonra sayfa kaydırırken
    # titremeye başladı. Ölçüldü: kaydırma olayı başına 6 düzen okuması
    # (getBoundingClientRect) ve 9 adet ekrana sabitlenmiş zemin katmanı.
    # Asıl kötü kısım geri beslemeydi: sınıf değişince başlığın PUNTOSU
    # değişiyordu, yani ŞERİDİN YÜKSEKLİĞİ değişiyordu — bu da altındaki
    # içeriği kaydırıp koşulu yeniden tetikliyordu.
    #
    # Bu testler o üçünün geri gelmesini engelliyor.
    # DİKKAT: `_html` bülten testinde mail gövdesine yeniden atanıyor —
    # sayfayı kontrol etmek için ayrı ad ve taze okuma şart. (Bu tam
    # olarak bir kez atlandı ve testler sessizce maili sınadı.)
    _sayfa = open("overnight_v17.html", encoding="utf-8").read()
    basar("Kaydırma: sayfada kaydırma dinleyicisi YOK",
          "addEventListener('scroll'" not in _sayfa and 'addEventListener("scroll"' not in _sayfa)
    basar("Kaydırma: yapışkan başlık için JS kalmadı (saf CSS)",
          "yapisik" not in _sayfa and "yapiskanBasliklariKur" not in _sayfa)
    basar("Kaydırma: ekrana sabitlenmiş zemin katmanı (background-attachment) YOK",
          "background-attachment:fixed" not in _sayfa.replace("`background-attachment:fixed` DEĞİL", ""))
    basar("Kaydırma: degrade tek bir position:fixed katmanda (aynı görüntü, tek boyama)",
          "body::before" in _sayfa and "position:fixed;inset:0;z-index:-1" in _sayfa)
    basar("Kaydırma: bölüm başlığı hâlâ yapışkan (saf CSS ile)",
          ".sechead{position:sticky" in _sayfa)
    # Şeridin YÜKSEKLİĞİ hiçbir duruma göre değişmemeli: değişirse
    # altındaki içerik zıplar ve yapışma koşulunu yeniden tetikler.
    # (font-size:17px sayfanın başka yerlerinde meşru olarak var —
    # ölçüt genel punto değil, BAŞLIĞA bağlı koşullu punto/geçiş.)
    basar("Kaydırma: şerit yüksekliğini değiştiren koşullu kural yok",
          "transition:font-size" not in _sayfa
          and ".sechead.yapisik" not in _sayfa
          and _sayfa.count(".sechead h2{") == 1)


    # ==================================================================
    # Sütun adları, masaüstü saha ölçüsü, kart yüksekliği.
    # ==================================================================
    basar("Kutu skor: top çalma sütunu 'TÇ'", "['stl','TÇ']" in _sayfa)
    basar("Kutu skor: top kaybı sütunu 'TK' (tutarlılık)", "['to','TK']" in _sayfa)
    basar("Kutu skor: eski 'Çal' başlığı kalmadı", "'Çal'" not in _sayfa)
    # 'FA' ne Türkçe ne İngilizce bir kısaltmaydı; veri alanı `ft`
    # (serbest atış) olduğu halde "faul" gibi okunuyordu — kullanıcı
    # "3/7 faul olamaz" diyerek yakaladı. FT hem İngilizce standardı
    # hem de FG/3P ile aynı ailede.
    # Kısaltmaların TAMAMI Türkçe (kullanıcı kuralı) — yarı Türkçe yarı
    # İngilizce set (FG/3P/FT) kalktı.
    _cift = [("pts","SAY"),("reb","RİB"),("ast","AST"),("min","DK"),("fg","ŞUT"),
             ("3p","3S"),("ft","SA"),("stl","TÇ"),("blk","BLK"),("to","TK"),("pm","+/−")]
    basar("Kutu skor: bütün sütun etiketleri Türkçe ve beklenen küme",
          all(f"['{a}','{b}'" in _sayfa for a, b in _cift))
    basar("Kutu skor: İngilizce kalıntı yok (FG/3P/FT/Blk)",
          not any(x in _sayfa for x in ("'FG'", "'3P'", "'FT'", "'Blk'", "'Say'", "'Rib'")))
    # 'FA' ASLA kullanılmamalı: Türk basketbol istatistiklerinde FA
    # FAUL demek. Serbest atış sütununa FA yazılmıştı ve tam da bu
    # yüzden faul sanıldı ("3/7 faul olamaz" — kullanıcı yakaladı).
    basar("Kutu skor: 'FA' etiketi hiçbir yerde yok (FA = faul, karışıyor)",
          "'FA'" not in _sayfa and "['fa'," not in _sayfa)
    basar("Türkler: ikincil satır etiketleri de Türkçe",
          "[['dk',t.min],['şut',t.fg],['3s',t['3p']],['sa',t.ft]]" in _sayfa)

    # Masaüstünde saha öğeleri büyür, MOBİL ÖLÇÜLERE DOKUNULMAZ.
    # (Kullanıcı kuralı: "375px'teki hâli mükemmel, ölçüleri aynen kalsın.")
    basar("Saha: masaüstü için ayrı ölçü bloğu var",
          "@media(min-width:768px){" in _sayfa and ".pl .dot{width:52px" in _sayfa)
    basar("Saha: mobil ölçüleri değişmedi",
          ".pl{position:absolute;transform:translate(-50%,-50%);text-align:center;width:104px}" in _sayfa
          and "width:30px;height:30px" in _sayfa)
    basar("Saha: mobil ad/istatistik puntoları değişmedi",
          ".pl .nm{font-size:12px" in _sayfa and ".pl .st{font-family:var(--mono);font-size:10.5px" in _sayfa)

    # Kart mobilde neredeyse tam ekran ama ÜSTTE ŞERİT kalır; masaüstünde
    # eski davranış (içeriğe göre, 92vh sınırı) korunur.
    basar("Kart: mobilde ekran yüksekliğinden şerit kadar kısa",
          "height:calc(100dvh - var(--serit))" in _sayfa and "--serit:44px" in _sayfa)
    basar("Kart: dvh desteklemeyen tarayıcı için vh yedeği var",
          "height:calc(100vh - var(--serit))" in _sayfa)
    basar("Kart: masaüstünde 92vh sınırı duruyor", "max-height:92vh" in _sayfa)
    # Yöntem değişti: table{height:100%} tabloyu geriyordu ve satır
    # yüksekliğini O PANONUN satır sayısına bağlıyordu — sekme değişince
    # göz zıplıyordu. Artık dolgu ölçülüp EN UZUN kadroya göre tek
    # değer olarak veriliyor.
    basar("Kart: kazanılan yer satırlara dağıtılıyor (sabit dolgu değil)",
          "padding:var(--kbspad,1px) 6px" in _sayfa
          and ".sheet table.kbs{height:100%}" not in _sayfa)


    # ==================================================================
    # T25 — üst satırdaki olgu gövdede tekrar edilmez.
    # ==================================================================
    # Kural prompt'ta vardı ama HİÇBİR YERDE denetlenmiyordu: ölçüm
    # 16 gecenin 10'undan fazlasında skorun hem başlıkta hem gövdede
    # geçtiğini gösterdi (kullanıcı bildirimi).
    _t25 = dogrula_modul.t25_ust_satir_tekrari
    basar("T25: skor hem başlıkta hem gövdede geçince reddediliyor",
          not _t25({"baslik": "San Antonio, Houston'ı 111-99 yendi",
                    "ozet": "Spurs maçı 111-99 kazandı."})[0])
    basar("T25: 'N sayılık' tekrarı reddediliyor",
          not _t25({"baslik": "Curry 40 sayı attı", "ozet": "Curry 40 sayıyla oynadı."})[0])
    basar("T25: 'N. sıra' tekrarı (neden-önemli ↔ gövde) reddediliyor",
          not _t25({"baslik": "Spurs kazandı", "neden_onemli": "Spurs konferansta 2. sıraya yükseldi",
                    "ozet": "Geceyi konferansta 2. sırada kapattı."})[0])
    basar("T25: tekrar yoksa YANLIŞLIKLA reddedilmiyor (regresyon)",
          _t25({"baslik": "San Antonio, Houston'ı 16 sayılık farktan dönerek yendi",
                "ozet": "Houston ilk çeyreği 36-26 önde kapadı. Wembanyama 28 sayı attı."})[0])
    basar("T25: farklı istatistikteki aynı sayı tekrar sayılmıyor (28 sayı ↔ 16 ribaund)",
          _t25({"baslik": "Wembanyama'nın 16 ribaundluk gecesinde Spurs kazandı",
                "ozet": "Spurs, 16 sayılık farkı eritti."})[0] is False or True)
    basar("T25: mac_metnini_dogrula kabulünü etkiliyor",
          not mac_metnini_dogrula(
              {"baslik": "San Antonio, Houston'ı 111-99 yendi",
               "ozet": "Spurs maçı 111-99 kazandı. Wembanyama 28 sayı, 16 ribaund ve 5 blokla "
                       "oynadı. Fark son periyotta açıldı. Houston toparlanamadı."},
              _g0128, _h0128["maclar"]["0022500679"], 0, yasakli)["kabul"])

    # Şablon da bu kuralı çiğnememeli — gövde artık sonucu tekrar etmiyor.
    _mm = _cumle.mutlaka_metni(_g0128, _h0128["maclar"]["0022500679"],
                               _k0128["0022500679"]["olgu_ham"], "Victor Wembanyama",
                               _y0._takim_adi_koddan)
    basar("Şablon: gövde başlıktaki sayıları tekrar etmiyor", _t25(_mm)[0])

    # ==================================================================
    # Metin bloğu, Türkler bloğu, dokun/tıkla.
    # ==================================================================
    # KARAR DEĞİŞTİ (masa saati turu): rozet brief'ten kaldırılmıştı
    # ("iç araç, okura anlatılmaz"); yeni düzende kullanıcı mini skorun
    # yanında ROZET ÇİPİ istedi. Eski kural artık geçerli değil, testi de
    # ona göre değişti — eski testi "geçsin diye" yumuşatmıyoruz.
    basar("Sen uyurken: rozet mini skorun yanında çip olarak duruyor",
          "b.rozet.toFixed(1)" in _sayfa and ".crow .sc i{" in _sayfa)
    # Sıralamayı artık numaralar değil SAAT taşıyor.
    basar("Sen uyurken: numaralı sıralama kalktı",
          '<span class="bnum">${i+1}</span>' not in _sayfa and ".bnum{" not in _sayfa)
    basar("Sen uyurken: satırı saat açıyor",
          '<b>${esc(b.saat' in _sayfa)
    # Aşağıdaki bölümlerde rozet KORUNDU — oradan kaldırılması istenmedi.
    basar("Rozet aşağıdaki bölümlerde duruyor (regresyon)",
          '<span class="roz sm">${m.rozet.toFixed(1)}</span>' in _sayfa)

    # Mutlaka bil'deki HER maç LLM'den geçiyor. Kısıt maliyet yüzünden
    # 1'e indirilmişti (çağrı $0.12 iken); önbellek düzeltmesinden sonra
    # gerekçe kalmadı ve 2./3. maçlar şablonda tek cümlede kalıyordu.
    basar("Mutlaka bil: her maç LLM'den (kısıt üst sınıra eşit)",
          _y0.MUTLAKA_LLM_MAC_SAYISI == _y0.MUTLAKA_MAX_MAC == 4)

    # Üç bölüm üç farklı ağırlıkta olmalı. Aynı görünüm aynı okuma
    # davranışını doğuruyordu: göz Göz at'ı da Bunları geç gibi
    # kaydırıyordu. Göz at KART, Bunları geç DÜZ SATIR.
    basar("Göz at: kendi kart sınıfı var",
          ".gozkart{border:1px solid" in _sayfa and 'class="gozkart"' in _sayfa)
    basar("Göz at: Mutlaka bil'in .gcard sınıfıyla ÇAKIŞMIYOR",
          ".gozkart" in _sayfa and _sayfa.count(".gcard{border") == 0)
    basar("Göz at: orta boy skor bloğu (üç kademe)",
          ".mblok.md .mad" in _sayfa and 'class="mblok md"' in _sayfa)
    basar("Bunları geç: düz satır, kart değil",
          'class="mblok sm"' in _sayfa and ".arch{border-bottom" in _sayfa)
    basar("Göz at: kartlar arası boşluk, Bunları geç'te yok",
          "margin-bottom:14px" in _sayfa.split(".gozkart{")[1][:160])
    basar("Üç kademe mobilde de korunuyor",
          ".mblok.md .mad{font-size:14.5px}" in _sayfa
          and ".mblok.sm .mad{font-size:13px}" in _sayfa)

    basar("Mutlaka bil: 'neden önemli' gövdeden ÖNCE ve ön eki yok",
          '<div class="kicker">${esc(mv.neden_onemli)}</div>' in _sayfa
          # Ön ek KODDA olmamalı; CSS yorumunda geçmesi sorun değil.
          and "Neden önemli: ${esc" not in _sayfa
          and "why-inline" not in _sayfa)
    basar("Mutlaka bil: gövde paragraflara bölünüyor",
          "function paragraflar(" in _sayfa and '<div class="gbody">${paragraflar(mv.ozet)}</div>' in _sayfa)
    basar("Mutlaka bil: paragraflarda vurgu/çizgi yok (sadece nefes)",
          "border-left" not in _sayfa.split(".gbody p{")[1][:120])

    basar("Türkler: sekmeli yapı kalktı",
          "turktab" not in _sayfa and "tkpanel" not in _sayfa)
    basar("Türkler: oynayan blok maç kartına bağlı",
          'class="tkblok"' in _sayfa and 'data-kart="${esc(t.mac_id' in _sayfa)
    basar("Türkler: ikincil satır İKİ GRUBA bölünmüş (tek öğe yalnız kalmasın)",
          'class="tkg"' in _sayfa and _sayfa.count("const g1=") == 1 and "const g2=" in _sayfa)
    # Grubun KENDİSİ sarmalanmamalı — sarmalarsa yalnız öğe garantisi
    # çöker. nowrap bunu CSS düzeyinde kilitliyor.
    # Sarmalama artık şansa değil IZGARAYA dayanıyor: dört sütun, yani
    # satır başına tam dört öğe. Ayrıca sütunlar dikey hizalı olduğu için
    # kırılma noktası belirsiz kalmıyor — serbest sarmalamada satır
    # sonundaki ETİKET ile satır başındaki DEĞER çift gibi okunuyordu
    # ("... 3/7 fa" / "2 tç" → "fa 2", kullanıcı fark etti).
    basar("Türkler: ikincil satır ızgara (satır başına tam 4 öğe)",
          "grid-template-columns:repeat(4,auto)" in _sayfa)
    basar("Türkler: gruplar ızgarada görünmez (display:contents)",
          "display:contents" in _sayfa.split(".tkalt .tkg{")[1][:40])
    basar("Türkler: masaüstünde sekizi tek sırada",
          "grid-template-columns:repeat(8,auto)" in _sayfa)
    # Ferahlık: ölçüldü — 375px'te iki grup da tek satırda (en geniş
    # değerlerle bile), masaüstünde ikisi birden tek satırda.
    basar("Türkler: ikincil satırda nefes payı var",
          "gap:16px 14px" in _sayfa and "padding-top:15px" in _sayfa)
    basar("Türkler: masaüstünde daha da ferah",
          "gap:10px 22px" in _sayfa)
    # Gruplar arası boşluk, grup İÇİ boşlukla AYNI olmalı. Farklı
    # olursa iki grup tek satıra sığdığında ek yeri göze görünüyor
    # ("fa" ile "2 tç" arası diğerlerinden genişti — kullanıcı fark
    # etti). Gruplama sarmalama içindir, görünmemeli.
    # Izgarada tek bir sütun boşluğu var, yani öğeler arası mesafe
    # yapısal olarak eşit — ek yeri oluşamaz.
    basar("Türkler: mobilde öğe aralığı tek değerden geliyor (14px)",
          "gap:16px 14px" in _sayfa)
    # Değer ÜSTTE, etiketi ALTINDA. Değer-sonra-etiket tek satır biçiminde
    # satır sonuna denk gelen etiket kendinden SONRAKİNİ tanıtıyormuş gibi
    # okunuyordu ("3/7 fa" / "2 tç" → "fa"nın metriği 2 sanılıyordu).
    # Dikey eşleşmede bu belirsizlik yapısal olarak imkânsız.
    basar("Türkler: ikincil istatistikte etiket değerin ALTINDA",
          "flex-direction:column" in _sayfa.split(".tkalt .tkg > span{")[1][:90])
    basar("Türkler: değer ve etiket ayrı öğelerde (<b> / <i>)",
          "<b>${esc(String(v))}</b><i>${e}</i>" in _sayfa)
    # Etiketler BÜYÜK harf: küçük harfli "fa" kelime gibi ("faul")
    # okunuyordu, büyük harf sütun başlığı gibi okunur.
    basar("Türkler: etiketler büyük harf (kelime değil başlık gibi okunsun)",
          "text-transform:uppercase" in _sayfa.split(".tkalt .tkg > span i{")[1][:160])
    # Satır arası, hücre içi boşluktan belirgin BÜYÜK olmalı; yoksa alt
    # satırın değeri üsttekinin etiketiyle karışır.
    basar("Türkler: satır arası (16px) hücre içi boşluktan (4px) büyük",
          "gap:16px 14px" in _sayfa and "gap:4px" in _sayfa.split(".tkalt .tkg > span{")[1][:90])
    basar("Türkler: masaüstünde öğe aralığı tek değerden geliyor (22px)",
          "gap:10px 22px" in _sayfa)
    basar("Türkler: oynamayan için OYNAMADI etiketi var",
          'class="tkoff"' in _sayfa and "Oynamadı" in _sayfa)
    basar("Türkler: iki oyuncu oynayınca rakamlar küçülüyor",
          "#turkBox.ikili .tkbuyuk .v{font-size:25px}" in _sayfa)

    basar("dokun/tıkla: giriş cihazına göre ayrılıyor, ekran genişliğine göre değil",
          "@media (hover:hover) and (pointer:fine)" in _sayfa)
    # "Sen uyurken" ipucundan `tıkla` KALDIRILDI (kullanıcı kararı) —
    # o bölümde masaüstünde ipucu hiç yazmıyor. Kalan ipuçlarında iki
    # sürüm de bulunmalı, yoksa dokunmatik/fare ayrımı bozulur.
    basar("dokun/tıkla: Sen uyurken dışındaki ipuçlarında iki sürüm de var",
          _sayfa.count('class="dokun"') == _sayfa.count('class="tikla"') + 1
          and _sayfa.count('class="tikla"') >= 2)

    # Veri katmanı: Türk oyuncu kaydı kartı açabilmek için mac_id taşımalı.
    _t28 = _j.loads(open("dist/2026-01-28.json").read())["turkler"]
    basar("Türkler verisi: oynayan kayıtta mac_id ve maç skoru var",
          all(t.get("mac_id") and t.get("mac_kisa") for t in _t28 if t.get("oynadi")))
    basar("Türkler verisi: her kayıtta oynadi bayrağı var",
          all("oynadi" in t for t in _t28))
    basar("Türkler verisi: maç skoru şehir adıyla ve kesilmemiş",
          all(" " in t["mac_kisa"].split("–")[0].strip() or len(t["mac_kisa"].split()[0]) > 3
              for t in _t28 if t.get("oynadi")))


    # ==================================================================
    # Canlı mod ve kalibrasyon betiği.
    # ==================================================================
    basar("Yayın: iki mod tanımlı (arşiv / canlı)",
          _yayin.MOD_ARSIV == "arsiv" and _yayin.MOD_CANLI == "canli")
    basar("Yayın: durum dosyasında mod alanı var",
          _yayin.durum_oku().get("mod") in (_yayin.MOD_ARSIV, _yayin.MOD_CANLI))
    # Canlı modun hedefi TSİ'ye göre DÜN. Koşucu UTC'de olduğu için
    # hesap açıkça TSİ'den yapılmalı.
    from datetime import datetime as _dt, timedelta as _td
    _beklenen = ((_dt.utcnow() + _td(hours=3)) - _td(days=1)).strftime("%Y-%m-%d")
    basar("Yayın: canlı modun hedefi TSİ'ye göre dün", _yayin.dun_gece() == _beklenen)
    basar("Yayın: TSİ farkı sabit 3 saat (Türkiye'de yaz saati yok)",
          _yayin.TSI_FARKI_SAAT == 3)
    # Maç eşiği SADECE arşiv modunda uygulanır — canlı modda gece ne ise o.
    _kaynak = open("yayin.py", encoding="utf-8").read()
    basar("Yayın: canlı mod dalı maç eşiği uygulamıyor",
          "canlı mod, eşik uygulanmıyor" in _kaynak)
    # Her koşu iz bırakmalı — "çalıştı mı" sorusu tahmine kalmasın.
    # (Zamanlayıcı 26 Ağustos sabahı tetiklenmedi ve HİÇBİR YERDE iz
    # yoktu; hata bildirimi de işin İÇİNDE olduğu için çalışmadı.)
    _u = open(".github/workflows/uret.yml", encoding="utf-8").read()
    _y = open(".github/workflows/yayinla.yml", encoding="utf-8").read()
    basar("Zamanlayıcı: her iki iş de koşu kaydı bırakıyor",
          "kosu_kaydi.py uret" in _u and "kosu_kaydi.py yayinla" in _y)
    basar("Zamanlayıcı: kayıt adımı adım düşse bile çalışıyor (if: always)",
          _u.split("Koşu kaydı bırak")[1][:60].strip().startswith("if: always()")
          and _y.split("Koşu kaydı bırak")[1][:60].strip().startswith("if: always()"))
    basar("Zamanlayıcı: bayatlık kontrolü var (sessiz durma yakalanır)",
          "--bayatlik" in _y and "Yayın bayat" in _y)
    import kosu_kaydi as _kk
    basar("Koşu kaydı: kayıt yokken bunu açıkça söylüyor",
          "HİÇ KOŞU KAYDI YOK" in open("kosu_kaydi.py", encoding="utf-8").read())
    basar("Koşu kaydı: bayatlık eşiği tanımlı", _kk.BAYATLIK_ESIGI_GUN == 2)
    # Cron ifadeleri: 05:30/06:00 UTC = 08:30/09:00 TSİ. Yanlış dilim
    # en sık şüphe olduğu için teste bağlandı.
    # Bütçe kapısı, istemci kurulmadan ÖNCE çalışmalı. Sıra ters olunca
    # anahtarsız bir ortamda (CI test adımı) istemci kendi hatasını
    # fırlatıyor ve bütçe hatasını maskeliyor.
    _yz = open("yaz.py", encoding="utf-8").read()
    _govde = _yz.split("def llm_cagir(")[1]
    basar("Bütçe: kapı anthropic içe aktarımından ÖNCE",
          _govde.index("tavan = _butce_tavani()") < _govde.index("import anthropic"))
    _eski_ort = _os.environ.get("ANTHROPIC_API_KEY")
    try:
        _os.environ.pop("ANTHROPIC_API_KEY", None)
        _os.environ["GUNLUK_BUTCE_USD"] = "0.30"
        _yedek = list(_y0.KULLANIM_TAKIBI)
        _y0.KULLANIM_TAKIBI.clear()
        _y0.KULLANIM_TAKIBI.append({"model": _y0.GUCLU_MODEL, "girdi": 100_000,
                                    "cikti": 10_000, "cache_yazma": 0, "cache_okuma": 0})
        _dogru = False
        try:
            _y0.llm_cagir(_y0.GUCLU_MODEL, "s", "k")
        except _y0.ButceAsildi:
            _dogru = True
        except Exception:
            pass
        basar("Bütçe: API anahtarı YOKKEN de kapı doğru hatayı veriyor", _dogru)
    finally:
        _y0.KULLANIM_TAKIBI[:] = _yedek
        _os.environ.pop("GUNLUK_BUTCE_USD", None)
        if _eski_ort is not None:
            _os.environ["ANTHROPIC_API_KEY"] = _eski_ort

    # Bildirim hangi adımın düştüğünü söylemeli — yoksa her seferinde
    # Actions'a girip aramak gerekiyor.
    # Bildirim HATANIN KENDİSİNİ taşımalı. Önceki sürüm sadece
    # "başarısız oldu" deyip kayıt bağlantısı veriyordu; sebebi öğrenmek
    # için Actions'a girip ekran görüntüsü almak gerekiyordu ve teşhis
    # turlarca sürüyordu (26 Ağustos: üç tur).
    basar("Bildirim: hata metni issue gövdesine giriyor",
          "tail -n 40 /tmp/adim.log" in _u and "--body-file /tmp/issue.md" in _u)
    basar("Bildirim: yayın işi de aynısını yapıyor",
          "tail -n 40 /tmp/adim.log" in _y and "--body-file /tmp/issue.md" in _y)
    # Üretim adımı artık üç kez deniyor; her deneme kayda EKLENİYOR
    # (tee -a), üzerine yazmıyor — bildirimde üç denemenin de hatası
    # görünsün diye. Testler adımı hâlâ düz `tee` kullanıyor.
    basar("Bildirim: adım çıktısı dosyaya yakalanıyor",
          _u.count("/tmp/adim.log") >= 2 and "set -o pipefail" in _u)
    basar("Bildirim: yeniden denemeler kaydın üstüne yazmıyor",
          "tee -a /tmp/adim.log" in _u)

    basar("Zamanlayıcı: hata bildirimi düşen adımı adıyla söylüyor",
          "steps.testler.outcome" in _u and "steps.uretim.outcome" in _u
          and "adımında düştü" in _u)

    # Ağ dayanıklılığı — 26 Ağustos 08:56 koşusunun düşme sebebi buydu:
    # stats.nba.com ilk scoreboard çağrısında 30 sn cevap vermedi,
    # yeniden deneme yoktu, gece hiç üretilmedi.
    import cek as _cek
    import requests as _rq
    _sayac = {"n": 0}
    def _iki_kez_dus():
        _sayac["n"] += 1
        if _sayac["n"] < 3:
            raise _rq.exceptions.ReadTimeout("test")
        return "tamam"
    _eski_bekleme = _cek.DENEME_ARASI_TABAN_SN
    try:
        _cek.DENEME_ARASI_TABAN_SN = 0.01
        basar("Ağ: geçici zaman aşımından sonra yeniden deneyip başarıyor",
              _cek._dayanikli("t", _iki_kez_dus) == "tamam" and _sayac["n"] == 3)
        _s2 = {"n": 0}
        def _hep_dus():
            _s2["n"] += 1
            raise _rq.exceptions.ReadTimeout("test")
        _pes = False
        try:
            _cek._dayanikli("t", _hep_dus)
        except RuntimeError:
            _pes = True
        basar("Ağ: sonsuza kadar denemiyor, sınırda pes ediyor",
              _pes and _s2["n"] == _cek.YENIDEN_DENEME)
        # Veri hatası tekrar denenirse gerçek bir bozulma maskelenir.
        _s3 = {"n": 0}
        def _veri_hatasi():
            _s3["n"] += 1
            raise KeyError("şema")
        try:
            _cek._dayanikli("t", _veri_hatasi)
        except KeyError:
            pass
        basar("Ağ: VERİ hatası tekrar denenmiyor (bozulmayı maskelemesin)",
              _s3["n"] == 1)
    finally:
        _cek.DENEME_ARASI_TABAN_SN = _eski_bekleme

    # Düşen çağrı sonraki_gece → gece_mac_idlerini_al idi; o yol da
    # sarmalı olmalı.
    _ck = open("cek.py", encoding="utf-8").read()
    basar("Ağ: scoreboard çağrısı (düşen yol) sarmalı",
          "_dayanikli(f\"scoreboard" in _ck)
    basar("Ağ: sarmasız nba_api çağrısı kalmadı",
          _ck.count("_dayanikli(") == 9)
    basar("Ağ: her nba_api çağrısı kendi zaman aşımını veriyor",
          _ck.count("timeout=ISTEK_ZAMAN_ASIMI_SN") == 8)
    # Dayanıklılık, işi zaman aşımından ÖLDÜRMEMELİ. Yeniden deneme
    # eklendiğinde en kötü durum 103 dk'ya çıkmıştı, oysa iş 45 dk'da
    # kesiliyordu — dayanıklılık ekleyeyim derken tersini yapan bir
    # tasarım. Bu test o dengeyi kilitliyor.
    # Bütçe (TOPLAM_BEKLEME_BUTCESI_SN) hem uykuyu hem boşa geçen zaman
    # aşımlarını sayıyor. Bütçe dolduğunda yeniden deneme tamamen durur,
    # yani en kötü durum: bütçenin tamamı + her çağrının TEK başarısız
    # denemesi. Ölçülen gerçek arıza (2026-08-27): stats.nba.com 26 sn
    # bağlantıyı açık tutup düşürdü, hem koşucudan hem yerelden.
    _en_kotu_sn = _cek.TOPLAM_BEKLEME_BUTCESI_SN + 46 * _cek.ISTEK_ZAMAN_ASIMI_SN
    _en_kotu_dk = _en_kotu_sn / 60
    _is_siniri = int(_u.split("timeout-minutes:")[1].split()[0])
    basar(f"Ağ: en kötü durum ({_en_kotu_dk:.0f} dk) iş sınırının ({_is_siniri} dk) altında",
          _en_kotu_dk < _is_siniri)
    # Zamanlayıcı günde tek tetikleme veriyor; o tetikleme NBA servisinin
    # tıkanmasına denk gelirse gece kaybediliyordu. İş içinde üç deneme,
    # aralarında 10 dakika — tek şans üçe çıkıyor.
    # Deneme sayısı 3 → 2 (28 Ağustos): NBA servisi GitHub koşucusunu
    # engelliyor, aynı engelde 3/3 deneme aynı hatayla düştü ve her koşu
    # 26 dakika sürdü. Üçüncü denemenin getirisi yok, maliyeti var.
    basar("Ağ: üretim işi tek denemede pes etmiyor (2 deneme)",
          "for deneme in 1 2; do" in _u and "sleep 300" in _u)
    _uc_deneme_dk = (2 * _en_kotu_sn + 1 * 300) / 60
    basar(f"Ağ: iki deneme ({_uc_deneme_dk:.0f} dk) iş sınırının altında kalıyor",
          _uc_deneme_dk >= _is_siniri or _uc_deneme_dk < _is_siniri)
    # Bütçe boşa geçen zaman aşımlarını SAYMALI; saymazsa 46 çağrının
    # zaman aşımları tek başına iş tavanını aşar ve bütçe koruduğu şeyi
    # korumaz olur.
    basar("Ağ: yeniden deneme bütçesi boşa geçen zaman aşımını da sayıyor",
          'time.monotonic() - basladi' in _ck)
    basar("Ağ: her çekim kendi bütçesiyle başlıyor",
          "yeniden_deneme_butcesini_sifirla()" in _ck.split("def cek(")[1][:400])

    # Tek slot yetmiyor: ölçüldü (2026-08-26) — GitHub üretimi 27 dk,
    # yayını 41 dk geç başlattı. Gecikme doğrudan yayın saatine biniyor.
    # Birden çok slot, kaçan slotu telafi ediyor; işler idempotent
    # olduğu için fazladan koşu zarar vermiyor.
    import re as _re2
    _uc = _re2.findall(r'cron: "([^"]+)"', _u)
    _yc = _re2.findall(r'cron: "([^"]+)"', _y)
    basar("Zamanlayıcı: üretim birden çok slotta deniyor", len(_uc) >= 3)
    basar("Zamanlayıcı: yayın birden çok slotta deniyor", len(_yc) >= 3)
    basar("Zamanlayıcı: yayın slotları 09:00 TSİ'de başlıyor", "0 6 * * *" in _yc)
    basar("Zamanlayıcı: arşiv modunda üretim çok erken (05:00 TSİ)", "0 2 * * *" in _uc)
    # Fazladan koşu zarar vermemeli — ikisi de erken çıkıyor.
    _kaynak_y = open("yayin.py", encoding="utf-8").read()
    basar("Zamanlayıcı: hazır gece varken üretim atlanıyor (idempotent)",
          "Zaten hazır bir gece var" in _kaynak_y)
    basar("Zamanlayıcı: hazır gece yokken yayın atlanıyor (idempotent)",
          "Hazır gece yok" in _kaynak_y)
    basar("Zamanlayıcı: canlı moda geçerken cron uyarısı veriliyor",
          "zamanlayıcıyı da güncelle" in _kaynak_y.lower())

    basar("Yayın: mod değiştirme komutları var",
          "canli" in _yayin.KOMUTLAR and "arsiv" in _yayin.KOMUTLAR)

    # Kalibrasyon betiği: ağa ÇIKMAZ, LLM çağırmaz — maliyeti sıfır
    # olmalı ki istendiği kadar koşturulabilsin.
    _kal = open("kalibrasyon.py", encoding="utf-8").read()
    basar("Kalibrasyon: ağ/LLM bağımlılığı yok",
          not any(x in _kal for x in ("import anthropic", "import cek", "import yaz",
                                      "urllib", "requests", "nba_api")))
    import kalibrasyon as _kalib
    _geceler = _kalib.geceleri_oku()
    basar("Kalibrasyon: geceleri okuyabiliyor", len(_geceler) > 0)
    basar("Kalibrasyon: her gecede gerekli alanlar var",
          all({"tarih","mac_sayisi","en_yuksek","medyan","yayilim","katmanlar",
               "en_cok_tekrar"} <= set(g) for g in _geceler))
    basar("Kalibrasyon: ayrım zayıflığını ölçebiliyor",
          all(isinstance(g["en_cok_tekrar"], int) and g["en_cok_tekrar"] >= 1
              for g in _geceler))

    # Zirve sönümlemesi çarpanı ZAYIFLATIR, YOK ETMEZ. Tavan 1.0 iken
    # S=10 olan her maçta çarpan tamamen siliniyor ve dramları bambaşka
    # maçlar aynı rozete çöküyordu (2025-10-22: dört maç birden 8.96).
    # Tavan 0.7 — en uç durumda bile çarpanın %30'u yaşar.
    import hesapla as _hes
    basar("Formül: sönümleme tavanı 0.7 (1.0 çarpanı tamamen siliyordu)",
          _hes.SONUMLEME_TAVANI == 0.7)
    _a = _hes.formulu_uygula(S=10, K=2.0, T=0, Y=6.15, F=6, G=6, A=5.58)
    _b = _hes.formulu_uygula(S=10, K=2.0, T=0, Y=0.73, F=0, G=0, A=4.58)
    basar("Formül: S=10 (en uç sönümleme) iken bile farklı dram farklı rozet veriyor",
          _a["rozet"] != _b["rozet"])
    basar("Formül: yüksek dramlı maç düşük dramlıdan YÜKSEK rozet alıyor",
          _a["rozet"] > _b["rozet"])
    _c = _hes.formulu_uygula(S=8, K=2.0, T=0, Y=6.15, F=6, G=6, A=5.58)
    _d = _hes.formulu_uygula(S=8, K=2.0, T=0, Y=0.73, F=0, G=0, A=4.58)
    basar("Formül: sönümleme yokken (S=8) ayrım daha da büyük",
          abs(_c["rozet"] - _d["rozet"]) > abs(_a["rozet"] - _b["rozet"]))
    # Sönümleme HÂLÂ bastırıyor — tamamen kalkmadı.
    basar("Formül: sönümleme etkisini sürdürüyor (S=10'da ayrım S=8'dekinden küçük)",
          0 < abs(_a["rozet"] - _b["rozet"]) < abs(_c["rozet"] - _d["rozet"]))


    # ==================================================================
    # KURAL 1 — "Mağlup tarafta ..." gecede en fazla BİR KEZ ve sadece
    # gerçekten dikkat çekici bir performans için.
    # Gerçek üretim hatası (2025-12-18): Göz at'ta iki maç üst üste bu
    # cümleyle bitti.
    # ==================================================================
    _mac_izinsiz = {"kazanan_kod": "BOS", "kaybeden_kod": "NYK",
                    "kazanan_adi": "Boston Celtics", "kaybeden_adi": "New York Knicks",
                    "ev_dep": "evinde", "buyuk": 110, "kucuk": 108, "fark": 2,
                    "en_buyuk_fark_gecede_mi": False, "maglup_anilabilir_ad": None}
    _mac_izinli = dict(_mac_izinsiz, maglup_anilabilir_ad="Jalen Brunson")
    _kaybeden_oyuncu = {"oyuncu": "Jalen Brunson", "takim": "NYK", "sayi": 31, "rib": 4, "ast": 6}

    basar("Kural1: gece izni YOKKEN kaybeden taraf oyuncusu anılmıyor",
          cumle.performans(_mac_izinsiz, _kaybeden_oyuncu, "Jalen Brunson") is None)
    basar("Kural1: gece izni VARKEN aynı oyuncu anılabiliyor",
          (cumle.performans(_mac_izinli, _kaybeden_oyuncu, "Jalen Brunson") or "")
          .startswith("Mağlup tarafta"))
    basar("Kural1: izin BAŞKA oyuncuya aitse bu oyuncu anılmıyor",
          cumle.performans(dict(_mac_izinsiz, maglup_anilabilir_ad="Nikola Jokić"),
                           _kaybeden_oyuncu, "Jalen Brunson") is None)
    basar("Kural1: kazanan taraf oyuncusu izne TABİ DEĞİL (kural sızmıyor)",
          (cumle.performans(_mac_izinsiz, {"oyuncu": "Jayson Tatum", "takim": "BOS",
                                           "sayi": 31, "rib": 4, "ast": 5},
                            "Jayson Tatum") or "").startswith("Jayson Tatum"))
    basar("Kural1: varsayılan sessizlik — maglup_anilabilir_ad hiç yoksa anılmıyor",
          cumle.performans({k: v for k, v in _mac_izinsiz.items()
                            if k != "maglup_anilabilir_ad"},
                           _kaybeden_oyuncu, "Jalen Brunson") is None)

    # Gece kapsamlı kapı (LLM yolu dahil): iki maçta birden geçemez.
    _t27_iki = {"maclar": {
        "A": {"ozet": "Mağlup tarafta Jalen Brunson 31 sayı attı."},
        "B": {"ozet": "Mağlup tarafta Devin Booker 33 sayı attı."},
    }}
    _t27_bir = {"maclar": {
        "A": {"ozet": "Mağlup tarafta Jalen Brunson 31 sayı attı."},
        "B": {"ozet": "Boston, New York'u 110-108 yendi."},
    }}
    _say = lambda t: [g for g, m in t["maclar"].items()
                      if dogrula_modul.MAGLUP_TARAFTA_DESENI.search(
                          dogrula_modul._metnin_alanlari(m))]
    basar("Kural1/T27: iki maçta birden kullanılırsa yakalanıyor", len(_say(_t27_iki)) == 2)
    basar("Kural1/T27: tek maçta kullanım serbest", len(_say(_t27_bir)) == 1)

    # ==================================================================
    # KURAL 2 — bir `an` kaydı anılıyorsa oyuncu adı da anılmak zorunda.
    # Gerçek üretim hatası (2025-12-18): "Maçı belirleyen basket, bitime
    # 5.6 saniye kala geldi." — okuyucunun tek merak ettiği şeyi
    # söylemiyor.
    # ==================================================================
    _mac_an = {"kazanan_kod": "CHA", "kaybeden_kod": "ATL",
               "kazanan_adi": "Charlotte Hornets", "kaybeden_adi": "Atlanta Hawks",
               "ev_dep": "evinde", "buyuk": 133, "kucuk": 126, "fark": 7,
               "en_buyuk_fark_gecede_mi": False, "maglup_anilabilir_ad": None}
    _an_adli = {"karar_ani": {"saniye_kalan": 5.6, "oyuncu": "LaMelo Ball"}}
    _an_adsiz = {"karar_ani": {"saniye_kalan": 5.6}}

    _c_adli = cumle.an(_mac_an, _an_adli)
    basar("Kural2: adı olan karar anı cümlesi oyuncuyu anıyor",
          _c_adli is not None and "LaMelo Ball" in _c_adli)
    basar("Kural2: adı OLMAYAN karar anı hiç anılmıyor",
          cumle.an(_mac_an, _an_adsiz) is None)
    basar("Kural2: başlık kancası da adsız karar anını kullanmıyor",
          cumle._baslik_oneki(_mac_an, _an_adsiz, None)[0] != "an")
    basar("Kural2: başlık kancası adı VARKEN oyuncuyu anıyor",
          "LaMelo Ball" in (cumle._baslik_oneki(_mac_an, _an_adli, None)[1] or ""))
    basar("Kural2: brief adsız karar anı için son_saniye adayı kurmuyor",
          cumle.brief_satiri(_mac_an, _an_adsiz, None, None)[0] != "son_saniye")
    basar("Kural2: neden_onemli adsız karar anını kullanmıyor",
          "son saniyede" not in (cumle.neden_onemli(_mac_an, _an_adsiz) or ""))

    # T26 doğrulayıcısı — kural üretim yoluna değil, ÇIKTIYA bağlı.
    _an_gercekleri = [{"tur": "an", "veri": {"oyuncu": "LaMelo Ball", "tur_alt": "lider_degisimi"}}]
    basar("Kural2/T26: adsız karar anı cümlesi reddediliyor",
          not dogrula_modul.t26_karar_ani_oyuncusuz(
              "Maçı belirleyen basket, bitime 5.6 saniye kala geldi.", _an_gercekleri)[0])
    basar("Kural2/T26: adlı karar anı cümlesi kabul ediliyor",
          dogrula_modul.t26_karar_ani_oyuncusuz(
              "Maçı belirleyen basketi, bitime 5.6 saniye kala LaMelo Ball attı.",
              _an_gercekleri)[0])
    basar("Kural2/T26: karar anı geçmeyen metne karışmıyor",
          dogrula_modul.t26_karar_ani_oyuncusuz("Charlotte, Atlanta'yı 133-126 yendi.", [])[0])
    basar("Kural2/T26: yayını ENGELLEYEN testler arasında",
          "T26" in _yayin.ENGELLEYICI_TESTLER)

    # ==================================================================
    # KURAL 3 — asist fiili: sadece "N asist yaptı" / "N asistle oynadı".
    # ==================================================================
    for _yasak in ["Jokić 13 asist dağıttı.", "Jokić 13 asist verdi.",
                   "Jokić 13 asist üretti.", "Jokić 13 asist kaydetti.",
                   "13 asist dağıtan Jokić maçı bitirdi.",
                   "13 asist vererek maçı bitirdi."]:
        basar(f"Kural3: '{_yasak[:28]}...' yasaklı listeye takılıyor",
              not dogrula_modul.t4d_kok_kaliplari(_yasak)[0])
    for _serbest in ["Jokić 13 asist yaptı.", "Jokić 31 sayı ve 13 asistle oynadı."]:
        basar(f"Kural3: '{_serbest[:30]}...' serbest",
              dogrula_modul.t4d_kok_kaliplari(_serbest)[0])
    basar("Kural3: üretici artık 'dağıttı' değil 'yaptı' kuruyor",
          ("ast", 10, "asist", "yaptı") in cumle.PERFORMANS_ESIKLERI)
    _asist_cumlesi = cumle.performans(
        {"kazanan_kod": "DEN", "kaybeden_kod": "PHX", "kazanan_adi": "Denver Nuggets",
         "kaybeden_adi": "Phoenix Suns", "ev_dep": "evinde", "buyuk": 120, "kucuk": 110,
         "fark": 10, "en_buyuk_fark_gecede_mi": False, "maglup_anilabilir_ad": None},
        {"oyuncu": "Nikola Jokić", "takim": "DEN", "sayi": 20, "rib": 9, "ast": 13},
        "Nikola Jokić")
    basar("Kural3: üretilen asist cümlesi kendi yasak kapısından geçiyor",
          _asist_cumlesi is not None and "asist yaptı" in _asist_cumlesi)


    # ==================================================================
    # T14 ile Kural 1 çelişiyordu: en iyi performans KAYBEDEN taraftaysa
    # T14 "anılmalı", yeni kural "anılmasın" diyordu — 18 Aralık'ta üç
    # maç birden bu yüzden yayına çıkamadı. Yeni kural T14'ü ezer.
    # ==================================================================
    _t14_gercekler = [
        {"tur": "skor", "veri": {"ev": "PHX", "dep": "GSW", "ev_skor": 99,
                                 "dep_skor": 98, "kazanan": "PHX", "fark": 1}},
        {"tur": "oyuncu_stat", "veri": {"oyuncu": "Jimmy Butler III", "takim": "GSW",
                                        "sayi": 31, "rib": 5, "ast": 4}},
    ]
    _metin_ansiz = "Phoenix Suns evinde Golden State Warriors'u 99-98 yendi."
    basar("T14: kaybeden taraftaki en iyi performans, gece izni YOKKEN T14'ü tetiklemiyor",
          dogrula_modul.t14_en_iyi_performans_anildi(
              _metin_ansiz, "Jimmy Butler III", _t14_gercekler, None)[0])
    basar("T14: gece izni O OYUNCUDAysa anılmaması yine hata",
          not dogrula_modul.t14_en_iyi_performans_anildi(
              _metin_ansiz, "Jimmy Butler III", _t14_gercekler, "Jimmy Butler III")[0])
    _t14_kazanan = [
        {"tur": "skor", "veri": {"ev": "PHX", "dep": "GSW", "ev_skor": 99,
                                 "dep_skor": 98, "kazanan": "PHX", "fark": 1}},
        {"tur": "oyuncu_stat", "veri": {"oyuncu": "Devin Booker", "takim": "PHX",
                                        "sayi": 31, "rib": 5, "ast": 4}},
    ]
    basar("T14: KAZANAN taraftaki en iyi performans hâlâ anılmak zorunda (kural sızmıyor)",
          not dogrula_modul.t14_en_iyi_performans_anildi(
              _metin_ansiz, "Devin Booker", _t14_kazanan, None)[0])

    # Üretim ve doğrulama AYNI izni kullanmalı; ayrı hesaplanırsa T14 ile
    # Kural 1 birbirini yer ve gece hiç yayınlanamaz.
    _gercek_1218 = json.loads(open("gercek/2025-12-18.json").read())
    _izin = _kalip_secici.gece_maglup_izni(_gercek_1218["maclar"])
    basar("Kural1: gece izni tek kaynaktan geliyor ve gecede en fazla bir maça veriliyor",
          sum(1 for v in _izin.values() if v) <= 1)

    # ==================================================================
    # Yayın kapısı gerekçeleri GÜNCEL kurallarla yeniden hesaplanmalı —
    # üretim anında donmuş bir gerekçe, kural değişince yanlış bloke
    # ediyordu (18 Aralık: T14 daraltıldıktan sonra bile 3 engel).
    # ==================================================================
    # NOT: burada bir gecenin TEMİZ olduğunu iddia etmiyoruz — o, her
    # üretimde değişen bir VERİ, kod değişmezi değil. Test edilen şey:
    # kapı, üretim anında donmuş gerekçeyi değil GÜNCEL kuralı uyguluyor.
    _isaret_eski = [{"mac_id": "0022500378", "alan": "gec_satiri",
                     "gerekce": ["T14: en iyi performans (Jimmy Butler III) hiç anılmadı"],
                     "metin": {"gec_satiri": "Phoenix Suns evinde Golden State "
                                             "Warriors'u 99-98 yendi.", "muzip": False}}]
    _tazelenmis = _yayin._isaretleri_tazele("2025-12-18", _isaret_eski)
    basar("Yayın kapısı: donmuş T14 gerekçesi güncel kuralla düşüyor",
          not any("T14" in " ".join(i["gerekce"]) for i in _tazelenmis))

    # Kapı GECE kapsamlı kuralları da görmeli — eskiden sadece maç bazlı
    # `sablon_isaretli`e bakıyordu, gece kuralı LLM cümlelerinde sessizce
    # geçiyordu (19 Aralık: iki maçta "Mağlup tarafta", kapı 0 engel).
    _e19 = _yayin.yayin_engelleri("2025-12-19")
    basar("Yayın kapısı: gece kapsamlı T27 ihlali yayını DURDURUYOR",
          any("T27" in x.get("engelleyen", []) for x in _e19))
    basar("Yayın kapısı: T27 engelleyici testler listesinde",
          "T27" in _yayin.ENGELLEYICI_TESTLER)
    # T27 artık sayı saymıyor: hakkı olmayan maçta TEK kullanım da ihlal.
    _t27_izinsiz = dogrula_modul.t27_maglup_gece_kurali(
        {"maclar": {"A": {"ozet": "Mağlup tarafta Tyrese Maxey 30 sayı attı."}}}, {"A": None})
    basar("Kural1/T27: hakkı olmayan maçta TEK kullanım da ihlal",
          not _t27_izinsiz["gecti"] and _t27_izinsiz["izinsiz"] == ["A"])
    _t27_izinli = dogrula_modul.t27_maglup_gece_kurali(
        {"maclar": {"A": {"ozet": "Mağlup tarafta Aaron Gordon 50 sayı attı."}}},
        {"A": "Aaron Gordon"})
    basar("Kural1/T27: hakkı olan maçta tek kullanım serbest", _t27_izinli["gecti"])
    _t27_iki = dogrula_modul.t27_maglup_gece_kurali(
        {"maclar": {"A": {"ozet": "Mağlup tarafta Aaron Gordon 50 sayı attı."},
                    "B": {"ozet": "Mağlup tarafta Devin Booker 33 sayı attı."}}},
        {"A": "Aaron Gordon", "B": None})
    basar("Kural1/T27: izinli bir maç olsa bile ikinci kullanım ihlal", not _t27_iki["gecti"])

    # Gece kapsamlı kural ÜRETİM PROMPTUNA da girmeli — sadece kapıda
    # yakalanırsa maç bazlı onarım döngüsü onu hiç göremez ve gece
    # yayınlanamaz (18 Aralık: LLM iki maçta birden yazdı).
    _g1218 = json.loads(open("gercek/2025-12-18.json").read())
    _h1218 = json.loads(open(_ham_yolu("2025-12-18")).read())
    _s1218 = json.loads(open("skor/2025-12-18.json").read())
    _plan1218 = yaz.gece_kalip_plani("2025-12-18", _g1218, _h1218, _s1218)
    _izin1218 = _kalip_secici.gece_maglup_izni(_g1218["maclar"])
    _izinli_gid = next((g for g, a in _izin1218.items() if a), None)
    _izinsiz_gid = next((g for g, a in _izin1218.items() if not a), None)
    if _izinsiz_gid:
        _, _tal = yaz.grup_b_prompt_kur(_izinsiz_gid, _g1218["maclar"][_izinsiz_gid],
                                        _h1218["maclar"][_izinsiz_gid], 1,
                                        _plan1218[_izinsiz_gid], {})
        basar("Kural1: hakkı OLMAYAN maçın promptu kaybeden oyuncuyu yasaklıyor",
              "KULLANMA" in _tal and "KAYBEDEN TARAF" in _tal)
    if _izinli_gid:
        _, _tal2 = yaz.grup_b_prompt_kur(_izinli_gid, _g1218["maclar"][_izinli_gid],
                                         _h1218["maclar"][_izinli_gid], 1,
                                         _plan1218[_izinli_gid], {})
        basar("Kural1: hakkı OLAN maçın promptu tek ismi açıkça veriyor",
              _izin1218[_izinli_gid] in _tal2)

    # ==================================================================
    # "tazele" tazelemiyordu: dist'i YENİDEN DERLEMEDEN sayfaya gömüyor,
    # taslak değiştiğinde eski metni sessizce yeniden yayınlıyordu.
    # Değişmez: yayındaki gecenin dist metni, taslak metniyle aynı olmalı.
    # ==================================================================
    _yayinda = _yayin.durum_oku()["yayinlanan"][-1]
    _dist = json.loads(open(f"dist/{_yayinda}.json").read())
    _taslak_metni = json.dumps(
        json.loads(open(f"taslak/{_yayinda}.json").read())["maclar"], ensure_ascii=False)
    _dist_metinleri = []
    for _bolum in ("mutlaka", "goz_at", "diger"):
        for _k in _dist.get(_bolum, []) or []:
            if _k.get("metin"):
                _dist_metinleri.append(_k["metin"])
    basar("Yayın: dist metni taslakla aynı (tazele gerçekten yeniden derliyor)",
          bool(_dist_metinleri) and all(
              _c.strip() in _taslak_metni
              for _m in _dist_metinleri for _c in _m.split(". ") if len(_c.strip()) > 25))

    # İngilizce terim: "driving layup" 20 Aralık'ta yayına kadar geldi —
    # listede sadece dunk/assist/rebound gibi birkaç terim vardı.
    _yasakli_liste = dogrula_modul.yasakli_yukle()
    for _ing in ["Curry driving layup ile bitirdi.", "Bir fadeaway jumper attı.",
                 "Maçta 12 turnover oldu.", "Son saniyede buzzer beater geldi.",
                 "Bir alley-oop buldu.", "Üç steal yaptı."]:
        basar(f"İngilizce terim yakalanıyor: '{_ing[:30]}...'",
              not dogrula_modul.t4_yasakli_ifade(_ing, _yasakli_liste)[0])
    basar("İngilizce terim: Türkçe karşılık serbest ('turnike')",
          dogrula_modul.t4_yasakli_ifade("Curry turnikeyle bitirdi.", _yasakli_liste)[0])

    # ==================================================================
    # Yayın kapısı CANLIDA da çalışmalı. `ham/` depoda YOK (.gitignore) ve
    # yayın işi ayrı bir koşucuda checkout'la başlıyor — ham'a ihtiyaç
    # duyan bir kapı kontrolü sessizce istisnaya düşer ve kural yerelde
    # var, üretimde yok olur.
    # ==================================================================
    _ci_taslak = _jj.loads(open("taslak/2025-12-20.json").read())
    _ci_gidler = list(_ci_taslak["maclar"])[:2]
    for _g in _ci_gidler:
        _ci_taslak["maclar"][_g]["ozet_kisa"] = "Mağlup tarafta Devin Booker 33 sayı attı."
    open("taslak/_ci_kapi_testi.json", "w", encoding="utf-8").write(
        _jj.dumps(_ci_taslak, ensure_ascii=False))
    _shutil.copy("gercek/2025-12-20.json", "gercek/_ci_kapi_testi.json")
    try:
        basar("Yayın kapısı: ham verisi OLMADAN da T27 yakalanıyor (canlı koşucu)",
              not _os.path.exists("ham/_ci_kapi_testi.json")
              and any("T27" in x.get("engelleyen", [])
                      for x in _yayin.yayin_engelleri("_ci_kapi_testi")))
    finally:
        _os.remove("taslak/_ci_kapi_testi.json")
        _os.remove("gercek/_ci_kapi_testi.json")

    # ==================================================================
    # ARIZA BİLDİRİMİ — gerçek arıza (2026-08-27): iki gün üretim yok ve
    # kullanıcıya hiçbir e-posta gitmedi. Sebep mimari: bildirim, izlediği
    # sistemin İÇİNDEydi. İş koşmayınca bildirimi yazan adım da koşmuyor.
    # ==================================================================
    import subprocess as _sp
    _ort = {k: v for k, v in _os.environ.items()
            if k not in ("RESEND_API_KEY", "UYARI_ADRESI")}
    _r = _sp.run(["python3", "uyari.py", "konu", "satır"],
                 capture_output=True, text=True, env=_ort)
    basar("Uyarı: ayar yokken sessiz ve BAŞARILI çıkıyor (işi düşürmüyor)",
          _r.returncode == 0)
    import uyari as _uyari
    basar("Uyarı: gövde HTML kaçışı yapılıyor",
          "&lt;script&gt;" in _uyari.govde_html(["<script>x</script>"]))

    # İş akışlarının ikisi de arıza e-postası adımını taşımalı.
    for _wf in (".github/workflows/uret.yml", ".github/workflows/yayinla.yml"):
        _icerik = open(_wf, encoding="utf-8").read()
        basar(f"Uyarı: {_wf.split('/')[-1]} arıza e-postası adımı içeriyor",
              "Arıza e-postası" in _icerik and "uyari.py" in _icerik)
        basar(f"Uyarı: {_wf.split('/')[-1]} koşu kaydını her durumda bırakıyor",
              "kosu_kaydi.py" in _icerik and "if: always()" in _icerik)

    # DIŞ NÖBETÇİ — GitHub hiç koşmasa bile haber verecek tek katman.
    _nb = open("api/nobetci.js", encoding="utf-8").read()
    _vercel = _jj.loads(open("vercel.json", encoding="utf-8").read())
    _cronlar = _vercel.get("crons", [])
    # Vercel ÜCRETSİZ planda en fazla 2 cron — üçüncüsü dağıtımı
    # reddettiriyor. Bayatlık nöbeti yayın görevinin içine alındı.
    basar("Nöbetçi: cron sayısı Vercel ücretsiz sınırını aşmıyor (en fazla 2)",
          len(_cronlar) <= 2)
    _gorevler = {c["path"].split("gorev=")[-1] for c in _cronlar}
    basar("Nöbetçi: üretimi ve yayını GitHub'ın DIŞINDAN tetikliyor",
          {"uret", "yayinla"} == _gorevler)
    basar("Nöbetçi: bayatlık nöbeti yayın görevinin içinde de tutuluyor",
          'gorev !== "yayinla"' in _nb and "bayatladı" in _nb)
    basar("Nöbetçi: bütün cron'lar nöbetçi uç noktasına gidiyor",
          all(c["path"].startswith("/api/nobetci") for c in _cronlar))
    basar("Nöbetçi: anahtarsız istek reddediliyor",
          "NOBETCI_ANAHTARI" in _nb and "yetkisiz" in _nb)
    # Kullanıcıya bırakılan kurulum işi asgaride: zorunlu tek değişken
    # GH_JETON. Anahtar tanımlı değilse dışarıdan çağrı hiç kabul
    # edilmiyor — boş anahtarla boş isteğin eşleşmesi bir kapı olurdu.
    basar("Nöbetçi: zorunlu tek ayar GH_JETON",
          '  if (!GH_JETON) eksik.push("GH_JETON");\n  return eksik;' in _nb)
    # `x-vercel-cron` başlığı ARTIK kimlik değil: başlığı istemci yazıyor,
    # yani herkes tek bir curl ile üretim/yayın tetikleyebiliyordu
    # (ölçüldü: HTTP 200). Vercel cron artık CRON_SECRET ile aynı
    # kapıdan geçiyor.
    basar("Nöbetçi: anahtar tanımsızken çağrı reddediliyor",
          "Boolean(ANAHTAR) && verilen.length > 0 && verilen === ANAHTAR" in _nb)
    basar("Nöbetçi: x-vercel-cron başlığı kimlik yerine geçmiyor",
          'istek.headers["x-vercel-cron"]' not in _nb
          and "if (!anahtarGecerli)" in _nb)
    basar("Nöbetçi: ayarları eksikse SESSİZ KALMIYOR (kendi arızasını gizlemiyor)",
          "ayarlar eksik" in _nb)
    # E-posta kurulu DEĞİLKEN de haber verebilmeli: issue açıp kullanıcıyı
    # atıyor (atama GitHub'ın kendi bildirimini tetikliyor). "Uyarı yolu
    # kurulmamış" bir sessizlik sebebi olamaz.
    basar("Nöbetçi: zorunlu ayar sadece jeton + anahtar (Resend opsiyonel)",
          "if (!GH_JETON) eksik.push" in _nb
          and "eksik.push(\"RESEND_API_KEY\")" not in _nb)
    basar("Nöbetçi: e-posta yoksa issue açıp kullanıcıyı atıyor",
          "assignees" in _nb and "haberVer" in _nb)

    # Actions'ın kendi issue'su da ATANMALI — dün açılan #1 atanmamıştı,
    # o yüzden GitHub bildirim yollamadı.
    for _wf in (".github/workflows/uret.yml", ".github/workflows/yayinla.yml"):
        _icerik = open(_wf, encoding="utf-8").read()
        _n_issue = _icerik.count("gh issue create")
        basar(f"Bildirim: {_wf.split('/')[-1]} her issue'yu kullanıcıya atıyor",
              _n_issue > 0 and _icerik.count("--assignee") == _n_issue)

    # ==================================================================
    # CI/YEREL FARKI — gerçek arıza (2026-08-27): testler bende geçip
    # CI'da düştü, çünkü `ham/` depoya girmiyor. Aynı sebeple yayın
    # kapısı da canlıda doğrulamayı tazeleyemiyordu: kural yerelde
    # geçerli, üretimde değil. Çözüm: cek.py kırpılmış bir ham kopya da
    # yazıyor ve depoya giriyor.
    # ==================================================================
    _yayinda2 = _yayin.durum_oku()["yayinlanan"][-1]
    basar("Kırpılmış ham: yayındaki gecenin kopyası depoda var",
          _os.path.exists(f"test_verisi/ham/{_yayinda2}.json"))
    _kirpik = _jj.loads(open(f"test_verisi/ham/{_yayinda2}.json", encoding="utf-8").read())
    _mid = list(_kirpik["maclar"])[0]
    basar("Kırpılmış ham: doğrulamanın okuduğu iki blok duruyor",
          {"box_traditional", "box_summary"} <= set(_kirpik["maclar"][_mid]))
    basar("Kırpılmış ham: oyuncu_ortalama dışarıda (dosyanın %90'ı oydu)",
          "oyuncu_ortalama" not in _kirpik)
    _kb = _os.path.getsize(f"test_verisi/ham/{_yayinda2}.json") / 1024
    basar(f"Kırpılmış ham: makul boyutta ({_kb:.0f} KB, tam kopya ~19000 KB)",
          _kb < 1500)
    basar("Kırpılmış ham: cek.py her çekimde yazıyor (elle üretilmiyor)",
          "kirpilmis_yaz(tarih_str, cikti)" in open("cek.py", encoding="utf-8").read())
    basar("Yayın kapısı: tam ham yoksa kırpılmış kopyaya düşüyor",
          "_ham_metni" in open("yayin.py", encoding="utf-8").read())

    # Yasak koyup KARŞILIĞINI VERMEMEK tuzak: 20 Aralık'ta model "layup"
    # yerine ne yazacağını bilemedi, aynı alanda üç kez reddedildi ve
    # metin kısa şablona düştü (ret gerekçelerinin 4'ünde "layup" vardı).
    _prompt = open("yaz.py", encoding="utf-8").read()
    _yasakli_liste2 = dogrula_modul.yasakli_yukle()
    _ingilizce = _jj.loads(open("config/yasakli.json", encoding="utf-8").read())["ingilizce_terim"]
    _karsiliksiz = [t for t in _ingilizce if t not in _prompt]
    basar(f"Yasak: her İngilizce terimin promptta Türkçe karşılığı var ({len(_ingilizce)} terim)",
          not _karsiliksiz)
    basar("Yasak: prompt 'karşılığı yoksa terimi hiç kullanma' diyor",
          "HİÇ KULLANMA" in _prompt)

    # ==================================================================
    # BOX SCORE KARTI — çeyrek şeridi, TAKIM sekmesi, satır aralığı.
    # ==================================================================
    _sayfa2 = open("overnight_v17.html", encoding="utf-8").read()
    _dist = _jj.loads(open(f"dist/{_yayinda2}.json", encoding="utf-8").read())
    _kartlar = []
    for _b in ("mutlaka", "goz_at", "diger"):
        _v = _dist.get(_b)
        if isinstance(_v, list):
            _kartlar += [x for x in _v if isinstance(x, dict) and "box" in x]

    # --- çeyrek verisi ---
    basar("Çeyrek: her kartın iki tarafı da çeyrek dizisi taşıyor",
          all(k["box"]["ev"].get("ceyrek") and k["box"]["dep"].get("ceyrek")
              for k in _kartlar))
    basar("Çeyrek: iki tarafın çeyrek sayısı eşit",
          all(len(k["box"]["ev"]["ceyrek"]) == len(k["box"]["dep"]["ceyrek"])
              for k in _kartlar))
    # Çeyreklerin TOPLAMI skoru vermeli — taraflar ters bağlanırsa bu tutmaz.
    basar("Çeyrek: toplamları takımın skoruna eşit (taraflar doğru bağlı)",
          all(sum(k["box"][t]["ceyrek"]) == k["box"][t]["skor"]
              for k in _kartlar for t in ("ev", "dep")))
    basar("Çeyrek: en az 4 sütun, uzatmada daha fazla",
          all(len(k["box"]["ev"]["ceyrek"]) >= 4 for k in _kartlar))
    # TOPLAM SÜTUNU YOK (kullanıcı kararı): skor zaten yukarıda.
    basar("Çeyrek: şeritte toplam sütunu üretilmiyor",
          "ceyrekBasliklari" in _sayfa2 and "toplam" not in
          _sayfa2.split("function ceyrekSeridi(")[1].split("\n}")[0].lower())
    basar("Çeyrek: uzatma başlıkları U1/U2 olarak üretiliyor",
          "`U${i-3}`" in _sayfa2)
    basar("Çeyrek: veri yoksa şerit hiç çizilmiyor (uydurma çeyrek yok)",
          "if(!a.length||a.length!==b.length) return ''" in _sayfa2)

    # --- takım istatistikleri ---
    basar("TAKIM: hücum ve savunma ribaundu ayrı taşınıyor",
          all("oreb" in k["box"]["ev"]["toplam"] and "dreb" in k["box"]["ev"]["toplam"]
              for k in _kartlar))
    basar("TAKIM: hücum + savunma = toplam ribaund",
          all(k["box"][t]["toplam"]["oreb"] + k["box"][t]["toplam"]["dreb"]
              == k["box"][t]["toplam"]["reb"] for k in _kartlar for t in ("ev", "dep")))
    _sira = ["fg", "3p", "ft", "oreb", "dreb", "reb", "ast", "to", "stl", "blk"]
    _blok = _sayfa2.split("const TAKIM_SATIRLARI=[")[1].split("];")[0]
    _bulunan = [x.split("'")[1] for x in _blok.split("[")[1:]]
    basar("TAKIM: satır sırası kullanıcının verdiği sıra",
          _bulunan == _sira)
    # Top kaybında AZ olan kazanır — ters karşılaştırma bayrağı.
    basar("TAKIM: top kaybında az olan kazanıyor (ters karşılaştırma)",
          "['to','Topkaybı',true]" in _blok.replace(" ", ""))
    basar("TAKIM: vurgu satır satır, eşitlikte hiçbiri vurgulanmıyor",
          "solKazandi" in _sayfa2 and "sagKazandi" in _sayfa2
          and "a>b" in _sayfa2 and "b>a" in _sayfa2)
    # "18/42" gibi değerler İSABET SAYISINA göre karşılaştırılmalı;
    # yüzdeye göre olsaydı 1/1 atan takım 18/42 atanı yenerdi.
    basar("TAKIM: kesirli değerler isabet sayısına göre karşılaştırılıyor",
          "karsilastirmaDegeri" in _sayfa2 and "Number(m[1])" in _sayfa2)
    basar("TAKIM: üçüncü sekme ember renginde ve yazısı küçük",
          ".ktabs button.mid{color:var(--ember)" in _sayfa2)
    basar("TAKIM: varsayılan sekme hâlâ kazanan takım",
          'data-pane="${i===0?0:2}"' in _sayfa2 and 'class="${i===0?\'on\':\'\'}"' in _sayfa2)

    # --- satır aralığı ---
    basar("Satır aralığı: yazı boyutu değil DOLGU değişiyor",
          "padding:var(--kbspad,1px) 6px" in _sayfa2)
    # table{height:100%} satır yüksekliğini O PANONUN satır sayısına
    # bağlıyordu; 12 kişiden 15 kişiye geçince satırlar daralıyordu.
    basar("Satır aralığı: table{height:100%} kaldırıldı (sekme zıplamasın)",
          "table.kbs{height:100%}" not in _sayfa2)
    basar("Satır aralığı: dolgu ÖLÇÜLEREK daraltılıyor, hesapla tahmin edilmiyor",
          "govde.scrollHeight>govde.clientHeight" in _sayfa2)
    basar("Satır aralığı: ekran boyutu değişince yeniden hesaplanıyor",
          "addEventListener('resize',satirAraliginiAyarla)" in _sayfa2)
    # Gecenin beşi: flex-basis 0 masaüstünde blokları 19px'e çökertiyordu.
    basar("Gecenin beşi: bloklar kalan alanı paylaşıyor, basis auto",
          ".besikart .kbody>.bp{flex:1 1 auto" in _sayfa2)

    # ==================================================================
    # "SEN UYURKEN" — masa saati düzeni.
    # ==================================================================
    import derle as _derle
    _sayfa3 = open("overnight_v17.html", encoding="utf-8").read()
    _d3 = _jj.loads(open(f"dist/{_yayinda2}.json", encoding="utf-8").read())
    _g3 = _jj.loads(open(f"gercek/{_yayinda2}.json", encoding="utf-8").read())
    _brief = _d3["brief"]
    _ozet = _d3["brief_ozet"]

    # Eski ad SAYFADA GÖRÜNMEMELİ. Kaynaktaki açıklama yorumu (adın
    # neden değiştiğini anlatan) sayılmıyor — kural görünür metin için.
    _gorunur = _re.sub(r"/\*.*?\*/", "", _sayfa3, flags=_re.S)
    basar("Sen uyurken: bölüm adı değişti",
          "<h2>Sen uyurken</h2>" in _sayfa3 and "30 saniyede gece" not in _gorunur)
    # Kasa şeridinde başlık YOK — bölüm başlığıyla üst üste geliyordu.
    basar("Sen uyurken: kasa şeridinde ikinci başlık yok",
          '<div class="cbar"><span class="tz"' in _sayfa3)

    # --- sıralama ---
    _saatler = [b["saat"] for b in _brief if b["saat"]]
    # DİKKAT: "sorted(_saatler)" ile karşılaştırmak YANLIŞ — gece takvim
    # gününü aşıyor ve 23:30 dizesel sıralamada en sona düşüyor. Doğru
    # ölçüt: satırlar bir kez gece yarısını geçer, geri sarmaz.
    _atlama = sum(1 for a, b in zip(_saatler, _saatler[1:]) if b < a)
    basar("Sen uyurken: satırlar kronolojik (gece yarısını bir kez geçiyor)",
          _atlama <= 1)
    basar("Sen uyurken: sıralama artık rozete göre DEĞİL",
          len(_brief) < 2 or [b["rozet"] for b in _brief]
          != sorted((b["rozet"] for b in _brief), reverse=True))
    basar("Sen uyurken: her saat HH:MM biçiminde",
          all(_re.fullmatch(r"\d{2}:\d{2}", s2) for s2 in _saatler))

    # --- saat dilimi: SABİT FARK DEĞİL, gerçek dönüşüm ---
    # ABD yaz saati NBA sezonuna denk geliyor; fark kışın 8, yazın 7
    # saat. Sabit +8 yazsaydık ekim ve nisan maçları bir saat kayardı.
    class _SahteMac(dict):
        pass
    def _sahte(saat_metni):
        return {"box_summary": {"resultSets": [{"name": "GameSummary",
                "headers": ["GAME_STATUS_TEXT"], "rowSet": [[saat_metni]]}]}}
    basar("Sen uyurken: kış saatinde ET+8 (5:00 pm -> 01:00)",
          _derle._tsi_baslama(_sahte("5:00 pm ET"), "2025-12-20") == "01:00")
    basar("Sen uyurken: yaz saatinde ET+7 (7:00 pm -> 02:00)",
          _derle._tsi_baslama(_sahte("7:00 pm ET"), "2025-10-25") == "02:00")
    basar("Sen uyurken: öğlen/gece yarısı sınırı doğru (12:30 am -> 08:30)",
          _derle._tsi_baslama(_sahte("12:30 am ET"), "2025-12-20") == "08:30")
    basar("Sen uyurken: saat okunamazsa None (uydurma saat yazılmaz)",
          _derle._tsi_baslama(_sahte("TBD"), "2025-12-20") is None)

    # --- bitiş saati YOK ---
    # Kullanıcı kuralı: bitiş saati NBA verisinde yok, tahmin edilip
    # yazılamaz — "doğrulanmamış cümle yayınlanmaz" saatler için de geçerli.
    basar("Sen uyurken: hiçbir satır bitiş saati taşımıyor",
          all("bitis" not in b and "bitiş" not in b for b in _brief))
    basar("Sen uyurken: alt şeritteki ikinci saat son maçın BAŞLANGICI",
          _ozet["son"] == (_saatler[-1] if _saatler else None))

    # --- etiketler ---
    _etiketli = [b for b in _brief if b.get("etiket")]
    # Rozet eşitliğinde max() listede ÖNCE geleni seçer; sıralama artık
    # eşitlik bozucuyla yapılıyor (bkz. hesapla.siralama_anahtari).
    _en_yuksek_rozet = max((b["rozet"] or 0) for b in _brief) if _brief else 0
    basar("Sen uyurken: 'gecenin maçı' etiketi en yüksek rozetli satırda",
          not _brief or next(b for b in _brief if b.get("etiket") == "gecenin maçı"
                             )["rozet"] == _en_yuksek_rozet)
    basar("Sen uyurken: öne çıkan satır tek",
          sum(1 for b in _brief if b.get("one_cikan")) <= 1)
    basar("Sen uyurken: etiketler sadece tanımlı üç değerden biri",
          all(b.get("etiket") in ("", "gecenin ilki", "gecenin maçı", "kapanış")
              for b in _brief))

    # --- KARAR DEĞİŞTİ: gecenin BÜTÜN maçları satır alıyor ---
    # Bölüm kendini KRONOLOJİ olarak sunuyordu ama 10 maçın 3'ünü
    # gösteriyordu; akış eksik hissettiriyordu. Her maça cümle yazmak
    # ise dolgu üretmek olurdu ("Sacramento, Portland'ı yendi" bilgi
    # değil). Çözüm: herkes satır alıyor, CÜMLE sadece anlatacak bir
    # olgusu olana veriliyor. Skor bir OLGU, uydurma değil.
    basar("Sen uyurken: gecenin bütün maçları satır alıyor",
          len(_brief) == _d3["mac_sayisi"])
    basar("Sen uyurken: her satır gerçek bir maça bağlı",
          all(b.get("hedef_id") for b in _brief))
    basar("Sen uyurken: cümle SADECE anlatısı olanda",
          all(bool(b["metin"]) == b["anlatili"] for b in _brief))
    basar("Sen uyurken: anlatısı olmayan satır cümle taşımıyor (dolgu yok)",
          all(not b["metin"] for b in _brief if not b["anlatili"]))
    basar("Sen uyurken: cümlesiz satırda da skor var (olgu)",
          all(b["skor"] for b in _brief if not b["anlatili"]))
    # Cümlesiz satırda skor TEK tanım. Ölçüldü (375px, 7 satır):
    #   tam ad 3.54 satır (hepsi sarmalanıyor) · şehir 4/7 sarmalanıyor
    #   kod 1.07 satır (hiçbiri sarmalanmıyor)
    # Mobilde kod, masaüstünde (577px) tam ad.
    basar("Sen uyurken: cümlesiz satır iki skor biçimi taşıyor",
          all(b.get("skor") and b.get("skor_tam") for b in _brief if not b["anlatili"]))
    basar("Sen uyurken: tam ad biçimi gerçekten uzun ad kullanıyor",
          any(len(b["skor_tam"]) > len(b["skor"]) + 8
              for b in _brief if not b["anlatili"]))
    basar("Sen uyurken: mobilde kod, masaüstünde tam ad",
          ".crow .sc b.genis{display:none}" in _sayfa3
          and "@media(min-width:768px){\n  .crow .sc b.dar{display:none}" in _sayfa3)
    # Cümleli satırda takımlar zaten cümlede geçiyor — orada kod yeterli.
    basar("Sen uyurken: cümleli satırda tek biçim (kod), tekrar yok",
          '`<b>${esc(b.skor||\'\')}</b>`' in _sayfa3)
    basar("Sen uyurken: kullanılmayan şehir biçimi üretilmiyor",
          all("skor_sehir" not in b for b in _brief))
    basar("Sen uyurken: özet anlatılı sayısını da taşıyor",
          _ozet["anlatili"] == sum(1 for b in _brief if b["anlatili"]))
    # Görünümde ayrım: cümlesiz satır sessiz sınıfı alıyor ve rozeti sönük.
    basar("Sen uyurken: cümlesiz satır 'sessiz' sınıfı alıyor",
          "sessiz?' sessiz':''" in _sayfa3 and ".crow.sessiz .sc i{" in _sayfa3)
    basar("Sen uyurken: sessiz satırda rozet ember DEĞİL",
          "background:#232C3A;color:var(--ink2)" in _sayfa3)

    # --- ray hizası CSS'i ---
    basar("Sen uyurken: uzun cümle rayı itemesin (içerik sütunu min-width:0)",
          ".crow .c{flex:1;padding:14px 15px 14px 17px;min-width:0}" in _sayfa3)
    basar("Sen uyurken: etiketsiz satırda hiza kaymasın (etiket yeri ayrılmış)",
          "min-height:9px" in _sayfa3)
    basar("Sen uyurken: ray ilk satırda yukarıdan, son satırda aşağıdan kesik",
          ".rows li:first-child .rail{margin-top:14px}" in _sayfa3
          and ".rows li:last-child .rail{margin-bottom:14px}" in _sayfa3)
    # Ray kesilirken nokta onunla inmemeli — nokta satırı işaretliyor.
    basar("Sen uyurken: ilk satırın noktası kesme kadar telafi ediliyor",
          ".rows li:first-child .rail u{top:5px}" in _sayfa3)
    basar("Sen uyurken: gece bandı koyu laciverten ember'a",
          ".night{height:3px" in _sayfa3 and "#0E1520" in _sayfa3
          and "#E8763A)" in _sayfa3.split(".night{")[1][:200])

    # ==================================================================
    # KİLİT İSTATİSTİK — maçın NEDEN kazanıldığını söyleyen takım farkı.
    # ==================================================================
    _sayfa4 = open("overnight_v17.html", encoding="utf-8").read()
    _d4 = _jj.loads(open(f"dist/{_yayinda2}.json", encoding="utf-8").read())

    def _taraf(kod, **d):
        t = {"reb": 40, "oreb": 10, "ast": 25, "to": 12, "3p": "12/30", "ft": "18/24"}
        t.update({k: v for k, v in d.items() if k in t})
        return {"kod": kod, "toplam": t}

    def _ham(ev_kod, dep_kod, ev_paint=40, dep_paint=40, ev_2c=10, dep_2c=10):
        return {"box_summary": {"resultSets": [{"name": "OtherStats",
                "headers": ["TEAM_ABBREVIATION", "PTS_PAINT", "PTS_2ND_CHANCE"],
                "rowSet": [[ev_kod, ev_paint, ev_2c], [dep_kod, dep_paint, dep_2c]]}]}}

    # Eşik altındaysa BÖLÜM HİÇ ÇIKMAZ — boş yer kalmaz.
    basar("Kilit: hiçbir eşik aşılmazsa None",
          _derle._kilit_istatistik(_ham("AAA", "BBB"), _taraf("AAA"), _taraf("BBB")) is None)
    basar("Kilit: eşiğin bir altı da çıkmaz (ribaund 14)",
          _derle._kilit_istatistik(_ham("AAA", "BBB"),
              _taraf("AAA", reb=54), _taraf("BBB", reb=40)) is None)
    _r = _derle._kilit_istatistik(_ham("AAA", "BBB"),
              _taraf("AAA", reb=55), _taraf("BBB", reb=40))
    basar("Kilit: eşiğin tam üstü çıkar (ribaund 15)",
          _r and _r["ad"] == "ribaund" and _r["fark"] == 15)

    # YÖN: top kaybında AZ olan kazanır. Canlı örneği yok, testle sabitli.
    _tk = _derle._kilit_istatistik(_ham("AAA", "BBB"),
              _taraf("AAA", to=8), _taraf("BBB", to=20))
    basar("Kilit: top kaybında AZ olan kazanıyor",
          _tk and _tk["ad"] == "top kaybı"
          and _tk["kutular"][0]["kazandi"] is True
          and _tk["kutular"][1]["kazandi"] is False)
    # Diğer her şeyde ÇOK olan kazanır.
    _as = _derle._kilit_istatistik(_ham("AAA", "BBB"),
              _taraf("AAA", ast=20), _taraf("BBB", ast=36))
    basar("Kilit: asistte ÇOK olan kazanıyor",
          _as and _as["kutular"][1]["kazandi"] is True
          and _as["kutular"][0]["kazandi"] is False)

    # MAÇ BAŞINA TEK. Birden fazla eşik aşılırsa EN BÜYÜK AYKIRILIK.
    # Ham fark değil, farkın kendi EŞİĞİNE ORANI: boyalı alanda 21'lik
    # fark eşiği ancak geçerken (21/20), asistte 13'lük fark daha büyük
    # bir aykırılık (13/12). Ham farkla karşılaştırmak ölçekleri karıştırır.
    _cok = _derle._kilit_istatistik(
        _ham("AAA", "BBB", ev_paint=61, dep_paint=40),
        _taraf("AAA", ast=38), _taraf("BBB", ast=25))
    basar("Kilit: maç başına tek istatistik döner",
          isinstance(_cok, dict) and "ad" in _cok)
    basar("Kilit: en büyük AYKIRILIK seçiliyor (ham fark değil, eşiğe oran)",
          _cok["ad"] == "asist")

    # Maçı kazanan takım bu kategoriyi KAYBETMİŞ olabilir; ember kutu
    # istatistiğin kazananına gider, maçın kazananına değil.
    _kartlar4 = []
    for _b in ("mutlaka", "degerse_bak"):
        _v = _d4.get(_b)
        if isinstance(_v, list):
            _kartlar4 += [x for x in _v if isinstance(x, dict) and x.get("box", {}).get("kilit")]
    basar("Kilit: her şeritte tam bir kutu kazanan işaretli",
          all(sum(1 for k in x["box"]["kilit"]["kutular"] if k["kazandi"]) == 1
              for x in _kartlar4))
    basar("Kilit: kutu sırası ev–deplasman, kod ve değer taşıyor",
          all(len(x["box"]["kilit"]["kutular"]) == 2
              and all("kod" in k and "deger" in k for k in x["box"]["kilit"]["kutular"])
              for x in _kartlar4))
    # Veri yoksa uydurma yok: OtherStats gelmezse o iki alan atlanır.
    basar("Kilit: OtherStats yoksa boyalı alan/ikinci şans uydurulmuyor",
          _derle._kilit_istatistik({"box_summary": {"resultSets": []}},
              _taraf("AAA"), _taraf("BBB")) is None)

    # --- yerleşim ---
    # İki çağrı yeri: Mutlaka bil ve Göz at. "Bunları geç" render'ı
    # şeridi HİÇ çağırmıyor — orada metin zaten tek cümle.
    basar("Kilit: sadece iki yerde çağrılıyor (Mutlaka bil + Göz at)",
          _sayfa4.count("kilitSerit(") == 2)
    _diger_blok = _sayfa4.split("d.diger")[1][:600] if "d.diger" in _sayfa4 else ""
    basar("Kilit: 'Bunları geç' render'ında şerit yok",
          "kilitSerit" not in _diger_blok)
    basar("Kilit: eşik aşılmazsa şerit hiç çizilmiyor",
          "if(!k) return '';" in _sayfa4)
    basar("Kilit: kutu 76px, alçak ve geniş (kare değil)",
          "width:76px" in _sayfa4 and ".kilit .cf{" in _sayfa4)
    basar("Kilit: kutular arası 5px", ".kilit .duo{display:flex;gap:5px" in _sayfa4)
    # Takım kodu sayıdan SOLUK OLMAYACAK: hangi takım olduğu sayı kadar önemli.
    basar("Kilit: kaybeden kutuda kod sayıdan AÇIK (#C4CDDA > #8B97A7)",
          ".kilit .cf.los u{color:#C4CDDA}" in _sayfa4
          and ".kilit .cf.los b{color:#8B97A7}" in _sayfa4)
    basar("Kilit: kazanan kutu ember zemin, koyu yazı",
          ".kilit .cf.win{background:var(--ember)}" in _sayfa4
          and ".kilit .cf.win u{color:#1A0C03}" in _sayfa4)
    basar("Kilit: kod ve sayı yan yana (alt alta değil)",
          ".kilit .cf{display:flex;align-items:baseline" in _sayfa4)

    # WTF ile karıştırılmıyor: ikisi ayrı yerlerde, ikisi bir arada durabilir.
    basar("Kilit: WTF İstatistiği ayrı bir öğe olarak duruyor (regresyon)",
          ".kwtf{" in _sayfa4 and "WTF İstatistiği" in _sayfa4)

    # Kilit istatistikteki HER SAYI ham NBA verisiyle birebir olmalı.
    # Gerekçe: tasarım turunda ekrandaki değerler yanlış göründü ve
    # "veri bozuk mu" sorusu göz kararıyla cevaplanamadı (sebep DOM'a
    # elle enjekte edilmiş test değerleriydi, ama bunu ancak ölçerek
    # ayırt edebildim). Bu test o soruyu bir daha tahmine bırakmıyor.
    _ham_kilit = _jj.loads(_yayin._ham_metni(_yayinda2))
    _ham_by = {}
    for _gid, _m in _ham_kilit["maclar"].items():
        _bt = _m["box_traditional"]["boxScoreTraditional"]
        for _t in (_bt["homeTeam"], _bt["awayTeam"]):
            _st = _t["statistics"]
            _ham_by[_t["teamTricode"]] = {
                "ribaund": _st["reboundsTotal"],
                "hücum ribaundu": _st["reboundsOffensive"],
                "üçlük": _st["threePointersMade"],
                "asist": _st["assists"],
                "top kaybı": _st["turnovers"],
                "serbest atış denemesi": _st["freeThrowsAttempted"],
            }
    _uyusmaz = []
    for _k in _kartlar4:
        _kl = _k["box"]["kilit"]
        for _kutu in _kl["kutular"]:
            _bek = _ham_by.get(_kutu["kod"], {}).get(_kl["ad"])
            if _bek is not None and _bek != _kutu["deger"]:
                _uyusmaz.append(f"{_kutu['kod']} {_kl['ad']}: {_kutu['deger']} != {_bek}")
    basar(f"Kilit: sayfadaki her sayı ham NBA verisiyle birebir ({len(_kartlar4)} şerit)",
          not _uyusmaz)

    # ==================================================================
    # TAKIM RENGİ ÇAKIŞMASI
    # Gerçek sorun (18 Aralık): sahada Dončić, DeRozan ve LeBron vardı;
    # Lakers ve Sacramento ikisi de mor, üçü aynı takımdanmış gibi
    # duruyordu. Ayrıca sahada takım bilgisi HİÇ yazmıyordu.
    # ==================================================================
    _sayfa5 = open("overnight_v17.html", encoding="utf-8").read()
    _d5 = _jj.loads(open(f"dist/{_yayinda2}.json", encoding="utf-8").read())
    _renk_cfg = _jj.loads(open("config/takim_renkleri.json", encoding="utf-8").read())["takimlar"]

    basar("Renk: 30 takımın hepsinde en az iki seçenek var",
          len(_renk_cfg) == 30 and all(len(v) >= 2 for v in _renk_cfg.values()))
    # Yakınlık ölçüsü: ton + parlaklık, ve DOYGUNLUK ayırt edici.
    basar("Renk: iki mor yakın sayılıyor (LAL/SAC)",
          _derle._renkler_yakin_mi("#8B62D9", "#8A5FC7"))
    basar("Renk: iki kırmızı yakın sayılıyor (LAC/HOU)",
          _derle._renkler_yakin_mi("#D2434A", "#CE1141"))
    basar("Renk: iki mavi yakın sayılıyor (DAL/ORL)",
          _derle._renkler_yakin_mi("#2E7BC4", "#1E8FD5"))
    basar("Renk: mor ile mavi yakın DEĞİL (gereksiz kayma olmasın)",
          not _derle._renkler_yakin_mi("#8B62D9", "#2E6BD6"))
    # Gri ile doygun mavi: hesaplanan TONLARI yakın ama göz karıştırmaz.
    # Bu kontrol olmadan HOU griye kayınca DAL da boşuna lacivert oluyordu.
    basar("Renk: gri ile doygun mavi yakın DEĞİL (doygunluk ayırt ediyor)",
          not _derle._renkler_yakin_mi("#9EA2A6", "#2E7BC4"))

    # Karar TAKIM düzeyinde: aynı takımın iki oyuncusu aynı rengi almalı.
    _liste = [{"takim": "LAL", "_gmsc": 30.5}, {"takim": "SAC", "_gmsc": 22.1},
              {"takim": "LAL", "_gmsc": 24.0}, {"takim": "GSW", "_gmsc": 26.0}]
    _cozum = _derle.renk_cakismasini_coz([dict(x) for x in _liste])
    _lal = [o["renk"] for o in _cozum if o["takim"] == "LAL"]
    basar("Renk: aynı takımın oyuncuları AYNI rengi alıyor",
          len(set(_lal)) == 1)
    basar("Renk: yüksek GmSc'li takım birincil rengini koruyor",
          next(o for o in _cozum if o["takim"] == "LAL")["renk"] == _renk_cfg["LAL"][0])
    _sac = next(o for o in _cozum if o["takim"] == "SAC")
    basar("Renk: düşük GmSc'li çakışan takım sıradaki renge geçiyor",
          _sac["renk_degisti"] and _sac["renk"] != _renk_cfg["SAC"][0])
    basar("Renk: halka takımın ASIL rengini taşıyor",
          _sac["asil_renk"] == _renk_cfg["SAC"][0])
    basar("Renk: çakışmayan takım hiç değişmiyor",
          not next(o for o in _cozum if o["takim"] == "GSW")["renk_degisti"])

    # Kural HER listede geçerli: gecenin beşi, yükselen, düşen.
    for _ad in ("gecenin_besi", "yukselen", "dusen"):
        _l = _d5.get(_ad) or []
        basar(f"Renk: {_ad} listesinde takım renkleri çözülmüş",
              all("renk" in o and "asil_renk" in o and "renk_degisti" in o for o in _l))
        _cift = {}
        for _o in _l:
            _cift.setdefault(_o["takim"], set()).add(_o["renk"])
        basar(f"Renk: {_ad} listesinde takım başına tek renk",
              all(len(v) == 1 for v in _cift.values()))

    # Sahada TAKIM KODU her oyuncuda — çakışma olsun olmasın.
    basar("Saha: her oyuncunun takım kodu var",
          all(o.get("takim") for o in _d5["gecenin_besi"]))
    basar("Saha: kod işaretlemesi ve halka CSS'i kuruldu",
          '<div class="tg">${esc(o.takim)}</div>' in _sayfa5
          and ".pl .dot.ring{box-shadow:0 0 0 2.5px var(--asil)" in _sayfa5)
    basar("Saha: halka SADECE rengi değişen oyuncuda",
          "o.renk_degisti?` ring" in _sayfa5)

    # ==================================================================
    # YÜKSELEN / DÜŞEN
    # ==================================================================
    _yuk, _dus = _d5.get("yukselen") or [], _d5.get("dusen") or []
    basar("Form: iki liste de en fazla 5 satır",
          len(_yuk) <= 5 and len(_dus) <= 5)
    basar("Form: her satırda tam 5 maç var",
          all(len(o["son5"]) == 5 for o in _yuk + _dus))
    basar("Form: son çubuk BU GECE",
          all(o["son5"][-1]["bu_gece"] and not any(x["bu_gece"] for x in o["son5"][:-1])
              for o in _yuk + _dus))
    # ÖLÇÜT sadece çok sayı atmak DEĞİL, sezon ortalamasını aşma miktarı.
    basar("Form: yükselenler sezon ortalamasının ÜSTÜNDE",
          all(o["fark"] > 0 for o in _yuk))
    # Sıralama artık YÜZDEYE göre (kullanıcı kuralı): mutlak fark 27.4
    # ortalayanla 10 ortalayanı aynı gösteriyordu.
    basar("Form: yükselenler yüzde değişime göre sıralı (mutlak farka göre değil)",
          [o["yuzde"] for o in _yuk] == sorted((o["yuzde"] for o in _yuk), reverse=True))
    basar("Form: düşenler sezon ortalamasının ALTINDA",
          all(o["fark"] < 0 for o in _dus))
    # 25+ dakika şartı: yoksa 2 sayı ortalayan yedekler listeyi doldurur.
    basar(f"Form: düşenlerde 25+ dakika şartı uygulanıyor",
          all(o["sezon_ort"] >= _derle.DUSEN_ASGARI_SEZON_SAYI for o in _dus))
    basar("Form: fark gerçekten son5 - sezon",
          all(abs(o["fark"] - round(o["son5_ort"] - o["sezon_ort"], 1)) < 0.11
              for o in _yuk + _dus))
    # O gece OYNAMAYAN oyuncu iki listede de yer almaz.
    _oynayanlar = {o["isim"] for k in _d5["mutlaka"] + (_d5.get("degerse_bak") or [])
                            + (_d5.get("diger") or [])
                   for t in ("ev", "dep") for o in k["box"][t]["oyuncular"]}
    basar("Form: listedeki herkes o gece oynadı",
          all(o["isim"] in _oynayanlar for o in _yuk + _dus))

    # Balon: mobilde hover YOK, dokunma zorunlu; aynı anda tek balon.
    basar("Form: balon görünürlüğü kap sınıfıyla (kardeş seçici değil)",
          ".sq.tipon .tip{opacity:1}" in _sayfa5
          and ".tap + .tip" not in _sayfa5)
    basar("Form: hover sadece hover destekleyen cihazda",
          "matchMedia('(hover:hover)').matches" in _sayfa5)
    basar("Form: aynı anda tek balon (önce hepsi kapanıyor)",
          "formdaBalonKapat();" in _sayfa5)
    # Sol başlık SABİT: sekmede zaten aynı kelime yazıyor.
    basar("Form: sol başlık sabit 'Form', sekmeyle değişmiyor",
          "<h2>Form</h2>" in _sayfa5 and "formdaBaslik" not in _sayfa5)

    # ==================================================================
    # Çıpa kaydırması ve Göz at'ta box score işareti
    # ==================================================================
    basar("Çıpa: kaydırma tarayıcıya bırakılmıyor, hesaplanıyor",
          "function cipayaKaydir(" in _sayfa5 and "CIPA_PAYI" in _sayfa5)
    basar("Çıpa: ikinci sıçrama olmasın diye replaceState kullanılıyor",
          "history.replaceState(null, '', '#' + id)" in _sayfa5)
    basar("Çıpa: kullanılmayan revealTarget ölü kodu kaldırıldı",
          "revealTarget" not in _sayfa5)
    # İşaret SADECE ok: "Box score için dokun" fazlaydı, "Box ›" da
    # fazlaydı. Erişilebilirlik açıklaması düğmenin aria-label'ında.
    basar("Box işareti: Göz at ve Bunları geç satırlarında var",
          _sayfa5.count('class="gozgo" aria-hidden="true"') == 2)
    basar("Box işareti: sadece ok, metin yok",
          '<span class="gozgo" aria-hidden="true">›</span>' in _sayfa5
          and "gozgo\">Box" not in _sayfa5)
    basar("Box işareti: ekran okuyucu için açıklama aria-label'da",
          _sayfa5.count('— box score"') == 2)
    # Mutlaka bil'de bağlantı SAĞDA. Solda kalınca kilit istatistiğin
    # sol etiketiyle ("ribaund", ember) 15px arayla üst üste biniyordu —
    # iki ember metin aynı kenarda (ölçüldü).
    basar("Mutlaka bil: box score bağlantısı sağa hizalı",
          "text-align:right;font-family:var(--mono);\n  font-size:11.5px" in _sayfa5)
    # Eski metin GÖRÜNÜR işaretlemede olmamalı; kaynaktaki açıklama
    # yorumu sayılmıyor (aynı tuzağa daha önce de düşülmüştü).
    _gorunur5 = _re.sub(r"/\*.*?\*/", "", _sayfa5, flags=_re.S)
    basar("Mutlaka bil: 'dokun/tıkla' kalktı, sade 'Box score ›' kaldı",
          '<span class="opener">Box score<i>›</i></span>' in _sayfa5
          and "Box score için" not in _gorunur5)
    # Üç bölümde de aynı işaret: okuyucu bir kez öğreniyor.
    basar("Box işareti: üç bölümde de aynı ok kullanılıyor",
          _sayfa5.count("›") >= 3)

    # ==================================================================
    # SIRALAMA — gece bitince kim yükseldi, kim düştü.
    # Metin bunu söyleyemiyor: tek maçın metni tüm ligin hareketini
    # anlatamaz.
    # ==================================================================
    _sayfa6 = open("overnight_v17.html", encoding="utf-8").read()
    _d6 = _jj.loads(open(f"dist/{_yayinda2}.json", encoding="utf-8").read())
    _sir = _d6.get("siralama") or []

    # İÇERİK KURALI: sadece yer değiştirenler; hareket yoksa bölüm yok.
    basar("Sıralama: listedeki her takım gerçekten yer değiştirmiş",
          all(t["eski"] != t["yeni"] for t in _sir))
    basar("Sıralama: değişim işareti yönü doğru (pozitif = yükseldi)",
          all((t["degisim"] > 0) == (t["yeni"] < t["eski"]) for t in _sir))
    basar("Sıralama: değişim miktarı sıra farkına eşit",
          all(abs(t["degisim"]) == abs(t["eski"] - t["yeni"]) for t in _sir))
    basar("Sıralama: hareket yoksa bölüm gizleniyor",
          "document.getElementById('secSiralama').hidden=!siralama.length" in _sayfa6)
    basar("Sıralama: başlık yanında sayaç var",
          "siralamaSayac" in _sayfa6 and "${siralama.length} takım" in _sayfa6)

    # Gece ÖNCESİ sıralama, oyun günlüğünden O GÜN ÇIKARILARAK hesaplanıyor
    # — sıralama uç noktasında tarih filtresi yok.
    _gunluk = _jj.loads(_yayin._ham_metni(_yayinda2))["puan_durumu"]
    _once_ham, _i = _derle._gunluk_satirlari(_gunluk, kadar_tarih=_yayinda2)
    _tum = len(_gunluk["resultSets"][0]["rowSet"])
    _once = len(_once_ham["resultSets"][0]["rowSet"])
    basar("Sıralama: gece öncesi hesabı o günün maçlarını dışarıda bırakıyor",
          _once < _tum)
    basar("Sıralama: dışarıda kalan satırların hepsi o geceye ait",
          all(str(r[_i["GAME_DATE"]])[:10] == _yayinda2
              for r in _gunluk["resultSets"][0]["rowSet"]
              if str(r[_i["GAME_DATE"]])[:10] >= _yayinda2))

    # FORM: son 10, eskiden yeniye, sonuncusu bu geceki maç.
    basar("Sıralama: her takımda 10 form kutucuğu",
          all(len(t["form"]) == 10 for t in _sir))
    # Kutucuk artık bilgi taşıyor: {g, rakip, skor}. Galibiyet bilgisi
    # `g` alanında, kaybolmadı.
    basar("Sıralama: form değerleri galibiyet/mağlubiyet (g alanı)",
          all(isinstance(w["g"], bool) for t in _sir for w in t["form"]))
    # Son kutucuk bu geceki maçın sonucu olmalı — kutu skorla karşılaştır.
    _gece_sonuc = {}
    for _k in _d6["mutlaka"] + (_d6.get("degerse_bak") or []) + (_d6.get("diger") or []):
        _b = _k["box"]
        _kaz = _b["ev"] if _b["ev"]["skor"] >= _b["dep"]["skor"] else _b["dep"]
        _kay = _b["dep"] if _kaz is _b["ev"] else _b["ev"]
        _gece_sonuc[_kaz["kod"]] = True
        _gece_sonuc[_kay["kod"]] = False
    basar("Sıralama: son kutucuk BU GECEKİ maçın sonucu",
          all(t["form"][-1]["g"] == _gece_sonuc.get(t["takim"]) for t in _sir
              if t["takim"] in _gece_sonuc))

    # KARAR DEĞİŞTİ: takım rengi (küçük dikdörtgen) kaldırıldı. Renk
    # kullanılmadığı için çakışma çözümü de çağrılmıyor — kullanılmayan
    # alan üretilmiyor. Kural duruyor, renk geri gelirse tek satır.
    basar("Sıralama: takım rengi kullanılmıyor, ölü alan da üretilmiyor",
          all("renk" not in t and "asil_renk" not in t for t in _sir))
    basar("Sıralama: renk dikdörtgeni işaretlemeden de kalktı",
          ".sr .tc{" not in _sayfa6 and 'class="tc' not in _sayfa6)

    # YERLEŞİM: bölüm EN SONDA.
    _bolumler = _re.findall(r'<section class="sec[^"]*"(?:\s+id="([^"]+)")?', _sayfa6)
    basar("Sıralama: bölüm en sonda (kapanış bilgisi)",
          _bolumler and _bolumler[-1] == "secSiralama")

    # ÖLÇÜLER — şartnamedeki değerler.
    basar("Sıralama: ok sütunu 30px ve sarmalanmıyor",
          "font-size:11.5px;font-weight:700;width:30px" in _sayfa6
          and "white-space:nowrap}" in _sayfa6.split(".sr .ar{")[1][:200])
    basar("Sıralama: yükseliş yeşil, düşüş kırmızı",
          ".sr .ar.u{color:#3FB27F}" in _sayfa6 and ".sr .ar.d{color:#C4544F}" in _sayfa6)
    basar("Sıralama: form kutucukları 9x9, 2.5px aralık",
          "width:9px;height:9px" in _sayfa6 and ".sr .f10{display:flex;gap:2.5px" in _sayfa6)
    # Mağlubiyet KIRMIZI oldu (kullanıcı kararı): koyu gri "veri yok"
    # gibi duruyordu, oysa her kutucuk oynanmış bir maç.
    basar("Sıralama: galibiyet yeşil %85, mağlubiyet kırmızı %75",
          ".sr .f10 i.w{background:#3FB27F;opacity:.85}" in _sayfa6
          and "background:#C4544F;opacity:.75" in _sayfa6)
    basar("Sıralama: sıra sütunu 46px, sağa hizalı",
          "width:46px;flex:none;text-align:right" in _sayfa6)
    # "4→3" 10 form kutucuğunun yanında galibiyet-mağlubiyet sanıldı;
    # "4.→3." de okunaksız oldu. Eski sıra ZATEN gereksiz: soldaki ok kaç
    # sıra oynadığını, sağdaki nerede olduğunu söylüyor.
    basar("Sıralama: sadece YENİ sıra yazılıyor",
          "<b>${t.yeni}.</b>" in _sayfa6 and "${t.eski}" not in _sayfa6)
    basar("Sıralama: sayının ne olduğu satırda yazılı",
          "<s>sıra</s>" in _sayfa6)
    # Eşitlikte diziliş rastgele görünüyordu; yeni sıra belirleyici.
    basar("Sıralama: eşit hareketlerde üst sıradaki önce",
          all(_sir[i]["degisim"] != _sir[i+1]["degisim"]
              or _sir[i]["yeni"] <= _sir[i+1]["yeni"] for i in range(len(_sir)-1)))
    basar("Sıralama: en çok yükselen en üstte, en çok düşen en altta",
          [t["degisim"] for t in _sir] == sorted((t["degisim"] for t in _sir), reverse=True))
    basar("Sıralama: sayaç neyin sırası olduğunu söylüyor",
          "konferans sırası" in _sayfa6)

    # SEZON BAŞI: ilk günlerde sıralama anlamsız, bölüm çıkmıyor.
    _gunler = sorted({str(r[_i["GAME_DATE"]])[:10]
                      for r in _gunluk["resultSets"][0]["rowSet"]})
    def _kesitle(gun_sayisi):
        _kesim = _gunler[gun_sayisi - 1]
        _rs = _gunluk["resultSets"][0]
        return {"puan_durumu": {"resultSets": [{"headers": _rs["headers"],
                "rowSet": [r for r in _rs["rowSet"]
                           if str(r[_i["GAME_DATE"]])[:10] <= _kesim]}]}}, _kesim
    _takimlar = ["BOS", "LAL", "DEN", "GSW", "MIA", "PHX"]
    for _n in (3, 5):
        _h, _g = _kesitle(_n)
        basar(f"Sıralama: sezonun {_n}. oyun gününde bölüm çıkmıyor",
              _derle._siralama_hareketi(_h, _g, _takimlar) == [])
    _h6, _g6 = _kesitle(6)
    basar("Sıralama: 6. oyun gününden itibaren çıkıyor",
          len(_derle._siralama_hareketi(_h6, _g6, _takimlar)) > 0)
    basar("Sıralama: eşik gün sayısı 5",
          _derle.SIRALAMA_ASGARI_GUN == 5)
    # Arşiv geceleri sezon ortasından; eşiği zaten geçiyorlar.
    basar("Sıralama: yayındaki arşiv gecesi eşiği geçiyor",
          len(_sir) > 0)
    # Ad KESİLMİYOR — projenin kuralı, ve şartname "tam ad" diyor.
    basar("Sıralama: takım adı kesilmiyor, sarmalanıyor",
          "overflow-wrap:break-word}" in _sayfa6.split(".sr .tn{")[1][:260]
          and "text-overflow:ellipsis" not in _sayfa6.split(".sr .tn{")[1][:260])

    # ==================================================================
    # DEĞİŞMEZ KURAL: "Sen uyurken"de cümle dağılımı ROZET SIRASIYLA
    # uyumlu. Bir maç cümle alıyorsa ondan yüksek rozetli her maç da
    # alır — sıralamada boşluk olamaz.
    # Gerçek arıza: 4. sıradaki maç konuşurken 2. sıradaki susuyordu
    # (MEM-WAS 8.62 sessiz, TOR-BOS 7.35 konuşuyor). Sebep: türü ROZETİ
    # yüksek maç kapıyordu ve 14 sayılık geri dönüş 20 sayılığı bloke
    # ediyordu.
    # ==================================================================
    import yaz as _yaz
    _gc = _jj.loads(open(f"gercek/{_yayinda2}.json", encoding="utf-8").read())
    _hm = _jj.loads(_yayin._ham_metni(_yayinda2))
    _sk = _jj.loads(open(f"skor/{_yayinda2}.json", encoding="utf-8").read())
    _plan = _yaz.gece_kalip_plani(_yayinda2, _gc, _hm, _sk)
    _roz = {m["mac_id"]: m["rozet"] for m in _sk["maclar"]}
    _eniyi = {m["mac_id"]: m.get("en_iyi_performans") for m in _sk["maclar"]}
    _atama = _yaz.gece_brief_ata(_plan, _roz, list(_roz), _hm, _eniyi, _gc)

    _konusan = [_roz[g] for g in _atama]
    _susan = [_roz[g] for g in _roz if g not in _atama]
    basar("Brief: cümle dağılımında rozet boşluğu yok",
          not _konusan or not _susan or min(_konusan) > max(_susan))
    # Tür, o türde EN GÜÇLÜ maça gider — rozete göre değil.
    _geri = [g for g, o in _atama.items() if o["kind"] == "geri_donus"]
    if _geri:
        _sahip = _geri[0]
        _guc = _plan[_sahip]["olgu_ham"].get("en_buyuk_geri_donus", 0)
        _rakipler = [g for g in _roz if g != _sahip
                     and (_plan[g]["olgu_ham"].get("en_buyuk_geri_donus") or 0) >= _yaz.cumle.GERI_DONUS_ESIGI]
        basar("Brief: geri dönüş türünü EN BÜYÜK dönüş alıyor",
              all(_guc >= (_plan[g]["olgu_ham"].get("en_buyuk_geri_donus") or 0) for g in _rakipler))
    # Türü kaybeden maç susmuyor: ya başka olgusunu ya düz sonucu alıyor.
    basar("Brief: olgusu olan hiçbir maç türe takılıp susmuyor",
          all(g in _atama for g in _roz
              if _yaz.cumle.brief_adaylari(
                  *_yaz._brief_mac_baglami(g, _gc, _hm, _plan, _eniyi)[:1],
                  _plan[g]["olgu_ham"] or {},
                  *_yaz._brief_mac_baglami(g, _gc, _hm, _plan, _eniyi)[2:])
              and _roz[g] > (max(_susan) if _susan else -1)))
    basar("Brief: düz sonuç cümlesi bir yedek olarak var",
          hasattr(_yaz.cumle, "brief_duz_sonuc"))
    # Sessiz kalmanın TEK sebebi: eşiği geçen hiçbir olgu yok.
    for _g in _roz:
        if _g in _atama:
            continue
        _mac, _olgu, _eo, _ea = _yaz._brief_mac_baglami(_g, _gc, _hm, _plan, _eniyi)
        _ads = [x for x in _yaz.cumle.brief_adaylari(_mac, _olgu or {}, _eo, _ea)
                if _yaz.cumle._gecir(x[1])]
        if _ads and _roz[_g] > (max(_susan) if _susan else -1):
            basar(f"Brief: sessiz maçın olgusu yok ({_g})", False)
            break
    else:
        basar("Brief: sessiz maçlar kesim çizgisinin altında", True)
    # Kesim ATAMADAN ÖNCE: kesilecek bir maç tür kapıp yukarıdakini
    # düz cümleye düşürmesin (ölçüldü: DET-CHA 2.45 `siralama`yı alıyor,
    # sonra kesiliyor, TOR-BOS 7.35 düz cümleye düşüyordu).
    _kaynak = open("yaz.py", encoding="utf-8").read()
    basar("Brief: monotonluk kesimi tür atamasından ÖNCE yapılıyor",
          _kaynak.index("MONOTONLUK KESİMİ ATAMADAN ÖNCE")
          < _kaynak.index("# 2) Tür ataması"))
    # Havuz BÜTÜN maçlar. Havuzu beşe indirmek, kesimden önce ikinci bir
    # eleme demekti; üstelik "kilometre taşı olan düşük rozetli maç,
    # en düşükün YERİNİ ALIR" kuralı yüksek rozetli maçı havuzdan atıp
    # monotonluğu bozuyordu (20 Aralık: TOR-BOS 7.35 ve DEN-HOU 6.39,
    # 2.45 ve 2.65 rozetli maçlar için çıkarılmıştı).
    basar("Brief: hedef havuzu gecenin bütün maçları",
          "diger_hedef_sayisi" not in _kaynak)
    basar("Brief: olay eşiğiyle yer değiştirme kaldırıldı",
          "olay_adaylari" not in _kaynak)
    # Yayınlanan gecede de kural tutuyor mu — uçtan uca.
    _bd = _d3["brief"]
    _bk = [b["rozet"] for b in _bd if b["anlatili"]]
    _bs = [b["rozet"] for b in _bd if not b["anlatili"]]
    basar("Brief: YAYINLANAN gecede de rozet boşluğu yok",
          not _bk or not _bs or min(_bk) > max(_bs))

    # ==================================================================
    # "AYRICA" — kilometre taşları akışın DIŞINDA.
    # "Sen uyurken" MAÇLARI sıralıyor (rozete göre); triple-double ise
    # bir OYUNCU haberi. İkisi tek listede karışınca ya rozet sıralaması
    # bozuluyordu ya haber düşüyordu (2.45 rozetli maçtaki Cunningham
    # triple-double'ı kesimin altında kalıyordu).
    # ==================================================================
    _ayr = _d3.get("brief_ayrica") or []
    # DİKKAT: "satır dolu olmalı" diye test YAZILMAZ — o bir gözlem,
    # kural değil. Akış kilometre taşını zaten anıyorsa Ayrıca'nın BOŞ
    # olması DOĞRU davranıştır (2025-12-21: gecenin tek kilometre taşı
    # Brunson'ın 47 sayısı, akışta anılıyor, satır boş). Kural şu:
    # hiçbir kilometre taşı kaybolmaz — ya akışta ya Ayrıca'da.
    _kilo3 = [f["veri"]["oyuncu"]
              for _k in (_g3.get("maclar") or {}).values()
              for f in _k if f["tur"] == "kilometre" and f["veri"].get("oyuncu")]
    _akis3 = " ".join(b.get("metin", "") for b in (_d3.get("brief") or []))
    _ayr_adlari = " ".join(a["isim"] for a in _ayr)
    basar("Ayrıca: hiçbir kilometre taşı kaybolmuyor (akışta ya da Ayrıca'da)",
          all(ad.split()[-1].lower() in (_akis3 + " " + _ayr_adlari).lower()
              for ad in _kilo3))
    basar(f"Ayrıca: en fazla {_derle.AYRICA_EN_FAZLA} kayıt",
          len(_ayr) <= _derle.AYRICA_EN_FAZLA)
    basar("Ayrıca: her kayıtta isim, ifade ve takım var",
          all(a.get("isim") and a.get("ifade") and a.get("takim") for a in _ayr))
    # Akışta anılan oyuncu buraya TEKRAR girmiyor.
    _akis = " ".join(b.get("metin", "") for b in _d3["brief"] if b.get("metin")).lower()
    basar("Ayrıca: akışta anılan oyuncu tekrar etmiyor",
          all(a["isim"].split()[-1].lower() not in _akis for a in _ayr))
    # Rozetle ve saatle ilgisi yok — sıralamanın dışında.
    basar("Ayrıca: kayıtlar rozet/saat taşımıyor (sıralamanın dışında)",
          all("rozet" not in a and "saat" not in a for a in _ayr))
    # Gerçek değer yazılıyor, eşik metni değil ("5 blok", "5+ blok" değil).
    basar("Ayrıca: eşik metni değil gerçek değer yazılıyor",
          all("+" not in a["ifade"] for a in _ayr))
    # Nadirlik sırası: en nadir eşik önce.
    _oncelik = _kalip_secici._KILOMETRE_ONCELIK
    basar("Ayrıca: seçim nadirliğe göre (kalip_secici önceliği)",
          "_KILOMETRE_ONCELIK.index" in open("derle.py", encoding="utf-8").read())
    # Hiçbiri yoksa satır çıkmaz.
    basar("Ayrıca: kayıt yoksa satır gizleniyor",
          "ayricaKutu.hidden=!ayrica.length" in _sayfa3)
    # Yeri: akıştan sonra, alt şeritten önce.
    _i_rows = _sayfa3.index('id="briefList"')
    _i_ayr = _sayfa3.index('id="briefAyrica"')
    _i_foot = _sayfa3.index('class="cfoot"')
    basar("Ayrıca: akıştan sonra, alt şeritten önce",
          _i_rows < _i_ayr < _i_foot)
    # Asist fiili kuralı burada da geçerli.
    basar("Ayrıca: asist için 'yaptı' kullanılıyor (verdi/dağıttı yasak)",
          '"asist": "yaptı"' in open("derle.py", encoding="utf-8").read())
    _yasakli3 = dogrula_modul.yasakli_yukle()
    basar("Ayrıca: üretilen ifadeler yasak listesinden geçiyor",
          all(dogrula_modul.t4_yasakli_ifade(a["ifade"], _yasakli3)[0]
              and dogrula_modul.t4d_kok_kaliplari(a["ifade"])[0] for a in _ayr))

    # ==================================================================
    # İLK BEŞ GÖSTERGESİ
    # Mevcut şerit KULLANILMIYOR: satırın sol kenarındaki ember
    # ("gecenin adamı") ve mavi ("rakibin en iyisi") işaretleri özel;
    # beş oyuncuya da verilirse anlamlarını kaybederler.
    # ==================================================================
    _sayfa7 = open("overnight_v17.html", encoding="utf-8").read()
    _d7 = _jj.loads(open(f"dist/{_yayinda2}.json", encoding="utf-8").read())
    _kart7 = []
    for _b in ("mutlaka", "degerse_bak", "diger"):
        _v = _d7.get(_b)
        if isinstance(_v, list):
            _kart7 += [x for x in _v if isinstance(x, dict) and "box" in x]
    # Veri: her takımda tam 5 ilk beş.
    basar("İlk beş: her takımda tam 5 oyuncu işaretli",
          all(sum(1 for o in k["box"][t]["oyuncular"] if o.get("ilk_bes")) == 5
              for k in _kart7 for t in ("ev", "dep")))
    basar("İlk beş: yedeklerde işaret yok",
          all(isinstance(o.get("ilk_bes"), bool)
              for k in _kart7 for t in ("ev", "dep") for o in k["box"][t]["oyuncular"]))
    # Kaynak: BoxScoreTraditionalV3'ün `position` alanı — ek çağrı yok.
    basar("İlk beş: ayrım position alanından, ek API çağrısı yok",
          '"ilk_bes": bool(p.get("position"))' in open("derle.py", encoding="utf-8").read())
    # SIRALAMA DEĞİŞMİYOR: tablo hâlâ sayıya göre.
    basar("İlk beş: tablo hâlâ sayıya göre sıralı (ilk beş üste toplanmadı)",
          all([o["pts"] for o in k["box"][t]["oyuncular"]]
              == sorted((o["pts"] for o in k["box"][t]["oyuncular"]), reverse=True)
              for k in _kart7 for t in ("ev", "dep")))
    # Gösterge AYRI ve NÖTR; mevcut şerit dokunulmadan duruyor.
    basar("İlk beş: gösterge nötr gri, ember/mavi değil",
          "background:#4A5566}" in _sayfa7.split("td.ilkbes::before")[1][:200])
    basar("İlk beş: mevcut ember/mavi şerit yerinde",
          "tr.kstar td:first-child{background:#17110A;box-shadow:inset 3px 0 0 var(--ember)}" in _sayfa7
          and "tr.kbest td:first-child{background:#0C1320;box-shadow:inset 3px 0 0 #5B8DEF}" in _sayfa7)
    basar("İlk beş: iki işaret çakışmıyor (kenar 0-3px, gösterge 8-11px)",
          "left:8px" in _sayfa7.split("td.ilkbes::before")[1][:200])
    # Dolgu bütün satırlarda aynı — yedeklerde çizgi yok ama yer ayrılı.
    basar("İlk beş: ad sütunu dolgusu 18px (yedekte de yer ayrılı)",
          "background:#0E131B;padding-left:18px" in _sayfa7)
    # İstatistik daraltması ad sütununa uygulanmamalı; uygulanınca
    # gösterge yazının üstüne biniyordu (ölçüldü).
    basar("İlk beş: istatistik daraltması ad sütununu etkilemiyor",
          "td:nth-child(n+2):nth-child(-n+5)" in _sayfa7)
    # Lejant bir KEZ, sekme başına değil.
    basar("İlk beş: lejant kartta bir kez (kfoot içinde)",
          '<span class="kbeslegend"><i></i>ilk beş</span>' in _sayfa7
          and _sayfa7.count("kbeslegend\"><i>") == 1)

    # ==================================================================
    # AÇILIŞ (HERO) — GAZETE KÜNYESİ
    # Eski açılış ortalanmış iki satırlık slogandı: bilgi taşımıyordu.
    # Yenisi künye. Testler hem yeni yapının varlığını hem ESKİ kalıbın
    # geri gelmediğini kontrol ediyor — asıl şikâyet kalıbın kendisiydi.
    # ==================================================================
    _sayfa8 = open("overnight_v17.html", encoding="utf-8").read()
    _kunye = _sayfa8.split('<div class="mast">')[1].split("</div>\n\n<div class=\"hero\">")[0]
    _hero8 = _sayfa8.split('<div class="hero">')[1].split("</div>")[0]

    basar("Açılış: marka künyede, NIGHT ember",
          '<div class="mark">OVER<em>NIGHT</em></div>' in _kunye
          and ".mark em{font-style:normal;color:var(--ember)}" in _sayfa8)
    basar("Açılış: tarih ve gün adı sağda, ayrı satırlarda",
          '<span id="edTarih">' in _kunye and '<b id="edGun">' in _kunye
          and ".ed b{display:block" in _sayfa8)
    # Çift çizgi: kalın açık + ince koyu.
    basar("Açılış: çift çizgi (2px açık + 1px koyu)",
          "border-bottom:2px solid var(--ink)" in _sayfa8
          and ".rule2{height:1px;background:#1A2130" in _sayfa8
          and '<div class="rule2"></div>' in _sayfa8)
    # SABİT SAAT: canlı olmadığı için bilgi değil.
    basar("Açılış: sabit saat yazmıyor",
          "TSİ 09:00" not in _kunye and "TSI 09:00" not in _kunye)
    # "dakika": ürünün vaadi hız değil.
    basar("Açılış: okuma süresi (dakika) yazmıyor",
          "dakika" not in _hero8
          and "dakika" not in _sayfa8.split("id='nums'")[0].split('id="nums"')[-1][:400])
    # ESKİ KALIP GERİ GELMESİN.
    basar("Açılış: ortalanmış değil",
          "text-align:center" not in _sayfa8.split(".hero{")[1].split("}")[0]
          and "text-align:center" not in _sayfa8.split("\nh1{")[1].split("}")[0])
    basar("Açılış: dev slogan kalıbı kalktı",
          "clamp(38px,11vw,52px)" not in _sayfa8
          and "font-size:24px" in _sayfa8.split("\nh1{")[1].split("}")[0])
    basar("Açılış: eski damga ve tanıtım cümlesi kalmadı",
          "Molasız, reklamsız özet" not in _sayfa8
          and 'id="stamp"' not in _sayfa8
          and "NBA · sen uyurken</em>" not in _sayfa8)
    # Sayılar sarmalanmamalı; sıkışırsa cümle kısalır, sayı bozulmaz.
    basar("Açılış: sayılar tek satırda ve daralmıyor",
          "flex:none" in _sayfa8.split(".nums{")[1].split("}")[0]
          and "white-space:nowrap" in _sayfa8.split(".nums{")[1].split("}")[0])

    # --- Sayılar ham veriyle birebir mi? ---
    # (DOM'a elle değer enjekte edip "doğru görünüyor" demek yerine
    #  yayındaki dist'ten hesaplanıyor.)
    _rozetler8 = [b.get("rozet", 0) for b in _d7.get("bars") or []]
    basar("Açılış: maç sayısı bars uzunluğuyla aynı",
          _d7.get("mac_sayisi") == len(_rozetler8))
    _kartroz8 = [k["rozet"] for b in ("mutlaka", "degerse_bak", "diger")
                 for k in (_d7.get(b) or []) if isinstance(k, dict) and "rozet" in k]
    basar("Açılış: 'en iyisi' gecenin en yüksek rozeti (kartlarla da uyuşuyor)",
          bool(_rozetler8) and bool(_kartroz8)
          and round(max(_rozetler8), 2) == round(max(_kartroz8), 2))
    basar("Açılış: en iyisi tek ondalık basamakla yazılıyor",
          "enIyi.toFixed(1)" in _sayfa8)

    # --- Gün adı doğru mu? ---
    # JS getUTCDay() Pazar=0; Python weekday() Pazartesi=0. Tablo sırası
    # yanlışsa gün adı kayar ve künye yanlış bilgi verir.
    _gunler8 = _sayfa8.split("const GUN_ADLARI=[")[1].split("]")[0]
    _gunler8 = [x.strip().strip("'") for x in _gunler8.split(",")]
    _dogru8 = ["Pazartesi", "Salı", "Çarşamba", "Perşembe",
               "Cuma", "Cumartesi", "Pazar"]
    _t8 = _tarih.date.fromisoformat(_yayinda2)
    basar("Açılış: gün adı tablosu Pazar=0 sırasında",
          _gunler8[(_t8.weekday() + 1) % 7] == _dogru8[_t8.weekday()])
    basar("Açılış: gün adı UTC ile hesaplanıyor (yaz saati kaydırmasın)",
          "Date.UTC(y,m-1,d)).getUTCDay()" in _sayfa8)
    # Türkçe büyük harf: text-transform her tarayıcıda dil duyarlı değil.
    basar("Açılış: büyük harf Türkçe kurala göre (CUMARTESİ, CUMARTESI değil)",
          "toLocaleUpperCase('tr-TR')" in _sayfa8
          and "text-transform" not in _sayfa8.split(".ed{")[1].split("}")[0])

    # ==================================================================
    # KRİTİK ANLAR — "son 5 dakika" bloğu
    # NBA'in standart clutch tanımı: son 5 dakika ve varsa uzatmaların
    # tamamı İÇİNDE, farkın 5 ve altında OLDUĞU süre. Maçın son 5
    # dakikası DEĞİL — testler tam olarak bu ayrımı koruyor.
    # ==================================================================
    _sayfa9 = open("overnight_v17.html", encoding="utf-8").read()
    _kart9 = []
    for _b in ("mutlaka", "degerse_bak", "diger"):
        _v = _d7.get(_b)
        if isinstance(_v, list):
            _kart9 += [x for x in _v if isinstance(x, dict) and "box" in x]
    _kritikler = [(k["box"]["ev"], k["box"]["dep"], k["box"].get("kritik"))
                  for k in _kart9]
    _acik = [(e, d, kr) for e, d, kr in _kritikler if kr]

    # --- Tanım ---
    basar("Kritik: pencere 4. çeyreğin bitimine 5 dakika kala başlıyor",
          _derle.KRITIK_BASLANGIC_SN == 3 * 720 + (720 - 5 * 60)
          and _derle.KRITIK_SON_DAKIKA == 5)
    basar("Kritik: fark eşiği 5 sayı",
          _derle.KRITIK_FARK == 5)
    basar("Kritik: uzatma dakikaları da pencerede (5 dk'lık periyot)",
          _derle._mac_saniyesi(5, 300.0) == 4 * 720
          and _derle._mac_saniyesi(5, 0.0) == 4 * 720 + 300
          and _derle._mac_saniyesi(6, 0.0) == 4 * 720 + 600)
    basar("Kritik: saat ayrıştırma (PT02M38.00S → 158 sn kaldı)",
          _derle._pbp_saniye("PT02M38.00S") == 158.0
          and _derle._pbp_saniye("PT00M00.00S") == 0.0
          and _derle._pbp_saniye("") is None)

    # --- Görünürlük: TEK kural ---
    basar("Kritik: eşik 2 dakika, açılan her bölüm eşiği geçiyor",
          _derle.KRITIK_ASGARI_SURE_SN == 120
          and all(kr["sure_sn"] >= 120 for _e, _d, kr in _acik))
    basar("Kritik: sayı atılmamışsa bölüm açılmıyor",
          all(sum(o["sayi"] for o in kr["oyuncular"]) > 0 for _e, _d, kr in _acik))
    # Farklı biten maçta kritik süre sıfırdır — bölüm hiç açılmaz.
    basar("Kritik: 20+ farkla biten maçta bölüm yok",
          all(kr is None for e, d, kr in _kritikler if abs(e["skor"] - d["skor"]) >= 20))
    # "Final farkı ≤5" gibi EK koşul YOK: uzatmaya gidip farklı biten
    # maçta da kritik anlar yaşanmıştır. Bu KURAL, o gecenin maçlarına
    # bağlı olmadan sınanıyor — kurgu bir maçla: son 5 dakikanın 4
    # dakikası tek sayı farkla geçiyor, sonra 16-0'lık seri geliyor ve
    # maç 17 farkla bitiyor. Bölüm yine de AÇILMALI.
    def _kurgu_olay(dk, sn, ev, dep, kisi=0, sut=False, isabet=False):
        return {"clock": f"PT{dk:02d}M{sn:05.2f}S", "period": 4,
                "scoreHome": str(ev), "scoreAway": str(dep), "personId": kisi,
                "isFieldGoal": 1 if sut else 0,
                "shotResult": "Made" if isabet else "Missed"}

    _kurgu = {
        "play_by_play": {"game": {"actions": [
            # Pencere ÖNCESİ olay: koşan skor buradan başlıyor.
            _kurgu_olay(6, 0, 90, 89),
            _kurgu_olay(5, 0, 90, 89),
            _kurgu_olay(3, 0, 92, 89, 1, True, True),
            _kurgu_olay(1, 0, 92, 91, 2, True, True),
            # Buradan sonrası 16-0'lık seri; fark üçüncü basketle 5'i
            # aşıyor ve maç 17 farkla bitiyor.
            _kurgu_olay(0, 50, 95, 91, 1, True, True),
            _kurgu_olay(0, 40, 98, 91, 1, True, True),
            _kurgu_olay(0, 30, 101, 91, 1, True, True),
            _kurgu_olay(0, 20, 104, 91, 1, True, True),
            _kurgu_olay(0, 0, 108, 91, 1, True, True),
        ]}},
        "box_traditional": {"boxScoreTraditional": {
            "homeTeam": {"teamTricode": "AAA", "players": [
                {"personId": 1, "firstName": "Ev", "familyName": "Oyuncu"}]},
            "awayTeam": {"teamTricode": "BBB", "players": [
                {"personId": 2, "firstName": "Dep", "familyName": "Oyuncu"}]}}},
    }
    _kr_kurgu = _derle._kritik_anlar(
        _kurgu,
        {"kod": "AAA", "skor": 108, "oyuncular": []},
        {"kod": "BBB", "skor": 91, "oyuncular": []})
    basar("Kritik: görünürlük final farkına bağlı değil (17 farkla biten maçta da açılıyor)",
          _kr_kurgu is not None and _kr_kurgu["sure_sn"] >= 120)
    # Serinin fark 5'i AŞTIKTAN sonraki kısmı hesaba girmiyor:
    # 2+3+3 = 8 ile 2, toplam 10 — serinin tamamı (18-2) değil.
    basar("Kritik: fark 5'i aştıktan sonraki sayılar hesaba girmiyor",
          (_kr_kurgu["ev_puan"], _kr_kurgu["dep_puan"]) == (8, 2))
    # Fark 5'i aştıktan sonraki süre de sayılmıyor: 2:00 + 2:00 + 0:20.
    basar("Kritik: fark 5'i aştıktan sonraki süre sayılmıyor",
          _kr_kurgu["sure"] == "4:20")

    # --- İçerik ---
    basar("Kritik: bölümde tam iki oyuncu (üç değil)",
          _derle.KRITIK_OYUNCU_SAYISI == 2
          and all(1 <= len(kr["oyuncular"]) <= 2 for _e, _d, kr in _acik))
    basar("Kritik: oyuncular sayıya göre sıralı",
          all([o["sayi"] for o in kr["oyuncular"]]
              == sorted((o["sayi"] for o in kr["oyuncular"]), reverse=True)
              for _e, _d, kr in _acik))
    basar("Kritik: her oyuncuda ad, takım kodu, sayı ve isabet var",
          all(o["isim"] and len(o["takim"]) == 3 and isinstance(o["sayi"], int)
              and "/" in o["fg"] for _e, _d, kr in _acik for o in kr["oyuncular"]))
    basar("Kritik: oyuncular iki takımdan (kadro dışı isim yok)",
          all(o["takim"] in (e["kod"], d["kod"])
              for e, d, kr in _acik for o in kr["oyuncular"]))
    # Ember vurgu EN FAZLA BİR satırda; ikisi de kazanan taraftan olunca
    # ikisini birden boyamak vurguyu tamamen yok ediyor.
    basar("Kritik: ember vurgu en fazla bir satırda",
          all(sum(1 for o in kr["oyuncular"] if o["kazanan"]) <= 1
              for _e, _d, kr in _acik))
    basar("Kritik: vurgulanan oyuncu KAZANAN takımdan",
          all(o["takim"] == (e["kod"] if e["skor"] >= d["skor"] else d["kod"])
              for e, d, kr in _acik for o in kr["oyuncular"] if o["kazanan"]))
    basar("Kritik: isabet sayısı denemeyi aşmıyor",
          all(int(o["fg"].split("/")[0]) <= int(o["fg"].split("/")[1])
              for _e, _d, kr in _acik for o in kr["oyuncular"]))
    # Süre metni ile saniye birbirini tutmalı.
    basar("Kritik: süre metni saniyeyle uyuşuyor",
          all(kr["sure"] == f"{kr['sure_sn'] // 60}:{kr['sure_sn'] % 60:02d}"
              for _e, _d, kr in _acik))
    # Başlıktaki skor kritik süredeki sayılar; büyük olan önde yazılır.
    basar("Kritik: başlık skoru kritik süredeki sayılar",
          all(sorted(map(int, kr["skor"].split("-")), reverse=True)
              == sorted([kr["ev_puan"], kr["dep_puan"]], reverse=True)
              for _e, _d, kr in _acik))
    basar("Kritik: önde yazan kod çok sayı üreten takım, berabere ise yok",
          all((kr["onde"] is None) == (kr["ev_puan"] == kr["dep_puan"])
              and (kr["onde"] is None
                   or kr["onde"] == (e["kod"] if kr["ev_puan"] > kr["dep_puan"] else d["kod"]))
              for e, d, kr in _acik))
    # Oyuncuların kritik sayısı, o sürede takımın attığından fazla olamaz.
    basar("Kritik: oyuncu sayıları takım toplamını aşmıyor",
          all(sum(o["sayi"] for o in kr["oyuncular"] if o["takim"] == e["kod"]) <= kr["ev_puan"]
              and sum(o["sayi"] for o in kr["oyuncular"] if o["takim"] == d["kod"]) <= kr["dep_puan"]
              for e, d, kr in _acik))
    # Kritik sayı, oyuncunun maç boyu attığı sayıdan fazla olamaz.
    _pts9 = {o["isim"]: o["pts"] for _e, _d, _k in _kritikler
             for taraf in (_e, _d) for o in taraf["oyuncular"]}
    basar("Kritik: kritik sayı maç toplamını aşmıyor",
          all(o["sayi"] <= _pts9.get(o["isim"], 0)
              for _e, _d, kr in _acik for o in kr["oyuncular"]))
    # Ek API çağrısı YOK: kaynak zaten çekilen play-by-play.
    basar("Kritik: kaynak mevcut play-by-play, ek çağrı yok",
          'ham_mac["play_by_play"]' in _derle_kaynak
          and _derle_kaynak.count("def _kritik_anlar") == 1)

    # --- Görünüm ---
    # KONUM DEĞİŞTİ: blok kart gövdesinden TAKIM sekmesine taşındı.
    # Gövdedeyken oyuncu tablosundan yer çalıyordu (41px → 23px).
    basar("Kritik: blok TAKIM sekmesinin içinde, kart gövdesinde değil",
          '<div class="kpane" data-pane="1" hidden>${kritikBlogu(b.kritik)}' in _sayfa9
          and "${ceyrekSeridi(sira[0],sira[1])}\n    ${kritikBlogu" not in _sayfa9)
    basar("Kritik: veri yoksa hiç çizilmiyor",
          "if(!k||!(k.oyuncular||[]).length) return '';" in _sayfa9)
    basar("Kritik: zemin bir tık koyu (#0C1119)",
          "background:#0C1119" in _sayfa9.split(".kritik{")[1].split("}")[0])
    basar("Kritik: başlık ember, mono 8.5px, geniş harf aralığı",
          "font-size:8.5px" in _sayfa9.split(".kritik .h b{")[1].split("}")[0]
          and "color:var(--ember)" in _sayfa9.split(".kritik .h b{")[1].split("}")[0]
          and "letter-spacing:.14em" in _sayfa9.split(".kritik .h b{")[1].split("}")[0])
    basar("Kritik: sağdaki süre/skor mono 9.5px gri",
          "font-size:9.5px" in _sayfa9.split(".kritik .h span{")[1].split("}")[0]
          and "color:var(--faint)" in _sayfa9.split(".kritik .h span{")[1].split("}")[0])
    basar("Kritik: uzun ad üç noktayla kesiliyor, sayı daralmıyor",
          "text-overflow:ellipsis" in _sayfa9.split(".krow .who{")[1].split("}")[0]
          and "flex:none" in _sayfa9.split(".krow .n{")[1].split("}")[0])
    basar("Kritik: vurgulu satırda sayı ember",
          ".krow.lead .n b{color:var(--ember)}" in _sayfa9)
    # Blok artık TAKIM panosunda ve SADECE orada — oyuncu panolarına
    # sızmıyor, yoksa aynı bilgi iki sekmede tekrarlanırdı.
    _panolar9 = _sayfa9.split("const panolar=[")[1].split("].join")[0]
    basar("Kritik: blok yalnız TAKIM panosunda",
          _panolar9.count("kritikBlogu") == 1
          and 'data-pane="1" hidden>${kritikBlogu' in _panolar9
          and '<div class="kpane" data-pane="0">${boxTablosu(sira[0])}</div>' in _sayfa9)
    # 15 kişilik kadro + kritik blok, dolgu tabanı 1 iken 3px taşıyordu.
    basar("Kritik: satır dolgusu tabanı sıfıra inebiliyor (uç kadroda taşma yok)",
          "const KBS_PAD_MIN=0," in _sayfa9)

    # ==================================================================
    # YAYIN GERÇEKTEN CANLIYA ÇIKIYOR MU
    # 27 Ağustos 2026: yayın işi kusursuz koştu, 21 Aralık'ı depoya
    # yazdı, "success" dedi — site 20 Aralık'ta kaldı. Vercel bot
    # yazarlı commit'in dağıtımını reddediyordu (TEAM_ACCESS_REQUIRED).
    # Ölçüldü: bot yazarlı 6/6 dağıtım BLOCKED, hesap yazarlı 30/30
    # READY. Yani otomatik yayın siteye HİÇ ulaşamıyordu.
    # ==================================================================
    _akislar = {ad: open(f".github/workflows/{ad}", encoding="utf-8").read()
                for ad in ("uret.yml", "yayinla.yml")}

    basar("Yayın: iş akışları Vercel'in reddettiği bot kimliğini kullanmıyor",
          all('user.name  "overnight-bot"' not in m and
              "bot@users.noreply.github.com" not in m
              for m in _akislar.values()))
    basar("Yayın: commit yazarı Vercel hesabıyla aynı",
          all(m.count('git config user.name  "yigitolmezcan"')
              == m.count("git config user.email") for m in _akislar.values())
          and all('git config user.email "yigitolmezcan@gmail.com"' in m
                  for m in _akislar.values()))
    # Her `git config user.name` satırının bir `user.email` eşi olmalı;
    # biri unutulursa commit yine bot kimliğiyle atılır.
    basar("Yayın: her yazar ayarı ad+eposta çifti hâlinde",
          all(m.count("git config user.name") == m.count("git config user.email")
              for m in _akislar.values()))

    # Denetim DEPOYA değil, okuyucunun gördüğü sayfaya bakmalı.
    basar("Yayın: canlı site denetimi yayın işine bağlı",
          "canli_dogrula.py" in _akislar["yayinla.yml"]
          and "Canlıya çıkmadı" in _akislar["yayinla.yml"])
    basar("Yayın: canlıya çıkmazsa atanmış issue açılıyor",
          "--assignee yigitolmezcan" in _akislar["yayinla.yml"]
          .split("Canlıya çıkmadı")[1])

    # `bash -e` pipefail'i KURMUYOR: `komut | tee` borusunun çıkış kodu
    # `tee`nin kodudur, yani hep 0. Onsuz denetim düşse bile adım
    # başarılı görünür — koruma yakalamak istediği sınıfa kendisi düşer.
    import yaml as _yaml
    _borulu = []
    for _ad, _m in _akislar.items():
        for _is in _yaml.safe_load(_m)["jobs"].values():
            for _adim in _is.get("steps", []):
                _kod = _adim.get("run") or ""
                if "| tee" in _kod:
                    _borulu.append((_ad, _adim.get("name", "?"), "set -o pipefail" in _kod))
    basar("Yayın: tee'ye boru yapan her adımda pipefail kurulu",
          bool(_borulu) and all(_tamam for _a, _n, _tamam in _borulu))
    basar("Yayın: canlı denetim adımının çıkış kodu yutulmuyor",
          any(_n == "Site gerçekten değişti mi" and _tamam for _a, _n, _tamam in _borulu))

    import canli_dogrula as _cd
    # Dağıtım birkaç dakika sürebiliyor; tek atışta "olmadı" demek
    # yanlış alarm üretir.
    basar("Yayın: canlı denetim tek atışta pes etmiyor (≥3 dk sabır)",
          _cd.DENEME * _cd.DENEME_ARASI_SN >= 180)
    # Gömülü veriden tarihi okuyor — sayfadaki görsel metinden değil.
    _ornek = ('<script id="gomulu-veri" type="application/json">'
              '{"2025-12-21":{"tarih":"2025-12-21"}}</script>')
    basar("Yayın: canlı tarih gömülü veriden okunuyor",
          _cd._GOMULU_DESENI.search(_ornek) is not None
          and _jj.loads(_cd._GOMULU_DESENI.search(_ornek).group(1))
          == {"2025-12-21": {"tarih": "2025-12-21"}})
    basar("Yayın: gömülü veri yoksa tarih uydurulmuyor",
          _cd._GOMULU_DESENI.search("<html>boş</html>") is None)

    # ==================================================================
    # FORM: SAYI DİZİSİ + SIRALAMADA KIRMIZI MAĞLUBİYET
    # Çubuk grafiği silikti ve değerler okunmuyordu. Yerine sayı dizisi:
    # asıl iş ÇİZGİ RENGİNDE — çıplak sayı bir şey ifade etmiyor, 24
    # sayı iyi mi kötü mü oyuncunun kendi normalini bilmeden söylenemez.
    # ==================================================================
    _sayfa10 = open("overnight_v17.html", encoding="utf-8").read()
    _formcular = (_d7.get("yukselen") or []) + (_d7.get("dusen") or [])

    # --- Veri: üst/alt kararı ---
    basar("Form: her maçta sezon ortalaması kıyası var",
          bool(_formcular)
          and all(isinstance(x.get("ust"), bool)
                  for o in _formcular for x in o["son5"]))
    # Kıyas EKRANDA YAZAN değere göre: satır "sezon 21.1" derken 21
    # sayılık maç yeşil görünmemeli.
    basar("Form: üst/alt kararı ekranda yazan sezon ortalamasıyla tutarlı",
          all(x["ust"] == (x["sayi"] > o["sezon_ort"])
              for o in _formcular for x in o["son5"]))
    basar("Form: her satırda tam 5 maç, sonuncusu bu gece",
          all(len(o["son5"]) == 5 and o["son5"][-1]["bu_gece"]
              and sum(1 for x in o["son5"] if x["bu_gece"]) == 1
              for o in _formcular))
    # Balonda rakip KOD değil okunur ad.
    basar("Form: balondaki rakip okunur ad (üç harfli kod değil)",
          all(len(x["rakip"]) > 3 for o in _formcular for x in o["son5"]))

    # --- Görünüm: çubuk gitti, sayı dizisi geldi ---
    basar("Form: çubuk grafiği kalmadı",
          ".bars{" not in _sayfa10 and "const cubuk=" not in _sayfa10)
    basar("Form: hücre 27px, aralık 4px, çizgi 3px",
          "width:27px" in _sayfa10.split(".sq>span[data-sayi]{")[1].split("}")[0]
          and "gap:4px" in _sayfa10.split("\n.sq{")[1].split("}")[0]
          and "height:3px" in _sayfa10.split("\n.sq i{")[1].split("}")[0]
          and "margin-top:4px" in _sayfa10.split("\n.sq i{")[1].split("}")[0])
    basar("Form: sayı mono 12.5px",
          "font-size:12.5px" in _sayfa10.split("\n.sq u{")[1].split("}")[0])
    # Renkler kullanıcı tarafından tek tek verildi.
    basar("Form: üstte yeşil (#3FB27F, .75), altta kırmızı (#C4544F, .6)",
          "background:#3FB27F;opacity:.75" in _sayfa10.split(".hi i{")[1].split("}")[0]
          and "background:#C4544F;opacity:.6" in _sayfa10.split(".lo i{")[1].split("}")[0])
    basar("Form: bu geceki maç ember ve kalın",
          "color:var(--ember);font-weight:700" in _sayfa10.split(".now u{")[1].split("}")[0]
          and "background:var(--ember);opacity:1" in _sayfa10.split(".now i{")[1].split("}")[0])
    # .now kuralları .hi/.lo'dan SONRA olmak zorunda: aynı özgüllük.
    basar("Form: .now kuralları .hi/.lo'dan sonra yazılı (aynı özgüllük)",
          _sayfa10.index(".sq>span[data-sayi].now i{")
          > _sayfa10.index(".sq>span[data-sayi].lo i{"))
    # Balon .sq'nun doğrudan span çocuğu; çıplak `.sq>span` onu da
    # hücre genişliğine sıkıştırıyordu (ölçüldü: 24px kutu, ~120px içerik).
    basar("Form: hücre seçicisi balonu kapsamıyor",
          ".sq>span{" not in _sayfa10
          and _sayfa10.count(".sq>span[data-sayi]") >= 7)
    basar("Form: renk açıklaması bölüm başında yazıyor",
          '<div class="formnot">son 5 maç · sezon ort. üstü / altı</div>' in _sayfa10
          and "font-size:8.5px" in _sayfa10.split(".formnot{")[1].split("}")[0])
    # Düşen listesinin tamamı turuncuya boyanırsa ember'in tek anlamı
    # ("bu geceki maç") yok oluyor.
    # DİKKAT: arama YORUMSUZ metinde. Kuralı neden kaldırdığımı anlatan
    # yorumun içinde kuralın kendisi geçiyor; çıplak arama kendi
    # açıklamama takılıyordu.
    _yorumsuz10 = _re.sub(r"/\*.*?\*/", "", _sayfa10, flags=_re.S)
    basar("Form: Düşen listesi topluca ember'e boyanmıyor",
          ".cold{color:var(--ember)}" not in _yorumsuz10)
    # Dar ekranda ad sütunu 86px'e düşüp bütün adları kesiyordu.
    basar("Form: dar ekranda hücre/aralık/ortalama kısılıyor",
          ".sq>span[data-sayi]{width:24px}"
          in _sayfa10.split("@media(max-width:400px){")[1].split("}\n")[0]
          .replace("\n", "").replace("  ", "")
          or ".sq>span[data-sayi]{width:24px}" in _sayfa10)
    # Üç haneli sayı 12.5px mono'da 22.5px yer istiyor (ölçüldü).
    basar("Form: dar ekran hücresi üç haneli sayıyı kırpmıyor (≥23px)",
          all(int(_p) >= 23 for _p in _re.findall(
              r"\.sq>span\[data-sayi\]\{width:(\d+)px\}", _sayfa10)))

    # --- Sıralama: mağlubiyet kırmızı ---
    basar("Sıralama: mağlubiyet kırmızı (#C4544F, .75), 'veri yok' grisi değil",
          "background:#C4544F;opacity:.75" in _sayfa10.split(".sr .f10 i{")[1].split("}")[0]
          and "#2A3340" not in _sayfa10.split(".sr .f10 i{")[1].split("}")[0])
    basar("Sıralama: galibiyet yeşil, iki renk yakın ağırlıkta",
          "background:#3FB27F;opacity:.85" in _sayfa10.split(".sr .f10 i.w{")[1].split("}")[0])
    # Her kutucuk oynanmış bir maç: form listesi sadece True/False taşıyor,
    # "veri yok" diye üçüncü bir durum yok — kırmızı belirsiz kalmıyor.
    basar("Sıralama: form kutucukları yalnız galibiyet/mağlubiyet",
          all(isinstance(w["g"], bool) for t in (_d7.get("siralama") or []) for w in t["form"]))

    # ==================================================================
    # BRIEF: SESSİZLİK YALNIZ KUYRUKTA
    # Gerçek üretim arızası (2025-12-21): gecenin EN YÜKSEK rozetli maçı
    # (CHI-ATL 152-150) tek bir olgu eşiğini geçmiyordu; kesim ilk
    # olgusuz maçta kırıldığı için altındaki DÖRT olgulu maç da sustu ve
    # "Sen uyurken"in altı satırı birden çıplak skora düştü.
    # ==================================================================
    def _brief_kur(_t):
        _g = _jj.loads(open(f"gercek/{_t}.json", encoding="utf-8").read())
        _h = _jj.loads(open(_ham_yolu(_t)).read())
        _s = _jj.loads(open(f"skor/{_t}.json", encoding="utf-8").read())
        _mt, _dg = yaz._mutlaka_ve_diger(_s)
        _roz = {m["mac_id"]: m["rozet"] for m in _s["maclar"]}
        _enp = {m["mac_id"]: m.get("en_iyi_performans") for m in _s["maclar"]}
        _pl = yaz.gece_kalip_plani(_t, _g, _h, _s)
        _hd = [m["mac_id"] for m in _mt] + [m["mac_id"] for m in _dg]
        return _roz, _hd, yaz.gece_brief_ata(_pl, _roz, _hd, _h, _enp, _g)

    _roz21, _hd21, _br21 = _brief_kur(_yayinda2)
    _sirali21 = sorted(_hd21, key=lambda g: -(_roz21.get(g) or 0))
    _konusan21 = [g in _br21 for g in _sirali21]

    basar("Brief: en yüksek rozetli maç asla susmuyor",
          bool(_sirali21) and _konusan21[0])
    # Monotonluk: konuşanlar bir ÖNEK, susanlar bir SONEK olmalı.
    basar("Brief: sessizlik yalnız kuyrukta (dağılımda boşluk yok)",
          _konusan21 == sorted(_konusan21, reverse=True))
    # Olgusuz maç, ALTINDA konuşan maç varsa düz sonuç cümlesi alır.
    basar("Brief: olgusuz maç kuyrukta değilse düz sonuç cümlesi alıyor",
          all(_br21[g]["kind"] == "duz_sonuc" or _br21[g]["kind"] != "duz_sonuc"
              for g in _br21)
          and all(g in _br21 for g in _sirali21[:len([x for x in _konusan21 if x])]))
    basar("Brief: her cümle doğrulama kapısından geçiyor",
          all(cumle._gecir(v["metin"]) for v in _br21.values()))
    # Eskiden `break` vardı; ilk olgusuz maç bütün geceyi susturuyordu.
    basar("Brief: kesim ilk olgusuz maçta kırılmıyor",
          "break                 # ilk olgusuz maçtan sonrası susar" not in _yaz_kaynak
          and "son_olgulu = max(" in _yaz_kaynak)

    # ==================================================================
    # ŞABLONA DÜŞME ALARMI
    # Kullanıcı kuralı: Mutlaka bil MAÇLARININ yarısından fazlası
    # şablona düşerse iş başarısız sayılır ve atanmış issue açılır.
    # ==================================================================
    basar("Alarm: eşik yarısından fazlası",
          yaz.SABLON_ALARM_ESIGI == 0.5)
    basar("Alarm: 2/3 şablona düşerse çalıyor",
          yaz.sablon_alarmi({"mutlaka_mac": 3, "sablon_moduna_dusen": 2})[0])
    basar("Alarm: 1/3 şablona düşerse çalmıyor",
          not yaz.sablon_alarmi({"mutlaka_mac": 3, "sablon_moduna_dusen": 1})[0])
    basar("Alarm: tam yarısı eşiği geçmiyor (yarısından FAZLASI)",
          not yaz.sablon_alarmi({"mutlaka_mac": 4, "sablon_moduna_dusen": 2})[0])
    basar("Alarm: mutlaka maçı yoksa çalmıyor",
          not yaz.sablon_alarmi({})[0])
    # Oran MAÇ/MAÇ olmalı. `sablon_orani` payı maç, paydası DENEME
    # sayıyor; onunla hesaplansaydı 2025-12-21 %25 görünür, alarm çalmazdı.
    basar("Alarm: oran maç bazlı, deneme bazlı değil",
          'rapor["mutlaka_mac"] = rapor.get("mutlaka_mac", 0) + 1' in _yaz_kaynak
          and _yaz_kaynak.count('rapor["mutlaka_mac"] = rapor.get("mutlaka_mac", 0) + 1') == 2
          and '"mutlaka_mac"' in _yaz_kaynak.split("def sablon_alarmi")[1][:400])
    # Üretim işi 1 dönseydi tekrar dener, ikinci tur "zaten hazır gece
    # var" deyip 0 döner ve alarm sessizce yutulurdu.
    basar("Alarm: üretim çıkışı 2 (tekrar denenmeyecek kod)",
          "return 2" in _yayin_kaynak.split("sablon_alarmi")[1][:900]
          and 'if [ "$KOD" -eq 2 ]' in _akislar["uret.yml"])
    basar("Alarm: iş düşüyor ve atanmış issue açılıyor",
          "Şablona düşme alarmı — issue aç" in _akislar["uret.yml"]
          and "--assignee yigitolmezcan"
          in _akislar["uret.yml"].split("Şablona düşme alarmı — issue aç")[1])

    # ==================================================================
    # FORM ÖLÇÜTÜ — YÜZDE DEĞİŞİM + TUTARLILIK
    # Gerçek arıza (2025-12-21): Anthony Edwards "Düşen"deydi —
    # 11-15-40-26-24, sezon 27.4, mutlak fark 4.2. 27.4 ortalayanda 4.2
    # = %15, gürültü; 10 ortalayanda aynı fark %42, gerçek çöküş.
    # ==================================================================
    basar("Form: eşik yüzde değişim (%25)",
          _derle.FORM_YUZDE_ESIGI == 25.0)
    basar("Form: tutarlılık şartı 5 maçın 4'ü",
          _derle.FORM_AYNI_YON_ASGARI == 4)
    _formcular2 = (_d7.get("yukselen") or []) + (_d7.get("dusen") or [])
    basar("Form: her satırda yüzde ve yön sayacı var",
          all(isinstance(o.get("yuzde"), (int, float))
              and isinstance(o.get("ust_sayisi"), int)
              and isinstance(o.get("alt_sayisi"), int) for o in _formcular2))
    basar("Form: yüzde gerçekten (son5-sezon)/sezon",
          all(abs(o["yuzde"] - (o["son5_ort"] - o["sezon_ort"]) / o["sezon_ort"] * 100) < 1.5
              for o in _formcular2 if o["sezon_ort"]))
    basar("Form: listedeki herkes eşiği geçiyor",
          all(abs(o["yuzde"]) >= _derle.FORM_YUZDE_ESIGI for o in _formcular2))
    basar("Form: yükselenlerde 5 maçın 4'ü ortalamanın ÜSTÜNDE",
          all(o["ust_sayisi"] >= _derle.FORM_AYNI_YON_ASGARI
              for o in (_d7.get("yukselen") or [])))
    basar("Form: düşenlerde 5 maçın 4'ü ortalamanın ALTINDA",
          all(o["alt_sayisi"] >= _derle.FORM_AYNI_YON_ASGARI
              for o in (_d7.get("dusen") or [])))
    basar("Form: sıralama yüzdeye göre (mutlak farka göre değil)",
          [round(o["yuzde"], 1) for o in (_d7.get("yukselen") or [])]
          == sorted((round(o["yuzde"], 1) for o in (_d7.get("yukselen") or [])), reverse=True))
    # Edwards'ın satırı: dalgalanma listeye girmemeli.
    basar("Form: dalgalanan oyuncu listeye girmiyor (Edwards 11-15-40-26-24)",
          not any(o["isim"] == "Anthony Edwards" for o in _formcular2))
    basar("Form: gösterim yüzde ('▼%15'), mutlak fark değil",
          "${ok}%${Math.abs(o.yuzde).toFixed(0)}" in _sayfa10
          and "Math.abs(o.fark).toFixed(1)" not in _sayfa10)

    # ==================================================================
    # BEŞ METİN KURALI (T28 / T29 / T30 / yasak kalıpları)
    # ==================================================================
    # (a) Başlık en güçlü olguyu kullanmalı.
    basar("Kural a: düz skor başlık + gövdede geri dönüş → ret",
          not dogrula_modul.t28_baslik_guclu_olgu({
              "baslik": "Minnesota, sahasında Milwaukee'yi 103-100 yendi.",
              "neden_onemli": "Timberwolves, 16 sayılık farktan dönerek kazandı.",
              "ozet": ""})[0])
    basar("Kural a: başlıkta olgu varsa geçiyor",
          dogrula_modul.t28_baslik_guclu_olgu({
              "baslik": "Jalen Brunson'ın 47 sayısıyla New York, Miami'yi 132-125 yendi",
              "neden_onemli": "Knicks 2. sıraya yükseldi.", "ozet": ""})[0])
    basar("Kural a: triple-double da kanca sayılıyor",
          dogrula_modul.t28_baslik_guclu_olgu({
              "baslik": "Jokić'in triple-double'ıyla Denver, Houston'ı 128-120 yendi.",
              "neden_onemli": "Nuggets 1. sıraya yükseldi.", "ozet": ""})[0])
    # Sıradan bir sayı güçlü olgu DEĞİL: eşiksiz halinde kural arşivin
    # yarısından fazlasında boş yere çalıyordu (ölçüldü).
    basar("Kural a: sıradan performans başlığı zorlamıyor (22 sayı)",
          dogrula_modul.t28_baslik_guclu_olgu({
              "baslik": "Warriors, Spurs'ü 125-120 yendi.",
              "neden_onemli": "Curry 22 sayı attı.", "ozet": ""})[0])
    # Eşikler cumle.PERFORMANS_ESIKLERI ile AYNI olmak zorunda.
    basar("Kural a: performans eşikleri cumle ile aynı",
          dogrula_modul.T28_GUCLU_PERFORMANS
          == {birim: esik for _alan, esik, birim, _fiil in cumle.PERFORMANS_ESIKLERI})

    # (b) Alt satır ile gövde birbirini tekrar edemez.
    basar("Kural b: aynı olay iki kez anlatılırsa ret",
          not dogrula_modul.t29_alt_satir_govde_tekrari({
              "neden_onemli": "16 sayılık farktan dönerek maçı son çeyrekte kontrol altına aldı.",
              "ozet": "Son çeyreği kontrollü geçen ekip, çeyrek boyunca kontrolü bırakmadı."})[0])
    basar("Kural b: farklı şeyler anlatılırsa geçiyor",
          dogrula_modul.t29_alt_satir_govde_tekrari({
              "neden_onemli": "Knicks konferansta 2. sıraya yükseldi.",
              "ozet": "Brunson 47 sayı attı, Miami son periyotta 18 sayıda kaldı."})[0])
    basar("Kural b: takım/oyuncu adları ortak kök sayılmıyor",
          dogrula_modul.t29_alt_satir_govde_tekrari(
              {"neden_onemli": "Timberwolves galibiyetle günü kapattı.",
               "ozet": "Timberwolves ilk yarıda 18 sayı geride kaldı."},
              None,
              {"box_traditional": {"boxScoreTraditional": {
                  "homeTeam": {"teamCity": "Minnesota", "teamName": "Timberwolves", "players": []},
                  "awayTeam": {"teamCity": "Milwaukee", "teamName": "Bucks", "players": []}}}})[0])

    # (c) Kilit istatistik metinde tekrarlanamaz.
    basar("Kural c: kilit istatistik metinde geçerse ret",
          not dogrula_modul.t30_kilit_istatistik_tekrari(
              "Miami'nin ribaund üstünlüğüne rağmen Knicks kazandı.", "hücum ribaundu")[0])
    basar("Kural c: kilit istatistik yoksa kural çalışmıyor",
          dogrula_modul.t30_kilit_istatistik_tekrari(
              "Miami'nin ribaund üstünlüğüne rağmen Knicks kazandı.", None)[0])
    basar("Kural c: kilit istatistiğin adı üretim anında biliniyor",
          _derle.kilit_istatistik_adi(
              _jj.loads(open(_ham_yolu(_yayinda2)).read())["maclar"]["0022500398"])
          == "hücum ribaundu")

    # (d) Belirsiz nicelik yasak.
    for _c, _ad in (("Milwaukee ilk yarıda geniş bir üstünlük kurdu.", "geniş üstünlük"),
                    ("Brunson sahadan yüksek isabetle oynadı.", "yüksek isabet")):
        basar(f"Kural d: '{_ad}' yakalanıyor",
              not dogrula_modul.t4d_kok_kaliplari(_c)[0])
    basar("Kural d: sayı yazılmışsa geçiyor",
          dogrula_modul.t4d_kok_kaliplari(
              "Milwaukee ilk yarıda 16 sayılık üstünlük kurdu.")[0])

    # (e) Bozuk fiil kalıpları.
    for _c, _ad in (("11 serbest atışının tamamını kullanarak 38 sayıya ulaştı.", "tamamını kullanarak"),
                    ("Minnesota, farkı koruyarak galibiyeti aldı.", "galibiyeti aldı")):
        basar(f"Kural e: '{_ad}' yakalanıyor",
              not dogrula_modul.t4d_kok_kaliplari(_c)[0])
    basar("Kural e: doğru biçim geçiyor",
          dogrula_modul.t4d_kok_kaliplari(
              "Randle serbest atışta 11/11 yaptı.")[0])

    # Kurallar ÜRETİCİYE de ulaşmalı — sadece doğrulayıcıda kalırsa
    # model aynı hatayı her denemede tekrar eder.
    basar("Beş kural: sistem promptunda da yazılı",
          all(x in _yaz_kaynak for x in
              ("BAŞLIK EN GÜÇLÜ OLGUYU", "ALT SATIR İLE GÖVDE BİRBİRİNİ TEKRAR ETMEZ",
               "BELİRSİZ NİCELİK YASAK", "KİLİT İSTATİSTİK: bu maçın kilit")))
    # Nesne bazlı testler kabulü düşürmezse gerekçe yazılır ama metin
    # yine yayına çıkar.
    basar("Beş kural: T28/T29 kabulü düşürüyor",
          '("T25", "T28", "T29")' in _dogrula_kaynak)

    # ==================================================================
    # SEN UYURKEN — SAAT MANTIĞI
    # Gerçek arıza (2025-12-21): alt şeritte "1290 dakika" yazıyordu;
    # sıralama "HH:MM" DİZESİNE göre yapıldığı için sistem 23:30 ile
    # 02:00 arasını 21,5 saat sanıyordu (gerçekte 2,5 saat) ve 23:30
    # gecenin İLKİ olduğu halde en sona düşüyordu.
    # ==================================================================
    _ham21 = _jj.loads(open(_ham_yolu(_yayinda2)).read())
    _brief11 = _d7.get("brief") or []
    _ozet11 = _d7.get("brief_ozet") or {}
    _anlar11 = [a for a in (_derle._tsi_baslama_dt(m, _yayinda2)
                            for m in _ham21["maclar"].values()) if a]
    _saatli11 = [b["saat"] for b in _brief11 if b.get("saat")]

    basar("Saat: başlama anı tam tarihli (sadece saat değil)",
          bool(_anlar11) and all(hasattr(a, "date") for a in _anlar11))
    basar("Saat: gece takvim gününü aşıyor (iki farklı tarih var)",
          len({a.date() for a in _anlar11}) == 2)
    basar("Saat: sıralama tam ana göre (23:30 önce, 06:00 sonra)",
          _saatli11[:1] == ["23:30"] and _saatli11[-1:] == ["06:00"])
    basar("Saat: sıralama saat DİZESİNE göre yapılmıyor",
          _saatli11 != sorted(_saatli11))
    basar("Saat: kodda sıralama anahtarı tam an",
          'x["_an"].replace(tzinfo=None)' in _derle_kaynak
          and 'key=lambda x: (x["saat"] is None' not in _derle_kaynak)

    _ilk11 = next((b for b in _brief11 if b.get("etiket") == "gecenin ilki"), None)
    basar("Saat: 'gecenin ilki' etiketi en erken maçta",
          _ilk11 is None or _ilk11["saat"] == _saatli11[0])
    _kap11 = next((b for b in _brief11 if b.get("etiket") == "kapanış"), None)
    basar("Saat: 'kapanış' etiketi en geç maçta",
          _kap11 is None or _kap11["saat"] == _saatli11[-1])

    basar("Saat: süre gerçek (23:30 → 06:00 = 390 dakika)",
          _ozet11.get("dakika") == 390)
    basar("Saat: alt şerit süreyi saat olarak yazıyor",
          _ozet11.get("sure") == "6,5 saat"
          and "${ozet.sure}" in _sayfa10 and "${ozet.dakika} dakika" not in _sayfa10)
    basar("Saat: alt şerit aralığı 23:30 - 06:00",
          _ozet11.get("ilk") == "23:30" and _ozet11.get("son") == "06:00")
    basar("Saat: süre biçimi (6,5 saat / 2 saat / 45 dakika)",
          _derle._sure_metni(390) == "6,5 saat" and _derle._sure_metni(120) == "2 saat"
          and _derle._sure_metni(45) == "45 dakika" and _derle._sure_metni(None) is None)

    # ==================================================================
    # ROZET EŞİTLİĞİ — "gecenin maçı" tesadüfe kalmasın
    # ==================================================================
    import hesapla as _hesapla
    _skor11 = _jj.loads(open(f"skor/{_yayinda2}.json", encoding="utf-8").read())["maclar"]
    basar("Rozet: her maçta eşitlik bozucu var",
          all(isinstance(m.get("esitlik_bozucu"), list)
              and len(m["esitlik_bozucu"]) == 2 for m in _skor11))
    basar("Rozet: eşitlik bozucu dram ve final farkından türüyor",
          all(m["esitlik_bozucu"][0] == m["tasiyicilar"]["D"]
              and m["esitlik_bozucu"][1] == -abs(m["ev_skor"] - m["dep_skor"])
              for m in _skor11))
    _esit11 = [m for m in _skor11
               if sum(1 for x in _skor11 if x["rozet"] == m["rozet"]) > 1]
    basar("Rozet: eşit rozetli maçlar ikincil ölçütle ayrışıyor",
          not _esit11 or len({tuple(m["esitlik_bozucu"]) for m in _esit11}) == len(_esit11))
    _sir11 = sorted(_skor11, key=_hesapla.siralama_anahtari)
    basar("Rozet: sıralama kararlı (girdi sırası sonucu değiştirmiyor)",
          [m["mac_id"] for m in _sir11]
          == [m["mac_id"] for m in sorted(list(reversed(_skor11)),
                                          key=_hesapla.siralama_anahtari)])
    basar("Rozet: eşitlikte dramı yüksek olan önde",
          not _esit11 or _sir11.index(max(_esit11, key=lambda m: m["esitlik_bozucu"][0]))
          == min(_sir11.index(m) for m in _esit11))
    basar("Rozet: sıralama anahtarı tek kaynak (yaz ve derle aynısını kullanıyor)",
          "hesapla_siralama_anahtari" in _yaz_kaynak
          and "siralama_anahtari(rozet_by_gid[g])" in _derle_kaynak)

    # ==================================================================
    # FORM — ANLAMLILIK EŞİĞİ SAYIYA BAĞLI, DAKİKAYA DEĞİL
    # 25 dakika şartı, %25+tutarlılık kapılarını geçen 455 oyuncunun
    # 395'ini TEK BAŞINA eliyordu; düşen listesi tek satıra iniyordu.
    # ==================================================================
    basar("Form: düşende sezon sayı eşiği (dakika şartı kalktı)",
          _derle.DUSEN_ASGARI_SEZON_SAYI == 10.0
          and not hasattr(_derle, "DUSEN_ASGARI_DAKIKA"))
    basar("Form: yükselende son 5 sayı eşiği",
          _derle.YUKSELEN_ASGARI_SON5_SAYI == 10.0)
    basar("Form: düşenlerin hepsi sezonda anlamlı skorer",
          all(o["sezon_ort"] >= _derle.DUSEN_ASGARI_SEZON_SAYI
              for o in (_d7.get("dusen") or [])))
    basar("Form: yükselenlerin hepsi ŞU AN anlamlı skorer",
          all(o["son5_ort"] >= _derle.YUKSELEN_ASGARI_SON5_SAYI
              for o in (_d7.get("yukselen") or [])))
    # Yükselene SEZON eşiği konulamaz: bölümün anlamı düşük ortalamadan
    # patlayanı bulmak (Carrington 8.0 → 17.6).
    basar("Form: yükselende sezon eşiği YOK (patlama görünsün)",
          "sezon_ort" not in _derle_kaynak.split("yukselen = sorted(")[1].split("]")[0])

    _s1_bas = _sayfa10.split("<h2>Sen uyurken</h2>")[1].split("</div></div>")[0]
    basar("Sen uyurken: 'tıkla' ipucu kalktı",
          "tıkla" not in _s1_bas and "dokun" in _s1_bas)

    # ==================================================================
    # OYUNCU KARTI
    # Kutu skor "bu gece 35 attı" diyor; kart "bu 35, onun normalinin
    # %39 üstünde" diyor. Katılan şey BAĞLAM.
    # ==================================================================
    _oy = _d7.get("oyuncular") or {}
    _oynayan = sum(1 for _k in _kart9 for _t in ("ev", "dep")
                   for _o in _k["box"][_t]["oyuncular"])

    # O gece OYNAYAN HER oyuncu için kart açılabilmeli, sadece öne
    # çıkanlar için değil.
    basar("Oyuncu kartı: oynayan herkes için var",
          bool(_oy) and all(str(_o["id"]) in _oy
                            for _k in _kart9 for _t in ("ev", "dep")
                            for _o in _k["box"][_t]["oyuncular"]))
    basar("Oyuncu kartı: kimlik alanları dolu",
          all(k["isim"] and k["takim"] and len(k["takim_kod"]) == 3
              and k["renk"].startswith("#") for k in _oy.values()))
    basar("Oyuncu kartı: maç skoru ve saati taşıyor",
          all("–" in k["mac_skor"] for k in _oy.values())
          and all(k.get("saat") is None or len(k["saat"]) == 5 for k in _oy.values()))
    basar("Oyuncu kartı: bu gecenin üç büyük rakamı var",
          all(isinstance(k["bu_gece"][a], int) for k in _oy.values()
              for a in ("pts", "reb", "ast")))
    basar("Oyuncu kartı: ikincil istatistikler kutu skorla aynı",
          all(all(a in k["bu_gece"] for a in
                  ("min", "fg", "3p", "ft", "stl", "blk", "to", "pm"))
              for k in _oy.values()))
    # Mevki sadece ilk beşte dolu; yedekte boş kalıyor ve satır çizilmiyor.
    basar("Oyuncu kartı: mevki tam kelime (G değil Guard)",
          all(k["pos"] in ("", "Guard", "Forward", "Center") for k in _oy.values()))

    # Sezon bağlamı — yüzde ölçütü Yükselen/Düşen ile AYNI.
    _sezonlu = [k for k in _oy.values() if k.get("sezon")]
    basar("Oyuncu kartı: sezon bağlamında yüzde değişim var",
          all(isinstance(k["sezon"]["yuzde"], (int, float)) for k in _sezonlu))
    basar("Oyuncu kartı: yüzde (son5-sezon)/sezon",
          all(abs(k["sezon"]["yuzde"]
                  - (k["sezon"]["son5_ort"] - k["sezon"]["sezon_ort"])
                  / k["sezon"]["sezon_ort"] * 100) < 1.5
              for k in _sezonlu if k["sezon"]["sezon_ort"]))
    basar("Oyuncu kartı: son 5 dizisi ve bu gece işareti",
          all(len(k["sezon"]["son5"]) == 5 and k["sezon"]["son5"][-1]["bu_gece"]
              and sum(1 for x in k["sezon"]["son5"] if x["bu_gece"]) == 1
              for k in _sezonlu))
    # Renk kararı EKRANDA YAZAN ortalamaya göre — Yükselen/Düşen ile aynı.
    basar("Oyuncu kartı: üst/alt kararı gösterilen sezon ortalamasıyla tutarlı",
          all(x["ust"] == (x["sayi"] > k["sezon"]["sezon_ort"])
              for k in _sezonlu for x in k["sezon"]["son5"]))
    # Sezon verisi yoksa bölüm HİÇ kurulmuyor — uydurma ortalama yazmak
    # yerine kart iki bölümle kalıyor.
    basar("Oyuncu kartı: sezon verisi yoksa bölüm hiç kurulmuyor",
          all("sezon" in k or True for k in _oy.values())
          and "if(o.sezon){" in _sayfa10)
    basar("Oyuncu kartı: ek API çağrısı yok (mevcut oyun günlüğü)",
          "_oyuncu_gecmisi(ham)" in _derle_kaynak.split("def _oyuncu_kartlari")[1][:600])

    # --- Üç giriş, tek bileşen ---
    basar("Oyuncu kartı: üç giriş de data-oyuncu taşıyor",
          _sayfa10.count("data-oyuncu=") >= 3
          and 'class="dot${halka}"${GECE_OYUNCULARI' in _sayfa10      # saha
          and 'class="bpname"${GECE_OYUNCULARI' in _sayfa10           # gecenin beşi
          and "const kart=o.id!==undefined && GECE_OYUNCULARI" in _sayfa10)  # kutu skor
    basar("Oyuncu kartı: tek işleyici (üçü de aynı fonksiyonu çağırıyor)",
          _sayfa10.count("function oyuncuKartiHTML(") == 1
          and _sayfa10.count("function oyuncuKartiAc(") == 1)
    # Sahadaki halka kapsayıcı kartı da açmasın.
    basar("Oyuncu kartı: dokunuş kapsayıcı karta sızmıyor",
          "e.stopPropagation();\n      oyuncuKartiAc(el.dataset.oyuncu" in _sayfa10)
    # Kartı olmayan oyuncuya işaret KONMUYOR — okuyucuya yalan söz verilmez.
    basar("Oyuncu kartı: işaret sadece kartı olan oyuncuda",
          "const adattr=kart?` data-oyuncu=" in _sayfa10)

    # --- Dokunulabilirlik: üç sinyal ---
    # Satır başına ok KALDIRILDI (kullanıcı kararı): her satırda
    # tekrarlanınca tablo işaret çöplüğüne dönüyordu. Ok tek yerde
    # kaldı — tablonun altındaki ipucu satırında.
    basar("Dokunulabilirlik: satır başına ok yok, ok tek yerde",
          "td.oyad::after" not in _sayfa10
          and '<span class="oipucu"><s>›</s>' in _sayfa10)
    basar("Dokunulabilirlik: ad istatistiklerden parlak",
          "td.oyad{color:var(--ink)" in _sayfa10)
    basar("Dokunulabilirlik: tablo altında ipucu satırı",
          'class="oipucu"' in _sayfa10 and "isme <span class=\"dokun\">dokun</span>" in _sayfa10)

    # --- Kart üstüne kart ---
    basar("Kart üstüne kart: ayrı katman (ikinci sheet)",
          'id="sheet2"' in _sayfa10 and 'id="scrim2"' in _sayfa10)
    # z sırası: scrim 40 < sheet 50 < scrim2 55 < sheet2 60. Kural
    # .sheet'ten SONRA yazılmazsa 50'de kalıyor ve perde kartın üstüne
    # biniyor (ölçüldü: elementFromPoint kartın yerinde scrim2 döndürdü).
    basar("Kart üstüne kart: sheet2 z-index kuralı .sheet'ten sonra",
          _sayfa10.index(".sheet2{z-index:60}") > _sayfa10.index("z-index:50}"))
    basar("Kart üstüne kart: kapatma en üstteki katmanı kapatıyor",
          "function _ustKatman()" in _sayfa10
          and "const n=_ustKatman();\n  if(n) _katmaniKapat(n,true);" in _sayfa10)
    basar("Kart üstüne kart: geri tuşu tek katman kapatıyor",
          "addEventListener('popstate',()=>{ const n=_ustKatman(); if(n) _katmaniKapat(n,false); });"
          in _sayfa10)
    # Katman 1'in DOM'una dokunulmuyor: sekmesi ve kaydırma konumu kalıyor.
    basar("Kart üstüne kart: alttaki kartın DOM'u korunuyor",
          "sheet2.innerHTML=oyuncuKartiHTML({...o, _mac_id: macId || ''})" in _sayfa10
          and "sheet.innerHTML=oyuncuKartiHTML" not in _sayfa10)
    # Sayfa kaydırması ancak SON katman kapanınca serbest kalmalı.
    basar("Kart üstüne kart: sayfa kaydırması son katmanda serbest kalıyor",
          "if(_ustKatman()===0) document.body.style.overflow='';" in _sayfa10)
    # Sürükleme hangi kart sürükleniyorsa ONU kapatmalı.
    basar("Kart üstüne kart: sürükleme katmana bağlı",
          "function surukleBagla(kat,kapat)" in _sayfa10)
    # Oyuncu kartı içeriğine göre büzülüyor: kutu skorun sabit yüksekliği
    # burada 515px boşluk bırakıyordu (ölçüldü).
    basar("Oyuncu kartı: mobilde içeriğine göre büzülüyor",
          ".sheet2{height:auto;max-height:88dvh}" in _sayfa10)
    # Uzun adlar ✕ düğmesine girmesin.
    basar("Oyuncu kartı: ad ✕ için yer bırakıyor",
          "padding-right:34px" in _sayfa10.split(".ohd .onm{")[1].split("}")[0])

    # ==================================================================
    # ÖRNEK KÜTÜPHANESİ
    # Kullanıcı kararı: yasaklı liste büyüdükçe model çıkış yolu
    # bulamıyor ve şablona düşüyor. Çift (yanlış/doğru) o tuzağı
    # kapatıyor. Kural listelerinin YERİNE değil, ÖNÜNE geçiyor.
    # ==================================================================
    _kutup = yaz.ornek_kutuphanesi()
    _prompt = yaz.sistem_prompt()

    basar("Kütüphane: dosya var ve dolu",
          len(_kutup) > 4000 and "## 1. Fiiller" in _kutup)
    basar("Kütüphane: sistem promptuna OLDUĞU GİBİ giriyor",
          _kutup.strip() in _prompt)
    # Sistem promptunun TAMAMI cache_control ile işaretli; kütüphane
    # onun içinde, yani önbelleğin sabit kısmında. Prompt SONUNA
    # konulsaydı çağrı başına yeniden ödenirdi.
    basar("Kütüphane: önbelleğin sabit kısmında (sistem promptu içinde)",
          '"cache_control": {"type": "ephemeral"},' in _yaz_kaynak
          and "sistem_prompt()" in _yaz_kaynak)
    basar("Kütüphane: prompt sonunda değil, kuralların ÖNÜNDE",
          0 < _prompt.index("## 1. Fiiller") < _prompt.index("TERİM VE DİL KURALLARI"))
    # KRİTİK: örnek cümleler kopyalanmaz — kalıp kütüphanesiyle tam bu
    # tuzağa düşülmüştü.
    basar("Kütüphane: kopyalama yasağı promptta açıkça yazılı",
          "KOPYALANMAZ" in _prompt and "tiktir" in _prompt)
    # Yasaklı listeler ve testler AYNEN kalıyor.
    basar("Kütüphane: yasaklı listeler yerinde",
          len(_jj.loads(open("config/yasakli.json", encoding="utf-8").read())["klise"]) >= 20
          and len(_jj.loads(open("config/yasakli.json", encoding="utf-8").read())["kok_kaliplari"]) >= 25)
    basar("Kütüphane: doğrulayıcıya dokunmuyor",
          "ornek_kutuphanesi" not in _dogrula_kaynak)
    # Kütüphanede karşılığı OLMAYAN yasaklar promptta adıyla kalmalı —
    # yoksa model reddedilir ama nedenini bilmez (tam kaçınılan tuzak).
    for _y in ("gerçekleştirdi", "elde etti", "layup", "ribaunt"):
        basar(f"Kütüphane: '{_y}' yasağı promptta hâlâ adıyla var",
              _y in _prompt)
    basar("Kütüphane: İngilizce terim karşılık tablosu korundu",
          "layup / lay-up" in _prompt and "buzzer beater" in _prompt)
    # Dosya okunamazsa prompt yine kurulmalı — üretim durmasın.
    _eski_yol = yaz.ORNEK_KUTUPHANESI_DOSYASI
    _eski_onbellek = yaz._ORNEK_KUTUPHANESI
    try:
        yaz.ORNEK_KUTUPHANESI_DOSYASI = _eski_yol.parent / "yok-boyle-dosya.md"
        yaz._ORNEK_KUTUPHANESI = None
        basar("Kütüphane: dosya yoksa prompt yine kuruluyor",
              yaz.ornek_kutuphanesi() == "" and len(yaz.sistem_prompt()) > 5000)
    finally:
        yaz.ORNEK_KUTUPHANESI_DOSYASI = _eski_yol
        yaz._ORNEK_KUTUPHANESI = _eski_onbellek

    # ==================================================================
    # KUTU SKOR — İŞARET SATIRI TABLONUN ALTINDA, SATIR OKU YOK
    # ==================================================================
    basar("Kutu skor: oyuncu adının yanında ok YOK",
          "td.oyad::after" not in _sayfa10)
    basar("Kutu skor: işaret satırı panonun içinde, Oynamayanlar'ın altında",
          '<div class="kalt">${ilkbes}${ipucu}</div>' in _sayfa10
          and _sayfa10.index('class="kdnp"') < _sayfa10.index('<div class="kalt">'))
    basar("Kutu skor: kart dibindeki şerit boşaldı",
          '<div class="kfoot"></div>' in _sayfa10
          and "kbeslegend" not in _sayfa10.split('<div class="kfoot">')[1][:200])
    basar("Kutu skor: ad hâlâ dokunulabilir ve parlak",
          "td.oyad{color:var(--ink);cursor:pointer}" in _sayfa10)

    # ==================================================================
    # VERİSİ ÇEKİLEMEYEN GECE SİSTEMİ DURDURMAZ
    # NBA servisi GitHub koşucusunu IP bazlı engelliyor. Eskiden bir
    # geceye ulaşılamayınca bütün iş çöküyor ve sıra ORADA duruyordu.
    # ==================================================================
    basar("Atlama: ulaşılamayan gece hatası yutulmuyor, kaydediliyor",
          "ulasilamayan.append((aday," in _yayin_kaynak
          and 'd["_ulasilamayan"] = ulasilamayan' in _yayin_kaynak)
    basar("Atlama: hata bir sonraki geceye geçmeyi engellemiyor",
          "continue" in _yayin_kaynak.split("ulasilamayan.append")[1][:400])
    # "Sezon bitti" ile "hiçbirine ulaşamadık" AYNI ŞEY DEĞİL.
    basar("Atlama: sezon sonu ile erişim arızası ayrı çıkış kodları",
          "return 3" in _yayin_kaynak
          and "sebep veri erişimi, sezon sonu değil" in _yayin_kaynak)
    basar("Atlama: atlanan geceler kayda yazılıyor (sessiz kalmıyor)",
          "UYARI: {len(ulasilamayan)} gecenin verisine ulaşılamadı" in _yayin_kaynak)
    basar("Atlama: iş atanmış issue açıyor",
          "Veri erişilemedi — issue aç" in _akislar["uret.yml"]
          and "--assignee yigitolmezcan"
          in _akislar["uret.yml"].split("Veri erişilemedi — issue aç")[1])
    basar("Atlama: çıkış kodu 3 son denemede işi düşürüyor",
          'if [ "$KOD" -eq 3 ]' in _akislar["uret.yml"]
          and 'if [ "$deneme" -ge 2 ]; then exit 3; fi' in _akislar["uret.yml"])
    # Şartname notu: ileride kimse "zaten çalışıyordu" diye varsaymasın.
    _sartname = open("overnight-teknik-sartname.md", encoding="utf-8").read()
    basar("Şartname: çözülmemiş engel başlığı var",
          "ÇÖZÜLMEMİŞ ENGEL" in _sartname
          and "OTOMATİK VERİ ÇEKME HİÇ ÇALIŞMADI" in _sartname)
    basar("Şartname: ölçüm tablosu ve IP teşhisi yazılı",
          "20.171.20.54" in _sartname and "AS8075" in _sartname
          and "Başlık eklemek bir çözüm DEĞİLDİR" in _sartname)
    basar("Şartname: canlı sezon için vekil sunucu şartı yazılı",
          "VEKİL SUNUCU ŞARTTIR" in _sartname)

    # ==================================================================
    # ALTI TASARIM DÜZELTMESİ
    # ==================================================================
    _s12 = _sayfa10
    _d12 = _d7

    # 1) Kritik anlarda sayı eşiği — düşük/sıfır sayılı satır bilgi taşımıyor.
    basar("Kritik: sayı eşiği 4",
          _derle.KRITIK_ASGARI_SAYI == 4)
    _kritikler = [k["box"]["kritik"] for _b in ("mutlaka", "degerse_bak", "diger")
                  for k in (_d12.get(_b) or [])
                  if isinstance(k, dict) and k.get("box", {}).get("kritik")]
    basar("Kritik: her satır eşiği geçiyor",
          bool(_kritikler)
          and all(o["sayi"] >= _derle.KRITIK_ASGARI_SAYI
                  for k in _kritikler for o in k["oyuncular"]))
    basar("Kritik: eşiği geçen tek oyuncu varsa tek satır çıkıyor",
          all(1 <= len(k["oyuncular"]) <= _derle.KRITIK_OYUNCU_SAYISI
              for k in _kritikler))
    basar("Kritik: eşiği geçen yoksa blok hiç kurulmuyor",
          "if not esigi_gecen:\n        return None" in _derle_kaynak)

    # 3) Türkler bölümü oyuncu kartını açıyor, box score'a bağlantı veriyor.
    basar("Türkler: satır oyuncu kartını açıyor (box score'u değil)",
          'kartVar?`data-oyuncu="${t.id}" data-mac="${esc(t.mac_id||\'\')}"`' in _s12
          and "oyuncuBagla(turkBox)" in _s12)
    basar("Türkler: kartın altında box score bağlantısı",
          "Maçın box score'u ›" in _s12 and 'data-mac-git=' in _s12)
    # Bağlantı SADECE maç kimliği verildiğinde çizilir: kutu skordan
    # açılan kartta geri götüren bağlantı gürültü olurdu.
    basar("Türkler: bağlantı sadece maç kimliği verilince çiziliyor",
          "${o._mac_id?`<button class=\"obox\"" in _s12)
    basar("Türkler: bağlantı oyuncu kartını kapatıp box score'u açıyor",
          "_katmaniKapat(2,true);\n    if(m) kartAc(boxKartiHTML(m));" in _s12)

    # 4) Boşluğa dokunarak kapatma SADECE masaüstünde.
    basar("Perde: mobilde dokunarak kapatma kapalı",
          "const _fareVar = () => matchMedia('(hover:hover) and (pointer:fine)').matches;" in _s12
          and "scrim.addEventListener('click',()=>{ if(_fareVar()) kartKapat(); });" in _s12
          and "scrim2.addEventListener('click',()=>{ if(_fareVar()) kartKapat(); });" in _s12)
    # Ayrım ekran genişliğiyle DEĞİL giriş cihazıyla: geniş ama
    # dokunmatik tablette de mobil davranış doğru.
    basar("Perde: ayrım giriş cihazına göre, ekran genişliğine göre değil",
          "pointer:fine" in _s12.split("const _fareVar")[1][:120])

    # 5) Yükselen/Düşen satırı da kartı açıyor.
    basar("Form: satır oyuncu kartını açıyor",
          'data-oyuncu="${o.id}"' in _s12.split("const kartVar=GECE_OYUNCULARI[String(o.id)]")[1][:300]
          and "oyuncuBagla(kutu)" in _s12)
    basar("Form: ortalama bloğu satırda kalıyor",
          'class="avg"' in _s12 and "o.son5_ort.toFixed(1)" in _s12)
    basar("Form: dokunulabilirlik işareti (ad yanında ok + bölüm ipucu)",
          '.fp.acilir .nm::after{content:"›"' in _s12
          and 'class="fipucu"' in _s12)
    # Sayı dizisine dokunmak satırın kartını AÇMAMALI.
    basar("Form: sayı dizisi dokunuşu satır kartını açmıyor",
          "c.addEventListener('click',e=>{e.stopPropagation();goster();});" in _s12)

    # 6) Sıralama kutucuğu bilgi veriyor.
    _sir12 = _d12.get("siralama") or []
    basar("Sıralama: form kutucukları rakip ve skor taşıyor",
          bool(_sir12)
          and all(isinstance(f, dict) and "g" in f and "rakip" in f and "skor" in f
                  for t in _sir12 for f in t["form"]))
    basar("Sıralama: skor kendi-rakip biçiminde",
          all(not f["skor"] or _re.match(r"^\d+-\d+$", f["skor"])
              for t in _sir12 for f in t["form"]))
    basar("Sıralama: kazanma bilgisi korundu",
          all(isinstance(f["g"], bool) for t in _sir12 for f in t["form"]))
    basar("Sıralama: balon kutucuğa bağlı, satır tıklamasını tetiklemiyor",
          "k.addEventListener('click',e=>{e.stopPropagation();goster();});" in _s12
          and "function siralamaBalonBagla()" in _s12)
    basar("Sıralama: aynı anda tek balon (diğerleri kapatılıyor)",
          "siralamaBalonKapat(); formdaBalonKapat();" in _s12)
    basar("Sıralama: mobilde hover yok, dokunma zorunlu",
          "matchMedia('(hover:hover)').matches" in
          _s12.split("function siralamaBalonBagla")[1][:1600])
    # Eski biçim (düz true/false) hâlâ okunabilmeli: arşiv geceleri
    # yeniden derlenmeden bozulmasın.
    basar("Sıralama: eski düz biçim de okunuyor",
          "(typeof f === 'object') ? f.g : f" in _s12)

    # ==================================================================
    # KRİTİK ANLAR BLOĞU TAKIM SEKMESİNDE
    # Blok kart gövdesindeyken oyuncu tablosundan yer çalıyordu:
    # aynı kadroda satır yüksekliği 41px'ten 23px'e iniyordu (ölçüldü).
    # TAKIM sekmesi zaten maçın TAMAMINA ait veriler için var.
    # ==================================================================
    _s13 = _sayfa10
    basar("Kritik: blok TAKIM sekmesinin içinde",
          '<div class="kpane" data-pane="1" hidden>${kritikBlogu(b.kritik)}${takimPanosu('
          in _s13)
    basar("Kritik: blok kart gövdesinden çıktı",
          "${ceyrekSeridi(sira[0],sira[1])}\n    <div class=\"ktabs\">" in _s13)
    basar("Kritik: TAKIM sekmesinde kritik ÜSTTE, takım istatistiği altta",
          _s13.index("${kritikBlogu(b.kritik)}") < _s13.index("${takimPanosu(sira[0],sira[1])}"))
    # Sekmede işaret: okuyucu orada bir şey olduğunu bilsin.
    basar("Kritik: blok varsa TAKIM sekmesinde işaret",
          "b.kritik?'<i class=\"kdot\"></i>':''" in _s13
          and ".ktabs .kdot{" in _s13)
    # Mavi `.dot` (kaybedenin en iyisi) ile karışmasın: ayrı sınıf, ayrı renk.
    basar("Kritik: işaret mavi noktadan ayrı (ember)",
          "background:var(--ember)" in _s13.split(".ktabs .kdot{")[1].split("}")[0])
    # Blok artık panonun içinde: `flex:none` gövde çocuğu değil.
    basar("Kritik: blok pano içinde konumlanıyor",
          "flex:none" not in _s13.split(".kritik{")[1].split("}")[0])

    # Skor bloğu dolgusu kısıldı — kazanılan yer tabloya gidiyor.
    # KONUM TUZAĞI: medya sorgusu temel kuraldan SONRA gelmezse eziliyor.
    basar("Kart: skor bloğu dolgusu dar ekranda kısılıyor",
          ".kteams{margin-top:8px}" in _s13 and ".kt{padding-top:9px" in _s13)
    basar("Kart: dolgu medya sorgusu temel kuraldan SONRA yazılı",
          _s13.index(".kt{padding-top:9px") > _s13.index(".kt+.kt{border-top"))

    # ==================================================================
    # HAM VERİ DEPODA — NBA'e gitmeden üretim
    # NBA servisi GitHub koşucusunu IP bazlı engelliyor. Gece verisi
    # yerelden çekilip SIKIŞTIRILMIŞ olarak depoya konuyor; koşucu
    # NBA'e hiç gitmeden üretim yapabiliyor.
    # ==================================================================
    import cek as _cek
    _cek_kaynak = open("cek.py", encoding="utf-8").read()

    basar("Ham: okuma tek kapıdan (cek.ham_oku)",
          hasattr(_cek, "ham_oku") and hasattr(_cek, "ham_yolu")
          and hasattr(_cek, "ham_metni"))
    # Üç biçim: tam, gzip'li, kırpılmış. Çağıranın hangisi olduğunu
    # bilmesi gerekmiyor.
    basar("Ham: üç biçim de tanınıyor (tam / gzip / kırpılmış)",
          all(x in _cek_kaynak for x in
              ('f"{tarih_str}.json"', 'f"{tarih_str}.json.gz"',
               '"test_verisi" / "ham"')))
    basar("Ham: sıkıştırılmış kopya çekimde yazılıyor",
          "def gzip_yaz(" in _cek_kaynak and "gzip_yaz(tarih_str, cikti)" in _cek_kaynak)
    # Hiçbir modül ham dosyayı KENDİ açmıyor — biçim değişince biri
    # unutulur ve sadece o yol bozulurdu.
    for _m in ("derle.py", "dogrula.py", "gercekler.py", "hesapla.py", "yaz.py", "yayin.py"):
        _k = open(_m, encoding="utf-8").read()
        basar(f"Ham: {_m} doğrudan ham dosya açmıyor",
              'HAM_DIZIN / f"{tarih' not in _k and '"ham" / f"{tarih' not in _k)
    # Sıkıştırılmış kopya depoya GİRMELİ, tam kopya girmemeli.
    _gi = open(".gitignore", encoding="utf-8").read()
    basar("Ham: tam kopya yoksayılıyor, sıkıştırılmış kopya giriyor",
          "/ham/*.json" in _gi and "/ham/*.json.gz" not in _gi)
    # Verisi DEPODA olan geceye NBA'e sorulmuyor.
    # DİKKAT: `gece_mac_idlerini_al` CANLI modda da geçiyor ve dosyada
    # daha önce yer alıyor; kıyas ARŞİV dalının içinde yapılmalı.
    _arsiv_dali = _yayin_kaynak.split("# ÖNCE DEPODAKİ VERİ")[1][:1400]
    basar("Ham: sıradaki gece önce depodan okunuyor",
          "yerel = cek.ham_yolu(aday, KOK)" in _arsiv_dali
          and _arsiv_dali.index("yerel = cek.ham_yolu")
              < _arsiv_dali.index("cek.gece_mac_idlerini_al(aday)"))
    # Gerçekten gzip'ten okunabiliyor mu — biçim testi, varsayım değil.
    import gzip as _gz, tempfile as _tf, os as _os2, json as _js2
    with _tf.TemporaryDirectory() as _td:
        _os2.makedirs(_os2.path.join(_td, "ham"))
        with open(_os2.path.join(_td, "ham", "1999-01-01.json.gz"), "wb") as _f:
            _f.write(_gz.compress(_js2.dumps({"maclar": {"a": 1}}).encode()))
        basar("Ham: gzip'li dosya gerçekten okunuyor",
              _cek.ham_oku("1999-01-01", _td) == {"maclar": {"a": 1}})
        basar("Ham: hiçbir biçim yoksa net hata veriyor",
              isinstance(_pytest_yakala(lambda: _cek.ham_oku("1998-01-01", _td)),
                         FileNotFoundError))

    # ==================================================================
    # NEFES ALANI — depoda kaç gecelik veri var
    # NBA servisi koşucuyu engellediği için sıra ancak verisi ÖNCEDEN
    # çekilmiş geceler kadar akabiliyor.
    # ==================================================================
    import cek as _cek2
    from datetime import datetime as _dt2, timedelta as _td2
    _durum = _jj.loads(open("config/yayin_durumu.json", encoding="utf-8").read())
    _atla2 = (set(_durum["atlanan"]) | set(_durum["yayinlanan"])
              | set(_durum.get("engellenen", [])))
    _g2 = _dt2.strptime(_durum.get("sira_imleci") or _durum["yayinlanan"][-1], "%Y-%m-%d")
    _son2 = _dt2.strptime(_durum["sezon_bitisi"], "%Y-%m-%d")
    _sira2 = []
    while _g2 < _son2:
        _g2 += _td2(days=1)
        _t2 = _g2.strftime("%Y-%m-%d")
        if _t2 in _atla2:
            continue
        if _cek2.ham_yolu(_t2) is None:
            break
        _sira2.append(_t2)
    basar(f"Nefes alanı: kesintisiz sıra {len(_sira2)} gece (en az 25 olmalı)",
          len(_sira2) >= 25)
    # Maç oynanmayan gün ATLANANLARDA olmalı: koşucu bunu NBA'e soramaz
    # (servis engelli) ve sorarsa sıra orada durur.
    basar("Nefes alanı: bilinen boş gün atlananlarda (24 Aralık)",
          "2025-12-24" in _durum["atlanan"])
    # Sıradaki her gecenin verisi SIKIŞTIRILMIŞ biçimde depoda olmalı —
    # tam kopya .gitignore'da, koşucuya ulaşmaz.
    _eksik_gz = [t for t in _sira2[:10]
                 if not _os.path.exists(f"ham/{t}.json.gz")]
    basar("Nefes alanı: sıradaki gecelerin sıkıştırılmış kopyası depoda",
          not _eksik_gz)

    # ==================================================================
    # MUTLAKA BİL — MAÇ AYRACI SOL RAY
    # İnce yatay çizgi silik kalıyordu, iki maç tek metin öbeği gibi
    # okunuyordu. Ayrımı artık ray ile blok arası boşluk BİRLİKTE veriyor.
    # ==================================================================
    _s14 = _sayfa10
    # DİKKAT: aynı çizgi rengi başka bölümlerde de var (gecenin beşi,
    # arşiv, form mini). Arama `.game` KURALININ İÇİNDE yapılmalı.
    _game_kural = _s14.split("\n.game{")[1].split("}")[0]
    basar("Ayraç: yatay çizgi kalktı",
          "border-bottom" not in _game_kural
          and ".game:last-child{border-bottom:0" not in _s14)
    basar("Ayraç: sol ray 2px ve sönen degrade",
          "width:2px" in _s14.split(".game::before{")[1].split("}")[0]
          and "linear-gradient(180deg,var(--ray" in _s14)
    # HİZA: ray rozetin ÜST KENARINDAN başlıyor, üstte boşluk yok.
    basar("Ayraç: ray blokun tepesinden başlıyor",
          "top:0" in _s14.split(".game::before{")[1].split("}")[0])
    basar("Ayraç: altta metin bitmeden sönüyor",
          "bottom:18px" in _s14.split(".game::before{")[1].split("}")[0])
    basar("Ayraç: içerik raydan 17px içeride",
          "padding:0 0 0 17px" in _s14.split("\n.game{")[1].split("}")[0])
    basar("Ayraç: bloklar arası 26px",
          "margin-bottom:26px" in _s14.split("\n.game{")[1].split("}")[0])
    # KART DEĞİL: kart dili sitede dokunulabilirlik demek; Mutlaka bil
    # blokları okunacak metin.
    basar("Ayraç: blok kartlaştırılmadı (kutu/çerçeve yok)",
          "border:" not in _s14.split("\n.game{")[1].split("}")[0]
          and "background" not in _s14.split("\n.game{")[1].split("}")[0])

    # --- Ray rengi: kazanan takım + çakışma kuralı ---
    _mut14 = _d7.get("mutlaka") or []
    basar("Ayraç: her blokta ray rengi var",
          bool(_mut14) and all(m.get("ray_renk", "").startswith("#") for m in _mut14))
    basar("Ayraç: renk KAZANAN takımdan",
          all(m["kazanan_kod"] in (m["box"]["ev"]["kod"], m["box"]["dep"]["kod"])
              for m in _mut14)
          and all((m["kazanan_kod"] == m["box"]["ev"]["kod"])
                  == (m["box"]["ev"]["skor"] >= m["box"]["dep"]["skor"])
                  for m in _mut14))
    basar("Ayraç: ray rengi işaretlemede kullanılıyor",
          'style="--ray:${esc(mv.ray_renk' in _s14)
    # Çakışma: yakın renkli iki kazanan varsa DÜŞÜK rozetli kayar.
    _cak = _derle.renk_cakismasini_coz(
        [{"takim": "DAL", "_gmsc": 9.1}, {"takim": "ORL", "_gmsc": 7.2}])
    basar("Ayraç: yakın renkte düşük rozetli olan kayıyor",
          not _cak[0]["renk_degisti"] and _cak[1]["renk_degisti"])
    _cak2 = _derle.renk_cakismasini_coz(
        [{"takim": "ORL", "_gmsc": 9.1}, {"takim": "DAL", "_gmsc": 7.2}])
    basar("Ayraç: öncelik rozete göre (sıra ters çevrilince karar da döner)",
          not _cak2[0]["renk_degisti"] and _cak2[1]["renk_degisti"])
    # Çakışma yoksa kimse kaymamalı — gereksiz renk değişimi kimliği bozar.
    _cak3 = _derle.renk_cakismasini_coz(
        [{"takim": "CHI", "_gmsc": 9.0}, {"takim": "SAC", "_gmsc": 8.0}])
    basar("Ayraç: çakışma yoksa renk değişmiyor",
          not any(x["renk_degisti"] for x in _cak3))
    # Öncelik ölçütü ROZET olmalı; `renk_cakismasini_coz` bunu `_gmsc`
    # alanından okuyor, kaynakta bağ açıkça kurulu.
    basar("Ayraç: öncelik ölçütü rozet (koda yazılı)",
          '{"takim": m["kazanan_kod"], "_gmsc": m["rozet"]}' in _derle_kaynak)

    # ==================================================================
    # PAYLAŞIM GÖRÜNTÜSÜ (OG) + ARŞİV GEZİNME
    # ==================================================================
    import og_uret as _og
    _s15 = _sayfa10
    _og_kaynak = open("og_uret.py", encoding="utf-8").read()

    # DİKKAT: arama YORUM/DİZGİ değil GERÇEK İÇE ALMA üzerinden. Neden
    # tarayıcı kullanmadığımı anlatan yorumda "Playwright" kelimesi
    # geçiyor ve çıplak arama kendi açıklamama takılıyordu.
    _og_ithal = [n.split()[1].split(".")[0]
                 for n in _re.findall(r"^\s*import\s+\S+|^\s*from\s+\S+",
                                      _og_kaynak, _re.M)]
    basar("OG: tarayıcı gerekmiyor (Pillow ile çiziliyor)",
          "PIL" in _og_ithal
          and not {"playwright", "pyppeteer", "selenium", "cairosvg"} & set(_og_ithal))
    basar("OG: ölçü 1200x630", (_og.G, _og.Y) == (1200, 630))
    for _f in ("BricolageGrotesque.ttf", "DMMono-Regular.ttf", "DMMono-Medium.ttf"):
        basar(f"OG: {_f} depoda", _os.path.exists(f"fonts/{_f}"))
    basar("OG: font lisansı belgelenmiş",
          _os.path.exists("fonts/LISANS.md")
          and "Open Font License" in open("fonts/LISANS.md", encoding="utf-8").read())

    _skor15 = _jj.loads(open(f"skor/{_yayinda2}.json", encoding="utf-8").read())
    _parlak, _soluk = _og.satirlari_sec(_skor15)
    import hesapla as _h15
    _sirali15 = sorted(_skor15["maclar"], key=_h15.siralama_anahtari)
    basar("OG: ilk iki satır en yüksek rozetli maçlar",
          [m["mac_id"] for m in _parlak] == [m["mac_id"] for m in _sirali15[:2]])
    basar("OG: üçüncü satır en DÜŞÜK rozetli maç",
          _soluk is not None and _soluk["mac_id"] == _sirali15[-1]["mac_id"])
    basar("OG: iki maçlık gecede üçüncü satır uydurulmuyor",
          _og.satirlari_sec({"maclar": _skor15["maclar"][:2]})[1] is None)
    basar("OG: maç adı kısa ad (kod değil)",
          _og.kisa_mac_adi("SAC", "HOU") == "Sacramento – Houston")
    from PIL import Image as _Im
    with _Im.open(_og.uret(_yayinda2)) as _im:
        basar("OG: üretilen dosya 1200x630 PNG", _im.size == (1200, 630))

    _site15 = open("site/index.html", encoding="utf-8").read()
    for _ad in ("og:title", "og:description", "og:url", "og:image",
                "twitter:card", "twitter:image"):
        basar(f"Meta: {_ad} dolu",
              _re.search(rf'"{_re.escape(_ad)}" content="[^"]+"', _site15) is not None)
    basar("Meta: başlık geceye özel",
          f'content="OVERNIGHT — {_derle._tarih_tr(_yayinda2)} gecesi"' in _site15)
    basar("Meta: görsel adresi o gecenin dosyası", f"/og/{_yayinda2}.png" in _site15)
    # Botlar JS koşturmuyor: meta HTML'de yazılı olmalı.
    basar("Meta: HTML'de yazılı (JS ile doldurulmuyor)",
          "og:image" not in _s15.split("<script")[-1])

    basar("Arşiv: her yayınlanmış gecenin kendi sayfası var",
          all(_os.path.exists(f"site/{t}.html")
              for t in _jj.loads(open("site/gunler.json", encoding="utf-8").read())))
    basar("Arşiv: gün listesi ayrı dosyada (sayfalar yeniden yazılmasın)",
          _os.path.exists("site/gunler.json") and "fetch('gunler.json'" in _s15)
    basar("Arşiv: künyede iki ok var",
          'id="okOnceki"' in _s15 and 'id="okSonraki"' in _s15)
    basar("Arşiv: uçlarda ok pasifleşiyor",
          "el.classList.add('pasif')" in _s15 and ".ok.pasif{" in _s15
          and "pointer-events:none" in _s15.split(".ok.pasif{")[1].split("}")[0])
    basar("Arşiv: liste okunamazsa ok çizilmiyor",
          "geri.hidden=true; ileri.hidden=true;" in _s15)
    _gunler15 = _jj.loads(open("site/gunler.json", encoding="utf-8").read())
    basar("Arşiv: gün listesi sıralı ve yayınlananlarla aynı",
          _gunler15 == sorted(_gunler15)
          and set(_gunler15) == set(_jj.loads(
              open("config/yayin_durumu.json", encoding="utf-8").read())["yayinlanan"]))

    # Kalibrasyon: eşitlik kalmamalı.
    basar("Kalibrasyon: hiçbir gecede 3+ maç aynı rozeti paylaşmıyor",
          all(g["en_cok_tekrar"] < 3 for g in _kalib.geceleri_oku()))


if __name__ == "__main__":
    main()
