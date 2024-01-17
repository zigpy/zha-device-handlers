"""Module for Philips quirks implementations."""
from __future__ import annotations

from typing import Any, Final

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.types.basic import enum_factory
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    Direction,
    GeneralCommand,
    ZCLAttributeDef,
    ZCLHeader,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

WWAH_CLUSTER_ID = 0xFC57


class DisplayUnit(enum_factory(t.uint16_t)):
    Celsius = 0
    Fahrenheit = 1


class SonoffClusterFC11(CustomCluster):
    """Sonoff custom cluster."""

    DisplayUnit: Final = DisplayUnit

    cluster_id = 0xFC11
    name = "SonoffClusterFC11"

    class AttributeDefs(BaseAttributeDefs):
        high_temperature_threshold: Final = ZCLAttributeDef(
            id=0x0003, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        low_temperature_threshold: Final = ZCLAttributeDef(
            id=0x0004, type=t.int16s, access="rwp", is_manufacturer_specific=True
        )
        low_humidity_threshold: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        high_humidity_threshold: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )
        display_unit: Final = ZCLAttributeDef(
            id=0x0007, type=DisplayUnit, access="rwp", is_manufacturer_specific=True
        )
        unknown_fffd: Final = ZCLAttributeDef(
            id=0xFFFD, type=t.uint16_t, access="rwp", is_manufacturer_specific=True
        )

    def _create_request(
        self,
        *,
        general: bool,
        command_id: GeneralCommand | int,
        schema: dict | t.Struct,
        manufacturer: int | None = None,
        tsn: int | None = None,
        disable_default_response: bool,
        direction: Direction,
        # Schema args and kwargs
        args: tuple[Any, ...],
        kwargs: Any,
    ) -> tuple[ZCLHeader, bytes]:
        """Override all request to disable manufacturer."""
        return super()._create_request(
            general=general,
            command_id=command_id,
            schema=schema,
            manufacturer=ZCLHeader.NO_MANUFACTURER_ID,
            tsn=tsn,
            disable_default_response=disable_default_response,
            direction=direction,
            args=args,
            kwargs=kwargs,
        )


class SonoffSNZB02D(CustomDevice):
    """Sonoff LCD Smart Temperature Humidity Sensor - model SNZB-02D"""

    signature = {
        MODELS_INFO: [
            ("SONOFF", "SNZB-02D"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    SonoffClusterFC11.cluster_id,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    RelativeHumidity.cluster_id,
                    SonoffClusterFC11,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
