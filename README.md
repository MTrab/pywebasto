# pywebasto

![Current Release](https://img.shields.io/github/release/mtrab/pywebasto/all.svg?style=plastic)

<a href="https://www.buymeacoffee.com/mtrab" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

This Python module provides access to controlling and reading states of Webasto heaters connected to https://my.webastoconnect.com

The API is reverse engineered, as Webasto doesn't want to contribute with documentation, to let us integrate this in to our own solutions, such as smart homes.

## Warning

USE THIS MODULE AT YOUR OWN RISK.

## Installation

Run this command to install the latest release from the PyPI repository:<br/>
`pip3 install pywebasto`

## Usage

The following example shows how to get the current temperature measurement from your connected device(s):<br/>

```python
import asyncio

from pywebasto import WebastoConnect


async def main() -> None:
    async with WebastoConnect("your-email", "your-password") as webasto:
        await webasto.connect()
        await webasto.update()

        for id, device in webasto.devices.items():
            print(f"Found device: {device.name} (ID: {device.device_id})")
            print(f"Temperature: {device.temperature}")


asyncio.run(main())
```

More examples can be found in the `example.py` file

### Request robustness

- Read/login requests (`LOGIN`, `GET_*`, `CHANGE_DEVICE`) use bounded retries for transient
  network/server failures (`429`, `5xx`, connection/timeouts).
- Command and settings writes are not retried automatically to avoid duplicate side effects.

## Web Interface Polling

Observed behavior in the Webasto web interface (`my.webastoconnect.com`):

- Default data refresh interval is `15` seconds - don't refresh faster or you risk getting banned.

## Available properties

This list indicates the available properties for a heater
| Property | Description | Type | Example |
| --- | --- | --- | --- |
| timeout_heat | Heat mode timeout in seconds | int | |
| timeout_ventilation | Ventilation mode timeout in seconds | int | |
| timeout_aux1 | AUX1 timeout in seconds | int | |
| timeout_aux2 | AUX2 timeout in seconds | int | |
| icon_heat | Icon used in the webinterface | str | `car_heat` |
| icon_vent | Icon used in the webinterface | str | |
| icon_aux1 | Icon used in the webinterface | str | |
| icon_aux2 | Icon used in the webinterface | str | |
| temperature | Measured temperature | int | `18` |
| voltage | Measured battery voltage | float | `12.4` |
| location | Location of the vehicle, if location is enabled.<br/> `state` indicating if location service is enabled<br/>`lat` and `lon` showing latitude and longitude<br/>`timestamp` unix timestamp of last location update | dict | `{'state': 'ON', 'lat': 'x.xxxxxx', 'lon': 'x.xxxxxx', 'timestamp': 1766325670}` |
| output_main | State of main output channel | bool | `True` |
| output_aux1 | State of AUX1 output channel | bool | `False` |
| output_aux2 | State of AUX2 output channel | bool | `False` |
| is_ventilation | Is the main output set to ventilation mode? | bool | `False` |
| temperature_unit | The configured temperature unit of the heater. Either `°C` or `°F` | str | `°C` |
| hardware_version | Hardware version of the device | str | |
| software_version | Software (firmware) of the device | str | |
| software_variant | Software variant(?!) | str | |
| allow_location | Is location services enabled? | bool | `True` |
| low_voltage_cutoff | At this voltage, the heater will automatically turn off | float | `11.5` |
| temperature_compensation | The set deviation from actual to measured temperature | float | `-4.0` |
| device_id | The API ID of the device | str | `9254659033752365` |
| name | Name of the device, as set in the app or webinterface | str | `My heater device` |
| output_main_name | Name of the main output channel | str | `Primary` |
| output_aux1_name | Name of AUX1 output channel | str | `Output 1` |
| output_aux2_name | Name of AUX2 output channel | str | `Output 2` |
| subscription_expiration | When the current subscription will expire | datetime | `datetime.datetime(2025, 12, 21, 16, 6, 28, 254801)` |
| connection_lost | Raw cloud link state from API (`true` means cloud connection lost) | bool | `False` |
| is_connected | Derived cloud link state (`not connection_lost`) | bool | `True` |

## Functions

This list indicates the available functions

| Function | Description | Params |
| --- | --- | --- |
| connect | Function used to connect to the API | |
| update | Fetch latest data from the API | `device_id` if set, only update this device |
| get_timers | Read `simple` timers for a given output line from API data | `device` send command to this device of WebastoDevice class<br/>`line` _optional_ Outputs ENUM, default: `Outputs.HEATER` |
| save_timers | Save a full list of `simple` timers via `/save_timers` | `device` send command to this device of WebastoDevice class<br/>`timers` list of `SimpleTimer` objects<br/>`line` _optional_ Outputs ENUM, currently supports `Outputs.HEATER` and `Outputs.VENTILATION` |
| set_output_main | Set current state of main output | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be switched on (`true`) or off (`false`) |
| set_output_aux1 | Set current state of AUX1 output | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be switched on (`true`) or off (`false`) |
| set_output_aux2 | Set current state of AUX2 output | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be switched on (`true`) or off (`false`) |
| ventilation_mode | Switch main output to ventilation mode or heater mode | `device` send command to this device of WebastoDevice class<br/>`state` bool indicating if it should be set to ventilation mode (`true`) or heater mode (`false`) |
| set_main_timeout | Set the timeout for auto off for the main output | `device` send command to this device of WebastoDevice class<br/>`heater` _optional_ int indicating heater timeout in seconds<br/>`ventilation` _optional_ int indicating ventilation timeout in seconds |
| set_aux_timeout | Set the timeout for auto off for an AUX output | `device` send command to this device of WebastoDevice class<br/>`timeout` int indicating timeout in seconds<br/>`aux` _optional_ Outputs ENUM indicating AUX to be changed, default: `Outputs.AUX1` |
| set_low_voltage_cutoff | Sets the minimum voltage before shutting off the device | `device` send command to this device of WebastoDevice class<br/>`value` minimum voltage as float |
| set_temperature_compensation | Set the temperature compensatioon for the device | `device` send command to this device of WebastoDevice class<br/>`value` temperature compensation as float |

## Timers (`simple` only)

Current timer support is limited to `simple` timers on:

- `Outputs.HEATER` (`line=OUTH`)
- `Outputs.VENTILATION` (`line=OUTV`)

Important behavior:

- `save_timers(...)` sends the full timer list for the line.
- To edit one timer, read all timers, modify one entry, and save the full list.
- To delete one timer, read all timers, remove one entry, and save the remaining list.

### Weekday bitmask (`repeat`)

Confirmed mapping:

- Monday = `1`
- Tuesday = `2`
- Wednesday = `4`
- Thursday = `8`
- Friday = `16`
- Saturday = `32`
- Sunday = `64`

Examples:

- `repeat=31` means Monday-Friday (`1+2+4+8+16`)
- `repeat=17` means Monday+Friday (`1+16`)

### Read timers

```python
from pywebasto import WebastoConnect

timers = await webasto.get_timers(device)
for timer in timers:
    print(timer)
```

### Create one timer

```python
from pywebasto import SimpleTimer

timers = await webasto.get_timers(device)

new_timer = SimpleTimer(
    start=830,          # minutes after midnight (UTC)
    duration=5400,      # seconds
    repeat=31,          # weekday bitmask
    enabled=True,
    # location is optional
    # latitude="56.461846",
    # longitude="10.866533",
)

await webasto.save_timers(device, timers + [new_timer])
```

### Edit an existing timer

```python
from pywebasto import SimpleTimer

timers = await webasto.get_timers(device)

# Example: replace first timer with updated start/duration/repeat
timers[0] = SimpleTimer(
    start=900,
    duration=3600,
    repeat=31,
    enabled=True,
)

await webasto.save_timers(device, timers)
```

### Delete a timer

```python
timers = await webasto.get_timers(device)

# Example: remove first timer
updated = timers[1:]
await webasto.save_timers(device, updated)
```

### Multiple timers

```python
from pywebasto import SimpleTimer

timer_a = SimpleTimer(start=830, duration=5400, repeat=31, enabled=True)
timer_b = SimpleTimer(start=1221, duration=4200, repeat=16, enabled=True)

await webasto.save_timers(device, [timer_a, timer_b])
```

## My heater doesn't show up

If your heater doesn't show up in the module, please make sure it is connected to the e-mail used.

- Login to https://my.webastoconnect.com _USING THE SAME EMAIL AND PASSWORD_ as used in this module
- Press `Account`

Make sure your device is listed under devices

If your device is NOT listed under devices:

- Open the ThermoConnect app on your phone
- Select the missing device (If you have more than one connected)
- Click on the `"My Webasto Connect` button in the lower left
- Choose `Login with mobile browser`
- Login with your existing email and password

The device should now be linked to your email account and will show up at next run
