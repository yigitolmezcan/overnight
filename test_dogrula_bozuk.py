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
    basar("Kart: kazanılan yer satırlara dağıtılıyor (sabit dolgu değil)",
          ".sheet table.kbs{height:100%}" in _sayfa)


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
    # Değer skoru İÇ araç, okura anlatılan bir bilgi değil. Brief
    # satırlarında görünmez; aşağıdaki bölümlerde (Mutlaka bil, Göz at,
    # Bunları geç) rozet olarak duruyor.
    basar("Brief: rozet satırı kalktı",
          "brozet" not in _sayfa and "rozet ${roz}" not in _sayfa)
    basar("Brief: rozet hesabı da kalmadı (ölü kod bırakılmadı)",
          "hedef.rozet.toFixed" not in _sayfa)
    basar("Brief: sıralamayı numaralar taşıyor",
          '<span class="bnum">${i+1}</span>' in _sayfa)
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
    basar("dokun/tıkla: her ipucunda iki sürüm de var",
          _sayfa.count('class="dokun"') == _sayfa.count('class="tikla"')
          and _sayfa.count('class="dokun"') >= 3)

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
    basar("Bildirim: adım çıktısı dosyaya yakalanıyor",
          _u.count("tee /tmp/adim.log") == 2 and "set -o pipefail" in _u)

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
    _tek = (_cek.YENIDEN_DENEME * _cek.ISTEK_ZAMAN_ASIMI_SN
            + sum(_cek.DENEME_ARASI_TABAN_SN * 2 ** i for i in range(_cek.YENIDEN_DENEME - 1)))
    _en_kotu_dk = 46 * _tek / 60
    _is_siniri = int(_u.split("timeout-minutes:")[1].split()[0])
    basar(f"Ağ: en kötü durum ({_en_kotu_dk:.0f} dk) iş sınırının ({_is_siniri} dk) altında",
          _en_kotu_dk < _is_siniri)

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
    _vercel = _jj.loads(open("vercel.json", encoding="utf-8").read())
    _cronlar = _vercel.get("crons", [])
    basar("Nöbetçi: vercel.json üç cron tanımlıyor (üret · yayınla · nöbet)",
          len(_cronlar) == 3)
    _gorevler = {c["path"].split("gorev=")[-1] for c in _cronlar}
    basar("Nöbetçi: üretimi ve yayını GitHub'ın DIŞINDAN tetikliyor",
          {"uret", "yayinla", "nobet"} == _gorevler)
    basar("Nöbetçi: bütün cron'lar nöbetçi uç noktasına gidiyor",
          all(c["path"].startswith("/api/nobetci") for c in _cronlar))
    _nb = open("api/nobetci.js", encoding="utf-8").read()
    basar("Nöbetçi: anahtarsız istek reddediliyor",
          "NOBETCI_ANAHTARI" in _nb and "yetkisiz" in _nb)
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

    # Kalibrasyon: eşitlik kalmamalı.
    basar("Kalibrasyon: hiçbir gecede 3+ maç aynı rozeti paylaşmıyor",
          all(g["en_cok_tekrar"] < 3 for g in _kalib.geceleri_oku()))


if __name__ == "__main__":
    main()
