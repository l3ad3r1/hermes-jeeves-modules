-- Room migration 15 -> 16 for the calendar module.
-- Register as MIGRATION_15_16 in HermesDatabase and add to DatabaseModule's addMigrations(...).

CREATE TABLE IF NOT EXISTS calendar_events (
    id               TEXT    NOT NULL PRIMARY KEY,
    title            TEXT    NOT NULL,
    description      TEXT    NOT NULL DEFAULT '',
    sourceCalendar   TEXT    NOT NULL DEFAULT 'default',
    startMs          INTEGER NOT NULL,
    endMs            INTEGER NOT NULL,
    allDay           INTEGER NOT NULL DEFAULT 0,
    location         TEXT,
    reminderMinutes  INTEGER NOT NULL DEFAULT 0,
    createdAt        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_calendar_events_startMs ON calendar_events(startMs);
