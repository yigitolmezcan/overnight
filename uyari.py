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

GÖNDEREMEZSE BAŞARISIZ ÇIKAR (1). Eskiden tam tersiydi: ayar yoksa
"mail atlanıyor" yazıp 0 dönüyordu ve adım YEŞİL görünüyordu. 28-29
Ağustos'ta olan tam olarak buydu — yayın işi iki gün düştü, bu betik
her seferinde çalıştı, anahtar tanımlı olmadığı için hiçbir şey
göndermedi ve kimse haberdar olmadı. Kullanıcı kuralı: "uyaramadım da
bir arızadır ve raporlanmalı."

Bu betik zaten yalnız `if: failure()` altında çalışıyor; iş o noktada
zaten kırmızı. Buradaki 1, işi kırmızıya çeviren şey değil — kayıtta
"üstelik haber de veremedim" satırının görünmesini sağlayan şey.
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
    eksik = [ad for ad, deger in (("RESEND_API_KEY", RESEND),
                                  ("UYARI_ADRESI", ADRES)) if not deger]
    if eksik:
        print("uyari: UYARI GÖNDERİLEMEDİ — şu ayarlar tanımlı değil: "
              + ", ".join(eksik))
        return 1
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
        # SEBEBİ DE YAZ: yalnız kodu yazmak hata ayıklanamaz hâle
        # getiriyordu (403 gördük, nedenini öğrenmek için ayrı koşu
        # gerekti). Resend gövdede açık mesaj döndürüyor.
        try:
            neden = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            neden = "(gövde okunamadı)"
        print(f"uyari: UYARI GÖNDERİLEMEDİ (HTTP {e.code}) — {neden}")
        return 1
    except Exception as e:
        print(f"uyari: UYARI GÖNDERİLEMEDİ ({e})")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(gonder(sys.argv[1], sys.argv[2:]))
