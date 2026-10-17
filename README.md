# @veteriner otomatik paylaşım

Her gün Türkiye saatiyle 20:03'ten başlayarak GitHub Actions bir özgün görsel ve metin hazırlar, görseli bu depoda `posts/` altına koyar, sonra Instagram API ile @veteriner hesabında yayımlar. GitHub zamanlanmış işleri geciktirebildiğinden 20:13, 20:23 ve 20:33'te yedek tetikler vardır; aynı günün sonraki çalışmaları ikinci post atmaz. Güncel olay yalnızca iki bağımsız kaynakla doğrulanabildiğinde kullanılır; aksi halde genel hayvan sağlığı bilgisi seçilir. Görsel temsili illüstrasyondur.

## Bir defalık kurulum

GitHub'da bu deponun **Settings → Secrets and variables → Actions → New repository secret** bölümüne iki gizli değer ekleyin:

- `OPENAI_API_KEY`: OpenAI API anahtarı; ChatGPT aboneliğinden ayrı API kullanımı ücretlendirilir.
- `IG_ACCESS_TOKEN`: @veteriner Instagram Login için uzun ömürlü erişim tokenı ve yayın izni. Tokenı koda, issue'ya veya sohbete yapıştırmayın.

İki gizli değer eklenene kadar zamanlanmış iş hata verip durur; paylaşım yapılmaz. İlk kurulumdan sonra **Actions → Daily Instagram post → Run workflow** ile bir deneme yapıp gerçek Instagram bağlantısını doğrulayın. Bunu yalnızca ilk kurulumda yapmanız gerekir. Günlük işlem ayrıca onay sormaz.

Instagram uzun ömürlü tokenı yaklaşık 60 günde sona erer; yenileme henüz otomatik değildir. Süresi dolmadan yeni tokenı aynı `IG_ACCESS_TOKEN` secret'ına girmeniz gerekir. Bu sınır giderilene kadar sürekli, süresiz çalıştığını varsaymayın. GitHub'ın planlanan işleri birkaç dakika geciktirebilmesi de mümkündür.

Başarısız işlemlerde gönderi yayımlanmaz ve Actions kayıtlarında hata görünür. Yayın çağrısından sonra ağ yanıtı kaybolursa gönderi yapılmış olabilir; betik otomatik tekrar denemez. Zamanlanmış yayınlar günlük dosyayı, elle başlatılan denemeler ise GitHub çalışma kimliğini taşıyan ayrı dosyaları kullanır. Böylece sabah yapılan bir deneme akşamın günlük paylaşımını engellemez; günlük yedek tetikler aynı gün ikinci kez paylaşmaz.

Story etiketlerinin onaylı yeniden paylaşımı bu günlük post iş akışında yoktur; o ayrı bir onay sürecidir.

## Ücretsiz Story erişim pilotu

`Story discovery pilot` ayrı, yalnızca elle başlatılan bir erişim denemesidir. Düzenli tarama ve Instagram'da Story yayını henüz açık değildir. Günlük özgün post işini değiştirmez.

1. https://console.apify.com/ adresinde ücretsiz hesap açın. Ücretli plan veya ödeme yöntemi gerekmez.
2. Apify **Settings → Integrations** bölümündeki API tokenını GitHub'da **Settings → Secrets and variables → Actions** altında `APIFY_TOKEN` isimli **repository secret** olarak kaydedin. Tokenı sohbete, dosyaya veya issue'ya yapıştırmayın. Mevcut `OPENAI_API_KEY` kullanılır; Instagram anahtarı bu iş akışına verilmez.
3. **Actions → Story discovery pilot → Run workflow → check_setup** ücretsiz hesap erişimini kontrol eder; tarama başlatmaz. Ardından `collect` ile deneme yapılır.
4. Sonuçlar Apify **Storage → Key-value stores → veteriner-story-pilot** içinde `LATEST` (JSON) ve `LATEST.html` (mobil uyumlu inceleme raporu) olarak bulunur. Rapor yayın/onay göndermez. Gerçek veri erişimi doğrulandıktan sonra onay ve yayın adımı ayrıca tamamlanacaktır.

İlk kaynaklar HAYTAP ve HAYTAP Sahiplendirme'dir; resmi kaynak bağlantıları `automation/story_sources.json` içindedir. Bunlar erişim testi kaynaklarıdır, yeniden paylaşım izni veya sürekli editoryal öneri değildir. Sağlayıcı yalnızca açık profesyonel/marka/içerik üretici hesaplarını kapsar; özel hesaplar kapsam dışıdır.

Pilot sınırları: her çalışmada en çok 10 Story, günde en çok 2 ve ayda en çok 60 tarama; her Actor çalışması için `maxTotalChargeUsd=0.06`. Ücretli veya durumu belirsiz Apify hesabında çalışmaz. Ücretli plana geçmez, ödeme yöntemi eklemez ve hesap harcama sınırlarını değiştirmez. Sağlayıcının ücretsiz havuzu doluysa açık hata verir; bunu 'Story yok' diye yorumlamaz. İlk canlı denemede sağlayıcının güncel şeması ve ücretsiz erişimi doğrulanmalıdır.

Tarama başlatma çağrısı başarısız/yanıtsız kalırsa otomatik tekrar yapılmaz ve o deneme kotadan düşer. Süresi geçmiş Story'ler, kaynak dışı hesaplar, özel hesaplar ve beklenmeyen medya adresleri elenir. Aynı Story sonraki çalışmada yeniden değerlendirilmez. En çok 3 yeni görsel OpenAI ile değerlendirilir; video ve diğer içerikler manuel inceleme bekler. OpenAI tüketimi Apify kredisinden ayrıdır.

Ham Story'ler, medya bağlantıları, yapay zekâ notları ve tarama geçmişi GitHub'a, Actions çıktısına veya public artifact'a yazılmaz. İnceleme deposu ve taramanın çıktıları Apify'de `RESTRICTED` erişime alınır; paylaşıma açık/imzalı URL üretilmez. Model çıktısı doğruluk teyidi, içerik sahibinin izni veya kullanıcının yayın onayı sayılmaz.
