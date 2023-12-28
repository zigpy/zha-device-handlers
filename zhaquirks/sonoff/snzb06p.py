"""Sonoff Smart Button SNZB-06P"""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import AnalogOutput, Basic, BinaryInput, Identify, Ota
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

SONOFF_CLUSTER_ID = 0xFC57
SONOFF_CLUSTER_ID_2 = 0xFC11
SONOFF_MANUFACTURER_ID = 0x1286
ATTR_SONOFF_ILLUMINATION_STATUS = 0x2001
ATTR_PRESENT_VALUE = 0x0055
ATTR_ULTRASONIC_O_TO_U_DELAY = 0x0020


class SonoffOccupancyTimeout(LocalDataCluster, AnalogOutput):
    """AnalogOutput cluster for setting the timeout for occupancy state."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.occupancy_timeout_bus.add_listener(self)
        self._update_attribute(
            self.attributes_by_name["description"].id, "Occupancy timeout"
        )
        self._update_attribute(self.attributes_by_name["max_present_value"].id, 65535)
        self._update_attribute(self.attributes_by_name["min_present_value"].id, 15)
        self._update_attribute(self.attributes_by_name["resolution"].id, 1)
        self._update_attribute(
            self.attributes_by_name["application_type"].id, 0x000E0001
        )  # Type=time
        self._update_attribute(
            self.attributes_by_name["engineering_units"].id, 73
        )  # Units=seconds

    def set_value(self, value):
        """Set new occupancy timeout value."""
        self._update_attribute(self.attributes_by_name["present_value"].id, value)

    def get_value(self):
        """Get current occupancy timeout value."""
        return self._attr_cache.get(self.attributes_by_name["present_value"].id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Modify value before passing it to the set_data tuya command."""
        for attrid, value in attributes.items():
            if isinstance(attrid, str):
                attrid = self.attributes_by_name[attrid].id
            if attrid not in self.attributes:
                self.error("%d is not a valid attribute id", attrid)
                continue
            if attrid == ATTR_PRESENT_VALUE:
                await self.endpoint.device.endpoints[1].occupancy.write_attributes(
                    {ATTR_ULTRASONIC_O_TO_U_DELAY: value}, manufacturer=None
                )

        return await super().write_attributes(attributes, manufacturer)


class SonoffOccupancyCluster(CustomCluster, OccupancySensing):
    """AnalogOutput cluster for setting the timeout for occupancy state."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == ATTR_ULTRASONIC_O_TO_U_DELAY:
            self.endpoint.device.occupancy_timeout_bus.listener_event(
                "set_value",
                value,
            )


class IlluminationStatus(t.uint8_t):
    """Last captured state of illumination."""

    Dark = 0x00
    Light = 0x01


class SonoffCluster(CustomCluster):
    """Sonoff manufacture specific cluster that provides illuminance"""

    cluster_id = SONOFF_CLUSTER_ID_2
    manufacturer_id_override = SONOFF_MANUFACTURER_ID

    attributes = CustomCluster.attributes.copy()
    attributes.update(
        {
            ATTR_SONOFF_ILLUMINATION_STATUS: (
                "last_illumination_state",
                IlluminationStatus,
                True,
            ),  # ramdom attribute ID
        }
    )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == ATTR_SONOFF_ILLUMINATION_STATUS:
            self.endpoint.device.illumination_bus.listener_event(
                "set_value",
                value,
            )


class SonoffIlluminanceLevelSensing(LocalDataCluster, BinaryInput):
    """Sonoff emulated illuminance level sensing cluster to provide access to FC11/2001."""

    name = "Last Illumination State"

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.illumination_bus.add_listener(self)
        self._update_attribute(
            self.attributes_by_name["description"].id, "Last illumination state"
        )
        self._update_attribute(self.attributes_by_name["active_text"].id, "Bright")
        self._update_attribute(self.attributes_by_name["inactive_text"].id, "Dark")
        # self._update_attribute(self.attributes_by_name["application_type"].id, 0x00ff0002)#Type=other

    def set_value(self, value):
        """Set new illumination status value."""
        self._update_attribute(
            self.attributes_by_name["present_value"].id,
            value == IlluminationStatus.Light,
        )


class SonoffPresenceSensorSNZB06P(CustomDevice):
    """Sonoff presence sensor - model SNZB-06P"""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.occupancy_timeout_bus = Bus()
        self.illumination_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=0
        #  device_version=1
        #  input_clusters=[0, 3, 1030, 1280, 64529, 64599]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [
            ("SONOFF", "SNZB-06P"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OccupancySensing.cluster_id,
                    IasZone.cluster_id,
                    SonoffCluster.cluster_id,
                    SONOFF_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    SonoffOccupancyCluster,
                    SonoffCluster,
                    SONOFF_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COMBINED_INTERFACE,
                INPUT_CLUSTERS: [
                    SonoffOccupancyTimeout,
                    SonoffIlluminanceLevelSensing,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
