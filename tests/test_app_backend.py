"""Tests for Android app backend behavior."""

import json
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from pywebasto import AppCredentials, WebastoConnect
from pywebasto.consts import APP_CLIENT_INFO
from pywebasto.device import WebastoDevice
from pywebasto.enums import Outputs
from pywebasto.exceptions import InvalidRequestException, UnauthorizedException
from pywebasto.timer import SimpleTimer


class TestAppCredentials(IsolatedAsyncioTestCase):
    """Validate app credential loading and generation."""

    async def test_explicit_credentials_are_used(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")

        await cloud._ensure_app_credentials()

        self.assertEqual(cloud.client_id, "client")
        self.assertEqual(cloud.client_secret, "secret")
        self.assertTrue(cloud.uses_app_backend)

    async def test_connect_does_not_require_context_manager(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._send_client_info = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]

        await cloud.connect()
        await cloud.close()

        cloud._send_client_info.assert_awaited_once()
        cloud.update.assert_awaited_once_with(force=True)

    async def test_credentials_load_callback_is_used(self) -> None:
        cloud = WebastoConnect(
            credential_load=lambda: AppCredentials("client", "secret")
        )

        await cloud._ensure_app_credentials()

        self.assertEqual(cloud.client_id, "client")
        self.assertEqual(cloud.client_secret, "secret")

    async def test_credentials_file_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "credentials.json"
            path.write_text(
                json.dumps({"client_id": "client", "client_secret": "secret"}),
                encoding="utf-8",
            )
            cloud = WebastoConnect(credential_store_path=str(path))

            await cloud._ensure_app_credentials()

        self.assertEqual(cloud.client_id, "client")
        self.assertEqual(cloud.client_secret, "secret")

    async def test_generated_credentials_are_saved(self) -> None:
        saved: list[AppCredentials] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "credentials.json"
            cloud = WebastoConnect(
                credential_store_path=str(path),
                credential_save=lambda credentials: saved.append(credentials),
            )
            cloud._app_call = AsyncMock(side_effect=["client", "200 OK"])  # type: ignore[method-assign]

            await cloud._ensure_app_credentials()

            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(cloud.client_id, "client")
        self.assertEqual(data["client_id"], "client")
        self.assertEqual(saved[0].client_id, "client")
        self.assertEqual(len(saved[0].client_secret), 32)
        self.assertEqual(
            [
                (
                    "GET",
                    "/remuc/mobile-api/client_id",
                ),
                (
                    "POST",
                    "/remuc/mobile-api/client/client/register",
                ),
            ],
            [call.args[:2] for call in cloud._app_call.call_args_list],
        )
        self.assertFalse(cloud._app_call.call_args_list[0].kwargs["auth"])
        self.assertFalse(cloud._app_call.call_args_list[1].kwargs["auth"])
        self.assertEqual(
            cloud._app_call.call_args_list[1].kwargs["extra_headers"],
            {"Content-Type": "application/json"},
        )


class TestAppBackendCalls(IsolatedAsyncioTestCase):
    """Validate app endpoint paths and payloads."""

    async def test_app_headers_include_client_secret_and_user_agent(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")

        headers = cloud.assemble_app_headers()

        self.assertEqual(headers["Authorization"], "secret")
        self.assertEqual(headers["User-Agent"], "Google-HTTP-Java-Client/1.24.1 (gzip)")
        self.assertEqual(headers["Accept-Encoding"], "gzip")
        self.assertNotIn("Content-Type", headers)

    async def test_client_info_uses_remote_info_endpoint(self) -> None:
        cloud = WebastoConnect(
            client_id="client",
            client_secret="secret",
            client_info="pywebasto test 123",
        )
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]

        await cloud._send_client_info()

        cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remote/client/client/info",
            payload="pywebasto test 123",
        )

    async def test_default_client_info_uses_package_name(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")

        self.assertEqual(cloud._get_client_info(), APP_CLIENT_INFO)

    async def test_set_output_main_uses_app_cmd(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]
        device = WebastoDevice("123", "Heater")

        await cloud.set_output_main(device, True)

        cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remote/client/client/device/123/cmd",
            payload="OUT H ON",
        )
        cloud.update.assert_awaited_once_with(device_id="123", force=True)

    async def test_ventilation_mode_uses_heatermode_endpoint(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]
        device = WebastoDevice("123", "Heater")

        await cloud.ventilation_mode(device, True)

        cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remuc/mobile-api/client/client/heatermode",
            payload='{"dev_id":"123","mode":1}',
        )

    async def test_save_timers_uses_timers2_output_id(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]
        device = WebastoDevice("123", "Heater")
        timers = [SimpleTimer(start=135, duration=1200, repeat=0, enabled=False)]

        await cloud.save_timers(device, timers, line=Outputs.HEATER)

        cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remote/client/client/device/123/timers2",
            payload=(
                '{"output":"H","timers":[{"type":"simple","start":135,'
                '"duration":1200,"repeat":0,"enabled":false}]}'
            ),
        )

    async def test_location_services_uses_app_endpoint(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]
        device = WebastoDevice("123", "Heater")

        await cloud.set_location_services(device, False)

        cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remuc/mobile-api/client/client/location-services",
            payload='{"dev_id":"123","state":"OFF"}',
        )

    async def test_pending_device_rejects_commands(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        device = WebastoDevice("123", "Heater")
        device.app_data = {"id": "123", "assocStatus": "pending"}

        with self.assertRaises(InvalidRequestException):
            await cloud.set_output_main(device, True)


class TestAppDeviceParsing(IsolatedAsyncioTestCase):
    """Validate app data parsing and webapi bootstrap behavior."""

    async def test_update_parses_app_device(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock(
            return_value={
                "devices": [
                    {
                        "id": "123",
                        "alias": "Car",
                        "assocStatus": "ok",
                        "temperature": "18C",
                        "voltage": "12.4V",
                        "location": {"state": "OFF"},
                        "connection_lost": False,
                        "subscription": {"expiration": 1766325670},
                        "outputs": [
                            {
                                "line": "OUTH",
                                "state": "OFF",
                                "icon": "car_heat",
                                "name": "Heater",
                                "timers": [],
                            }
                        ],
                        "disabled_outputs": [],
                    }
                ]
            }
        )  # type: ignore[method-assign]

        await cloud.update(force=True)

        self.assertIn("123", cloud.devices)
        self.assertEqual(cloud.devices["123"].name, "Car")
        self.assertEqual(cloud.devices["123"].temperature, 18)
        self.assertFalse(cloud.devices["123"].pending_approval)

    async def test_pending_device_is_not_parsed_as_normal_data(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock(
            return_value={"devices": [{"id": "123", "assocStatus": "pending"}]}
        )  # type: ignore[method-assign]

        await cloud.update(force=True)

        self.assertTrue(cloud.devices["123"].pending_approval)
        self.assertEqual(cloud.devices["123"].temperature, 0)

    async def test_webapi_top_level_id_and_check_id_start_association(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._hssess_webclient = "cookie"
        cloud.devices = {}
        cloud._call = AsyncMock(  # type: ignore[method-assign]
            return_value={
                "id": "123",
                "check_id": "abcd",
                "alias": "Car",
                "account_info": {"devices": [["123", "Car"]]},
            }
        )
        cloud.association_status = AsyncMock(return_value="none")  # type: ignore[method-assign]
        cloud.associate_device = AsyncMock(return_value="pending")  # type: ignore[method-assign]

        await cloud._start_missing_associations_from_webapi()

        cloud.associate_device.assert_awaited_once_with("123", "abcd")

    async def test_webapi_only_settings_require_webapi_credentials(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        device = WebastoDevice("123", "Heater")

        with self.assertRaises(UnauthorizedException):
            await cloud.set_low_voltage_cutoff(device, 11.5)


class TestAppUpdateThrottle(IsolatedAsyncioTestCase):
    """Validate app update throttling."""

    async def test_update_uses_cache_within_refresh_interval(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._update_all_devices = AsyncMock()  # type: ignore[method-assign]

        await cloud.update()
        await cloud.update()

        cloud._update_all_devices.assert_awaited_once()

    async def test_force_update_bypasses_cache(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._update_all_devices = AsyncMock()  # type: ignore[method-assign]

        await cloud.update()
        await cloud.update(force=True)

        self.assertEqual(cloud._update_all_devices.await_count, 2)
