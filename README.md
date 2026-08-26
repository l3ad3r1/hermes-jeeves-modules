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
That work is preserved for reference in [`legacy/`](legacy/README.md) but nothing in this
repo builds or ships that way anymore.

## Repository layout

```text
registry.json                    # the URL entered under Settings → Features → Modules
modules/<id>/manifest.json        # one module: manifest + its JS source, fetched by the app
tools/build_registry.py           # generates modules/*/manifest.json + registry.json
examples/                         # starter manifest.json / registry entry to copy
docs/CREATING_MODULES.md          # the how-to guide
legacy/                           # superseded native-APK-era module source (reference only)
```

## Modules in this repo

| Module | Tool(s) | What it does |
|---|---|---|
| [word-count](modules/word-count/) | `word_count` | Counts words, characters, sentences; estimates reading time |
| [text-tools](modules/text-tools/) | `text_transform` | Case conversion, reverse, URL slug, whitespace strip |
| [unit-convert](modules/unit-convert/) | `unit_convert` | Length, mass, and temperature conversion |
| [date-math](modules/date-math/) | `date_diff`, `date_add` | Gap between two dates, or shift a date by N days |
| [json-format](modules/json-format/) | `json_format` | Pretty-print/validate JSON |

All five declare `permissions: []` — each is pure computation on its own arguments. That's
deliberate, not incidental: see the permissions gap called out below.

## ⚠️ Known gap: host-backed permissions aren't wired up yet

`data.read`, `data.write`, and `network` are defined in the schema and enforced by the
sandbox (a module without the permission gets a thrown, JS-catchable error if it tries), but
neither Hermes nor Jeeves has an app-side
[`ScriptPluginHost`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginHost.kt)
implementation yet — `ScriptPluginEngine.host` stays `null` at runtime in both apps, so
`hermes.data.read`/`write` and `hermes.http.get` are currently no-ops. Until a host
implementation is added to both apps, build modules that only transform their own
arguments — that's why every module published here today needs zero permissions. Full
detail in [docs/CREATING_MODULES.md](docs/CREATING_MODULES.md) under "Current gap".

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
own arguments is the permission-gated `hermes.*` API, and today that API's host-backed calls
are unimplemented no-ops (see the gap above) — so in practice, every module currently
published here really can only transform text it's handed and return text. Treat that as the
actual current trust boundary, not the aspirational one described by the permission names.
