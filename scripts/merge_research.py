"""Merge the research in data/research/ into data/catalog.json.

Layers, later ones winning:
- output-*.json: first-draft notes on every book and author.
- link-check.json: each draft source link, fetched; links that resolved are
  replaced with the page they resolved to, the rest are dropped.
- verified-*.json: entries checked against pages opened on the web.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "data" / "research"
GENRE_SAME = {"ghost story": "ghost stories", "coming-of-age": "coming of age",
              "fairy tales": "fairy tale", "detective": "mystery", "fiction": None}


def tidy_genres(book):
    genres = [GENRE_SAME.get(g, g) for g in book.get("genres") or []]
    book["genres"] = list(dict.fromkeys(g for g in genres if g))
    return book


def main():
    works = {b["work"] for b in json.loads((ROOT / "data" / "books.json").read_text())}
    catalog = {"books": {}, "authors": {}}
    for path in sorted(RESEARCH.glob("output-*.json")):
        batch = json.loads(path.read_text())
        for work, book in batch.get("books", {}).items():
            catalog["books"][work] = tidy_genres(book)
        for name, author in batch.get("authors", {}).items():
            catalog["authors"].setdefault(name, author)

    link_check = RESEARCH / "link-check.json"
    if link_check.exists():
        for key, result in json.loads(link_check.read_text()).items():
            kind, name = key.split("|", 1)
            entry = catalog[kind].get(name)
            if entry is None:
                continue
            entry["source"] = result["resolved"] if result["status"] == "ok" else None
            entry["checked"] = result["status"] == "ok"

    verified = 0
    for path in sorted(RESEARCH.glob("verified-*.json")):
        batch = json.loads(path.read_text())
        for work, book in batch.get("books", {}).items():
            book = tidy_genres(book)
            book["checked"] = bool(book.get("source"))
            catalog["books"][work] = book
            verified += 1
        for name, author in batch.get("authors", {}).items():
            author["checked"] = bool(author.get("source"))
            catalog["authors"][name] = author

    named = {n for b in catalog["books"].values() for n in b.get("author_names") or []}
    for name in sorted(catalog["authors"].keys() - named):
        del catalog["authors"][name]
    missing = works - catalog["books"].keys()
    extra = catalog["books"].keys() - works
    for work in extra:
        del catalog["books"][work]
    (ROOT / "data" / "catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    checked = sum(bool(b.get("checked")) for b in catalog["books"].values())
    print(f"{len(catalog['books'])} books ({checked} with a checked source, {verified} re-verified), "
          f"{len(catalog['authors'])} authors; missing {sorted(missing)}; dropped {sorted(extra)}; "
          f"authors without a record {sorted(named - catalog['authors'].keys())}")


if __name__ == "__main__":
    main()
