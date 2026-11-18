# ADR-0004: Terminal durum makinesi

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-18

## Bağlam

POS terminalleri kurulumdan sökülmeye kadar bir yaşam döngüsünden geçiyor: kaydedilir, aktive edilir, arıza ya da şüpheli işlem nedeniyle askıya alınabilir, sonunda hizmetten çıkarılır. Epic 6'da ödeme başlatma yalnızca `active` terminallere izin verecek. Bu yüzden durumun hangi işlemle, hangi durumdan hangisine değişebileceği açık ve tek bir yerde tanımlı olmalı.

Kurallar dağılırsa (router'larda `if` zincirleri, ileride Celery task'larında kopyaları) biri mutlaka eksik kalır. En tehlikeli sonuç, hizmetten çıkarılmış (sökülmüş, kaybolmuş ya da çalınmış) bir cihazın yeniden aktive edilip ödeme alabilmesidir.

## Karar

1. **Dört durum:** `registered`, `active`, `suspended`, `decommissioned`. Yeni terminal `registered` doğar.
2. **Geçiş tablosu (izin listesi):**

   | İşlem | İzin verilen kaynak durumlar | Hedef |
   |---|---|---|
   | `activate` | `registered`, `suspended` | `active` |
   | `suspend` | `active` | `suspended` |
   | `decommission` | `registered`, `active`, `suspended` | `decommissioned` |

   Tabloda olmayan her geçiş geçersizdir ve 409 döner. Tablo yasaklananları değil izin verilenleri listeler; yeni bir durum eklendiğinde unutulan geçişler varsayılan olarak kapalı kalır.
3. **`decommissioned` son durumdur.** Hizmetten çıkarılan cihaz geri getirilmez; yeniden kullanılacaksa yeni bir kayıt gerekir, ama seri numarası tekliği bunu engeller. Bir cihazın sahaya dönmesi bilinçli bir operasyon kararıdır ve bu ticket'ın kapsamında değildir.
4. **Aynı duruma geçiş 409 döner, idempotent değildir** (`active` iken `activate`, `suspended` iken `suspend`). Kural tek tiptir: tabloda olmayan her şey hata. Client tekrar denemesi sonrası 409 görürse terminali `GET` ile okuyup durumunu kontrol eder. Gerçek idempotency, Epic 6'daki Idempotency Key ile ele alınacak.
5. **Kurallar domain katmanında.** `app/domain/terminal_status.py` içinde `TRANSITIONS` tablosu ve `next_status(current, action)` fonksiyonu var; ikisi de HTTP'yi ve depolamayı bilmez. Repository geçiş kararını bu fonksiyona sorar; router yalnızca repository'yi çağırır.
6. **İşlem endpoint'leri:** `POST /api/v1/terminals/{id}/activate`, `/suspend`, `/decommission`. Yalnızca `suspend` gövde alır (`reason`, 1–200 karakter, zorunlu).
7. **Yan alanlar:** `status_changed_at` son gerçek geçişin zamanı; `suspension_reason` yalnızca `suspended` iken dolu, diğer geçişlerde temizlenir.
8. **Pompa ve seri numarası:** Hizmetten çıkarılan terminal pompasını serbest bırakır (aynı pompaya yeni cihaz takılabilir), seri numarasını bırakmaz (cihaz başka bir yerde yeniden kaydedilemez).

## Alternatifler

- **`PATCH /terminals/{id}` ile `{"status": "active"}` yazmak:** Reddedildi. Durum bir alan değil, kurallı bir süreç. `PATCH` ile askıya alma nedeni gibi işleme özgü girdiler ve kurallar alan doğrulamasına sıkışır; aynı istekte başka alanlar da gelirse anlamı belirsizleşir. İleride işlem bazlı yetki (Epic 5) ve işlem adlı event'ler (Epic 10) gerekecek.
- **Tek bir `POST /terminals/{id}/transitions` endpoint'i, gövdede işlem adı:** Reddedildi. Tek endpoint ve tek doğrulama noktası sağlar, ama gövde şeması işleme göre değişir (`suspend` için `reason` zorunlu, diğerlerinde yok). Bu ya ayrık bir union şema ya da gevşek doğrulama demek; OpenAPI ve client kodu karmaşıklaşır.
- **Aynı duruma geçişi no-op (200) yapmak:** Reddedildi. Tekrar denemelere toleranslı olurdu, ama "aynı istek" tanımı belirsiz: farklı nedenle gelen ikinci `suspend` yeni neden mi yazmalı? Bu soru Epic 6'daki Idempotency Key ile genel olarak çözülecek.
- **Kuralları repository içinde `if` zincirleriyle yazmak:** Reddedildi. Epic 4'te PostgreSQL repository'si ve Epic 9'da Celery task'ları aynı kuralları tekrar yazmak zorunda kalırdı.
- **`decommissioned` durumundan `activate`'e izin vermek:** Reddedildi. Ödeme sisteminde sökülmüş cihazın sessizce geri dönmesi kabul edilemez bir risk.

## Sonuçlar

- **Olumlu:** Bütün kural tek bir tablo. `tests/test_terminal_status.py` her durum–işlem çiftinin kararını elle yazılı bir beklentiyle doğruluyor; `Status` ya da `Action`'a yeni bir değer eklenirse, o kombinasyonların kararı yazılana kadar test kırmızı kalır.
- **Olumlu:** 409 mesajı mevcut durumu ve işlemi içeriyor (`Cannot 'activate' a terminal in status 'decommissioned'.`); destek ekibi nedeni yanıttan okuyabilir.
- **Olumsuz:** `status` enum'una üç yeni değer eklendi. ADR-0003'e göre yanıta alan eklemek breaking değildir, ama mevcut bir enum'a değer eklemek, kapalı enum ile kod üreten katı client'ları kırabilir. Terminal yazılımları bilinmeyen durum değerlerini tolere etmeli; bu entegrasyon dokümanına yazılmalı.
- **Olumsuz:** Aynı duruma geçiş 409 verdiği için, timeout sonrası tekrar deneyen client başarılı bir işlemi başarısız sanabilir. Client'lar 409'dan sonra kaynağı okumalı.
- **Olumsuz:** Durum geçmişi tutulmuyor; yalnızca son geçişin zamanı var. Denetim için olay tablosu Epic 4/10'da eklenecek.
- **Olumsuz:** Eşzamanlı iki geçiş bugün tek process'te sırayla işlenir; veritabanı geldiğinde (Epic 4) koşullu `UPDATE ... WHERE status = ...` ya da kilitleme gerekecek.
- **Not:** `InvalidStatusTransitionError`, `app.repositories.errors.ConflictError`'dan türüyor; böylece mevcut 409 handler'ı onu da yakalıyor. Bedeli: domain modülü repository paketine bağımlı. `ConflictError` ileride domain katmanına taşınabilir.
