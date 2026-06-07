"""Aqara W500 floor heating thermostat (lumi.airrtc.aeu001 / UT-A01E)."""

from __future__ import annotations

from zigpy import types as t
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType, UnitOfTemperature
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.xiaomi import LUMI, XiaomiAqaraE1Cluster

XIAOMI_MFG_CODE = 0x115F


class AqaraThermostatPreset(t.enum8):
    """Preset attribute values."""

    Home = 0x01
    Away = 0x02
    Sleep = 0x03
    Vacation = 0x05
    Evening = 0x06
    Manual = 0x08


class AqaraThermostatState(t.enum8):
    """Heating state attribute values."""

    Working = 0x00
    Idle = 0x02


class AqaraSensorSource(t.enum8):
    """Temperature sensor source attribute values."""

    Internal = 0x00
    External = 0x01
    NTC = 0x02


class AqaraNTCType(t.enum32):
    """External NTC sensor resistance attribute values."""

    NTC_10k = 10
    NTC_50k = 50
    NTC_100k = 100
    Unknown = 10000


class AqaraThermostatW500Cluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster for the W500 floor heating thermostat."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        sensor_source = ZCLAttributeDef(
            id=0x0280,
            type=AqaraSensorSource,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        window_detection = ZCLAttributeDef(
            id=0x0273,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        child_lock = ZCLAttributeDef(
            id=0x0277,
            type=t.Bool,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        hysteresis = ZCLAttributeDef(
            id=0x030C,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        state = ZCLAttributeDef(
            id=0x0310,
            type=AqaraThermostatState,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        preset = ZCLAttributeDef(
            id=0x0311,
            type=AqaraThermostatPreset,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )

        ntc_sensor_type = ZCLAttributeDef(
            id=0x0315,
            type=AqaraNTCType,
            zcl_type=DataTypeId.uint32,
            access="rwp",
            manufacturer_code=XIAOMI_MFG_CODE,
        )


(
    QuirkBuilder(LUMI, "lumi.airrtc.aeu001")
    .applies_to("Aqara", "lumi.airrtc.aeu001")
    .replaces(AqaraThermostatW500Cluster)
    .enum(
        AqaraThermostatW500Cluster.AttributeDefs.preset.name,
        AqaraThermostatPreset,
        AqaraThermostatW500Cluster.cluster_id,
        translation_key="preset",
        fallback_name="Preset",
    )
    .enum(
        AqaraThermostatW500Cluster.AttributeDefs.state.name,
        AqaraThermostatState,
        AqaraThermostatW500Cluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="thermostat_state",
        fallback_name="State",
    )
    .enum(
        AqaraThermostatW500Cluster.AttributeDefs.sensor_source.name,
        AqaraSensorSource,
        AqaraThermostatW500Cluster.cluster_id,
        translation_key="temperature_sensor_source",
        fallback_name="Temperature sensor source",
    )
    .enum(
        AqaraThermostatW500Cluster.AttributeDefs.ntc_sensor_type.name,
        AqaraNTCType,
        AqaraThermostatW500Cluster.cluster_id,
        translation_key="ntc_sensor_type",
        fallback_name="NTC sensor type",
    )
    .switch(
        AqaraThermostatW500Cluster.AttributeDefs.window_detection.name,
        AqaraThermostatW500Cluster.cluster_id,
        translation_key="window_detection",
        fallback_name="Open window detection",
    )
    .switch(
        AqaraThermostatW500Cluster.AttributeDefs.child_lock.name,
        AqaraThermostatW500Cluster.cluster_id,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .number(
        AqaraThermostatW500Cluster.AttributeDefs.hysteresis.name,
        AqaraThermostatW500Cluster.cluster_id,
        min_value=0,
        max_value=3,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="hysteresis",
        fallback_name="Hysteresis",
    )
    .add_to_registry()
)
