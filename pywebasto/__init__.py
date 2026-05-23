"""Module for interfacing with Webasto Connect."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable
import json
import logging
from pathlib import Path
import sys
from time import monotonic
from uuid import uuid4

import aiohttp

from .device import WebastoDevice

from .consts import (
    API_URL,
    APP_API_URL,
    APP_USER_AGENT,
    CMD_AUX1_OFF,
    CMD_AUX1_ON,
    CMD_AUX2_OFF,
    CMD_AUX2_ON,
    CMD_HEATER_OFF,
    CMD_HEATER_ON,
    CMD_VENTILATION_OFF,
    CMD_VENTILATION_ON,
    USER_AGENT,
)
from .enums import Outputs, Request
from .exceptions import (
    ForbiddenException,
    InvalidRequestException,
    InvalidResponseException,
    TooManyRequestsException,
    UnauthorizedException,
)
from .timer import SimpleTimer

if sys.version_info < (3, 11, 0):
    sys.exit("The pywebasto module requires Python 3.11.0 or later")

__all__ = ["AppCredentials", "WebastoConnect", "SimpleTimer"]

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=60, connect=10, sock_read=45)
DEFAULT_REFRESH_INTERVAL = 60
MAX_READ_RETRIES = 2
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
RETRYABLE_REQUESTS = {
    Request.LOGIN,
    Request.GET_DATA,
    Request.GET_DATA_NOPOLL,
    Request.GET_SETTINGS,
    Request.CHANGE_DEVICE,
}


@dataclass(slots=True)
class AppCredentials:
    """Client credentials used by the Android app backend."""

    client_id: str
    client_secret: str


class WebastoConnect:
    """Webasto Connect implementation."""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_interval: float = DEFAULT_REFRESH_INTERVAL,
        credential_store_path: str | None = None,
        credential_load: Callable[
            [], AppCredentials | dict | Awaitable[AppCredentials | dict | None] | None
        ]
        | None = None,
        credential_save: Callable[[AppCredentials], Awaitable[None] | None]
        | None = None,
    ) -> None:
        """Initialize the component."""
        self._usn: str | None = username
        self._pwd: str | None = password
        self._client_id: str | None = client_id
        self._client_secret: str | None = client_secret
        self._credential_store_path = (
            Path(credential_store_path) if credential_store_path is not None else None
        )
        self._credential_load = credential_load
        self._credential_save = credential_save
        self._hssess: str | None = None
        self._hssess_webclient: str | None = None
        self._data: dict | None = None
        self._session: aiohttp.ClientSession | None = None
        self._refresh_interval = refresh_interval
        self._last_full_update: float | None = None
        self._last_device_update: dict[str, float] = {}
        self._update_lock = asyncio.Lock()

        self.devices: dict[str, WebastoDevice] = {}

    @property
    def client_id(self) -> str | None:
        """Return the app client id."""
        return self._client_id

    @property
    def client_secret(self) -> str | None:
        """Return the app client secret."""
        return self._client_secret

    @property
    def uses_app_backend(self) -> bool:
        """Return whether app backend credentials are available."""
        return self._client_id is not None and self._client_secret is not None

    @property
    def uses_webapi_session(self) -> bool:
        """Return whether a web API session cookie is available."""
        return self._hssess is not None or self._hssess_webclient is not None

    async def connect(self) -> None:
        """Connect to the API."""
        if (self._usn is None) != (self._pwd is None):
            raise InvalidRequestException("Both username and password must be provided")

        await self._ensure_app_credentials()
        if self._usn is not None and self._pwd is not None:
            await self._ensure_webapi_session()

        await self.update(force=True)
        if self.uses_webapi_session:
            await self._start_missing_associations_from_webapi()
            await self.update(force=True)

    def assemble_headers(self) -> dict:
        """Generate headers."""
        _headers: dict = {"User-Agent": USER_AGENT}

        if isinstance(self._hssess, type(None)) and isinstance(
            self._hssess_webclient, type(None)
        ):
            pass
        else:
            if isinstance(self._hssess_webclient, type(None)):
                _headers.update({"Cookie": f"hssess={self._hssess};"})
            else:
                _headers.update(
                    {"Cookie": f"hssess-webclient={self._hssess_webclient};"}
                )

        return _headers

    def _handle_cookies(self, response: aiohttp.ClientResponse) -> None:
        """Handle cookies from the response."""
        hssess_cookie = response.cookies.get("hssess")
        if hssess_cookie is not None:
            self._hssess = hssess_cookie.value

        hssess_webclient_cookie = response.cookies.get("hssess-webclient")
        if hssess_webclient_cookie is not None:
            self._hssess_webclient = hssess_webclient_cookie.value

    def assemble_app_headers(self, auth: bool = True) -> dict:
        """Generate headers for the Android app backend."""
        headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": APP_USER_AGENT,
        }
        if auth:
            if self._client_secret is None:
                raise UnauthorizedException("App client secret is missing")
            headers["Authorization"] = self._client_secret
        return headers

    def _credentials_from_dict(self, data: dict | AppCredentials | None) -> None:
        """Set app credentials from a simple object or dictionary."""
        if data is None:
            return
        if isinstance(data, AppCredentials):
            self._client_id = data.client_id
            self._client_secret = data.client_secret
            return
        self._client_id = data.get("client_id")
        self._client_secret = data.get("client_secret")

    def _load_credentials_from_file(self) -> None:
        """Load app credentials from the configured JSON file."""
        if self._credential_store_path is None:
            return
        if not self._credential_store_path.exists():
            return
        with self._credential_store_path.open(encoding="utf-8") as credential_file:
            self._credentials_from_dict(json.load(credential_file))

    async def _save_credentials(self) -> None:
        """Save app credentials through the configured store."""
        if self._client_id is None or self._client_secret is None:
            return

        credentials = AppCredentials(self._client_id, self._client_secret)
        if self._credential_save is not None:
            result = self._credential_save(credentials)
            if isawaitable(result):
                await result

        if self._credential_store_path is not None:
            with self._credential_store_path.open("w", encoding="utf-8") as file:
                json.dump(
                    {
                        "client_id": credentials.client_id,
                        "client_secret": credentials.client_secret,
                    },
                    file,
                    indent=2,
                )
                file.write("\n")

    async def _ensure_app_credentials(self) -> None:
        """Ensure app client credentials exist."""
        if self.uses_app_backend:
            return

        if self._credential_load is not None:
            loaded = self._credential_load()
            if isawaitable(loaded):
                loaded = await loaded
            self._credentials_from_dict(loaded)
        if not self.uses_app_backend:
            self._load_credentials_from_file()
        if self.uses_app_backend:
            return

        client_id = await self._app_call(
            "GET",
            "/remuc/mobile-api/client_id",
            auth=False,
        )
        if not isinstance(client_id, str) or client_id == "":
            raise InvalidResponseException("Could not get app client id")

        self._client_id = client_id.strip()
        self._client_secret = uuid4().hex
        payload = json.dumps({"secret": self._client_secret}, separators=(",", ":"))
        await self._app_call(
            "POST",
            f"/remuc/mobile-api/client/{self._client_id}/register",
            payload=payload,
            auth=False,
            extra_headers={"Content-Type": "application/json"},
        )
        await self._save_credentials()

    async def _ensure_webapi_session(self) -> None:
        """Ensure a web API session exists when username/password were provided."""
        if self.uses_webapi_session:
            return
        if self._usn is None or self._pwd is None:
            raise UnauthorizedException("Web API username/password is required")
        await self._call(Request.LOGIN, {"username": self._usn, "password": self._pwd})
        if self._hssess is None and self._hssess_webclient is None:
            raise InvalidResponseException("Login failed, no session cookie received")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Create or reuse an HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._session

    @staticmethod
    def _is_retryable_request(api_type: Request) -> bool:
        """Return whether a request is safe to retry."""
        return api_type in RETRYABLE_REQUESTS

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        """Return exponential backoff delay in seconds."""
        return float(2**attempt)

    async def close(self) -> None:
        """Close any open HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "WebastoConnect":
        """Allow async context manager usage."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close resources when leaving async context."""
        await self.close()

    async def _call(
        self,
        api_type: Request,
        payload: dict | str | None = None,
        extra_headers: dict | None = None,
    ) -> dict | None:
        """Make an API request."""

        if isinstance(payload, type(None)):
            payload = {}

        headers = self.assemble_headers()
        if isinstance(extra_headers, dict):
            headers.update(extra_headers)

        max_attempts = (
            MAX_READ_RETRIES + 1 if self._is_retryable_request(api_type) else 1
        )

        for attempt in range(max_attempts):
            session = await self._get_session()
            try:
                start = monotonic()
                async with session.post(
                    f"{API_URL}{api_type.value}",
                    headers=headers,
                    data=payload,
                ) as response:
                    self._handle_cookies(response)
                    elapsed = monotonic() - start
                    LOGGER.debug(
                        "Request %s completed in %.3f seconds with status %s",
                        api_type.name,
                        elapsed,
                        response.status,
                    )

                    if response.status != 200:
                        if response.status == 401:
                            raise UnauthorizedException(
                                "Username or password incorrect"
                            )
                        if response.status == 403:
                            raise ForbiddenException(
                                "Access to the requested resource is forbidden"
                            )
                        if response.status == 429:
                            raise TooManyRequestsException(
                                "Too many requests - you are being rate limited"
                            )
                        if (
                            response.status in RETRYABLE_STATUS_CODES
                            and attempt < max_attempts - 1
                        ):
                            delay = self._backoff_seconds(attempt)
                            LOGGER.debug(
                                "Retrying %s after HTTP %s in %.1f seconds (attempt %s/%s)",
                                api_type.name,
                                response.status,
                                delay,
                                attempt + 1,
                                max_attempts,
                            )
                            await asyncio.sleep(delay)
                            continue

                        text = await response.text()
                        raise InvalidRequestException(
                            f"API reported {response.status}: {text}"
                        )

                    if "GET" in api_type.name:
                        try:
                            return await response.json(content_type=None)
                        except (aiohttp.ContentTypeError, json.JSONDecodeError) as err:
                            text = await response.text()
                            raise InvalidResponseException(
                                f"Invalid JSON response for {api_type.name}: {text}"
                            ) from err

                    return None
            except (
                aiohttp.ClientConnectionError,
                aiohttp.ClientOSError,
                aiohttp.ServerTimeoutError,
                asyncio.TimeoutError,
            ) as err:
                if attempt < max_attempts - 1:
                    delay = self._backoff_seconds(attempt)
                    LOGGER.debug(
                        "Retrying %s after network error in %.1f seconds (attempt %s/%s): %s",
                        api_type.name,
                        delay,
                        attempt + 1,
                        max_attempts,
                        err.__class__.__name__,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise InvalidRequestException(f"API request failed: {err}") from err

        raise InvalidRequestException("API request failed after retries")

    async def _app_call(
        self,
        method: str,
        path: str,
        payload: str | None = None,
        auth: bool = True,
        expect_json: bool = False,
        extra_headers: dict | None = None,
    ) -> dict | str | None:
        """Make an app backend request."""
        headers = self.assemble_app_headers(auth=auth)
        if extra_headers is not None:
            headers.update(extra_headers)
        session = await self._get_session()
        data = payload.encode("utf-8") if payload is not None else None

        try:
            start = monotonic()
            async with session.request(
                method,
                f"{APP_API_URL}{path}",
                headers=headers,
                data=data,
            ) as response:
                elapsed = monotonic() - start
                LOGGER.debug(
                    "App request %s %s completed in %.3f seconds with status %s",
                    method,
                    path,
                    elapsed,
                    response.status,
                )

                text = await response.text()
                if response.status != 200:
                    if response.status == 401:
                        raise UnauthorizedException("App client is unauthorized")
                    if response.status == 403:
                        raise ForbiddenException(
                            "Access to the requested app resource is forbidden"
                        )
                    if response.status == 429:
                        raise TooManyRequestsException(
                            "Too many requests - you are being rate limited"
                        )
                    raise InvalidRequestException(
                        f"App API reported {response.status}: {text}"
                    )

                if expect_json:
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError as err:
                        raise InvalidResponseException(
                            f"Invalid JSON response for app request {path}: {text}"
                        ) from err

                return text
        except (
            aiohttp.ClientConnectionError,
            aiohttp.ClientOSError,
            aiohttp.ServerTimeoutError,
            asyncio.TimeoutError,
        ) as err:
            raise InvalidRequestException(f"App API request failed: {err}") from err

    def _is_update_fresh(self, last_update: float | None) -> bool:
        """Return whether cached data is still fresh enough to reuse."""
        if self._refresh_interval <= 0:
            return False

        if last_update is None:
            return False

        return monotonic() - last_update < self._refresh_interval

    async def update(self, device_id: str | None = None, force: bool = False) -> None:
        """Get current data from Webasto API."""
        async with self._update_lock:
            if isinstance(device_id, type(None)):
                if not force and self._is_update_fresh(self._last_full_update):
                    LOGGER.debug("Skipping update because cached account data is fresh")
                    return

                await self._update_all_devices()
                self._last_full_update = monotonic()
                return

            if not force and self._is_update_fresh(
                self._last_device_update.get(device_id)
            ):
                LOGGER.debug(
                    "Skipping update for device %s because cached data is fresh",
                    device_id,
                )
                return

            # A specific device was requested, only update that one
            await self._update_device_data(device_id)

    async def _update_all_devices(self) -> None:
        """Refresh app account data for all devices."""
        if self._client_id is None:
            raise UnauthorizedException("App client id is missing")

        self._data = await self._app_call(
            "GET",
            f"/remuc/mobile-api/client/{self._client_id}/all?api_v=8",
            expect_json=True,
        )
        if not isinstance(self._data, dict):
            raise InvalidResponseException("Invalid app data response")

        for device_data in self._data.get("devices", []):
            device_id = str(device_data["id"])
            device = self.devices.get(device_id)
            if device is None:
                device = WebastoDevice(
                    device_id,
                    device_data.get("name") or device_data.get("alias") or device_id,
                )

            device.app_data = device_data
            self.devices[device_id] = device
            self._last_device_update[device_id] = monotonic()

            if self.uses_webapi_session and not device.pending_approval:
                await self._update_webapi_device_settings(device_id)

    async def _update_device_data(
        self, device_id: str, switch_device: bool = True
    ) -> None:
        """Refresh data for one device."""
        await self._update_all_devices()
        self._last_device_update[device_id] = monotonic()

    async def _update_webapi_device_settings(self, device_id: str) -> None:
        """Refresh webapi-only settings for one device if available."""
        if not self.uses_webapi_session:
            return
        if device_id not in self.devices:
            return

        await self._change_device(device_id)
        self.devices[device_id].settings = await self._call(Request.GET_SETTINGS)

    async def _change_device(self, device_id: str) -> None:
        """Change the active device."""
        await self._call(Request.CHANGE_DEVICE, {"device": device_id})

    def _list_devices(self) -> list[dict]:
        """List all devices associated with the account."""
        device_list = []
        if isinstance(self._data, type(None)):
            return device_list

        account_info = self._data.get("account_info", {})
        for device in account_info.get("devices", []):
            if isinstance(device, dict):
                device_list.append(
                    {
                        "id": str(
                            device.get("id")
                            or device.get("device_id")
                            or device.get("dev_id")
                        ),
                        "name": device.get("name", ""),
                        "check_id": device.get("check_id") or device.get("checkId"),
                    }
                )
            else:
                device_list.append(
                    {
                        "id": str(device[0]),
                        "name": device[1],
                        "check_id": device[2] if len(device) > 2 else None,
                    }
                )

        return device_list

    def _list_webapi_association_devices(self) -> list[dict]:
        """List webapi devices with check id when available."""
        devices = []
        if not isinstance(self._data, dict):
            return devices

        if self._data.get("id") and self._data.get("check_id"):
            devices.append(
                {
                    "id": str(self._data["id"]),
                    "name": self._data.get("alias", ""),
                    "check_id": self._data["check_id"],
                }
            )

        for device in self._list_devices():
            if any(existing["id"] == device["id"] for existing in devices):
                continue
            devices.append(device)

        return devices

    async def _start_missing_associations_from_webapi(self) -> None:
        """Start app association for webapi devices missing from app data."""
        self._data = await self._call(Request.GET_DATA_NOPOLL)
        for device in self._list_webapi_association_devices():
            device_id = device["id"]
            check_id = device.get("check_id")
            if device_id in self.devices:
                continue
            if not check_id:
                LOGGER.debug(
                    "Skipping auto-association for %s because check id is missing",
                    device_id,
                )
                continue
            status = await self.association_status(device_id)
            if status in ("master", "pending"):
                continue
            await self.associate_device(device_id, str(check_id))

    @staticmethod
    def _extract_simple_timers_from_data(
        data: dict | None, line: str
    ) -> list[SimpleTimer]:
        """Extract simple timers for a specific output line from API data."""
        if not isinstance(data, dict):
            return []

        timers: list[SimpleTimer] = []
        for section in ("outputs", "disabled_outputs"):
            outputs = data.get(section)
            if not isinstance(outputs, list):
                continue

            for output in outputs:
                if not isinstance(output, dict):
                    continue
                if output.get("line") != line:
                    continue

                output_timers = output.get("timers")
                if not isinstance(output_timers, list):
                    continue

                for timer_data in output_timers:
                    if not isinstance(timer_data, dict):
                        continue
                    if timer_data.get("type") != "simple":
                        continue

                    try:
                        timers.append(SimpleTimer.from_api_dict(timer_data))
                    except (KeyError, TypeError, ValueError) as err:
                        raise InvalidRequestException(
                            f"Invalid simple timer data in response: {err}"
                        ) from err

        return timers

    def _device_path(self, device_id: str, endpoint: str) -> str:
        """Build an app remote device path."""
        if self._client_id is None:
            raise UnauthorizedException("App client id is missing")
        return f"/remote/client/{self._client_id}/device/{device_id}/{endpoint}"

    @staticmethod
    def _raise_if_pending(device: WebastoDevice) -> None:
        """Reject operations for devices waiting for approval."""
        if device.pending_approval:
            raise InvalidRequestException("Device is waiting for association approval")

    async def _send_device_command(self, device: WebastoDevice, command: str) -> None:
        """Send a raw app command to a device."""
        await self._app_call(
            "POST",
            self._device_path(device.device_id, "cmd"),
            payload=command,
        )

    async def get_timers(
        self, device: WebastoDevice, line: Outputs = Outputs.HEATER
    ) -> list[SimpleTimer]:
        """Get simple timers for an output line from the latest API data."""
        if device.pending_approval:
            return []
        await self.update(device_id=device.device_id, force=True)
        data = self.devices[device.device_id].last_data
        return self._extract_simple_timers_from_data(data, line.value)

    async def save_timers(
        self,
        device: WebastoDevice,
        timers: list[SimpleTimer],
        line: Outputs = Outputs.HEATER,
    ) -> None:
        """Save a full simple-timer list using the app `timers2` contract."""
        self._raise_if_pending(device)

        payload = {
            "output": line.value[-1],
            "timers": [timer.to_api_dict() for timer in timers],
        }
        await self._app_call(
            "POST",
            self._device_path(device.device_id, "timers2"),
            payload=json.dumps(payload, separators=(",", ":")),
        )
        await self.update(device_id=device.device_id, force=True)

    async def get_simple_timers(
        self, device: WebastoDevice, line: Outputs = Outputs.HEATER
    ) -> list[SimpleTimer]:
        """Backward-compatible alias for `get_timers`."""
        return await self.get_timers(device=device, line=line)

    async def save_simple_timers(
        self,
        device: WebastoDevice,
        timers: list[SimpleTimer],
        line: Outputs = Outputs.HEATER,
    ) -> None:
        """Backward-compatible alias for `save_timers`."""
        await self.save_timers(device=device, timers=timers, line=line)

    async def set_output_main(self, device: WebastoDevice, state: bool) -> None:
        """Turn on or off the heater or ventilation."""
        self._raise_if_pending(device)

        if state:
            if device.is_ventilation:
                await self._send_device_command(device, CMD_VENTILATION_ON)
            else:
                await self._send_device_command(device, CMD_HEATER_ON)
        else:
            if device.is_ventilation:
                await self._send_device_command(device, CMD_VENTILATION_OFF)
            else:
                await self._send_device_command(device, CMD_HEATER_OFF)
        await self.update(device_id=device.device_id, force=True)

    async def set_output_aux1(self, device: WebastoDevice, state: bool) -> None:
        """Turn on or off the aux1 output."""
        self._raise_if_pending(device)

        if state:
            await self._send_device_command(device, CMD_AUX1_ON)
        else:
            await self._send_device_command(device, CMD_AUX1_OFF)
        await self.update(device_id=device.device_id, force=True)

    async def set_output_aux2(self, device: WebastoDevice, state: bool) -> None:
        """Turn on or off the aux2 output."""
        self._raise_if_pending(device)

        if state:
            await self._send_device_command(device, CMD_AUX2_ON)
        else:
            await self._send_device_command(device, CMD_AUX2_OFF)
        await self.update(device_id=device.device_id, force=True)

    async def ventilation_mode(self, device: WebastoDevice, state: bool) -> None:
        """Turn ventilation mode on or off."""
        self._raise_if_pending(device)
        payload = {"dev_id": device.device_id, "mode": 1 if state else 0}
        await self._app_call(
            "POST",
            f"/remuc/mobile-api/client/{self._client_id}/heatermode",
            payload=json.dumps(payload, separators=(",", ":")),
        )
        await self.update(device_id=device.device_id, force=True)

    async def associate_device(
        self,
        device_id: str,
        check_id: str,
        message: str = "Association request",
    ) -> str:
        """Start association for a device and return the current status."""
        payload = {"checkId": check_id, "msg": message}
        result = await self._app_call(
            "POST",
            self._device_path(device_id, "assoc3"),
            payload=json.dumps(payload, separators=(",", ":")),
        )
        return "" if result is None else str(result).strip()

    async def association_status(self, device_id: str) -> str:
        """Get the app association status for a device."""
        result = await self._app_call(
            "GET",
            self._device_path(device_id, "assocstatus2"),
        )
        return "" if result is None else str(result).strip()

    async def disassociate_device(self, device: WebastoDevice | str) -> None:
        """Remove a device association from this app client."""
        device_id = device.device_id if isinstance(device, WebastoDevice) else device
        if self._client_id is None:
            raise UnauthorizedException("App client id is missing")
        await self._app_call(
            "POST",
            self._device_path(device_id, "setassoc"),
            payload=f"{self._client_id} none",
        )
        self.devices.pop(device_id, None)

    async def set_location_services(self, device: WebastoDevice, state: bool) -> None:
        """Enable or disable app location services for a device."""
        payload = {"dev_id": device.device_id, "state": "ON" if state else "OFF"}
        await self._app_call(
            "POST",
            f"/remuc/mobile-api/client/{self._client_id}/location-services",
            payload=json.dumps(payload, separators=(",", ":")),
        )
        await self.update(device_id=device.device_id, force=True)

    async def get_location_text(self, device: WebastoDevice) -> str:
        """Read the raw app location2 text for a device."""
        result = await self._app_call(
            "GET",
            self._device_path(device.device_id, "location2"),
        )
        return "" if result is None else str(result)

    async def set_main_timeout(
        self,
        device: WebastoDevice,
        heater: int | None = None,
        ventilation: int | None = None,
    ) -> None:
        """Sets timeout of main output port in seconds."""
        await self._ensure_webapi_session()
        if not isinstance(heater, type(None)):
            device.timeout_heat = heater

        if not isinstance(ventilation, type(None)):
            device.timeout_vent = ventilation

        await self._change_device(device_id=device.device_id)

        vent_sec = device.timeout_vent % (24 * 3600)
        vent_h = vent_sec // 3600
        vent_sec = vent_sec % 3600
        vent_m = vent_sec // 60

        heat_sec = device.timeout_heat % (24 * 3600)
        heat_h = heat_sec // 3600
        heat_sec = heat_sec % 3600
        heat_m = heat_sec // 60

        payload = {
            "device_settings": {
                "webasto_emul_mode": "thermoconnect",
                "OUTV_timeout_on": True,
                "OUTV_timeout_h": vent_h,
                "OUTV_timeout_min": vent_m,
                "OUTH_timeout_on": True,
                "OUTH_timeout_h": heat_h,
                "OUTH_timeout_min": heat_m,
            },
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        await self._call(Request.POST_SETTING, json.dumps(payload))
        await self.update(device_id=device.device_id, force=True)

    async def set_aux_timeout(
        self,
        device: WebastoDevice,
        timeout: int,
        aux: Outputs = Outputs.AUX1,
    ) -> None:
        """Sets timeout of an AUX port in seconds."""
        await self._ensure_webapi_session()
        await self._change_device(device_id=device.device_id)

        if aux == Outputs.AUX1:
            device.timeout_aux1 = timeout
        elif aux == Outputs.AUX2:
            device.timeout_aux2 = timeout

        heat_sec = timeout % (24 * 3600)
        heat_h = heat_sec // 3600
        heat_sec = heat_sec % 3600
        heat_m = heat_sec // 60

        data = {
            "device_settings": {
                f"{aux.value}_function": "enabled",
                f"{aux.value}_timeout_on": True,
                f"{aux.value}_timeout_h": heat_h,
                f"{aux.value}_timeout_min": heat_m,
            },
            "service_settings": {
                f"{aux.value}_on": True,
                f"{aux.value}_name": (
                    device.output_aux1_name
                    if aux == Outputs.AUX1
                    else device.output_aux2_name
                ),
                f"{aux.value}_icon": (
                    device.icon_aux1 if aux == Outputs.AUX1 else device.icon_aux2
                ),
            },
            "location_events": None,
            "air_heater": {},
        }

        await self._call(Request.POST_SETTING, json.dumps(data))
        await self._update_device_data(device.device_id, switch_device=False)

    async def set_low_voltage_cutoff(self, device: WebastoDevice, value: float) -> None:
        """Set the low voltage cutoff value."""
        await self._ensure_webapi_session()
        await self._change_device(device_id=device.device_id)

        payload = {
            "device_settings": {"low_voltage_cutoff": value},
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        await self._call(Request.POST_SETTING, json.dumps(payload))
        await self._update_device_data(device.device_id, switch_device=False)

    async def set_temperature_compensation(
        self, device: WebastoDevice, value: float
    ) -> None:
        """Set the temperature compensation value."""
        await self._ensure_webapi_session()
        await self._change_device(device_id=device.device_id)

        payload = {
            "device_settings": {"ext_temp_comp": value},
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        await self._call(Request.POST_SETTING, json.dumps(payload, indent=4))
        await self._update_device_data(device.device_id, switch_device=False)
