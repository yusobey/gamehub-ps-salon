"""Ayarlar > Bildirim: süre dolunca bildirim + ses tercihleri."""
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QCheckBox,
    QLineEdit, QSpinBox, QFileDialog,
)

from core.theme import RENK
from core.bildirim import ayar_al, VARSAYILAN_AYARLAR, ses_dosyasi_kopyala
from ui.widgets import bilgilendir, uyar, SessizSpinBox


class BildirimAyarlariView(QWidget):
    def __init__(self, state, yonetici_getir, parent=None):
        super().__init__(parent)
        self.state = state
        self.yonetici_getir = yonetici_getir
        self._yukleniyor = True

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)
        baslik = QLabel("Ayarlar  ›  Bildirim")
        baslik.setObjectName("pageTitle")
        v.addWidget(baslik)
        alt = QLabel("Süreli masanın süresi dolunca uyarı verilir (uygulama arka planda olsa da).")
        alt.setObjectName("pageSubtitle")
        v.addWidget(alt)

        kutu = QFrame()
        kutu.setObjectName("masaKart")
        kutu.setMaximumWidth(720)
        kv = QVBoxLayout(kutu)
        kv.setContentsMargins(18, 16, 18, 16)
        kv.setSpacing(12)

        self.bildirim_cb = QCheckBox("Ekranın sağ altında bildirim göster")
        self.ses_cb = QCheckBox("Uyarı sesi çal")
        for cb in (self.bildirim_cb, self.ses_cb):
            cb.setStyleSheet("background:transparent;")
        kv.addWidget(self.bildirim_cb)
        kv.addWidget(self.ses_cb)

        # --- Ses dosyası ---
        kv.addWidget(self._etiket("Uyarı sesi"))
        ses_satir = QHBoxLayout()
        self.ses_lbl = QLabel()
        self.ses_lbl.setStyleSheet(f"color:{RENK['text_muted']}; background:transparent;")
        ses_satir.addWidget(self.ses_lbl, 1)
        sec_btn = QPushButton("Ses Dosyası Seç…")
        sec_btn.setObjectName("secenekBtn")
        sec_btn.clicked.connect(self._ses_sec)
        ses_satir.addWidget(sec_btn)
        varsayilan_btn = QPushButton("Varsayılana Dön")
        varsayilan_btn.setObjectName("ghostBtn")
        varsayilan_btn.clicked.connect(self._varsayilan_ses)
        ses_satir.addWidget(varsayilan_btn)
        kv.addLayout(ses_satir)
        ipucu = QLabel(".wav veya .mp3 seçebilirsiniz (uzun sesler de olur).")
        ipucu.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px; background:transparent;")
        kv.addWidget(ipucu)

        # --- Metin ---
        kv.addWidget(self._etiket("Bildirim başlığı"))
        self.baslik_input = QLineEdit()
        kv.addWidget(self.baslik_input)
        kv.addWidget(self._etiket("Bildirim mesajı"))
        self.mesaj_input = QLineEdit()
        kv.addWidget(self.mesaj_input)
        yer = QLabel("Yer tutucular:  {masa} = masa adı,  {birim} = birim adı")
        yer.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px; background:transparent;")
        kv.addWidget(yer)

        maks_satir = QHBoxLayout()
        maks_satir.addWidget(self._etiket("Ses en fazla"))
        self.maks_spin = SessizSpinBox()
        self.maks_spin.setRange(1, 120)
        self.maks_spin.setSuffix(" sn")
        self.maks_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.maks_spin.setFixedWidth(100)
        maks_satir.addWidget(self.maks_spin)
        maks_satir.addWidget(self._etiket("çalsın (uzun ses dosyaları için)"))
        maks_satir.addStretch()
        kv.addLayout(maks_satir)

        # --- Tekrar ---
        tekrar_satir = QHBoxLayout()
        self.tekrar_cb = QCheckBox("Masa kapatılana kadar tekrarla, her")
        self.tekrar_cb.setStyleSheet("background:transparent;")
        tekrar_satir.addWidget(self.tekrar_cb)
        self.tekrar_spin = SessizSpinBox()
        self.tekrar_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tekrar_spin.setRange(5, 600)
        self.tekrar_spin.setSuffix(" sn")
        self.tekrar_spin.setFixedWidth(100)
        tekrar_satir.addWidget(self.tekrar_spin)
        tekrar_satir.addStretch()
        kv.addLayout(tekrar_satir)

        # --- Dene ---
        self.dene_btn = QPushButton("🔔  Dene")
        self.dene_btn.setObjectName("primaryBtn")
        self.dene_btn.clicked.connect(self._dene)
        kv.addWidget(self.dene_btn, 0, Qt.AlignmentFlag.AlignLeft)

        v.addWidget(kutu)
        v.addStretch()

        self._yukle()
        for w in (self.bildirim_cb, self.ses_cb, self.tekrar_cb):
            w.toggled.connect(self._kaydet)
        self.baslik_input.textChanged.connect(self._kaydet)
        self.mesaj_input.textChanged.connect(self._kaydet)
        self.tekrar_spin.valueChanged.connect(self._kaydet)
        self.maks_spin.valueChanged.connect(self._kaydet)
        self._yukleniyor = False

    def _etiket(self, metin):
        l = QLabel(metin)
        l.setStyleSheet(f"font-weight:700; background:transparent; color:{RENK['text']};")
        return l

    def _yukle(self):
        a = ayar_al(self.state)
        self.bildirim_cb.setChecked(a["bildirim_acik"])
        self.ses_cb.setChecked(a["ses_acik"])
        self.baslik_input.setText(a["baslik"])
        self.mesaj_input.setText(a["mesaj"])
        self.tekrar_cb.setChecked(a["tekrar_acik"])
        self.tekrar_spin.setValue(int(a["tekrar_saniye"]))
        self.maks_spin.setValue(int(a["ses_max_saniye"]))
        self.tekrar_spin.setEnabled(a["tekrar_acik"])
        self._ses_etiketi(a)

    def _ses_etiketi(self, a=None):
        a = a or ayar_al(self.state)
        self.ses_lbl.setText(
            f"Seçili: {a['ses_dosyasi_gorunen']}" if a.get("ses_dosyasi") and a.get("ses_dosyasi_gorunen")
            else "Seçili: Varsayılan melodi"
        )

    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        a = dict(self.state.bildirim_ayarlari or {})
        a.update({
            "bildirim_acik": self.bildirim_cb.isChecked(),
            "ses_acik": self.ses_cb.isChecked(),
            "baslik": self.baslik_input.text(),
            "mesaj": self.mesaj_input.text(),
            "tekrar_acik": self.tekrar_cb.isChecked(),
            "tekrar_saniye": self.tekrar_spin.value(),
            "ses_max_saniye": self.maks_spin.value(),
        })
        self.state.bildirim_ayarlari = a
        self.tekrar_spin.setEnabled(self.tekrar_cb.isChecked())

    def _ses_sec(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Uyarı sesi seçin", "", "Ses dosyaları (*.wav *.mp3);;Tüm dosyalar (*)"
        )
        if not yol:
            return
        if not yol.lower().endswith((".wav", ".mp3")):
            uyar(self, "Desteklenmeyen dosya", "Lütfen .wav veya .mp3 bir dosya seçin.")
            return
        try:
            kayitli = ses_dosyasi_kopyala(yol)
        except Exception as e:
            uyar(self, "Hata", f"Ses dosyası kopyalanamadı:\n{e}")
            return
        a = dict(self.state.bildirim_ayarlari or {})
        a["ses_dosyasi"] = kayitli
        a["ses_dosyasi_gorunen"] = os.path.basename(yol)
        self.state.bildirim_ayarlari = a
        self._ses_etiketi()

    def _varsayilan_ses(self):
        a = dict(self.state.bildirim_ayarlari or {})
        a["ses_dosyasi"] = ""
        a.pop("ses_dosyasi_gorunen", None)
        self.state.bildirim_ayarlari = a
        self._ses_etiketi()
        y = self.yonetici_getir()
        if y is not None:
            y.sesi_durdur()

    def _dene(self):
        y = self.yonetici_getir()
        if y is None:
            return
        if y.calıyor_mu():
            y.sesi_durdur()
            self.dene_btn.setText("🔔  Dene")
            return
        y.dene()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1100, self._dene_butonunu_izle)  # ses bildirimden ~0.7 sn sonra başlar

    def _dene_butonunu_izle(self):
        y = self.yonetici_getir()
        if y is not None and y.calıyor_mu():
            self.dene_btn.setText("⏹  Durdur")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self._dene_butonunu_izle)
        else:
            self.dene_btn.setText("🔔  Dene")
