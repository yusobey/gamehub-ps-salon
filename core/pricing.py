"""
Fiyatlandırma Motoru
=====================
Kurallar (kullanıcı ile netleşen mantık):
- İlk 30 dakika: saatlik ücretin yarısı, SABİT (artmaz).
- 31. dakikadan 60. dakikaya kadar: her dakika eşit oranda artar,
  60. dakikada tam saatlik ücrete ulaşır.
- 60. dakikadan sonra: aynı desen bir saatlik bloklar halinde tekrar eder
  (2. saat de kendi içinde aynı 30dk-sabit + 30dk-artan mantığıyla işler).
- Fiyat SIÇRAMALI (step) değişir: dakika tam bitmeden değişmez,
  dakika biter bitmez anında yeni değere geçer. Kademeli/yumuşak geçiş YOK.
- Ekranda gösterilen HER tutar 5 TL'nin katına YUKARI yuvarlanır.
  (101-104 -> 105, 106-109 -> 110). Küsuratlı tutar asla gösterilmez.

NOT: Bu dosya kasıtlı olarak UI'dan bağımsız, saf hesaplama katmanı.
İleride tarife yapısı değişirse (örn. ilk 30dk oranı ayarlanabilir olsun
istenirse) sadece burası güncellenir, UI tarafı etkilenmez.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta


def para_ustunu_dagitimdan_dus(dagitim: dict, toplam: float, nakit_anahtari: str = "NAKİT") -> dict:
    """
    Ödeme ekranlarında girilen tutar toplamı ödenecek tutardan FAZLA olabilir
    (müşteri 160 TL verip 130 TL'lik hesaba karşılık 30 TL para üstü alması
    gibi). Bu FAZLA kısım (para üstü) müşteriye GERİ VERİLDİĞİ için kasaya/
    ciroya asla o yöntemin tam girilen tutarıyla yazılmamalı - aksi halde
    ciro gerçekte kasada kalan paradan fazla görünür.

    Fazlalık öncelikle NAKİT'ten düşülür (para üstü gerçek hayatta hep
    nakitten verilir); nakit yetersiz/yoksa kalan fazlalık diğer yöntemlerden
    de düşülür. Sonuçta dönen dağılımın toplamı HER ZAMAN tam olarak
    'toplam'a eşit olur - orijinal dagitim sözlüğü DEĞİŞTİRİLMEZ, yeni bir
    kopya döner.
    """
    duzeltilmis = dict(dagitim)
    girilen = sum(duzeltilmis.values())
    fazla = girilen - toplam
    if fazla <= 0:
        return duzeltilmis

    if nakit_anahtari in duzeltilmis:
        dusum = min(duzeltilmis[nakit_anahtari], fazla)
        duzeltilmis[nakit_anahtari] -= dusum
        fazla -= dusum
        if duzeltilmis[nakit_anahtari] <= 0:
            del duzeltilmis[nakit_anahtari]

    if fazla > 0:
        for anahtar in list(duzeltilmis.keys()):
            if fazla <= 0:
                break
            dusum = min(duzeltilmis[anahtar], fazla)
            duzeltilmis[anahtar] -= dusum
            fazla -= dusum
            if duzeltilmis[anahtar] <= 0:
                del duzeltilmis[anahtar]

    return duzeltilmis


def round_up_5(amount: float) -> int:
    """Her zaman 5 TL'nin katına yukarı yuvarlar. 0 TL için 0 döner."""
    if amount <= 0:
        return 0
    import math
    return int(math.ceil(amount / 5.0) * 5)


def odenecek_tutar(ham_toplam: float, indirim: float = 0.0) -> int:
    """Ödenecek tutar: önce ekranda görünen toplam 5 TL'ye yuvarlanır, İNDİRİM bundan TAM
    olarak düşülür (125 - 119 = 6; eskiden 6 -> 10'a yuvarlanıyordu, hatalıydı).
    İndirim girilmediyse sonuç eskisiyle aynıdır."""
    return max(0, round_up_5(ham_toplam) - int(round(indirim or 0)))


def devam_price_for_elapsed(hourly_rate: float, elapsed_seconds: float) -> float:
    """
    Kol Değiştir ('şu andan itibaren') veya Masa Taşı sonrası DEVAM EDEN dilim
    için kullanılır. 'İlk 30 dakika sabit yarı fiyat' kuralı SADECE masanın
    İLK açılışında bir kez geçerlidir - kol değiştirildiğinde ya da masa
    taşındığında bu kural TEKRAR uygulanmaz (aksi halde her kol değişiminde
    anlık, haksız bir sıçrama olurdu). Bunun yerine oynanan dakikaya tam
    ORANTILI, dakika tamamlanınca sıçrayan (basamaklı ama düz oranlı) bir
    hesap yapılır: 0. dakikada 0 TL, 60. dakikada tam saatlik ücret.
    """
    if elapsed_seconds <= 0:
        return 0.0
    total_minutes_elapsed = int(elapsed_seconds // 60)
    return (total_minutes_elapsed / 60.0) * hourly_rate


def step_price_for_elapsed(hourly_rate: float, elapsed_seconds: float) -> float:
    """
    Verilen saatlik ücrete göre, geçen saniyeye karşılık gelen HAM (yuvarlanmamış)
    fiyatı döner.

    KURAL (kullanıcıyla netleşen, İKİ KEZ düzeltilen mantık):
    - 'İlk 30 dakika sabit yarım ücret + 31-60. dakika artan' basamaklı deseni
      SADECE masanın GERÇEK İLK SAATİNDE (elapsed < 60 dk) uygulanır.
    - 60. dakikadan SONRA bu bonus/desen BİR DAHA UYGULANMAZ - aksi halde her
      saat başında (61., 121., ... dakikalarda) yarım ücret bonusu bir kez
      daha eklenip (örn. 250 TL/saatte 60.dk'da 250 TL iken 61.dk'da aniden
      375 TL'ye sıçrama) ÇİFT SAYIM hatası oluşuyordu (bildirilen hata - bu
      fonksiyon önceden saatlik BLOKLAR halinde bu deseni TEKRARLIYORDU, o
      tasarım YANLIŞTI). 60. dakikadan sonrası artık devam_price_for_elapsed
      ile AYNI mantıkla (dakikaya tam orantılı, düz) hesaplanır - saat başına
      ekstra bir sıçrama YOKTUR, sadece sürekli/yumuşak artış vardır.
    """
    if elapsed_seconds <= 0:
        return 0.0

    half = hourly_rate / 2.0
    increment_per_minute = (hourly_rate - half) / 30.0

    total_minutes_elapsed = int(elapsed_seconds // 60)

    if total_minutes_elapsed < 60:
        # Gerçek ilk saat (henüz hiç tam saat tamamlanmadı) - basamaklı desen.
        if total_minutes_elapsed < 30:
            return half
        steps_passed = total_minutes_elapsed - 29
        price = half + steps_passed * increment_per_minute
        return min(price, hourly_rate)

    # 60. dakika ve sonrası: tam saatlerin ücreti + içinde bulunulan saate
    # dakikaya ORANTILI (düz, sıçramasız) ekleme - bonus TEKRARLANMAZ.
    full_hours = total_minutes_elapsed // 60
    minute_in_current_hour = total_minutes_elapsed % 60
    return full_hours * hourly_rate + (minute_in_current_hour / 60.0) * hourly_rate


def minutes_for_amount(hourly_rate: float, amount: float) -> float:
    """
    'Tutar ile Aç' için TERSİNE hesap: X TL karşılığı kaç dakika süre verilecek.

    VARSAYIM (kullanıcıya sorulacak): İlk 30 dakika ekranda SABİT fiyat gösterse
    de, süre satın alırken TL başına süre orantısal kabul edilir. Yani müşteri
    90 TL verdiğinde bu tutarın saatlik ücrete oranına göre dakika hesaplanır.
    Örn: saatlik 170 TL ise 90 TL -> (90/170)*60 dakikaya yakın bir değer,
    basamaklı yapının tersini alarak hesaplanır.
    """
    if amount <= 0 or hourly_rate <= 0:
        return 0.0

    half = hourly_rate / 2.0
    increment_per_minute = (hourly_rate - half) / 30.0

    full_hours = int(amount // hourly_rate)
    remaining = amount - (full_hours * hourly_rate)

    if remaining <= half:
        # İlk 30 dakikalık dilimde orantısal süre
        minutes_in_hour = (remaining / half) * 30.0 if half > 0 else 0.0
    else:
        extra = remaining - half
        steps = extra / increment_per_minute if increment_per_minute > 0 else 0.0
        minutes_in_hour = 30.0 + steps

    return full_hours * 60.0 + minutes_in_hour


@dataclass
class TariffSegment:
    """
    Bir masanın açık kaldığı süre boyunca, kol/tarife DEĞİŞTİRDİĞİ her an
    yeni bir segment başlar. Böylece 'saat X'te 2 KOL'den 4 KOL'e geçti'
    geçmişi tam olarak tutulur (detay ekranında gösterilecek).
    """
    tariff_name: str        # örn. "STANDART - 2 KOL"
    hourly_rate: float
    start_time: datetime
    base_amount: float = 0.0   # segment başlamadan önce birikmiş tutar
    end_time: datetime | None = None  # segment kapandıysa (ödeme alındıysa) doldurulur
    # True ise: bu segment bir "kol değiştir (şu andan itibaren)" ya da
    # "masa taşı" sonucu oluşmuştur - 'ilk 30dk sabit' kuralı UYGULANMAZ,
    # devam_price_for_elapsed kullanılır. False (varsayılan): masa YENİ
    # açıldığında ya da 'açılıştan itibaren'/'başlangıç saati düzelt' ile
    # SIFIRDAN hesaplanıyor gibi davranılır - ilk 30dk sabit kuralı geçerlidir.
    devam_segmenti: bool = False

    def elapsed_seconds(self, now: datetime | None = None) -> float:
        end = self.end_time or (now or datetime.now())
        return max(0.0, (end - self.start_time).total_seconds())

    def current_raw_amount(self, now: datetime | None = None, azami_saniye: float | None = None) -> float:
        elapsed = self.elapsed_seconds(now)
        if azami_saniye is not None and not self.devam_segmenti and elapsed >= azami_saniye:
            # Süreli masa (Süre/Tutar ile Aç) dolduğunda ücret, satın alınan sürenin tam sonundaki
            # fiyattır: 30 dk = ilk 30 dk sabit ücret. (Tam 30:00'da dakika sayacı bir sonraki
            # basamağa geçtiği için eskiden 125 yerine 130, 85 yerine 90 çıkıyordu.)
            elapsed = max(0.0, azami_saniye - 1e-6)
        if self.devam_segmenti:
            ham = devam_price_for_elapsed(self.hourly_rate, elapsed)
        else:
            ham = step_price_for_elapsed(self.hourly_rate, elapsed)
        return self.base_amount + ham

    def devam_esasli_tutar(self, now: datetime | None = None) -> float:
        """Kol Değiştir/Masa Taşı sırasında 'harcanan' (devredilecek) tutarı
        hesaplamak için kullanılır. Bu segment fiili ekranda 'ilk 30dk sabit'
        (plato) gösteriyor olsa bile - o plato SADECE o tarifede KALINDIĞI
        sürece geçerli bir 'masa açılış ücreti'dir. Kol değiştirilince/masa
        taşınınca plato iptal olur, bu tarifede GERÇEKTEN geçen dakikaya
        orantılı (düz) tutar esas alınır."""
        return self.base_amount + devam_price_for_elapsed(self.hourly_rate, self.elapsed_seconds(now))
