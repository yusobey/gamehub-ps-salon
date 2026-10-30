"""
Veri Modelleri
==============
Şimdilik hafızada (in-memory) çalışıyor. Bir sonraki aşamada bu katman
SQLite'a bağlanacak ama dışarıya (UI'a) verdiği arayüz aynı kalacak -
yani UI kodunu değiştirmemize gerek kalmayacak.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
import itertools

from core.pricing import TariffSegment, round_up_5


class MasaDurumu(str, Enum):
    BOS = "BOŞ"
    ACIK = "AÇIK"
    ODEME_BEKLIYOR = "ÖDEME BEKLENİYOR"
    DURAKLATILDI = "DURAKLATILDI"


class AcilisModu(str, Enum):
    NORMAL = "NORMAL"          # süre sınırsız, elle kapatılır
    SURE_ILE = "SURE_ILE"      # geri sayım
    TUTAR_ILE = "TUTAR_ILE"    # tutar karşılığı geri sayım


class OdemeYontemi(str, Enum):
    # NOT: QR ödeme yöntemi KALDIRILDI - Kart/POS ile ayrımı gereksiz
    # görüldüğü için kullanıcı isteğiyle kaldırıldı, "poslu işlemler" KART
    # altında toplanıyor. Eski kayıtlarda (varsa) "QR" anahtarlı geçmiş
    # veriler etkilenmez/silinmez, sadece yeni ödemelerde bu seçenek artık
    # sunulmuyor.
    NAKIT = "NAKİT"
    KART = "KART"
    IBAN = "İBAN"
    BORC = "BORÇ"


_id_counter = itertools.count(1)


def next_id() -> int:
    return next(_id_counter)


def id_sayacini_ayarla(baslangic: int):
    """Kayıtlı veriden geri yüklerken çağrılır - yeni oluşturulacak ID'lerin
    dosyadaki EN BÜYÜK ID'nin üzerinden devam etmesini sağlar, aksi halde
    program yeniden açıldığında ID'ler sıfırdan başlar ve mevcut kayıtlarla
    ÇAKIŞABİLİR (örn. iki farklı masa aynı ID'yi paylaşabilir)."""
    global _id_counter
    _id_counter = itertools.count(baslangic)


def is_gunu(zaman: datetime) -> date:
    """İş günü sınırı 06:00'dır: saat 06:00'dan önceki her şey BİR ÖNCEKİ günün
    'iş günü'ne sayılır. Örn. 02.09.2026 03:00 -> 01.09.2026 iş günü.
    Bu yüzden 'gün sonu' raporu, gerçek takvim gününü değil, salonun kapanış
    saatini esas alan bu mantığı kullanır."""
    if zaman.hour < 6:
        return (zaman - timedelta(days=1)).date()
    return zaman.date()


@dataclass
class UrunSatisi:
    urun_adi: str
    adet: int
    birim_fiyat: float
    eklenme_zamani: datetime = field(default_factory=datetime.now)

    @property
    def toplam(self) -> float:
        return self.adet * self.birim_fiyat


@dataclass
class KolDegisimKaydi:
    """Detay ekranında gösterilecek: hangi saatte hangi tarifeden hangi tarifeye geçildi."""
    zaman: datetime
    eski_tarife: str
    yeni_tarife: str


@dataclass
class Masa:
    id: int
    ad: str  # örn "PS4 MASA 1" - masa eklenince sadece bu değişir
    konsol_tipi: str = "PS4"  # PS4 / PS5 / DEV EKRAN - ayarlarda tanımlanır
    bolum: str = ""  # Anasayfada gruplanacağı başlık - boşsa konsol_tipi kullanılır.
                       # İleride "BİLARDO" gibi konsol dışı özel bölümler de eklenebilecek.
    aktif_tarife_profili: str = ""  # boşsa konsol tipinin varsayılan profili kullanılır
    # KALICI tarife: Ayarlar > Masa Bazlı Tarife Ataması'ndaki seçim. "Tarife Değiştir" /
    # "Tarife ile Aç" sadece o oturum içindir (aktif_tarife_profili); masa kapanınca
    # (ödeme/iptal) aktif tarife bu kalıcı tarifeye geri döner.
    varsayilan_tarife_profili: str = ""
    durum: MasaDurumu = MasaDurumu.BOS

    segments: list[TariffSegment] = field(default_factory=list)
    urunler: list[UrunSatisi] = field(default_factory=list)
    kol_degisim_gecmisi: list[KolDegisimKaydi] = field(default_factory=list)

    acilis_modu: AcilisModu = AcilisModu.NORMAL
    hedef_saniye: float | None = None  # SURE_ILE / TUTAR_ILE için geri sayım hedefi
    kilitli: bool = False
    ilk_acilis_zamani: datetime | None = None  # "masa açılışından itibaren" hesapları için

    # ------------ Zaman / Tutar hesapları ------------
    def toplam_baslangic_zamani(self) -> datetime | None:
        return self.segments[0].start_time if self.segments else None

    def guncel_masa_ucreti_ham(self, now: datetime | None = None) -> float:
        if not self.segments:
            return 0.0
        return self.segments[-1].current_raw_amount(now)

    def guncel_masa_ucreti(self, now: datetime | None = None) -> int:
        return round_up_5(self.guncel_masa_ucreti_ham(now))

    def urun_toplami(self) -> float:
        return sum(u.toplam for u in self.urunler)

    def genel_toplam(self, now: datetime | None = None) -> int:
        """Masa ücreti (5 TL yuvarlı) + ürün toplamı (ürünler yuvarlanmaz)."""
        return self.guncel_masa_ucreti(now) + int(self.urun_toplami())

    def kalan_geri_sayim_saniye(self, now: datetime | None = None) -> float | None:
        if self.acilis_modu == AcilisModu.NORMAL or self.hedef_saniye is None:
            return None
        # Kilitle/Odeme Al gibi dondur-devam-et döngülerinde her segment ayrı
        # sayılır, bu yüzden TÜM segmentlerin toplam süresi alınır - yoksa
        # devam edildiğinde geri sayım yanlışlıkla sıfırdan başlardı.
        gecen = sum(s.elapsed_seconds(now) for s in self.segments)
        kalan = self.hedef_saniye - gecen
        return max(0.0, kalan)

    def suresi_doldu_mu(self, now: datetime | None = None) -> bool:
        kalan = self.kalan_geri_sayim_saniye(now)
        return kalan is not None and kalan <= 0

    # ------------ Durum değişiklikleri ------------
    def gorunur_bolum(self) -> str:
        """bolum alanı boşsa konsol_tipi'ni bölüm başlığı olarak kullanır."""
        return self.bolum or self.konsol_tipi

    def ac(self, tarife_adi: str, saatlik_ucret: float, acilis_modu=AcilisModu.NORMAL,
           hedef_saniye: float | None = None):
        now = datetime.now()
        self.segments = [TariffSegment(tariff_name=tarife_adi, hourly_rate=saatlik_ucret, start_time=now)]
        self.urunler = []
        self.kol_degisim_gecmisi = []
        self.acilis_modu = acilis_modu
        self.hedef_saniye = hedef_saniye
        self.durum = MasaDurumu.ACIK
        self.ilk_acilis_zamani = now

    def kol_degistir_simdiden(self, yeni_tarife_adi: str, yeni_saatlik_ucret: float):
        """Kol/Tarife Değiştir - 'Şu andan itibaren': eski tarifede GERÇEKTEN
        geçen dakikaya orantılı tutar (plato/'ilk 30dk sabit' DEĞİL - o kural
        sadece o tarifede kalınırsa geçerlidir, değiştirilince iptal olur)
        devredilir. Yeni kol/tarife o andan itibaren, 'ilk 30dk sabit' kuralı
        UYGULANMADAN, oynanan dakikaya orantılı düz bir hesapla üstüne eklenir."""
        now = datetime.now()
        mevcut = self.segments[-1]
        harcanan = mevcut.devam_esasli_tutar(now)
        mevcut.end_time = now
        self.kol_degisim_gecmisi.append(
            KolDegisimKaydi(zaman=now, eski_tarife=mevcut.tariff_name,
                            yeni_tarife=f"{yeni_tarife_adi} (şu andan itibaren)")
        )
        self.segments.append(
            TariffSegment(tariff_name=yeni_tarife_adi, hourly_rate=yeni_saatlik_ucret,
                          start_time=now, base_amount=harcanan, devam_segmenti=True)
        )

    def kol_degistir_acilistan(self, yeni_tarife_adi: str, yeni_saatlik_ucret: float):
        """Kol/Tarife Değiştir - 'Masa açılışından itibaren': önceki kol/tarifenin
        ücreti TAMAMEN İPTAL edilir, masa SANKİ EN BAŞTAN yeni kol/tarife ile
        açılmış gibi, geçen sürenin tamamı yeni ücrete göre yeniden hesaplanır.

        ÖNEMLİ: devam_segmenti=True verilir - 'ilk 30dk sabit yarım ücret'
        kuralı burada UYGULANMAZ. O kural SADECE masanın gerçek İLK açılışında
        (Masa.ac()) bir kez geçerlidir; kol değiştirme (ister 'şu andan', ister
        'açılıştan itibaren' seçilsin) bu bonusu YENİDEN vermemeli - aksi halde
        kullanıcı kol/tarife değiştirdiğinde ekstra bir yarım-ücret sıçraması
        oluşurdu (bildirilen hata)."""
        now = datetime.now()
        eski_baslangic = self.ilk_acilis_zamani or (self.segments[0].start_time if self.segments else now)
        eski_ozet = self.segments[-1].tariff_name if self.segments else "-"
        self.segments = [
            TariffSegment(tariff_name=yeni_tarife_adi, hourly_rate=yeni_saatlik_ucret,
                          start_time=eski_baslangic, base_amount=0.0, devam_segmenti=True)
        ]
        self.kol_degisim_gecmisi.append(
            KolDegisimKaydi(zaman=now, eski_tarife=eski_ozet,
                            yeni_tarife=f"{yeni_tarife_adi} (masa açılışından itibaren yeniden hesaplandı)")
        )

    def baslangic_saatini_degistir(self, yeni_baslangic: datetime):
        """Süre Değiştir: masa açılırken unutulmuşsa, gerçek başlangıç saati
        manuel girilir. Mevcut tarife/kol korunur, tutar/süre o saate göre
        GÜNCEL SAATE ORANTILI olarak sıfırdan yeniden hesaplanır (kol_degistir_
        acilistan ile aynı mekanizma, sadece tarife değil zaman değişiyor).

        ÖNEMLİ: devam_segmenti=True verilir - 'ilk 30dk sabit yarım ücret'
        kuralı burada UYGULANMAZ. Bu kural SADECE masanın gerçek İLK
        açılışında (Masa.ac()) bir kez geçerlidir. Başlangıç saati düzeltilip
        süre GERİYE alındığında (ör. unutulan açılışı 1 saat öne çekmek) bu
        bonus tekrar eklenmemeli - aksi halde tutar, geçen sürenin tam saatlik
        ücretinin üstüne bir de fazladan yarım-ücret ekleyerek yanlış
        hesaplanırdı (bildirilen hata)."""
        if not self.segments:
            return
        aktif = self.segments[-1]
        self.segments = [
            TariffSegment(tariff_name=aktif.tariff_name, hourly_rate=aktif.hourly_rate,
                          start_time=yeni_baslangic, base_amount=0.0, devam_segmenti=True)
        ]
        self.ilk_acilis_zamani = yeni_baslangic
        self.kol_degisim_gecmisi.append(
            KolDegisimKaydi(
                zaman=datetime.now(), eski_tarife="Başlangıç saati düzeltildi",
                yeni_tarife=f"Yeni başlangıç: {yeni_baslangic.strftime('%H:%M')}"
            )
        )

    def sure_ekle(self, ek_saniye: float):
        """Süre Ekle: SÜRELİ (Süre ile Aç / Tutar ile Aç) masalarda kullanılır -
        müşteri süresi dolduğunda ya da dolmadan uzatmak istediğinde, geri
        sayım HEDEFİNE (hedef_saniye) ekstra süre eklenir. 'Süre Değiştir'
        (baslangic_saatini_degistir) İLE KARIŞTIRILMASIN: o, masanın
        BAŞLANGIÇ SAATİNİ değiştirip tutarı SIFIRDAN yeniden hesaplıyordu -
        süreli masalarda bu anlamsızdı (kullanıcı: 'süreli masalarda süre
        değiştir yerine süre eklkme olmalı'). Bu fonksiyon ise segment'lere
        ASLA dokunmaz - ücret, normal akışta olduğu gibi GEÇEN SÜREYE göre
        (guncel_masa_ucreti/step_price_for_elapsed) kendiliğinden birikmeye
        devam eder, sadece 'süre doldu' geri sayımı ötelenir."""
        if self.hedef_saniye is None:
            return
        self.hedef_saniye += ek_saniye
        self.kol_degisim_gecmisi.append(
            KolDegisimKaydi(
                zaman=datetime.now(), eski_tarife="Süre uzatıldı",
                yeni_tarife=f"+{int(ek_saniye // 60)} dakika eklendi"
            )
        )

    def tasi_ve_devret(self, hedef: "Masa", hedef_profil: str, hedef_kol_adi: str, hedef_saatlik_ucret: float):
        """Sürükle-bırak ile masa taşıma: BU masadaki (self) devam eden oturum
        (harcanan tutar + ürünler + geçmiş) hedef masaya aktarılır, hedef HEDEFİN
        KENDİ tarifesiyle ('şu andan itibaren' mantığıyla) devam eder. Kaynak masa
        tamamen boşa döner (kapat_ve_sifirla)."""
        now = datetime.now()
        harcanan = self.segments[-1].devam_esasli_tutar(now) if self.segments else 0.0
        eski_ozet = self.segments[-1].tariff_name if self.segments else "-"

        hedef.aktif_tarife_profili = hedef_profil
        hedef.segments = [
            TariffSegment(tariff_name=hedef_kol_adi, hourly_rate=hedef_saatlik_ucret,
                          start_time=now, base_amount=harcanan, devam_segmenti=True)
        ]
        hedef.ilk_acilis_zamani = self.ilk_acilis_zamani or now
        hedef.urunler = list(self.urunler)
        hedef.kol_degisim_gecmisi = list(self.kol_degisim_gecmisi) + [
            KolDegisimKaydi(
                zaman=now, eski_tarife=f"{self.ad}: {eski_ozet}",
                yeni_tarife=f"{hedef.ad}: {hedef_kol_adi} (masa taşındı)"
            )
        ]
        hedef.acilis_modu = self.acilis_modu
        hedef.hedef_saniye = self.hedef_saniye
        hedef.durum = MasaDurumu.ACIK
        hedef.kilitli = False

        self.kapat_ve_sifirla()

    def urun_ekle(self, urun_adi: str, birim_fiyat: float):
        """Aynı üründen zaten sepette varsa adedini 1 artırır, yoksa yeni satır açar."""
        mevcut = next((u for u in self.urunler if u.urun_adi == urun_adi), None)
        if mevcut:
            mevcut.adet += 1
        else:
            self.urunler.append(UrunSatisi(urun_adi=urun_adi, adet=1, birim_fiyat=birim_fiyat))

    def urun_azalt(self, urun_adi: str):
        """Adedi 1 azaltır, 0'a inerse satırı tamamen kaldırır."""
        mevcut = next((u for u in self.urunler if u.urun_adi == urun_adi), None)
        if mevcut:
            mevcut.adet -= 1
            if mevcut.adet <= 0:
                self.urunler.remove(mevcut)

    def urun_adedi(self, urun_adi: str) -> int:
        mevcut = next((u for u in self.urunler if u.urun_adi == urun_adi), None)
        return mevcut.adet if mevcut else 0

    def odeme_beklemeye_al(self):
        """Süre/tutar dolduğunda ya da 'Ödeme Al' ekranı açıldığında çağrılır.
        Segment'i dondurur (end_time atanır) böylece süre artık işlemez."""
        if self.segments and self.segments[-1].end_time is None:
            self.segments[-1].end_time = datetime.now()
        self.durum = MasaDurumu.ODEME_BEKLIYOR

    def odeme_devam_ettir(self):
        """Ödeme ekranından ya da kilitten 'devam et' ile dönülürse süre kaldığı
        yerden devam eder. AYNI segmentin başlangıç saati, duraklama süresi kadar
        ileri kaydırılır (segment yeniden başlatılmaz) - böylece hem geçen süre
        hem tutar sıçramadan, tam donduğu noktadan devam eder."""
        if self.segments and self.segments[-1].end_time is not None:
            seg = self.segments[-1]
            duraklama_suresi = datetime.now() - seg.end_time
            seg.start_time += duraklama_suresi
            seg.end_time = None
        self.durum = MasaDurumu.ACIK
        self.kilitli = False

    def kilitle(self):
        """Kilitle: süre/ücret aynen 'Ödeme Al' ekranındaki gibi DONAR, ürün
        eklenebilir ama tutar/süre işlemez. Tekrar tıklanınca DEVAM_ET ile açılır."""
        if self.segments and self.segments[-1].end_time is None:
            self.segments[-1].end_time = datetime.now()
        self.kilitli = True
        self.durum = MasaDurumu.DURAKLATILDI

    def kilidi_ac(self):
        """Kilidi Aç: süre kaldığı yerden devam eder (odeme_devam_ettir ile aynı mekanizma)."""
        self.odeme_devam_ettir()

    def kapat_ve_sifirla(self):
        self.segments = []
        self.urunler = []
        self.kol_degisim_gecmisi = []
        self.acilis_modu = AcilisModu.NORMAL
        self.hedef_saniye = None
        self.durum = MasaDurumu.BOS
        self.kilitli = False
        if self.varsayilan_tarife_profili:
            self.aktif_tarife_profili = self.varsayilan_tarife_profili

    def iptal_et(self):
        """Masayı İptal Et: ödeme alınmadan sıfırlar (ciroya YAZILMAZ)."""
        self.kapat_ve_sifirla()


@dataclass
class Borc:
    id: int
    ad_soyad: str
    tutar: float
    olusturma_zamani: datetime = field(default_factory=datetime.now)
    odendi: bool = False
    odenme_zamani: datetime | None = None
    kaynak_masa_adi: str = ""
    # Bu borcun doğduğu satışın (KasaIslemi) id'si - "Detay" ekranında o
    # masanın ücreti/ürünleri gösterilsin diye. Bu alan EKLENMEDEN önce
    # yazılmış eski borçlarda None'dır; onlar için AppState.borc_islemi_bul
    # zaman/masa eşleşmesiyle bulmayı dener.
    kasa_islem_id: int | None = None


@dataclass
class KasaIslemi:
    """
    Ciro/kasa hareketi. is_borc_tahsilati=True olan işlemler GÜNLÜK CİROYA
    DAHİL EDİLMEZ - kullanıcının özellikle vurguladığı kural budur:
    önceden borç yazılmış bir tutarın sonradan tahsil edilmesi, o günün
    satış cirosu gibi görünmemeli (zaten geçmişte bir kez borç olarak
    kapatılırken de ciroya yazılmamıştı - alacak/tahsilat farklı bir kalemdir).
    """
    id: int
    masa_adi: str
    toplam_tutar: float
    odeme_dagilimi: dict  # {"NAKİT": 200, "KART": 500}
    indirim_tutari: float = 0.0
    zaman: datetime = field(default_factory=datetime.now)  # KAPANIŞ (ödeme alınma) saati
    acilis_zamani: datetime | None = None  # Son İşlemler'de "açılış saati" göstermek için
    masa_ucreti: float = 0.0  # sadece süre ücreti (ürünler hariç) - Son İşlemler detayı için
    is_borc_tahsilati: bool = False
    is_borc_olusturma: bool = False  # bu işlemde borca yazılan kısım var mı
    # Kapanış anındaki ürün sepetinin anlık görüntüsü (Gün Sonu > "hangi
    # ürünler satılmış" raporu için) - [{"ad":"Cola","adet":2,"birim_fiyat":40.0}, ...]
    urunler: list = field(default_factory=list)
    # Doluysa bu kayıt GERÇEK bir satış değil, "Masayı İptal Et" ile
    # nedenli olarak iptal edilmiş bir masa kaydıdır - ciroya/masa bazlı
    # rapora KATILMAZ ama Son İşlemler'de sebebiyle birlikte görünür
    # (denetim/hesap sorma amaçlı - "neden iptal edildi" hep bilinsin).
    iptal_nedeni: str | None = None


@dataclass
class Gider:
    """Kasa > Gün Sonu'ndan eklenen gider kalemi (örn. 'Ömer günlük ücret').
    Günlük net ciro hesaplanırken toplam cirodan DÜŞÜLÜR."""
    id: int
    aciklama: str
    tutar: float
    zaman: datetime = field(default_factory=datetime.now)


@dataclass
class Avans:
    """Kasa > Gün Sonu'ndan eklenen açılış parası (örn. sabah kasaya konan
    bozukluk/para üstü parası). CİROYA DA GİDERE DE DAHİL EDİLMEZ - sadece
    bilgi amaçlı, kasada o gün ne kadar nakit bulunduğunu takip etmek için."""
    id: int
    aciklama: str
    tutar: float
    zaman: datetime = field(default_factory=datetime.now)


@dataclass
class Not:
    """Sol menü > Notlar. Küçük bir yapışkan not kağıdı gibi ekranda serbestçe
    gezdirilebilir, siz kapatana kadar hangi sayfada olursanız olun görünür kalır."""
    id: int
    metin: str = ""
    olusturma_zamani: datetime = field(default_factory=datetime.now)


class AppState:
    """Uygulamanın tek gerçek kaynağı (single source of truth). Şimdilik in-memory."""

    def __init__(self):
        self.salon_adi: str = "Salonum"
        # Ayarlar > Bildirim: süreli masa dolunca bildirim/ses tercihleri
        self.bildirim_ayarlari: dict = {}
        # Sol menüde GAMEHUB logosuna tıklayınca açılan Yardım penceresinde
        # gösterilir - programı kuran/satan kişinin iletişim bilgisi.
        self.gelistirici_iletisim: str = ""
        # Anasayfa > Alışveriş (masasız satış) sepeti - BİLEREK AppState'te
        # tutuluyor, dialog kapansa/pencere değişse bile silinmesin. Müşteri
        # ürünü seçip hemen ödemeyebilir (oturup sohbet edip sonra ödeyebilir)
        # - sepet SADECE ödeme tamamlanınca ya da kullanıcı elle temizleyince
        # boşalır. urun_adi -> {"adet":int, "birim_fiyat":float}
        self.masasiz_sepet: dict = {}
        self.masasiz_indirim: float = 0.0
        # ÖNEMLİ: Bu program artık HİÇBİR örnek/demo veriyle (masa, ürün,
        # tarife) gelmiyor - program bir bilgisayara YENİ kurulduğunda her şey
        # BOŞ başlar, salon sahibi kendi masalarını/ürünlerini/tarifelerini
        # Ayarlar ve Ürünler ekranlarından kendisi ekler. (Daha önceki
        # sürümlerde test amaçlı otomatik gelen PS4 MASA 1/2, PS5 MASA 1,
        # Cola/Cips gibi örnekler kalıcı olarak kaldırıldı.)
        self.tarife_profilleri: dict[str, dict[str, float]] = {}
        self.konsol_varsayilan_profil: dict[str, str] = {}
        # Masa Kayıtları > Konsol Tipi Ekle'den yönetilir - masa eklerken açılır
        # listede görünecek tüm tipler (henüz hiç masası olmasa bile).
        self.konsol_tipleri: list[str] = []
        # Masa Kayıtları > Grup Ekle'den yönetilir - Anasayfa'da masalar bu
        # gruplara göre YAN YANA panel halinde gösterilir (konsol tipinden
        # bağımsız - örn. "PlayStation" grubunda hem PS4 hem PS5 masaları,
        # "Bilardo" grubunda bilardo masaları olabilir).
        self.gruplar: list[str] = []
        self.masalar: list[Masa] = []
        # Anasayfada masaların gösterim sırası (masa id listesi). Boşsa self.masalar
        # sırası kullanılır. Anasayfa > Düzeni Değiştir'den sürükle-bırak ile kaydedilir.
        self.masa_sirasi: list[int] = []
        self.borclar: list[Borc] = []
        self.kasa_islemleri: list[KasaIslemi] = []
        self.giderler: list[Gider] = []
        self.avanslar: list[Avans] = []
        self.notlar: list[Not] = []
        # Her ürün {"fiyat":..., "gorsel": <dosya yolu ya da None>} - Ürünler
        # ekranından fiyat ve görsel düzenlenebilir.
        self.urun_katalogu: dict[str, dict[str, dict]] = {}

    def tarife_profili_ekle(self, ad: str) -> bool:
        if not ad or ad in self.tarife_profilleri:
            return False
        # BOŞ başlar - kafa karışıklığı olmasın diye otomatik "2 KOL" gelmez,
        # kullanıcı "+ Kol Ekle" popup'ından kendisi ekler.
        self.tarife_profilleri[ad] = {}
        return True

    def tarife_profili_yeniden_adlandir(self, eski_ad: str, yeni_ad: str) -> bool:
        if not yeni_ad or eski_ad == yeni_ad or yeni_ad in self.tarife_profilleri:
            return False
        if eski_ad not in self.tarife_profilleri:
            return False
        # Sozlukte sirayi bozmadan anahtari degistir
        yeni_sozluk = {}
        for k, v in self.tarife_profilleri.items():
            yeni_sozluk[yeni_ad if k == eski_ad else k] = v
        self.tarife_profilleri = yeni_sozluk
        # Bu profili kullanan tum masalari ve varsayilan konsol eslesmelerini guncelle
        for masa in self.masalar:
            if masa.aktif_tarife_profili == eski_ad:
                masa.aktif_tarife_profili = yeni_ad
            if masa.varsayilan_tarife_profili == eski_ad:
                masa.varsayilan_tarife_profili = yeni_ad
        for konsol, profil in list(self.konsol_varsayilan_profil.items()):
            if profil == eski_ad:
                self.konsol_varsayilan_profil[konsol] = yeni_ad
        return True

    def tarife_profili_sil(self, ad: str) -> tuple[bool, str]:
        if len(self.tarife_profilleri) <= 1:
            return False, "En az bir tarife profili kalmalı."
        if any(ad in (m.aktif_tarife_profili, m.varsayilan_tarife_profili) for m in self.masalar):
            return False, "Bu tarifeyi kullanan masalar var - önce onları başka tarifeye taşıyın."
        del self.tarife_profilleri[ad]
        for konsol, profil in list(self.konsol_varsayilan_profil.items()):
            if profil == ad:
                self.konsol_varsayilan_profil[konsol] = next(iter(self.tarife_profilleri))
        return True, ""

    def konsol_tipi_ekle(self, ad: str) -> bool:
        if not ad or ad in self.konsol_tipleri:
            return False
        self.konsol_tipleri.append(ad)
        return True

    def grup_ekle(self, ad: str) -> bool:
        if not ad or ad in self.gruplar:
            return False
        self.gruplar.append(ad)
        return True

    def grup_yeniden_adlandir(self, eski: str, yeni: str) -> bool:
        """Birim (grup) adını düzeltir; içindeki TÜM masalar korunur (silip yeniden eklemek gerekmez)."""
        yeni = (yeni or "").strip()
        if not yeni or yeni == eski or eski not in self.gruplar or yeni in self.gruplar:
            return False
        self.gruplar[self.gruplar.index(eski)] = yeni
        for m in self.masalar:
            if m.gorunur_bolum() == eski:
                m.bolum = yeni
        return True

    def kategori_yeniden_adlandir(self, grup: str, eski: str, yeni: str,
                                  masa_adlarini_da: bool = False) -> bool:
        """Bir birimdeki kategori adını (konsol_tipi) düzeltir. Aynı birimde zaten o adda
        kategori varsa ikisi birleşir. masa_adlarini_da=True ise 'ps4 1' gibi eski adla
        başlayan masa adları da yeni adla güncellenir (çakışan ad oluşursa o masa atlanır)."""
        yeni = (yeni or "").strip()
        if not yeni or yeni == eski:
            return False
        etkilenen = [m for m in self.masalar if m.gorunur_bolum() == grup and m.konsol_tipi == eski]
        if not etkilenen:
            return False
        for m in etkilenen:
            m.konsol_tipi = yeni
            if masa_adlarini_da and m.ad.startswith(eski):
                aday = yeni + m.ad[len(eski):]
                if not any(x is not m and x.ad == aday for x in self.masalar):
                    m.ad = aday
        if not any(m.konsol_tipi == eski for m in self.masalar):
            if eski in self.konsol_tipleri:
                if yeni in self.konsol_tipleri:
                    self.konsol_tipleri.remove(eski)
                else:
                    self.konsol_tipleri[self.konsol_tipleri.index(eski)] = yeni
            if eski in self.konsol_varsayilan_profil:
                prof = self.konsol_varsayilan_profil.pop(eski)
                self.konsol_varsayilan_profil.setdefault(yeni, prof)
        elif yeni not in self.konsol_tipleri:
            self.konsol_tipleri.append(yeni)
        return True

    def grup_sil(self, ad: str) -> bool:
        """Grubu KULLANAN masa varsa silmez (masalar önce başka gruba
        taşınmalı/silinmeli) - aksi halde o masalar 'hayalet' bir grupta kalır."""
        if any(m.gorunur_bolum() == ad for m in self.masalar):
            return False
        if ad in self.gruplar:
            self.gruplar.remove(ad)
            return True
        return False

    def masa_ekle(self, ad: str, konsol_tipi: str = "PS4", grup: str | None = None) -> Masa:
        # Varsayılan tarife seçimi (öncelik sırasıyla):
        # 1) Bu gruba/konsol tipine daha önce "Masa Bazlı Tarife Ataması"ndan
        #    açıkça bir tarife atanmışsa onu kullan.
        # 2) Grup adıyla BİREBİR aynı isimde bir tarife profili varsa onu
        #    kullan (kullanıcılar genelde "DEV EKRAN" grubuna "DEV EKRAN"
        #    tarifesini, "PS4/5 STANDART" grubuna aynı isimli tarifeyi
        #    veriyor - bu isimlendirme örtüşmesini akıllıca kullanıyoruz).
        # 3) Hiçbiri yoksa, son çare olarak tanımlı İLK tarifeyi kullan
        #    (eskiden HER ZAMAN buraya düşülüyordu, bu da grup ne olursa
        #    olsun tüm yeni masaların aynı tarifeyi almasına sebep oluyordu).
        profil = (
            self.konsol_varsayilan_profil.get(konsol_tipi)
            or (konsol_tipi if konsol_tipi in self.tarife_profilleri else None)
            or next(iter(self.tarife_profilleri), "")
        )
        grup_adi = grup or konsol_tipi
        m = Masa(
            id=next_id(), ad=ad, konsol_tipi=konsol_tipi, bolum=grup_adi,
            aktif_tarife_profili=profil, varsayilan_tarife_profili=profil,
        )
        self.masalar.append(m)
        self.masa_sirasi.append(m.id)
        if konsol_tipi not in self.konsol_tipleri:
            self.konsol_tipleri.append(konsol_tipi)
        if grup_adi not in self.gruplar:
            self.gruplar.append(grup_adi)
        return m

    def siralanmis_masalar(self) -> list["Masa"]:
        """masa_sirasi'na göre sıralı masa listesi döner (Masa Düzeni'nden kaydedilen
        sıra). Sırada olmayan (yeni eklenmiş) masalar sona eklenir."""
        if not self.masa_sirasi:
            return list(self.masalar)
        id_to_masa = {m.id: m for m in self.masalar}
        sirali = [id_to_masa[i] for i in self.masa_sirasi if i in id_to_masa]
        sirali += [m for m in self.masalar if m.id not in self.masa_sirasi]
        return sirali

    def gunluk_ciro(self) -> float:
        """Borç tahsilatları HARİÇ tutularak hesaplanan TÜM ZAMANLARIN toplam cirosu."""
        return sum(k.toplam_tutar for k in self.kasa_islemleri if not k.is_borc_tahsilati)

    def toplam_tahsil_edilen_borc(self) -> float:
        return sum(k.toplam_tutar for k in self.kasa_islemleri if k.is_borc_tahsilati)

    def anlik_salon_toplami(self) -> float:
        """Kasa > Anlık Salon: şu an açık/dolu tüm masaların GÜNCEL tutarlarının
        toplamı - henüz ödeme alınmamış, oynanmaya devam eden hesaplar."""
        return sum(m.genel_toplam() for m in self.masalar if m.durum != MasaDurumu.BOS)

    def borc_islemi_bul(self, borc: "Borc"):
        """Borcun doğduğu satış kaydını (KasaIslemi) döndürür, bulunamazsa None.
        Önce kayıtlı id'ye bakar; eski (id'siz) borçlar için aynı masa adlı,
        borç oluşturan ve borcun yazıldığı ana EN YAKIN (en fazla 2 dk) satışı seçer."""
        if borc.kasa_islem_id is not None:
            for k in self.kasa_islemleri:
                if k.id == borc.kasa_islem_id:
                    return k
        adaylar = [
            k for k in self.kasa_islemleri
            if k.is_borc_olusturma and not k.iptal_nedeni and not k.is_borc_tahsilati
            and k.masa_adi == borc.kaynak_masa_adi
            and abs((k.zaman - borc.olusturma_zamani).total_seconds()) <= 120
        ]
        if not adaylar:
            return None
        return min(adaylar, key=lambda k: abs((k.zaman - borc.olusturma_zamani).total_seconds()))

    def gun_ozet(self, gun: date) -> dict:
        """Kasa > Gün Sonu: verilen İŞ GÜNÜ (06:00-05:59 aralığı) için tam rapor.
        'gun' parametresi is_gunu() ile hesaplanan takvim tarihidir."""
        satislar = [
            k for k in self.kasa_islemleri
            if not k.is_borc_tahsilati and not k.iptal_nedeni and is_gunu(k.zaman) == gun
        ]
        borc_tahsilatlari = [k for k in self.kasa_islemleri if k.is_borc_tahsilati and is_gunu(k.zaman) == gun]
        giderler_gun = sorted([g for g in self.giderler if is_gunu(g.zaman) == gun], key=lambda g: g.zaman)
        avanslar_gun = sorted([a for a in self.avanslar if is_gunu(a.zaman) == gun], key=lambda a: a.zaman)

        ciro = sum(s.toplam_tutar for s in satislar)
        toplam_gider = sum(g.tutar for g in giderler_gun)
        toplam_avans = sum(a.tutar for a in avanslar_gun)

        masa_bazli: dict[str, dict] = {}
        masa_disi_satis_toplami = 0.0
        masa_disi_urun_bazli: dict[str, dict] = {}
        toplam_indirim = 0.0
        for s in satislar:
            # "Masa Dışı Alışveriş" (Anasayfa > Alışveriş kartından yapılan
            # masasız satış) gerçek bir masa DEĞİL - "Masa Bazlı Ciro"
            # listesine/en çok kazandıran yarışına karışmasın, ayrı bir
            # toplam olarak gösterilsin. Ürünleri de "Satılan Ürünler"e
            # KARIŞMASIN diye ayrı bir sözlükte tutuluyor - aksi halde aynı
            # ürün hem "Satılan Ürünler"de hem "Masa Dışı Satış"ta görünüp
            # sanki iki ayrı satış varmış gibi kafa karıştırıyordu.
            if s.masa_adi == "Masa Dışı Alışveriş":
                masa_disi_satis_toplami += s.toplam_tutar
                for u in s.urunler:
                    kayit = masa_disi_urun_bazli.setdefault(u["ad"], {"adet": 0, "tutar": 0.0})
                    kayit["adet"] += u["adet"]
                    kayit["tutar"] += u["adet"] * u["birim_fiyat"]
            else:
                kayit = masa_bazli.setdefault(
                    s.masa_adi, {"toplam": 0.0, "masa_ucreti": 0.0, "urun_geliri": 0.0}
                )
                urun_toplami_bu_islem = sum(u["adet"] * u["birim_fiyat"] for u in s.urunler)
                # İndirim EKRANDA masa ücretinden düşülmüş gibi gösterilir
                # (siparişin mantığı bu şekilde - önce masa ücretinden düşer,
                # taşarsa kalanı üründen düşer) - aksi halde "Masa: X ₺"
                # yazan kısım indirimsizmiş gibi görünüyordu.
                indirim_bu_islem = s.indirim_tutari
                efektif_masa_ucreti = max(0.0, s.masa_ucreti - indirim_bu_islem)
                kalan_indirim = indirim_bu_islem - (s.masa_ucreti - efektif_masa_ucreti)
                efektif_urun_geliri = max(0.0, urun_toplami_bu_islem - kalan_indirim)
                kayit["toplam"] += s.toplam_tutar
                kayit["masa_ucreti"] += efektif_masa_ucreti
                kayit["urun_geliri"] += efektif_urun_geliri
                toplam_indirim += indirim_bu_islem

        # "Satılan Ürünler" HER KAYNAKTAN (hem gerçek masalardan hem Masa
        # Dışı Alışveriş'ten) satılan ürünlerin TOPLAMINI gösterir - yani 6
        # adet masada + 2 adet masa dışında satılan Kola varsa burada 8
        # olarak görünür. "Masa Dışı Satış" detayı ise bu 8'in İÇİNDEN hangi
        # kısmının masa dışında satıldığını (2 Kola) ayrıca gösterir - bu
        # ikisi ÇELİŞMEZ, biri toplam biri alt kırılım.
        urun_bazli: dict[str, dict] = {}
        for s in satislar:
            for u in s.urunler:
                kayit = urun_bazli.setdefault(u["ad"], {"adet": 0, "tutar": 0.0})
                kayit["adet"] += u["adet"]
                kayit["tutar"] += u["adet"] * u["birim_fiyat"]

        odeme_bazli: dict[str, float] = {}
        for s in satislar:
            for yontem, tutar in s.odeme_dagilimi.items():
                odeme_bazli[yontem] = odeme_bazli.get(yontem, 0.0) + tutar

        en_cok_kazandiran = (
            max(masa_bazli.items(), key=lambda kv: kv[1]["toplam"])
            if masa_bazli else None
        )
        if en_cok_kazandiran:
            en_cok_kazandiran = (en_cok_kazandiran[0], en_cok_kazandiran[1]["toplam"])

        # Ciro'nun ne kadarının masa (süre) ücretinden, ne kadarının ürün
        # ("market") satışından geldiğini ayrı ayrı göstermek için.
        toplam_masa_ucreti = sum(v["masa_ucreti"] for v in masa_bazli.values())
        toplam_urun_geliri = sum(v["tutar"] for v in urun_bazli.values())

        return {
            "gun": gun,
            "ciro": ciro,
            "gider": toplam_gider,
            "net": ciro - toplam_gider,
            "avans": toplam_avans,
            "masa_bazli": sorted(masa_bazli.items(), key=lambda kv: -kv[1]["toplam"]),
            "urun_bazli": sorted(urun_bazli.items(), key=lambda kv: -kv[1]["tutar"]),
            "odeme_bazli": odeme_bazli,
            "en_cok_kazandiran": en_cok_kazandiran,
            "masa_disi_satis_toplami": masa_disi_satis_toplami,
            "masa_disi_urun_bazli": sorted(masa_disi_urun_bazli.items(), key=lambda kv: -kv[1]["tutar"]),
            "toplam_masa_ucreti": toplam_masa_ucreti,
            "toplam_urun_geliri": toplam_urun_geliri,
            "toplam_indirim": toplam_indirim,
            "borc_tahsilati_toplam": sum(b.toplam_tutar for b in borc_tahsilatlari),
            "giderler": giderler_gun,
            "avanslar": avanslar_gun,
            "satis_sayisi": len(satislar),
        }

    def mevcut_gunler(self) -> list[date]:
        """Ciro/gider/avans kaydı bulunan tüm iş günlerini (tekilleştirilmiş,
        en yeni önce) döner - Kasa > Genel'de ay ay gruplamak için kullanılır."""
        gunler = set()
        for k in self.kasa_islemleri:
            gunler.add(is_gunu(k.zaman))
        for g in self.giderler:
            gunler.add(is_gunu(g.zaman))
        for a in self.avanslar:
            gunler.add(is_gunu(a.zaman))
        return sorted(gunler, reverse=True)
