#!/usr/bin/env python3
"""
ingest_biscuits.py — Disco Biscuits shows (JSON dump) -> unified DB.

The Biscuits source of record is the `discobiscuits` MCP server
(https://discobiscuits.net/mcp), which Claude queries in-session — it is not
importable from Python. So this module ingests a JSON file that a Claude
session exports from MCP results (see /update-music-intel).

Usage: python ingest_biscuits.py path/to/shows.json

Expected JSON shape (list of shows):
[
  {
    "date": "2026-04-24",              # ISO, required
    "venue": "Brooklyn Bowl Las Vegas",
    "city": "Las Vegas", "state": "NV", "country": "US",
    "url": "https://discobiscuits.net/shows/...",
    "show_type": "standard",           # or "tractorbeam" / "acoustic"; default standard
    "sets": [
      {"label": "S1", "songs": [
        {"title": "Shelby Rose", "transition": ">", "notes": "inverted"},
        {"title": "Spacebirdmatingcall", "transition": ","}
      ]},
      {"label": "E", "songs": [{"title": "Story of the World"}]}
    ]
  }
]

show_type matters: Tractorbeam and acoustic sets are tagged so gap analysis
can exclude them — a song "gap" that resets because of a DJ set is wrong.
"""

import sys
import json

import music_db

ARTIST_NAME = "Disco Biscuits"
ARTIST_SLUG = "disco-biscuits"
SOURCE = "discobiscuits.net"


def ingest_shows(conn, shows):
    """Write JSON-shaped show dicts into the DB. Returns count ingested."""
    artist_id = music_db.get_or_create_artist(conn, ARTIST_NAME, ARTIST_SLUG)
    count = 0
    for show in shows:
        date = show.get("date", "")
        sets = show.get("sets", [])
        if not date or not sets:
            print(f"  ! skipping show with missing date or sets: {show.get('url', '?')}")
            continue
        venue_id = music_db.get_or_create_venue(
            conn, show.get("venue", ""), show.get("city", ""),
            show.get("state", ""), show.get("country", ""),
        )
        source_key = show.get("url", "") or date
        show_id = music_db.upsert_show(
            conn, artist_id, date, venue_id, SOURCE, source_key,
            show_type=show.get("show_type", "standard"), url=show.get("url", ""),
        )
        for st in sets:
            for pos, song in enumerate(st.get("songs", []), start=1):
                title = song.get("title", "").strip()
                if not title:
                    continue
                song_id = music_db.get_or_create_song(conn, artist_id, title)
                music_db.add_performance(
                    conn, show_id, song_id, st.get("label", "?"), pos,
                    song.get("transition"), song.get("notes", ""),
                )
        count += 1
    conn.commit()
    return count


def main():
    if len(sys.argv) != 2:
        print("Usage: python ingest_biscuits.py path/to/shows.json")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        shows = json.load(f)
    if not shows:
        print("ERROR: JSON file contains no shows — nothing written.")
        sys.exit(1)

    print(f"Ingesting Disco Biscuits from {sys.argv[1]} ({len(shows)} shows)...")
    conn = music_db.connect()
    n = ingest_shows(conn, shows)
    conn.close()
    print(f"Done. Ingested {n} shows.")


if __name__ == "__main__":
    main()
