"""Quirk for Aqara aqara.feeder.acn001."""

import logging
from typing import Any

from zigpy.profiles import zha
import zigpy.types as types
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)

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
PORTIONS_PER_DAY = 0x0D680055
WEIGHT_PER_DAY = 0x0D690055
ERROR = 0x0D0B0055
SCHEDULING_STRING = 0x080008C8
LED_INDICATOR = 0x04170055
CHILD_LOCK = 0x04160055
MODE = 0x04180055
SERVING_SIZE = 0x0E5C0055
PORTION_WEIGHT = 0x0E5F0055

FEEDER_ATTR = 0xFFF1

# Fake ZCL attribute ids we can use for entities for the opple cluster
ZCL_FEEDING = 0x1388
ZCL_FEEDING_SOURCE = 0x1389
ZCL_FEEDING_SIZE = 0x138A
ZCL_PORTIONS_PER_DAY = 0x138B
ZCL_WEIGHT_PER_DAY = 0x138C
ZCL_ERROR = 0x138D
ZCL_LED_INDICATOR = 0x138E
ZCL_CHILD_LOCK = 0x138F
ZCL_MODE = 0x1390
ZCL_SERVING_SIZE = 0x1391
ZCL_PORTION_WEIGHT = 0x1392

AQARA_TO_ZCL = {
    FEEDING: ZCL_FEEDING,
    ERROR: ZCL_ERROR,
    LED_INDICATOR: ZCL_LED_INDICATOR,
    CHILD_LOCK: ZCL_CHILD_LOCK,
    MODE: ZCL_MODE,
    SERVING_SIZE: ZCL_SERVING_SIZE,
    PORTION_WEIGHT: ZCL_PORTION_WEIGHT,
}

ZCL_TO_AQARA = {
    ZCL_FEEDING: FEEDING,
    ZCL_LED_INDICATOR: LED_INDICATOR,
    ZCL_CHILD_LOCK: CHILD_LOCK,
    ZCL_MODE: MODE,
    ZCL_SERVING_SIZE: SERVING_SIZE,
    ZCL_PORTION_WEIGHT: PORTION_WEIGHT,
}

LOGGER = logging.getLogger(__name__)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class FeedingSource(types.enum8):
        """Feeding source."""

        Manual = 0x01
        Remote = 0x02

    class FeedingMode(types.enum8):
        """Feeding mode."""

        Manual = 0x00
        Schedule = 0x01

    ep_attribute = "opple_cluster"
    attributes = {
        ZCL_FEEDING: ("feeding", types.Bool, True),
        ZCL_FEEDING_SOURCE: ("feeding_source", FeedingSource, True),
        ZCL_FEEDING_SIZE: ("feeding_size", types.uint8_t, True),
        ZCL_PORTIONS_PER_DAY: ("portions_per_day", types.uint16_t, True),
        ZCL_WEIGHT_PER_DAY: ("weight_per_day", types.uint32_t, True),
        ZCL_ERROR: ("error", types.Bool, True),
        ZCL_LED_INDICATOR: ("led_indicator", types.Bool, True),
        ZCL_CHILD_LOCK: ("child_lock", types.Bool, True),
        ZCL_MODE: ("feeding_mode", FeedingMode, True),
        ZCL_SERVING_SIZE: ("serving_size", types.uint8_t, True),
        ZCL_PORTION_WEIGHT: ("portion_weight", types.uint8_t, True),
        FEEDER_ATTR: ("feeder_attr", types.LVBytes, True),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._send_sequence = None

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        LOGGER.debug(
            "OppleCluster._update_attribute: %s, %s",
            self.attributes.get(attrid).name
            if self.attributes.get(attrid) is not None
            else attrid,
            value.name if isinstance(value, types.enum8) else value,
        )
        if attrid == FEEDER_ATTR:
            self._parse_feeder_attribute(value)

    def _update_feeder_attribute(self, attrid: int, value: Any) -> None:
        zcl_attr_def = self.attributes.get(AQARA_TO_ZCL[attrid])
        self._update_attribute(zcl_attr_def.id, zcl_attr_def.type.deserialize(value)[0])

    def _parse_feeder_attribute(self, value):
        """Parse the feeder attribute."""
        # attribute is big endian, so we need to reverse the bytes
        attribute, _ = types.int32s.deserialize(bytes(reversed(value[3:7])))
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
                ZCL_FEEDING_SOURCE, OppleCluster.FeedingSource(feeding_source)
            )
            self._update_attribute(ZCL_FEEDING_SIZE, feeding_size)
        elif attribute == PORTIONS_PER_DAY:
            portions_per_day, _ = types.uint16_t.deserialize(
                bytes(reversed(attribute_value))
            )
            self._update_attribute(ZCL_PORTIONS_PER_DAY, portions_per_day)
        elif attribute == WEIGHT_PER_DAY:
            weight_per_day, _ = types.uint32_t.deserialize(
                bytes(reversed(attribute_value))
            )
            self._update_attribute(ZCL_WEIGHT_PER_DAY, weight_per_day)
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

    def _build_feeder_attribute(self, attribute_id, value, length):
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
        val += bytes(reversed(types.int32s(attribute_id).serialize()))
        val += bytes(reversed(types.uint8_t(length).serialize()))

        if length == 1:
            val += types.uint8_t(value).serialize()
        elif length == 2:
            val += bytes(reversed(types.uint16_t(value).serialize()))
        elif length == 4:
            val += bytes(reversed(types.uint32_t(value).serialize()))
        else:
            val += value
        LOGGER.debug(
            "OppleCluster.build_feeder_attribute: id: %s, cooked value: %s length: %s",
            attribute_id,
            val,
            length,
        )
        return "feeder_attr", val

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
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
        return await super().write_attributes(attrs, manufacturer)


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
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
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
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }
