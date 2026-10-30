import sys
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPalette, QColor, QGuiApplication

from core.theme import QSS, RENK, temayi_uygula
from core import kayit
from core.bildirim import BildirimYoneticisi
from ui.bildirim_ayarlari import BildirimAyarlariView
from ui.giris import giris_akisi
from ui.veri_sayfasi import VeriSayfasi, GuncellemeDialog
from core import guncelleme
from core.surum import GUNCELLEME_ADRESI
from core import hesap
from ui.widgets import soru_sor
from PyQt6.QtWidgets import QMessageBox
from core.models import MasaDurumu
from ui.views import (
    Sidebar, HomeView, BorclarView, SalonAdiView, MasaKayitlariView,
    UrunlerView, KasaView, SonIslemlerView,
    NotlarView, NotWidget, YapimAsamasindaView, KarsilamaDialog, VedaDialog, YardimDialog
)

AY_ADLARI_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUN_ADLARI_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PS Salon Otomasyonu")
        self.resize(1280, 800)

        self.state = kayit.yukle_veya_yeni()
        self._otomatik_kayit_sayaci = 0

        merkez = QWidget()
        self.setCentralWidget(merkez)
        yatay = QHBoxLayout(merkez)
        yatay.setContentsMargins(0, 0, 0, 0)
        yatay.setSpacing(0)

        self.sidebar = Sidebar(self.state)
        yatay.addWidget(self.sidebar)

        # --- Sağ taraf: üstte ince bir başlık çubuğu (canlı tarih/saat) +
        # altında sayfa alanı ---
        sag_dikey = QVBoxLayout()
        sag_dikey.setContentsMargins(0, 0, 0, 0)
        sag_dikey.setSpacing(0)

        ust_cubuk = QWidget()
        ust_cubuk.setStyleSheet(f"background-color:{RENK['bg']};")
        ust_cubuk_h = QHBoxLayout(ust_cubuk)
        ust_cubuk_h.setContentsMargins(24, 10, 24, 2)
        ust_cubuk_h.addStretch()
        self.tarih_saat_lbl = QLabel()
        self.tarih_saat_lbl.setStyleSheet(
            f"color:{RENK['text']}; font-size:18px; font-weight:800; background:transparent;"
        )
        ust_cubuk_h.addWidget(self.tarih_saat_lbl)
        sag_dikey.addWidget(ust_cubuk)

        self.sayfalar = QStackedWidget()
        sag_dikey.addWidget(self.sayfalar)

        sag_widget = QWidget()
        sag_widget.setLayout(sag_dikey)
        yatay.addWidget(sag_widget, 1)

        # --- Birim (grup) sayfaları: her biri (PlayStation, Bilardo, VR gibi)
        # kendi ayrı HomeView'ına sahip - "_grup_sayfalarini_kur" ile
        # state.gruplar'a göre dinamik olarak oluşturulur/senkronize edilir. ---
        self.grup_sayfalari: dict[str, HomeView] = {}
        self.sayfa_map: dict[str, QWidget] = {}
        self._grup_sayfalarini_kur()

        self.borclar_view = BorclarView(self.state)
        self.salon_adi_view = SalonAdiView(self.state, self._tum_birim_sayfalarini_yenile)
        self.masa_kayitlari_view = MasaKayitlariView(self.state, self._tum_birim_sayfalarini_yenile)
        self.bildirim_ayar_view = BildirimAyarlariView(self.state, lambda: getattr(self, "bildirim", None))
        self.veri_view = VeriSayfasi(self.state)
        self.urunler_view = UrunlerView(self.state)
        self.kasa_view = KasaView(self.state)
        self.son_islemler_view = SonIslemlerView(self.state)
        self.acik_notlar: dict[int, NotWidget] = {}  # not.id -> NotWidget (kapatılmayanlar burada kalır)
        self.notlar_view = NotlarView(self.state, self.not_ac)

        self.sayfa_map.update({
            "kasa": self.kasa_view,
            "borclar": self.borclar_view,
            "son_islemler": self.son_islemler_view,
            "urunler": self.urunler_view,
            "salon_adi": self.salon_adi_view,
            "bildirim": self.bildirim_ayar_view,
            "veri": self.veri_view,
            "masa_kayitlari": self.masa_kayitlari_view,
            "notlar": self.notlar_view,
        })
        for key in ["kasa", "borclar", "son_islemler", "urunler", "salon_adi", "bildirim", "veri", "masa_kayitlari", "notlar"]:
            self.sayfalar.addWidget(self.sayfa_map[key])

        self.sidebar.sekme_secildi.connect(self._sekme_degisti)
        self.sidebar.yardim_istendi.connect(self._yardim_ac)
        self.sidebar.cikis_istendi.connect(self._oturumu_kapat)

        # Başlangıçta gösterilecek sayfa: varsa İLK birim, yoksa (henüz hiç
        # grup eklenmemişse) kullanıcıyı doğrudan grup ekleyebileceği
        # "Masa ve Tarife Kayıtları" sayfasına yönlendiriyoruz.
        if self.state.gruplar:
            ilk_key = f"grup:{self.state.gruplar[0]}"
            self.sayfalar.setCurrentWidget(self.sayfa_map[ilk_key])
            self.sidebar._sec(ilk_key)
        else:
            self.sayfalar.setCurrentWidget(self.masa_kayitlari_view)
            self.sidebar._sec("masa_kayitlari")

        self._tarih_saat_guncelle()

        # Süreli masa dolunca sağ-alt bildirim + ses (uygulama arka planda olsa da)
        self.bildirim = BildirimYoneticisi(self, QApplication.windowIcon(), self.state, self)
        self._uyari_caldi = False
        self._bildirilen_masalar: dict = {}  # anahtar -> son bildirim zamanı (monotonic)

        # Canlı güncelleme: süre/tutar sıçramalarının GECİKMESİZ görünmesi için
        # sık aralıkla (250ms) tazeleniyor - dakika/saniye sınırını asla kaçırmaz.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._canli_guncelle)
        self.timer.start(250)

    def _grup_sayfalarini_kur(self):
        """state.gruplar'a göre her birim (grup) için bir HomeView sayfası
        oluşturur/senkronize eder - yeni birim eklenince YENİ bir sayfa+
        sidebar butonu otomatik çıkar, birim silinince kaldırılır. PlayStation,
        Bilardo, VR gibi farklı birimler böylece HİÇ karışmadan, kendi ayrı
        sayfalarında gösterilir - ciro/kasa ise ORTAK kalır (bu fonksiyon
        SADECE görüntüleme sayfalarını etkiler, finansal veriyi değil)."""
        mevcut = set(self.state.gruplar)
        var_olanlar = set(self.grup_sayfalari.keys())

        for grup in var_olanlar - mevcut:
            sayfa = self.grup_sayfalari.pop(grup)
            self.sayfalar.removeWidget(sayfa)
            self.sayfa_map.pop(f"grup:{grup}", None)
            sayfa.deleteLater()

        for grup in mevcut - var_olanlar:
            sayfa = HomeView(self.state, grup)
            self.grup_sayfalari[grup] = sayfa
            self.sayfa_map[f"grup:{grup}"] = sayfa
            self.sayfalar.addWidget(sayfa)

        self.sidebar.gruplari_kur()

    def _tum_birim_sayfalarini_yenile(self, zorla_yeniden_kur: bool = False):
        """SalonAdiView (salon adı değişince) ve MasaKayitlariView (masa/grup
        ekleme-silme-yeniden adlandırma sonrası) tarafından çağrılır - TÜM
        birim sayfalarını (ve gerekirse birim listesinin kendisini) tazeler."""
        mevcut = set(self.state.gruplar)
        if set(self.grup_sayfalari.keys()) != mevcut:
            self._grup_sayfalarini_kur()
        for sayfa in self.grup_sayfalari.values():
            sayfa._baslik_guncelle()
            sayfa.yenile(zorla_yeniden_kur=zorla_yeniden_kur)

    def _sekme_degisti(self, key):
        widget = self.sayfa_map.get(key)
        if widget:
            if widget in self.grup_sayfalari.values():
                widget.yenile(zorla_yeniden_kur=True)
            elif widget is self.borclar_view:
                self.borclar_view.yenile()
            elif widget is self.masa_kayitlari_view:
                self.masa_kayitlari_view.yenile()
            elif widget is self.urunler_view:
                self.urunler_view._listeyi_kur()
            elif widget is self.kasa_view:
                self.kasa_view.yenile()
            elif widget is self.son_islemler_view:
                self.son_islemler_view.yenile()
            elif widget is self.notlar_view:
                self.notlar_view.yenile()
            self.sayfalar.setCurrentWidget(widget)

    def not_ac(self, not_obj):
        """Notu ana pencerenin ÜZERİNDE (QStackedWidget'ın dışında, doğrudan bu
        pencereye child olarak) açar - böylece hangi sayfaya geçilirse geçilsin
        kaybolmaz, sadece kendi X'ine basılınca kapanır."""
        if not_obj.id in self.acik_notlar:
            self.acik_notlar[not_obj.id].raise_()
            return
        widget = NotWidget(not_obj, parent=self)
        widget.kapatildi.connect(self._not_kapatildi)
        # Üst üste binmesinler diye her yeni not biraz kaydırılarak açılır
        kademe = (len(self.acik_notlar) % 8) * 28
        widget.move(self.width() - 260 - kademe, 80 + kademe)
        widget.show()
        widget.raise_()
        self.acik_notlar[not_obj.id] = widget

    def _not_kapatildi(self, not_id: int):
        self.acik_notlar.pop(not_id, None)

    def _tarih_saat_guncelle(self):
        simdi = datetime.now()
        self.tarih_saat_lbl.setText(
            f"{simdi.day} {AY_ADLARI_TR[simdi.month - 1]} {GUN_ADLARI_TR[simdi.weekday()]}   {simdi.strftime('%H:%M:%S')}"
        )
        self.sidebar.giris_bilgisini_guncelle(self.state.salon_adi)

    def _sure_dolanlari_kontrol(self):
        """Süreli (geri sayımlı) açık masalardan süresi dolanlar için bildirim+ses.
        İlk dolduğunda hemen, sonra (ayardaki aralıkta, varsayılan 30 sn)
        masa kapanana / süre eklenene kadar tekrarlar."""
        import time
        simdi = time.monotonic()
        ayar = self.bildirim.ayarlar()
        dolu = set()
        for m in self.state.masalar:
            # Ödeme beklerken de (masa tamamen kapanana/boşalana kadar) tekrarlasın
            if m.durum in (MasaDurumu.ACIK, MasaDurumu.ODEME_BEKLIYOR) and m.suresi_doldu_mu():
                anahtar = (m.id, m.hedef_saniye, m.ilk_acilis_zamani)
                dolu.add(anahtar)
                son = self._bildirilen_masalar.get(anahtar)
                tekrar = ayar["tekrar_acik"] and son is not None and \
                    simdi - son >= max(5, int(ayar["tekrar_saniye"]))
                if son is None or tekrar:
                    self._bildirilen_masalar[anahtar] = simdi
                    self._uyari_caldi = True
                    baslik, mesaj = self.bildirim.metin_hazirla(m.ad, m.gorunur_bolum())
                    self.bildirim.bildir(baslik, mesaj)
        for anahtar in list(self._bildirilen_masalar):
            if anahtar not in dolu:
                del self._bildirilen_masalar[anahtar]
        # Çalan uyarı varken ilgili masa kapandı/süre eklendi ve başka dolu masa
        # kalmadıysa sesi hemen sustur.
        if not dolu and self._uyari_caldi:
            self._uyari_caldi = False
            self.bildirim.sesi_durdur()

    def _canli_guncelle(self):
        self._sure_dolanlari_kontrol()
        self._tarih_saat_guncelle()
        aktif = self.sayfalar.currentWidget()
        if aktif in self.grup_sayfalari.values():
            aktif.yenile()
        elif aktif is self.kasa_view:
            # Masa kapatma/ödeme gibi işlemler Anasayfa'dan yapılıyor - Kasa
            # sekmesine geçince (hatta zaten açıkken bile) rakamların ANLIK
            # güncel olması için bunu da periyodik tazeliyoruz.
            self.kasa_view.yenile()
        elif aktif is self.son_islemler_view:
            self.son_islemler_view.yenile()

        # OTOMATİK KAYIT: 250ms'lik tikin her turunda diske yazmak gereksiz
        # yere disk yorar - bunun yerine yaklaşık her 5 SANİYEDE bir (20 tik)
        # tüm veriyi diske kaydediyoruz. Elektrik kesintisi gibi ani bir
        # kapanmada kaybedilecek veri en fazla birkaç saniyelik olur, açık
        # masalar dahil her şey bir sonraki açılışta kaldığı yerden gelir.
        self._otomatik_kayit_sayaci += 1
        if self._otomatik_kayit_sayaci >= 20:
            self._otomatik_kayit_sayaci = 0
            kayit.kaydet(self.state)

    def _oturumu_kapat(self):
        c = soru_sor(self, "Oturumu Kapat",
                     "Oturum kapatılıp program kapanacak. Bir sonraki açılışta şifre sorulacak. Devam edilsin mi?")
        if c == QMessageBox.StandardButton.Yes:
            hesap.hatirla_ayarla(False)
            self.close()

    def acilista_guncelleme_denetle(self):
        """Açılışta arka planda sessizce denetler; yeni sürüm varsa sorar."""
        if not GUNCELLEME_ADRESI:
            return
        self._guncelleme_kontrolcu = guncelleme.GuncellemeKontrolcu(self)
        def sonuc(bildirim, hata):
            if bildirim is not None and guncelleme.yeni_surum_var_mi(bildirim):
                GuncellemeDialog(bildirim, self).exec()
        self._guncelleme_kontrolcu.sonuc.connect(sonuc)
        self._guncelleme_kontrolcu.kontrol_et()

    def _yardim_ac(self):
        YardimDialog(self.state, self).exec()

    def closeEvent(self, event):
        """Pencere kapatılırken: önce veriyi diske kaydet, sonra kısa bir
        veda ekranı göster, ardından gerçekten kapat."""
        kayit.kaydet(self.state)
        VedaDialog(self.state.salon_adi, self).exec()
        event.accept()


def main():
    app = QApplication(sys.argv)
    temayi_uygula(app)
    # Lisans + giriş kapısı: geçemeyen programa erişemez
    if not giris_akisi():
        sys.exit(0)
    pencere = AnaPencere()
    pencere.show()
    KarsilamaDialog(pencere.state.salon_adi, pencere).exec()
    pencere.acilista_guncelleme_denetle()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
