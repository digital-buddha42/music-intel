#!/usr/bin/env python3
"""
ingest_phish.py — Phish setlists (phish.net API v5) -> unified DB.

Requires: PHISHNET_API_KEY env var (free at https://api.phish.net/keys/)
Usage:    python ingest_phish.py [--shows N]   (default 30)

Note: the DB computes window-limited gaps only. phish.net's own gap chart
(full history since 1983) remains the authoritative Phish source and is
still fetched by fetch_phish.py for the bustout watch table.
"""

import os
import sys
import argparse
import requests
from datetime import datetime

import music_db

API_BASE = "https://api.phish.net/v5"
ARTIST_NAME = "Phish"
ARTIST_SLUG = "phish"
SOURCE = "phish.net"


def api_get(endpoint, api_key):
    url = f"{API_BASE}/{endpoint}.json?apikey={api_key}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])


def get_recent_show_dates(api_key, num_shows):
    today = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    shows = []
    for year in [current_year, current_year - 1, current_year - 2]:
        shows.extend(api_get(f"shows/showyear/{year}", api_key))
        if len([s for s in shows if s.get("showdate", "") <= today]) >= num_shows:
            break
    shows = [s for s in shows if s.get("showdate", "") <= today]
    shows.sort(key=lambda x: x.get("showdate", ""), reverse=True)
    # dedup dates (API sometimes returns duplicates)
    seen, dates = set(), []
    for s in shows:
        d = s.get("showdate", "")
        if d and d not in seen:
            seen.add(d)
            dates.append(d)
    return dates[:num_shows]


def ingest_setlist_entries(conn, entries):
    """Write one show's phish.net setlist entries into the DB (pure-ish, testable)."""
    if not entries:
        return None
    artist_id = music_db.get_or_create_artist(conn, ARTIST_NAME, ARTIST_SLUG)
    first = entries[0]
    date = first.get("showdate", "")
    venue_id = music_db.get_or_create_venue(
        conn, first.get("venue", ""), first.get("city", ""), first.get("state", ""),
        first.get("country", ""),
    )
    source_key = str(first.get("showid", "")) or date
    show_id = music_db.upsert_show(
        conn, artist_id, date, venue_id, SOURCE, source_key,
        url=first.get("permalink", ""),
    )
    positions = {}
    for entry in entries:
        title = entry.get("song", "").strip()
        if not title:
            continue
        set_label = entry.get("set", "?")
        positions[set_label] = positions.get(set_label, 0) + 1
        song_id = music_db.get_or_create_song(conn, artist_id, title)
        trans = (entry.get("trans_mark", "") or "").strip() or None
        notes = (entry.get("footnote", "") or "")[:200]
        if entry.get("isjamchart"):
            notes = (notes + " [jamchart]").strip()
        music_db.add_performance(conn, show_id, song_id, set_label, positions[set_label], trans, notes)
    return show_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shows", type=int, default=30, help="number of recent shows to ingest")
    args = parser.parse_args()

    api_key = os.environ.get("PHISHNET_API_KEY", "")
    if not api_key:
        print("ERROR: PHISHNET_API_KEY environment variable not set.")
        print("Get a free key at https://api.phish.net/keys/")
        sys.exit(1)

    print(f"Ingesting Phish from phish.net ({args.shows} shows)...")
    dates = get_recent_show_dates(api_key, args.shows)
    if not dates:
        print("ERROR: no show dates returned — nothing written.")
        sys.exit(1)

    conn = music_db.connect()
    count = 0
    for date in dates:
        try:
            entries = api_get(f"setlists/showdate/{date}", api_key)
            if entries and ingest_setlist_entries(conn, entries):
                count += 1
                print(f"  + {date}")
        except Exception as e:
            print(f"  ! {date}: {e}")
    conn.commit()
    conn.close()
    print(f"Done. Ingested {count} shows.")


if __name__ == "__main__":
    main()
