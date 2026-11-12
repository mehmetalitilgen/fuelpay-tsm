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

- Sağlık kontrolü: http://127.0.0.1:8000/health → `{"status": "ok"}`
- API dokümantasyonu: http://127.0.0.1:8000/docs

## Testleri çalıştırma

```bash
uv run pytest
```

Ayarlar `pyproject.toml` içindeki `[tool.pytest.ini_options]` bölümünde.

## Notlar

- `uv.lock` commit'lenir; herkes aynı sürümleri kursun diye. Bağımlılık eklerken `uv add <paket>` (dev için `uv add --dev <paket>`) kullan, lock dosyası otomatik güncellenir.
- `.venv/` commit'lenmez (`.gitignore`'da).
