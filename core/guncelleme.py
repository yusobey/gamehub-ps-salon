"""
Uzaktan güncelleme (internet varsa).

Akış: satıcı yeni kurulum dosyasını (GameHub_Kurulum_x.y.z.exe) ve imzalı
'surum.json' bildirimini bir adrese yükler -> program açılışta bildirimi okur
-> yeni sürüm varsa kullanıcıya sorar -> kurulum dosyasını indirir -> SHA256 ve
satıcının dijital imzasını doğrular (imza tutmazsa ASLA çalıştırmaz) -> kurulumu
sessizce çalıştırır, program kapanır, güncel sürüm açılır. Veriler %APPDATA%'da
olduğu için güncellemeden etkilenmez.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request

from PyQt6.QtCore import QObject, pyqtSignal

from core import ed25519
from core.lisans import ACIK_ANAHTAR
from core.surum import SURUM, GUNCELLEME_ADRESI, GUNCELLEME_ACIK_ANAHTAR


def surum_tuple(s: str) -> tuple:
    try:
        return tuple(int(p) for p in s.strip().split("."))
    except Exception:
        return (0,)


def bildirim_imza_mesaji(b: dict) -> bytes:
    return f"{b['surum']}|{b['sha256'].lower()}|{b['dosya']}".encode("utf-8")


def bildirimi_dogrula(b: dict) -> bool:
    try:
        mesaj, imza = bildirim_imza_mesaji(b), bytes.fromhex(b["imza"])
        # Önce güncelleme anahtarı (otomatik yayın), olmazsa eski satıcı anahtarı (elle yayın)
        return any(ed25519.verify(k, mesaj, imza)
                   for k in (bytes.fromhex(GUNCELLEME_ACIK_ANAHTAR), ACIK_ANAHTAR))
    except Exception:
        return False


def bildirimi_getir(adres: str | None = None, zaman_asimi: int = 8) -> dict | None:
    """surum.json'u indirir; imzası geçerliyse dict, değilse None (hata fırlatır: ağ)."""
    adres = adres or GUNCELLEME_ADRESI
    if not adres:
        raise RuntimeError("Güncelleme adresi ayarlanmamış.")
    istek = urllib.request.Request(adres, headers={"User-Agent": "GameHubPS-Guncelleme"})
    with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
        veri = json.loads(r.read().decode("utf-8"))
    return veri if bildirimi_dogrula(veri) else None


def yeni_surum_var_mi(b: dict | None) -> bool:
    return bool(b) and surum_tuple(b["surum"]) > surum_tuple(SURUM)


def indir_ve_dogrula(b: dict, ilerleme=None, hedef_klasor: str | None = None) -> str:
    """Kurulum dosyasını indirir, SHA256'sını bildirimle karşılaştırır, yolunu döner."""
    klasor = hedef_klasor or tempfile.mkdtemp(prefix="gamehub_guncelleme_")
    yol = os.path.join(klasor, "GameHub_Kurulum.exe")
    istek = urllib.request.Request(b["dosya"], headers={"User-Agent": "GameHubPS-Guncelleme"})
    h = hashlib.sha256()
    with urllib.request.urlopen(istek, timeout=30) as r, open(yol, "wb") as f:
        toplam = int(r.headers.get("Content-Length") or 0)
        okunan = 0
        while True:
            parca = r.read(256 * 1024)
            if not parca:
                break
            f.write(parca)
            h.update(parca)
            okunan += len(parca)
            if ilerleme and toplam:
                ilerleme(int(okunan * 100 / toplam))
    if h.hexdigest().lower() != b["sha256"].lower():
        os.remove(yol)
        raise RuntimeError("İndirilen dosya doğrulanamadı (bozuk veya değiştirilmiş). Güncelleme iptal edildi.")
    return yol


def kurulumu_baslat(yol: str):
    """Kurulumu sessiz başlatır (Windows). Çağıran program hemen kapanmalıdır."""
    if sys.platform != "win32":
        raise RuntimeError("Otomatik kurulum sadece Windows'ta çalışır.")
    subprocess.Popen([yol, "/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART"], close_fds=True)


class GuncellemeKontrolcu(QObject):
    """Arka planda kontrol eder; arayüzü dondurmaz."""
    sonuc = pyqtSignal(object, str)  # (bildirim | None, hata_mesaji)

    def kontrol_et(self):
        def is_():
            try:
                b = bildirimi_getir()
                if b is None:
                    self.sonuc.emit(None, "Güncelleme bildirimi doğrulanamadı.")
                else:
                    self.sonuc.emit(b, "")
            except Exception as e:
                self.sonuc.emit(None, str(e))
        threading.Thread(target=is_, daemon=True).start()
