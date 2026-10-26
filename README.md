# Nuthatch Books

A timeline of the books a mother read aloud to her five children in a log cabin in the woods, 1980s–1990s, built from her handwritten notebook.

- `data/books.json` holds every book in notebook order with its estimated date.
- `data/catalog.json` holds what we found out about each book and author.
- `site/` holds the page template, styles and script.
- `scripts/build.py` combines them into one self-contained `dist/index.html`.

```bash
python3 scripts/build.py
```
