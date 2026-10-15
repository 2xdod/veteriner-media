# @veteriner otomatik paylaşım

Her gün Türkiye saatiyle 20:00'de GitHub Actions bir özgün görsel ve metin hazırlar, görseli bu depoda `posts/` altına koyar, sonra Instagram API ile @veteriner hesabında yayımlar. Güncel olay yalnızca iki bağımsız kaynakla doğrulanabildiğinde kullanılır; aksi halde genel hayvan sağlığı bilgisi seçilir. Görsel temsili illüstrasyondur.

## Bir defalık kurulum

GitHub'da bu deponun **Settings → Secrets and variables → Actions → New repository secret** bölümüne iki gizli değer ekleyin:

- `OPENAI_API_KEY`: OpenAI API anahtarı; ChatGPT aboneliğinden ayrı API kullanımı ücretlendirilir.
- `IG_ACCESS_TOKEN`: @veteriner Instagram Login için uzun ömürlü erişim tokenı ve yayın izni. Tokenı koda, issue'ya veya sohbete yapıştırmayın.

İki gizli değer eklenene kadar zamanlanmış iş hata verip durur; paylaşım yapılmaz. İlk kurulumdan sonra **Actions → Daily Instagram post → Run workflow** ile bir deneme yapıp gerçek Instagram bağlantısını doğrulayın. Bunu yalnızca ilk kurulumda yapmanız gerekir. Günlük 20:00 işlemi ayrıca onay sormaz.

Instagram uzun ömürlü tokenı yaklaşık 60 günde sona erer; yenileme henüz otomatik değildir. Süresi dolmadan yeni tokenı aynı `IG_ACCESS_TOKEN` secret'ına girmeniz gerekir. Bu sınır giderilene kadar sürekli, süresiz çalıştığını varsaymayın. GitHub'ın planlanan işleri birkaç dakika geciktirebilmesi de mümkündür.

Başarısız işlemlerde gönderi yayımlanmaz ve Actions kayıtlarında hata görünür. Yayın çağrısından sonra ağ yanıtı kaybolursa gönderi yapılmış olabilir; betik otomatik tekrar denemez. Günlük dosya varlığı mükerrer denemeleri önler.

Story etiketlerinin onaylı yeniden paylaşımı bu iş akışında yoktur; o ayrı bir onay sürecidir.
