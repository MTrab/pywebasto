"""Module for interfacing with Webasto Connect."""

from datetime import datetime
import json
import threading
from typing import Any

import requests

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


class WebastoConnect:
    """Webasto Connect implementation."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the component."""
        self.__initialized: bool = False

        self._usn: str = username
        self._pwd: str = password
        self._hssess: str = None
        self._authorized: bool = False
        self._last_data = {}
        self._dev_data = {}
        self._settings = {}
        self._output_main = {}
        self._output_aux1 = {}
        self._output_aux2 = {}

        self._timeout_vent: int = 3600
        self._timeout_heat: int = 3600
        self._timeout_aux1: int = 3600
        self._timeout_aux2: int = 3600

        self._icon_vent: str
        self._icon_heat: str
        self._icon_aux1: str
        self._icon_aux2: str

        self._ventilation: bool = False
        self._iscelcius: bool = False

    def connect(self) -> None:
        """Connect to the API."""
        self._call(Request.LOGIN, {"username": self._usn, "password": self._pwd})
        if self._authorized:
            self.__initialized = True
            self.update()
        else:
            raise UnauthorizedException("Username or password incorrect")

    def assemble_headers(self) -> dict:
        """Generate headers."""
        _headers: dict = {"origin": "https://my.webastoconnect.com"}

        if isinstance(self._hssess, type(None)):
            # _headers.update(
            #     {"Cookie": "__stripe_mid=70011fb4-8351-41c7-baad-047402d8cafed894b1;"}
            # )
            pass
        else:
            _headers.update({"Cookie": f"hssess={self._hssess};"})

        return _headers

    def _call(
        self, api_type: Request, payload: dict | str | None = None
    ) -> dict | None:
        """Make an API request."""

        if isinstance(payload, type(None)):
            payload = {}

        response = requests.request(
            "POST",
            f"{API_URL}{api_type.value}",
            headers=self.assemble_headers(),
            data=payload,
            timeout=60,
        )
        # self._cookies = response.cookies
        if isinstance(self._hssess, type(None)):
            self._hssess = response.cookies["hssess"]

        if response.status_code != 200:
            if response.status_code == 401:
                self._authorized = False
                if self.__initialized:
                    self.__initialized = False
                    self._call(
                        Request.LOGIN, {"username": self._usn, "password": self._pwd}
                    )
                    if self._authorized:
                        self.__initialized = True
                        self._call(api_type, payload)
                    else:
                        raise UnauthorizedException("Username or password incorrect")
            elif response.status_code == 403:
                retry = threading.Timer(30, self._call, [api_type, payload])
                retry.start()
            else:
                raise InvalidRequestException(
                    f"API reported {response.status_code}: {response.text}"
                )
        else:
            self._authorized = True

        if "GET" in api_type.name:
            return response.json()

    def update(self) -> None:
        """Get current data from Webasto API."""
        self._settings = self._call(Request.GET_SETTINGS)
        self.__get_timeouts()
        self._last_data = self._call(Request.GET_DATA)
        self._dev_data = self._call(Request.GET_DATA_NOPOLL)

        if self._last_data["temperature"][-1] == "C":
            self._iscelcius = True

        for output in self._last_data["outputs"]:
            if output["line"] == "OUTH" or output["line"] == "OUTV":
                self._output_main = output
                if output["line"] == "OUTH":
                    self._ventilation = False
                    self._icon_heat = output["icon"]
                else:
                    self._ventilation = True
                    self._icon_vent = output["icon"]
            elif output["line"] == "OUT1":
                self._output_aux1 = output
                self._icon_aux1 = output["icon"]
            elif output["line"] == "OUT2":
                self._output_aux2 = output
                self._icon_aux2 = output["icon"]

    def set_output_main(self, state: bool) -> None:
        """Turn on or off the heater or ventilation."""
        if state:
            if self._ventilation:
                self._call(Request.COMMAND, CMD_VENTILATION_ON)
            else:
                self._call(Request.COMMAND, CMD_HEATER_ON)
        else:
            if self._ventilation:
                self._call(Request.COMMAND, CMD_VENTILATION_OFF)
            else:
                self._call(Request.COMMAND, CMD_HEATER_OFF)
        self.update()

    def set_output_aux1(self, state: bool) -> None:
        """Turn on or off the aux1 output."""
        if state:
            self._call(Request.COMMAND, CMD_AUX1_ON)
        else:
            self._call(Request.COMMAND, CMD_AUX1_OFF)
        self.update()

    def set_output_aux2(self, state: bool) -> None:
        """Turn on or off the aux2 output."""
        if state:
            self._call(Request.COMMAND, CMD_AUX2_ON)
        else:
            self._call(Request.COMMAND, CMD_AUX2_OFF)
        self.update()

    def ventilation_mode(self, state: bool) -> None:
        """Turn ventilation mode on or off."""
        vent_sec = self._timeout_vent % (24 * 3600)
        vent_h = vent_sec // 3600
        vent_sec = vent_sec % 3600
        vent_m = vent_sec // 60

        heat_sec = self._timeout_heat % (24 * 3600)
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

        self._call(Request.POST_SETTING, json.dumps(ventmode))
        self.update()

    def set_main_timeout(
        self,
        heater: int | None = None,
        ventilation: int | None = None,
    ) -> None:
        """Sets timeout of main output port in seconds."""
        if not isinstance(heater, type(None)):
            self._timeout_heat = heater

        if not isinstance(ventilation, type(None)):
            self._timeout_vent = ventilation

        self.ventilation_mode(self._ventilation)

    def set_aux_timeout(
        self,
        timeout: int | None = None,
        aux: Outputs = Outputs.AUX1,
    ) -> None:
        """Sets timeout of an AUX port in seconds."""

        if aux == Outputs.AUX1:
            self._timeout_aux1 = timeout
        elif aux == Outputs.AUX2:
            self._timeout_aux2 = timeout

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
                f"{aux.value}_name": self.output_aux1_name
                if aux == Outputs.AUX1
                else self.output_aux2_name,
                f"{aux.value}_icon": self._icon_aux1
                if aux == Outputs.AUX1
                else self._icon_aux1,
            },
            "location_events": None,
            "air_heater": {},
        }

        self._call(Request.POST_SETTING, json.dumps(data))
        self.update()

    def set_low_voltage_cutoff(self, value: float) -> None:
        """Set the low voltage cutoff value."""

        payload = {
            "device_settings": {"low_voltage_cutoff": value},
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        self._call(Request.POST_SETTING, json.dumps(payload))
        self.update()

    def set_temperature_compensation(self, value: float) -> None:
        """Set the temperature compensation value."""

        payload = {
            "device_settings": {"ext_temp_comp": value},
            "service_settings": {},
            "location_events": None,
            "air_heater": {},
        }
        self._call(Request.POST_SETTING, json.dumps(payload, indent=4))
        self.update()

    @property
    def temperature(self) -> int:
        """Returns the current temperature."""
        return self._last_data["temperature"][: len(self._last_data["temperature"]) - 1]

    @property
    def voltage(self) -> float:
        """Returns the current voltage."""
        return self._last_data["voltage"][: len(self._last_data["voltage"]) - 1]

    @property
    def location(self) -> dict:
        """Returns the current location."""
        return (
            self._last_data["location"]
            if self._last_data["location"]["state"] == "ON"
            else None
        )

    @property
    def output_main(self) -> bool:
        """Get the main output state."""
        if "state" in self._output_main:
            return False if self._output_main["state"] == "OFF" else True
        else:
            return False

    @property
    def output_aux1(self) -> bool:
        """Get the aux output state."""
        if "state" in self._output_aux1:
            return False if self._output_aux1["state"] == "OFF" else True
        else:
            return False

    @property
    def output_aux2(self) -> bool:
        """Get the aux output state."""
        if "state" in self._output_aux2:
            return False if self._output_aux2["state"] == "OFF" else True
        else:
            return False

    @property
    def is_ventilation(self) -> bool:
        """Get the mode of the output channel."""
        return self._ventilation

    @property
    def temperature_unit(self) -> bool:
        """Get the temperature unit."""
        return "°C" if self._iscelcius else "°F"

    @property
    def hardware_version(self) -> str:
        """Get the hardware version."""
        return self._settings["hw_version"]

    @property
    def software_version(self) -> str:
        """Get the software version."""
        return self._settings["sw_version"]

    @property
    def software_variant(self) -> str:
        """Get the software variant."""
        return self._settings["sw_variant"]

    @property
    def allow_location(self) -> str:
        """Get the location setting."""
        return self.__get_value("general", "allow_GPS")

    @property
    def low_voltage_cutoff(self) -> str:
        """Get the low_voltage_cutoff setting."""
        return self.__get_value("general", "low_voltage_cutoff")

    @property
    def temperature_compensation(self) -> str:
        """Get the ext_temp_comp setting."""
        return self.__get_value("general", "ext_temp_comp")

    @property
    def device_id(self) -> str:
        """Get the ID of the device (QR code ID)"""
        return self._dev_data["id"]

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self._dev_data["alias"]

    @property
    def output_main_name(self) -> str:
        """Get the main output name."""
        if "name" in self._output_main:
            return self._output_main["name"] or "Primary"
        else:
            return False

    @property
    def output_aux1_name(self) -> str:
        """Get the aux1 output name."""
        if "name" in self._output_aux1:
            return self._output_aux1["name"] or "Output 1"
        else:
            return False

    @property
    def output_aux2_name(self) -> str:
        """Get the aux2 output name."""
        if "name" in self._output_aux2:
            return self._output_aux2["name"] or "Output 2"
        else:
            return False

    @property
    def subscription_expiration(self) -> datetime:
        """Get subscription expiration."""
        expiration = self._dev_data["subscription"]["expiration"]
        return datetime.fromtimestamp(expiration)

    def __get_value(self, group: str, key: str) -> Any:
        """Get a value from the settings dict."""
        for g in self._settings["settings_tab"]:
            if g["group"] != group:
                continue

            for o in g["options"]:
                if o["key"] == key:
                    return o["value"]

    def __get_timeouts(self) -> None:
        for g in self._settings["settings_tab"]:
            if g["group"] not in ["webasto", "outputs"]:
                continue

            for o in g["options"]:
                if o["key"] == "OUTH":
                    self._timeout_heat = o["timeout"]
                elif o["key"] == "OUTV":
                    self._timeout_vent = o["timeout"]
                elif o["key"] == "OUT1":
                    self._timeout_aux1 = o["timeout"]
                elif o["key"] == "OUT2":
                    self._timeout_aux2 = o["timeout"]
