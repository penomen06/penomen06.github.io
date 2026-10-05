"""RSS kaynaklarından haberleri çekip data/news.json dosyasına yazar."""
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
FEEDS = json.loads((ROOT / "data" / "feeds.json").read_text(encoding="utf-8"))
OUT = ROOT / "data" / "news.json"
PER_FEED = 15      # her kaynaktan alınacak en fazla haber
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
    items, seen = [], set()
    for category, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url, agent="Mozilla/5.0 HaberBot")
            except Exception as err:  # bir kaynak bozuksa diğerleri devam etsin
                print("HATA", url, err)
                continue
            source = clean(feed.feed.get("title", url), 40)
            for e in feed.entries[:PER_FEED]:
                link = e.get("link")
                if not link or link in seen:
                    continue
                seen.add(link)
                items.append({
                    "title": clean(e.get("title"), 160),
                    "summary": clean(e.get("summary")),
                    "link": link,
                    "image": find_image(e),
                    "source": source,
                    "category": category,
                    "date": when(e),
                })
            print(f"{len(feed.entries):>3} haber  {url}")
    items.sort(key=lambda x: x["date"], reverse=True)
    if not items and OUT.exists():
        print("Hiç haber gelmedi, eski liste korunuyor.")
        return
    OUT.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": items[:MAX_TOTAL],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Toplam:", len(items[:MAX_TOTAL]))


if __name__ == "__main__":
    main()
