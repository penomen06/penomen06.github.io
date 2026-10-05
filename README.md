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
| `.github/ISSUE_TEMPLATE/haber-ekle.yml` | Senin haber ekleme formun |
| `scripts/add_post.py` + `haber-ekle.yml` | Formdaki haberi `data/manual.json`'a ekleyip yayınlar |

## Kurulum (bir kerelik, ~5 dakika)

1. GitHub'da **`KULLANICIADIN.github.io`** adında **Public** bir depo (repository) oluştur.
   Sitenin adresi tam olarak bu olur: `https://KULLANICIADIN.github.io`
2. Bu klasördeki her şeyi depoya yükle (gizli `.github` klasörü dahil).
3. Depoda **Settings → Actions → General → Workflow permissions** → **Read and write permissions** seç → Save.
4. **Settings → Pages** → Source: **Deploy from a branch**, Branch: **main / (root)** → Save.
5. **Actions** sekmesi → "Haberleri otomatik çek" → **Run workflow**. 1–2 dakika sonra site haberlerle dolar.

Bundan sonra haberler her 30 dakikada bir kendiliğinden yenilenir.

## Kendi haberini ekleme

Depoda **Issues → New issue → 📰 Haber Ekle**:
- Başlık, kategori, açıklama yaz
- Resmi kutuya sürükle-bırak yap (telefonda galeriden seç) ya da resim linki yapıştır
- İstersen haber linkini ekle, "Sabitle" ile manşete koy
- **Submit** → 1–2 dakika içinde sitede yayında, form kendiliğinden kapanır.

Güvenlik: Sadece depo sahibinin (senin) açtığı formlar yayınlanır, başkaları ekleyemez.

**Silme / düzenleme:** `data/manual.json` dosyasını GitHub'da açıp kalem simgesiyle düzenle.

## Kaynak ekleme / çıkarma

`data/feeds.json` dosyasına RSS adresi ekle. Yeni kategori de açabilirsin (ör. `"spor": [...]`);
sitede görünmesi için `index.html`'deki menüye bir buton eklemen yeterli.

## Notlar
- GitHub zamanlanmış görevleri yoğunlukta birkaç dakika gecikmeli çalıştırabilir.
- Sitede haberlerin yalnızca başlık, kısa özet ve resmi gösterilir; tamamı için okur kaynağa yönlendirilir.
- Kendi alan adını (ör. `haberim.com`) sonradan **Settings → Pages → Custom domain** ile bağlayabilirsin.
