"""Module for interfacing with Webasto Connect."""

import asyncio
import json
import sys
import threading

import aiohttp

from .device import WebastoDevice

from .consts import (
    API_URL,
    CMD_AUX1_OFF,
    CMD_AUX1_ON,
    CMD_AUX2_OFF,
    CMD_AUX2_ON,
    CMD_HEATER_OFF,
    CMD_HEATER_ON,
    CMD_VENTILATION_OFF,
    CMD_VENTILATION_ON,
)
from .enums import Outputs, Request
from .exceptions import InvalidRequestException, UnauthorizedException

if sys.version_info < (3, 11, 0):
    sys.exit("The pyWorxcloud module requires Python 3.11.0 or later")


class WebastoConnect:
    """Webasto Connect implementation."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the component."""
        self._usn: str = username
        self._pwd: str = password
        self._hssess: str | None = None
        self._hssess_webclient: str | None = None
        self._authorized: bool = False
        self._data: dict | None = None

        self.devices: dict[int, WebastoDevice] = {}

    async def connect(self) -> None:
        """Connect to the API."""
        await self._call(Request.LOGIN, {"username": self._usn, "password": self._pwd})
        if self._authorized:
            await self.update()
        else:
            raise UnauthorizedException("Username or password incorrect")

    def assemble_headers(self) -> dict:
        """Generate headers."""
        _headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
        }

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

    async def _call(
        self, api_type: Request, payload: dict | str | None = None
    ) -> dict | None:
        """Make an API request."""

        if isinstance(payload, type(None)):
            payload = {}

        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{API_URL}{api_type.value}",
                headers=self.assemble_headers(),
                data=payload,
            ) as response:

                # Gem cookies hvis de ikke allerede er sat
                if self._hssess is None and self._hssess_webclient is None:
                    self._hssess = (
                        response.cookies.get("hssess").value
                        if "hssess" in response.cookies
                        else None
                    )
                    self._hssess_webclient = (
                        response.cookies.get("hssess-webclient").value
                        if "hssess-webclient" in response.cookies
                        else None
                    )

                if response.status != 200:
                    if response.status == 401:
                        raise UnauthorizedException("Username or password incorrect")

                    elif response.status == 403:
                        # async pendant til threading.Timer
                        async def retry():
                            await asyncio.sleep(30)
                            await self._call(api_type, payload)

                        asyncio.create_task(retry())

                    else:
                        text = await response.text()
                        raise InvalidRequestException(
                            f"API reported {response.status}: {text}"
                        )
                else:
                    self._authorized = True

                if "GET" in api_type.name:
                    return await response.json(content_type=None)

    async def update(self, device_id: str | None = None) -> None:
        """Get current data from Webasto API."""
        self._data = await self._call(Request.GET_DATA_NOPOLL)
        available_devices = self._list_devices()

        if isinstance(device_id, type(None)):
            # Loop through all devices
            for device in available_devices:
                await self._change_device(device["id"])  # Switch device

                device_data = WebastoDevice(device["id"], device["name"])
                device_data.settings = await self._call(Request.GET_SETTINGS)
                device_data.last_data = await self._call(Request.GET_DATA)
                device_data.dev_data = await self._call(Request.GET_DATA_NOPOLL)

                self.devices.update({device["id"]: device_data})
        else:
            # A specific device was requested, only update that one
            await self._change_device(device_id)  # Switch device
            device_data = self.devices[device_id]  # type: ignore
            device_data.settings = await self._call(Request.GET_SETTINGS)
            device_data.last_data = await self._call(Request.GET_DATA)
            device_data.dev_data = await self._call(Request.GET_DATA_NOPOLL)

            self.devices.update({device_id: device_data})  # type: ignore

    async def _change_device(self, device_id: str) -> None:
        """Change the active device."""
        await self._call(Request.CHANGE_DEVICE, {"device": device_id})

    def _list_devices(self) -> list[dict]:
        """List all devices associated with the account."""
        device_list = []
        if isinstance(self._data, type(None)):
            return device_list

        for device in self._data["account_info"]["devices"]:
            device_list.append({"id": device[0], "name": device[1]})

        return device_list

    async def set_output_main(self, device: WebastoDevice, state: bool) -> None:
        """Turn on or off the heater or ventilation."""
        await self._change_device(device_id=device.device_id)

        if state:
            if device.is_ventilation:
                await self._call(Request.COMMAND, CMD_VENTILATION_ON)
            else:
                await self._call(Request.COMMAND, CMD_HEATER_ON)
        else:
            if device.is_ventilation:
                await self._call(Request.COMMAND, CMD_VENTILATION_OFF)
            else:
                await self._call(Request.COMMAND, CMD_HEATER_OFF)
        await self.update()

    async def set_output_aux1(self, device: WebastoDevice, state: bool) -> None:
        """Turn on or off the aux1 output."""
        await self._change_device(device_id=device.device_id)

        if state:
            await self._call(Request.COMMAND, CMD_AUX1_ON)
        else:
            await self._call(Request.COMMAND, CMD_AUX1_OFF)
        await self.update()

    async def set_output_aux2(self, device: WebastoDevice, state: bool) -> None:
        """Turn on or off the aux2 output."""
        await self._change_device(device_id=device.device_id)

        if state:
            await self._call(Request.COMMAND, CMD_AUX2_ON)
        else:
            await self._call(Request.COMMAND, CMD_AUX2_OFF)
        await self.update()

    async def ventilation_mode(self, device: WebastoDevice, state: bool) -> None:
        """Turn ventilation mode on or off."""
        await self._change_device(device_id=device.device_id)

        vent_sec = device.timeout_vent % (24 * 3600)
        vent_h = vent_sec // 3600
        vent_sec = vent_sec % 3600
        vent_m = vent_sec // 60

        heat_sec = device.timeout_heat % (24 * 3600)
        heat_h = heat_sec // 3600
        heat_sec = heat_sec % 3600
        heat_m = heat_sec // 60

        ventmode = {
            "device_settings": {
                "webasto_emul_mode": "thermoconnect",
                "OUTV_timeout_on": True,
                "OUTV_timeout_h": vent_h,
                "OUTV_timeout_min": vent_m,
                "OUTH_timeout_on": True,
                "OUTH_timeout_h": heat_h,
                "OUTH_timeout_min": heat_m,
            },
            "service_settings": {
                "OUTH_on": True if not state else False,
                "OUTV_on": False if not state else True,
                "heater_mode": 0 if not state else 1,
                "OUTV_name": "Ventilation",
                "OUTV_icon": "car_vent",
                "OUTH_name": "Heater",
                "OUTH_icon": "car_heat",
            },
            "location_events": None,
            "air_heater": {},
        }

        await self._call(Request.POST_SETTING, json.dumps(ventmode))
        await self.update()

    async def set_main_timeout(
        self,
        device: WebastoDevice,
        heater: int | None = None,
        ventilation: int | None = None,
    ) -> None:
        """Sets timeout of main output port in seconds."""
        await self._change_device(device_id=device.device_id)

        if not isinstance(heater, type(None)):
            device.timeout_heat = heater

        if not isinstance(ventilation, type(None)):
            device.timeout_vent = ventilation

        await self.ventilation_mode(device, device.is_ventilation)

    async def set_aux_timeout(
        self,
        device: WebastoDevice,
        timeout: int,
        aux: Outputs = Outputs.AUX1,
    ) -> None:
        """Sets timeout of an AUX port in seconds."""
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
        await self.update()

    async def set_low_voltage_cutoff(self, device: WebastoDevice, value: float) -> None:
        """Set the low voltage cutoff value."""
        await self._change_device(device_id=device.device_id)

        payload = {
            "device_settings": {"low_voltage_cutoff": value},
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        await self._call(Request.POST_SETTING, json.dumps(payload))
        await self.update()

    async def set_temperature_compensation(
        self, device: WebastoDevice, value: float
    ) -> None:
        """Set the temperature compensation value."""
        await self._change_device(device_id=device.device_id)

        payload = {
            "device_settings": {"ext_temp_comp": value},
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        await self._call(Request.POST_SETTING, json.dumps(payload, indent=4))
        await self.update()
