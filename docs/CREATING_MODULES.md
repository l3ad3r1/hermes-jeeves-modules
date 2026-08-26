# Creating a module

A module is one `manifest.json` — plain JSON, served over HTTPS — that carries its own
JavaScript in its `main` field. There is no APK, no signing key, and no package installer.
The isolation boundary is the sandbox both apps run the script in
([`ScriptPluginEngine`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginEngine.kt),
in the shared `agent-core` repo's `:core:plugin` module), not the Android process boundary.
That's what makes a module installable on demand from a URL instead of requiring a signed
package install.

Both Hermes and Jeeves run the exact same engine and repository code
(`ScriptPluginRepository`, byte-for-byte identical in both app repos as of this writing), so
one module works unmodified in both products.

## 1. Design the tool

Decide:
- **What the model calls it and when.** `tools[].name` is the function name the LLM sees;
  `tools[].description` is the only thing that tells the model when to reach for it — write
  it like a docstring aimed at the model, not at a human reading your README.
- **Its parameters.** Each one needs `name`, `type` (`STRING`, `NUMBER`, `BOOLEAN`, or an
  enum via `enum: [...]` — an unrecognized type silently degrades to `STRING` rather than
  failing install, so get this right), `description`, and `required`.
- **Whether it touches anything beyond its own arguments.** If the answer is no — it's pure
  computation on the input the model gives it, like the five modules already in this repo
  (`date-math`, `json-format`, `text-tools`, `unit-convert`, `word-count`) — it needs zero
  `permissions`. See [Permissions](#permissions) below if it needs more.

## 2. Write the script

The script body is a plain JavaScript source string (Mozilla Rhino, interpreted mode — no
`import`/`export`, no ES6 classes are guaranteed, stick to ES5-style JS to be safe). At
load time it runs once in its own scope with one global object, `hermes`:

```js
hermes.registerTool(name, function (args) { ... });   // required — call once per tool
hermes.log(message);                                    // debug logging, always available

hermes.http.get(url);                                    // needs the "network" permission
hermes.data.read(collection, query);                      // needs "data.read"
hermes.data.write(collection, payloadJson);                // needs "data.write"
```

- `registerTool`'s callback receives one `args` object (its keys are exactly the
  `parameters` your manifest declared) and must **return a string** (or a plain
  object/array, which is JSON-stringified for you). Whatever it returns is what the model
  reads back.
- A tool your manifest declares but whose `registerTool` call never actually runs (e.g. a
  script that throws before reaching it) is silently **not** published — the host only
  offers the model tools the script actually registered, never ones just claimed in the
  manifest.
- Every module gets a fresh 5,000,000-instruction budget per load/run; a runaway or
  infinite-loop script is killed with an error rather than hanging the host.
- The sandbox has **no access to any Java/Android class** (`Context.setClassShutter`
  denies everything) — no file IO, no sockets, no reflection. The only way out is the
  `hermes.*` API above, and only for permissions you were granted.
- Escaping the JS as a Python string (see `tools/build_registry.py`) is much less
  error-prone than hand-escaping it inside JSON — a hand-typed `\n` or unescaped quote
  inside a JSON string literal is the most common way to produce a manifest that fails to
  parse.

### ⚠️ Current gap: `hermes.data.*` and `hermes.http.get` are not wired up yet

Neither app has an app-side implementation of
[`ScriptPluginHost`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginHost.kt)
yet — `ScriptPluginEngine.host` is `null` at runtime in both Hermes and Jeeves today, so
those three calls are effectively no-ops (`http.get`/`data.read` return `""`, `data.write`
returns `""`). Declaring `data.read`, `data.write`, or `network` in a manifest today gets
the permission approved and granted, but the call itself does nothing useful until a host
implementation lands in both apps. **Until then, only build modules that are pure
computation on their own arguments** (no permissions needed) — that's why every module
currently in this repo declares `permissions: []`.

## 3. Write the manifest

Copy [`examples/manifest-example.json`](../examples/manifest-example.json). Fields:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique, stable. Used as the primary key in the host's `script_plugins` table — changing it later is a new install, not an update. |
| `name` | yes | Shown in the Modules list and the install prompt. |
| `version` | yes | Free-form string (e.g. semver). Not currently compared on reinstall — reinstalling the same `id` overwrites the stored entity regardless of version. |
| `author` | no | Shown in the install prompt. |
| `description` | no | Shown in the browse list. |
| `type` | yes | Must be `"tool"` — the only type the current schema supports. |
| `minAppVersion` | no | Host `versionCode` required; `0` means "any". Declared but **not currently enforced** by either app. |
| `permissions` | yes (may be empty) | Any of `data.read`, `data.write`, `network` — see [Permissions](#permissions). |
| `tools` | yes, non-empty | Array of tool specs (name/description/category/parameters/requiresConfirmation) — see step 1. |
| `main` | yes | The JS source from step 2. |

Validation the host repository runs before ever installing a manifest (in
`ScriptPluginRepository.validate`): `id` non-blank, `type == "tool"`, `main` non-blank,
`tools` non-empty, and every tool has a non-blank `name`. A manifest that fails any of these
is rejected outright, before the install prompt is even shown.

## 4. Add it to the registry

`registry.json` at the repo root is the file both apps fetch by default
(`ScriptPluginRepository.DEFAULT_REGISTRY_URL`, pre-filled in Settings → Features →
Modules). It's an index only — one entry per module pointing at that module's
`manifestUrl` — not the manifest itself:

```json
{
  "schemaVersion": 1,
  "plugins": [
    { "id": "...", "name": "...", "version": "...", "author": "...",
      "description": "...", "type": "tool", "permissions": [],
      "manifestUrl": "https://raw.githubusercontent.com/l3ad3r1/hermes-jeeves-modules/main/modules/<id>/manifest.json" }
  ]
}
```

The easiest path — and the one every module in this repo was built with — is to add your
module to the `MODULES` list in [`tools/build_registry.py`](../tools/build_registry.py)
(script body as a plain Python string, so JSON-escaping is handled by `json.dump`, not by
hand) and run:

```bash
python tools/build_registry.py
```

This writes `modules/<id>/manifest.json` and regenerates `registry.json` from scratch for
every module in the script. Review the diff before committing — it rewrites the whole file.

If you'd rather hand-author a manifest directly instead of adding it to the Python script,
that's fine too: create `modules/<id>/manifest.json` yourself and add the matching entry to
`registry.json` by hand, matching [`examples/registry-entry-example.json`](../examples/registry-entry-example.json).

## 5. Test it in Hermes and/or Jeeves

1. Push the branch (or work on `main` if you're confident) so the raw GitHub URL resolves.
2. In the app: **Settings → Features → Modules**. The registry URL field is pre-filled with
   this repo's `registry.json` — tap load.
3. Find your module in the browse list, tap install. You'll see the install/permission
   prompt built from your manifest's `permissions` — confirm it.
4. The module is persisted to Room (`script_plugins` table, DB version 18 in both apps) and
   the engine reloads immediately — no restart needed. Ask the assistant something that
   should trigger your tool and confirm it answers using your tool's output.
5. Toggle it off/on and uninstall from the same screen to confirm those paths work too —
   `setEnabled`/`uninstall` both call `reloadEnabled()`, which unregisters the tool from the
   agent's `ToolRegistry` immediately rather than waiting for a restart.

## Permissions

| Permission | Grants | Host method | Status |
|---|---|---|---|
| `data.read` | `hermes.data.read(collection, query)` | `ScriptPluginHost.readData` | not yet implemented in-app (returns `""`) |
| `data.write` | `hermes.data.write(collection, payload)` | `ScriptPluginHost.writeData` | not yet implemented in-app (returns `""`) |
| `network` | `hermes.http.get(url)` | `ScriptPluginHost.httpGet` | not yet implemented in-app (returns `""`) |

A module with no permissions is pure computation: it can transform the arguments it's given
and return a string, and nothing else. Calling a gated API without the permission throws a
JS-catchable `IllegalStateException` inside the sandbox rather than silently failing.

## Design constraints worth internalizing

- **No shared state between modules.** Each module gets its own Rhino scope; there is no
  module-to-module call path.
- **A module's failure is isolated.** If your script throws at load time, that module is
  skipped and reported — it does not stop other modules from loading or crash the host.
- **The manifest's tool list is the source of truth for the model**, not the running
  script — the schema shown to the LLM comes from `tools[]` before any JS executes, so a
  script can't misrepresent itself into new capabilities after a user has approved a fixed
  permission set.
- **Reinstalling replaces the granted-permission snapshot.** Permissions are re-approved
  and re-persisted on every install, not merged with a previous grant.
