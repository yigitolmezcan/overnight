#!/usr/bin/env python3
"""Arıza uyarısı — e-posta.

NEDEN: hata bildirimi şimdiye kadar SADECE GitHub Issue açıyordu.
Kullanıcı Issues sekmesine bakmıyor; "iki gündür üretim yok ve bana
hiçbir e-posta gelmedi" şikâyeti bundan. Issue kalıyor (izlenebilirlik
için), üstüne mail ekleniyor.

SINIRI: bu betik iş AKTIĞINDA çalışır. İş hiç koşmazsa buradan mail
çıkmaz — o durumu GitHub'ın DIŞINDAKİ nöbetçi yakalıyor (api/nobetci.js).
İki katman ayrı sebeplerle var, biri diğerinin yerine geçmiyor.

Kullanım:
    python3 uyari.py "konu" "gövde satırı" ["ikinci satır" ...]

Ayar yoksa SESSİZCE ve BAŞARIYLA çıkar (0): uyarı gönderememek, işin
kendisini başarısız saymak için sebep değil — asıl hata zaten
raporlanıyor.
"""
import html as _html
import json
import os
import sys
import urllib.error
import urllib.request

RESEND = os.environ.get("RESEND_API_KEY", "")
ADRES = os.environ.get("UYARI_ADRESI", "")
GONDEREN = os.environ.get("GONDEREN_ADRES", "OVERNIGHT <onboarding@resend.dev>")


def govde_html(satirlar):
    guvenli = [_html.escape(s) for s in satirlar]
    return ('<div style="font:15px/1.6 -apple-system,sans-serif"><p>'
            + "<br>".join(guvenli) + "</p></div>")


def gonder(konu, satirlar):
    if not RESEND or not ADRES:
        print("uyari: RESEND_API_KEY ya da UYARI_ADRESI yok — mail atlanıyor.")
        return 0
    istek = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps({
            "from": GONDEREN,
            "to": [ADRES],
            "subject": konu,
            "html": govde_html(satirlar),
            "text": "\n".join(satirlar),
        }).encode("utf-8"),
        headers={"Authorization": f"Bearer {RESEND}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(istek, timeout=20) as yanit:
            yanit.read()
        print(f"uyari: mail gönderildi -> {ADRES}")
        return 0
    except urllib.error.HTTPError as e:
        print(f"uyari: mail gönderilemedi ({e.code})")
        return 0
    except Exception as e:
        print(f"uyari: mail gönderilemedi ({e})")
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(gonder(sys.argv[1], sys.argv[2:]))
