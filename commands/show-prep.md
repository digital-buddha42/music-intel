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
Read:
- `show-prep-template.md`
- `artists/[artist].md`
- `setlists/[artist]-recent.md`
- `tour-radar.md`
- `config.md`

### Step 2 — Determine the show
If user said "next": find the next upcoming show from `tour-radar.md` or web search.
If user gave a date or venue: confirm date/venue by checking `tour-radar.md` or searching the web.

### Step 3 — Identify the recent runs
From `setlists/[artist]-recent.md`, group past shows into runs. A run is either:
- A named/announced tour leg, OR
- A multi-night stand at a single venue (e.g., 3 nights at Mishawaka = one run), OR
- An isolated standalone show

Pull setlists from at least the last 3 shows, spanning at least 2 runs. These go in the "Recent Setlists" section.

### Step 4 — Generate the brief
Keep it tight. Use the `show-prep-template.md` structure:

- **Recent Setlists**: raw setlists from the last 3+ shows (labeled by run/venue/date). More is better — at minimum cover the two previous runs.

- **Top 10 Likely Songs**: ranked list of songs most likely to appear at this show. Base on: songs appearing in 2+ of the last 3 shows, opener/closer patterns, songs they're clearly building toward, and gap pressure for overdue staples. No commentary in the list — just rank them.

- **Bustout Watch**: songs with 50+ show gaps. Pull from `artists/[artist].md` or gap notes in setlist data. Flag 75+ as prime candidates.

- **What To Listen For**: 2-3 specific things — tour narrative, jam tendencies, recurring vehicles, teases to watch for.

- **Logistics**: travel from Phoenix or Denver (whichever is closer), venue notes, curfew.

- **Warm-Up Listening**: 1-2 highly-rated recent shows. Link to phish.in for Phish, archive.org for Biscuits.

### Step 5 — Save the file
Save to: `show-prep/[artist-slug]-[date].md`

### Step 6 — Report to user
Display the brief directly in the terminal. Show the full file — it should be short enough to read in one shot.

## Notes
- Tone: enthusiast-level. Assume the user knows the catalog.
- For Phish: gap chart context is non-negotiable.
- Flag travel if the show is > 2 hours from Phoenix or Denver.
