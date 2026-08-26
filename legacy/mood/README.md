# Mood Module

Tool: **`mood`** — log daily mood entries and receive insights about emotional patterns.

## Actions

| Action | Description | Required params |
|--------|-------------|-----------------|
| `log` | Record today's (or a given date's) mood | `mood`, optional `intensity`, `note`, `date_ms` |
| `list` | View entries | optional `limit` |
| `get` | Read an entry by id | `id` |
| `delete` | Remove an entry | `id` |
| `insights` | Trend + most frequent mood over N days | optional `days` (default 30) |
| `today` | Get today's entry (report if missing) | — |

- **Category:** `productivity`
- **Capabilities:** `mood`
- **Max result size:** 4 KiB

## Source files

```
src/main/kotlin/com/hermes/agent/
  domain/model/MoodEntry.kt                # Domain model + MoodLevel enum
  domain/repository/MoodRepository.kt      # Repository interface
  data/local/entity/MoodEntryEntity.kt     # Room entity ("mood_entries" table)
  data/local/dao/MoodEntryDao.kt           # Room DAO
  data/tools/MoodTool.kt                   # Tool implementation + Hilt @Binds module
  data/repository/MoodRepositoryImpl.kt    # App-side repository implementation
  di/MoodModule.kt                         # Hilt binding for the repository
schema/migration-16-17.sql                 # Room migration 16 -> 17 (CREATE TABLE mood_entries)
```

## Schema (Room migration 16 -> 17)

```sql
CREATE TABLE IF NOT EXISTS mood_entries (
    id         TEXT    NOT NULL PRIMARY KEY,
    dateMs     INTEGER NOT NULL,
    mood       TEXT    NOT NULL DEFAULT 'MID',
    intensity  INTEGER NOT NULL DEFAULT 5,
    note       TEXT    NOT NULL DEFAULT '',
    tagsJson   TEXT    NOT NULL DEFAULT '[]',
    createdAt  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_mood_entries_dateMs ON mood_entries(dateMs);
```

> Migration 16 -> 17 also creates the `bookmarks` table; both modules share that migration.

## Mood values

`MoodLevel`: `VERY_BAD`, `BAD`, `MID`, `GOOD`, `VERY_GOOD` (stored as their enum name; unknown values fall back to `MID`). `intensity` is 1-10, default 5.

## Integration notes

- Entries are queried by `dateMs` (day start) for `getForDate`/`today`; `MoodTool.todayStartMs()` normalizes to local midnight.
- Aggregation for `getWeeklyStats`/`getMostFrequentMood`/`getTrend` is done in the Kotlin repository layer — Room aggregate queries returning `Pair` don't compile via KSP, so `getInRange(...)` + `groupBy` is used instead.
- Mood entries are append-only in the current repository implementation; `update` is a no-op placeholder.
- Entries are identified by a `md_`-prefixed id (`IdGenerator`).
- Grant the `mood` capability to a persona via `AgentToolAccess` and mention it in the persona prompts.

## Tests

The module is exercised through the repository contract; run:

```bash
./gradlew :app:compileDebugKotlin :app:testDebugUnitTest
```
