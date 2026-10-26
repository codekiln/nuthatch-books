"""Merge the research batches in data/research/ into data/catalog.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENRE_SAME = {"ghost story": "ghost stories", "coming-of-age": "coming of age",
              "fairy tales": "fairy tale", "detective": "mystery", "fiction": None}


def main():
    works = {b["work"] for b in json.loads((ROOT / "data" / "books.json").read_text())}
    catalog = {"books": {}, "authors": {}}
    for path in sorted((ROOT / "data" / "research").glob("output-*.json")):
        batch = json.loads(path.read_text())
        for work, book in batch.get("books", {}).items():
            genres = [GENRE_SAME.get(g, g) for g in book.get("genres") or []]
            book["genres"] = list(dict.fromkeys(g for g in genres if g))
            catalog["books"][work] = book
        for name, author in batch.get("authors", {}).items():
            catalog["authors"].setdefault(name, author)
    missing = works - catalog["books"].keys()
    extra = catalog["books"].keys() - works
    for work in extra:
        del catalog["books"][work]
    (ROOT / "data" / "catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{len(catalog['books'])} books, {len(catalog['authors'])} authors; missing {sorted(missing)}; dropped {sorted(extra)}")


if __name__ == "__main__":
    main()
