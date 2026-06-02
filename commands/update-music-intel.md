# /update-music-intel

## Purpose
Refresh all artist profiles, setlists, and tour data.

## Instructions for Claude

When this command is invoked, do the following steps in order:

### Step 1 — Run data fetching scripts in parallel
Use multiple agents to run these simultaneously:

**Agent A — Phish data:**
```bash
cd scripts && python fetch_phish.py
```
This writes to:
- `artists/phish.md`
- `setlists/phish-recent.md`

**Agent B — Disco Biscuits data:**
```bash
cd scripts && python fetch_biscuits.py
```
This writes to:
- `artists/disco-biscuits.md`
- `setlists/biscuits-recent.md`

**Agent C — Widespread Panic data:**
```bash
cd scripts && python fetch_wsp.py
```
This writes to:
- `artists/widespread-panic.md`
- `setlists/wsp-recent.md`

**Agent D — Tour radar:**
```bash
cd scripts && python tour_radar.py
```
This writes to:
- `tour-radar.md`

### Step 2 — Generate summary
After all agents finish, read the output files and write a brief `update-summary.md` with:
- Date/time of update
- What was updated and whether it succeeded
- Any notable items found (bustouts, nearby shows in next 60 days, etc.)
- Any errors or warnings

### Step 3 — Report to user
Tell the user:
- What updated successfully
- Any nearby shows in the next 60 days (from tour-radar.md)
- Top 2-3 bustout candidates for Phish
- Any errors to fix

## Notes
- If PHISHNET_API_KEY is missing, remind the user to get one at https://api.phish.net/keys/ and add it to their shell profile
- If a script fails, log the error but continue with other agents
- Always update `update-summary.md` even if some fetches failed
