#!/usr/bin/env python3
"""Generates module manifests and registry.json for the Hermes/Jeeves module repo.

Scripts are authored as plain Python strings here so JSON escaping is handled
by the encoder rather than by hand — hand-escaped JavaScript inside JSON was
the source of every malformed manifest in this repo's history.

Each registry entry carries the SHA-256 of the manifest it points at. A module's
JavaScript lives inside its manifest, so an unpinned manifest URL means the code
a user approved can be swapped for different code afterwards. The app refuses to
install a manifest whose bytes do not match this digest, so ALWAYS regenerate
with this script rather than hand-editing a manifest — an edited manifest with a
stale digest is rejected on every device.
"""

import hashlib
import json
import os

REPO = "https://raw.githubusercontent.com/l3ad3r1/hermes-jeeves-modules/main"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(ROOT, "modules")

WORD_COUNT_JS = """
hermes.registerTool('word_count', function (args) {
  var text = String(args.text || '');
  if (!text) { return 'No text provided.'; }
  var words = text.split(/\\s+/).filter(function (w) { return w.length > 0; });
  var sentences = text.split(/[.!?]+/).filter(function (s) { return s.trim().length > 0; });
  var minutes = Math.max(1, Math.round(words.length / 200));
  return 'Words: ' + words.length +
    '\\nCharacters: ' + text.length +
    '\\nCharacters (no spaces): ' + text.replace(/\\s/g, '').length +
    '\\nSentences: ' + sentences.length +
    '\\nReading time: about ' + minutes + ' min';
});
"""

TEXT_TOOLS_JS = """
function toTitleCase(s) {
  return s.replace(/\\w\\S*/g, function (t) {
    return t.charAt(0).toUpperCase() + t.substr(1).toLowerCase();
  });
}

hermes.registerTool('text_transform', function (args) {
  var text = String(args.text || '');
  var op = String(args.operation || '').toLowerCase();
  if (!text) { return 'No text provided.'; }
  switch (op) {
    case 'upper': return text.toUpperCase();
    case 'lower': return text.toLowerCase();
    case 'title': return toTitleCase(text);
    case 'reverse': return text.split('').reverse().join('');
    case 'slug':
      return text.toLowerCase().trim()
        .replace(/[^a-z0-9\\s-]/g, '')
        .replace(/[\\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
    case 'strip':
      return text.replace(/\\s+/g, ' ').trim();
    default:
      return 'Unknown operation "' + op + '". Use one of: upper, lower, title, reverse, slug, strip.';
  }
});
"""

UNIT_CONVERT_JS = """
var UNITS = {
  km: 1000, m: 1, cm: 0.01, mm: 0.001, mi: 1609.344, ft: 0.3048, in: 0.0254, yd: 0.9144
};
var MASS = { kg: 1, g: 0.001, mg: 0.000001, lb: 0.45359237, oz: 0.028349523125 };

hermes.registerTool('unit_convert', function (args) {
  var value = parseFloat(args.value);
  var from = String(args.from || '').toLowerCase();
  var to = String(args.to || '').toLowerCase();
  if (isNaN(value)) { return 'Provide a numeric value.'; }

  if (from === 'c' && to === 'f') { return (value * 9 / 5 + 32).toFixed(2) + ' F'; }
  if (from === 'f' && to === 'c') { return ((value - 32) * 5 / 9).toFixed(2) + ' C'; }

  var table = null;
  if (UNITS[from] && UNITS[to]) { table = UNITS; }
  else if (MASS[from] && MASS[to]) { table = MASS; }
  if (!table) {
    return 'Cannot convert ' + from + ' to ' + to +
      '. Supported: length (km, m, cm, mm, mi, ft, in, yd), mass (kg, g, mg, lb, oz), temperature (c, f).';
  }
  var result = value * table[from] / table[to];
  return value + ' ' + from + ' = ' + parseFloat(result.toFixed(6)) + ' ' + to;
});
"""

DATE_MATH_JS = """
function parseDate(s) {
  var d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

hermes.registerTool('date_diff', function (args) {
  var a = parseDate(String(args.from || ''));
  var b = parseDate(String(args.to || ''));
  if (!a || !b) { return 'Provide two dates the parser understands, for example 2026-01-31.'; }
  var ms = Math.abs(b.getTime() - a.getTime());
  var days = Math.floor(ms / 86400000);
  var weeks = Math.floor(days / 7);
  return 'Difference: ' + days + ' days (' + weeks + ' weeks and ' + (days % 7) + ' days)' +
    '\\nHours: ' + Math.floor(ms / 3600000);
});

hermes.registerTool('date_add', function (args) {
  var base = parseDate(String(args.date || ''));
  var days = parseInt(args.days, 10);
  if (!base) { return 'Provide a date the parser understands, for example 2026-01-31.'; }
  if (isNaN(days)) { return 'Provide a whole number of days.'; }
  var out = new Date(base.getTime() + days * 86400000);
  return out.toISOString().slice(0, 10);
});
"""

JSON_FORMAT_JS = """
hermes.registerTool('json_format', function (args) {
  var text = String(args.text || '');
  if (!text) { return 'No JSON provided.'; }
  try {
    var parsed = JSON.parse(text);
    var indent = parseInt(args.indent, 10);
    if (isNaN(indent)) { indent = 2; }
    return JSON.stringify(parsed, null, indent);
  } catch (e) {
    return 'Invalid JSON: ' + e.message;
  }
});
"""

DAILY_DIGEST_JS = """
hermes.registerTool('daily_digest', function (args) {
  var todos = JSON.parse(hermes.data.read('todos', '') || '[]');
  var notes = JSON.parse(hermes.data.read('notes', '') || '[]');
  var bookmarks = JSON.parse(hermes.data.read('bookmarks', '') || '[]');
  var now = Date.now();

  var open = todos.filter(function (t) { return !t.done; });
  var overdue = open.filter(function (t) { return t.dueDateMs != null && t.dueDateMs < now; });
  var highPriority = open.filter(function (t) {
    return (t.priority === 'HIGH' || t.priority === 'CRITICAL') && (t.dueDateMs == null || t.dueDateMs >= now);
  });
  var starred = notes.filter(function (n) { return n.starred; });
  var recentBookmarks = bookmarks.slice(0, 5);

  if (open.length === 0 && starred.length === 0 && recentBookmarks.length === 0) {
    return 'Nothing notable today: no open todos, starred notes, or bookmarks.';
  }

  var lines = [];
  lines.push('Daily digest: ' + open.length + ' open todo(s), ' + overdue.length + ' overdue.');
  if (overdue.length > 0) {
    lines.push('Overdue:');
    overdue.forEach(function (t) { lines.push('  • ' + t.title); });
  }
  if (highPriority.length > 0) {
    lines.push('High priority (not overdue):');
    highPriority.forEach(function (t) { lines.push('  • ' + t.title); });
  }
  if (starred.length > 0) {
    lines.push('Starred notes:');
    starred.forEach(function (n) { lines.push('  • ' + n.title); });
  }
  if (recentBookmarks.length > 0) {
    lines.push('Recent bookmarks:');
    recentBookmarks.forEach(function (b) { lines.push('  • ' + (b.title || b.url)); });
  }
  return lines.join('\\n');
});
"""

WEATHER_JS = """
function weatherCodeText(code) {
  var map = {
    0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Depositing rime fog',
    51: 'Light drizzle', 53: 'Moderate drizzle', 55: 'Dense drizzle',
    61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
    71: 'Slight snow', 73: 'Moderate snow', 75: 'Heavy snow',
    80: 'Slight rain showers', 81: 'Moderate rain showers', 82: 'Violent rain showers',
    95: 'Thunderstorm', 96: 'Thunderstorm with slight hail', 99: 'Thunderstorm with heavy hail'
  };
  return map[code] || ('Weather code ' + code);
}

hermes.registerTool('weather', function (args) {
  var city = String(args.city || '').trim();
  if (!city) { return 'Provide a city name.'; }

  var geoUrl = 'https://geocoding-api.open-meteo.com/v1/search?count=1&name=' + encodeURIComponent(city);
  var geo;
  try { geo = JSON.parse(hermes.http.get(geoUrl)); } catch (e) { return 'Could not look up "' + city + '": bad response from the geocoder.'; }
  if (!geo.results || geo.results.length === 0) { return 'Could not find a location named "' + city + '".'; }
  var loc = geo.results[0];

  var forecastUrl = 'https://api.open-meteo.com/v1/forecast?latitude=' + loc.latitude +
    '&longitude=' + loc.longitude +
    '&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&temperature_unit=celsius';
  var wx;
  try { wx = JSON.parse(hermes.http.get(forecastUrl)); } catch (e) { return 'Could not fetch weather for ' + loc.name + '.'; }
  var cur = wx.current;
  if (!cur) { return 'No current weather data for ' + loc.name + '.'; }

  var place = loc.name + (loc.admin1 ? ', ' + loc.admin1 : '') + (loc.country ? ', ' + loc.country : '');
  return place + ': ' + weatherCodeText(cur.weather_code) + ', ' + cur.temperature_2m + '\\u00B0C, humidity ' +
    cur.relative_humidity_2m + '%, wind ' + cur.wind_speed_10m + ' km/h.';
});
"""

CURRENCY_CONVERT_JS = """
function formatNum(n) {
  var parts = Number(n).toFixed(2).split('.');
  parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
  return parts.join('.');
}

function formatAmount(n) {
  var s = String(n);
  var parts = s.split('.');
  parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
  return parts.join('.');
}

hermes.registerTool('convert_currency', function (args) {
  var amount = parseFloat(args.amount);
  if (isNaN(amount)) { return 'Provide a numeric amount.'; }
  var from = String(args.from || '').trim().toUpperCase();
  var to = String(args.to || '').trim().toUpperCase();
  if (!from || !to) { return 'Provide both source and target currency codes (e.g. USD, EUR).'; }
  if (from === to) {
    return formatAmount(amount) + ' ' + from + ' = ' + formatAmount(amount) + ' ' + to;
  }

  var url = 'https://api.frankfurter.app/latest?amount=' +
    encodeURIComponent(amount) + '&from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to);

  var resp;
  try {
    resp = hermes.http.get(url);
  } catch (e) {
    return 'Could not convert ' + formatAmount(amount) + ' ' + from + ' to ' + to + ': invalid currency code or network error.';
  }

  var data;
  try {
    data = JSON.parse(resp);
  } catch (e) {
    return 'Could not parse response from currency service.';
  }

  if (!data || !data.rates || data.rates[to] === undefined) {
    return 'No conversion rate returned for ' + to + '.';
  }

  var converted = data.rates[to];
  var dateStr = data.date ? ' (' + data.date + ' rate)' : '';
  return formatAmount(amount) + ' ' + from + ' = ' + formatNum(converted) + ' ' + to + dateStr;
});
"""

WORD_LOOKUP_JS = """
hermes.registerTool('define_word', function (args) {
  var word = String(args.word || '').trim().toLowerCase();
  if (!word) { return 'Provide a word to look up.'; }

  var url = 'https://api.dictionaryapi.dev/api/v2/entries/en/' + encodeURIComponent(word);
  var resp;
  try {
    resp = hermes.http.get(url);
  } catch (e) {
    return 'No definition found for "' + word + '".';
  }

  var data;
  try {
    data = JSON.parse(resp);
  } catch (e) {
    return 'No definition found for "' + word + '".';
  }

  if (!data || !data.length) {
    return 'No definition found for "' + word + '".';
  }

  var entry = data[0];
  var phonetic = entry.phonetic || '';
  if (!phonetic && entry.phonetics && entry.phonetics.length) {
    for (var p = 0; p < entry.phonetics.length; p++) {
      if (entry.phonetics[p] && entry.phonetics[p].text) {
        phonetic = entry.phonetics[p].text;
        break;
      }
    }
  }

  var lines = [];
  var header = entry.word || word;
  if (phonetic) { header += ' (' + phonetic + ')'; }
  lines.push(header + ':');

  var count = 0;
  if (entry.meanings && entry.meanings.length) {
    for (var m = 0; m < entry.meanings.length && count < 2; m++) {
      var meaning = entry.meanings[m];
      var pos = meaning.partOfSpeech ? '[' + meaning.partOfSpeech + '] ' : '';
      var defs = meaning.definitions || [];
      for (var d = 0; d < defs.length && count < 2; d++) {
        var defText = defs[d] && defs[d].definition ? defs[d].definition.trim() : '';
        if (defText) {
          count++;
          lines.push(count + '. ' + pos + defText);
        }
      }
    }
  }

  if (count === 0) {
    return 'No definition found for "' + word + '".';
  }

  return lines.join('\\n');
});
"""

TAG_EXPLORER_JS = """
function hasTag(tags, target) {
  if (!tags || !tags.length) { return false; }
  for (var i = 0; i < tags.length; i++) {
    if (String(tags[i] || '').trim().toLowerCase() === target) {
      return true;
    }
  }
  return false;
}

hermes.registerTool('tag_report', function (args) {
  var notes = JSON.parse(hermes.data.read('notes', '') || '[]');
  var todos = JSON.parse(hermes.data.read('todos', '') || '[]');
  var bookmarks = JSON.parse(hermes.data.read('bookmarks', '') || '[]');

  var filterTag = args && args.tag ? String(args.tag).trim().toLowerCase() : '';

  if (filterTag) {
    var matches = [];
    var i;
    for (i = 0; i < notes.length; i++) {
      var n = notes[i];
      if (hasTag(n.tags, filterTag)) {
        matches.push('  • [Note] ' + (n.title || 'Untitled'));
      }
    }
    for (i = 0; i < todos.length; i++) {
      var t = todos[i];
      if (hasTag(t.tags, filterTag)) {
        var status = t.done ? 'done' : 'open';
        matches.push('  • [Todo] ' + (t.title || 'Untitled') + ' (' + status + ')');
      }
    }
    for (i = 0; i < bookmarks.length; i++) {
      var b = bookmarks[i];
      if (hasTag(b.tags, filterTag)) {
        matches.push('  • [Bookmark] ' + (b.title || b.url || 'Untitled'));
      }
    }

    if (matches.length === 0) {
      return 'No items found tagged with "' + filterTag + '" (checked up to 25 recent items per collection).';
    }

    return 'Items tagged "' + filterTag + '" (' + matches.length + ' found across recent notes, todos, bookmarks):\\n' +
      matches.join('\\n');
  }

  var counts = {};
  function tally(items, type) {
    for (var i = 0; i < items.length; i++) {
      var tags = items[i].tags;
      if (tags && tags.length) {
        for (var j = 0; j < tags.length; j++) {
          var raw = String(tags[j] || '').trim().toLowerCase();
          if (raw) {
            if (!counts[raw]) {
              counts[raw] = { total: 0, notes: 0, todos: 0, bookmarks: 0 };
            }
            counts[raw].total++;
            counts[raw][type]++;
          }
        }
      }
    }
  }

  tally(notes, 'notes');
  tally(todos, 'todos');
  tally(bookmarks, 'bookmarks');

  var tagNames = [];
  for (var k in counts) {
    if (Object.prototype.hasOwnProperty.call(counts, k)) {
      tagNames.push(k);
    }
  }

  if (tagNames.length === 0) {
    return 'No tagged items found across recent notes, todos, or bookmarks (checked up to 25 items each).';
  }

  tagNames.sort(function (a, b) {
    return counts[b].total - counts[a].total;
  });

  var lines = [];
  lines.push('Tag summary across recent collections (capped at 25 items each):');
  for (var idx = 0; idx < tagNames.length; idx++) {
    var name = tagNames[idx];
    var c = counts[name];
    var breakdown = [];
    if (c.notes > 0) { breakdown.push(c.notes + ' note' + (c.notes === 1 ? '' : 's')); }
    if (c.todos > 0) { breakdown.push(c.todos + ' todo' + (c.todos === 1 ? '' : 's')); }
    if (c.bookmarks > 0) { breakdown.push(c.bookmarks + ' bookmark' + (c.bookmarks === 1 ? '' : 's')); }
    lines.push('  • ' + name + ': ' + c.total + ' item' + (c.total === 1 ? '' : 's') + ' (' + breakdown.join(', ') + ')');
  }

  return lines.join('\\n');
});
"""

MODULES = [
    {
        "id": "word-count",
        "name": "Word Count",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Counts words, characters, and sentences, and estimates reading time.",
        "type": "tool",
        "permissions": [],
        "tools": [
            {
                "name": "word_count",
                "description": "Count words, characters and sentences in text and estimate reading time. Use when asked how long a piece of text is.",
                "category": "productivity",
                "parameters": [
                    {"name": "text", "type": "STRING", "description": "The text to analyse", "required": True},
                ],
            },
        ],
        "main": WORD_COUNT_JS,
    },
    {
        "id": "text-tools",
        "name": "Text Tools",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Changes text case and makes URL slugs.",
        "type": "tool",
        "permissions": [],
        "tools": [
            {
                "name": "text_transform",
                "description": "Transform text: upper, lower, title case, reverse, URL slug, or strip extra whitespace.",
                "category": "productivity",
                "parameters": [
                    {"name": "text", "type": "STRING", "description": "The text to transform", "required": True},
                    {
                        "name": "operation",
                        "type": "STRING",
                        "description": "One of: upper, lower, title, reverse, slug, strip",
                        "required": True,
                        "enumValues": ["upper", "lower", "title", "reverse", "slug", "strip"],
                    },
                ],
            },
        ],
        "main": TEXT_TOOLS_JS,
    },
    {
        "id": "unit-convert",
        "name": "Unit Converter",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Converts length, mass, and temperature units.",
        "type": "tool",
        "permissions": [],
        "tools": [
            {
                "name": "unit_convert",
                "description": "Convert between units of length (km, m, cm, mm, mi, ft, in, yd), mass (kg, g, mg, lb, oz), or temperature (c, f).",
                "category": "information",
                "parameters": [
                    {"name": "value", "type": "NUMBER", "description": "The numeric value to convert", "required": True},
                    {"name": "from", "type": "STRING", "description": "Unit to convert from", "required": True},
                    {"name": "to", "type": "STRING", "description": "Unit to convert to", "required": True},
                ],
            },
        ],
        "main": UNIT_CONVERT_JS,
    },
    {
        "id": "date-math",
        "name": "Date Math",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Works out the gap between two dates, or shifts a date by days.",
        "type": "tool",
        "permissions": [],
        "tools": [
            {
                "name": "date_diff",
                "description": "Calculate the number of days, weeks and hours between two dates.",
                "category": "productivity",
                "parameters": [
                    {"name": "from", "type": "STRING", "description": "Start date, e.g. 2026-01-31", "required": True},
                    {"name": "to", "type": "STRING", "description": "End date, e.g. 2026-03-15", "required": True},
                ],
            },
            {
                "name": "date_add",
                "description": "Add (or subtract, with a negative number) a number of days to a date.",
                "category": "productivity",
                "parameters": [
                    {"name": "date", "type": "STRING", "description": "Base date, e.g. 2026-01-31", "required": True},
                    {"name": "days", "type": "NUMBER", "description": "Days to add; negative subtracts", "required": True},
                ],
            },
        ],
        "main": DATE_MATH_JS,
    },
    {
        "id": "json-format",
        "name": "JSON Formatter",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Pretty-prints and validates JSON.",
        "type": "tool",
        "permissions": [],
        "tools": [
            {
                "name": "json_format",
                "description": "Validate and pretty-print a JSON string. Reports the parse error when the JSON is invalid.",
                "category": "productivity",
                "parameters": [
                    {"name": "text", "type": "STRING", "description": "The JSON text to format", "required": True},
                    {"name": "indent", "type": "NUMBER", "description": "Indent width, default 2", "required": False},
                ],
            },
        ],
        "main": JSON_FORMAT_JS,
    },
    {
        "id": "daily-digest",
        "name": "Daily Digest",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Summarizes overdue/high-priority todos, starred notes, and recent bookmarks into one digest.",
        "type": "tool",
        "permissions": ["data.read"],
        "tools": [
            {
                "name": "daily_digest",
                "description": "Produce a short summary of what's outstanding: overdue and high-priority todos, starred notes, and recently saved bookmarks. Use when the user asks what's on their plate, for a daily summary, or 'what am I missing'.",
                "category": "productivity",
                "parameters": [],
            },
        ],
        "main": DAILY_DIGEST_JS,
    },
    {
        "id": "weather",
        "name": "Weather",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Current weather conditions for a city, via the free open-meteo.com API.",
        "type": "tool",
        "permissions": ["network"],
        "tools": [
            {
                "name": "weather",
                "description": "Get current weather conditions (temperature, humidity, wind, sky) for a named city.",
                "category": "information",
                "parameters": [
                    {"name": "city", "type": "STRING", "description": "City name, e.g. 'Hyderabad' or 'London, UK'", "required": True},
                ],
            },
        ],
        "main": WEATHER_JS,
    },
    {
        "id": "currency-convert",
        "name": "Currency Converter",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Converts currencies using live ECB exchange rates via Frankfurter.",
        "type": "tool",
        "permissions": ["network"],
        "tools": [
            {
                "name": "convert_currency",
                "description": "Convert an amount from one currency to another using live exchange rates. Supported: 3-letter currency codes like USD, EUR, GBP, INR, JPY.",
                "category": "information",
                "parameters": [
                    {"name": "amount", "type": "NUMBER", "description": "The numeric amount to convert", "required": True},
                    {"name": "from", "type": "STRING", "description": "Source currency code, e.g. USD, EUR", "required": True},
                    {"name": "to", "type": "STRING", "description": "Target currency code, e.g. INR, GBP", "required": True},
                ],
            },
        ],
        "main": CURRENCY_CONVERT_JS,
    },
    {
        "id": "word-lookup",
        "name": "Word Lookup",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Looks up English word definitions, pronunciation, and part of speech via DictionaryAPI.",
        "type": "tool",
        "permissions": ["network"],
        "tools": [
            {
                "name": "define_word",
                "description": "Look up definitions, pronunciation, and part of speech for an English word. Use when asked for the definition or meaning of a word.",
                "category": "information",
                "parameters": [
                    {"name": "word", "type": "STRING", "description": "The word to look up", "required": True},
                ],
            },
        ],
        "main": WORD_LOOKUP_JS,
    },
    {
        "id": "tag-explorer",
        "name": "Tag Explorer",
        "version": "1.0.0",
        "author": "Hermes",
        "description": "Surveys and lists notes, todos, and bookmarks by tag across all collections.",
        "type": "tool",
        "permissions": ["data.read"],
        "tools": [
            {
                "name": "tag_report",
                "description": "Report tag counts or list items with a specific tag across notes, todos, and bookmarks (capped at 25 newest items per collection). Use when exploring tags or searching for items with a specific tag across collections.",
                "category": "productivity",
                "parameters": [
                    {"name": "tag", "type": "STRING", "description": "Optional tag name to filter by. If omitted, returns a frequency count of all tags across collections.", "required": False},
                ],
            },
        ],
        "main": TAG_EXPLORER_JS,
    },
]


def main():
    os.makedirs(MODULES_DIR, exist_ok=True)
    registry = {"schemaVersion": 1, "plugins": []}

    for module in MODULES:
        module_dir = os.path.join(MODULES_DIR, module["id"])
        os.makedirs(module_dir, exist_ok=True)
        path = os.path.join(module_dir, "manifest.json")
        payload = json.dumps(module, indent=2, ensure_ascii=False) + "\n"
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)

        # Hash the exact bytes served from raw.githubusercontent.com, which are
        # the bytes just written — the app hashes the response body the same way.
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        registry["plugins"].append(
            {
                "id": module["id"],
                "name": module["name"],
                "version": module["version"],
                "author": module["author"],
                "description": module["description"],
                "type": module["type"],
                "permissions": module["permissions"],
                "manifestUrl": "%s/modules/%s/manifest.json" % (REPO, module["id"]),
                "sha256": digest,
            }
        )

    with open(os.path.join(ROOT, "registry.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(registry, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print("Wrote %d modules and registry.json" % len(MODULES))


if __name__ == "__main__":
    main()
