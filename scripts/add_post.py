"""GitHub'daki 'Haber Ekle' formundan gelen içeriği data/manual.json'a ekler."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "manual.json"


def parse_form(body):
    """Issue formu '### Alan adı' başlıkları altında değer üretir."""
    fields = {}
    for block in re.split(r"^### ", body, flags=re.M)[1:]:
        name, _, value = block.partition("\n")
        value = value.strip()
        fields[name.strip()] = "" if value == "_No response_" else value
    return fields


def first_image(text):
    m = re.search(r"!\[[^\]]*\]\((https?://[^)]+)\)", text) or \
        re.search(r'src="(https?://[^"]+)"', text) or \
        re.search(r"(https?://\S+\.(?:png|jpe?g|gif|webp)\S*)", text, re.I)
    return m.group(1) if m else ""


def main():
    f = parse_form(os.environ.get("ISSUE_BODY", ""))
    title = f.get("Başlık", "").strip()
    if not title:
        raise SystemExit("Başlık boş, haber eklenmedi.")
    image = first_image(f.get("Resim", ""))
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    data.insert(0, {
        "id": int(os.environ.get("ISSUE_NUMBER", "0")),
        "title": title,
        "summary": f.get("Açıklama", ""),
        "link": f.get("Link", "").strip(),
        "image": image,
        "source": "Editör",
        "category": f.get("Kategori", "gundem").strip().lower(),
        "date": datetime.now(timezone.utc).isoformat(),
        "pinned": "Sabitle" in f.get("Seçenekler", ""),
    })
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Eklendi:", title)


if __name__ == "__main__":
    main()
