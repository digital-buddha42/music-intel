# /show-prep

## Usage
```
/show-prep [artist] [date or "next"]
```

Examples:
- `/show-prep phish next`
- `/show-prep phish 2025-08-15`
- `/show-prep biscuits next`

## Instructions for Claude

When this command is invoked:

### Step 1 — Gather context
Read the following files:
- `show-prep-template.md` — the output template to use
- `artists/[artist].md` — current artist profile (hot songs, bustout watch)
- `setlists/[artist]-recent.md` — recent setlists
- `tour-radar.md` — to find the specific show date/venue
- `config.md` — for location preferences

### Step 2 — Determine the show
If user said "next": find the next upcoming show for this artist from `tour-radar.md` or by web searching "[artist name] tour dates 2025 2026".

If user gave a date: confirm venue/location by checking `tour-radar.md` or searching the web.

### Step 3 — Generate the brief
Using the `show-prep-template.md` structure, populate:

- **Recent setlist context**: pull from `setlists/[artist]-recent.md` — look at last 3-5 shows. What songs are showing up every night? What's the opener pattern? What are they closing Set 2 with?

- **Bustout candidates**: pull from `artists/[artist].md` bustout watch table. For Phish especially, reference gap chart data. Flag songs with 75+ show gaps as "prime candidates."

- **Missing from this tour**: compare recent setlists to the full song catalog. What notable songs haven't appeared yet this run?

- **Likely setlist shape**: based on recent show patterns, describe the probable arc

- **What to listen for**: synthesize the tour narrative into 2-3 specific things — e.g., "They've been building Tweezer into massive Type II territory lately" or "Page has been featured heavily in Set 1 recently"

- **Warm-up listening**: suggest 1-2 shows from `setlists/[artist]-recent.md` that are rated highly or have notable jams. Link to phish.in for Phish recordings.

### Step 4 — Save the file
Save the completed brief to:
`show-prep/[artist-slug]-[date].md`

### Step 5 — Report to user
Display the key highlights directly in the terminal (not the whole file):
- The show details
- Top 3 bustout candidates
- What to listen for
- Link to the saved file

## Notes
- For Phish: always check gap chart context. Fans care deeply about gaps.
- Tone: enthusiast-level — assume the user knows the catalog. Don't explain who Trey is.
- For "next" shows that are > 2 hours from Phoenix or Denver, note the travel situation
