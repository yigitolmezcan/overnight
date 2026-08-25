# OVERNIGHT — Dil Kılavuzu + Örnek Gece

Aşağıdaki metinler **2 Ocak 2026** gecesinin gerçek verisinden yazıldı.
Uydurma yok: her cümle box score'dan veya puan durumundan geliyor.
Doğrulayamadığım hiçbir şey yazılmadı — nerede veri eksikse işaretledim.

---

## Bölüm 1 — Dil kuralları

### Kural: terim seçimi

Tek tek yasaklı kelimeler değil, genel bir ilke — ama ölçüt **"Türkçe
karşılığı var mı" değil, "Türkçe karşılığı okuyucuya doğal geliyor
mu."** Smaç doğaldır — Türk basketbol seyircisi öyle der. "Çöp zaman"
(garbage time) zorlamadır — kimse öyle konuşmaz, herkes İngilizcesini
kullanır. Şüphede kalırsan ölçüt şu: **Türk basketbol seyircisi
konuşurken hangisini kullanıyor, onu yaz.**

Buradan üç grup çıkıyor: (1) doğal bir Türkçe karşılığı olanlar — o
karşılık yazılır; (2) karşılığı yok ama Türkçe yazımı yerleşmiş
olanlar (ribaund, asist gibi) — Türkçe yazımıyla yazılır; (3) hem
karşılığı yok HEM Türkçe yazımı da doğal durmuyor olanlar (triple-double,
garbage time gibi) — İngilizce haliyle, olduğu gibi bırakılır.

**Türkçe kullanılacaklar (karşılığı var ve doğal):**

| İngilizce | Türkçe |
|---|---|
| dunk | smaç |
| turnover | top kaybı |
| steal | top çalma |
| block | blok |
| free throw | serbest atış |
| three-pointer | üçlük |
| overtime | uzatma |
| buzzer-beater | son saniye basketi |
| fast break | hızlı hücum |
| lead change | lider değişimi |
| comeback | geri dönüş |
| starter / bench | ilk beş / yedek |
| point guard | oyun kurucu |
| paint | boyalı alan |
| screen | perde |
| ejection | ihraç |
| roster | kadro |

**Türkçe yazımıyla kullanılacaklar (karşılığı yok, yazımı doğal):**
ribaund, asist, faul, MVP.

**İngilizce haliyle kalacaklar (karşılığı da yok, Türkçe yazımı da
zorlama):** playoff, play-in, alley-oop, pick and roll, triple-double,
double-double, garbage time. Bunları Türkçeleştirmeye ÇALIŞMA —
"üçlü-dubl", "çöp zaman" gibi bir uydurma daha kötü okunur, İngilizcesi
zaten Türkçe spor diline geçmiş.

**Asla kullanılmayacaklar (İngilizce hâlleri, çünkü doğal Türkçe
karşılığı var — bkz. yukarıdaki tablo):** dunk, assist, rebound,
block, clutch, box score, and-one, possession.

**"Clutch" özel durum:** metne çıkan hiçbir cümlede İngilizce
geçmez — "son bölümde", "kritik anlarda" gibi Türkçe ifadelerle
karşılanır. Formül dokümanında bir bileşen adı olarak kalabilir, ama
okuyucuya giden metnin içinde yeri yok.

### Kural: puan/sayı, fark/açık, diğer sözcük seçimleri

**"Puan" yasak, "sayı" zorunlu** — oyuncunun/takımın attığı her şey
"sayı"dır. "Puan" SADECE lig sıralamasının puanı için kullanılır
("puan durumu"). ✗ "34 puanla", "20 puanlık açık" → ✓ "34 sayıyla",
"20 sayılık fark".

**"Fark" ile "açık" karıştırılmaz.** Fark = iki skor arasındaki
mesafe, nötr bir sayı. Açık = geride olan takımın kapatması gereken
mesafe, geride olan tarafın bakış açısından. "Skor farkı 20 sayıydı"
ama "Suns'ın açığı 20 sayıya çıktı" (Suns geride olduğunda).

**"Açığı kapatmak" basketbolda kullanılmaz** — geride olan takım
kazandığında ✗ "16 sayılık açığı kapattı" değil, ✓ "16 sayılık
farktan döndü" / "farkı eritti" denir. Benzer şekilde önde olan
takımın farkı büyütmesi ✗ "farkı açtı" değil, ✓ "farkı yükseltti" /
"farkı çıkardı" ile anlatılır.

**Bu ikisinin öznesi (kim geri döndü, kim farkı büyüttü) DAİMA maçın
gerçek akışıyla eşleşmeli** — geri dönüşü her zaman KAZANAN taraf
yapar, kaybeden değil. Bir maçta 16 sayı geriden dönüp kazanan
takımın adını "geri dönüş" cümlesinin öznesi yap, rakibini değil.

**"Sepet" yasak, "basket" zorunlu** — sayı olan atışa "basket" denir;
sepet potanın fiziksel parçasıdır, atışın kendisi değildir. ✗
"Kuzma'nın sepetiyle" → ✓ "Kuzma'nın basketiyle".

**Diğer tercihler:**
- "kayıp serisi" değil "mağlubiyet serisi"
- "peş peşe" değil "üst üste"
- "müsabaka" değil "maç"

### Kural: fiil çekimi

Duyulan/aktarılan geçmiş zaman (-mış/-miş/-muş/-müş) yasak — bu çekim
Türkçede "bana söylendi, kendim görmedim" izlenimi verir, oysa her
cümle doğrulanmış bir kayıttan geliyor. Bilinen/görülen geçmiş zaman
(-dı/-di/-du/-dü) zorunlu.

### Kural: takım adı

Takım adı ve şehri SADECE o maçın kaydındaki resmî alandan gelir —
takımın gerçek şehri hakkındaki genel bilgi kullanılmaz. Bir takımın
gerçek dünyadaki şehri ile kayıttaki `teamCity` alanı farklı
olabilir (kısaltma, tarihî isim, resmî kullanım farkı); metin her
zaman kayıttakini yazar.

**Üç harfli takım kodu (MIL, CHA, DEN gibi) okuyucuya giden metinde
ASLA geçmez.** Kod veri katmanında (gerçekler, box score) dolaşır ama
cümle her zaman tam şehir/takım adını yazar (Milwaukee, Charlotte).
Takma ad (Bucks, Hornets) çeşitlilik için seyrek kullanılabilir, kod
hiçbir zaman.

### Yasak: register — resmi yazışma dili ve gazetecilik klişesi

> suretiyle · mahkûm etti · gömdü · +/- (artı-eksi verisi metinde
> geçmez, kutu skorda kalır)

Bunlar ya resmi yazışma diline ait (suretiyle) ya abartılı gazetecilik
klişesi (mahkûm etti, gömdü) ya da okuyucunun ilgilenmediği ham veri
(plus-minus, kutu skorda kalması gereken bir sayı).

### Yasak: klişeler

Bunlar Türk spor yazısının otomatik pilotu. Hiçbiri bilgi taşımıyor.
Çekimli/ek almış varyantları da yasaktır — "damga vurdu" kadar
"damgasını vurarak" da yasak.

> adeta · resmen · tam anlamıyla · sahne aldı · damga vurdu · boy gösterdi
> galibiyete imza attı · skor makinesi · parmak ısırttı · şov yaptı
> tarihe geçti · efsane performans · adeta bir ders verdi · nefesleri kesti
> çeyreği kazandı (bir takımın bir çeyreği rakibinden fazla sayı atarak
> bitirmesi skorla anlatılır, "kazandı" fiiliyle değil)
> zorlu mücadele · kritik karşılaşma · önemli bir galibiyet

### Yasak: yapay zekâ tikleri

Bunlar daha sinsi, çünkü hata gibi durmuyorlar. Boş değerlendirme
cümleleri — hiçbir şey söylemeden bir şey söylemiş gibi yapıyorlar.

> "dikkat çekici bir performans sergiledi"
> "başarılı bir gece geçirdi"
> "takımın galibiyetinde önemli rol oynadı"
> "mücadelenin son bölümünde belirleyici oldu"
> "istatistikleriyle göz doldurdu"

**Test:** cümleden sayıyı çıkardığında geriye bir şey kalıyor mu? Kalan
şey her maç için doğruysa, o cümle yok demektir.

### Yasak: fiil şişirmesi

`sergiledi · kaydetti · elde etti · gerçekleştirdi · imza attı`

Sayıyı söyle, yeter — fiil şişirmesi olmadan, düz bilinen geçmiş
zamanla ("bitirdi", "attı" gibi) ya da sadece sayı öbeğiyle.

### Yasak: doğrulanamayan an

Play-by-play verisi yoksa **son saniye basketi, kimin attığı, hangi
hücumda ne olduğu yazılmaz.** Bunlar en çekici cümleler olduğu için
uydurma baskısı en çok burada. Veri yoksa cümle yok.

### Kural: sıradan bir maçta sade bitir — ZORUNLULUKLARI ÇAKIŞTIRMA

**Bu kural diğerlerinden önce gelir.** Aynı anda dayatma: kazananı
söyle + en yüksek performansı an + maç içi bir detay ver + eşik altı
bir şey anma. Sıradan bir maçta bunların hepsi birden sağlanamaz —
zorlarsan cümle bükülür, yüklem üst üste yığılır.

Doğru sıra: önce haber değeri eşiğini (aşağıda) geçen bir olgu var mı
diye bak.
- **Yoksa** — sadece sonucu yaz ve BİTİR. "Washington, Brooklyn'i
  119-99 yendi." Bu yeterli ve dürüst bir cümledir, üzerine bir şey
  eklemeye ÇALIŞMA.
- **Varsa** — o olguyu ekle, ama tek bir tane. İkinci bir olgu için
  üçüncü zorunluluk aranmaz.

En yüksek GmSc'li performans kuralı da aynı mantığa bağlı: sadece o
performans kendisi bir eşiği geçiyorsa (30+ sayı, 15+ ribaund, 10+
asist vb. — bkz. haber değeri eşikleri) anılır. Sıradan bir gecede
24 sayı 6 ribaundluk "en iyi performans" diye bir şey zorla cümleye
sokulmaz.

### Kural: her maç farklı bir yerden başlar

Onu bir maçta skorla, birinde çeyrekle, birinde oyuncuyla, birinde
puan durumuyla aç. Aynı kalıp iki kez üst üste gelmesin.

### Kural: takım "atar", oyuncu "oynar"

Bir takımın sayı üretmesi "atmak" fiiliyle anlatılır, "oynamak"
fiiliyle değil — "oynadı" oyuncuya ait bir fiildir, takıma değil. Aynı
mantık sayı öbeklerinin iyeliği için de geçerli: bir dönemi ("son
bölüm", "üçüncü çeyrek" gibi) bir takımın SAHİPLİĞİNE değil, o dönemi
YÖNETEN taraf olarak anlat — cümlenin öznesi takım olsun, dönem değil.

### Kural: cümlenin öznesi maçı kontrol eden taraftır

Bir fark ya da farkın kapanması anlatılırken cümlenin öznesi, o anı
YARATAN/AÇAN taraf olur — geride kalan taraf değil. Ünlü takımı öne
almak refleksi var — kırılması gerekiyor. Anlatının öznesi maçı
yöneten taraf olur, tanınan taraf değil.

### Kural: kazananı söylemeden cümle bitmez

Her maç metninde sonucun kime gittiği açıkça geçer. Ne kadar dolaylı
anlatılırsa anlatılsın, okuyucu "e kim kazandı" diye sormamalı.

### Kural: en yüksek performans anılıyorsa, kazanandan başlanır

En yüksek GmSc'li performans anmaya değer buluyorsan (bkz. bir önceki
kural — eşiği geçmesi şart), kaybeden taraftan bir isim ancak ondan
SONRA gelebilir. Kaybeden takımın bir oyuncusu cümlenin ÖZNESİ olarak
BAŞLAYAMAZ — hikaye kaybedenin oyuncusuyla açılıp kazananın performansı
hiç geçmeden bitemez.

### Kural: haber değeri eşikleri

Bir olgunun DOĞRU olması onu anılmaya değer kılmaz. Aşağıdaki
eşiklerin ALTINDA kalan olgular metinde HİÇ geçmez — editör her
maçta bunları eleyerek "bu gerçekten okuyucunun önemsemesi gereken
bir şey mi" diye sorar.

| Olgu | Anılma eşiği |
|---|---|
| Geri dönüş | 10+ sayı. Altı anılmaz |
| Lider değişimi | Maç genelinde 15+. Altı anılmaz |
| "Üst üste" serisi | 3+ galibiyet/mağlubiyet. İkinci galibiyet "üst üste" değildir |
| Seri (run) | Sadece kesintisiz ve tek taraflı bölümler (10-0, 12-2, 15-3 gibi). Çeyrek skoru ASLA seri değildir — "41-27'lik seri" yanlış, bir çeyrekte iki takım da sayı atmış olabilir |
| Serbest atış | 12+ denemede yüksek isabet. 7/7 gibi düşük denemeli mükemmellik anılmaz |
| Üçlük | 6+ isabet, veya 5/5 ve üstü verim |
| Ribaund | 15+ |
| Asist | 10+ |
| Blok / top çalma | 4+ |
| Sayı | 30+ anılır, 40+ başlığa çıkabilir |
| Fark | 20+ "farklı galibiyet" sayılır |
| Artı-eksi (plus-minus) | Metinde ASLA geçmez, kutu skorda kalır |

### Kural: cümle disiplini

Bir cümle bir fikir taşır, en fazla iki yan cümle. Üçüncü bir olgu
eklemen gerekiyorsa yeni bir cümle kur, aynı cümleye tıkıştırma. Aynı
yüklem ailesini aynı cümlede tekrarlama ("...kazanarak ... yenerek"
gibi iki farklı yerde aynı anlamı taşıyan fiil olmaz).

✗ "Okongwu'nun 23 sayı ve 9 ribaundla başını çektiği Atlanta, Trae
Young'ın yokluğunda üçüncü çeyrekte 34-23'lük üstünlükle farkı 24
sayıya çıkararak New York'u 111-99 yendi." (tek cümlede beş olgu,
yüklem yığılması)

✓ "Trae Young'sız çıkan Atlanta, üçüncü çeyrekte farkı 24 sayıya
çıkardı. Okongwu 23 sayı 9 ribaundla öne çıktı, Atlanta New York'u
111-99 geçti."

**Gerçek düzeltmeler (editörden, kural değil örnek):**

| Yanlış | Doğru |
|---|---|
| topladığı 25 sayıyla | attığı 25 sayıyla |
| Kuzma'nın sepetiyle | Kuzma'nın basketiyle |
| dördüncü çeyrek 30-19 kazanarak | dördüncü çeyreği 30-19 kazanarak |
| bir daha baskı altında kalmadı | bir daha arkasına bakmadı |
| İki Doğu takımı da dip sıralarda | Doğu'nun dibindeki iki takımın maçında |
| son saniye galibiyeti belirledi | galibiyeti son saniye basketi belirledi |
| Mitchell 33 sayıyla | Mitchell'ın attığı 33 sayıyla (fiil düşürülmez, "33 sayıyla" tek başına eksik cümle) |
| Portland'ı 10 sayı geriden geri getirdi | "geri getirmek" basketbolda kullanılmaz — "10 sayı geriden dönerek Portland'ı öne taşıdı" |
| 16 sayılık rahatlığı geceye yetmedi | uydurma kişileştirme — kaybeden takımın rahatlığından değil, kazananın performansından bahset |

### Örnek cümleler — editörün onayladığı altın standart

Bunlar KISA, TEK FİKİRLİ, sonucu net söyleyen, laf kalabalığı
taşımayan cümleler. Editörün ret gerekçesi hep aynıydı: "bitir geç."

✓ "Phoenix, Booker'ın 33 sayısıyla Sacramento'yu 129-102 yendi."

✓ "Liderliğin 19 kez el değiştirdiği maçta Chicago, dördüncü
çeyrekteki performansıyla maçı kazandı."

✓ "Atlanta Hawks, Trae Young'sız New York'u 111-99 mağlup etti."

✓ "Deni Avdija 34 sayı 11 asistle Portland'ı sırtladı, ilk çeyreği 8
sayı geride kapatan Blazers ikinci periyotta farkı tersine çevirdi ve
122-109 kazandı."

Berbat örnek — TEK cümlede beş olgu üst üste yığılmış, öznesi kayan,
"kazanarak ... yenerek" aynı anlamı iki kez taşıyan yüklem:

✗ "Dončić 34 sayı 8 asistle Lakers'ı dördüncü çeyreği 32-25 kazanarak
Memphis'i 128-121 yenerek üçüncü mağlubiyet serisine soktu."

### Kural: bir istatistik bir takım sonucunun sebebi değildir

Bir oyuncunun maç içi istatistiği (sayı/ribaund/asist) ile takımın
SEZON GENELİ bir sonucu (galibiyet/mağlubiyet serisi) arasında
doğrudan sebep-sonuç kurma — ikisi farklı ölçek. ✗ "Day'Ron Sharpe 14
sayı 9 ribaundla mağlubiyet serisini üçe çıkardı" (bir oyuncunun tek
maçlık istatistiği takımın serisini "çıkarmaz", takımın maç sonucu
çıkarır). Oyuncunun istatistiğiyle takımın sonucunu ayrı cümlelerde
anlat.

### Kural: çeyrek sayısına yaslanma

Çeyrek kırılımı elimizdeki en kolay veri olduğu için metin oraya
kayıyor. Dört maçta üst üste çeyrek sayısı sayarsak tabloya
dönüşür. Bir maçın her çeyreğini ayrı ayrı saymak yerine, o çeyrek
dizisinin anlattığı ŞEYİ söyle (baştan sona kontrol, tek bir çeyrekte
kopuş, gel-git) — tam box score ve play-by-play'den çıkan ribaund,
top kaybı, kimin devraldığı gibi ayrıntılarla.

### Kural: beklentiye göre çerçeve (SADECE gerçek bir sürprizse)

Favori kaybettiyse ya da derece farkı büyükse bunu cümleye taşımak
değer katar. Ama bu ZORUNLU bir katman değil — favori beklenen gibi
kazandıysa bunu ayrıca belirtmeye çalışma, sonuç zaten kendini
anlatıyor.

### İzin: ölçülü muziplik

Bu, yasak listesinin tersi — metnin kuru bir tabloya dönmemesi için
gereken tek şey. Sulanmadan, hafif çokbilmişlikle bir gözlem
katılabilir: maçın kırılma anına dair kısa bir yorum, bir takımın
beklentisiyle çelişen başlangıcına bir iğneleme, tek taraflı bir
sonuca dair kuru bir tespit gibi. Yapısal gerçekler (bir derece, bir
seri) adıyla söylenir, süslenmez.

Kural: **gecede en fazla iki-üç kez.** Her maçta espri yaparsan
espri olmaktan çıkar, tik olur. Ve asla bir oyuncunun aleyhine
kişisel olmaz — hedef maçtır, takımın durumudur, ligin yapısıdır.

### Kural: uzunluk

| Yer | Uzunluk |
|---|---|
| 30 saniyede gece satırı | Tek cümle, 12 kelimeyi geçmez |
| Maç başlığı | Tek satır, fiil içerir, 10 kelimeyi geçmez |
| Neden önemli | Tek cümle, 15 kelimeyi geçmez |
| Mutlaka bil özeti | 3–4 cümle |
| Bunları geç satırı | **VARSAYILAN: TEK cümle, 15-20 kelime.** İkinci cümle KURAL DEĞİL, İSTİSNA — sadece maçta eşiği geçen, gerçekten anlatmaya değer ikinci bir olgu varsa eklenir. Sıradan bir maçta tek cümle yeterlidir, ikinci cümle ARANMAZ. |

### Kural: "30 saniyede gece" bir MANŞETTİR, özet değil

Brief satırı skoru tekrar etmez — skor zaten hemen aşağıdaki kartta
duruyor, brief'te tekrarı gürültü (TEK istisna: skorun/farkın kendisi
haberse, ör. 20+ sayılık fark). Satır TEK fikir + TEK cümledir, o maçı
benzersiz kılan şeyi söyler — "X, Y'yi Z-W yendi" gibi sonuç-only bir
cümle de, "farkı 13'e çıkardı" gibi sonuçsuz bir ara-detay da YETERSİZ.
Beş satır beş farklı şekilde kurulur (kimi oyuncuyla açar, kimi olayla,
kimi takımla) — aynı cümle iskeleti gece içinde tekrar edemez.

✓ "Giannis bitime 4.7 saniye kala smaçla bitirdi, Milwaukee 16
   sayıdan döndü."
✓ "Trae Young yoktu, Jalen Johnson triple-double yaptı."
✓ "Avdija 34 sayı ve 11 asistle Portland'ı sırtladı."
✗ "Cleveland Cavaliers, Denver Nuggets'ı 113-108 yendi." (sadece sonuç,
   skor tekrarı)
✗ çeyrek skorları, ara fark değişimleri, "farkı X'e çıkardı" gibi
sonuçsuz ara durumlar.

### Kural: OVERNIGHT telefonda okunur

Ürün yatakta, telefonda, uyanır uyanmaz okunuyor — hiçbir metin bloğu
ekranda kaydırma gerektirmemeli. Bu yüzden her alanın sıkı bir üst
sınırı var (bkz. "Kural: uzunluk" tablosu) ve bu sınırlar bilgi
eksikliği değil YOĞUNLUK ister: gereksiz ikinci bir sayı/ayrıntı
("16 sayıya kadar taşıyarak" gibi tek yeter, "...ve farkı X'te tuttu"
gibi bir ikincisi gerekmez), aşırı hassas zaman damgaları ("45.7
saniye kala" yerine çoğu zaman "son dakikada" yeter) ve aynı bilginin
iki cümlede tekrarı ("en etkili isim oldu" + ayrı cümlede aynı
oyuncunun istatistiklerini bir daha sayması) budanır.

### Kural: "neden önemli" başlığı tekrar etmez

`neden_onemli`, `baslik`'ta zaten söylenmiş şeyi başka kelimelerle
tekrar etmez — başlıkta OLMAYAN bir şey söyler: sonucun ne anlama
geldiği (sıralama, seri, playoff durumu). Başlık "son saniye
smacıyla kazandı" diyorsa alt satır bunu bir daha anlatmaz, "bu
galibiyet Bucks'ı play-in hattının neresine taşıdı" gibi bir şey
söyler.

### Kural: gece içi tekrar yasağı

Bir sözcük öbeği (iki kelime ve üstü) gece boyunca birden fazla maçta
tekrar etmez — adlar ve istatistik ifadeleri ("30 sayı", "10 ribaund"
gibi, doğası gereği tekrar edecek) hariç. "Her maç farklı bir yerden
başlar" kuralı tek bir maçın içi için geçerliydi; bu kural aynı şeyi
gecenin TAMAMI için istiyor — iki maçta da "peş peşe galibiyet" gibi
bir çerçeve kullanılmışsa, biri değişmeli.

### Kural: nötr ton nerede zorunlu

Sakatlık, disiplin olayı, kavga. Kutlama dili yok, "kötü haber" dili
de yok. Ne olduğu yazılır, yorum yapılmaz.

---

## Bölüm 2 — Örnek gece: 2 Ocak 2026

10 maç oynandı. Hiçbiri 8.5 eşiğini geçmedi — **sakin gece.**

### 30 saniyede gece

- Milwaukee 16 sayılık farkı kapattı, maçı 1 sayıyla aldı.
- Cleveland son çeyreği 25-11 alarak Denver'ı devirdi.
- Oklahoma City sezonun 30. galibiyetini aldı; Golden State eksikti.
- Lakers üçüncü çeyrek sonunda berabereydi, son 12 dakikayı aldı.
- Indiana 29. yenilgisini aldı: 6-29.

### Mutlaka bil — 1 maç

> **Bu gece sakindi.** 10 maçın hiçbiri eşiği geçmedi. Tek maç yeter —
> kalan dokuzu aşağıda, açık şekilde duruyor.

---

**Charlotte 121 — Milwaukee 122** · 8.4

**Milwaukee 16 sayı geriden döndü, maçı 1 sayıyla bitirdi.**

*Neden önemli: Gecenin tek çekişmeli maçıydı; Giannis 30-10 yaptı.*

Charlotte ilk çeyreği 38-24 önde kapattı; fark ikinci çeyreğin başında 16'ya
kadar çıktı. Hornets o çeyrekte 22 sayıda kalınca fark 9'a indi. Üçüncü çeyreğe
kadar önde giden Hornets son 12 dakikayı 35-30 kaybetti ve maçı 1 sayı
farkla verdi. Giannis Antetokounmpo 30 sayı 10 ribaundla bitirdi;
Milwaukee 15-20'ye yükseldi, Charlotte 11-23'te kaldı.

> ⚠ *Bu paragrafta play-by-play olsa eklenecek tek cümle: maçın son
> hücumunda ne olduğu. Şu an elimde yok, o yüzden yazılmadı.*

---

### Türkler

> ⚠ **Bu gece hiçbir Türk oyuncu sahaya çıkmadı.** Houston ve
> Philadelphia oynamadı. Bölüm boş kalıyor — arayüzde bu halin
> tasarlanması gerekiyor.

### Bunları geç — 9 maç

**Denver 108 — Cleveland 113** · 8.1
Denver üçüncü çeyrekte 38 sayı attı ve 9 öne geçti. Son bölümde vitesi
artıran Cleveland maçı çevirdi; Denver son çeyrekte 11 sayıda kaldı.
Jamal Murray 34 attı, yetmedi.

**Memphis 121 — Lakers 128** · 7.6
Üçüncü çeyrek 96-96 bitti. Lakers son 12 dakikayı 32-25 alıp kazandı,
Dončić 34 attı. Batı'da beşinci sıra korundu: 21-11.

**Orlando 114 — Chicago 121** · 5.8
Orlando son çeyreğe 4 sayı önde girdi ama o çeyrekte 19 sayıda kaldı;
Chicago 30 atıp maçı aldı. Banchero'nun 31 sayısı yetmedi. Chicago
tam ortada duruyor: 17-17.
> ⚠ *Farkın nereden açıldığını söyleyecek satır burada eksik — tam box
> score bağlanınca ribaund/top kaybı verisiyle doldurulacak.*

**Sacramento 102 — Phoenix 129** · 5.4
Baştan sona Phoenix kontrolünde geçti. Booker 33 attı. Sacramento
8-27 ile Batı'nın dibinde.

**Portland 122 — New Orleans 109** · 7.5
New Orleans maça "bu kez olacak gibi" başladı — ilk çeyrek 37 sayı —
ama sonraki iki çeyrekte toplam 38 bulabildi. Gecenin en iyi bireysel
performansı buradan çıktı: Deni Avdija 34 sayı, 11 asist, 7 ribaundla
oynadı ve Portland'ı taşıdı. Zion'un 35 sayısı yetmedi; New Orleans 8-28.

**Atlanta 111 — New York 99** · 4.0
Atlanta üç çeyrekte New York'a 24 fark attı. New York son çeyrekte 29
sayı atıp farkı 12'ye indirdi ama iş işten geçmişti. Brunson 24 attı,
Hukporti 16 ribaund aldı.
> ⚠ *"Son çeyreği Brunson yaklaştırdı" cümlesi doğru olabilir ama
> elimdeki veri sadece maç toplamını gösteriyor, çeyrek dağılımını
> değil. Play-by-play gelince yazılacak.*

**OKC 131 — Golden State 94** · 3.6
Maçın kırılma anı hava atışı oldu. Warriors'ta Curry, Butler ve Green
oynamadı; takım 90 şuttan 32 isabet buldu. Gilgeous-Alexander 28
dakikada 30 attı, Holmgren 15 sayı 15 ribaund 4 blok yaptı. OKC 30-5.

**San Antonio 123 — Indiana 113** · 3.5
Spurs favori olduğu maçı ikinci çeyrekte attığı 41 sayıyla kopardı; Indiana
üçüncü çeyrekte bir kez yaklaştı ama son çeyrekte fark kalıcı olarak açıldı. Indiana ligin en kötü derecesiyle
tanking'e devam ediyor: 6-29.

**Brooklyn 99 — Washington 119** · 1.2
İddiasız maçta Wizards rahat kazandı. Maçın en skoreri Champagnie'nin
attığı 20 sayı, gecenin on maçındaki en düşük "en skorer" performansı
oldu.

---

## Bölüm 2b — Bu metindeki düzeltilen hatalar

Örnek gece ilk yazıldığında play-by-play verisi yoktu ve üç iddia çeyrek
skorlarından **çıkarımla** yazılmıştı; dördüncüsü de tam box score'un
sadece bir köşesine (en skorer) bakılarak kuruldu. `gercekler.py` ve
`hesapla.py` dördünü de yakaladı:

| İddia | Gerçek |
|---|---|
| "14 sayılık farkı kapattı" | En büyük açık **16**'ydı; 14 sadece ilk çeyrek sonundaki farktı |
| "gecenin en yüksek çeyreği" (Charlotte 38) | San Antonio ikinci çeyrekte **41** attı |
| "fark bir daha 8'in altına inmedi" | Üçüncü çeyrekte bir kez daha indi |
| "Zion 35 gecenin en iyisiydi" | Avdija 34/11/7 daha yüksek (GmSc 32.6 vs 29.6); elle yazarken sadece "en skorer" alanına bakılmış, asist lideri ayrıca kontrol edilmemiş |

Dördü de aynı kökten geliyor: **veri yokken (veya veriyi eksik okuyarak) çıkarım yapmak.**
Bu, sistemin engellemek için tasarlandığı hata türünün ta kendisi —
ve doğrulayıcı yazıldığında bu dört cümle reddedilecekti.

Ders: çeyrek skorları bir maçın *şeklini* verir, *olaylarını* vermez.
Bir iddia çeyrek sınırlarının içinde ne olduğuna dayanıyorsa,
play-by-play olmadan yazılamaz.

## Bölüm 3 — Bu denemeden çıkan üç bulgu

**1. En çekici cümleler tam da yazamadıklarım.** Charlotte–Milwaukee'nin
son hücumunda ne olduğu, o maçın metnindeki en değerli bilgi olurdu ve
elimde yok. Play-by-play sayfası ayrı bir adres; boru hattına eklenmesi
şart. Yoksa ya cümle eksik kalır ya da uydurulur — ikincisi ürünü öldürür.

**2. Türkler bölümü o gece bomboş.** Houston ve Philadelphia oynamadı.
Bu sanılandan sık olacak: sezonda muhtemelen 30-40 gece. Bölümün "boş"
hali tasarlanmalı — ya gizlenir ya da "Bu gece Türk oyuncu sahada
yoktu, Şengün bir sonraki maçına yarın çıkıyor" gibi bir satır alır.

**3. Sakin gecede "Bunları geç" dokuz maç taşıyor.** Yani asıl yük
oraya biniyor. O dokuz satırın her biri tek cümle olmak zorunda,
yoksa "geç" bölümü sayfanın en uzun kısmı olur ve triyaj tezini
kendi elimizle bozarız.
