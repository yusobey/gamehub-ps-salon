from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QScrollArea, QLineEdit, QMessageBox, QComboBox, QDialog,
    QDoubleSpinBox, QStackedWidget, QCheckBox, QAbstractButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QDate, QSize
from PyQt6.QtGui import QPalette, QColor
from datetime import datetime, date, timedelta

from core.models import AppState, Masa, MasaDurumu, Borc, KasaIslemi, Gider, Avans, Not, is_gunu, next_id, round_up_5
from core.pricing import round_up_5 as rd5, para_ustunu_dagitimdan_dus
from core.theme import RENK, durum_rengi, durum_zemin_rengi, kaynak_yolu
from core.kayit import gorseli_kalici_klasore_kopyala
from ui.table_card import MasaKarti
from ui.kasa_araclari import ParaSaymaDialog, HesapMakinesiDialog
from ui.dialogs import MasaAcDialog, MasaIslemDialog, OdemeAlDialog, MasaDetayDialog, AlisverisDialog
from ui.widgets import SessizDoubleSpinBox, SessizSpinBox, soru_sor, uyar, bilgilendir, OrtalanmisDialog, TamamlamaKutusu, SessizComboBox, SessizDateEdit, cop_kutusu_ikonu, cop_butonu_yap, metin_sor


SEKMELER = [
    ("kasa", "💰", "Kasa"),
    ("borclar", "📒", "Borçlar"),
    ("son_islemler", "🧾", "Son İşlemler"),
    ("urunler", "🛒", "Ürünler"),
    ("notlar", "📝", "Notlar"),
]

# Ayarlar altında açılan alt sekmeler - siz yenilerini söyledikçe buraya eklenecek.
AYARLAR_ALT_SEKMELER = [
    ("salon_adi", "🏷️", "Salon Adı"),
    ("bildirim", "🔔", "Bildirim"),
    ("veri", "💾", "Veri ve\nGüncelleme"),
    ("masa_kayitlari", "🖥️", "Masa ve Tarife\nKayıtları"),
]


class Sidebar(QFrame):
    sekme_secildi = pyqtSignal(str)
    yardim_istendi = pyqtSignal()
    cikis_istendi = pyqtSignal()

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self.butonlar = {}
        self._ayarlar_acik = False
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 20, 14, 20)
        v.setSpacing(4)

        marka_row = QHBoxLayout()
        marka_row.setSpacing(8)
        logo_kutu = QLabel("🐐")
        logo_kutu.setFixedSize(38, 38)
        logo_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _logo_yolu = kaynak_yolu("logo_kafa.png")
        if _logo_yolu:
            from PyQt6.QtGui import QPixmap
            _pm = QPixmap(_logo_yolu).scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
            logo_kutu.setPixmap(_pm)
            logo_kutu.setStyleSheet("background:transparent;")
        else:
            logo_kutu.setStyleSheet(
                f"background-color:{RENK['accent']}; border-radius:10px; font-size:18px;"
            )
        marka_row.addWidget(logo_kutu)
        marka_v = QVBoxLayout()
        marka_v.setSpacing(0)
        marka_baslik = QLabel()
        marka_baslik.setObjectName("brandTitle")
        marka_baslik.setTextFormat(Qt.TextFormat.RichText)
        marka_baslik.setText(
            f"<span style='color:{RENK['accent']};'>GAME</span>"
            f"<span style='color:{RENK['accent2']};'>HUB</span>"
        )
        marka_v.addWidget(marka_baslik)
        marka_alt = QLabel("Lounge Management System")
        marka_alt.setObjectName("brandSubtitle")
        marka_alt.setWordWrap(True)
        marka_v.addWidget(marka_alt)
        marka_row.addLayout(marka_v, 1)
        marka_widget = QFrame()
        marka_widget.setLayout(marka_row)
        marka_widget.setMinimumHeight(54)
        marka_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        marka_widget.setToolTip("Yardım")
        marka_widget.mousePressEvent = lambda event: self.yardim_istendi.emit()
        v.addWidget(marka_widget)
        v.addSpacing(18)

        # --- Birimler (gruplar): her biri kendi ayrı sayfasında (kendi masa
        # ızgarası+durum özeti) gösterilir - PlayStation, Bilardo, VR gibi
        # farklı birimler tek kalabalık sayfada karışmasın diye. Bu bölüm
        # DİNAMİKTİR - grup eklenince/silinince gruplari_kur() ile yeniden
        # kurulur. ---
        self.gruplar_container = QWidget()
        self.gruplar_v = QVBoxLayout(self.gruplar_container)
        self.gruplar_v.setContentsMargins(0, 0, 0, 0)
        self.gruplar_v.setSpacing(4)
        v.addWidget(self.gruplar_container)
        self.gruplari_kur()

        for key, icon, ad in SEKMELER:
            btn = QPushButton(f"{icon}   {ad}")
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._sec(k))
            v.addWidget(btn)
            self.butonlar[key] = btn

        # --- Ayarlar: tıklanınca sayfaya gitmez, sadece altını açar/kapatır ---
        self.ayarlar_btn = QPushButton("⚙️   Ayarlar" + "  ▸")
        self.ayarlar_btn.setObjectName("sidebarBtn")
        self.ayarlar_btn.setCheckable(True)
        self.ayarlar_btn.clicked.connect(self._ayarlar_toggle)
        v.addWidget(self.ayarlar_btn)

        self.ayarlar_alt_container = QWidget()
        alt_v = QVBoxLayout(self.ayarlar_alt_container)
        alt_v.setContentsMargins(18, 2, 0, 2)
        alt_v.setSpacing(2)
        for key, icon, ad in AYARLAR_ALT_SEKMELER:
            btn = QPushButton(f"{icon}  {ad}")
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.setStyleSheet("font-size:12px;")
            btn.clicked.connect(lambda checked, k=key: self._sec(k))
            alt_v.addWidget(btn)
            self.butonlar[key] = btn
        self.ayarlar_alt_container.setVisible(False)
        v.addWidget(self.ayarlar_alt_container)

        v.addStretch()

        # --- Sol alt: lisans/giriş bilgisi için yer tutucu alan - lisanslama
        # eklenince burada ilgili kişinin (kullanıcı adı/işletme) giriş bilgisi
        # gösterilecek. Şimdilik salon adını gösteriyor. ---
        self.giris_kutu = QFrame()
        self.giris_kutu.setStyleSheet(
            f"background:transparent; border-top:1px solid {RENK['border']};"
        )
        giris_v = QVBoxLayout(self.giris_kutu)
        giris_v.setContentsMargins(18, 10, 18, 10)
        giris_v.setSpacing(1)
        from core import hesap as _hesap
        giris_ikon_lbl = QLabel(f"👤  {_hesap.kullanici_adi() or 'Yerel Oturum'}")
        giris_ikon_lbl.setStyleSheet(f"font-size:10px; font-weight:700; color:{RENK['text_muted']}; background:transparent;")
        giris_v.addWidget(giris_ikon_lbl)
        self.giris_ad_lbl = QLabel("Salonum")
        self.giris_ad_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['text']}; background:transparent;")
        giris_v.addWidget(self.giris_ad_lbl)
        cikis_btn = QPushButton("Oturumu Kapat")
        cikis_btn.setObjectName("linkBtn")
        cikis_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cikis_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{RENK['accent']}; "
            f"font-size:11px; font-weight:700; text-align:left; padding:3px 0 0 0; }}"
            f"QPushButton:hover {{ text-decoration:underline; }}"
        )
        cikis_btn.clicked.connect(lambda: self.cikis_istendi.emit())
        giris_v.addWidget(cikis_btn)
        v.addWidget(self.giris_kutu)
        # Başlangıç seçimi arti_btnk main.py tarafından yapılır (hangi birim/grup
        # sayfasının varsayılan gösterileceğine main.py karar verir).

    def gruplari_kur(self):
        """state.gruplar'a göre birim (grup) butonlarını sıfırdan kurar - her
        grup KENDİ AYRI sayfasına gider (PlayStation, Bilardo, VR gibi farklı
        birimler tek kalabalık sayfada karışmasın diye). Grup eklenince/
        silinince/yeniden adlandırılınca main.py bunu tekrar çağırır."""
        # Eski grup butonlarının arti_btnk geçersiz (silinmiş widget'a işaret
        # eden) referanslarını da butonlar sözlüğünden temizliyoruz.
        for k in [k for k in self.butonlar if k.startswith("grup:")]:
            del self.butonlar[k]
        while self.gruplar_v.count():
            item = self.gruplar_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        for grup in self.state.gruplar:
            key = f"grup:{grup}"
            btn = QPushButton(f"🎮   {grup}")
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._sec(k))
            self.gruplar_v.addWidget(btn)
            self.butonlar[key] = btn

    def _ayarlar_toggle(self):
        self._ayarlar_acik = not self._ayarlar_acik
        self.ayarlar_alt_container.setVisible(self._ayarlar_acik)
        self.ayarlar_btn.setText("⚙️   Ayarlar" + ("  ▾" if self._ayarlar_acik else "  ▸"))
        # Ayarlar'ın kendisi bir sayfa değil - sadece açılıp kapanır, checked
        # durumunu (tıklanabilir görünmesin diye) hemen geri bırakıyoruz.
        self.ayarlar_btn.setChecked(False)

    def giris_bilgisini_guncelle(self, metin: str):
        """Lisanslama eklenince gerçek kullanıcı/işletme bilgisiyle
        değiştirilecek - şimdilik salon adını gösteriyor."""
        self.giris_ad_lbl.setText(metin)

    def _sec(self, key):
        for k, b in self.butonlar.items():
            aktif = (k == key)
            b.setChecked(aktif)
            b.setObjectName("sidebarBtnActive" if aktif else "sidebarBtn")
            # objectName degistirmek tek basina Qt'nin QSS'i yeniden uygulamasini
            # SAGLAMAZ - unpolish/polish cagirmadan eski stil (orn. hep "Anasayfa"
            # secili gorunmesi) yapisik kalir. Bu satirlar o hatayi giderir.
            b.style().unpolish(b)
            b.style().polish(b)
        # Tıklanan bir Ayarlar alt sekmesiyse, Ayarlar menüsü açık kalsın
        alt_sekme_anahtarlari = {k for k, _, _ in AYARLAR_ALT_SEKMELER}
        if key in alt_sekme_anahtarlari and not self._ayarlar_acik:
            self._ayarlar_acik = True
            self.ayarlar_alt_container.setVisible(True)
            self.ayarlar_btn.setText("⚙️   Ayarlar  ▾")
        self.sekme_secildi.emit(key)


class StatCard(QFrame):
    """Üst özet kartları: küçük ikon + büyük sayı + etiket."""
    def __init__(self, ikon: str, renk: str, baslik: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(4)

        ust = QHBoxLayout()
        ikon_kutu = QLabel(ikon)
        ikon_kutu.setFixedSize(20, 20)
        ikon_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ikon_kutu.setStyleSheet(f"background-color:{_hex_rgba(renk, 0.14)}; border-radius:6px; font-size:10px;")
        ust.addWidget(ikon_kutu)
        ust.addStretch()
        v.addLayout(ust)

        baslik_lbl = QLabel(baslik)
        baslik_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:10px; font-weight:600; background:transparent;")
        v.addWidget(baslik_lbl)

        self.deger_lbl = QLabel("0")
        self.deger_lbl.setStyleSheet(f"font-size:19px; font-weight:800; color:{RENK['text']}; background:transparent;")
        v.addWidget(self.deger_lbl)

    def deger_ayarla(self, deger: str):
        self.deger_lbl.setText(deger)


class AlisverisKarti(QFrame):
    """Anasayfa üst satırda, stat kartlarının yanında duran tıklanabilir kart -
    masa açmadan direkt ürün satışı yapmak için (örn. sadece içecek alan müşteri)."""
    tiklandi = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(4)

        ust = QHBoxLayout()
        ikon_kutu = QLabel("🛒")
        ikon_kutu.setFixedSize(20, 20)
        ikon_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ikon_kutu.setStyleSheet(f"background-color:{_hex_rgba(RENK['accent'], 0.14)}; border-radius:6px; font-size:10px;")
        ust.addWidget(ikon_kutu)
        ust.addStretch()
        v.addLayout(ust)

        baslik_lbl = QLabel("Alışveriş")
        baslik_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:10px; font-weight:600; background:transparent;")
        v.addWidget(baslik_lbl)

        alt_lbl = QLabel("Masasız Satış")
        alt_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['accent']}; background:transparent;")
        v.addWidget(alt_lbl)
        self.alt_lbl = alt_lbl

    def sepeti_guncelle(self, sepet: dict):
        """Kalıcı masasız satış sepetinde bekleyen bir tutar varsa (müşteri
        ürünü seçip henüz ödemediyse) burada gösterilir - böylece dialog
        kapalıyken bile ne kadar sepette olduğu Anasayfa'dan görülebilir."""
        toplam = sum(v["adet"] * v["birim_fiyat"] for v in sepet.values())
        if toplam > 0:
            self.alt_lbl.setText(f"{toplam:.0f} ₺ sepette")
        else:
            self.alt_lbl.setText("Masasız Satış")

    def mousePressEvent(self, event):
        self.tiklandi.emit()
        super().mousePressEvent(event)


class HomeView(QWidget):
    """Bir BİRİM'in (grup - örn. 'PS4/5 STANDART', 'BİLARDO', 'VR') kendi
    özel sayfası: hoş geldin başlığı, o birime ait durum özetleri ve SADECE
    o birimin masa kartları. Her birim kendi ayrı sayfasında gösterilir -
    PlayStation, Bilardo, VR gibi farklı birimler tek kalabalık sayfada
    karışmasın diye. Ciro/kasa ise TÜM birimlerde ORTAK kalır (ayrılmaz)."""

    def __init__(self, state: AppState, grup_filtresi: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.grup_filtresi = grup_filtresi
        self.kartlar: dict[int, MasaKarti] = {}
        self.duzenleme_modu: bool = False

        dis = QVBoxLayout(self)
        dis.setContentsMargins(22, 16, 22, 14)
        dis.setSpacing(4)

        self.baslik_lbl = QLabel()
        self.baslik_lbl.setObjectName("pageTitle")
        self.baslik_lbl.hide()  # birim adı zaten aşağıdaki "… Masaları" başlığında var
        dis.addWidget(self.baslik_lbl)
        self.alt_baslik = QLabel()
        self.alt_baslik.setStyleSheet(
            f"font-size:26px; font-weight:800; color:{RENK['accent']}; background:transparent; letter-spacing:0.5px;"
        )
        dis.addWidget(self.alt_baslik)
        dis.addSpacing(10)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(10)
        self.stat_acik = StatCard("🎮", RENK["accent2"], "AÇIK MASA")
        self.stat_bos = StatCard("⭕", RENK["text_muted"], "BOŞ MASA")
        self.stat_kilitli = StatCard("🔒", RENK["danger"], "KİLİTLİ MASA")
        self.stat_odeme_bekleyen = StatCard("⏳", RENK["warning"], "ÖDEME BEKLEYEN")
        self.alisveris_karti = AlisverisKarti()
        self.alisveris_karti.tiklandi.connect(self._alisveris_ac)
        for sc in [self.stat_acik, self.stat_bos, self.stat_kilitli, self.stat_odeme_bekleyen, self.alisveris_karti]:
            stat_row.addWidget(sc)
        dis.addLayout(stat_row)
        dis.addSpacing(10)

        masalar_baslik_satir = QHBoxLayout()
        self.masalar_baslik = QLabel()
        self.masalar_baslik.setStyleSheet(f"font-size:15px; font-weight:700; color:{RENK['text']};")
        masalar_baslik_satir.addWidget(self.masalar_baslik)
        masalar_baslik_satir.addStretch()
        self.duzen_btn = QPushButton("✏️ Düzeni Değiştir")
        self.duzen_btn.setObjectName("ghostBtn")
        self.duzen_btn.clicked.connect(self._duzenleme_modunu_degistir)
        masalar_baslik_satir.addWidget(self.duzen_btn)
        dis.addLayout(masalar_baslik_satir)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background:transparent;")
        ic = QWidget()
        ic.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(ic)
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(ic)
        dis.addWidget(scroll)

        self._baslik_guncelle()
        self._kartlari_olustur()
        self.alisveris_karti.sepeti_guncelle(self.state.masasiz_sepet)

    def _baslik_guncelle(self):
        self.baslik_lbl.setText(f"🎮  {self.grup_filtresi}")
        self.alt_baslik.setText(self.state.salon_adi)
        self.masalar_baslik.setText(f"🎮  {self.grup_filtresi} Masaları")

    def _bu_birimin_masalari(self):
        return [m for m in self.state.masalar if m.gorunur_bolum() == self.grup_filtresi]

    def _stat_kartlarini_guncelle(self):
        masalar = self._bu_birimin_masalari()
        acik = sum(1 for m in masalar if m.durum == MasaDurumu.ACIK)
        bos = sum(1 for m in masalar if m.durum == MasaDurumu.BOS)
        kilitli = sum(1 for m in masalar if m.durum == MasaDurumu.DURAKLATILDI)
        odeme_bekleyen = sum(1 for m in masalar if m.durum == MasaDurumu.ODEME_BEKLIYOR)
        self.stat_acik.deger_ayarla(str(acik))
        self.stat_bos.deger_ayarla(str(bos))
        self.stat_kilitli.deger_ayarla(str(kilitli))
        self.stat_odeme_bekleyen.deger_ayarla(str(odeme_bekleyen))

    def _hesapla_sutun(self) -> int:
        """Bir grup panelinin içinde, mevcut pencere genişliğine kaç masa karti_btnnın
        yan yana sığacağını hesaplar - pencere büyüyüp küçülünce otomatik uyum sağlar."""
        kart_birim = MasaKarti.KART_GENISLIK + self.grid.spacing()
        panel_ici_bosluk = 24 + 24  # panelin sol+sağ iç boşluğu
        kullanilabilir = max(self.width() - 56 - panel_ici_bosluk, kart_birim)
        return max(1, kullanilabilir // kart_birim)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        yeni_deger = self._hesapla_sutun()
        if yeni_deger != getattr(self, "_mevcut_sutun", None):
            self._mevcut_sutun = yeni_deger
            self._kartlari_olustur()

    def _kartlari_olustur(self):
        """Bu sayfa TEK bir birime (gruba) ait - ama o birim İÇİNDE, masalar
        KATEGORİYE (konsol_tipi - örn. 'DEV EKRAN', 'PLAYSTATION 4', 'PLAYSTATION 5')
        göre kendi ayrı panellerinde gösterilir. Yani PLAYSTATİON biriminde
        DEV EKRAN paneli, PLAYSTATION 4 paneli, PLAYSTATION 5 paneli alt alta
        durur - panelin İÇİNDEKİ masalar pencere genişliğine göre yan yana dizilir."""
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        self.kartlar.clear()

        masalar = [m for m in self.state.siralanmis_masalar() if m.gorunur_bolum() == self.grup_filtresi]

        if not masalar:
            bos_lbl = QLabel("Bu birimde henüz masa yok - Ayarlar > Masa ve Tarife Kayıtları'ndan ekleyebilirsin.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
            self.grid.addWidget(bos_lbl, 0, 0)
            return

        # Masaları KATEGORİYE (konsol_tipi) göre ayırıyoruz - kategori
        # boşsa (eski/basit kurulumlar) birim adının kendisini kullanıyoruz.
        kategorili: dict[str, list] = {}
        for masa in masalar:
            kategorili.setdefault(masa.konsol_tipi or self.grup_filtresi, []).append(masa)

        SUTUN = self._hesapla_sutun()
        self._mevcut_sutun = SUTUN

        for i, (kategori_adi, kat_masalar) in enumerate(kategorili.items()):
            panel = QFrame()
            panel.setObjectName("masaKart")
            pv = QVBoxLayout(panel)
            pv.setContentsMargins(14, 9, 14, 10)
            pv.setSpacing(6)

            baslik_lbl = QLabel(f"{kategori_adi}  ({len(kat_masalar)})")
            baslik_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text_muted']};")
            pv.addWidget(baslik_lbl)

            ic_grid_widget = QWidget()
            ic_grid = QGridLayout(ic_grid_widget)
            ic_grid.setSpacing(10)
            ic_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            for j, masa in enumerate(kat_masalar):
                kart = MasaKarti(masa, duzenleme_modu=self.duzenleme_modu)
                kart.cift_tiklandi.connect(self._masaya_cift_tiklandi)
                kart.detay_tiklandi.connect(self._detay_ac)
                kart.masa_uzerine_birakildi.connect(self._masa_tasindi)
                kart.pozisyon_degisti.connect(self._masa_pozisyonu_degistir)
                ic_grid.addWidget(kart, j // SUTUN, j % SUTUN)
                self.kartlar[masa.id] = kart
            pv.addWidget(ic_grid_widget)

            self.grid.addWidget(panel, i, 0, Qt.AlignmentFlag.AlignTop)

    def _duzenleme_modunu_degistir(self):
        self.duzenleme_modu = not self.duzenleme_modu
        self.duzen_btn.setText("✓ Bitti" if self.duzenleme_modu else "✏️ Düzeni Değiştir")
        self.duzen_btn.setObjectName("primaryBtn" if self.duzenleme_modu else "ghostBtn")
        self.duzen_btn.style().unpolish(self.duzen_btn)
        self.duzen_btn.style().polish(self.duzen_btn)
        self._kartlari_olustur()

    def _masa_pozisyonu_degistir(self, kaynak_id: int, hedef_id: int):
        """Düzenleme modunda bir karti_btn başka bir karti_btnn üzerine bırakınca çalışır:
        kaynağı hedefin hemen önüne taşır (sırayı günceller) - bu sayfa TEK bir
        birime ait olduğu için (bolum zaten sabit), farklı bir KATEGORİ
        (konsol_tipi) panelindeki bir masanın üzerine bırakılırsa masa o
        kategoriye taşınır - yani DEV EKRAN panelinden PS4 paneline sürükleyip
        bırakabilirsiniz."""
        kaynak = self._masa_bul(kaynak_id)
        hedef = self._masa_bul(hedef_id)
        if not kaynak or not hedef or kaynak is hedef:
            return

        kaynak.konsol_tipi = hedef.konsol_tipi

        sira = self.state.masa_sirasi
        for m in self.state.masalar:
            if m.id not in sira:
                sira.append(m.id)
        if kaynak_id in sira:
            sira.remove(kaynak_id)
        hedef_index = sira.index(hedef_id) if hedef_id in sira else len(sira)
        sira.insert(hedef_index, kaynak_id)

        self._kartlari_olustur()

    def yenile(self, zorla_yeniden_kur: bool = False):
        """Ayarlar'dan yeni masa/düzen eklendiyse ızgarayı yeniden kurar; aksi
        halde sadece kartların içeriğini (süre/tutar) tazeler. ÖNEMLİ: SADECE
        bu birimin (grubun) masalarını dolaşıyoruz - state.masalar TÜM
        birimlerin masalarını içerir, hepsini taramaya çalışmak self.kartlar
        sözlüğünde olmayan (başka birime ait) masalar için KeyError verirdi."""
        masalar = self._bu_birimin_masalari()
        if zorla_yeniden_kur or len(self.kartlar) != len(masalar):
            self._kartlari_olustur()
        else:
            for masa in masalar:
                if masa.durum != MasaDurumu.BOS and masa.suresi_doldu_mu():
                    masa.odeme_beklemeye_al()
                self.kartlar[masa.id].guncelle()
        self._stat_kartlarini_guncelle()
        self.alisveris_karti.sepeti_guncelle(self.state.masasiz_sepet)

    def _masa_bul(self, masa_id):
        return next((m for m in self.state.masalar if m.id == masa_id), None)

    def _masaya_cift_tiklandi(self, masa_id):
        masa = self._masa_bul(masa_id)
        if not masa:
            return

        if masa.durum == MasaDurumu.BOS:
            if not self.state.tarife_profilleri:
                uyar(self, "Önce Tarife Ekleyin",
                     "Bu masayı açabilmek için önce Ayarlar > Tarife Kayıtları'ndan en az bir tarife oluşturmalısınız.")
                return
            profil_adi = masa.aktif_tarife_profili or self.state.konsol_varsayilan_profil.get(
                masa.konsol_tipi
            ) or next(iter(self.state.tarife_profilleri))
            tarife_sozlugu = self.state.tarife_profilleri.get(profil_adi, {})
            d = MasaAcDialog(masa, tarife_sozlugu, self.state.tarife_profilleri, self)
            if d.exec() and d.sonuc:
                s = d.sonuc
                # "Tarife ile Aç" farklı bir profil seçtiyse onu kullan, aksi halde
                # masanın varsayılan profilini
                masa.aktif_tarife_profili = s.get("profil") or profil_adi
                masa.ac(s["tarife"], s["hourly"], s["mod"], s["hedef_saniye"])
        else:
            self._yonetim_menusunu_ac(masa)
        self.yenile()

    def _yonetim_menusunu_ac(self, masa):
        """Açık/kilitli/ödeme bekleyen her masada aynı yönetim menüsü açılır -
        kilitliyse 'Kilidi Aç', ödeme bekliyorsa 'Masaya Devam Et' seçeneği içerir."""
        d = MasaIslemDialog(masa, self)
        if d.exec() and d.secilen_aksiyon:
            self._islem_yap(masa, d.secilen_aksiyon)

    def _islem_yap(self, masa, aksiyon):
        if aksiyon == "DEVAM_ET":
            masa.odeme_devam_ettir()
        elif aksiyon == "ODEME_AL":
            d = OdemeAlDialog(masa, self.state, self)
            d.exec()
            if not d.tamamlandi:
                # Ödeme tamamlanmadan kapatıldıysa (Vazgeç/X) süre donmuş halde
                # kalır - yönetim menüsü tekrar açılır, kullanıcı bilinçli olarak
                # "Masaya Devam Et" ya da tekrar "Ödeme Al" seçebilir.
                self._yonetim_menusunu_ac(masa)
        elif aksiyon == "URUN_EKLE":
            from ui.dialogs import UrunEkleDialog
            d = UrunEkleDialog(masa, self.state.urun_katalogu, self)
            d.exec()
            # Ürün Ekle popup'ı kapanınca TÜM zincir kapanıp anasayfaya
            # dönmesin - kullanıcı bu ekrana "Masa İşlem" menüsünden (Ödeme
            # Al / Ürün Ekle / Masa Düzenle listesinden) geldiği için, ürün
            # eklemeyi bitirip Kapat'a basınca o menüye GERİ dönmeli, isterse
            # başka bir işlem seçsin, isterse menüyü kendi kapatsın.
            self._yonetim_menusunu_ac(masa)
        elif aksiyon == "KILITLE":
            if masa.kilitli:
                masa.kilidi_ac()
            else:
                masa.kilitle()
        elif aksiyon == "IPTAL_ET":
            self._masa_iptal_penceresi(masa)
        elif aksiyon == "DUZENLE":
            from ui.dialogs import MasaDuzenleDialog
            MasaDuzenleDialog(masa, self.state.tarife_profilleri, self).exec()
            # Aynı sebeple (Ürün Ekle'deki gibi) - Masa Düzenle kapanınca da
            # doğrudan anasayfaya değil, çağrıldığı "Masa İşlem" menüsüne dönsün.
            self._yonetim_menusunu_ac(masa)

    def _masa_iptal_penceresi(self, masa):
        """Masayı İptal Et: para tahsil edilmeden sıfırlanır - bu yüzden bir
        sebep ZORUNLU (sebepsiz iptale izin verilmez). Sebep, ciroya
        yazılmasa da Son İşlemler'de o gün için görünür kalır - kim/ne
        zaman/neden iptal etti her zaman bilinsin."""
        d = OrtalanmisDialog(self)
        d.setWindowTitle(f"{masa.ad} - İptal Sebebi")
        d.setMinimumWidth(360)
        v = QVBoxLayout(d)
        v.setSpacing(10)

        uyari = QLabel("⚠️ Bu masa ÜCRETSİZ iptal edilecek (ciroya yazılmayacak). Devam etmek için bir sebep girmelisiniz.")
        uyari.setWordWrap(True)
        uyari.setStyleSheet(f"color:{RENK['danger']}; font-size:12px; font-weight:600;")
        v.addWidget(uyari)

        v.addWidget(QLabel("İptal Sebebi:"))
        sebep_input = QLineEdit()
        sebep_input.setPlaceholderText("örn: Müşteri vazgeçti, yanlış açıldı, arıza...")
        v.addWidget(sebep_input)

        onayla_btn = QPushButton("✕ İptali Onayla")
        onayla_btn.setObjectName("dangerBtn")
        v.addWidget(onayla_btn)

        vazgec_btn = QPushButton("Vazgeç")
        vazgec_btn.setObjectName("ghostBtn")
        vazgec_btn.clicked.connect(d.reject)
        v.addWidget(vazgec_btn)

        def _onayla():
            sebep = sebep_input.text().strip()
            if not sebep:
                uyar(d, "Sebep Gerekli", "İptal etmek için bir sebep girmelisiniz.")
                return
            # Son İşlemler'de görünmesi için PARA ALINMAMIŞ olsa bile bir
            # kayıt bırakıyoruz - toplam_tutar 0, ama masa_ucreti/ürün anlık
            # görüntüsü ve iptal_nedeni ile birlikte (denetim amaçlı).
            islem = KasaIslemi(
                id=next_id(), masa_adi=masa.ad, toplam_tutar=0.0,
                odeme_dagilimi={}, zaman=datetime.now(),
                acilis_zamani=masa.segments[0].start_time if masa.segments else None,
                masa_ucreti=masa.guncel_masa_ucreti(),
                urunler=[{"ad": u.urun_adi, "adet": u.adet, "birim_fiyat": u.birim_fiyat} for u in masa.urunler],
                iptal_nedeni=sebep,
            )
            self.state.kasa_islemleri.append(islem)
            masa.iptal_et()
            d.accept()
            self.yenile(zorla_yeniden_kur=True)

        onayla_btn.clicked.connect(_onayla)
        d.exec()

    def _detay_ac(self, masa_id):
        masa = self._masa_bul(masa_id)
        if masa and masa.durum != MasaDurumu.BOS:
            MasaDetayDialog(masa, self).exec()

    def _alisveris_ac(self):
        AlisverisDialog(self.state, self).exec()
        self.alisveris_karti.sepeti_guncelle(self.state.masasiz_sepet)

    def _masa_tasindi(self, kaynak_id, hedef_id):
        kaynak = self._masa_bul(kaynak_id)
        hedef = self._masa_bul(hedef_id)
        if not kaynak or not hedef or kaynak.durum == MasaDurumu.BOS:
            return
        if hedef.durum != MasaDurumu.BOS:
            uyar(self, "Taşınamaz", "Hedef masa boş değil - önce hedef masayı boşaltın.")
            return

        cevap = soru_sor(
            self, "Masa Taşı",
            f"{kaynak.ad} masasındaki oturum {hedef.ad} masasına taşınsın mı?\n"
            f"Ücret bundan sonra {hedef.ad}'ın tarifesiyle hesaplanmaya devam edecek."
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return

        hedef_profil = hedef.aktif_tarife_profili or self.state.konsol_varsayilan_profil.get(
            hedef.konsol_tipi
        ) or next(iter(self.state.tarife_profilleri), "")
        hedef_kollar = self.state.tarife_profilleri.get(hedef_profil, {})
        kaynak_kol = kaynak.segments[-1].tariff_name if kaynak.segments else None
        hedef_kol = kaynak_kol if kaynak_kol in hedef_kollar else next(iter(hedef_kollar), None)
        if not hedef_kol:
            uyar(self, "Tarife Yok", f"{hedef.ad} için tanımlı bir tarife bulunamadı.")
            return
        hedef_ucret = hedef_kollar[hedef_kol]

        kaynak.tasi_ve_devret(hedef, hedef_profil, hedef_kol, hedef_ucret)
        self.yenile()


def _hex_rgba(hex_renk: str, alfa: float) -> str:
    """'#FF4D6D', 0.12 -> 'rgba(255,77,109,0.12)' (Qt QSS'te '#RRGGBBAA' yok,
    '#AARRGGBB' okunur - saydam tonlar için rgba() kullanılır)."""
    h = hex_renk.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alfa})"


_AY_ADLARI_TAM = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def tarih_okunakli(dt: datetime) -> str:
    """'14 Ekim 2026 · 21:53' - gün.ay.yıl rakamları yerine ay ADI ile."""
    return f"{dt.day} {_AY_ADLARI_TAM[dt.month - 1]} {dt.year} · {dt.strftime('%H:%M')}"


class _BorcDetayDialog(OrtalanmisDialog):
    """Borç karti_btnndaki 'Detay ›' - müşteri 'bu borç ne borcuydu?' diye
    sorduğunda: hangi masa, ne zaman, masa ücreti, market kalemleri, satışın
    toplamı, peşin ödenen kısım ve borca yazılan tutar. Satış kaydı
    bulunamazsa (çok eski/eşleşmeyen borç) yalnızca temel bilgi gösterilir."""
    def __init__(self, borc: Borc, islem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Borç Detayı - {borc.ad_soyad}")
        self.setMinimumWidth(380)
        v = QVBoxLayout(self)
        v.setSpacing(14)

        ust_kart = QFrame()
        ust_kart.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #FFF6DD, stop:1 #FFEBB8); border-radius:12px; }"
        )
        ukv = QVBoxLayout(ust_kart)
        ukv.setContentsMargins(18, 14, 18, 14)
        ad_lbl = QLabel(f"👤 {borc.ad_soyad}")
        ad_lbl.setStyleSheet("color:#8A6A1A; font-size:12px; font-weight:800; background:transparent;")
        ukv.addWidget(ad_lbl)
        tutar_lbl = QLabel(f"{borc.tutar:.0f} ₺")
        tutar_lbl.setStyleSheet(f"color:{RENK['warning']}; font-size:28px; font-weight:800; background:transparent;")
        ukv.addWidget(tutar_lbl)
        v.addWidget(ust_kart)

        kart = QFrame()
        kart.setObjectName("masaKart")
        kv = QVBoxLayout(kart)
        kv.addWidget(self._satir("📅 Borç Tarihi", tarih_okunakli(borc.olusturma_zamani)))
        kv.addWidget(self._satir("🎮 Masa", borc.kaynak_masa_adi or "-"))

        if islem is None:
            yok = QLabel("Bu borcun masa/ürün detayı kayıtlı değil.")
            yok.setWordWrap(True)
            yok.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px; margin-top:6px;")
            kv.addWidget(yok)
        else:
            if islem.acilis_zamani:
                kv.addWidget(self._satir("🟢 Açılış", tarih_okunakli(islem.acilis_zamani)))
            kv.addWidget(self._satir("🔴 Kapanış", tarih_okunakli(islem.zaman)))
            kv.addWidget(self._ayirici())
            kv.addWidget(self._satir("Masa Ücreti", f"{islem.masa_ucreti:.0f} ₺"))
            if islem.urunler:
                urun_baslik = QLabel("🛒  Market / Ürünler")
                urun_baslik.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['text']}; margin-top:6px;")
                kv.addWidget(urun_baslik)
                for u in islem.urunler:
                    kv.addWidget(self._satir(f"{u['ad']}  ×{u['adet']}", f"{u['adet'] * u['birim_fiyat']:.0f} ₺"))
            else:
                bos = QLabel("Market satışı yok")
                bos.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px; margin-top:4px;")
                kv.addWidget(bos)
            if islem.indirim_tutari:
                kv.addWidget(self._satir("İndirim", f"-{islem.indirim_tutari:.0f} ₺"))
            kv.addWidget(self._ayirici())
            kv.addWidget(self._satir("Satış Toplamı", f"{islem.toplam_tutar:.0f} ₺", kalin=True))
            pesin = [(ad, t) for ad, t in odeme_kalemleri(islem.odeme_dagilimi) if ad != "Borç"]
            for ad, t in pesin:
                kv.addWidget(self._satir(f"Ödenen ({ad})", f"{t:.0f} ₺"))
            kv.addWidget(self._satir("Borca Yazılan", f"{borc.tutar:.0f} ₺", kalin=True))
        v.addWidget(kart)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("ghostBtn")
        kapat_btn.clicked.connect(self.accept)
        v.addWidget(kapat_btn)

    def _ayirici(self) -> QFrame:
        a = QFrame()
        a.setFrameShape(QFrame.Shape.HLine)
        a.setStyleSheet(f"background-color:{RENK['border_strong']}; max-height:1px; margin-top:6px; margin-bottom:4px;")
        return a

    def _satir(self, etiket: str, deger: str, kalin: bool = False) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        e = QLabel(etiket)
        e.setStyleSheet(f"font-size:12px; color:{RENK['text'] if kalin else RENK['text_muted']}; font-weight:{800 if kalin else 600};")
        d = QLabel(deger)
        d.setStyleSheet(f"font-size:12px; color:{RENK['text']}; font-weight:800;")
        h.addWidget(e)
        h.addStretch()
        h.addWidget(d)
        return w


class BorclarView(QWidget):
    """Borçlar sayfası - eskiden tek sütun, uçtan uca uzayan çirkin bir liste
    idi (kullanıcı: 'borçlar kısmı çirkin duruyor'). Artık MasaKarti/UrunKarti
    ile aynı ailede, sabit boyutlu, ızgara halinde dizilen 'premium' kartlar
    kullanıyor - pencere genişliğine göre otomatik sütun sayısı ayarlanır."""

    KART_GENISLIK = 236
    KART_YUKSEKLIK = 184

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        dis = QVBoxLayout(self)
        dis.setContentsMargins(28, 24, 28, 24)
        baslik = QLabel("Borçlar")
        baslik.setObjectName("pageTitle")
        dis.addWidget(baslik)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.ic = QWidget()
        self.ic.setObjectName("borcIc")
        self.ic.setStyleSheet("QWidget#borcIc { background:transparent; }")
        self.liste = QGridLayout(self.ic)
        self.liste.setSpacing(14)
        self.liste.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self.ic)
        dis.addWidget(scroll)

        # Alt toplam çubuğu: kart seçilince seçilenlerin, seçim yoksa tüm açık borçların toplamı
        self._secili: set[int] = set()
        alt_cubuk = QHBoxLayout()
        self.ipucu_lbl = QLabel("Toplam görmek için kartlara tıklayarak seçin")
        self.ipucu_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px;")
        alt_cubuk.addWidget(self.ipucu_lbl)
        alt_cubuk.addStretch()
        self.secimi_temizle_btn = QPushButton("Seçimi Temizle")
        self.secimi_temizle_btn.setObjectName("ghostBtn")
        self.secimi_temizle_btn.clicked.connect(self._secimi_temizle)
        alt_cubuk.addWidget(self.secimi_temizle_btn)
        self.toplam_lbl = QLabel()
        self.toplam_lbl.setStyleSheet(
            f"font-size:15px; font-weight:800; color:{RENK['warning']}; background:#FFFFFF;"
            f"border:1px solid {RENK['border_strong']}; border-radius:10px; padding:8px 16px;"
        )
        alt_cubuk.addWidget(self.toplam_lbl)
        dis.addLayout(alt_cubuk)
        self.yenile()

    def _secimi_temizle(self):
        self._secili.clear()
        self.yenile()

    def _borc_secimi_degistir(self, borc: Borc):
        if borc.id in self._secili:
            self._secili.discard(borc.id)
        else:
            self._secili.add(borc.id)
        self.yenile()

    def _toplam_guncelle(self, acik_borclar):
        self._secili &= {b.id for b in acik_borclar}
        secililer = [b for b in acik_borclar if b.id in self._secili]
        if secililer:
            toplam = sum(b.tutar for b in secililer)
            self.toplam_lbl.setText(f"Seçili {len(secililer)} borç:  {toplam:.0f} ₺")
            self.ipucu_lbl.setText("")
        else:
            toplam = sum(b.tutar for b in acik_borclar)
            self.toplam_lbl.setText(f"Tüm açık borçlar ({len(acik_borclar)}):  {toplam:.0f} ₺")
            self.ipucu_lbl.setText("Toplam görmek için kartlara tıklayarak seçin" if acik_borclar else "")
        self.secimi_temizle_btn.setVisible(bool(secililer))

    def _hesapla_sutun(self) -> int:
        kart_birim = self.KART_GENISLIK + self.liste.spacing()
        kenar_boslugu = 28 + 28 + 24  # sayfa iç boşluğu + scrollbar payı
        kullanilabilir = max(self.width() - kenar_boslugu, kart_birim)
        return max(1, kullanilabilir // kart_birim)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        yeni_deger = self._hesapla_sutun()
        if yeni_deger != getattr(self, "_mevcut_sutun", None):
            self._mevcut_sutun = yeni_deger
            self.yenile()

    def yenile(self):
        while self.liste.count():
            item = self.liste.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        acik_borclar = [b for b in self.state.borclar if not b.odendi]
        self._toplam_guncelle(acik_borclar)
        if not acik_borclar:
            self.liste.addWidget(QLabel("Açık borç yok"), 0, 0)
            return

        SUTUN = self._hesapla_sutun()
        self._mevcut_sutun = SUTUN
        for i, borc in enumerate(acik_borclar):
            kart = self._borc_karti(borc)
            self.liste.addWidget(kart, i // SUTUN, i % SUTUN)

    def _borc_karti(self, borc: Borc) -> QFrame:
        f = QFrame()
        f.setObjectName("masaKart")
        f.setFixedSize(self.KART_GENISLIK, self.KART_YUKSEKLIK)
        f.setCursor(Qt.CursorShape.PointingHandCursor)
        if borc.id in self._secili:
            f.setStyleSheet(
                f"QFrame#masaKart {{ border:2px solid {RENK['accent']}; background-color:{_hex_rgba(RENK['accent'], 0.07)}; }}"
            )
        f.mousePressEvent = lambda e, b=borc: (
            self._borc_secimi_degistir(b) if e.button() == Qt.MouseButton.LeftButton else None
        )
        v = QVBoxLayout(f)
        v.setContentsMargins(14, 12, 14, 10)
        v.setSpacing(4)

        # --- Üst satır: ikon + ad soyad (sol) | tutar rozeti (sağ) ---
        ust = QHBoxLayout()
        ust.setSpacing(8)
        ikon_kutu = QLabel("👤")
        ikon_kutu.setFixedSize(26, 26)
        ikon_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ikon_kutu.setStyleSheet(
            f"background-color:{_hex_rgba(RENK['warning'], 0.14)}; border-radius:7px; font-size:13px;"
        )
        ust.addWidget(ikon_kutu)
        ad_lbl = QLabel(borc.ad_soyad)
        ad_lbl.setObjectName("masaAdi")
        ad_lbl.setStyleSheet("font-size:13px; font-weight:800;")
        ad_lbl.setWordWrap(True)
        ust.addWidget(ad_lbl, 1)
        v.addLayout(ust)

        v.addStretch()

        # --- Orta: büyük, dikkat çeken tutar ---
        tutar_lbl = QLabel(f"{borc.tutar:.0f} ₺")
        tutar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tutar_lbl.setStyleSheet(f"font-size:22px; font-weight:800; color:{RENK['warning']};")
        v.addWidget(tutar_lbl)

        v.addStretch()

        # --- Bilgi satırı: solda OKUNAKLI tarih+saat ve hangi masadan
        # doğduğu, sağ altta "Detay ›" (MasaKarti'ndaki düzenle) ---
        bilgi_satir = QHBoxLayout()
        bilgi_satir.setSpacing(6)
        bilgi_v = QVBoxLayout()
        bilgi_v.setSpacing(1)
        tarih_lbl = QLabel(f"📅 {tarih_okunakli(borc.olusturma_zamani)}")
        tarih_lbl.setStyleSheet(f"font-size:11px; font-weight:700; color:{RENK['text']};")
        bilgi_v.addWidget(tarih_lbl)
        if borc.kaynak_masa_adi:
            kaynak_lbl = QLabel(f"🎮 {borc.kaynak_masa_adi}")
            kaynak_lbl.setStyleSheet(f"font-size:10px; font-weight:600; color:{RENK['text_muted']};")
            bilgi_v.addWidget(kaynak_lbl)
        bilgi_satir.addLayout(bilgi_v, 1)
        detay_btn = QPushButton("Detay ›")
        detay_btn.setObjectName("ghostBtn")
        detay_btn.setStyleSheet("padding:3px 9px; font-size:10px; font-weight:700;")
        detay_btn.clicked.connect(lambda: self._detay(borc))
        bilgi_satir.addWidget(detay_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        v.addLayout(bilgi_satir)

        # --- Alt satır: Düzenle (ghost) | Borcu Öde (primary) ---
        alt = QHBoxLayout()
        alt.setSpacing(6)
        duzenle_btn = QPushButton("Düzenle")
        duzenle_btn.setObjectName("ghostBtn")
        duzenle_btn.setStyleSheet("padding:4px 8px; font-size:10px; font-weight:700;")
        duzenle_btn.clicked.connect(lambda: self._duzenle(borc))
        alt.addWidget(duzenle_btn, 0, Qt.AlignmentFlag.AlignLeft)
        alt.addStretch()

        ode_btn = QPushButton("Borcu Öde")
        ode_btn.setObjectName("primaryBtn")
        ode_btn.setStyleSheet("padding:4px 8px; font-size:10px; font-weight:700;")
        ode_btn.clicked.connect(lambda: self._ode(borc))
        alt.addWidget(ode_btn, 0, Qt.AlignmentFlag.AlignRight)
        v.addLayout(alt)
        return f

    def _detay(self, borc: Borc):
        _BorcDetayDialog(borc, self.state.borc_islemi_bul(borc), self).exec()

    def _duzenle(self, borc: Borc):
        yeni_ad, ok = metin_sor(self, "Düzenle", "Ad Soyad:", borc.ad_soyad)
        if ok and yeni_ad.strip():
            borc.ad_soyad = yeni_ad.strip()
            self.yenile()

    def _ode(self, borc: Borc):
        """Borç ödeme ekranı - masa ödeme ekranıyla AYNI mantık ama BORÇ seçeneği YOK,
        ve bu işlem ciroya YAZILMAZ (is_borc_tahsilati=True)."""
        d = _BorcOdemeDialog(borc, self)
        if d.exec() and d.tamamlandi:
            islem = KasaIslemi(
                id=next_id(), masa_adi=f"[BORÇ TAHSİLATI] {borc.ad_soyad}",
                toplam_tutar=borc.tutar, odeme_dagilimi=d.dagitim,
                is_borc_tahsilati=True
            )
            self.state.kasa_islemleri.append(islem)
            borc.odendi = True
            from datetime import datetime
            borc.odenme_zamani = datetime.now()
            self.yenile()


class _BorcOdemeDialog(OrtalanmisDialog):
    """Borç kapatma için sadeleştirilmiş ödeme ekranı (BORÇ seçeneği hariç)."""
    def __init__(self, borc: Borc, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Borç Öde - {borc.ad_soyad}")
        self.borc = borc
        self.tamamlandi = False
        self.dagitim = {}

        v = QVBoxLayout(self)
        v.setSpacing(10)

        tutar_lbl = QLabel(f"Borç Tutarı: {borc.tutar:.0f} ₺")
        tutar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tutar_lbl.setStyleSheet(f"font-size:20px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
        v.addWidget(tutar_lbl)

        odeme_baslik = QLabel("Ödeme Dağılımı")
        odeme_baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        odeme_baslik.setStyleSheet("font-weight:700; margin-top:6px;")
        v.addWidget(odeme_baslik)

        ODEME_IKONLARI = {"NAKİT": "💵", "KART": "💳", "İBAN": "🏦"}
        self.inputs = {}
        for yontem in ["NAKİT", "KART", "İBAN"]:
            row = QHBoxLayout()
            row.addStretch()
            etiket = QLabel(f"{ODEME_IKONLARI[yontem]}  {yontem}")
            etiket.setMinimumWidth(100)
            etiket.setStyleSheet("font-weight:600;")
            row.addWidget(etiket)
            spin = SessizDoubleSpinBox()
            spin.setRange(0, 999999)
            spin.setDecimals(0)
            spin.setFixedWidth(130)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.valueChanged.connect(self._hesapla)
            self.inputs[yontem] = spin
            row.addWidget(spin)
            row.addStretch()
            v.addLayout(row)

        self.kalan_lbl = QLabel()
        self.kalan_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kalan_lbl.setStyleSheet("font-size:15px; font-weight:800; background:transparent; border:none; margin-top:4px;")
        v.addWidget(self.kalan_lbl)

        tamamla = QPushButton("Ödemeyi Tamamla")
        tamamla.setObjectName("odemeBtn")
        tamamla.setDefault(True)
        tamamla.setAutoDefault(True)
        tamamla.clicked.connect(self._tamamla)
        v.addWidget(tamamla)
        self._hesapla()

    def _hesapla(self):
        girilen = sum(s.value() for s in self.inputs.values())
        kalan = self.borc.tutar - girilen
        ortak_stil = "font-size:15px; font-weight:800; background:transparent; border:none; margin-top:4px;"
        if kalan > 0:
            self.kalan_lbl.setText(f"Kalan: {kalan:.0f} ₺")
            self.kalan_lbl.setStyleSheet(f"color:#f5a623; {ortak_stil}")
        elif kalan < 0:
            self.kalan_lbl.setText(f"Para Üstü: {abs(kalan):.0f} ₺")
            self.kalan_lbl.setStyleSheet(f"color:#2ecc71; {ortak_stil}")
        else:
            self.kalan_lbl.setText("Tam ödendi ✓")
            self.kalan_lbl.setStyleSheet(f"color:#2ecc71; {ortak_stil}")

    def _tamamla(self):
        girilen = sum(s.value() for s in self.inputs.values())
        if girilen < self.borc.tutar:
            uyar(self, "Eksik Ödeme", "Girilen tutar borç tutarından az olamaz.")
            return
        dagitim_ham = {k: v.value() for k, v in self.inputs.items() if v.value() > 0}
        self.dagitim = para_ustunu_dagitimdan_dus(dagitim_ham, self.borc.tutar)
        self.tamamlandi = True
        self.accept()


class SalonAdiView(QWidget):
    """Ayarlar > Salon Adı alt sayfası - her birim sayfasındaki 'Hoş geldin, ...'
    yazısında kullanılır."""
    def __init__(self, state: AppState, birim_sayfalarini_yenile_cb, parent=None):
        super().__init__(parent)
        self.state = state
        self.birim_sayfalarini_yenile_cb = birim_sayfalarini_yenile_cb
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)
        baslik = QLabel("Ayarlar  ›  Salon Adı")
        baslik.setObjectName("pageTitle")
        v.addWidget(baslik)

        kutu = QFrame()
        kutu.setObjectName("masaKart")
        kv = QVBoxLayout(kutu)
        kv.addWidget(QLabel("Salon Adı"))
        satir = QHBoxLayout()
        self.salon_input = QLineEdit(self.state.salon_adi)
        satir.addWidget(self.salon_input)
        kaydet_btn = QPushButton("Kaydet")
        kaydet_btn.setObjectName("primaryBtn")
        kaydet_btn.clicked.connect(self._kaydet)
        satir.addWidget(kaydet_btn)
        kv.addLayout(satir)
        v.addWidget(kutu)
        v.addStretch()

    def _kaydet(self):
        yeni_ad = self.salon_input.text().strip()
        if yeni_ad:
            self.state.salon_adi = yeni_ad
            self.birim_sayfalarini_yenile_cb()
            bilgilendir(self, "Kaydedildi", f"Salon adı '{yeni_ad}' olarak güncellendi.")


class MasaKayitlariView(QWidget):
    """Ayarlar > Masa Kayıtları: Grup Ekle + Masa Ekle (isim + grup seçimi;
    grup seçilince isim otomatik '{grup} {sıradaki_no}' olarak önerilir, siz
    isterseniz değiştirebilirsiniz) + kayıtlı masalar listesi (isim/grup
    düzenlenebilir, silinebilir)."""
    def __init__(self, state: AppState, birim_sayfalarini_yenile_cb, parent=None):
        super().__init__(parent)
        self.state = state
        self.birim_sayfalarini_yenile_cb = birim_sayfalarini_yenile_cb
        self.combolar: dict[int, QComboBox] = {}
        self._acik_profiller: set[str] = set()

        # TEK BİR dış kaydırma alanı (Kasa/Anasayfa'daki gibi) - alt
        # bölümlerin HER BİRİNE ayrı ayrı küçük kaydırma kutusu koymak
        # (eski hâli) iç içe kaydırma çakışmasına ve bölümlerin "tek satıra
        # sıkışmış" görünmesine sebep oluyordu. Artık her bölüm doğal
        # boyutunda büyüyor, taşarsa SADECE sayfanın kendisi kayıyor.
        outer_v = QVBoxLayout(self)
        outer_v.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        ic = QWidget()
        ic.setStyleSheet("background:transparent;")
        v = QVBoxLayout(ic)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)
        scroll.setWidget(ic)
        outer_v.addWidget(scroll)

        baslik = QLabel("Ayarlar  ›  Masa ve Tarife Kayıtları")
        baslik.setObjectName("pageTitle")
        v.addWidget(baslik)

        # --- Grup Ekle / Tarife Ekle / Masa Ekle: sayfada sürekli açık
        # durmasınlar, tıklayınca küçük birer pencere açılsın ---
        ust_buton_satir = QHBoxLayout()
        grup_ekle_btn = QPushButton("+ Grup Ekle")
        grup_ekle_btn.setObjectName("secenekBtn")
        grup_ekle_btn.clicked.connect(self._grup_ekle_penceresi)
        ust_buton_satir.addWidget(grup_ekle_btn)
        tarife_ekle_btn = QPushButton("+ Tarife Ekle")
        tarife_ekle_btn.setObjectName("secenekBtn")
        tarife_ekle_btn.clicked.connect(self._tarife_ekle_penceresi)
        ust_buton_satir.addWidget(tarife_ekle_btn)
        masa_ekle_btn = QPushButton("+ Masa Ekle")
        masa_ekle_btn.setObjectName("secenekBtn")
        masa_ekle_btn.clicked.connect(self._masa_ekle_penceresi)
        ust_buton_satir.addWidget(masa_ekle_btn)
        ust_buton_satir.addStretch()
        v.addLayout(ust_buton_satir)

        # --- Kayıtlı Gruplar (liste) ---
        grup_liste_kutu = QFrame()
        grup_liste_kutu.setObjectName("masaKart")
        self.grup_liste_v = QVBoxLayout(grup_liste_kutu)
        self.grup_liste_v.setSpacing(6)
        self.grup_liste_v.addWidget(QLabel("Kayıtlı Gruplar"))
        v.addWidget(grup_liste_kutu)

        # --- Kayıtlı Masalar: açılır/kapanır başlık + doğal boyutunda liste
        # (ayrı kaydırma kutusu YOK arti_btnk - sayfa kendisi kayıyor) ---
        self._masalar_acik = True
        liste_kutu = QFrame()
        liste_kutu.setObjectName("masaKart")
        liste_kutu_v = QVBoxLayout(liste_kutu)
        self.masalar_baslik_btn = QPushButton()
        self.masalar_baslik_btn.setObjectName("ghostBtn")
        self.masalar_baslik_btn.setStyleSheet("text-align:left; font-weight:700; background:transparent; border:none; padding:4px 0;")
        self.masalar_baslik_btn.clicked.connect(self._masalar_ac_kapa)
        liste_kutu_v.addWidget(self.masalar_baslik_btn)

        self.masalar_icerik = QWidget()
        self.liste_v = QVBoxLayout(self.masalar_icerik)
        self.liste_v.setContentsMargins(0, 0, 0, 0)
        self.liste_v.setSpacing(6)
        liste_kutu_v.addWidget(self.masalar_icerik)

        v.addWidget(liste_kutu)

        # --- Tanımlı Tarife Profilleri: açılır/kapanır başlık + doğal
        # boyutunda liste (arti_btnk ayrı bir sayfa değil, gereksiz bir Ayarlar
        # maddesi kalkmış oldu) ---
        self._profiller_acik = True
        profiller_kutu = QFrame()
        profiller_kutu.setObjectName("masaKart")
        profiller_kutu_v = QVBoxLayout(profiller_kutu)
        self.profiller_baslik_btn = QPushButton()
        self.profiller_baslik_btn.setObjectName("ghostBtn")
        self.profiller_baslik_btn.setStyleSheet("text-align:left; font-weight:700; background:transparent; border:none; padding:4px 0;")
        self.profiller_baslik_btn.clicked.connect(self._profiller_ac_kapa)
        profiller_kutu_v.addWidget(self.profiller_baslik_btn)

        self.profiller_icerik = QWidget()
        self.pkv = QVBoxLayout(self.profiller_icerik)
        self.pkv.setContentsMargins(0, 0, 0, 0)
        self.pkv.setSpacing(8)
        profiller_kutu_v.addWidget(self.profiller_icerik)
        v.addWidget(profiller_kutu)

        # --- Masa Bazlı Tarife Ataması: açılır/kapanır başlık + doğal
        # boyutunda liste ---
        self._masa_atama_acik = True
        masa_atama_kutu = QFrame()
        masa_atama_kutu.setObjectName("masaKart")
        masa_atama_kutu_v = QVBoxLayout(masa_atama_kutu)
        self.masa_atama_baslik_btn = QPushButton()
        self.masa_atama_baslik_btn.setObjectName("ghostBtn")
        self.masa_atama_baslik_btn.setStyleSheet("text-align:left; font-weight:700; background:transparent; border:none; padding:4px 0;")
        self.masa_atama_baslik_btn.clicked.connect(self._masa_atama_ac_kapa)
        masa_atama_kutu_v.addWidget(self.masa_atama_baslik_btn)

        self.masa_atama_icerik = QWidget()
        self.mkv = QVBoxLayout(self.masa_atama_icerik)
        self.mkv.setContentsMargins(0, 0, 0, 0)
        self.mkv.setSpacing(6)
        masa_atama_kutu_v.addWidget(self.masa_atama_icerik)
        v.addWidget(masa_atama_kutu)

        v.addStretch()

        self._satirlari_kur()
        self._grup_satirlarini_kur()
        self._profil_listesini_kur()
        self._masa_satirlarini_kur()

    def _profiller_ac_kapa(self):
        self._profiller_acik = not self._profiller_acik
        self.profiller_icerik.setVisible(self._profiller_acik)
        self._profiller_baslik_guncelle()

    def _profiller_baslik_guncelle(self):
        ok = "▾" if self._profiller_acik else "▸"
        self.profiller_baslik_btn.setText(f"{ok}  Tanımlı Tarife Profilleri  ({len(self.state.tarife_profilleri)})")

    def _masa_atama_ac_kapa(self):
        self._masa_atama_acik = not self._masa_atama_acik
        self.masa_atama_icerik.setVisible(self._masa_atama_acik)
        self._masa_atama_baslik_guncelle()

    def _masa_atama_baslik_guncelle(self):
        ok = "▾" if self._masa_atama_acik else "▸"
        self.masa_atama_baslik_btn.setText(f"{ok}  Masa Bazlı Tarife Ataması  ({len(self.state.masalar)})")

    def _masalar_ac_kapa(self):
        self._masalar_acik = not self._masalar_acik
        self.masalar_icerik.setVisible(self._masalar_acik)
        self._masalar_baslik_guncelle()

    def _masalar_baslik_guncelle(self):
        ok = "▾" if self._masalar_acik else "▸"
        self.masalar_baslik_btn.setText(f"{ok}  Kayıtlı Masalar  ({len(self.state.masalar)})")

    def _grup_satirlarini_kur(self):
        while self.grup_liste_v.count() > 1:
            item = self.grup_liste_v.takeAt(1)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        if not self.state.gruplar:
            bos_lbl = QLabel("Henüz kayıtlı grup yok.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
            self.grup_liste_v.addWidget(bos_lbl)
            return

        for grup in self.state.gruplar:
            satir_kutu = QFrame()
            satir_kutu.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
                f"QFrame:hover {{ background-color:#E8E9ED; border-color:{RENK['accent']}; }}"
            )
            satir = QHBoxLayout(satir_kutu)
            satir.setContentsMargins(10, 6, 10, 6)
            masa_sayisi = sum(1 for m in self.state.masalar if m.gorunur_bolum() == grup)
            ad_lbl = QLabel(f"{grup}  ({masa_sayisi} masa)")
            ad_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text']}; background:transparent;")
            satir.addWidget(ad_lbl, 1)
            duzenle_btn = QPushButton("✏  Adı Düzenle")
            duzenle_btn.setObjectName("ghostBtn")
            duzenle_btn.clicked.connect(lambda checked, g=grup: self._grup_adini_duzenle(g))
            satir.addWidget(duzenle_btn)
            sil_btn = cop_butonu_yap(QPushButton())
            sil_btn.clicked.connect(lambda checked, g=grup: self._grup_sil(g))
            satir.addWidget(sil_btn)
            wrap = satir_kutu
            self.grup_liste_v.addWidget(wrap)

            # Bu birimin kategorileri (PS4, PS5 gibi) - adı yanlış yazıldıysa düzeltilebilsin
            sayac: dict[str, int] = {}
            for m in self.state.masalar:
                if m.gorunur_bolum() == grup:
                    sayac[m.konsol_tipi] = sayac.get(m.konsol_tipi, 0) + 1
            for kat, adet in sayac.items():
                kr = QHBoxLayout()
                kr.setContentsMargins(26, 0, 4, 0)
                kl = QLabel(f"↳ Kategori: {kat}  ({adet} masa)")
                kl.setStyleSheet(f"font-size:11px; color:{RENK['text_muted']}; font-weight:600;")
                kr.addWidget(kl, 1)
                kb = QPushButton("✏  Kategori Adını Düzenle")
                kb.setObjectName("ghostBtn")
                kb.setStyleSheet("padding:3px 9px; font-size:10px; font-weight:700;")
                kb.clicked.connect(lambda checked, g=grup, k=kat: self._kategori_adini_duzenle(g, k))
                kr.addWidget(kb)
                kw = QWidget()
                kw.setLayout(kr)
                self.grup_liste_v.addWidget(kw)

    def _yenile_hepsi(self):
        self.birim_sayfalarini_yenile_cb(zorla_yeniden_kur=True)
        self._satirlari_kur()
        self._grup_satirlarini_kur()
        self._masa_satirlarini_kur()

    def _grup_adini_duzenle(self, grup: str):
        yeni, ok = metin_sor(self, "Grup Adını Düzenle", "Yeni ad:", grup)
        yeni = yeni.strip()
        if not ok or not yeni or yeni == grup:
            return
        if not self.state.grup_yeniden_adlandir(grup, yeni):
            uyar(self, "Aynı İsim", "Bu isimde başka bir grup zaten var.")
            return
        self._yenile_hepsi()

    def _kategori_adini_duzenle(self, grup: str, kategori: str):
        yeni, ok = metin_sor(self, "Kategori Adını Düzenle", "Yeni ad:", kategori)
        yeni = yeni.strip()
        if not ok or not yeni or yeni == kategori:
            return
        mevcut = {m.konsol_tipi for m in self.state.masalar if m.gorunur_bolum() == grup}
        if yeni in mevcut:
            if soru_sor(self, "Birleştir",
                        f"'{yeni}' kategorisi zaten var. '{kategori}' içindeki masalar onunla birleştirilsin mi?"
                        ) != QMessageBox.StandardButton.Yes:
                return
        masa_adlari = False
        if any(m.ad.startswith(kategori) for m in self.state.masalar
               if m.gorunur_bolum() == grup and m.konsol_tipi == kategori):
            masa_adlari = soru_sor(
                self, "Masa Adları",
                f"Masa adlarındaki '{kategori}' kısmı da '{yeni}' olsun mu?\n(Örn: '{kategori} 1' → '{yeni} 1')"
            ) == QMessageBox.StandardButton.Yes
        self.state.kategori_yeniden_adlandir(grup, kategori, yeni, masa_adlari)
        self._yenile_hepsi()

    def _grup_sil(self, grup: str):
        masa_sayisi = sum(1 for m in self.state.masalar if m.gorunur_bolum() == grup)
        if masa_sayisi > 0:
            uyar(self, "Silinemedi",
                 f"'{grup}' grubunda hâlâ {masa_sayisi} masa var. Önce bu masaları başka bir gruba "
                 f"taşıyın ya da silin, sonra grubu silebilirsiniz.")
            return
        cevap = soru_sor(self, "Grubu Sil", f"'{grup}' grubu silinsin mi?")
        if cevap == QMessageBox.StandardButton.Yes:
            self.state.grup_sil(grup)
            self._grup_satirlarini_kur()

    def _grup_ekle_penceresi(self):
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Grup Ekle")
        d.setMinimumWidth(320)
        v = QVBoxLayout(d)
        aciklama = QLabel(
            "Anasayfa'da masalar bu gruplara göre yan yana panel halinde gösterilir. "
            "Örnek: 'Dev Ekran' grubunu ekleyin, sonra masa eklerken bu grubu seçin - "
            "isim otomatik 'Dev Ekran 1', 'Dev Ekran 2' diye önerilir."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px;")
        v.addWidget(aciklama)
        v.addWidget(QLabel("Grup Adı:"))
        ad_input = QLineEdit()
        v.addWidget(ad_input)
        ekle_btn = QPushButton("+ Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setDefault(True)
        ekle_btn.setAutoDefault(True)
        v.addWidget(ekle_btn)

        def _ekle():
            ad = ad_input.text().strip()
            if not ad:
                uyar(d, "Eksik Bilgi", "Grup adı boş olamaz.")
                return
            if not self.state.grup_ekle(ad):
                uyar(d, "Aynı İsim", "Bu grup zaten kayıtlı.")
                return
            self._grup_satirlarini_kur()
            d.accept()

        ekle_btn.clicked.connect(_ekle)
        d.exec()

    def _masa_ekle_penceresi(self):
        if not self.state.gruplar:
            bilgilendir(self, "Önce Grup Ekleyin", "Masa eklemeden önce en az bir grup oluşturmalısınız.")
            return
        if not self.state.tarife_profilleri:
            bilgilendir(self, "Önce Tarife Ekleyin",
                        "Masa eklemeden önce Ayarlar > Tarife Kayıtları'ndan en az bir tarife oluşturmalısınız.")
            return
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Masa Ekle")
        d.setMinimumWidth(340)
        v = QVBoxLayout(d)

        v.addWidget(QLabel("Birim:"))
        grup_combo = TamamlamaKutusu(self.state.gruplar)
        grup_combo.setMinimumWidth(200)
        v.addWidget(grup_combo)

        v.addWidget(QLabel("Kategori (aynı birim İÇİNDE alt bölüm - örn. 'DEV EKRAN', 'PLAYSTATION 4'. Boş bırakırsanız birim adıyla aynı olur):"))
        kategori_combo = TamamlamaKutusu([])
        kategori_combo.setMinimumWidth(200)
        v.addWidget(kategori_combo)

        v.addWidget(QLabel("Masa Adı:"))
        isim_input = QLineEdit()
        isim_input.setPlaceholderText("Kategori seçince otomatik önerilir, isterseniz değiştirin")
        v.addWidget(isim_input)

        def _isim_oner():
            kategori = kategori_combo.text().strip() or grup_combo.text().strip()
            if not kategori:
                return
            sira = len([m for m in self.state.masalar if m.konsol_tipi == kategori]) + 1
            isim_input.setText(f"{kategori} {sira}")

        def _grup_degisti(grup):
            grup = grup.strip()
            if not grup:
                return
            # Bu birimde daha önce kullanılan kategorileri (DEV EKRAN, PS4 gibi)
            # öneri listesine koyuyoruz - kullanıcı bunlardan seçebilir ya da
            # yeni bir kategori adı yazabilir.
            mevcut_kategoriler = sorted({m.konsol_tipi for m in self.state.masalar if m.gorunur_bolum() == grup})
            kategori_combo.secenekleri_guncelle(mevcut_kategoriler)
            _isim_oner()

        grup_combo.textChanged.connect(_grup_degisti)
        kategori_combo.textChanged.connect(lambda _: _isim_oner())

        ekle_btn = QPushButton("+ Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setDefault(True)
        ekle_btn.setAutoDefault(True)
        v.addWidget(ekle_btn)

        def _ekle():
            grup = grup_combo.text().strip()
            kategori = kategori_combo.text().strip() or grup
            ad = isim_input.text().strip()
            if not grup:
                uyar(d, "Eksik Bilgi", "Birim seçin ya da yazın.")
                return
            if not ad:
                uyar(d, "Eksik Bilgi", "Masa adı boş olamaz.")
                return
            if any(m.ad == ad for m in self.state.masalar):
                uyar(d, "Aynı İsim", "Bu isimde bir masa zaten var.")
                return
            self.state.masa_ekle(ad, konsol_tipi=kategori, grup=grup)
            self.birim_sayfalarini_yenile_cb(zorla_yeniden_kur=True)
            self._satirlari_kur()
            self._grup_satirlarini_kur()
            self._masa_satirlarini_kur()
            d.accept()

        ekle_btn.clicked.connect(_ekle)
        d.exec()

    def _satirlari_kur(self):
        self._masalar_baslik_guncelle()
        while self.liste_v.count():
            item = self.liste_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        for masa in self.state.masalar:
            satir_kutu = QFrame()
            satir_kutu.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
                f"QFrame:hover {{ background-color:#E8E9ED; border-color:{RENK['accent']}; }}"
            )
            satir = QHBoxLayout(satir_kutu)
            satir.setContentsMargins(10, 6, 10, 6)

            ad_edit = QLineEdit(masa.ad)
            satir.addWidget(ad_edit, 2)

            grup_combo = TamamlamaKutusu(self.state.gruplar)
            grup_combo.setMinimumWidth(150)
            grup_combo.setText(masa.gorunur_bolum())
            satir.addWidget(grup_combo, 1)

            kaydet_btn = QPushButton("Kaydet")
            kaydet_btn.setObjectName("ghostBtn")
            kaydet_btn.clicked.connect(
                lambda checked, m=masa, a=ad_edit, g=grup_combo: self._satir_kaydet(m, a, g)
            )
            satir.addWidget(kaydet_btn)

            sil_btn = QPushButton("Sil")
            sil_btn.setObjectName("dangerBtn")
            sil_btn.clicked.connect(lambda checked, m=masa: self._sil(m))
            satir.addWidget(sil_btn)

            wrap = satir_kutu
            self.liste_v.addWidget(wrap)

    def _satir_kaydet(self, masa: Masa, ad_edit: QLineEdit, grup_combo: "TamamlamaKutusu"):
        yeni_ad = ad_edit.text().strip()
        yeni_grup = grup_combo.text().strip()
        if not yeni_ad or not yeni_grup:
            uyar(self, "Eksik Bilgi", "Masa adı ve grup boş olamaz.")
            return
        if any(m.ad == yeni_ad for m in self.state.masalar if m is not masa):
            uyar(self, "Aynı İsim", "Bu isimde başka bir masa zaten var.")
            return
        masa.ad = yeni_ad
        masa.bolum = yeni_grup  # kategori (konsol_tipi) korunur - sadece birim değişir
        if yeni_grup not in self.state.gruplar:
            self.state.gruplar.append(yeni_grup)
        self.birim_sayfalarini_yenile_cb(zorla_yeniden_kur=True)
        self._satirlari_kur()
        self._grup_satirlarini_kur()
        self._masa_satirlarini_kur()
        bilgilendir(self, "Kaydedildi", f"'{yeni_ad}' güncellendi.")

    def _sil(self, masa: Masa):
        if masa.durum != MasaDurumu.BOS:
            uyar(self, "Silinemez", "Bu masa boş değil - önce ödeme alıp boşaltın.")
            return
        cevap = soru_sor(
            self, "Masayı Sil", f"'{masa.ad}' kalıcı olarak silinsin mi?"
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        self.state.masalar.remove(masa)
        if masa.id in self.state.masa_sirasi:
            self.state.masa_sirasi.remove(masa.id)
        self.birim_sayfalarini_yenile_cb(zorla_yeniden_kur=True)
        self._satirlari_kur()
        self._grup_satirlarini_kur()
        self._masa_satirlarini_kur()

    def _profil_listesini_kur(self):
        self._profiller_baslik_guncelle()
        while self.pkv.count():
            item = self.pkv.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        self.pkv.addWidget(self._olustur_aciklama(
            "Bir tarifenin adına tıklayınca kol/fiyat listesi açılır - fiyatları "
            "buradan güncelleyin, kaydettiğinizde bu tarifeyi kullanan masalarda "
            "bundan sonraki açılış/kol geçişlerinde otomatik yeni fiyat geçerli olur."
        ))

        self.profil_spinlar: dict[str, dict[str, SessizDoubleSpinBox]] = {}
        for profil_adi, kollar in self.state.tarife_profilleri.items():
            acik = profil_adi in self._acik_profiller
            profil_kutu = QFrame()
            profil_kutu.setStyleSheet(f"border-top:1px solid {RENK['border']}; margin-top:6px; padding-top:6px;")
            pv = QVBoxLayout(profil_kutu)
            pv.setSpacing(8)

            baslik_btn = QPushButton(f"{'▾' if acik else '▸'}  {profil_adi}")
            baslik_btn.setObjectName("ghostBtn")
            baslik_btn.setStyleSheet("text-align:left; font-weight:700;")
            baslik_btn.clicked.connect(lambda checked, p=profil_adi: self._profil_ac_kapa(p))
            pv.addWidget(baslik_btn)

            if acik:
                ad_satir = QHBoxLayout()
                ad_satir.addWidget(QLabel("Tarife Adı:"))
                ad_input = QLineEdit(profil_adi)
                ad_satir.addWidget(ad_input, 2)
                ad_kaydet_btn = QPushButton("Adı Güncelle")
                ad_kaydet_btn.setObjectName("ghostBtn")
                ad_kaydet_btn.clicked.connect(
                    lambda checked, eski=profil_adi, inp=ad_input: self._profil_adini_guncelle(eski, inp)
                )
                ad_satir.addWidget(ad_kaydet_btn)
                pv.addLayout(ad_satir)

                self.profil_spinlar[profil_adi] = {}
                for kol_adi, ucret in kollar.items():
                    satir_kutu = QFrame()
                    satir_kutu.setStyleSheet(
                        f"QFrame {{ background-color:{RENK['panel_hover']}; "
                        f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
                        f"QFrame:hover {{ background-color:#E8E9ED; border-color:{RENK['accent']}; }}"
                    )
                    satir = QHBoxLayout(satir_kutu)
                    satir.setContentsMargins(12, 8, 12, 8)
                    kol_lbl = QLabel(kol_adi)
                    kol_lbl.setMinimumWidth(60)
                    kol_lbl.setStyleSheet(f"color:{RENK['text']}; font-weight:700; background:transparent;")
                    satir.addWidget(kol_lbl)
                    spin = SessizDoubleSpinBox()
                    spin.setRange(0, 99999)
                    spin.setDecimals(0)
                    spin.setSuffix(" ₺/saat")
                    spin.setValue(ucret)
                    satir.addWidget(spin)
                    sil_kutu = QFrame()
                    sil_kutu.setFixedWidth(60)
                    sil_kutu.setStyleSheet(
                        f"QFrame {{ background-color: transparent; "
                        f"border:1px solid {RENK['danger']}; border-radius:8px; }}"
                        f"QFrame:hover {{ background-color: rgba(255,77,109,0.08); }}"
                    )
                    sh2 = QHBoxLayout(sil_kutu)
                    sh2.setContentsMargins(0, 0, 0, 0)
                    sil_btn = QPushButton("Sil")
                    sil_btn.setStyleSheet(
                        f"background:transparent; border:none; color:{RENK['danger']}; "
                        f"font-weight:600; padding:10px 8px;"
                    )
                    sil_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    sil_btn.clicked.connect(
                        lambda checked, p=profil_adi, k=kol_adi: self._kol_sil(p, k)
                    )
                    sh2.addWidget(sil_btn)
                    satir.addWidget(sil_kutu)
                    pv.addWidget(satir_kutu)
                    self.profil_spinlar[profil_adi][kol_adi] = spin

                kol_ekle_btn = QPushButton("+ Kol Ekle")
                kol_ekle_btn.setObjectName("secenekBtn")
                kol_ekle_btn.setFixedWidth(160)
                kol_ekle_btn.clicked.connect(
                    lambda checked, p=profil_adi: self._kol_ekle_penceresi(p)
                )
                kol_ekle_satir = QHBoxLayout()
                kol_ekle_satir.addWidget(kol_ekle_btn)
                kol_ekle_satir.addStretch()
                # ÖNEMLİ: addLayout değil, gerçek bir QWidget'a sarıp addWidget
                # kullanıyoruz - çıplak addLayout, butonun üst kenarlığının
                # render sırasında yukarıdaki öğeyle çakışıp eksik/kesik
                # görünmesine sebep oluyordu.
                kol_ekle_wrap = QWidget()
                kol_ekle_wrap.setLayout(kol_ekle_satir)
                pv.addWidget(kol_ekle_wrap)

                ayirici = QFrame()
                ayirici.setFrameShape(QFrame.Shape.HLine)
                ayirici.setStyleSheet(f"background-color:{RENK['border_strong']}; max-height:1px; margin-top:8px; margin-bottom:4px;")
                pv.addWidget(ayirici)

                kaydet_kutu = QFrame()
                kaydet_kutu.setStyleSheet(
                    f"QFrame {{ background-color: rgba(108,77,246,0.12); "
                    f"border:1.5px solid {RENK['accent']}; border-radius:10px; }}"
                    f"QFrame:hover {{ background-color: rgba(108,77,246,0.20); }}"
                )
                kaydet_kutu.setFixedWidth(200)
                kh = QHBoxLayout(kaydet_kutu)
                kh.setContentsMargins(0, 0, 0, 0)
                kaydet_btn = QPushButton("Fiyatları Kaydet")
                kaydet_btn.setStyleSheet(
                    f"background:transparent; border:none; color:{RENK['accent']}; "
                    f"font-weight:700; padding:10px 18px;"
                )
                kaydet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                kaydet_btn.clicked.connect(lambda checked, p=profil_adi: self._profil_kaydet(p))
                kh.addWidget(kaydet_btn)
                kaydet_satir = QHBoxLayout()
                kaydet_satir.addWidget(kaydet_kutu)
                kaydet_satir.addStretch()
                kaydet_wrap = QWidget()
                kaydet_wrap.setLayout(kaydet_satir)
                pv.addWidget(kaydet_wrap)

                sil_profil_kutu = QFrame()
                sil_profil_kutu.setStyleSheet(
                    f"QFrame {{ background-color: transparent; "
                    f"border:1px solid {RENK['danger']}; border-radius:8px; }}"
                    f"QFrame:hover {{ background-color: rgba(255,77,109,0.08); }}"
                )
                sph = QHBoxLayout(sil_profil_kutu)
                sph.setContentsMargins(0, 0, 0, 0)
                sil_profil_btn = QPushButton("Bu Tarife Profilini Sil")
                sil_profil_btn.setStyleSheet(
                    f"background:transparent; border:none; color:{RENK['danger']}; "
                    f"font-weight:600; padding:10px 18px;"
                )
                sil_profil_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                sil_profil_btn.clicked.connect(lambda checked, p=profil_adi: self._profil_sil(p))
                sph.addWidget(sil_profil_btn)
                pv.addWidget(sil_profil_kutu)

            self.pkv.addWidget(profil_kutu)

    def _profil_ac_kapa(self, profil_adi: str):
        if profil_adi in self._acik_profiller:
            self._acik_profiller.discard(profil_adi)
        else:
            self._acik_profiller.add(profil_adi)
        self._profil_listesini_kur()

    def _tarife_ekle_penceresi(self):
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Tarife Ekle")
        d.setMinimumWidth(300)
        v = QVBoxLayout(d)
        v.addWidget(QLabel("Yeni Tarife Adı:"))
        ad_input = QLineEdit()
        v.addWidget(ad_input)
        ekle_btn = QPushButton("+ Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setDefault(True)
        ekle_btn.setAutoDefault(True)
        v.addWidget(ekle_btn)

        def _ekle():
            ad = ad_input.text().strip()
            if not ad:
                uyar(d, "Eksik Bilgi", "Tarife adı boş olamaz.")
                return
            if not self.state.tarife_profili_ekle(ad):
                uyar(d, "Aynı İsim", "Bu isimde bir tarife zaten var.")
                return
            self._acik_profiller.add(ad)
            self._profil_listesini_kur()
            self._masa_satirlarini_kur()
            d.accept()

        ekle_btn.clicked.connect(_ekle)
        d.exec()

    def _profil_adini_guncelle(self, eski_ad: str, input_widget: QLineEdit):
        yeni_ad = input_widget.text().strip()
        if not self.state.tarife_profili_yeniden_adlandir(eski_ad, yeni_ad):
            uyar(self, "Değiştirilemedi", "Bu isim boş olamaz ya da zaten kullanılıyor.")
            return
        if eski_ad in self._acik_profiller:
            self._acik_profiller.discard(eski_ad)
            self._acik_profiller.add(yeni_ad)
        self._profil_listesini_kur()
        self._masa_satirlarini_kur()
        bilgilendir(self, "Güncellendi", f"Tarife adı '{yeni_ad}' olarak güncellendi.")

    def _kol_ekle_penceresi(self, profil_adi: str):
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Kol Ekle")
        d.setMinimumWidth(300)
        v = QVBoxLayout(d)

        v.addWidget(QLabel("Kol Adı:"))
        ad_input = QLineEdit()
        v.addWidget(ad_input)

        # Sık kullanılan kol adları için hızlı seçim - yazmak zorunda kalmadan.
        # Hangisinin seçili olduğu belli olsun diye tıklanan buton grimsi/koyu
        # zeminle işaretlenir, diğerleri normale döner.
        hizli_satir = QHBoxLayout()
        hizli_butonlar: dict[str, QPushButton] = {}

        def _hizli_sec(secilen_ad: str):
            ad_input.setText(secilen_ad)
            for ad, btn in hizli_butonlar.items():
                if ad == secilen_ad:
                    btn.setStyleSheet(
                        f"background-color:{RENK['border_strong']}; color:{RENK['text']}; "
                        f"border:1.5px solid {RENK['text_muted']}; border-radius:8px; "
                        f"padding:10px 18px; font-weight:800;"
                    )
                else:
                    btn.setStyleSheet("")  # secenekBtn'in normal (global) stiline dön

        for hazir_ad in ["2 KOL", "3 KOL", "4 KOL"]:
            hizli_btn = QPushButton(hazir_ad)
            hizli_btn.setObjectName("secenekBtn")
            hizli_btn.setAutoDefault(False)
            hizli_btn.clicked.connect(lambda checked, a=hazir_ad: _hizli_sec(a))
            hizli_satir.addWidget(hizli_btn)
            hizli_butonlar[hazir_ad] = hizli_btn
        v.addLayout(hizli_satir)

        v.addWidget(QLabel("Saatlik Ücret:"))
        fiyat_input = SessizDoubleSpinBox()
        fiyat_input.setRange(0, 99999)
        fiyat_input.setDecimals(0)
        fiyat_input.setSuffix(" ₺/saat")
        v.addWidget(fiyat_input)

        ekle_btn = QPushButton("+ Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setDefault(True)
        ekle_btn.setAutoDefault(True)
        v.addWidget(ekle_btn)

        def _ekle():
            kol_adi = ad_input.text().strip()
            if not kol_adi:
                uyar(d, "Eksik Bilgi", "Kol adı boş olamaz.")
                return
            if kol_adi in self.state.tarife_profilleri[profil_adi]:
                uyar(d, "Aynı İsim", "Bu isimde bir kol zaten var.")
                return
            self.state.tarife_profilleri[profil_adi][kol_adi] = fiyat_input.value()
            self._profil_listesini_kur()
            d.accept()

        ekle_btn.clicked.connect(_ekle)
        d.exec()

    def _kol_sil(self, profil_adi: str, kol_adi: str):
        if len(self.state.tarife_profilleri[profil_adi]) <= 1:
            uyar(self, "Silinemez", "Bir tarifede en az bir kol kalmalı.")
            return
        del self.state.tarife_profilleri[profil_adi][kol_adi]
        self._profil_listesini_kur()

    def _profil_sil(self, profil_adi: str):
        cevap = soru_sor(self, "Tarifeyi Sil", f"'{profil_adi}' kalıcı olarak silinsin mi?")
        if cevap != QMessageBox.StandardButton.Yes:
            return
        basarili, mesaj = self.state.tarife_profili_sil(profil_adi)
        if not basarili:
            uyar(self, "Silinemedi", mesaj)
            return
        self._acik_profiller.discard(profil_adi)
        self._profil_listesini_kur()
        self._masa_satirlarini_kur()

    def _olustur_aciklama(self, metin: str) -> QLabel:
        lbl = QLabel(metin)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px;")
        return lbl

    def _profil_kaydet(self, profil_adi: str):
        for kol_adi, spin in self.profil_spinlar[profil_adi].items():
            self.state.tarife_profilleri[profil_adi][kol_adi] = spin.value()
        bilgilendir(
            self, "Kaydedildi",
            f"'{profil_adi}' fiyatları güncellendi. Bu tarifeyi kullanan masalarda "
            f"bundan sonraki açılış/kol geçişlerinde yeni fiyat geçerli olacak."
        )

    # ---------------- Masa bazlı tarife ataması ----------------
    def _masa_satirlarini_kur(self):
        self._masa_atama_baslik_guncelle()
        while self.mkv.count():
            item = self.mkv.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        self.combolar.clear()
        for masa in self.state.masalar:
            satir_kutu = QFrame()
            satir_kutu.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
                f"QFrame:hover {{ background-color:#E8E9ED; border-color:{RENK['accent']}; }}"
            )
            satir = QHBoxLayout(satir_kutu)
            satir.setContentsMargins(10, 6, 10, 6)
            ad_lbl = QLabel(masa.ad)
            ad_lbl.setMinimumWidth(140)
            ad_lbl.setStyleSheet(f"font-weight:700; color:{RENK['text']}; background:transparent;")
            satir.addWidget(ad_lbl)

            combo = SessizComboBox()
            combo.addItems(list(self.state.tarife_profilleri.keys()))
            mevcut = masa.varsayilan_tarife_profili or masa.aktif_tarife_profili or self.state.konsol_varsayilan_profil.get(
                masa.konsol_tipi
            ) or next(iter(self.state.tarife_profilleri), "")
            if mevcut in self.state.tarife_profilleri:
                combo.setCurrentText(mevcut)
            satir.addWidget(combo)
            self.combolar[masa.id] = combo

            # "Kaydet" butonu YOK arti_btnk - seçim değişince (activated, sadece
            # KULLANICI seçince tetiklenir, satır ilk kurulurken/programatik
            # setCurrentText çağrısında TETİKLENMEZ) otomatik kaydedilir.
            combo.activated.connect(lambda index, m=masa: self._kaydet(m))

            self.mkv.addWidget(satir_kutu)

    def _kaydet(self, masa: Masa):
        combo = self.combolar[masa.id]
        secilen = combo.currentText()
        masa.varsayilan_tarife_profili = secilen
        if masa.durum == MasaDurumu.BOS:
            masa.aktif_tarife_profili = secilen
        # ÖNEMLİ: sadece BU masaya değil, aynı gruba/konsol tipine ait
        # BUNDAN SONRA eklenecek YENİ masalara da bu tarife varsayılan olsun
        # diye grubun varsayılan profilini de güncelliyoruz. Aksi halde yeni
        # bir masa eklendiğinde konsol_varsayilan_profil boş kaldığı için
        # HER ZAMAN ilk tanımlı tarifeye düşüyordu (grup ne olursa olsun).
        self.state.konsol_varsayilan_profil[masa.konsol_tipi] = secilen


    def yenile(self):
        """Sekmeye her geçişte çağrılır - masa/grup listesini ve tarife
        atama listesini günceller."""
        self._satirlari_kur()
        self._grup_satirlarini_kur()
        if len(self.combolar) != len(self.state.masalar):
            self._masa_satirlarini_kur()

class UrunYonetDialog(OrtalanmisDialog):
    """Ürünler sayfasında bir ürüne tıklanınca açılır: Düzenle (Fiyat/Görsel) / Sil."""
    def __init__(self, state: AppState, kategori: str, urun_adi: str, parent=None):
        super().__init__(parent)
        self.state = state
        self.kategori = kategori
        self.urun_adi = urun_adi
        self.silindi = False
        self.setWindowTitle(urun_adi)
        self.setMinimumWidth(300)

        self.stack = QStackedWidget()
        ana = QVBoxLayout(self)
        ana.addWidget(self.stack)

        self.stack.addWidget(self._ana_menu())      # 0
        self.stack.addWidget(self._duzenle_menu())  # 1
        self.stack.addWidget(self._fiyat_form())    # 2

    def _urun(self) -> dict:
        return self.state.urun_katalogu[self.kategori][self.urun_adi]

    def _ana_menu(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(f"{self.urun_adi}  ·  {self._urun()['fiyat']:.0f} ₺"))

        duzenle_btn = QPushButton("✏️ Düzenle")
        duzenle_btn.setObjectName("secenekBtn")
        duzenle_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        v.addWidget(duzenle_btn)

        sil_btn = QPushButton(" Sil")
        sil_btn.setObjectName("dangerBtn")
        sil_btn.setIcon(cop_kutusu_ikonu(RENK["danger"], 18))
        sil_btn.clicked.connect(self._sil)
        v.addWidget(sil_btn)

        kapat = QPushButton("Kapat")
        kapat.setObjectName("ghostBtn")
        kapat.clicked.connect(self.reject)
        v.addWidget(kapat)
        return w

    def _duzenle_menu(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Ne değiştirmek istersiniz?"))

        fiyat_btn = QPushButton("💲 Fiyat Düzenle")
        fiyat_btn.setObjectName("secenekBtn")
        fiyat_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        v.addWidget(fiyat_btn)

        gorsel_btn = QPushButton("🖼 Görsel Düzenle")
        gorsel_btn.setObjectName("secenekBtn")
        gorsel_btn.clicked.connect(self._gorsel_sec)
        v.addWidget(gorsel_btn)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _fiyat_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Yeni Fiyat"))
        self.fiyat_spin = SessizDoubleSpinBox()
        self.fiyat_spin.setRange(0, 99999)
        self.fiyat_spin.setDecimals(0)
        self.fiyat_spin.setSuffix(" ₺")
        self.fiyat_spin.setValue(self._urun()["fiyat"])
        v.addWidget(self.fiyat_spin)

        kaydet = QPushButton("Kaydet")
        kaydet.setObjectName("primaryBtn")
        kaydet.clicked.connect(self._fiyat_kaydet)
        v.addWidget(kaydet)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        v.addWidget(geri)
        return w

    def _fiyat_kaydet(self):
        self._urun()["fiyat"] = self.fiyat_spin.value()
        self.accept()

    def _gorsel_sec(self):
        from PyQt6.QtWidgets import QFileDialog
        yol, _ = QFileDialog.getOpenFileName(
            self, "Görsel Seç", "", "Resimler (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if yol:
            # Seçilen dosyanın orijinal yolu DEĞİL, kalıcı 'gorseller'
            # klasörüne alınmış KOPYASININ yolu kaydedilir - aksi halde
            # kullanıcı masaüstündeki orijinal dosyayı silince/taşıyınca
            # uygulamadaki görsel de kaybolurdu (bildirilen hata).
            kalici_yol = gorseli_kalici_klasore_kopyala(yol)
            self._urun()["gorsel"] = kalici_yol if kalici_yol else yol
            self.accept()

    def _sil(self):
        cevap = soru_sor(self, "Ürünü Sil", f"'{self.urun_adi}' silinsin mi?")
        if cevap == QMessageBox.StandardButton.Yes:
            del self.state.urun_katalogu[self.kategori][self.urun_adi]
            self.silindi = True
            self.accept()


class UrunKarti(QFrame):
    """Ürünler sayfasındaki tek bir ürün karti_btn - görseli (varsa), adı, fiyatı.
    Tıklanınca dışarıya sinyal verir (Düzenle/Sil menüsü açması için)."""
    tiklandi = pyqtSignal()

    def __init__(self, ad: str, fiyat: float, gorsel: str | None, parent=None):
        super().__init__(parent)
        self.setObjectName("masaKart")
        self.setFixedSize(120, 110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 6)
        v.setSpacing(2)

        gorsel_lbl = QLabel()
        gorsel_lbl.setFixedHeight(40)
        gorsel_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if gorsel:
            from PyQt6.QtGui import QPixmap
            pix = QPixmap(gorsel)
            if not pix.isNull():
                gorsel_lbl.setPixmap(pix.scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation))
            else:
                gorsel_lbl.setText("📦")
                gorsel_lbl.setStyleSheet("font-size:24px;")
        else:
            gorsel_lbl.setText("📦")
            gorsel_lbl.setStyleSheet("font-size:24px;")
        v.addWidget(gorsel_lbl)

        ad_lbl = QLabel(ad)
        ad_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ad_lbl.setWordWrap(True)
        ad_lbl.setStyleSheet("font-size:12px; font-weight:600;")
        v.addWidget(ad_lbl)

        fiyat_lbl = QLabel(f"{fiyat:.0f} ₺")
        fiyat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fiyat_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['accent']};")
        v.addWidget(fiyat_lbl)

    def mousePressEvent(self, event):
        self.tiklandi.emit()
        super().mousePressEvent(event)


class UrunlerView(QWidget):
    """Ürünler sayfası: her kategori tıklanınca açılıp kapanan bir başlık (akordeon),
    altında ürün kartları (görsel + ad + fiyat). Bir karta tıklayınca Düzenle/Sil menüsü açılır."""
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self._acik_kategoriler: set[str] = set()

        self.disv = QVBoxLayout(self)
        self.disv.setContentsMargins(28, 24, 28, 24)
        self.disv.setSpacing(14)
        baslik = QLabel("Ürünler")
        baslik.setObjectName("pageTitle")
        self.disv.addWidget(baslik)

        # --- Kategori Ekle / Ürün Ekle: sayfada sürekli açık durmasın, tıklayınca
        # küçük bir pencere açılsın ---
        ust_buton_satir = QHBoxLayout()
        kategori_ekle_btn = QPushButton("+ Kategori Ekle")
        kategori_ekle_btn.setObjectName("secenekBtn")
        kategori_ekle_btn.clicked.connect(self._kategori_ekle_penceresi)
        ust_buton_satir.addWidget(kategori_ekle_btn)
        urun_ekle_btn = QPushButton("+ Ürün Ekle")
        urun_ekle_btn.setObjectName("secenekBtn")
        urun_ekle_btn.clicked.connect(self._urun_ekle_penceresi)
        ust_buton_satir.addWidget(urun_ekle_btn)
        ust_buton_satir.addStretch()
        self.disv.addLayout(ust_buton_satir)

        self.liste_alani = QVBoxLayout()
        self.disv.addLayout(self.liste_alani)
        self.disv.addStretch()

        self._listeyi_kur()

    def _hesapla_sutun(self) -> int:
        """Mevcut pencere genişliğine kaç ürün karti_btnnın yan yana sığacağını
        hesaplar - pencere büyüyüp küçülünce otomatik uyum sağlar, satır
        dolmadan erken alt satıra geçmez (eskiden sabit 6'ydı)."""
        kart_birim = 120 + 10  # UrunKarti genişliği + ızgara boşluğu
        kenar_boslugu = 28 + 28 + 32 + 32  # sayfa + kart iç boşlukları
        kullanilabilir = max(self.width() - kenar_boslugu, kart_birim)
        return max(1, kullanilabilir // kart_birim)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        yeni_deger = self._hesapla_sutun()
        if yeni_deger != getattr(self, "_mevcut_sutun", None):
            self._mevcut_sutun = yeni_deger
            self._listeyi_kur()

    def _kategori_ekle_penceresi(self):
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Kategori Ekle")
        d.setMinimumWidth(300)
        v = QVBoxLayout(d)
        v.addWidget(QLabel("Kategori Adı:"))
        ad_input = QLineEdit()
        v.addWidget(ad_input)
        ekle_btn = QPushButton("+ Ekle")
        ekle_btn.setObjectName("primaryBtn")
        v.addWidget(ekle_btn)

        def _ekle():
            ad = ad_input.text().strip()
            if not ad:
                uyar(d, "Eksik Bilgi", "Kategori adı boş olamaz.")
                return
            if ad in self.state.urun_katalogu:
                uyar(d, "Aynı İsim", "Bu kategori zaten var.")
                return
            self.state.urun_katalogu[ad] = {}
            self._acik_kategoriler.add(ad)
            self._listeyi_kur()
            d.accept()

        ekle_btn.clicked.connect(_ekle)
        d.exec()

    def _urun_ekle_penceresi(self):
        if not self.state.urun_katalogu:
            bilgilendir(self, "Önce Kategori Ekleyin", "Ürün eklemeden önce en az bir kategori oluşturmalısınız.")
            return
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Ürün Ekle")
        d.setMinimumWidth(340)
        v = QVBoxLayout(d)
        v.setSpacing(10)

        ad_baslik = QLabel("🏷️  Ürün Adı")
        ad_baslik.setStyleSheet(f"font-weight:700; color:{RENK['text']};")
        v.addWidget(ad_baslik)
        ad_input = QLineEdit()
        v.addWidget(ad_input)

        kategori_baslik = QLabel("📂  Kategori")
        kategori_baslik.setStyleSheet(f"font-weight:700; color:{RENK['text']};")
        v.addWidget(kategori_baslik)
        kategori_combo = TamamlamaKutusu(list(self.state.urun_katalogu.keys()))
        v.addWidget(kategori_combo)

        fiyat_baslik = QLabel("💰  Fiyat")
        fiyat_baslik.setStyleSheet(f"font-weight:700; color:{RENK['text']};")
        v.addWidget(fiyat_baslik)
        fiyat_input = SessizDoubleSpinBox()
        fiyat_input.setRange(0, 99999)
        fiyat_input.setDecimals(0)
        fiyat_input.setSuffix(" ₺")
        v.addWidget(fiyat_input)

        ekle_btn = QPushButton("+ Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setDefault(True)
        ekle_btn.setAutoDefault(True)
        v.addWidget(ekle_btn)

        def _ekle():
            ad = ad_input.text().strip()
            kategori = kategori_combo.text().strip()
            if not ad or not kategori:
                uyar(d, "Eksik Bilgi", "Ürün adı ve kategori boş olamaz.")
                return
            if ad in self.state.urun_katalogu.get(kategori, {}):
                uyar(d, "Aynı İsim", "Bu kategoride aynı isimde ürün zaten var.")
                return
            self.state.urun_katalogu.setdefault(kategori, {})[ad] = {"fiyat": fiyat_input.value(), "gorsel": None}
            self._acik_kategoriler.add(kategori)
            self._listeyi_kur()
            d.accept()

        ekle_btn.clicked.connect(_ekle)
        d.exec()

    def _listeyi_kur(self):
        while self.liste_alani.count():
            item = self.liste_alani.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        if not self.state.urun_katalogu:
            bos_lbl = QLabel("Henüz kayıtlı kategori/ürün yok - üstteki alanlardan ekleyin.")
            bos_lbl.setObjectName("pageSubtitle")
            self.liste_alani.addWidget(bos_lbl)
            return

        for kategori, urunler in self.state.urun_katalogu.items():
            kutu = QFrame()
            kutu.setObjectName("masaKart")
            kv = QVBoxLayout(kutu)

            acik = kategori in self._acik_kategoriler
            baslik_satir = QHBoxLayout()
            baslik_btn = QPushButton(f"{'▾' if acik else '▸'}  {kategori}  ({len(urunler)})")
            baslik_btn.setObjectName("ghostBtn")
            baslik_btn.setStyleSheet("text-align:left; font-weight:700;")
            baslik_btn.clicked.connect(lambda checked, k=kategori: self._kategori_ac_kapa(k))
            baslik_satir.addWidget(baslik_btn, 1)
            kategori_sil_btn = cop_butonu_yap(QPushButton(), 34, 22)
            kategori_sil_btn.clicked.connect(lambda checked, k=kategori: self._kategori_sil(k))
            baslik_satir.addWidget(kategori_sil_btn)
            kv.addLayout(baslik_satir)

            if acik:
                if not urunler:
                    bos_lbl = QLabel("Bu kategoride henüz ürün yok - üstteki 'Ürün Ekle' alanından ekleyin.")
                    bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px; padding:6px 0;")
                    kv.addWidget(bos_lbl)
                else:
                    grid_widget = QWidget()
                    grid = QGridLayout(grid_widget)
                    grid.setSpacing(10)
                    grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    SUTUN = self._hesapla_sutun()
                    for i, (urun_adi, veri) in enumerate(urunler.items()):
                        kart = UrunKarti(urun_adi, veri["fiyat"], veri.get("gorsel"))
                        kart.tiklandi.connect(lambda k=kategori, a=urun_adi: self._urune_tiklandi(k, a))
                        grid.addWidget(kart, i // SUTUN, i % SUTUN)
                    kv.addWidget(grid_widget)

            self.liste_alani.addWidget(kutu)

    def _kategori_ac_kapa(self, kategori: str):
        if kategori in self._acik_kategoriler:
            self._acik_kategoriler.discard(kategori)
        else:
            self._acik_kategoriler.add(kategori)
        self._listeyi_kur()

    def _kategori_sil(self, kategori: str):
        urun_sayisi = len(self.state.urun_katalogu.get(kategori, {}))
        mesaj = f"'{kategori}' kategorisi"
        if urun_sayisi > 0:
            mesaj += f" ve içindeki {urun_sayisi} ürün"
        mesaj += " kalıcı olarak silinsin mi?"
        cevap = soru_sor(self, "Kategoriyi Sil", mesaj)
        if cevap == QMessageBox.StandardButton.Yes:
            self.state.urun_katalogu.pop(kategori, None)
            self._acik_kategoriler.discard(kategori)
            self._listeyi_kur()

    def _urune_tiklandi(self, kategori, urun_adi):
        dlg = UrunYonetDialog(self.state, kategori, urun_adi, self)
        dlg.exec()
        self._listeyi_kur()


class _GiderAvansDialog(OrtalanmisDialog):
    """Gider Ekle / Avans Ekle / Düzenle için ortak küçük form (açıklama + tutar)."""
    def __init__(self, baslik: str, mevcut_aciklama: str = "", mevcut_tutar: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(baslik)
        self.setMinimumWidth(300)
        self.sonuc: dict | None = None
        # ÇİFT GÜVENCE: uygulama genelindeki tema bir sebeple bu pencereye
        # ulaşmasa bile (Windows karanlık mod senkronizasyon garipliği gibi),
        # bu pencere KENDİ stilini doğrudan taşır - asla karanlık/görünmez
        # buton içermez. (Butonları da eklemeyi unutmuştum - "Kaydet"
        # butonunun beyaz zemin üstünde beyaz yazı gibi görünmez olmasının
        # sebebi buydu.)
        self.setStyleSheet(f"""
            QDialog {{ background-color:{RENK['panel']}; }}
            QLabel {{ color:{RENK['text']}; background:transparent; }}
            QLineEdit {{ background-color:#FFFFFF; color:{RENK['text']};
                border:1px solid {RENK['border_strong']}; border-radius:6px; padding:8px; }}
            QPushButton#primaryBtn {{ background-color:rgba(108,77,246,0.12); color:{RENK['accent']};
                border-width:1.5px; border-style:solid; border-color:{RENK['accent']};
                border-radius:10px; padding:10px 18px; font-weight:700; }}
            QPushButton#primaryBtn:hover {{ background-color:rgba(108,77,246,0.20); }}
            QPushButton#ghostBtn {{ background-color:{RENK['panel_hover']}; color:{RENK['text']};
                border-radius:8px; padding:10px 18px;
                border-width:1px; border-style:solid; border-color:{RENK['border']}; }}
        """)

        v = QVBoxLayout(self)
        v.addWidget(QLabel("Açıklama:"))
        self.aciklama_input = QLineEdit(mevcut_aciklama)
        v.addWidget(self.aciklama_input)

        v.addWidget(QLabel("Tutar:"))
        self.tutar_input = SessizDoubleSpinBox()
        self.tutar_input.setRange(0, 999999)
        self.tutar_input.setDecimals(0)
        self.tutar_input.setSuffix(" ₺")
        self.tutar_input.setValue(mevcut_tutar)
        v.addWidget(self.tutar_input)

        kaydet_btn = QPushButton("Kaydet")
        kaydet_btn.setObjectName("primaryBtn")
        kaydet_btn.setDefault(True)
        kaydet_btn.setAutoDefault(True)
        kaydet_btn.clicked.connect(self._kaydet)
        v.addWidget(kaydet_btn)

        iptal_btn = QPushButton("Vazgeç")
        iptal_btn.setObjectName("ghostBtn")
        iptal_btn.setAutoDefault(False)
        iptal_btn.clicked.connect(self.reject)
        v.addWidget(iptal_btn)

    def _kaydet(self):
        aciklama = self.aciklama_input.text().strip()
        if not aciklama:
            uyar(self, "Eksik Bilgi", "Açıklama boş olamaz.")
            return
        self.sonuc = {"aciklama": aciklama, "tutar": self.tutar_input.value()}
        self.accept()


class AnlikSalonSayfasi(QWidget):
    """Kasa > Anlık Salon: şu an açık tüm masaların güncel tutar toplamı."""
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        v = QVBoxLayout(self)
        v.setSpacing(14)

        # --- Hero kart: titanyum gri zemin + neon yeşil rakam - koyu/lacivert
        # yerine daha zarif, gerçek "premium" bir gri his. Tam sayfa genişliği
        # yerine kompakt bir çubuk (sabit genişlik). ---
        ust_kutu = QFrame()
        ust_kutu.setFixedWidth(360)
        ust_kutu.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 #E9EAEE, stop:1 #DADCE2); border-radius:16px; }"
        )
        ukv = QVBoxLayout(ust_kutu)
        ukv.setContentsMargins(24, 20, 24, 20)
        baslik = QLabel("💰  ŞU AN SALON TOPLAMI")
        baslik.setStyleSheet("color:#6B6F7A; font-size:11px; font-weight:700; background:transparent; border:none; letter-spacing:2px;")
        ukv.addWidget(baslik)
        self.toplam_lbl = QLabel("0 ₺")
        self.toplam_lbl.setStyleSheet("font-size:40px; font-weight:800; color:#00E676; background:transparent; border:none;")
        ukv.addWidget(self.toplam_lbl)
        aciklama = QLabel("Henüz ödemesi alınmamış, oynanmaya devam eden tüm masaların güncel toplamı - bu bir ciro değil, anlık bir gösterge.")
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("color:#8A8FA3; font-size:11px; background:transparent; border:none;")
        ukv.addWidget(aciklama)
        ust_satir = QHBoxLayout()
        ust_satir.addWidget(ust_kutu)
        ust_satir.addStretch()
        v.addLayout(ust_satir)

        baslik_lbl = QLabel("Açık Masalar")
        baslik_lbl.setStyleSheet(f"font-size:14px; font-weight:700; color:{RENK['text']}; margin-top:4px;")
        v.addWidget(baslik_lbl)

        self.liste_v = QVBoxLayout()
        self.liste_v.setSpacing(8)
        v.addLayout(self.liste_v)
        v.addStretch()

        self.yenile()

    def yenile(self):
        while self.liste_v.count():
            item = self.liste_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        aktifler = [m for m in self.state.masalar if m.durum != MasaDurumu.BOS]
        toplam = sum(m.genel_toplam() for m in aktifler)
        self.toplam_lbl.setText(f"{toplam:.0f} ₺")

        if not aktifler:
            bos_lbl = QLabel("Şu an açık masa yok.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
            self.liste_v.addWidget(bos_lbl)
            return

        for m in sorted(aktifler, key=lambda x: -x.genel_toplam()):
            renk = durum_rengi(m.durum.value)
            zemin = durum_zemin_rengi(m.durum.value)
            satir = QFrame()
            satir.setStyleSheet(
                f"QFrame {{ background-color:{zemin}; border-left:4px solid {renk}; "
                f"border-radius:10px; }}"
            )
            sh = QHBoxLayout(satir)
            sh.setContentsMargins(14, 10, 14, 10)
            ad_lbl = QLabel(f"🎮  {m.ad}")
            ad_lbl.setStyleSheet("font-size:13px; font-weight:700; background:transparent; border:none;")
            sh.addWidget(ad_lbl)
            durum_lbl = QLabel(m.durum.value)
            durum_lbl.setStyleSheet(
                f"background-color:rgba(255,255,255,0.7); color:{renk}; font-size:10px; "
                f"font-weight:800; padding:2px 8px; border-radius:8px; border:none;"
            )
            sh.addWidget(durum_lbl)
            sh.addStretch()
            tutar_lbl = QLabel(f"{m.genel_toplam():.0f} ₺")
            tutar_lbl.setStyleSheet(f"font-size:15px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
            sh.addWidget(tutar_lbl)
            self.liste_v.addWidget(satir)


class GunSonuSayfasi(QWidget):
    """Kasa > Gün Sonu: 06:00-05:59 iş günü mantığıyla tam gün raporu + Gider/Avans
    Ekle. Aynı ekran, Genel'den bir tarihe tıklandığında da (gunu_goster ile)
    o günün raporunu göstermek için yeniden kullanılıyor."""
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.goruntulenen_gun: date = is_gunu(datetime.now())

        v = QVBoxLayout(self)
        v.setSpacing(12)

        # --- Üstte kasa araçları: Para Sayma + Hesap Makinesi (gün sonunda
        # kasayı elle saymayı/hesaplamayı kolaylaştırır, veriye dokunmaz) ---
        arac_satir = QHBoxLayout()
        para_say_btn = QPushButton("💵  Para Say")
        para_say_btn.setObjectName("secenekBtn")
        para_say_btn.setAutoDefault(False)
        para_say_btn.clicked.connect(self._para_say)
        arac_satir.addWidget(para_say_btn)
        hesap_btn = QPushButton("🧮  Hesap Makinesi")
        hesap_btn.setObjectName("secenekBtn")
        hesap_btn.setAutoDefault(False)
        hesap_btn.clicked.connect(self._hesap_makinesi)
        arac_satir.addWidget(hesap_btn)
        arac_satir.addStretch()
        v.addLayout(arac_satir)

        gun_satir = QHBoxLayout()
        onceki_btn = QPushButton("◀ Önceki Gün")
        onceki_btn.setObjectName("ghostBtn")
        onceki_btn.clicked.connect(self._onceki_gun)
        gun_satir.addWidget(onceki_btn)

        gun_satir.addStretch()

        bugun_btn = QPushButton("Bugün")
        bugun_btn.setObjectName("primaryBtn")
        # Bazı durumlarda global QSS bu pencereye tam ulaşmayabiliyor - yerel
        # stil ile beyaz yazının HER ZAMAN mor zemin üzerinde görünmesini
        # garantiliyoruz (aksi halde metin görünmez oluyordu).
        bugun_btn.setStyleSheet(
            f"background-color:rgba(108,77,246,0.12); color:{RENK['accent']}; "
            f"border-width:1.5px; border-style:solid; border-color:{RENK['accent']}; "
            f"border-radius:10px; padding:10px 18px; font-weight:700;"
        )
        bugun_btn.clicked.connect(self._bugune_don)
        gun_satir.addWidget(bugun_btn)

        gun_satir.addStretch()

        sonraki_btn = QPushButton("Sonraki Gün ▶")
        sonraki_btn.setObjectName("ghostBtn")
        sonraki_btn.clicked.connect(self._sonraki_gun)
        gun_satir.addWidget(sonraki_btn)
        v.addLayout(gun_satir)

        self.gun_baslik_lbl = QLabel()
        self.gun_baslik_lbl.setStyleSheet(f"font-size:16px; font-weight:700; color:{RENK['text']}; background:transparent;")
        self.gun_baslik_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.gun_baslik_lbl)

        gun_aralik_lbl = QLabel()
        gun_aralik_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gun_aralik_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px;")
        self.gun_aralik_lbl = gun_aralik_lbl
        v.addWidget(gun_aralik_lbl)

        # --- özet kartları (ikonlu) ---
        ozet_satir = QHBoxLayout()
        ozet_satir.setSpacing(12)
        self.ciro_lbl = self._ozet_kart(ozet_satir, "💰", "CİRO", RENK["accent2"])
        self.gider_lbl = self._ozet_kart(ozet_satir, "📉", "GİDER", RENK["danger"])
        self.net_lbl = self._ozet_kart(ozet_satir, "📊", "NET", RENK["accent"])
        # _yenile() her çağrıldığında güncellenir - kart tıklanınca hangi
        # günün masa dışı ürün detayının gösterileceğini bilmek için.
        self._son_masa_disi_urunler: list = []
        self._son_masa_disi_toplam: float = 0.0
        self.masa_disi_kutu, self.masa_disi_lbl = self._ozet_kart_olustur("🛍️", "MASA DIŞI SATIŞ", RENK["text"])
        self.masa_disi_kutu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.masa_disi_kutu.mousePressEvent = lambda event: self._masa_disi_urunleri_goster(
            self._son_masa_disi_urunler, self._son_masa_disi_toplam
        )
        ozet_satir.addWidget(self.masa_disi_kutu)
        v.addLayout(ozet_satir)

        # --- üç bölüm YAN YANA: ödeme yöntemleri / satılan ürünler / masa bazlı ---
        uc_sutun = QHBoxLayout()
        uc_sutun.setSpacing(12)

        self.odeme_kutu = QFrame()
        self.odeme_kutu.setObjectName("masaKart")
        self.odeme_v = QVBoxLayout(self.odeme_kutu)
        self.odeme_v.setSpacing(8)
        self.odeme_v.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.urun_kutu = QFrame()
        self.urun_kutu.setObjectName("masaKart")
        self.urun_v = QVBoxLayout(self.urun_kutu)
        self.urun_v.setSpacing(6)
        self.urun_v.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.masa_kutu = QFrame()
        self.masa_kutu.setObjectName("masaKart")
        self.masa_v = QVBoxLayout(self.masa_kutu)
        self.masa_v.setSpacing(6)
        self.masa_v.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ÖNEMLİ: her sütun AlignTop ile ekleniyor - aksi halde QHBoxLayout
        # üç sütunu da EN UZUN olanın boyuna eşitliyordu (örn. "Satılan
        # Ürünler" listesi uzayınca "Ödeme Yöntemi Dağılımı" kutusu da
        # gerilip çirkin/boşluklu görünüyordu - bildirilen hata). AlignTop
        # ile her kutu SADECE kendi içeriğinin gerektirdiği boyu kaplar.
        # SOL SÜTUN: Ödeme Yöntemi Dağılımı + Gider/Avans Ekle butonları +
        # gider/avans geçmişi HEP BİRLİKTE, ödeme kutusunun HEMEN ALTINDA.
        # Eskiden bu butonlar/geçmişler üç sütunun TAMAMININ altına
        # ekleniyordu; "Satılan Ürünler" ya da "Masa Bazlı" listesi uzadıkça
        # gider/avans da aşağı itiliyordu (bildirilen hata). Artık o iki
        # sütun kendi başına aşağı uzar, gider/avans yerinde kalır.
        sol_sutun = QWidget()
        sol_sutun.setStyleSheet("background:transparent;")
        sol_v = QVBoxLayout(sol_sutun)
        sol_v.setContentsMargins(0, 0, 0, 0)
        sol_v.setSpacing(12)
        sol_v.setAlignment(Qt.AlignmentFlag.AlignTop)
        sol_v.addWidget(self.odeme_kutu)

        # --- GİDER karti_btn: başlık + "+" butonu + o günün gider kayıtları tek
        # kutuda (eskiden ayrı "Gider Ekle" butonu + ayrı "Gider Geçmişi"
        # kutusu vardı). Arama arti_btnk Kasa > Genel'de. ---
        self.gider_gecmisi_kutu = QFrame()
        self.gider_gecmisi_kutu.setObjectName("masaKart")
        self.gider_gecmisi_v = QVBoxLayout(self.gider_gecmisi_kutu)
        sol_v.addWidget(self.gider_gecmisi_kutu)

        # --- AVANS karti_btn: aynı yapı (başlık + "+" + o günün avansları) ---
        self.avans_gecmisi_kutu = QFrame()
        self.avans_gecmisi_kutu.setObjectName("masaKart")
        self.avans_gecmisi_v = QVBoxLayout(self.avans_gecmisi_kutu)
        sol_v.addWidget(self.avans_gecmisi_kutu)

        uc_sutun.addWidget(sol_sutun, 1, Qt.AlignmentFlag.AlignTop)
        uc_sutun.addWidget(self.urun_kutu, 1, Qt.AlignmentFlag.AlignTop)
        uc_sutun.addWidget(self.masa_kutu, 1, Qt.AlignmentFlag.AlignTop)

        v.addLayout(uc_sutun)

        v.addStretch()
        self._yenile()

    def _para_say(self):
        ParaSaymaDialog(self).exec()

    def _hesap_makinesi(self):
        HesapMakinesiDialog(self).exec()

    def _ozet_kart(self, satir: QHBoxLayout, ikon: str, baslik: str, renk: str) -> QLabel:
        kutu, deger_lbl = self._ozet_kart_olustur(ikon, baslik, renk)
        satir.addWidget(kutu)
        return deger_lbl

    def _ozet_kart_olustur(self, ikon: str, baslik: str, renk: str) -> tuple[QFrame, QLabel]:
        kutu = QFrame()
        kutu.setObjectName("masaKart")
        kv = QVBoxLayout(kutu)
        kv.setSpacing(4)
        ust = QHBoxLayout()
        ikon_lbl = QLabel(ikon)
        ikon_lbl.setStyleSheet("font-size:16px;")
        ust.addWidget(ikon_lbl)
        b = QLabel(baslik)
        b.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px; font-weight:700; letter-spacing:1px;")
        ust.addWidget(b)
        ust.addStretch()
        kv.addLayout(ust)
        deger_lbl = QLabel("0 ₺")
        deger_lbl.setStyleSheet(f"font-size:24px; font-weight:800; color:{renk};")
        kv.addWidget(deger_lbl)
        return kutu, deger_lbl

    def gunu_goster(self, gun: date):
        self.goruntulenen_gun = gun
        self._yenile()

    def _onceki_gun(self):
        self.goruntulenen_gun -= timedelta(days=1)
        self._yenile()

    def _sonraki_gun(self):
        self.goruntulenen_gun += timedelta(days=1)
        self._yenile()

    def _bugune_don(self):
        self.goruntulenen_gun = is_gunu(datetime.now())
        self._yenile()

    _son_imza = None

    def _yenile(self):
        gun = self.goruntulenen_gun
        ozet = self.state.gun_ozet(gun)

        # KRİTİK: ana pencere bu sayfayı her 250ms'de çağırıyor. Veri
        # DEĞİŞMEDİYSE satırları yeniden kurmuyoruz - aksi halde fare
        # kalem/çöp kutusunun üstündeyken düğmeler yok edilip yeniden
        # yaratılıyor, imleç titriyor ve ilk tıklama boşa gidiyordu.
        imza = repr((gun, ozet))
        if imza == self._son_imza:
            return
        self._son_imza = imza

        bugun_mu = " (Bugün)" if gun == is_gunu(datetime.now()) else ""
        self.gun_baslik_lbl.setText(gun.strftime("%d.%m.%Y") + bugun_mu)
        baslangic = datetime(gun.year, gun.month, gun.day, 6, 0)
        bitis = baslangic + timedelta(hours=23, minutes=59)
        self.gun_aralik_lbl.setText(
            f"{baslangic.strftime('%d.%m.%Y %H:%M')} - {bitis.strftime('%d.%m.%Y %H:%M')} arası"
        )

        self.ciro_lbl.setText(f"{ozet['ciro']:.0f} ₺")
        self.gider_lbl.setText(f"{ozet['gider']:.0f} ₺")
        self.net_lbl.setText(f"{ozet['net']:.0f} ₺")

        # masa bazlı
        while self.masa_v.count():
            item = self.masa_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        baslik_lbl = QLabel("🎮  Masa Bazlı Ciro")
        baslik_lbl.setStyleSheet(f"font-weight:800; font-size:13px; color:{RENK['text']};")
        self.masa_v.addWidget(baslik_lbl)
        if ozet["toplam_indirim"] > 0:
            indirim_lbl = QLabel(f"💸 Bugün yapılan toplam indirim: {ozet['toplam_indirim']:.0f} ₺")
            indirim_lbl.setStyleSheet(f"color:{RENK['danger']}; font-size:10px; font-weight:700;")
            self.masa_v.addWidget(indirim_lbl)
        if ozet["en_cok_kazandiran"]:
            en_cok_ad, en_cok_tutar = ozet["en_cok_kazandiran"]
            en_cok_lbl = QLabel(f"🏆 En çok kazandıran: {en_cok_ad} ({en_cok_tutar:.0f} ₺)")
            en_cok_lbl.setStyleSheet(f"color:{RENK['accent']}; font-size:11px; font-weight:700;")
            en_cok_lbl.setWordWrap(True)
            self.masa_v.addWidget(en_cok_lbl)
        if not ozet["masa_bazli"]:
            self.masa_v.addWidget(self._bos_etiket("Bu gün satış yok."))
        for ad, veri in ozet["masa_bazli"]:
            kutu = QFrame()
            kutu.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
            )
            kv2 = QVBoxLayout(kutu)
            kv2.setContentsMargins(12, 8, 12, 8)
            kv2.setSpacing(2)
            ust = QHBoxLayout()
            ad_lbl = QLabel(ad)
            ad_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['text']}; background:transparent;")
            ust.addWidget(ad_lbl)
            ust.addStretch()
            tutar_lbl = QLabel(f"{veri['toplam']:.0f} ₺")
            tutar_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['accent']}; background:transparent;")
            ust.addWidget(tutar_lbl)
            kv2.addLayout(ust)
            detay_lbl = QLabel(f"🎮 Masa: {veri['masa_ucreti']:.0f} ₺   🛍️ Market: {veri['urun_geliri']:.0f} ₺")
            detay_lbl.setStyleSheet(f"font-size:11px; font-weight:700; color:{RENK['text']}; background:transparent;")
            kv2.addWidget(detay_lbl)
            self.masa_v.addWidget(kutu)

        # ürün bazlı
        while self.urun_v.count():
            item = self.urun_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        u_baslik = QLabel(f"🛒  Satılan Ürünler  —  {ozet['toplam_urun_geliri']:.0f} ₺")
        u_baslik.setStyleSheet(f"font-weight:800; font-size:13px; color:{RENK['text']};")
        self.urun_v.addWidget(u_baslik)
        if not ozet["urun_bazli"]:
            self.urun_v.addWidget(self._bos_etiket("Bu gün ürün satışı yok."))
        for ad, veri in ozet["urun_bazli"]:
            kutu = QFrame()
            kutu.setMaximumWidth(320)
            kutu.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
            )
            kh = QHBoxLayout(kutu)
            kh.setContentsMargins(12, 8, 12, 8)
            ad_lbl = QLabel(f"🥤  {ad}  ×{veri['adet']}")
            ad_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text_muted']}; background:transparent;")
            kh.addWidget(ad_lbl)
            kh.addStretch()
            tutar_lbl = QLabel(f"{veri['tutar']:.0f} ₺")
            tutar_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['text']}; background:transparent;")
            kh.addWidget(tutar_lbl)
            # ÖNEMLİ: addLayout değil addWidget - aynı "hayalet metin" hatasını
            # burada da önlemek için kutu bir QFrame (gerçek widget).
            self.urun_v.addWidget(kutu)

        # Masa Dışı Alışveriş (Anasayfa > Alışveriş'ten yapılan masasız satış)
        # - "Satılan Ürünler" karti_btnna KARIŞMIYOR (o kart sadece gerçek
        # masalardaki ürün satışlarını gösterir) - kafa karışıklığına sebep
        # oluyordu ("Satılan Ürünler"in İÇİNDE ayrı bir toplam gibi
        # duruyordu). Artık üstteki özet satırında KENDİ ayrı karti_btnnda.
        self._son_masa_disi_urunler = ozet["masa_disi_urun_bazli"]
        self._son_masa_disi_toplam = ozet["masa_disi_satis_toplami"]
        self.masa_disi_lbl.setText(f"{ozet['masa_disi_satis_toplami']:.0f} ₺")

        # ödeme yöntemleri - her biri KENDİ küçük çerçeveli çipinde, ikonlu,
        # koyu ve büyük puntolu tutar
        while self.odeme_v.count():
            item = self.odeme_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        o_baslik = QLabel("💳  Ödeme Yöntemi Dağılımı")
        o_baslik.setStyleSheet(f"font-weight:800; font-size:13px; color:{RENK['text']};")
        self.odeme_v.addWidget(o_baslik)

        ODEME_IKONLARI = {"NAKİT": "💵", "KART": "💳", "İBAN": "🏦", "BORÇ": "📝"}
        for yontem in ["NAKİT", "KART", "İBAN", "BORÇ"]:
            tutar = ozet["odeme_bazli"].get(yontem, 0.0)
            cip = QFrame()
            cip.setMaximumWidth(260)
            cip.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
            )
            ch = QHBoxLayout(cip)
            ch.setContentsMargins(12, 8, 12, 8)
            ikon_ad = QLabel(f"{ODEME_IKONLARI[yontem]}  {yontem}")
            ikon_ad.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text_muted']}; background:transparent;")
            ch.addWidget(ikon_ad)
            ch.addStretch()
            tutar_lbl = QLabel(f"{tutar:.0f} ₺")
            tutar_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # SABİT genişlik: 100 TL ile 2500 TL aynı büyüklükteki kutuya
            # girsin - eskiden etiket metne göre doğal genişlikte olduğu
            # için rakam sayısı arttıkça kutu görsel olarak "büyüyormuş"
            # gibi duruyordu (bildirilen hata).
            tutar_lbl.setFixedWidth(76)
            tutar_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['text']}; background:transparent;")
            ch.addWidget(tutar_lbl)
            self.odeme_v.addWidget(cip)

        if ozet["borc_tahsilati_toplam"] > 0:
            tahsilat_lbl = QLabel(
                f"(+ bu gün tahsil edilen eski borç: {ozet['borc_tahsilati_toplam']:.0f} ₺ - ciroya dahil değil)"
            )
            tahsilat_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:10px; margin-top:4px;")
            tahsilat_lbl.setWordWrap(True)
            self.odeme_v.addWidget(tahsilat_lbl)

        # gider geçmişi - arama kutusu doluysa TÜM günlerde ara, boşsa sadece bu günü göster
        while self.gider_gecmisi_v.count():
            item = self.gider_gecmisi_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        self.gider_gecmisi_v.addWidget(
            self._baslik_ekle_satiri("💸  Gider", self._gider_ekle, RENK["danger"], "Gider ekle")
        )
        if not ozet["giderler"]:
            self.gider_gecmisi_v.addWidget(self._bos_etiket("Bu gün gider eklenmemiş."))
        for gider in ozet["giderler"]:
            self._gider_satiri_ekle(gider, tarih_goster=False)

        # avans geçmişi
        while self.avans_gecmisi_v.count():
            item = self.avans_gecmisi_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        self.avans_gecmisi_v.addWidget(
            self._baslik_ekle_satiri("💰  Avans", self._avans_ekle, RENK["accent2"], "Avans ekle",
                                     ipucu="Avans ciroya ve gidere dahil değildir")
        )
        if not ozet["avanslar"]:
            self.avans_gecmisi_v.addWidget(self._bos_etiket("Bu gün avans eklenmemiş."))
        for avans in ozet["avanslar"]:
            self._avans_satiri_ekle(avans)

    def _avans_satiri_ekle(self, avans: Avans):
        satir = QFrame()
        satir.setMaximumWidth(620)
        satir.setStyleSheet(
            f"QFrame {{ background-color:{RENK['panel_hover']}; border-radius:8px; }}"
        )
        sh = QHBoxLayout(satir)
        sh.setContentsMargins(12, 8, 8, 8)
        bilgi_lbl = QLabel(f"{avans.zaman.strftime('%H:%M')}  ·  {avans.aciklama}")
        bilgi_lbl.setStyleSheet("font-size:12px; background:transparent; border:none;")
        bilgi_lbl.setWordWrap(True)  # dar sütunda uzun açıklama alt satıra insin
        sh.addWidget(bilgi_lbl, 1)
        tutar_lbl = QLabel(f"{avans.tutar:.0f} ₺")
        tutar_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['accent2']}; background:transparent; border:none;")
        sh.addWidget(tutar_lbl)
        duzenle_btn = QPushButton("✏️")
        duzenle_btn.setObjectName("ghostBtn")
        duzenle_btn.setFixedSize(30, 30)
        duzenle_btn.setStyleSheet("padding:0; font-size:12px;")
        duzenle_btn.clicked.connect(lambda checked, a=avans: self._avans_duzenle(a))
        sh.addWidget(duzenle_btn)
        sil_btn = cop_butonu_yap(QPushButton())
        sil_btn.clicked.connect(lambda checked, a=avans: self._avans_sil(a))
        sh.addWidget(sil_btn)
        self.avans_gecmisi_v.addWidget(satir)

    def _avans_duzenle(self, avans: Avans):
        d = _GiderAvansDialog("Avansı Düzenle", avans.aciklama, avans.tutar, parent=self)
        if d.exec() and d.sonuc:
            avans.aciklama = d.sonuc["aciklama"]
            avans.tutar = d.sonuc["tutar"]
            self._yenile()

    def _avans_sil(self, avans: Avans):
        cevap = soru_sor(self, "Avansı Sil", f"'{avans.aciklama}' silinsin mi?")
        if cevap == QMessageBox.StandardButton.Yes:
            self.state.avanslar.remove(avans)
            self._yenile()

    def _masa_disi_urunleri_goster(self, urun_bazli: list, toplam: float):
        d = OrtalanmisDialog(self)
        d.setWindowTitle("Masa Dışı Satış - Ürün Detayı")
        d.setMinimumWidth(340)
        # Bazı durumlarda global QSS bu pencereye tam ulaşmayabiliyor - yerel
        # stil ile zeminin HER ZAMAN açık/beyaz görünmesini garantiliyoruz
        # (aksi halde koyu/siyah bir zemin görünebiliyordu).
        d.setStyleSheet(f"QDialog {{ background-color:{RENK['panel']}; }}")
        v = QVBoxLayout(d)
        v.setSpacing(10)

        ust_kart = QFrame()
        ust_kart.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #E9EAEE, stop:1 #DADCE2); border-radius:12px; }"
        )
        ukv = QVBoxLayout(ust_kart)
        ukv.setContentsMargins(16, 12, 16, 12)
        baslik = QLabel("🛍️  MASA DIŞI SATIŞ")
        baslik.setStyleSheet("color:#6B6F7A; font-size:11px; font-weight:700; background:transparent; letter-spacing:1px;")
        ukv.addWidget(baslik)
        tutar_lbl = QLabel(f"{toplam:.0f} ₺")
        tutar_lbl.setStyleSheet("color:#00E676; font-size:24px; font-weight:800; background:transparent;")
        ukv.addWidget(tutar_lbl)
        v.addWidget(ust_kart)

        if not urun_bazli:
            bos_lbl = QLabel("Bu satışta ürün bilgisi yok.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px; background:transparent;")
            v.addWidget(bos_lbl)

        for ad, veri in urun_bazli:
            satir = QHBoxLayout()
            ad_lbl = QLabel(f"{ad}  ×{veri['adet']}")
            ad_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text']}; background:transparent;")
            satir.addWidget(ad_lbl)
            satir.addStretch()
            tutar_urun_lbl = QLabel(f"{veri['tutar']:.0f} ₺")
            tutar_urun_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['accent']}; background:transparent;")
            satir.addWidget(tutar_urun_lbl)
            v.addLayout(satir)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("ghostBtn")
        kapat_btn.clicked.connect(d.accept)
        v.addWidget(kapat_btn)
        d.exec()

    def _bos_etiket(self, metin: str) -> QLabel:
        lbl = QLabel(metin)
        lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px;")
        return lbl

    def _baslik_ekle_satiri(self, baslik: str, tiklama, renk: str, buton_ipucu: str, ipucu: str = "") -> QWidget:
        """'Gider' / 'Avans' kart başlığı + sağında yuvarlak '+' butonu."""
        kap = QWidget()
        kap.setStyleSheet("background:transparent;")
        h = QHBoxLayout(kap)
        h.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(baslik)
        lbl.setStyleSheet(f"font-weight:800; font-size:14px; color:{RENK['text']}; background:transparent;")
        if ipucu:
            lbl.setToolTip(ipucu)
        h.setSpacing(8)
        h.addWidget(lbl)
        arti_btn = QPushButton("+")
        arti_btn.setFixedSize(30, 30)
        arti_btn.setAutoDefault(False)
        arti_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        arti_btn.setToolTip(buton_ipucu)
        arti_btn.setStyleSheet(
            f"QPushButton {{ background-color:{_hex_rgba(renk, 0.12)}; color:{renk}; border:1.5px solid {renk}; "
            f"border-radius:15px; font-size:18px; font-weight:800; padding:0 0 2px 0; }}"
            f"QPushButton:hover {{ background-color:{renk}; color:#FFFFFF; }}"
        )
        arti_btn.clicked.connect(lambda checked=False: tiklama())
        h.addWidget(arti_btn)
        h.addStretch()
        return kap

    def _gider_satiri_ekle(self, gider: Gider, tarih_goster: bool = False):
        zaman_str = gider.zaman.strftime("%d.%m.%Y %H:%M") if tarih_goster else gider.zaman.strftime("%H:%M")
        satir = QFrame()
        satir.setMaximumWidth(620)
        satir.setStyleSheet(
            f"QFrame {{ background-color:{RENK['panel_hover']}; border-radius:8px; }}"
        )
        sh = QHBoxLayout(satir)
        sh.setContentsMargins(12, 8, 8, 8)
        bilgi_lbl = QLabel(f"{zaman_str}  ·  {gider.aciklama}")
        bilgi_lbl.setStyleSheet("font-size:12px; background:transparent; border:none;")
        bilgi_lbl.setWordWrap(True)  # dar sütunda uzun açıklama alt satıra insin
        sh.addWidget(bilgi_lbl, 1)
        tutar_lbl = QLabel(f"{gider.tutar:.0f} ₺")
        tutar_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['danger']}; background:transparent; border:none;")
        sh.addWidget(tutar_lbl)
        duzenle_btn = QPushButton("✏️")
        duzenle_btn.setObjectName("ghostBtn")
        duzenle_btn.setFixedSize(30, 30)
        duzenle_btn.setStyleSheet("padding:0; font-size:12px;")
        duzenle_btn.clicked.connect(lambda checked, g=gider: self._gider_duzenle(g))
        sh.addWidget(duzenle_btn)
        sil_btn = cop_butonu_yap(QPushButton())
        sil_btn.clicked.connect(lambda checked, g=gider: self._gider_sil(g))
        sh.addWidget(sil_btn)
        self.gider_gecmisi_v.addWidget(satir)

    def _gider_ekle(self):
        d = _GiderAvansDialog("Gider Ekle", parent=self)
        if d.exec() and d.sonuc:
            self.state.giderler.append(Gider(id=next_id(), **d.sonuc))
            self._yenile()

    def _gider_duzenle(self, gider: Gider):
        d = _GiderAvansDialog("Gideri Düzenle", gider.aciklama, gider.tutar, parent=self)
        if d.exec() and d.sonuc:
            gider.aciklama = d.sonuc["aciklama"]
            gider.tutar = d.sonuc["tutar"]
            self._yenile()

    def _gider_sil(self, gider: Gider):
        cevap = soru_sor(self, "Gideri Sil", f"'{gider.aciklama}' silinsin mi?")
        if cevap == QMessageBox.StandardButton.Yes:
            self.state.giderler.remove(gider)
            self._yenile()

    def _avans_ekle(self):
        d = _GiderAvansDialog("Avans Ekle", parent=self)
        if d.exec() and d.sonuc:
            self.state.avanslar.append(Avans(id=next_id(), **d.sonuc))
            self._yenile()


class GenelRaporSayfasi(QWidget):
    """Kasa > Genel: kayıtlı tüm iş günleri AY AY gruplanır (akordeon), bir güne
    tıklayınca Gün Sonu sayfası o günü göstererek açılır."""
    def __init__(self, state: AppState, gunsonu_sayfa: GunSonuSayfasi, gun_secildi_cb, parent=None):
        super().__init__(parent)
        self.state = state
        self.gunsonu_sayfa = gunsonu_sayfa
        self.gun_secildi_cb = gun_secildi_cb
        self._acik_aylar: set[tuple[int, int]] = set()
        # Her ayın KENDİ arama kutusundaki metni ayrı ayrı hatırlıyoruz - o ay
        # tekrar açıldığında/sayfa tazelendiğinde arama kaybolmasın diye.
        self._ay_arama_metinleri: dict[tuple[int, int], str] = {}

        self.disv = QVBoxLayout(self)
        self.disv.setContentsMargins(28, 24, 28, 24)
        self.disv.setSpacing(14)
        baslik = QLabel("Genel Rapor")
        baslik.setObjectName("pageTitle")
        self.disv.addWidget(baslik)
        alt_baslik = QLabel("Kayıtlı tüm iş günleri ay ay gruplanır - bir aya/güne ÇİFT tıklayınca açılır/raporu gelir.")
        alt_baslik.setObjectName("pageSubtitle")
        self.disv.addWidget(alt_baslik)

        # --- Tarih Seç: aylar arasında tek tek tıklamadan, doğrudan
        # istenen güne atlamak için - örn. "7 ay önceki bir gün" aranırken
        # ay ay açıp kapatmak yerine tarihi seçip direkt o günün Gün Sonu
        # raporuna gidiliyor (bildirilen istek). ---
        tarih_satir = QHBoxLayout()
        tarih_etiket = QLabel("📅  Tarihe Git:")
        tarih_etiket.setStyleSheet(f"font-weight:700; color:{RENK['text']};")
        tarih_satir.addWidget(tarih_etiket)
        self.tarih_sec = SessizDateEdit()
        self.tarih_sec.setCalendarPopup(True)
        self.tarih_sec.setDate(QDate.currentDate())
        self.tarih_sec.setDisplayFormat("dd.MM.yyyy")
        self.tarih_sec.setFixedWidth(140)
        # KRİTİK: takvim açılır penceresi ayrı bir ÜST DÜZEY (top-level,
        # Qt::Popup) pencere olarak açılıyor. Sadece QSS ("QCalendarWidget
        # {...}") ve WA_StyledBackground yetmedi - Windows'ta bu tip
        # top-level popup'lar Qt tarafından her AÇILIŞTA sistemin
        # karanlık/açık temasına göre YENİDEN paletlenebiliyor (main.py'de
        # ana pencereler için zaten bu yüzden elle açık palet
        # zorlanıyordu - aynı sorun burada da var, üstelik popup'ta QSS bile
        # bazen yetersiz kalabiliyor çünkü bazı iç parçalar QPalette
        # renkleriyle çiziliyor, stylesheet'le değil). Bu yüzden takvimin VE
        # TÜM iç parçalarının (nav bar, spin box, tablo görünümü...)
        # palet'ini DOĞRUDAN, elle, açık renklerle sabitliyoruz - bu,
        # stylesheet'ten daha güçlü, OS temasının ezemeyeceği bir katman.
        self._takvimi_isiklandir(self.tarih_sec)
        tarih_satir.addWidget(self.tarih_sec)
        git_btn = QPushButton("Git →")
        git_btn.setObjectName("primaryBtn")
        git_btn.setAutoDefault(False)
        git_btn.clicked.connect(self._tarihe_git)
        tarih_satir.addWidget(git_btn)
        tarih_satir.addStretch()
        self.disv.addLayout(tarih_satir)

        self.liste_alani = QVBoxLayout()
        self.liste_alani.setSpacing(10)
        self.disv.addLayout(self.liste_alani)
        self.disv.addStretch()

        self._listeyi_kur()

    AY_ADLARI = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

    def _listeyi_kur(self):
        while self.liste_alani.count():
            item = self.liste_alani.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        gunler = self.state.mevcut_gunler()
        if not gunler:
            bos_lbl = QLabel("Henüz herhangi bir güne ait kayıt yok.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
            self.liste_alani.addWidget(bos_lbl)
            return

        aylara_gore: dict[tuple[int, int], list[date]] = {}
        for g in gunler:
            aylara_gore.setdefault((g.year, g.month), []).append(g)

        for (yil, ay), ay_gunleri in aylara_gore.items():
            acik = (yil, ay) in self._acik_aylar
            ay_ciro = sum(self.state.gun_ozet(g)["ciro"] for g in ay_gunleri)
            ay_gider = sum(self.state.gun_ozet(g)["gider"] for g in ay_gunleri)
            ay_net = sum(self.state.gun_ozet(g)["net"] for g in ay_gunleri)
            # "Ciro" zaten masa ücreti + ürün (market) gelirini İÇİNDE
            # barındırıyor (gun_ozet -> ciro = tüm satışların toplam_tutar'ı,
            # ürünler dahil) - burada AYRICA gösterilen "Market" bu toplamı
            # DEĞİŞTİRMİYOR, sadece cironun ne kadarının ürün satışından
            # geldiğini kullanıcıya ayrıca gösteriyor (çift sayım YOK).
            ay_market = sum(self.state.gun_ozet(g)["toplam_urun_geliri"] for g in ay_gunleri)

            # --- Ay "klasörü": masaüstü dosya/klasör simgesi gibi, sarımsı
            # amber tonlu, belirgin bir kart ---
            kutu = QFrame()
            kutu.setStyleSheet(
                "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
                "stop:0 #FFF6DD, stop:1 #FFEBB8); border:1px solid #F0D68A; border-radius:12px; }"
            )
            kv = QVBoxLayout(kutu)
            kv.setContentsMargins(14, 10, 14, 10)
            kv.setSpacing(8)

            # ÖNEMLİ: QPushButton DEĞİL, düz bir kutu kullanıyoruz - metin
            # uzun olunca QPushButton'ın tıklanabilir alanı bazen tutarsız
            # davranıyordu ("bazen tek tıkta, bazen üç tıkta açılıyordu").
            # Düz bir QFrame + mouseDoubleClickEvent, SATIRIN HER NOKTASINI
            # garantili şekilde tıklanabilir yapar.
            baslik_kutu = QFrame()
            baslik_kutu.setStyleSheet("background:transparent; border:none;")
            baslik_kutu.setCursor(Qt.CursorShape.PointingHandCursor)
            bh = QHBoxLayout(baslik_kutu)
            bh.setContentsMargins(0, 0, 0, 0)
            baslik_lbl = QLabel(
                f"{'📂' if acik else '🗀'}  {self.AY_ADLARI[ay-1]} {yil}   ·   Ciro: {ay_ciro:.0f} ₺   ·   Market: {ay_market:.0f} ₺   ·   Gider: {ay_gider:.0f} ₺   ·   Net: {ay_net:.0f} ₺"
            )
            baslik_lbl.setStyleSheet(
                "background:transparent; font-weight:800; font-size:14px; color:#8A6A1A;"
            )
            bh.addWidget(baslik_lbl)
            bh.addStretch()
            baslik_kutu.mouseDoubleClickEvent = lambda event, k=(yil, ay): self._ay_ac_kapa(k)
            kv.addWidget(baslik_kutu)

            if acik:
                # --- Bu AYA ÖZEL gider arama kutusu - sadece bu ayın
                # giderlerinde arar, başka aylara karışmaz. Metin değişince
                # sadece kendi küçük sonuç alanını (ay_sonuc_v) günceller,
                # sayfanın geri kalanını yeniden kurmaz - yazarken odak
                # kaybolmasın diye. ---
                ay_arama_satir = QHBoxLayout()
                ay_arama_etiket = QLabel("🔍")
                ay_arama_satir.addWidget(ay_arama_etiket)
                ay_arama_input = QLineEdit()
                ay_arama_input.setPlaceholderText(f"{self.AY_ADLARI[ay-1]} içinde gider ara...")
                ay_arama_input.setText(self._ay_arama_metinleri.get((yil, ay), ""))
                ay_arama_input.setStyleSheet(
                    f"background-color:#FFFFFF; color:{RENK['text']}; "
                    f"border:1px solid {RENK['border_strong']}; border-radius:6px; padding:6px;"
                )
                ay_arama_satir.addWidget(ay_arama_input)
                kv.addLayout(ay_arama_satir)

                ay_sonuc_v = QVBoxLayout()
                kv.addLayout(ay_sonuc_v)

                def _ay_arama_guncelle(metin, yil=yil, ay=ay, ay_gunleri=ay_gunleri, sonuc_v=ay_sonuc_v):
                    self._ay_arama_metinleri[(yil, ay)] = metin
                    while sonuc_v.count():
                        item = sonuc_v.takeAt(0)
                        w = item.widget()
                        if w:
                            w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                            w.deleteLater()
                    arama_metni = metin.strip().lower()
                    if not arama_metni:
                        return
                    eslesenler = sorted(
                        [g for g in self.state.giderler
                         if arama_metni in g.aciklama.lower() and is_gunu(g.zaman) in ay_gunleri],
                        key=lambda g: g.zaman, reverse=True
                    )
                    toplam = sum(g.tutar for g in eslesenler)
                    sonuc_baslik = QLabel(
                        f"'{metin.strip()}' için {len(eslesenler)} sonuç, toplam {toplam:.0f} ₺ "
                        f"({self.AY_ADLARI[ay-1]} {yil})"
                    )
                    sonuc_baslik.setStyleSheet(f"font-weight:800; font-size:12px; color:{RENK['text']}; background:transparent;")
                    sonuc_v.addWidget(sonuc_baslik)
                    if not eslesenler:
                        bos_lbl = QLabel("Eşleşen gider bulunamadı.")
                        bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:11px; background:transparent;")
                        sonuc_v.addWidget(bos_lbl)
                        return
                    for gider in eslesenler:
                        satir = QFrame()
                        satir.setMaximumWidth(620)
                        satir.setStyleSheet(
                            f"QFrame {{ background-color:#FFFFFF; border:1px solid #F0D68A; border-radius:8px; }}"
                        )
                        sh = QHBoxLayout(satir)
                        sh.setContentsMargins(12, 8, 8, 8)
                        bilgi_lbl = QLabel(f"{gider.zaman.strftime('%d.%m.%Y %H:%M')}  ·  {gider.aciklama}")
                        bilgi_lbl.setStyleSheet("font-size:12px; background:transparent; border:none;")
                        sh.addWidget(bilgi_lbl)
                        sh.addStretch()
                        tutar_lbl = QLabel(f"{gider.tutar:.0f} ₺")
                        tutar_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['danger']}; background:transparent; border:none;")
                        sh.addWidget(tutar_lbl)
                        sonuc_v.addWidget(satir)

                ay_arama_input.textChanged.connect(_ay_arama_guncelle)
                if self._ay_arama_metinleri.get((yil, ay)):
                    _ay_arama_guncelle(self._ay_arama_metinleri[(yil, ay)])

                for g in ay_gunleri:
                    gun_ozet = self.state.gun_ozet(g)
                    gun_satir = QFrame()
                    gun_satir.setStyleSheet(
                        "QFrame { background-color:#FFFFFF; border:1px solid #F0D68A; border-radius:8px; }"
                    )
                    gun_satir.setCursor(Qt.CursorShape.PointingHandCursor)
                    gh = QHBoxLayout(gun_satir)
                    gh.setContentsMargins(12, 8, 12, 8)
                    tarih_lbl = QLabel(f"📄  {g.strftime('%d.%m.%Y')}")
                    tarih_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text']}; background:transparent;")
                    gh.addWidget(tarih_lbl)
                    gh.addStretch()
                    ciro_lbl = QLabel(f"Ciro: {gun_ozet['ciro']:.0f} ₺")
                    ciro_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['accent2']}; background:transparent;")
                    gh.addWidget(ciro_lbl)
                    market_lbl = QLabel(f"Market: {gun_ozet['toplam_urun_geliri']:.0f} ₺")
                    market_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['info']}; background:transparent; margin-left:14px;")
                    gh.addWidget(market_lbl)
                    gider_lbl = QLabel(f"Gider: {gun_ozet['gider']:.0f} ₺")
                    gider_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['danger']}; background:transparent; margin-left:14px;")
                    gh.addWidget(gider_lbl)
                    net_lbl = QLabel(f"Net: {gun_ozet['net']:.0f} ₺")
                    net_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['accent']}; background:transparent; margin-left:14px;")
                    gh.addWidget(net_lbl)
                    # Ay başlığıyla TUTARLI olsun diye burası da ÇİFT TIK.
                    gun_satir.mouseDoubleClickEvent = lambda event, gg=g: self._gune_tiklandi(gg)
                    kv.addWidget(gun_satir)

            self.liste_alani.addWidget(kutu)

    def _ay_ac_kapa(self, ay_anahtari: tuple[int, int]):
        if ay_anahtari in self._acik_aylar:
            self._acik_aylar.discard(ay_anahtari)
        else:
            self._acik_aylar.add(ay_anahtari)
        self._listeyi_kur()

    def _gune_tiklandi(self, gun: date):
        self.gunsonu_sayfa.gunu_goster(gun)
        self.gun_secildi_cb()

    def _tarihe_git(self):
        """'Tarihe Git' butonu: seçilen tarihin ay klasörünü otomatik açar
        (o güne göz atarken diğer ayları elle açıp kapatmaya gerek kalmasın)
        ve Gün Sonu raporunu doğrudan o günü göstererek açar - tıpkı bir
        güne çift tıklamış gibi."""
        qdate = self.tarih_sec.date()
        secilen_gun = date(qdate.year(), qdate.month(), qdate.day())
        self._acik_aylar.add((secilen_gun.year, secilen_gun.month))
        self._gune_tiklandi(secilen_gun)

    def _takvimi_isiklandir(self, tarih_sec: SessizDateEdit):
        """Açılır takvimi (ve TÜM iç parçalarını) zorla açık/beyaz temaya
        sabitler. Bkz. tarih_sec oluşturulurken bırakılan not - sadece
        stylesheet güvenilir olmadığı için burada QPalette'i doğrudan,
        elle veriyoruz."""
        takvim = tarih_sec.calendarWidget()

        acik_palet = QPalette()
        acik_palet.setColor(QPalette.ColorRole.Window, QColor(RENK["panel"]))
        acik_palet.setColor(QPalette.ColorRole.WindowText, QColor(RENK["text"]))
        acik_palet.setColor(QPalette.ColorRole.Base, QColor(RENK["panel"]))
        acik_palet.setColor(QPalette.ColorRole.AlternateBase, QColor(RENK["panel"]))
        acik_palet.setColor(QPalette.ColorRole.Text, QColor(RENK["text"]))
        acik_palet.setColor(QPalette.ColorRole.Button, QColor(RENK["bg"]))
        acik_palet.setColor(QPalette.ColorRole.ButtonText, QColor(RENK["text"]))
        acik_palet.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
        acik_palet.setColor(QPalette.ColorRole.ToolTipText, QColor(RENK["text"]))
        acik_palet.setColor(QPalette.ColorRole.Highlight, QColor(RENK["accent"]))
        acik_palet.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        acik_palet.setColor(QPalette.ColorRole.PlaceholderText, QColor(RENK["text_muted"]))

        def _uygula():
            # Takvimin kendisine VE içindeki KAPSAYICI/parça widget'lara
            # (gün tablosu, başlık satırı, kaydırma çubukları, ay/yıl kutusu
            # vb.) paleti zorluyoruz - Qt'de palet normalde alt widget'lara
            # miras kalır, ama bu popup pencere top-level olduğu ve
            # Windows tarafından yeniden temalanabildiği için garantiye
            # almak adına hiçbirini şansa bırakmıyoruz.
            #
            # ÖNEMLİ: QAbstractButton/QToolButton (◀ ▶ ay/yıl butonları ve
            # tablonun gizli köşe düğmesi) ve QMenu buraya KASITLI OLARAK
            # DAHİL EDİLMİYOR - bunlar zaten uygulamanın genel QSS'i
            # (şeffaf zemin) üzerinden doğru görünüyordu; onlara da
            # autoFillBackground+palet zorlarsak, normalde şeffaf/görünmez
            # olan bu düğmeler (özellikle tablonun gizli köşe düğmesi) SOLID
            # MOR KUTULAR olarak ortaya çıkıyor - bildirilen "üstte iki mor
            # kutu" hatasının sebebi tam olarak buydu.
            for w in [takvim] + takvim.findChildren(QWidget):
                if isinstance(w, (QAbstractButton, QMenu)):
                    continue
                w.setPalette(acik_palet)
                w.setAutoFillBackground(True)
                w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        _uygula()
        # Gün tablosunun (qt_calendar_calendarview) fare hareketini
        # İZLEMESİNİ açıyoruz - varsayılan olarak KAPALI, bu yüzden
        # ":hover" QSS kuralımız (yukarıda) fare üzerine gelince hiç
        # tetiklenmiyordu (bildirilen "üzerine gelince buz mavisi olsun"
        # isteği).
        gun_tablosu = takvim.findChild(QWidget, "qt_calendar_calendarview")
        if gun_tablosu is not None:
            gun_tablosu.setMouseTracking(True)
            if gun_tablosu.viewport() is not None:
                gun_tablosu.viewport().setMouseTracking(True)
        # Bazı alt parçalar (ör. kaydırma çubukları) TAKVİM İLK KEZ
        # GÖRÜNDÜĞÜNDE tembel (lazy) oluşturuluyor, yani yukarıdaki ilk
        # uygulamada henüz yoklar. Bu yüzden takvim her açıldığında
        # (Show olayında) paleti TEKRAR uyguluyoruz - böylece sonradan
        # oluşan hiçbir parça karanlıkta kalmıyor.
        takvim.installEventFilter(self)
        self._takvim_widget = takvim
        self._takvimi_yeniden_isikla = _uygula

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_takvim_widget", None) and event.type() == event.Type.Show:
            self._takvimi_yeniden_isikla()
        return super().eventFilter(obj, event)


class KasaView(QWidget):
    """Kasa: üstte 3 iç sekme (Anlık Salon / Gün Sonu / Genel), altta seçili
    sekmenin içeriği."""
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state

        disv = QVBoxLayout(self)
        disv.setContentsMargins(28, 24, 28, 24)
        disv.setSpacing(14)

        baslik = QLabel("Kasa")
        baslik.setObjectName("pageTitle")
        disv.addWidget(baslik)

        sekme_satir = QHBoxLayout()
        self.sekme_butonlari: dict[str, QPushButton] = {}
        for key, ad in [("anlik", "Anlık Salon"), ("gunsonu", "Gün Sonu"), ("genel", "Genel")]:
            btn = QPushButton(ad)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._sekme_sec(k))
            sekme_satir.addWidget(btn)
            self.sekme_butonlari[key] = btn
        sekme_satir.addStretch()
        disv.addLayout(sekme_satir)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background:transparent;")
        ic = QWidget()
        ic.setStyleSheet("background:transparent;")
        ic_v = QVBoxLayout(ic)

        self.stack = QStackedWidget()
        self.anlik_sayfa = AnlikSalonSayfasi(state)
        self.gunsonu_sayfa = GunSonuSayfasi(state)
        self.genel_sayfa = GenelRaporSayfasi(state, self.gunsonu_sayfa, lambda: self._sekme_sec("gunsonu"))
        self.stack.addWidget(self.anlik_sayfa)
        self.stack.addWidget(self.gunsonu_sayfa)
        self.stack.addWidget(self.genel_sayfa)
        ic_v.addWidget(self.stack)
        scroll.setWidget(ic)
        disv.addWidget(scroll)

        self._sekme_sec("anlik")

    def _sekme_sec(self, key: str):
        for k, btn in self.sekme_butonlari.items():
            btn.setChecked(k == key)
            btn.setObjectName("primaryBtn" if k == key else "ghostBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        sayfa_map = {"anlik": self.anlik_sayfa, "gunsonu": self.gunsonu_sayfa, "genel": self.genel_sayfa}
        sayfa = sayfa_map[key]
        self.stack.setCurrentWidget(sayfa)
        if key == "anlik":
            self.anlik_sayfa.yenile()
        elif key == "genel":
            self.genel_sayfa._listeyi_kur()

    def yenile(self):
        """main.py sekme değişince çağırır - hangi iç sekme açıksa onu tazeler.
        ÖNEMLİ: Genel Rapor SAYILMAZ - o sayfadaki toplam/liste, Anlık
        Salon'un aksine, saniye saniye değişen bir şey değil (sadece başka
        bir işlem yapılınca değişir). Onu da her ~250ms'de bir tazelersek,
        kullanıcı bir ayın arama kutusuna yazı yazarken kutu her seferinde
        yok edilip yeniden kuruluyor, odak kayboluyor ve YAZI YAZILAMIYOR
        hale geliyordu (kullanıcı bunu fark etti). Genel Rapor SADECE
        sekmeye ilk geçişte (_sekme_degisti) tazelenir, bu yeterlidir."""
        if self.stack.currentWidget() is self.anlik_sayfa:
            self.anlik_sayfa.yenile()
        elif self.stack.currentWidget() is self.gunsonu_sayfa:
            self.gunsonu_sayfa._yenile()


_ODEME_SIRASI = ["NAKİT", "KART", "İBAN", "BORÇ"]
_ODEME_ADLARI = {"NAKİT": "Nakit", "KART": "Kart", "İBAN": "İBAN", "BORÇ": "Borç"}


def odeme_kalemleri(dagilim: dict) -> list:
    """Bir satışın ödeme dağılımını [(Görünen Ad, tutar), ...] olarak, sabit bir
    sırayla (Nakit, Kart, İBAN, Borç, sonra bilinmeyen eski anahtarlar) verir.
    Tutarı 0 olanlar atlanır. Eski kayıtlardaki (örn. kaldırılmış 'QR')
    anahtarlar da silinmeden ham adlarıyla gösterilir."""
    if not dagilim:
        return []
    sirali = [k for k in _ODEME_SIRASI if k in dagilim] + [k for k in dagilim if k not in _ODEME_SIRASI]
    return [(_ODEME_ADLARI.get(k, k), dagilim[k]) for k in sirali if dagilim[k] and dagilim[k] > 0]


def odeme_ozeti(dagilim: dict) -> str:
    """'Nakit' ya da 'Nakit + Kart' gibi kısa özet (tutarsız)."""
    return " + ".join(ad for ad, _ in odeme_kalemleri(dagilim))


class _SonIslemDetayDialog(OrtalanmisDialog):
    """Son İşlemler'de bir satıra tıklayınca açılır - masa ücreti, ürün detayı,
    açılış/kapanış saati."""
    def __init__(self, islem: KasaIslemi, parent=None):
        super().__init__(parent)
        self.setWindowTitle(islem.masa_adi)
        self.setMinimumWidth(380)
        v = QVBoxLayout(self)
        v.setSpacing(14)

        # --- Üst kart: masa/işlem adı + toplam tutar (titanyum gri + neon
        # yeşil) - İPTAL edilmişse kırmızı "İptal Edildi" gösterir ---
        ust_kart = QFrame()
        ust_kart.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #E9EAEE, stop:1 #DADCE2); border-radius:12px; }"
        )
        ukv = QVBoxLayout(ust_kart)
        ukv.setContentsMargins(18, 14, 18, 14)
        ad_lbl = QLabel(islem.masa_adi)
        ad_lbl.setStyleSheet("color:#6B6F7A; font-size:11px; font-weight:700; background:transparent; letter-spacing:1px;")
        ukv.addWidget(ad_lbl)
        if islem.iptal_nedeni:
            toplam_lbl = QLabel("❌ İPTAL EDİLDİ")
            toplam_lbl.setStyleSheet(f"color:{RENK['danger']}; font-size:22px; font-weight:800; background:transparent;")
        else:
            toplam_lbl = QLabel(f"{islem.toplam_tutar:.0f} ₺")
            toplam_lbl.setStyleSheet("color:#00E676; font-size:28px; font-weight:800; background:transparent;")
        ukv.addWidget(toplam_lbl)
        v.addWidget(ust_kart)

        if islem.iptal_nedeni:
            sebep_kart = QFrame()
            sebep_kart.setObjectName("masaKart")
            skv = QVBoxLayout(sebep_kart)
            sebep_baslik = QLabel("📝  İptal Sebebi")
            sebep_baslik.setStyleSheet(f"font-size:13px; font-weight:800; color:{RENK['text']};")
            skv.addWidget(sebep_baslik)
            sebep_metin = QLabel(islem.iptal_nedeni)
            sebep_metin.setWordWrap(True)
            sebep_metin.setStyleSheet(f"font-size:12px; color:{RENK['text']}; font-weight:600;")
            skv.addWidget(sebep_metin)
            v.addWidget(sebep_kart)

        # --- Tek kart: masa ücreti + ürünler + açılış/kapanış saati bir arada
        # (öncesinde 2 ayrı kutuydu, gereksiz yere bölünmüş duruyordu) ---
        detay_kart = QFrame()
        detay_kart.setObjectName("masaKart")
        dkv = QVBoxLayout(detay_kart)
        dkv.setSpacing(7)
        dkv.setContentsMargins(12, 12, 12, 12)
        dkv.addWidget(self._satir("Masa Ücreti", f"{islem.masa_ucreti:.0f} ₺"))

        if islem.urunler:
            urun_baslik = QLabel("🛒  Ürünler")
            urun_baslik.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['text']}; margin-top:6px;")
            dkv.addWidget(urun_baslik)
            for u in islem.urunler:
                toplam = u["adet"] * u["birim_fiyat"]
                dkv.addWidget(self._satir(f"{u['ad']}  ×{u['adet']}", f"{toplam:.0f} ₺"))
        else:
            bos_lbl = QLabel("Ürün satışı yok")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px; margin-top:4px;")
            dkv.addWidget(bos_lbl)

        if islem.indirim_tutari and not islem.iptal_nedeni:
            indirim_satir = self._satir("💸 İndirim", f"-{islem.indirim_tutari:.0f} ₺")
            for lbl in indirim_satir.findChildren(QLabel)[1:]:
                lbl.setStyleSheet(f"font-size:13px; color:{RENK['danger']}; font-weight:800; background:transparent; border:none;")
            dkv.addWidget(indirim_satir)

        odemeler = odeme_kalemleri(islem.odeme_dagilimi)
        if odemeler and not islem.iptal_nedeni:
            odeme_baslik = QLabel("💳  Ödeme Yöntemi")
            odeme_baslik.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['text']}; margin-top:6px;")
            dkv.addWidget(odeme_baslik)
            for ad, tutar in odemeler:
                dkv.addWidget(self._satir(ad, f"{tutar:.0f} ₺"))

        ayirici = QFrame()
        ayirici.setFrameShape(QFrame.Shape.HLine)
        ayirici.setStyleSheet(f"background-color:{RENK['border_strong']}; max-height:1px; margin-top:8px; margin-bottom:4px;")
        dkv.addWidget(ayirici)

        acilis_str = islem.acilis_zamani.strftime("%d.%m.%Y %H:%M") if islem.acilis_zamani else "-"
        kapanis_str = islem.zaman.strftime("%d.%m.%Y %H:%M")
        dkv.addWidget(self._satir("🟢 Açılış Saati", acilis_str))
        dkv.addWidget(self._satir("🔴 Kapanış Saati", kapanis_str))
        v.addWidget(detay_kart)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("ghostBtn")
        kapat_btn.clicked.connect(self.accept)
        v.addWidget(kapat_btn)

    def _satir(self, etiket: str, deger: str, kalin: bool = False) -> QWidget:
        """Her kalem kendi yuvarlak köşeli, ince çerçeveli kutusunda (premium)."""
        w = QFrame()
        w.setObjectName("detaySatir")
        w.setStyleSheet(
            f"QFrame#detaySatir {{ background-color:#FAFAFE; border:1px solid {RENK['border']}; "
            f"border-radius:10px; }}"
        )
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 8, 12, 8)
        e = QLabel(etiket)
        e.setStyleSheet(f"font-size:12px; color:{RENK['text']}; font-weight:600; background:transparent; border:none;")
        d = QLabel(deger)
        d.setStyleSheet(f"font-size:13px; color:{RENK['accent']}; font-weight:800; background:transparent; border:none;")
        h.addWidget(e)
        h.addStretch()
        h.addWidget(d)
        return w


class SonIslemlerView(QWidget):
    """Son İşlemler: Gün Sonu ile AYNI gün gezinme mantığı (◀ Önceki Gün /
    Bugün / Sonraki Gün ▶) - o iş gününde kapanmış (ödemesi alınmış) tüm
    masalar listelenir, bir satıra tıklayınca detay (ücret/ürün/açılış-kapanış
    saati) açılır. Ayrıca kaydetmeye gerek yok - zaten Kasa'ya işlenmiş veriler
    üzerinden gösteriliyor."""
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.goruntulenen_gun: date = is_gunu(datetime.now())

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)

        baslik = QLabel("Son İşlemler")
        baslik.setObjectName("pageTitle")
        v.addWidget(baslik)

        gun_satir = QHBoxLayout()
        onceki_btn = QPushButton("◀ Önceki Gün")
        onceki_btn.setObjectName("ghostBtn")
        onceki_btn.clicked.connect(self._onceki_gun)
        gun_satir.addWidget(onceki_btn)

        gun_satir.addStretch()

        bugun_btn = QPushButton("Bugün")
        bugun_btn.setObjectName("primaryBtn")
        # Bazı durumlarda global QSS bu pencereye tam ulaşmayabiliyor - yerel
        # stil ile beyaz yazının HER ZAMAN mor zemin üzerinde görünmesini
        # garantiliyoruz (aksi halde metin görünmez oluyordu).
        bugun_btn.setStyleSheet(
            f"background-color:rgba(108,77,246,0.12); color:{RENK['accent']}; "
            f"border-width:1.5px; border-style:solid; border-color:{RENK['accent']}; "
            f"border-radius:10px; padding:10px 18px; font-weight:700;"
        )
        bugun_btn.clicked.connect(self._bugune_don)
        gun_satir.addWidget(bugun_btn)

        gun_satir.addStretch()

        sonraki_btn = QPushButton("Sonraki Gün ▶")
        sonraki_btn.setObjectName("ghostBtn")
        sonraki_btn.clicked.connect(self._sonraki_gun)
        gun_satir.addWidget(sonraki_btn)
        v.addLayout(gun_satir)

        self.gun_baslik_lbl = QLabel()
        self.gun_baslik_lbl.setStyleSheet(f"font-size:16px; font-weight:700; color:{RENK['text']}; background:transparent;")
        self.gun_baslik_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.gun_baslik_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background:transparent;")
        ic = QWidget()
        ic.setStyleSheet("background:transparent;")
        self.liste_v = QVBoxLayout(ic)
        self.liste_v.setSpacing(8)
        # ÖNEMLİ: hizalama TOP olmazsa, kaydırma alanı içindeki fazla boşluk
        # satırların ARASINA dağılıyordu (2 satır varken aralarında devasa
        # boşluk oluşuyordu) - bu, satırları üste sabitler, boşluk en alta gider.
        self.liste_v.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(ic)
        v.addWidget(scroll)

        self.yenile()

    def _onceki_gun(self):
        self.goruntulenen_gun -= timedelta(days=1)
        self.yenile()

    def _sonraki_gun(self):
        self.goruntulenen_gun += timedelta(days=1)
        self.yenile()

    def _bugune_don(self):
        self.goruntulenen_gun = is_gunu(datetime.now())
        self.yenile()

    _son_imza = None

    def yenile(self):
        gun = self.goruntulenen_gun
        bugun_mu = " (Bugün)" if gun == is_gunu(datetime.now()) else ""
        self.gun_baslik_lbl.setText(gun.strftime("%d.%m.%Y") + bugun_mu)

        # Veri değişmediyse satırları yeniden kurma (hover/tıklama bozulmasın)
        imza = repr((gun, [k for k in self.state.kasa_islemleri
                           if not k.is_borc_tahsilati and is_gunu(k.zaman) == gun]))
        if imza == self._son_imza:
            return
        self._son_imza = imza

        while self.liste_v.count():
            item = self.liste_v.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        islemler = sorted(
            [k for k in self.state.kasa_islemleri if not k.is_borc_tahsilati and is_gunu(k.zaman) == gun],
            key=lambda k: k.zaman, reverse=True
        )

        if not islemler:
            bos_lbl = QLabel("Bu gün kapanan masa yok.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
            self.liste_v.addWidget(bos_lbl)
            return

        for islem in islemler:
            acilis_str = islem.acilis_zamani.strftime("%H:%M") if islem.acilis_zamani else "-"
            satir = QFrame()
            satir.setStyleSheet(
                f"QFrame {{ background-color:#FFFFFF; border:1px solid {RENK['border_strong']}; "
                f"border-radius:10px; }}"
                f"QFrame:hover {{ background-color:{RENK['panel_hover']}; border-color:{RENK['accent']}; }}"
            )
            satir.setFixedHeight(46)
            satir.setMaximumWidth(700)
            satir.setCursor(Qt.CursorShape.PointingHandCursor)
            satir.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            sh = QHBoxLayout(satir)
            sh.setContentsMargins(14, 4, 14, 4)

            ikon_kutu = QLabel("❌" if islem.iptal_nedeni else "🎮")
            ikon_kutu.setFixedSize(26, 26)
            ikon_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ikon_kutu.setStyleSheet(
                f"background-color:{RENK['panel_hover']}; border-radius:7px; font-size:12px; border:none;"
            )
            sh.addWidget(ikon_kutu)

            # ÖNEMLİ: addLayout değil, gerçek bir QWidget'a sarıp addWidget
            # kullanıyoruz - çıplak addLayout, kenarlıklı/hover'lı bir kutunun
            # İÇİNDE kullanılınca öğelerin etrafında istenmeyen küçük
            # "kutu içinde kutu" kenarlıkları oluşmasına sebep oluyordu.
            bilgi_v = QVBoxLayout()
            bilgi_v.setSpacing(0)
            bilgi_v.setContentsMargins(0, 0, 0, 0)
            saat_lbl = QLabel(f"⏱ {acilis_str}")
            saat_lbl.setStyleSheet(f"font-size:10px; font-weight:600; color:{RENK['text_muted']}; background:transparent; border:none;")
            bilgi_v.addWidget(saat_lbl)
            ad_lbl = QLabel(islem.masa_adi)
            ad_lbl.setStyleSheet(f"font-size:13px; font-weight:800; color:{RENK['text']}; background:transparent; border:none;")
            bilgi_v.addWidget(ad_lbl)
            bilgi_wrap = QWidget()
            bilgi_wrap.setStyleSheet("background:transparent; border:none;")
            bilgi_wrap.setLayout(bilgi_v)
            sh.addWidget(bilgi_wrap)
            sh.addStretch()

            if islem.iptal_nedeni:
                tutar_lbl = QLabel("İptal Edildi")
                tutar_lbl.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['danger']}; background:transparent; border:none;")
            else:
                tutar_lbl = QLabel(f"{islem.toplam_tutar:.0f} ₺")
                tutar_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
            tutar_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Tutarın altında küçük "Nakit" / "Nakit + Kart" özeti (tutar
            # kırılımı satıra tıklayınca açılan detayda).
            tutar_v = QVBoxLayout()
            tutar_v.setSpacing(0)
            tutar_v.setContentsMargins(0, 0, 0, 0)
            tutar_v.addWidget(tutar_lbl)
            ozet = "" if islem.iptal_nedeni else odeme_ozeti(islem.odeme_dagilimi)
            if ozet:
                yontem_lbl = QLabel(ozet)
                yontem_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                yontem_lbl.setStyleSheet(f"font-size:10px; font-weight:700; color:{RENK['text_muted']}; background:transparent; border:none;")
                tutar_v.addWidget(yontem_lbl)
            tutar_wrap = QWidget()
            tutar_wrap.setStyleSheet("background:transparent; border:none;")
            tutar_wrap.setLayout(tutar_v)
            sh.addWidget(tutar_wrap)

            ok_lbl = QLabel("›")
            ok_lbl.setStyleSheet(f"font-size:16px; color:{RENK['text_muted']}; font-weight:700; margin-left:10px; background:transparent; border:none;")
            sh.addWidget(ok_lbl)

            satir.mousePressEvent = lambda event, i=islem: self._detay_ac(i)
            self.liste_v.addWidget(satir)

    def _detay_ac(self, islem: KasaIslemi):
        _SonIslemDetayDialog(islem, self).exec()


class _SurukleBaslik(QWidget):
    """NotWidget'ın üst kısmı - buradan tutup sürükleyince tüm not kağıdı hareket eder."""
    def __init__(self, hedef_widget: QWidget, parent=None):
        super().__init__(parent)
        self.hedef = hedef_widget
        self._baslangic: QPoint | None = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._baslangic = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._baslangic is not None:
            delta = event.position().toPoint() - self._baslangic
            self.hedef.move(self.hedef.pos() + delta)


class NotWidget(QFrame):
    """Küçük, sarı bir yapışkan not kağıdı - sürüklenebilir, serbest metin
    girilebilir, sağ üstteki X ile kapatılana kadar hangi sayfada olursa olsun
    ana pencerenin ÜZERİNDE kalır (QStackedWidget'a değil, doğrudan ana
    pencereye child olarak eklenir)."""
    kapatildi = pyqtSignal(int)  # not.id

    def __init__(self, not_obj: Not, parent=None):
        super().__init__(parent)
        self.not_obj = not_obj
        self.setFixedSize(220, 190)
        self.setStyleSheet(
            "NotWidget { background-color:#FFF3B0; border:1px solid #E3D06E; border-radius:10px; }"
        )

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        baslik = _SurukleBaslik(self)
        baslik.setFixedHeight(28)
        baslik.setStyleSheet("background-color:#F5E48A; border-top-left-radius:10px; border-top-right-radius:10px;")
        bh = QHBoxLayout(baslik)
        bh.setContentsMargins(10, 2, 6, 2)
        etiket = QLabel("📝 Not")
        etiket.setStyleSheet("background:transparent; border:none; font-weight:700; font-size:11px; color:#5c4d10;")
        bh.addWidget(etiket)
        bh.addStretch()
        kapat_btn = QPushButton("✕")
        kapat_btn.setFixedSize(20, 20)
        kapat_btn.setStyleSheet(
            "background:transparent; border:none; font-weight:700; color:#5c4d10; font-size:12px;"
        )
        kapat_btn.clicked.connect(self._kapat)
        bh.addWidget(kapat_btn)
        v.addWidget(baslik)

        from PyQt6.QtWidgets import QTextEdit
        self.metin_input = QTextEdit()
        self.metin_input.setPlainText(not_obj.metin)
        self.metin_input.setPlaceholderText("Notunuzu buraya yazın...")
        self.metin_input.setStyleSheet(
            "background:transparent; border:none; font-size:12px; color:#4a3f0a; padding:8px;"
        )
        self.metin_input.textChanged.connect(self._metin_degisti)
        v.addWidget(self.metin_input)

    def _metin_degisti(self):
        self.not_obj.metin = self.metin_input.toPlainText()

    def _kapat(self):
        self.kapatildi.emit(self.not_obj.id)
        self.hide()
        self.deleteLater()


class NotlarView(QWidget):
    """Sol menü > Notlar: yeni not oluşturma + daha önce kapatılmış notları
    tekrar açabileceğiniz liste. Notun kendisi bu sayfada değil, ana pencerenin
    üzerinde yüzen ayrı bir kağıt olarak açılır (not_ac_cb ile MainWindow'a
    devredilir)."""
    def __init__(self, state: AppState, not_ac_cb, parent=None):
        super().__init__(parent)
        self.state = state
        self.not_ac_cb = not_ac_cb

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(14)

        baslik = QLabel("Notlar")
        baslik.setObjectName("pageTitle")
        v.addWidget(baslik)
        aciklama = QLabel("Yeni bir not ekleyin - küçük bir kağıt olarak ekranın üzerinde açılır, siz kapatana kadar hangi sayfaya geçerseniz geçin görünür kalır.")
        aciklama.setObjectName("pageSubtitle")
        aciklama.setWordWrap(True)
        v.addWidget(aciklama)

        ekle_btn = QPushButton("+ Yeni Not Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setFixedWidth(200)
        ekle_btn.clicked.connect(self._yeni_not)
        ekle_satir = QHBoxLayout()
        ekle_satir.addWidget(ekle_btn)
        ekle_satir.addStretch()
        v.addLayout(ekle_satir)

        self.liste_kutu = QFrame()
        self.liste_kutu.setObjectName("masaKart")
        self.liste_v = QVBoxLayout(self.liste_kutu)
        self.liste_v.addWidget(QLabel("Kayıtlı Notlar"))
        v.addWidget(self.liste_kutu)
        v.addStretch()

        self._listeyi_kur()

    def _yeni_not(self):
        yeni = Not(id=next_id())
        self.state.notlar.append(yeni)
        self.not_ac_cb(yeni)
        self._listeyi_kur()

    def _listeyi_kur(self):
        while self.liste_v.count() > 1:
            item = self.liste_v.takeAt(1)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        if not self.state.notlar:
            bos_lbl = QLabel("Henüz not eklenmemiş.")
            bos_lbl.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
            self.liste_v.addWidget(bos_lbl)
            return

        for not_obj in self.state.notlar:
            satir = QHBoxLayout()
            onizleme = (not_obj.metin[:40] + "...") if len(not_obj.metin) > 40 else (not_obj.metin or "(boş not)")
            bilgi_lbl = QLabel(f"{not_obj.olusturma_zamani.strftime('%d.%m.%Y %H:%M')}  ·  {onizleme}")
            bilgi_lbl.setStyleSheet("font-size:12px;")
            satir.addWidget(bilgi_lbl, 1)

            ac_btn = QPushButton("Aç")
            ac_btn.setObjectName("ghostBtn")
            ac_btn.clicked.connect(lambda checked, n=not_obj: self.not_ac_cb(n))
            satir.addWidget(ac_btn)

            sil_btn = QPushButton("Sil")
            sil_btn.setObjectName("dangerBtn")
            sil_btn.clicked.connect(lambda checked, n=not_obj: self._sil(n))
            satir.addWidget(sil_btn)

            wrap = QWidget()
            wrap.setLayout(satir)
            self.liste_v.addWidget(wrap)

    def _sil(self, not_obj: Not):
        cevap = soru_sor(self, "Notu Sil", "Bu not kalıcı olarak silinsin mi?")
        if cevap == QMessageBox.StandardButton.Yes:
            self.state.notlar.remove(not_obj)
            self._listeyi_kur()

    def yenile(self):
        self._listeyi_kur()


class YapimAsamasindaView(QWidget):
    def __init__(self, baslik: str, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 24)
        b = QLabel(baslik)
        b.setObjectName("pageTitle")
        v.addWidget(b)
        lbl = QLabel("Bu sekme bir sonraki madde ile birlikte detaylandırılacak.")
        lbl.setObjectName("pageSubtitle")
        v.addWidget(lbl)
        v.addStretch()


class KarsilamaDialog(OrtalanmisDialog):
    """Program her açıldığında kısaca gösterilen karşılama ekranı - salon adını
    içerir, birkaç saniye sonra kendiliğinden kapanır (ya da tıklanarak
    hemen geçilebilir). Kendi yerel stilini taşır - hiçbir koşulda
    karanlık/görünmez açılmaz."""
    def __init__(self, salon_adi: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hoş Geldiniz")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #1A1B2E, stop:1 #2A2149); border-radius:14px; }}
            QLabel {{ color:white; background:transparent; }}
            QPushButton {{ background-color:{RENK['accent2']}; color:#0B1F1A;
                border-radius:8px; padding:10px 20px; font-weight:800; border:none; }}
            QPushButton:hover {{ background-color:#00E8BC; }}
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(30, 28, 30, 26)
        v.setSpacing(8)

        emoji = QLabel("👋")
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji.setStyleSheet("font-size:42px; background:transparent;")
        v.addWidget(emoji)

        baslik = QLabel(f"Merhaba, {salon_adi}!")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baslik.setStyleSheet("font-size:22px; font-weight:900; background:transparent;")
        baslik.setWordWrap(True)
        v.addWidget(baslik)

        alt = QLabel("GAMEHUB Lounge Management System")
        alt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        alt.setStyleSheet(f"font-size:12px; font-weight:800; color:{RENK['accent2']}; background:transparent; margin-top:2px;")
        v.addWidget(alt)

        dilek = QLabel("Bol cirolu bir gün diler 🎮")
        dilek.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dilek.setStyleSheet("font-size:13px; font-weight:600; background:transparent; margin-top:8px;")
        v.addWidget(dilek)

        v.addSpacing(10)
        tamam_btn = QPushButton("Başlayalım")
        tamam_btn.clicked.connect(self.accept)
        v.addWidget(tamam_btn)

        # Kullanıcı tıklamasa bile birkaç saniye sonra kendiliğinden kapanır -
        # işine devam etmesini bekletmemek için.
        QTimer.singleShot(3500, self.accept)


class VedaDialog(OrtalanmisDialog):
    """Program kapatılırken kısaca gösterilen veda ekranı."""
    def __init__(self, salon_adi: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Güle Güle")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #1A1B2E, stop:1 #2A2149); border-radius:14px; }}
            QLabel {{ color:white; background:transparent; }}
            QPushButton {{ background-color:{RENK['accent2']}; color:#0B1F1A;
                border-radius:8px; padding:10px 20px; font-weight:800; border:none; }}
            QPushButton:hover {{ background-color:#00E8BC; }}
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(30, 28, 30, 26)
        v.setSpacing(8)

        emoji = QLabel("🌙")
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji.setStyleSheet("font-size:42px; background:transparent;")
        v.addWidget(emoji)

        baslik = QLabel(f"Güle Güle, {salon_adi}!")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baslik.setStyleSheet("font-size:22px; font-weight:900; background:transparent;")
        baslik.setWordWrap(True)
        v.addWidget(baslik)

        dilek = QLabel("Keyifli dinlenmeler 🌟")
        dilek.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dilek.setStyleSheet("font-size:13px; font-weight:600; background:transparent; margin-top:8px;")
        v.addWidget(dilek)

        bilgi = QLabel("Tüm verileriniz güvenle kaydedildi.")
        bilgi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bilgi.setStyleSheet(f"font-size:11px; font-weight:600; background:transparent; margin-top:4px; color:{RENK['accent2']};")
        v.addWidget(bilgi)

        v.addSpacing(10)
        tamam_btn = QPushButton("Kapat")
        tamam_btn.clicked.connect(self.accept)
        v.addWidget(tamam_btn)

        QTimer.singleShot(2000, self.accept)


class YardimDialog(OrtalanmisDialog):
    """Sol menüdeki GAMEHUB logosuna tıklayınca açılır - programı kuran/satan
    kişinin iletişim bilgisini (telefon/mail) gösterir ve düzenlemeye izin verir."""
    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Yardım")
        self.setMinimumWidth(360)

        v = QVBoxLayout(self)
        v.setSpacing(12)

        ust_kart = QFrame()
        ust_kart.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #1A1B2E, stop:1 #2A2149); border-radius:12px; }"
        )
        ukv = QVBoxLayout(ust_kart)
        ukv.setContentsMargins(18, 16, 18, 16)
        logo_lbl = QLabel("🐐  GAMEHUB")
        logo_lbl.setStyleSheet(f"color:{RENK['accent2']}; font-size:16px; font-weight:800; background:transparent;")
        ukv.addWidget(logo_lbl)
        alt_lbl = QLabel("Lounge Management System")
        alt_lbl.setStyleSheet("color:rgba(255,255,255,0.6); font-size:11px; font-weight:600; background:transparent;")
        ukv.addWidget(alt_lbl)
        v.addWidget(ust_kart)

        aciklama = QLabel("Destek almak, hata bildirmek ya da yeni özellik istemek için:")
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet(f"color:{RENK['text_muted']}; font-size:12px;")
        v.addWidget(aciklama)

        v.addWidget(QLabel("Geliştirici İletişim (telefon / e-posta):"))
        self.iletisim_input = QLineEdit(state.gelistirici_iletisim)
        self.iletisim_input.setPlaceholderText("örn: 0555 555 55 55  ·  destek@ornek.com")
        v.addWidget(self.iletisim_input)

        kaydet_btn = QPushButton("Kaydet")
        kaydet_btn.setObjectName("primaryBtn")
        kaydet_btn.clicked.connect(self._kaydet)
        v.addWidget(kaydet_btn)

        kapat_btn = QPushButton("Kapat")
        kapat_btn.setObjectName("ghostBtn")
        kapat_btn.clicked.connect(self.accept)
        v.addWidget(kapat_btn)

    def _kaydet(self):
        self.state.gelistirici_iletisim = self.iletisim_input.text().strip()
        bilgilendir(self, "Kaydedildi", "İletişim bilgisi kaydedildi.")
