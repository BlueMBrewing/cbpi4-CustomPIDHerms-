from setuptools import setup

setup(
  name="cbpi4-CustomPIDHerms",
  version="0.0.1",
  description="Custom PID HERMS Kettle Logic plugin for CraftBeerPi 4 on Pi 5",
  author="BlueMBrewing",
  packages=["cbpi4-CustomPIDHerms"],
  entry_points={
    "cbpi4.plugins": [
      "CustomPIDHermsController = cbpi4-CustomPIDHerms:CustomPIDHermsController"
    ]
  }
)
