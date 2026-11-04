"""Quirk for Aqara aqara.feeder.acn001."""

from __future__ import annotations

import logging
from typing import Any, Final

from zigpy import types
from zigpy.profiles import zgp, zha
from zigpy.zcl import AttributeReportedEvent, AttributeUpdatedEvent, foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster, XiaomiCustomDevice

# 32 bit signed integer values that are encoded in FEEDER_ATTR = 0xFFF1
FEEDING = 0x04150055
FEEDING_REPORT = 0x041502BC
PORTIONS_DISPENSED = 0x0D680055
WEIGHT_DISPENSED = 0x0D690055
ERROR_DETECTED = 0x0D0B0055
SCHEDULING_STRING = 0x080008C8
DISABLE_LED_INDICATOR = 0x04170055
CHILD_LOCK = 0x04160055
FEEDING_MODE = 0x04180055
SERVING_SIZE = 0x0E5C0055
PORTION_WEIGHT = 0x0E5F0055

FEEDER_ATTR = 0xFFF1
FEEDER_ATTR_NAME = "feeder_attr"

# Fake ZCL attribute ids we can use for entities for the opple cluster
ZCL_FEEDING = 0x1388
ZCL_LAST_FEEDING_SOURCE = 0x1389
ZCL_LAST_FEEDING_SIZE = 0x138A
ZCL_PORTIONS_DISPENSED = 0x138B
ZCL_WEIGHT_DISPENSED = 0x138C
ZCL_ERROR_DETECTED = 0x138D
ZCL_DISABLE_LED_INDICATOR = 0x138E
ZCL_CHILD_LOCK = 0x138F
ZCL_FEEDING_MODE = 0x1390
ZCL_SERVING_SIZE = 0x1391
ZCL_PORTION_WEIGHT = 0x1392

AQARA_TO_ZCL: dict[int, int] = {
    FEEDING: ZCL_FEEDING,
    ERROR_DETECTED: ZCL_ERROR_DETECTED,
    DISABLE_LED_INDICATOR: ZCL_DISABLE_LED_INDICATOR,
    CHILD_LOCK: ZCL_CHILD_LOCK,
    FEEDING_MODE: ZCL_FEEDING_MODE,
    SERVING_SIZE: ZCL_SERVING_SIZE,
    PORTION_WEIGHT: ZCL_PORTION_WEIGHT,
}

ZCL_TO_AQARA: dict[int, int] = {
    ZCL_FEEDING: FEEDING,
    ZCL_DISABLE_LED_INDICATOR: DISABLE_LED_INDICATOR,
    ZCL_CHILD_LOCK: CHILD_LOCK,
    ZCL_FEEDING_MODE: FEEDING_MODE,
    ZCL_SERVING_SIZE: SERVING_SIZE,
    ZCL_PORTION_WEIGHT: PORTION_WEIGHT,
    ZCL_ERROR_DETECTED: ERROR_DETECTED,
}

LOGGER = logging.getLogger(__name__)


class FeedingSource(types.enum8):
    """Feeding source."""

    Feeder = 0x01
    Remote = 0x02


class FeedingMode(types.enum8):
    """Feeding mode."""

    Manual = 0x00
    Schedule = 0x01


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        feeding: Final = ZCLAttributeDef(
            id=ZCL_FEEDING, type=types.Bool, manufacturer_code=0x115F
        )
        last_feeding_source: Final = ZCLAttributeDef(
            id=ZCL_LAST_FEEDING_SOURCE, type=FeedingSource, manufacturer_code=0x115F
        )
        last_feeding_size: Final = ZCLAttributeDef(
            id=ZCL_LAST_FEEDING_SIZE, type=types.uint8_t, manufacturer_code=0x115F
        )
        portions_dispensed: Final = ZCLAttributeDef(
            id=ZCL_PORTIONS_DISPENSED, type=types.uint16_t, manufacturer_code=0x115F
        )
        weight_dispensed: Final = ZCLAttributeDef(
            id=ZCL_WEIGHT_DISPENSED, type=types.uint32_t, manufacturer_code=0x115F
        )
        error_detected: Final = ZCLAttributeDef(
            id=ZCL_ERROR_DETECTED, type=types.Bool, manufacturer_code=0x115F
        )
        disable_led_indicator: Final = ZCLAttributeDef(
            id=ZCL_DISABLE_LED_INDICATOR, type=types.Bool, manufacturer_code=0x115F
        )
        child_lock: Final = ZCLAttributeDef(
            id=ZCL_CHILD_LOCK, type=types.Bool, manufacturer_code=0x115F
        )
        feeding_mode: Final = ZCLAttributeDef(
            id=ZCL_FEEDING_MODE, type=FeedingMode, manufacturer_code=0x115F
        )
        serving_size: Final = ZCLAttributeDef(
            id=ZCL_SERVING_SIZE, type=types.uint8_t, manufacturer_code=0x115F
        )
        portion_weight: Final = ZCLAttributeDef(
            id=ZCL_PORTION_WEIGHT, type=types.uint8_t, manufacturer_code=0x115F
        )
        feeder_attr: Final = ZCLAttributeDef(
            id=FEEDER_ATTR, type=types.LVBytes, manufacturer_code=0x115F
        )

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._send_sequence: int = None
        # Set default values for attributes
        if ZCL_DISABLE_LED_INDICATOR not in self._attr_cache:
            self._update_attribute(ZCL_DISABLE_LED_INDICATOR, False)
        if ZCL_CHILD_LOCK not in self._attr_cache:
            self._update_attribute(ZCL_CHILD_LOCK, False)
        if ZCL_FEEDING_MODE not in self._attr_cache:
            self._update_attribute(ZCL_FEEDING_MODE, FeedingMode.Manual)
        if ZCL_SERVING_SIZE not in self._attr_cache:
            self._update_attribute(ZCL_SERVING_SIZE, 1)
        if ZCL_PORTION_WEIGHT not in self._attr_cache:
            self._update_attribute(ZCL_PORTION_WEIGHT, 8)
        if ZCL_ERROR_DETECTED not in self._attr_cache:
            self._update_attribute(ZCL_ERROR_DETECTED, False)
        if ZCL_PORTIONS_DISPENSED not in self._attr_cache:
            self._update_attribute(ZCL_PORTIONS_DISPENSED, 0)
        if ZCL_WEIGHT_DISPENSED not in self._attr_cache:
            self._update_attribute(ZCL_WEIGHT_DISPENSED, 0)

        # Subscribe to attribute events to parse feeder_attr
        self.on_event(AttributeReportedEvent.event_type, self._handle_attribute_event)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_attribute_event)

    def _handle_attribute_event(
        self, event: AttributeReportedEvent | AttributeUpdatedEvent
    ) -> None:
        """Handle attribute report/update event to parse feeder attribute."""
        if event.attribute_id == FEEDER_ATTR:
            self._parse_feeder_attribute(event.value)

    def _update_feeder_attribute(self, attrid: int, value: Any) -> None:
        zcl_attr_def = self.attributes.get(AQARA_TO_ZCL[attrid])
        self._update_attribute(zcl_attr_def.id, zcl_attr_def.type.deserialize(value)[0])

    def _parse_feeder_attribute(self, value: bytes) -> None:
        """Parse the feeder attribute."""
        attribute, _ = types.int32s_be.deserialize(value[3:7])
        LOGGER.debug("OppleCluster._parse_feeder_attribute: attribute: %s", attribute)
        length, _ = types.uint8_t.deserialize(value[7:8])
        LOGGER.debug("OppleCluster._parse_feeder_attribute: length: %s", length)
        attribute_value = value[8 : (length + 8)]
        LOGGER.debug("OppleCluster._parse_feeder_attribute: value: %s", attribute_value)

        if attribute in AQARA_TO_ZCL:
            self._update_feeder_attribute(attribute, attribute_value)
        elif attribute == FEEDING_REPORT:
            attr_str = attribute_value.decode("utf-8")
            feeding_source = attr_str[0:2]
            feeding_size = attr_str[3:4]
            self._update_attribute(
                ZCL_LAST_FEEDING_SOURCE, FeedingSource(feeding_source)
            )
            self._update_attribute(ZCL_LAST_FEEDING_SIZE, int(feeding_size, base=16))
        elif attribute == PORTIONS_DISPENSED:
            portions_per_day, _ = types.uint16_t_be.deserialize(attribute_value)
            self._update_attribute(ZCL_PORTIONS_DISPENSED, portions_per_day)
        elif attribute == WEIGHT_DISPENSED:
            weight_per_day, _ = types.uint32_t_be.deserialize(attribute_value)
            self._update_attribute(ZCL_WEIGHT_DISPENSED, weight_per_day)
        elif attribute == SCHEDULING_STRING:
            LOGGER.debug(
                "OppleCluster._parse_feeder_attribute: schedule not currently handled: attribute: %s value: %s",
                attribute,
                attribute_value,
            )
        else:
            LOGGER.debug(
                "OppleCluster._parse_feeder_attribute: unhandled attribute: %s value: %s",
                attribute,
                attribute_value,
            )

    def _build_feeder_attribute(
        self, attribute_id: int, value: Any = None, length: int | None = None
    ):
        """Build the Xiaomi feeder attribute."""
        LOGGER.debug(
            "OppleCluster.build_feeder_attribute: id: %s, value: %s length: %s",
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
            "OppleCluster.build_feeder_attribute: id: %s, cooked value: %s length: %s",
            attribute_id,
            val,
            length,
        )
        return FEEDER_ATTR_NAME, val

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
            if attr_id in ZCL_TO_AQARA:
                attribute, cooked_value = self._build_feeder_attribute(
                    ZCL_TO_AQARA[attr_id],
                    value,
                    4 if attr_def.name in ["serving_size", "portion_weight"] else 1,
                )
                attrs[attribute] = cooked_value
            else:
                attrs[attr] = value
        LOGGER.debug("OppleCluster.write_attributes: %s", attrs)
        # Skip attr cache because of the encoding from Xiaomi and
        # the attributes are reported back by the device
        kwargs.pop("update_cache", None)  # To not break when this is passed already
        return await super().write_attributes(attrs, update_cache=False, **kwargs)


class AqaraFeederAcn001(XiaomiCustomDevice):
    """Aqara aqara.feeder.acn001 custom device implementation."""

    signature = {
        MODEL: "aqara.feeder.acn001",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    replacement = {
        MANUFACTURER: "Aqara",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OppleCluster,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
