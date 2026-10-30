from datetime import datetime, timedelta
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QSize
from PyQt6.QtGui import QFont, QDrag

from core.models import Masa, MasaDurumu
from core.theme import durum_rengi, durum_zemin_rengi, RENK


def sure_str(saniye: float) -> str:
    saniye = int(max(0, saniye))
    h, kalan = divmod(saniye, 3600)
    m, s = divmod(kalan, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class _KisalanEtiket(QLabel):
    """Yeri yetmediğinde sonuna "…" koyarak KISALAN etiket (masa adı / konsol
    tipi için). Amaç: kartın üst satırında yer daraldığında SAĞDAKİ durum
    rozetinin ("ÖDEME BEKLENİYOR" gibi uzun bir yazının) KESİLMEMESİ - bunun
    yerine yazıya göre rozet kendi tam genişliğini alır, adın uzun kısmı
    kısalır. Yer bol olduğunda ad TAM görünür."""
    def __init__(self, metin="", parent=None):
        super().__init__(parent)
        self._tam_metin = metin
        self._kisalt()

    def setText(self, metin):
        self._tam_metin = metin
        self._kisalt()

    def sizeHint(self):
        h = super().sizeHint().height()
        return QSize(self.fontMetrics().horizontalAdvance(self._tam_metin) + 2, h)

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._kisalt()

    def _kisalt(self):
        w = self.width()
        if w <= 1:
            QLabel.setText(self, self._tam_metin)
            return
        kisa = self.fontMetrics().elidedText(self._tam_metin, Qt.TextElideMode.ElideRight, w)
        if kisa != self.text():
            QLabel.setText(self, kisa)


class MasaKarti(QFrame):
    """
    Tek bir masa kartı - DİKDÖRTGEN, duruma göre TÜM ZEMİN renklenir (AÇIK:
    yeşil-turkuaz parıltı, DURAKLATILDI: sarımsı-amber parıltı, BOŞ: nötr).
    Tutar sol altta, Detay sağ altta. Çift tıklama sinyali dışarıya (HomeView'e)
    verilir, hangi popup'ın açılacağına HomeView karar verir.
    """
    cift_tiklandi = pyqtSignal(int)   # masa.id
    detay_tiklandi = pyqtSignal(int)  # masa.id
    masa_uzerine_birakildi = pyqtSignal(int, int)  # kaynak masa.id, hedef masa.id (bu kart) - OTURUM taşıma
    pozisyon_degisti = pyqtSignal(int, int)        # kaynak masa.id, hedef masa.id - sadece YER değiştirme

    KART_GENISLIK = 228
    KART_YUKSEKLIK = 136

    def __init__(self, masa: Masa, duzenleme_modu: bool = False, parent=None):
        super().__init__(parent)
        self.masa = masa
        self.duzenleme_modu = duzenleme_modu
        self.setObjectName("masaKart")
        self.setFixedSize(self.KART_GENISLIK, self.KART_YUKSEKLIK)
        self.setAcceptDrops(True)
        self._surukle_baslangic: QPoint | None = None
        self._kur_arayuz()

    def _kur_arayuz(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(12, 9, 12, 8)
        ana.setSpacing(2)

        # --- Üst satır: ikon + isim/konsol (sol)  |  durum rozeti (sağ) ---
        ust = QHBoxLayout()
        ust.setSpacing(6)
        self.ikon_kutu = QLabel("🎮")
        self.ikon_kutu.setFixedSize(24, 24)
        self.ikon_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ust.addWidget(self.ikon_kutu)

        isim_v = QVBoxLayout()
        isim_v.setSpacing(0)
        self.ad_lbl = _KisalanEtiket(self.masa.ad)
        self.ad_lbl.setObjectName("masaAdi")
        self.ad_lbl.setStyleSheet("font-size:12px; font-weight:800;")
        isim_v.addWidget(self.ad_lbl)
        self.konsol_lbl = _KisalanEtiket(self.masa.konsol_tipi)
        self.konsol_lbl.setStyleSheet(f"font-size:9px; font-weight:600; color:{RENK['text_muted']};")
        isim_v.addWidget(self.konsol_lbl)
        ust.addLayout(isim_v, 1)

        self.durum_lbl = QLabel(self.masa.durum.value)
        self.durum_lbl.setObjectName("durumEtiket")
        self.durum_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Etiketin genişliği kendi içeriği kadar kalsın diye (tam satırı
        # kaplayan bir "bar" görünümüne dönüşmesin diye) sabit boyut vermiyoruz,
        # QHBoxLayout içinde doğal genişliğiyle sağa yaslanıyor.
        # Rozet HER ZAMAN kendi yazısının tam genişliğini alır (yazıya göre
        # boşluk) - yer daralırsa kısalan şey masa adıdır, rozet asla kesilmez.
        self.durum_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        ust.addWidget(self.durum_lbl)
        ana.addLayout(ust)

        # --- Orta: tarife/kol (küçük) + süre (büyük) + başlangıç saati (küçük) ---
        self.tarife_lbl = QLabel("")
        self.tarife_lbl.setObjectName("tarifeBilgi")
        self.tarife_lbl.setStyleSheet(f"font-size:9px; font-weight:600; color:{RENK['text_muted']};")
        ana.addWidget(self.tarife_lbl)

        orta = QVBoxLayout()
        orta.setSpacing(0)
        self.sure_lbl = QLabel("--:--:--")
        self.sure_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sure_lbl.setStyleSheet(f"font-size:17px; font-weight:800; color:{RENK['text']};")
        orta.addWidget(self.sure_lbl)
        self.baslama_lbl = QLabel("")
        self.baslama_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.baslama_lbl.setStyleSheet(f"font-size:9px; font-weight:600; color:{RENK['text_muted']};")
        orta.addWidget(self.baslama_lbl)
        ana.addLayout(orta)

        ana.addStretch()

        # --- Alt satır: tutar (SOL)  |  Detay (SAĞ) ---
        alt = QHBoxLayout()
        alt.setSpacing(6)
        self.tutar_lbl = QLabel("0 ₺")
        self.tutar_lbl.setObjectName("tutarBuyuk")
        self.tutar_lbl.setStyleSheet(f"font-size:17px; font-weight:800; color:{RENK['accent']};")
        alt.addWidget(self.tutar_lbl)
        alt.addStretch()
        self.detay_btn = QPushButton("Detay ›")
        self.detay_btn.setObjectName("ghostBtn")
        self.detay_btn.setStyleSheet("padding:3px 9px; font-size:10px; font-weight:700;")
        self.detay_btn.clicked.connect(lambda: self.detay_tiklandi.emit(self.masa.id))
        alt.addWidget(self.detay_btn)
        ana.addLayout(alt)

        self.guncelle()

    def mouseDoubleClickEvent(self, event):
        if self.duzenleme_modu:
            return  # düzenleme modunda çift tıklama masa açma/yönetme ekranını tetiklemesin
        self.cift_tiklandi.emit(self.masa.id)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        # Düzenleme modunda HER masa (boş dahil) sürüklenebilir - normal modda
        # ise sadece dolu masalar sürüklenebilir (oturum taşıma amacıyla).
        if event.button() == Qt.MouseButton.LeftButton and (self.duzenleme_modu or self.masa.durum != MasaDurumu.BOS):
            self._surukle_baslangic = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._surukle_baslangic is None:
            return
        if not self.duzenleme_modu and self.masa.durum == MasaDurumu.BOS:
            return
        if (event.position().toPoint() - self._surukle_baslangic).manhattanLength() < 14:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(self.masa.id))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._surukle_baslangic = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            kaynak_id = int(event.mimeData().text())
        except ValueError:
            return
        if kaynak_id != self.masa.id:
            if self.duzenleme_modu:
                self.pozisyon_degisti.emit(kaynak_id, self.masa.id)
            else:
                self.masa_uzerine_birakildi.emit(kaynak_id, self.masa.id)
        event.acceptProposedAction()

    def guncelle(self):
        """QTimer tarafından periyodik çağrılır - ekrandaki tüm anlık veriyi tazeler."""
        m = self.masa
        self.ad_lbl.setText(m.ad)
        self.konsol_lbl.setText(m.konsol_tipi)

        if self.duzenleme_modu:
            # Düzenleme modunda durum rengi yerine tek tip, dikkat çeken kesikli
            # çerçeve gösterilir - "şu an sürüklenebilir" hissi verir, tıpkı
            # telefonlarda ana ekran ikonlarını düzenlemek gibi.
            self.setStyleSheet(
                f"QFrame#masaKart {{ background-color:{RENK['panel_hover']}; "
                f"border:2px dashed {RENK['accent']}; border-radius:16px; }}"
            )
            self.durum_lbl.setText("⠿ Sürükle")
            self.durum_lbl.setStyleSheet(
                f"background-color: rgba(255,255,255,0.7); color:{RENK['accent']};"
                f"font-size:10px; font-weight:700; padding:2px 8px; border-radius:9px;"
            )
            self.durum_lbl.updateGeometry()
            self.ikon_kutu.setStyleSheet(
                f"background-color: rgba(255,255,255,0.7); border:1px dashed {RENK['accent']}; "
                f"border-radius:8px; font-size:15px;"
            )
            self.tarife_lbl.setText(m.gorunur_bolum())
            self.sure_lbl.setText("")
            self.baslama_lbl.setText("")
            self.tutar_lbl.setText("")
            self.detay_btn.setEnabled(False)
            return
        else:
            self.detay_btn.setEnabled(True)

        self.durum_lbl.setText(m.durum.value)
        renk = durum_rengi(m.durum.value)
        zemin = durum_zemin_rengi(m.durum.value)

        # Uzun durum yazıları (ÖDEME BEKLENİYOR / DURAKLATILDI) biraz daha
        # kompakt yazı+iç boşlukla çizilir ki masa adına da yer kalsın; kısa
        # olanlar (AÇIK / BOŞ) eski rahat ölçüsünde kalır. Yani boşluk YAZIYA
        # GÖRE ayarlanıyor, tek bir sabit ölçü yok.
        if len(m.durum.value) > 8:
            rozet_olcu = "font-size:9px; padding:3px 7px;"
        else:
            rozet_olcu = "font-size:10px; padding:3px 9px;"
        self.durum_lbl.setStyleSheet(
            f"background-color: rgba(255,255,255,0.6); color:{renk};"
            f"{rozet_olcu} font-weight:800; border-radius:9px;"
        )
        self.durum_lbl.updateGeometry()
        self.ikon_kutu.setStyleSheet(
            f"background-color: rgba(255,255,255,0.65); border:1px solid {renk}; border-radius:8px; font-size:15px;"
        )

        # Kart zemini TAMAMEN duruma göre renklenir: AÇIK = yeşil-turkuaz parıltı,
        # DURAKLATILDI = sarımsı-amber parıltı, ÖDEME BEKLİYOR = amber, BOŞ = nötr beyaz.
        if m.durum == MasaDurumu.BOS:
            self.setStyleSheet(
                f"QFrame#masaKart {{ background-color:{RENK['panel']}; "
                f"border:1px solid {RENK['border']}; border-radius:16px; }}"
            )
        else:
            self.setStyleSheet(
                f"QFrame#masaKart {{ background-color:{zemin}; "
                f"border:2px solid {renk}; border-radius:16px; }}"
            )

        if m.durum == MasaDurumu.BOS:
            self.tarife_lbl.setText("")
            self.sure_lbl.setText("Boş")
            self.baslama_lbl.setText("")
            self.tutar_lbl.setText("0 ₺")
            return

        aktif_seg = m.segments[-1] if m.segments else None
        self.tarife_lbl.setText(aktif_seg.tariff_name if aktif_seg else "")

        toplam_gecen = sum(s.elapsed_seconds() for s in m.segments) if m.segments else 0

        kalan = m.kalan_geri_sayim_saniye()
        if kalan is not None:
            self.sure_lbl.setText(sure_str(kalan))
        else:
            self.sure_lbl.setText(sure_str(toplam_gecen))

        # Masa açılınca hesaplanan sürenin (yukarıdaki sure_lbl) hemen altına/
        # yanına başlangıç saati otomatik yazılır.
        baslama = m.toplam_baslangic_zamani()
        self.baslama_lbl.setText(f"Başlangıç: {baslama.strftime('%H:%M')}" if baslama else "")

        self.tutar_lbl.setText(f"{m.genel_toplam()} ₺")
