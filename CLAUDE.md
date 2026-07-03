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
- **Disco Biscuits**: `discobiscuits` MCP server at `https://discobiscuits.net/mcp` — 16 tools including SEARCH_SHOWS, GET_SETLIST, SEARCH_SONGS, SEARCH_SEGUES, SONG_HISTORY. Configured in `.claude/settings.json`. Use MCP tools first; fall back to `fetch_biscuits.py` only if MCP is unavailable.
- **Widespread Panic**: setlist.fm API (requires SETLISTFM_API_KEY) via `fetch_wsp.py`
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
  /.claude/commands/      ← slash command definitions (registered with Claude Code)
    show-prep.md
    bustout-watch.md
    update-music-intel.md
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

**`fetch_biscuits.py`** — fallback scraper for Disco Biscuits. Use the `discobiscuits` MCP server instead when available (see `.claude/settings.json`). The scraper is kept as a backup for local/home-network use where the site is accessible.

**`tour_radar.py`** — pulls Phish upcoming shows from phish.net API, filters against `TARGETS` dict of city lists for PHX and Denver/Boulder regions. Other artists (Biscuits, Billy Strings, TAB) are listed as manual check links — no scraping for those.

## Unified Database Layer

All sources normalize into one SQLite schema at `data/music.db` (gitignored, regenerable) so gap analysis works across bands:

- **`music_db.py`** — schema + helpers (artists, venues, shows, songs, performances). Song titles dedup via `normalize_title`. Shows are unique per (artist, source, source_key); re-ingest is idempotent. `show_type` tags Tractorbeam/acoustic sets so gap math can exclude them.
- **`ingest_phish.py`** — phish.net API → DB (`--shows N`, needs PHISHNET_API_KEY)
- **`ingest_wsp.py`** — setlist.fm API → DB (`--shows N`, needs SETLISTFM_API_KEY). setlist.fm has no segue data, so WSP transitions are NULL.
- **`ingest_biscuits.py`** — JSON dump → DB. Biscuits data comes from the `discobiscuits` MCP server queried in-session; export MCP results to JSON (shape documented in the module docstring), then run `python ingest_biscuits.py shows.json`.
- **`gap_analysis.py`** — writes `gap-report.md` across all bands + prints dedup warnings. Gaps are **window-limited** (only ingested shows count); phish.net's official gap chart stays authoritative for Phish bustout calls.
- **Tests**: `cd scripts && python -m pytest tests/ -v` — fixture-based, no API keys needed; one live setlist.fm spot-check runs only when SETLISTFM_API_KEY is set.

## Slash Command Definitions

Slash commands are registered as Claude Code custom commands in `.claude/commands/`. Type `/command-name` in any session to invoke them. Their full step-by-step behavior lives in `.claude/commands/*.md`:

- `.claude/commands/update-music-intel.md` — runs all fetch scripts via parallel agents, then writes `update-summary.md`
- `.claude/commands/show-prep.md` — reads artist profile + recent setlists + tour-radar, generates a pre-show brief using `show-prep-template.md`, saves to `show-prep/[artist]-[date].md`
- `.claude/commands/bustout-watch.md` — read-only; aggregates gap data from `artists/*.md` and prints a ranked summary

## Templates

- `artist-template.md` — structure reference when creating a new artist profile from scratch
- `show-prep-template.md` — structure reference used by `/show-prep` to populate the pre-show brief
