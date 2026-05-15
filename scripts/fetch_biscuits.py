#!/usr/bin/env python3
"""
fetch_biscuits.py — Scrape Disco Biscuits setlists from discobiscuits.net
Outputs markdown to ../artists/disco-biscuits.md and ../setlists/biscuits-recent.md

Install deps: pip install requests beautifulsoup4 lxml
"""

import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; music-intel-personal/1.0)"}
BASE_URL = "https://discobiscuits.net"

def fetch_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def get_recent_show_urls(num_shows=10):
    """Get recent show URLs from the year pages."""
    today = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    show_urls = []

    for year in [current_year, current_year - 1]:
        try:
            soup = fetch_soup(f"{BASE_URL}/shows/year/{year}")
            # Find all show links — pattern: /shows/YYYY-MM-DD-venue-city-state
            links = soup.find_all("a", href=re.compile(r"/shows/\d{4}-\d{2}-\d{2}-"))
            for link in links:
                href = link.get("href", "")
                # Extract date from URL
                date_match = re.search(r"/shows/(\d{4}-\d{2}-\d{2})-", href)
                if date_match:
                    show_date = date_match.group(1)
                    if show_date <= today:
                        full_url = BASE_URL + href if href.startswith("/") else href
                        if full_url not in show_urls:
                            show_urls.append((show_date, full_url))
        except Exception as e:
            print(f"  Warning: could not fetch year {year}: {e}")

    # Sort by date descending, take most recent N
    show_urls.sort(key=lambda x: x[0], reverse=True)
    return [url for _, url in show_urls[:num_shows]]

def scrape_show(url):
    """Scrape a single show page."""
    try:
        soup = fetch_soup(url)
        result = {"url": url, "date": "", "venue": "", "city": "", "sets": {}, "notes": ""}

        # Extract date from URL
        date_match = re.search(r"/shows/(\d{4}-\d{2}-\d{2})-", url)
        if date_match:
            result["date"] = date_match.group(1)

        # Try to get venue/city from page title or h1
        h1 = soup.find("h1")
        if h1:
            result["headline"] = h1.get_text(strip=True)

        # Try to find setlist content
        # discobiscuits.net uses structured set blocks
        sets_content = {}

        # Look for set labels and song lists
        set_headers = soup.find_all(string=re.compile(r"^S[0-9E]$|^Set [0-9]|^Encore", re.I))
        
        # Fallback: grab main content text
        main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile("content|show|setlist", re.I))
        if main:
            text = main.get_text(separator="\n", strip=True)
            # Clean up and limit
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            result["raw_text"] = "\n".join(lines[:80])

        return result
    except Exception as e:
        print(f"  Warning: failed to scrape {url}: {e}")
        return None

def format_show_md(show):
    if not show:
        return ""
    lines = []
    headline = show.get("headline", "")
    date = show.get("date", "")
    url = show.get("url", "")

    header = f"### {date}"
    if headline:
        header += f" — {headline}"
    lines.append(header)
    lines.append(f"*[discobiscuits.net]({url})*")

    raw = show.get("raw_text", "")
    if raw:
        lines.append(raw[:1200])

    return "\n".join(lines)

def write_files(shows, project_root):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Artist profile
    artist_path = os.path.join(project_root, "artists", "disco-biscuits.md")
    os.makedirs(os.path.dirname(artist_path), exist_ok=True)
    with open(artist_path, "w", encoding="utf-8") as f:
        f.write(f"# Disco Biscuits\n\n")
        f.write(f"*Last updated: {now}*\n\n")
        f.write(f"## Current Activity\n")
        f.write(f"- {len(shows)} recent shows scraped\n")
        f.write(f"- Full show index: https://discobiscuits.net/shows/year/{datetime.now().year}\n\n")
        f.write(f"## About\n")
        f.write(f"- Trance-fusion, Philly based, active since 1995\n")
        f.write(f"- Known for: Spaga, Story of the World, Above the Waves, Basis for a Day, Little Shimmy\n")
        f.write(f"- New drummer Marlon B. Lewis as of 2025/2026\n")
        f.write(f"- Summer 2026 tour includes Northeast dates + Telluride Jazz Fest\n\n")
        f.write(f"## Resources\n")
        f.write(f"- Setlists: https://discobiscuits.net\n")
        f.write(f"- Recordings: https://archive.org/search?query=disco+biscuits&and[]=subject%3A%22etree%22\n")
        f.write(f"- Tour dates: https://discobiscuits.com/shows\n")
        f.write(f"- Reddit: https://reddit.com/r/discobiscuits\n")
    print(f"✓ Wrote {artist_path}")

    # Recent setlists
    setlist_path = os.path.join(project_root, "setlists", "biscuits-recent.md")
    os.makedirs(os.path.dirname(setlist_path), exist_ok=True)
    with open(setlist_path, "w", encoding="utf-8") as f:
        f.write(f"# Disco Biscuits — Recent Setlists\n")
        f.write(f"*Last updated: {now}*\n\n")
        if not shows:
            f.write("No setlists scraped. Check https://discobiscuits.net directly.\n")
        else:
            for show in shows:
                f.write(format_show_md(show))
                f.write("\n\n---\n\n")
    print(f"✓ Wrote {setlist_path}")

def main():
    print("Fetching Disco Biscuits data...")
    print("  -> Finding recent show URLs...")
    urls = get_recent_show_urls(num_shows=10)
    print(f"     Found {len(urls)} shows")

    shows = []
    for url in urls:
        print(f"  -> Scraping {url.split('/')[-1]}...")
        show = scrape_show(url)
        if show:
            shows.append(show)

    if not shows:
        print("\nERROR: No shows scraped — skipping file writes to preserve existing data.")
        print("Check if discobiscuits.net is blocking requests (403) and try again later.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    write_files(shows, project_root)
    print("\nDone! Disco Biscuits data updated.")

if __name__ == "__main__":
    main()