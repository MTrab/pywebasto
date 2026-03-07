"""Tests for simple timer parsing and serialization."""

import unittest

from pywebasto import WebastoConnect
from pywebasto.timer import SimpleTimer


class TestSimpleTimer(unittest.TestCase):
    """Validate simple timer behavior."""

    def test_to_api_dict_contains_required_fields(self) -> None:
        timer = SimpleTimer(
            start=830,
            duration=5400,
            repeat=31,
            latitude="1.0",
            longitude="2.0",
            enabled=False,
        )

        payload = timer.to_api_dict()
        self.assertEqual(payload["type"], "simple")
        self.assertEqual(payload["start"], 830)
        self.assertEqual(payload["duration"], 5400)
        self.assertEqual(payload["repeat"], 31)
        self.assertEqual(payload["location"], {"lat": "1.0", "lon": "2.0"})
        self.assertFalse(payload["enabled"])

    def test_validate_rejects_non_positive_start(self) -> None:
        timer = SimpleTimer(
            start=0,
            duration=5400,
            repeat=31,
            latitude="1.0",
            longitude="2.0",
        )
        with self.assertRaises(ValueError):
            timer.validate()

    def test_to_api_dict_allows_missing_location(self) -> None:
        timer = SimpleTimer(
            start=830,
            duration=5400,
            repeat=31,
            enabled=True,
        )
        payload = timer.to_api_dict()
        self.assertNotIn("location", payload)

    def test_validate_rejects_partial_location(self) -> None:
        timer = SimpleTimer(
            start=830,
            duration=5400,
            repeat=31,
            latitude="1.0",
            longitude=None,
        )
        with self.assertRaises(ValueError):
            timer.validate()


class TestTimerExtraction(unittest.TestCase):
    """Validate extraction from GET_DATA-like payloads."""

    def test_extract_from_outputs_and_disabled_outputs(self) -> None:
        payload = {
            "outputs": [
                {
                    "line": "OUTH",
                    "timers": [
                        {
                            "type": "simple",
                            "start": 1380,
                            "duration": 1800,
                            "repeat": 72,
                            "location": {"lat": "A", "lon": "B"},
                            "enabled": True,
                        }
                    ],
                }
            ],
            "disabled_outputs": [
                {
                    "line": "OUTH",
                    "timers": [
                        {
                            "type": "simple",
                            "start": 255,
                            "duration": 5400,
                            "repeat": 0,
                            "location": {"lat": "A", "lon": "B"},
                            "enabled": False,
                        }
                    ],
                }
            ],
        }

        timers = WebastoConnect._extract_simple_timers_from_data(payload, "OUTH")
        self.assertEqual(len(timers), 2)
        self.assertEqual(timers[0].start, 1380)
        self.assertEqual(timers[1].start, 255)
        self.assertFalse(timers[1].enabled)

    def test_extract_ignores_non_simple_timers(self) -> None:
        payload = {
            "outputs": [
                {
                    "line": "OUTH",
                    "timers": [
                        {
                            "type": "smart",
                            "start": 830,
                            "repeat": 30,
                            "maxDuration": 3000,
                            "comfortLevel": 5,
                            "departure": 830,
                            "location": {"lat": "A", "lon": "B"},
                        }
                    ],
                }
            ]
        }

        timers = WebastoConnect._extract_simple_timers_from_data(payload, "OUTH")
        self.assertEqual(timers, [])

    def test_extract_handles_simple_timer_without_location(self) -> None:
        payload = {
            "outputs": [
                {
                    "line": "OUTH",
                    "timers": [
                        {
                            "type": "simple",
                            "start": 1221,
                            "duration": 4200,
                            "repeat": 16,
                            "enabled": True,
                        }
                    ],
                }
            ]
        }

        timers = WebastoConnect._extract_simple_timers_from_data(payload, "OUTH")
        self.assertEqual(len(timers), 1)
        self.assertIsNone(timers[0].latitude)
        self.assertIsNone(timers[0].longitude)

    def test_extract_for_outv_line(self) -> None:
        payload = {
            "outputs": [
                {
                    "line": "OUTV",
                    "timers": [
                        {
                            "type": "simple",
                            "start": 900,
                            "duration": 3600,
                            "repeat": 16,
                            "enabled": False,
                        }
                    ],
                }
            ]
        }

        timers = WebastoConnect._extract_simple_timers_from_data(payload, "OUTV")
        self.assertEqual(len(timers), 1)
        self.assertEqual(timers[0].start, 900)


if __name__ == "__main__":
    unittest.main()
