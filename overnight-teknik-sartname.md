# OVERNIGHT — Teknik Şartname

Bu doküman koda geçmeden önce verilmesi gereken kararları içeriyor.
Kodu yazacak modelin buraya bakıp soru sormadan ilerleyebilmesi hedefleniyor.

İlgili dokümanlar: `overnight-deger-skoru-v2-1.md` (formül),
`overnight-dil-kilavuzu-ve-ornek-gece.md` (dil kuralları).

---

## 0. Temel ilke

> Her cümle, kayıttaki bir olguya bağlanabilmeli. Bağlanamayan cümle yayına
> çıkamaz.

Sistem, metin üretenin "akıllı" olmasına güvenmez. **Söyleyebileceklerini
kısıtlar.** Bu yüzden mimarinin merkezinde `gercekler` dizisi var: bir maç
hakkında doğrulanmış, atomik olgular. Metin üretici sadece bunlardan
cümle kurabilir, doğrulayıcı da çıktıyı bunlara karşı denetler.

Başarısızlık modu **sıkıcı** olmalı, asla **yanlış** değil.

---

## 1. Boru hattı

Her modül bir sonrakine dosya bırakır. Her adım tek başına çalıştırılabilir
ve tekrar koşturulabilir olmalı — bu, hata ayıklamayı ve geriye dönük
kalibrasyonu mümkün kılan tek şey.

| # | Modül | Girdi | Çıktı |
|---|---|---|---|
| 1 | `cek.py` | tarih | `ham/{tarih}.json` — API'dan gelen işlenmemiş veri |
| 2 | `gercekler.py` | ham | `gercek/{tarih}.json` — atomik olgular |
| 3 | `hesapla.py` | ham + config | `skor/{tarih}.json` — bileşenler ve rozetler |
| 4 | `yaz.py` | gerçek + skor | `taslak/{tarih}.json` — LLM metni |
| 5 | `dogrula.py` | taslak + gerçek | kabul / ret + gerekçe |
| 6 | `derle.py` | hepsi | `gece/{tarih}.json` — **yayın dosyası** |
| 7 | `yayinla.py` | gece + şablon | `site/{tarih}.html` |

Zamanlama: **08:30 TSİ'de 1-6, 09:00'da 7.** Yayın saati 09:00 çünkü
08:00'de hâlâ devam eden maç olabilir; 09:00'da hiçbir maç sürmüyor.
Yarım saatlik pay, geç biten maçlar ve tekrar denemeler için.

### Elle tutulan config dosyaları

Bunlar sezonda birkaç kez güncellenir, gece başına dokunulmaz:

- `config/yildizlar.json` — yıldız kademeleri (küresel + Türkiye sütunu)
- `config/takim_beklenti.json` — sezon öncesi takım kalitesi beklentisi
  (şu an 2024-25 NET_RATING fallback'i, bkz. bölüm 8)
- `config/turk_oyuncular.json` — Türkler bölümü + Türkçe ad düzeltmeleri
  için elle tutulan Türk oyuncu listesi (ad/takım)
- `config/takvim.json` — önceden bilinen editoryal olaylar (veda maçı,
  eski takıma dönüş, kilometre taşı eşiği)
- `config/yasakli.json` — yasaklı ifade listesi (dil kılavuzundan)

**Bakım: `yildizlar.json` doğrulaması.** Sezon başında ve her takas
döneminden sonra listedeki her oyuncunun adı ve `takim` alanı güncel
sezon verisine karşı kontrol edilmeli — isim yazım farkları (aksan/
kısaltma) ve takas sonrası eskimiş takım kodları asıl hata kaynağı.
Kontrol otomatik yapılabilir (bir gecelik box score verisine karşı
isim+takım eşleştirmesi) ama SADECE o gece oynayan takımların
oyuncularını doğrulayabilir — eksik/negatif sonuç "hata" değil, "bu
gece test edilemedi" anlamına gelir. Bir oyuncu, takımı o gece
oynadığı halde ne aktif ne kadro dışı listesinde çıkıyorsa (uzun
süreli sakatlık, takas, ya da kaynağın kadro dışı listesini eksik
doldurması olabilir) elle kontrol gerekir.

**Bilinen sınır: kadro dışı tespiti KISMİ.** `box_summary`'nin
`InactivePlayers` alanı bazı gecelerde boş dönüyor — gerçekten
oynamayan bir yıldız (ör. uzun süreli sakatlık) bu yüzden ne aktif ne
kadro dışı listesinde görünebilir. Bunun kritik sonucu: **bir
oyuncunun kadro dışı listesinde OLMAMASI "oynadı" anlamına gelmez.**
Kod bu çıkarımı hiçbir yerde yapmamalı — sadece POZİTİF tespit (bir
oyuncu DND/DNP notuyla kadro dışı listesinde görünüyorsa) güvenilir
ve kullanılabilir (E kancası, A bileşeni yıldız ağırlığı gibi yerlerde
sadece bu). Tespit YOKLUĞU bilgi değildir — "X oynamadı" cümlesi
sadece bu yokluktan asla üretilmez. Bu sınır resmi bir sakatlık
raporu kaynağı eklenene kadar kalıcı.

## 2. Veri kaynağı

**nba_api** (Python). Kurulumun ilk adımı: aşağıdaki uç noktaların hâlâ
çalıştığını tek bir geçmiş tarihle doğrula. Çalışmayan varsa alternatifini
bul, şemayı değiştirme.

| İhtiyaç | Uç nokta |
|---|---|
| Gecenin maçları | `ScoreboardV2` |
| Oyuncu box score | `BoxScoreTraditionalV3` |
| İleri istatistik | `BoxScoreAdvancedV3` |
| Maç künyesi (skor, tarih, önceki karşılaşma) | `BoxScoreSummaryV2` |
| En büyük fark, lider değişimi | `PlayByPlayV3`'ten türetilir |
| Kadro dışı oyuncular | `BoxScoreTraditionalV3`'ten türetilir |
| **Play-by-play** | `PlayByPlayV3` |
| Puan durumu, seri | `LeagueGameLog` (tarihe göre kesilir, derece + seri hesaplanır) |
| Sezon ortalamaları (sapma tabanı) | `PlayerGameLogs` |

Play-by-play zorunlu — F (final dramı), G (geri dönüş), Y (yakınlık) ve
clutch ağırlığı sadece oradan çıkıyor.

**2026-01-02 ile doğrulandı — V2 → V3 geçişi.** `BoxScoreTraditionalV2`,
`BoxScoreAdvancedV2` ve `PlayByPlayV2`, 2025-26 sezonu için NBA tarafında
boş dönüyor (ham yanıt `{}`). V3 sürümleri çalışıyor ve JSON şekli farklı
ama aynı bilgiyi (hatta fazlasını) taşıyor:

- `BoxScoreTraditionalV3`, sahaya çıkmayan her oyuncuyu da listeler ve
  `comment` alanında nedenini verir (örn. `"DND - Injury/Illness"`,
  `"NWT"`). `kadro_disi` gerçeği artık ayrı bir kaynağa değil, doğrudan
  bu alandan (boş olmayan `comment`) çıkarılıyor.
- `PlayByPlayV3`, her olayda o anki skoru (`scoreHome`/`scoreAway`) ve
  periyot + saat (`period`, `clock`, ISO 8601 süre biçiminde geri sayım)
  taşıyor. `fark_serisi` (en büyük fark, lider değişimi, kapatılan açık)
  bundan hesaplanıyor — `BoxScoreSummaryV2`'nin artık boş dönen
  `OtherStats` alanına ihtiyaç kalmadı. F bileşeni (son 2 dakikada fark
  ≤5) de `period`/`clock` üzerinden hesaplanabiliyor, doğrulandı.

`BoxScoreSummaryV2` tamamen ölmedi ama daraldı: `GameSummary`, `GameInfo`,
`LineScore` (çeyrek sütunları hariç) ve `LastMeeting` doluyor;
`OtherStats`, `Officials`, `InactivePlayers`, `SeasonSeries` 2025-26
sezonu için boş dönüyor. Hakem bilgisi için çalışan bir kaynak
bulunamadı — ancak bölüm 4'teki gerçek türleri listesinde hakem zaten
yok, bu yüzden boru hattını etkilemiyor.

**`LeagueStandingsV3` kullanımdan kaldırıldı.** Bu uç nokta tarih
parametresi almıyor — geçmiş bir tarih için çağrılsa bile her zaman
çağrıldığı ANDAKİ güncel puan durumunu döndürüyor. 2 Ocak 2026 için
çekildiğinde OKC'yi 64-18 (sezon ortası bir rakam) gösterdi, oysa o
gece sonu doğru rakam 30-5'ti. Bu, kalibrasyon betiği (9. adım) 200+
geçmiş geceyi işlerken her gecede o gecenin değil "bugünün" puan
durumunu yazacağı, sessiz ve fark edilmesi zor bir hataydı. Yerine
`LeagueGameLog` (sezonun tüm maç sonuçları, `date_to_nullable` ile
hedef tarihe kesilir — bu tarih dahil) kullanılıyor: derece takım
başına galibiyet/mağlubiyet sayılarak, seri de en son maçtan geriye
doğru aynı sonucun tekrarı sayılarak hesaplanıyor. Konferans/lig sırası
için 30 takımın konferans bilgisi elle tutulan sabit bir tabloda
(nadiren değişir, sezon başı config'e taşınabilir).

---

## 3. Gece dosyası şeması

`gece/{tarih}.json` — sitenin okuduğu tek dosya.

```json
{
  "tarih": "2026-01-02",
  "olusturuldu": "2026-01-03T04:32:11Z",

  "veri": {
    "durum": "tam",
    "eksik": [],
    "not": null
  },

  "gece": {
    "mac_sayisi": 10,
    "hal": "siradan",
    "en_iyi_skor": 8.4,
    "esik": { "pencere_gece": 30, "alt_yuzdelik_15": 6.4, "ust_yuzdelik_20": 8.7 }
  },

  "maclar": [ { /* bkz. 3.1 */ } ],

  "brief": [
    { "ikon": "geri_donus", "metin": "...", "hedef_mac": "0022500481", "spoiler": true }
  ],

  "turkler": {
    "durum": "yok",
    "oyuncular": [],
    "sonraki": [
      { "oyuncu": "Alperen Şengün", "takim": "HOU", "tarih": "2026-01-03", "rakip": "DAL" }
    ]
  },

  "gecenin_besi": [ { "oyuncu": "...", "takim": "...", "one_cikan": "REB", "stat": {} } ],

  "notlar": [
    { "tur": "sakatlik", "metin": "...", "haber_skoru": 8, "ton": "notr" }
  ]
}
```

### 3.1 Maç nesnesi

```json
{
  "id": "0022500484",
  "saat_tsi": "05:00",
  "ev":  { "kod": "GSW", "ad": "Golden State", "skor": 94,  "derece": "18-17" },
  "dep": { "kod": "OKC", "ad": "Oklahoma City", "skor": 131, "derece": "30-5" },
  "kazanan": "OKC",
  "uzatma": 0,
  "ceyrekler": { "OKC": [34,30,31,36], "GSW": [23,22,21,28] },

  "skor": {
    "rozet": 3.6,
    "ham": 3.71,
    "katman": "gec",
    "tasiyicilar": { "S": 3.3, "K": 2.5, "T": 0, "D": 0 },
    "yukselticiler": { "Y": 1, "F": 0, "G": 0, "A": 4.5 },
    "dram_terfi": false,
    "sonumleme_k": 0,
    "editoryal": 0
  },

  "haber_skoru": 0,

  "box": {
    "OKC": [ { "oyuncu": "...", "id": "...", "dk": "28:11", "sayi": 30,
               "rib": 1, "ast": 7, "cal": 0, "blk": 0, "tk": 3,
               "fg": "10/20", "uc": "3/5", "sut": "7/7",
               "gmsc": 21.8, "arti_eksi": 26 } ],
    "GSW": [ ],
    "kadro_disi": { "GSW": ["Stephen Curry", "Jimmy Butler", "Draymond Green"] }
  },

  "gercekler": [ { /* bkz. 4 */ } ],

  "metin": {
    "baslik": "...",
    "neden_onemli": "...",
    "ozet": "...",
    "gec_satiri": "...",
    "kullanilan_gercekler": ["f1","f4","f7"],
    "muzip": false
  },

  "video": { "youtube_id": null }
}
```

**Alan kuralları**

- `katman`: `mutlaka` | `ikinci` | `gec`. `hesapla.py`'de bu bir EŞİK
  sınıflandırması (rozet ≥ 8.5 → `mutlaka`) — bir gecede eşiği aşan
  BİRDEN FAZLA maç olabilir. **Kural (yaz.py'de `_mutlaka_ve_diger`
  uyguluyor): "Mutlaka bil"e giren maç HER ZAMAN gecenin en yüksek
  rozetli TEK maçıdır** — `katman: mutlaka` etiketli başka maçlar
  varsa onlar `diğer`e (Grup A, `gec_satiri`) düşer. Gerçek üretim
  bug'ı (25 Aralık 2025): iki maç birden `mutlaka` etiketi aldı, ikisi
  de Grup B'ye girdi, "Mutlaka bil" kartı hangi maçın olduğu
  belirsizleşti (birinin metni boştu, görünen maç yanlış olanıydı).
- `hal`: `buyuk` | `siradan` | `kotunun_iyisi`
- `durum` (veri): `tam` | `kismi` | `gecikti`
- `box` her maç için **sahaya çıkan herkesi** içerir. Kadro dışı ayrı alanda.
  Bu, üründe pazarlık edilemez bir kural.
- `spoiler: true` olan her metin alanı arayüzde `veil` sınıfıyla sarılır.
- `gec_satiri` sadece `katman: gec` için doldurulur, 2-3 cümledir.
  (İlk taslakta "tek cümle" deniyordu; dogrula.py'nin kabul testinde
  dil kılavuzundaki tüm örnek "Bunları geç" paragrafları 2-3 cümleydi
  ve triyaj değerlerini kaybetmeden tek cümleye sıkışamıyorlardı —
  kural buna göre gevşetildi.)
- `ozet` sadece `katman: mutlaka` için doldurulur.
- **`gecenin_besi`, maç sıralamasından (rozet) TAMAMEN AYRI bir liste.**
  `derle.py` bunu doldururken maçları rozete göre değil, gecedeki TÜM
  oyuncuların kendi performansına (GmSc) göre sıralamalı. Örnek: 2 Ocak
  2026'da Deni Avdija'nın 34/11/7'si (GmSc 32.6), Zion'un 35 sayısından
  (GmSc 29.6) daha iyi bireysel performans — Avdija maç sıralamasında
  Portland–New Orleans'ı sadece 2. sıraya taşırken `gecenin_besi`'nde
  1. sırada olmalı. `hesapla.py`'deki `S_hesapla` zaten "maçın en iyi
  performansı"nı hesaplıyor (`skor/{tarih}.json` içinde
  `en_iyi_performans` alanı) — `derle.py` bu değeri maçlar arası
  toplayıp kendi sıralamasını buradan üretebilir, maç rozetinden değil.

---

## 4. Gerçek kaydı

Metin üreticinin kullanabileceği tek hammadde. Yapısal veri taşır,
Türkçe cümle **taşımaz** — cümleyi üretici kurar, doğrulayıcı da
bu kayıtlara karşı denetler.

```json
{
  "id": "f7",
  "tur": "oyuncu_stat",
  "veri": { "oyuncu": "Chet Holmgren", "sayi": 15, "rib": 15, "blk": 4 },
  "kaynak": "BoxScoreTraditionalV2:0022500484:203999",
  "guven": "kesin"
}
```

### Gerçek türleri

| tur | Ne taşır | Nereden |
|---|---|---|
| `skor` | final skor, kazanan | box summary |
| `ceyrek` | çeyrek sayıları, çeyrek sonu farkı | box summary |
| `oyuncu_stat` | bir oyuncunun maç toplamı | box traditional |
| `oyuncu_ceyrek` | bir oyuncunun çeyrek dağılımı | play-by-play |
| `takim_stat` | isabet, top kaybı, ribaund toplamı | box traditional |
| `an` | belirli bir saniyedeki olay (basket, ihraç, sakatlık çıkışı) | play-by-play |
| `fark_serisi` | maç boyunca fark eğrisi, en büyük fark, kapatılan açık | play-by-play |
| `kadro_disi` | oynamayan oyuncular | box summary |
| `derece` | maç sonrası galibiyet-mağlubiyet, sıra | standings |
| `seri` | galibiyet/mağlubiyet serisi ve kırılması | standings geçmişi |
| `kilometre` | eşik aşımı — "dikkat çekici" (50 sayı, triple-double, 20 rib, 10 üçlük, 5 blok) VE "olağanüstü" (60 sayı, 25 rib, 20 asist, 15 üçlük, quadruple-double) iki kademe | box (bkz. `gercekler.KILOMETRE_ESIKLERI`) |

`guven` alanı iki değer alır:

- `kesin` — doğrudan API alanından geliyor
- `turetilmis` — hesaplanmış (fark eğrisi, seri, kilometre taşı)

**Kural:** `an` türündeki hiçbir gerçek play-by-play olmadan üretilemez.
Play-by-play çekilemediyse o maçta `an` gerçeği yoktur, dolayısıyla metin
son hücumdan, buzzer-beater'dan, "kim maçı bitirdi"den bahsedemez.
Bu, boru hattının sessizce uydurma yapmasını engelleyen tek mekanizma.

---

## 5. Doğrulayıcı

`dogrula.py`, üretilen her metin alanını sırayla şu testlerden geçirir.
Herhangi biri düşerse metin reddedilir.

**T1 — Sayı izlenebilirliği.**
Metindeki her sayı, ya `gercekler` içinde bir alan değeri olmalı, ya da
şu beyaz listeden bir türetme olmalı: iki skorun farkı, çeyrek toplamları,
derece dizeleri. Başka türetme kabul edilmez.

**T2 — Özel ad izlenebilirliği.**
Metindeki her oyuncu ve takım adı, o maçın kadrosunda veya kadro dışı
listesinde geçmeli. Ligdeki başka bir oyuncunun adı geçemez.

**T3 — An iddiası.**
Metin şu kalıplardan birini içeriyorsa (`son saniye`, `son hücum`,
`galibiyet basketi`, `uzatmaya götüren`, `bitime N saniye`), o maçta
en az bir `an` türü gerçek bulunmalı ve gerçeğin saati son 2 dakikada
olmalı. Yoksa ret.

**T4 — Yasaklı ifade.**
`config/yasakli.json` içindeki kalıplar. İki liste: klişeler ve yapay
zekâ tikleri. Eşleşme varsa ret.

**T5 — Kazanan.**
Maç metninde kazanan takımın adı veya kodu geçmeli. Geçmiyorsa ret.

**T6 — Uzunluk (üst VE alt sınır).**

| Alan | Üst sınır | Alt sınır (asgari kelime) |
|---|---|---|
| `brief[].metin` | 12 kelime | 3 |
| `baslik` | 10 kelime, 1 satır, fiil zorunlu | 3 |
| `neden_onemli` | 15 kelime | 3 |
| `ozet` | 4 cümle / 75 kelime | 8 |
| `gec_satiri` | 2-3 cümle | 4 |

Alt sınır sonradan eklendi (gerçek üretim bug'ı): eskiden sadece üst
sınır kontrol ediliyordu, TAMAMEN BOŞ bir metin ("") her üst sınırı
vakumsal olarak geçip hiçbir testte ihlal bulamıyordu — 11 gecelik bir
toplu üretimde onlarca alan boş yayınlandı. Ayrıca `mac_metnini_dogrula`
eskiden boş alanları doğrulama kapsamının TAMAMEN dışına atıyordu
(`if v` filtresi) — o filtre de kaldırıldı, artık mevcut ama boş bir
alan T6'dan geçmek zorunda (yani asgari kontrolüne takılıp reddedilir).

**T13/T17/T18 genişlemeleri (bu tabloya sonradan eklendi, ayrıntı
kodda):** T13 artık bir TAKIM skorunun bir OYUNCUYA atfedilmesini de
yakalıyor ("150'ye ulaşan Adebayo" — 150 takımın skoruydu). T18 artık
"kariyer rekoru / tarihte / ilk kez" gibi ifadeleri SADECE o maçta bir
"olağanüstü" kilometre gerçeği (60+ sayı, 25+ ribaund, 20+ asist, 15+
üçlük, quadruple-double) varsa kabul ediyor — ama kesin bir SIRA/RANK
iddiası ("tarihin ikinci en yüksek skoru") kilometre gerçeği olsa BİLE
HER ZAMAN reddedilir (all-time sıralama veritabanımız yok).

**T7 — Muziplik sayacı.**
Üretici, muzip register kullandığı alanları `muzip: true` ile işaretler.
Gecede en fazla **3** alan işaretli olabilir. Fazlası varsa en düşük
rozetli maçlardan başlayarak sıfırlanır ve o alanlar yeniden üretilir.

**T8 — Nötr ton.**
`haber_skoru >= 6` olan bir maçın metninde kutlama register'ı ve muziplik
yasak. `muzip: true` ise doğrudan ret.

### Ret davranışı

```
ret → yeniden üret (en fazla 2 deneme)
    → hâlâ ret ise ŞABLON MODU
```

**Şablon modu**, LLM kullanmayan deterministik bir metin üreticidir.
Sadece gerçek kayıtlarından kalıp doldurur:

> `{kazanan} deplasmanda {skor} kazandı. {en_skorer} {sayi} sayı attı.`

Sonuç kuru olur ama **her zaman doğrudur.** Yayın hiçbir koşulda
doğrulanmamış metinle çıkmaz. Site sessizce boş kalmaktansa sıkıcı çıkar.

---

## 6. Hata halleri

| Durum | Davranış |
|---|---|
| Bir maçın play-by-play'i gelmedi | O maç `an` gerçeği olmadan yayınlanır; Y/F/G çeyrek verisinden tahmin edilir ve `guven: turetilmis` işaretlenir |
| Bir maçın box score'u gelmedi | Maç listede skor ve derece ile kalır, `metin` boş, kart açılmaz |
| API tamamen çöktü | `veri.durum = "gecikti"`, sayfa dünkü içeriği değil, açık bir gecikme notu gösterir; iş 15 dk arayla 4 kez tekrar dener |
| Hiç Türk oyuncu oynamadı | `turkler.durum = "yok"`, `sonraki` doldurulur |
| Gece hiç maç yok | Sayfa "Bu gece maç yok" haliyle çıkar |

Her hata GitHub Actions üzerinden e-posta bildirimi üretir. Sen uyurken
sistem kendi kendine karar verir; sen gün içinde bakarsın.

---

## 7. Koda geçmeden önce doğrulanacaklar

Sırayla, her biri tek başına test edilebilir:

1. nba_api'nin 7 uç noktası çalışıyor mu — tek geçmiş tarihle dene
2. `PlayByPlayV2`'den fark eğrisi çıkarılabiliyor mu (Y, F, G bundan geliyor)
3. Sezon ortalaması sorgusu tarihe göre kesilebiliyor mu — 2 Ocak'ın
   sapması, 2 Ocak öncesi ortalamayla hesaplanmalı, sezon sonu ortalamasıyla değil
4. Bir gecenin tam JSON'u üretilebiliyor mu — metin olmadan, sadece veri ve skor
5. 2 Ocak 2026 için üretilen rozetler, elle hesapladıklarımızla eşleşiyor mu
   (8.4 / 8.1 / 7.6 ... 1.2)

**5. madde kritik:** formülün koda doğru geçtiğinin tek kanıtı bu.
Eşleşmiyorsa koda devam etme, önce farkı bul.

## 8. `hesapla.py` — sezon öncesi beklenti (`config/takim_beklenti.json`)

A bileşeninin "takım kalitesi" yarısı artık `config/takim_beklenti.json`
ile harmanlanıyor (`takim_kalitesi_hesapla`, `n/(n+20)` ağırlığı — n =
takımın hedef geceden önce oynadığı maç sayısı). n küçükken (sezon
başı) beklenti baskın, n büyüdükçe bu sezonun gerçek verisi baskın olur.

**Kaynak — KULLANICI KARARI:** gerçek bahis galibiyet hedefleri
bulunamadı (bu ortamda canlı bahis-oranı verisine erişim yok).
Fallback olarak **2024-25 sezonu NET_RATING'i** kullanıldı
(`nba_api.stats.endpoints.leaguedashteamstats`,
`measure_type_detailed_defense='Advanced'`, 2026-08-15'te çekildi —
bkz. `config/takim_beklenti.json` içindeki `kaynak` alanı). Her sezon
başında güncellenmeli; gerçek bir preseason bahis-oranı kaynağı
bulunursa bunun yerine o kullanılmalı (daha isabetli).

**Bilinen sınır — bu harman AŞAĞIDAKİ tekrar-eden-rozet sorununu
ÇÖZMEZ.** 2025-10-22 (sezonun 2. gecesi) beş farklı maç TAM OLARAK
aynı rozeti (8.96) aldı. Kök neden A bileşeni DEĞİL — `formulu_uygula`
içindeki "zirve sönümlemesi" kuralı: S (en iyi bireysel performans)
tavana (10) ulaştığında `carpan_efektif` TAM OLARAK 1'e sıfırlanıyor,
yani Y/F/G/A (A dahil) o maçın rozetini HİÇ etkilemiyor. Erken sezonda
K bileşeni de (kazanma yüzdesi farkının 82 maça yayılmış hâli, `ay_k`
katsayısıyla ekim ayında zaten dampinglenmiş) birçok maçta aynı tavana
(2.0) çarpıyor — S=10, K=2.0, T=0, D=0 kombinasyonu birden fazla maçta
birebir eşleşince "taban" da eşitleniyor, A ne kadar farklı olursa
olsun `ham` (ve dolayısıyla rozet) aynı çıkıyor. Bu, `config/takim_beklenti.json`
eklenmeden ÖNCE de vardı, eklendikten SONRA da duruyor — ayrı bir
formül davranışı, S/K tavan doygunluğu erken sezonda ne sıklıkla
tetikleniyor incelenmeden düzeltilmemeli.
