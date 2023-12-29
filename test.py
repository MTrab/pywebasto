"""Test file for the module."""
from os import environ

from pywebasto import WebastoConnect
from pywebasto.enums import Outputs

webasto = WebastoConnect(environ["EMAIL"], environ["PASSWORD"])
webasto.connect()

# Get temperature
print(f"Temperature: {webasto.temperature}")

# Get battery voltage
print(f"Voltage: {webasto.voltage}V")

# Is location services enabled?
print(f"Allow location services: {webasto.allow_location}")

# Get current location
print(f"Current location: {webasto.location}")

# Get low voltage cutoff setting
print(f"Low voltage cutoff: {webasto.low_voltage_cutoff}V")

# Get temperature compensation value
print(f"Temperature compensation: {webasto.temperature_compensation}")

# Get subscription expiration
print(f"Subscription expiration: {webasto.subscription_expiration}")

# Set timeout of heater function to 2 hours (7200 seconds) and ventilation to 2 hours (7200 seconds)
# webasto.set_timeout(7200, 7200)

# Set low voltage cutoff to 11.3V
# webasto.set_low_voltage_cutoff(11.3)

# Set temperature compensation to -5C
# webasto.set_temperature_compensation(-5)

# Enable ventilation mode
# webasto.ventilation_mode(False)

# Is primary output on?
if webasto.output_main_name is not False:
    print(f"{webasto.output_main_name} on: {webasto.output_main}")

# Is aux1 output on?
if webasto.output_aux1_name is not False:
    print(f"{webasto.output_aux1_name} on: {webasto.output_aux1}")

# Is aux1 output on?
if webasto.output_aux2_name is not False:
    print(f"{webasto.output_aux2_name} on: {webasto.output_aux2}")

# Toggle main output
# if webasto.output_main:
#     webasto.set_output_main(False)
# else:
#     webasto.set_output_main(True)

# Toggle aux1 output
# if webasto.output_aux1:
#     webasto.set_output_aux1(False)
# else:
#     webasto.set_output_aux1(True)

# Toggle aux1 output
# if webasto.output_aux2:
#     webasto.set_output_aux2(False)
# else:
#     webasto.set_output_aux2(True)

# Set timeout for aux1
# webasto.set_aux_timeout(2400)

# Set timeout for aux2
# webasto.set_aux_timeout(2400, Outputs.AUX2)

# Update data
# webasto.update()
