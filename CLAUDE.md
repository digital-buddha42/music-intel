# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Music Intel — Claude Code Context

## What This Project Is
A personal music intelligence system for tracking jam band artists, setlists, tour dates, bustouts, and show prep. Built for a fan who attends live shows regularly and wants to stay deep in the weeds on setlist trends, gap charts, and upcoming dates.

## Owner Preferences
- Jam band focus: Phish, Grateful Dead / Dead & Company, Disco Biscuits, and related artists
- Interested in: bustouts, song gaps, jam quality, tour routing near Phoenix AZ and Colorado (Boulder/Denver)
- Setlist analysis style: enthusiast-level, not casual — reference gap charts, tease notes, jam ratings
- Output format: markdown files, terse and scannable
- Tone: fellow fan, not a press release

## Data Sources
- **Phish**: phish.net API v5 (requires PHISHNET_API_KEY env var) + phish.in for recordings
- **Disco Biscuits**: discobiscuits.net setlists + archive.org etree
- **Dead & Company / GD**: setlist.fm scraping
- **General tours/shows**: songkick or bandsintown scraping for upcoming dates

## File Structure
```
music-intel/
  CLAUDE.md               ← you are here (project memory)
  artists.md              ← master list of tracked artists
  config.md               ← API keys location, preferences
  /artists/
    phish.md              ← auto-generated artist profile
    disco-biscuits.md
    dead-and-company.md
    [etc]
  /setlists/              ← raw scraped setlist data
    phish-recent.md
    biscuits-recent.md
  /show-prep/             ← generated pre-show briefs
  /commands/              ← slash command definitions (human-readable)
    update-artist.md
    show-prep.md
    tour-radar.md
```

## Environment Variables Needed
- `PHISHNET_API_KEY` — get free key at https://api.phish.net/keys/
- Optional: `SETLISTFM_API_KEY` — for Dead/non-Phish artists

## Running the Scripts

All scripts must be run from the `scripts/` directory (they resolve paths relative to their parent, i.e. the project root):

```bash
cd scripts
pip install -r requirements.txt   # one-time setup
python fetch_phish.py             # → artists/phish.md + setlists/phish-recent.md
python fetch_biscuits.py          # → artists/disco-biscuits.md + setlists/biscuits-recent.md
python tour_radar.py              # → tour-radar.md
```

`fetch_phish.py` exits early with a clear error if `PHISHNET_API_KEY` is not set. `fetch_biscuits.py` and `tour_radar.py` work without any API keys. All scripts use ASCII-only print output and work without any encoding flags on Windows.

## Script Architecture

**`fetch_phish.py`** — phish.net API v5 client. Fetches last 15 show dates, pulls each setlist, then calls `/songs` for gap data. Songs with 50+ gap are written to the bustout watch table. `isjamchart` flag marks notable jams with ⭐. All output is structured markdown.

**`fetch_biscuits.py`** — scrapes `discobiscuits.net/shows/year/YYYY` for show URLs, then scrapes each show page. The site structure is fragile; `raw_text` fallback grabs up to 80 lines of the main content block when structured parsing fails.

**`tour_radar.py`** — pulls Phish upcoming shows from phish.net API, filters against `TARGETS` dict of city lists for PHX and Denver/Boulder regions. Other artists (Biscuits, Billy Strings, TAB) are listed as manual check links — no scraping for those.

## Slash Command Definitions

Commands listed under `## Slash Commands Available` are **Claude instructions**, not shell scripts. Their full step-by-step behavior lives in `commands/*.md`. When a command is invoked, read the corresponding file in `commands/` and follow it exactly:

- `commands/update-music-intel.md` — runs all three scripts via parallel agents, then writes `update-summary.md`
- `commands/show-prep.md` — reads artist profile + recent setlists + tour-radar, generates a pre-show brief using `show-prep-template.md`, saves to `show-prep/[artist]-[date].md`
- `commands/bustout-watch.md` — read-only; aggregates gap data from `artists/*.md` and prints a ranked summary

## Templates

- `artist-template.md` — structure reference when creating a new artist profile from scratch
- `show-prep-template.md` — structure reference used by `/show-prep` to populate the pre-show brief
