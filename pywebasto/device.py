"""Device class for Webasto devices."""

from datetime import datetime
from typing import Any


class WebastoDevice:
    """Webasto Device representation."""

    def __init__(self, device_id: str, name: str) -> None:
        """Initialize the device."""
        self.__device_id: str = device_id
        self.__name: str = name
        self.__temperature: int = 0
        self.__voltage: float = 0.0
        self.__location: dict = {}
        self.__output_main: dict = {}
        self.__output_aux1: dict = {}
        self.__output_aux2: dict = {}
        self.__ventilation: bool = False
        self.__iscelcius: bool = False
        self.__hardware_version: str = ""
        self.__software_version: str = ""
        self.__software_variant: str = ""
        self.__allow_location: bool = False
        self.__low_voltage_cutoff: float = 0.0
        self.__temperature_compensation: float = 0.0
        self.__subscription_expiration: datetime | None = None
        self.__last_data: dict | None = {}
        self.__dev_data: dict | None = {}
        self.__settings: dict | None = {}
        self.__icon_vent: str = ""
        self.__icon_heat: str = ""
        self.__icon_aux1: str = ""
        self.__icon_aux2: str = ""
        self.__timeout_heat: int = 0
        self.__timeout_vent: int = 0
        self.__timeout_aux1: int = 0
        self.__timeout_aux2: int = 0

    @property
    def timeout_heat(self) -> int:
        """Returns the heater timeout in seconds."""
        return self.__timeout_heat

    @timeout_heat.setter
    def timeout_heat(self, value: int) -> None:
        """Sets the heater timeout in seconds."""
        self.__timeout_heat = value

    @property
    def timeout_vent(self) -> int:
        """Returns the ventilation timeout in seconds."""
        return self.__timeout_vent

    @timeout_vent.setter
    def timeout_vent(self, value: int) -> None:
        """Sets the ventilation timeout in seconds."""
        self.__timeout_vent = value

    @property
    def timeout_aux1(self) -> int:
        """Returns the aux1 timeout in seconds."""
        return self.__timeout_aux1

    @timeout_aux1.setter
    def timeout_aux1(self, value: int) -> None:
        """Sets the aux1 timeout in seconds."""
        self.__timeout_aux1 = value

    @property
    def timeout_aux2(self) -> int:
        """Returns the aux2 timeout in seconds."""
        return self.__timeout_aux2

    @timeout_aux2.setter
    def timeout_aux2(self, value: int) -> None:
        """Sets the aux2 timeout in seconds."""
        self.__timeout_aux2 = value

    @property
    def icon_vent(self) -> str:
        """Returns the ventilation icon."""
        return self.__icon_vent

    @property
    def icon_heat(self) -> str:
        """Returns the heater icon."""
        return self.__icon_heat

    @property
    def icon_aux1(self) -> str:
        """Returns the aux1 icon."""
        return self.__icon_aux1

    @property
    def icon_aux2(self) -> str:
        """Returns the aux2 icon."""
        return self.__icon_aux2

    @property
    def last_data(self) -> dict | None:
        """Returns the last data dictionary."""
        return self.__last_data

    @last_data.setter
    def last_data(self, value: dict | None) -> None:
        """Sets the last data dictionary."""
        self.__last_data = value

        if self.__last_data is None:
            return

        if self.__last_data["temperature"][-1] == "C":
            self.__iscelcius = True

        self.__temperature = int(
            self.__last_data["temperature"][: len(self.__last_data["temperature"]) - 1]
        )
        self.__voltage = float(
            self.__last_data["voltage"][: len(self.__last_data["voltage"]) - 1]
        )
        self.__location = self.__last_data["location"]

        for output in self.__last_data["outputs"]:
            if output["line"] == "OUTH" or output["line"] == "OUTV":
                self.__output_main = output
                if output["line"] == "OUTH":
                    self.__ventilation = False
                    self.__icon_heat = output["icon"]
                else:
                    self.__ventilation = True
                    self.__icon_vent = output["icon"]
            elif output["line"] == "OUT1":
                self.__output_aux1 = output
                self.__icon_aux1 = output["icon"]
            elif output["line"] == "OUT2":
                self.__output_aux2 = output
                self.__icon_aux2 = output["icon"]

    @property
    def dev_data(self) -> dict | None:
        """Returns the device data dictionary."""
        return self.__dev_data

    @dev_data.setter
    def dev_data(self, value: dict | None) -> None:
        """Sets the device data dictionary."""
        self.__dev_data = value
        if self.__dev_data is None:
            return

        self.__subscription_expiration = datetime.fromtimestamp(
            value["subscription"]["expiration"]
        )

    @property
    def settings(self) -> dict | None:
        """Returns the settings dictionary."""
        return self.__settings

    @settings.setter
    def settings(self, value: dict | None) -> None:
        """Sets the settings dictionary."""
        self.__settings = value

        if value is None:
            return

        self.__allow_location = self.__get_value("general", "allow_GPS")
        self.__low_voltage_cutoff = self.__get_value("general", "low_voltage_cutoff")
        self.__temperature_compensation = self.__get_value("general", "ext_temp_comp")

        # self.timeout_heat = self.__get_value("settings_tab", "OUTH")
        # self.timeout_vent = self.__get_value("settings_tab", "OUTV")
        # self.timeout_aux1 = self.__get_value("settings_tab", "OUT1")
        # self.timeout_aux2 = self.__get_value("settings_tab", "OUT2")
        self.__get_timeouts()

    @property
    def temperature(self) -> int:
        """Returns the current temperature."""
        return self.__temperature

    @property
    def voltage(self) -> float:
        """Returns the current voltage."""
        return self.__voltage

    @property
    def location(self) -> dict | bool:
        """Returns the current location."""
        return self.__location if self.__location["state"] == "ON" else False

    @property
    def output_main(self) -> bool:
        """Get the main output state."""
        if "state" in self.__output_main:
            return False if self.__output_main["state"] == "OFF" else True
        else:
            return False

    @property
    def output_aux1(self) -> bool:
        """Get the aux output state."""
        if "state" in self.__output_aux1:
            return False if self.__output_aux1["state"] == "OFF" else True
        else:
            return False

    @property
    def output_aux2(self) -> bool:
        """Get the aux output state."""
        if "state" in self.__output_aux2:
            return False if self.__output_aux2["state"] == "OFF" else True
        else:
            return False

    @property
    def is_ventilation(self) -> bool:
        """Get the mode of the output channel."""
        return self.__ventilation

    @property
    def temperature_unit(self) -> str:
        """Get the temperature unit."""
        return "°C" if self.__iscelcius else "°F"

    @property
    def hardware_version(self) -> str:
        """Get the hardware version."""
        return self.__hardware_version

    @property
    def software_version(self) -> str:
        """Get the software version."""
        return self.__software_version

    @property
    def software_variant(self) -> str:
        """Get the software variant."""
        return self.__software_variant

    @property
    def allow_location(self) -> bool:
        """Get the location setting."""
        return self.__allow_location

    @property
    def low_voltage_cutoff(self) -> float:
        """Get the low_voltage_cutoff setting."""
        return self.__low_voltage_cutoff

    @property
    def temperature_compensation(self) -> float:
        """Get the ext_temp_comp setting."""
        return self.__temperature_compensation

    @property
    def device_id(self) -> str:
        """Get the ID of the device (QR code ID)"""
        return self.__device_id

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self.__name

    @property
    def output_main_name(self) -> str | bool:
        """Get the main output name."""
        if "name" in self.__output_main:
            return self.__output_main["name"] or "Primary"
        else:
            return False

    @property
    def output_aux1_name(self) -> str | bool:
        """Get the aux1 output name."""
        if "name" in self.__output_aux1:
            return self.__output_aux1["name"] or "Output 1"
        else:
            return False

    @property
    def output_aux2_name(self) -> str | bool:
        """Get the aux2 output name."""
        if "name" in self.__output_aux2:
            return self.__output_aux2["name"] or "Output 2"
        else:
            return False

    @property
    def subscription_expiration(self) -> datetime:
        """Get subscription expiration."""
        return self.__subscription_expiration

    def __get_value(self, group: str, key: str) -> Any:
        """Get a value from the settings dict."""
        if self.settings is None:
            return None

        for g in self.settings["settings_tab"]:
            if g["group"] != group:
                continue

            for o in g["options"]:
                if o["key"] == key:
                    return o["value"]

    def __get_timeouts(self) -> None:
        """Get output timeouts from the settings dict."""
        if self.settings is None:
            return None

        for g in self.settings["settings_tab"]:
            if g["group"] not in ["webasto", "outputs"]:
                continue

            for o in g["options"]:
                if o["key"] == "OUTH":
                    self.__timeout_heat = o["timeout"]
                elif o["key"] == "OUTV":
                    self.__timeout_vent = o["timeout"]
                elif o["key"] == "OUT1":
                    self.__timeout_aux1 = o["timeout"]
                elif o["key"] == "OUT2":
                    self.__timeout_aux2 = o["timeout"]
