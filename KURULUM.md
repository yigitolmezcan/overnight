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
