# OVERNIGHT — canlıya alma

Üç adım. Hepsi tarayıcıdan, tek bir terminal komutu var.
Sırayı bozma; 3. adım 1. ve 2.'ye bağlı.

---

## 1 — Kodu GitHub'a koy

GitHub hesabın yoksa github.com'dan aç (ücretsiz).

Yeni bir depo oluştur: **github.com/new**
- Repository name: `overnight`
- **Private** seç (kod ve API kullanımı görünmesin)
- "Add a README" / ".gitignore" / "license" kutularının HİÇBİRİNİ işaretleme
- **Create repository**

Sonraki ekranda GitHub sana komutlar gösterecek; onları kullanma.
Bunun yerine Terminal'i aç (Spotlight → "Terminal") ve şunu olduğu gibi
yapıştır. `KULLANICI_ADIN` yazan yeri kendi GitHub kullanıcı adınla değiştir:

```bash
cd ~/Desktop/OVERNIGHT && git init && git add -A && git commit -m "OVERNIGHT ilk yayın" && git branch -M main && git remote add origin https://github.com/KULLANICI_ADIN/overnight.git && git push -u origin main
```

Kullanıcı adı ve şifre sorarsa: şifre yerine **Personal Access Token**
gerekiyor. github.com/settings/tokens → "Generate new token (classic)" →
`repo` kutusunu işaretle → oluştur → çıkan uzun metni şifre alanına yapıştır.

> `.env` dosyası depoya GİTMEZ — `.gitignore` içinde. API anahtarın
> koda hiçbir yerde yazılı değil.

---

## 2 — API anahtarını secret olarak koy

Deponda: **Settings → Secrets and variables → Actions → New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Secret: `.env` dosyandaki `sk-ant-...` ile başlayan değerin tamamı

**Add secret**.

Bir de aynı sayfada **Variables** sekmesine geçip bütçeyi oraya koyabilirsin
(istersen sonra tek yerden değiştirirsin):
- Name: `GUNLUK_BUTCE_USD` — Value: `1.00`

---

## 3 — Vercel'e bağla

**vercel.com** → "Continue with GitHub" ile giriş yap (ücretsiz Hobby planı).

- **Add New → Project**
- `overnight` deposunu seç → **Import**
- Framework Preset: **Other**
- Build ve Output ayarlarına DOKUNMA — depodaki `vercel.json` zaten söylüyor
- **Deploy**

Bir dakika sonra sana `overnight-xxxx.vercel.app` gibi bir adres verecek.
Adresin sabit hâli **Settings → Domains** altında; kendi alan adını da
oradan bağlayabilirsin.

Bundan sonra her `git push` kendiliğinden yayına çıkar — zamanlanmış iş
her sabah push attığı için sen hiçbir şey yapmayacaksın.

---

## Kendiliğinden ne oluyor

| Saat (TSİ) | İş | Ne yapıyor |
|---|---|---|
| 08:30 | `Gece üret` | Sıradaki arşiv gecesini çeker, metni üretir, depoya yazar |
| 09:00 | `Yayınla` | Hazır geceyi siteye gömer, push atar, Vercel yayına alır |

Aradaki yarım saat kasıtlı: üretim takılırsa 09:00 işi ortada hazır gece
bulamaz ve **hiçbir şey yapmaz** — site boşalmaz, bir önceki gece yayında kalır.

## Zamanlayıcı neden dışarıda

GitHub'ın kendi zamanlayıcısı bu depoda **güvenilir değil**. Ölçüldü:

| gün | ateşlenmesi gereken slot | gerçekten ateşlenen |
|---|---|---|
| 26 Ağustos | 6 | 2 |
| 27 Ağustos | 6 | 0 |

Elle tetikleme (`workflow_dispatch`) ise **anında** çalışıyor. Yani sorun
kota ya da bozuk bir dosya değil; GitHub zamanlanmış tetiklemeyi düşürüyor.
Bu bizim düzeltebileceğimiz bir şey değil — o yüzden zamanlayıcıyı dışarı
taşıdık.

**Asıl zamanlayıcı: Vercel Cron** → `api/nobetci.js` → GitHub'ı elle
tetikler gibi başlatır. GitHub'ın kendi cron'u yedek olarak duruyor.
İşler idempotent: ikisi birden ateşlerse ikinci hiçbir şey yapmaz.

Üstüne bir de **nöbet** var: her gün 11:00'de yayının bayatlığına bakar,
eşiği aşmışsa haber verir.

### Gereken tek ayar

Vercel → Settings → Environment Variables:

| değişken | değer |
|---|---|
| `GH_JETON` | GitHub'da yeni bir token (aşağıda) |
| `NOBETCI_ANAHTARI` | rastgele uzun bir metin, kendin uydur |

Vercel ÜCRETSİZ planda **en fazla 2 cron** olabiliyor ve saatler dakika
hassasiyetinde değil (06:00 cron'u 06:00–07:00 arasında bir yerde ateşler).
O yüzden GitHub'ın kendi cron'u da duruyor: hangisi önce ateşlerse iş
yapılır, ikincisi "zaten yapılmış" deyip geçer.

Token için: github.com/settings/tokens → **Fine-grained token** →
sadece `overnight` deposu → izinler: **Actions: Read and write**,
**Contents: Read**, **Issues: Read and write**.

Bu ikisi yeterli. E-posta (Resend) **isteğe bağlı**: kuruluysa mail atar,
kurulu değilse GitHub'da issue açıp seni atar — atama zaten GitHub'ın
kendi bildirim e-postasını tetikler.

Mail de istersen ekle: `RESEND_API_KEY`, `UYARI_ADRESI` (kendi adresin).

## Bir şey ters giderse

Üretim ya da yayın başarısız olursa deponda otomatik bir **Issue** açılır ve
GitHub sana e-posta yollar. E-posta gelmiyorsa:
github.com/settings/notifications → "Actions" altında
**"Send notifications for failed workflows only"** işaretli olsun.

Her iki durumda da site DEĞİŞMEZ; bir önceki gece yayında kalır.

## Elle müdahale (gerekmez ama dursun)

```bash
cd ~/Desktop/OVERNIGHT && python3 yayin.py durum
```

Deponun **Actions** sekmesinden her iki işi de "Run workflow" düğmesiyle
elle de çalıştırabilirsin.

---

# Bülten kurulumu

Sitenin altındaki kayıt formu artık gerçek. Çalışması için iki hesap ve
üç anahtar gerekiyor. Hepsi ücretsiz.

## 4 — Resend hesabı (mail gönderimi)

**https://resend.com** → **Sign up** (GitHub ile girebilirsin).

Ücretsiz katman: **ayda 3.000 mail, günde 100**. Birkaç yüz abonede
rahat rahat yeter; 100 aboneyi geçersen günlük limit dolar, o zaman
ücretli katmana (aylık $20) geçmek gerekir.

**Önemli kısıt:** Resend, doğrulanmış bir alan adın yoksa SADECE kendi
adresine mail göndermene izin verir. Yani:

- **Şimdi test etmek için**: hiçbir şey yapmana gerek yok, kendi adresine
  mail gider.
- **Başkalarına göndermek için**: bir alan adı gerekiyor (overnight.com.tr
  gibi). Resend'de **Domains → Add Domain** deyip verdiği DNS kayıtlarını
  alan adı sağlayıcına girmen gerek. Alan adın yoksa söyle, birlikte
  bakarız.

Hesap açtıktan sonra: **API Keys → Create API Key** → adını `overnight`
koy → **Sending access** yetkisi yeter → oluştur. Çıkan `re_...` ile
başlayan değeri kopyala, birazdan iki yere koyacağız.

## 5 — Upstash hesabı (abone listesi)

Abone adresleri **depoda tutulmuyor**. Sebebi: bir adres git geçmişine
girdikten sonra silinemez — abonelikten çıkan biri güncel listeden düşer
ama eski kayıtlarda kalır. Bunun yerine Upstash denen ücretsiz bir
depolama kullanıyoruz.

**https://upstash.com** → **Sign up** (GitHub ile girebilirsin).

- **Create Database** → **Redis**
- **Name**: `overnight`
- **Region**: sana en yakını (Frankfurt uygun)
- **Type**: **Free**
- **Create**

Açılan sayfada aşağı in, **REST API** bölümünü bul. İki değer var:
`UPSTASH_REDIS_REST_URL` ve `UPSTASH_REDIS_REST_TOKEN`. İkisini de
kopyala (her birinin yanında kopyalama düğmesi var).

Ücretsiz katman: 256 MB veri ve ayda yüz binlerce komut. Biz günde
birkaç komut kullanıyoruz (bir abone eklendiğinde bir, bülten
gönderilirken bir) — bu sınırlara yaklaşmamız mümkün değil.

## 6 — Anahtarları yerine koy

### Vercel'e (formun çalışması için)

Projende: **Settings → Environment Variables**. Dört tane ekle, hepsinde
Environment olarak **Production, Preview, Development** üçünü de işaretle:

| Name | Value |
|---|---|
| `RESEND_API_KEY` | Resend'den aldığın `re_...` |
| `UPSTASH_REDIS_REST_URL` | Upstash'ten aldığın `https://...upstash.io` |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash'ten aldığın uzun değer |
| `ABONE_GIZLI_ANAHTAR` | aşağıdaki komutun ürettiği değer |

Gizli anahtarı üretmek için Terminal'de:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(32))"
```

Çıkan değeri kopyala — **hem Vercel'e hem GitHub'a AYNI değeri**
koyacaksın. Onay ve çıkış bağlantıları bu anahtarla imzalanıyor; iki
taraf farklı olursa bağlantılar çalışmaz.

Değişkenleri ekledikten sonra Vercel'de **Deployments → en üstteki →
⋯ → Redeploy** de (yeni değişkenler ancak yeni deploy'da geçerli olur).

### GitHub'a (günlük gönderim için)

**Settings → Secrets and variables → Actions**

**Secrets** sekmesinde dört tane:

| Name | Value |
|---|---|
| `RESEND_API_KEY` | aynı `re_...` |
| `ABONE_GIZLI_ANAHTAR` | Vercel'e koyduğun AYNI değer |
| `UPSTASH_REDIS_REST_URL` | Vercel'e koyduğun AYNI değer |
| `UPSTASH_REDIS_REST_TOKEN` | Vercel'e koyduğun AYNI değer |

**Variables** sekmesinde iki tane:

| Name | Value |
|---|---|
| `SITE_ADRESI` | Vercel'in verdiği adres, sonunda `/` olmadan |
| `GONDEREN_ADRES` | alan adın yoksa `OVERNIGHT <onboarding@resend.dev>` |

## 7 — Kendi adresinle test et

1. Siteyi aç, alttaki forma **kendi adresini** yaz, gönder
2. "Onay maili yolladık" yazısını gör
3. Mail kutuna gelen maildeki **Aboneliği onayla** düğmesine bas
4. "Kaydın tamam" sayfasını gör
5. Upstash panelinde **Data Browser** sekmesine bak — `overnight:aboneler`
   içinde adresini görmelisin
6. Bülteni beklemeden denemek için, deponun **Actions → Yayınla → Run
   workflow** düğmesine bas

Mailin altındaki **Abonelikten çık** bağlantısını da dene; adresin
listeden çıkmalı.

## Bilmen gereken iki şey

**Abone adresleri artık depoda değil.** Upstash'te duruyorlar ve
abonelikten çıkan biri gerçekten siliniyor — geride iz kalmıyor. Adresler
şifrelenmiş değil; Upstash hesabına giren onları görebilir, o yüzden o
hesabın parolasını güçlü tut.

**Form kötüye kullanılabilir.** Biri başkasının adresini yazarsa o adrese
bir onay maili gider (listeye EKLENMEZ, çift onay bunu engelliyor). Resend'in
günlük 100 mail limiti doğal bir tavan; kötüye kullanım görürsen söyle,
forma hız sınırı eklerim.

---

# Alan adı

Resend, doğrulanmış bir alan adın olmadan sadece **kendi adresine** mail
atmana izin veriyor. Başkalarına göndermek için bir alan adı şart.

## İsim önerileri

Hepsi kısa, akılda kalır ve "overnight" geçiyor. Alınıp alınmadığını
sipariş ekranında göreceksin — biri doluysa sıradakine geç.

| Alan adı | Neden | Yıllık (yaklaşık) |
|---|---|---|
| **overnight.report** | "overnight report" diye okunuyor, tam işi anlatıyor | ~$15 |
| **overnightnba.com** | En açık ve en güvenli seçim, kimse şaşırmaz | ~$12 |
| **overnight.gg** | `.gg` spor/oyun dünyasında tanıdık, kısa | ~$25 |
| **overnightnba.co** | `.com` doluysa en yakın alternatif | ~$12 |
| **overnight.basketball** | Anlamı tartışmasız ama uzun ve pahalı | ~$40 |

Benim önerim **overnight.report** — sitenin ne olduğunu ismin kendisi
söylüyor ve `.com` kalabalığında kaybolmuyor.

## Nereden alınır

**https://porkbun.com** öneriyorum: fiyatları düşük, gizlilik koruması
(WHOIS privacy) ücretsiz ve ekranı sade. Namecheap veya Cloudflare da
olur; aşağıdaki adımlar hepsinde benzer.

1. Porkbun'da arama kutusuna ismi yaz, **Search**
2. Uygun olanın yanındaki **Add to cart** → **Checkout**
3. Hesap aç, öde (kredi kartı yeter)

## Vercel'e bağlama

1. Vercel'de projene gir → **Settings → Domains**
2. **Add** → aldığın alan adını yaz (ör. `overnight.report`) → **Add**
3. Vercel sana **iki nameserver** ya da **birkaç DNS kaydı** gösterecek.
   En kolayı nameserver yöntemi: `ns1.vercel-dns.com` ve
   `ns2.vercel-dns.com`
4. Porkbun'da: **Domain Management** → alan adının yanındaki **Details** →
   **Authoritative Nameservers** → **Edit** → Vercel'in verdiği iki
   adresi yaz → **Submit**
5. Vercel'e dön, birkaç dakika içinde alan adının yanında yeşil bir
   onay çıkar

> Bu yayılma bazen 1-2 saat sürebilir. Sabırlı ol, bir şey bozulmadı.

Bağlandıktan sonra GitHub'daki `SITE_ADRESI` değişkenini yeni adrese
güncelle (sonunda `/` olmadan, ör. `https://overnight.report`).

## Resend'de doğrulama

1. Resend'de **Domains** → **Add Domain**
2. Alan adını yaz → **Add**
3. Resend sana 3 kayıt verecek (bir `MX`, iki `TXT` — DKIM ve SPF)
4. **Nameserver'ları Vercel'e verdiysen** bu kayıtları Vercel'de
   gireceksin: **Settings → Domains → alan adın → DNS Records → Add**
   - Her kayıt için: Resend'deki **Type**, **Name** ve **Value**
     alanlarını birebir kopyala
5. Resend'e dön → **Verify DNS Records**
6. Üçü de yeşil olunca hazırsın

> Kopyalarken **Name** alanına dikkat: Resend `send` ya da
> `resend._domainkey` gibi kısa bir ad verir. Vercel'de de aynen o kısa
> hâlini yaz, sonuna alan adını EKLEME.

Doğrulama bitince GitHub'daki `GONDEREN_ADRES` değişkenini güncelle:

```
OVERNIGHT <gunaydin@overnight.report>
```

`gunaydin@` kısmını istediğin gibi seçebilirsin, o adresin ayrıca var
olması gerekmiyor — alan adı doğrulanmış olması yeterli.

## Sıra önemli

Alan adını al → Vercel'e bağla → Resend'de doğrula → iki değişkeni
güncelle. Doğrulama bitmeden bülten hâlâ sadece sana gider; sistem
bozulmaz, sadece bekler.
