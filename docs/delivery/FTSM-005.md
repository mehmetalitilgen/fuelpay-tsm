# FTSM-005 — Teslimat notu

- **Tarih:** 2026-11-18
- **Durum:** Üç komut yeşil (271 test).

> **Not:** Parça A, B ve C'nin büyük kısmı ile endpoint'lerin ilk hali geliştirici tarafından yazıldı. Geliştiricinin isteği üzerine Engineering Lead şunları tamamladı: `change_status`'taki `suspension_reason` hatası ve pompa kuralı (C4, C6), endpoint'lerde `response_model` ve ortak 404 yardımcısı (D2–D4), yeni repository ve integration testleri (C5, C6, D5, D6), ADR-0004, README ve bu notun "Elle denenenler", "Komut çıktıları" ve "Cevaplar" bölümleri. Cevapları kendi cümlelerinle tekrar edebilmelisin.

## Kararlar

1. **(a) Aynı duruma geçiş idempotent değil, 409 döner.** `next_status`, `active` iken `activate` ya da `suspended` iken `suspend` için `InvalidStatusTransitionError` fırlatır ve API bunu 200 yerine 409 olarak döndürür. Kural tek tiptir: tabloda olmayan her şey hata. Gerekçe ve bedeli ADR-0004'te.
2. **Strict `pump_number`:** `Field(strict=True)`. Strict modda `"3"`, `" 4 "`, `3.0` ve `true` 422 döner (`int_type`); boolean'ı reddeden ayrı validator gereksiz kaldığı için silindi.
3. **Sayfalama sabitleri** `app/schemas/pagination.py` içinde tek yerde; istasyon ve terminal router'ları ile repository'leri oradan import ediyor.

## Ticket'tan sapmalar

1. **`InvalidStatusTransitionError` `ConflictError`'dan türüyor.** B5 domain'in repository paketini import etmemesini istiyordu. Bu türetme sayesinde mevcut 409 handler'ı yeni exception'ı da yakalıyor ve D1 (ayrı handler) gereksiz kaldı. Bedeli: `app/domain/terminal_status.py` → `app/repositories/errors.py` bağımlılığı. Lead kabul etti (ADR-0004, Sonuçlar).
2. **Endpoint'ler ortak bir `_change_status_or_404` yardımcısı kullanıyor;** üç handler'daki aynı 404 bloğu tek yerde.
3. **`activate` ve `decommission` gövde almıyor; gönderilen gövde yok sayılıyor** (bkz. Elle denenenler #11). FastAPI, gövde parametresi olmayan endpoint'te gövdeyi okumaz. Ticket bunu açıkça belirtmiyordu; 422 istenirse ileride ele alınabilir.

## Elle denenenler

`TestClient` ile, tek bir uygulama üzerinde sırayla çalıştırıldı.

| # | Durum | İşlem / girdi | Beklenen | Alınan |
|---|---|---|---|---|
| 1 | registered | activate | 200 | 200, `active` |
| 2 | registered | suspend | 409 | 409 |
| 3 | active | activate | 409 (Karar a) | 409 |
| 4 | active | suspend, neden `"  Arıza  "` | 200, neden kırpılmış | 200, `"Arıza"` |
| 5 | suspended | suspend, farklı neden | 409 (Karar a) | 409 |
| 6 | suspended | activate | 200, neden `null` | 200, `null` |
| 7 | decommissioned | activate / suspend / decommission | 409 | 409 / 409 / 409 |
| 8 | active | suspend, gövdesiz | 422 | 422 (`missing`) |
| 9 | active | suspend, `{"reason": ""}` | 422 | 422 (`string_too_short`) |
| 10 | active | suspend, `{"reason": "x", "foo": 1}` | 422 | 422 (`extra_forbidden`) |
| 11 | registered | activate, gövde `{"foo": 1}` | ? | **200** ⚠ |
| 12 | — | olmayan UUID ile activate | 404 | 404 |
| 13 | — | `abc` ile activate | 422 | 422 |
| 14 | pompa 1 decommissioned | aynı istasyona pompa 1, yeni seri | 201 | 201 |
| 15 | seri `TERMA0001` decommissioned | `terma0001` ile yeni kayıt | 409 | 409 |
| 16 | — | `pump_number: "3"` / `3.0` / `true` | 422 | 422 / 422 / 422 |

**Şaşırtıcı sonuç:** #11. Gövde almayan endpoint'e gönderilen gövde sessizce yok sayılıyor. Zararsız (işlem gövdeye bakmıyor), ama `extra="forbid"` ile kurduğumuz "beklenmeyen girdi 422" ilkesinden farklı. Sapma 3'e yazıldı.

## Komut çıktıları

```
$ uv run pytest
======================= 271 passed =======================
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
39 files already formatted
```

Testler iki kez üst üste, shell'e farklı `FUELPAY_*` değerleri verilerek ve `tests/test_terminals.py` `-p no:cacheprovider` ile tek başına çalıştırıldı; sonuç aynı.

## Cevaplar

**1. İki operasyon kullanıcısı aynı anda aynı terminale biri `suspend`, diğeri `decommission` gönderirse bugün ne olur? Epic 4'te ne olabilir?**

Bugün tek process ve tek event loop var, `change_status` içinde de gerçekten bekleyen bir `await` yok. İstekler sırayla işlenir: önce gelen uygulanır, ikincisi yeni duruma göre değerlendirilir. `suspend` önce gelirse `suspended → decommission` geçerlidir; `decommission` önce gelirse `decommissioned → suspend` 409 alır. Tablo dışı bir yol oluşmaz.

Epic 4'te ikisi de veritabanından aynı eski durumu (`active`) okuyabilir, ikisi de geçişi geçerli bulur ve sonra yazan kazanır (lost update). Sonuç, tablonun izin vermediği bir sıra olabilir (örnek: `decommissioned` bir terminalin üzerine `suspended` yazılması). Çözüm kontrolü yazmayla birleştirmek: `UPDATE ... SET status = 'suspended' WHERE id = :id AND status = 'active'` ve etkilenen satır 0 ise 409; ya da `SELECT ... FOR UPDATE` ile kilitlemek; ya da `version` sütunuyla optimistic locking.

**2. `status` alanını neden `PATCH` ile doğrudan yazdırmadık?**

Durum serbestçe yazılan bir alan değil, kuralları olan bir süreç. İşlemi adlandırmak (`suspend`) niyeti açık eder, işleme özgü girdiyi (askıya alma nedeni) doğal kılar ve ileride işlem bazlı yetkiyi (kim askıya alabilir) ve işlem adlı event'leri (`terminal.suspended`) mümkün kılar. `PATCH` ile bunların hepsi alan doğrulamasına sıkışır ve aynı istekte başka alanlar gelirse anlamı belirsizleşir.

## Açık işler

- #11: gövde almayan endpoint'lerde gövdeyi reddetmek (isteğe bağlı).
- `ConflictError`'ı domain katmanına taşımak (isteğe bağlı; ADR-0004).
- Durum geçmişi (olay tablosu) ve eşzamanlı geçişler: Epic 4 / Epic 10.
