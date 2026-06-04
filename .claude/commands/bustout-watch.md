# /bustout-watch

## Purpose
Show songs with the longest gaps across all tracked artists. Good for pre-show or just general nerd interest.

## Instructions for Claude

### Step 1 — Read all artist files
Read:
- `artists/phish.md` — has bustout watch table
- `artists/disco-biscuits.md`
- Any other artist files in the `artists/` folder

### Step 2 — Aggregate and rank
Compile all songs with notable gaps (50+ shows for Phish, estimate for others).

For Phish specifically:
- Pull the bustout watch table from `artists/phish.md`
- Sort by gap count descending
- Flag anything over 100 shows as "LONG overdue"
- Flag anything over 200 shows as "holy shit territory"

For other artists:
- Use whatever gap data is in their artist files
- If no gap data, note that

### Step 3 — Output
Print a clean summary directly in the terminal:

```
🎸 BUSTOUT WATCH — [date]

PHISH (sorted by gap):
  [song] — [gap] shows — last played [date]
  ...

DISCO BISCUITS:
  [song] — estimated gap — last played [date if known]
  ...
```

Also note: "Songs most likely to get played next based on gap + tour pattern" (your best guess based on what's been hovering near the top of the gap chart)

## Notes
- This command is read-only — just reads existing files and prints output
- If files are stale (>7 days old), recommend running /update-music-intel first
- For Phish, phish.net gap chart is the authoritative source: https://phish.net/song
