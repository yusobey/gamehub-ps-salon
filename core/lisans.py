"""
Lisans sistemi (internet gerektirmez).

* Anahtar, satıcının GİZLİ anahtarıyla Ed25519 imzalanır; uygulamanın içinde
  yalnızca DOĞRULAMA (açık) anahtarı vardır. Bu yüzden herkes kendi anahtarını
  kopyalayıp çoğaltabilir ama YENİ anahtar üretemez.
* Anahtar isteğe bağlı olarak belirli bir CİHAZA bağlanır (cihaz kodu) - başka
  bilgisayarda çalışmaz. İsteğe bağlı bitiş tarihi taşır.
* Anahtar formatı:  GH-XXXXXX-XXXXXX-...  (Base32, kopyala-yapıştır içindir)
"""
import base64
import hashlib
import json
import os
import sys
from datetime import date, datetime, timedelta

from core import ed25519
from core.kayit import veri_dosyasi_yolu

# Satıcının AÇIK anahtarı (gizli anahtar ASLA uygulamada bulunmaz)
ACIK_ANAHTAR = bytes.fromhex("28d099c635787b873daa5e5f48b3b28d0e671e2a901a0baef29c07d63ce52876")

_SURUM = 1
_EPOCH = date(2020, 1, 1)


class LisansHatasi(Exception):
    pass


# ---------------------------------------------------------------- cihaz kodu
def _makine_kimligi() -> str:
    try:
        if sys.platform == "win32":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                                0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                return str(winreg.QueryValueEx(k, "MachineGuid")[0])
        for yol in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            if os.path.isfile(yol):
                return open(yol).read().strip()
    except Exception:
        pass
    import uuid
    return str(uuid.getnode())


def cihaz_hash() -> bytes:
    return hashlib.sha256(b"GameHubPS|" + _makine_kimligi().encode()).digest()[:8]


def cihaz_kodu() -> str:
    h = cihaz_hash().hex().upper()
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def cihaz_kodunu_coz(kod: str) -> bytes:
    h = "".join(c for c in kod.upper() if c in "0123456789ABCDEF")
    if len(h) != 16:
        raise LisansHatasi("Cihaz kodu 16 karakter (A-F, 0-9) olmalı.")
    return bytes.fromhex(h)


# ------------------------------------------------------------ anahtar üretimi
def anahtar_uret(gizli: bytes, musteri_id: int, cihaz: bytes | None = None,
                 bitis: date | None = None) -> str:
    """SADECE lisans üretici araçta kullanılır."""
    bayrak = 1 if cihaz else 0
    bitis_gun = 0 if bitis is None else (bitis - _EPOCH).days
    if not (0 <= bitis_gun < 65536):
        raise LisansHatasi("Bitiş tarihi geçersiz.")
    veri = (b"GH" + bytes([_SURUM, bayrak]) + int(musteri_id).to_bytes(4, "big")
            + bitis_gun.to_bytes(2, "big") + (cihaz or bytes(8)))
    imza = ed25519.sign(gizli, veri)
    ham = base64.b32encode(veri + imza).decode().rstrip("=")
    return "GH-" + "-".join(ham[i:i + 6] for i in range(0, len(ham), 6))


# --------------------------------------------------------------- doğrulama
def anahtar_coz(anahtar: str) -> dict:
    """İmzayı/biçimi doğrular, içeriği döner. Hata varsa LisansHatasi."""
    metin = "".join(anahtar.split()).upper().replace("-", "")
    if metin.startswith("GH"):
        metin = metin[2:]
    else:
        raise LisansHatasi("Geçersiz lisans anahtarı.")
    # 'GH-' öneki de Base32 harfi olduğundan: baştaki GH atılınca kalan ham Base32'dir
    try:
        ham = base64.b32decode(metin + "=" * (-len(metin) % 8))
    except Exception:
        raise LisansHatasi("Geçersiz lisans anahtarı (karakter hatası).")
    if len(ham) != 18 + 64:
        raise LisansHatasi("Geçersiz lisans anahtarı (eksik veya fazla karakter).")
    veri, imza = ham[:18], ham[18:]
    if veri[:2] != b"GH" or not ed25519.verify(ACIK_ANAHTAR, veri, imza):
        raise LisansHatasi("Geçersiz lisans anahtarı.")
    bitis_gun = int.from_bytes(veri[8:10], "big")
    return {
        "surum": veri[2],
        "cihaza_bagli": bool(veri[3] & 1),
        "musteri_id": int.from_bytes(veri[4:8], "big"),
        "bitis": None if bitis_gun == 0 else _EPOCH + timedelta(days=bitis_gun),
        "cihaz": veri[10:18],
    }


def _lisans_dosyasi():
    return veri_dosyasi_yolu().parent / "lisans.json"


def anahtar_kontrol(anahtar: str, bugun: date | None = None) -> dict:
    """Anahtarı bu cihazda/bugün geçerli mi diye denetler; geçerliyse bilgi döner."""
    bilgi = anahtar_coz(anahtar)
    bugun = bugun or date.today()
    if bilgi["cihaza_bagli"] and bilgi["cihaz"] != cihaz_hash():
        raise LisansHatasi("Bu lisans anahtarı başka bir bilgisayar için üretilmiş.")
    if bilgi["bitis"] is not None and bugun > bilgi["bitis"]:
        raise LisansHatasi(f"Lisansın süresi {bilgi['bitis']:%d.%m.%Y} tarihinde doldu.")
    return bilgi


def kayitli_anahtar() -> str | None:
    try:
        with open(_lisans_dosyasi(), "r", encoding="utf-8") as f:
            return json.load(f).get("anahtar")
    except Exception:
        return None


def anahtari_kaydet(anahtar: str):
    yol = _lisans_dosyasi()
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"anahtar": "".join(anahtar.split()).upper(),
                   "son_gorulen": date.today().isoformat()}, f)


def kayitli_lisansi_dogrula() -> dict:
    """Açılışta çağrılır. Geçerliyse bilgi, değilse LisansHatasi."""
    anahtar = kayitli_anahtar()
    if not anahtar:
        raise LisansHatasi("Lisans anahtarı girilmemiş.")
    bilgi = anahtar_kontrol(anahtar)
    # Süreli lisansta sistem saatini geri alarak süre uzatmayı engelle
    if bilgi["bitis"] is not None:
        try:
            with open(_lisans_dosyasi(), "r", encoding="utf-8") as f:
                veri = json.load(f)
            son = date.fromisoformat(veri.get("son_gorulen", ""))
            if date.today() < son - timedelta(days=1):
                raise LisansHatasi("Sistem saati geriye alınmış görünüyor. Lütfen tarihi düzeltin.")
            if date.today() > son:
                veri["son_gorulen"] = date.today().isoformat()
                with open(_lisans_dosyasi(), "w", encoding="utf-8") as f:
                    json.dump(veri, f)
        except LisansHatasi:
            raise
        except Exception:
            pass
    return bilgi
