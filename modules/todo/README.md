# Todo Module

Tool: **`todo`** — manage personal todos and tasks with due dates and reminders. Distinct from the Kanban board which is for project tickets.

## Actions

| Action | Description | Required params |
|--------|-------------|-----------------|
| `create` | Add a task | `title`, optional `body`, `priority`, `due_date_ms`, `reminder`, `tags` |
| `list` | View pending or all tasks | optional `limit` |
| `get` | Read a task by id | `id` |
| `complete` | Mark done | `id` |
| `uncomplete` | Re-open | `id` |
| `delete` | Remove a task | `id` |
| `search` | Find by title/body or tag | `query` or `tag`, optional `limit` |
| `set_priority` | Change priority | `id`, `priority` |
| `reschedule` | Update due date | `id`, optional `due_date_ms` |
| `overdue` | See past-due tasks | — |

- **Category:** `productivity`
- **Capabilities:** `todo`
- **Max result size:** 8 KiB

## Source files

```
src/main/kotlin/com/hermes/agent/
  domain/model/TodoTask.kt                 # Domain model + TaskPriority enum
  domain/repository/TodoRepository.kt      # Repository interface
  data/local/entity/TodoTaskEntity.kt      # Room entity ("todo_tasks" table)
  data/local/dao/TodoTaskDao.kt            # Room DAO
  data/tools/TodoTool.kt                   # Tool implementation + Hilt @Binds module
  data/repository/TodoRepositoryImpl.kt    # App-side repository implementation
  di/TodoModule.kt                         # Hilt binding for the repository
schema/migration-14-15.sql                 # Room migration 14 -> 15 (CREATE TABLE todo_tasks)
```

## Schema (Room migration 14 -> 15)

```sql
CREATE TABLE IF NOT EXISTS todo_tasks (
    id           TEXT    NOT NULL PRIMARY KEY,
    title        TEXT    NOT NULL,
    body         TEXT    NOT NULL DEFAULT '',
    done         INTEGER NOT NULL DEFAULT 0,
    priority     TEXT    NOT NULL DEFAULT 'MEDIUM',
    tagsJson     TEXT    NOT NULL DEFAULT '[]',
    dueDateMs    INTEGER,
    reminderText TEXT,
    createdAt    INTEGER NOT NULL,
    updatedAt    INTEGER NOT NULL,
    completedAt  INTEGER
);
CREATE INDEX IF NOT EXISTS index_todo_tasks_done        ON todo_tasks(done);
CREATE INDEX IF NOT EXISTS index_todo_tasks_dueDateMs ON todo_tasks(dueDateMs);
```

## Priority values

`TaskPriority`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` (stored as their enum name; unknown values fall back to `MEDIUM`).

## Integration notes

- `done` uses a `setDone` DAO query that stamps `completedAt` on first completion and `updatedAt` on every change.
- Tasks are identified by a `td_`-prefixed id (`IdGenerator`).
- This module is complementary to `KanbanTool` (`kanban`); todo is for personal tasks, kanban for project tickets. Both can coexist.
- Grant the `todo` capability to a persona via `AgentToolAccess` and mention it in the persona prompts.

## Tests

The module is exercised through the repository contract; run:

```bash
./gradlew :app:compileDebugKotlin :app:testDebugUnitTest
```
