(() => {
  const { family, books, catalog } = window.NB;
  const kids = family.filter((f) => f.born);
  const SEASONS = [
    { key: "winter", label: "Winter", months: "Dec–Feb" },
    { key: "spring", label: "Spring", months: "Mar–May" },
    { key: "summer", label: "Summer", months: "Jun–Aug" },
    { key: "fall", label: "Fall", months: "Sep–Nov" },
  ];
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"];
  // Typical height in inches by age, for pencil marks on the doorframe.
  const HEIGHT = [20, 29.5, 34, 37.5, 40.5, 43, 45.5, 48, 50.5, 52.5, 54.5, 56.5, 59, 61.5, 64, 65.5, 66.5, 67, 67.5, 68, 68];

  const root = document.documentElement;
  const $ = (sel, el = document) => el.querySelector(sel);

  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c.nodeType ? c : document.createTextNode(c));
    }
    return el;
  }
  const svgUse = (id, cls) => {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    if (cls) svg.setAttribute("class", cls);
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(ns, "use");
    use.setAttribute("href", "#" + id);
    svg.append(use);
    return svg;
  };
  const portrait = (member, cls) => [
    h("img", { class: (cls || "") + " day-img", src: member.day, alt: "" }),
    h("img", { class: (cls || "") + " night-img", src: member.night, alt: "" }),
  ];
  const yy = (y) => "’" + String(y).slice(2);

  // ---------- data shaping ----------
  const info = (b) => catalog.books[b.work] || null;
  function authorNames(b) {
    const c = info(b);
    if (c && c.author_names && c.author_names.length) return c.author_names;
    return b.author.split(/\s*(?:&|,| and )\s*/).filter(Boolean);
  }
  const authors = new Map();
  for (const b of books) {
    for (const name of authorNames(b)) {
      if (!authors.has(name)) authors.set(name, { name, readings: [], works: new Set() });
      const a = authors.get(name);
      a.readings.push(b);
      a.works.add(b.work);
    }
  }
  const readingsOf = (work) => books.filter((b) => b.work === work);
  const lastName = (name) => {
    const parts = name.replace(/,?\s+(Jr\.|Sr\.|III)$/, "").split(/\s+/);
    return parts[parts.length - 1];
  };

  function haystack(b) {
    const c = info(b) || {};
    return [b.title, b.author, b.parts.join(" "), c.title, c.summary, (c.characters || []).join(" "),
      (c.genres || []).join(" "), c.setting, c.series].filter(Boolean).join(" ").toLowerCase();
  }
  const hay = new Map(books.map((b) => [b.id, haystack(b)]));

  function whenText(b) {
    if (b.date_basis === "estimated") return `≈ ${b.season} ${yy(b.season_year)}`;
    if (!b.date_raw || /^\d{4}$/.test(b.date_raw.trim())) return String(b.year);
    const start = `${MONTHS[b.month - 1]} ${yy(b.year)}`;
    if (b.end_year !== b.year || b.end_month !== b.month) {
      const end = `${MONTHS[b.end_month - 1]} ${yy(b.end_year)}`;
      return b.end_year === b.year ? `${MONTHS[b.month - 1]}–${end}` : `${start} – ${end}`;
    }
    return start;
  }
  function agesAt(year) {
    return kids.filter((k) => year >= k.born).map((k) => ({ kid: k, age: year - k.born }));
  }

  // ---------- state ----------
  const state = { q: "", genre: "", focus: null };

  // ---------- day / night ----------
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  let sky = "auto";
  try { sky = localStorage.getItem("nb-sky") || "auto"; } catch (e) { /* storage unavailable */ }
  function applySky() {
    if (sky === "auto") root.removeAttribute("data-sky");
    else root.setAttribute("data-sky", sky);
    const theme = root.getAttribute("data-theme");
    const night = sky === "night" || (sky === "auto" && (theme === "dark" || (theme !== "light" && mq.matches)));
    root.setAttribute("data-mode", night ? "night" : "day");
    document.querySelectorAll(".sky button").forEach((btn) => btn.setAttribute("aria-checked", String(btn.dataset.sky === sky)));
  }
  document.querySelectorAll(".sky button").forEach((btn) => btn.addEventListener("click", () => {
    sky = btn.dataset.sky;
    try { localStorage.setItem("nb-sky", sky); } catch (e) { /* storage unavailable */ }
    applySky();
  }));
  mq.addEventListener("change", applySky);
  new MutationObserver(applySky).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  applySky();

  // ---------- header tally ----------
  const years = books.map((b) => b.season_year);
  const firstYear = Math.min(...years);
  const lastYear = Math.max(...years);
  const tally = [
    [books.length, "readings"],
    [new Set(books.map((b) => b.work)).size, "different books"],
    [authors.size, "authors"],
    [`${firstYear}–${yy(lastYear)}`, "years"],
  ];
  $("#tally").append(...tally.map(([n, label]) => h("div", {}, h("dt", { text: label }), h("dd", { text: n }))));

  // ---------- family ----------
  const familyEl = $("#family");
  for (const member of family) {
    const isKid = !!member.born;
    const btn = h("button", {
      class: "kid", type: "button", disabled: !isKid,
      "aria-pressed": isKid ? "false" : null,
      onclick: isKid ? () => setFocus(state.focus === member.slug ? null : member.slug) : null,
    },
      h("span", { class: "frame" }, portrait(member)),
      h("span", { class: "kid-name", text: member.name }),
      h("span", { class: "kid-born", text: isKid ? `born ${member.born}` : member.role }),
    );
    btn.dataset.slug = member.slug;
    familyEl.append(h("li", {}, btn));
  }
  function setFocus(slug) {
    state.focus = slug;
    familyEl.querySelectorAll(".kid[data-slug]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.slug === slug)));
    document.querySelectorAll(".ages").forEach((ul) => {
      ul.classList.toggle("dim", !!slug);
      ul.querySelectorAll(".age").forEach((li) => li.classList.toggle("focus", li.dataset.kid === slug));
    });
  }

  // ---------- timeline ----------
  const timeline = $("#timeline");
  const yearEls = new Map();
  const slipEls = new Map();

  function ageChip(kid, age) {
    const li = h("li", { class: "age" + (age === 0 ? " newborn" : ""), title: kid.name },
      h("img", { class: "day-img", src: kid.day, alt: "" }),
      h("img", { class: "night-img", src: kid.night, alt: "" }),
      h("span", {}, kid.name, " ", age === 0 ? h("b", { text: "born!" }) : h("b", { text: age })),
    );
    li.dataset.kid = kid.slug;
    return li;
  }

  function authorButtons(b) {
    const names = authorNames(b);
    const out = [];
    names.forEach((name, i) => {
      if (i) out.push(i === names.length - 1 ? " & " : ", ");
      out.push(h("button", { class: "author-link", type: "button", onclick: () => openAuthor(name), text: name }));
    });
    return h("span", {}, out);
  }

  function slip(b) {
    const c = info(b);
    const li = h("li", { class: "slip" },
      h("button", { class: "slip-title", type: "button", onclick: () => openBook(b.id), text: c && c.title ? c.title : b.title }),
      h("div", { class: "slip-meta" },
        authorButtons(b),
        b.parts.length ? h("span", { class: "parts-n", text: `${b.parts.length} books` }) : null,
        b.reading > 1 ? h("span", { class: "stamp", text: "again!" }) : null,
        h("span", { class: "when" + (b.date_basis === "estimated" ? " est" : ""), text: whenText(b) }),
      ),
    );
    slipEls.set(b.id, li);
    return li;
  }

  for (let y = firstYear; y <= lastYear; y++) {
    const inYear = books.filter((b) => b.season_year === y);
    const ages = agesAt(y);
    const li = h("li", { class: "year", id: `y${y}` },
      h("div", { class: "year-head" },
        h("h2", { class: "year-sign", text: y }),
        h("span", { class: "year-count", text: inYear.length === 1 ? "1 book" : `${inYear.length} books` }),
        ages.length ? h("ul", { class: "ages", "aria-label": `Ages in ${y}` }, ages.map((a) => ageChip(a.kid, a.age))) : null,
      ),
      h("div", { class: "seasons" }, SEASONS.map((s) => {
        const list = inYear.filter((b) => b.season === s.key);
        return h("section", { class: `season ${s.key}`, "aria-label": `${s.label} ${y}` },
          h("h3", { class: "season-h" }, svgUse(`i-${s.key}`), s.label, h("small", { text: s.months })),
          list.length ? h("ul", { class: "slips" }, list.map(slip)) : h("p", { class: "season-empty", text: emptyLine(s.key) }),
        );
      })),
    );
    li.dataset.year = y;
    yearEls.set(y, li);
    timeline.append(li);
  }
  function emptyLine(season) {
    return { winter: "snowed in, no book noted", spring: "out in the garden", summer: "out in the garden", fall: "putting up the harvest" }[season];
  }

  // ---------- filters ----------
  const genreSel = $("#genre");
  const genreCount = new Map();
  for (const b of books) for (const g of (info(b) || {}).genres || []) genreCount.set(g, (genreCount.get(g) || 0) + 1);
  [...genreCount.entries()].filter(([, n]) => n >= 3).sort((a, b) => a[0].localeCompare(b[0]))
    .forEach(([g, n]) => genreSel.append(h("option", { value: g, text: `${g} (${n})` })));
  if (genreSel.options.length === 1) genreSel.hidden = true;

  const jumpSel = $("#jump");
  for (const y of yearEls.keys()) jumpSel.append(h("option", { value: y, text: y }));
  jumpSel.addEventListener("change", () => {
    if (jumpSel.value) goToYear(+jumpSel.value);
    jumpSel.value = "";
  });

  const note = $("#result-note");
  function applyFilter() {
    const q = state.q.trim().toLowerCase();
    const active = q || state.genre;
    let shown = 0;
    for (const b of books) {
      const el = slipEls.get(b.id);
      const ok = (!q || hay.get(b.id).includes(q)) && (!state.genre || ((info(b) || {}).genres || []).includes(state.genre));
      el.hidden = !ok;
      el.classList.toggle("hit", !!active && ok);
      if (ok) shown++;
    }
    for (const [, el] of yearEls) el.hidden = !!active && !el.querySelector(".slip:not([hidden])");
    note.hidden = !active;
    note.replaceChildren(
      `${shown} of ${books.length} readings match. `,
      h("button", { type: "button", text: "Show all", onclick: () => { $("#q").value = ""; genreSel.value = ""; state.q = ""; state.genre = ""; applyFilter(); } }),
    );
  }
  let qTimer;
  $("#q").addEventListener("input", (e) => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => { state.q = e.target.value; applyFilter(); }, 120);
  });
  genreSel.addEventListener("change", () => { state.genre = genreSel.value; applyFilter(); });

  function goToYear(y) {
    const el = yearEls.get(y);
    if (el && !el.hidden) el.scrollIntoView({ block: "start" });
  }

  // ---------- "what did we read when ___ was ___" ----------
  const wwKid = $("#ww-kid");
  const wwAge = $("#ww-age");
  kids.forEach((k) => wwKid.append(h("option", { value: k.slug, text: k.name })));
  function fillAges() {
    const k = kids.find((x) => x.slug === wwKid.value);
    const prev = wwAge.value;
    wwAge.replaceChildren();
    for (let a = Math.max(0, firstYear - k.born); a <= lastYear - k.born; a++) wwAge.append(h("option", { value: a, text: a === 0 ? "a baby" : a }));
    if ([...wwAge.options].some((o) => o.value === prev)) wwAge.value = prev;
    else wwAge.value = String(Math.min(Math.max(+wwAge.options[0].value, 7), lastYear - k.born));
  }
  wwKid.addEventListener("change", fillAges);
  fillAges();
  $("#whenwas-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const k = kids.find((x) => x.slug === wwKid.value);
    setFocus(k.slug);
    goToYear(k.born + +wwAge.value);
  });

  // ---------- doorframe + climbing nuthatch ----------
  const doorYear = $("#door-year");
  const doorMarks = $("#door-marks");
  let currentYear = null;
  function drawDoor(y) {
    if (y === currentYear) return;
    currentYear = y;
    doorYear.textContent = y;
    const marks = agesAt(y).map(({ kid, age }) => ({ kid, age, pct: (HEIGHT[Math.min(age, HEIGHT.length - 1)] / 72) * 100 }))
      .sort((a, b) => a.pct - b.pct);
    // Labels sit to the right of the marks, nudged upward so close heights stay readable.
    const doorPx = doorMarks.offsetHeight || 480;
    let labelPx = -Infinity;
    doorMarks.replaceChildren(...marks.map((m) => {
      const markPx = (m.pct / 100) * doorPx;
      labelPx = Math.max(markPx, labelPx + 20);
      return h("div", { class: "mark", style: `bottom:${m.pct.toFixed(1)}%` },
        h("span", { style: `transform:translateY(${(markPx - labelPx).toFixed(0)}px)`, text: `${m.kid.name} ${m.age || "·"}` }));
    }));
  }
  const seen = new Map();
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) seen.set(+e.target.dataset.year, e.isIntersecting);
    const visible = [...seen.entries()].filter(([, v]) => v).map(([y]) => y);
    if (visible.length) drawDoor(Math.min(...visible));
  }, { rootMargin: "-30% 0px -55% 0px" });
  yearEls.forEach((el) => io.observe(el));
  drawDoor(firstYear);

  const climber = $(".climber");
  let hopTimer = 0;
  window.addEventListener("scroll", () => {
    if (!climber || hopTimer) return;
    hopTimer = setTimeout(() => { hopTimer = 0; }, 420);
    climber.classList.remove("hop");
    void climber.offsetWidth;
    climber.classList.add("hop");
  }, { passive: true });

  // ---------- authors section ----------
  const ranked = [...authors.values()].sort((a, b) => b.readings.length - a.readings.length || a.name.localeCompare(b.name));
  const top = ranked.slice(0, 12);
  const max = top[0].readings.length;
  $("#most-read").append(
    h("h3", { class: "card-kind", style: "text-align:center;margin-bottom:.4rem", text: "Read aloud most often" }),
    ...top.map((a) => h("div", { class: "bar-row" },
      h("button", { class: "author-link", type: "button", onclick: () => openAuthor(a.name), text: a.name }),
      h("div", { class: "bar", style: `width:${(a.readings.length / max) * 85}%` }, h("span", { text: a.readings.length })),
    )),
  );
  const byLetter = new Map();
  [...authors.values()].sort((a, b) => lastName(a.name).localeCompare(lastName(b.name)) || a.name.localeCompare(b.name))
    .forEach((a) => {
      const L = lastName(a.name)[0].toUpperCase();
      if (!byLetter.has(L)) byLetter.set(L, []);
      byLetter.get(L).push(a);
    });
  $("#author-index").append(...[...byLetter.entries()].map(([L, list]) => h("div", { class: "letter" },
    h("h3", { text: L }),
    h("ul", {}, list.map((a) => h("li", {},
      h("button", { class: "author-link", type: "button", onclick: () => openAuthor(a.name), text: a.name }),
      h("small", { text: a.readings.length }),
    ))),
  )));

  // ---------- library cards ----------
  const dialog = $("#card");
  const cardBody = $("#card-body");
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  function showCard(children, labelText) {
    cardBody.replaceChildren(
      h("button", { class: "card-close", type: "button", "aria-label": "Close card", onclick: () => dialog.close(), text: "×" }),
      ...children.flat().filter(Boolean),
    );
    dialog.setAttribute("aria-label", labelText);
    if (!dialog.open) dialog.showModal();
    cardBody.scrollTop = 0;
    dialog.scrollTop = 0;
  }
  const field = (label, value) => value ? [h("dt", { text: label }), h("dd", {}, value)] : [];
  const link = (url) => url ? h("p", { class: "source" }, "Source: ", h("a", { href: url, target: "_blank", rel: "noopener", text: url.replace(/^https?:\/\/(www\.)?/, "") })) : null;

  function openBook(id) {
    const b = books.find((x) => x.id === id);
    const c = info(b) || {};
    const all = readingsOf(b.work);
    const ages = agesAt(b.season_year);
    showCard([
      h("p", { class: "card-kind", text: `Read-aloud card · line ${b.n} of the notebook` }),
      h("h2", { id: "card-title", text: c.title || b.title }),
      h("p", { class: "by" }, "by ", authorButtons(b)),
      c.genres && c.genres.length ? h("ul", { class: "genres" }, c.genres.map((g) => h("li", { text: g }))) : null,
      c.summary ? h("p", { text: c.summary }) : h("p", { class: "pending", text: "Notes on this book are still being gathered." }),
      h("dl", { class: "fields" },
        field("Published", c.published ? String(c.published) : null),
        field("Setting", c.setting),
        field("Series", c.series),
        field("Illustrated", c.illustrator),
        field("Ages", c.reading_age),
        field("Awards", c.awards && c.awards.length ? c.awards.join("; ") : null),
      ),
      ages.length ? [h("h3", { text: `Listening in ${b.season} ${b.season_year}` }), h("ul", { class: "read-when" }, ages.map((a) => ageChip(a.kid, a.age)))] : null,
      c.characters && c.characters.length ? [h("h3", { text: "Characters" }), h("ul", { class: "list" }, c.characters.map((x) => h("li", { text: x })))] : null,
      b.parts.length ? [h("h3", { text: "Books on this line" }), h("ul", { class: "list" }, b.parts.map((x) => h("li", { text: x })))] : null,
      h("h3", { text: all.length > 1 ? `Read aloud ${all.length} times` : "Read aloud" }),
      checkoutTable(all, false),
      link(c.source),
    ], c.title || b.title);
    highlightAges();
  }

  function openAuthor(name) {
    const a = authors.get(name);
    const c = catalog.authors[name] || {};
    const life = c.born || c.died ? `${c.born || "?"}–${c.died || ""}` : null;
    showCard([
      h("p", { class: "card-kind", text: "Author card" }),
      h("h2", { id: "card-title", text: name }),
      life || c.birthplace ? h("p", { class: "by", text: [life, c.birthplace].filter(Boolean).join(" · born in ") }) : null,
      c.bio ? h("p", { text: c.bio }) : h("p", { class: "pending", text: "Notes on this author are still being gathered." }),
      h("dl", { class: "fields" },
        field("From", c.nationality),
        field("Known for", c.known_for && c.known_for.length ? c.known_for.join("; ") : null),
      ),
      h("h3", { text: `${a.readings.length} ${a.readings.length === 1 ? "reading" : "readings"} in the notebook` }),
      checkoutTable(a.readings, true),
      link(c.source),
    ], name);
    highlightAges();
  }

  function checkoutTable(list, withTitle) {
    return h("div", { class: "table-wrap" }, h("table", { class: "checkout" },
      h("thead", {}, h("tr", {}, h("th", { text: "When" }), withTitle ? h("th", { text: "Title" }) : null, h("th", { text: "Ages" }))),
      h("tbody", {}, list.map((r) => h("tr", {},
        h("td", { text: whenText(r) }),
        withTitle ? h("td", {}, h("button", { type: "button", onclick: () => openBook(r.id), text: (info(r) || {}).title || r.title })) : null,
        h("td", { text: agesAt(r.season_year).map((x) => `${x.kid.name} ${x.age}`).join(", ") || "before the children" }),
      ))),
    ));
  }
  function highlightAges() {
    if (!state.focus) return;
    cardBody.querySelectorAll(".age").forEach((li) => li.classList.toggle("focus", li.dataset.kid === state.focus));
  }
})();
