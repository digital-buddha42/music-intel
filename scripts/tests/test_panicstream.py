"""
Tests for the panicstream.com WSP source — the only WSP source with real
segue marks. Fixtures are VERBATIM captures from the live site (July 2026),
covering both observed setlist-string formats:

- Chicago 6/04/2025:  "1) ... 2) ... E) ..."   (one encore, paren markers)
- Red Rocks 6/28/2026: "1. ... 2. ... E1. ... E2. ..." (two encores, period markers)

Run from scripts/:  python -m pytest tests/ -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import music_db
import fetch_panicstream as ps
import ingest_panicstream


@pytest.fixture
def conn(tmp_path):
    c = music_db.connect(str(tmp_path / "test.db"))
    yield c
    c.close()


# Verbatim from <meta name="description"> on the Chicago show page.
CHICAGO_DESC = (
    "1) From the Cradle &gt; Imitation Leather Shoes &gt; Weight of the World &gt; "
    "Party At Your Mama&#039;s House &gt; Stop Breakin&#039; Down Blues, This Part of Town, "
    "Big Wooly Mammoth &gt; Radio Child, Little By Little "
    "2) Travelin&#039; Light, Good People &gt; Dark Bar &gt; Good People &gt; Pigeons, "
    "Mercy &gt; Drums &gt; Rock, Climb To Safety, For What It&#039;s Worth, Life During Wartime "
    "E) We Walk Each Other Home, Porch Song"
)

# Verbatim from aioseo_meta_data.description in the REST API response.
RED_ROCKS_DESC = (
    "1. Big Wooly Mammoth, Jack, Radio Child, This Part Of Town, "
    "Fishwater &gt; All Time Low &gt; Fishwater &gt; Rock, Heroes &gt; Papa's Home "
    "2. North, Gradle, Don't Be Denied, Party At Your Mama's House &gt; Stop Breakin' Down Blues, "
    "Second Skin &gt; Airplane &gt; Take Off Jam &gt; Drums &gt; Halloween Face, "
    "Ride Me High &gt; Red Hot Mama "
    "E1. Greta &gt; You Got Yours, May Your Glass Be Filled "
    "E2. Goin' Out West"
)


def red_rocks_post():
    """Shape mirrors the live wp-json/wp/v2/posts response."""
    return {
        "id": 27893,
        "slug": "widespread-panic-06-28-2026-morrison-co",
        "link": "https://www.panicstream.com/vault/widespread-panic-06-28-2026-morrison-co/",
        "title": {"rendered": "Widespread Panic &#8211; 06/28/2026 &#8211; Morrison, CO"},
        "content": {"rendered": (
            "<h1>Widespread Panic<br />\nRed Rocks Amphitheatre<br />\n"
            "Morrison, Colorado<br />\n2026-06-28</h1><p>Set 1</p>"
        )},
        "aioseo_meta_data": {
            "description": RED_ROCKS_DESC,
            "og_title": "Widespread Panic - 06/28/2026 - Morrison, CO",
        },
    }


# ---------------------------- parsing: paren format ----------------------------

def test_chicago_paren_format_sets_and_segues():
    sets = ps.parse_setlist_string(CHICAGO_DESC)
    assert [s["label"] for s in sets] == ["S1", "S2", "E"]

    s1 = sets[0]["songs"]
    assert [x["title"] for x in s1] == [
        "From the Cradle", "Imitation Leather Shoes", "Weight of the World",
        "Party At Your Mama's House", "Stop Breakin' Down Blues", "This Part of Town",
        "Big Wooly Mammoth", "Radio Child", "Little By Little",
    ]
    # segues preserved: > where the site had >, None on comma gaps
    assert [x["transition"] for x in s1] == [">", ">", ">", ">", None, None, ">", None, None]

    encore = sets[2]["songs"]
    assert [x["title"] for x in encore] == ["We Walk Each Other Home", "Porch Song"]
    assert all(x["transition"] is None for x in encore)


# ---------------------------- parsing: period format ----------------------------

def test_red_rocks_period_format_double_encore():
    sets = ps.parse_setlist_string(RED_ROCKS_DESC)
    assert [s["label"] for s in sets] == ["S1", "S2", "E", "E2"]

    s1 = sets[0]["songs"]
    assert len(s1) == 10
    # Fishwater sandwich: Fishwater > All Time Low > Fishwater > Rock
    assert [x["title"] for x in s1[4:8]] == ["Fishwater", "All Time Low", "Fishwater", "Rock"]
    assert [x["transition"] for x in s1[4:7]] == [">", ">", ">"]

    assert [x["title"] for x in sets[3]["songs"]] == ["Goin' Out West"]


# ---------------------------- post mapping ----------------------------

def test_map_post_date_venue_location():
    show = ps.map_post(red_rocks_post())
    assert show["date"] == "2026-06-28"          # from slug MM-DD-YYYY, not publish date
    assert show["source_key"] == "27893"
    assert show["venue"] == "Red Rocks Amphitheatre"
    assert show["city"] == "Morrison"
    assert show["state"] == "CO"
    assert len(show["sets"]) == 4


def test_city_not_polluted_by_date_in_title():
    city, state = ps.extract_city_state("Widespread Panic - 06/04/2025 - Chicago, IL")
    assert (city, state) == ("Chicago", "IL")
    city, state = ps.extract_city_state("Widespread Panic &#8211; 06/28/2026 &#8211; Morrison, CO")
    assert (city, state) == ("Morrison", "CO")


# ---------------------------- DB ingestion ----------------------------

def test_ingest_preserves_segues_and_dedups_sandwich(conn):
    assert ingest_panicstream.ingest_shows(conn, [red_rocks_post()]) == 1

    segues = conn.execute(
        "SELECT COUNT(*) c FROM performances WHERE transition = '>'"
    ).fetchone()["c"]
    assert segues == 11  # every > in RED_ROCKS_DESC survives to the DB (4 in S1, 6 in S2, 1 in E)

    # Fishwater played twice in S1 -> 2 performances, 1 song row
    rows = conn.execute(
        "SELECT COUNT(*) c FROM performances p JOIN songs s ON s.song_id = p.song_id "
        "WHERE s.norm_title = 'fishwater'"
    ).fetchone()["c"]
    assert rows == 2
    assert conn.execute(
        "SELECT COUNT(*) c FROM songs WHERE norm_title = 'fishwater'"
    ).fetchone()["c"] == 1


def test_reingest_is_idempotent(conn):
    ingest_panicstream.ingest_shows(conn, [red_rocks_post()])
    ingest_panicstream.ingest_shows(conn, [red_rocks_post()])
    assert conn.execute("SELECT COUNT(*) c FROM shows").fetchone()["c"] == 1
    total = conn.execute("SELECT COUNT(*) c FROM performances").fetchone()["c"]
    assert total == 10 + 12 + 3 + 1  # S1 + S2 + E + E2


def test_gap_analysis_sees_panicstream_shows(conn):
    ingest_panicstream.ingest_shows(conn, [red_rocks_post()])
    gaps = {g["song"]: g for g in music_db.compute_gaps(conn, "widespread-panic")}
    assert gaps["Fishwater"]["last_played"] == "2026-06-28"
    assert gaps["Fishwater"]["times_played"] == 1  # per-show, not per-performance
