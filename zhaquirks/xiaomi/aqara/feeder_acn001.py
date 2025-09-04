"""Quirk for Aqara aqara.feeder.acn001."""

from __future__ import annotations

import ast
import json
import logging
import time
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

from zhaquirks import EventableCluster
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
SCHEDULING = 0x080008C8
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
ZCL_SCHEDULE = 0x1393

AQARA_TO_ZCL: dict[int, int] = {
    FEEDING: ZCL_FEEDING,
    ERROR_DETECTED: ZCL_ERROR_DETECTED,
    DISABLE_LED_INDICATOR: ZCL_DISABLE_LED_INDICATOR,
    CHILD_LOCK: ZCL_CHILD_LOCK,
    FEEDING_MODE: ZCL_FEEDING_MODE,
    SERVING_SIZE: ZCL_SERVING_SIZE,
    PORTION_WEIGHT: ZCL_PORTION_WEIGHT,
    SCHEDULING: ZCL_SCHEDULE,
}

ZCL_TO_AQARA: dict[int, int] = {
    ZCL_FEEDING: FEEDING,
    ZCL_DISABLE_LED_INDICATOR: DISABLE_LED_INDICATOR,
    ZCL_CHILD_LOCK: CHILD_LOCK,
    ZCL_FEEDING_MODE: FEEDING_MODE,
    ZCL_SERVING_SIZE: SERVING_SIZE,
    ZCL_PORTION_WEIGHT: PORTION_WEIGHT,
    ZCL_ERROR_DETECTED: ERROR_DETECTED,
    ZCL_SCHEDULE: SCHEDULING,
}

LOGGER = logging.getLogger(__name__)

# Day mapping
DAYS_MAP = {
    'everyday': 0x7F,
    'workdays': 0x1F,
    'weekend': 0x60,
    'mon': 0x01,
    'tue': 0x02,
    'wed': 0x04,
    'thu': 0x08,
    'fri': 0x10,
    'sat': 0x20,
    'sun': 0x40,
}

# Reverse lookup for efficiency
DAYS_REVERSE_MAP = {v: k for k, v in DAYS_MAP.items()}

ATTR_NAMES = {
    FEEDING: "feeding",
    ERROR_DETECTED: "error_detected",
    DISABLE_LED_INDICATOR: "disable_led_indicator", 
    CHILD_LOCK: "child_lock",
    FEEDING_MODE: "feeding_mode",
    SERVING_SIZE: "serving_size",
    PORTION_WEIGHT: "portion_weight",
    SCHEDULING: "scheduling",
    FEEDING_REPORT: "feeding_report",
    PORTIONS_DISPENSED: "portions_dispensed",
    WEIGHT_DISPENSED: "weight_dispensed"
}

IMPORTANT_ATTRS = {
    ZCL_SCHEDULE: "schedule_updated",
    ZCL_FEEDING_MODE: "feeding_mode_changed", 
    ZCL_CHILD_LOCK: "child_lock_changed",
    ZCL_DISABLE_LED_INDICATOR: "led_indicator_changed",
    ZCL_SERVING_SIZE: "serving_size_changed",
    ZCL_PORTION_WEIGHT: "portion_weight_changed",
    ZCL_LAST_FEEDING_SOURCE: "feeding_occurred",
    ZCL_ERROR_DETECTED: "error_detected"
}


class OppleCluster(XiaomiAqaraE1Cluster, EventableCluster):
    """Opple cluster with event support."""

    class FeedingSource(types.enum8):
        """Feeding source."""

        Schedule = 0x00
        Manual = 0x01
        Remote = 0x02

    class FeedingMode(types.enum8):
        """Feeding mode."""

        Manual = 0x00
        Schedule = 0x01

    # Mark all custom attributes as reportable to ensure entities are created
    attributes = {
        ZCL_FEEDING: foundation.ZCLAttributeDef(
            id=ZCL_FEEDING, name="feeding", type=types.Bool, access="rps"
        ),
        ZCL_LAST_FEEDING_SOURCE: foundation.ZCLAttributeDef(
            id=ZCL_LAST_FEEDING_SOURCE, name="last_feeding_source", type=FeedingSource, access="rps"
        ),
        ZCL_LAST_FEEDING_SIZE: foundation.ZCLAttributeDef(
            id=ZCL_LAST_FEEDING_SIZE, name="last_feeding_size", type=types.uint8_t, access="rps"
        ),
        ZCL_PORTIONS_DISPENSED: foundation.ZCLAttributeDef(
            id=ZCL_PORTIONS_DISPENSED, name="portions_dispensed", type=types.uint16_t, access="rps"
        ),
        ZCL_WEIGHT_DISPENSED: foundation.ZCLAttributeDef(
            id=ZCL_WEIGHT_DISPENSED, name="weight_dispensed", type=types.uint32_t, access="rps"
        ),
        ZCL_ERROR_DETECTED: foundation.ZCLAttributeDef(
            id=ZCL_ERROR_DETECTED, name="error_detected", type=types.Bool, access="rps"
        ),
        ZCL_DISABLE_LED_INDICATOR: foundation.ZCLAttributeDef(
            id=ZCL_DISABLE_LED_INDICATOR, name="disable_led_indicator", type=types.Bool, access="rps"
        ),
        ZCL_CHILD_LOCK: foundation.ZCLAttributeDef(
            id=ZCL_CHILD_LOCK, name="child_lock", type=types.Bool, access="rps"
        ),
        ZCL_FEEDING_MODE: foundation.ZCLAttributeDef(
            id=ZCL_FEEDING_MODE, name="feeding_mode", type=FeedingMode, access="rps"
        ),
        ZCL_SERVING_SIZE: foundation.ZCLAttributeDef(
            id=ZCL_SERVING_SIZE, name="serving_size", type=types.uint8_t, access="rps"
        ),
        ZCL_PORTION_WEIGHT: foundation.ZCLAttributeDef(
            id=ZCL_PORTION_WEIGHT, name="portion_weight", type=types.uint8_t, access="rps"
        ),
        ZCL_SCHEDULE: foundation.ZCLAttributeDef(
            id=ZCL_SCHEDULE, name="schedule", type=types.CharacterString, access="rps"
        ),
        FEEDER_ATTR: foundation.ZCLAttributeDef(
            id=FEEDER_ATTR, name=FEEDER_ATTR_NAME, type=types.LVBytes, access="rps"
        ),
        # Add the unknown attribute to prevent crashes
        0x00F7: foundation.ZCLAttributeDef(
            id=0x00F7, name="status_report", type=types.LVBytes, access="rps"
        ),
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._send_sequence: int = 0
        self._recently_written: dict[int, Any] = {}
        self._write_timestamps: dict[int, float] = {}
        self._attributes_initialized = False
        
        self._cached_nwk: int | None = None
        
        self._attr_cache: dict[int, Any] = {
            ZCL_FEEDING: False,
            ZCL_LAST_FEEDING_SOURCE: self.FeedingSource.Manual,
            ZCL_LAST_FEEDING_SIZE: 0,
            ZCL_PORTIONS_DISPENSED: 0,
            ZCL_WEIGHT_DISPENSED: 0,
            ZCL_ERROR_DETECTED: False,
            ZCL_DISABLE_LED_INDICATOR: False,
            ZCL_CHILD_LOCK: False,
            ZCL_FEEDING_MODE: self.FeedingMode.Manual,
            ZCL_SERVING_SIZE: 1,
            ZCL_PORTION_WEIGHT: 8,
            ZCL_SCHEDULE: "[]",
        }

    def _initialize_attributes(self):
        """Initialize all custom attributes with default values."""
        if self._attributes_initialized:
            return
        
        for attr_id, default_value in self._attr_cache.items():
            try:
                super()._update_attribute(attr_id, default_value)
            except Exception:
                pass
        
        self._attributes_initialized = True

    def _get_device_nwk(self) -> int:
        """Get device network address with caching."""
        if self._cached_nwk is None:
            try:
                self._cached_nwk = self._endpoint.device.nwk
            except Exception:
                self._cached_nwk = 0
        return self._cached_nwk

    def _is_recently_written(self, attr_id: int) -> bool:
        """Check if attribute was recently written (within 10 seconds)."""
        timestamp = self._write_timestamps.get(attr_id)
        if timestamp is None:
            return False
        return (time.time() - timestamp) < 10.0

    def _mark_as_written(self, attr_id: int, value: Any) -> None:
        """Mark attribute as recently written."""
        self._recently_written[attr_id] = value
        self._write_timestamps[attr_id] = time.time()

    def _get_attribute_name(self, attrid: int) -> str:
        """Get attribute name efficiently."""
        attr_def = self.attributes.get(attrid)
        if attr_def is None:
            return f"attr_{attrid:04X}"
        
        if hasattr(attr_def, 'name'):
            return attr_def.name
        
        if isinstance(attr_def, tuple) and len(attr_def) >= 1:
            return attr_def[0]
        
        return f"attr_{attrid:04X}"

    @staticmethod
    def _make_json_safe(value) -> str:
        """Convert value to JSON-safe format efficiently."""
        if hasattr(value, 'name'):
            return value.name
        elif isinstance(value, bytes):
            return value.hex()
        elif hasattr(value, '__bytes__'):
            return bytes(value).hex()
        else:
            return str(value)

    def _fire_attribute_event(self, attrid: int, attr_name: str, old_value: Any, new_value: Any) -> None:
        """Fire ZHA event for attribute changes using EventableCluster."""
        if old_value == new_value:
            return
        
        try:
            if attrid == FEEDER_ATTR:
                old_hex = self._make_json_safe(old_value) if old_value else ""
                new_hex = self._make_json_safe(new_value)
                
                confirmation_args = {
                    "attribute_id": attrid,
                    "attribute_name": attr_name,
                    "old_value": old_hex,
                    "new_value": new_hex,
                    "response_length": len(new_value) if isinstance(new_value, (bytes, types.LVBytes)) else 0,
                }
                
                if isinstance(new_value, (bytes, types.LVBytes)) and len(new_value) >= 8:
                    try:
                        response_attr_id, _ = types.int32s_be.deserialize(bytes(new_value)[3:7])
                        confirmation_args["response_attribute_id"] = f"0x{response_attr_id:08X}"
                        confirmation_args["response_attribute_name"] = ATTR_NAMES.get(response_attr_id, "unknown")
                    except Exception:
                        pass
                
                self.listener_event("zha_event", "device_response_received", confirmation_args)
                return

            event_type = IMPORTANT_ATTRS.get(attrid)
            if event_type is None:
                return

            event_args = {
                "attribute_id": attrid,
                "attribute_name": attr_name,
                "old_value": self._make_json_safe(old_value),
                "new_value": self._make_json_safe(new_value),
                "is_confirmation": self._is_recently_written(attrid),
            }
            
            if event_args["is_confirmation"]:
                event_args["write_timestamp"] = self._write_timestamps.get(attrid, 0)

            if attrid == ZCL_SCHEDULE and isinstance(new_value, str):
                try:
                    schedule_data = json.loads(new_value) if new_value.strip() else []
                    event_args["schedule_entries"] = len(schedule_data)
                    event_args["schedule_data"] = schedule_data
                except json.JSONDecodeError:
                    pass

            self.listener_event("zha_event", event_type, event_args)
                
        except Exception as e:
            LOGGER.error("[0x%04X] Error in _fire_attribute_event: %s", self._get_device_nwk(), e)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        """Update attribute with proper listener notification."""
        if attrid == 0x00F7 and isinstance(value, (bytes, types.LVBytes)):
            raw_value = bytes(value)
            self._attr_cache[attrid] = raw_value
            if hasattr(self, '_attributes'):
                self._attributes[attrid] = raw_value.hex()
            return
        
        if attrid == FEEDER_ATTR and isinstance(value, (bytes, types.LVBytes)):
            raw_value = bytes(value)
            old_value = self._attr_cache.get(attrid)
            self._attr_cache[attrid] = raw_value
            
            self._parse_feeder_attribute(raw_value)
            
            super()._update_attribute(attrid, raw_value.hex())
            
            attr_name = self._get_attribute_name(attrid)
            self._fire_attribute_event(attrid, attr_name, old_value, raw_value)
            return
        
        old_value = self._attr_cache.get(attrid)
        self._attr_cache[attrid] = value
        
        super()._update_attribute(attrid, value)
        
        if old_value != value:
            attr_name = self._get_attribute_name(attrid)
            self._fire_attribute_event(attrid, attr_name, old_value, value)

    def _update_feeder_attribute(self, attrid: int, value: Any) -> None:
        """Update feeder attribute with validation."""
        zcl_attr_id = AQARA_TO_ZCL.get(attrid)
        if zcl_attr_id and zcl_attr_id in self.attributes:
            zcl_attr_def = self.attributes[zcl_attr_id]
            if hasattr(zcl_attr_def, 'type'):
                try:
                    parsed_value = zcl_attr_def.type.deserialize(value)[0]
                    self._update_attribute(zcl_attr_id, parsed_value)
                except Exception:
                    pass

    def _parse_feeder_attribute(self, value: Any) -> None:
        """Parse the feeder attribute efficiently."""
        try:
            if isinstance(value, str) and value.startswith("b'"):
                value = ast.literal_eval(value)
            
            if not isinstance(value, bytes) or len(value) < 8:
                return

            attribute, _ = types.int32s_be.deserialize(value[3:7])
            length = value[7]
            
            if len(value) < length + 8:
                return
                
            attribute_value = value[8:8+length]

            if attribute in AQARA_TO_ZCL:
                self._update_feeder_attribute(attribute, attribute_value)
            elif attribute == FEEDING_REPORT:
                self._parse_feeding_report(attribute_value)
            elif attribute == PORTIONS_DISPENSED:
                try:
                    portions_per_day, _ = types.uint16_t_be.deserialize(attribute_value)
                    self._update_attribute(ZCL_PORTIONS_DISPENSED, portions_per_day)
                except ValueError:
                    pass
            elif attribute == WEIGHT_DISPENSED:
                try:
                    weight_per_day, _ = types.uint32_t_be.deserialize(attribute_value)
                    self._update_attribute(ZCL_WEIGHT_DISPENSED, weight_per_day)
                except ValueError:
                    pass
            elif attribute == SCHEDULING:
                self._parse_schedule(attribute_value)

        except Exception as e:
            LOGGER.error("[0x%04X] Error parsing feeder attribute: %s", self._get_device_nwk(), e)

    def _parse_feeding_report(self, value: bytes) -> None:
        """Parse feeding report efficiently."""
        try:
            attr_str = value.decode("utf-8")
            
            if len(attr_str) >= 4:
                feeding_source = int(attr_str[0:2], 16)
                enum_value = self.FeedingSource(feeding_source)
                
                self._update_attribute(ZCL_LAST_FEEDING_SOURCE, enum_value)
                self._update_attribute(ZCL_LAST_FEEDING_SIZE, int(attr_str[3:4], 16))
                
                feeding_event_args = {
                    "feeding_source": enum_value.name,
                    "feeding_size": int(attr_str[3:4], 16),
                    "raw_data": attr_str
                }
                
                self.listener_event("zha_event", "feeding_completed", feeding_event_args)
                    
        except (ValueError, UnicodeDecodeError):
            pass

    def _parse_schedule(self, value: bytes) -> None:
        """Parse schedule from device response efficiently."""
        try:
            schedule_value = value.decode("utf-8").strip()
            
            if not schedule_value:
                self._update_attribute(ZCL_SCHEDULE, "[]")
                return
            
            schedules = []
            schedule_parts = schedule_value.split(',') if ',' in schedule_value else schedule_value.split()
            
            for part in schedule_parts:
                part = part.strip()
                if len(part) >= 8:
                    try:
                        days_mask = int(part[0:2], 16)
                        hour = int(part[2:4], 16)
                        minute = int(part[4:6], 16)
                        portions = int(part[6:8], 16)
                        
                        day_name = DAYS_REVERSE_MAP.get(days_mask)
                        
                        if day_name and hour < 24 and minute < 60 and portions > 0:
                            schedule_entry = {
                                "days": day_name,
                                "hour": hour,
                                "minute": minute,
                                "portions": portions
                            }
                            schedules.append(schedule_entry)
                    except ValueError:
                        continue
            
            schedule_json = json.dumps(schedules, separators=(',', ':'))
            self._update_attribute(ZCL_SCHEDULE, schedule_json)
            
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

    def _encode_schedule(self, schedule_input: Any) -> bytes | None:
        """Encode schedule to device format efficiently."""
        try:
            if isinstance(schedule_input, str):
                schedule_list = json.loads(schedule_input)
            elif isinstance(schedule_input, list):
                schedule_list = schedule_input
            else:
                return None

            if not isinstance(schedule_list, list) or len(schedule_list) > 5:
                return None
            
            schedule_parts = []
            for schedule in schedule_list:
                days = schedule.get('days', 'everyday')
                hour = schedule.get('hour', 0)
                minute = schedule.get('minute', 0)
                portions = schedule.get('portions', 1)
                
                if hour > 23 or minute > 59 or portions < 1:
                    return None
                
                days_mask = DAYS_MAP.get(days, 0x7F)
                schedule_hex = f"{days_mask:02X}{hour:02X}{minute:02X}{portions:02X}00"
                schedule_parts.append(schedule_hex)
            
            schedule_data = ",".join(schedule_parts)
            header = bytes([0x05, 0x15, 0x08, 0x00, 0x08, 0xc8])
            return header + b" " + schedule_data.encode()
            
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _build_feeder_attribute(
        self, attribute_id: int, value: Any = None, length: int | None = None
    ):
        """Build the Xiaomi feeder attribute efficiently."""
        self._send_sequence = (self._send_sequence + 1) % 256
        val = bytearray([0x00, 0x02, self._send_sequence])
        val.extend(types.int32s_be(attribute_id).serialize())
        
        if length is not None and value is not None:
            val.append(length)  
            if length == 1:
                val.append(value)
            elif length == 2:
                val.extend(types.uint16_t_be(value).serialize())
            elif length == 4:
                val.extend(types.uint32_t_be(value).serialize())
            else:
                val.extend(value)
        
        return FEEDER_ATTR_NAME, bytes(val)

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device with immediate UI feedback."""
        attrs = {}
        for attr, value in attributes.items():
            if attr == ZCL_SCHEDULE or (isinstance(attr, str) and attr == "schedule"):
                try:
                    schedule_val = str(getattr(value, "value", value))
                    if schedule_val.strip():
                        packet = self._encode_schedule(schedule_val)
                        if packet:
                            self._update_attribute(ZCL_SCHEDULE, schedule_val)
                            
                            tv = foundation.TypeValue()
                            tv.type = 0x41
                            tv.value = types.LongOctetString(packet)
                            result = await self._write_attributes(
                                [foundation.Attribute(FEEDER_ATTR, tv)],
                                manufacturer=0x115F
                            )
                            return result
                except Exception:
                    pass
                continue

            attr_def = self.find_attribute(attr)
            if not attr_def:
                continue
                
            attr_id = attr_def.id
            
            if attr_id in ZCL_TO_AQARA:
                self._mark_as_written(attr_id, value)
                
                self._update_attribute(attr_id, value)
                
                attr_name = getattr(attr_def, 'name', '')
                length = 4 if attr_name in {"serving_size", "portion_weight"} else 1
                
                attribute, cooked_value = self._build_feeder_attribute(
                    ZCL_TO_AQARA[attr_id],
                    value,
                    length,
                )
                attrs[attribute] = cooked_value
            else:
                attrs[attr] = value

        if attrs:
            result = await super().write_attributes(attrs, manufacturer=0x115F)
            return result
        
        return [foundation.Status.SUCCESS]

    async def write_attributes_raw(
        self, attrs: list[foundation.Attribute], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device without internal 'attributes' validation."""
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
    
    async def configure(self):
        """Configure the device."""
        try:
            await super().configure()
            
            opple_cluster = self.endpoints[1].in_clusters.get(OppleCluster.cluster_id)
            if opple_cluster:
                nwk = getattr(self, 'nwk', 0)
                
                opple_cluster._initialize_attributes()
                
                try:
                    import asyncio
                    await asyncio.sleep(1.0)
                    await opple_cluster.read_attributes([FEEDER_ATTR], allow_cache=False)
                except Exception:
                    pass
                
                LOGGER.info("[0x%04X] Feeder configuration completed", nwk)
        except Exception as e:
            nwk = getattr(self, 'nwk', 0)
            LOGGER.error("[0x%04X] Error during feeder configuration: %s", nwk, str(e))