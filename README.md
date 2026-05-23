# pywebasto

![Current Release](https://img.shields.io/github/release/mtrab/pywebasto/all.svg?style=plastic)

<a href="https://www.buymeacoffee.com/mtrab" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

Python client for Webasto ThermoConnect devices.

The protocol is reverse engineered. There is no official Webasto API for this
module.

## Warning

USE THIS MODULE AT YOUR OWN RISK.

## Installation

```bash
pip3 install pywebasto
```

## Login

The preferred login is with an app `client_id` and `client_secret`.

```python
import asyncio

from pywebasto import WebastoConnect


async def main() -> None:
    webasto = WebastoConnect(
        client_id="your-client-id",
        client_secret="your-client-secret",
    )

    try:
        await webasto.connect()

        for device in webasto.devices.values():
            print(f"{device.name}: {device.temperature}{device.temperature_unit}")
    finally:
        await webasto.close()


asyncio.run(main())
```

You can read the values after connect:

```python
print(webasto.client_id)
print(webasto.client_secret)
```

Store them somewhere safe and reuse them next time.

## First Run With Email And Password

If you do not have app credentials yet, you can still start with email and
password. The module will create an app client and save it if you give it a file
path.

```python
import asyncio

from pywebasto import WebastoConnect


async def main() -> None:
    webasto = WebastoConnect(
        username="your-email",
        password="your-password",
        credential_store_path="webasto_credentials.json",
    )

    try:
        await webasto.connect()

        print(webasto.client_id)
        print(webasto.client_secret)
    finally:
        await webasto.close()


asyncio.run(main())
```

Integrations that already have their own storage can use `credential_load` and
`credential_save` instead of `credential_store_path`.

On first run, a device may need approval in the ThermoConnect app. If a device
is waiting for approval, `device.pending_approval` is `True`. Approve it in the
app and then call:

```python
await webasto.update(force=True)
```

Email and password are still needed for:

- first-time association when app credentials do not already exist
- `set_low_voltage_cutoff`
- `set_temperature_compensation`
- webapi-only settings

## Updates

Status is read from the app endpoint. Normal `update()` calls are cached for 60
seconds.

```python
await webasto.update()
```

Use `force=True` when you know you need fresh data:

```python
await webasto.update(force=True)
```

## Available Properties

| Property | Description | Type |
| --- | --- | --- |
| client_id | App client id used for the current session | str |
| client_secret | Secret for the app client id | str |
| temperature | Measured temperature | int |
| voltage | Measured battery voltage | float |
| location | Vehicle location if enabled, otherwise `False` | dict or bool |
| output_main | Main output state | bool |
| output_aux1 | AUX1 output state | bool |
| output_aux2 | AUX2 output state | bool |
| is_ventilation | Main output is in ventilation mode | bool |
| temperature_unit | `C` or `F` display unit | str |
| allow_location | Location setting from webapi settings | bool |
| low_voltage_cutoff | Webapi low-voltage cutoff setting | float |
| temperature_compensation | Webapi temperature compensation setting | float |
| device_id | Device id | str |
| name | Device name | str |
| pending_approval | Device is waiting for app approval | bool |
| association_status | Raw app association status | str |
| connection_lost | Raw cloud link state | bool |
| is_connected | Derived cloud link state | bool |

## Functions

| Function | Description |
| --- | --- |
| connect | Set up app credentials and load devices |
| update | Refresh app data, cached for 60 seconds unless `force=True` |
| get_timers | Read simple timers for an output |
| save_timers | Save the full simple timer list for an output |
| set_output_main | Turn heater or ventilation output on/off |
| set_output_aux1 | Turn AUX1 on/off |
| set_output_aux2 | Turn AUX2 on/off |
| ventilation_mode | Switch between heating and ventilation |
| associate_device | Start association for a DeviceID and CheckID |
| association_status | Read association status for a device |
| disassociate_device | Remove this app client from a device |
| set_location_services | Enable or disable location services |
| get_location_text | Read raw `/location2` text |
| set_low_voltage_cutoff | Change low-voltage cutoff using webapi |
| set_temperature_compensation | Change temperature compensation using webapi |

## Association

Manual association:

```python
status = await webasto.associate_device(
    device_id="device-id-from-label",
    check_id="check-id-from-label",
)
print(status)
```

The usual first status is `pending`. Approve the request in the ThermoConnect
app, then refresh:

```python
await webasto.update(force=True)
```

## Timers

Timer support is for `simple` timers.

```python
from pywebasto import SimpleTimer

timers = await webasto.get_timers(device)

new_timer = SimpleTimer(
    start=830,      # minutes after midnight UTC
    duration=5400,  # seconds
    repeat=31,      # Monday-Friday
    enabled=True,
)

await webasto.save_timers(device, timers + [new_timer])
```

`save_timers()` sends the full timer list. To edit or delete a timer, read the
list, change it locally, and save the whole list again.

Weekday bitmask:

- Monday = `1`
- Tuesday = `2`
- Wednesday = `4`
- Thursday = `8`
- Friday = `16`
- Saturday = `32`
- Sunday = `64`

Examples:

- `repeat=31` means Monday-Friday
- `repeat=17` means Monday and Friday
- `repeat=0` means no repeat

## Location

Use the app endpoint to enable or disable location services:

```python
await webasto.set_location_services(device, True)
```

After enabling, the device can report `WAITING_FOR_LOCATION` until a fresh
position is available.

## Notes

- Commands and normal status reads use the app backend.
- Email/password login uses the older webapi only when it is needed.
- Command writes are not retried automatically.
- Rate-limited responses raise an exception.
