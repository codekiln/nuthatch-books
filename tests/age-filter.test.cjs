const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const context = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'site/age-filter.js'), 'utf8'), context);
const { range, matches, groups } = context.window.NBAgeFilter;

test('closed ranges include both endpoints and all overlapping groups', () => {
  assert.equal(matches('8-12', '6-8'), true);
  assert.equal(matches('8-12', '9-12'), true);
  assert.equal(matches('8-12', '13-17'), false);
  assert.equal(matches('5–9', '0-5'), true);
  assert.equal(matches('5—9', '9-12'), true);
  assert.equal(matches('13-18', 'adult'), true);
  assert.equal(matches('6', '6-8'), true);
  assert.equal(matches('6', '0-5'), false);
});

test('open ranges and adult descriptions retain their upper coverage', () => {
  for (const text of ['12+', '14-adult', 'Adult', 'adult', ' Adult / older readers ']) {
    assert.equal(matches(text, 'adult'), true, text);
  }
  assert.equal(matches('12+', '9-12'), true);
  assert.equal(matches('12+', '6-8'), false);
  assert.equal(matches('11-adult', '9-12'), true);
  assert.equal(matches('Adult', '13-17'), false);
});

test('missing, grade-based, broad and malformed descriptions remain unspecified', () => {
  for (const text of [null, undefined, '', 'grades 5-7', 'Young adult', 'Children', 'Young readers', 'Leo Politi', '12-8', 8]) {
    assert.equal(range(text), null, String(text));
    assert.equal(matches(text, 'unknown'), true, String(text));
    assert.equal(matches(text, '9-12'), false, String(text));
    assert.equal(matches(text, ''), true, String(text));
  }
  assert.equal(matches('8-12', 'unknown'), false);
});

test('every catalog reading is available through all ages and at least one group', () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(root, 'data/catalog.json'), 'utf8'));
  const books = JSON.parse(fs.readFileSync(path.join(root, 'data/books.json'), 'utf8'));
  for (const book of books) {
    const value = catalog.books[book.work]?.reading_age;
    assert.equal(matches(value, ''), true, book.title);
    assert.equal(groups.some(({ key }) => matches(value, key)), true, book.title);
  }
});
