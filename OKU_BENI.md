# GameHub PS Salon Otomasyonu

## 🚀 KURULUM PROGRAMI (SETUP) ÜRETME — BİR KEZ / HER YENİ SÜRÜMDE

Amaç: müşteriye **tek bir `GameHub_Kurulum_x.y.z.exe`** vermek. Çalıştırınca normal bir
Windows programı gibi kurulur: kurulum klasörü (`C:\Users\..\AppData\Local\Programs\GameHub PS Salon`
veya yönetici olarak `Program Files`), Başlat menüsü, masaüstü kısayolu, "Program Ekle/Kaldır" girişi.

**Seçenek A – Kendi bilgisayarınızda (Windows):**
1. Python 3.11+ kurun ("Add python.exe to PATH" işaretli) ve [Inno Setup 6](https://jrsoftware.org/isdl.php) kurun (ücretsiz).
2. `build.bat` dosyasına çift tıklayın. Bitince **`Output\GameHub_Kurulum_1.0.0.exe`** oluşur.

**Seçenek B – Hiçbir şey kurmadan (GitHub):** bu klasörü GitHub'a yükleyin → *Actions* → *Kurulum Derle* → *Run workflow*. Setup dosyası indirilebilir olarak çıkar.

> İlk açılışta Windows SmartScreen "tanınmayan uygulama" uyarısı verebilir (imzasız olduğu için normal): *Ek Bilgi → Yine de Çalıştır*.

## 📦 Veriler ve görseller
- Program dosyaları ile **veriler ayrıdır**. Veriler: `%APPDATA%\GameHub` (Ayarlar › Veri ve Güncelleme sayfasından *Klasörü Aç*).
- Ürün görselleri seçildiği anda bu klasördeki `gorseller` içine **kopyalanır**; masaüstündeki orijinal silinse de ürün görseli kalır.
- Güncelleme ve kaldırma verileri **silmez**. *Yedek Al / Yedekten Geri Yükle* aynı sayfadadır.

## 🔄 Uzaktan güncelleme (tek tıkla yayın)
1. Değişen dosyaları GitHub'a yükleyin. `core/surum.py` içindeki `SURUM`'u artırın (örn. `1.0.3`).
2. GitHub › **Actions › Surum Yayinla › Run workflow** → yenilik notunu yazın → **Run workflow**.
3. ~3 dakika sonra GitHub otomatik olarak Setup'ı derler, imzalı `surum.json`'u üretir ve **Release** olarak yayınlar.
4. Müşterilerin programı bir sonraki açılışta "Yeni sürüm var" penceresini gösterir; imza ve parmak izi doğrulanınca kurar, program yeniden açılır. Veriler korunur.

Tek seferlik ayar: depoda **Settings › Secrets and variables › Actions › New repository secret** → adı `GUNCELLEME_ANAHTARI`,
değeri satıcı paketindeki `guncelleme_anahtari.txt` içeriği. Bu anahtar yalnızca güncelleme imzalar (lisans üretemez).
Aynı sürüm numarası ikinci kez yayınlanamaz (workflow durur): önce `SURUM`'u artırın.

## 🔑 Lisans ve Giriş

İlk açılışta program **Cihaz Kodu** gösterir ve **lisans anahtarı** ister. Anahtarı
girmeyen programa erişemez. Anahtarlar satıcıya ait *Lisans Üretici* aracıyla üretilir
(ayrı pakettir, müşteriye verilmez); cihaz koduna bağlı anahtar yalnızca o bilgisayarda
çalışır. Lisanstan sonra kullanıcı adı + şifre belirlenir; *Beni hatırla* işaretliyse
sonraki açılışlarda otomatik giriş yapılır (sol alttaki *Oturumu Kapat* ile sıfırlanır).
Şifre unutulursa giriş ekranındaki *Şifremi unuttum* ile lisans anahtarıyla yenilenir.

## 💾 Verileriniz Nerede Duruyor?

Tüm salon verileriniz (masalar, kasa, ürünler, notlar vb.) programın
kendisinden **tamamen bağımsız** olarak şu klasörde tutulur:

```
%APPDATA%\GameHub\salon_verileri.json
```

Bu sayede:
- Programı güncellediğinizde (yeni `.exe` ile değiştirdiğinizde) **veriniz
  asla kaybolmaz** - çünkü program dosyalarıyla aynı yerde durmuyor.
- Her kayıtta otomatik olarak **son 7 günün** ayrı yedeği de aynı klasörün
  altındaki `yedekler` alt klasörüne alınır - ana dosya bir şekilde bozulursa
  buradan geri dönülebilir.

## 🖥️ Kurulum (Python kaynak kodundan çalıştırma - geliştirme/test için)
1. Python 3.11+ → "Add python.exe to PATH" işaretle
2. `pip install PyQt6`
3. Bu klasöre gir → `python main.py`

## 📋 Sonraki Adımlar
- [ ] 1 günlük gerçek kullanım testi (şu an buradasınız)
- [ ] Lisans/aktivasyon katmanı
- [ ] İlk müşterilere dağıtım
