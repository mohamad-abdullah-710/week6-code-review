from datetime import date

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_create_and_list_habit():
    r = client.post("/habits", json={"name": "Read 20 minutes"})
    assert r.status_code == 200
    hid = r.json()["id"]
    r2 = client.get("/habits")
    assert r2.status_code == 200
    assert any(h["id"] == hid for h in r2.json())


def test_checkin_flow():
    hid = client.post("/habits", json={"name": "Stretch"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
    r2 = client.get(f"/habits/{hid}/checkins")
    assert r2.json() == ["2026-09-22"]


def test_checkin_unknown_habit_404():
    r = client.post("/habits/99999/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 404


# --- Streak ---------------------------------------------------------------

FIXED_TODAY = date(2026, 9, 22)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the app at a fresh database in a temporary folder for one test."""
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test_habits.db")
    main.init_db()


@pytest.fixture
def fixed_today(monkeypatch):
    monkeypatch.setattr(main, "today", lambda: FIXED_TODAY)


def _habit_with_checkins(*days):
    hid = client.post("/habits", json={"name": "Streak test"}).json()["id"]
    for d in days:
        client.post(f"/habits/{hid}/checkin", json={"day": d})
    return hid


def test_streak_counts_consecutive_days_ending_today(temp_db, fixed_today):
    hid = _habit_with_checkins("2026-09-20", "2026-09-21", "2026-09-22")
    r = client.get(f"/habits/{hid}/streak")
    assert r.status_code == 200
    assert r.json() == {"habit_id": hid, "streak": 3}


def test_streak_stops_at_a_gap(temp_db, fixed_today):
    hid = _habit_with_checkins("2026-09-18", "2026-09-21", "2026-09-22")
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 2


def test_streak_is_zero_without_checkin_today(temp_db, fixed_today):
    hid = _habit_with_checkins("2026-09-20", "2026-09-21")
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 0


def test_streak_counts_duplicate_days_once(temp_db, fixed_today):
    hid = _habit_with_checkins("2026-09-22", "2026-09-22", "2026-09-21")
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 2


def test_streak_ignores_future_checkins(temp_db, fixed_today):
    hid = _habit_with_checkins("2026-09-23", "2026-09-22")
    assert client.get(f"/habits/{hid}/streak").json()["streak"] == 1


def test_streak_unknown_habit_404(temp_db):
    assert client.get("/habits/99999/streak").status_code == 404
