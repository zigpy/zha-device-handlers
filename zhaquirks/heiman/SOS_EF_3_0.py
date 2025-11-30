from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.util.dt import now, as_local

(
	QuirkBuilder("HEIMAN", "SOS-EF-3.0")
	.sensor(
		attribute_name="zone_status",
		cluster_id=0x0500,
		attribute_converter=lambda x: as_local(now()),
		state_class=SensorStateClass.MEASUREMENT,
		device_class=SensorDeviceClass.TIMESTAMP,
		fallback_name="Timestamp"
	)
	.add_to_registry()
)