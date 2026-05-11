# Update Summary

*Last updated: 2026-05-10 20:17*

## Status

| Script | Status | Output |
|--------|--------|--------|
| fetch_phish.py | ✓ Success | artists/phish.md, setlists/phish-recent.md |
| fetch_biscuits.py | ✓ Success | artists/disco-biscuits.md, setlists/biscuits-recent.md |
| tour_radar.py | ✓ Success | tour-radar.md |

Note: Scripts require `$env:PYTHONIOENCODING = "utf-8"` on Windows — the `→` arrow in print statements crashes cp1252. Either set this env var or replace arrows with `->` in the scripts.

## Phish

- Most recent show: 2026-05-02, Sphere, Las Vegas (2026 Sphere run)
- 15 setlists fetched (2026-03-28 through 2026-05-02)
- 749 songs flagged with 50+ show gaps (includes many one-off covers — see notes below)
- Hot songs / jam chart: showing "(not enough data)" — the 2x 2026-04-24 duplicate in the API response may be skewing the frequency count

### Bustout Watch caveat
The top 20 gap list is dominated by songs with "unknown" last-played dates and gaps of 2000+. These are essentially songs Phish has never played or played once in the early 90s (Roadhouse Blues, Bertha, Eyes of the World, etc. — many are GD/classic rock covers). Not actionable bustout candidates. The phish.net song gap chart at https://phish.net/song is the better source for actual Phish-original bustout tracking.

## Disco Biscuits

- 10 shows scraped (2026-03-20 through 2026-05-07)
- Most recent: 2026-05-07, Viva el Gonzo, San Jose del Cabo (Mexico)
- Recent run: Brooklyn Bowl Las Vegas (4/24–4/25), Bay Area (4/16–4/18), Crystal Bay (4/19)

## Tour Radar — Shows Near You

### Denver/Boulder (next 6 months)
- **2026-06-07** — Red Rocks Amphitheatre, Morrison CO ← drive from Denver
- **2026-09-04–06** — Dicks Sporting Goods Park, Commerce City CO ← Dicks weekend

### Phoenix AZ
- No Phish shows near PHX in the 180-day window.

### Phish next 30 days
PNW + mountain west run starting 5/26:
- 5/26 Portland, 5/27 Seattle, 5/29–30 Missoula MT, 5/31 Jackson Hole WY
- 6/2 Salt Lake City, 6/3 Vail CO, 6/7 Red Rocks
