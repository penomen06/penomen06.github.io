"""Betiklerin ortak kullandığı yardımcılar: veri dosyaları, ayarlar, form şablonları."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"

DEFAULT_SETTINGS = {
    "title": "Gündem & Teknoloji",
    "subtitle": "Otomatik güncellenir",
    "description": "Teknoloji ve gündemden en güncel haberler; her 30 dakikada bir otomatik güncellenir.",
    "accent": "#d7263d",
    "footer": "Haber başlıkları ve özetleri ilgili kaynaklardan alınır; tamamı için habere tıklayın.",
    "categories": {"teknoloji": "Teknoloji", "gundem": "Gündem"},
    "per_feed": 15,
    "blocked_words": [],
    "blocked_links": [],
    "google_verification": "",
    "site_url": "",
}


def load(name, default):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def settings():
    s = {**DEFAULT_SETTINGS, **load("settings.json", {})}
    s["categories"] = s.get("categories") or dict(DEFAULT_SETTINGS["categories"])
    return s


def item_id(link):
    return hashlib.sha1(link.encode("utf-8")).hexdigest()[:8]


TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").translate(TR).lower()).strip("-")


# ---------------------------------------------------------------- formlar
q = lambda s: json.dumps(s, ensure_ascii=False)  # YAML için güvenli tırnaklama


def _field(kind, fid, label, description="", required=False, extra=""):
    out = f"  - type: {kind}\n    id: {fid}\n    attributes:\n      label: {q(label)}\n"
    if description:
        out += f"      description: {q(description)}\n"
    out += extra
    if required:
        out += "    validations:\n      required: true\n"
    return out


def _dropdown(fid, label, options, description="", required=True):
    extra = "      options:\n" + "".join(f"        - {q(o)}\n" for o in options) + "      default: 0\n"
    return _field("dropdown", fid, label, description, required, extra)


def _form(name, about, title, label, fields):
    return (f"name: {q(name)}\ndescription: {q(about)}\ntitle: {q(title)}\n"
            f"labels: [{q(label)}]\nbody:\n" + "".join(fields))


def write_templates(s, feeds):
    """Formları güncel kategorilere göre yeniden üretir."""
    cats = list(s["categories"].values())
    cat_list = ", ".join(f"{k} ({v})" for k, v in s["categories"].items())
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    files = {
        "1-haber-ekle.yml": _form("📰 Haber Ekle", "Siteye kendi haberini ekle", "[Haber] ", "haber", [
            _field("input", "baslik", "Başlık", required=True),
            _dropdown("kategori", "Kategori", cats),
            _field("textarea", "aciklama", "Haber metni", "Haberin tamamı; sitende kendi sayfasında okunur. Paragraflar arasına boş satır bırak, araya resim de sürükleyebilirsin."),
            _field("textarea", "resim", "Resim", "Resmi buraya sürükle-bırak yap ya da resim linkini yapıştır"),
            _field("input", "link", "Link", "Haberin kaynağı / devamı (isteğe bağlı)"),
            _field("checkboxes", "secenek", "Seçenekler", extra="      options:\n        - label: \"Sabitle (manşette göster)\"\n"),
        ]),
        "2-haber-duzenle.yml": _form("✏️ Haber Düzenle", "Bir haberi değiştir ya da manşete al/çıkar. Boş bıraktığın alanlar değişmez; bir alanı silmek için içine sadece - yaz.", "[Düzenle] ", "duzenle", [
            _field("input", "haber_id", "Haber ID", "Sitede yönetim modunda her haberin altında yazar", required=True),
            _field("input", "baslik", "Başlık"),
            _dropdown("kategori", "Kategori", ["Değiştirme"] + cats),
            _field("textarea", "aciklama", "Haber metni", "Paragraflar arasına boş satır bırak, araya resim sürükleyebilirsin."),
            _field("textarea", "resim", "Resim", "Yeni resmi sürükle-bırak yap ya da linkini yapıştır"),
            _field("input", "link", "Link"),
            _dropdown("manset", "Manşet", ["Değiştirme", "Sabitle", "Sabitlemeyi kaldır"]),
        ]),
        "3-haber-sil.yml": _form("🗑️ Haber Sil", "Bir haberi siteden kaldır. Otomatik gelen bir haberi silersen bir daha gelmez.", "[Sil] ", "sil", [
            _field("input", "haber_id", "Haber ID", "Birden fazla haber için ID'leri virgülle ayır", required=True),
        ]),
        "4-site-ayarlari.yml": _form("⚙️ Site Ayarları", "Sitenin adını, rengini, yazılarını ve filtrelerini değiştir. Boş bıraktığın alanlar değişmez.", "[Ayarlar] ", "ayarlar", [
            _field("input", "baslik", "Site adı", "Örn: Gündem & Teknoloji (& işareti renkli görünür)"),
            _field("input", "altyazi", "Üst yazı", "Başlığın yanındaki kısa yazı"),
            _field("textarea", "aciklama", "Site açıklaması", "Google arama sonuçlarında sitenin altında görünen 1-2 cümle (en fazla ~160 karakter)"),
            _field("input", "renk", "Vurgu rengi", "Başlık bandı, butonlar ve logo bu renkte olur. Örn: #d7263d (kırmızı), #1f4fd8 (mavi), #0f8a5f (yeşil), #7b2cbf (mor), #f77f00 (turuncu)"),
            _field("textarea", "altbilgi", "Alt bilgi", "Sayfanın en altındaki yazı"),
            _field("input", "adet", "Her kaynaktan haber sayısı", "1 ile 50 arası bir sayı"),
            _field("textarea", "kelimeler", "Engellenen kelimeler", "Bu kelimeleri içeren otomatik haberler gösterilmez. Her satıra bir kelime. Listeyi boşaltmak için sadece - yaz."),
            _field("input", "google", "Google doğrulama kodu", "Google Search Console'un verdiği HTML etiketi ya da içindeki kod. Silmek için - yaz."),
        ]),
        "5-kaynak-kategori.yml": _form("📡 Kaynak ve Kategori", "Haber kaynağı (RSS) ekle/kaldır, kategori aç/kaldır/adını değiştir.", "[Kaynak] ", "kaynak", [
            _dropdown("islem", "İşlem", ["Kaynak ekle", "Kaynak kaldır", "Kategori adını değiştir", "Kategoriyi kaldır"]),
            _field("input", "kategori", "Kategori", f"Mevcut kategoriler: {cat_list}. Yeni bir ad yazarsan yeni kategori açılır."),
            _field("input", "kategori_adi", "Kategorinin sitede görünen adı", "İsteğe bağlı, örn: Spor"),
            _field("input", "rss", "RSS adresi", "Kaynak ekleme/kaldırma için, örn: https://site.com/feed"),
        ]),
    }
    for old in TEMPLATES.glob("*.yml"):
        if old.name not in files and old.name != "config.yml":
            old.unlink()
    for name, text in files.items():
        (TEMPLATES / name).write_text(text, encoding="utf-8")
    (TEMPLATES / "config.yml").write_text("blank_issues_enabled: true\n", encoding="utf-8")
