"""Quirk for Aqara aqara.feeder.acn001."""

from __future__ import annotations

import logging
from typing import Any

from zigpy import types
from zigpy.profiles import zgp, zha
from zigpy.zcl import foundation
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
ZCL_SCHEDULING_STRING = 0x1393

AQARA_TO_ZCL: dict[int, int] = {
    FEEDING: ZCL_FEEDING,
    ERROR_DETECTED: ZCL_ERROR_DETECTED,
    DISABLE_LED_INDICATOR: ZCL_DISABLE_LED_INDICATOR,
    CHILD_LOCK: ZCL_CHILD_LOCK,
    FEEDING_MODE: ZCL_FEEDING_MODE,
    SERVING_SIZE: ZCL_SERVING_SIZE,
    PORTION_WEIGHT: ZCL_PORTION_WEIGHT,
    SCHEDULING_STRING: ZCL_SCHEDULING_STRING,
}

ZCL_TO_AQARA: dict[int, int] = {
    ZCL_FEEDING: FEEDING,
    ZCL_DISABLE_LED_INDICATOR: DISABLE_LED_INDICATOR,
    ZCL_CHILD_LOCK: CHILD_LOCK,
    ZCL_FEEDING_MODE: FEEDING_MODE,
    ZCL_SERVING_SIZE: SERVING_SIZE,
    ZCL_PORTION_WEIGHT: PORTION_WEIGHT,
    ZCL_ERROR_DETECTED: ERROR_DETECTED,
    ZCL_SCHEDULING_STRING: SCHEDULING_STRING,
}

LOGGER = logging.getLogger(__name__)

DAY_CODES = {
    77: 127,  # everyday
    55: 31,  # workdays
    22: 96,  # weekend
    11: 1,  # mon
    12: 2,  # tue
    13: 4,  # wed
    14: 8,  # thu
    15: 16,  # fri
    16: 32,  # sat
    17: 64,  # sun
    44: 85,  # mon-wed-fri-sun
    33: 42,  # tue-thu-sat
}

class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class FeedingSource(types.enum8):
        """Feeding source."""

        Schedule = 0x00
        Feeder = 0x01
        Remote = 0x02

    class FeedingMode(types.enum8):
        """Feeding mode."""

        Manual = 0x00
        Schedule = 0x01

    attributes = {
        ZCL_FEEDING: ("feeding", types.Bool, True),
        ZCL_LAST_FEEDING_SOURCE: ("last_feeding_source", FeedingSource, True),
        ZCL_LAST_FEEDING_SIZE: ("last_feeding_size", types.uint8_t, True),
        ZCL_PORTIONS_DISPENSED: ("portions_dispensed", types.uint16_t, True),
        ZCL_WEIGHT_DISPENSED: ("weight_dispensed", types.uint32_t, True),
        ZCL_ERROR_DETECTED: ("error_detected", types.Bool, True),
        ZCL_DISABLE_LED_INDICATOR: ("disable_led_indicator", types.Bool, True),
        ZCL_CHILD_LOCK: ("child_lock", types.Bool, True),
        ZCL_FEEDING_MODE: ("feeding_mode", FeedingMode, True),
        ZCL_SERVING_SIZE: ("serving_size", types.uint8_t, True),
        ZCL_PORTION_WEIGHT: ("portion_weight", types.uint8_t, True),
        ZCL_SCHEDULING_STRING: ("scheduling_string", types.CharacterString, True),
        FEEDER_ATTR: (FEEDER_ATTR_NAME, types.LVBytes, True),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._send_sequence: int = None
        self._attr_cache: dict[int, Any] = {
            ZCL_DISABLE_LED_INDICATOR: False,
            ZCL_CHILD_LOCK: False,
            ZCL_FEEDING_MODE: self.FeedingMode.Manual,
            ZCL_SERVING_SIZE: 1,
            ZCL_PORTION_WEIGHT: 8,
            ZCL_ERROR_DETECTED: False,
            ZCL_PORTIONS_DISPENSED: 0,
            ZCL_WEIGHT_DISPENSED: 0,
            ZCL_SCHEDULING_STRING: "",
        }

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
        """Update feeder attribute with validation."""
        zcl_attr_def = self.attributes.get(AQARA_TO_ZCL[attrid])
        self._update_attribute(zcl_attr_def.id, zcl_attr_def.type.deserialize(value)[0])

    def _parse_feeder_attribute(self, value: Any) -> None:
        """Parse the feeder attribute."""
        try:
            if isinstance(value, str) and value.startswith("b'"):
                value = eval(value)
            
            if not isinstance(value, bytes):
                LOGGER.error("Invalid value type: %s", type(value))
                return
                
            if len(value) < 8:
                LOGGER.debug("Attribute too short: %s bytes", len(value))
                return

            attribute, _ = types.int32s_be.deserialize(value[3:7])
            length, _ = types.uint8_t.deserialize(value[7:8])
            
            if len(value) < length + 8:
                LOGGER.debug("Incomplete attribute %s: %s < %s", 
                           attribute, len(value), length + 8)
                return
                
            attribute_value = value[8 : (length + 8)]
            LOGGER.debug("Processing attr %s: %s (%s bytes)", 
                        attribute, attribute_value.hex(), len(attribute_value))

            if attribute in AQARA_TO_ZCL:
                self._update_feeder_attribute(attribute, attribute_value)
            elif attribute == FEEDING_REPORT:
                try:
                    attr_str = attribute_value.decode("utf-8")
                    LOGGER.debug("Raw feeding report: %r", attr_str)
                    
                    raw_source = attr_str[0:2]
                    feeding_source = int(raw_source, 16)
                    LOGGER.debug("Parsed source value: %r", feeding_source)
                    
                    enum_value = self.FeedingSource(feeding_source)
                    LOGGER.debug("Created enum: %r (%s)", enum_value, str(enum_value))
                    
                    self._update_attribute(ZCL_LAST_FEEDING_SOURCE, enum_value)
                    feeding_size = attr_str[3:4]
                    self._update_attribute(ZCL_LAST_FEEDING_SIZE, int(feeding_size, base=16))
                except Exception as e:
                    LOGGER.debug("Failed to parse feeding report: %s", e)
            elif attribute == PORTIONS_DISPENSED:
                try:
                    portions_per_day, _ = types.uint16_t_be.deserialize(attribute_value)
                    self._update_attribute(ZCL_PORTIONS_DISPENSED, portions_per_day)
                except ValueError as e:
                    LOGGER.debug("Failed to parse portions: %s", e)
            elif attribute == WEIGHT_DISPENSED:
                try:
                    weight_per_day, _ = types.uint32_t_be.deserialize(attribute_value)
                    self._update_attribute(ZCL_WEIGHT_DISPENSED, weight_per_day)
                except ValueError as e:
                    LOGGER.debug("Failed to parse weight: %s", e)
            elif attribute == SCHEDULING_STRING:
                try:
                    schedule_value = attribute_value.decode("utf-8")
                    self._update_attribute(ZCL_SCHEDULING_STRING, schedule_value)
                except ValueError as e:
                    LOGGER.debug("Failed to parse scheduling string: %s", e)
            else:
                LOGGER.debug("Unhandled attribute: %s = %s", attribute, attribute_value)

        except Exception as e:
            LOGGER.debug("Error parsing attribute: %s", e)

    def _build_feeder_attribute(
        self, attribute_id: int, value: Any = None, length: int | None = None
    ):
        """Build the Xiaomi feeder attribute."""
        self._send_sequence = ((self._send_sequence or 0) + 1) % 256
        val = bytes([0x00, 0x02, self._send_sequence])
        self._send_sequence += 1
        val += types.int32s_be(attribute_id).serialize()
        if length is not None and value is not None:
            val += types.uint8_t(length).serialize()
            if length == 1:
                val += types.uint8_t(value).serialize()
            elif length == 2:
                val += types.uint16_t_be(value).serialize()
            elif length == 4:
                val += types.uint32_t_be(value).serialize()
            else:
                val += value
        return FEEDER_ATTR_NAME, val

    def _build_xiaomi_attribute(self, attr_id: int, value: bytes, length: int) -> bytes:
        """Build Xiaomi attribute data format."""
        self._send_sequence = ((self._send_sequence or 0) + 1) % 256
        header = bytearray([0x00, 0x02, self._send_sequence])
        header.extend(attr_id.to_bytes(4, "big"))
        header.append(length)
        header.extend(value)
        return bytes(header)

    def _build_schedule_bytes(self, value: Any) -> None:
        """Log schedule integer segments."""
        try:
            schedule_str = str(value)
            schedules = [schedule_str[i:i + 8] for i in range(0, len(schedule_str), 8)]

            for schedule in schedules:
                day = int(schedule[0:2])
                hour = int(schedule[2:4])
                minute = int(schedule[4:6])
                portions = int(schedule[6:8])

                LOGGER.info(
                    "Schedule: Day=%02d (%s), Time=%02d:%02d, Portions=%d [Raw=%s]",
                    day,
                    DAY_CODES.get(day, "unknown"),
                    hour,
                    minute,
                    portions,
                    schedule,
                )

        except Exception as e:
            LOGGER.error("Schedule parse error: %s", e)

    def _encode_schedule(self, value: Any) -> bytes:
        """Build schedule packet for up to 5 schedules."""
        try:
            # Timezone is UTC
            # Schedule string in DDHHMMPP format - day, 24hour, minute, portions
            schedule_str = str(value).strip()
            if not schedule_str.isdigit():
                LOGGER.error("Schedule must be digits only: %r", schedule_str)
                return None
            # multiple schedules combined like DDHHMMPPDDHHMMPP up to 5 schedules
            if len(schedule_str) % 8 != 0:
                LOGGER.error("Schedule length must be multiple of 8: %d", len(schedule_str))
                return None

            schedules = [schedule_str[i:i + 8] for i in range(0, len(schedule_str), 8)]
            if len(schedules) > 5:
                LOGGER.error("Max 5 schedules allowed, got: %d", len(schedules))
                return None

            schedule_parts = []
            for i, schedule in enumerate(schedules, 1):
                day = int(schedule[0:2])
                hour = int(schedule[2:4])
                minute = int(schedule[4:6])
                portions = int(schedule[6:8])

                if hour > 23 or minute > 59 or portions == 0:
                    LOGGER.error(
                        "Invalid schedule %d: time=%02d:%02d, portions=%d",
                        i,
                        hour,
                        minute,
                        portions,
                    )
                    return None

                day_code = DAY_CODES.get(day, day)
                schedule_hex = (
                    f"{day_code:02X}"
                    f"{hour:02X}"
                    f"{minute:02X}"
                    f"{portions:02X}"
                    "00"
                )
                schedule_parts.append(schedule_hex)
                LOGGER.debug(
                    "Added schedule %d: %s (day=%d->%d)", 
                    i,
                    schedule_hex,
                    day,
                    day_code,
                )

            header = bytes([0x05, 0x15, 0x08, 0x00, 0x08, 0xc8])
            packet = header + b" " + ",".join(schedule_parts).encode()
            LOGGER.debug("Schedule packet: %s", packet.hex())
            return packet

        except Exception as e:
            LOGGER.error("Schedule encode error: %s", e)
            return None

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device with internal 'attributes' validation."""
        attrs = {}
        for attr, value in attributes.items():
            # Special handling for schedule string
            if attr == ZCL_SCHEDULING_STRING or (
                isinstance(attr, str) and attr == "scheduling_string"
            ):
                try:
                    schedule_val = str(getattr(value, "value", value))
                    if schedule_val.strip().isdigit():
                        packet = self._encode_schedule(schedule_val)
                        if packet:
                            tv = foundation.TypeValue()
                            tv.type = 0x41
                            tv.value = types.LongOctetString(packet)
                            return await self._write_attributes(
                                [foundation.Attribute(FEEDER_ATTR, tv)],
                                manufacturer=0x115F
                            )
                except Exception as e:
                    LOGGER.error("Schedule processing error: %s", e)
                continue

            attr_def = self.find_attribute(attr)
            if not attr_def:
                continue
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

        return await super().write_attributes(attrs, manufacturer=0x115F)

    async def write_attributes_raw(
        self, attrs: list[foundation.Attribute], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device without internal 'attributes' validation."""
        # intentionally skip attr cache because of the encoding from Xiaomi and
        # the attributes are reported back by the device
        return await self._write_attributes(attrs, manufacturer=manufacturer)

    async def write_attributes_safe(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Use same attribute handling as write_attributes."""
        return await self.write_attributes(attributes, manufacturer)

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
