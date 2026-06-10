"""Test file for the module."""

import asyncio
from os import environ

from pywebasto import WebastoConnect


async def main():
    client_id = environ.get("CLIENT_ID")
    client_secret = environ.get("CLIENT_SECRET")
    email = environ.get("EMAIL")
    password = environ.get("PASSWORD")

    if not ((client_id and client_secret) or (email and password)):
        raise SystemExit(
            "Set CLIENT_ID and CLIENT_SECRET, or set EMAIL and PASSWORD for first setup"
        )

    webasto = WebastoConnect(
        client_id=client_id,
        client_secret=client_secret,
        username=email,
        password=password,
        credential_store_path=environ.get("WEBASTO_CREDENTIALS"),
    )

    try:
        await webasto.connect()

        print(f"Client ID: {webasto.client_id}")
        print(f"Client secret: {webasto.client_secret}")

        for _, device in webasto.devices.items():
            print(f"Found device: {device.name} (ID: {device.device_id})")
            if device.pending_approval:
                print("Device is waiting for approval in the ThermoConnect app")
                continue

            # Get temperature
            print(f"Temperature: {device.temperature}{device.temperature_unit}")

            # Get battery voltage
            print(f"Voltage: {device.voltage}V")

            # Is location services enabled?
            print(f"Allow location services: {device.allow_location}")

            # Get current location
            print(f"Current location: {device.location}")

            # Get low voltage cutoff setting
            print(f"Low voltage cutoff: {device.low_voltage_cutoff}V")

            # Get temperature compensation value
            print(f"Temperature compensation: {device.temperature_compensation}")

            # Get subscription expiration
            print(f"Subscription expiration: {device.subscription_expiration}")

            # Set timeout of heater function to 2 hours (7200 seconds) and ventilation to 2 hours (7200 seconds)
            # webasto.set_timeout(device, 7200, 7200)

            # Set low voltage cutoff to 11.3V
            # webasto.set_low_voltage_cutoff(device, 11.3)

            # Set temperature compensation to -5C
            # webasto.set_temperature_compensation(device, -5)

            # Enable ventilation mode
            # webasto.ventilation_mode(device, False)

            # Toggle main output
            # if device.output_main:
            #     await webasto.set_output_main(device, False)
            # else:
            #     await webasto.set_output_main(device, True)

            # Toggle aux1 output
            # if device.output_aux1:
            #     webasto.set_output_aux1(device, False)
            # else:
            #     webasto.set_output_aux1(device, True)

            # Toggle aux2 output
            # if device.output_aux2:
            #     webasto.set_output_aux2(device, False)
            # else:
            #     webasto.set_output_aux2(device, True)

            # Is primary output on?
            if device.output_main_name is not False:
                print(f"{device.output_main_name} on: {device.output_main}")

            # Is aux1 output on?
            if device.output_aux1_name is not False:
                print(f"{device.output_aux1_name} on: {device.output_aux1}")

            # Is aux2 output on?
            if device.output_aux2_name is not False:
                print(f"{device.output_aux2_name} on: {device.output_aux2}")

            # Set timeout for aux1
            # webasto.set_aux_timeout(device, 2400)

            # Set timeout for aux2
            # webasto.set_aux_timeout(device, 2400, Outputs.AUX2)

            # Read simple timers for the main output line (OUTH)
            # timers = await webasto.get_timers(device)
            # for timer in timers:
            #     print(timer)

            # Save full timer list for OUTH (replace current list)
            # await webasto.save_timers(
            #     device,
            #     [
            #         # from pywebasto import SimpleTimer
            #         SimpleTimer(
            #             start=830,
            #             duration=5400,
            #             repeat=31,
            #             latitude="REPLACE_LAT",
            #             longitude="REPLACE_LON",
            #             enabled=True,
            #         )
            #     ],
            # )

            # Update data
            # await webasto.update()
            print("-----")
    finally:
        await webasto.close()


if __name__ == "__main__":
    asyncio.run(main())
