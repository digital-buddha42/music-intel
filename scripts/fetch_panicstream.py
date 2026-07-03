#!/usr/bin/env python3
"""
fetch_panicstream.py — Fetch Widespread Panic setlists from panicstream.com (WordPress REST API)
Outputs markdown to ../artists/widespread-panic.md and ../setlists/wsp-recent.md

Preferred WSP source: panicstream.com publishes real segue marks (>) in its
SEO plugin's meta description field, unlike setlist.fm (fetch_wsp.py — no
segue data at all) or Phantasy Tour (flattens every transition to commas
even in its own rendered UI). Discovery and setlist text both come from one
paginated REST API endpoint (wp-json/wp/v2/posts) — no per-show page
fetches needed. No API key required.

Two description formats have been observed in the wild and both are
handled: "1) Song > Song, Song E) Song" (older posts) and
"1. Song > Song, Song E1. Song E2. Song" (newer posts, supports multiple
encores).

Install deps: pip install requests
"""

import os
import re
import html
import time
import requests
from datetime import datetime

BASE_URL = "https://www.panicstream.com/vault"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; music-intel-personal/1.0)"}

# Only request the fields we actually use — full posts include large,
# unused blobs (aioseo_head, aioseo_head_json, jetpack-related-posts) and
# content.rendered embeds multiple full audio-player playlists per show,
# which is slow to fetch at per_page=50 and can time out on a 15s budget.
API_FIELDS = "id,slug,link,title,content,aioseo_meta_data"

SET_MARKER_RE = re.compile(r'(\d+[.)]|E\d*[.)])\s*')
TRANS_SPLIT_RE = re.compile(r'\s*(>|,)\s*')
SLUG_DATE_RE = re.compile(r'widespread-panic-(\d{2})-(\d{2})-(\d{4})-')
VENUE_RE = re.compile(r'<h1>Widespread Panic<br\s*/?>\s*(.*?)<br\s*/?>', re.IGNORECASE | re.DOTALL)


def api_get_posts(page=1, per_page=20, retries=2):
    params = {"per_page": per_page, "page": page, "_fields": API_FIELDS}
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(
                f"{BASE_URL}/wp-json/wp/v2/posts",
                params=params, headers=HEADERS, timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.Timeout as e:
            last_err = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))  # brief backoff, then retry
    raise last_err


def fetch_recent_posts(num_shows=30):
    """Paginate the REST API, keep only WSP show posts, return newest N by show date."""
    posts = []
    page = 1
    while len(posts) < num_shows and page <= 20:  # 20-page safety cap
        if page > 1:
            time.sleep(1.5)  # courtesy delay between pages -- repeat requests in
            # quick succession from the same IP appear to get throttled by the host
        try:
            batch = api_get_posts(page=page, per_page=20)
        except requests.HTTPError:
            break
        except requests.Timeout:
            print(f"  Warning: page {page} timed out after retries, skipping")
            break
        if not batch:
            break
        for post in batch:
            slug = post.get("slug", "")
            if slug.startswith("widespread-panic-") and SLUG_DATE_RE.search(slug):
                posts.append(post)
        page += 1

    def show_date(post):
        m = SLUG_DATE_RE.search(post.get("slug", ""))
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else "0000-00-00"

    posts.sort(key=show_date, reverse=True)
    return posts[:num_shows]


def parse_setlist_string(desc):
    """AIOSEO description/og_description -> [{label, songs:[{title, transition}]}].

    transition is '>' for a real segue, None for a comma gap (or last song
    in a set). Handles both '1)'/'E)' and '1.'/'E1.'/'E2.' marker styles.
    """
    if not desc:
        return []
    text = html.unescape(desc)
    parts = SET_MARKER_RE.split(text)

    sets = []
    encore_count = 0
    for i in range(1, len(parts), 2):
        raw_label = parts[i].rstrip(".)")
        song_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if raw_label.startswith("E"):
            encore_count += 1
            label = "E" if encore_count == 1 else f"E{encore_count}"
        else:
            label = f"S{raw_label}"

        tokens = [t for t in TRANS_SPLIT_RE.split(song_text) if t != ""]
        songs = []
        j = 0
        while j < len(tokens):
            title = tokens[j].strip()
            if title:
                trans = tokens[j + 1] if j + 1 < len(tokens) else None
                songs.append({"title": title, "transition": trans if trans == ">" else None})
            j += 2
        if songs:
            sets.append({"label": label, "songs": songs})
    return sets


def extract_venue(content_html):
    if not content_html:
        return ""
    m = VENUE_RE.search(content_html)
    return html.unescape(m.group(1)).strip() if m else ""


def extract_city_state(title_text):
    """Title is 'Widespread Panic - MM/DD/YYYY - City, ST' — take the last dash chunk."""
    t = html.unescape(title_text or "")
    chunk = re.split(r'\s[–—-]\s', t)[-1]
    if ',' not in chunk:
        return "", ""
    city, _, state = chunk.rpartition(',')
    return city.strip(), state.strip()


def map_post(post):
    """Normalize one WP REST API post object into a show dict (pure, testable)."""
    slug = post.get("slug", "")
    date_m = SLUG_DATE_RE.search(slug)
    date = f"{date_m.group(3)}-{date_m.group(1)}-{date_m.group(2)}" if date_m else ""

    meta = post.get("aioseo_meta_data") or {}
    desc = meta.get("description") or meta.get("og_description") or ""
    title_text = meta.get("og_title") or post.get("title", {}).get("rendered", "")
    city, state = extract_city_state(title_text)
    venue = extract_venue(post.get("content", {}).get("rendered", ""))

    return {
        "date": date,
        "source_key": str(post.get("id", slug)),
        "url": post.get("link", ""),
        "venue": venue,
        "city": city,
        "state": state,
        "sets": parse_setlist_string(desc),
    }


def format_show_md(show):
    location = ", ".join(filter(None, [show["venue"], show["city"], show["state"]]))
    lines = [f"### {show['date']} — {location}", f"*[panicstream.com]({show['url']})*", ""]
    for st in show["sets"]:
        parts = [song["title"] + (" >" if song["transition"] == ">" else "") for song in st["songs"]]
        lines.append(f"**{st['label']}:** {' '.join(parts)}")
    return "\n".join(lines)


def write_files(shows, project_root):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    artist_path = os.path.join(project_root, "artists", "widespread-panic.md")
    os.makedirs(os.path.dirname(artist_path), exist_ok=True)
    with open(artist_path, "w", encoding="utf-8") as f:
        f.write("# Widespread Panic\n\n")
        f.write(f"*Last updated: {now}*\n\n")
        f.write("## Current Activity\n")
        f.write(f"- {len(shows)} recent shows fetched (panicstream.com, real segue data)\n")
        f.write(f"- Full archive: {BASE_URL}\n\n")
        f.write("## About\n")
        f.write("- Southern rock / jam, Athens GA, active since 1986\n")
        f.write("- Known for: Chilly Water, Pleas, Stop-Go, Fishwater, Surprise Valley, Driving Song, Ain't Life Grand\n")
        f.write("- Lineup: JB, Jimmy Herring (guitar), JoJo Hermann (keys), Dave Schools (bass), Duane Trucks (drums), Sunny Ortiz (perc)\n\n")
        f.write("## Resources\n")
        f.write(f"- Setlists (real segue data): {BASE_URL}\n")
        f.write("- Recordings: streamed per-show on panicstream.com\n")
        f.write("- Tour dates: https://widespreadpanic.com/shows\n")
    print(f"Wrote {artist_path}")

    setlist_path = os.path.join(project_root, "setlists", "wsp-recent.md")
    os.makedirs(os.path.dirname(setlist_path), exist_ok=True)
    with open(setlist_path, "w", encoding="utf-8") as f:
        f.write("# Widespread Panic — Recent Setlists\n")
        f.write(f"*Last updated: {now}*\n\n")
        f.write("*Data via [panicstream.com](https://www.panicstream.com) — real segue marks preserved*\n\n")
        for show in shows:
            f.write(format_show_md(show))
            f.write("\n\n---\n\n")
    print(f"Wrote {setlist_path}")


def main():
    print("Fetching Widespread Panic data from panicstream.com...")
    try:
        posts = fetch_recent_posts(num_shows=30)
    except Exception as e:
        print(f"ERROR: {e}")
        posts = []

    if not posts:
        print("\nERROR: No shows fetched — skipping file writes to preserve existing data.")
        return

    shows = [map_post(p) for p in posts]
    shows = [s for s in shows if s["sets"]]
    print(f"  Found {len(shows)} shows with parseable setlists")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    write_files(shows, project_root)
    print("\nDone! Widespread Panic data updated (panicstream.com).")


if __name__ == "__main__":
    main()
