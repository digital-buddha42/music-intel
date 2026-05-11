#!/usr/bin/env python3
"""
fetch_phish.py — Pull Phish data from phish.net API v5
Outputs markdown files to ../artists/phish.md and ../setlists/phish-recent.md

Requires: PHISHNET_API_KEY environment variable
Install deps: pip install requests python-dateutil
"""

import os
import sys
import json
import re
import requests
from datetime import datetime
from collections import Counter

API_BASE = "https://api.phish.net/v5"
API_KEY = os.environ.get("PHISHNET_API_KEY", "")

if not API_KEY:
    print("ERROR: PHISHNET_API_KEY environment variable not set.")
    print("Get a free key at https://api.phish.net/keys/")
    sys.exit(1)

def api_get(endpoint):
    url = f"{API_BASE}/{endpoint}.json?apikey={API_KEY}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])

def get_recent_show_dates(num_shows=15):
    today = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    shows = []
    for year in [current_year, current_year - 1]:
        shows.extend(api_get(f"shows/showyear/{year}"))
    # Only past shows
    shows = [s for s in shows if s.get("showdate", "") <= today]
    shows.sort(key=lambda x: x.get("showdate", ""), reverse=True)
    return [s["showdate"] for s in shows[:num_shows] if s.get("showdate")]

def get_setlist_for_date(showdate):
    return api_get(f"setlists/showdate/{showdate}")

def parse_setlist_to_md(songs):
    if not songs:
        return ""
    first = songs[0]
    date = first.get("showdate", "")
    venue = first.get("venue", "")
    city = first.get("city", "")
    state = first.get("state", "")
    tourname = first.get("tourname", "")
    permalink = first.get("permalink", "")
    notes_raw = first.get("setlistnotes", "")
    notes = re.sub(r'<[^>]+>', '', notes_raw).strip()[:400] if notes_raw else ""

    sets = {}
    for entry in songs:
        set_label = entry.get("set", "?")
        if set_label not in sets:
            sets[set_label] = []
        song = entry.get("song", "")
        trans = entry.get("trans_mark", "")
        isjamchart = entry.get("isjamchart", 0)
        footnote = entry.get("footnote", "")
        song_str = song + (" ⭐" if isjamchart else "") + (f" [{footnote[:50]}]" if footnote else "")
        sets[set_label].append((song_str, trans))

    lines = [f"### {date} — {venue}, {city}, {state}"]
    if tourname:
        lines.append(f"*{tourname}*")
    if permalink:
        lines.append(f"*[phish.net]({permalink})*")

    order_map = {"1": 0, "2": 1, "3": 2, "E": 3, "E2": 4}
    set_order = sorted(sets.keys(), key=lambda x: order_map.get(x, 99))

    for set_label in set_order:
        label = {"E": "Encore", "E2": "Encore 2"}.get(set_label, f"Set {set_label}")
        songs_in_set = sets[set_label]
        parts = []
        for i, (song, trans) in enumerate(songs_in_set):
            if i < len(songs_in_set) - 1 and trans.strip():
                parts.append(f"{song} {trans.strip()}")
            else:
                parts.append(song)
        lines.append(f"**{label}:** {' '.join(parts)}")

    if notes:
        lines.append(f"\n*Notes: {notes}*")

    return "\n".join(lines)

def get_song_gaps():
    try:
        songs = api_get("songs")
        gaps = []
        for s in songs:
            try:
                gap = int(s.get("gap", 0) or 0)
            except (ValueError, TypeError):
                gap = 0
            if gap >= 50:
                gaps.append({
                    "song": s.get("song", ""),
                    "gap": gap,
                    "last_played": s.get("last_date", s.get("lastdate", "unknown")),
                })
        gaps.sort(key=lambda x: x["gap"], reverse=True)
        return gaps
    except Exception as e:
        print(f"  Warning: song gap fetch failed: {e}")
        return []

def find_hot_songs(all_setlists, window=10):
    counts = Counter()
    for songs in all_setlists[:window]:
        seen = set()
        for entry in songs:
            song = entry.get("song", "")
            if song and song not in seen:
                counts[song] += 1
                seen.add(song)
    return [(s, c) for s, c in counts.most_common(12) if c >= 3]

def find_jamchart_highlights(all_setlists, window=10):
    highlights = []
    for songs in all_setlists[:window]:
        if not songs:
            continue
        date = songs[0].get("showdate", "")
        venue = songs[0].get("venue", "")
        city = songs[0].get("city", "")
        for entry in songs:
            if entry.get("isjamchart"):
                highlights.append({
                    "song": entry.get("song", ""),
                    "date": date,
                    "venue": f"{venue}, {city}",
                    "desc": entry.get("jamchart_description", ""),
                })
    return highlights

def write_artist_profile(all_setlists, gaps, output_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    hot_songs = find_hot_songs(all_setlists)
    jam_highlights = find_jamchart_highlights(all_setlists)

    recent = all_setlists[0][0] if all_setlists and all_setlists[0] else {}

    lines = [
        "# Phish", "",
        f"*Last updated: {now}*", "",
        "## Current Activity",
        f"- Most recent show: **{recent.get('showdate','')}** — {recent.get('venue','')}, {recent.get('city','')}, {recent.get('state','')}",
        f"- Tour: {recent.get('tourname', 'see phish.net')}",
        f"- Upcoming dates: https://phish.com/tour", "",
        "## Hot Songs Right Now (last 10 shows)",
    ]

    if hot_songs:
        for song, count in hot_songs:
            lines.append(f"- **{song}** — {count}/10 recent shows")
    else:
        lines.append("- (not enough data)")

    lines += ["", "## Recent Jam Chart Highlights ⭐"]
    if jam_highlights:
        for j in jam_highlights[:8]:
            desc = f" — {j['desc']}" if j['desc'] else ""
            lines.append(f"- **{j['song']}** — {j['date']}, {j['venue']}{desc}")
    else:
        lines.append("- (none in last 10 shows)")

    lines += [
        "", "## Bustout Watch (50+ show gaps)",
        "| Song | Last Played | Gap (shows) |",
        "|------|-------------|-------------|",
    ]
    for b in gaps[:20]:
        lines.append(f"| {b['song']} | {b['last_played']} | {b['gap']} |")
    if not gaps:
        lines.append("| (check phish.net/song for gap chart) | | |")

    lines += [
        "", "## Resources",
        "- Gap chart: https://phish.net/song",
        "- Stream recordings: https://phish.in",
        "- Setlist reviews: https://phish.net/setlists",
        "- Jam chart: https://phish.net/jamchart",
    ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✓ Wrote {output_path}")

def write_recent_setlists(all_setlists, output_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["# Phish — Recent Setlists", f"*Last updated: {now}*", "*(⭐ = Jam Chart version)*", ""]
    for songs in all_setlists:
        if songs:
            lines.append(parse_setlist_to_md(songs))
            lines += ["", "---", ""]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✓ Wrote {output_path}")

def main():
    print("Fetching Phish data from phish.net API...")

    print("  -> Getting recent show dates...")
    dates = get_recent_show_dates(num_shows=15)
    print(f"     Found {len(dates)} shows")

    print("  -> Fetching setlists...")
    all_setlists = []
    for date in dates:
        try:
            songs = get_setlist_for_date(date)
            if songs:
                all_setlists.append(songs)
                print(f"     ✓ {date} ({len(songs)} songs)")
            else:
                print(f"     - {date} (no data)")
        except Exception as e:
            print(f"     ✗ {date}: {e}")

    print(f"  -> Fetching song gap data...")
    gaps = get_song_gaps()
    print(f"     {len(gaps)} songs with 50+ show gaps")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    write_artist_profile(all_setlists, gaps, os.path.join(project_root, "artists", "phish.md"))
    write_recent_setlists(all_setlists, os.path.join(project_root, "setlists", "phish-recent.md"))

    print("\nDone! Phish data updated.")

if __name__ == "__main__":
    main()
