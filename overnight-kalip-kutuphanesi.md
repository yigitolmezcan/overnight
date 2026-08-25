# OVERNIGHT — Kalıp Kütüphanesi

Kaynak: editörün dört yıllık BSL özet arşivinden 50 metin.
**İçerik değil, iskelet ödünç alındı.** Yerel öğeler (renk lakapları, şehir
temsilcisi, semt adları, haftalık lig çerçevesi) tamamen çıkarıldı.

Bu doküman, sistem promptundaki uzun kural anlatımlarının **yerine geçer.**
Yasak listeleri ve T testleri aynen kalır.

---

## 1. Evrensel iskelet

Arşivdeki 50 metnin 45'i tam olarak bu yapıda:

```
CÜMLE 1:  [KANCA] + [KAZANAN], [YER] [KAYBEDEN]'i [SKOR] [YENME FİİLİ].
CÜMLE 2:  [NİTELEYİCİ] [KAZANAN]'da [OYUNCU], [İSTATİSTİK] [ÖNE ÇIKMA FİİLİ].
```

Örnek:

> **[Haftanın açılışında]** **[Trabzonspor]**, **[sahasında]** **[Tofaş]**'ı
> **[92-87]** **[mağlup etti]**. **[İki maç aradan sonra kazanan]**
> **[Trabzonspor]**'da **[Marcquise Reed]**, **[41 sayılık flaş performansıyla]**
> **[kariyer rekorunu kırdı]**.

Çeşitlilik iskeletten değil, **blokların içeriğinden** gelir. İskelet sabit
kalır; her blok için aşağıda bir banka var.

**Kritik gözlem:** ikinci cümlenin niteleyicisi, metnin bilgi taşıyan asıl
yeridir. "İkinci galibiyetini alan" değil — "14 yıl sonra ilk kez lige beşte
beşle başlayan". Kutu skora bakan biri bunu göremez. Ürünün silahı burada.

---

## 2. Kanca bankası (Cümle 1'in açılışı)

Öncelik sırasıyla. Eşiği geçen en yüksek öncelikli kanca seçilir.

### A — Dram
> Kazananı son saniyelerde belli olan maçta…
> Gecenin nefes kesen maçında…
> Uzatmaya giden mücadelede…

### S — Sürpriz sonuç
> Kağıt üstünde çok gerideki [X], favoriyi sahasında yendi…
> Sezonun en büyük sürprizlerinden birinde…
> Kimsenin beklemediği bir sonuçla…

### Z — Zirve maçı
> Batı'nın (Doğu'nun) zirvesinde…
> Konferansın zirvesindeki iki takımın karşılaşmasında…
> Sıralamanın tepesindeki iki ekip sahaya çıktığında…

### P — Bireysel patlama
> Gecenin tek yıldızı [Oyuncu] olurken…
> [Oyuncu], nadir görülen bir performansa imza attı…
> [Oyuncu]'nun gecesinde…

**Yasak (kullanıcı kararı):** "kariyerine yakışan" gibi oyuncunun
KARİYERİ hakkında bir nitelemeyle açılan kancalar — bu maçta olan
şeyin ötesine geçen bir övgü uydurması. Sadece BU MAÇTA olanı yaz,
kariyer hakkında yorum yapma.

### B — Bahis / önem
> Play-in sıralamasını yakından ilgilendiren karşılaşmada…
> Gecenin bir diğer kritik maçında…
> Aynı sıra için yarışan iki takımın maçında…
> Play-off eşleşmelerini doğrudan etkileyen maçta…

### C — Form / gidişat
> Son dönemde formunu yükselten ekiplerden [X]…
> Aralık ayını kusursuz geçiren [X]…
> Zirve takibini sürdüren [X]…
> Bu sezon inişli çıkışlı bir performans sergileyen [X]…
> Ligin formda ekiplerinden [X]…

### D — Sıralama / statü
> Lider [X]…
> Ligin namağlup tek takımı [X]…
> [N] galibiyetli iki takımın maçında…
> Batı'nın dibindeki iki takımın maçında…

### E — Kadro / haber
> [Oyuncu]'nun oynamadığı maçta…
> Her iki başantrenörün de atıldığı maçta…
> [Oyuncu]'nun eski takımına karşı çıktığı maçta…

### F — Maç içi olağandışılık
> Toplam [N] serbest atışın kullanıldığı maçta…
> Liderliğin [N] kez el değiştirdiği maçta…
> İki takımın toplam [N] üçlük attığı maçta…

### G — Gecedeki sıra
> Gecenin ilk maçında…
> Gecenin kapanışında…
> Türkiye saatiyle gecenin en geç maçında…

### H — Doğrudan (kanca yok)
> [X], sahasında [Y]'yi [SKOR] yendi.

**Kural:** aynı gecede aynı kanca iki kez kullanılamaz. Kullanılan kanca
menüden düşer, ikinci maç bir alt önceliğe iner.

---

## 3. Niteleyici bankası (Cümle 2'nin açılışı)

Arşivin en değerli kısmı. Her biri veriden hesaplanabilir.

**Seri ve derece**
> Sezonu galibiyetle açan… / Üst üste [N]. galibiyetini alan…
> İlk galibiyetine ulaşan… / Galibiyet sayısını [N]'e yükselten…
> [N] maç aradan sonra kazanan… / [N] maç sonra galibiyeti hatırlayan…
> Sahasındaki namağlup ünvanını sürdüren…
> İç sahada oynadığı [N]. maçını da kazanan…

**Tarihsel bağlam**
> [N] yıl sonra ilk kez [X] yapan…
> Kulüp tarihinin en iyi sezon başlangıcını yapan…

**Maçın kazanılma biçimi**
> İlk yarının sonunda [N] sayıya kadar ulaşan farktan dönerek kazanan…
> Üçüncü çeyrek performansıyla maçı kazanan…
> İkinci yarıdaki savunmasıyla rakibine yalnızca [N] sayı izni veren…
> Rakibine tam [N] sayı fark atan…

**Sıralama etkisi**
> [N]. sıra için iddiasını sürdüren…
> Geceyi [N]. sırada kapatan…
> Normal sezonu [N]. sırada bitiren…

**Kadro / teknik**
> Yeni başantrenörü [X] yönetiminde ilk maçını kazanan…
> [X]'siz oynadığı maçı kazanan…

---

## 4. Oyuncu tarafı

### Öne çıkma fiilleri
> öne çıktı · maçın en skorer ismi oldu · takımını sırtladı · yıldızlaştı
> galibiyetin mimarı oldu · etkili oldu · oynadı · double-double yaptı
> kariyer rekorunu kırdı · galibiyeti getiren isim oldu · öne çıkan isim oldu
> takımını taşıdı · takımını sürükledi · maçı tek başına bitirdi · takımını omuzladı

Aynı gecede aynı fiil iki kez kullanılamaz.

**Yasak — gazete manşeti klişesi (kullanıcı kararı):** güldürdü,
gülümsetti, sevindirdi, üç puanı hanesine yazdırdı, gol oldu, zafere
taşıdı, mutlu etti. Bunlar Türk spor gazeteciliğinin yerleşik klişeleri
— OVERNIGHT'ın sesine yakışmıyor. Bunun yerine yukarıdaki oyuncu-taşıma
fiillerini kullan: sırtladı, taşıdı, sürükledi, tek başına bitirdi,
omuzladı.

### Oyuncu kancaları (istatistikten önce gelen bağlam)
> eski takımına karşı… · sakatlıktan yeni dönen… · kenardan gelerek attığı…
> [N] dakikada attığı… · sezonun ilk maçına çıkan… · altıda beş üçlük isabetiyle…

### İki oyuncu anma kalıbı
> [A] [N] sayı ve [N] asistle, [B] ise [N] sayı ve [N] ribaundla double-double yaptı.
> [A] [N], [B] [N] sayıyla yıldızlaştı.

---

## 5. Zenginlik kademeleri

| Kademe | Koşul | Yapı |
|---|---|---|
| **Fakir** | Eşiği geçen 0 olgu | Kanca G veya H + sonuç. Niteleyici basit (derece/seri). |
| **Orta** | 1 olgu | Kanca o olgudan seçilir, niteleyici sonuçtan gelir. |
| **Zengin** | 2+ olgu | En güçlü olgu kancayı, ikincisi niteleyiciyi doldurur. |

İki cümle her kademede korunur. Fakir kademe kısa cümle demek değil,
**olay iddiası olmayan** cümle demektir.

---

## 6. NBA'e uyarlanmış örnekler

Aşağıdakiler arşivden değil, arşivin iskeletinin NBA'e uyarlanmış hâlidir.
Editör onayına tabidir.

**Fakir — kanca H**
> Washington, sahasında Brooklyn'i 119-99 yendi. Üst üste üçüncü galibiyetini
> alan Wizards'ta Alex Sarr, 19 sayı ve 4 blokla öne çıktı.

**Fakir — kanca G**
> Gecenin ilk maçında San Antonio, Indiana'yı deplasmanda 123-113 geçti.
> Galibiyet sayısını 25'e yükselten Spurs'te Pascal Siakam 23 sayı attı.

**Orta — kanca C (form)**
> Son dokuz maçını kaybeden Boston, kötü gidişatını Miami karşısında
> sonlandırdı. İki hafta sonra galibiyeti hatırlayan Celtics'te Jayson Tatum,
> attığı 35 sayıyla takımını sırtladı.

**Orta — kanca E (kadro)**
> Trae Young'ın oynamadığı maçta Atlanta, New York'u 111-99 mağlup etti.
> Jalen Johnson 18 sayı, 10 ribaund ve 11 asistle triple-double yaptı.

**Zengin — kanca A (dram)**
> Kazananı son saniyede belli olan maçta Milwaukee, Charlotte'u 122-121
> yendi. 16 sayılık farktan dönerek kazanan Bucks'ta galibiyeti getiren isim,
> bitime 4.7 saniye kala alley-oop smaç yapan Giannis Antetokounmpo oldu.

**Zengin — kanca F (maç içi)**
> Liderliğin 19 kez el değiştirdiği maçta Chicago, Orlando'yu 121-114 geçti.
> Son çeyreği 30-19 kazanan Bulls'ta Josh Giddey, 24 sayı ve 11 asistle
> galibiyetin mimarı oldu.

**Zengin — kanca B (bahis)**
> Batı'da aynı sıra için yarışan iki takımın maçında Cleveland, Denver'ı
> 113-108 mağlup etti. Son çeyrekte 25-11'lik bölümle maçı çeviren
> Cavaliers'ta Donovan Mitchell, attığı 33 sayıyla öne çıktı.

---

## 7. NBA'e AKTARILMAYACAK yerel öğeler

Arşivde bunlar var ve **hiçbiri kullanılmayacak:**

| Yerel öğe | Neden |
|---|---|
| Renk lakapları (siyah-beyazlılar, sarı-lacivertliler) | NBA takımlarının renk lakabı yoktur |
| Şehir temsilcisi (Bursa temsilcisi, başkent temsilcisi) | NBA'de takım-şehir bağı bu düzeyde kimliksel değil; Kaliforniya'da üç takım var |
| Semt/şehir adı yer belirtirken (Akatlar'da, İzmir'de) | Aynı sebep |
| Başantrenör adıyla takım anma ("Kokoskov'un ekibinde") | Türk NBA yazısında kullanılmaz, çeviri gibi durur |
| Haftalık lig çerçevesi (haftanın açılışı, cumartesi seansı) | NBA gecelik oynanır → "gecenin ilk maçı" |
| "Damgasını vurdu", "imzasını attı" | Zaten yasaklı klişe listesinde |

**Takma adlar kullanılabilir ve çeşitliliğin asıl kaynağıdır:**
Celtics, Lakers, Warriors, Bucks, Blazers, Wolves, Sixers, Cavaliers, Spurs,
Nuggets, Suns, Kings, Nets, Wizards, Hawks, Bulls, Magic, Pelicans, Thunder,
Pacers, Grizzlies, Hornets, Knicks, Heat, Mavericks, Rockets, Jazz, Clippers,
Raptors, Pistons.

Kural: ilk anışta şehir/takım adı, ikinci anışta takma ad.

---

## 8. Değişmeyen ilke

> Çeşitlilik hiçbir zaman inandırıcılık pahasına olmaz.

Bir ifade Türk basketbol konuşmasında doğal duruyorsa girer. Kulağa çeviri
veya zorlama geliyorsa, ne kadar çeşitlilik katarsa katsın girmez.
