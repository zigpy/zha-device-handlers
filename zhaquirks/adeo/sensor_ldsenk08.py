"""Device handler for ADEO Lexman LDSENK08 smart door/window sensor."""

from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import ZONE_STATUS, ZONE_TYPE


class IasMultiZoneCluster(CustomCluster, IasZone):
    """IAS zone cluster with LDSENK08 sensitivity handling.

    `zone_status` bit mapping used by this quirk:
    - bit 0 (`Alarm_1`): contact/opening
    - bit 1 (`Alarm_2`): vibration
    - bit 2 (`Tamper`): tamper/manipulation
    - bit 3: battery low
    """

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Contact_Switch}
    STATUS_CHANGE_COMMAND_ID = IasZone.ClientCommandDefs.status_change_notification.id
    SENSITIVITY_ATTRIBUTE_ID = IasZone.AttributeDefs.current_zone_sensitivity_level.id
    SENSITIVITY_LABELS = {"low": 0, "medium": 1, "high": 2}
    SENSITIVITY_MIN = 0
    SENSITIVITY_MAX = 4

    @classmethod
    def _normalize_sensitivity(cls, value: Any) -> int:
        """Normalize sensitivity value accepted by this sensor."""
        if isinstance(value, str):
            mapped_value = cls.SENSITIVITY_LABELS.get(value.lower())
            if mapped_value is None:
                msg = f"Unsupported sensitivity label: {value}"
                raise ValueError(msg)
            return mapped_value

        normalized_value = int(value)
        if not cls.SENSITIVITY_MIN <= normalized_value <= cls.SENSITIVITY_MAX:
            msg = (
                "Sensitivity must be in range "
                f"{cls.SENSITIVITY_MIN}..{cls.SENSITIVITY_MAX}"
            )
            raise ValueError(msg)
        return normalized_value

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | t.uint16_t | None = None,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes with sensitivity normalization."""
        normalized_attributes = {}
        for attr, value in attributes.items():
            attr_id = attr.id if isinstance(attr, foundation.ZCLAttributeDef) else attr
            if (
                isinstance(attr_id, str)
                and attr_id == IasZone.AttributeDefs.current_zone_sensitivity_level.name
            ) or attr_id == self.SENSITIVITY_ATTRIBUTE_ID:
                normalized_attributes[attr] = self._normalize_sensitivity(value)
            else:
                normalized_attributes[attr] = value

        return await super().write_attributes(
            normalized_attributes, manufacturer=manufacturer, **kwargs
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: (
            t.Addressing.Group | t.Addressing.IEEE | t.Addressing.NWK | None
        ) = None,
    ) -> None:
        """Handle a cluster command received on this cluster."""
        if hdr.command_id == self.STATUS_CHANGE_COMMAND_ID and args:
            try:
                zone_status = int(args[0])
            except (TypeError, ValueError):
                super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
                return
            # Keep full IAS bitmask so contact/vibration/tamper entities can derive from it.
            self.update_attribute(ZONE_STATUS, zone_status)
        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder("ADEO", "LDSENK08")
    .replaces(IasMultiZoneCluster)
    # Contact/opening from IAS zone_status Alarm_1 (bit 0).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.OPENING,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_1),
        unique_id_suffix="contact",
        entity_type=EntityType.STANDARD,
        fallback_name="Contact",
    )
    # Vibration from IAS zone_status Alarm_2 (bit 1).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.VIBRATION,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_2),
        unique_id_suffix="vibration",
        entity_type=EntityType.STANDARD,
        fallback_name="Vibration",
    )
    # Tamper/manipulation from IAS zone_status Tamper (bit 2).
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        entity_type=EntityType.STANDARD,
        fallback_name="Tamper",
    )
    .number(
        attribute_name=IasZone.AttributeDefs.current_zone_sensitivity_level.name,
        cluster_id=IasZone.cluster_id,
        min_value=0,
        max_value=4,
        step=1,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    # Prevent ZHA's stock IAS zone binary (unique id …-1-1280). Quirk binaries use
    # -contact / -vibration / -tamper and must not match this suffix.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        unique_id_suffix="-1-1280",
    )
    .add_to_registry()
)
