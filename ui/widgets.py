"""
Ortak, tekrar kullanılan küçük widget'lar.

SessizDoubleSpinBox / SessizSpinBox:
Normal QDoubleSpinBox/QSpinBox fare tekerleğiyle ya da yukarı/aşağı oklarla
değeri kazara değiştirebiliyor (özellikle fiyat gibi hassas alanlarda tehlikeli
- kasada birisi fare tekerleğini yanlışlıkla oynatırsa fiyat değişebilir).
Bu sınıflar ok butonlarını gizler VE fare tekerleği olayını yok sayar - değer
SADECE klavyeden yazılarak değişebilir. Uygulamadaki TÜM fiyat/tutar/dakika
girişleri bundan sonra bu sınıfları kullanmalı.

Ayrıca kutuya tıklayınca/odaklanınca, değer 0 ise kutu TAMAMEN BOŞALIR (mavi
"seçili" hâlde durmaz) - kullanıcı direkt rakam yazmaya başlayabilir. Boş
bırakılıp başka yere tıklanırsa otomatik olarak 0'a geri döner. Değer 0
DEĞİLSE (örn. bir gideri düzenlerken) klasik "hepsini seç" davranışı geçerli
olmaya devam eder, ki mevcut tutarın üzerine hızlıca yazılabilsin.
"""
from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox, QAbstractSpinBox, QMessageBox, QDialog, QLineEdit, QComboBox, QTimeEdit, QDateEdit, QListWidget
from PyQt6.QtCore import QTimer, Qt
from core.theme import RENK


class SessizComboBox(QComboBox):
    """Normal QComboBox, üzerindeyken fare tekerleği çevrilince İÇERİĞİ
    (seçili tarife/kol/kategori) DEĞİŞTİRİR - kullanıcı sadece SAYFAYI
    kaydırmak isterken kutunun üzerinden geçince yanlışlıkla tarife/kol
    değişebiliyordu. Bu sınıf tekerlek olayını YOK SAYAR - fare tekerleği
    her zaman sayfayı kaydırmaya devam eder, kutunun içeriğini asla
    değiştirmez. Uygulamadaki TÜM tarife/kol/profil seçim kutuları bunu
    kullanmalı."""
    def wheelEvent(self, event):
        event.ignore()


class SessizTimeEdit(QTimeEdit):
    """QTimeEdit de aynı şekilde fare tekerleğiyle saat/dakika değerini
    değiştiriyordu (masa başlangıç saati düzeltme ekranında) - aynı sebeple
    tekerlek olayını yok sayıyoruz."""
    def wheelEvent(self, event):
        event.ignore()


class SessizDateEdit(QDateEdit):
    """QDateEdit de aynı fare tekerleği sorununa sahip (Genel Rapor > Tarih
    Seç alanında kullanılıyor) - aynı sebeple tekerlek olayını yok sayıyoruz."""
    def wheelEvent(self, event):
        event.ignore()


class OrtalanmisDialog(QDialog):
    """Tüm popup pencerelerin ORTAK atası - hangi ekranda, nereye tıklanırsa
    tıklansın, popup HER ZAMAN ebeveyn pencerenin (yoksa ekranın) TAM
    ORTASINDA açılır. Öncesinde popup'lar bazen alt köşede/rastgele bir
    konumda açılıp fare ile aranması gerekiyordu - bu sınıf bunu engeller."""
    def showEvent(self, event):
        super().showEvent(event)
        ebeveyn = self.parentWidget()
        merkez = None
        if ebeveyn is not None:
            ust_pencere = ebeveyn.window()
            if ust_pencere is not None:
                merkez = ust_pencere.geometry().center()
        if merkez is None:
            ekran = self.screen()
            if ekran is not None:
                merkez = ekran.geometry().center()
        if merkez is not None:
            yeni_geo = self.frameGeometry()
            yeni_geo.moveCenter(merkez)
            self.move(yeni_geo.topLeft())


def _mesaj_kutusu_stilini_uygula(kutu: QMessageBox):
    """Windows karanlık modu bazı QMessageBox pencerelerini (özellikle Sil
    onayı gibi) tamamen siyah/görünmez yapabiliyordu - uygulama genelindeki
    tema bu pencerelere bir sebeple ulaşmıyordu. Bu yüzden HER QMessageBox'a
    kendi yerel, garantili stilini doğrudan veriyoruz."""
    kutu.setStyleSheet(f"""
        QMessageBox {{ background-color:{RENK['panel']}; }}
        QMessageBox QLabel {{ color:{RENK['text']}; background:transparent; font-size:13px; }}
        QPushButton {{ background-color:{RENK['panel_hover']}; color:{RENK['text']};
            border:1px solid {RENK['border_strong']}; border-radius:6px;
            padding:8px 16px; min-width:70px; }}
        QPushButton:hover {{ background-color:#E4F3FC; border-color:#8FD1F2; }}
    """)


def soru_sor(parent, baslik: str, mesaj: str) -> int:
    """QMessageBox.question(...) ile birebir aynı şekilde kullanılır, tek
    farkı görünürlüğü garanti eden yerel stili taşımasıdır."""
    kutu = QMessageBox(parent)
    kutu.setWindowTitle(baslik)
    kutu.setText(mesaj)
    kutu.setIcon(QMessageBox.Icon.Question)
    kutu.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    kutu.setDefaultButton(QMessageBox.StandardButton.No)
    kutu.button(QMessageBox.StandardButton.Yes).setText("Evet")
    kutu.button(QMessageBox.StandardButton.No).setText("Hayır")
    _mesaj_kutusu_stilini_uygula(kutu)
    return kutu.exec()


def uyar(parent, baslik: str, mesaj: str) -> int:
    """QMessageBox.warning(...) ile birebir aynı şekilde kullanılır."""
    kutu = QMessageBox(parent)
    kutu.setWindowTitle(baslik)
    kutu.setText(mesaj)
    kutu.setIcon(QMessageBox.Icon.Warning)
    kutu.setStandardButtons(QMessageBox.StandardButton.Ok)
    kutu.button(QMessageBox.StandardButton.Ok).setText("Tamam")
    _mesaj_kutusu_stilini_uygula(kutu)
    return kutu.exec()


def bilgilendir(parent, baslik: str, mesaj: str) -> int:
    """QMessageBox.information(...) ile birebir aynı şekilde kullanılır."""
    kutu = QMessageBox(parent)
    kutu.setWindowTitle(baslik)
    kutu.setText(mesaj)
    kutu.setIcon(QMessageBox.Icon.Information)
    kutu.setStandardButtons(QMessageBox.StandardButton.Ok)
    kutu.button(QMessageBox.StandardButton.Ok).setText("Tamam")
    _mesaj_kutusu_stilini_uygula(kutu)
    return kutu.exec()


class TamamlamaKutusu(QLineEdit):
    """QComboBox'ın küçük ok butonuna tıklama zorunluluğunu kaldırır - kutunun
    HERHANGİ bir yerine tıklayınca/odaklanınca kayıtlı seçenekler hemen altında
    açılır. Serbest yazmaya da izin verir (yeni bir grup/kategori adı gibi).
    Öğe üzerine gelince (henüz tıklamadan) buz mavisi ile vurgulanır.

    ÖNEMLİ TEKNİK NOT: Qt'nin kendi QCompleter popup'ı KULLANILMIYOR - o,
    gerçek bir "popup" pencere olduğu için (işletim sistemi düzeyinde fare
    yakalar), dışarıdaki HER tıklamayı (pencerenin X butonu dahil) önce
    "kendini kapatmak" için yutuyordu - bu da "X'e basınca ilk seferde
    kapanmıyor" hatasına sebep oluyordu (kullanıcı fark etti, focusOutEvent
    ile bile düzelmedi çünkü sorun popup'ın KENDİ dahili fare yakalamasıydı).
    Bunun yerine sıradan bir ÇOCUK widget (QListWidget, popup DEĞİL) kullanıyoruz
    - bu, işletim sistemi düzeyinde hiçbir şeyi yakalamaz, dışarıdaki hiçbir
    tıklamayı (X butonu dahil) asla yutmaz."""
    def __init__(self, secenekler: list[str] | None = None, parent=None):
        super().__init__(parent)
        self._tum_secenekler: list[str] = list(secenekler or [])
        # Liste GEÇ (ilk odaklanmada) oluşturulur - o ana kadar bu kutunun
        # hangi PENCEREYE (dialog'a) ait olacağı henüz kesinleşmemiş olabilir.
        # Kutunun KENDİSİNE parent yapılırsa liste, kutunun küçücük alanına
        # KESİLİR ve görünmez olur - bu yüzden en üst pencereye (window())
        # parent yapılması ŞART, bunu da ilk odaklanma anında çözüyoruz.
        self._liste: QListWidget | None = None
        self.textEdited.connect(self._yaziya_gore_filtrele)

    def _liste_olustur_gerekirse(self):
        if self._liste is not None:
            return
        # Bu kutunun EN ÜST penceresine (dialog'a) child olarak ekleniyor -
        # gerçek bir top-level/popup pencere DEĞİL, bu yüzden dışarıdaki
        # tıklamaları (X butonu dahil) asla yakalayıp yutamaz.
        self._liste = QListWidget(self.window())
        self._liste.setWindowFlags(Qt.WindowType.Widget)
        self._liste.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._liste.setStyleSheet(f"""
            QListWidget {{ background-color:#FFFFFF; color:{RENK['text']};
                border:1px solid {RENK['border_strong']}; border-radius:6px;
                padding:4px; outline:none; }}
            QListWidget::item {{ padding:6px 10px; border-radius:4px; }}
            QListWidget::item:hover, QListWidget::item:selected {{
                background-color:#E4F3FC; color:{RENK['text']}; }}
        """)
        self._liste.hide()
        self._liste.itemClicked.connect(self._secim_yapildi)
        self._secenekleri_yukle()

    def _secenekleri_yukle(self):
        if self._liste is None:
            return
        self._liste.clear()
        for secenek in self._tum_secenekler:
            self._liste.addItem(secenek)

    def secenekleri_guncelle(self, secenekler: list[str]):
        self._tum_secenekler = list(secenekler)
        self._secenekleri_yukle()

    def _yaziya_gore_filtrele(self, metin: str):
        self._liste_olustur_gerekirse()
        metin_kucuk = metin.lower()
        self._liste.clear()
        for secenek in self._tum_secenekler:
            if metin_kucuk in secenek.lower():
                self._liste.addItem(secenek)
        if self._liste.count():
            self._listeyi_konumla_ve_goster()
        else:
            self._liste.hide()

    def _listeyi_konumla_ve_goster(self):
        if self._liste is None or self._liste.count() == 0:
            return
        # Kutunun HEMEN ALTINA, ana pencereye göre konumlandırıyoruz.
        sol_alt = self.mapTo(self._liste.parentWidget(), self.rect().bottomLeft())
        self._liste.move(sol_alt)
        satir_yuksekligi = self._liste.sizeHintForRow(0) or 28
        yukseklik = min(180, satir_yuksekligi * self._liste.count() + 10)
        self._liste.resize(self.width(), yukseklik)
        self._liste.raise_()
        self._liste.show()

    def _secim_yapildi(self, item):
        self.setText(item.text())
        self._liste.hide()
        self.setFocus()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._liste_olustur_gerekirse()
        # SADECE kutu BOŞKEN otomatik listeyi gösteriyoruz (ilk kez tıklayınca
        # keşif için). Bir öğe seçildikten SONRA odak kutuya geri dönerse
        # kutu artık boş olmadığı için popup gereksiz yere tekrar açılmıyor.
        if not self.text():
            self._secenekleri_yukle()
            QTimer.singleShot(0, self._listeyi_konumla_ve_goster)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self._liste is None:
            return
        # Bir listedeki öğeye TIKLAMA da odağı kaybettirir - eğer listeyi HEMEN
        # gizlersek, tıklama olayı listeye ULAŞAMADAN kaybolur (klasik "odak
        # kaybı vs. tıklama" yarış durumu). Küçük bir gecikmeyle gizleyerek
        # itemClicked'in önce işlenmesine izin veriyoruz.
        QTimer.singleShot(150, self._liste.hide)


class _TamSilinebilirSatir(QLineEdit):
    """SessizDoubleSpinBox/SessizSpinBox'ların GERÇEK klavye odağını alan iç
    satır. ÖNEMLİ AYRINTI: bir spinbox'a yazarken tuş vuruşları spinbox'ın
    KENDİSİNE değil, onun İÇ QLineEdit'ine gider (spinbox sadece dıştaki bir
    kap/çerçevedir, odak proxy'si iç satırdadır) - bu yüzden dış spinbox
    sınıfında keyPressEvent override etmek YETERSİZ kalıyordu, o metot HİÇ
    ÇAĞRILMIYORDU (önceki düzeltme denemesi bu yüzden gerçek uygulamada
    çalışmadı, kullanıcı doğru şekilde fark etti).

    ASIL SORUN: Qt'nin QDoubleSpinBox/QSpinBox için kurduğu doğrulayıcı,
    Backspace/Delete ile kutuyu TAMAMEN boşaltmayı (sonuç "" oluyorsa)
    'Invalid' sayıp bu SON silme adımını sessizce GERİ ALIYOR (bilinen bir Qt
    davranışı) - bu yüzden "500 TL yaz, tamamen sil" gibi bir işlemde her
    zaman tek bir rakam (5) kutuda takılı kalıyordu. Silme sonrası metnin
    TAMAMEN boş kalacağı durumu (tüm metin seçiliyken ya da tek karakter
    kalmışken Backspace/Delete) burada, GERÇEK odağı tutan bu satırın kendi
    keyPressEvent'inde yakalayıp doğrudan clear() çağırıyoruz - Qt'nin
    sorunlu doğrulama/geri-alma adımını tamamen devre dışı bırakıyoruz."""
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            metin = self.text()
            secili = self.selectedText()
            tamamini_siliyor = (secili != "" and secili == metin) or (secili == "" and len(metin) <= 1)
            if tamamini_siliyor:
                self.clear()
                return
        super().keyPressEvent(event)


class SessizDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOT: ButtonSymbols.NoButtons KULLANMIYORUZ - yeni Qt sürümlerinde (6.12) QSS ile
        # birlikte iç yazı alanını 1 piksele çökertip rakamları GÖRÜNMEZ yapıyordu.
        # Okları bunun yerine tema QSS'inde (#sessizSpin) sıfır genişliğe indiriyoruz.
        self.setObjectName("sessizSpin")
        # Varsayılan iç satırı, TAMAMEN silmeye izin veren kendi satırımızla
        # DEĞİŞTİRİYORUZ - bkz. _TamSilinebilirSatir docstring'i.
        self.setLineEdit(_TamSilinebilirSatir(self))

    def wheelEvent(self, event):
        event.ignore()

    def _odaklaninca_duzenle(self):
        le = self.lineEdit()
        if le is None:
            return
        if self.value() == 0:
            # "0" mavi seçili göstermek yerine kutuyu TAMAMEN BOŞALTIYORUZ -
            # kullanıcı hiçbir şeyi silmeden direkt rakam yazabilsin.
            le.clear()
        else:
            le.selectAll()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._odaklaninca_duzenle)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        QTimer.singleShot(0, self._odaklaninca_duzenle)

    def focusOutEvent(self, event):
        # ÖNEMLİ: metni super().focusOutEvent(event) ÇAĞRILMADAN ÖNCE
        # okuyoruz. Qt'nin kendi focusOutEvent'i, kutu boşken/geçersizken
        # interpretText() çağırıp görünen metni SESSİZCE eski değere (ör.
        # "400") GERİ ALIYOR - biz süper çağrısından SONRA kontrol edersek
        # metni hep dolu buluyoruz ve hiç sıfırlamıyoruz. Bu da kullanıcının
        # bildirdiği "tamamen sildim ama başka yere tıklayınca değer geri
        # geliyor" hatasının asıl sebebiydi.
        le = self.lineEdit()
        bos_birakilmis = le is not None and le.text().strip() == ""
        super().focusOutEvent(event)
        if bos_birakilmis:
            self.setValue(0)


class SessizSpinBox(QSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOT: ButtonSymbols.NoButtons KULLANMIYORUZ - yeni Qt sürümlerinde (6.12) QSS ile
        # birlikte iç yazı alanını 1 piksele çökertip rakamları GÖRÜNMEZ yapıyordu.
        # Okları bunun yerine tema QSS'inde (#sessizSpin) sıfır genişliğe indiriyoruz.
        self.setObjectName("sessizSpin")
        # Varsayılan iç satırı, TAMAMEN silmeye izin veren kendi satırımızla
        # DEĞİŞTİRİYORUZ - bkz. _TamSilinebilirSatir docstring'i.
        self.setLineEdit(_TamSilinebilirSatir(self))

    def wheelEvent(self, event):
        event.ignore()

    def _odaklaninca_duzenle(self):
        le = self.lineEdit()
        if le is None:
            return
        if self.value() == 0:
            le.clear()
        else:
            le.selectAll()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._odaklaninca_duzenle)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        QTimer.singleShot(0, self._odaklaninca_duzenle)

    def focusOutEvent(self, event):
        # bkz. SessizDoubleSpinBox.focusOutEvent - aynı sebeple metni süper
        # çağrısından ÖNCE okuyoruz.
        le = self.lineEdit()
        bos_birakilmis = le is not None and le.text().strip() == ""
        super().focusOutEvent(event)
        if bos_birakilmis:
            self.setValue(0)


def cop_kutusu_ikonu(renk: str = "#FF4D6D", boyut: int = 18):
    """Net okunan çöp kutusu ikonu (emoji yerine çizim - emoji soluk/gri çıkıyordu)."""
    from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QPainterPath
    from PyQt6.QtCore import Qt, QRectF, QPointF
    olcek = 4
    pm = QPixmap(boyut * olcek, boyut * olcek)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(olcek * boyut / 24.0, olcek * boyut / 24.0)
    kalem = QPen(QColor(renk), 2.0)
    kalem.setCapStyle(Qt.PenCapStyle.RoundCap)
    kalem.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(kalem)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(4, 6.5), QPointF(20, 6.5))            # kapak
    p.drawLine(QPointF(9.5, 6.5), QPointF(9.5, 4))            # kulp
    p.drawLine(QPointF(9.5, 4), QPointF(14.5, 4))
    p.drawLine(QPointF(14.5, 4), QPointF(14.5, 6.5))
    g = QPainterPath()                                         # gövde
    g.moveTo(6, 6.5); g.lineTo(7, 19.5); g.lineTo(17, 19.5); g.lineTo(18, 6.5)
    p.drawPath(g)
    p.drawLine(QPointF(10, 10), QPointF(10, 16))               # çizgiler
    p.drawLine(QPointF(14, 10), QPointF(14, 16))
    p.end()
    return QIcon(pm)


def cop_butonu_yap(btn, boyut: int = 30, ikon_boyut: int = 20):
    """Çöp kutusu butonu: kutusuz/çerçevesiz, sadece net kırmızı ikon;
    üstüne gelince çok hafif kırmızı zemin. Uygulamadaki TÜM sil ikonları bunu kullanır."""
    from PyQt6.QtCore import QSize, Qt
    renk = RENK["danger"]
    btn.setText("")
    btn.setIcon(cop_kutusu_ikonu(renk, ikon_boyut))
    btn.setIconSize(QSize(ikon_boyut, ikon_boyut))
    btn.setFixedSize(boyut, boyut)
    btn.setToolTip("Sil")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        "QPushButton { background-color:transparent; border:none; border-radius:8px; padding:0; }"
        "QPushButton:hover { background-color:rgba(255,77,109,0.14); }"
    )
    return btn


def metin_sor(parent, baslik: str, etiket: str, metin: str = ""):
    """QInputDialog.getText'in Türkçe düğmeli karşılığı -> (metin, tamam_mi)."""
    from PyQt6.QtWidgets import QInputDialog
    d = QInputDialog(parent)
    d.setWindowTitle(baslik)
    d.setLabelText(etiket)
    d.setTextValue(metin)
    d.setOkButtonText("Tamam")
    d.setCancelButtonText("İptal")
    ok = d.exec() == QInputDialog.DialogCode.Accepted
    return d.textValue(), ok
