// Recommended ages describe the book's audience, independently of its listeners.
window.NBAgeFilter = (() => {
  const groups = [
    { key: "0-5", label: "Ages 0–5", min: 0, max: 5 },
    { key: "6-8", label: "Ages 6–8", min: 6, max: 8 },
    { key: "9-12", label: "Ages 9–12", min: 9, max: 12 },
    { key: "13-17", label: "Ages 13–17", min: 13, max: 17 },
    { key: "adult", label: "Adults (18+)", min: 18, max: Infinity },
    { key: "unknown", label: "Age not specified" },
  ];

  function range(value) {
    if (typeof value !== "string") return null;
    const text = value.trim().toLowerCase().replace(/[–—]/g, "-");
    if (/^adult(?:\s*\/\s*older readers)?$/.test(text)) return { min: 18, max: Infinity };
    const match = text.match(/^(\d+)\s*(?:-\s*(\d+|adult)|(\+))?$/);
    if (!match) return null;
    const min = Number(match[1]);
    const max = match[3] || match[2] === "adult" ? Infinity : Number(match[2] || match[1]);
    return min <= max ? { min, max } : null;
  }

  function matches(value, key) {
    if (!key) return true;
    const ages = range(value);
    if (key === "unknown") return ages === null;
    const group = groups.find((g) => g.key === key);
    return !!(ages && group && ages.min <= group.max && ages.max >= group.min);
  }

  return { groups, range, matches };
})();
