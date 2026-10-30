"""
Masa süresi dolunca: Windows sağ-alt bildirimi (uygulama arka planda/başka
ekranda olsa bile görünür) + uyarı sesi + görev çubuğunda yanıp sönme.
Ayarlar > Bildirim sayfasından özelleştirilir (ses dosyası, metin, tekrar).
"""
import io
import math
import shutil
import struct
import sys
import wave
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

VARSAYILAN_AYARLAR = {
    "bildirim_acik": True,
    "ses_acik": True,
    "ses_dosyasi": "",          # boş = yerleşik melodi
    "baslik": "⏰ {masa} - süre doldu!",
    "mesaj": "{birim} · {masa} masasının süresi bitti.",
    "tekrar_acik": True,
    "tekrar_saniye": 30,
    "ses_max_saniye": 8,        # uzun ses dosyaları en fazla bu kadar çalar
}


_MCI_ALIAS = "gh_uyari"


def _mci(komut: str) -> tuple:
    """Windows'un yerleşik MCI sesi (winmm): .wav ve .mp3'ü Qt Multimedia
    eklentilerine/codec'lerine İHTİYAÇ DUYMADAN çalar. (kod, yanıt) döner."""
    import ctypes
    tampon = ctypes.create_unicode_buffer(256)
    kod = ctypes.windll.winmm.mciSendStringW(komut, tampon, 255, 0)
    return kod, tampon.value


def mci_cal(yol: str) -> bool:
    _mci(f"close {_MCI_ALIAS}")
    tur = "waveaudio" if yol.lower().endswith(".wav") else "mpegvideo"
    kod, _ = _mci(f'open "{yol}" type {tur} alias {_MCI_ALIAS}')
    if kod != 0:
        return False
    kod, _ = _mci(f"play {_MCI_ALIAS}")
    return kod == 0


def mci_durdur():
    _mci(f"stop {_MCI_ALIAS}")
    _mci(f"close {_MCI_ALIAS}")


def mci_caliyor_mu() -> bool:
    kod, yanit = _mci(f"status {_MCI_ALIAS} mode")
    return kod == 0 and yanit == "playing"


def _log(mesaj: str):
    """Sorun giderme için küçük günlük: veri klasöründeki bildirim.log"""
    try:
        from datetime import datetime
        from core.kayit import veri_dosyasi_yolu
        yol = veri_dosyasi_yolu().parent / "bildirim.log"
        if yol.exists() and yol.stat().st_size > 100_000:
            yol.unlink()
        with open(yol, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%d.%m.%Y %H:%M:%S}  {mesaj}\n")
    except Exception:
        pass


def ayar_al(state) -> dict:
    a = dict(VARSAYILAN_AYARLAR)
    a.update(getattr(state, "bildirim_ayarlari", {}) or {})
    return a


def ses_klasoru() -> Path:
    from core.kayit import veri_dosyasi_yolu
    p = veri_dosyasi_yolu().parent / "sesler"
    p.mkdir(parents=True, exist_ok=True)
    return p


def ses_dosyasi_kopyala(kaynak: str) -> str:
    """Seçilen ses dosyasını uygulamanın veri klasörüne kopyalar (orijinal
    silinse/taşınsa bile çalmaya devam etsin) ve kayıtlı dosya adını döner."""
    k = Path(kaynak)
    hedef = ses_klasoru() / ("bildirim_sesi" + k.suffix.lower())
    for eski in ses_klasoru().glob("bildirim_sesi.*"):
        try:
            eski.unlink()
        except OSError:
            pass
    shutil.copyfile(k, hedef)
    return hedef.name


def _uyari_sesi_wav() -> bytes:
    """Dosyaya ihtiyaç duymadan bellekte üretilen kısa 'ding-dong' x3 melodisi."""
    hz = 22050
    notalar = [(880, 0.20), (1175, 0.30), (0, 0.12)] * 3
    veri = bytearray()
    for frekans, sure in notalar:
        n = int(hz * sure)
        for i in range(n):
            if frekans == 0:
                ornek = 0
            else:
                zarf = min(1.0, i / 300) * max(0.0, 1 - i / n) ** 1.5
                ornek = int(20000 * zarf * math.sin(2 * math.pi * frekans * i / hz))
            veri += struct.pack("<h", ornek)
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(hz)
        w.writeframes(bytes(veri))
    return tampon.getvalue()


class BildirimYoneticisi(QObject):
    def __init__(self, ana_pencere, ikon, state, parent=None):
        super().__init__(parent)
        self.ana_pencere = ana_pencere
        self.state = state
        self._wav = _uyari_sesi_wav()
        self._oynatici = None
        self._cikis = None
        self._durdur_zamanlayici = QTimer(self)
        self._durdur_zamanlayici.setSingleShot(True)
        self._durdur_zamanlayici.timeout.connect(self.sesi_durdur)
        self.tepsi = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tepsi = QSystemTrayIcon(ikon, self)
            self.tepsi.setToolTip("GameHub PS Salon")
            self.tepsi.messageClicked.connect(self._one_getir)
            self.tepsi.activated.connect(lambda _r: self._one_getir())
            self.tepsi.show()

    def ayarlar(self) -> dict:
        return ayar_al(self.state)

    def _one_getir(self):
        p = self.ana_pencere
        p.showNormal()
        p.raise_()
        p.activateWindow()

    def _ozel_ses_yolu(self, ayar=None):
        ayar = ayar or self.ayarlar()
        ad = ayar.get("ses_dosyasi")
        if not ad:
            return None
        try:
            yol = ses_klasoru() / ad
            return yol if yol.is_file() else None
        except Exception:
            return None

    def calıyor_mu(self) -> bool:
        if sys.platform == "win32":
            try:
                return mci_caliyor_mu()
            except Exception:
                return False
        try:
            from PyQt6.QtMultimedia import QMediaPlayer
            return self._oynatici is not None and \
                self._oynatici.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        except Exception:
            return False

    def sesi_durdur(self):
        self._durdur_zamanlayici.stop()
        if sys.platform == "win32":
            try:
                mci_durdur()
            except Exception:
                pass
        try:
            if self._oynatici is not None:
                self._oynatici.stop()
        except Exception:
            pass
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def ses_cal(self):
        """Seçili özel ses (wav/mp3) varsa onu, yoksa yerleşik melodiyi çalar.
        Uzun dosyalar ayardaki azami süre kadar çalar (sonsuza kadar değil)."""
        yol = self._ozel_ses_yolu()
        if yol is not None and sys.platform == "win32":
            try:
                ok = mci_cal(str(yol))
                _log(f"özel ses çal: {yol.name} -> {'tamam' if ok else 'BAŞARISIZ, varsayılana düşülüyor'}")
                if ok:
                    self._durdur_zamanlayici.start(max(1, int(self.ayarlar()["ses_max_saniye"])) * 1000)
                    return
            except Exception:
                pass  # özel ses çalınamazsa yerleşik melodiye düşülür
        elif yol is not None:
            try:
                from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
                if self._oynatici is None:
                    self._oynatici = QMediaPlayer(self)
                    self._cikis = QAudioOutput(self)
                    self._oynatici.setAudioOutput(self._cikis)
                self._oynatici.stop()
                self._oynatici.setSource(QUrl.fromLocalFile(str(yol)))
                self._cikis.setVolume(1.0)
                self._oynatici.play()
                self._durdur_zamanlayici.start(max(1, int(self.ayarlar()["ses_max_saniye"])) * 1000)
                return
            except Exception:
                pass  # özel ses çalınamazsa yerleşik melodiye düş
        try:
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(self._wav, winsound.SND_MEMORY | winsound.SND_ASYNC)
                return
        except Exception:
            pass
        QApplication.beep()

    def metin_hazirla(self, masa_ad: str, birim: str):
        a = self.ayarlar()
        def doldur(s):
            return s.replace("{masa}", masa_ad).replace("{birim}", birim)
        return doldur(a["baslik"]), doldur(a["mesaj"])

    def bildir(self, baslik: str, mesaj: str, ayarlari_yoksay: bool = False):
        """Gerçek uyarı ve 'Dene' AYNI yolu kullanır (test gerçeği yansıtsın).
        Önce Windows bildirimi gösterilir, ses ~0.7 sn SONRA çalınır: bildirimin
        kendi sistem sesi başlarken bizim sesin ezilip kesilmesini önlemek için."""
        a = self.ayarlar()
        if ayarlari_yoksay:
            a["ses_acik"] = a["bildirim_acik"] = True
        _log(f"bildir: '{baslik}' ses_acik={a['ses_acik']} bildirim_acik={a['bildirim_acik']} "
             f"ses_dosyasi='{a.get('ses_dosyasi','')}' tepsi={'var' if self.tepsi else 'YOK'}")
        if a["bildirim_acik"]:
            if self.tepsi is not None:
                self.tepsi.showMessage(baslik, mesaj, QSystemTrayIcon.MessageIcon.Warning, 15000)
            try:
                QApplication.alert(self.ana_pencere, 0)  # görev çubuğunda yanıp sönsün
            except Exception:
                pass
        if a["ses_acik"]:
            QTimer.singleShot(700 if a["bildirim_acik"] else 0, self._ses_cal_kayitli)

    def _ses_cal_kayitli(self):
        try:
            self.ses_cal()
            _log("ses_cal çağrıldı")
        except Exception as e:
            _log(f"ses_cal HATA: {e!r}")

    def dene(self):
        """Ayarlar sayfasındaki 'Dene' - gerçek uyarının AYNISINI verir."""
        baslik, mesaj = self.metin_hazirla("Masa 1", "PlayStation")
        self.bildir(baslik, mesaj, ayarlari_yoksay=True)
