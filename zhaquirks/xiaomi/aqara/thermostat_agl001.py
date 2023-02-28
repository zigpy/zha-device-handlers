"""Aqara E1 Radiator Thermostat Quirk."""
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, Time
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

    # remove cooling mode
    _CONSTANT_ATTRIBUTES = {
        Thermostat.attributes_by_name[
            "ctrl_sequence_of_oper"
        ].id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
    ):
        """Pass reading attributes to Xiaomi cluster if applicable."""
        if "system_mode" in attributes:
            self.debug("Passing 'system_mode' read to Xiaomi cluster")
            return await self.endpoint.aqara_cluster.read_attributes(
                [SYSTEM_MODE], allow_cache, only_cache, manufacturer
            )
        return await super().read_attributes(
            attributes, allow_cache, only_cache, manufacturer
        )

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Pass writing attributes to Xiaomi cluster if applicable."""
        if "system_mode" in attributes:
            self.debug("Passing 'system_mode' write to Xiaomi cluster")
            return await self.endpoint.aqara_cluster.write_attributes(
                {SYSTEM_MODE: min(int(attributes.get("system_mode")), 1)}
            )
        return await super().write_attributes(attributes, manufacturer)


SYSTEM_MODE = 0x0271
PRESET = 0x0272
WINDOW_DETECTION = 0x0273
VALVE_DETECTION = 0x0274
VALVE_ALARM = 0x0275
CHILD_LOCK = 0x0277
AWAY_PRESET_TEMPERATURE = 0x0279
WINDOW_OPEN = 0x027A
CALIBRATED = 0x027B
SENSOR = 0x027E
BATTERY_PERCENTAGE = 0x040A

XIAOMI_CLUSTER_ID = 0xFCC0


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    ep_attribute = "aqara_cluster"

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            SYSTEM_MODE: ("system_mode", t.uint8_t, True),
            PRESET: ("preset", t.uint8_t, True),
            WINDOW_DETECTION: ("window_detection", t.uint8_t, True),
            VALVE_DETECTION: ("valve_detection", t.uint8_t, True),
            VALVE_ALARM: ("valve_alarm", t.uint32_t, True),
            CHILD_LOCK: ("child_lock", t.uint8_t, True),
            AWAY_PRESET_TEMPERATURE: ("away_preset_temperature", t.uint32_t, True),
            WINDOW_OPEN: ("window_open", t.uint8_t, True),
            CALIBRATED: ("calibrated", t.uint8_t, True),
            SENSOR: ("sensor", t.uint8_t, True),
            BATTERY_PERCENTAGE: ("battery_percentage", t.uint8_t, True),
        }
    )

    def _update_attribute(self, attrid, value):
        self.debug("Updating attribute on Xiaomi cluster %s with %s", attrid, value)
        if attrid == BATTERY_PERCENTAGE:
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
                    Ota.cluster_id,
                ],
            }
        }
    }
