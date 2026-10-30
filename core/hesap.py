"""Yerel giriş hesabı: kullanıcı adı + şifre (PBKDF2 ile hashlenir, düz saklanmaz)
ve 'Beni hatırla' (otomatik giriş) tercihi."""
import hashlib
import hmac
import json
import os

from core.kayit import veri_dosyasi_yolu

_TEKRAR = 200_000


def _yol():
    return veri_dosyasi_yolu().parent / "hesap.json"


def _hash(sifre: str, tuz: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), tuz, _TEKRAR).hex()


def _oku() -> dict | None:
    try:
        with open(_yol(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _yaz(veri: dict):
    yol = _yol()
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f)
    gecici.replace(yol)


def hesap_var_mi() -> bool:
    v = _oku()
    return bool(v and v.get("kullanici") and v.get("hash"))


def kullanici_adi() -> str:
    v = _oku()
    return v.get("kullanici", "") if v else ""


def hesap_olustur(kullanici: str, sifre: str, hatirla: bool = False):
    tuz = os.urandom(16)
    _yaz({"kullanici": kullanici.strip(), "tuz": tuz.hex(), "hash": _hash(sifre, tuz),
          "hatirla": bool(hatirla)})


def sifre_dogru_mu(kullanici: str, sifre: str) -> bool:
    v = _oku()
    if not v:
        return False
    ad_ok = hmac.compare_digest(v.get("kullanici", "").casefold().encode(), kullanici.strip().casefold().encode())
    hash_ok = hmac.compare_digest(_hash(sifre, bytes.fromhex(v["tuz"])), v["hash"])
    return ad_ok and hash_ok


def sifre_degistir(yeni_sifre: str):
    v = _oku()
    if not v:
        return
    tuz = os.urandom(16)
    v["tuz"], v["hash"] = tuz.hex(), _hash(yeni_sifre, tuz)
    _yaz(v)


def hatirla_ayarla(deger: bool):
    v = _oku()
    if v:
        v["hatirla"] = bool(deger)
        _yaz(v)


def hatirlaniyor_mu() -> bool:
    v = _oku()
    return bool(v and v.get("hatirla"))
