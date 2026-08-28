# Fontlar

Bu klasördeki fontlar **SIL Open Font License 1.1** ile dağıtılıyor ve
depoya bilerek konuldu.

| Dosya | Aile | Kaynak |
|---|---|---|
| `BricolageGrotesque.ttf` | Bricolage Grotesque ExtraBold | Google Fonts |
| `DMMono-Regular.ttf` | DM Mono Regular | Google Fonts |
| `DMMono-Medium.ttf` | DM Mono Medium | Google Fonts |

**Neden depoda:** paylaşım görüntüsü (`og_uret.py`) Pillow ile
çiziliyor ve GitHub koşucusunda sistem fontu yok. Tarayıcı kurmak
(Playwright/Puppeteer) yerine üç font dosyası taşımak hem daha hızlı
hem daha az kırılgan — üretim ağa hiç çıkmıyor.

Sayfa bu fontları Google Fonts'tan yüklemeye devam ediyor; buradaki
kopyalar SADECE görüntü üretimi için.
