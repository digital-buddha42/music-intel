#!/usr/bin/env python3
"""
ingest_panicstream.py — Widespread Panic setlists (panicstream.com REST API) -> unified DB.

Preferred WSP source: panicstream.com publishes real segue marks, unlike
setlist.fm (ingest_wsp.py — transitions always NULL there). No API key
required. See fetch_panicstream.py for the parsing details.

Usage: python ingest_panicstream.py [--shows N]   (default 30)
"""

import sys
import argparse

import music_db
from fetch_panicstream import fetch_recent_posts, map_post

ARTIST_NAME = "Widespread Panic"
ARTIST_SLUG = "widespread-panic"
SOURCE = "panicstream.com"


def ingest_shows(conn, posts):
    """Write mapped panicstream.com post objects into the DB. Returns count ingested."""
    artist_id = music_db.get_or_create_artist(conn, ARTIST_NAME, ARTIST_SLUG)
    count = 0
    for post in posts:
        show = map_post(post)
        if not show["sets"] or not show["date"]:
            continue
        venue_id = music_db.get_or_create_venue(conn, show["venue"], show["city"], show["state"], "US")
        show_id = music_db.upsert_show(
            conn, artist_id, show["date"], venue_id, SOURCE, show["source_key"], url=show["url"]
        )
        for st in show["sets"]:
            for pos, song in enumerate(st["songs"], start=1):
                song_id = music_db.get_or_create_song(conn, artist_id, song["title"])
                if song_id:
                    music_db.add_performance(conn, show_id, song_id, st["label"], pos, song["transition"])
        count += 1
    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shows", type=int, default=30, help="number of recent shows to ingest")
    args = parser.parse_args()

    print(f"Ingesting Widespread Panic from panicstream.com ({args.shows} shows)...")
    try:
        posts = fetch_recent_posts(num_shows=args.shows)
    except Exception as e:
        print(f"ERROR: {e}")
        posts = []

    if not posts:
        print("ERROR: no posts fetched — nothing written.")
        sys.exit(1)

    conn = music_db.connect()
    n = ingest_shows(conn, posts)
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM shows s JOIN artists a ON a.artist_id = s.artist_id "
        "WHERE a.slug = ? AND s.source = ?",
        (ARTIST_SLUG, SOURCE),
    ).fetchone()["n"]
    conn.close()
    print(f"Done. Ingested {n} shows this run ({total} panicstream.com WSP shows total in DB).")


if __name__ == "__main__":
    main()
