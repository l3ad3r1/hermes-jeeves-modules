# Hermes / Jeeves Modules

This is the public module repository for the Hermes Android app and the private Jeeves
Android app. Both products fetch the same `registry.json` and run installed modules'
JavaScript in an in-process sandbox — there is no APK, no signing key, and no package
installer involved.

**For the step-by-step guide to building and shipping a new module, see
[docs/CREATING_MODULES.md](docs/CREATING_MODULES.md).** This file covers the repo layout
and the architecture; that one walks through designing, writing, and registering a module.

## How this works

A module is:
1. One `manifest.json`, served over HTTPS, with a `main` field holding the module's
   JavaScript source and a `tools[]` array describing the tool(s) it exposes to the model.
2. One entry in `registry.json`, the index both apps browse, pointing at that manifest's URL.

When a user installs a module in-app (Settings → Features → Modules), the host:
- fetches and validates the manifest (`ScriptPluginRepository.fetchManifest`/`validate`),
- shows the declared `permissions` for approval,
- persists it to Room (`script_plugins` table, DB version **18**, identical schema in both
  apps),
- and hands the granted set to
  [`ScriptPluginEngine`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginEngine.kt) —
  a Mozilla Rhino sandbox running in interpreted mode with all Java class access denied and
  a per-load instruction budget — which runs the script and registers whatever tools it
  calls `hermes.registerTool(...)` on, so the model sees them exactly like built-in tools.

This design (ported from the JS scripting system already running in production in Octo
Jotter) replaced an earlier native-APK module design — one signed installable package per
module, verified by SHA-256/signer fingerprint and handed to the Android package installer.
That earlier design's source is gone from this repo (nothing in it built or shipped under
the current architecture); it's still recoverable from git history before commit `6726805`
if it's ever needed as reference.

## Repository layout

```text
registry.json                    # the URL entered under Settings → Features → Modules
modules/<id>/manifest.json        # one module: manifest + its JS source, fetched by the app
tools/build_registry.py           # generates modules/*/manifest.json + registry.json
examples/                         # starter manifest.json / registry entry to copy
docs/CREATING_MODULES.md          # the how-to guide
```

## Modules in this repo

| Module | Tool(s) | What it does |
|---|---|---|
| [word-count](modules/word-count/) | `word_count` | Counts words, characters, sentences; estimates reading time |
| [text-tools](modules/text-tools/) | `text_transform` | Case conversion, reverse, URL slug, whitespace strip |
| [unit-convert](modules/unit-convert/) | `unit_convert` | Length, mass, and temperature conversion |
| [date-math](modules/date-math/) | `date_diff`, `date_add` | Gap between two dates, or shift a date by N days |
| [json-format](modules/json-format/) | `json_format` | Pretty-print/validate JSON |

All five declare `permissions: []` — each predates the host implementation below and never
needed updating, since pure-computation modules don't need permissions anyway. Nothing stops
a new module from declaring `data.read`, `data.write`, or `network` now.

## Host-backed permissions are implemented

[`ScriptPluginHostImpl`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginHostImpl.kt)
(agent-core, shared by both apps) backs all three gated APIs:

- **`hermes.data.read(collection, query)`** / **`hermes.data.write(collection, payload)`**
  — `collection` is `"notes"`, `"todos"`, or `"bookmarks"` (the same repositories the
  built-in notes/todo/bookmark tools use). `read` returns a JSON array; `query` blank lists
  everything (capped at 25), non-blank searches. `write` takes a JSON object with an
  `"action"` field — `create`/`update`/`delete` for notes and bookmarks,
  `create`/`complete`/`uncomplete`/`delete` for todos — and returns
  `{"ok":true,"id":"..."}`. Full field-by-field contract, with examples, in
  [docs/CREATING_MODULES.md](docs/CREATING_MODULES.md#permissions).
- **`hermes.http.get(url)`** — a synchronous GET through the host's own OkHttp client (a
  module never opens its own socket), response capped at 32,000 characters so one module
  can't blow a whole turn's context budget.

No module in this repo currently uses any of these — all five are still pure computation —
but new ones can now declare `data.read`/`data.write`/`network` and expect the calls to
actually work end to end, not just be approved and silently do nothing.

## Add a module

See [docs/CREATING_MODULES.md](docs/CREATING_MODULES.md) for the full walkthrough. Short
version:

1. Design the tool's name, description, and parameters — the description is what tells the
   model when to use it.
2. Write the JS (`hermes.registerTool(name, fn)`), keeping it in `tools/build_registry.py`
   as a Python string so escaping is handled for you.
3. Run `python tools/build_registry.py` to write `modules/<id>/manifest.json` and regenerate
   `registry.json`.
4. Push, then load the registry URL in-app (Settings → Features → Modules) and install.

## Publishing

This repo is small text/JSON, so everything stays in normal Git history — publish by
pushing to `main`. The apps cache no registry URL of their own choosing beyond the default,
so a private Jeeves build can point at a different/mirrored `registry.json` if needed.

## Security model

The sandbox boundary is Rhino running in interpreted mode with `setClassShutter { false }`
(denies every Java class — no reflection, file IO, or sockets reachable) and a
5,000,000-instruction budget per load/run. A module's only way to reach anything outside its
own arguments is the permission-gated `hermes.*` API — network and the three host
collections listed above, nothing else. There is no generic filesystem or settings access,
and no cross-module communication.
