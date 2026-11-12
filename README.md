# fuelpay-tsm

FastAPI servisi.

## Gereksinimler

- Python 3.12 (`.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Kurulum

```bash
uv sync
```

`.venv/` oluşturur, bağımlılıkları (dev grubu dahil) `uv.lock`'taki sürümlerle kurar.

## Server'ı başlatma

```bash
uv run uvicorn app.main:app --reload
```

- API dokümantasyonu: http://127.0.0.1:8000/docs

## Endpoint'ler

| Metod | Path      | Yanıt (200)                                                      |
|-------|-----------|------------------------------------------------------------------|
| GET   | `/health` | `{"status": "ok", "service": "fuelpay-tsm", "version": "0.1.0"}` |

`version` alanı `app.main` içindeki FastAPI uygulama sürümüyle aynı olmalı; testler bunu kontrol eder.

## Testleri çalıştırma

```bash
uv run pytest
```

Ayarlar `pyproject.toml` içindeki `[tool.pytest.ini_options]` bölümünde. Testler `fastapi.testclient.TestClient` ile uygulamayı ağ açmadan, process içinde çağırır; server'ın çalışıyor olması gerekmez.

## Lint ve format

```bash
uv run ruff check .
uv run ruff format .
```

Kural seti `pyproject.toml` içindeki `[tool.ruff.lint]` bölümünde (`E`, `W`, `F`, `I`, `UP`, `B`). Commit öncesi ikisinin de temiz olması beklenir; CI'da kontrol için `uv run ruff format --check .` kullanılabilir.

## Notlar

- `uv.lock` commit'lenir; herkes aynı sürümleri kursun diye. Bağımlılık eklerken `uv add <paket>` (dev için `uv add --dev <paket>`) kullan, lock dosyası otomatik güncellenir.
- `.venv/` commit'lenmez (`.gitignore`'da).
