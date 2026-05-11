#!/usr/bin/env python3
"""
tour_radar.py — Upcoming shows radar
Phish dates pulled from phish.net API.
All other artists: check official sites listed in output.
Outputs ../tour-radar.md
"""

import os
import requests
from datetime import datetime, timedelta

PHISHNET_API_KEY = os.environ.get("PHISHNET_API_KEY", "")

TARGETS = {
    "Phoenix AZ": ["Phoenix", "Tempe", "Scottsdale", "Mesa", "Tucson", "Flagstaff"],
    "Denver/Boulder CO": ["Denver", "Boulder", "Fort Collins", "Colorado Springs", "Morrison", "Commerce City", "Broomfield", "Bellvue"],
}

ARTIST_LINKS = {
    "Disco Biscuits": "https://www.discobiscuits.com/shows",
    "Billy Strings": "https://billystrings.com/shows",
    "Trey Anastasio Band": "https://treyanastasio.com/tour",
}

def fetch_phish_tour():
    events = []
    if not PHISHNET_API_KEY:
        print("    skipping Phish (no PHISHNET_API_KEY)")
        return events
    today = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    for year in [current_year, current_year + 1]:
        try:
            r = requests.get(
                f"https://api.phish.net/v5/shows/showyear/{year}.json?apikey={PHISHNET_API_KEY}",
                timeout=15
            )
            for s in r.json().get("data", []):
                date = s.get("showdate", "")
                if date >= today:
                    events.append({
                        "date": date,
                        "venue": s.get("venue", ""),
                        "city": s.get("city", ""),
                        "state": s.get("state", ""),
                        "url": s.get("permalink", "https://phish.com/tour"),
                    })
        except Exception as e:
            print(f"    phish.net error: {e}")
    return events

def is_near_target(event, cities):
    city = event.get("city", "").lower()
    return any(tc.lower() in city or city in tc.lower() for tc in cities)

def write_tour_radar(phish_shows, output_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff_30 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    cutoff_180 = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")

    lines = [
        "# Tour Radar",
        f"*Last updated: {now}*",
        "",
    ]

    # Phish near targets
    lines.append("## Phish — Near You")
    for target_name, target_cities in TARGETS.items():
        regional = [(e["date"], e) for e in phish_shows if e["date"] <= cutoff_180 and is_near_target(e, target_cities)]
        regional.sort()
        if regional:
            lines.append(f"### {target_name}")
            lines.append("| Date | Venue | City |")
            lines.append("|------|-------|------|")
            for date, e in regional:
                lines.append(f"| {date} | {e['venue']} | {e['city']}, {e['state']} |")
            lines.append("")

    # Phish next 30 days
    lines.append("## Phish — Next 30 Days")
    upcoming_phish = sorted([e for e in phish_shows if today <= e["date"] <= cutoff_30], key=lambda x: x["date"])
    if upcoming_phish:
        for e in upcoming_phish:
            lines.append(f"- **{e['date']}** -- {e['venue']}, {e['city']}, {e['state']}")
    else:
        lines.append("*No Phish shows in the next 30 days.*")
    lines.append("")

    # Full Phish schedule
    lines.append("## Phish — Full Upcoming Schedule")
    future_phish = sorted([e for e in phish_shows if e["date"] >= today], key=lambda x: x["date"])
    if future_phish:
        for e in future_phish:
            lines.append(f"- {e['date']} -- {e['venue']}, {e['city']}, {e['state']}")
    lines.append("")

    # Other artists — manual check
    lines += [
        "## Other Artists — Check Official Sites",
        "",
        "| Artist | Tour Page |",
        "|--------|-----------|",
    ]
    for artist, url in ARTIST_LINKS.items():
        lines.append(f"| {artist} | {url} |")

    lines += [
        "",
        "## Venue Watch",
        "- Red Rocks (Morrison CO): https://www.redrocksonline.com/events/",
        "- Mishawaka Amphitheatre (Bellvue CO): https://www.themishawaka.com",
        "- Phish at Dicks (Commerce City CO): https://www.ticketmaster.com",
        "- Mesa Amphitheatre (PHX): https://www.mesaamp.com",
        "- Talking Stick Resort Amp (PHX): https://www.livenation.com",
    ]

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {output_path}")

def main():
    print("Running tour radar...")

    print("  -> Phish...")
    phish_shows = fetch_phish_tour()
    print(f"     Found {len(phish_shows)} upcoming shows")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    write_tour_radar(phish_shows, os.path.join(project_root, "tour-radar.md"))
    print("Done! Tour radar updated.")

if __name__ == "__main__":
    main()