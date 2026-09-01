"""Sitenin adresi — TEK KAYNAK.

og:url, og:image, canonical, bülten bağlantıları ve çıkış (unsubscribe)
adresi hep buradan okuyor. Eskiden yayin.py'de sabit, bulten.py'de ayrı
bir ortam değişkeninde duruyordu; alan adı değişince biri güncellenip
öbürü eski Vercel adresinde kalıyordu.

Ortam değişkeni SITE_ADRESI verilirse o kazanır (test ve önizleme için).
"""
import os

VARSAYILAN = "https://overnightnba.com"


def site_adresi():
    return (os.environ.get("SITE_ADRESI") or VARSAYILAN).rstrip("/")


SITE_ADRESI = site_adresi()
