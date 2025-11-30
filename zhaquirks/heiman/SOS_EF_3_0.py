"""Heiman SOS-EF-3.0 device."""

import datetime as dt

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass

(
    QuirkBuilder("HEIMAN", "SOS-EF-3.0")
    .sensor(
        attribute_name="zone_status",
        cluster_id=0x0500,
        attribute_converter=lambda x: dt.datetime.now().astimezone(),
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TIMESTAMP,
        fallback_name="Timestamp",
    )
    .add_to_registry()
)
