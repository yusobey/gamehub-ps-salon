from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit,
    QStackedWidget, QWidget, QMessageBox, QFrame, QDoubleSpinBox, QSpinBox, QTimeEdit
)
from PyQt6.QtCore import Qt, QTime
from datetime import datetime, timedelta

from core.models import Masa, AcilisModu, OdemeYontemi, MasaDurumu, KasaIslemi, Borc, next_id
from core.pricing import minutes_for_amount, round_up_5, para_ustunu_dagitimdan_dus
from core.theme import RENK
from ui.widgets import SessizDoubleSpinBox, SessizSpinBox, soru_sor, uyar, bilgilendir, OrtalanmisDialog, SessizComboBox, SessizTimeEdit


# ============================================================
#  1) BOŞ MASA -> "Masa Aç" popup
# ============================================================
class MasaAcDialog(OrtalanmisDialog):
    def __init__(self, masa: Masa, tarifeler: dict, tum_profiller: dict[str, dict], parent=None):
        super().__init__(parent)
        self.masa = masa
        self.tarifeler = tarifeler
        self.tum_profiller = tum_profiller
        self.setWindowTitle(f"{masa.ad} - Masayı Aç")
        self.setMinimumWidth(360)
        self.sonuc: dict | None = None  # {"tarife":..., "hourly":..., "mod":..., "hedef_saniye":..., "profil":...}
        self._tarife_ile_ac_secilen_profil: str | None = None

        self.stack = QStackedWidget()
        ana = QVBoxLayout(self)
        ana.addWidget(self.stack)

        self.stack.addWidget(self._ana_menu())                    # 0
        self.stack.addWidget(self._sure_ile_form())                # 1
        self.stack.addWidget(self._tutar_ile_form())                # 2
        self.stack.addWidget(self._tarife_ile_ac_profil_sayfasi())  # 3
        self.stack.addWidget(self._tarife_ile_ac_kol_sayfasi())     # 4

    def _ana_menu(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        

        for tarife_adi, ucret in self.tarifeler.items():
            btn = QPushButton(f"{tarife_adi}  ·  {ucret:.0f} ₺/saat")
            btn.setObjectName("secenekBtn")
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, t=tarife_adi, u=ucret: self._normal_ac(t, u))
            v.addWidget(btn)

        cizgi = QFrame()
        cizgi.setFrameShape(QFrame.Shape.HLine)
        v.addWidget(cizgi)

        # Üç özel açılış modu YAN YANA duruyor - alt alta gereksiz yer kaplamasın
        ozel_satir = QHBoxLayout()
        ozel_satir.setSpacing(8)

        sure_btn = QPushButton("⏱ Süre ile Aç")
        sure_btn.setObjectName("secenekBtn")
        sure_btn.setAutoDefault(False)
        sure_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        ozel_satir.addWidget(sure_btn)

        tutar_btn = QPushButton("₺ Tutar ile Aç")
        tutar_btn.setObjectName("secenekBtn")
        tutar_btn.setAutoDefault(False)
        tutar_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        ozel_satir.addWidget(tutar_btn)

        tarife_ile_btn = QPushButton("🎯 Tarife ile Aç")
        tarife_ile_btn.setObjectName("secenekBtn")
        tarife_ile_btn.setAutoDefault(False)
        tarife_ile_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        ozel_satir.addWidget(tarife_ile_btn)

        v.addLayout(ozel_satir)
        return w

    # ---------- Tarife ile Aç: başka bir tarife profili seçip o profille normal aç ----------
    def _tarife_ile_ac_profil_sayfasi(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Hangi tarifeyle açılsın?"))
        aciklama = QLabel(
            "Bu masanın kendi tarifesi dışında farklı bir tarifeyle açmak için "
            "kullanın (örn. DEV EKRAN'ı PS5 fiyatından açmak gibi)."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("color:#8b93a7; font-size:11px;")
        v.addWidget(aciklama)

        for profil_adi in self.tum_profiller.keys():
            btn = QPushButton(profil_adi)
            btn.setObjectName("secenekBtn")
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, p=profil_adi: self._tarife_ile_ac_profil_secildi(p))
            v.addWidget(btn)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _tarife_ile_ac_kol_sayfasi(self) -> QWidget:
        w = QWidget()
        self._tarife_ile_ac_kol_layout = QVBoxLayout(w)
        return w

    def _tarife_ile_ac_profil_secildi(self, profil_adi: str):
        self._tarife_ile_ac_secilen_profil = profil_adi
        layout = self._tarife_ile_ac_kol_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        layout.addWidget(QLabel(f"{profil_adi}  ·  Kol seç"))
        for kol_adi, ucret in self.tum_profiller.get(profil_adi, {}).items():
            btn = QPushButton(f"{kol_adi}  ·  {ucret:.0f} ₺/saat")
            btn.setObjectName("secenekBtn")
            btn.setAutoDefault(False)
            btn.clicked.connect(
                lambda checked, k=kol_adi, u=ucret, p=profil_adi: self._ayarla_ve_kapat(
                    k, u, AcilisModu.NORMAL, None, profil=p
                )
            )
            layout.addWidget(btn)
        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        layout.addWidget(geri)
        self.stack.setCurrentIndex(4)

    def _tarife_secim_satiri(self) -> tuple[QWidget, callable]:
        """Süre/Tutar formlarında ortak kullanılan kol seçim satırı."""
        row = QHBoxLayout()
        row.addWidget(QLabel("Tarife:"))
        combo = SessizComboBox()
        combo.addItems(list(self.tarifeler.keys()))
        row.addWidget(combo)
        w = QWidget()
        w.setLayout(row)
        return w, combo

    def _sure_ile_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Süre ile Aç"))
        secim_widget, combo = self._tarife_secim_satiri()
        v.addWidget(secim_widget)

        dk_row = QHBoxLayout()
        dk_row.addWidget(QLabel("Dakika:"))
        dk_spin = SessizSpinBox()
        dk_spin.setRange(1, 999)
        dk_spin.setValue(60)
        dk_row.addWidget(dk_spin)
        v.addLayout(dk_row)

        onay = QPushButton("Başlat")
        onay.setObjectName("primaryBtn")
        onay.setDefault(True)
        onay.setAutoDefault(True)

        def basla():
            tarife = combo.currentText()
            ucret = self.tarifeler[tarife]
            self._ayarla_ve_kapat(tarife, ucret, AcilisModu.SURE_ILE, dk_spin.value() * 60)
        onay.clicked.connect(basla)
        v.addWidget(onay)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _tutar_ile_form(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Tutar ile Aç"))
        secim_widget, combo = self._tarife_secim_satiri()
        v.addWidget(secim_widget)

        tl_row = QHBoxLayout()
        tl_row.addWidget(QLabel("Tutar (₺):"))
        tl_spin = SessizDoubleSpinBox()
        tl_spin.setRange(1, 99999)
        tl_spin.setValue(90)
        tl_spin.setDecimals(0)
        tl_row.addWidget(tl_spin)
        v.addLayout(tl_row)

        onizleme = QLabel("")
        v.addWidget(onizleme)

        def guncelle_onizleme():
            tarife = combo.currentText()
            ucret = self.tarifeler[tarife]
            dk = minutes_for_amount(ucret, tl_spin.value())
            onizleme.setText(f"≈ {int(dk)} dakika süre verilecek")
        tl_spin.valueChanged.connect(guncelle_onizleme)
        combo.currentTextChanged.connect(guncelle_onizleme)
        guncelle_onizleme()

        onay = QPushButton("Başlat")
        onay.setObjectName("primaryBtn")
        onay.setDefault(True)
        onay.setAutoDefault(True)

        def basla():
            tarife = combo.currentText()
            ucret = self.tarifeler[tarife]
            dk = minutes_for_amount(ucret, tl_spin.value())
            self._ayarla_ve_kapat(tarife, ucret, AcilisModu.TUTAR_ILE, dk * 60)
        onay.clicked.connect(basla)
        v.addWidget(onay)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _normal_ac(self, tarife, ucret):
        self._ayarla_ve_kapat(tarife, ucret, AcilisModu.NORMAL, None)

    def _ayarla_ve_kapat(self, tarife, ucret, mod, hedef_saniye, profil=None):
        self.sonuc = {"tarife": tarife, "hourly": ucret, "mod": mod, "hedef_saniye": hedef_saniye, "profil": profil}
        self.accept()


# ============================================================
#  2) AÇIK MASA -> işlem menüsü popup
# ============================================================
class MasaIslemDialog(OrtalanmisDialog):
    AKSIYONLAR = ["DEVAM_ET", "ODEME_AL", "URUN_EKLE", "KILITLE", "IPTAL_ET", "DUZENLE"]

    def __init__(self, masa: Masa, parent=None):
        super().__init__(parent)
        self.masa = masa
        self.setWindowTitle(masa.ad)
        self.setMinimumWidth(300)
        self.secilen_aksiyon: str | None = None

        v = QVBoxLayout(self)

        ust_kart = QFrame()
        ust_kart.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #E9EAEE, stop:1 #DADCE2); border-radius:12px; }"
        )
        ukv = QVBoxLayout(ust_kart)
        ukv.setContentsMargins(16, 12, 16, 12)
        ad_lbl = QLabel(masa.ad)
        ad_lbl.setStyleSheet("color:#6B6F7A; font-size:12px; font-weight:700; background:transparent; border:none; letter-spacing:1px;")
        ukv.addWidget(ad_lbl)
        tutar_lbl = QLabel(f"{masa.genel_toplam()} ₺")
        tutar_lbl.setStyleSheet("color:#00E676; font-size:26px; font-weight:800; background:transparent; border:none;")
        ukv.addWidget(tutar_lbl)
        v.addWidget(ust_kart)

        if masa.durum == MasaDurumu.ODEME_BEKLIYOR:
            bilgi = QLabel("Süre/ücret şu an donduruldu.")
            bilgi.setStyleSheet("color:#8b93a7; font-size:11px;")
            v.addWidget(bilgi)
            devam_btn = QPushButton("▶ Masaya Devam Et")
            devam_btn.setObjectName("primaryBtn")
            devam_btn.clicked.connect(lambda: self._sec("DEVAM_ET"))
            v.addWidget(devam_btn)

        odeme_btn = QPushButton("💳 Ödeme Al")
        odeme_btn.setObjectName("ghostBtn" if masa.durum == MasaDurumu.ODEME_BEKLIYOR else "odemeBtn")
        odeme_btn.clicked.connect(lambda: self._sec("ODEME_AL"))
        v.addWidget(odeme_btn)

        urun_btn = QPushButton("🛒 Ürün Ekle")
        urun_btn.setObjectName("ghostBtn")
        urun_btn.clicked.connect(lambda: self._sec("URUN_EKLE"))
        v.addWidget(urun_btn)

        kilit_metni = "🔓 Kilidi Aç" if masa.kilitli else "🔒 Kilitle"
        kilit_btn = QPushButton(kilit_metni)
        kilit_btn.setObjectName("ghostBtn")
        kilit_btn.clicked.connect(lambda: self._sec("KILITLE"))
        v.addWidget(kilit_btn)

        duzenle_btn = QPushButton("✏️ Masa Düzenle")
        duzenle_btn.setObjectName("ghostBtn")
        duzenle_btn.clicked.connect(lambda: self._sec("DUZENLE"))
        v.addWidget(duzenle_btn)

        iptal_btn = QPushButton("✕ Masayı İptal Et")
        iptal_btn.setObjectName("dangerBtn")
        iptal_btn.clicked.connect(lambda: self._sec("IPTAL_ET"))
        v.addWidget(iptal_btn)

    def _sec(self, aksiyon):
        self.secilen_aksiyon = aksiyon
        self.accept()


# ============================================================
#  3) ÖDEME AL popup
# ============================================================
class OdemeAlDialog(OrtalanmisDialog):
    def __init__(self, masa: Masa, state, parent=None):
        super().__init__(parent)
        self.masa = masa
        self.state = state
        self.setWindowTitle(f"{masa.ad} - Ödeme Al")
        self.setMinimumWidth(380)
        self.indirim = 0.0
        self.tamamlandi = False

        masa.odeme_beklemeye_al()  # süre donar, ürün eklenebilir

        v = QVBoxLayout(self)

        ust_satir = QHBoxLayout()
        detay_btn = QPushButton("Masa Detayı")
        detay_btn.setObjectName("ghostBtn")
        detay_btn.setAutoDefault(False)
        detay_btn.clicked.connect(self._detay_goster)
        ust_satir.addWidget(detay_btn)
        ust_satir.addStretch()
        urun_ekle_btn = QPushButton("+ Ürün Ekle")
        urun_ekle_btn.setObjectName("ghostBtn")
        urun_ekle_btn.setAutoDefault(False)
        urun_ekle_btn.clicked.connect(self._urun_ekle)
        ust_satir.addWidget(urun_ekle_btn)
        v.addLayout(ust_satir)

        self.toplam_lbl = QLabel()
        self.toplam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toplam_lbl.setStyleSheet(f"font-size:22px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
        v.addWidget(self.toplam_lbl)

        indirim_row = QHBoxLayout()
        indirim_row.addStretch()
        indirim_etiket = QLabel("💸  İndirim (₺):")
        indirim_etiket.setMinimumWidth(100)
        indirim_etiket.setStyleSheet("font-weight:600;")
        indirim_row.addWidget(indirim_etiket)
        self.indirim_spin = SessizDoubleSpinBox()
        self.indirim_spin.setRange(0, 99999)
        self.indirim_spin.setDecimals(0)
        self.indirim_spin.setFixedWidth(130)
        self.indirim_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indirim_spin.valueChanged.connect(self._yeniden_hesapla)
        indirim_row.addWidget(self.indirim_spin)
        indirim_row.addStretch()
        v.addLayout(indirim_row)

        odeme_baslik = QLabel("Ödeme Dağılımı")
        odeme_baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        odeme_baslik.setStyleSheet("font-weight:700; margin-top:6px;")
        v.addWidget(odeme_baslik)
        self.yontem_inputs: dict[str, QDoubleSpinBox] = {}
        ODEME_IKONLARI = {
            OdemeYontemi.NAKIT: "💵", OdemeYontemi.KART: "💳",
            OdemeYontemi.IBAN: "🏦", OdemeYontemi.BORC: "📝",
        }
        for yontem in [OdemeYontemi.NAKIT, OdemeYontemi.KART,
                       OdemeYontemi.IBAN, OdemeYontemi.BORC]:
            row = QHBoxLayout()
            row.addStretch()
            etiket = QLabel(f"{ODEME_IKONLARI[yontem]}  {yontem.value}")
            etiket.setMinimumWidth(100)
            etiket.setStyleSheet("font-weight:600;")
            row.addWidget(etiket)
            spin = SessizDoubleSpinBox()
            spin.setRange(0, 999999)
            spin.setDecimals(0)
            spin.setFixedWidth(130)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.valueChanged.connect(self._yeniden_hesapla)
            self.yontem_inputs[yontem.value] = spin
            row.addWidget(spin)
            row.addStretch()
            v.addLayout(row)

        self.kalan_lbl = QLabel()
        self.kalan_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kalan_lbl.setStyleSheet(f"font-size:15px; font-weight:800; background:transparent; border:none; margin-top:4px;")
        v.addWidget(self.kalan_lbl)

        # Önce nakit/kart girildi, geriye kalan tutardan indirim yapılacaksa tek tıkla uygula
        self.kalani_indirim_btn = QPushButton("✂  Kalanı İndirim Yap")
        self.kalani_indirim_btn.setObjectName("ghostBtn")
        self.kalani_indirim_btn.setAutoDefault(False)
        self.kalani_indirim_btn.clicked.connect(self._kalani_indirim_yap)
        v.addWidget(self.kalani_indirim_btn)

        tamamla_btn = QPushButton("Ödemeyi Tamamla")
        tamamla_btn.setObjectName("odemeBtn")
        tamamla_btn.setDefault(True)
        tamamla_btn.setAutoDefault(True)
        tamamla_btn.clicked.connect(self._tamamla)
        v.addWidget(tamamla_btn)

        vazgec_btn = QPushButton("Vazgeç")
        vazgec_btn.setObjectName("ghostBtn")
        vazgec_btn.setAutoDefault(False)
        vazgec_btn.clicked.connect(self.reject)
        v.addWidget(vazgec_btn)

        self._yeniden_hesapla()

    def _kalani_indirim_yap(self):
        """Girilen ödemeler sabit kalır; ödenecek tutarı girilen toplama indirecek kadar indirim yazar."""
        import math
        girilen = sum(s.value() for s in self.yontem_inputs.values())
        ham = self.masa.genel_toplam()
        yeni = max(0, min(math.ceil(ham - girilen), math.floor(ham)))
        self.indirim_spin.setValue(yeni)  # valueChanged -> _yeniden_hesapla

    def _toplam(self) -> float:
        ham = self.masa.genel_toplam() - self.indirim
        return max(0.0, ham)

    def _yeniden_hesapla(self):
        self.indirim = self.indirim_spin.value()
        toplam = self._toplam()
        self.toplam_lbl.setText(f"Ödenecek: {round_up_5(toplam)} ₺")

        girilen = sum(s.value() for s in self.yontem_inputs.values())
        kalan = round_up_5(toplam) - girilen
        ortak_stil = "font-size:15px; font-weight:800; background:transparent; border:none; margin-top:4px;"
        self.kalani_indirim_btn.setVisible(kalan > 0 and girilen > 0)
        if kalan > 0:
            self.kalan_lbl.setText(f"Kalan: {kalan:.0f} ₺")
            self.kalan_lbl.setStyleSheet(f"color:#f5a623; {ortak_stil}")
        elif kalan < 0:
            self.kalan_lbl.setText(f"Para Üstü: {abs(kalan):.0f} ₺")
            self.kalan_lbl.setStyleSheet(f"color:#2ecc71; {ortak_stil}")
        else:
            self.kalan_lbl.setText("Tam ödendi ✓")
            self.kalan_lbl.setStyleSheet(f"color:#2ecc71; {ortak_stil}")

    def _detay_goster(self):
        d = MasaDetayDialog(self.masa, self)
        d.exec()

    def _urun_ekle(self):
        d = UrunEkleDialog(self.masa, self.state.urun_katalogu, self)
        d.exec()
        self._yeniden_hesapla()

    def _tamamla(self):
        toplam = round_up_5(self._toplam())
        girilen = sum(s.value() for s in self.yontem_inputs.values())
        if girilen < toplam:
            uyar(self, "Eksik Ödeme", "Girilen tutar, ödenecek tutardan az olamaz.")
            return

        dagitim_ham = {k: v.value() for k, v in self.yontem_inputs.items() if v.value() > 0}
        dagitim = para_ustunu_dagitimdan_dus(dagitim_ham, toplam)
        borc_tutari = dagitim.get(OdemeYontemi.BORC.value, 0)

        ad_soyad = ""
        if borc_tutari > 0:
            bd = BorcAdSoyadDialog(self)
            if not bd.exec():
                return
            ad_soyad = bd.ad_soyad

        # Kasa işlemi - TAM SATIŞ TUTARI ciro olarak yazılır (borç kısmı dahil,
        # çünkü satış gerçekleşti; borcun sonradan TAHSİLİ ayrı ve ciroya girmez)
        urun_anlik_goruntu = [
            {"ad": u.urun_adi, "adet": u.adet, "birim_fiyat": u.birim_fiyat} for u in self.masa.urunler
        ]
        islem = KasaIslemi(
            id=next_id(), masa_adi=self.masa.ad, toplam_tutar=toplam,
            odeme_dagilimi=dagitim, indirim_tutari=self.indirim,
            acilis_zamani=self.masa.ilk_acilis_zamani,
            masa_ucreti=self.masa.guncel_masa_ucreti(),
            is_borc_tahsilati=False, is_borc_olusturma=borc_tutari > 0,
            urunler=urun_anlik_goruntu,
        )
        self.state.kasa_islemleri.append(islem)

        if borc_tutari > 0:
            self.state.borclar.append(Borc(
                id=next_id(), ad_soyad=ad_soyad, tutar=borc_tutari,
                kaynak_masa_adi=self.masa.ad, kasa_islem_id=islem.id
            ))

        self.masa.kapat_ve_sifirla()
        self.tamamlandi = True
        self.accept()


# ============================================================
#  4) Yardımcı küçük diyaloglar
# ============================================================
class BorcAdSoyadDialog(OrtalanmisDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Borç - Ad Soyad")
        self.ad_soyad = ""
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Borç kime yazılacak?"))
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ad Soyad")
        v.addWidget(self.input)
        onay = QPushButton("Tamam")
        onay.setObjectName("primaryBtn")
        onay.clicked.connect(self._tamam)
        v.addWidget(onay)

    def _tamam(self):
        if not self.input.text().strip():
            uyar(self, "Eksik", "Ad soyad giriniz.")
            return
        self.ad_soyad = self.input.text().strip()
        self.accept()


class UrunKartiChip(QFrame):
    """Tek bir ürünü temsil eden tıklanabilir kart - İSİM üstte, ORTADA ürün
    görseli (yoksa nötr bir simge), ALTTA net/koyu fiyat. Bu TEK bileşen
    tüm kategorilerde (İçecek, Yiyecek, vs.) kullanıldığı için buradaki
    düzen otomatik olarak HER YERDE aynı şekilde uygulanır. Karta tıklamak
    1 adet ekler, üzerindeki '-' butonuna basmak 1 adet azaltır. Adet sağ
    üstte rozet olarak görünür."""
    def __init__(self, urun_adi: str, fiyat: float, gorsel: str | None, mevcut_adet: int,
                 ekle_cb, azalt_cb, parent=None):
        super().__init__(parent)
        self.urun_adi = urun_adi
        self.ekle_cb = ekle_cb
        self.azalt_cb = azalt_cb
        self.setObjectName("masaKart")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(148, 172)

        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(4)

        # --- Üst satır: ürün adı (sol) + adet rozeti (sağ) ---
        ust = QHBoxLayout()
        ad_lbl = QLabel(urun_adi)
        ad_lbl.setWordWrap(True)
        ad_lbl.setStyleSheet(f"font-weight:800; font-size:13px; color:{RENK['text']}; background:transparent;")
        ust.addWidget(ad_lbl, 1)
        self.rozet = QLabel()
        self.rozet.setStyleSheet(
            "background-color:#5b8cff; color:white; font-weight:700; font-size:11px;"
            "border-radius:9px; padding:1px 8px;"
        )
        ust.addWidget(self.rozet, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(ust)

        # --- Orta: ürün görseli (varsa) - yoksa nötr bir simge ile aynı alan
        # yine de ayrılır, kart her zaman aynı düzende kalır ---
        gorsel_kutu = QLabel()
        gorsel_kutu.setFixedHeight(64)
        gorsel_kutu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gorsel_kutu.setStyleSheet(
            f"background-color:{RENK['panel_hover']}; border-radius:10px;"
        )
        if gorsel:
            from PyQt6.QtGui import QPixmap
            pix = QPixmap(gorsel)
            if not pix.isNull():
                gorsel_kutu.setPixmap(pix.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))
                gorsel_yuklendi = True
            else:
                gorsel_yuklendi = False
        else:
            gorsel_yuklendi = False
        if not gorsel_yuklendi:
            gorsel_kutu.setText("🛒")
            gorsel_kutu.setStyleSheet(
                f"background-color:{RENK['panel_hover']}; border-radius:10px; font-size:26px;"
            )
        v.addWidget(gorsel_kutu)

        # --- Alt: fiyat (NET/KOYU, artık sönük değil) + azalt butonu ---
        alt = QHBoxLayout()
        fiyat_lbl = QLabel(f"{fiyat:.0f} ₺")
        fiyat_lbl.setStyleSheet(f"color:{RENK['accent']}; font-size:15px; font-weight:800; background:transparent;")
        alt.addWidget(fiyat_lbl)
        alt.addStretch()
        eksi_btn = QPushButton("−")
        eksi_btn.setFixedSize(26, 26)
        eksi_btn.setObjectName("ghostBtn")
        eksi_btn.setStyleSheet("font-size:16px; font-weight:700; padding:0;")
        eksi_btn.clicked.connect(self._azalt_tiklandi)
        alt.addWidget(eksi_btn)
        v.addLayout(alt)

        self._adedi_guncelle(mevcut_adet)

    def _adedi_guncelle(self, adet: int):
        self.rozet.setText(str(adet))
        self.rozet.setVisible(adet > 0)

    def mousePressEvent(self, event):
        # Karta (eksi butonu hariç) tıklamak = 1 adet ekle
        self.ekle_cb(self.urun_adi)
        super().mousePressEvent(event)

    def _azalt_tiklandi(self):
        self.azalt_cb(self.urun_adi)


class UrunEkleDialog(OrtalanmisDialog):
    """Kategorili ürün ekleme ekranı. Kartlara tıkladıkça anında masa.urunler'e işlenir
    (adet birikir), '-' ile azalır. Kapat'a basınca dialog kapanır, ekleme zaten canlı yapılmıştır."""
    def __init__(self, masa: Masa, katalog: dict[str, dict[str, dict]], parent=None):
        super().__init__(parent)
        self.masa = masa
        self.katalog = katalog
        self.setWindowTitle(f"{masa.ad} - Ürün Ekle")
        self.setMinimumWidth(950)
        self.aktif_kategori = next(iter(katalog.keys()), None)

        self.ana_layout = QVBoxLayout(self)

        self.kategori_row = QHBoxLayout()
        self.ana_layout.addLayout(self.kategori_row)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(10)
        self.ana_layout.addWidget(self.grid_widget)

        # --- Sepet özeti: TEK uzun metin yerine, HER ürün KENDİ ayrı
        # kutucuğunda - "REDBULL x1, SU x1, KUTU KOLA x2" gibi karışık
        # görünmek yerine, her biri kendi net sınırlı kutusunda duruyor. ---
        self.sepet_bos_lbl = QLabel("🛒 Sepette ürün yok")
        self.sepet_bos_lbl.setStyleSheet(
            f"color:{RENK['text_muted']}; font-size:12px; font-weight:600; margin-top:6px;"
        )
        self.ana_layout.addWidget(self.sepet_bos_lbl)
        self.sepet_alani = QHBoxLayout()
        self.sepet_alani.setSpacing(8)
        self.ana_layout.addLayout(self.sepet_alani)

        kapat = QPushButton("Kapat")
        kapat.setObjectName("primaryBtn")
        kapat.setDefault(True)
        kapat.setAutoDefault(True)
        kapat.clicked.connect(self.accept)
        self.ana_layout.addWidget(kapat)

        self._kategori_butonlarini_kur()
        self._urun_gridini_kur()

    def _kategori_butonlarini_kur(self):
        while self.kategori_row.count():
            item = self.kategori_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        for kategori in self.katalog.keys():
            btn = QPushButton(kategori)
            btn.setCheckable(True)
            btn.setChecked(kategori == self.aktif_kategori)
            btn.setObjectName("primaryBtn" if kategori == self.aktif_kategori else "ghostBtn")
            # Enter'a basınca kategori değişmesin diye - Enter sadece Kapat'ı
            # tetiklemeli.
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, k=kategori: self._kategori_sec(k))
            self.kategori_row.addWidget(btn)
        self.kategori_row.addStretch()

    def _kategori_sec(self, kategori):
        self.aktif_kategori = kategori
        self._kategori_butonlarini_kur()
        self._urun_gridini_kur()

    def _hesapla_urun_sutun(self) -> int:
        """Mevcut pencere genişliğine kaç ürün çipinin (148px) yan yana
        sığacağını hesaplar - eskiden sabit 3'tü, çok dar/uzun duruyordu."""
        kart_birim = 148 + self.grid.spacing()
        kenar_boslugu = 48
        kullanilabilir = max(self.width() - kenar_boslugu, kart_birim)
        return max(1, kullanilabilir // kart_birim)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        yeni_deger = self._hesapla_urun_sutun()
        if yeni_deger != getattr(self, "_mevcut_sutun", None):
            self._mevcut_sutun = yeni_deger
            self._urun_gridini_kur()

    def _urun_gridini_kur(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        urunler = self.katalog.get(self.aktif_kategori, {})
        SUTUN = self._hesapla_urun_sutun()
        for i, (urun_adi, veri) in enumerate(urunler.items()):
            chip = UrunKartiChip(
                urun_adi, veri["fiyat"], veri.get("gorsel"), self.masa.urun_adedi(urun_adi),
                ekle_cb=self._ekle, azalt_cb=self._azalt
            )
            self.grid.addWidget(chip, i // SUTUN, i % SUTUN)

        self._sepeti_guncelle()

    def _ekle(self, urun_adi):
        fiyat = self.katalog[self.aktif_kategori][urun_adi]["fiyat"]
        self.masa.urun_ekle(urun_adi, fiyat)
        self._urun_gridini_kur()

    def _azalt(self, urun_adi):
        self.masa.urun_azalt(urun_adi)
        self._urun_gridini_kur()

    def _sepeti_guncelle(self):
        while self.sepet_alani.count():
            item = self.sepet_alani.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        if not self.masa.urunler:
            self.sepet_bos_lbl.setVisible(True)
            return
        self.sepet_bos_lbl.setVisible(False)

        for u in self.masa.urunler:
            kutu = QFrame()
            kutu.setStyleSheet(
                f"QFrame {{ background-color:{RENK['panel_hover']}; "
                f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
            )
            kh = QHBoxLayout(kutu)
            kh.setContentsMargins(10, 6, 10, 6)
            kh.setSpacing(4)
            ad_lbl = QLabel(u.urun_adi)
            ad_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text']}; background:transparent; border:none;")
            kh.addWidget(ad_lbl)
            adet_lbl = QLabel(f"×{u.adet}")
            adet_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
            kh.addWidget(adet_lbl)
            self.sepet_alani.addWidget(kutu)
        self.sepet_alani.addStretch()


# ============================================================
#  5) MASA DÜZENLE popup - Kol Değiştir / Tarife Değiştir / Süre Değiştir
# ============================================================
class MasaDuzenleDialog(OrtalanmisDialog):
    """
    - Kol Değiştir: masanın MEVCUT tarife profili içinde kol değiştirir
      (2/3/4 KOL). "Şu andan itibaren" ya da "Masa açılışından itibaren" seçilir.
    - Tarife Değiştir: FARKLI bir tarife profili (örn. DEV EKRAN masayı PS4
      fiyatından açmak) + o profilin kolu seçilir, aynı iki zamanlama seçeneği
      sunulur. Seçilen profil masaya kalıcı olarak atanır (aktif_tarife_profili).
    - Süre Değiştir: henüz netleşmedi, yer tutucu.
    """
    def __init__(self, masa: Masa, tarife_profilleri: dict[str, dict[str, float]], parent=None):
        super().__init__(parent)
        self.masa = masa
        self.tarife_profilleri = tarife_profilleri
        self.setWindowTitle(f"{masa.ad} - Masa Düzenle")
        self.setMinimumWidth(360)

        # akış-arası geçici seçim
        self._secilen_profil: str | None = None
        self._secilen_kol: str | None = None
        self._secilen_ucret: float | None = None

        self.stack = QStackedWidget()
        ana = QVBoxLayout(self)
        ana.addWidget(self.stack)

        self.stack.addWidget(self._ana_menu())                  # 0
        self.stack.addWidget(self._kol_secim_sayfasi())          # 1 - kol değiştir: kol seç
        self.stack.addWidget(self._profil_secim_sayfasi())       # 2 - tarife değiştir: profil seç
        self.stack.addWidget(self._profil_kol_secim_sayfasi())   # 3 - tarife değiştir: kol seç
        self.stack.addWidget(self._zamanlama_sayfasi())          # 4 - ortak: şu andan / açılıştan
        self.stack.addWidget(self._sure_degistir_yer_tutucu())   # 5 - NORMAL masa: başlangıç saati düzelt
        self.stack.addWidget(self._sure_ekle_formu())            # 6 - SÜRELİ masa: süreye ekleme

    # ---------- 0: ana menü ----------
    def _ana_menu(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(f"Şu an: {self.masa.aktif_tarife_profili or '-'}"))

        kol_btn = QPushButton("🔁 Kol Değiştir")
        kol_btn.setObjectName("secenekBtn")
        kol_btn.setAutoDefault(False)
        kol_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        v.addWidget(kol_btn)

        tarife_btn = QPushButton("🎯 Tarife Değiştir")
        tarife_btn.setObjectName("secenekBtn")
        tarife_btn.setAutoDefault(False)
        tarife_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        v.addWidget(tarife_btn)

        # SÜRELİ masalarda (Süre ile Aç / Tutar ile Aç) başlangıç saatini
        # değiştirmek anlamsız - o zaman "Süre Değiştir" yerine "Süre Ekle"
        # gösteriyoruz (kullanıcı: 'süreli masalarda süre değiştir yerine
        # süre eklkme olmalı'). Sadece süresiz (NORMAL) masalarda klasik
        # 'başlangıç saatini düzelt' seçeneği anlamlı, o yüzden orada kalıyor.
        if self.masa.acilis_modu == AcilisModu.NORMAL:
            sure_btn = QPushButton("⏱ Süre Değiştir")
            sure_btn.setObjectName("ghostBtn")
            sure_btn.setAutoDefault(False)
            sure_btn.clicked.connect(lambda: self.stack.setCurrentIndex(5))
            v.addWidget(sure_btn)
        else:
            sure_ekle_btn = QPushButton("⏱ Süre Ekle")
            sure_ekle_btn.setObjectName("ghostBtn")
            sure_ekle_btn.setAutoDefault(False)
            sure_ekle_btn.clicked.connect(lambda: self.stack.setCurrentIndex(6))
            v.addWidget(sure_ekle_btn)

        kapat = QPushButton("Kapat")
        kapat.setObjectName("ghostBtn")
        kapat.setAutoDefault(False)
        kapat.clicked.connect(self.reject)
        v.addWidget(kapat)
        return w

    # ---------- 1: Kol Değiştir - kol seç (mevcut profil içinde) ----------
    def _kol_secim_sayfasi(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(f"Kol Değiştir  ·  {self.masa.aktif_tarife_profili or '-'}"))

        profil_adi = self.masa.aktif_tarife_profili
        kollar = self.tarife_profilleri.get(profil_adi, {})
        for kol_adi, ucret in kollar.items():
            btn = QPushButton(f"{kol_adi}  ·  {ucret:.0f} ₺/saat")
            btn.setObjectName("secenekBtn")
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, k=kol_adi, u=ucret: self._kol_secildi(profil_adi, k, u))
            v.addWidget(btn)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _kol_secildi(self, profil_adi, kol_adi, ucret):
        self._secilen_profil = profil_adi
        self._secilen_kol = kol_adi
        self._secilen_ucret = ucret
        self.stack.setCurrentIndex(4)

    # ---------- 2: Tarife Değiştir - profil seç ----------
    def _profil_secim_sayfasi(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Hangi tarifeyle devam etsin?"))

        for profil_adi in self.tarife_profilleri.keys():
            btn = QPushButton(profil_adi)
            btn.setObjectName("secenekBtn")
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, p=profil_adi: self._profil_secildi(p))
            v.addWidget(btn)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _profil_secildi(self, profil_adi):
        self._secilen_profil = profil_adi
        # o profilin kol sayfasını canlı doldur
        self._profil_kol_sayfasini_doldur(profil_adi)
        self.stack.setCurrentIndex(3)

    # ---------- 3: Tarife Değiştir - seçilen profilde kol seç ----------
    def _profil_kol_secim_sayfasi(self) -> QWidget:
        w = QWidget()
        self._profil_kol_layout = QVBoxLayout(w)
        return w

    def _profil_kol_sayfasini_doldur(self, profil_adi):
        layout = self._profil_kol_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        layout.addWidget(QLabel(f"{profil_adi}  ·  Kol seç"))
        for kol_adi, ucret in self.tarife_profilleri.get(profil_adi, {}).items():
            btn = QPushButton(f"{kol_adi}  ·  {ucret:.0f} ₺/saat")
            btn.setObjectName("secenekBtn")
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, k=kol_adi, u=ucret, p=profil_adi: self._kol_secildi(p, k, u))
            layout.addWidget(btn)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        layout.addWidget(geri)

    # ---------- 4: ortak zamanlama seçimi ----------
    def _zamanlama_sayfasi(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        self._zamanlama_baslik = QLabel("")
        self._zamanlama_baslik.setWordWrap(True)
        v.addWidget(self._zamanlama_baslik)

        simdi_btn = QPushButton("▶ Şu Andan İtibaren")
        simdi_btn.setObjectName("secenekBtn")
        simdi_btn.setAutoDefault(False)
        simdi_btn.clicked.connect(lambda: self._uygula(acilistan=False))
        v.addWidget(simdi_btn)
        simdi_aciklama = QLabel("O ana kadarki tutar sabit kalır, yeni ücret bu andan itibaren işlemeye başlar.")
        simdi_aciklama.setWordWrap(True)
        simdi_aciklama.setStyleSheet("color:#8b93a7; font-size:11px;")
        v.addWidget(simdi_aciklama)

        acilis_btn = QPushButton("⏮ Masa Açılışından İtibaren")
        acilis_btn.setObjectName("secenekBtn")
        acilis_btn.setAutoDefault(False)
        acilis_btn.clicked.connect(lambda: self._uygula(acilistan=True))
        v.addWidget(acilis_btn)
        acilis_aciklama = QLabel("Geçen sürenin TAMAMI yeni ücrete göre yeniden hesaplanır (öncekiler iptal olur).")
        acilis_aciklama.setWordWrap(True)
        acilis_aciklama.setStyleSheet("color:#8b93a7; font-size:11px;")
        v.addWidget(acilis_aciklama)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _uygula(self, acilistan: bool):
        self._zamanlama_baslik.setText(f"Seçim: {self._secilen_kol}  ·  {self._secilen_ucret:.0f} ₺/saat")
        self.masa.aktif_tarife_profili = self._secilen_profil
        if acilistan:
            self.masa.kol_degistir_acilistan(self._secilen_kol, self._secilen_ucret)
        else:
            self.masa.kol_degistir_simdiden(self._secilen_kol, self._secilen_ucret)
        self.accept()

    # ---------- 5: Süre Değiştir - başlangıç saatini düzelt ----------
    def _sure_degistir_yer_tutucu(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Başlangıç Saatini Düzelt"))
        aciklama = QLabel(
            "Masa açılırken unutulduysa, müşterinin GERÇEKTE geldiği saati girin - "
            "tutar/süre o saate göre güncel saate orantılı yeniden hesaplanır."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("color:#8b93a7; font-size:11px;")
        v.addWidget(aciklama)

        self._saat_input = SessizTimeEdit()
        aktif_seg = self.masa.segments[-1] if self.masa.segments else None
        if aktif_seg:
            self._saat_input.setTime(QTime(aktif_seg.start_time.hour, aktif_seg.start_time.minute))
        else:
            simdi = datetime.now()
            self._saat_input.setTime(QTime(simdi.hour, simdi.minute))
        self._saat_input.setDisplayFormat("HH:mm")
        self._saat_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._saat_input.setStyleSheet(
            f"font-size:28px; font-weight:800; color:{RENK['accent']}; "
            f"padding:14px; border:1.5px solid {RENK['border_strong']}; border-radius:10px;"
        )
        v.addWidget(self._saat_input)

        kaydet = QPushButton("Kaydet")
        kaydet.setObjectName("primaryBtn")
        kaydet.setDefault(True)
        kaydet.setAutoDefault(True)
        kaydet.clicked.connect(self._baslangic_saatini_kaydet)
        v.addWidget(kaydet)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _baslangic_saatini_kaydet(self):
        secilen = self._saat_input.time()
        simdi = datetime.now()
        yeni_baslangic = simdi.replace(hour=secilen.hour(), minute=secilen.minute(), second=0, microsecond=0)
        if yeni_baslangic > simdi:
            # gece yarisini gecen durum (orn. 23:50 acilip 00:05'te duzeltiliyor) -
            # girilen saat "simdiden ileri" cikiyorsa bir onceki gune ait kabul et
            yeni_baslangic -= timedelta(days=1)
        self.masa.baslangic_saatini_degistir(yeni_baslangic)
        self.accept()

    # ---------- 6: Süre Ekle - SÜRELİ masalarda (Süre ile Aç / Tutar ile Aç) ----------
    def _sure_ekle_formu(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Süre Ekle"))
        aciklama = QLabel(
            "Müşteri süresini uzatmak isterse buradan ekleyin - başlangıç saati ve "
            "o ana kadar biriken ücret DEĞİŞMEZ, sadece süre dolum vakti ötelenir; "
            "ücret her zamanki gibi geçen süreye göre birikmeye devam eder."
        )
        aciklama.setWordWrap(True)
        aciklama.setStyleSheet("color:#8b93a7; font-size:11px;")
        v.addWidget(aciklama)

        self._kalan_bilgi_lbl = QLabel()
        self._kalan_bilgi_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._kalan_bilgi_lbl.setStyleSheet(f"font-size:13px; font-weight:700; color:{RENK['text_muted']};")
        kalan = self.masa.kalan_geri_sayim_saniye()
        if kalan is not None:
            kalan_dk = int(kalan // 60)
            self._kalan_bilgi_lbl.setText(f"Şu an kalan süre: ~{kalan_dk} dakika")
        v.addWidget(self._kalan_bilgi_lbl)

        dk_row = QHBoxLayout()
        dk_row.addWidget(QLabel("Eklenecek Süre (dk):"))
        self._sure_ekle_spin = SessizSpinBox()
        self._sure_ekle_spin.setRange(1, 999)
        self._sure_ekle_spin.setValue(30)
        self._sure_ekle_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sure_ekle_spin.setFixedWidth(100)
        dk_row.addWidget(self._sure_ekle_spin)
        v.addLayout(dk_row)

        hizli_row = QHBoxLayout()
        for dk in (15, 30, 60):
            hizli_btn = QPushButton(f"+{dk} dk")
            hizli_btn.setObjectName("ghostBtn")
            hizli_btn.setAutoDefault(False)
            hizli_btn.clicked.connect(lambda checked, d=dk: self._sure_ekle_spin.setValue(d))
            hizli_row.addWidget(hizli_btn)
        v.addLayout(hizli_row)

        ekle_btn = QPushButton("Süreyi Ekle")
        ekle_btn.setObjectName("primaryBtn")
        ekle_btn.setDefault(True)
        ekle_btn.setAutoDefault(True)
        ekle_btn.clicked.connect(self._sure_ekle_kaydet)
        v.addWidget(ekle_btn)

        geri = QPushButton("← Geri")
        geri.setObjectName("ghostBtn")
        geri.setAutoDefault(False)
        geri.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        v.addWidget(geri)
        return w

    def _sure_ekle_kaydet(self):
        dk = self._sure_ekle_spin.value()
        self.masa.sure_ekle(dk * 60)
        self.accept()


class AlisverisDialog(OrtalanmisDialog):
    """Anasayfa > Alışveriş kartı: masa açmadan direkt ürün satışı. Ürün seçimi
    UrunEkleDialog ile aynı kategori/kart mantığını kullanır, ama masa yerine
    kendi geçici sepetine (self.sepet) ekler. Ödeme alınca KasaIslemi olarak
    'Masa Dışı Alışveriş' etiketiyle kaydedilir - Gün Sonu/Son İşlemler'de
    normal bir satış gibi görünür, sadece masa_ucreti her zaman 0'dır.

    ÖNEMLİ: self.sepet, state.masasiz_sepet sözlüğünün KENDİSİDİR (referans
    olarak atanır, kopyası değil) - bu yüzden pencere ödemesiz kapatılsa bile
    (müşteri ürünü seçip hemen ödemeyip sonra gelebilir) sepet SİLİNMEZ, bir
    dahaki açılışta aynen kaldığı yerden devam eder. Sepet SADECE ödeme
    tamamlanınca ya da kullanıcı elle boşaltınca sıfırlanır."""
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.sepet: dict = state.masasiz_sepet
        self.indirim: float = state.masasiz_indirim
        self.setWindowTitle("Alışveriş - Masa Dışı Satış")
        self.setMinimumWidth(950)
        self.tamamlandi = False

        self.stack = QStackedWidget()
        ana = QVBoxLayout(self)
        ana.addWidget(self.stack)

        self.stack.addWidget(self._urun_sayfasi())     # 0
        self.stack.addWidget(self._odeme_sayfasi())    # 1

    # ---------------- Ürün seçim sayfası ----------------
    def _urun_sayfasi(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Ürün Seç"))

        self.kategori_row = QHBoxLayout()
        v.addLayout(self.kategori_row)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(10)
        v.addWidget(self.grid_widget)

        self.sepet_bos_lbl = QLabel("🛒 Sepet boş")
        self.sepet_bos_lbl.setStyleSheet(
            f"color:{RENK['text_muted']}; font-size:12px; font-weight:600; margin-top:6px;"
        )
        v.addWidget(self.sepet_bos_lbl)
        self.sepet_alani = QHBoxLayout()
        self.sepet_alani.setSpacing(8)
        v.addLayout(self.sepet_alani)

        # ÖNEMLİ: bu etiket ürün sayfasının KENDİ toplamı - ödeme sayfasındaki
        # "Ödenecek" etiketiyle (self._odeme_toplam_lbl) AYNI isim/değişken
        # kullanılmıyor. Eskiden ikisi de "self.toplam_lbl" idi; ödeme
        # sayfasına bir kez gidilince bu değişken o etikete atanıp kalıyordu,
        # bu yüzden ürün sayfasına geri dönüp ürün ekleyip/çıkarınca buradaki
        # etiket bir daha GÜNCELLENMİYORDU (bildirilen hata).
        self.urun_sayfasi_toplam_lbl = QLabel("Toplam: 0 ₺")
        self.urun_sayfasi_toplam_lbl.setStyleSheet("font-size:16px; font-weight:800;")
        v.addWidget(self.urun_sayfasi_toplam_lbl)

        odeme_btn = QPushButton("Ödemeye Geç")
        odeme_btn.setObjectName("primaryBtn")
        odeme_btn.setDefault(True)
        odeme_btn.setAutoDefault(True)
        odeme_btn.clicked.connect(self._odemeye_gec)
        v.addWidget(odeme_btn)

        kapat_btn = QPushButton("Vazgeç")
        kapat_btn.setObjectName("ghostBtn")
        kapat_btn.setAutoDefault(False)
        kapat_btn.clicked.connect(self.reject)
        v.addWidget(kapat_btn)

        self._aktif_kategori = next(iter(self.state.urun_katalogu.keys()), None)
        self._kategori_butonlarini_kur()
        self._urun_gridini_kur()
        return w

    def _kategori_butonlarini_kur(self):
        while self.kategori_row.count():
            item = self.kategori_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        for kategori in self.state.urun_katalogu.keys():
            btn = QPushButton(kategori)
            btn.setObjectName("primaryBtn" if kategori == self._aktif_kategori else "ghostBtn")
            # ÖNEMLİ: Enter'a basınca bu kategori butonlarından biri
            # tetiklenmesin diye (bu, "Enter'a basınca alakasız bir sekmeye
            # geçiyor" hissine sebep oluyordu) - Enter SADECE asıl işlem
            # butonuna (Ödemeye Geç / Ödemeyi Tamamla) gitmeli.
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda checked, k=kategori: self._kategori_sec(k))
            self.kategori_row.addWidget(btn)
        self.kategori_row.addStretch()

    def _kategori_sec(self, kategori):
        self._aktif_kategori = kategori
        self._kategori_butonlarini_kur()
        self._urun_gridini_kur()

    def _hesapla_urun_sutun(self) -> int:
        """Mevcut pencere genişliğine kaç ürün çipinin (148px) yan yana
        sığacağını hesaplar - eskiden sabit 3'tü, çok dar/uzun duruyordu."""
        kart_birim = 148 + self.grid.spacing()
        kenar_boslugu = 48
        kullanilabilir = max(self.width() - kenar_boslugu, kart_birim)
        return max(1, kullanilabilir // kart_birim)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        yeni_deger = self._hesapla_urun_sutun()
        if yeni_deger != getattr(self, "_mevcut_sutun", None):
            self._mevcut_sutun = yeni_deger
            self._urun_gridini_kur()

    def _urun_gridini_kur(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()
        urunler = self.state.urun_katalogu.get(self._aktif_kategori, {})
        SUTUN = self._hesapla_urun_sutun()
        for i, (urun_adi, veri) in enumerate(urunler.items()):
            mevcut_adet = self.sepet.get(urun_adi, {}).get("adet", 0)
            chip = UrunKartiChip(
                urun_adi, veri["fiyat"], veri.get("gorsel"), mevcut_adet,
                ekle_cb=self._ekle, azalt_cb=self._azalt
            )
            self.grid.addWidget(chip, i // SUTUN, i % SUTUN)
        self._sepeti_guncelle()

    def _ekle(self, urun_adi):
        fiyat = self.state.urun_katalogu[self._aktif_kategori][urun_adi]["fiyat"]
        kayit = self.sepet.setdefault(urun_adi, {"adet": 0, "birim_fiyat": fiyat})
        kayit["adet"] += 1
        self._urun_gridini_kur()

    def _azalt(self, urun_adi):
        if urun_adi in self.sepet:
            self.sepet[urun_adi]["adet"] -= 1
            if self.sepet[urun_adi]["adet"] <= 0:
                del self.sepet[urun_adi]
        self._urun_gridini_kur()

    def _sepet_toplami(self) -> float:
        return sum(v["adet"] * v["birim_fiyat"] for v in self.sepet.values())

    def _sepeti_guncelle(self):
        while self.sepet_alani.count():
            item = self.sepet_alani.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        if not self.sepet:
            self.sepet_bos_lbl.setText("🛒 Sepet boş - ürün seçin")
            self.sepet_bos_lbl.setVisible(True)
        else:
            self.sepet_bos_lbl.setVisible(False)
            for ad, v in self.sepet.items():
                kutu = QFrame()
                kutu.setStyleSheet(
                    f"QFrame {{ background-color:{RENK['panel_hover']}; "
                    f"border:1px solid {RENK['border_strong']}; border-radius:8px; }}"
                )
                kh = QHBoxLayout(kutu)
                kh.setContentsMargins(10, 6, 10, 6)
                kh.setSpacing(4)
                ad_lbl = QLabel(ad)
                ad_lbl.setStyleSheet(f"font-size:12px; font-weight:700; color:{RENK['text']}; background:transparent; border:none;")
                kh.addWidget(ad_lbl)
                adet_lbl = QLabel(f"×{v['adet']}")
                adet_lbl.setStyleSheet(f"font-size:14px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
                kh.addWidget(adet_lbl)
                self.sepet_alani.addWidget(kutu)
            self.sepet_alani.addStretch()

        self.urun_sayfasi_toplam_lbl.setText(f"Toplam: {self._sepet_toplami():.0f} ₺")

    def _odemeye_gec(self):
        if not self.sepet:
            uyar(self, "Sepet Boş", "Ödemeye geçmeden önce en az bir ürün ekleyin.")
            return
        self._odeme_sayfasini_doldur()
        self.stack.setCurrentIndex(1)

    # ---------------- Ödeme sayfası ----------------
    def _odeme_sayfasi(self) -> QWidget:
        w = QWidget()
        self._odeme_v = QVBoxLayout(w)
        return w

    def _odeme_sayfasini_doldur(self):
        layout = self._odeme_v
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)  # HEMEN kopar - deleteLater() gecikmeli
                w.deleteLater()

        toplam_ham = self._sepet_toplami()
        self.toplam_lbl = QLabel(f"Ödenecek: {round_up_5(max(0.0, toplam_ham - self.indirim))} ₺")
        self.toplam_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toplam_lbl.setStyleSheet(f"font-size:22px; font-weight:800; color:{RENK['accent']}; background:transparent; border:none;")
        layout.addWidget(self.toplam_lbl)

        indirim_row = QHBoxLayout()
        indirim_row.addStretch()
        indirim_etiket = QLabel("💸  İndirim (₺):")
        indirim_etiket.setMinimumWidth(100)
        indirim_etiket.setStyleSheet("font-weight:600;")
        indirim_row.addWidget(indirim_etiket)
        self.indirim_spin = SessizDoubleSpinBox()
        self.indirim_spin.setRange(0, 99999)
        self.indirim_spin.setDecimals(0)
        self.indirim_spin.setFixedWidth(130)
        self.indirim_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indirim_spin.setValue(self.indirim)
        self.indirim_spin.valueChanged.connect(self._indirim_degisti)
        indirim_row.addWidget(self.indirim_spin)
        indirim_row.addStretch()
        layout.addLayout(indirim_row)

        odeme_baslik = QLabel("Ödeme Dağılımı")
        odeme_baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        odeme_baslik.setStyleSheet("font-weight:700; margin-top:6px;")
        layout.addWidget(odeme_baslik)

        ODEME_IKONLARI = {"NAKİT": "💵", "KART": "💳", "İBAN": "🏦", "BORÇ": "📝"}
        self.yontem_inputs: dict[str, SessizDoubleSpinBox] = {}
        for yontem in ["NAKİT", "KART", "İBAN", "BORÇ"]:
            satir = QHBoxLayout()
            satir.addStretch()
            etiket = QLabel(f"{ODEME_IKONLARI[yontem]}  {yontem}")
            etiket.setMinimumWidth(100)
            etiket.setStyleSheet("font-weight:600;")
            satir.addWidget(etiket)
            spin = SessizDoubleSpinBox()
            spin.setRange(0, 999999)
            spin.setDecimals(0)
            spin.setFixedWidth(130)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.valueChanged.connect(self._kalan_guncelle)
            satir.addWidget(spin)
            satir.addStretch()
            wrap = QWidget()
            wrap.setLayout(satir)
            layout.addWidget(wrap)
            self.yontem_inputs[yontem] = spin

        self.kalan_lbl = QLabel()
        self.kalan_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kalan_lbl.setStyleSheet("font-size:15px; font-weight:800; background:transparent; border:none; margin-top:4px;")
        layout.addWidget(self.kalan_lbl)

        tamamla_btn = QPushButton("Ödemeyi Tamamla")
        tamamla_btn.setObjectName("odemeBtn")
        tamamla_btn.setDefault(True)
        tamamla_btn.setAutoDefault(True)
        tamamla_btn.clicked.connect(self._tamamla)
        layout.addWidget(tamamla_btn)

        geri_btn = QPushButton("← Geri (Ürünlere Dön)")
        geri_btn.setObjectName("ghostBtn")
        geri_btn.setAutoDefault(False)
        geri_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(geri_btn)

        self._kalan_guncelle()

    def _indirim_degisti(self):
        self.indirim = self.indirim_spin.value()
        self.state.masasiz_indirim = self.indirim
        toplam_ham = self._sepet_toplami()
        self.toplam_lbl.setText(f"Ödenecek: {round_up_5(max(0.0, toplam_ham - self.indirim))} ₺")
        self._kalan_guncelle()

    def _kalan_guncelle(self):
        toplam = max(0.0, self._sepet_toplami() - self.indirim)
        girilen = sum(s.value() for s in self.yontem_inputs.values())
        kalan = round_up_5(toplam) - girilen
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
        toplam = round_up_5(max(0.0, self._sepet_toplami() - self.indirim))
        girilen = sum(s.value() for s in self.yontem_inputs.values())
        if girilen < toplam:
            uyar(self, "Eksik Ödeme", "Girilen tutar, ödenecek tutardan az olamaz.")
            return

        dagitim_ham = {k: v.value() for k, v in self.yontem_inputs.items() if v.value() > 0}
        dagitim = para_ustunu_dagitimdan_dus(dagitim_ham, toplam)
        borc_tutari = dagitim.get("BORÇ", 0)

        # NOT: Masa ödemesindeki (OdemeAlDialog) BORÇ mantığıyla AYNI -
        # dağılımda BORÇ tutarı varsa, kime yazılacağını (ad soyad) sorup
        # Borç kaydı oluşturuyoruz. Ad soyad girilmeden vazgeçilirse satış
        # TAMAMLANMAZ (kullanıcı ödeme ekranında kalır, tekrar deneyebilir).
        ad_soyad = ""
        if borc_tutari > 0:
            bd = BorcAdSoyadDialog(self)
            if not bd.exec():
                return
            ad_soyad = bd.ad_soyad

        urun_anlik_goruntu = [
            {"ad": ad, "adet": v["adet"], "birim_fiyat": v["birim_fiyat"]} for ad, v in self.sepet.items()
        ]
        islem = KasaIslemi(
            id=next_id(), masa_adi="Masa Dışı Alışveriş", toplam_tutar=toplam,
            odeme_dagilimi=dagitim, indirim_tutari=self.indirim, masa_ucreti=0.0,
            is_borc_tahsilati=False, is_borc_olusturma=borc_tutari > 0,
            urunler=urun_anlik_goruntu,
        )
        self.state.kasa_islemleri.append(islem)

        if borc_tutari > 0:
            self.state.borclar.append(Borc(
                id=next_id(), ad_soyad=ad_soyad, tutar=borc_tutari,
                kaynak_masa_adi="Masa Dışı Alışveriş", kasa_islem_id=islem.id
            ))
        # Satış tamamlandı - kalıcı sepeti (state.masasiz_sepet) ve indirimi
        # şimdi boşaltıyoruz. self.sepet.clear() kullanıyoruz (yeni bir
        # sözlük atamak değil) çünkü self.sepet zaten state.masasiz_sepet ile
        # AYNI nesne - clear() ile ikisi birden boşalır.
        self.sepet.clear()
        self.state.masasiz_indirim = 0.0
        self.indirim = 0.0
        self.tamamlandi = True
        self.accept()


class MasaDetayDialog(OrtalanmisDialog):
    """Ürünler + masa tutarı + kol/tarife değişim geçmişi (saatiyle)."""
    def __init__(self, masa: Masa, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{masa.ad} - Detay")
        self.setMinimumWidth(380)
        v = QVBoxLayout(self)
        v.setSpacing(14)

        # --- Üst kart: masa adı + toplam tutar (titanyum gri zemin, yeşil
        # rakam - koyu/lacivert değil, daha zarif ve "premium" bir gri his) ---
        ust_kart = QFrame()
        ust_kart.setStyleSheet(
            "QFrame { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #E9EAEE, stop:1 #DADCE2); border-radius:12px; }"
        )
        ukv = QVBoxLayout(ust_kart)
        ukv.setContentsMargins(18, 14, 18, 14)
        ad_lbl = QLabel(masa.ad)
        ad_lbl.setStyleSheet("color:#6B6F7A; font-size:11px; font-weight:700; background:transparent; letter-spacing:1px;")
        ukv.addWidget(ad_lbl)
        tutar_lbl = QLabel(f"{masa.guncel_masa_ucreti()} ₺")
        tutar_lbl.setStyleSheet("color:#00E676; font-size:28px; font-weight:800; background:transparent;")
        ukv.addWidget(tutar_lbl)
        v.addWidget(ust_kart)

        # --- Ürünler kartı: başlıkta TOPLAM ürün tutarı, her satırda adet VE
        # birim fiyat (sadece satır toplamı değil) ---
        urun_kart = QFrame()
        urun_kart.setObjectName("masaKart")
        ukv2 = QVBoxLayout(urun_kart)
        urun_toplami = sum(u.toplam for u in masa.urunler)
        urun_baslik = QLabel(f"🛒  Ürünler  —  {urun_toplami:.0f} ₺")
        urun_baslik.setStyleSheet(f"font-size:13px; font-weight:800; color:{RENK['text']};")
        ukv2.addWidget(urun_baslik)
        if masa.urunler:
            for u in masa.urunler:
                satir = QHBoxLayout()
                ad = QLabel(f"{u.urun_adi}  ×{u.adet}")
                ad.setStyleSheet(f"font-size:12px; color:{RENK['text']}; font-weight:600;")
                satir.addWidget(ad)
                satir.addStretch()
                birim = QLabel(f"{u.birim_fiyat:.0f} ₺/adet")
                birim.setStyleSheet(f"font-size:11px; color:{RENK['text_muted']}; font-weight:600;")
                satir.addWidget(birim)
                ukv2.addLayout(satir)
        else:
            bos = QLabel("Ürün satışı yok")
            bos.setStyleSheet(f"font-size:12px; color:{RENK['text_muted']};")
            ukv2.addWidget(bos)
        v.addWidget(urun_kart)

        # --- Kol/Tarife değişim geçmişi kartı ---
        gecmis_kart = QFrame()
        gecmis_kart.setObjectName("masaKart")
        gkv = QVBoxLayout(gecmis_kart)
        gecmis_baslik = QLabel("🔁  Kol / Tarife Değişimleri")
        gecmis_baslik.setStyleSheet(f"font-size:13px; font-weight:800; color:{RENK['text']};")
        gkv.addWidget(gecmis_baslik)
        if masa.kol_degisim_gecmisi:
            for k in masa.kol_degisim_gecmisi:
                satir = QLabel(f"{k.zaman.strftime('%H:%M')}  ·  {k.eski_tarife} → {k.yeni_tarife}")
                satir.setWordWrap(True)
                satir.setStyleSheet(f"font-size:11px; color:{RENK['text_muted']}; font-weight:600;")
                gkv.addWidget(satir)
        else:
            bos2 = QLabel("Değişiklik yok")
            bos2.setStyleSheet(f"font-size:12px; color:{RENK['text_muted']};")
            gkv.addWidget(bos2)
        v.addWidget(gecmis_kart)

        kapat = QPushButton("Kapat")
        kapat.setObjectName("ghostBtn")
        kapat.clicked.connect(self.accept)
        v.addWidget(kapat)
