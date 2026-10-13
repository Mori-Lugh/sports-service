import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.sample_data import MATCHES
from app.events import EVENTS


class EventTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_matches = MATCHES.copy()
        self.original_events = EVENTS.copy()
        EVENTS.clear()

    def tearDown(self):
        MATCHES[:] = self.original_matches
        EVENTS[:] = self.original_events

    def test_scheduled_event(self):
        data = self.client.get("/matches/3").json()
        data["match_id"] = 10
        self.assertEqual(self.client.post("/matches", json=data).status_code, 201)
        event = self.client.get("/events").json()[0]
        self.assertEqual(event["event_type"], "match.scheduled")
        self.assertEqual(event["match_id"], 10)
        for field in ["event_id", "occurred_at", "version", "home", "away", "starts_at", "sport", "status"]:
            self.assertIn(field, event)
        self.assertEqual(self.client.post("/matches", json=data).status_code, 409)
        self.assertEqual(len(EVENTS), 1)

    def test_finish_and_correction(self):
        self.assertEqual(self.client.post("/matches/3/start").status_code, 200)
        self.assertIn("started_at", EVENTS[0])
        response = self.client.post("/matches/3/finish", json={"home": 2, "away": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EVENTS[-1]["outcome"], "home")
        self.assertEqual(self.client.get("/teams/2/stats?season_id=1").json()["points"], 3)

        response = self.client.post("/matches/3/correct-result", json={"home": 1, "away": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EVENTS[-1]["outcome"], "away")
        self.assertEqual(self.client.get("/teams/2/stats?season_id=1").json()["points"], 0)
        self.assertEqual([event["event_type"] for event in EVENTS],
                         ["match.started", "match.finished", "match.result_corrected"])
        #старое событие сохраняет старый результат
        self.assertEqual(EVENTS[1]["score"], {"home": 2, "away": 1})
        self.assertEqual(len({event["event_id"] for event in EVENTS}), 3)

    def test_invalid_transition_and_score(self):
        self.assertEqual(self.client.post("/matches/3/finish", json={"home": 1, "away": 0}).status_code, 409)
        self.assertEqual(self.client.post("/matches/999/start").status_code, 404)
        self.assertEqual(self.client.post("/matches/3/start").status_code, 200)
        self.assertEqual(self.client.post("/matches/3/start").status_code, 409)
        self.assertEqual(self.client.post("/matches/3/finish", json={"home": -1, "away": 0}).status_code, 422)
        self.assertEqual(self.client.get("/matches/3").json()["status"], "live")
        self.assertEqual(len(EVENTS), 1)

    def test_cancel_match(self):
        self.assertEqual(self.client.post("/matches/3/cancel").status_code, 200)
        self.assertEqual(EVENTS[-1]["event_type"], "match.cancelled")
        self.assertNotIn("outcome", EVENTS[-1])
        self.assertEqual(self.client.post("/matches/3/start").status_code, 409)
        self.assertEqual(self.client.post("/matches/3/cancel").status_code, 409)
        self.assertEqual(len(EVENTS), 1)

    def test_draw_and_unchanged_correction(self):
        self.client.post("/matches/3/start")
        self.client.post("/matches/3/finish", json={"home": 1, "away": 1})
        self.assertEqual(EVENTS[-1]["outcome"], "draw")
        self.assertEqual(self.client.post("/matches/3/correct-result", json={"home": 1, "away": 1}).status_code, 409)
        self.assertEqual(len(EVENTS), 2)


if __name__ == "__main__":
    unittest.main()
