"""RSS kaynaklarından haberleri çekip data/news.json dosyasına yazar."""
import html
import re
import time
from datetime import datetime, timezone

import feedparser

from common import DATA, item_id, load, save, settings

MAX_TOTAL = 200    # sitede tutulacak en fazla otomatik haber
TAG_RE = re.compile(r"<[^>]+>")


def clean(text, limit=220):
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def find_image(e):
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key, []) or []:
            if m.get("url"):
                return m["url"]
    for l in e.get("links", []) or []:
        if l.get("rel") == "enclosure" and str(l.get("type", "")).startswith("image"):
            return l.get("href")
    raw = e.get("summary", "") + "".join(c.get("value", "") for c in e.get("content", []) or [])
    m = re.search(r'<img[^>]+src="([^"]+)"', raw)
    return m.group(1) if m else ""


def when(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    ts = time.mktime(t) if t else time.time()
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def main():
    s = settings()
    feeds = load("feeds.json", {})
    blocked_links = set(s["blocked_links"])
    words = [w.lower() for w in s["blocked_words"] if w.strip()]
    items, seen = [], set(blocked_links)
    for category, urls in feeds.items():
        for url in urls:
            try:
                feed = feedparser.parse(url, agent="Mozilla/5.0 HaberBot")
            except Exception as err:  # bir kaynak bozuksa diğerleri devam etsin
                print("HATA", url, err)
                continue
            source = clean(feed.feed.get("title", url), 40)
            for e in feed.entries[: s["per_feed"]]:
                link = e.get("link")
                if not link or link in seen:
                    continue
                seen.add(link)
                item = {
                    "id": item_id(link),
                    "title": clean(e.get("title"), 160),
                    "summary": clean(e.get("summary")),
                    "link": link,
                    "image": find_image(e),
                    "source": source,
                    "category": category,
                    "date": when(e),
                }
                text = (item["title"] + " " + item["summary"]).lower()
                if any(w in text for w in words):
                    continue
                items.append(item)
            print(f"{len(feed.entries):>3} haber  {url}")
    items.sort(key=lambda x: x["date"], reverse=True)
    if not items and (DATA / "news.json").exists() and feeds:
        print("Hiç haber gelmedi, eski liste korunuyor.")
        return
    save("news.json", {"updated": datetime.now(timezone.utc).isoformat(), "items": items[:MAX_TOTAL]})
    print("Toplam:", len(items[:MAX_TOTAL]))


if __name__ == "__main__":
    main()
