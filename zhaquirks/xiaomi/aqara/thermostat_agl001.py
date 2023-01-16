"""Aqara E1 Radiator Thermostat Quirk."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Time
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)


class ThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {0x001B: 0x02}


XIAOMI_CLUSTER_ID = 0xFCC0


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    ep_attribute = "aqara_cluster"

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            0x040A: ("battery_percentage", t.uint8_t, True),
        }
    )

    def _update_attribute(self, attrid, value):
        self.debug("Attribute/Value", attrid, value)
        if attrid == 0x040A:
            self.endpoint.device.battery_bus.listener_event(
                "battery_percent_reported", value
            )
        super()._update_attribute(attrid, value)


class AGL001(XiaomiCustomDevice):
    """Aqara E1 Radiator Thermostat (AGL001) Device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=1
        # input_clusters=[0, 1, 3, 513, 64704]
        # output_clusters=[3, 513, 64704]>
        MODELS_INFO: [(LUMI, "lumi.airrtc.agl001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    Time.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ThermostatCluster,
                    Time.cluster_id,
                    XiaomiPowerConfiguration,
                    AqaraThermostatSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    ThermostatCluster,
                    AqaraThermostatSpecificCluster,
                ],
            }
        }
    }
