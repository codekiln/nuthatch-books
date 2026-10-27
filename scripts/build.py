"""Combine site/ and data/ into one self-contained dist/index.html."""

import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"
DIST = ROOT / "dist"

FAMILY = [
    {"slug": "nuthatch", "name": "nuthatch", "role": "the reader"},
    {"slug": "wonderful-cat", "name": "wonderful cat", "born": 1980},
    {"slug": "fawnicorn", "name": "fawnicorn", "born": 1981},
    {"slug": "treefrog", "name": "treefrog", "born": 1984},
    {"slug": "rabbit", "name": "rabbit", "born": 1987},
    {"slug": "pigeon", "name": "pigeon", "born": 1991},
]

BOOK_FIELDS = ["id", "work", "n", "title", "parts", "author", "year", "month",
               "season_year", "season", "end_year", "end_month", "date_basis",
               "date_raw", "reading", "page"]


def data_uri(path):
    mime = "image/jpeg" if path.suffix == ".jpg" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def load_catalog():
    path = DATA / "catalog.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"books": {}, "authors": {}}


def main():
    books = [{k: b[k] for k in BOOK_FIELDS} for b in json.loads((DATA / "books.json").read_text())]
    family = []
    for member in FAMILY:
        member = dict(member)
        portraits = SITE / "img" / "portraits"
        supplied = portraits / f"{member['slug']}.jpg"
        for theme in ("day", "night"):
            path = supplied if supplied.exists() else portraits / f"{member['slug']}-{theme}.png"
            member[theme] = data_uri(path)
        family.append(member)
    payload = {"family": family, "books": books, "catalog": load_catalog()}

    html = (SITE / "index.html").read_text()
    css = (SITE / "style.css").read_text()
    js = (SITE / "app.js").read_text()
    age_js = (SITE / "age-filter.js").read_text()
    data_js = "window.NB = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"
    html = html.replace('<link rel="stylesheet" href="style.css">', f"<style>\n{css}\n</style>")
    html = html.replace('<script src="data.js"></script>', f"<script>{data_js}</script>")
    html = html.replace('<script src="app.js"></script>', f"<script>\n{js}\n</script>")
    html = html.replace('<script src="age-filter.js"></script>', f"<script>\n{age_js}\n</script>")
    assert not re.search(r'src="(app|data|age-filter)\.js"', html)

    DIST.mkdir(exist_ok=True)
    # artifact.html is the page body for a Claude artifact, which supplies its own
    # document shell; index.html is the standalone page for GitHub Pages.
    (DIST / "artifact.html").write_text(html)
    head, body = html.split("\n\n<svg", 1)
    page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{head}\n</head>\n<body>\n<svg{body}</body>\n</html>\n")
    out = DIST / "index.html"
    out.write_text(page)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(books)} readings)")


if __name__ == "__main__":
    main()
