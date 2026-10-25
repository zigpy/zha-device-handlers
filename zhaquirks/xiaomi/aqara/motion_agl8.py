"""Quirk for Aqara lumi.sensor_occupy.agl8."""

from typing import Final

from zha.application import EntityType
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zigpy import types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.builder.metadata import ReportingConfig
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster, XiaomiPowerConfiguration

AQARA_MANUFACTURER_CODE: Final = 0x115F


class FP300PowerConfigurationVoltage(XiaomiPowerConfiguration):
    """Battery level based on voltage, ignoring the device's own buggy percentage reports."""

    MIN_VOLTS_MV = 2800
    MAX_VOLTS_MV = 3000

    def battery_percent_reported(self, battery_percent: int) -> None:
        """Ignore buggy percentage reports from device."""


class AqaraFP300ManuCluster(XiaomiAqaraE1Cluster):
    """Aqara FP300 manufacturer cluster."""

    cluster_id = 0xFCC0
    ep_attribute = "aqara_fp300_manu"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for Aqara FP300 manu cluster."""

        presence: Final = ZCLAttributeDef(
            id=0x0142,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

        pir_detection: Final = ZCLAttributeDef(
            id=0x014D,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )


(
    QuirkBuilder("Aqara", "lumi.sensor_occupy.agl8")
    .friendly_name(manufacturer="Aqara", model="Presence Sensor FP300")
    .replaces(AqaraFP300ManuCluster)
    .replaces(FP300PowerConfigurationVoltage)
    .binary_sensor(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.presence.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        entity_type=EntityType.STANDARD,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=1,
        ),
        translation_key="occupancy",
        fallback_name="Occupancy",
    )
    .binary_sensor(
        attribute_name=AqaraFP300ManuCluster.AttributeDefs.pir_detection.name,
        cluster_id=AqaraFP300ManuCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOTION,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=900,
            reportable_change=1,
        ),
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="pir_detection",
        fallback_name="PIR detection",
    )
    .add_to_registry()
)
