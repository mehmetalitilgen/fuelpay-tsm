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
| POST  | `/api/v1/stations/{station_id}/terminals` | 201 terminal + `Location: /api/v1/terminals/{id}` header'ı                        | 404 istasyon yok · 409 seri no ya da pompa dolu · 422 geçersiz gövde |
| GET   | `/api/v1/stations/{station_id}/terminals` | 200 `{"items": [...], "total": n, "limit": 50, "offset": 0}` (yalnızca o istasyon) | 404 istasyon yok · 422 `offset < 0` ya da `limit` 1–100 dışında |
| GET   | `/api/v1/terminals/{id}`     | 200 terminal                                                                                   | 404 bulunamadı · 422 `id` geçerli UUID değil   |
| POST  | `/api/v1/terminals/{id}/activate`     | 200 terminal (`active`)                                                     | 404 terminal yok · 409 geçersiz geçiş · 422 `id` geçerli UUID değil |
| POST  | `/api/v1/terminals/{id}/suspend`      | 200 terminal (`suspended`); gövde `{"reason": "..."}`                       | 404 · 409 · 422 geçersiz UUID ya da gövde |
| POST  | `/api/v1/terminals/{id}/decommission` | 200 terminal (`decommissioned`)                                             | 404 · 409 · 422 |

**İstasyon:** `{"id": "<uuid>", "code": "34-001", "name": "...", "city": "...", "created_at": "<ISO 8601, timezone'lu>"}`

**Terminal:** `{"id": "<uuid>", "station_id": "<uuid>", "serial_number": "TRM00001", "pump_number": 1, "status": "registered", "created_at": "<ISO 8601, timezone'lu>", "status_changed_at": null, "suspension_reason": null}`

- **Terminal POST gövdesi:** `serial_number` ve `pump_number`, ikisi de zorunlu. `id`, `station_id`, `status` gibi başka alanlar 422 döner; istasyon URL'den gelir.
  - `serial_number`: 8–16 karakter, yalnızca `A–Z` ve `0–9`. Baştaki ve sondaki boşluk kırpılır, büyük harfe çevrilir (`trm00001` → `TRM00001`). ASCII dışı harfler (`İ`, `ı`, `ß`…) dönüştürülmez, 422 döner.
  - `pump_number`: 1–32 arası JSON tam sayısı (strict). `"3"`, `3.0` ve `true` 422 döner.
- **Terminal listesi:** İstasyon bazlıdır; tüm istasyonları dönen bir `GET /api/v1/terminals` yoktur. `pump_number`'a göre artan sırada döner; sayfalama bu sıraya göre yapılır.
- **Tekillik:** `serial_number` tüm sistemde tekildir; aynı seri numarası başka bir istasyonda da 409 döner, harf büyüklüğü fark etmez. `pump_number` istasyon başına tekildir; aynı pompa numarası başka bir istasyonda kullanılabilir. Hizmetten çıkarılan (`decommissioned`) terminal pompasını serbest bırakır, seri numarasını bırakmaz.
- **Terminal durumları** ([ADR-0004](docs/adr/0004-terminal-status-machine.md)):

  | İşlem | İzin verilen durumlar | Sonuç |
  |---|---|---|
  | `activate` | `registered`, `suspended` | `active` |
  | `suspend` (gövde: `reason`, 1–200 karakter, kırpılır) | `active` | `suspended` |
  | `decommission` | `registered`, `active`, `suspended` | `decommissioned` (son durum) |

  Tabloda olmayan her geçiş, aynı duruma geçiş dahil, 409 döner. `suspension_reason` yalnızca `suspended` iken doludur; `status_changed_at` son geçişin zamanıdır. Kurallar `app/domain/terminal_status.py` içinde tek yerde durur.

- **POST gövdesi:** `code`, `name`, `city`, üçü de zorunlu. `code` biçimi `NN-NNN` (ör. `34-001`). `name` 1–100, `city` 1–50 karakter olmalı. Baştaki ve sondaki boşluklar kırpılır.
- **Hata gövdesi:** 404 ve 409 yanıtları `{"detail": "..."}` biçimindedir ve OpenAPI'de `ErrorResponse` şemasıyla belgelenmiştir (`/docs`).
- **İstasyon listesi:** Ekleme sırasıyla döner. `offset` ve `limit` query parametreleri opsiyoneldir (varsayılan `0` / `50`, `limit` en fazla `100`).
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
