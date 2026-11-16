# ADR-0001: Konfigürasyon stratejisi

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-12

## Bağlam

Servis `local`, `test`, `staging` ve `production` ortamlarında çalışacak. Ortama göre değişen ayarlar var (şimdilik ortam adı ve API dokümantasyonunun açık olup olmadığı), sayıları artacak. Ayar okuma hataları sessizdir: yanlış prefix, yanlış tip ya da unutulmuş bir değişken çoğu zaman ancak production'da fark edilir. Testlerin de geliştiricinin kendi `.env` dosyasından ve shell'inden bağımsız çalışması gerekiyor; aksi hâlde "bende geçiyor, CI'da kırılıyor" durumu oluşur.

## Karar

1. **Ayarlar tek bir tipli sınıfta.** `app/core/config.py` içindeki `Settings(BaseSettings)` (pydantic-settings) ortam değişkenlerinden ve `.env` dosyasından okur. Ortam değişkeni `.env`'i ezer. Tüm değişkenler `FUELPAY_` prefix'i alır. `ENVIRONMENT` bir `Literal`, yani dört değerden biri olmak zorunda.
2. **Ayarlara tek giriş noktası `get_settings()`.** `@lru_cache` ile bir kez okunur. Endpoint'ler ayarları `Depends(get_settings)` ile alır. Testler `get_settings.cache_clear()` ile yeniden okutur.
3. **Uygulama `create_app()` fabrikasıyla kurulur.** Modül düzeyinde `app` nesnesi yoktur. Server `uvicorn app.main:create_app --factory` ile başlar. `app.main`'i import etmek ayar okumaz.
4. **`DOCS_ENABLED`'ın varsayılanı yok, zorunlu.** `ENVIRONMENT` için de aynısı geçerli. Eksik ya da geçersiz değer, uygulamayı açılışta `ValidationError` ile durdurur.

## Alternatifler

- **Kod içinde dağınık `os.getenv(...)`:** Reddedildi. Tip dönüşümü yok (`"false"` truthy bir string), doğrulama yok, eksik değer `None` olarak sessizce akar ve ayarların tam listesi tek yerde görünmez.
- **YAML/TOML ayar dosyaları ya da Dynaconf:** Reddedildi. İki ayar için ek bağımlılık ve ikinci bir format getirir. Ortam değişkenleri zaten her deploy hedefinde (container, CI) birinci sınıf destekleniyor.
- **Prefix'siz değişken adları (`ENVIRONMENT`):** Reddedildi. Aynı host ya da container'daki başka araçların değişkenleriyle çakışır ve hangi değişkenin bu servise ait olduğu anlaşılmaz.
- **Modül düzeyinde global `settings = Settings()` / `app = FastAPI(...)`:** Reddedildi. Ayarlar import anında, test fixture'ları çalışmadan önce okunur. Testler geliştiricinin `.env`'ini görür ve farklı ayarla app kurmak için `importlib.reload` gerekir.
- **`create_app(settings)` ile ayarı parametre olarak geçirip testte `app.dependency_overrides` kullanmak:** Şimdilik reddedildi. Ayarı hem fabrikaya hem dependency'ye ayrı ayrı vermeyi gerektirir. İkisi ayrışabilir: docs biri ile, `/health` diğeri ile kurulur. Tek kaynak (`get_settings`) ve `cache_clear` bu boyutta yeterli.
- **`DOCS_ENABLED=True` varsayılanı:** Reddedildi. Production'da değişkeni unutmak, API şemasını herkese açar. Hata sessiz ve güvenlik açısından yanlış yönde.
- **`DOCS_ENABLED=False` varsayılanı:** Reddedildi. Güvenli ama sessiz: local'de `/docs` 404 verir ve neden kapalı olduğu anlaşılmaz. Zorunlu alan aynı güvenliği açık bir hata mesajıyla sağlar.

## Sonuçlar

- **Olumlu:** Yanlış ya da eksik ayar deploy anında ve açık bir mesajla patlar, production'da sessizce yanlış davranmaz. Ayarların tam listesi ve tipleri `Settings` sınıfında, örnek değerler `.env.example`'da.
- **Olumlu:** Testler ortamdan bağımsız. `tests/conftest.py` `.env` okumayı kapatır, `FUELPAY_*` değişkenlerini temizler ve cache'i sıfırlar.
- **Olumsuz:** Server komutu `--factory` gerektirir. `app.main:app` bekleyen araçlar ya da dokümanlar güncellenmeli.
- **Olumsuz:** Ayar değişikliği yeniden başlatma ister (cache). Her yeni zorunlu alan `.env.example`'a ve `conftest.py`'deki test varsayılanlarına da eklenmeli; yeni bir kişinin local'de ilk açılışta iki değişkeni set etmesi gerekir.
