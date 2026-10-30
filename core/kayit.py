# -*- coding: utf-8 -*-
"""
Kalıcı Veri Saklama
====================
Program kapanıp açıldığında (hatta elektrik kesintisi gibi ANİ kapanmalarda
bile) hiçbir verinin kaybolmaması için AppState düzenli aralıklarla ve
kapanışta bir JSON dosyasına ATOMİK olarak yazılır, açılışta oradan geri
yüklenir.

ATOMİK YAZMA NE DEMEK: Doğrudan asıl dosyanın üzerine yazmak yerine önce
".tmp" uzantılı GEÇİCİ bir dosyaya tam olarak yazılır, ancak yazma TAMAMEN
bittikten sonra bu geçici dosya asıl dosyanın üzerine "değiştirilir"
(os.replace - işletim sistemi düzeyinde bölünmez/atomik bir işlem). Böylece
tam yazma sırasında elektrik kesilirse bile ASIL dosya bozulmaz - ya eski
hali (son başarılı kayıt) ya da yeni hali kalır, ASLA yarım/bozuk kalmaz.
"""
import sys
import os
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime

from core.models import (
    AppState, Masa, Borc, KasaIslemi, Gider, Avans, Not, UrunSatisi,
    KolDegisimKaydi, MasaDurumu, AcilisModu, id_sayacini_ayarla,
)
from core.pricing import TariffSegment


def veri_dosyasi_yolu() -> Path:
    """Veri dosyasının nerede tutulacağını belirler. Programın kendisi
    nereye kurulursa kurulsun/güncellensin - Windows'ta HER ZAMAN
    %APPDATA%\\GameHub\\ klasöründe durur, program dosyalarından TAMAMEN
    BAĞIMSIZDIR. Böylece bir güncelleme sırasında program klasörü silinip
    yeni sürüm konsa bile (ya da program başka bir yere taşınsa bile) veri
    ASLA kaybolmaz - eskiden .exe'nin yanına/proje köküne yazılıyordu, bu da
    program klasörü silinince verinin de gitmesi demekti."""
    if sys.platform == "win32":
        taban = Path(os.environ.get("APPDATA", Path.home())) / "GameHub"
    else:
        # Geliştirme ortamı (Linux/Mac) için - Windows'ta bu dal hiç çalışmaz
        taban = Path.home() / ".gamehub"
    taban.mkdir(parents=True, exist_ok=True)
    return taban / "salon_verileri.json"


def gorsel_klasoru() -> Path:
    """Ürün görsellerinin KALICI olarak saklandığı klasör - veri dosyasıyla
    AYNI dizinin altında 'gorseller' alt klasörü. Kullanıcı bir ürüne görsel
    seçtiğinde, orijinal dosya (örn. masaüstündeki bir resim) SİLİNSE/
    TAŞINSA bile uygulamanın görseli kaybetmemesi için, seçilen dosya bu
    klasöre KOPYALANIR ve ürün kaydında bu kopyanın yolu tutulur - asla
    kullanıcının orijinal dosyasının yoluna güvenilmez."""
    yol = veri_dosyasi_yolu().parent / "gorseller"
    yol.mkdir(parents=True, exist_ok=True)
    return yol


def gorseli_kalici_klasore_kopyala(kaynak_yol: str) -> str | None:
    """Kullanıcının seçtiği bir görsel dosyasını kalıcı 'gorseller' klasörüne
    kopyalar ve kopyanın yolunu döner. Kopyalama başarısız olursa (dosya
    silinmiş, izin yok vb.) None döner - çağıran taraf bu durumda eski
    davranışa (orijinal yolu kullanma) düşebilir ya da hata gösterebilir.
    Dosya adı çakışmalarını önlemek için benzersiz bir önek eklenir (aynı
    isimli iki farklı görsel seçilirse birbirinin üzerine yazmasın)."""
    try:
        kaynak = Path(kaynak_yol)
        if not kaynak.exists() or not kaynak.is_file():
            return None
        benzersiz_ad = f"{uuid.uuid4().hex[:12]}_{kaynak.name}"
        hedef = gorsel_klasoru() / benzersiz_ad
        shutil.copyfile(kaynak, hedef)
        return str(hedef)
    except Exception:
        return None


def _gorselleri_kalici_yap(katalog: dict):
    """ESKİ sürümlerde ürün görseli orijinal dosya yoluyla (örn. masaüstü)
    saklanıyordu - o dosya silinince görsel kayboluyordu. Açılışta, hâlâ var olan
    ama 'gorseller' klasörü DIŞINDAKİ görselleri kalıcı klasöre kopyalayıp yolu
    günceller (artık orijinal silinse de ürün görseli kalır)."""
    try:
        kalici = gorsel_klasoru().resolve()
        for kategori in katalog.values():
            for urun in kategori.values():
                yol = urun.get("gorsel") if isinstance(urun, dict) else None
                if not yol:
                    continue
                p = Path(yol)
                try:
                    if p.resolve().parent == kalici:
                        continue
                except Exception:
                    pass
                yeni = gorseli_kalici_klasore_kopyala(yol)
                if yeni:
                    urun["gorsel"] = yeni
    except Exception:
        pass


def yedek_klasoru() -> Path:
    """Günlük dönen yedeklerin tutulduğu klasör - veri dosyasıyla AYNI
    dizinin altında 'yedekler' alt klasörü."""
    yol = veri_dosyasi_yolu().parent / "yedekler"
    yol.mkdir(parents=True, exist_ok=True)
    return yol


def _eski_yedekleri_temizle(gunler_saklanacak: int = 7):
    """Sadece SON N günün yedeğini tutar, daha eskilerini siler - disk
    dolmasın diye sonsuza kadar birikmesin."""
    try:
        yedekler = sorted(yedek_klasoru().glob("yedek_*.json"))
        fazlalik = len(yedekler) - gunler_saklanacak
        for eski in yedekler[:max(0, fazlalik)]:
            eski.unlink()
    except Exception:
        pass  # yedek temizliği başarısız olsa bile asıl kayıt ETKİLENMEMELİ


def _gunluk_yedek_al(veri: dict):
    """Her BAŞARILI kaydetmede, o güne ait yedek dosyasını günceller (aynı
    gün içinde tekrar tekrar üzerine yazılır, gün değişince YENİ bir dosya
    açılır) - böylece elde her zaman son 7 günün ayrı ayrı anlık görüntüsü
    kalır, ana dosya bir şekilde bozulursa/silinirse buradan geri dönülebilir.
    Yedekleme başarısız olsa bile ASIL kayıt işlemini ASLA etkilemez."""
    try:
        bugun = datetime.now().strftime("%Y-%m-%d")
        yedek_yol = yedek_klasoru() / f"yedek_{bugun}.json"
        gecici_yol = yedek_yol.with_suffix(".tmp")
        with open(gecici_yol, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        gecici_yol.replace(yedek_yol)
        _eski_yedekleri_temizle()
    except Exception:
        pass


# ---------------------------------------------------------------
#  Tarih/saat yardımcıları (JSON'da datetime tutulamaz, metne çeviriyoruz)
# ---------------------------------------------------------------
def _dt(z: datetime | None) -> str | None:
    return z.isoformat() if z is not None else None


def _dt_oku(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


# ---------------------------------------------------------------
#  Her veri sınıfı için yaz/oku çifti
# ---------------------------------------------------------------
def _segment_yaz(s: TariffSegment) -> dict:
    return {
        "tariff_name": s.tariff_name, "hourly_rate": s.hourly_rate,
        "start_time": _dt(s.start_time), "base_amount": s.base_amount,
        "end_time": _dt(s.end_time), "devam_segmenti": s.devam_segmenti,
    }


def _segment_oku(d: dict) -> TariffSegment:
    return TariffSegment(
        tariff_name=d["tariff_name"], hourly_rate=d["hourly_rate"],
        start_time=_dt_oku(d["start_time"]) or datetime.now(),
        base_amount=d.get("base_amount", 0.0),
        end_time=_dt_oku(d.get("end_time")),
        devam_segmenti=d.get("devam_segmenti", False),
    )


def _urun_satisi_yaz(u: UrunSatisi) -> dict:
    return {"urun_adi": u.urun_adi, "adet": u.adet, "birim_fiyat": u.birim_fiyat,
            "eklenme_zamani": _dt(u.eklenme_zamani)}


def _urun_satisi_oku(d: dict) -> UrunSatisi:
    return UrunSatisi(
        urun_adi=d["urun_adi"], adet=d["adet"], birim_fiyat=d["birim_fiyat"],
        eklenme_zamani=_dt_oku(d.get("eklenme_zamani")) or datetime.now(),
    )


def _kol_kaydi_yaz(k: KolDegisimKaydi) -> dict:
    return {"zaman": _dt(k.zaman), "eski_tarife": k.eski_tarife, "yeni_tarife": k.yeni_tarife}


def _kol_kaydi_oku(d: dict) -> KolDegisimKaydi:
    return KolDegisimKaydi(
        zaman=_dt_oku(d.get("zaman")) or datetime.now(),
        eski_tarife=d.get("eski_tarife", ""), yeni_tarife=d.get("yeni_tarife", ""),
    )


def _masa_yaz(m: Masa) -> dict:
    return {
        "id": m.id, "ad": m.ad, "konsol_tipi": m.konsol_tipi, "bolum": m.bolum,
        "aktif_tarife_profili": m.aktif_tarife_profili,
        "varsayilan_tarife_profili": m.varsayilan_tarife_profili, "durum": m.durum.value,
        "segments": [_segment_yaz(s) for s in m.segments],
        "urunler": [_urun_satisi_yaz(u) for u in m.urunler],
        "kol_degisim_gecmisi": [_kol_kaydi_yaz(k) for k in m.kol_degisim_gecmisi],
        "acilis_modu": m.acilis_modu.value, "hedef_saniye": m.hedef_saniye,
        "kilitli": m.kilitli, "ilk_acilis_zamani": _dt(m.ilk_acilis_zamani),
    }


def _masa_oku(d: dict) -> Masa:
    return Masa(
        id=d["id"], ad=d["ad"], konsol_tipi=d.get("konsol_tipi", "PS4"),
        bolum=d.get("bolum", ""), aktif_tarife_profili=d.get("aktif_tarife_profili", ""),
        # eski kayıtlarda yok: mevcut atamayı kalıcı kabul et
        varsayilan_tarife_profili=d.get("varsayilan_tarife_profili") or d.get("aktif_tarife_profili", ""),
        durum=MasaDurumu(d.get("durum", "BOŞ")),
        segments=[_segment_oku(s) for s in d.get("segments", [])],
        urunler=[_urun_satisi_oku(u) for u in d.get("urunler", [])],
        kol_degisim_gecmisi=[_kol_kaydi_oku(k) for k in d.get("kol_degisim_gecmisi", [])],
        acilis_modu=AcilisModu(d.get("acilis_modu", "NORMAL")),
        hedef_saniye=d.get("hedef_saniye"), kilitli=d.get("kilitli", False),
        ilk_acilis_zamani=_dt_oku(d.get("ilk_acilis_zamani")),
    )


def _borc_yaz(b: Borc) -> dict:
    return {
        "id": b.id, "ad_soyad": b.ad_soyad, "tutar": b.tutar,
        "olusturma_zamani": _dt(b.olusturma_zamani), "odendi": b.odendi,
        "odenme_zamani": _dt(b.odenme_zamani), "kaynak_masa_adi": b.kaynak_masa_adi,
        "kasa_islem_id": b.kasa_islem_id,
    }


def _borc_oku(d: dict) -> Borc:
    return Borc(
        id=d["id"], ad_soyad=d["ad_soyad"], tutar=d["tutar"],
        olusturma_zamani=_dt_oku(d.get("olusturma_zamani")) or datetime.now(),
        odendi=d.get("odendi", False), odenme_zamani=_dt_oku(d.get("odenme_zamani")),
        kaynak_masa_adi=d.get("kaynak_masa_adi", ""),
        kasa_islem_id=d.get("kasa_islem_id"),
    )


def _kasa_islemi_yaz(k: KasaIslemi) -> dict:
    return {
        "id": k.id, "masa_adi": k.masa_adi, "toplam_tutar": k.toplam_tutar,
        "odeme_dagilimi": k.odeme_dagilimi, "indirim_tutari": k.indirim_tutari,
        "zaman": _dt(k.zaman), "acilis_zamani": _dt(k.acilis_zamani),
        "masa_ucreti": k.masa_ucreti, "is_borc_tahsilati": k.is_borc_tahsilati,
        "is_borc_olusturma": k.is_borc_olusturma, "urunler": k.urunler,
        "iptal_nedeni": k.iptal_nedeni,
    }


def _kasa_islemi_oku(d: dict) -> KasaIslemi:
    return KasaIslemi(
        id=d["id"], masa_adi=d["masa_adi"], toplam_tutar=d["toplam_tutar"],
        odeme_dagilimi=d.get("odeme_dagilimi", {}), indirim_tutari=d.get("indirim_tutari", 0.0),
        zaman=_dt_oku(d.get("zaman")) or datetime.now(),
        acilis_zamani=_dt_oku(d.get("acilis_zamani")),
        masa_ucreti=d.get("masa_ucreti", 0.0),
        is_borc_tahsilati=d.get("is_borc_tahsilati", False),
        is_borc_olusturma=d.get("is_borc_olusturma", False),
        urunler=d.get("urunler", []),
        iptal_nedeni=d.get("iptal_nedeni"),
    )


def _gider_yaz(g: Gider) -> dict:
    return {"id": g.id, "aciklama": g.aciklama, "tutar": g.tutar, "zaman": _dt(g.zaman)}


def _gider_oku(d: dict) -> Gider:
    return Gider(id=d["id"], aciklama=d["aciklama"], tutar=d["tutar"],
                 zaman=_dt_oku(d.get("zaman")) or datetime.now())


def _avans_yaz(a: Avans) -> dict:
    return {"id": a.id, "aciklama": a.aciklama, "tutar": a.tutar, "zaman": _dt(a.zaman)}


def _avans_oku(d: dict) -> Avans:
    return Avans(id=d["id"], aciklama=d["aciklama"], tutar=d["tutar"],
                 zaman=_dt_oku(d.get("zaman")) or datetime.now())


def _not_yaz(n: Not) -> dict:
    return {"id": n.id, "metin": n.metin, "olusturma_zamani": _dt(n.olusturma_zamani)}


def _not_oku(d: dict) -> Not:
    return Not(id=d["id"], metin=d.get("metin", ""),
               olusturma_zamani=_dt_oku(d.get("olusturma_zamani")) or datetime.now())


# ---------------------------------------------------------------
#  Ana kaydet / yükle
# ---------------------------------------------------------------
KAYIT_ENGELLI = False  # yedekten geri yükleme sonrası eski veriyle ÜSTÜNE YAZILMASIN diye


def kaydet(state: AppState) -> bool:
    """AppState'in TAMAMINI diske yazar. Hata olursa (disk dolu, izin yok vb.)
    programı ÇÖKERTMEZ, sessizce False döner - kalıcı kayıt önemli ama
    kasadaki işi durdurmaya değmez."""
    if KAYIT_ENGELLI:
        return False
    try:
        veri = {
            "surum": 1,
            "salon_adi": state.salon_adi,
            "bildirim_ayarlari": state.bildirim_ayarlari,
            "gelistirici_iletisim": state.gelistirici_iletisim,
            "masasiz_sepet": state.masasiz_sepet,
            "masasiz_indirim": state.masasiz_indirim,
            "tarife_profilleri": state.tarife_profilleri,
            "konsol_varsayilan_profil": state.konsol_varsayilan_profil,
            "konsol_tipleri": state.konsol_tipleri,
            "gruplar": state.gruplar,
            "masalar": [_masa_yaz(m) for m in state.masalar],
            "masa_sirasi": state.masa_sirasi,
            "borclar": [_borc_yaz(b) for b in state.borclar],
            "kasa_islemleri": [_kasa_islemi_yaz(k) for k in state.kasa_islemleri],
            "giderler": [_gider_yaz(g) for g in state.giderler],
            "avanslar": [_avans_yaz(a) for a in state.avanslar],
            "notlar": [_not_yaz(n) for n in state.notlar],
            "urun_katalogu": state.urun_katalogu,
        }
        yol = veri_dosyasi_yolu()
        gecici_yol = yol.with_suffix(".tmp")
        with open(gecici_yol, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        gecici_yol.replace(yol)  # ATOMİK - ya tam yazılır ya asıl dosya hiç değişmez
        _gunluk_yedek_al(veri)
        return True
    except Exception:
        return False


def yukle() -> AppState | None:
    """Kayıtlı veri dosyası varsa ondan bir AppState oluşturup döner. Dosya
    yoksa ya da BOZUKSA (örn. yazma sırasında elektrik kesintisi -tmp
    dosyasında kalmış olabilir ama asıl dosya atomik olduğu için bozuk
    OLMAMALI, yine de savunma amaçlı try/except var) None döner - bu durumda
    çağıran taraf sıfırdan boş bir AppState() oluşturur."""
    yol = veri_dosyasi_yolu()
    if not yol.exists():
        return None
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)

        state = AppState()
        state.salon_adi = veri.get("salon_adi", "Salonum")
        state.bildirim_ayarlari = veri.get("bildirim_ayarlari", {})
        state.gelistirici_iletisim = veri.get("gelistirici_iletisim", "")
        state.masasiz_sepet = veri.get("masasiz_sepet", {})
        state.masasiz_indirim = veri.get("masasiz_indirim", 0.0)
        state.tarife_profilleri = veri.get("tarife_profilleri", {})
        state.konsol_varsayilan_profil = veri.get("konsol_varsayilan_profil", {})
        state.konsol_tipleri = veri.get("konsol_tipleri", [])
        state.gruplar = veri.get("gruplar", [])
        state.masalar = [_masa_oku(d) for d in veri.get("masalar", [])]
        state.masa_sirasi = veri.get("masa_sirasi", [])
        state.borclar = [_borc_oku(d) for d in veri.get("borclar", [])]
        state.kasa_islemleri = [_kasa_islemi_oku(d) for d in veri.get("kasa_islemleri", [])]
        state.giderler = [_gider_oku(d) for d in veri.get("giderler", [])]
        state.avanslar = [_avans_oku(d) for d in veri.get("avanslar", [])]
        state.notlar = [_not_oku(d) for d in veri.get("notlar", [])]
        state.urun_katalogu = veri.get("urun_katalogu", {})
        _gorselleri_kalici_yap(state.urun_katalogu)

        # ID ÇAKIŞMASINI ÖNLEME: yeni oluşturulacak ID'ler dosyadaki en büyük
        # ID'nin bir fazlasından devam etsin, yoksa program yeniden açıldığında
        # sayaç sıfırdan başlar ve mevcut kayıtlarla çakışabilir.
        tum_idler = (
            [m.id for m in state.masalar] + [b.id for b in state.borclar] +
            [k.id for k in state.kasa_islemleri] + [g.id for g in state.giderler] +
            [a.id for a in state.avanslar] + [n.id for n in state.notlar]
        )
        if tum_idler:
            id_sayacini_ayarla(max(tum_idler) + 1)

        return state
    except Exception:
        return None


def yukle_veya_yeni() -> AppState:
    """Ana giriş noktası: kayıtlı veri varsa yükler, yoksa/bozuksa BOŞ
    (demo verisiz) bir AppState döner."""
    return yukle() or AppState()
