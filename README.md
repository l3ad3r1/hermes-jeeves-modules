# Hermes / Jeeves Modules

This is the public module repository for the Hermes Android app and the private Jeeves
Android app. Both products consume the same HTTPS catalog format and verify every APK's
size, SHA-256, package identity, manifest, exported service, and signing certificate
before it can be staged.

## Repository layout

```text
catalog-v1.json                 # the URL entered under Settings → Features → Modules
artifacts/<package>/<version>/  # immutable APK release artifacts
examples/                        # starter manifest and service examples
modules/<name>/                  # source trees for the featured modules (see below)
```

## Featured modules

Five in-app agent tools were generated from the productivity features ported into the Hermes
app (domain model + repository interface + Room entity/DAO + tool + Hilt binding). Each lives
under [`modules/`](modules/) with its own README, source tree, and Room migration SQL.

| Module | Tool | Capability | DB migration | README |
|--------|------|------------|--------------|--------|
| [notes](modules/notes/) | `notes` — knowledge capture, markdown notes | `notes` | 13 → 14 | [README](modules/notes/README.md) |
| [todo](modules/todo/) | `todo` — personal tasks with due dates (distinct from kanban) | `todo` | 14 → 15 | [README](modules/todo/README.md) |
| [calendar](modules/calendar/) | `calendar` — events, writes to device calendar via `CalendarEventGateway` | `calendar` | 15 → 16 | [README](modules/calendar/README.md) |
| [bookmarks](modules/bookmarks/) | `bookmarks` — save/search URLs and links | `bookmarks` | 16 → 17 | [README](modules/bookmarks/README.md) |
| [mood](modules/mood/) | `mood` — daily mood logging + insights | `mood` | 16 → 17 | [README](modules/mood/README.md) |

The `bookmarks` and `mood` modules share the single `MIGRATION_16_17` (both tables are created in
one migration). `calendar` requires `READ_CALENDAR`/`WRITE_CALENDAR` runtime permissions and a
`CalendarEventGateway` binding in the host app.

Each module must be registered in the host before it is usable: add the Room entity/DAO to
`HermesDatabase`, the migration to `DatabaseModule.addMigrations(...)`, the tool to
`di/ToolsModule`, the capability grant to `AgentToolAccess`, and mention it in the persona
prompts.

The empty [`catalog-v1.json`](catalog-v1.json) is a valid starting catalog. Do not point
the apps at a catalog until every listed artifact is available at its final HTTPS URL.
For a smoke test, paste this raw URL into either app's Modules setting:
`https://raw.githubusercontent.com/l3ad3r1/hermes-jeeves-modules/main/catalog-v1.json`.

## Create a module

1. Create an Android library or application module that exposes one plugin service. The
   service must be safe to run in a sandbox and must implement the shared protocol version
   `1`. Keep the plugin package ID stable; schema v1 requires it to equal the plugin ID.
2. Add the manifest metadata key
   `com.hermes.agent.PLUGIN_MANIFEST_V1`. Its value is the JSON-encoded manifest shown in
   [`examples/plugin-manifest-v1.json`](examples/plugin-manifest-v1.json). Declare the
   catalog `serviceClassName` as an exported service with the agreed intent contract.
3. Declare only the permissions the module needs. Every permission needs a user-facing
   rationale. Keep network and remote content handling explicit; never hide privileged
   behavior in initialization.
4. Sign the release APK with a stable publisher certificate. Compute its SHA-256
   fingerprint and place that fingerprint in the manifest. A changed signing key is a
   new publisher identity and requires a new approval.
5. Publish the APK at an immutable HTTPS URL. Do not replace bytes at an existing version
   path. Record the exact byte count and SHA-256 digest.
6. Add the entry to [`catalog-v1.json`](catalog-v1.json), including the complete manifest,
   artifact URL, digest, size, package name, service class, and protocol version.
7. Validate the catalog and test it in both products: open **Settings → Features →
   Modules**, enter the raw catalog URL, load it, and download the module. Review the
   displayed permissions and publisher identity before any future installer handoff.

## Catalog entry checklist

- `schemaVersion` is `1`.
- Plugin IDs are unique, reverse-DNS identifiers, and match Android package names.
- `versionCode` is positive and increases for every published update.
- `signatureFingerprint` and `apkSha256` are uppercase SHA-256 values.
- `apkUrl` uses HTTPS and is immutable.
- `sizeBytes` equals the final APK byte count.
- `serviceClassName` is present in the APK and exported as required by the host contract.
- Capability and tool names are unique; permission rationales are non-empty.

## Publishing

Keep APKs out of normal Git history when they are large; GitHub Releases are preferred.
After uploading an immutable APK, update the catalog and publish the catalog from the
default branch. The apps cache no trusted catalog URL, so users can choose the public
repository explicitly and private Jeeves installations can use a controlled mirror.

The full schema and verification rules are maintained in the shared core documentation:
[`PLUGIN_REPOSITORY.md`](https://github.com/l3ad3r1/agent-core/blob/main/docs/PLUGIN_REPOSITORY.md).

## Security model

An HTTPS URL and checksum protect transport integrity, not publisher trust. Hermes and
Jeeves inspect the downloaded APK and bind approval to the exact plugin ID, version,
digest, signer, and permission list. Treat catalog edits and signing keys as release
operations, review them, and never publish credentials in this repository.
