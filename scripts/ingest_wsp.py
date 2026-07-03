#!/usr/bin/env python3
"""
ingest_wsp.py — Widespread Panic setlists (setlist.fm API) -> unified DB.

Requires: SETLISTFM_API_KEY env var (free at https://www.setlist.fm/settings/api)
Usage:    python ingest_wsp.py [--shows N]   (default 30)

Known limitation: setlist.fm does not encode segue marks, so transition is
NULL for every WSP performance. Everyday Companion has segues but blocks
cloud IPs; a home-network scrape could backfill them later.
"""

import os
import sys
import argparse
from datetime import datetime

import music_db
from fetch_wsp import fetch_recent_setlists

ARTIST_NAME = "Widespread Panic"
ARTIST_SLUG = "widespread-panic"
SOURCE = "setlist.fm"


def map_setlist(s):
    """setlist.fm setlist object -> normalized show dict (pure, testable)."""
    date = datetime.strptime(s["eventDate"], "%d-%m-%Y").strftime("%Y-%m-%d")
    venue = s.get("venue", {})
    city_data = venue.get("city", {})
    sets = []
    set_num = 0
    for st in s.get("sets", {}).get("set", []):
        if st.get("encore"):
            label = "E" if st["encore"] == 1 else f"E{st['encore']}"
        elif st.get("name", "").strip():
            label = st["name"].strip()
        else:
            set_num += 1
            label = f"S{set_num}"
        songs = []
        for song in st.get("song", []):
            title = song.get("name", "").strip()
            if not title:
                continue
            cover = song.get("cover") or {}
            notes = song.get("info", "") or ""
            if song.get("tape"):
                notes = (notes + " [tape]").strip()
            songs.append({
                "title": title,
                "is_cover": 1 if cover else 0,
                "original_artist": cover.get("name", ""),
                "notes": notes,
            })
        if songs:
            sets.append({"label": label, "songs": songs})
    return {
        "date": date,
        "source_key": s.get("id", ""),
        "url": s.get("url", ""),
        "venue": venue.get("name", ""),
        "city": city_data.get("name", ""),
        "state": city_data.get("stateCode") or city_data.get("state", ""),
        "country": city_data.get("country", {}).get("code", ""),
        "sets": sets,
    }


def ingest_shows(conn, setlists):
    """Write mapped setlist.fm objects into the DB. Returns count ingested."""
    artist_id = music_db.get_or_create_artist(conn, ARTIST_NAME, ARTIST_SLUG)
    count = 0
    for raw in setlists:
        show = map_setlist(raw)
        if not show["sets"]:
            continue
        venue_id = music_db.get_or_create_venue(
            conn, show["venue"], show["city"], show["state"], show["country"]
        )
        show_id = music_db.upsert_show(
            conn, artist_id, show["date"], venue_id, SOURCE, show["source_key"], url=show["url"]
        )
        for st in show["sets"]:
            for pos, song in enumerate(st["songs"], start=1):
                song_id = music_db.get_or_create_song(
                    conn, artist_id, song["title"], song["is_cover"], song["original_artist"]
                )
                if song_id:
                    # transition=None: setlist.fm carries no segue data
                    music_db.add_performance(
                        conn, show_id, song_id, st["label"], pos, None, song["notes"]
                    )
        count += 1
    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shows", type=int, default=30, help="number of recent shows to ingest")
    args = parser.parse_args()

    if not os.environ.get("SETLISTFM_API_KEY", ""):
        print("ERROR: SETLISTFM_API_KEY not set.")
        print("Get a free key at https://www.setlist.fm/settings/api")
        sys.exit(1)

    print(f"Ingesting Widespread Panic from setlist.fm ({args.shows} shows)...")
    setlists = fetch_recent_setlists(num_shows=args.shows)
    if not setlists:
        print("ERROR: no setlists returned — nothing written.")
        sys.exit(1)

    conn = music_db.connect()
    n = ingest_shows(conn, setlists)
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM shows s JOIN artists a ON a.artist_id = s.artist_id WHERE a.slug = ?",
        (ARTIST_SLUG,),
    ).fetchone()["n"]
    conn.close()
    print(f"Done. Ingested {n} shows this run ({total} WSP shows total in DB).")


if __name__ == "__main__":
    main()
