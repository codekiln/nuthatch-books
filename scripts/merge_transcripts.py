"""Merge per-page notebook transcripts into data/books.json.

Each book gets a reading date: the month written in the margin when there is
one, otherwise an estimate from its neighbours in notebook order.
"""

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "data" / "transcripts"
OUT = ROOT / "data" / "books.json"
CATALOG_PATH = ROOT / "data" / "catalog.json"
CATALOG = json.loads(CATALOG_PATH.read_text())["books"] if CATALOG_PATH.exists() else {}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jn": 6, "jun": 6, "june": 6, "jly": 7, "jul": 7, "july": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
SEASON_MONTH = {"winter": 2, "spring": 5, "summer": 8, "fall": 11, "autumn": 11}
TOKEN = re.compile(r"(19\d\d|20\d\d|\d\d|[a-z]+)")


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def full_year(token):
    n = int(token)
    if n >= 1900:
        return n
    return 1900 + n if n >= 50 else 2000 + n


def parse_date(raw):
    """Return a list of (year|None, month) points written in a margin note."""
    if not raw or "struck" in raw:
        return []
    points, pending = [], []
    for tok in TOKEN.findall(raw.lower()):
        if tok.isdigit():
            year = full_year(tok)
            if pending:
                points.extend((year, m) for m in pending)
                pending = []
            elif points and points[-1][0] is None:
                points[-1] = (year, points[-1][1])
            else:
                points.append((year, 6))
        elif tok in MONTHS:
            pending.append(MONTHS[tok])
        elif tok in SEASON_MONTH:
            pending.append(SEASON_MONTH[tok])
    points.extend((None, m) for m in pending)
    return points


def month_index(year, month):
    return year * 12 + (month - 1)


def season_of(year, month):
    """Meteorological seasons; December opens the next year's winter."""
    if month == 12:
        return year + 1, "winter"
    return year, ("winter", "spring", "summer", "fall")[month // 3]


def split_parts(entry):
    title, comment = entry["title"], entry.get("comment") or ""
    parts = []
    if ":" in title and ";" in title:
        head, rest = title.split(":", 1)
        parts = [p.strip() for p in rest.split(";") if p.strip()]
        title = head.strip()
    elif comment.startswith("Lists:"):
        parts = [p.strip() for p in comment[len("Lists:"):].split(";") if p.strip()]
    title = re.sub(r"\s*\((books?|bks\.?)[^)]*\)\s*$", "", title, flags=re.I)
    return title, parts


def published_floor(row):
    """Month index of a mid-year release of the newest book on the line, if known."""
    book = CATALOG.get(slug(row["title"]), {})
    year = book.get("published_last") or book.get("published")
    return month_index(year, 7) if year else None


def estimate_after_last_date(rows, start):
    """Date the lines written after the last margin date.

    The notebook runs in reading order, so no line can come before a book
    above it was published. Lines are grouped wherever that floor jumps and
    spread evenly up to the next jump; the last group is a season apart.
    """
    groups, floor = [[start, []]], start
    for row in rows:
        f = published_floor(row)
        if f is not None and f > floor:
            floor = f
            groups.append([floor, []])
        groups[-1][1].append(row)
    groups = [g for g in groups if g[1]]
    for k, (begin, members) in enumerate(groups):
        end = groups[k + 1][0] if k + 1 < len(groups) else begin + 3 * (len(members) + 1)
        for j, row in enumerate(members):
            if k > 0:  # the group opens with the line whose publication set the floor
                row["estimate"] = begin + round((end - begin) * j / len(members))
            else:
                row["estimate"] = begin + round((end - begin) * (j + 1) / (len(members) + 1))


def main():
    rows = []
    for path in sorted(TRANSCRIPTS.glob("IMG_*.json")):
        page = json.loads(path.read_text())
        for entry in page["entries"]:
            title, parts = split_parts(entry)
            points = parse_date(entry.get("date_raw"))
            rows.append({
                "page": page["image"],
                "line": entry["seq"],
                "title": title,
                "parts": parts,
                "author": entry["author"],
                "date_raw": entry.get("date_raw"),
                "points": points,
                "confidence": entry.get("confidence"),
            })

    # Fill a missing year on month-only notes from the nearest dated neighbour.
    last_year = None
    for row in rows:
        fixed = []
        for year, month in row["points"]:
            year = year or last_year
            if year:
                fixed.append((year, month))
        row["points"] = fixed
        if fixed:
            last_year = fixed[-1][0]

    # The notebook opens with books read before the log began in Jan 1986;
    # those undated lines are spread across 1984-85 in notebook order.
    # Page IMG_0318 is another list from those years, written after the log began.
    early = [r for i, r in enumerate(rows) if not r["points"]
             and (r["page"] == "IMG_0318" or not any(x["points"] for x in rows[:i]))]
    lo, hi = month_index(1984, 7), month_index(1985, 12)
    for k, row in enumerate(early):
        row["estimate"] = lo + round((hi - lo) * k / max(1, len(early) - 1))

    anchors = [(i, month_index(*r["points"][0])) for i, r in enumerate(rows) if r["points"]]
    last_anchor = anchors[-1]
    for i, row in enumerate(rows):
        if row["points"] or "estimate" in row:
            continue
        before = [a for a in anchors if a[0] < i]
        if before and i < last_anchor[0]:
            row["estimate"] = before[-1][1]
    estimate_after_last_date(rows[last_anchor[0] + 1:], last_anchor[1])

    seen, books = {}, []
    for n, row in enumerate(rows, 1):
        if row["points"]:
            start = month_index(*row["points"][0])
            end = month_index(*row["points"][-1])
            basis = "written"
        else:
            start = end = row["estimate"]
            basis = "estimated"
        key = slug(row["title"])
        times = seen.get(key, 0) + 1
        seen[key] = times
        season_year, season = season_of(start // 12, start % 12 + 1)
        books.append({
            "id": f"{key}-{times}" if times > 1 else key,
            "work": key,
            "n": n,
            "title": row["title"],
            "parts": row["parts"],
            "author": row["author"],
            "year": start // 12,
            "month": start % 12 + 1,
            "season_year": season_year,
            "season": season,
            "end_year": end // 12,
            "end_month": end % 12 + 1,
            "date_basis": basis,
            "date_raw": row["date_raw"],
            "reading": times,
            "page": row["page"],
            "line": row["line"],
            "confidence": row["confidence"],
        })

    OUT.write_text(json.dumps(books, indent=1, ensure_ascii=False) + "\n")
    est = sum(b["date_basis"] == "estimated" for b in books)
    print(f"{len(books)} books, {est} with estimated dates, "
          f"{books[0]['year']}-{max(b['year'] for b in books)}")


if __name__ == "__main__":
    main()
