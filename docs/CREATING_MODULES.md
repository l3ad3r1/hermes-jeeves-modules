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

See [Permissions](#permissions) below for the exact `hermes.data.read`/`write` JSON
contract — which collections exist, what a read call returns, and what a write payload
needs.

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

| Permission | Grants | Host method |
|---|---|---|
| `data.read` | `hermes.data.read(collection, query)` | `ScriptPluginHost.readData` |
| `data.write` | `hermes.data.write(collection, payload)` | `ScriptPluginHost.writeData` |
| `network` | `hermes.http.get(url)` | `ScriptPluginHost.httpGet` |

A module with no permissions is pure computation: it can transform the arguments it's given
and return a string, and nothing else. Calling a gated API without the permission throws a
JS-catchable `IllegalStateException` inside the sandbox rather than silently failing.

All three are backed by
[`ScriptPluginHostImpl`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginHostImpl.kt)
in `agent-core`, shared identically by both apps.

### `hermes.data.read(collection, query)` — needs `data.read`

`collection` is `"notes"`, `"todos"`, or `"bookmarks"` — the same three repositories the
built-in notes/todo/bookmark tools use; there is no generic storage escape hatch beyond
these. An unknown collection throws. `query` blank lists everything (capped at 25 results,
newest-first repository order); non-blank runs that repository's own search. Returns a JSON
array as a **string** — parse it yourself with `JSON.parse`:

```js
// notes: [{id, title, content, category, starred, tags: [...]}, ...]
// todos: [{id, title, body, done, priority, dueDateMs, tags: [...]}, ...]
// bookmarks: [{id, url, title, note, tags: [...]}, ...]
var items = JSON.parse(hermes.data.read('notes', ''));
```

Long text fields (`content`, `body`, `note`) are truncated to 300 characters per item —
this is for listing/searching, not for pulling one item's full content back out.

### `hermes.data.write(collection, payload)` — needs `data.write`

`payload` is a JSON **string** (build it with `JSON.stringify`, not a raw object) with a
required `"action"` field. Returns `{"ok":true,"id":"..."}` as a string on success; an
invalid action, missing field, or record `id` that doesn't exist throws (JS-catchable).

| Collection | Actions | Notes |
|---|---|---|
| `notes` | `create` (`title` required; `content`, `tags`, `category`, `folder` optional), `update` (`id` required; any of `title`/`content`/`tags`/`starred` to change), `delete` (`id` required) | |
| `todos` | `create` (`title` required; `body`, `priority`, `dueDateMs`, `tags` optional), `complete` (`id`), `uncomplete` (`id`), `delete` (`id`) | `priority` is one of `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` (case-insensitive); unrecognized falls back to `MEDIUM` |
| `bookmarks` | `create` (`url` required; `title`, `note`, `tags` optional), `update` (`id`; any of `title`/`note`/`tags`), `delete` (`id`) | |

```js
hermes.registerTool('save_finding', function (args) {
  var result = hermes.data.write('notes', JSON.stringify({
    action: 'create',
    title: args.title,
    content: args.content,
    tags: ['from-module'],
  }));
  return 'Saved as ' + JSON.parse(result).id;
});
```

### `hermes.http.get(url)` — needs `network`

Synchronous GET through the host's own OkHttp client — a module never opens its own socket.
`url` must start with `http://` or `https://` or the call throws. Returns the response body
as a string, truncated at 32,000 characters. A non-2xx response throws.

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
