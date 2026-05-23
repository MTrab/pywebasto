"""Tests for HTTP retry behavior and session handling."""

import asyncio
from time import monotonic
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import aiohttp

from pywebasto import WebastoConnect
from pywebasto.device import WebastoDevice
from pywebasto.enums import Request
from pywebasto.exceptions import InvalidRequestException, TooManyRequestsException


class _FakeResponseContext:
    """Async context manager for mocked aiohttp responses."""

    def __init__(self, response: "_FakeResponse") -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeResponse":
        return self._response

    async def __aexit__(self, *_: object) -> None:
        return None


class _FakeResponse:
    """Minimal aiohttp response-like object."""

    def __init__(self, status: int, json_data: dict | None = None, text_data: str = ""):
        self.status = status
        self._json_data = json_data
        self._text_data = text_data
        self.cookies: dict = {}

    async def json(self, **_: object) -> dict | None:
        return self._json_data

    async def text(self) -> str:
        return self._text_data


class _FakeSession:
    """Minimal aiohttp session-like object with scripted outcomes."""

    def __init__(self, scripted: list[object]) -> None:
        self._scripted = scripted
        self.calls = 0
        self.closed = False

    def post(self, *_: object, **__: object) -> _FakeResponseContext:
        self.calls += 1
        next_item = self._scripted.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return _FakeResponseContext(next_item)

    async def close(self) -> None:
        self.closed = True


class TestHttpResilience(IsolatedAsyncioTestCase):
    """Validate retry strategy for request categories."""

    async def test_retries_transient_status_for_get_requests(self) -> None:
        cloud = WebastoConnect("user", "pass")
        session = _FakeSession(
            [
                _FakeResponse(status=503, text_data="busy"),
                _FakeResponse(status=200, json_data={"ok": True}),
            ]
        )
        cloud._get_session = AsyncMock(return_value=session)  # type: ignore[method-assign]

        with patch("pywebasto.__init__.asyncio.sleep", new=AsyncMock()):
            result = await cloud._call(Request.GET_DATA_NOPOLL)

        self.assertEqual({"ok": True}, result)
        self.assertEqual(session.calls, 2)

    async def test_does_not_retry_non_read_requests(self) -> None:
        cloud = WebastoConnect("user", "pass")
        session = _FakeSession([_FakeResponse(status=503, text_data="busy")])
        cloud._get_session = AsyncMock(return_value=session)  # type: ignore[method-assign]

        with patch("pywebasto.__init__.asyncio.sleep", new=AsyncMock()):
            with self.assertRaises(InvalidRequestException):
                await cloud._call(Request.COMMAND, {"command": "noop"})

        self.assertEqual(session.calls, 1)

    async def test_does_not_retry_rate_limited_requests(self) -> None:
        cloud = WebastoConnect("user", "pass")
        session = _FakeSession([_FakeResponse(status=429, text_data="too many")])
        cloud._get_session = AsyncMock(return_value=session)  # type: ignore[method-assign]

        with patch("pywebasto.__init__.asyncio.sleep", new=AsyncMock()) as sleep_mock:
            with self.assertRaises(TooManyRequestsException):
                await cloud._call(Request.GET_DATA_NOPOLL)

        self.assertEqual(session.calls, 1)
        sleep_mock.assert_not_awaited()

    async def test_retries_network_errors_for_get_requests(self) -> None:
        cloud = WebastoConnect("user", "pass")
        session = _FakeSession(
            [
                aiohttp.ClientConnectionError("offline"),
                _FakeResponse(status=200, json_data={"online": True}),
            ]
        )
        cloud._get_session = AsyncMock(return_value=session)  # type: ignore[method-assign]

        with patch("pywebasto.__init__.asyncio.sleep", new=AsyncMock()):
            result = await cloud._call(Request.GET_DATA)

        self.assertEqual({"online": True}, result)
        self.assertEqual(session.calls, 2)

    async def test_specific_device_update_uses_app_backend(self) -> None:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._call = AsyncMock()  # type: ignore[method-assign]
        cloud._app_call = AsyncMock(  # type: ignore[method-assign]
            return_value={
                "devices": [
                    {
                        "id": "123",
                        "assocStatus": "ok",
                        "temperature": "18C",
                        "voltage": "12.4V",
                        "location": {"state": "OFF"},
                        "subscription": {"expiration": 1766325670},
                        "outputs": [
                            {"line": "OUTH", "state": "OFF", "icon": "car_heat"}
                        ],
                        "disabled_outputs": [],
                    }
                ]
            }
        )

        await cloud.update(device_id="123")

        cloud._app_call.assert_awaited_once_with(
            "GET",
            "/remuc/mobile-api/client/client/all?api_v=8",
            expect_json=True,
        )
        cloud._call.assert_not_awaited()

    async def test_full_update_uses_cached_data_within_refresh_interval(self) -> None:
        cloud = WebastoConnect("user", "pass")
        cloud._update_all_devices = AsyncMock()  # type: ignore[method-assign]

        await cloud.update()
        await cloud.update()

        cloud._update_all_devices.assert_awaited_once()

    async def test_force_update_bypasses_refresh_interval(self) -> None:
        cloud = WebastoConnect("user", "pass")
        cloud._update_all_devices = AsyncMock()  # type: ignore[method-assign]

        await cloud.update()
        await cloud.update(force=True)

        self.assertEqual(cloud._update_all_devices.await_count, 2)

    async def test_device_update_uses_cached_data_within_refresh_interval(self) -> None:
        cloud = WebastoConnect("user", "pass")
        cloud.devices["123"] = WebastoDevice("123", "Heater")  # type: ignore[index]
        cloud._last_device_update["123"] = monotonic()
        cloud._update_device_data = AsyncMock()  # type: ignore[method-assign]

        await cloud.update(device_id="123")

        cloud._update_device_data.assert_not_awaited()

    async def test_zero_refresh_interval_keeps_repeated_updates_enabled(self) -> None:
        cloud = WebastoConnect("user", "pass", refresh_interval=0)
        cloud._update_all_devices = AsyncMock()  # type: ignore[method-assign]

        await cloud.update()
        await cloud.update()

        self.assertEqual(cloud._update_all_devices.await_count, 2)

    async def test_concurrent_full_updates_share_one_refresh(self) -> None:
        cloud = WebastoConnect("user", "pass")

        async def update_all_devices() -> None:
            await asyncio.sleep(0)

        cloud._update_all_devices = AsyncMock(  # type: ignore[method-assign]
            side_effect=update_all_devices
        )

        await asyncio.gather(cloud.update(), cloud.update())

        cloud._update_all_devices.assert_awaited_once()

    async def test_command_refreshes_only_target_device(self) -> None:
        cloud = WebastoConnect("user", "pass")
        cloud._client_id = "client"  # type: ignore[attr-defined]
        cloud._client_secret = "secret"  # type: ignore[attr-defined]
        device = WebastoDevice("123", "Heater")
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        cloud._update_device_data = AsyncMock()  # type: ignore[method-assign]

        await cloud.set_output_main(device, True)

        cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remote/client/client/device/123/cmd",
            payload="OUT H ON",
        )
        cloud._update_device_data.assert_awaited_once_with("123")

    async def test_close_closes_persistent_session(self) -> None:
        cloud = WebastoConnect("user", "pass")
        session = _FakeSession([])
        cloud._session = session  # type: ignore[assignment]

        await cloud.close()

        self.assertTrue(session.closed)
