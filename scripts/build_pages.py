"""Arama motorları için statik sayfaları üretir.

Üretilenler:
  index.html                  anasayfa (haberlerle önceden dolu)
  kategori/<ad>/index.html    her kategori + "editor" sayfası
  haber/<baslik>-<id>/        her haberin kendi sayfası
  sitemap.xml, robots.txt, feed.xml (RSS), 404.html
  assets/icon.svg, assets/og.png (paylaşım görseli)

Sayfa tasarımı assets/style.css'de, tarayıcı davranışı assets/app.js'de.
Sayfaların HTML iskeleti bu dosyadadır.
"""
import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from common import ROOT, load, save, settings, slug

TR_TZ = timezone(timedelta(hours=3))  # Türkiye (yaz/kış saati yok)
MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
          "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PALETTE = ["var(--tech)", "var(--gundem)", "#b7791f", "#8b5cf6", "#0e7490", "#db2777", "#4d7c0f"]
PRERENDER = 24  # liste sayfalarında önceden yazılan haber sayısı


def e(x):
    return escape(str(x or ""), quote=True)


def parse_date(iso):
    try:
        d = datetime.fromisoformat(iso)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def tr_date(iso, with_time=True):
    d = parse_date(iso).astimezone(TR_TZ)
    s = f"{d.day} {MONTHS[d.month - 1]} {d.year}"
    return s + f" {d:%H:%M}" if with_time else s


def site_url(s):
    cname = ROOT / "CNAME"
    if cname.exists() and cname.read_text().strip():
        return "https://" + cname.read_text().strip().rstrip("/")
    if s.get("site_url"):
        return s["site_url"].rstrip("/")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "penomen06").lower()
    return f"https://{owner}.github.io"


def repo_name():
    return os.environ.get("GITHUB_REPOSITORY") or "penomen06/penomen06.github.io"


def preview(text, limit=None):
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)|<img[^>]*>", " ", text or "", flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if limit and len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0] + "…"
    return t


def safe_url(u):
    return u if re.match(r"^https?://", u or "", re.I) else ""


def body_html(raw):
    """Editör metnini paragraflara, resimlere ve linklere çevirir (app.js ile aynı kurallar)."""
    imgs = []

    def keep(m):
        imgs.append(m.group(1) or m.group(2))
        return f"\x00{len(imgs) - 1}\x00"

    marked = re.sub(r'!\[[^\]]*\]\((https?://[^)\s]+)\)|<img[^>]*src="(https?://[^"]+)"[^>]*>', keep, raw or "", flags=re.I)
    out = []
    for par in re.split(r"\n\s*\n", marked):
        h = e(par.strip())
        h = re.sub(r"https?://[^\s<]+", lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>', h)
        h = h.replace("\n", "<br>")
        h = re.sub(r"\x00(\d+)\x00", lambda m: f'</p><img src="{e(imgs[int(m.group(1))])}" alt="" loading="lazy" referrerpolicy="no-referrer"><p>', h)
        if h:
            out.append(f"<p>{h}</p>")
    return re.sub(r"<p>(\s|<br>)*</p>", "", "".join(out))


# ---------------------------------------------------------------- ortak parçalar
def head(s, base, *, title, desc, path, image="", kind="website", robots="index, follow", extra=""):
    url = base + path
    img = image or base + "/assets/og.png"
    g = f'<meta name="google-site-verification" content="{e(s["google_verification"])}">\n' if s.get("google_verification") else ""
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots}, max-image-preview:large">
<link rel="canonical" href="{e(url)}">
{g}<meta name="theme-color" content="{e(s['accent'])}">
<meta property="og:site_name" content="{e(s['title'])}">
<meta property="og:locale" content="tr_TR">
<meta property="og:type" content="{kind}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(img)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{e(s['title'])}" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
<style>:root{{--accent:{e(s['accent'])}}}</style>
{extra}</head>
"""


def admin_bar():
    return """<div id="admin"><div class="wrap">
  <b>🔧 Yönetim</b>
  <a id="a-add" target="_blank" rel="noopener">＋ Haber ekle</a>
  <a id="a-set" target="_blank" rel="noopener">⚙️ Site ayarları</a>
  <button id="a-src">📡 Kaynaklar & kategoriler</button>
  <a id="a-log" target="_blank" rel="noopener">📋 Geçmiş</a>
  <button id="a-exit" class="end">Yönetimden çık</button>
</div></div>
<div id="panel"><div class="wrap" id="panel-in"></div></div>
"""


def masthead(s, logo_tag, updated):
    title = e(s["title"]).replace("&amp;", "<span>&amp;</span>")
    return f"""<header class="wrap">
  <div class="top">
    <{logo_tag} class="logo"><a href="/">{title}</a></{logo_tag}>
    <div class="meta"><span class="live"></span>{e(s['subtitle'])}<br><span id="upd">Son güncelleme: {e(tr_date(updated))}</span></div>
  </div>
</header>
"""


def nav(s, active, search):
    tabs = [("hepsi", "Tümü", "/")] + [(k, v, f"/kategori/{k}/") for k, v in s["categories"].items()] + \
           [("editor", "Editörün Seçtikleri", "/kategori/editor/")]
    on = ' aria-current="page"'
    links = "".join(
        f'<a class="tab{" on" if k == active else ""}" href="{href}"{on if k == active else ""}>{e(label)}</a>'
        for k, label, href in tabs)
    box = '<label class="sr" for="q">Haberlerde ara</label><input id="q" type="search" placeholder="Haberlerde ara…">' if search else ""
    return f'<nav class="topnav" aria-label="Kategoriler"><div class="wrap bar" id="tabs">{links}{box}</div></nav>\n'


def tail(s, page_attrs):
    return f"""<footer class="wrap"><p>{e(s['footer'])}</p><p><a href="/feed.xml">RSS</a> · <a href="/sitemap.xml">Site haritası</a></p></footer>
<script src="/assets/app.js" defer></script>
</body>
</html>
"""


def chip(item, s):
    if item.get("manual"):
        return '<span class="chip" style="--c:var(--editor)">Editör</span>'
    keys = list(s["categories"])
    idx = keys.index(item["category"]) if item.get("category") in keys else 0
    return f'<span class="chip" style="--c:{PALETTE[idx % len(PALETTE)]}">{e(s["categories"].get(item.get("category"), item.get("category")))}</span>'


def img_tag(item, cls="", alt="", eager=False):
    u = safe_url(item.get("image"))
    if not u:
        return ""
    load_attr = 'fetchpriority="high"' if eager else 'loading="lazy"'
    cls_attr = f' class="{cls}"' if cls else ""
    return f'<img{cls_attr} src="{e(u)}" alt="{e(alt)}" {load_attr} referrerpolicy="no-referrer" onerror="this.remove()">'


def card(item, s):
    u = e(item["url"])
    summary = f"<p>{e(preview(item.get('summary'), 240))}</p>" if item.get("summary") else ""
    return f"""<article class="card"><a href="{u}" tabindex="-1">{img_tag(item)}</a>
<div class="body">{chip(item, s)}<h3><a href="{u}">{e(item['title'])}</a></h3>{summary}
<div class="foot"><span>{e(item['source'])}</span><time datetime="{e(item['date'])}">{e(tr_date(item['date'], False))}</time></div></div></article>
"""


# ---------------------------------------------------------------- sayfalar
def list_page(s, base, items, updated, *, key, title, h1, desc, path):
    if key == "hepsi":
        pool = items
    elif key == "editor":
        pool = [i for i in items if i.get("manual")]
    else:
        pool = [i for i in items if i.get("category") == key]
    lead = next((i for i in pool if i.get("pinned")), None) or next((i for i in pool if i.get("image")), None)
    rest = [i for i in pool if i is not lead][:PRERENDER]
    hero = ""
    if lead:
        hero = f"""<div class="hero"><a href="{e(lead['url'])}" tabindex="-1">{img_tag(lead, eager=True)}</a>
<div>{chip(lead, s)}<h2><a href="{e(lead['url'])}">{e(lead['title'])}</a></h2><p>{e(preview(lead.get('summary'), 260))}</p>
<div class="foot"><span>{e(lead['source'])}</span><time datetime="{e(lead['date'])}">{e(tr_date(lead['date'], False))}</time></div></div></div>"""
    ld = [{
        "@context": "https://schema.org", "@type": "CollectionPage", "name": title, "description": desc, "url": base + path,
        "isPartOf": {"@type": "WebSite", "name": s["title"], "url": base + "/"},
        "mainEntity": {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "url": base + i["url"], "name": i["title"]}
            for n, i in enumerate(([lead] if lead else []) + rest)]},
    }]
    if key == "hepsi":
        ld.append({"@context": "https://schema.org", "@type": "WebSite", "name": s["title"], "url": base + "/",
                   "description": s["description"], "inLanguage": "tr-TR"})
        ld.append({"@context": "https://schema.org", "@type": "NewsMediaOrganization", "name": s["title"],
                   "url": base + "/", "logo": base + "/assets/og.png"})
    extra = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in ld)
    sr_h1 = "" if key == "hepsi" else f'<h1 class="sr">{e(h1)}</h1>'
    return (head(s, base, title=title, desc=desc, path=path, extra=extra)
            + f'<body data-page="list" data-cat="{e(key)}" data-repo="{e(repo_name())}">\n' + admin_bar()
            + masthead(s, "h1" if key == "hepsi" else "div", updated) + nav(s, key, True)
            + f"""<main class="wrap">{sr_h1}
  <section id="hero">{hero}</section>
  <section id="grid" class="grid">{"".join(card(i, s) for i in rest) or '<div class="empty">Bu bölümde henüz haber yok.</div>'}</section>
  <button id="more" class="tab" hidden>Daha fazla göster</button>
</main>
""" + tail(s, ""))


def article_page(s, base, item, updated):
    manual = bool(item.get("manual"))
    link = safe_url(item.get("link"))
    path = item["url"]
    desc = preview(item.get("summary"), 160) or item["title"]
    cat_label = s["categories"].get(item.get("category"), "")
    if manual:
        text = body_html(item.get("summary"))
        if link:
            text += f'<p class="note">Kaynak: <a href="{e(link)}" target="_blank" rel="noopener">{e(urlparse(link).hostname)}</a></p>'
    else:
        text = (f"<p>{e(item.get('summary'))}</p>" if item.get("summary") else "")
        if link:
            text += (f'<a class="src" href="{e(link)}" target="_blank" rel="noopener">Haberin devamını {e(item["source"])} sitesinde oku →</a>'
                     f'<p class="note">Bu özet {e(item["source"])} tarafından yayınlanmıştır.</p>')
    image = safe_url(item.get("image"))
    ld = {
        "@context": "https://schema.org", "@type": "NewsArticle", "headline": item["title"][:110],
        "description": desc, "datePublished": item["date"], "dateModified": item.get("updated") or item["date"],
        "mainEntityOfPage": base + path, "inLanguage": "tr-TR",
        "author": {"@type": "Organization", "name": s["title"] if manual else item["source"]},
        "publisher": {"@type": "Organization", "name": s["title"], "logo": {"@type": "ImageObject", "url": base + "/assets/og.png"}},
    }
    if image:
        ld["image"] = [image]
    if cat_label:
        ld["articleSection"] = cat_label
    crumbs = [{"@type": "ListItem", "position": 1, "name": "Anasayfa", "item": base + "/"}]
    if cat_label:
        crumbs.append({"@type": "ListItem", "position": 2, "name": cat_label, "item": f"{base}/kategori/{item['category']}/"})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": item["title"]})
    extra = (f'<meta property="article:published_time" content="{e(item["date"])}">\n'
             + (f'<meta property="article:section" content="{e(cat_label)}">\n' if cat_label else "")
             + f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
             + f'<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs}, ensure_ascii=False)}</script>\n')
    # Otomatik haberler başka sitelerin özetidir: Google'da kopya içerik sayılmasın diye dizine eklenmez.
    robots = "index, follow" if manual else "noindex, follow"
    crumb_html = '<a href="/">Anasayfa</a>' + (f' › <a href="/kategori/{e(item["category"])}/">{e(cat_label)}</a>' if cat_label else "")
    return (head(s, base, title=f"{item['title']} | {s['title']}", desc=desc, path=path, image=image,
                 kind="article", robots=robots, extra=extra)
            + f'<body data-page="article" data-id="{e(item["id"])}" data-itemcat="{e(item.get("category"))}" data-repo="{e(repo_name())}">\n'
            + admin_bar() + masthead(s, "div", updated) + nav(s, None, False)
            + f"""<main class="wrap">
<article class="article">
  <nav class="crumbs" aria-label="Konum">{crumb_html}</nav>
  {chip(item, s)}
  <h1>{e(item['title'])}</h1>
  <div class="by">{e(item['source'])} · <time datetime="{e(item['date'])}">{e(tr_date(item['date']))}</time></div>
  {img_tag(item, "cover", item['title'], eager=True)}
  <div class="text">{text}</div>
  <div id="adm-slot"></div>
</article>
<section id="related" class="related"></section>
</main>
""" + tail(s, ""))


def not_found(s, base):
    return (head(s, base, title=f"Sayfa bulunamadı | {s['title']}", desc=s["description"], path="/404.html", robots="noindex")
            + f'<body data-page="list" data-cat="hepsi" data-repo="{e(repo_name())}">\n'
            + """<script>
// Haber başlığı değiştiyse eski adres buraya düşer: sondaki ID'den yeni adresi bulup yönlendir.
(async () => {
  const m = location.pathname.match(/\\/haber\\/(?:.*-)?([a-z0-9]+)\\/?$/i);
  if (!m) return;
  const get = f => fetch(f).then(r => r.ok ? r.json() : null).catch(() => null);
  const [n, man] = await Promise.all([get("/data/news.json"), get("/data/manual.json")]);
  const hit = [...(man || []), ...(n?.items || [])].find(i => String(i.id) === m[1]);
  if (hit && hit.url && hit.url !== location.pathname) location.replace(hit.url);
})();
</script>
""" + admin_bar() + masthead(s, "div", datetime.now(timezone.utc).isoformat()) + nav(s, None, False)
            + """<main class="wrap"><div class="empty"><h1>Aradığın sayfa bulunamadı</h1>
<p>Haber yayından kaldırılmış olabilir. <a class="lnk" href="/">Anasayfaya dön →</a></p></div>
<section id="hero" hidden></section><section id="grid" hidden></section><button id="more" hidden></button><input id="q" hidden></main>
""" + tail(s, ""))


def sitemap(base, s, items):
    rows = [(base + "/", max((i["date"] for i in items), default=None))]
    rows += [(f"{base}/kategori/{k}/", None) for k in list(s["categories"]) + ["editor"]]
    rows += [(base + i["url"], i.get("updated") or i["date"]) for i in items if i.get("manual")]
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, mod in rows:
        out.append(f"  <url><loc>{e(loc)}</loc>" + (f"<lastmod>{parse_date(mod).date().isoformat()}</lastmod>" if mod else "") + "</url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def rss(base, s, items):
    def rfc(iso):
        d = parse_date(iso).astimezone(timezone.utc)
        return d.strftime("%a, %d %b %Y %H:%M:%S +0000")
    entries = "".join(f"""  <item>
    <title>{e(i['title'])}</title>
    <link>{e(base + i['url'])}</link>
    <guid isPermaLink="true">{e(base + i['url'])}</guid>
    <pubDate>{rfc(i['date'])}</pubDate>
    <description>{e(preview(i.get('summary'), 300))}</description>
  </item>
""" for i in items[:50])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{e(s['title'])}</title>
  <link>{e(base)}/</link>
  <description>{e(s['description'])}</description>
  <language>tr</language>
  <atom:link href="{e(base)}/feed.xml" rel="self" type="application/rss+xml"/>
{entries}</channel>
</rss>
"""


def icon_svg(s):
    letter = e((s["title"].strip() or "H")[0].upper())
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{e(s['accent'])}"/><text x="32" y="45" font-family="Georgia,serif" font-size="40" font-weight="700" text-anchor="middle" fill="#fff">{letter}</text></svg>\n"""


def og_image(s):
    """1200x630 paylaşım görseli; sadece site adı veya renk değişince yeniden çizilir."""
    out, stamp = ROOT / "assets" / "og.png", ROOT / "assets" / "og.txt"
    key = f"{s['title']}|{s['accent']}|{s['description']}"
    if out.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == key:
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow yok, paylaşım görseli güncellenmedi.")
        return
    fonts = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"]
    small = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    fbig = next((f for f in fonts if Path(f).exists()), None)
    fsmall = next((f for f in small if Path(f).exists()), None)
    if not fbig:
        print("Yazı tipi yok, paylaşım görseli güncellenmedi.")
        return
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#f6f4ef")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 18], fill=s["accent"])
    d.rectangle([0, H - 18, W, H], fill="#16161a")
    title, size = s["title"], 120
    font = ImageFont.truetype(fbig, size)
    while d.textlength(title, font=font) > W - 160 and size > 50:
        size -= 6
        font = ImageFont.truetype(fbig, size)
    x, y = 80, 210
    for part in re.split(r"(&)", title):  # "&" vurgu renginde
        d.text((x, y), part, font=font, fill=s["accent"] if part == "&" else "#16161a")
        x += d.textlength(part, font=font)
    if fsmall:
        f2 = ImageFont.truetype(fsmall, 34)
        words, lines, cur = s["description"].split(), [], ""
        for w in words:
            if d.textlength((cur + " " + w).strip(), font=f2) > W - 160:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        for n, line in enumerate(lines[:2]):
            d.text((80, y + size + 50 + n * 48), line, font=f2, fill="#6b6b74")
    img.save(out, optimize=True)
    stamp.write_text(key, encoding="utf-8")


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def main():
    s = settings()
    base = site_url(s)
    news = load("news.json", {"items": []})
    manual = load("manual.json", [])

    # Her habere kalıcı bir adres ver (veri dosyalarına da yazılır, app.js kullanır)
    used = set()
    for item in manual + news["items"]:
        stem = slug(item["title"])[:70].strip("-") or "haber"
        url = f"/haber/{stem}-{item['id']}/"
        item["url"] = url
        used.add(url.strip("/").split("/")[1])
    save("manual.json", manual)
    save("news.json", news)

    items = sorted(manual + news["items"], key=lambda i: (bool(i.get("pinned")), i["date"]), reverse=True)
    updated = news.get("updated") or datetime.now(timezone.utc).isoformat()

    write("index.html", list_page(s, base, items, updated, key="hepsi", path="/",
                                  title=f"{s['title']} – Son Dakika Teknoloji ve Gündem Haberleri"
                                  if s["title"] == "Gündem & Teknoloji" else s["title"],
                                  h1=s["title"], desc=s["description"]))
    cats = dict(s["categories"], editor="Editörün Seçtikleri")
    for key, label in cats.items():
        write(f"kategori/{key}/index.html", list_page(
            s, base, items, updated, key=key, path=f"/kategori/{key}/",
            title=f"{label} Haberleri | {s['title']}" if key != "editor" else f"{label} | {s['title']}",
            h1=f"{label} haberleri", desc=f"En güncel {label.lower()} haberleri. {s['description']}"[:160]))
    for old in sorted((ROOT / "kategori").glob("*")):  # kaldırılan kategorilerin sayfalarını sil
        if old.is_dir() and old.name not in cats:
            shutil.rmtree(old)

    for item in items:
        write(item["url"].strip("/") + "/index.html", article_page(s, base, item, updated))
    haber = ROOT / "haber"
    for old in sorted(haber.glob("*")) if haber.exists() else []:  # yayından düşen haberlerin sayfalarını sil
        if old.is_dir() and old.name not in used:
            shutil.rmtree(old)

    write("404.html", not_found(s, base))
    write("sitemap.xml", sitemap(base, s, items))
    write("feed.xml", rss(base, s, sorted(items, key=lambda i: i["date"], reverse=True)))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n")
    write("assets/icon.svg", icon_svg(s))
    og_image(s)
    print(f"{len(items)} haber sayfası, {len(cats)} kategori sayfası üretildi → {base}")


if __name__ == "__main__":
    main()
