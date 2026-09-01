// POST /api/abone  {eposta}
// Adresi LİSTEYE EKLEMEZ — sadece onay maili yollar. Kullanıcı kuralı:
// çift onay zorunlu, kullanıcı bağlantıya tıklayana kadar hiçbir yere
// yazılmaz. Böylece bir başkasının adresini buraya yazan biri o adresi
// listeye sokamaz; en fazla tek bir onay maili tetikler.
import { adresiNormallestir, token, kodla, mailGonder, ayarlarEksik, sayfa } from "./_ortak.js";

export default async function handler(istek, yanit) {
  if (istek.method !== "POST") return yanit.status(405).json({ hata: "Sadece POST" });

  const eksik = ayarlarEksik();
  if (eksik.length) {
    console.error("Eksik ortam değişkeni:", eksik.join(", "));
    return yanit.status(500).json({ hata: "Sunucu ayarları eksik." });
  }

  const govde = typeof istek.body === "string" ? JSON.parse(istek.body || "{}") : (istek.body || {});
  const adres = adresiNormallestir(govde.eposta);
  if (!adres) return yanit.status(400).json({ hata: "Geçerli bir e-posta adresi gir." });

  const kok = `https://${istek.headers["x-forwarded-host"] || istek.headers.host}`;
  const bag = `${kok}/api/onayla?e=${kodla(adres)}&t=${token("onay", adres)}`;

  try {
    await mailGonder({
      kime: adres,
      konu: "OVERNIGHT — aboneliğini onayla",
      metin: `Aboneliğini onaylamak için: ${bag}\n\nBu isteği sen yapmadıysan bu maili yok say; onaylamadığın sürece listeye eklenmezsin.`,
      html: `<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:520px;color:#1a1a1a">
<p style="font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.14em;color:#888">OVERNIGHT</p>
<h2 style="font-size:20px;margin:0 0 12px">Son bir adım</h2>
<p style="color:#444;line-height:1.6">Her sabah 09:00'da gecenin özetini yollayacağız. Onaylamak için:</p>
<p><a href="${bag}" style="display:inline-block;background:#E2701C;color:#fff;text-decoration:none;padding:12px 22px;font-weight:600">Aboneliği onayla</a></p>
<p style="color:#888;font-size:13px;line-height:1.6">Bu isteği sen yapmadıysan bu maili yok say — onaylamadığın sürece listeye eklenmezsin ve başka mail almazsın.</p>
</div>`,
    });
  } catch (e) {
    console.error("Onay maili gönderilemedi:", e.message);
    // TEŞHİS: Vercel'in çalışma zamanı kayıtları API'den okunamıyor ve
    // kullanıcıya dönen mesaj sebebi söylemiyor — bir kez bu yüzden
    // sebebi bulmak için tahmin yürütmek zorunda kaldık. Ops anahtarını
    // taşıyan istek gerçek hatayı da görüyor; anahtarsız istekte
    // davranış hiç değişmiyor.
    const tani =
      process.env.TANI_ANAHTARI &&
      istek.headers["x-tani"] === process.env.TANI_ANAHTARI;
    return yanit.status(502).json({
      hata: "Onay maili gönderilemedi, birazdan tekrar dene.",
      ...(tani ? { detay: String(e.message).slice(0, 400) } : {}),
    });
  }

  // Adresin listede olup olmadığını SÖYLEMİYORUZ — aynı yanıt her
  // durumda. Aksi halde bu uç nokta "bu adres kayıtlı mı?" sorusunu
  // yanıtlayan bir araca dönüşürdü.
  return yanit.status(200).json({ tamam: true, mesaj: "Onay maili yolladık, kutunu kontrol et." });
}
