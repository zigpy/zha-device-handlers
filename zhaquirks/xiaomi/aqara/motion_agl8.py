"""Quirk for Aqara lumi.sensor_occupy.agl8."""

import logging
from typing import Final

from zigpy import types as t
from zigpy.typing import AddressingMode
from zigpy.zcl import foundation
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    DataTypeId,
    ZCLAttributeDef,
    ZCLHeader,
)

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    ReportingConfig,
)
from zhaquirks.const import BatterySize
from zhaquirks.xiaomi import (
    BATTERY_QUANTITY_ATTR,
    BATTERY_SIZE_ATTR,
    XIAOMI_AQARA_ATTRIBUTE_E1,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfigurationPercent,
)

_LOGGER = logging.getLogger(__name__)


class FP300PowerConfigurationVoltage(XiaomiPowerConfigurationPercent):
    """Battery from the Aqara TLV report: voltage from tag 23, percentage from tag 24.

    The device also pushes standard PowerConfiguration reports, but those contradict the
    TLV values (e.g. a stuck or zero percentage). They are ignored, so values derived from
    the TLV report are the single source of truth.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        # The FP300 runs on two CR2450 cells, as the device itself reports
        self._CONSTANT_ATTRIBUTES = {
            BATTERY_QUANTITY_ATTR: 2,
            BATTERY_SIZE_ATTR: BatterySize.CR2450,
        }

    def handle_cluster_general_request(
        self,
        hdr: ZCLHeader,
        args: list,
        *,
        dst_addressing: AddressingMode | None = None,
    ) -> None:
        """Ignore the device's standard battery reports."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            if not hdr.frame_control.disable_default_response:
                self.send_default_rsp(hdr, foundation.Status.SUCCESS)
            return
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


class AqaraFP300ManuCluster(XiaomiAqaraE1Cluster):
    """Aqara FP300 manufacturer cluster."""

    cluster_id = 0xFCC0
    ep_attribute = "aqara_fp300_manu"

    async def apply_custom_configuration(self, *args, **kwargs):
        """Read the Aqara TLV struct on (re)configuration, as newer firmware doesn't push it."""
        try:
            await self.read_attributes([self.AttributeDefs.aqara_attributes.id])
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Failed to read initial battery state: %s", exc)

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for Aqara FP300 manu cluster."""

        aqara_attributes: Final = ZCLAttributeDef(
            id=XIAOMI_AQARA_ATTRIBUTE_E1,
            type=t.LVBytes,
            manufacturer_code=0x115F,
        )

        presence: Final = ZCLAttributeDef(
            id=0x0142,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=0x115F,
        )

        pir_detection: Final = ZCLAttributeDef(
            id=0x014D,
            type=t.Bool,
            zcl_type=DataTypeId.uint8,
            access="rp",
            manufacturer_code=0x115F,
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
        fallback_name="Motion",
    )
    .add_to_registry()
)
