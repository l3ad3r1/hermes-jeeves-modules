-- Room migration 16 -> 17 for the bookmarks + mood modules.
-- Register as MIGRATION_16_17 in HermesDatabase and add to DatabaseModule's addMigrations(...).
-- This migration creates BOTH the bookmarks and the mood_entries tables.

CREATE TABLE IF NOT EXISTS bookmarks (
    id         TEXT    NOT NULL PRIMARY KEY,
    url        TEXT    NOT NULL,
    title      TEXT    NOT NULL DEFAULT '',
    note       TEXT    NOT NULL DEFAULT '',
    tagsJson   TEXT    NOT NULL DEFAULT '[]',
    createdAt  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_bookmarks_url ON bookmarks(url);

CREATE TABLE IF NOT EXISTS mood_entries (
    id        TEXT    NOT NULL PRIMARY KEY,
    dateMs    INTEGER NOT NULL,
    mood      TEXT    NOT NULL DEFAULT 'MID',
    intensity INTEGER NOT NULL DEFAULT 5,
    note      TEXT    NOT NULL DEFAULT '',
    tagsJson  TEXT    NOT NULL DEFAULT '[]',
    createdAt INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS index_mood_entries_dateMs ON mood_entries(dateMs);
