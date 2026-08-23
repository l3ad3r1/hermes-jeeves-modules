-- Room migration 14 -> 15 for the todo module.
-- Register as MIGRATION_14_15 in HermesDatabase and add to DatabaseModule's addMigrations(...).

CREATE TABLE IF NOT EXISTS todo_tasks (
    id            TEXT    NOT NULL PRIMARY KEY,
    title         TEXT    NOT NULL,
    body          TEXT    NOT NULL DEFAULT '',
    done          INTEGER NOT NULL DEFAULT 0,
    priority      TEXT    NOT NULL DEFAULT 'MEDIUM',
    tagsJson      TEXT    NOT NULL DEFAULT '[]',
    dueDateMs     INTEGER,
    reminderText  TEXT,
    createdAt     INTEGER NOT NULL,
    updatedAt     INTEGER NOT NULL,
    completedAt   INTEGER
);
CREATE INDEX IF NOT EXISTS index_todo_tasks_done        ON todo_tasks(done);
CREATE INDEX IF NOT EXISTS index_todo_tasks_dueDateMs ON todo_tasks(dueDateMs);
