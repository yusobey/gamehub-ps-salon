"""Ayarlar > Veri ve Güncelleme: klasörler, yedek al/geri yükle, sürüm, güncelleme."""
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QFileDialog,
    QApplication, QProgressBar, QMessageBox,
)

from core import kayit, guncelleme
from core.surum import SURUM, GUNCELLEME_ADRESI
from core.theme import RENK
from ui.widgets import OrtalanmisDialog, soru_sor, uyar, bilgilendir

_YEDEKLENEN = ("salon_verileri.json", "gorseller", "sesler")


def program_klasoru() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(sys.argv[0]).resolve().parent


def klasoru_ac(yol: Path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(yol)))


class GuncellemeDialog(OrtalanmisDialog):
    def __init__(self, bildirim: dict, parent=None):
        super().__init__(parent)
        self.bildirim = bildirim
        self.setWindowTitle("Güncelleme")
        self.setMinimumWidth(440)
        self.setStyleSheet(f"""
            QDialog {{ background:#FFFFFF; }} QLabel {{ background:transparent; color:{RENK['text']}; }}
            QPushButton#ana {{ background:{RENK['accent']}; color:white; border:none; border-radius:9px;
                padding:11px 18px; font-weight:800; }}
            QPushButton#ana:disabled {{ background:#B9BCD0; }}
            QPushButton#ikinci {{ background:#FFFFFF; border:1px solid {RENK['border_strong']};
                border-radius:9px; padding:10px 16px; font-weight:700; }}
            QProgressBar {{ border:1px solid {RENK['border_strong']}; border-radius:6px; height:14px; text-align:center; }}
            QProgressBar::chunk {{ background:{RENK['accent2']}; border-radius:5px; }}
        """)
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 22)
        v.setSpacing(10)
        t = QLabel(f"🎉  Yeni sürüm var: {bildirim['surum']}")
        t.setStyleSheet("font-size:18px; font-weight:900;")
        v.addWidget(t)
        v.addWidget(QLabel(f"Kurulu sürüm: {SURUM}"))
        notlar = bildirim.get("notlar", "")
        if notlar:
            n = QLabel(notlar)
            n.setWordWrap(True)
            n.setStyleSheet(f"background:{RENK['bg']}; border-radius:8px; padding:10px;")
            v.addWidget(n)
        v.addWidget(QLabel("Verileriniz (kasa, masalar, ürünler) güncellemeden etkilenmez."))
        self.bar = QProgressBar()
        self.bar.hide()
        v.addWidget(self.bar)
        self.durum = QLabel("")
        self.durum.setWordWrap(True)
        self.durum.setStyleSheet(f"color:{RENK['danger']}; font-weight:700;")
        v.addWidget(self.durum)
        satir = QHBoxLayout()
        sonra = QPushButton("Sonra")
        sonra.setObjectName("ikinci")
        sonra.clicked.connect(self.reject)
        satir.addWidget(sonra)
        self.btn = QPushButton("Şimdi Güncelle")
        self.btn.setObjectName("ana")
        self.btn.clicked.connect(self._guncelle)
        satir.addWidget(self.btn)
        v.addLayout(satir)

    def _guncelle(self):
        self.btn.setEnabled(False)
        self.durum.setText("")
        self.bar.show()
        QApplication.processEvents()
        try:
            def ilerle(y):
                self.bar.setValue(y)
                QApplication.processEvents()
            yol = guncelleme.indir_ve_dogrula(self.bildirim, ilerle)
            guncelleme.kurulumu_baslat(yol)
        except Exception as e:
            self.durum.setText(str(e))
            self.btn.setEnabled(True)
            self.bar.hide()
            return
        # kurulum başladı: program kapanmalı ki dosyalar değiştirilebilsin
        kayit.kaydet(self.parent().state) if self.parent() is not None and hasattr(self.parent(), "state") else None
        QApplication.instance().quit()
        os._exit(0)


class VeriSayfasi(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)
        b = QLabel("Ayarlar  ›  Veri ve Güncelleme")
        b.setObjectName("pageTitle")
        v.addWidget(b)

        v.addWidget(self._kart("Klasörler", [
            ("Program klasörü", str(program_klasoru()), lambda: klasoru_ac(program_klasoru())),
            ("Veri klasörü (kasa, ürünler, görseller, yedekler)", str(kayit.veri_dosyasi_yolu().parent),
             lambda: klasoru_ac(kayit.veri_dosyasi_yolu().parent)),
        ]))

        yk = QFrame()
        yk.setObjectName("masaKart")
        yk.setMaximumWidth(760)
        yv = QVBoxLayout(yk)
        yv.setContentsMargins(18, 14, 18, 14)
        yv.addWidget(self._baslik("Yedek"))
        a = QLabel("Verilerinizin kopyasını bir .zip dosyasına alın (flash bellek, başka bilgisayar için). "
                   "Program ayrıca her gün otomatik yedek tutar.")
        a.setWordWrap(True)
        a.setStyleSheet(f"color:{RENK['text_muted']}; background:transparent;")
        yv.addWidget(a)
        s = QHBoxLayout()
        al = QPushButton("💾  Yedek Al…")
        al.setObjectName("secenekBtn")
        al.clicked.connect(self._yedek_al)
        s.addWidget(al)
        gy = QPushButton("♻️  Yedekten Geri Yükle…")
        gy.setObjectName("ghostBtn")
        gy.clicked.connect(self._geri_yukle)
        s.addWidget(gy)
        s.addStretch()
        yv.addLayout(s)
        v.addWidget(yk)

        gk = QFrame()
        gk.setObjectName("masaKart")
        gk.setMaximumWidth(760)
        gv = QVBoxLayout(gk)
        gv.setContentsMargins(18, 14, 18, 14)
        gv.addWidget(self._baslik("Sürüm ve Güncelleme"))
        self.surum_lbl = QLabel(f"Kurulu sürüm: {SURUM}")
        self.surum_lbl.setStyleSheet("background:transparent; font-weight:700;")
        gv.addWidget(self.surum_lbl)
        self.durum_lbl = QLabel("")
        self.durum_lbl.setWordWrap(True)
        self.durum_lbl.setStyleSheet(f"color:{RENK['text_muted']}; background:transparent;")
        gv.addWidget(self.durum_lbl)
        self.denetle_btn = QPushButton("🔄  Güncellemeleri Denetle")
        self.denetle_btn.setObjectName("secenekBtn")
        self.denetle_btn.clicked.connect(self._denetle)
        gv.addWidget(self.denetle_btn, 0, Qt.AlignmentFlag.AlignLeft)
        v.addWidget(gk)
        v.addStretch()

        self._kontrolcu = guncelleme.GuncellemeKontrolcu(self)
        self._kontrolcu.sonuc.connect(self._denetim_sonucu)

    def _baslik(self, t):
        l = QLabel(t)
        l.setStyleSheet(f"font-weight:800; font-size:14px; background:transparent; color:{RENK['text']};")
        return l

    def _kart(self, baslik, satirlar):
        k = QFrame()
        k.setObjectName("masaKart")
        k.setMaximumWidth(760)
        kv = QVBoxLayout(k)
        kv.setContentsMargins(18, 14, 18, 14)
        kv.setSpacing(8)
        kv.addWidget(self._baslik(baslik))
        for etiket, yol, fn in satirlar:
            e = QLabel(etiket)
            e.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px; background:transparent;")
            kv.addWidget(e)
            h = QHBoxLayout()
            y = QLabel(yol)
            y.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            y.setWordWrap(True)
            y.setStyleSheet("background:transparent; font-weight:600;")
            h.addWidget(y, 1)
            ac = QPushButton("Klasörü Aç")
            ac.setObjectName("ghostBtn")
            ac.clicked.connect(fn)
            h.addWidget(ac)
            kv.addLayout(h)
        return k

    # ------------------------------------------------------------ yedek
    def _yedek_al(self):
        kayit.kaydet(self.state)  # en güncel hali diske yaz
        varsayilan = f"GameHub_Yedek_{datetime.now():%Y%m%d_%H%M}.zip"
        yol, _ = QFileDialog.getSaveFileName(self, "Yedeği kaydet", varsayilan, "Zip dosyası (*.zip)")
        if not yol:
            return
        try:
            taban = kayit.veri_dosyasi_yolu().parent
            with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
                for ad in _YEDEKLENEN:
                    p = taban / ad
                    if p.is_file():
                        z.write(p, ad)
                    elif p.is_dir():
                        for f in p.rglob("*"):
                            if f.is_file():
                                z.write(f, str(f.relative_to(taban)))
        except Exception as e:
            uyar(self, "Hata", f"Yedek alınamadı:\n{e}")
            return
        bilgilendir(self, "Yedek alındı", f"Yedek kaydedildi:\n{yol}")

    def _geri_yukle(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Yedek dosyası seçin", "", "Zip dosyası (*.zip)")
        if not yol:
            return
        c = soru_sor(self, "Geri Yükle",
                     "Şu anki TÜM veriler seçtiğiniz yedekle DEĞİŞTİRİLECEK ve program kapanacak. "
                     "Devam edilsin mi?")
        if c != QMessageBox.StandardButton.Yes:
            return
        try:
            taban = kayit.veri_dosyasi_yolu().parent
            with zipfile.ZipFile(yol) as z:
                adlar = z.namelist()
                if "salon_verileri.json" not in adlar:
                    uyar(self, "Geçersiz yedek", "Bu dosya bir GameHub yedeği değil.")
                    return
                kayit.KAYIT_ENGELLI = True  # kapanırken eski veri üstüne yazılmasın
                for ad in adlar:
                    if ".." in ad or ad.startswith(("/", "\\")):
                        continue
                    if not ad.split("/")[0] in _YEDEKLENEN:
                        continue
                    hedef = taban / ad
                    if ad.endswith("/"):
                        hedef.mkdir(parents=True, exist_ok=True)
                        continue
                    hedef.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(ad) as src, open(hedef, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        except Exception as e:
            kayit.KAYIT_ENGELLI = False
            uyar(self, "Hata", f"Geri yüklenemedi:\n{e}")
            return
        bilgilendir(self, "Tamam", "Yedek geri yüklendi. Program şimdi kapanacak; tekrar açın.")
        QApplication.instance().quit()
        os._exit(0)

    # ------------------------------------------------------------ güncelleme
    def _denetle(self):
        if not GUNCELLEME_ADRESI:
            self.durum_lbl.setText("Güncelleme adresi ayarlanmamış (satıcı tarafından tanımlanır).")
            return
        self.denetle_btn.setEnabled(False)
        self.durum_lbl.setText("Denetleniyor…")
        self._kontrolcu.kontrol_et()

    def _denetim_sonucu(self, bildirim, hata):
        self.denetle_btn.setEnabled(True)
        if bildirim is None:
            self.durum_lbl.setText(f"Denetlenemedi: {hata}")
        elif guncelleme.yeni_surum_var_mi(bildirim):
            self.durum_lbl.setText(f"Yeni sürüm bulundu: {bildirim['surum']}")
            GuncellemeDialog(bildirim, self.window()).exec()
        else:
            self.durum_lbl.setText("✓ Programınız güncel.")
