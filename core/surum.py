"""Sürüm ve güncelleme ayarları.

SURUM            : Her yeni sürümde (güncelleme yayınlarken) artırın: 1.0.0 -> 1.1.0
GUNCELLEME_ADRESI: Yayınladığınız 'surum.json' dosyasının İNTERNET adresi.
                   Boş bırakılırsa otomatik güncelleme kontrolü kapalıdır.
                   Örnek (GitHub Releases): 
                   https://github.com/KULLANICI/DEPO/releases/latest/download/surum.json
"""
SURUM = "1.0.4"
GUNCELLEME_ADRESI = "https://github.com/yusobey/gamehub-ps-salon/releases/latest/download/surum.json"

# Güncelleme bildirimlerini doğrulayan AÇIK anahtar. Karşılığı olan GİZLİ anahtar yalnızca GitHub
# "Secrets" içinde (GUNCELLEME_ANAHTARI) durur; lisans üretme anahtarından AYRIDIR - sızsa bile
# kimse lisans üretemez.
GUNCELLEME_ACIK_ANAHTAR = "b81c302358511b34747d1dbcf4bcc856d0d8a74e929cc539b6a50a8c01b85cc9"
