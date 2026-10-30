# -*- coding: utf-8 -*-
"""
Kasa > Gün Sonu araçları: Para Sayma ve Hesap Makinesi.

Her ikisi de salonun verisine DOKUNMAZ - sadece gün sonunda kasayı elle
saymayı/hesaplamayı kolaylaştıran bağımsız küçük pencerelerdir.
"""
from decimal import Decimal, InvalidOperation, DivisionByZero

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from core.theme import RENK
from ui.widgets import OrtalanmisDialog, SessizSpinBox


# Bu pencereler Windows KARANLIK modda tamamen siyah açılıyordu (uygulama
# genelindeki QSS popup'lara her zaman ulaşmıyor - _GiderAvansDialog'da da
# aynı sebeple yerel stil var). Bu yüzden iki katmanlı güvence: (1) pencerenin
# KENDİ stil sayfası, (2) açık renkli QPalette + autoFillBackground.
_TEMA_QSS = f"""
QDialog {{ background-color:#FFFFFF; }}
QLabel {{ background:transparent; color:{RENK['text']}; }}
QFrame#baslikBant {{
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #6C4DF6, stop:1 #9B7BFF);
    border-radius:14px;
}}
QFrame#satirKart {{
    background-color:{RENK['panel_hover']}; border:1px solid {RENK['border']}; border-radius:12px;
}}
QFrame#toplamKart {{
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #E3FBF5, stop:1 #F4FFFB);
    border:1px solid #BDEFE2; border-radius:14px;
}}
QFrame#ekranKart {{
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {RENK['bg']}, stop:1 #FFFFFF);
    border:1px solid {RENK['border_strong']}; border-radius:14px;
}}
QSpinBox {{
    background-color:#FFFFFF; color:{RENK['text']}; border:1px solid {RENK['border_strong']};
    border-radius:8px; padding:6px 8px; font-size:15px; font-weight:800;
}}
QSpinBox {{ selection-background-color:{RENK['accent']}; selection-color:#FFFFFF; }}
QSpinBox:focus {{ border:1.5px solid {RENK['accent']}; }}
QPushButton#primaryBtn {{
    background-color:rgba(108,77,246,0.12); color:{RENK['accent']};
    border-width:1.5px; border-style:solid; border-color:{RENK['accent']};
    border-radius:10px; padding:10px 18px; font-weight:700;
}}
QPushButton#primaryBtn:hover {{ background-color:rgba(108,77,246,0.20); }}
QPushButton#ghostBtn {{
    background-color:{RENK['panel_hover']}; color:{RENK['text']}; border-radius:10px; padding:10px 18px;
    border-width:1px; border-style:solid; border-color:{RENK['border']}; font-weight:600;
}}
QPushButton#ghostBtn:hover {{ border-color:{RENK['accent']}; }}
QPushButton#tusRakam {{
    background-color:#FFFFFF; color:{RENK['text']}; border:1px solid {RENK['border_strong']};
    border-radius:12px; font-size:17px; font-weight:700;
}}
QPushButton#tusRakam:hover {{ background-color:#E4F3FC; border-color:#8FD1F2; }}
QPushButton#tusRakam:pressed {{ background-color:#CFE9F8; }}
QPushButton#tusIslem {{
    background-color:rgba(108,77,246,0.12); color:{RENK['accent']}; border:1.5px solid {RENK['accent']};
    border-radius:12px; font-size:19px; font-weight:800;
}}
QPushButton#tusIslem:hover {{ background-color:rgba(108,77,246,0.22); }}
QPushButton#tusIslem:pressed {{ background-color:rgba(108,77,246,0.32); }}
QPushButton#tusTemizle {{
    background-color:rgba(255,77,109,0.10); color:{RENK['danger']}; border:1.5px solid {RENK['danger']};
    border-radius:12px; font-size:16px; font-weight:800;
}}
QPushButton#tusTemizle:hover {{ background-color:rgba(255,77,109,0.20); }}
QPushButton#tusGeri {{
    background-color:{RENK['panel_hover']}; color:{RENK['text']}; border:1px solid {RENK['border_strong']};
    border-radius:12px; font-size:17px; font-weight:700;
}}
QPushButton#tusGeri:hover {{ border-color:{RENK['accent']}; }}
QPushButton#tusEsit {{
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0E8F63, stop:1 #17C98A);
    color:white; border:none; border-radius:12px; font-size:22px; font-weight:800;
}}
QPushButton#tusEsit:hover {{
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0B7752, stop:1 #14B87C);
}}
"""


def _rgba(hex_renk: str, alfa: float) -> str:
    """'#A855F7', 0.15 -> 'rgba(168,85,247,0.15)'. NOT: Qt stil sayfasında 8
    haneli '#RRGGBBAA' YOK, '#AARRGGBB' okunur - bu yüzden '{renk}22' yazımı
    rengi bozuyordu; saydam tonlar için hep rgba() kullanılmalı."""
    h = hex_renk.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alfa})"


def _acik_temayi_zorla(dialog):
    """Pencereyi (ve içindeki her şeyi) sistem karanlık modundan bağımsız,
    AÇIK/premium temaya sabitler."""
    dialog.setStyleSheet(_TEMA_QSS)
    palet = QPalette()
    palet.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
    palet.setColor(QPalette.ColorRole.WindowText, QColor(RENK["text"]))
    palet.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palet.setColor(QPalette.ColorRole.AlternateBase, QColor(RENK["panel_hover"]))
    palet.setColor(QPalette.ColorRole.Text, QColor(RENK["text"]))
    palet.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palet.setColor(QPalette.ColorRole.ButtonText, QColor(RENK["text"]))
    palet.setColor(QPalette.ColorRole.Highlight, QColor(RENK["accent"]))
    palet.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palet.setColor(QPalette.ColorRole.PlaceholderText, QColor("#B4B8C9"))
    dialog.setPalette(palet)
    dialog.setAutoFillBackground(True)
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class ParaSaymaDialog(OrtalanmisDialog):
    """Banknot adetlerini girince her satırın tutarını ve en altta genel
    toplamı otomatik hesaplar (200/100/50/20/10/5 ₺)."""
    BANKNOTLAR = [200, 100, 50, 20, 10, 5]
    # Gerçek TL banknot renklerine yakın rozet renkleri
    BANKNOT_RENK = {200: "#A855F7", 100: "#4F8CFF", 50: "#F5A623", 20: "#12B76A", 10: "#E5484D", 5: "#8D6E63"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Para Sayma")
        self.setMinimumWidth(380)
        _acik_temayi_zorla(self)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(12)

        bant = QFrame()
        bant.setObjectName("baslikBant")
        bv = QVBoxLayout(bant)
        bv.setContentsMargins(18, 14, 18, 14)
        bv.setSpacing(2)
        baslik = QLabel("💵  Para Sayma")
        baslik.setStyleSheet("font-size:18px; font-weight:800; color:#FFFFFF;")
        bv.addWidget(baslik)
        aciklama = QLabel("Banknotun yanına adedini yazın, tutar ve toplam otomatik hesaplanır.")
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("font-size:11px; font-weight:600; color:rgba(255,255,255,0.88);")
        bv.addWidget(aciklama)
        v.addWidget(bant)

        self.spinler: dict[int, SessizSpinBox] = {}
        self.tutar_lbl: dict[int, QLabel] = {}
        liste = QVBoxLayout()
        liste.setSpacing(8)
        for deger in self.BANKNOTLAR:
            renk = self.BANKNOT_RENK[deger]
            kart = QFrame()
            kart.setObjectName("satirKart")
            h = QHBoxLayout(kart)
            h.setContentsMargins(12, 8, 14, 8)
            h.setSpacing(12)

            rozet = QLabel(f"{deger} ₺")
            rozet.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rozet.setFixedWidth(78)
            rozet.setStyleSheet(
                f"background-color:{_rgba(renk, 0.14)}; color:{renk}; border:1px solid {_rgba(renk, 0.45)}; "
                f"border-radius:8px; font-size:15px; font-weight:800; padding:5px 0;"
            )
            h.addWidget(rozet)

            carpi = QLabel("×")
            carpi.setStyleSheet(f"font-size:14px; font-weight:700; color:{RENK['text_muted']};")
            h.addWidget(carpi)

            spin = SessizSpinBox()
            spin.setRange(0, 99999)
            spin.setFixedWidth(96)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.lineEdit().setPlaceholderText("0")
            spin.valueChanged.connect(self._hesapla)
            # Enter'a basınca bir sonraki banknota geç - hızlı sayım için.
            spin.lineEdit().returnPressed.connect(spin.focusNextChild)
            h.addWidget(spin)
            self.spinler[deger] = spin

            h.addStretch()
            tutar = QLabel("0 ₺")
            tutar.setMinimumWidth(92)
            tutar.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            tutar.setStyleSheet(f"font-size:15px; font-weight:700; color:{RENK['text_muted']};")
            h.addWidget(tutar)
            self.tutar_lbl[deger] = tutar
            liste.addWidget(kart)
        v.addLayout(liste)

        toplam_kart = QFrame()
        toplam_kart.setObjectName("toplamKart")
        th = QHBoxLayout(toplam_kart)
        th.setContentsMargins(18, 12, 18, 12)
        toplam_etiket = QLabel("TOPLAM")
        toplam_etiket.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['text_muted']}; letter-spacing:2px;")
        th.addWidget(toplam_etiket)
        th.addStretch()
        self.toplam_lbl = QLabel("0 ₺")
        self.toplam_lbl.setStyleSheet(f"font-size:28px; font-weight:800; color:#0E9F78;")
        th.addWidget(self.toplam_lbl)
        v.addWidget(toplam_kart)

        butonlar = QHBoxLayout()
        butonlar.setSpacing(10)
        temizle_btn = QPushButton("Temizle")
        temizle_btn.setObjectName("ghostBtn")
        temizle_btn.setAutoDefault(False)
        temizle_btn.clicked.connect(self._temizle)
        butonlar.addWidget(temizle_btn)
        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("primaryBtn")
        kapat_btn.setAutoDefault(False)
        kapat_btn.clicked.connect(self.accept)
        butonlar.addWidget(kapat_btn)
        v.addLayout(butonlar)

    def toplam(self) -> int:
        return sum(deger * spin.value() for deger, spin in self.spinler.items())

    def _hesapla(self):
        for deger, spin in self.spinler.items():
            satir_tutari = deger * spin.value()
            self.tutar_lbl[deger].setText(f"{satir_tutari:,} ₺".replace(",", "."))
            renk = RENK["text"] if satir_tutari > 0 else RENK["text_muted"]
            self.tutar_lbl[deger].setStyleSheet(f"font-size:15px; font-weight:700; color:{renk};")
        self.toplam_lbl.setText(f"{self.toplam():,} ₺".replace(",", "."))

    def _temizle(self):
        for spin in self.spinler.values():
            spin.setValue(0)


class HesapMakinesiDialog(OrtalanmisDialog):
    """Basit dört işlem hesap makinesi - fare VEYA klavye ile (rakamlar,
    + - * /, Enter/=, Backspace, C). Hesaplama Decimal ile yapılır; böylece
    0,1 + 0,2 gibi işlemler 0,30000000000000004 çıkmaz."""
    ISLEMLER = {"+": "+", "-": "−", "*": "×", "/": "÷"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hesap Makinesi")
        self.setFixedWidth(312)
        _acik_temayi_zorla(self)
        self._sifirla()

        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        ekran = QFrame()
        ekran.setObjectName("ekranKart")
        ev = QVBoxLayout(ekran)
        ev.setContentsMargins(16, 10, 16, 10)
        ev.setSpacing(0)
        self.ifade_lbl = QLabel("")
        self.ifade_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.ifade_lbl.setFixedHeight(20)
        self.ifade_lbl.setStyleSheet(f"font-size:12px; font-weight:600; color:{RENK['text_muted']};")
        ev.addWidget(self.ifade_lbl)
        self.ekran_lbl = QLabel("0")
        self.ekran_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.ekran_lbl.setFixedHeight(46)
        self.ekran_lbl.setStyleSheet(f"font-size:32px; font-weight:800; color:{RENK['text']};")
        ev.addWidget(self.ekran_lbl)
        v.addWidget(ekran)

        izgara = QGridLayout()
        izgara.setSpacing(8)
        R, I = "tusRakam", "tusIslem"
        duzen = [
            [("C", "tusTemizle", self.temizle), ("⌫", "tusGeri", self.geri), ("÷", I, lambda: self.islem_sec("/")), ("×", I, lambda: self.islem_sec("*"))],
            [("7", R, lambda: self.rakam("7")), ("8", R, lambda: self.rakam("8")), ("9", R, lambda: self.rakam("9")), ("−", I, lambda: self.islem_sec("-"))],
            [("4", R, lambda: self.rakam("4")), ("5", R, lambda: self.rakam("5")), ("6", R, lambda: self.rakam("6")), ("+", I, lambda: self.islem_sec("+"))],
            [("1", R, lambda: self.rakam("1")), ("2", R, lambda: self.rakam("2")), ("3", R, lambda: self.rakam("3")), ("=", "tusEsit", self.esittir)],
            [("0", R, lambda: self.rakam("0")), (",", R, self.virgul)],
        ]
        for r, satir in enumerate(duzen):
            for c, (metin, nesne_adi, islev) in enumerate(satir):
                b = QPushButton(metin)
                b.setObjectName(nesne_adi)
                if metin == "=":
                    b.setMinimumHeight(50)
                    b.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
                else:
                    b.setFixedHeight(50)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # klavye hep pencerede kalsın
                b.setAutoDefault(False)
                b.clicked.connect(lambda checked=False, f=islev: f())
                # Son iki satırda: "0" iki sütun geniş, "," yanında, "=" ise
                # sağ sütunda İKİ SATIR yüksekliğinde (klasik hesap makinesi düzeni)
                if metin == "0":
                    izgara.addWidget(b, r, c, 1, 2)
                elif metin == ",":
                    izgara.addWidget(b, r, c + 1, 1, 1)
                elif metin == "=":
                    izgara.addWidget(b, r, c, 2, 1)
                else:
                    izgara.addWidget(b, r, c)
        v.addLayout(izgara)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("ghostBtn")
        kapat_btn.setAutoDefault(False)
        kapat_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        kapat_btn.clicked.connect(self.accept)
        v.addWidget(kapat_btn)
        self._goster()

    # ---- durum ----
    def _sifirla(self):
        self.giris = "0"              # şu an yazılan sayı (metin)
        self.birikim: Decimal | None = None
        self.islem: str | None = None
        self.yeni_giris = True        # sıradaki rakam girişi ekranı sıfırdan başlatsın mı
        self.hata = False
        self.ifade = ""

    @staticmethod
    def _bicim(d: Decimal) -> str:
        d = d.normalize() if d != 0 else Decimal(0)
        metin = format(d, "f")
        if "." in metin:
            tam, ondalik = metin.split(".")
            ondalik = ondalik[:10]
            metin = tam + ("," + ondalik if ondalik else "")
        return metin

    def _deger(self) -> Decimal:
        try:
            return Decimal(self.giris.replace(",", "."))
        except InvalidOperation:
            return Decimal(0)

    def _goster(self):
        self.ekran_lbl.setText("Hata" if self.hata else self.giris.replace(".", ","))
        self.ifade_lbl.setText(self.ifade)

    # ---- işlemler ----
    def rakam(self, d: str):
        if self.hata:
            self._sifirla()
        if self.yeni_giris:
            self.giris = d
            self.yeni_giris = False
        elif len(self.giris.replace(",", "").replace("-", "")) < 15:
            self.giris = d if self.giris == "0" else self.giris + d
        self._goster()

    def virgul(self):
        if self.hata:
            self._sifirla()
        if self.yeni_giris:
            self.giris = "0,"
            self.yeni_giris = False
        elif "," not in self.giris:
            self.giris += ","
        self._goster()

    def geri(self):
        if self.hata:
            self._sifirla()
        elif not self.yeni_giris:
            self.giris = self.giris[:-1] or "0"
            if self.giris in ("", "-"):
                self.giris = "0"
        self._goster()

    def temizle(self):
        self._sifirla()
        self._goster()

    def _uygula(self, a: Decimal, op: str, b: Decimal) -> Decimal:
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if b == 0:
            raise DivisionByZero
        return a / b

    def islem_sec(self, op: str):
        if self.hata:
            self._sifirla()
        # Üst üste işlem seçilirse (5 + × gibi) sadece işlemi değiştir.
        if self.islem is not None and self.yeni_giris:
            self.islem = op
            self.ifade = f"{self._bicim(self.birikim)} {self.ISLEMLER[op]}"
            self._goster()
            return
        if self.islem is not None and self.birikim is not None:
            try:
                self.birikim = self._uygula(self.birikim, self.islem, self._deger())
            except (DivisionByZero, InvalidOperation):
                self._hata_ver()
                return
        else:
            self.birikim = self._deger()
        self.islem = op
        self.ifade = f"{self._bicim(self.birikim)} {self.ISLEMLER[op]}"
        self.giris = self._bicim(self.birikim)
        self.yeni_giris = True
        self._goster()

    def esittir(self):
        if self.hata or self.islem is None or self.birikim is None:
            return
        b = self._deger()
        ifade = f"{self._bicim(self.birikim)} {self.ISLEMLER[self.islem]} {self._bicim(b)} ="
        try:
            sonuc = self._uygula(self.birikim, self.islem, b)
        except (DivisionByZero, InvalidOperation):
            self._hata_ver()
            return
        self.giris = self._bicim(sonuc)
        self.birikim = None
        self.islem = None
        self.yeni_giris = True
        self.ifade = ifade
        self._goster()

    def _hata_ver(self):
        self._sifirla()
        self.hata = True
        self._goster()

    def keyPressEvent(self, event):
        k = event.key()
        t = event.text()
        if t and t in "0123456789":
            self.rakam(t)
        elif t in (",", "."):
            self.virgul()
        elif t in ("+", "-", "*", "/"):
            self.islem_sec(t)
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter) or t == "=":
            self.esittir()
        elif k == Qt.Key.Key_Backspace:
            self.geri()
        elif t in ("c", "C") or k == Qt.Key.Key_Delete:
            self.temizle()
        else:
            super().keyPressEvent(event)
