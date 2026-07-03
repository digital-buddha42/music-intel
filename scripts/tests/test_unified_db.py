"""
Tests for the unified music DB: schema, ingestion mapping, dedup, gap math.

Fixture-based tests run anywhere. Live tests hit setlist.fm and are skipped
unless SETLISTFM_API_KEY is set.

Run from scripts/:  python -m pytest tests/ -v
"""

import os
import re
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import music_db
import ingest_wsp
import ingest_biscuits
import ingest_phish


@pytest.fixture
def conn(tmp_path):
    c = music_db.connect(str(tmp_path / "test.db"))
    yield c
    c.close()


# ---------- fixtures: one fake show per source, real-world shapes ----------

def setlistfm_fixture(date="24-07-2025", set_id="abc123"):
    """Mirrors the setlist.fm API v1.0 response shape."""
    return {
        "id": set_id,
        "eventDate": date,
        "url": "https://www.setlist.fm/setlist/widespread-panic/x.html",
        "venue": {
            "name": "Red Rocks Amphitheatre",
            "city": {"name": "Morrison", "stateCode": "CO", "country": {"code": "US"}},
        },
        "sets": {"set": [
            {"song": [
                {"name": "Chilly Water"},
                {"name": "Pleas"},
                {"name": "Love Tractor"},
            ]},
            {"song": [
                {"name": "Fishwater"},
                {"name": "Ride Me High", "cover": {"name": "J.J. Cale"}},
            ]},
            {"encore": 1, "song": [{"name": "Ain't Life Grand"}]},
        ]},
    }


def biscuits_fixture(date="2026-04-24"):
    return {
        "date": date,
        "venue": "Brooklyn Bowl Las Vegas",
        "city": "Las Vegas", "state": "NV", "country": "US",
        "url": f"https://discobiscuits.net/shows/{date}-brooklyn-bowl",
        "sets": [
            {"label": "S1", "songs": [
                {"title": "Shelby Rose", "transition": ">"},
                {"title": "Spacebirdmatingcall", "transition": ">"},
            ]},
            {"label": "E", "songs": [{"title": "Story of the World"}]},
        ],
    }


def phishnet_fixture(date="2026-05-02", showid=1234):
    """Mirrors phish.net API v5 setlists/showdate entries."""
    common = {"showdate": date, "showid": showid, "venue": "Sphere",
              "city": "Las Vegas", "state": "NV", "country": "USA",
              "permalink": "https://phish.net/setlists/x"}
    return [
        dict(common, song="Tweezer", set="1", trans_mark=">", isjamchart=1),
        dict(common, song="Ghost", set="1", trans_mark=""),
        dict(common, song="Tweezer Reprise", set="E", trans_mark=""),
    ]


# ---------------------------- mapping tests ----------------------------

def test_wsp_mapping_dates_sets_covers():
    show = ingest_wsp.map_setlist(setlistfm_fixture())
    assert show["date"] == "2025-07-24"                      # DD-MM-YYYY -> ISO
    assert show["venue"] == "Red Rocks Amphitheatre"
    assert show["state"] == "CO"
    labels = [s["label"] for s in show["sets"]]
    assert labels == ["S1", "S2", "E"]                       # unnamed sets numbered, encore -> E
    cover = show["sets"][1]["songs"][1]
    assert cover["is_cover"] == 1 and cover["original_artist"] == "J.J. Cale"


def test_wsp_ingest_row_counts(conn):
    n = ingest_wsp.ingest_shows(conn, [setlistfm_fixture()])
    assert n == 1
    assert conn.execute("SELECT COUNT(*) c FROM shows").fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM performances").fetchone()["c"] == 6
    assert conn.execute("SELECT COUNT(*) c FROM songs").fetchone()["c"] == 6
    # transitions unknown for setlist.fm -> all NULL
    assert conn.execute(
        "SELECT COUNT(*) c FROM performances WHERE transition IS NOT NULL"
    ).fetchone()["c"] == 0


def test_reingest_is_idempotent(conn):
    ingest_wsp.ingest_shows(conn, [setlistfm_fixture()])
    ingest_wsp.ingest_shows(conn, [setlistfm_fixture()])    # same source_key again
    assert conn.execute("SELECT COUNT(*) c FROM shows").fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM performances").fetchone()["c"] == 6


def test_biscuits_ingest_keeps_transitions_and_show_type(conn):
    show = biscuits_fixture()
    tb = dict(biscuits_fixture("2026-04-17"), show_type="tractorbeam",
              url="https://discobiscuits.net/shows/2026-04-17-1015-folsom")
    assert ingest_biscuits.ingest_shows(conn, [show, tb]) == 2
    assert conn.execute(
        "SELECT COUNT(*) c FROM performances WHERE transition = '>'"
    ).fetchone()["c"] == 4
    assert conn.execute(
        "SELECT COUNT(*) c FROM shows WHERE show_type = 'tractorbeam'"
    ).fetchone()["c"] == 1


def test_phish_ingest_transitions_and_jamchart(conn):
    ingest_phish.ingest_setlist_entries(conn, phishnet_fixture())
    conn.commit()
    row = conn.execute(
        "SELECT p.transition, p.notes FROM performances p JOIN songs s ON s.song_id = p.song_id "
        "WHERE s.title = 'Tweezer'"
    ).fetchone()
    assert row["transition"] == ">"
    assert "[jamchart]" in row["notes"]


# ---------------------------- schema sanity ----------------------------

def test_all_dates_iso_and_in_range(conn):
    ingest_wsp.ingest_shows(conn, [setlistfm_fixture()])
    ingest_biscuits.ingest_shows(conn, [biscuits_fixture()])
    for row in conn.execute("SELECT date FROM shows"):
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", row["date"])
        year = int(row["date"][:4])
        assert 1983 <= year <= datetime.now().year + 1


def test_bad_date_rejected(conn):
    aid = music_db.get_or_create_artist(conn, "X", "x")
    with pytest.raises(ValueError):
        music_db.upsert_show(conn, aid, "24-07-2025", None, "test", "k1")


def test_song_normalization_dedupes():
    assert music_db.normalize_title("Ain't Life Grand") == music_db.normalize_title("Aint Life Grand")
    assert music_db.normalize_title("Chilly  Water ") == "chilly water"


# ---------------------------- gap math ----------------------------

def test_gap_counts_shows_since_last_played(conn):
    shows = [setlistfm_fixture(f"{d:02d}-07-2025", f"id{d}") for d in (20, 21, 22, 23)]
    # remove Chilly Water from the last 3 shows
    for s in shows[1:]:
        s["sets"]["set"][0]["song"] = s["sets"]["set"][0]["song"][1:]
    ingest_wsp.ingest_shows(conn, shows)
    gaps = {g["song"]: g for g in music_db.compute_gaps(conn, "widespread-panic")}
    assert gaps["Chilly Water"]["shows_since"] == 3
    assert gaps["Chilly Water"]["last_played"] == "2025-07-20"
    assert gaps["Ain't Life Grand"]["shows_since"] == 0
    assert gaps["Chilly Water"]["window_shows"] == 4


def test_gap_excludes_tractorbeam_shows(conn):
    ingest_biscuits.ingest_shows(conn, [
        biscuits_fixture("2026-04-20"),
        dict(biscuits_fixture("2026-04-21"), show_type="tractorbeam",
             url="https://discobiscuits.net/shows/2026-04-21-tb"),
    ])
    gaps = {g["song"]: g for g in music_db.compute_gaps(conn, "disco-biscuits")}
    # only 1 standard show in window; the TB show neither counts nor resets gaps
    assert gaps["Shelby Rose"]["window_shows"] == 1
    assert gaps["Shelby Rose"]["shows_since"] == 0


# ---------------------------- dedup / merge ----------------------------

def test_dedup_flags_cross_source_duplicate_show(conn):
    ingest_biscuits.ingest_shows(conn, [biscuits_fixture("2026-04-24")])
    aid = conn.execute("SELECT artist_id FROM artists WHERE slug='disco-biscuits'").fetchone()["artist_id"]
    music_db.upsert_show(conn, aid, "2026-04-24", None, "setlist.fm", "other-key")
    conn.commit()
    report = music_db.dedup_report(conn)
    assert len(report["duplicate_shows"]) == 1
    assert report["duplicate_shows"][0]["date"] == "2026-04-24"


def test_multiple_artists_do_not_collide(conn):
    ingest_wsp.ingest_shows(conn, [setlistfm_fixture()])
    ingest_biscuits.ingest_shows(conn, [biscuits_fixture()])
    ingest_phish.ingest_setlist_entries(conn, phishnet_fixture())
    conn.commit()
    assert conn.execute("SELECT COUNT(*) c FROM artists").fetchone()["c"] == 3
    assert not music_db.dedup_report(conn)["duplicate_shows"]


# ---------------------------- live spot-check ----------------------------

WSP_STAPLES = {"chilly water", "fishwater", "surprise valley", "driving song",
               "aint life grand", "pleas", "love tractor", "porch song",
               "space wrangler", "climb to safety", "pigeons", "tall boy"}


@pytest.mark.skipif(not os.environ.get("SETLISTFM_API_KEY"), reason="SETLISTFM_API_KEY not set")
def test_live_wsp_spot_check(conn):
    """Pull 10 real recent WSP shows and sanity-check the data."""
    from fetch_wsp import fetch_recent_setlists
    setlists = fetch_recent_setlists(num_shows=10)
    assert len(setlists) >= 5
    n = ingest_wsp.ingest_shows(conn, setlists)
    assert n >= 5
    rows = conn.execute(
        "SELECT sh.date, v.name AS venue FROM shows sh LEFT JOIN venues v ON v.venue_id = sh.venue_id"
    ).fetchall()
    for r in rows:
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["date"])
        assert r["venue"]
    # across 10 real shows, at least one catalog staple must appear
    titles = {r["norm_title"] for r in conn.execute("SELECT norm_title FROM songs")}
    assert titles & WSP_STAPLES, f"no known WSP staple in {sorted(titles)[:20]}"
