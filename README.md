# Nuthatch Books

A timeline of the books a mother read aloud to her five children in a log cabin in the woods, 1980s–1990s, built from her handwritten notebook.

- `data/books.json` holds every book in notebook order with its estimated date.
- `data/catalog.json` holds what we found out about each book and author.
- `site/` holds the page template, styles and script.
- `scripts/build.py` combines them into one self-contained `dist/index.html`.

```bash
python3 scripts/build.py
```

Every push to `main` rebuilds the page and deploys it to https://codekiln.github.io/nuthatch-books/.

Browse the timeline by recommended age group, genre, or search text. A book appears in every age group its recommendation overlaps. Grade-only, broad, missing, and unrecognized age descriptions appear under “Age not specified”; the original recommendation stays on the book card.

Run the age-filter checks with Node.js:

```bash
node --test tests/age-filter.test.cjs
```
