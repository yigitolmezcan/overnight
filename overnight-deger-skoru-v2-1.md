# OVERNIGHT — Değer Skoru v2.1

**Ne değişti:** Ağırlıklı ortalama kaldırıldı. Üç taban kuralı kaldırıldı.
Tek skor yerine iki eksen geldi. Yapı, altı test maçında taban kuralı
kullanmadan doğru sıralamayı üretiyor.

---

## 0. Formülün gerçek işi

Bu formül **maçın kalitesini** ölçmüyor. Şunu ölçüyor:

> Bu maçı bilmezsem yarın pişman olur muyum?

Bu ayrım pratik sonuçlar doğuruyor. 49 sayı ile 50 sayı istatistiksel
olarak aynı, konuşma değeri olarak değil. Çöp zamanda gelen 18 sayı ile
son beş dakikada gelen 18 sayı aynı Game Score'u üretir, aynı pişmanlığı
üretmez. Formül boyunca ölçüt bu.

İkinci ilke: **skorun işi sıralamak değil, katmana atmak.** 9'un üstündeki
iki maç arasındaki fark gürültüdür; ikisi de "mutlaka bil" katmanındadır ve
aralarındaki sıra editoryal bir tercihtir. Formülü ondalık hassasiyette
haklı çıkarmaya çalışma.

---

## 1. İki eksen

Eski yapının en büyük kavram hatası, sakatlığı eğlence puanıyla aynı
cetvele koymaktı. Sakatlık maçı *okumaya değer* yapmaz, olayı *bilmeye
değer* yapar. Bunlar farklı şeyler ve farklı ürün davranışı gerektiriyor.

| Eksen | Ne sorar | Neyi belirler |
|---|---|---|
| **D — Değer skoru** | Bu maç zamanıma değer mi? | Maçın sayfadaki yeri, rozetteki sayı |
| **H — Haber skoru** | Bunu bilmem gerekir mi? | Uyarı işareti, "30 saniyede gece" satırı |

Bir maç D'si düşük H'si yüksek olabilir: iki kötü takımın tek taraflı
maçında yıldız oyuncu sakatlanmışsa maç "Bunları geç"te kalır ama başlığında
⚠ işareti taşır ve brief'te bir satırı olur. Tersi de olur: nefes kesen bir
maçta bilmen gereken hiçbir "haber" yoktur.

**H'nin D'yi yükseltmesi yasak.** Sakatlığın maçı "gecenin maçı" yapması
tam olarak kaçınmak istediğimiz şey.

---

## 2. Değer skoru — yapı

### Taşıyıcılar ve yükselticiler

Kritik ayrım: **bazı bileşenler bir maçı tek başına taşıyabilir, bazıları
taşıyamaz.**

**Taşıyıcılar** (0–10) — biri tek başına maçı zirveye çıkarabilir:

- **S** — Yıldız gecesi
- **K** — Kader / bahis
- **T** — Tarihilik / nadirlik
- **D** — Dram *(koşullu — aşağıya bak)*

**Yükselticiler** (0–10) — tek başına hiçbir şey ifade etmez, sadece çarpar:

- **Y** — Yakınlık (maç boyu gerilim)
- **F** — Final dramı (son 2 dakika)
- **G** — Geri dönüş
- **A** — Çekicilik (takım kalitesi + sahadaki yıldız ağırlığı)

### D — Dram taşıyıcısı (koşullu)

Yakınlık normalde çarpandır ve öyle kalıyor. Ama **uç dram taşıyıcıya
terfi eder.** Ayrım şu: "sıkıcı ama yakın" ile "iki alakasız takım
arasında nefes kesen bir maç" aynı şey değil, ve sadece çarpan
kullanmak ikisini ayırt edemiyor.

```
Eğer F ≥ 9 (son hücumda belli oldu)  VEYA  G ≥ 8 (15+ açık kapatılıp kazanıldı):
    D = max(F, G) − 2
    ve F ile G çarpandan düşürülür (çift sayılmasın)
Değilse:
    D = 0, F ve G normal çarpan olarak kalır
```

Eşik burada asıl işi yapıyor. F=8'lik bir maç (yakın ama son iki
dakikada karar verilmiş) terfi etmez ve dipte kalır; F=9 (son
hücumda belli olan maç) terfi eder.

Yakınlığın taşıyıcı olmaktan çıkarılması bilinçli. İki zayıf takımın 1
farkla biten, kimsenin 30 atmadığı maçı gerçekten geçilebilir bir maçtır —
senin de beşinci test vakasında istediğin buydu. Yakınlık var olan bir
sebebi büyütür, sebep yaratmaz.

### Hesap

```
0. Dram terfisi: F ≥ 9 veya G ≥ 8 ise D = max(F,G) − 2 ve F, G
   çarpandan düşülür. Değilse D = 0.

0b. S sönümlemesi — performans HANGİ MAÇTA atıldı?

   T > 0 ise            sönümleme YOK (tarihi performans istisnası)
   final fark ≤ 10      S ×1.00
   final fark 11–19     S ×0.90
   final fark 20–29     S ×0.80
   final fark 30+       S ×0.70

0c. A → K karışımı:  K = K + 0.20·A

1. Taşıyıcıları büyükten küçüğe sırala: C1 ≥ C2 ≥ C3  (S, K, T, D arasından)

   Taban = C1 + 0.30·C2 + 0.10·C3

2. Çarpan = 0.80 + 0.014·Y + 0.011·F + 0.010·G + 0.013·A
   (aralık: 0.80 – 1.28)

3. Zirve sönümlemesi — C1 yüksekse bağlam susar:

   C1, S veya T ise:   k = (C1 − 8.5) / 1.5   , 0 ile 0.7 arasına kırp
   C1, K veya D ise:   k = 0

   Çarpan_efektif = 1 + (Çarpan − 1) × (1 − k)

4. Ham = Taban × Çarpan_efektif        ← sıralama bununla yapılır

5. Rozet (ekranda görünen sayı):
   Ham ≤ 8   →  Rozet = Ham
   Ham > 8   →  Rozet = 8 + 2 × (1 − e^(−(Ham−8)/4))
```

**0b neden var:** Rozet "izlenmeye değer mi" diyor, "iyi oynadı mı"
demiyor. S bileşeni eskiden performansın hangi maçta atıldığına hiç
bakmıyordu — clutch ağırlığı yalnız "maçın en iyisi kim" SEÇİMİNDE
kullanılıyor, S'in değerine girmiyor. 41 farkla biten bir maçta atılan
33 sayı iyi bir performans olabilir ama o maçı izlemenin değeri düşük.

Fark büyüklüğü zaten rozeti YÜKSELTEMİYORDU (formüle yalnız F ve Y'den
giriyor, ikisi de yakınlığı ödüllendirir; T yalnız 50+ sayıya bakıyor).
Ölçüm: 29 gece, 217 maç, fark ↔ rozet korelasyonu −0.458 → −0.570.

**Tarihi performans istisnası (T > 0):** sönümlemenin amacı çöp zamanda
toplanan sayıyı ödüllendirmemek; tarihi bir performans o kategoriye
girmiyor. Adebayo'nun 83 sayısı 21 farkla biten bir maçta atıldı
(MIA 150–129 WAS) ve sönümleme onu 9.21'den 8.40'a indiriyordu. İstisna
ile 9.23'te kalıyor. Veri setinde T > 0 olan 7 maç var.

**0c neden var ve ORAN NEDEN 0.20:** A (takım kalitesi) yalnız çarpanda
vardı, çarpan da 0.80–1.28'e sıkışık. Katsayıyı ikiye katlamak bile iki
maç arasındaki boşluğu kapatmıyordu (LAC 131–90 SAC ile LAL 106–128 DET
arası 3.11 → 1.63). Taşıyıcıya karıştırmak çalışıyor çünkü taşıyıcı
tabana doğrudan giriyor, tavana takılmıyor.

ÖLÇÜLEN SINIR — kural: "A, sürpriz sonuç ve dram bileşenlerinin üstüne
çıkmasın."

| A→K oranı | A'nın K'ya katkısı (ort / EN ÇOK) | sürprizi geçiyor mu? |
|---|---|---|
| 0.20 | 1.00 / **1.82** | hayır (sürpriz tabanı 2.00) |
| 0.25 | 1.25 / **2.28** | **evet** |
| 0.35 | 1.76 / 3.19 | evet |

Sürpriz bonusu K'ya 2.00–4.00 ekliyor, dram taşıyıcı olduğunda ortalama
7.06. **0.20, sınırı çiğnemeyen en yüksek oran** — bu yüzden 0.20.

0.35 denendi: Detroit LAC'yi geçiyor ama gece başına tepe rozetin
sapması 0.45'ten 0.38'e düşüyor (geceler birbirine benzemeye başlıyor)
ve tepede A≥7 maç sayısı 9/29'dan 11/29'a çıkıyor.

**3. adım neden var:** 83 sayılık bir gece, maçın 21 farkla bitmiş olmasına
bakmaz. Tarihi bir bireysel performans bağlama muhtaç değildir. Ama yüksek
bahisli bir maç (K) dramla büyür — orada sönümleme uygulanmaz. Bu tek kural,
senin "80 sayı ne olursa olsun manşet" ilkeni tek bir taban kuralı eklemeden
sağlıyor.

**Tavan neden 1.0 değil 0.7 (2026-08-25 düzeltmesi):** Kural ilk yazıldığında
`k` 1.0'a kadar çıkabiliyordu. Bu, S=10 olan HER maçta çarpanı tamamen
siliyordu — `Çarpan_efektif` tam olarak 1 oluyor ve Y/F/G/A hiç sayılmıyordu.
Sonuç: taşıyıcıları aynı olan maçlar, dramları bambaşka olsa bile AYNI rozete
çöküyordu. 22 Ekim 2025'te dört maç birden 8.96 aldı; çarpanları 0.87 ile 1.08
arasında farklıydı ama hepsi sıfırla çarpıldı. Kuralın amacı bağlamı
ZAYIFLATMAKTI, YOK ETMEK değil — "83 sayı bağlama muhtaç değildir" demek
"bağlam hiç sayılmaz" demek değil. Tavan 0.7'ye çekildi: en uç durumda bile
çarpanın %30'u etkisini korur. Kalibrasyon (16 gece, 112 maç): aynı rozeti
3+ maçın paylaştığı gece sayısı 1/16'dan 0/16'ya indi.

**5. adım neden var:** Ham skorlar 12–14'e çıkabiliyor. Düz kırpma yapsak
gecenin en iyi dört maçı da 10.0 okur ve rozet ayırt etme gücünü kaybeder.
Bu sıkıştırma 8'in altını hiç bozmuyor, 8'in üstünü 8–10 bandına yayıyor ve
10'a asla ulaşmıyor. **Hiçbir maç 10 almaz — 10 teorik tavandır.** Bu ürün
için de iyi bir cümle.

---

## 3. Bileşenlerin ölçekleri

Her bileşen için hem hesap kuralı hem çapa tablosu var. Kalibrasyonda
kullanılacak olan çapa tablosu.

### S — Yıldız gecesi

Ham girdi: **GmSc+**, üç düzeltmeyle Game Score:

1. **Clutch ağırlığı** — son 5 dakikada fark ≤5 iken üretilen sayı, asist
   ve top çalma ×1.5 sayılır. (Play-by-play'de mevcut.) v1'in en büyük
   körlüğü buydu: maçı kimin kazandırdığını hiç görmüyordu.
2. **Mutlak + kişisel birlikte** — sadece sapmaya bakmak yanlış. 4 GmSc
   ortalayan yedeğin 18'i (+14) ile SGA'nın 25→38'i (+13) neredeyse aynı
   sapma, aynı hikâye değil.
   `S_ham = 0.60 × (lig geneli yüzdelik) + 0.40 × (kişisel z-skor yüzdeliği)`
3. **Eşik bonusu** — 50 sayı, triple-double, 20 ribaund, 10 üçlük, 5 blok:
   her biri +0.5, toplam en fazla +1.5. 49 ile 50 aynı değil çünkü
   ölçtüğümüz şey konuşma değeri.
4. **Yıldız katsayısı (Y★)** — Giannis'in 30 sayısı ile sıradan bir
   oyuncunun 30 sayısı aynı haber değildir. Bkz. aşağıdaki bölüm.

```
S = [0.60 × lig yüzdeliği + 0.40 × kişisel z yüzdeliği + eşik bonusu] × Y★
    (0–10 arasına kırpılır)
```

Sezon başı: kişisel ortalama yoksa geçen sezonla harmanla, `n/(n+10)`
ağırlığıyla bu sezona kay. Çaylakta pozisyon/rol ortalaması kullanılır.

| S | Karşılığı |
|---|---|
| 10 | Sezonun en iyi 2–3 performansından biri |
| 9 | 45–55 sayı, veya 30/15/10 tipi tam hakimiyet |
| 8 | 40 civarı verimli sayı, veya güçlü bir triple-double |
| 6 | 32–36 sayı, iyi verim |
| 4 | Sağlam ama sıradan bir yıldız gecesi |
| 2 | Gecenin en iyisi bile vasat |

### Y★ — Yıldız katsayısı

Elle tutulan bir liste. Sezonda 3-4 kez güncellenir. Formülleştirilmesi
gereken bir şey değil — kimin yıldız olduğunu sen zaten biliyorsun.

| Kademe | Katsayı | Kim | Kaç kişi |
|---|---|---|---|
| 1 — Küresel | ×1.20 | MVP seviyesi, adı basketbol bilmeyene bile tanıdık | 6–8 |
| 2 — Yıldız | ×1.08 | All-Star düzenlisi, All-NBA adayı | 20–25 |
| 3 — Tanınan | ×0.95 | İlk beş oynayan, adı bilinen oyuncu | varsayılan |
| 4 — Bilinmeyen | ×0.80 | Derin yedek, two-way, çoğu çaylak | — |

**Türkiye katsayısı.** Site Türkçe, dolayısıyla ölçek **senin okuyucunun
ünlü listesi** olmalı, Amerika'nınki değil. Şengün senin okuyucun için
1. kademedir, küresel sıralaması ne olursa olsun. Aynı şey EuroLeague'den
tanınan isimler için de geçerli — okuyucun Larkin'i, Micić'i tanır,
ortalama bir Amerikalı tanımaz. Bu liste iki ayrı sütun taşımalı:
küresel kademe ve Türkiye kademesi; hesapta **yüksek olan** kullanılır.

**İki koruma kuralı:**

1. **Y★ sadece S'ye uygulanır.** D, K, T ve çarpana bulaşmaz. Yoksa
   kötü bir Lakers maçı her yerden şişer.
2. **Elit performansta ceza kalkar.** Ham performans lig genelinde
   ilk %1'e giriyorsa Y★ en az 1.00 alınır. Yoksa bilinmeyen bir
   oyuncunun 45 sayılık gecesi bastırılırdı — oysa asıl haber odur.
   Katsayı ünlüyü yukarı çeker, bilinmeyeni aşağı itmez.

Neden gerekli: S'nin sapma yarısı düşük tabanlı oyuncuyu şişiriyordu.
Simons'ın 30'u kendi ortalamasına göre Giannis'in 30'undan daha büyük
bir sapma olabilir ve formül onu daha yukarı koyardı — tam tersi doğru.

Bunun bir yan etkisi var, farkında ol: **ünlüye ağırlık vermek ünlüyü
daha ünlü yapar.** Site, henüz ünlü olmamış oyuncuları sistematik olarak
az gösterir. 2. koruma kuralı bunu kısmen dengeliyor, tamamen değil.

### K — Kader / bahis

Bu bileşen **takvime bağlı.** Aynı maç Kasım'da 2, Nisan'da 8 olabilir.
v1'deki "sıralama etkisi takım ağırlığıyla örtüşüyor" gerekçesi bu yüzden
yarım doğruydu: takım ağırlığı *seviye* ölçer, K *marjinal fark* ölçer ve
tam da K'nın var olma sebebi olan durumlarda (Nisan'da 38–38 ile 37–39
aynı sıra için oynarken) örtüşme kaybolur.

| K | Karşılığı |
|---|---|
| 10 | Eleme: play-in, playoff kapanışı, sezonu bitiren maç |
| 8 | Nisan, sonucu doğrudan playoff/play-in yerini belirleyebilir |
| 6 | İlk dört / saha avantajı yarışında doğrudan rakipler |
| 4 | Aynı konferansta yakın iki takım, Mart |
| 2 | Sıralamaya dolaylı etki |
| 0 | İki takım da yarış dışı |

**Sürpriz sonuç katkısı (kullanıcı düzeltmesi).** Yukarıdaki tablo
SADECE maç ÖNCESİ beklentiyi (standings yakınlığı) ölçüyor — sonucun
kendisinin ne kadar sarsıcı olduğunu ölçen hiçbir bileşen yoktu. Somut
örnek: lig lideri OKC (26-5), 8 maçlık galibiyet serisi süren SAS'a
Noel gecesi kaybetti. Maç öncesi "kader" açısından sıradan bir maçtı
(iki takım aynı sıralama bandında değildi) ama SONUÇ ligin o haftaki
en önemli haberlerinden biriydi — K bunu 0 ölçüyordu, maç "Bunları
geç"e düşüyordu.

K'ya eklenen katkı **iki AYRI kavramdan** geliyor (`hesapla.
surpriz_katkisi_hesapla`) — kullanıcı düzeltmesi (2. tur): ilk sürüm
"kaybeden lig lideri/ilk-3" ve "belirgin kalite farkı"nı TEK bir
"sürpriz" başlığında topluyordu. Ama San Antonio (Batı'nın en
iyilerinden biri, kalite 7.0/10) OKC'yi (lig lideri) yendiğinde bu
sürpriz DEĞİL — iki güçlü takımın doğrudan çarpışması. İki ayrı
tetikleyici, ikisi de tetiklenebilir, katkılar toplanır:

| Kavram | Tetikleyici | Katkı |
|---|---|---|
| **Sürpriz** — kazananla kaybeden arasında belirgin kalite farkı VARSA (kaybeden İYİ_TAKIM_ESIGI'nin üstünde, kazanan KÖTÜ_TAKIM_ESIGI'nin altında) | Taban | +2 |
| | Kalite farkına orantılı ek | en fazla +2 |
| **Zirve maçı** — konferansta ilk 3'teki iki takım karşılaştıysa (kalite farkı şartı YOK) | Sıralara göre (1-1 en yüksek) | +4 ile +6 arası |

Takım kalitesi, A bileşeniyle AYNI kaynaktan (`hesapla.takim_kalite_puani`,
0-10 ölçek, eşikler de `hesapla.IYI_TAKIM_ESIGI`/`KOTU_TAKIM_ESIGI` —
kalıp_secici'nin sürpriz/zirve kanca seçimiyle AYNI eşikler) — iki ayrı
kalite tanımı olmasın diye. Katkı, K'nın geri kalanının aksine **ay
katsayısıyla çarpılmaz** — bir sonucun sarsıcılığı takvime göre
küçülmez. K yine de toplamda 10 ile sınırlı.

**Kalibrasyon notu.** İlk denenen ağırlıklar (+5/+3/+4/+2, tek "sürpriz"
başlığı altında) OKC'nin Noel gecesi SAS'a kaybını rozet 8.57'ye (K=8.6)
taşımıştı — "mutlaka" katmanına, üçüncü bir "mutlaka" adayı daha.
Kavramlar ayrılınca (SAS-OKC artık "zirve maçı", "sürpriz" değil) ve
ağırlıklar yeniden kalibre edilince aynı örnek K≈5.5, rozet≈6.45
veriyor — hâlâ "ikinci" katmanında, doğru etikette.

### T — Tarihilik

Ölçek **olayın sıklığının logaritması.** İnsan hafızası da böyle çalışıyor.

| T | Sıklık | Örnek |
|---|---|---|
| 10 | Tüm zamanlarda ilk 5, veya ilk kez | 83 sayı, ilk quadruple-double |
| 8 | On yılda birkaç kez | 70+ sayı, 30 ribaund |
| 6 | Sezonda birkaç kez | Franchise rekoru, çaylak rekoru |
| 4 | Ayda birkaç kez | Kariyer rekoru |
| 2 | Haftada birkaç kez | Sezon kişisel rekoru |
| 0 | Rutin | — |

### Y — Yakınlık (maç boyu)

Girdi: ortalama mutlak fark, lider değişimi sayısı, farkın ≤5 kaldığı süre.
Çöp zaman kuralın burada yaşıyor: **3. çeyrekten itibaren 20+ fark, geride
kalan takım son birkaç dakikada en az 10-0 civarı bir seri yapmadıysa maçı
"kapandı" sayar** — sert kesme yok, kademeli düşüş.

| Y | Karşılığı |
|---|---|
| 10 | Uzatma, veya son çeyrek boyunca fark ≤5 |
| 8 | Son 5 dakikaya fark ≤5 girildi |
| 6 | Son çeyreğe fark ≤8 girildi |
| 4 | 10–15 fark, hiç kopmadı |
| 2 | 3. çeyrekte koptu |
| 0 | 2. çeyrekte koptu |

### F — Final dramı (yeni)

**v1'in ikinci büyük körlüğü.** 108–104 biten yakın bir maçla, son saniye
üçlüğüyle biten 107–106 v1'de tamamen aynı puanı alıyordu. Basketbolda
ertesi gün en çok konuşulan tek an bu.

| F | Karşılığı |
|---|---|
| 10 | Son saniye galibiyet basketi, veya uzatmaya götüren basket |
| 8 | Son 30 saniyede öne geçme |
| 6 | Son 1 dakikada fark ≤3 |
| 3 | Son 2 dakikada fark ≤5 ama karar erken verildi |
| 0 | Son 2 dakika anlamsız |

### G — Geri dönüş

| G | Karşılığı |
|---|---|
| 10 | 20+ açığı kapatıp kazandı |
| 8 | 15+ açığı kapatıp kazandı |
| 6 | 20+ kapatıp yine de kaybetti, veya 10+ kapatıp kazandı |
| 3 | 10+ kapatıp kaybetti |
| 0 | Yok |

### A — Çekicilik

```
A = 0.5 × takım kalitesi + 0.5 × sahadaki yıldız ağırlığı
```

**Takım kalitesi.** Sezon başı sorununun çözümü, kayan ağırlığı değiştirmek
değil — yöntem doğru, girdi zayıftı. Geçen sezonun net rating'i kadro
değişimini görmez. Yerine **sezon öncesi bahis galibiyet hedefleri**: halka
açık, kadro hareketlerini zaten fiyatlamış ve geçen sezon verisinden belirgin
biçimde daha isabetli. Oradan `n/(n+20)` ile bu sezonun gerçek net rating'ine
kay.

**Sahadaki yıldız ağırlığı.** Yeni ve önemli. İnsanlar kötü Spurs'ü değil
Wembanyama'yı izliyor. Bu terim iki işi birden yapıyor:
- Kötü takımdaki yıldızı doğru şekilde yukarı çeker
- Yıldızın oynamadığı maçı otomatik olarak aşağı çeker — v1'de bunu yakalayan
  hiçbir şey yoktu, "GSW 6 oyuncu eksik" bilgisi formüle hiç girmiyordu

Bu, senin "NBA bireysel oyuncular ligidir" tezinin takım tarafındaki doğal
karşılığı.

---

## 4. Haber skoru (H)

Ayrı hesaplanır, D'yi asla etkilemez.

| Girdi | H |
|---|---|
| Yıldızın sezonu bitiren sakatlığı | 10 |
| Yıldızın uzun süreli sakatlığı | 8 |
| Rotasyon oyuncusunun ciddi sakatlığı | 5 |
| Kavga, toplu ihraç, disiplin olayı | 6 |
| Maçın sonucunu değiştiren tartışmalı karar | 6 |
| Uzun sakatlıktan dönüş, dikkat çeken debut | 4 |
| Uzun serinin bitmesi (10+ maç) | 3 |

**Ürün davranışı:**

- H ≥ 6 ise maç başlığı ⚠ işareti taşır, hangi katmanda olursa olsun
- H ≥ 6 ise "30 saniyede gece" bölümünde bir satır alır
- H yüksek + D düşük → maç yine "Bunları geç"te kalır, ama işaretli
- Dil **nötr**: kutlama tonu yok, "gecenin maçı" vurgusu yok
- Sakatlık maçı, D'si ne olursa olsun o günün manşeti seçilemez

---

## 5. Katmanlar

Rozet mutlak, **yerleşim geceye göre görelidir.** Bu ayrım önemli: üç taban
kuralı da 8.0–8.5'te otursaydı, aynı gece bir play-in maçı + bir sakatlık +
bir rekor olduğunda üç maç birden 8+ okur ve "üçünü bilmen yeter" vaadi
çökerdi.

| Rozet | Katman | Kural |
|---|---|---|
| 8.5+ | Mutlaka bil | **En fazla 3 maç.** Fazlası ikinci katmana düşer |
| 6.0 – 8.5 | İkinci kademe | Sayfada var, açık, ama kısa |
| < 6.0 | Bunları geç | Kapalı satır, box score bir tık uzakta |

**Üst sınır:** 8.5'i geçen dörtten fazla maç varsa (nadir), en yüksek üçü
kalır.

### Gecenin üç hali

Gerçek veriyle test edilince ortaya çıktı: **sıradan bir gecede hiçbir maç
8.5'i geçmiyor.** 2 Ocak 2026'da 10 maçın en iyisi 8.4'tü. 8.5+ bir gece
muhtemelen haftada bir.

Format hiç bozulmuyor — üç hal de **üç maç** gösteriyor. Değişen tek şey,
gecenin kendi karakterini söyleyip söylemediği:

| Hal | Koşul | Sayfada ne yazar |
|---|---|---|
| **Büyük gece** | en iyi maç 8.5+ | Not yok, bölüm normal akar |
| **Sıradan gece** | en iyi maç 6.5 – 8.5 | *"Sakin bir geceydi. En iyi üçü bunlar."* |
| **Kötünün iyisi** | en iyi maç 6.5 altı | *"Kötünün iyisi."* Gerçekten bir şey olmadı. |

Vaat "her sabah üç harika maç" değil, **"her sabah dürüst bir sıralama".**

### Eşik kayan yüzdelikle belirlenir

Sabit 6.5 eşiğinin riski şu: geceler çoğunlukla o eşiğin altına düşerse
okuyucu her sabah "kötünün iyisi" görür ve ürün kendi içeriğini sürekli
küçümsemiş olur. O ifade gücünü nadir olmasından alıyor.

Çözüm rozeti şişirmek **değil** — 8.5 her zaman aynı şeyi ifade etmeli,
yoksa ölçek anlamını kaybeder ve iki hafta sonra kimse sayıya güvenmez.
Bunun yerine **eşik gecelere göre kayar:**

```
Son 30 gecenin "o gecenin en iyi maç skoru" değerlerini sırala.

Kötünün iyisi  = alttaki %15
Büyük gece     = üstteki %20  (ayrıca en iyi maç 8.5+ olmak zorunda)
Sıradan gece   = geri kalan
```

"Kötünün iyisi" böylece **yapı gereği** nadir kalır — sezonda kabaca
12-15 gece — ve rozetin anlamı hiç bozulmaz. Ligin genel temposu
yükselse de düşse de sistem kendini ayarlar, elle müdahale gerekmez.

**Beklenti (henüz doğrulanmadı):** risk 10+ maçlık gecelerde değil,
**3-4 maçlık küçük gecelerde** yoğunlaşıyor. 10 maçta en iyisinin 6.5'in
altında kalması için o gece kimsenin 30 sayı atmaması, hiçbir maçın yakın
bitmemesi ve hiç geri dönüş olmaması gerekir — çok zor. 4 maçta gayet
mümkün. 2 Ocak verisi bunu destekliyor: sıradan bir 10 maçlık gecede ilk
üç 8.4 / 8.1 / 7.6 çıktı, üçü de 6.5'in epey üstünde.

**Doğrulama planı:** 40-50 gecelik dağılım çalışması sohbet içinde
yapılabilecek bir iş değil — her gece ayrı sayfa çekimi demek. Box score
ve play-by-play boru hattı kurulunca bu bir kalibrasyon betiği olarak
otomatik koşar. O zamana kadar kayan yüzdelik güvenlik supabı görevi
görüyor: dağılım ne çıkarsa çıksın etiket nadir kalır.

## 6. Editoryal kaldıraç

Formülleştirilmemesi gereken şeyler var: bir efsanenin son maçı, hakem
skandalı, ilk kez karşılaşan iki kardeş, eski takımına dönen oyuncu, sahadaki
bir kavganın büyüklüğü. Bunların hiçbiri veriden güvenilir biçimde çıkmaz ama
sen bakınca anlarsın.

Bunlar için yeni taban kuralı ekleme. Formülün üstüne tek bir manuel kol koy:

```
+0  (varsayılan)   +1  (dikkate değer)   +2  (bu gecenin hikâyesi)
PIN (bu maç gecenin maçı, skoru ne olursa olsun)
```

Senin editoryal yargın zaten bu projenin motoru. Onu formüle çevirmeye
çalışmak, en iyi yaptığın şeyi kaybetmek olur.

---

## 7. Kalibrasyon — 2 Ocak 2026 (10 maç)

Gerçek bir gece, gerçek veriyle. Dram taşıyıcısı ve yıldız katsayısı dahil.

| # | Maç | Skor | Taşıyıcılar | **Rozet** |
|---|---|---|---|---|
| 1 | Charlotte – Milwaukee | 121–122 | D 7 · S 6.0 (Giannis 30/10) · K 1.5 | **8.4** |
| 2 | Denver – Cleveland | 108–113 | S 5.9 · K 4 | **8.1** |
| 3 | Memphis – Lakers | 121–128 | S 5.9 (Dončić 34) · K 4 | **7.6** |
| 4 | Portland – New Orleans | 122–109 | S 5.3 (Zion 35) · K 1 | **5.3** |
| 5 | Orlando – Chicago | 114–121 | S 4.9 (Banchero 31) · K 3 | **5.8** |
| 6 | Sacramento – Phoenix | 102–129 | S 5.4 (Booker 33) · K 3 | **5.4** |
| 7 | Atlanta – Knicks | 111–99 | K 3.5 · S 2.9 | **4.0** |
| 8 | OKC – Golden State | 131–94 | S 3.3 · K 2.5 | **3.6** |
| 9 | San Antonio – Indiana | 123–113 | S 2.9 · K 3 | **3.5** |
| 10 | Brooklyn – Washington | 99–119 | S 1.2 · K 0 | **1.2** |

**Ne öğrendik:**

- **Dram taşıyıcısı çalışıyor.** Charlotte–Milwaukee (1 sayı fark, 14
  sayılık geri dönüş, Giannis 30/10) v2'de 3. sıradaydı — yanlıştı.
  Şimdi gecenin maçı. İki takımın da yarış dışı olması artık maçı
  gömmüyor.
- **Dip sağlam.** OKC'nin 37 farkı 3.6, Brooklyn–Washington 1.2.
  Yakınlığın çarpan kalması çöp maçları yukarı taşımadı.
- **Sıradan gecede tavan 8.4.** Katman eşiği bu yüzden ürün tarafında
  "sakin gece" haline bağlandı (bkz. 5. bölüm).
- **S hiçbir maçta 6'yı geçmedi.** Bu iyi bir işaret: S ancak gerçekten
  olağanüstü bir gecede (45+ sayı) taşıyıcı olur, sıradan bir 30 sayı
  maçı tek başına yukarı çekmez.

## 8. Hâlâ formülde olmayan şeyler

Bilerek dışarıda bıraktım, ama farkında ol:

- **Seri bağlamı** — 12 maçlık galibiyet serisi bitiyorsa, 15 maçlık
  mağlubiyet serisi kırılıyorsa. D'ye girmiyor; H'ye ve recap cümlesine
  gidiyor. "Neden önemli" satırının en iyi yakıtı bu.
- **Rekabet/anlatı** — eski takımına karşı oynama, kardeş düellosu. Sadece
  recap tonu ve editoryal kol.
- **Antrenör durumu** — kovulma eşiğindeki antrenör. H'ye eklenebilir,
  şimdilik dışarıda.

---

## 9. Sıradaki adım: kalibrasyon

Formülü daha fazla kurcalamanın getirisi bitti. Şimdi gereken şey veri.

**Yöntem:** 25–30 gerçek gece seç (biri Ekim, biri Ocak, biri Nisan olsun).
Her gecenin maçlarını **sen** elle sırala — hangi maçı önce okurdun. Sonra
aynı geceleri v2 ile puanla ve iki sıralamayı karşılaştır.

Bakılacak tek şey: **senin ilk üçün ile formülün ilk üçü ne kadar örtüşüyor.**
Formülün işi senin yargını taklit etmek. Ondalık farklar önemsiz, katman
farkları önemli.

Ayarlanacak yerler, muhtemelen bu sırayla:
1. S'nin çapa tablosu (en çok gürültü buradan gelir)
2. Çarpan katsayıları (Y ve A ağırlıkları)
3. Katman eşiği (8.5 doğru yerde mi)
4. Zirve sönümlemesinin başlangıç noktası (8.5) ve tavanı (0.7)
