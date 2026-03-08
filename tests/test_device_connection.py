"""Tests for cloud connection indicators on WebastoDevice."""

import unittest

from pywebasto.device import WebastoDevice


class TestDeviceConnectionState(unittest.TestCase):
    """Validate connection_lost/is_connected mapping."""

    def test_last_data_connection_lost_false_means_connected(self) -> None:
        device = WebastoDevice("id-1", "Device")
        device.last_data = {
            "temperature": "18C",
            "voltage": "12.4V",
            "location": {"state": "OFF"},
            "connection_lost": False,
            "outputs": [{"line": "OUTH", "state": "OFF", "icon": "car_heat"}],
        }

        self.assertFalse(device.connection_lost)
        self.assertTrue(device.is_connected)

    def test_last_data_connection_lost_true_means_disconnected(self) -> None:
        device = WebastoDevice("id-1", "Device")
        device.last_data = {
            "temperature": "18C",
            "voltage": "12.4V",
            "location": {"state": "OFF"},
            "connection_lost": True,
            "outputs": [{"line": "OUTH", "state": "OFF", "icon": "car_heat"}],
        }

        self.assertTrue(device.connection_lost)
        self.assertFalse(device.is_connected)

    def test_dev_data_connection_lost_updates_state(self) -> None:
        device = WebastoDevice("id-1", "Device")
        device.dev_data = {
            "connection_lost": True,
            "subscription": {"expiration": 1766325670},
        }
        self.assertTrue(device.connection_lost)
        self.assertFalse(device.is_connected)

        device.dev_data = {
            "connection_lost": False,
            "subscription": {"expiration": 1766325670},
        }
        self.assertFalse(device.connection_lost)
        self.assertTrue(device.is_connected)


if __name__ == "__main__":
    unittest.main()
