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


# --- Validation -----------------------------------------------------------


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_create_habit_rejects_blank_name(name):
    r = client.post("/habits", json={"name": name})
    assert r.status_code == 422
    assert "habit name must not be empty" in r.text


def test_create_habit_strips_whitespace():
    r = client.post("/habits", json={"name": "  Drink water  "})
    assert r.status_code == 200
    assert r.json()["name"] == "Drink water"


@pytest.mark.parametrize(
    "day",
    [
        "",
        "yesterday",
        "22-09-2026",
        "2026/09/22",
        "20260922",
        "2026-9-22",
        "2026-09-22\n",
    ],
)
def test_checkin_rejects_malformed_day(day):
    hid = client.post("/habits", json={"name": "Validation test"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": day})
    assert r.status_code == 422
    assert "YYYY-MM-DD" in r.text


@pytest.mark.parametrize("day", ["2026-02-30", "2026-13-01", "2026-00-10"])
def test_checkin_rejects_impossible_date(day):
    hid = client.post("/habits", json={"name": "Validation test"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": day})
    assert r.status_code == 422
    assert "not a real calendar date" in r.text


def test_checkin_accepts_leap_day():
    hid = client.post("/habits", json={"name": "Validation test"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2024-02-29"})
    assert r.status_code == 200


@pytest.mark.parametrize("day", ["2026-09-23", "2030-01-01"])
def test_checkin_rejects_future_day(monkeypatch, day):
    monkeypatch.setattr(main, "today", lambda: date(2026, 9, 22))
    hid = client.post("/habits", json={"name": "Validation test"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": day})
    assert r.status_code == 422
    assert "is in the future" in r.text


def test_checkin_accepts_today(monkeypatch):
    monkeypatch.setattr(main, "today", lambda: date(2026, 9, 22))
    hid = client.post("/habits", json={"name": "Validation test"}).json()["id"]
    r = client.post(f"/habits/{hid}/checkin", json={"day": "2026-09-22"})
    assert r.status_code == 200
