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

## 5 — Depoya yazma izni (abone listesi için)

Abone listesi ayrı bir veritabanında değil, deponun içinde
`config/aboneler.json` dosyasında duruyor. Formu işleyen kodun oraya
yazabilmesi için dar yetkili bir anahtar gerekiyor.

**https://github.com/settings/personal-access-tokens/new**

- **Token name**: `overnight-bulten`
- **Expiration**: `1 year`
- **Repository access**: **Only select repositories** → `overnight`
- **Permissions → Repository permissions** → **Contents** → **Read and write**
- **Generate token**

Çıkan `github_pat_...` değerini kopyala.

## 6 — Anahtarları yerine koy

### Vercel'e (formun çalışması için)

Projende: **Settings → Environment Variables**. Dört tane ekle, hepsinde
Environment olarak **Production, Preview, Development** üçünü de işaretle:

| Name | Value |
|---|---|
| `RESEND_API_KEY` | Resend'den aldığın `re_...` |
| `GITHUB_DEPO_TOKEN` | GitHub'dan aldığın `github_pat_...` |
| `GITHUB_DEPO` | `yigitolmezcan/overnight` |
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

**Secrets** sekmesinde iki tane:

| Name | Value |
|---|---|
| `RESEND_API_KEY` | aynı `re_...` |
| `ABONE_GIZLI_ANAHTAR` | Vercel'e koyduğun AYNI değer |

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
5. Depoda `config/aboneler.json` dosyasına bak — adresin orada olmalı
6. Bülteni beklemeden denemek için, deponun **Actions → Yayınla → Run
   workflow** düğmesine bas

Mailin altındaki **Abonelikten çık** bağlantısını da dene; adresin
listeden çıkmalı.

## Bilmen gereken iki şey

**Abone adresleri depoda duruyor.** Depo gizli (private), o yüzden
kimse göremez. Ama git geçmişi silinmez: biri abonelikten çıkınca adresi
güncel listeden düşer, eski commit'lerde kalmaya devam eder. Birkaç yüz
kişilik bir bülten için kabul edilebilir; liste binlere çıkarsa gerçek
bir veritabanına geçmek gerekir.

**Form kötüye kullanılabilir.** Biri başkasının adresini yazarsa o adrese
bir onay maili gider (listeye EKLENMEZ, çift onay bunu engelliyor). Resend'in
günlük 100 mail limiti doğal bir tavan; kötüye kullanım görürsen söyle,
forma hız sınırı eklerim.
