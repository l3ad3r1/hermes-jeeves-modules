-- Room migration 13 -> 14 for the notes module.
-- Register as MIGRATION_13_14 in HermesDatabase and add to DatabaseModule's addMigrations(...).

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
