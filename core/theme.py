"""
Tema - "Premium Beyaz + Neon" Görünüm
=======================================
Zemin saf beyaz DEĞİL, hafif gri-lavanta tonlu bir "premium beyaz"
(RENK['bg']). Kartlar tam beyaz ve ince gölge hissi veren border ile
zeminden ayrışıyor. Vurgu renkleri (mor + turkuaz + amber + pembe-kırmızı)
neon/canlı tutuluyor ki koyu temadaki enerji korunsun ama göz yormasın.

Bu paleti değiştirmek (örn. müşteri kendi marka rengini isterse) tek
yerden yönetilebilir - sadece RENK sözlüğü güncellenir.
"""

RENK = {
    "bg": "#F3F4FA",            # ana zemin - premium beyaz (hafif lavanta-gri)
    "bg_soft": "#FFFFFF",       # sidebar zemini
    "panel": "#FFFFFF",         # kart zemini
    "panel_hover": "#F7F7FD",
    "border": "#E6E7F2",
    "border_strong": "#D8DAEE",

    "accent": "#6C4DF6",        # neon mor - ana marka rengi, GAMEHUB vurgusu
    "accent2": "#00D2A8",       # neon turkuaz - AÇIK durum, PS ikonları
    "success": "#12B76A",
    "warning": "#F5A623",       # ÖDEME BEKLENİYOR
    "danger": "#FF4D6D",        # DURAKLATILDI / iptal
    "info": "#4F8CFF",

    "text": "#161821",          # ana metin (koyu, açık zemin üstünde)
    "text_muted": "#8A8FA3",
}

QSS = f"""
QWidget {{
    background-color: {RENK['bg']};
    color: {RENK['text']};
    font-family: 'Segoe UI', 'Arial';
    font-size: 13px;
}}
QFrame#sidebar {{
    background-color: {RENK['bg_soft']};
    border-right: 1px solid {RENK['border']};
}}
QLabel#brandTitle {{
    font-size: 19px;
    font-weight: 800;
}}
QLabel#brandSubtitle {{
    font-size: 9px;
    font-weight: 600;
    color: {RENK['text_muted']};
    line-height: 1.3;
}}
QPushButton#sidebarBtn {{
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 10px;
    color: #5B6072;
    font-size: 14px;
    font-weight: 600;
    background-color: transparent;
}}
QPushButton#sidebarBtn:hover {{
    background-color: #EAF6FD;
    color: {RENK['text']};
}}
QPushButton#sidebarBtnActive {{
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 10px;
    background-color: {RENK['accent']};
    color: white;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#sidebarBtnActive:hover {{
    background-color: {RENK['accent']};
}}
QFrame#masaKart {{
    background-color: {RENK['panel']};
    border: 1px solid {RENK['border']};
    border-radius: 16px;
}}
QFrame#masaKart:hover {{
    border: 1px solid {RENK['accent']};
}}
QFrame#statCard {{
    background-color: {RENK['panel']};
    border: 1px solid {RENK['border']};
    border-radius: 14px;
}}
/* KRİTİK: Hem kart zemini (panel, beyaz) hem QDialog zemini (panel, beyaz)
   ile genel QWidget zemini (bg, hafif gri-lavanta) FARKLI renkler - bir
   QLabel bunların İÇİNE doğrudan eklenip kendi arka planını miras alırsa,
   "çizgili satır" gibi görünür. Bu yüzden hem kart içindeki hem TÜM popup
   pencerelerindeki (QDialog) düz metin etiketleri şeffaf olmalı - tek bir
   yerden TÜM uygulamadaki bu görünüm hatasını çözer. (Butonlar/kutular
   kasıtlı olarak DIŞARIDA bırakıldı - onların kendi renkli stilleri olduğu
   için şeffaf yapılırsa o stiller bozulurdu.) */
QFrame#masaKart QLabel, QFrame#statCard QLabel, QDialog QLabel {{
    background-color: transparent;
}}
QLabel#masaAdi {{
    font-size: 15px;
    font-weight: 700;
    color: {RENK['text']};
}}
QLabel#durumEtiket {{
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 10px;
}}
QLabel#tutarBuyuk {{
    font-size: 24px;
    font-weight: 800;
    color: {RENK['accent']};
}}
QLabel#tarifeBilgi {{
    font-size: 11px;
    color: {RENK['text_muted']};
}}
QLabel#pageTitle {{
    font-size: 20px;
    font-weight: 800;
    color: {RENK['text']};
}}
QLabel#pageSubtitle {{
    font-size: 12px;
    color: {RENK['text_muted']};
}}
QPushButton#primaryBtn {{
    background-color: rgba(108, 77, 246, 0.12);
    color: {RENK['accent']};
    border-width: 1.5px;
    border-style: solid;
    border-color: {RENK['accent']};
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 700;
}}
QPushButton#primaryBtn:hover {{
    background-color: rgba(108, 77, 246, 0.20);
}}
QPushButton#odemeBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0E8F63, stop:1 #17C98A);
    color: white;
    border-radius: 10px;
    padding: 12px 18px;
    font-weight: 800;
    font-size: 13px;
    border-width: 2px;
    border-style: solid;
    border-color: #7FE0BE;
}}
QPushButton#odemeBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B7752, stop:1 #14B87C);
    border-color: #5FD1A8;
}}
QPushButton#secenekBtn {{
    background-color: #FFFFFF;
    color: {RENK['text']};
    border-width: 1px;
    border-style: solid;
    border-color: {RENK['border_strong']};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 700;
    text-align: center;
}}
QPushButton#secenekBtn:hover {{
    background-color: #E4F3FC;
    border-color: #8FD1F2;
}}
QPushButton#dangerBtn {{
    background-color: transparent;
    color: {RENK['danger']};
    border-width: 1px;
    border-style: solid;
    border-color: {RENK['danger']};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton#dangerBtn:hover {{ background-color: rgba(255,77,109,0.08); }}
QPushButton#ghostBtn {{
    background-color: {RENK['panel_hover']};
    color: {RENK['text']};
    border-radius: 8px;
    padding: 10px 18px;
    border-width: 1px;
    border-style: solid;
    border-color: {RENK['border']};
}}
QPushButton#ghostBtn:hover {{ border-color: {RENK['accent']}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background-color: {RENK['bg']};
    border: 1px solid {RENK['border_strong']};
    border-radius: 6px;
    padding: 8px 10px;
    color: {RENK['text']};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border: 1px solid {RENK['accent']}; }}
/* Tarih seçici (Kasa > Genel > Tarihe Git) açılır takvimi - eskiden stil
   hiç verilmemişti, Qt'nin varsayılan KOYU/siyah takvimi çıkıyordu (bildirilen
   görünüm hatası). Takvimin her parçasını (üst gezinme çubuğu, gün başlıkları,
   hücreler, bugünün/seçilinin vurgusu) uygulamanın genel "premium beyaz"
   temasıyla eşleştiriyoruz. */
QCalendarWidget {{
    background-color: {RENK['panel']};
    color: {RENK['text']};
    border: 1px solid {RENK['border_strong']};
    border-radius: 10px;
}}
QCalendarWidget QWidget {{
    background-color: {RENK['panel']};
    color: {RENK['text']};
    alternate-background-color: {RENK['panel']};
}}
QCalendarWidget QToolButton {{
    background-color: transparent;
    color: {RENK['text']};
    font-weight: 700;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    icon-size: 16px;
}}
QCalendarWidget QToolButton:hover {{
    background-color: {RENK['panel_hover']};
}}
QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {RENK['bg']};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}
QCalendarWidget QMenu {{
    background-color: #FFFFFF;
    color: {RENK['text']};
    border: 1px solid {RENK['border_strong']};
}}
QCalendarWidget QSpinBox {{
    background-color: {RENK['bg']};
    color: {RENK['text']};
    border: 1px solid {RENK['border_strong']};
    border-radius: 4px;
}}
QCalendarWidget QAbstractItemView:enabled {{
    background-color: {RENK['panel']};
    color: {RENK['text']};
    selection-background-color: {RENK['accent']};
    selection-color: #FFFFFF;
    outline: none;
}}
QCalendarWidget QAbstractItemView:disabled {{
    color: {RENK['text_muted']};
}}
/* Fare bir güne SEÇMEDEN üzerine geldiğinde hafif buz mavisi vurgu -
   seçili gün (mor) ile karışmasın diye ayrı, daha soluk bir renk. */
QCalendarWidget QAbstractItemView::item:hover {{
    background-color: #E4F3FC;
    color: {RENK['text']};
}}
QCalendarWidget QTableView {{
    background-color: {RENK['panel']};
    gridline-color: {RENK['border']};
}}
/* Tüm QComboBox açılır listeleri (Masa Bazlı Tarife Ataması, Konsol Tipi
   seçimi, vb.) - üzerine fareyle GELİNCE (tıklamadan) grimsi vurgu, seçili
   olan ise mor. Öncesinde bu liste hiç stillenmemişti, düz beyaz üzerine
   düz siyah yazı duruyordu - hangi seçeneğin üzerinde olunduğu belli değildi. */
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    color: {RENK['text']};
    border: 1px solid {RENK['border_strong']};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 22px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: #E4F3FC;
    color: {RENK['text']};
}}
QCheckBox {{ background: transparent; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1.5px solid #B9BCD0; border-radius: 5px; background: #FFFFFF;
}}
QCheckBox::indicator:hover {{ border-color: {RENK['accent']}; }}
QCheckBox::indicator:checked {{
    background-color: {RENK['accent']}; border-color: {RENK['accent']};
    image: url(__TIK_YOLU__);
}}
/* Sağ tık (kes/kopyala/yapıştır) menüleri ve diğer QMenu'ler - Windows
   karanlık modunda siyah çıkıyordu. */
QMenu {{
    background-color: #FFFFFF;
    color: {RENK['text']};
    border: 1px solid {RENK['border_strong']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    background-color: transparent;
    padding: 6px 22px 6px 14px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background-color: #E4F3FC;
    color: {RENK['text']};
}}
QMenu::item:disabled {{ color: {RENK['text_muted']}; }}
QMenu::separator {{
    height: 1px;
    background: {RENK['border']};
    margin: 4px 8px;
}}
QToolTip {{
    background-color: #FFFFFF;
    color: {RENK['text']};
    border: 1px solid {RENK['border_strong']};
    padding: 4px 8px;
}}
QDialog {{ background-color: {RENK['panel']}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {RENK['border_strong']}; border-radius: 4px; }}
"""


def durum_rengi(durum_str: str) -> str:
    eslesme = {
        "BOŞ": RENK["text_muted"],
        "AÇIK": RENK["accent2"],
        "ÖDEME BEKLENİYOR": RENK["warning"],
        "DURAKLATILDI": RENK["danger"],
    }
    return eslesme.get(durum_str, RENK["text_muted"])


def durum_zemin_rengi(durum_str: str) -> str:
    """Durum rozetinin arka planı - ana rengin çok açık (hafif) tonu."""
    eslesme = {
        "BOŞ": "#F0F1F6",
        "AÇIK": "#E3FBF5",
        "ÖDEME BEKLENİYOR": "#FDF3E0",
        "DURAKLATILDI": "#FFE9EE",
    }
    return eslesme.get(durum_str, "#F0F1F6")


# ---------------------------------------------------------------------------
# Açık tema uygulama katmanı (Windows karanlık modunda siyah pencere/menü
# çıkmasını önlemek için "kemer + pantolon askısı" yaklaşımı)
# ---------------------------------------------------------------------------
def acik_palet():
    from PyQt6.QtGui import QPalette, QColor
    p = QPalette()
    R = QPalette.ColorRole
    p.setColor(R.Window, QColor(RENK["bg"]))
    p.setColor(R.WindowText, QColor(RENK["text"]))
    p.setColor(R.Base, QColor("#FFFFFF"))
    p.setColor(R.AlternateBase, QColor(RENK["panel_hover"]))
    p.setColor(R.Text, QColor(RENK["text"]))
    p.setColor(R.Button, QColor(RENK["panel"]))
    p.setColor(R.ButtonText, QColor(RENK["text"]))
    p.setColor(R.ToolTipBase, QColor("#FFFFFF"))
    p.setColor(R.ToolTipText, QColor(RENK["text"]))
    p.setColor(R.PlaceholderText, QColor(RENK["text_muted"]))
    p.setColor(R.Highlight, QColor(RENK["accent"]))
    p.setColor(R.HighlightedText, QColor("#FFFFFF"))
    p.setColor(R.Link, QColor(RENK["accent"]))
    return p


def _menu_paleti():
    from PyQt6.QtGui import QPalette, QColor
    p = acik_palet()
    R = QPalette.ColorRole
    p.setColor(R.Window, QColor("#FFFFFF"))
    p.setColor(R.Button, QColor("#FFFFFF"))
    p.setColor(R.Highlight, QColor("#E4F3FC"))
    p.setColor(R.HighlightedText, QColor(RENK["text"]))
    for grup in (QPalette.ColorGroup.Disabled,):
        p.setColor(grup, R.Text, QColor(RENK["text_muted"]))
        p.setColor(grup, R.WindowText, QColor(RENK["text_muted"]))
        p.setColor(grup, R.ButtonText, QColor(RENK["text_muted"]))
    return p


_MENU_QSS = f"""
QMenu {{ background-color:#FFFFFF; color:{RENK['text']}; border:1px solid {RENK['border_strong']}; padding:4px; }}
QMenu::item {{ background-color:transparent; color:{RENK['text']}; padding:7px 26px 7px 14px; border-radius:4px; }}
QMenu::item:selected {{ background-color:#E4F3FC; color:{RENK['text']}; }}
QMenu::item:disabled {{ color:#B4B8C6; background-color:transparent; }}
QMenu::separator {{ height:1px; background:{RENK['border']}; margin:4px 8px; }}
"""


def turkce_baglam_menusu(widget, pos):
    """Metin alanları için TÜRKÇE ve her zaman açık renkli sağ tık menüsü
    (Qt'nin yabancı dilli/siyah çıkabilen varsayılanı yerine)."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QMenu, QLineEdit, QApplication
    from PyQt6.QtGui import QAction
    tek = isinstance(widget, QLineEdit)
    salt = widget.isReadOnly()
    if tek:
        secili = widget.hasSelectedText()
        geri_var = widget.isUndoAvailable()
        ileri_var = widget.isRedoAvailable()
        gizli = widget.echoMode() != QLineEdit.EchoMode.Normal
        tumu_var = bool(widget.text())
    else:
        secili = widget.textCursor().hasSelection()
        doc = widget.document()
        geri_var = doc.isUndoAvailable()
        ileri_var = doc.isRedoAvailable()
        gizli = False
        tumu_var = not doc.isEmpty()
    yapistir_var = bool(QApplication.clipboard().text()) and not salt

    m = QMenu(widget)
    m.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    m.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    m.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    m.setPalette(_menu_paleti())
    m.setStyleSheet(_MENU_QSS)

    def ekle(ad, kisayol, fn, etkin):
        a = QAction(f"{ad}\t{kisayol}" if kisayol else ad, m)
        a.setEnabled(bool(etkin))
        a.triggered.connect(fn)
        m.addAction(a)

    ekle("Geri Al", "Ctrl+Z", widget.undo, geri_var and not salt)
    ekle("Yinele", "Ctrl+Y", widget.redo, ileri_var and not salt)
    m.addSeparator()
    ekle("Kes", "Ctrl+X", widget.cut, secili and not salt and not gizli)
    ekle("Kopyala", "Ctrl+C", widget.copy, secili and not gizli)
    ekle("Yapıştır", "Ctrl+V", widget.paste, yapistir_var)
    ekle("Sil", "", (widget.del_ if tek else (lambda: widget.textCursor().removeSelectedText())),
         secili and not salt)
    m.addSeparator()
    ekle("Tümünü Seç", "Ctrl+A", widget.selectAll, tumu_var)
    m.popup(widget.mapToGlobal(pos))


def _AcikTemaFiltresiSinifi():
    from PyQt6.QtCore import QObject, QEvent, Qt
    from PyQt6.QtWidgets import (QWidget, QMenu, QMainWindow, QAbstractButton,
                                 QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QTabBar)

    class AcikTemaFiltresi(QObject):
        """Yeni açılan her pencere/menü/popup'ı Windows koyu moduna rağmen
        açık renkli yapar. Butonlara dokunmaz (arka plan boyama bozar)."""

        def eventFilter(self, obj, ev):
            t = ev.type()
            if t == QEvent.Type.Polish and isinstance(obj, QWidget):
                try:
                    # Tıklanabilir her şeyde el imleci (uygulama geneli)
                    if isinstance(obj, (QAbstractButton, QComboBox, QTabBar)):
                        if obj.cursor().shape() == Qt.CursorShape.ArrowCursor:
                            obj.setCursor(Qt.CursorShape.PointingHandCursor)
                    # Metin alanlarında Türkçe, açık renkli sağ tık menüsü
                    if isinstance(obj, (QLineEdit, QTextEdit, QPlainTextEdit)) \
                            and not obj.property("_tr_menu"):
                        obj.setProperty("_tr_menu", True)
                        obj.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                        obj.customContextMenuRequested.connect(
                            lambda pos, w=obj: turkce_baglam_menusu(w, pos))
                except RuntimeError:
                    pass
            if t in (QEvent.Type.Polish, QEvent.Type.Show) and isinstance(obj, QWidget):
                try:
                    if isinstance(obj, QMenu):
                        if not obj.property("_acik_tema"):
                            obj.setProperty("_acik_tema", True)
                            obj.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                            obj.setPalette(_menu_paleti())
                    elif (obj.isWindow() and not isinstance(obj, QMainWindow)
                          and not isinstance(obj, QAbstractButton)
                          and t == QEvent.Type.Show
                          and not obj.property("_acik_tema")):
                        obj.setProperty("_acik_tema", True)
                        obj.setPalette(acik_palet())
                        obj.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                        obj.setAutoFillBackground(True)
                except RuntimeError:
                    pass
            return False

    return AcikTemaFiltresi


def temayi_uygula(app):
    """Uygulama genelinde açık temayı sabitler."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QToolTip
    app.setStyle("Fusion")
    try:
        QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception:
        pass
    pal = acik_palet()
    app.setPalette(pal)
    mp = _menu_paleti()
    for sinif in ("QMenu", "QLineEdit", "QAbstractItemView", "QComboBox",
                  "QAbstractSpinBox", "QDialog", "QMessageBox", "QCalendarWidget"):
        app.setPalette(mp if sinif == "QMenu" else pal, sinif)
    QToolTip.setPalette(pal)
    app.setStyleSheet(QSS.replace("__TIK_YOLU__", _tik_ikonu_yolu()))
    # Qt'nin kendi yabancı dilli metinleri (Evet/Hayır, Tamam/İptal, Kes/Kopyala...) Türkçe
    try:
        from PyQt6.QtCore import QTranslator, QLibraryInfo
        tr = QTranslator(app)
        if tr.load("qtbase_tr", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(tr)
            app._qt_tr = tr
    except Exception:
        pass
    app.setWindowIcon(uygulama_ikonu())
    filtre = _AcikTemaFiltresiSinifi()(app)
    app.installEventFilter(filtre)
    app._acik_tema_filtresi = filtre


def kaynak_yolu(*parcalar):
    """assets/ altındaki bir dosyanın yolu (geliştirmede ve .exe içinde)."""
    import os, sys
    kokler = []
    if getattr(sys, "_MEIPASS", None):
        kokler.append(sys._MEIPASS)
    kokler.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    kokler.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    for kok in kokler:
        yol = os.path.join(kok, "assets", *parcalar)
        if os.path.isfile(yol):
            return yol
    return None


def uygulama_ikonu():
    """Uygulama ikonu: main.py'nin yanındaki assets/ klasöründe icon.ico / icon.png
    varsa onu kullanır (müşteri kendi logosunu koyabilir); yoksa çizilmiş
    varsayılan GameHub ikonu."""
    import os, sys
    from PyQt6.QtGui import (QIcon, QPixmap, QPainter, QColor, QLinearGradient,
                             QFont, QPen)
    from PyQt6.QtCore import Qt, QRectF
    kokler = [os.path.dirname(os.path.abspath(sys.argv[0])),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]
    if getattr(sys, "_MEIPASS", None):
        kokler.insert(0, sys._MEIPASS)
    for kok in kokler:
        for ad in ("icon.ico", "icon.png"):
            yol = os.path.join(kok, "assets", ad)
            if os.path.isfile(yol):
                ikon = QIcon(yol)
                if not ikon.isNull():
                    return ikon
    ikon = QIcon()
    for boyut in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(boyut, boyut)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, boyut, boyut)
        g.setColorAt(0, QColor(RENK["accent"]))
        g.setColorAt(1, QColor(RENK["accent2"]))
        p.setBrush(g)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, boyut, boyut), boyut * 0.24, boyut * 0.24)
        p.setPen(QPen(QColor("white")))
        f = QFont("Segoe UI")
        f.setBold(True)
        f.setPixelSize(int(boyut * 0.56))
        p.setFont(f)
        p.drawText(QRectF(0, 0, boyut, boyut), Qt.AlignmentFlag.AlignCenter, "GH")
        p.end()
        ikon.addPixmap(pm)
    return ikon


def _tik_ikonu_yolu() -> str:
    """Seçili onay kutusu için beyaz ✓ ikonunu çizip geçici klasöre yazar."""
    import os, tempfile
    from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
    from PyQt6.QtCore import Qt, QPointF
    yol = os.path.join(tempfile.gettempdir(), "gamehub_tik.png")
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    kalem = QPen(QColor("white"), 4.5)
    kalem.setCapStyle(Qt.PenCapStyle.RoundCap)
    kalem.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(kalem)
    p.drawPolyline([QPointF(8, 17), QPointF(14, 23), QPointF(24, 10)])
    p.end()
    pm.save(yol, "PNG")
    return yol.replace("\\", "/")
