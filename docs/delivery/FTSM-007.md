# FTSM-007 — Teslimat notu

- **Tarih:** 2026-11-19
- **Durum:** Dört komut yeşil (292 test, mypy strict temiz).

> **Not:** Kod ve testler geliştirici tarafından yazıldı. Bu not, `StationRepositoryPort`'un daraltılması ve B3 deneyi geliştiricinin isteği üzerine Engineering Lead tarafından yapıldı/yazıldı.

## Yapılanlar

- mypy (`strict = true`, `pydantic.mypy` eklentisi) eklendi; `uv run mypy app` temiz, `type: ignore` yok.
- `app/services/ports.py`: `TerminalRepositoryPort` (beş method) ve `StationRepositoryPort` (yalnızca `get_by_id`). `TerminalService` artık somut repository'leri değil bu protokolleri bekliyor; `app/services` `app/repositories`'i import etmiyor.
- `tests/test_terminal_router.py`: `dependency_overrides` ile sahte servis; router'ın `action` ve kırpılmış `reason`'ı doğru geçirdiği ve `TerminalNotFoundError`'ın 404'e çevrildiği gerçek repository olmadan test ediliyor.

## mypy'nin bulduğu ve düzeltilenler

- `TerminalService.change_status`'ta `action: str` → `Action`.
- Repository kayıt sözlükleri `dict[uuid.UUID, dict[str, Any]]`.
- `app.state`'ten okunan repository'ler tipli bir değişkene atanıp döndürülüyor (`no-any-return`).
- Exception handler'ların parametresi `exc: Exception` (Starlette her `Exception`'ı kabul edebilen bir handler bekliyor; parametre tipleri contravariant'tır).

## Sapmalar

Yok. `StationRepositoryPort` ilk halinde istasyon repository'sinin dört method'unu içeriyordu; servis yalnızca `get_by_id` kullandığı için ticket'taki (B2) gibi tek method'a indirildi.

## B3 deneyi: protokol gerçekten çalışıyor mu?

`TerminalRepository.count_by_station` geçici olarak `count_for_station` diye yeniden adlandırıldı ve `uv run mypy app` çalıştırıldı:

```
app\api\deps.py:28: error: Argument "terminals" to "TerminalService" has incompatible type "TerminalRepository"; expected "TerminalRepositoryPort"  [arg-type]
app\api\deps.py:28: note: "TerminalRepository" is missing following "TerminalRepositoryPort" protocol member:
app\api\deps.py:28: note:     count_by_station
```

Hata, method'u kullanan servis satırında değil, somut repository'nin servise verildiği yerde (`deps.py`) çıkıyor ve eksik method'u adıyla söylüyor. Ad geri alındı; mypy tekrar temiz.

## Komut çıktıları

```
$ uv run pytest
============================= 292 passed =============================
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
46 files already formatted
$ uv run mypy app
Success: no issues found in 25 source files
```

## Cevap

**Router testinde gerçek servis yerine sahte servis kullanmak neyi test eder, neyi etmez?**

Router'ın kendi işini test eder: URL ve gövdeden doğru işlem adını ve kırpılmış nedeni servise geçirdiğini, servisin sonucunu olduğu gibi döndürdüğünü ve servisin exception'ını doğru status code'a çevirdiğini. Servisin ve repository'nin gerçekten doğru çalıştığını, ya da gerçek servisin sahtenin taklit ettiği exception'ları fırlattığını test etmez; o yüzden `tests/test_terminals.py`'deki uçtan uca testler yerinde kalıyor.
