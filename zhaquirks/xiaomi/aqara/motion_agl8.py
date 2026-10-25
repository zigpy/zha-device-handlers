"""Quirk for Aqara lumi.sensor_occupy.agl8."""

import logging
from typing import Any, Final

from zigpy import types as t
from zigpy.zcl import AttributeReadEvent
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
from zhaquirks.xiaomi import (
    XIAOMI_AQARA_ATTRIBUTE_E1,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfigurationPercent,
)

_LOGGER = logging.getLogger(__name__)

AQARA_MANUFACTURER_CODE: Final = 0x115F


class FP300PowerConfigurationVoltage(XiaomiPowerConfigurationPercent):
    """Battery from the Aqara TLV report: voltage from tag 23, percentage from tag 24.

    The device also pushes standard PowerConfiguration reports, but those contradict the
    TLV values (e.g. a stuck or zero percentage). Only values derived from the TLV report
    may enter the attribute cache, so there is a single source of truth.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        self._tlv_battery_update = False
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Drop battery attribute updates that don't come from the TLV report."""
        if not self._tlv_battery_update and attrid in (
            self.BATTERY_VOLTAGE_ATTR,
            self.BATTERY_PERCENTAGE_REMAINING,
        ):
            return
        super()._update_attribute(attrid, value)

    def battery_reported(self, voltage_mv: int) -> None:
        """Battery voltage reported from the TLV report."""
        self._tlv_battery_update = True
        try:
            super().battery_reported(voltage_mv)
        finally:
            self._tlv_battery_update = False

    def battery_percent_reported(self, battery_percent: int) -> None:
        """Battery percentage reported from the TLV report."""
        self._tlv_battery_update = True
        try:
            super().battery_percent_reported(battery_percent)
        finally:
            self._tlv_battery_update = False


class AqaraFP300ManuCluster(XiaomiAqaraE1Cluster):
    """Aqara FP300 manufacturer cluster."""

    cluster_id = 0xFCC0
    ep_attribute = "aqara_fp300_manu"

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        # A read response only emits AttributeReadEvent, which the Xiaomi cluster doesn't handle
        self.on_event(AttributeReadEvent.event_type, self._handle_attribute_event)

    async def bind(self, **kwargs):
        """Bind and read the Aqara TLV struct, as newer firmware doesn't push it by itself."""
        result = await super().bind(**kwargs)
        try:
            await self.read_attributes([self.AttributeDefs.aqara_attributes.id])
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Failed to read initial battery state: %s", exc)
        return result

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for Aqara FP300 manu cluster."""

        aqara_attributes: Final = ZCLAttributeDef(
            id=XIAOMI_AQARA_ATTRIBUTE_E1,
            type=t.LVBytes,
            manufacturer_code=AQARA_MANUFACTURER_CODE,
        )

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
        primary=True,
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
