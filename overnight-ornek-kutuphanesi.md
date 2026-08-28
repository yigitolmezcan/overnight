# OVERNIGHT — Örnek Kütüphanesi

Bu dosya kural listesi **değildir.** Editörün bu projede verdiği gerçek
düzeltmelerin yanlış/doğru çiftleri hâlinde toplanmış hâlidir.

**Neden örnek, neden kural değil:** modele "şunu yazma" demek, ne yazacağını
söylemiyor. Yasaklı liste büyüdükçe model çıkış yolu bulamıyor ve şablona
düşüyor. Bir çift ise hem yanlışı hem doğruyu aynı anda gösteriyor.

Bu dosya sistem promptuna **olduğu gibi** eklenir. Yasaklı listeler ve
doğrulayıcı testleri aynen kalır — bu onların yerine geçmez, önlerine geçer.

---

## 1. Fiiller — en sık hata alanı

| ✗ Yanlış | ✓ Doğru |
|---|---|
| Brunson 8 asist **verdi** | Brunson 8 asist **yaptı** / 8 **asistle oynadı** |
| 10 asist **dağıttı** | 10 asist yaptı |
| 25 sayı **kaydetti** | 25 sayı **attı** |
| **topladığı** 25 sayıyla | **attığı** 25 sayıyla |
| Denver üçüncü çeyreği 38 sayıyla **oynadı** | Denver üçüncü çeyrekte 38 sayı **attı** |
| Booker 33 **sayıyla oynadı** | Booker'ın **attığı** 33 sayıyla |
| 15 ribaund **aldı** | 15 ribaund **topladı** |

**İlke:** takım **atar**, oyuncu **oynar**. "Toplamak" yalnızca ribaund
fiilidir; sayı için kullanılmaz.

---

## 2. Belirsiz nicelik — sayı varsa sayı yazılır

| ✗ Yanlış | ✓ Doğru |
|---|---|
| Milwaukee ilk yarıda **geniş bir üstünlük** kurdu | Milwaukee ilk yarıda **farkı 16'ya çıkardı** |
| **sahadan yüksek isabetle** oynadı | **13/21 isabetle** oynadı *(veya cümleden çıkar)* |
| 11 serbest atışının **tamamını kullanarak** | 11 serbest atışının **11'ini attı** |
| **ciddi bir fark** yarattı | **22 sayılık fark** yarattı |

---

## 3. Fark ve geri dönüş dili

| ✗ Yanlış | ✓ Doğru |
|---|---|
| 16 sayılık **açığı kapattı** | 16 sayılık **farktan döndü** / farkı **eritti** |
| farkı 16'ya **açtı** | farkı 16 sayıya **çıkardı** / **yükseltti** |
| Portland'ı 10 sayı geriden **geri getirdi** | Portland 10 sayı geriden **dönüp** kazandı |
| 129-102 **farkla ezdi** | **129-102'lik skorla ezdi** *(skor verilince "farkla" denmez)* |
| Detroit deplasmanda 138-100 **ezdi** | Detroit deplasmanda **Brooklyn'i** 138-100 ezdi *(nesne düşmez)* |

---

## 4. Cümle yapısı — bir cümle bir fikir

**✗ Referans berbat cümle:**
> Dončić 34 sayı 8 asistle Lakers'ı dördüncü çeyreği 32-25 kazanarak
> Memphis'i 128-121 yenerek üçüncü mağlubiyet serisine soktu.

Aynı cümlede dört fikir, iki "-erek", özne kaymış.

**✓ Referans iyi cümleler:**
> Phoenix, Booker'ın 33 sayısıyla Sacramento'yu 129-102 yendi.

> Liderliğin 19 kez el değiştirdiği maçta Chicago, dördüncü çeyrekteki
> performansıyla maçı kazandı.

> Atlanta, Trae Young'suz New York'u 111-99 mağlup etti.

> Deni Avdija 34 sayı 11 asistle Portland'ı sırtladı, ilk çeyreği 8 sayı
> geride kapatan Blazers ikinci periyotta farkı tersine çevirdi ve
> 122-109 kazandı.

**Ortak özellik:** kısa, tek fikirli, sonucu net söylüyor, laf kalabalığı yok.
Editörün ret gerekçesi hep aynıydı: *"bitir geç."*

Diğer bozuk yapılar:

| ✗ Yanlış | ✓ Doğru |
|---|---|
| 15 **lider değişimli maçta** | **Liderliğin 15 kez el değiştirdiği** maçta |
| beş kez lider değişimiyle geçen çekişmeli bir **final oynadı** | son çeyrekte liderlik beş kez el değiştirdi |
| Minnesota'yı son çeyrekte Edwards'ın üçlüğü 115-115'e **taşıdı** | Minnesota, Edwards'ın son saniye üçlüğüyle skoru 115-115'e **getirdi** |
| Son dakikada serbest atışlarla **150'ye ulaşan** Adebayo | *(150 takımın skoru — oyuncuya atfedilemez)* |

---

## 5. Dolgu ve klişe

| ✗ Yanlış | ✓ Doğru |
|---|---|
| …ve **galibiyeti aldı** *(cümle sonunda)* | *(çıkar, cümleyi bitir)* |
| Jokić'in triple-double'ı Denver'ı **güldürdü** | Jokić Denver'ı **sırtladı** / **taşıdı** |
| **kariyerine yakışan** bir gecede | *(oyuncunun kariyeri hakkında niteleme yapılmaz)* |
| **kilometre taşı** bir gece geçirdi | **tarihe geçti** *(iç terminoloji metne çıkmaz)* |
| bir daha **baskı altında kalmadı** | bir daha **arkasına bakmadı** |
| **bir avuç oyuncunun** başardığı | **NBA tarihinde altıncı kez** *(sayı > belirsiz övgü)* |

**Kök bazlı yasaklı fiiller** (her çekimi yasak): damga vur-, sergile-,
kaydet-, imza at-, mahkûm et-, göm-, güldür-, gülümset-, sevindir-,
zafere taşı-, mutlu et-.

Ayrıca yasak: suretiyle, müsabaka, +/- tablosunda, sepet *(potadır; sayı olan
atış **baskettir**)*.

---

## 6. Türkçe ek uyumu

Ekler **okunuşa** göre gelir, yazılışa göre değil.

| ✗ Yanlış | ✓ Doğru |
|---|---|
| Curry'**un** | Curry'**nin** |
| Bane'**nin** | Bane'**in** |
| Booker'**in** | Booker'**ın** |
| Murray'**ın** | Murray'**in** |
| Edwards'**nin** | Edwards'**ın** |
| Wizards'**yi** | Wizards'**ı** |
| Doğu'**nın** | Doğu'**nun** |
| Trae Young'**siz** | Trae Young'**suz** |

**Geçici koruma:** ekin doğruluğundan emin olunamıyorsa ekli kullanımdan
tamamen kaçın, cümleyi eksiz kur:

> ✗ "Curry'un basketiyle" → ✓ "Curry, basketiyle"
> ✗ "Murray'ın 34 sayısı" → ✓ "Murray 34 sayı attı"

---

## 7. Terim ve yazım

| ✗ Yanlış | ✓ Doğru |
|---|---|
| puan *(sayı için)* | **sayı** *("puan" yalnızca puan durumunda)* |
| dunk | **smaç** |
| driving layup | **turnike** |
| ribaunt | **ribaund** |
| Sengun | **Şengün** |
| takım kodu metinde (DEN, LAC) | **tam ad** (Denver, LA Clippers) |
| şehir adı uydurma (Indianapolis) | veri kaynağındaki ad (Indiana) |
| uzun tire (—) | **virgül** |

**İlke:** Türkçe karşılığı okuyucuya doğal geliyorsa Türkçe yazılır.
"Smaç" doğaldır, "çöp zaman" zorlamadır — bu yüzden *garbage time* İngilizce
kalır. Şüphede kalırsan Türk basketbol seyircisinin konuşurken hangisini
kullandığını sor.

---

## 8. Zaman kipi

| ✗ Yanlış | ✓ Doğru |
|---|---|
| Cleveland üçüncü galibiyetini **almış** | Cleveland üçüncü galibiyetini **aldı** |

"-mış" duyulan geçmiştir; haber metni kesin geçmiş kullanır.

---

## 9. Haber değeri — neyin anılmayacağı

Bu bölüm dil değil, **editoryal yargı.** Modelin en çok hata yaptığı yer.

| ✗ Anılmaz | Sebep |
|---|---|
| "farkı 13'e çıkardı" *(tek başına)* | Sonuç söylemiyor — "da noldu?" |
| "2 sayı farkla yendi" | Skor zaten başlıkta; fark 20+ değilse anılmaz |
| "9 sayılık farktan döndü" | Geri dönüş eşiği 10+ |
| "5 lider değişimi" | Eşik 15+, alt kırılım hiç anılmaz |
| "7/7 serbest atış" | Eşik 12+ deneme |
| "ikinci galibiyetini üst üste aldı" | "Üst üste" için 3+ gerekir |
| "41-27'lik seri" | Çeyrek skoru **seri değildir** — seri kesintisiz ve tek taraflıdır (10-0, 12-2) |
| "konferansta 10. sıraya oturdu" | Sıralama yalnızca ilk 3 veya play-in hattı için anlamlı |
| "10. mağlubiyetini üst üste aldı" | Heves kırıcı; kayıp serisi yalnızca **kırıldığında** veya 15+ ise anılır |
| "sezonu 21-11 yaptı" | Derece son çare cümlesi, bilgi taşımıyor |
| "üst üste 4. galibiyetini alan lig lideri" | Lig liderinin serisi haber değil |
| artı-eksi verisi | Metinde geçmez, kutu skorda kalır |

**Kural:** eşiği geçen hiçbir olgu yoksa **sadece sonucu yaz ve bitir.**
"Washington, Brooklyn'i 119-99 yendi." yeterli ve dürüst bir cümledir.
Boşluk doldurmak için cümle üretme.

---

## 10. Tekrar ve atıf

| ✗ Yanlış | ✓ Doğru |
|---|---|
| Başlık ve gövde aynı cümleyi söylüyor | Gövde başlığın **devamıdır**, kopyası değil |
| Aynı gecede iki "Mağlup tarafta…" | Gecede en fazla bir kez |
| Aynı gecede iki "farktan dönerek" | Bir olgu türü gecede en fazla iki kez |
| "Maçı belirleyen basket bitime 5.6 saniye kala geldi" | **Kimin attığı** söylenmeden an anılmaz |
| Kaybeden takımın oyuncusu cümlenin öznesi | Önce kazananın en iyisi; kaybeden ancak gecenin en yükseğiyse |
| "Sharpe 14 sayı 9 ribaundla mağlubiyet serisini üçe çıkardı" | Oyuncu istatistiği takım serisinin **sebebi değildir** |

---

## 11. Kullanım notu

Bu dosya sistem promptunda **örnek** olarak durur, kural listesi olarak değil.
Model bu çiftleri okuyup doğrunun neye benzediğini görür.

Yeni bir editör düzeltmesi geldiğinde buraya **çift olarak** eklenir —
yanlış hâli de doğru hâli de. Sadece yasak eklemek, modeli çıkışsız
bırakıp şablona iter.
