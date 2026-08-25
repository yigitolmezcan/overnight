"""
dogrula.py'nin RET tarafını test eder — kasten bozulmuş cümleler.
Her biri ayrı bir T testini düşürmeli. Hepsi düşerse dogrula.py doğru
çalışıyor demektir.

Kullanım: python3 test_dogrula_bozuk.py
"""

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
    olgu_karar_ani = {"karar_ani": {"saniye_kalan": 1.0}}
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
    metin_dusuk_kaybeden = yaz.sablon_uret(gercekler_ind_cha, ham_ind_cha, "LaMelo Ball", None, kanca_harf="A", olgu={}, rozet=5.0)
    basar("rozet bütçesi: kaybeden takımın oyuncusu 'Mağlup tarafta' çerçevesiyle anılıyor", "Mağlup tarafta LaMelo Ball" in metin_dusuk_kaybeden)
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
    _n2 = cumle.neden_onemli(_mac, {"kazanan_derece": _kd, "karar_ani": {"saniye_kalan": 4.7}})
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
    basar("A4: birleşik ifade 've' ile tek parçada", "55 sayı ve 12 ribaundluk" in _r["baslik"])
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
          _bek4["metin"] == "Bu gece Türk oyuncu sahada yoktu. Şengün 24 Ekim'de, Bona 25 Ekim'de sahaya çıkıyor.")

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
          _bek["metin"] == "Bu gece Türk oyuncu sahada yoktu. Şengün 7 Mart'ta, Osman 9 Mart'ta sahaya çıkıyor.")

    _bek2 = _derle._turkler_bekleyen({"sonraki_maclar": {"HOU": "2026-03-07", "SAS": "2026-03-07"}}, _tk)
    basar("türkler: aynı gün oynayan iki oyuncu 've' ile tek tarihte birleşiyor",
          _bek2["metin"] == "Bu gece Türk oyuncu sahada yoktu. Şengün ve Osman 7 Mart'ta sahaya çıkıyor.")

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
    basar("html: başlık altı cümlesi güncellendi",
          "Molasız, reklamsız özet." in _html and "Sıraya senin yerine biz karar verdik" not in _html)


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
    basar("Maliyet: varsayılan olarak gecede tek maç LLM'e gidiyor",
          _yaz.MUTLAKA_LLM_MAC_SAYISI == 1)

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
    basar("Yayın durumu: emekli geceler yayın sırasına girmiyor",
          len(_d["atlanan"]) == 14 and "2026-03-05" in _d["atlanan"])
    basar("Yayın durumu: takılan geceler emekli listesinden AYRI tutuluyor",
          "engellenen" in _d or _d.get("engellenen") == [])


if __name__ == "__main__":
    main()
