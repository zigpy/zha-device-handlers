"""Schneider Electric NHMOTION motion sensors with a relay or dimmer output."""

import math
from typing import Final

from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.number import NumberConfigurationEntity
from zigpy import types as t
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import LIGHT_LUX, NumberDeviceClass, QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.schneiderelectric import (
    SE_MANUF_ID,
    SE_MANUF_NAME,
    SEBallast,
    SEBasic,
    SEControlMode,
    SEOnOff,
)

MOTION_ENDPOINT_ID = 37
SWITCH_ENDPOINT_ID = 1
DIMMER_ENDPOINT_ID = 3

AMBIENCE_LIGHT_THRESHOLD_MIN_LUX = 1
AMBIENCE_LIGHT_THRESHOLD_MAX_LUX = 2000


def lux_to_raw(lux: float) -> int:
    """Encode lux the same way as ZCL illuminance: 10000 * log10(lux) + 1."""
    return round(10000 * math.log10(max(lux, AMBIENCE_LIGHT_THRESHOLD_MIN_LUX)) + 1)


def raw_to_lux(raw: int) -> int:
    """Decode a ZCL illuminance encoded value to lux."""
    return round(10 ** ((raw - 1) / 10000))


class SEOccupancySensitivity(t.enum8):
    """Sensitivity of the PIR sensor. The device stores it as a plain uint8."""

    Low = 50
    Medium = 75
    High = 100


class SEOccupancySensing(CustomCluster, OccupancySensing):
    """Occupancy sensing cluster with the Schneider Electric sensitivity attribute."""

    manufacturer_id_override = SE_MANUF_ID

    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Attribute definitions."""

        se_sensitivity: Final = ZCLAttributeDef(
            id=0xE003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )


class SEOccupancyConfiguration(CustomCluster):
    """Schneider Electric manufacturer specific occupancy configuration cluster."""

    name = "Schneider Electric Manufacturer Specific Occupancy Configuration"
    ep_attribute = "occupancy_configuration"
    cluster_id = 0xFF19
    manufacturer_id_override = SE_MANUF_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Illuminance above which occupancy does not switch the light on,
        # encoded like the ZCL illuminance measured value.
        ambience_light_threshold: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )


class SEAmbienceLightThreshold(NumberConfigurationEntity):
    """Ambience light threshold in lux, stored by the device as encoded illuminance."""

    _unique_id_suffix = "ambience_light_threshold"
    _attribute_name = (
        SEOccupancyConfiguration.AttributeDefs.ambience_light_threshold.name
    )
    _attr_translation_key = "ambience_light_threshold"
    _attr_fallback_name = "Ambience light threshold"
    _attr_device_class = NumberDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_native_min_value = AMBIENCE_LIGHT_THRESHOLD_MIN_LUX
    _attr_native_max_value = AMBIENCE_LIGHT_THRESHOLD_MAX_LUX
    _attr_native_step = 1

    _server_cluster_config = {
        SEOccupancyConfiguration.cluster_id: ClusterConfig(
            attributes={
                SEOccupancyConfiguration.AttributeDefs.ambience_light_threshold: (
                    AttrConfig(read_on_startup=False)
                ),
            },
        ),
    }

    @property
    def native_value(self) -> int | None:
        """Return the threshold in lux."""
        raw = self._cluster.get(self._attribute_name)
        if raw is None:
            return None
        return raw_to_lux(raw)

    async def async_set_native_value(self, value: float) -> None:
        """Write the threshold given in lux."""
        await super().async_set_native_value(lux_to_raw(value))


base_motion = (
    QuirkBuilder()
    .replaces(SEOccupancySensing, endpoint_id=MOTION_ENDPOINT_ID)
    .replaces(SEOccupancyConfiguration, endpoint_id=MOTION_ENDPOINT_ID)
    .enum(
        attribute_name=SEOccupancySensing.AttributeDefs.se_sensitivity.name,
        enum_class=SEOccupancySensitivity,
        cluster_id=SEOccupancySensing.cluster_id,
        endpoint_id=MOTION_ENDPOINT_ID,
        translation_key="occupancy_sensitivity",
        fallback_name="Occupancy sensitivity",
    )
    .adds_entity(
        SEAmbienceLightThreshold,
        endpoint_id=MOTION_ENDPOINT_ID,
        cluster_id=SEOccupancyConfiguration.cluster_id,
        force_create=True,
    )
)

(
    base_motion.clone()
    .applies_to(SE_MANUF_NAME, "NHMOTION/SWITCH/1")
    .replaces(SEBasic, endpoint_id=SWITCH_ENDPOINT_ID)
    .replaces(SEOnOff, endpoint_id=SWITCH_ENDPOINT_ID)
    .add_to_registry()
)

(
    base_motion.clone()
    .applies_to(SE_MANUF_NAME, "NHMOTION/DIMMER/1")
    .applies_to(SE_MANUF_NAME, "NHMOTION/UNIDIM/1")
    .replaces(SEBasic, endpoint_id=DIMMER_ENDPOINT_ID)
    .replaces(SEBallast, endpoint_id=DIMMER_ENDPOINT_ID)
    .replaces(SEOnOff, endpoint_id=DIMMER_ENDPOINT_ID)
    .enum(
        attribute_name=SEBallast.AttributeDefs.se_control_mode.name,
        enum_class=SEControlMode,
        cluster_id=SEBallast.cluster_id,
        endpoint_id=DIMMER_ENDPOINT_ID,
        translation_key="control_mode",
        fallback_name="Control mode",
    )
    .add_to_registry()
)
