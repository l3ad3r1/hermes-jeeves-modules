#!/usr/bin/env node
/**
 * Smoke test suite for Hermes / Jeeves script modules.
 * Executes each module's JavaScript inside a Node vm context with a mocked `hermes` object,
 * verifying happy paths, edge cases, and error handling.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.dirname(__dirname);

function loadModule(moduleId) {
  const manifestPath = path.join(ROOT, 'modules', moduleId, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  return manifest;
}

function runScript(jsCode, hermesMock) {
  const tools = {};
  const mock = {
    registerTool: (name, fn) => {
      tools[name] = fn;
    },
    log: () => {},
    ...hermesMock,
  };
  const context = vm.createContext({
    hermes: mock,
    console: console,
    Date: Date,
    Math: Math,
    String: String,
    Number: Number,
    parseFloat: parseFloat,
    parseInt: parseInt,
    isNaN: isNaN,
    JSON: JSON,
    encodeURIComponent: encodeURIComponent,
  });
  vm.runInContext(jsCode, context);
  return tools;
}

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
    failed++;
  }
}

console.log('Testing Currency Converter Module (currency-convert)...');
{
  const manifest = loadModule('currency-convert');
  assert.strictEqual(manifest.id, 'currency-convert');
  assert.deepStrictEqual(manifest.permissions, ['network']);

  let httpCallUrl = null;
  let httpResponse = JSON.stringify({
    amount: 100,
    base: 'USD',
    date: '2026-09-04',
    rates: { INR: 8432.10 },
  });

  const tools = runScript(manifest.main, {
    http: {
      get: (url) => {
        httpCallUrl = url;
        if (httpResponse instanceof Error) throw httpResponse;
        return httpResponse;
      },
    },
  });

  test('Tool convert_currency is registered', () => {
    assert.strictEqual(typeof tools.convert_currency, 'function');
  });

  test('Happy path: converts 100 USD to INR', () => {
    httpResponse = JSON.stringify({
      amount: 100,
      base: 'USD',
      date: '2026-09-04',
      rates: { INR: 8432.10 },
    });
    const result = tools.convert_currency({ amount: 100, from: 'USD', to: 'INR' });
    assert.ok(result.includes('100 USD = 8,432.10 INR'));
    assert.ok(result.includes('(2026-09-04 rate)'));
    assert.ok(httpCallUrl.includes('from=USD'));
    assert.ok(httpCallUrl.includes('to=INR'));
  });

  test('Same currency returns immediately without network request', () => {
    httpCallUrl = null;
    const result = tools.convert_currency({ amount: 50, from: 'EUR', to: 'EUR' });
    assert.strictEqual(result, '50 EUR = 50 EUR');
    assert.strictEqual(httpCallUrl, null);
  });

  test('Invalid amount returns validation message', () => {
    const result = tools.convert_currency({ amount: 'invalid', from: 'USD', to: 'EUR' });
    assert.strictEqual(result, 'Provide a numeric amount.');
  });

  test('Missing currency code returns validation message', () => {
    const result = tools.convert_currency({ amount: 100, from: '', to: 'EUR' });
    assert.strictEqual(result, 'Provide both source and target currency codes (e.g. USD, EUR).');
  });

  test('Network error or non-2xx handled cleanly', () => {
    httpResponse = new Error('HTTP 404 from Frankfurter');
    const result = tools.convert_currency({ amount: 100, from: 'USD', to: 'XYZ' });
    assert.ok(result.includes('Could not convert'));
    assert.ok(result.includes('invalid currency code or network error'));
  });

  test('Missing rate in response handled cleanly', () => {
    httpResponse = JSON.stringify({ amount: 100, base: 'USD', date: '2026-09-04', rates: {} });
    const result = tools.convert_currency({ amount: 100, from: 'USD', to: 'INR' });
    assert.strictEqual(result, 'No conversion rate returned for INR.');
  });
}

console.log('\nTesting Word Lookup Module (word-lookup)...');
{
  const manifest = loadModule('word-lookup');
  assert.strictEqual(manifest.id, 'word-lookup');
  assert.deepStrictEqual(manifest.permissions, ['network']);

  let httpResponse = null;
  const tools = runScript(manifest.main, {
    http: {
      get: (url) => {
        if (httpResponse instanceof Error) throw httpResponse;
        return httpResponse;
      },
    },
  });

  test('Tool define_word is registered', () => {
    assert.strictEqual(typeof tools.define_word, 'function');
  });

  test('Happy path: word with phonetic and definitions', () => {
    httpResponse = JSON.stringify([
      {
        word: 'serendipity',
        phonetic: '/ˌsɛrənˈdɪpɪti/',
        meanings: [
          {
            partOfSpeech: 'noun',
            definitions: [
              { definition: 'The faculty of making fortunate discoveries by accident.' },
              { definition: 'Good fortune; luck.' },
            ],
          },
        ],
      },
    ]);
    const result = tools.define_word({ word: 'serendipity' });
    assert.ok(result.includes('serendipity (/ˌsɛrənˈdɪpɪti/):'));
    assert.ok(result.includes('1. [noun] The faculty of making fortunate discoveries by accident.'));
    assert.ok(result.includes('2. [noun] Good fortune; luck.'));
  });

  test('Extracts phonetic from phonetics array if top-level phonetic is missing', () => {
    httpResponse = JSON.stringify([
      {
        word: 'test',
        phonetic: '',
        phonetics: [{ text: '/tɛst/' }],
        meanings: [
          {
            partOfSpeech: 'noun',
            definitions: [{ definition: 'A procedure intended to establish quality.' }],
          },
        ],
      },
    ]);
    const result = tools.define_word({ word: 'test' });
    assert.ok(result.includes('test (/tɛst/):'));
    assert.ok(result.includes('1. [noun] A procedure intended to establish quality.'));
  });

  test('Empty word returns validation error', () => {
    const result = tools.define_word({ word: '   ' });
    assert.strictEqual(result, 'Provide a word to look up.');
  });

  test('Unknown word (404 / HTTP error) returns clear not-found message', () => {
    httpResponse = new Error('HTTP 404 from DictionaryAPI');
    const result = tools.define_word({ word: 'nonexistentwordxyz' });
    assert.strictEqual(result, 'No definition found for "nonexistentwordxyz".');
  });

  test('Empty API array returns not-found message', () => {
    httpResponse = JSON.stringify([]);
    const result = tools.define_word({ word: 'unknown' });
    assert.strictEqual(result, 'No definition found for "unknown".');
  });
}

console.log('\nTesting Tag Explorer Module (tag-explorer)...');
{
  const manifest = loadModule('tag-explorer');
  assert.strictEqual(manifest.id, 'tag-explorer');
  assert.deepStrictEqual(manifest.permissions, ['data.read']);

  const mockNotes = [
    { id: '1', title: 'Work notes', tags: ['work', 'urgent'] },
    { id: '2', title: 'Ideas', tags: ['work'] },
    { id: '3', title: 'Recipes', tags: ['home'] },
  ];
  const mockTodos = [
    { id: 't1', title: 'Submit report', done: false, tags: ['work', 'urgent'] },
    { id: 't2', title: 'Buy milk', done: true, tags: ['home'] },
  ];
  const mockBookmarks = [
    { id: 'b1', title: 'Doc site', url: 'https://docs.example.com', tags: ['work'] },
  ];

  let currentNotes = mockNotes;
  let currentTodos = mockTodos;
  let currentBookmarks = mockBookmarks;

  const tools = runScript(manifest.main, {
    data: {
      read: (col) => {
        if (col === 'notes') return JSON.stringify(currentNotes);
        if (col === 'todos') return JSON.stringify(currentTodos);
        if (col === 'bookmarks') return JSON.stringify(currentBookmarks);
        return '[]';
      },
    },
  });

  test('Tool tag_report is registered', () => {
    assert.strictEqual(typeof tools.tag_report, 'function');
  });

  test('No tag argument produces frequency summary across collections', () => {
    const result = tools.tag_report({});
    assert.ok(result.includes('Tag summary across recent collections'));
    assert.ok(result.includes('work: 4 items (2 notes, 1 todo, 1 bookmark)'));
    assert.ok(result.includes('urgent: 2 items (1 note, 1 todo)'));
    assert.ok(result.includes('home: 2 items (1 note, 1 todo)'));
  });

  test('Specific tag argument lists matching items across collections', () => {
    const result = tools.tag_report({ tag: 'urgent' });
    assert.ok(result.includes('Items tagged "urgent"'));
    assert.ok(result.includes('• [Note] Work notes'));
    assert.ok(result.includes('• [Todo] Submit report (open)'));
    assert.ok(!result.includes('Recipes'));
  });

  test('Filtering by tag is case-insensitive', () => {
    const result = tools.tag_report({ tag: 'HOME' });
    assert.ok(result.includes('Items tagged "home"'));
    assert.ok(result.includes('• [Note] Recipes'));
    assert.ok(result.includes('• [Todo] Buy milk (done)'));
  });

  test('Searching for non-existent tag returns clear message', () => {
    const result = tools.tag_report({ tag: 'travel' });
    assert.ok(result.includes('No items found tagged with "travel"'));
  });

  test('Empty collections return empty summary message', () => {
    currentNotes = [];
    currentTodos = [];
    currentBookmarks = [];
    const result = tools.tag_report({});
    assert.ok(result.includes('No tagged items found across recent notes, todos, or bookmarks'));
  });
}

console.log(`\nResults: ${passed} passed, ${failed} failed.`);
if (failed > 0) {
  process.exit(1);
} else {
  console.log('All module smoke tests passed successfully!');
}
