# Gündem & Teknoloji

Teknoloji ve gündem haberlerini her 30 dakikada bir kendisi çeken, ücretsiz barındırılan haber sitesi.
Kendi haberini de telefondan bile resim ve linkle ekleyebilirsin.

## Nasıl çalışır?

| Parça | Görevi |
|---|---|
| `index.html` | Sitenin kendisi (kategoriler, arama, manşet, karanlık mod) |
| `data/feeds.json` | Haberlerin çekildiği RSS kaynakları — istediğin kadar ekle/çıkar |
| `scripts/fetch_news.py` | Kaynaklardan haberleri çekip `data/news.json`'a yazar |
| `.github/workflows/haberleri-cek.yml` | Bu betiği her 30 dakikada bir GitHub'da otomatik çalıştırır |
| `.github/ISSUE_TEMPLATE/` | Yönetim formları (betik tarafından otomatik üretilir) |
| `scripts/admin.py` + `yonetim.yml` | Formları işleyip siteyi günceller |
| `data/settings.json` | Site ayarları |
| `data/manual.json` | Senin eklediğin / düzenlediğin haberler |

## Kurulum (bir kerelik, ~5 dakika)

1. GitHub'da **`KULLANICIADIN.github.io`** adında **Public** bir depo (repository) oluştur.
   Sitenin adresi tam olarak bu olur: `https://KULLANICIADIN.github.io`
2. Bu klasördeki her şeyi depoya yükle (gizli `.github` klasörü dahil).
3. Depoda **Settings → Actions → General → Workflow permissions** → **Read and write permissions** seç → Save.
4. **Settings → Pages** → Source: **Deploy from a branch**, Branch: **main / (root)** → Save.
5. **Actions** sekmesi → "Haberleri otomatik çek" → **Run workflow**. 1–2 dakika sonra site haberlerle dolar.

Bundan sonra haberler her 30 dakikada bir kendiliğinden yenilenir.

## Siteyi yönetme

Sitende **`https://penomen06.github.io/?yonetim`** adresini aç (yer imlerine ekle). Üstte koyu bir yönetim çubuğu çıkar,
her haberin altında da **ID**, **✏️ Düzenle / manşet** ve **🗑️ Sil** bağlantıları görünür. Tarayıcı bunu hatırlar;
kapatmak için "Yönetimden çık"a bas. Bağlantılara tıklayınca GitHub'da **doldurulmuş bir form** açılır, sen sadece
**Submit**'e basarsın. 1–2 dakika içinde sitede görünür; form sonucu yazıp kendiliğinden kapanır.

| Ne yapmak istiyorsun? | Form |
|---|---|
| Haber eklemek (resim, link, manşet) | 📰 Haber Ekle |
| Haberin başlığını/metnini/resmini/linkini değiştirmek, manşete almak/çıkarmak | ✏️ Haber Düzenle |
| Haber silmek (otomatik gelen bir haberi silersen bir daha gelmez) | 🗑️ Haber Sil |
| Site adı, üst yazı, vurgu rengi, alt bilgi, kaynak başına haber sayısı, yasaklı kelimeler | ⚙️ Site Ayarları |
| RSS kaynağı eklemek/kaldırmak, yeni kategori açmak, kategori adını değiştirmek/kaldırmak | 📡 Kaynak ve Kategori |

Formlara doğrudan da ulaşabilirsin: https://github.com/penomen06/penomen06.github.io/issues/new/choose

İpuçları:
- Düzenleme formunda boş bıraktığın alanlar değişmez. Bir alanı tamamen silmek için içine sadece `-` yaz.
- Yeni bir kategori adıyla kaynak eklersen menüde o kategori sekmesi kendiliğinden açılır.
- Formlarda bir hata olursa (yanlış renk kodu, olmayan ID gibi) hiçbir şey değişmez; form nedenini yazarak kapanır.
- Sadece depo sahibinin (senin) gönderdiği formlar işlenir. Yapılan tüm işlemler "📋 Geçmiş"te durur.

## Notlar
- GitHub zamanlanmış görevleri yoğunlukta birkaç dakika gecikmeli çalıştırabilir.
- Sitede haberlerin yalnızca başlık, kısa özet ve resmi gösterilir; tamamı için okur kaynağa yönlendirilir.
- Kendi alan adını (ör. `haberim.com`) sonradan **Settings → Pages → Custom domain** ile bağlayabilirsin.
