import logging
from cbpi.api import KettleController, Property, cbpi
logger = logging.getLogger(__name__)
@cbpi.controller
class CustomPIDHermsController(KettleController):
# --- Standard PID Properties ---
p_gain = Property.Number("P-Gain", configurable=True,
default_value=10.0, description="Proportional gain")
i_gain = Property.Number("I-Gain", configurable=True,
default_value=0.1, description="Integral gain")
d_gain = Property.Number("D-Gain", configurable=True,
default_value=1.0, description="Derivative gain")
max_output = Property.Number("Max PID Power (%)",
configurable=True, default_value=100, description="Maximum power allowed for PID control")
max_boil_temp = Property.Number("Boil Temp Threshold",
configurable=True, default_value=98.0, description="Temperature above which PID is ignored and constant power is applied")
max_boil_output = Property.Number("Max Boil Power (%)",
configurable=True, default_value=80, description="Constant power percentage used during boiling")
# --- Dual Sensor & Delta Protection Properties ---
# Note: The standard "Kettle Sensor" in CBPi will act as your Mash
Sensor (driving the target temperature)
hlt_sensor = Property.Sensor("HLT Sensor", description="Select the sensor monitoring your Hot Liquor Tank (HLT)")
max_delta = Property.Number("Max Delta Temp", configurable=True,
default_value=5.0, description="Max allowed temp difference between HLT and Mash before shutting down power")
def __init__(self, cbpi, id, props):
super(CustomPIDHermsController, self).__init__(cbpi, id,
props)
self.integral = 0.0
self.last_error = 0.0
self.delta_interrupted = False # Track if we are currently in a safety lockout
async def run(self):
"""
Main logic loop executing dual-sensor monitoring and Delta safety checks.
"""
while self.is_running():
try:
# 1. Fetch current target and Mash temperature (from
the primary Kettle sensor)
target_temp = float(self.get_target_temp())
mash_temp = float(self.get_current_temp())
# 2. Fetch the secondary HLT sensor temperature
hlt_temp_str =
self.cbpi.cache.get("sensor").get(self.hlt_sensor).value
if hlt_temp_str is None:
logger.warning("[CustomPIDHerms] HLT Sensor
reading is unavailable. Skipping cycle for safety.")
await self.set_power(0.0)
await cbpi.sleep(2)
continue
hlt_temp = float(hlt_temp_str)
current_delta = hlt_temp - mash_temp
max_allowed_delta = float(self.max_delta)
# 3. Delta Safety Check Logic
if current_delta > max_allowed_delta:
if not self.delta_interrupted:
logger.warning(
f"[CustomPIDHerms] SAFETY ALERT: HLT
({hlt_temp:.2f}°C) exceeds Mash ({mash_temp:.2f}°C) "
f"by {current_delta:.2f}°C (Max Delta:
{max_allowed_delta}°C). Shutting down heating element."
)
self.delta_interrupted = True
# Force heating element off
await self.set_power(0.0)
# Pause the PID integral tracking while interrupted so it doesn't wind up heavily
await cbpi.sleep(2)
continue
# If it was interrupted but has now dropped back into the safe zone
if self.delta_interrupted and current_delta <=
max_allowed_delta:
logger.info(f"[CustomPIDHerms] Delta recovered
({current_delta:.2f}°C). Resuming PID logic.")
self.delta_interrupted = False
# 4. Boil Threshold Check
if mash_temp >= float(self.max_boil_temp):
logger.info(f"[CustomPIDHerms] Target reached Boil
threshold. Setting flat power.")
await self.set_power(float(self.max_boil_output))
# 5. Standard PID Math (driven by the Mash temperature)
else:
error = target_temp - mash_temp
self.integral += error
derivative = error - self.last_error
p_out = float(self.p_gain) * error
i_out = float(self.i_gain) * self.integral
d_out = float(self.d_gain) * derivative
output = p_out + i_out + d_out
output = max(0.0, min(output,
float(self.max_output)))
self.last_error = error
logger.info(
f"[CustomPIDHerms] Mash: {mash_temp:.1f}°C |
HLT: {hlt_temp:.1f}°C | "
f"Delta: {current_delta:.1f}°C | Output Power:
{output:.1f}%"
)
await self.set_power(output)
except Exception as e:
logger.error(f"Error in CustomPIDHerms execution:
{str(e)}")
await self.set_power(0.0) # Safe default on error
await cbpi.sleep(2)
def stop(self):
"""Cleanup actions when the kettle logic stops."""
self.integral = 0.0
self.last_error = 0.0
self.delta_interrupted = False
super(CustomPIDHermsController, self).stop()
