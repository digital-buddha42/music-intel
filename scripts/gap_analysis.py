#!/usr/bin/env python3
"""
gap_analysis.py — Cross-band gap report from the unified DB.

Computes shows-since-last-played for every song of every artist in
../data/music.db and writes ../gap-report.md. Also prints the dedup report
(duplicate shows across sources, near-duplicate song titles).

Usage: python gap_analysis.py [--min-gap N]   (default 0 = show all)

Honesty rules baked in:
- Gaps are WINDOW-LIMITED: only shows ingested into the DB count. A song's
  true gap may be far larger than reported. The window size is printed with
  every table.
- Phish: phish.net's official full-history gap chart (via fetch_phish.py)
  stays authoritative for bustout calls; this report covers recent-window
  trends across ALL bands with one consistent method.
- Non-standard shows (Tractorbeam, acoustic) are excluded from gap math.
"""

import argparse
from datetime import datetime

import music_db


def write_report(conn, output_path, min_gap=0):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Gap Report — All Bands",
        f"*Generated: {now}*",
        "",
        "Gaps are **window-limited**: only shows in the local database count.",
        "\"Shows since\" can never exceed the window size — treat top-of-table",
        "songs as \"not seen in this window,\" not as true full-history gaps.",
        "For Phish full-history gaps, use phish.net/song (fetch_phish.py).",
        "",
    ]

    artists = conn.execute("SELECT name, slug FROM artists ORDER BY name").fetchall()
    if not artists:
        lines.append("*Database is empty — run the ingest scripts first.*")

    for artist in artists:
        gaps = music_db.compute_gaps(conn, artist["slug"])
        if not gaps:
            continue
        window = gaps[0]["window_shows"]
        lines += [
            f"## {artist['name']}",
            f"*Window: last {window} standard shows in DB*",
            "",
            "| Song | Last Played | Shows Since | Times in Window |",
            "|------|-------------|-------------|-----------------|",
        ]
        for g in gaps:
            if g["shows_since"] < min_gap:
                continue
            lines.append(
                f"| {g['song']} | {g['last_played']} | {g['shows_since']} | {g['times_played']} |"
            )
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {output_path}")


def print_dedup(conn):
    report = music_db.dedup_report(conn)
    if report["duplicate_shows"]:
        print("\nWARNING - duplicate shows across sources:")
        for d in report["duplicate_shows"]:
            print(f"  {d['artist']} {d['date']}: {d['source_a']} vs {d['source_b']}")
    if report["near_duplicate_songs"]:
        print("\nWARNING - near-duplicate song titles (review and merge by hand):")
        for a, b in report["near_duplicate_songs"]:
            print(f"  '{a}' ~ '{b}'")
    if not report["duplicate_shows"] and not report["near_duplicate_songs"]:
        print("No duplicate shows or near-duplicate songs found.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-gap", type=int, default=0, help="only list songs with gap >= N")
    args = parser.parse_args()

    import os
    conn = music_db.connect()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(os.path.dirname(script_dir), "gap-report.md")
    write_report(conn, output_path, args.min_gap)
    print_dedup(conn)
    conn.close()


if __name__ == "__main__":
    main()
