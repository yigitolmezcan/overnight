// Bülten uç noktalarının ortak parçaları.
//
// TASARIM KARARI — abone listesi DEPONUN DIŞINDA. Önce depoda düz bir
// JSON dosyasındaydı; çalışıyordu ama kalıcı bir kusuru vardı: bir adres
// git geçmişine girdikten sonra silinemiyor. Abonelikten çıkan biri
// güncel listeden düşüyor ama eski commit'lerde kalmaya devam ediyordu.
// Depo bir gün herkese açılırsa adresler orada. Beş kişiyken önemsiz,
// elli kişiyken ciddi — ve sonradan taşımak şimdi taşımaktan zor.
//
// Yerine Upstash Redis (REST API). Seçilme sebebi: HTTP üzerinden
// çalışıyor, yani sunucusuz fonksiyonda bağlantı havuzu/istemci
// kütüphanesi gerekmiyor — düz `fetch` yetiyor, projeye tek bir
// bağımlılık eklenmiyor. Veri tek bir SET içinde: SADD ekler, SREM
// çıkarır, SMEMBERS listeler.
//
// TASARIM KARARI — onay ve çıkış bağlantıları DURUMSUZ (bu kısım
// değişmedi). Token, adresin gizli anahtarla HMAC'i; hiçbir yerde
// saklanmıyor, uç nokta yeniden hesaplayıp karşılaştırıyor. Onaysız
// adres hiçbir yere yazılmıyor.

import crypto from "node:crypto";

const REDIS_URL = (process.env.UPSTASH_REDIS_REST_URL || "").replace(/\/$/, "");
const REDIS_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN || "";
const GIZLI = process.env.ABONE_GIZLI_ANAHTAR || "";
export const ANAHTAR = "overnight:aboneler";

export function ayarlarEksik() {
  const eksik = [];
  if (!REDIS_URL) eksik.push("UPSTASH_REDIS_REST_URL");
  if (!REDIS_TOKEN) eksik.push("UPSTASH_REDIS_REST_TOKEN");
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

async function redis(...komut) {
  const yanit = await fetch(REDIS_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${REDIS_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(komut),
  });
  if (!yanit.ok) throw new Error(`Depolama hatası (${yanit.status}): ${await yanit.text()}`);
  return (await yanit.json()).result;
}

export async function aboneEkle(adres) {
  // SADD kümeye ekler; adres zaten varsa 0 döner, yani aynı adres iki
  // kez kaydedilmiyor ve ayrıca kontrol etmeye gerek kalmıyor.
  return (await redis("SADD", ANAHTAR, adres)) === 1;
}

export async function aboneCikar(adres) {
  return (await redis("SREM", ANAHTAR, adres)) === 1;
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
