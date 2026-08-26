# Bookmarks Module

Tool: **`bookmarks`** — save, organize, and retrieve URLs and links. Use when the user asks to "save this link", "find a bookmark", or wants to look up research references.

## Actions

| Action | Description | Required params |
|--------|-------------|-----------------|
| `save` | Store a URL | `url`, optional `title`, `note`, `tags` |
| `list` | View all bookmarks | optional `limit` |
| `get` | Read a bookmark by id | `id` |
| `search` | Find by title/url/note or tag | `query` or `tag`, optional `limit` |
| `delete` | Remove a bookmark | `id` |
| `update` | Edit title/note/tags | `id` |

- **Category:** `productivity`
- **Capabilities:** `bookmarks`
- **Max result size:** 8 KiB

## Source files

```
src/main/kotlin/com/hermes/agent/
  domain/model/Bookmark.kt                 # Domain model
  domain/repository/BookmarkRepository.kt  # Repository interface
  data/local/entity/BookmarkEntity.kt      # Room entity ("bookmarks" table)
  data/local/dao/BookmarkDao.kt            # Room DAO
  data/tools/BookmarkTool.kt               # Tool implementation + Hilt @Binds module
  data/repository/BookmarkRepositoryImpl.kt # App-side repository implementation
  di/BookmarkModule.kt                     # Hilt binding for the repository
schema/migration-16-17.sql                 # Room migration 16 -> 17 (CREATE TABLE bookmarks)
```

## Schema (Room migration 16 -> 17)

```sql
CREATE TABLE IF NOT EXISTS bookmarks (
    id         TEXT    NOT NULL PRIMARY KEY,
    url        TEXT    NOT NULL,
    title      TEXT    NOT NULL DEFAULT '',
    note       TEXT    NOT NULL DEFAULT '',
    tagsJson   TEXT    NOT NULL DEFAULT '[]',
    createdAt  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_bookmarks_url ON bookmarks(url);
```

> Migration 16 -> 17 also creates the `mood_entries` table; both modules share that migration.

## Integration notes

- `tagsJson` is serialized with kotlinx.serialization; the DAO's tag filter matches the JSON array syntax with a `LIKE` clause.
- Bookmarks are identified by a `bm_`-prefixed id (`IdGenerator`).
- Grant the `bookmarks` capability to a persona via `AgentToolAccess` and mention it in the persona prompts.

## Tests

The module is exercised through the repository contract; run:

```bash
./gradlew :app:compileDebugKotlin :app:testDebugUnitTest
```
