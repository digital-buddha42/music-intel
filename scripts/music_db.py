#!/usr/bin/env python3
"""
music_db.py — Unified SQLite layer for all tracked artists.

Normalizes shows, setlists, songs, and venues from every source
(phish.net API, setlist.fm API, discobiscuits MCP) into one schema in
../data/music.db so gap analysis works across bands.

Not a script — imported by ingest_*.py and gap_analysis.py.
"""

import os
import re
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS artists (
    artist_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    slug      TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    city     TEXT NOT NULL DEFAULT '',
    state    TEXT NOT NULL DEFAULT '',
    country  TEXT NOT NULL DEFAULT '',
    UNIQUE(name, city, state)
);
CREATE TABLE IF NOT EXISTS shows (
    show_id    INTEGER PRIMARY KEY,
    artist_id  INTEGER NOT NULL REFERENCES artists(artist_id),
    date       TEXT NOT NULL,               -- ISO YYYY-MM-DD
    venue_id   INTEGER REFERENCES venues(venue_id),
    source     TEXT NOT NULL,               -- 'phish.net' | 'setlist.fm' | 'discobiscuits.net'
    source_key TEXT NOT NULL,               -- stable id within that source
    show_type  TEXT NOT NULL DEFAULT 'standard',  -- 'standard' | 'tractorbeam' | 'acoustic' | ...
    url        TEXT NOT NULL DEFAULT '',
    UNIQUE(artist_id, source, source_key)
);
CREATE TABLE IF NOT EXISTS songs (
    song_id         INTEGER PRIMARY KEY,
    artist_id       INTEGER NOT NULL REFERENCES artists(artist_id),
    title           TEXT NOT NULL,
    norm_title      TEXT NOT NULL,
    is_cover        INTEGER NOT NULL DEFAULT 0,
    original_artist TEXT NOT NULL DEFAULT '',
    UNIQUE(artist_id, norm_title)
);
CREATE TABLE IF NOT EXISTS performances (
    perf_id    INTEGER PRIMARY KEY,
    show_id    INTEGER NOT NULL REFERENCES shows(show_id) ON DELETE CASCADE,
    song_id    INTEGER NOT NULL REFERENCES songs(song_id),
    set_label  TEXT NOT NULL,
    position   INTEGER NOT NULL,
    transition TEXT,                        -- '>' / ',' / NULL (NULL = unknown; setlist.fm has no segue data)
    notes      TEXT NOT NULL DEFAULT '',
    UNIQUE(show_id, set_label, position)
);
CREATE INDEX IF NOT EXISTS idx_shows_artist_date ON shows(artist_id, date);
CREATE INDEX IF NOT EXISTS idx_perf_song ON performances(song_id);
"""

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def default_db_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(script_dir), "data", "music.db")


def connect(db_path=None):
    path = db_path or default_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def normalize_title(title):
    """Dedup key for song titles: lowercase, collapse whitespace, strip punctuation."""
    t = title.lower().strip()
    t = re.sub(r"[‘’']", "", t)          # apostrophes
    t = re.sub(r"[^a-z0-9 ]+", " ", t)             # everything else -> space
    t = re.sub(r"\s+", " ", t).strip()
    return t


def get_or_create_artist(conn, name, slug):
    row = conn.execute("SELECT artist_id FROM artists WHERE slug = ?", (slug,)).fetchone()
    if row:
        return row["artist_id"]
    cur = conn.execute("INSERT INTO artists(name, slug) VALUES (?, ?)", (name, slug))
    return cur.lastrowid


def get_or_create_venue(conn, name, city="", state="", country=""):
    if not name:
        return None
    row = conn.execute(
        "SELECT venue_id FROM venues WHERE name = ? AND city = ? AND state = ?",
        (name, city, state),
    ).fetchone()
    if row:
        return row["venue_id"]
    cur = conn.execute(
        "INSERT INTO venues(name, city, state, country) VALUES (?, ?, ?, ?)",
        (name, city, state, country),
    )
    return cur.lastrowid


def get_or_create_song(conn, artist_id, title, is_cover=0, original_artist=""):
    norm = normalize_title(title)
    if not norm:
        return None
    row = conn.execute(
        "SELECT song_id FROM songs WHERE artist_id = ? AND norm_title = ?",
        (artist_id, norm),
    ).fetchone()
    if row:
        return row["song_id"]
    cur = conn.execute(
        "INSERT INTO songs(artist_id, title, norm_title, is_cover, original_artist) VALUES (?, ?, ?, ?, ?)",
        (artist_id, title.strip(), norm, int(bool(is_cover)), original_artist),
    )
    return cur.lastrowid


def upsert_show(conn, artist_id, date, venue_id, source, source_key, show_type="standard", url=""):
    """Insert a show, or return the existing show_id for (artist, source, source_key).

    Re-ingesting an existing show wipes its performances so the caller can
    re-add them — this makes every ingest idempotent.
    """
    if not ISO_DATE_RE.match(date or ""):
        raise ValueError(f"show date must be ISO YYYY-MM-DD, got: {date!r}")
    row = conn.execute(
        "SELECT show_id FROM shows WHERE artist_id = ? AND source = ? AND source_key = ?",
        (artist_id, source, source_key),
    ).fetchone()
    if row:
        show_id = row["show_id"]
        conn.execute(
            "UPDATE shows SET date = ?, venue_id = ?, show_type = ?, url = ? WHERE show_id = ?",
            (date, venue_id, show_type, url, show_id),
        )
        conn.execute("DELETE FROM performances WHERE show_id = ?", (show_id,))
        return show_id
    cur = conn.execute(
        "INSERT INTO shows(artist_id, date, venue_id, source, source_key, show_type, url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (artist_id, date, venue_id, source, source_key, show_type, url),
    )
    return cur.lastrowid


def add_performance(conn, show_id, song_id, set_label, position, transition=None, notes=""):
    conn.execute(
        "INSERT INTO performances(show_id, song_id, set_label, position, transition, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (show_id, song_id, set_label, position, transition, notes),
    )


def compute_gaps(conn, artist_slug, include_types=("standard",)):
    """Shows-since-last-played per song, within the ingested window.

    Returns dicts: {song, last_played, shows_since, times_played, window_shows}.
    shows_since counts only shows of the included types AFTER the song's last
    appearance. Gaps are window-limited: a song can never show a gap larger
    than the number of ingested shows.
    """
    type_ph = ",".join("?" for _ in include_types)
    artist = conn.execute("SELECT artist_id FROM artists WHERE slug = ?", (artist_slug,)).fetchone()
    if not artist:
        return []
    aid = artist["artist_id"]

    window_shows = conn.execute(
        f"SELECT COUNT(*) AS n FROM shows WHERE artist_id = ? AND show_type IN ({type_ph})",
        (aid, *include_types),
    ).fetchone()["n"]

    rows = conn.execute(
        f"""
        SELECT s.title AS song,
               MAX(sh.date) AS last_played,
               COUNT(DISTINCT sh.show_id) AS times_played
        FROM songs s
        JOIN performances p ON p.song_id = s.song_id
        JOIN shows sh ON sh.show_id = p.show_id
        WHERE s.artist_id = ? AND sh.show_type IN ({type_ph})
        GROUP BY s.song_id
        """,
        (aid, *include_types),
    ).fetchall()

    out = []
    for r in rows:
        since = conn.execute(
            f"SELECT COUNT(*) AS n FROM shows WHERE artist_id = ? AND date > ? AND show_type IN ({type_ph})",
            (aid, r["last_played"], *include_types),
        ).fetchone()["n"]
        out.append({
            "song": r["song"],
            "last_played": r["last_played"],
            "shows_since": since,
            "times_played": r["times_played"],
            "window_shows": window_shows,
        })
    out.sort(key=lambda x: (-x["shows_since"], x["song"]))
    return out


def dedup_report(conn):
    """Cross-source duplicate shows and near-duplicate song titles.

    Reported, never auto-merged — a human decides.
    """
    dup_shows = conn.execute(
        """
        SELECT a.name AS artist, s1.date, s1.source AS source_a, s2.source AS source_b,
               s1.show_id AS show_a, s2.show_id AS show_b
        FROM shows s1
        JOIN shows s2 ON s1.artist_id = s2.artist_id
                      AND s1.date = s2.date
                      AND s1.show_id < s2.show_id
                      AND s1.source != s2.source
        JOIN artists a ON a.artist_id = s1.artist_id
        """
    ).fetchall()

    near_songs = []
    songs = conn.execute("SELECT song_id, artist_id, title, norm_title FROM songs").fetchall()
    by_artist = {}
    for s in songs:
        by_artist.setdefault(s["artist_id"], []).append(s)
    for artist_songs in by_artist.values():
        seen = {}
        for s in artist_songs:
            # collapse leading "the " and trailing parenthetical for near-match
            loose = re.sub(r"^the ", "", s["norm_title"])
            loose = re.sub(r"\s*\([^)]*\)\s*$", "", loose).strip()
            if loose in seen and seen[loose]["song_id"] != s["song_id"]:
                near_songs.append((seen[loose]["title"], s["title"]))
            else:
                seen[loose] = s

    return {"duplicate_shows": [dict(r) for r in dup_shows], "near_duplicate_songs": near_songs}
