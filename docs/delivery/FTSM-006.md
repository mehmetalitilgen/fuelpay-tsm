# FTSM-006 — Teslimat notu

- **Tarih:** 2026-11-18
- **Durum:** Üç komut yeşil (288 test; 17'si yeni servis testi).

## Kararlar

1. **Terminal iş kuralları `TerminalService`'te (`app/services/terminals.py`).** Router artık repository'leri doğrudan çağırmıyor; `TerminalServiceDep` (`app/api/deps.py`) servisi istek başına iki repository'yle kuruyor. Servis HTTP bilmez: "istasyon var mı", "terminal var mı" ve sayfa + toplam gibi birden fazla repository çağrısı gerektiren akışları yönetir.
2. **Servisin sözleşmesi exception'larla ifade ediliyor.** Bulunamadı → `StationNotFoundError` / `TerminalNotFoundError` (`NotFoundError` alt sınıfları); çakışma ve geçersiz geçiş → `ConflictError` alt sınıfları. `main.py`'deki iki handler bunları 404 ve 409'a çeviriyor. Router'daki `HTTPException(404)` blokları ve `None` kontrolleri kalktı.
3. **Hata sınıfları domain katmanında (`app/domain/errors.py`).** `app/repositories/errors.py` silindi. Böylece `app/domain/terminal_status.py` artık repository paketini import etmiyor; FTSM-005'te kabul edilen `domain → repositories` bağımlılığı (ADR-0004, Sonuçlar) kapandı.
4. **`list_for_station` `(items, total)` döner;** `TerminalList` zarfını router kurar. Zarf bir HTTP biçimi, servis yalnızca veriyi verir.

## Ticket'tan sapmalar

1. **İstasyon endpoint'leri servise taşınmadı.** `app/api/v1/stations.py` hâlâ repository'yi doğrudan kullanıyor ve 404/409'u `HTTPException` ile üretiyor. Gövde biçimi aynı (`{"detail": "..."}`), davranış değişmedi; ama iki router iki farklı yolla hata üretiyor (bkz. Açık işler).
2. **Servis testleri gerçek in-memory repository'lerle yazıldı, mock'la değil** (`tests/test_terminal_service.py`). Repository'ler hızlı ve deterministik; mock, servisin repository'yi gerçekten doğru çağırıp çağırmadığını (ör. sayfa + toplam) gizlerdi.

## Elle denenenler

`TestClient` ile, tek bir uygulama üzerinde sırayla. A (`34-001`) ve B (`06-001`) iki istasyon; A'da pompa 7 ve 2, B'de pompa 1.

| # | İşlem / girdi | Beklenen | Alınan |
|---|---|---|---|
| 1 | olmayan istasyona terminal kaydı | 404 | 404, `Station … not found` |
| 2 | olmayan istasyonun terminal listesi | 404 | 404, `Station … not found` |
| 3 | olmayan terminal `GET` | 404 | 404, `Terminal … not found` |
| 4 | olmayan terminale `activate` | 404 | 404, `Terminal … not found` |
| 5 | A listesi, `limit=1` | 200, pompa 2, toplam 2 | 200, `items=[2]`, `total=2` |
| 6 | A'daki seri (`trm00007`) B'ye | 409 | 409, `Duplicate serial number: 'TRM00007'.` |
| 7 | `registered` terminale `suspend` | 409 | 409, `Cannot 'suspend' a terminal in status 'registered'.` |
| 8 | 404 gövdesinin anahtarları | `{"detail"}` | `["detail"]` |

Şaşırtıcı sonuç yok. #5 bu ticket sırasında 500 dönüyordu (servis toplamı döndürmüyordu); düzeltildi ve `test_list_for_station_returns_page_and_total` ile kilitlendi.

**Servis testlerinin gerçekten yakaladığı doğrulandı:** bellekte, dosyalara dokunmadan üç eski hata geri getirildi (istasyon kontrolsüz `register`, toplamsız `list_for_station`, `None` dönen `change_status`). 17 servis testinden tam olarak ilgili 5'i kırmızıya döndü.

## Komut çıktıları

```
$ uv run pytest
============================= 288 passed in 6.09s =============================
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
44 files already formatted
```

Testler iki kez üst üste çalıştırıldı, ikincisinde shell'e `FUELPAY_ENVIRONMENT=production FUELPAY_DOCS_ENABLED=false` verildi; iki seferde de 288/288. `tests/test_terminal_service.py` `-p no:cacheprovider` ile tek başına da geçiyor (17/17).

## Cevaplar

> Bu bölüm geliştiricinin isteği üzerine Engineering Lead tarafından yazıldı.

**Servis katmanı olmasaydı Epic 9'daki otomatik askıya alma task'ı terminali nasıl askıya alırdı, ne ters gidebilirdi?**

Task router'ı çağıramayacağı için repository'yi doğrudan kullanır ve router'daki kontrolleri ("terminal var mı", sonucu 404'e çevirme) kendi içinde tekrar yazardı. Kopyalar zamanla ayrışır: router'a eklenen yeni bir kural (örnek: yetki ya da audit kaydı) task'a eklenmeyi unutulur ve aynı işlem HTTP'den yapıldığında başka, task'tan yapıldığında başka davranır. Ayrıca task, repository'nin `None` dönüşünü kontrol etmeyi unutursa sessizce hiçbir şey yapmaz. Servisle iki giriş noktası da aynı `TerminalService.change_status`'ı çağırır ve aynı exception'ları alır; task bunları 404/409'a değil kendi davranışına (log, atla, tekrar dene) çevirir.

## Açık işler

- **İstasyon router'ı da servise / domain exception'larına geçirilmeli** (Sapma 1); iki router aynı yolla hata üretsin.
