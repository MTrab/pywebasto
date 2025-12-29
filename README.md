![Current Release](https://img.shields.io/github/release/mtrab/pywebasto/all.svg?style=plastic)

<a href="https://www.buymeacoffee.com/mtrab" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

This Python module provides access to controlling and reading states of Webasto heaters connected to https://my.webastoconnect.com

The API is reverse engineered, as Webasto doesn't want to contribute with documentation, to let us integrate this in to our own solutions, such as smart homes.

Hence:
### !USE THIS MODULE AT YOU OWN RISK!

## Installation
Run this command to install the latest release from the PyPI repository:<br/>
`pip3 install pywebasto`

## Usage
The following example shows how to get the current temperature measurement from your connected device(s):<br/>
```
from pywebasto import WebastoConnect

webasto = WebastoConnect("your-email", "your-password")
webasto.connect()
webasto.update()

for id, device in webasto.devices.items():
    print(f"Found device: {device.name} (ID: {device.device_id})")
    print(f"Temperature: {device.temperature}")
```

More examples can be found in the `test.py`file

## Available properties
This list indicates the available properties for a heater
Property | Description | Type | Example
-|-|-|-
timeout_heat | Heat mode timeout in seconds | int |
timeout_ventilation | Ventilation mode timeout in seconds | int |
timeout_aux1 | AUX1 timeout in seconds | int |
timeout_aux2 | AUX2 timeout in seconds | int |
icon_heat | Icon used in the webinterface | str | `car_heat`
icon_vent | Icon used in the webinterface | str |
icon_aux1 | Icon used in the webinterface | str |
icon_aux2 | Icon used in the webinterface | str |
temperature | Measured temperature | int | `18`
voltage | Measured battery voltage | float | `12.4`
location | Location of the vehicle, if location is enabled.<br/> `state` indicating if location service is enabled<br/>`lat` and `lon` showing latitude and longitude<br/>`timestamp` unix timestamp of last location update | dict | `{'state': 'ON', 'lat': 'x.xxxxxx', 'lon': 'x.xxxxxx', 'timestamp': 1766325670}`
output_main | State of main output channel | bool | `True`
output_aux1 | State of AUX1 output channel | bool | `False`
output_aux2 | State of AUX2 output channel | bool | `False`
is_ventilation | Is the main output set to ventilation mode? | bool | `False`
temperature_unit | The configured temperature unit of the heater. Either `°C` or `°F` | str | `°C`
hardware_version | Hardware version of the device | str |
software_version | Software (firmware) of the device |str |
software_variant | Software variant(?!) | str |
allow_location | Is location services enabled? | bool | `True`
low_voltage_cutoff | At this voltage, the heater will automatically turn off | float | `11.5`
temperature_compensation | The set deviation from actual to measured temperature | float | `-4.0`
device_id | The API ID of the device | str | `9254659033752365`
name | Name of the device, as set in the app or webinterface | str | `My heater device`
output_main_name | Name of the main output channel | str | `Primary`
output_aux1_name | Name of AUX1 output channel | str | `Output 1`
output_aux2_name | Name of AUX2 output channel | str | `Output 2`
subscription_expiration | When the current subscription will expire | datetime | `datetime.datetime(2025, 12, 21, 16, 6, 28, 254801)`

## Functions
This list indicates the available functions
Function | Description | Params
-|-|-
connect | Function used to connect to the API |
update | Fetch latest data from the API | `device_id` if set, only update this device
set_output_main | Set current state of main output | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be switched on (`true`) or off (`false`)
set_output_aux1 | Set current state of AUX1 output | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be switched on (`true`) or off (`false`)
set_output_aux2 | Set current state of AUX2 output | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be switched on (`true`) or off (`false`)
ventilation_mode | Switch main output to ventilation mode or heater mode | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be set to ventilation mode (`true`) or heater mode (`false`)
set_main_timeout | Set the timeout for auto off for the main output |`device` send command to this device of WebastoDevice class<br/>`heater` _optional_ int indicating heater timeout in seconds<br/>`ventilation` _optional_ int indicating ventilation timeout in seconds
set_aux_timeout | Set the timeout for auto off for an AUX output | `device` send command to this device of WebastoDevice class<br/>`timeout` int indicating timeout in seconds<br/>`aux` _optional_ Outputs ENUM indicating AUX to be changed, default: `Outputs.AUX1`
set_low_voltage_cutoff | Sets the minimum voltage before shutting off the device | `device` send command to this device of WebastoDevice class<br/>`value` minimum voltage as float
set_temperature_compensation | Set the temperature compensatioon for the device | `device` send command to this device of WebastoDevice class<br/>`value` temperature compensation as float

# My heater doesn't show up

If your heater doesn't show up in the module, please make sure it is connected to the e-mail used.

* Login to https://my.webastoconnect.com _USING THE SAME EMAIL AND PASSWORD_ as used in the in this module
* Press `Account`

Make sure your device is listed under devices

If your device is NOT listed under devices:

* Open the ThermoConnect app on your phone
* Select the missing device (If you have more than one connected)
* Click on the `"My Webasto Connect` button in the lower left
* Choose `Login with mobile browser`
* Login with your existing email and password

The device should now be linked to your email account and will show up at next run