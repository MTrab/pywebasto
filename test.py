"""Test file for the module."""

from os import environ

from pywebasto import WebastoConnect
from pywebasto.enums import Outputs

webasto = WebastoConnect(environ["EMAIL"], environ["PASSWORD"])
webasto.connect()
webasto.update()


for id, device in webasto.devices.items():
    print(f"Found device: {device.name} (ID: {device.device_id})")
    # Get temperature
    print(f"Temperature: {device.temperature}")

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
    #     webasto.set_output_main(device, False)
    # else:
    #     webasto.set_output_main(device, True)

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

    # Update data
    # webasto.update()
    print("-----")
