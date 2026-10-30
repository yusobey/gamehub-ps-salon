"""Açılış akışı: lisans etkinleştirme -> hesap oluşturma -> giriş (beni hatırla)."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
    QPlainTextEdit, QApplication,
)

from core import lisans, hesap
from core.theme import RENK, kaynak_yolu
from ui.widgets import OrtalanmisDialog, uyar, bilgilendir

_STIL = f"""
QDialog {{ background-color:#FFFFFF; }}
QLabel {{ background:transparent; color:{RENK['text']}; }}
QLineEdit, QPlainTextEdit {{
    background-color:{RENK['bg']}; border:1px solid {RENK['border_strong']};
    border-radius:8px; padding:9px 11px; color:{RENK['text']}; font-size:13px; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border:1.5px solid {RENK['accent']}; }}
QCheckBox {{ background:transparent; }}
QPushButton#anaBtn {{
    background-color:{RENK['accent']}; color:white; border:none; border-radius:9px;
    padding:11px 18px; font-weight:800; font-size:13px; }}
QPushButton#anaBtn:hover {{ background-color:#5B3DE0; }}
QPushButton#ikinciBtn {{
    background-color:#FFFFFF; color:{RENK['text']}; border:1px solid {RENK['border_strong']};
    border-radius:9px; padding:9px 14px; font-weight:700; }}
QPushButton#ikinciBtn:hover {{ background-color:#E4F3FC; border-color:#8FD1F2; }}
QPushButton#linkBtn {{
    background:transparent; border:none; color:{RENK['accent']}; font-weight:700; padding:4px; }}
QPushButton#linkBtn:hover {{ text-decoration:underline; }}
"""


class _TemelDialog(OrtalanmisDialog):
    def __init__(self, baslik: str, alt: str, genislik: int = 440, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GameHub PS Salon")
        self.setMinimumWidth(genislik)
        self.setStyleSheet(_STIL)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(34, 28, 34, 26)
        self.v.setSpacing(10)
        yol = kaynak_yolu("logo_kafa.png")
        if yol:
            logo = QLabel()
            logo.setPixmap(QPixmap(yol).scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.v.addWidget(logo)
        t = QLabel(baslik)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("font-size:21px; font-weight:900;")
        self.v.addWidget(t)
        a = QLabel(alt)
        a.setAlignment(Qt.AlignmentFlag.AlignCenter)
        a.setWordWrap(True)
        a.setStyleSheet(f"font-size:12px; color:{RENK['text_muted']}; margin-bottom:6px;")
        self.v.addWidget(a)

    def alan(self, etiket: str, sifre: bool = False, yer: str = "") -> QLineEdit:
        l = QLabel(etiket)
        l.setStyleSheet("font-weight:700; font-size:12px; margin-top:4px;")
        self.v.addWidget(l)
        e = QLineEdit()
        e.setPlaceholderText(yer)
        if sifre:
            e.setEchoMode(QLineEdit.EchoMode.Password)
        self.v.addWidget(e)
        return e

    def hata_etiketi(self) -> QLabel:
        h = QLabel("")
        h.setWordWrap(True)
        h.setStyleSheet(f"color:{RENK['danger']}; font-weight:700; font-size:12px;")
        self.v.addWidget(h)
        return h


# ------------------------------------------------------------- lisans
class LisansDialog(_TemelDialog):
    def __init__(self, mesaj: str = "", parent=None):
        super().__init__("Lisans Etkinleştirme",
                         "Programı kullanmak için size verilen lisans anahtarını girin.", 520, parent)
        l = QLabel("Cihaz Kodunuz  (lisans talep ederken bize iletin)")
        l.setStyleSheet("font-weight:700; font-size:12px; margin-top:4px;")
        self.v.addWidget(l)
        satir = QHBoxLayout()
        kod = QLineEdit(lisans.cihaz_kodu())
        kod.setReadOnly(True)
        kod.setStyleSheet("font-family:Consolas,monospace; font-weight:800; font-size:15px; letter-spacing:1px;")
        satir.addWidget(kod, 1)
        kopya = QPushButton("Kopyala")
        kopya.setObjectName("ikinciBtn")
        kopya.clicked.connect(lambda: (QApplication.clipboard().setText(lisans.cihaz_kodu()),
                                       kopya.setText("Kopyalandı ✓")))
        satir.addWidget(kopya)
        self.v.addLayout(satir)

        l2 = QLabel("Lisans Anahtarı")
        l2.setStyleSheet("font-weight:700; font-size:12px; margin-top:6px;")
        self.v.addWidget(l2)
        self.anahtar = QPlainTextEdit()
        self.anahtar.setPlaceholderText("GH-XXXXXX-XXXXXX-XXXXXX-...")
        self.anahtar.setFixedHeight(84)
        self.v.addWidget(self.anahtar)
        self.hata = self.hata_etiketi()
        self.hata.setText(mesaj)

        etkin = QPushButton("Etkinleştir")
        etkin.setObjectName("anaBtn")
        etkin.setDefault(True)
        etkin.clicked.connect(self._etkinlestir)
        self.v.addWidget(etkin)
        cik = QPushButton("Çıkış")
        cik.setObjectName("linkBtn")
        cik.clicked.connect(self.reject)
        self.v.addWidget(cik, 0, Qt.AlignmentFlag.AlignCenter)

    def _etkinlestir(self):
        anahtar = " ".join(self.anahtar.toPlainText().split())
        try:
            lisans.anahtar_kontrol(anahtar)
        except lisans.LisansHatasi as e:
            self.hata.setText(str(e))
            return
        lisans.anahtari_kaydet(anahtar)
        self.accept()


# --------------------------------------------------------------- hesap
class HesapOlusturDialog(_TemelDialog):
    def __init__(self, parent=None):
        super().__init__("Hesabınızı Oluşturun",
                         "Lisansınız etkinleştirildi. Programa giriş için bir kullanıcı adı ve şifre belirleyin.",
                         parent=parent)
        self.kullanici = self.alan("Kullanıcı adı")
        self.sifre = self.alan("Şifre", True)
        self.sifre2 = self.alan("Şifre (tekrar)", True)
        self.hatirla = QCheckBox("Beni hatırla (sonraki açılışta otomatik giriş)")
        self.hatirla.setChecked(True)
        self.v.addWidget(self.hatirla)
        self.hata = self.hata_etiketi()
        b = QPushButton("Hesabı Oluştur")
        b.setObjectName("anaBtn")
        b.setDefault(True)
        b.clicked.connect(self._olustur)
        self.v.addWidget(b)

    def _olustur(self):
        ad, s1, s2 = self.kullanici.text().strip(), self.sifre.text(), self.sifre2.text()
        if len(ad) < 3:
            self.hata.setText("Kullanıcı adı en az 3 karakter olmalı.")
        elif len(s1) < 4:
            self.hata.setText("Şifre en az 4 karakter olmalı.")
        elif s1 != s2:
            self.hata.setText("Şifreler aynı değil.")
        else:
            hesap.hesap_olustur(ad, s1, self.hatirla.isChecked())
            self.accept()


class GirisDialog(_TemelDialog):
    def __init__(self, parent=None):
        super().__init__("Hoş Geldiniz", "Devam etmek için giriş yapın.", parent=parent)
        self.kullanici = self.alan("Kullanıcı adı")
        self.kullanici.setText(hesap.kullanici_adi())
        self.sifre = self.alan("Şifre", True)
        self.hatirla = QCheckBox("Beni hatırla")
        self.hatirla.setChecked(True)
        self.v.addWidget(self.hatirla)
        self.hata = self.hata_etiketi()
        b = QPushButton("Giriş Yap")
        b.setObjectName("anaBtn")
        b.setDefault(True)
        b.clicked.connect(self._giris)
        self.v.addWidget(b)
        unut = QPushButton("Şifremi unuttum")
        unut.setObjectName("linkBtn")
        unut.clicked.connect(self._unuttum)
        self.v.addWidget(unut, 0, Qt.AlignmentFlag.AlignCenter)
        self.sifre.setFocus() if self.kullanici.text() else self.kullanici.setFocus()

    def _giris(self):
        if hesap.sifre_dogru_mu(self.kullanici.text(), self.sifre.text()):
            hesap.hatirla_ayarla(self.hatirla.isChecked())
            self.accept()
        else:
            self.hata.setText("Kullanıcı adı veya şifre hatalı.")
            self.sifre.clear()

    def _unuttum(self):
        SifreSifirlaDialog(self).exec()


class SifreSifirlaDialog(_TemelDialog):
    def __init__(self, parent=None):
        super().__init__("Şifre Yenileme",
                         "Şifrenizi yenilemek için bu bilgisayara ait lisans anahtarını girin.", 500, parent)
        l = QLabel("Lisans Anahtarı")
        l.setStyleSheet("font-weight:700; font-size:12px;")
        self.v.addWidget(l)
        self.anahtar = QPlainTextEdit()
        self.anahtar.setFixedHeight(70)
        self.v.addWidget(self.anahtar)
        self.s1 = self.alan("Yeni şifre", True)
        self.s2 = self.alan("Yeni şifre (tekrar)", True)
        self.hata = self.hata_etiketi()
        b = QPushButton("Şifreyi Yenile")
        b.setObjectName("anaBtn")
        b.clicked.connect(self._yenile)
        self.v.addWidget(b)

    def _yenile(self):
        giren = "".join(self.anahtar.toPlainText().split()).upper()
        kayitli = "".join((lisans.kayitli_anahtar() or "").split()).upper()
        if not giren or giren != kayitli:
            self.hata.setText("Lisans anahtarı bu kurulumdaki anahtarla eşleşmiyor.")
        elif len(self.s1.text()) < 4:
            self.hata.setText("Şifre en az 4 karakter olmalı.")
        elif self.s1.text() != self.s2.text():
            self.hata.setText("Şifreler aynı değil.")
        else:
            hesap.sifre_degistir(self.s1.text())
            bilgilendir(self, "Tamam", "Şifreniz yenilendi. Yeni şifrenizle giriş yapabilirsiniz.")
            self.accept()


# ------------------------------------------------------------------ akış
def giris_akisi() -> bool:
    """True: program açılabilir. False: kullanıcı vazgeçti / yetkisiz -> çık."""
    mesaj = ""
    try:
        lisans.kayitli_lisansi_dogrula()
    except lisans.LisansHatasi as e:
        mesaj = "" if "girilmemiş" in str(e) else str(e)
        if LisansDialog(mesaj).exec() != LisansDialog.DialogCode.Accepted:
            return False
        try:
            lisans.kayitli_lisansi_dogrula()
        except lisans.LisansHatasi:
            return False

    if not hesap.hesap_var_mi():
        return HesapOlusturDialog().exec() == HesapOlusturDialog.DialogCode.Accepted

    if hesap.hatirlaniyor_mu():
        return True  # otomatik giriş
    return GirisDialog().exec() == GirisDialog.DialogCode.Accepted
