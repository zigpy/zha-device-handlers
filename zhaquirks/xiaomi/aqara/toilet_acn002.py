"""Quirk for Aqara aqara.toilet.acn002."""

from __future__ import annotations

import logging
from typing import Any, Final

from zigpy import types
from zigpy.quirks.v2 import BinarySensorDeviceClass, QuirkBuilder
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent, foundation
from zigpy.zcl.clusters.general import Time
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.xiaomi import XiaomiAqaraE1Cluster

TOILET_ATTR = 0xFFF1
TOILET_ATTR_NAME = "toilet_attr"
LOGGER = logging.getLogger(__name__)

# (Aqara_ID, ZCL_ID, Name, Type, Access)
TOILET_REGISTRY = [
    [0x04030055, 0, "lid_switch", types.uint8_t, "rwp"],
    [0x04040055, 0, "seat_switch", types.uint8_t, "rwp"],
    [0x04200055, 0, "night_light", types.uint8_t, "rwp"],
    [0x0E2F0055, 0, "seat_temp", types.uint32_t_be, "rwp"],
    [0x0E300055, 0, "cleaning_mode", types.uint32_t_be, "rwp"],
    [0x0E340055, 0, "nozzle_position", types.uint32_t_be, "rwp"],
    [0x0E330055, 0, "water_pressure", types.uint32_t_be, "rwp"],
    [0x0E320055, 0, "water_temp", types.uint32_t_be, "rwp"],
    [0x0E350055, 0, "dryer_temp", types.uint32_t_be, "rwp"],
    [0x0E270055, 0, "nozzle_clean", types.uint32_t_be, "rwp"],
    [0x04010055, 0, "stop_button", types.uint8_t, "w"],
    [0x04070055, 0, "flush_big", types.uint8_t, "w"],
    [0x04020055, 0, "flush_small", types.uint8_t, "w"],
    [0x04190055, 0, "foam_shield", types.uint8_t, "w"],
    [0x03010055, 0, "occupancy_status", types.Bool, "rp"],
    [0x041A0055, 0, "foot_sensor_switch", types.uint8_t, "rwp"],
    [0x041F0055, 0, "auto_flush_after_leave", types.uint8_t, "rwp"],
    [0x04220055, 0, "beeper_switch", types.uint8_t, "rwp"],
    [0x04240055, 0, "child_seat_mode", types.uint8_t, "rwp"],
    [0x04250055, 0, "pre_mist_switch", types.uint8_t, "rwp"],
    [0x04420055, 0, "auto_foam_on_sit", types.uint8_t, "rwp"],
    [0x04430055, 0, "auto_foam_on_leave", types.uint8_t, "rwp"],
]

AQARA_TO_ZCL: dict[int, int] = {}

ZCL_ID = 0x1388
for item in TOILET_REGISTRY:
    item[1] = ZCL_ID
    ZCL_ID += 1
    AQARA_TO_ZCL[item[0]] = item[1]


class SeatTemp(types.enum32_be):
    """Seat temperature setting."""
    Off = 0
    Temp_31C = 1
    Temp_33C = 2
    Temp_35C = 3
    Temp_37C = 4
    Temp_39C = 5


class CleaningMode(types.enum32_be):
    """Cleaning mode."""
    Stop = 0
    Rear = 1
    Rear_Moving = 2
    Female = 3
    Female_Moving = 4
    Child = 5


class NozzlePosition(types.enum32_be):
    """Nozzle position."""
    Back = 0
    Slightly_Back = 1
    Middle = 2
    Slightly_Front = 3
    Front = 4


class WaterPressure(types.enum32_be):
    """Water pressure."""
    Weak = 0
    Slightly_Weak = 1
    Middle = 2
    Slightly_Strong = 3
    Strong = 4


class WaterTemp(types.enum32_be):
    """Water temperature."""
    Off = 0
    Temp_31C = 1
    Temp_33C = 2
    Temp_35C = 3
    Temp_37C = 4
    Temp_39C = 5


class DryerTemp(types.enum32_be):
    """Dryer temperature."""
    Off = 0
    Normal = 1
    Low = 2
    Mid_Low = 3
    Middle = 4
    Mid_High = 5
    High = 6


class NozzleClean(types.enum32_be):
    """Nozzle cleaning mode."""
    Off = 0
    Auto = 1
    Manual = 2


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        toilet_attr: Final = ZCLAttributeDef(
            id=TOILET_ATTR, type=types.LVBytes, manufacturer_code=0x115F
        )

    for _, zcl_id, attr_name, attr_type, attr_access in TOILET_REGISTRY:
        setattr(
            AttributeDefs,
            attr_name,
            ZCLAttributeDef(id=zcl_id, type=attr_type, access=attr_access),
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._send_sequence: int = None

        # Subscribe to attribute events to parse toilet_attr
        self.on_event(AttributeReportedEvent.event_type, self._handle_attribute_event)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_attribute_event)

    def _handle_attribute_event(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ) -> None:
        """Handle attribute report/update event to parse toilet attribute."""
        if event.attribute_id == TOILET_ATTR:
            self._parse_toilet_attribute(event.value)
        elif event.attribute_id in (0x00FF, 0x0007, 0x00F7):
            pass

    def _update_toilet_attribute(self, attrid: int, value: Any) -> None:
        zcl_attr_def = self.attributes.get(AQARA_TO_ZCL[attrid])
        self._update_attribute(zcl_attr_def.id, zcl_attr_def.type.deserialize(value)[0])

    def _parse_toilet_attribute(self, value: bytes) -> None:
        """Parse the toilet attribute."""
        attribute, _ = types.int32s_be.deserialize(value[3:7])
        LOGGER.debug("OppleCluster._parse_toilet_attribute: attribute: %s", attribute)
        length, _ = types.uint8_t.deserialize(value[7:8])
        LOGGER.debug("OppleCluster._parse_toilet_attribute: length: %s", length)
        attribute_value = value[8 : (length + 8)]
        LOGGER.debug("OppleCluster._parse_toilet_attribute: value: %s", attribute_value)

        if attribute in AQARA_TO_ZCL:
            self._update_toilet_attribute(attribute, attribute_value)
        else:
            LOGGER.debug(
                "OppleCluster._parse_toilet_attribute: unhandled attribute: %s value: %s",
                attribute,
                attribute_value,
            )

    def _build_toilet_attribute(
        self, attribute_id: int, value: Any = None, length: int | None = None
    ):
        """Build the Xiaomi toilet attribute."""
        LOGGER.debug(
            "OppleCluster.build_toilet_attribute: id: %s, value: %s length: %s",
            attribute_id,
            value,
            length,
        )
        self._send_sequence = ((self._send_sequence or 0) + 1) % 256
        val = bytes([0x00, 0x02, self._send_sequence])
        self._send_sequence += 1
        val += types.int32s_be(attribute_id).serialize()
        if length is not None and value is not None:
            val += types.uint8_t(length).serialize()
        if value is not None:
            if length == 1:
                val += types.uint8_t(value).serialize()
            elif length == 2:
                val += types.uint16_t_be(value).serialize()
            elif length == 4:
                val += types.uint32_t_be(value).serialize()
            else:
                val += value
        LOGGER.debug(
            "OppleCluster.build_toilet_attribute: id: %s, cooked value: %s length: %s",
            attribute_id,
            val,
            length,
        )
        return TOILET_ATTR_NAME, val

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Write attributes to device with internal 'attributes' validation."""
        attrs = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            attr_id = attr_def.id
            find_attr = next((k for k, v in AQARA_TO_ZCL.items() if v == attr_id), None)
            if find_attr is not None:
                attribute, cooked_value = self._build_toilet_attribute(
                    find_attr,
                    value,
                    getattr(attr_def.type, "_size", 1),
                )
                attrs[attribute] = cooked_value
            else:
                attrs[attr] = value
        LOGGER.debug("OppleCluster.write_attributes: %s", attrs)
        # Skip attr cache because of the encoding from Xiaomi and
        # the attributes are reported back by the device
        kwargs.pop("update_cache", None)  # To not break when this is passed already
        return await super().write_attributes(attrs, update_cache=False, **kwargs)


(
    QuirkBuilder("Aqara", "aqara.toilet.acn002")
    .applies_to(None, "aqara.toilet.acn002")
    .applies_to(
        None, "lumi.sen_gas.hrcn01"
    )  # The reason for adding lumi.sen_gas.hrcn01 is that the model number reported by a toilet is exactly this
    .friendly_name(
        manufacturer="Aqara",
        model="aqara.toilet.acn002",
    )
    .adds(Time)
    .replaces(OppleCluster)
    .switch(
        OppleCluster.AttributeDefs.lid_switch.name,
        OppleCluster.cluster_id,
        translation_key="lid_switch",
        fallback_name="Lid Switch",
    )
    .switch(
        OppleCluster.AttributeDefs.seat_switch.name,
        OppleCluster.cluster_id,
        translation_key="seat_switch",
        fallback_name="Seat Switch",
    )
    .switch(
        OppleCluster.AttributeDefs.night_light.name,
        OppleCluster.cluster_id,
        translation_key="night_light",
        fallback_name="Night Light",
    )
    .switch(
        OppleCluster.AttributeDefs.foot_sensor_switch.name,
        OppleCluster.cluster_id,
        translation_key="foot_sensor_switch",
        fallback_name="Foot Sensor Switch",
    )
    .switch(
        OppleCluster.AttributeDefs.auto_flush_after_leave.name,
        OppleCluster.cluster_id,
        translation_key="auto_flush_after_leave",
        fallback_name="Auto Flush After Leave",
        off_value=1,
        on_value=0,
    )
    .switch(
        OppleCluster.AttributeDefs.beeper_switch.name,
        OppleCluster.cluster_id,
        translation_key="beeper_switch",
        fallback_name="Beeper Switch",
        off_value=1,
        on_value=0,
    )
    .switch(
        OppleCluster.AttributeDefs.child_seat_mode.name,
        OppleCluster.cluster_id,
        translation_key="child_seat_mode",
        fallback_name="Child Seat Mode",
    )
    .switch(
        OppleCluster.AttributeDefs.pre_mist_switch.name,
        OppleCluster.cluster_id,
        translation_key="pre_mist_switch",
        fallback_name="Pre Mist Switch",
    )
    .switch(
        OppleCluster.AttributeDefs.auto_foam_on_sit.name,
        OppleCluster.cluster_id,
        translation_key="auto_foam_on_sit",
        fallback_name="Auto Foam on Sit",
    )
    .switch(
        OppleCluster.AttributeDefs.auto_foam_on_leave.name,
        OppleCluster.cluster_id,
        translation_key="auto_foam_on_leave",
        fallback_name="Auto Foam on Leave",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.stop_button.name,
        1,
        OppleCluster.cluster_id,
        translation_key="stop_button",
        fallback_name="Stop",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.flush_big.name,
        1,
        OppleCluster.cluster_id,
        translation_key="flush_big",
        fallback_name="Flush Big",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.flush_small.name,
        1,
        OppleCluster.cluster_id,
        translation_key="flush_small",
        fallback_name="Flush Small",
    )
    .write_attr_button(
        OppleCluster.AttributeDefs.foam_shield.name,
        0,
        OppleCluster.cluster_id,
        translation_key="foam_shield",
        fallback_name="Foam Shield",
    )
    .enum(
        OppleCluster.AttributeDefs.seat_temp.name,
        SeatTemp,
        OppleCluster.cluster_id,
        translation_key="seat_temp",
        fallback_name="Seat Temperature",
    )
    .enum(
        OppleCluster.AttributeDefs.cleaning_mode.name,
        CleaningMode,
        OppleCluster.cluster_id,
        translation_key="cleaning_mode",
        fallback_name="Cleaning Mode",
    )
    .enum(
        OppleCluster.AttributeDefs.nozzle_position.name,
        NozzlePosition,
        OppleCluster.cluster_id,
        translation_key="nozzle_position",
        fallback_name="Nozzle Position",
    )
    .enum(
        OppleCluster.AttributeDefs.water_pressure.name,
        WaterPressure,
        OppleCluster.cluster_id,
        translation_key="water_pressure",
        fallback_name="Water Pressure",
    )
    .enum(
        OppleCluster.AttributeDefs.water_temp.name,
        WaterTemp,
        OppleCluster.cluster_id,
        translation_key="water_temp",
        fallback_name="Water Temperature",
    )
    .enum(
        OppleCluster.AttributeDefs.dryer_temp.name,
        DryerTemp,
        OppleCluster.cluster_id,
        translation_key="dryer_temp",
        fallback_name="Dryer Temperature",
    )
    .enum(
        OppleCluster.AttributeDefs.nozzle_clean.name,
        NozzleClean,
        OppleCluster.cluster_id,
        translation_key="nozzle_clean",
        fallback_name="Nozzle Clean",
    )
    .binary_sensor(
        OppleCluster.AttributeDefs.occupancy_status.name,
        OppleCluster.cluster_id,
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        translation_key="occupancy_status",
        fallback_name="Occupancy Status",
    )
    .add_to_registry()
)
