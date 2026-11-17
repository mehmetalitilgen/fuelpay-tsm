# FTSM-004 — Teslimat notu

- **Tarih:** 2026-11-17
- **Durum:** Üç komut yeşil (192 test). Bir açık iş var: `pump_number` hâlâ lax (bkz. Kararlar, a).

> **Not:** "Kararlar" ve "Cevaplar" bölümleri ile bu turdaki güncellemeler, geliştiricinin isteği üzerine Engineering Lead tarafından yazıldı. Kararlar koddaki mevcut duruma bakılarak kaydedildi; gerekçeleri kendi cümlelerinle tekrar edebilmelisin.

## Özet

- **Yeni endpoint'ler:**
  - `POST /api/v1/stations/{station_id}/terminals`
  - `GET /api/v1/stations/{station_id}/terminals`: istasyon bazlı liste, `pump_number` artan sırada
  - `GET /api/v1/terminals/{id}`
- **Testler:**
  - `tests/test_terminal_repository.py`: HTTP'siz repository sözleşmesi. Epic 4'teki PostgreSQL implementasyonu da bu testlerden geçmeli.
  - `tests/test_terminals.py`: endpoint'ler, integration.
  - Senaryoların yarısından fazlası iki istasyon kuruyor: başka istasyonun pompası, başka istasyonun seri numarası (harf büyüklüğü farklı da olsa), olmayan istasyon, bir istasyonun listesine başka istasyonun terminalinin karışmaması, araya başka istasyonun kayıtları girdiğinde sayfalama.
- **Ortak yardımcılar:** `create_station` yardımcısı `tests/test_stations.py`'den `tests/helpers.py`'ye taşındı. `create_terminal` ve `terminal_payload` aynı dosyaya eklendi. `openapi` fixture'ı `tests/conftest.py`'ye taşındı.
- **OpenAPI:** 404 ve 409 yanıtları altı endpoint'te `responses=` ile belgelendi; gövde şeması `app/schemas/errors.py` içindeki `ErrorResponse`.
- **README:** Endpoint tablosuna üç terminal satırı, terminal gövdesi, doğrulama ve tekillik kuralları eklendi.

## Kararlar

### (a) `pump_number` için string (`"3"`) kabul edilsin mi?

- **Koddaki durum:** Lax. `Field(..., strict=False)` ve yalnızca boolean'ı reddeden bir `before` validator var.
- **Sonuç (2026-11-17'de elle denendi):** `"3"` → 201, `" 4 "` → 201, `3.0` ve `"3.0"` → pompa 3 olarak kabul ediliyor, `true` → 422.
- **Değerlendirme:** Geliştiricinin elle denemedeki beklentisi 422'ydi ve gerekçesi doğruydu: string'in sayı gibi kabul edilmesi client'taki tip hatasını gizler. Lead bu yönü (strict) onayladı, ama bu turda uygulanmadı ve `"3"` için bir test (T13) yazılmadı.
- **Açık iş:** `strict=True` uygulanacak, boolean validator'ı gereksiz kalacağı için kaldırılacak, T13 (`"3"` → 422) ve `3.0` testi yazılacak. FTSM-005'in ilk adımına taşındı.

### (b) Sayfalama ve zarf tekrarı

- **Koddaki durum:** "Tekrarla" seçeneği. `TerminalList` ayrı bir model; `limit`/`offset` query parametreleri iki router'da ayrı tanımlı.
- **Gerekçe:** İki kullanımda generic bir `Page[T]` OpenAPI'deki şema adlarını değiştirir; ortak dependency bir kat dolaylılık ekler. İki kopya için soyutlama erken.
- **Eksik:** `DEFAULT_PAGE_LIMIT` / `MAX_PAGE_LIMIT` sabitleri hem `app/schemas/stations.py` hem `app/schemas/terminals.py` içinde tanımlı; terminal router'ı istasyon şemasındakini, terminal repository'si kendi dosyasındakini kullanıyor. Değerler bugün aynı, ama biri değişirse sessizce ayrışır. Sabitler tek bir yere indirilecek (açık iş).

## Ticket'tan sapmalar ve ticket'ta olmayan kararlar

1. **Liste istasyon bazlı:** `GET /api/v1/stations/{station_id}/terminals`. Tüm istasyonları dönen bir `GET /api/v1/terminals` yok (404). Olmayan istasyonun listesi 404, boş istasyonun listesi 200 ve boş döner. (Ticket'la aynı.)
2. **`serial_number` tüm sistemde tekil, harf büyüklüğünden bağımsız:** Gelen değer büyük harfe çevrilip saklanıyor. (Ticket'la aynı.)
3. **`pump_number` istasyon başına tekil:** Aynı numara başka istasyonda serbest. (Ticket'la aynı.)
4. **`serial_number` içinde ASCII dışı karakter 422 döner.** `upper()` bu harfleri ASCII'ye çeviriyordu (`ı` → `I`, `ß` → `SS`), bu yüzden `TRMı0001` ile `TRMI0001` aynı seri numarasına düşüyordu. Artık dönüştürmeden önce reddediliyor. **Lead bu sapmayı kabul etti ve ticket'ı düzeltti.**
5. **`pump_number: true/false` 422 döner.** Ayrı bir validator reddediyor. `strict=True`'ya geçilince gereksiz kalacak.
6. **409 çevirisi merkezi:** Ticket router'da `try/except` öngörüyordu. Bunun yerine `app/main.py` içinde `ConflictError` için tek bir exception handler kayıtlı; repository'nin fırlattığı her teklik hatası tek yerde 409'a çevriliyor. Yeni bir `ConflictError` alt sınıfı eklendiğinde router'a dokunmak gerekmiyor. Bedeli: 409 mesajı artık exception'ın kendi mesajı (`Duplicate serial number: 'FP2A7K91X3'.`); istasyon kod tekrarı ise hâlâ router'da ve farklı bir mesaj biçimiyle dönüyor.
7. **Repository sözleşmesi:**
   - Teklik kontrolleri kayıt yazılmadan önce yapılıyor; çakışma ya da doğrulama hatasında depoya hiçbir şey girmiyor.
   - Kayıt saklanmadan önce `TerminalRead` olarak doğrulanıyor.
   - Liste `pump_number` artan sırada; sıralama sayfalamadan **önce** uygulanıyor.

## Elle denemeler

Server `uvicorn app.main:create_app --factory` ile açıldı, istekler curl ile gönderildi. İki istasyon kuruldu: A (`34-001`) ve B (`06-001`). Satırlar sırayla, aynı server üzerinde çalıştırıldı. 15. satır ve altındaki ek satırlar 2026-11-17'de son kodla yeniden denendi.

| # | Girdi | Beklenen | Alınan |
|---|-------|---------:|-------:|
| 1 | A'ya geçerli: `TRM00001`, pompa 1 | 201 | 201 |
| 2 | gövdede `id` | 422 | 422 |
| 3 | gövdede `station_id` (B'nin id'si) | 422 | 422 |
| 4 | gövdede `status: "active"` | 422 | 422 |
| 5 | küçük harf `trm00002` | 201 | 201 |
| 6 | baş/son boşluk `"  TRM00003  "`, pompa 3 | 201 | 201 |
| 7 | iç boşluk `"TRM 0004"` | 422 | 422 |
| 8 | tire `TRM-0004` | 422 | 422 |
| 9 | Türkçe `İSTANBUL1` | 422 | 422 |
| 10 | Türkçe `TRMı0004` | 422 | 422 |
| 11 | Türkçe küçük `trmi0005` (→ `TRMI0005`, ASCII) | 201 | 201 |
| 12 | `pump_number: 0` | 422 | 422 |
| 13 | `pump_number: 33` | 422 | 422 |
| 14 | `pump_number: 3.5` | 422 | 422 |
| 15 | `pump_number: "3"` (boş pompa) | 422 | **201** ⚠ |
| 15a | `pump_number: " 4 "` | 422 | **201** ⚠ |
| 15b | `pump_number: 3.0` / `"3.0"` | 422 | pompa 3 kabul ⚠ |
| 16 | `pump_number: true` | 422 | 422 |
| 17 | `pump_number: null` | 422 | 422 |
| 18 | B'ye `trm00001` (1'deki seri, farklı harf, başka istasyon) | 409 | 409 |
| 19 | A'ya `TRM00008`, pompa 1 (A'da dolu) | 409 | 409 |
| 20 | B'ye `TRM00009`, pompa 1 (B'de boş) | 201 | 201 |
| 21 | olmayan istasyona POST | 404 | 404 |
| 22 | `GET` A'nın listesi (pompalar 5, 1, 3 eklendi) | 200, sıra 1-3-5 | 200, 1-3-5 |
| 23 | `GET` B'nin listesi | 200 | 200 |
| 24 | `GET` olmayan istasyonun listesi | 404 | 404 |
| 25 | `GET /api/v1/terminals` | 404 | 404 |
| 26 | `GET /api/v1/` | 404 | 404 |

**Şaşırtıcı sonuçlar:**

- **#15, 15a, 15b:** Pydantic'in lax modu string'i, boşluklu string'i ve tam sayı değerli float'ı tam sayıya çeviriyor. Bkz. Kararlar (a).
- **İlk tur (kod düzeltilmeden önce):** #10 (`ı`) ve #16 (`true`) doğrulamadan geçip repository'ye ulaşıyordu; başarısız POST'lar repository'de yarım kayıt bırakıyordu ve liste 500 dönüyordu. Sapmalar 4, 5 ve 7 bunları kapattı.

## Cevaplar

**1. FTSM-003'te kod tekrarını router'da "önce bak, sonra ekle" ile kontrol ettin. İki istek aynı anda aynı kodu gönderirse bugünkü in-memory repository ile ikisi de 201 alabilir mi? Epic 4'te sorgu gerçek bir veritabanına gidince cevap değişir mi?**

Bugün, tek process'te: hayır. `get_by_code` ve `add` `async def` ama içlerinde gerçekten bekleyen (suspend eden) bir `await` yok; askıya alınmayan bir coroutine'i `await` etmek kontrolü event loop'a geri vermez. Kontrol ile ekleme arasında başka bir isteğe geçilemediği için ikisi fiilen atomik. (Birden fazla worker'da ise her process'in ayrı belleği olduğu için teklik kuralı zaten yoktur.)

Epic 4'te: evet, değişir. `get_by_code` ağ üzerinden veritabanına gidince gerçek bir bekleme noktası olur; iki istek de `SELECT`'te "yok" görüp ikisi de `INSERT` yapabilir. Çözüm kontrolü uygulamadan veriye taşımaktır: `code` üzerinde unique constraint, uygulama `INSERT` yapıp ihlali yakalayıp 409'a çevirir. Bu ticket'ta terminal teklik kurallarını repository'ye taşımamızın nedeni bu.

**2. Bu ticket'ta teklik kontrolünü repository'ye taşıdık. İstasyonun varlık kontrolü hâlâ router'da ve "önce bak, sonra ekle" biçiminde. İstasyon silme özelliği gelirse burada ne ters gidebilir? Veritabanı bunu neyle engeller?**

İstasyon var mı diye bakıldıktan sonra, terminal eklenmeden önce istasyon silinirse sahipsiz (orphan) bir terminal oluşur: hiçbir istasyonun listesinde görünmez, ama seri numarası teklik kuralında yer kaplar.

Veritabanında `terminals.station_id` üzerindeki foreign key bunu engeller: var olmayan istasyona `INSERT` hata verir. Silme sırasında ne olacağını `ON DELETE` belirler (`RESTRICT`: terminali olan istasyon silinemez). PostgreSQL child satır eklerken parent satırı paylaşımlı kilitler (`FOR KEY SHARE`), bu yüzden eşzamanlı silme bekler ya da hata alır. Router'daki kontrol yine kalabilir; kullanıcıya anlamlı bir 404 vermek için, ama doğruluğun garantisi değildir.

**3. `def` olarak yazılmış bir dependency'yi (FTSM-002'deki `get_settings`) FastAPI nerede çalıştırır? `async def` olanı nerede?**

`async def` dependency doğrudan event loop'ta `await` edilir. `def` dependency `starlette.concurrency.run_in_threadpool` ile threadpool'da çalıştırılır (kurulu FastAPI'de `fastapi/dependencies/utils.py` içinde doğrulandı). Yani `get_settings` her istekte bir thread geçişi maliyeti taşır; `lru_cache` sayesinde iş kendisi ucuz olsa da. Repository dependency'leri (`get_station_repo`, `get_terminal_repo`) `async def` olduğu için event loop'ta kalıyor; içlerinde bloklayan çağrı olmadığı için bu doğru seçim. Kural endpoint'lerle aynı: bloklayan iş yapan dependency `def` olur, yapmayan `async def`.

## Bilinen sorunlar ve açık işler

- `pump_number` strict değil; T13 yok (Kararlar a). → FTSM-005
- Sayfalama sabitleri iki dosyada (Kararlar b). → FTSM-005
- `app/repositories/terminals.py`: global `get_sum` kullanılmıyor.
- `app/api/v1/terminals.py`: `add_terminal`'ın `request` parametresi kullanılmıyor; terminal `Location`'ı elle string ile, istasyonunki `url_for` ile üretiliyor.
- Eksik testler: `GET /api/v1/health` → 404, `limit=1` → 200.

Testler iki kez üst üste aynı sonucu verdi; `test_terminals.py` `-p no:cacheprovider` ile tek başına da geçiyor.

## Komut çıktıları

```
$ uv run pytest
============================= 192 passed =============================
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
34 files already formatted
```
