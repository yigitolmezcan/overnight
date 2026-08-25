// GET /api/cikis?e=<adres>&t=<token>
// Her bültenin altındaki tek tıklık çıkış bağlantısı. Onay ekranı YOK —
// kullanıcı çıkmak için tıkladıysa çıkar; araya ekran koymak hem yasal
// beklentiye hem de servislerin şartına aykırı.
import { adresiNormallestir, tokenGecerli, coz, listeOku, listeYaz, sayfa, ayarlarEksik } from "./_ortak.js";

export default async function handler(istek, yanit) {
  yanit.setHeader("Content-Type", "text/html; charset=utf-8");
  if (ayarlarEksik().length) return yanit.status(500).send(sayfa("Bir sorun var", "Sunucu ayarları eksik."));

  const adres = adresiNormallestir(coz(istek.query.e));
  if (!adres || !tokenGecerli("cikis", adres, istek.query.t)) {
    return yanit.status(400).send(sayfa("Bağlantı geçersiz", "Bu çıkış bağlantısı okunamadı."));
  }

  try {
    const { aboneler, sha } = await listeOku();
    const kalan = aboneler.filter((a) => a.eposta !== adres);
    if (kalan.length !== aboneler.length) await listeYaz(kalan, sha, "abonelikten çıkıldı");
  } catch (e) {
    console.error("Liste güncellenemedi:", e.message);
    return yanit.status(502).send(sayfa("Bir sorun var", "Çıkışını kaydedemedik. Birazdan tekrar dene."));
  }

  return yanit.status(200).send(sayfa("Çıkışın alındı.", "Bir daha mail göndermeyeceğiz.", `<p><a href="/">Siteye dön</a></p>`));
}
