"""GitHub Actions tarafından çağrılır: kurulum dosyasından imzalı surum.json üretir.
Gizli anahtar ortam değişkeninden (GUNCELLEME_ANAHTARI) okunur, depoda ASLA bulunmaz.
Kullanım: python arac/surum_imzala.py KURULUM.exe SURUM ADRES   (notlar: NOTLAR ortam değişkeni)"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import ed25519  # noqa: E402


def main():
    yol, surum, adres = sys.argv[1:4]
    gizli = bytes.fromhex(os.environ["GUNCELLEME_ANAHTARI"].strip())
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(1024 * 1024), b""):
            h.update(p)
    sha = h.hexdigest().lower()
    imza = ed25519.sign(gizli, f"{surum}|{sha}|{adres}".encode("utf-8")).hex()
    with open("surum.json", "w", encoding="utf-8") as f:
        json.dump({"surum": surum, "dosya": adres, "sha256": sha,
                   "notlar": os.environ.get("NOTLAR", ""), "imza": imza}, f, ensure_ascii=False, indent=2)
    print("surum.json hazir:", surum, sha)


if __name__ == "__main__":
    main()
