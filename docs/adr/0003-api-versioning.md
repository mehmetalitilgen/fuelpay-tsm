# ADR-0003: API versiyonlama

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-16

## Bağlam

İlk iş endpoint'leri (`/stations`) yayınlanıyor. Bu API'yi sahadaki terminaller kullanacak. Bir terminal bir adrese bağlandıktan sonra onu güncellemek yavaş ve koordinasyon isteyen bir iş, tüm terminaller aynı anda güncellenemez. Dolayısıyla API sözleşmesi kırıldığında eski ve yeni client'ların bir süre birlikte çalışabilmesi gerekiyor. Versiyonlama yöntemi de yayınlandıktan sonra değiştirilemez, çünkü terminaller o yönteme göre yapılandırılmış olur.

## Karar

1. **Versiyon URL ön ekinde, yalnızca major olarak tutulur:** `/api/v1/...`. Tüm iş endpoint'leri `app/api/v1/router.py` üzerinden bu ön ekin altına bağlanır.
2. **Breaking change yeni major demektir.** Yeni sürüm `/api/v2` altında ayrı bir router olarak `v1`'in yanında yayınlanır. `v1`, terminaller geçene kadar kapatılmaz. Breaking olmayan değişiklikler `v1`'e versiyon değişmeden girer.
3. **`/health` versiyonsuzdur.** Tüketicisi terminaller değil; load balancer, orkestratör ve izleme sistemleri. Sorduğu soru "bu process ayakta mı?" ve cevabı API sürümünden bağımsız. Aynı process hem `v1` hem `v2`'yi sunacağı için tek bir health adresi olmalı. `/api/v1/health` olsaydı `v1` kaldırıldığında altyapı ayarlarının da değişmesi gerekirdi.
4. **Breaking change sayılanlar:**
   - yanıttan alan silmek ya da yeniden adlandırmak
   - bir alanın tipini ya da biçimini değiştirmek (ör. `id` UUID → integer, `created_at` biçimi)
   - isteğe zorunlu alan eklemek
   - doğrulamayı sıkılaştırmak, yani önceden geçerli olan bir girdiyi reddetmek
   - status code'u ya da hata anlamını değiştirmek
   - endpoint'i ya da path'i kaldırmak

   **Breaking sayılmayanlar:**
   - isteğe opsiyonel alan eklemek
   - yanıta yeni alan eklemek (client'lar tanımadıkları alanları yok saymalı; bu, terminal tarafındaki sözleşmenin parçasıdır)
   - yeni endpoint eklemek
   - doğrulamayı gevşetmek

## Alternatifler

- **Header ile versiyon (`Accept: application/vnd.fuelpay.v1+json` ya da `X-API-Version: 1`):** Reddedildi. Terminal yazılımlarının her birinde özel header set edilebileceği garanti değil. Header log'larda ve URL'de görünmediği için sahadaki bir hatada hangi sürümün çağrıldığını anlamak zorlaşır. Header gelmezse hangi sürümün döneceği ayrıca karar ister. Proxy ve cache katmanları da sürüme göre yönlendirme için ek ayar (`Vary`) gerektirir.
- **Query parametresi (`?version=1`):** Reddedildi. Doğası gereği opsiyoneldir, eksik bırakıldığında hangi sürümün döneceği belirsizdir. İş parametreleriyle (`offset`, `limit`) aynı yerde karışır. Ara katmanlar ya da client kütüphaneleri query'yi kolayca düşürür.
- **Hiç versiyonlamamak:** Reddedildi. İlk breaking change'te tüm terminallerin aynı anda güncellenmesi gerekir; sahada bu mümkün değil. Alternatif olarak, kırılmamak için yanlış tasarımı sonsuza kadar taşımak gerekir.

## Sonuçlar

- **Olumlu:** Sürüm her istekte, log'larda ve proxy kurallarında açıkça görünür. curl ya da tarayıcıyla test etmek kolay. `v1` ve `v2` ayrı router modülleri olarak yan yana yaşayabilir.
- **Olumlu:** Neyin breaking olduğu yazılı olduğu için review'da her sözleşme değişikliği bu listeye göre değerlendirilir.
- **Olumsuz:** Major sürüm değişince terminallerin yapılandırmasındaki adres de değişmeli. Bir süre iki sürümün kodunu ve testlerini birlikte bakımda tutmak gerekecek.
- **Olumsuz:** "Yeni yanıt alanı breaking değildir" kuralı, terminallerin tanımadıkları alanları yok saymasına dayanıyor. Terminal entegrasyon dokümanına yazılmalı.
- Ön ekin dışına sızan bir iş endpoint'i olmadığını `tests/test_stations.py::test_stations_are_only_served_under_v1_prefix` doğrular.
