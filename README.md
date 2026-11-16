# fuelpay-tsm

FastAPI servisi.

## Gereksinimler

- Python 3.12 (`.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Kurulum

```bash
uv sync
cp .env.example .env
```

`uv sync`, `.venv/` oluşturur, bağımlılıkları (dev grubu dahil) `uv.lock`'taki sürümlerle ve projenin kendisini kurar. `.env` dosyasını kendi ortamına göre düzenle (bkz. [Konfigürasyon](#konfigürasyon)).

## Server'ı başlatma

```bash
uv run uvicorn app.main:create_app --factory --reload
```

Uygulama `create_app()` fabrikasıyla kurulur; modül düzeyinde `app` nesnesi yoktur (neden: [ADR-0001](docs/adr/0001-configuration.md)).

- Sağlık kontrolü: http://127.0.0.1:8000/health
- API dokümantasyonu: http://127.0.0.1:8000/docs (yalnızca `FUELPAY_DOCS_ENABLED=true` iken)

## Konfigürasyon

Ayarlar `app/core/config.py` içindeki `Settings` sınıfında tanımlı ve `pydantic-settings` ile okunur. Tüm değişkenler `FUELPAY_` prefix'i alır.

| Değişken               | Değerler                                     | Açıklama                                                      |
|------------------------|----------------------------------------------|---------------------------------------------------------------|
| `FUELPAY_ENVIRONMENT`  | `local` \| `test` \| `staging` \| `production` | Servisin çalıştığı ortam                                      |
| `FUELPAY_DOCS_ENABLED` | `true` \| `false`                            | `false` iken `/docs`, `/redoc` ve `/openapi.json` kapalı (404) |

- **Okuma sırası:** ortam değişkeni > `.env` dosyası. Aynı ayar ikisinde de varsa ortam değişkeni kazanır.
- **İki değişken de zorunlu.** Biri eksikse ya da geçersizse uygulama açılışta `ValidationError` ile durur; yanlış ayarla sessizce çalışmaz.
- `.env` commit'lenmez (`.gitignore`'da). Yeni bir ayar eklendiğinde `.env.example` da güncellenir; ekip için referans odur.
- Ayarlar `get_settings()` ile bir kez okunup cache'lenir; `.env` değişikliği için server'ı yeniden başlat.

## Endpoint'ler

| Metod | Path                         | Başarılı yanıt                                                                                 | Hatalar                                        |
|-------|------------------------------|------------------------------------------------------------------------------------------------|------------------------------------------------|
| GET   | `/health`                    | 200 `{"status": "ok", "service": "fuelpay-tsm", "version": "0.1.0", "environment": "local"}`   | —                                              |
| POST  | `/api/v1/stations`           | 201 istasyon + `Location: /api/v1/stations/{id}` header'ı                                      | 409 kod zaten var · 422 geçersiz gövde          |
| GET   | `/api/v1/stations`           | 200 `{"items": [...], "total": n, "limit": 50, "offset": 0}`                                   | 422 `offset < 0` ya da `limit` 1–100 dışında   |
| GET   | `/api/v1/stations/{id}`      | 200 istasyon                                                                                   | 404 bulunamadı · 422 `id` geçerli UUID değil   |

**İstasyon:** `{"id": "<uuid>", "code": "34-001", "name": "...", "city": "...", "created_at": "<ISO 8601, timezone'lu>"}`

- **POST gövdesi:** `code`, `name`, `city`, üçü de zorunlu. `code` biçimi `NN-NNN` (ör. `34-001`). `name` 1–100, `city` 1–50 karakter olmalı. Baştaki ve sondaki boşluklar kırpılır.
- **Liste:** Ekleme sırasıyla döner. `offset` ve `limit` query parametreleri opsiyoneldir (varsayılan `0` / `50`, `limit` en fazla `100`).
- **Versiyonlama:** İş endpoint'leri `/api/v1` altında; `/health` versiyonsuz. Neyin breaking change sayıldığı ve nedenleri [ADR-0003](docs/adr/0003-api-versioning.md)'te.

- `version`, `pyproject.toml` içindeki `[project].version` değerinden okunur (`app/__init__.py` → `__version__`). Sürüm değiştirince `uv sync` çalıştır, yoksa eski sürüm görünür. `pyproject.toml`'daki `[build-system]` bu yüzden gerekli, silme (neden: [ADR-0002](docs/adr/0002-version-source.md)).
- `environment`, `FUELPAY_ENVIRONMENT` ayarından gelir.

## Testleri çalıştırma

```bash
uv run pytest
```

Ayarlar `pyproject.toml` içindeki `[tool.pytest.ini_options]` bölümünde. Testler `fastapi.testclient.TestClient` ile uygulamayı ağ açmadan, process içinde çağırır; server'ın çalışıyor olması gerekmez.

Testler senin `.env` dosyanı ve shell'deki `FUELPAY_*` değişkenlerini **okumaz**: `tests/conftest.py` her test için `.env` okumayı kapatır, `FUELPAY_*` değişkenlerini silip sabit değerler (`FUELPAY_ENVIRONMENT=test`, `FUELPAY_DOCS_ENABLED=true`) yazar ve `get_settings` cache'ini temizler. Farklı ayarla app gerekiyorsa `make_client(ENVIRONMENT="staging")` fixture'ını kullan. `Settings`'e yeni zorunlu alan eklersen `conftest.py`'deki varsayılanlara da ekle.

## Lint ve format

```bash
uv run ruff check .
uv run ruff format .
```

Kural seti `pyproject.toml` içindeki `[tool.ruff.lint]` bölümünde (`E`, `W`, `F`, `I`, `UP`, `B`). Commit öncesi ikisinin de temiz olması beklenir; CI'da kontrol için `uv run ruff format --check .` kullanılabilir.

## Notlar

- `uv.lock` commit'lenir; herkes aynı sürümleri kursun diye. Bağımlılık eklerken `uv add <paket>` (dev için `uv add --dev <paket>`) kullan, lock dosyası otomatik güncellenir.
- `.venv/` ve `.env` commit'lenmez (`.gitignore`'da).
