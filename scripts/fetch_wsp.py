#!/usr/bin/env python3
"""
fetch_wsp.py — Fetch Widespread Panic setlists via setlist.fm API
Everyday Companion (everydaycompanion.com) is the preferred fan source but
blocks cloud/datacenter IPs. setlist.fm provides equivalent structured data
and works everywhere with a free API key.

Requires: SETLISTFM_API_KEY env var (free at https://www.setlist.fm/settings/api)
Outputs: ../artists/widespread-panic.md and ../setlists/wsp-recent.md

Install deps: pip install requests
"""

import os
import sys
import requests
from datetime import datetime

API_KEY = os.environ.get("SETLISTFM_API_KEY", "")
BASE_URL = "https://api.setlist.fm/rest/1.0"
WSP_MBID = "bdfbef92-3e84-4db9-a8e3-f31b5f08b4f6"  # Widespread Panic on MusicBrainz

def api_get(path, params=None):
    headers = {
        "x-api-key": API_KEY,
        "Accept": "application/json",
    }
    r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_recent_setlists(num_shows=10):
    shows = []
    page = 1
    while len(shows) < num_shows:
        data = api_get(f"/artist/{WSP_MBID}/setlists", params={"p": page})
        items = data.get("setlist", [])
        if not items:
            break
        for s in items:
            sets_data = s.get("sets", {}).get("set", [])
            if not sets_data:
                continue  # skip shows with no setlist data
            shows.append(s)
            if len(shows) >= num_shows:
                break
        page += 1
    return shows

def parse_sets(sets_data):
    """Convert setlist.fm sets structure to readable markdown lines."""
    lines = []
    for s in sets_data:
        name = s.get("name", "").strip()
        encore = s.get("encore", 0)
        if encore:
            label = "E"
        elif name:
            label = name
        else:
            set_count = len([l for l in lines if l.startswith("S")]) + 1
            label = f"S{set_count}"

        songs = s.get("song", [])
        song_names = []
        for song in songs:
            n = song.get("name", "?")
            if song.get("tape"):
                n += " [tape]"
            cover = song.get("cover", {})
            if cover:
                n += f" [{cover.get('name', '')} cover]"
            song_names.append(n)
        if song_names:
            lines.append(f"{label}: {' > '.join(song_names)}")
    return lines

def format_show_md(s):
    date_raw = s.get("eventDate", "")  # format: DD-MM-YYYY
    try:
        dt = datetime.strptime(date_raw, "%d-%m-%Y")
        date = dt.strftime("%Y-%m-%d")
    except ValueError:
        date = date_raw

    venue = s.get("venue", {})
    venue_name = venue.get("name", "")
    city_data = venue.get("city", {})
    city = city_data.get("name", "")
    state = city_data.get("stateCode") or city_data.get("state", "")
    country = city_data.get("country", {}).get("code", "")
    location = ", ".join(filter(None, [city, state if country == "US" else country]))

    url = s.get("url", "")
    sets_data = s.get("sets", {}).get("set", [])
    set_lines = parse_sets(sets_data)

    headline = f"### {date} — {venue_name}, {location}"
    lines = [headline, f"*[setlist.fm]({url})*", ""]
    lines.extend(set_lines)
    return "\n".join(lines)

def write_files(shows, project_root):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    artist_path = os.path.join(project_root, "artists", "widespread-panic.md")
    os.makedirs(os.path.dirname(artist_path), exist_ok=True)
    with open(artist_path, "w", encoding="utf-8") as f:
        f.write("# Widespread Panic\n\n")
        f.write(f"*Last updated: {now}*\n\n")
        f.write("## Current Activity\n")
        f.write(f"- {len(shows)} recent shows scraped\n")
        f.write("- Full setlist archive: https://everydaycompanion.com\n")
        f.write("- setlist.fm: https://www.setlist.fm/setlists/widespread-panic-43d6a4c7.html\n\n")
        f.write("## About\n")
        f.write("- Southern rock / jam, Athens GA, active since 1986\n")
        f.write("- Known for: Chilly Water, Pleas, Stop-Go, Fishwater, Surprise Valley, Driving Song, Ain't Life Grand\n")
        f.write("- Lineup: JB, Jimmy Herring (guitar), JoJo Hermann (keys), Dave Schools (bass), Duane Trucks (drums), Sunny Ortiz (perc)\n\n")
        f.write("## Resources\n")
        f.write("- Setlists (fan archive): https://everydaycompanion.com\n")
        f.write("- Recordings: https://archive.org/search?query=widespread+panic&and[]=subject%3A%22etree%22\n")
        f.write("- Tour dates: https://widespreadpanic.com/shows\n")
        f.write("- Reddit: https://reddit.com/r/widespreadpanic\n")
    print(f"Wrote {artist_path}")

    setlist_path = os.path.join(project_root, "setlists", "wsp-recent.md")
    os.makedirs(os.path.dirname(setlist_path), exist_ok=True)
    with open(setlist_path, "w", encoding="utf-8") as f:
        f.write("# Widespread Panic — Recent Setlists\n")
        f.write(f"*Last updated: {now}*\n\n")
        f.write("*Data via [setlist.fm](https://www.setlist.fm). For full notes and deep archive: [Everyday Companion](https://everydaycompanion.com)*\n\n")
        for show in shows:
            f.write(format_show_md(show))
            f.write("\n\n---\n\n")
    print(f"Wrote {setlist_path}")

def main():
    if not API_KEY:
        print("ERROR: SETLISTFM_API_KEY not set.")
        print("Get a free key at https://www.setlist.fm/settings/api")
        print("Then add to your shell: export SETLISTFM_API_KEY=your_key_here")
        sys.exit(1)

    print("Fetching Widespread Panic data from setlist.fm...")
    try:
        shows = fetch_recent_setlists(num_shows=10)
    except Exception as e:
        print(f"ERROR: {e}")
        shows = []

    if not shows:
        print("\nERROR: No shows scraped — skipping file writes to preserve existing data.")
        return

    print(f"  Found {len(shows)} shows with setlists")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    write_files(shows, project_root)
    print("\nDone! Widespread Panic data updated.")

if __name__ == "__main__":
    main()
