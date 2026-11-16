# ADR-0002: Uygulama sürümünün kaynağı

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-12

## Bağlam

Sürüm iki yerde görünür: FastAPI'nin OpenAPI şemasında (`app.version`) ve `/health` yanıtının `version` alanında. Paket sürümü ise `pyproject.toml` içindeki `[project].version` değeridir. Bu üç değer elle senkron tutulursa ayrışır: biri `pyproject.toml`'u bump'lar, koddaki sabiti unutur ve `/health` yanlış sürümü raporlar. Sürüm bir ortam ayarı değildir, kodla birlikte değişir. Bu yüzden ADR-0001'deki `Settings`'e değil, ayrı bir karara aittir.

## Karar

1. **Tek kaynak `pyproject.toml` → `[project].version`.**
2. **Çalışma anında `importlib.metadata` ile okunur.** `app/__init__.py` içinde `__version__ = version("fuelpay-tsm")` var. `create_app()` ve `/health` yalnızca `app.__version__` kullanır.
3. **Proje kurulabilir bir paket olarak tanımlanır.** `importlib.metadata`, sadece kurulu bir paketin metadata'sını okuyabilir. Bu nedenle `pyproject.toml`'a `[build-system]` (hatchling) ve `[tool.hatch.build.targets.wheel] packages = ["app"]` eklendi. Bu bölümler olmadan uv projeyi "virtual" sayar ve kurmaz. O durumda `version("fuelpay-tsm")` çağrısı `PackageNotFoundError` fırlatır ve uygulama import aşamasında açılmaz.

## Alternatifler

- **Kodda sabit (`VERSION = "0.1.0"`):** Reddedildi. `pyproject.toml` ile ikinci bir doğruluk kaynağı oluşur ve ayrışma ancak biri `/health`'e bakınca fark edilir. `uv version --bump` gibi araçlar yalnızca `pyproject.toml`'u günceller.
- **`pyproject.toml`'u çalışma anında `tomllib` ile okumak:** Reddedildi. Dosyanın uygulamaya göre konumuna bağımlıdır ve kurulmuş wheel'de ya da yalnızca `app/` kopyalanmış bir imajda bulunmaz.
- **Hatch dinamik sürüm (`[tool.hatch.version] path = "app/__init__.py"`):** Reddedildi. Kaynağı koda taşır ama `[build-system]` yine gerekir. Ayrıca `uv version` ile sürüm yönetimini kırar. Bedeli aynı, kazancı yok.
- **Git tag'inden sürüm (hatch-vcs / setuptools-scm):** Şimdilik reddedildi. Sürüm git durumuna bağlı olur, `.git`'in olmadığı Docker build'lerinde ek ayar ister. Release süreci tag tabanlı olduğunda yeniden değerlendirilir.
- **CI'ın verdiği ortam değişkeni (`FUELPAY_VERSION`):** Reddedildi. Sürüm kodun bir özelliğidir, deploy ayarı değildir. Yanlış ya da eksik değişken, yanlış sürüm raporlatır.

## Sonuçlar

- **Olumlu:** Sürüm tek yerde değişir. OpenAPI ve `/health` otomatik olarak aynı değeri gösterir. Bunu `tests/test_health.py` doğrular.
- **Olumsuz:** `[build-system]` ve `[tool.hatch...]` bölümleri gereksiz görünse de **silinmemeli**. Silinirse uygulama `PackageNotFoundError` ile açılmaz.
- **Olumsuz:** Proje editable kurulur. Kod değişiklikleri anında yansır ama sürüm, kurulum anındaki `fuelpay_tsm-<sürüm>.dist-info` içinde donar. Sürüm değişince proje yeniden kurulmalıdır: `uv sync` ya da çalıştırmadan önce senkronlayan `uv run`. `.venv` içindeki python doğrudan ya da `--no-sync` ile çalıştırılırsa eski sürüm görünür.
- **Olumsuz:** Deploy imajı projeyi paket olarak kurmalıdır (`uv sync`, `--no-install-project` olmadan). Yalnızca `app/` klasörünü kopyalamak yetmez.
