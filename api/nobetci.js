// NÖBETÇİ — zamanlayıcının kendisini izleyen dış göz.
//
// NEDEN GEREKLİ (gerçek arıza, 2026-08-27): GitHub Actions iki gün üst
// üste zamanlanmış işi ateşlemedi. Hata bildirimi de gelmedi — ÇÜNKÜ
// BİLDİRİM İŞİN KENDİ İÇİNDEYDİ. İş hiç koşmayınca bildirimi yazacak
// adım da koşmuyor. Alarm, izlediği sistemin içinde yaşayamaz.
//
// Bu uç nokta GitHub'ın DIŞINDA (Vercel) çalışıyor ve iki iş yapıyor:
//   1) TETİKLE — GitHub iş akışını workflow_dispatch ile kendisi
//      başlatır. Ölçüldü: elle tetiklenen koşu ANINDA başlıyor,
//      zamanlanmış tetikleme ise düşüyor. Yani asıl zamanlayıcı artık
//      burası; GitHub'ın kendi cron'u yedek olarak duruyor.
//   2) NÖBET — yayının bayatlığını kontrol eder, eşiği aşmışsa
//      e-posta atar. İş hiç koşmasa bile bu mail gelir.
//
// İşler İDEMPOTENT (uret: hazır gece varsa atlar, yayinla: yayınlanmışsa
// atlamaz) — iki zamanlayıcının da ateşlemesi zarar vermez.
//
// GÜVENLİK: uç nokta NOBETCI_ANAHTARI ile korunuyor. Anahtarsız istek
// hiçbir şey yapmaz. GitHub jetonu sadece burada, ortam değişkeninde.

const GH_DEPO = process.env.GH_DEPO || "yigitolmezcan/overnight";
const GH_JETON = process.env.GH_JETON || "";
const ANAHTAR = process.env.NOBETCI_ANAHTARI || "";
const UYARI_ADRESI = process.env.UYARI_ADRESI || "";
const BAYATLIK_ESIGI_GUN = Number(process.env.BAYATLIK_ESIGI_GUN || 2);

// ZORUNLU tek ayar: GH_JETON. Kullanıcıya bırakılan kurulum işi ne
// kadar azsa o kadar iyi — her ek değişken bir kurulum adımı, her
// kurulum adımı bir arıza ihtimali.
//
// NOBETCI_ANAHTARI ZORUNLU — Vercel cron da dahil HER çağrı bunu
// taşımak zorunda.
//
// Önceden `x-vercel-cron` başlığının VARLIĞI kimlik yerine geçiyordu.
// O bir kapıydı: başlık istemci tarafından yazılıyor, yani internetteki
// herkes tek bir curl ile üretim/yayın iş akışlarını tetikleyebiliyordu
// (ölçüldü: `curl -H "x-vercel-cron: 1" .../api/nobetci` → HTTP 200).
// Vercel'in kendi cron'u, `CRON_SECRET` ortam değişkeni tanımlıysa
// isteğe `Authorization: Bearer <CRON_SECRET>` koyuyor — doğru yol bu.
// CRON_SECRET ile NOBETCI_ANAHTARI aynı değere kuruluyor, böylece cron
// da elle çağrı da AYNI kapıdan geçiyor.
//
// Resend de opsiyonel: e-posta kurulu değilse nöbetçi susmuyor, GitHub'da
// issue açıp kullanıcıyı ATIYOR — atama GitHub'ın kendi bildirimini
// tetikliyor. "Uyarı yolu kurulmamış" bir sessizlik sebebi olamaz.
function eksikAyarlar() {
  const eksik = [];
  if (!GH_JETON) eksik.push("GH_JETON");
  return eksik;
}

const MAIL_KURULU = () => Boolean(process.env.RESEND_API_KEY && UYARI_ADRESI);

async function gh(yol, secenekler = {}) {
  const yanit = await fetch(`https://api.github.com/repos/${GH_DEPO}${yol}`, {
    ...secenekler,
    headers: {
      Authorization: `Bearer ${GH_JETON}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "overnight-nobetci",
      ...(secenekler.headers || {}),
    },
  });
  return yanit;
}

async function isAkisiniTetikle(dosya) {
  const yanit = await gh(`/actions/workflows/${dosya}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main" }),
  });
  return { dosya, durum: yanit.status, tamam: yanit.status === 204 };
}

// Yayın durumunu DEPODAN okuyor (site/index.html değil): tek doğru
// kaynak orası ve sitenin dağıtımı gecikse bile doğru cevabı verir.
async function sonYayinTarihi() {
  const yanit = await gh("/contents/config/yayin_durumu.json?ref=main", {
    headers: { Accept: "application/vnd.github.raw+json" },
  });
  if (!yanit.ok) throw new Error(`yayin_durumu okunamadı (${yanit.status})`);
  const d = JSON.parse(await yanit.text());
  return d?.son_yayin?.yayinlandi || null;
}

// Tek giriş noktası: hangi yol açıksa oradan haber veriyor.
async function haberVer(konu, satirlar) {
  if (MAIL_KURULU()) {
    try {
      await mailAt(konu, satirlar);
      return "mail";
    } catch (e) {
      console.error("mail gitmedi, issue'ya düşülüyor:", e.message);
    }
  }
  const yanit = await gh("/issues", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: konu,
      body: satirlar.join("\n\n"),
      assignees: [GH_DEPO.split("/")[0]],
    }),
  });
  return yanit.ok ? "issue" : `haber verilemedi (HTTP ${yanit.status})`;
}

async function mailAt(konu, satirlar) {
  const metin = satirlar.join("\n");
  const html = `<div style="font:15px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<p>${satirlar.map((s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;")).join("<br>")}</p></div>`;
  const yanit = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: process.env.GONDEREN_ADRES || "OVERNIGHT <onboarding@resend.dev>",
      to: [UYARI_ADRESI],
      subject: konu,
      html,
      text: metin,
    }),
  });
  if (!yanit.ok) throw new Error(`uyarı maili gönderilemedi (${yanit.status})`);
}

export default async function handler(istek, yanit) {
  // TEK KAPI. Vercel cron `Authorization: Bearer <CRON_SECRET>` ile
  // geliyor (CRON_SECRET = NOBETCI_ANAHTARI), elle çağrı aynı başlıkla
  // ya da ?anahtar= ile. `x-vercel-cron` başlığı ARTIK KİMLİK DEĞİL —
  // istemci yazabildiği için kapı işlevi görüyordu.
  const verilen = istek.query?.anahtar || (istek.headers.authorization || "").replace(/^Bearer\s+/i, "");
  // Anahtar tanımlı DEĞİLSE hiçbir çağrı kabul edilmiyor; boş anahtarla
  // boş isteğin eşleşmesi kapının kendisi olurdu.
  const anahtarGecerli = Boolean(ANAHTAR) && verilen.length > 0 && verilen === ANAHTAR;
  if (!anahtarGecerli) {
    return yanit.status(401).json({ hata: "yetkisiz" });
  }

  const eksik = eksikAyarlar();
  if (eksik.length) {
    // Ayar eksikse SESSİZ KALMIYOR — bu uç noktanın var olma sebebi
    // sessiz arızayı önlemek; kendi sessiz arızası kabul edilemez.
    console.error("Nöbetçi ayarları eksik:", eksik.join(", "));
    return yanit.status(500).json({ hata: "ayarlar eksik", eksik });
  }

  const gorev = (istek.query?.gorev || "nobet").toString();
  const rapor = { gorev, zaman: new Date().toISOString() };

  try {
    if (gorev === "uret" || gorev === "yayinla") {
      rapor.tetikleme = await isAkisiniTetikle(`${gorev}.yml`);
      if (!rapor.tetikleme.tamam) {
        rapor.haber = await haberVer("OVERNIGHT · iş tetiklenemedi", [
          `${gorev}.yml tetiklenemedi.`,
          `GitHub yanıtı: HTTP ${rapor.tetikleme.durum}`,
          "Site bugün güncellenmeyebilir.",
        ]);
        return yanit.status(200).json(rapor);
      }
      // Vercel ücretsiz planda 2 cron sınırı var; bayatlık nöbeti ayrı
      // bir cron olamıyor. Yayın görevi tetiklemeyi yaptıktan SONRA
      // aynı çağrıda nöbeti de tutuyor — dünkü yayın çıkmadıysa bunu
      // yakalayan tek katman bu.
      if (gorev !== "yayinla") return yanit.status(200).json(rapor);
    }

    // Nöbet: yayın bayat mı?
    const sonYayin = await sonYayinTarihi();
    rapor.son_yayin = sonYayin;
    if (!sonYayin) {
      rapor.haber = await haberVer("OVERNIGHT · hiç yayın kaydı yok", [
        "config/yayin_durumu.json içinde son_yayin bulunamadı.",
      ]);
      rapor.uyari = "kayit_yok";
      return yanit.status(200).json(rapor);
    }
    const gun = (Date.now() - Date.parse(sonYayin)) / 86400000;
    rapor.gun_gecti = Number(gun.toFixed(2));
    rapor.esik_gun = BAYATLIK_ESIGI_GUN;
    if (gun > BAYATLIK_ESIGI_GUN) {
      rapor.haber = await haberVer("OVERNIGHT · site bayatladı", [
        `Son yayın: ${sonYayin}`,
        `Üstünden ${gun.toFixed(1)} gün geçti (eşik: ${BAYATLIK_ESIGI_GUN} gün).`,
        "Zamanlayıcı çalışmamış olabilir.",
        `Koşular: https://github.com/${GH_DEPO}/actions`,
      ]);
      rapor.uyari = "bayat";
    } else {
      rapor.uyari = null;
    }
    return yanit.status(200).json(rapor);
  } catch (hata) {
    console.error("Nöbetçi hatası:", hata);
    try {
      await haberVer("OVERNIGHT · nöbetçi hata verdi", [String(hata && hata.message)]);
    } catch (_) { /* mail de gitmiyorsa kayıt en azından Vercel loglarında */ }
    return yanit.status(500).json({ hata: String(hata && hata.message) });
  }
}
