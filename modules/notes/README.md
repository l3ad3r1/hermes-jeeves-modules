# Notes Module

Tool: **`notes`** — read, write, and search structured markdown notes for knowledge capture, meeting summaries, and research.

## Actions

| Action | Description | Required params |
|--------|-------------|-----------------|
| `create` | Store a note | `title`, optional `content`, `tags`, `category`, `folder` |
| `list` | View all notes or filter by category | optional `category`, `limit` |
| `get` | Read a note by id | `id` |
| `search` | Keyword search across titles and content | `query`, optional `limit` |
| `update` | Edit title/content/tags/starred | `id` |
| `toggle_star` | Mark/unmark as favorite | `id` |
| `delete` | Remove a note | `id` |

- **Category:** `productivity`
- **Capabilities:** `notes`
- **Max result size:** 8 KiB

## Source files

```
src/main/kotlin/com/hermes/agent/
  domain/model/Note.kt                     # Domain model
  domain/repository/NotesRepository.kt     # Repository interface
  data/local/entity/NoteEntity.kt          # Room entity ("notes" table)
  data/local/dao/NoteDao.kt                # Room DAO
  data/tools/NotesTool.kt                  # Tool implementation + Hilt @Binds module
  data/repository/NotesRepositoryImpl.kt   # App-side repository implementation
  di/NotesModule.kt                        # Hilt binding for the repository
schema/migration-13-14.sql                 # Room migration 13 -> 14 (CREATE TABLE notes)
```

## Schema (Room migration 13 -> 14)

```sql
CREATE TABLE IF NOT EXISTS notes (
    id         TEXT    NOT NULL PRIMARY KEY,
    title      TEXT    NOT NULL,
    content    TEXT    NOT NULL DEFAULT '',
    tagsJson   TEXT    NOT NULL DEFAULT '[]',
    category   TEXT    NOT NULL DEFAULT 'general',
    isStarred  INTEGER NOT NULL DEFAULT 0,
    folder     TEXT,
    createdAt  INTEGER NOT NULL,
    updatedAt  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_notes_category   ON notes(category);
CREATE INDEX IF NOT EXISTS index_notes_updatedAt  ON notes(updatedAt);
```

## Integration notes

- Migration column names intentionally match the Room entity field names (`createdAt`, `updatedAt`, and so on); changing their casing breaks upgrade validation.
- Notes are identified by a `n_`-prefixed id (`IdGenerator`).
- Grant the `notes` capability to a persona via `AgentToolAccess` (e.g. `PRODUCTIVITY`, `RESEARCH`, `CONVERSATIONAL`) and mention it in the persona prompts.

## Tests

The module is exercised through the repository contract; run:

```bash
./gradlew :app:compileDebugKotlin :app:testDebugUnitTest
```
