# OVERNIGHT — Proje Brifi

**Bu dosyayı ilk sen oku. Diğer dosyalara buradan yönleneceksin.**

---

## Proje nedir

OVERNIGHT, gece oynanan NBA maçlarını saat farkı yüzünden kaçıran Türk
basketbolseverler için hazırlanan bir sabah özeti sitesi. Her sabah 09:00'da
(TSİ) kendiliğinden yayınlanır. Bu saat bilinçli: 08:00'de hâlâ devam eden
maç olabilir, 09:00'da hiçbir maç sürmüyor.

Ürünün tek vaadi **triyaj**: "10 maç oynandı, üçünü bilmen yeter." Maçlar
bir değer skoruyla sıralanır; okuyucu neyi okuyacağına ve neyi geçeceğine
saniyeler içinde karar verir.

## Klasördeki dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `overnight-teknik-sartname.md` | **Ana referans.** JSON şeması, boru hattı, doğrulayıcı kuralları, hata halleri |
| `overnight-deger-skoru-v2-1.md` | Değer skoru formülü. `hesapla.py` bunu birebir uygular |
| `overnight-dil-kilavuzu-ve-ornek-gece.md` | Metin üreticinin dil kuralları + doğrulanmış örnek çıktı |
| `overnight_v17.html` | Bitmiş tasarım. İçerik elle yazılmış; şablona çevrilecek |

## Kullanıcı hakkında — önemli

**Kullanıcı geliştirici değil.** Kod okumayacak, teknik tercihleri
değerlendiremez.

- Teknik kararları **sen ver**, ona sorma. Kütüphane seçimi, dosya yapısı,
  hata yönetimi, dağıtım — bunlar senin işin. Kararı verdikten sonra tek
  cümleyle neden öyle yaptığını söyle, onay bekleme.
- Ona **sadece ürün sorusu** sor: bir bölüm nasıl görünsün, bir metin nasıl
  olsun, hangi bilgi öne çıksın. Bu konularda yargısı çok güçlü.
- Bir şey çalışmadığında ona hata mesajı yapıştırma. Ne bozulduğunu ve ne
  yaptığını Türkçe tek paragrafta anlat.

## Pazarlık edilmeyen üç kural

1. **Doğrulanmamış cümle yayına çıkmaz.** Metindeki her sayı ve her isim,
   o maçın `gercekler` kaydına bağlanabilmeli. Bağlanamıyorsa metin
   reddedilir ve deterministik şablon devreye girer. Sıkıcı kabul,
   yanlış değil.
2. **Her maçın box score'u eksiksiz olmalı** — sahaya çıkan her oyuncu,
   geçilecek maçlarda bile. Okuyucu tek bir yedek oyuncu için gelmiş
   olabilir.
3. **Sistem kullanıcıya bağlı olmamalı.** Hiç kimse başında olmadan,
   365 gün, kendiliğinden yayınlanmalı.

## Yapım sırası

Her adım tek başına test edilir. Bir adım geçmeden sonrakine geçme.

**1 — Kaynak doğrulama.** nba_api'nin şartnamedeki 7 uç noktası çalışıyor mu?
Tek bir geçmiş tarihle (2026-01-02) dene. Çalışmayan varsa alternatifini
bul, şemayı değiştirme.

**2 — Veri çekme.** `cek.py` → `ham/2026-01-02.json`. Ham veri, işlenmemiş.

**3 — Gerçek kayıtları.** `gercekler.py`. Şartname bölüm 4'teki türleri
üret. `an` türü **sadece** play-by-play'den gelir.

**4 — Formül.** `hesapla.py`. Formül dokümanını birebir uygula.

> **KABUL TESTİ:** 2 Ocak 2026 için üretilen rozetler şunlar olmalı:
> Charlotte–Milwaukee **8.4**, Denver–Cleveland **8.1**,
> Memphis–Lakers **7.6**, Orlando–Chicago **5.8**,
> Sacramento–Phoenix **5.4**, Portland–New Orleans **5.3**,
> Atlanta–New York **4.0**, OKC–Golden State **3.6**,
> San Antonio–Indiana **3.5**, Brooklyn–Washington **1.2**
>
> (±0.3 tolerans. Bileşen puanları elle takdir edildiği için birebir
> tutmayabilir; **sıralama** tutmak zorunda.) Tutmuyorsa devam etme,
> önce farkı bul.

**5 — Doğrulayıcı.** `dogrula.py`. T1–T8 testleri. Metin üreticiden
**önce** yaz — dil kılavuzundaki örnek gece metinlerini girdi olarak ver,
hepsi geçmeli. Sonra kasten bozulmuş cümleler ver, hepsi düşmeli.

**6 — Metin üretici.** `yaz.py`. Dil kılavuzu sistem promptu olur.
Ret oranı yüksek çıkarsa sorun genelde kurallar değil, gerçek
kayıtlarının eksik olmasıdır — 3. adıma dön.

**7 — Şablon.** `overnight_v17.html`'i JSON okuyacak hale getir.
Tasarımı değiştirme; sadece içeriği dinamikleştir.

**8 — Zamanlama ve yayın.** Zamanlanmış görev 08:30 TSİ, yayın 09:00. Hata olursa
e-posta. Ücretsiz barındırma, sunucu yok, veritabanı yok.

**9 — Kalibrasyon betiği.** Geçmiş 200+ geceyi koştur, "o gecenin en iyi
maç skoru" dağılımını çıkar. Şartnamedeki kayan yüzdelik eşikleri bundan
beslenir.

## Çalışma tarzı

- Küçük adımlar, her adımda çalıştırılabilir çıktı.
- Her modül tek başına ve geçmiş bir tarihle tekrar koşturulabilir olsun —
  geriye dönük kalibrasyonu mümkün kılan tek şey bu.
- Ham veriyi diskte tut. API'ı her denemede yeniden çağırma.
- Uydurma veriyle test etme. Her test gerçek bir gecenin verisiyle koşsun.
