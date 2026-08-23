# Calendar Module

Tool: **`calendar`** — read, write, and manage calendar events. Use for scheduling, checking availability, and responding to "what's on my schedule" queries. `create` writes both to the local Room store and to the device calendar via the `CalendarEventGateway` platform boundary.

## Actions

| Action | Description | Required params |
|--------|-------------|-----------------|
| `list` / `upcoming` | View next N upcoming events | optional `limit` (default 10) |
| `get` | Read an event by id | `id` |
| `create` | Add to local store + device calendar | `title`, `start_ms`, optional `end_ms`, `description`, `all_day`, `location`, `source_calendar`, `reminder_minutes` |
| `update` | Edit a local event | `id`, optional `title`, `description`, `start_ms`, `end_ms`, `all_day`, `location` |
| `delete` | Remove an event | `id` |
| `range` | Events between two dates | `start_date_ms`, `end_date_ms` |

- **Category:** `productivity`
- **Capabilities:** `calendar`
- **Max result size:** 8 KiB

## Source files

```
src/main/kotlin/com/hermes/agent/
  domain/model/CalendarEvent.kt              # Domain model
  domain/repository/CalendarRepository.kt    # Repository interface
  domain/calendar/CalendarEventGateway.kt    # Platform boundary (CalendarEventRequest, CreatedCalendarEvent)
  data/local/entity/CalendarEventEntity.kt   # Room entity ("calendar_events" table)
  data/local/dao/CalendarEventDao.kt         # Room DAO
  data/tools/CalendarTool.kt                 # Tool implementation + Hilt @Binds module
  data/repository/CalendarRepositoryImpl.kt  # App-side repository implementation
  di/CalendarModule.kt                       # Hilt binding for the repository
  data/calendar/AndroidCalendarEventGateway.kt  # Device-calendar implementation (ContentResolver)
schema/migration-15-16.sql                   # Room migration 15 -> 16 (CREATE TABLE calendar_events)
test/.../CalendarToolTest.kt                 # Unit tests (fake repo + fake gateway)
```

## Schema (Room migration 15 -> 16)

```sql
CREATE TABLE IF NOT EXISTS calendar_events (
    id                TEXT    NOT NULL PRIMARY KEY,
    title             TEXT    NOT NULL,
    description       TEXT    NOT NULL DEFAULT '',
    sourceCalendar    TEXT    NOT NULL DEFAULT 'default',
    startMs           INTEGER NOT NULL,
    endMs             INTEGER NOT NULL,
    allDay            INTEGER NOT NULL DEFAULT 0,
    location          TEXT,
    reminderMinutes   INTEGER NOT NULL DEFAULT 0,
    createdAt         INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_calendar_events_startMs ON calendar_events(startMs);
```

## Device calendar integration

`CalendarTool.handleCreate` persists locally first, then calls `CalendarEventGateway.createEvent(...)` with the resolved `Instant` start/end and the system timezone. Gateway failures are **non-fatal**: the local event still succeeds and the tool reports `device calendar write failed: <reason>`.

`AndroidCalendarEventGateway` (app module) requires both `READ_CALENDAR` and `WRITE_CALENDAR` runtime permissions and picks the first visible calendar with `CAL_ACCESS_CONTRIBUTOR` access, preferring the primary one. Declare the permissions and request them at runtime; add the Android `permissions` entries to the module manifest with a user-facing rationale.

## Integration notes

- The `calendar` capability is intentionally excluded from the `CONVERSATIONAL` role's tool set in `AgentToolAccess` (pre-existing exclusion); grant it to `PRODUCTIVITY`/`RESEARCH`/`DEVICE_CONTROL` as desired.
- Events are identified by a `ce_`-prefixed id (`IdGenerator`).
- Hilt must provide a `CalendarEventGateway` binding; `AndroidCalendarEventGateway` is bound as a `@Singleton` in the app.

## Tests

```bash
./gradlew :core:tools:testDebugUnitTest   # CalendarToolTest (gateway success, gateway failure fallback, upcoming, missing action)
./gradlew :app:compileDebugKotlin
```
