# OVERNIGHT — son tur (27 Ağustos 2026)

## İstenen üç dil kuralı

**1. "Mağlup tarafta ..." kalıbı** — Göz at'ta iki maç üst üste bu cümleyle
bitiyordu. Artık gecede en fazla bir kez, ve sadece kaybeden taraftaki oyuncu
bir kilometre taşı geçmişse (40+ sayı, triple-double, 20+ ribaund). Hak gece
düzeyinde tek bir maça veriliyor: `kalip_secici.gece_maglup_izni`. Üretim,
doğrulama ve LLM promptu **aynı fonksiyonu** çağırıyor — ayrı hesaplansa
kurallar birbirini yerdi.

**2. Karar anı oyuncuyu anmak zorunda** — "Maçı belirleyen basket, bitime 5.6
saniye kala geldi." okuyucunun tek merak ettiği şeyi söylemiyordu. `karar_ani`
kaydına `oyuncu` alanı eklendi; adı olmayan an artık hiç anılmıyor. Yeni
doğrulayıcı **T26**, yayını engelleyen testlerde.

**3. Asist fiili** — sadece "N asist yaptı" / "N asistle oynadı". `asist
ver-/dağıt-/üret-/kaydet-` kök bazlı yasak + sistem promptu.

> Çakışma: eski bir kural "asistle oynadı"yı zaten yasaklıyordu ("fiil yavan").
> Yeni talimat onu açıkça serbest bıraktığı için eski desenden çıkarıldı.

---

## Araya çıkan hatalar

**T14 yeni kuralla çelişiyordu.** T14 "gecenin en iyi performansı anılmalı"
diyor, yeni kural "kaybeden taraftaki sıradan performans anılmasın" diyor.
18 Aralık'ta en iyi üç performansın üçü de kaybeden taraftaydı → gece hiç
yayınlanamadı. T14 daraltıldı: anılması zaten yasak olan ismi zorlayamaz.

**Yayın kapısı donmuş gerekçe okuyordu.** Üretim anındaki doğrulama sonucunu
saklayıp ona bakıyordu; kural değişince artık geçerli olmayan bir sebeple
geceyi bloke ediyordu. Artık güncel kurallarla yeniden hesaplıyor.

**Kapı gece kapsamlı kuralları hiç görmüyordu.** Sadece maç bazlı rapora
bakıyordu, yani LLM'in yazdığı gece kuralı ihlali sessizce geçiyordu. T27
kapıya bağlandı.

**`tazele` tazelemiyordu.** `dist`'i yeniden *derlemeden* sayfaya gömüyordu —
yeni metin üretildikten sonra "TAZELENDİ" deyip eski metni yeniden
yayınlıyordu. Bu yakalanmasaydı üç kural düzeltilip yayında hiçbir şey
değişmemiş olacaktı.

**İngilizce terim listesi zayıftı** — "driving layup" yayına kadar geldi.
Listede sadece 8 kelime varmış; layup, fadeaway, jumper, turnover, steal,
buzzer, alley-oop vb. eklendi.

**Testler yerelde geçip CI'da düşüyordu.** Sebep: `ham/` depoya girmiyor (gece
başına ~19MB). Aynı sebeple yayın kapısı canlıda doğrulamayı tazeleyemiyordu —
kural yerelde geçerli, üretimde değil.

---

## Zamanlayıcı: iki ayrı arıza, önceki turda karıştırılmış

Önceki tur "GitHub gecikiyor" diye teşhis edilip üç zaman slotu konmuştu.
**Teşhis yanlıştı** ve doğrulanmamıştı — sadece *ateşlendiğinde ne olacağı*
test edilmişti, ateşlenip ateşlenmediği değil.

### A) GitHub zamanlanmış tetiklemeyi ateşlemiyor

```
26 Ağustos: 6 slottan 2'si ateşlendi
27 Ağustos: 6 slottan 0'ı
```

Yan etkisiz bir test iş akışı kuruldu (11:25 UTC). 34 dakika sonra hâlâ
ateşlenmemişti. Elle tetikleme (`workflow_dispatch`) ise her seferinde anında
çalıştı. Takılı koşuyu iptal etmeye çalışınca GitHub'ın cevabı:
`"Cannot cancel a workflow run that has not been queued yet."` — "queued"
görünen koşu aslında hiç kuyruğa girmemiş.

Elenen hipotezler: kota bitmiş değil, iş akışları `state=active`.

### B) Bildirim, izlediği sistemin içindeydi

İş hiç koşmayınca bildirimi yazan adım da koşmuyor. Ayrıca dünkü arıza issue'su
**açılmıştı** (#1) ama **kimseye atanmamıştı** — GitHub atanmamış issue için
garanti e-posta yollamıyor. "Neden haberim olmuyor"un doğrudan cevabı.

### C) NBA veri servisi erişilemez

Nöbetçi üretimi tetikledi, testler geçti, iş şurada düştü:

```
scoreboard 2025-12-21: ağ hatası (ReadTimeout)
RuntimeError: stats.nba.com read timeout
```

Yerelden ölçüldü:
```
stats.nba.com: HTTP 000 · 26.3s   (bağlantı açık tutulup düşürülüyor)
stats.nba.com: HTTP 000 · 18.1s   (birkaç dakika sonra, yine)
```

GitHub'ın IP'si engelli değil — aynı makineden bir buçuk saat önce 20 Aralık
sorunsuz çekilmişti.

---

## Yapılanlar

**Zamanlayıcı dışarı taşındı** — `api/nobetci.js` (Vercel Cron). GitHub iş
akışlarını `workflow_dispatch` ile kendisi başlatıyor. GitHub'ın cron'u yedek;
işler idempotent, iki tetikleme zarar vermiyor. Vercel ücretsiz planda 2 cron
sınırı var, bayatlık nöbeti yayın görevinin içine alındı.

**Bildirim iki katmanlı ve dış servise bağımlı değil** — her issue kullanıcıya
atanıyor (GitHub'ın kendi e-postası). Nöbetçide Resend opsiyonel: mail yoksa
issue açıp atıyor. `uyari.py` Resend kurulunca devreye girer.

**CI/yerel farkı kaldırıldı** — `cek.py` her çekimde kırpılmış ham kopya da
yazıyor (`test_verisi/ham/`, ~250KB, depoya giriyor). `oyuncu_ortalama`
dışarıda: 5MB → 250KB. Yayın kapısı tam kopya yoksa buna düşüyor; tazeleyemezse
artık uyarı basıyor. Testler `ham/` gizlenerek de koşuldu.

**Ağ dayanıklılığı** — 4 deneme, 20 sn zaman aşımı, 5/10/20 sn bekleme. Üstüne
toplam bütçe (900 sn) — hem uykuyu hem **boşa geçen zaman aşımını** sayıyor.
Sadece uyku sayılsaydı 46 çağrının zaman aşımı iş tavanını aşardı ve bütçe
koruduğu şeyi korumaz olurdu. En kötü durum 30 dk, sınır 60 dk.

**Site dışarıya kapalıymış** — `ssoProtection: all_except_custom_domains`,
özel alan adı olmadığı için her şey kilitliydi. Giren herkes Vercel giriş
ekranı görüyordu; fark edilmemişti çünkü geliştirme tarayıcısı zaten giriş
yapmıştı. Kapatıldı, site artık HTTP 200.

---

## Ölçülen kanıtlar

```
Nöbetçi anahtarsız → {"hata":"yetkisiz"} HTTP 401
Nöbetçi anahtarlı  → {"gorev":"nobet","gun_gecti":0.03,"uyari":null} HTTP 200
Nöbetçi → GitHub   → {"tetikleme":{"durum":204,"tamam":true}} → in_progress (anında)

#2  2026-08-27T11:49:19Z  atanan=['yigitolmezcan']   <- e-posta gitti
#1  2026-08-26T05:57:44Z  atanan=YOK                 <- dün mail gelmemesinin sebebi

Site: overnight-yigit8.vercel.app  HTTP 200 · "tarih":"2025-12-20"
```

---

## Durum

| | |
|---|---|
| Yayında | **2025-12-20** |
| Hazır | **yok** — NBA API erişilemediği için üretilemedi |
| Emekli gece | 15 (19 Aralık bugün eklendi) |
| Test seti | **418** |

19 Aralık emekli edildi: iki üretim hakkını doldurmuştu ve ikisinde de "Mağlup
tarafta" kuralını ihlal ediyordu.

Yarın NBA servisi düzelirse gece üretilir ve 09:00'da yayınlanır. Düzelmezse
site 20 Aralık'ta kalır ama sessiz kalmaz — nöbetçi iki günü aşınca atanmış
issue açar.

## Açık işler

1. **`GH_JETON` değiştirilmeli.** Vercel'de şu an sohbete yapıştırılmış eski
   GitHub jetonu duruyor (kullanıcının koyduğunun üzerine yanlışlıkla yazıldı).
   Yeni jeton konmadan eskisi silinmemeli — nöbetçi sessizce ölür.
2. Bülten kurulumu yarım (Resend + Upstash yok).
3. Alan adı yok, site hâlâ `*.vercel.app`.
