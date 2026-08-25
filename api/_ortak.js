// Bülten uç noktalarının ortak parçaları.
//
// TASARIM KARARI — veritabanı yok. Abone listesi deponun içinde düz bir
// JSON dosyası (config/aboneler.json); uç noktalar GitHub Contents API
// ile okuyup yazıyor. Birkaç yüz aboneye kadar bu fazlasıyla yeterli ve
// bakım gerektirmiyor: yedek zaten git geçmişinde, listeyi görmek için
// dosyaya bakmak yeterli.
//
// TASARIM KARARI — onay ve çıkış bağlantıları DURUMSUZ. Token, adresin
// gizli anahtarla HMAC'i; hiçbir yerde saklanmıyor, uç nokta yeniden
// hesaplayıp karşılaştırıyor. Böylece "bekleyen onaylar" için ikinci bir
// depoya ihtiyaç kalmıyor ve onaysız adres hiçbir yere yazılmıyor.

import crypto from "node:crypto";

export const DEPO = process.env.GITHUB_DEPO || "";
const DEPO_TOKEN = process.env.GITHUB_DEPO_TOKEN || "";
const GIZLI = process.env.ABONE_GIZLI_ANAHTAR || "";
export const LISTE_YOLU = "config/aboneler.json";

export function ayarlarEksik() {
  const eksik = [];
  if (!DEPO) eksik.push("GITHUB_DEPO");
  if (!DEPO_TOKEN) eksik.push("GITHUB_DEPO_TOKEN");
  if (!GIZLI) eksik.push("ABONE_GIZLI_ANAHTAR");
  if (!process.env.RESEND_API_KEY) eksik.push("RESEND_API_KEY");
  return eksik;
}

// Adres doğrulama: aşırı yaratıcı olmayan, pratikte işe yarayan bir
// kontrol. Amaç geçersiz girdiyi elemek, RFC 5322'yi taklit etmek değil.
const ADRES_DESENI = /^[^\s@,;:<>()[\]\\]+@[^\s@.,;:<>()[\]\\]+(\.[^\s@.,;:<>()[\]\\]+)+$/;

export function adresiNormallestir(ham) {
  const adres = String(ham || "").trim().toLowerCase();
  if (adres.length < 6 || adres.length > 254) return null;
  if (!ADRES_DESENI.test(adres)) return null;
  return adres;
}

export function token(amac, adres) {
  return crypto.createHmac("sha256", GIZLI).update(`${amac}:${adres}`).digest("base64url");
}

// Zamanlama saldırısına kapalı karşılaştırma — token doğrulaması bir
// sır kontrolü, uzunluk farkı bile sızdırmasın.
export function tokenGecerli(amac, adres, gelen) {
  const beklenen = Buffer.from(token(amac, adres));
  const verilen = Buffer.from(String(gelen || ""));
  return beklenen.length === verilen.length && crypto.timingSafeEqual(beklenen, verilen);
}

export const kodla = (s) => Buffer.from(s, "utf8").toString("base64url");
export const coz = (s) => Buffer.from(String(s || ""), "base64url").toString("utf8");

async function githubIstek(yol, secenek = {}) {
  const yanit = await fetch(`https://api.github.com/repos/${DEPO}/${yol}`, {
    ...secenek,
    headers: {
      Authorization: `Bearer ${DEPO_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "overnight-bulten",
      ...(secenek.headers || {}),
    },
  });
  return yanit;
}

export async function listeOku() {
  const yanit = await githubIstek(`contents/${LISTE_YOLU}`);
  if (yanit.status === 404) return { aboneler: [], sha: null };
  if (!yanit.ok) throw new Error(`Liste okunamadı (${yanit.status})`);
  const veri = await yanit.json();
  const icerik = JSON.parse(Buffer.from(veri.content, "base64").toString("utf8"));
  return { aboneler: icerik.aboneler || [], sha: veri.sha };
}

export async function listeYaz(aboneler, sha, mesaj) {
  const govde = JSON.stringify({ _aciklama: "Onaylı bülten aboneleri. api/onayla.js ekler, api/cikis.js çıkarır — elle düzenlenmesi gerekmez.", aboneler }, null, 2) + "\n";
  const yanit = await githubIstek(`contents/${LISTE_YOLU}`, {
    method: "PUT",
    body: JSON.stringify({
      message: mesaj,
      content: Buffer.from(govde, "utf8").toString("base64"),
      ...(sha ? { sha } : {}),
    }),
  });
  if (!yanit.ok) throw new Error(`Liste yazılamadı (${yanit.status}): ${await yanit.text()}`);
}

export async function mailGonder({ kime, konu, html, metin }) {
  const yanit = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: process.env.GONDEREN_ADRES || "OVERNIGHT <onboarding@resend.dev>",
      to: [kime],
      subject: konu,
      html,
      text: metin,
    }),
  });
  if (!yanit.ok) throw new Error(`Mail gönderilemedi (${yanit.status}): ${await yanit.text()}`);
}

export function sayfa(baslik, mesaj, altMesaj = "") {
  return `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${baslik} · OVERNIGHT</title>
<style>body{background:#080B11;color:#E8EAED;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:24px;text-align:center}
.k{max-width:460px}h1{font-size:24px;margin:0 0 12px;letter-spacing:-.02em}p{color:#9AA4B2;margin:0 0 20px}
a{color:#E2701C;text-decoration:none;border-bottom:1px solid #E2701C;padding-bottom:1px}
.m{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;letter-spacing:.14em;color:#5A6472;text-transform:uppercase;margin-bottom:18px}</style>
</head><body><div class="k"><div class="m">OVERNIGHT</div><h1>${baslik}</h1><p>${mesaj}</p>${altMesaj}</div></body></html>`;
}
