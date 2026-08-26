# Legacy: native host-ported modules

This directory holds the five modules generated back when Hermes/Jeeves modules were
**native Kotlin source trees** meant to be compiled into the host app itself (a domain
model, a `Repository` interface + implementation, a Room `Entity`/`DAO`, a `Tool`, and a
Hilt binding — plus a Room migration SQL file), distributed as signed installable APKs.

**Both products have moved on from that design.** Modules today are JavaScript running in
the in-app sandbox described in the top-level [README.md](../README.md) — see
[docs/CREATING_MODULES.md](../docs/CREATING_MODULES.md) for the current format. Nothing in
this directory is fetched, built, or referenced by the current `registry.json`, and none of
it will run as-is: it predates `ScriptPluginManifest`/`ScriptPluginEngine` entirely.

Kept for reference only:

| Module | What it was |
|--------|-------------|
| `notes/` | Markdown note capture: create/list/get/search/update/star/delete |
| `todo/` | Personal tasks with due dates |
| `calendar/` | Events, writing to the device calendar via `CalendarEventGateway` |
| `bookmarks/` | Save/search URLs |
| `mood/` | Daily mood logging + insights |

Two of these — `calendar` (device calendar write access) and anything needing background
services — are exactly the kind of capability the current sandboxed-JS engine **cannot**
do (no Android APIs are reachable from the sandbox; see the `host` gap noted in the
top-level README). If one of these is ever rebuilt, it will need a new
[`ScriptPluginHost`](https://github.com/l3ad3r1/agent-core/blob/main/core/plugin/src/main/kotlin/com/hermes/agent/data/plugin/script/ScriptPluginHost.kt)
capability rather than a native module — do not resurrect this native path.
