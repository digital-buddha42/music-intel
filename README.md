# Music Intel — Getting Started

## What This Is
A Claude Code project that keeps you dialed in on Phish, the Biscuits, and your other tracked artists. Setlists, bustout gaps, upcoming shows near you, pre-show briefs — all in markdown files that Claude can read and update.

## One-Time Setup

### 1. Get a phish.net API key (free, instant)
Go to: https://api.phish.net/keys/

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export PHISHNET_API_KEY="your_key_here"
```
Then: `source ~/.zshrc`

### 2. Install Python deps
```bash
pip install -r scripts/requirements.txt --break-system-packages
```

### 3. Launch Claude Code in this folder
```bash
cd ~/music-intel
claude
```

First time: run `/init` when Claude asks, then start using commands.

---

## Slash Commands

| Command | What it does |
|---------|-------------|
| `/update-music-intel` | Refresh all artist data, setlists, tour radar |
| `/show-prep phish next` | Pre-show brief for next Phish show |
| `/show-prep phish 2025-08-15` | Pre-show brief for specific date |
| `/bustout-watch` | See overdue songs across all artists |
| `/tour-radar` | Just rerun the tour date check |

---

## File Map

```
music-intel/
  CLAUDE.md               ← project memory / instructions for Claude
  README.md               ← this file
  artists.md              ← master list of tracked artists
  config.md               ← your preferences, API key instructions
  artist-template.md      ← template used when generating artist profiles
  show-prep-template.md   ← template used for pre-show briefs
  tour-radar.md           ← auto-generated: upcoming shows near you
  update-summary.md       ← auto-generated: last update log
  
  artists/
    phish.md              ← auto-generated Phish profile
    disco-biscuits.md     ← auto-generated Biscuits profile
  
  setlists/
    phish-recent.md       ← last ~15 Phish setlists
    biscuits-recent.md    ← recent Biscuits setlists
  
  show-prep/
    phish-2025-08-15.md   ← example pre-show brief
  
  scripts/
    fetch_phish.py        ← phish.net API fetcher
    fetch_biscuits.py     ← discobiscuits.net scraper
    tour_radar.py         ← upcoming shows finder
    requirements.txt      ← pip dependencies
  
  commands/
    update-music-intel.md ← slash command definition
    show-prep.md          ← slash command definition
    bustout-watch.md      ← slash command definition
```

---

## Suggested Workflow

**Weekly (Sunday-ish):**
→ Open Claude Code in `~/music-intel`
→ `/update-music-intel`
→ Skim `tour-radar.md` for upcoming shows

**Day before a show:**
→ `/show-prep phish [date]`
→ Read the brief, queue up the suggested warm-up recording

**Random nerd session:**
→ `/bustout-watch`
→ Argue with yourself about whether Harpua is coming

---

## Extending This
- Add more artists: add to `artists.md`, Claude will include them in future updates
- Customize gap threshold: edit `config.md`
- Add a new artist fetcher: add a script to `scripts/`, update `commands/update-music-intel.md`
- Build toward the music travel app concept: the `tour-radar.md` data is the seed
