// GET /api/onayla?e=<adres>&t=<token>
// Token doğrulanırsa adres listeye yazılır. Aynı adres iki kez eklenmez.
import { adresiNormallestir, tokenGecerli, coz, aboneEkle, sayfa, ayarlarEksik } from "./_ortak.js";

export default async function handler(istek, yanit) {
  yanit.setHeader("Content-Type", "text/html; charset=utf-8");
  if (ayarlarEksik().length) return yanit.status(500).send(sayfa("Bir sorun var", "Sunucu ayarları eksik. Kısa süre içinde düzelecek."));

  const adres = adresiNormallestir(coz(istek.query.e));
  if (!adres || !tokenGecerli("onay", adres, istek.query.t)) {
    return yanit.status(400).send(sayfa("Bağlantı geçersiz", "Bu onay bağlantısı okunamadı. Formu tekrar doldurup yeni bir mail isteyebilirsin."));
  }

  try {
    await aboneEkle(adres);
  } catch (e) {
    console.error("Liste güncellenemedi:", e.message);
    return yanit.status(502).send(sayfa("Bir sorun var", "Kaydını tamamlayamadık. Birazdan bağlantıya tekrar tıkla."));
  }

  return yanit.status(200).send(sayfa(
    "Kaydın tamam.",
    "Yarın sabah 09:00'da ilk özet kutunda olacak.",
    `<p><a href="/">Siteye dön</a></p>`
  ));
}
