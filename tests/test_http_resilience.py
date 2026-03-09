"""Tests for HTTP retry behavior and session handling."""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import aiohttp

from pywebasto import WebastoConnect
from pywebasto.enums import Request
from pywebasto.exceptions import InvalidRequestException


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

    async def test_close_closes_persistent_session(self) -> None:
        cloud = WebastoConnect("user", "pass")
        session = _FakeSession([])
        cloud._session = session  # type: ignore[assignment]

        await cloud.close()

        self.assertTrue(session.closed)
