"""GitHub'daki yönetim formlarını işler: haber ekle/düzenle/sil, site ayarları, kaynaklar.

Sonuç mesajı .sonuc.txt dosyasına yazılır; iş akışı bunu forma yorum olarak ekleyip formu kapatır.
"""
import os
import re
import sys
from datetime import datetime, timezone

from common import ROOT, item_id, load, save, settings, slug, write_templates

RESULT = ROOT / ".sonuc.txt"


class Hata(Exception):
    pass


def parse_form(body):
    """Issue formu '### Alan adı' başlıkları altında değer üretir."""
    fields = {}
    for block in re.split(r"^### ", body or "", flags=re.M)[1:]:
        name, _, value = block.partition("\n")
        value = value.strip()
        fields[name.strip()] = "" if value == "_No response_" else value
    return fields


def first_image(text):
    m = re.search(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", text) or \
        re.search(r'src="(https?://[^"]+)"', text) or \
        re.search(r"(https?://\S+)", text)
    return m.group(1) if m else ""


def valid_url(u):
    u = (u or "").strip()
    if u and not re.match(r"^https?://\S+$", u):
        raise Hata(f"Geçersiz link: {u}")
    return u


def check_category(c, s):
    c = slug(c)
    for key, label in s["categories"].items():  # görünen ad da kabul edilir
        if c == slug(label):
            return key
    if c not in s["categories"]:
        raise Hata(f"'{c}' diye bir kategori yok. Mevcutlar: {', '.join(s['categories'])}")
    return c


def find(hid):
    """ID'ye göre haberi bulur: (liste adı, haber) döner."""
    hid = hid.strip().lstrip("#")
    for i in load("manual.json", []):
        if str(i.get("id")) == hid:
            return "manual", i
    for i in load("news.json", {}).get("items", []):
        i.setdefault("id", item_id(i.get("link", "")))
        if i["id"] == hid:
            return "auto", i
    raise Hata(f"'{hid}' ID'li haber bulunamadı. ID'yi sitede yönetim modunda haberin altında görebilirsin.")


def block_auto(link):
    s = settings()
    if link and link not in s["blocked_links"]:
        s["blocked_links"] = (s["blocked_links"] + [link])[-2000:]
        save("settings.json", s)
    news = load("news.json", {"items": []})
    news["items"] = [i for i in news["items"] if i.get("link") != link]
    save("news.json", news)


def to_manual(item):
    """Otomatik bir haberi düzenlenebilir hale getirir (kopyasını editör listesine alır)."""
    manual = load("manual.json", [])
    new = {**item, "id": "d" + item["id"], "manual": True, "pinned": False}
    manual.insert(0, new)
    save("manual.json", manual)
    block_auto(item["link"])
    return new


# ---------------------------------------------------------------- komutlar
def cmd_haber(f, n):
    s = settings()
    title = f.get("Başlık", "").strip()
    if not title:
        raise Hata("Başlık boş olamaz.")
    manual = load("manual.json", [])
    manual.insert(0, {
        "id": f"e{n}",
        "title": title,
        "summary": f.get("Haber metni") or f.get("Açıklama", ""),
        "link": valid_url(f.get("Link")),
        "image": first_image(f.get("Resim", "")),
        "source": "Editör",
        "category": check_category(f.get("Kategori") or next(iter(s["categories"])), s),
        "date": datetime.now(timezone.utc).isoformat(),
        "pinned": "[X]" in f.get("Seçenekler", "").upper(),
        "manual": True,
    })
    save("manual.json", manual)
    return f"✅ Haber yayınlandı (ID: e{n}). 1-2 dakika içinde sitede görünür."


def cmd_duzenle(f, n):
    s = settings()
    kind, item = find(f.get("Haber ID", ""))
    if kind == "auto":
        item = to_manual(item)
    changes = []

    def setval(key, label, value, fn=lambda v: v):
        if value == "":
            return
        item[key] = "" if value.strip() == "-" else fn(value)
        changes.append(label)

    setval("title", "başlık", f.get("Başlık", "").strip())
    setval("summary", "metin", f.get("Haber metni") or f.get("Açıklama", ""))
    setval("image", "resim", f.get("Resim", ""), first_image)
    setval("link", "link", f.get("Link", ""), valid_url)
    cat = f.get("Kategori", "")
    if cat and cat != "Değiştirme":
        item["category"] = check_category(cat, s)
        changes.append("kategori")
    if not item.get("title"):
        raise Hata("Başlık boş bırakılamaz.")
    m = f.get("Manşet", "")
    if m == "Sabitle":
        item["pinned"] = True
        changes.append("manşete alındı")
    elif m == "Sabitlemeyi kaldır":
        item["pinned"] = False
        changes.append("manşetten çıkarıldı")
    item["updated"] = datetime.now(timezone.utc).isoformat()
    manual = [item if i["id"] == item["id"] else i for i in load("manual.json", [])]
    save("manual.json", manual)
    if not changes:
        return f"ℹ️ Değişiklik yapılmadı (ID: {item['id']}); hiçbir alan doldurulmamış."
    return f"✅ Haber güncellendi (ID: {item['id']}): " + ", ".join(changes)


def cmd_sil(f, n):
    done = []
    for hid in re.split(r"[,\s]+", f.get("Haber ID", "")):
        if not hid:
            continue
        kind, item = find(hid)
        if kind == "manual":
            save("manual.json", [i for i in load("manual.json", []) if i["id"] != item["id"]])
            if item["id"].startswith("d"):
                block_auto(item.get("link"))  # düzenlenmiş otomatik haber geri gelmesin
        else:
            block_auto(item["link"])
        done.append(f"„{item['title']}”")
    if not done:
        raise Hata("Silinecek haber ID'si yazılmamış.")
    return "🗑️ Silindi: " + ", ".join(done)


def cmd_ayarlar(f, n):
    s = settings()
    changes = []
    if f.get("Site adı"):
        s["title"] = f["Site adı"].strip()[:60]; changes.append("site adı")
    if f.get("Üst yazı"):
        s["subtitle"] = f["Üst yazı"].strip()[:80]; changes.append("üst yazı")
    if f.get("Site açıklaması"):
        s["description"] = re.sub(r"\s+", " ", f["Site açıklaması"]).strip()[:300]; changes.append("site açıklaması")
    if f.get("İletişim formu e-postası"):
        v = f["İletişim formu e-postası"].strip()
        if not re.fullmatch(r"[^@\s/]+@[^@\s/]+\.[a-z]{2,}|[A-Za-z0-9]{16,64}", v, re.I):
            raise Hata("İletişim e-postası anlaşılmadı. Bir e-posta adresi ya da FormSubmit kodu yaz.")
        s["contact_email"] = v; changes.append("iletişim e-postası")
    if f.get("Google doğrulama kodu"):
        g = f["Google doğrulama kodu"].strip()
        m = re.search(r'content="([^"]+)"', g)
        g = "" if g == "-" else (m.group(1) if m else g)
        if g and not re.fullmatch(r"[A-Za-z0-9_\-]{10,100}", g):
            raise Hata("Google doğrulama kodu anlaşılmadı. Search Console'daki etiketi olduğu gibi yapıştır.")
        s["google_verification"] = g; changes.append("Google doğrulama kodu")
    if f.get("Vurgu rengi"):
        c = f["Vurgu rengi"].strip()
        c = c if c.startswith("#") else "#" + c
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
            raise Hata(f"Renk kodu anlaşılmadı: {c}. Örnek: #e4402d")
        s["accent"] = c; changes.append("renk")
    if f.get("Alt bilgi"):
        s["footer"] = f["Alt bilgi"].strip()[:300]; changes.append("alt bilgi")
    if f.get("Her kaynaktan haber sayısı"):
        try:
            s["per_feed"] = max(1, min(50, int(f["Her kaynaktan haber sayısı"])))
        except ValueError:
            raise Hata("Haber sayısı bir sayı olmalı.")
        changes.append("haber sayısı")
    if f.get("Engellenen kelimeler"):
        txt = f["Engellenen kelimeler"].strip()
        s["blocked_words"] = [] if txt == "-" else [w.strip() for w in txt.splitlines() if w.strip()]
        changes.append("engellenen kelimeler")
    if not changes:
        return "ℹ️ Hiçbir alan doldurulmadığı için ayarlar değişmedi."
    save("settings.json", s)
    return "✅ Ayarlar güncellendi: " + ", ".join(changes) + ". Haberler yeni ayarlarla yeniden çekildi."


def cmd_kaynak(f, n):
    s = settings()
    feeds = load("feeds.json", {})
    op = f.get("İşlem", "Kaynak ekle")
    raw_cat = f.get("Kategori", "").strip()
    try:
        cat = check_category(raw_cat, s)  # görünen adıyla yazılmış olabilir
    except Hata:
        cat = slug(raw_cat)
    label = f.get("Kategorinin sitede görünen adı", "").strip()
    rss = valid_url(f.get("RSS adresi"))

    if op == "Kaynak ekle":
        if not rss or not cat:
            raise Hata("Kaynak eklemek için Kategori ve RSS adresi gerekli.")
        if any(rss in v for v in feeds.values()):
            raise Hata("Bu RSS adresi zaten ekli.")
        new_cat = cat not in s["categories"]
        if new_cat:
            s["categories"][cat] = label or raw_cat.title()
        feeds.setdefault(cat, []).append(rss)
        msg = f"✅ Kaynak eklendi → {s['categories'][cat]}" + (" (yeni kategori açıldı)" if new_cat else "")
    elif op == "Kaynak kaldır":
        if not rss:
            raise Hata("Kaldırılacak RSS adresini yaz.")
        if not any(rss in v for v in feeds.values()):
            raise Hata("Bu RSS adresi kayıtlı değil.")
        feeds = {k: [u for u in v if u != rss] for k, v in feeds.items()}
        msg = "🗑️ Kaynak kaldırıldı."
    elif op == "Kategori adını değiştir":
        check_category(cat, s)
        if not label:
            raise Hata("Yeni görünen adı yaz.")
        s["categories"][cat] = label
        msg = f"✅ Kategori adı değişti: {label}"
    elif op == "Kategoriyi kaldır":
        check_category(cat, s)
        if len(s["categories"]) == 1:
            raise Hata("Son kategori kaldırılamaz.")
        del s["categories"][cat]
        feeds.pop(cat, None)
        msg = f"🗑️ '{cat}' kategorisi ve kaynakları kaldırıldı. Bu kategorideki editör haberleri 'Tümü' altında görünmeye devam eder."
    else:
        raise Hata(f"Bilinmeyen işlem: {op}")
    save("settings.json", s)
    save("feeds.json", feeds)
    return msg + " Haberler yeniden çekildi."


COMMANDS = {"haber": cmd_haber, "duzenle": cmd_duzenle, "sil": cmd_sil, "ayarlar": cmd_ayarlar, "kaynak": cmd_kaynak}
TITLE_PREFIX = {"[Haber]": "haber", "[Düzenle]": "duzenle", "[Sil]": "sil", "[Ayarlar]": "ayarlar", "[Kaynak]": "kaynak"}


def detect(labels, title):
    for l in labels:
        if l in COMMANDS:
            return l
    for p, c in TITLE_PREFIX.items():
        if title.strip().startswith(p):
            return c
    return None


def main():
    labels = [l.strip() for l in os.environ.get("ISSUE_LABELS", "").split(",") if l.strip()]
    cmd = detect(labels, os.environ.get("ISSUE_TITLE", ""))
    if not cmd:
        print("Yönetim formu değil, atlanıyor.")
        return
    try:
        msg = COMMANDS[cmd](parse_form(os.environ.get("ISSUE_BODY", "")), os.environ.get("ISSUE_NUMBER", "0"))
        write_templates(settings(), load("feeds.json", {}))
        if cmd in ("ayarlar", "kaynak"):
            import fetch_news
            fetch_news.main()
    except Hata as e:
        RESULT.write_text(f"❌ {e}\n\nHiçbir şey değişmedi. Formu düzeltip yeniden gönderebilirsin.", encoding="utf-8")
        print("HATA:", e)
        sys.exit(1)
    except Exception as e:
        RESULT.write_text(f"❌ Beklenmeyen bir hata oldu: {e}\n\nHiçbir şey değişmedi.", encoding="utf-8")
        raise
    RESULT.write_text(msg, encoding="utf-8")
    print(msg)


if __name__ == "__main__":
    main()
