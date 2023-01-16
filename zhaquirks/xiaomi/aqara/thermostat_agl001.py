"""Aqara E1 Radiator Thermostat Quirk."""
from __future__ import annotations

import functools
import struct
import time
from typing import Any

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, Time
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
    XiaomiPowerConfiguration,
)


class ThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster."""

    _CONSTANT_ATTRIBUTES = {0x001B: 0x02}


SYSTEM_MODE = 0x0271
PRESET = 0x0272
WINDOW_DETECTION = 0x0273
VALVE_DETECTION = 0x0274
VALVE_ALARM = 0x0275
CHILD_LOCK = 0x0277
AWAY_PRESET_TEMPERATURE = 0x0279
WINDOW_OPEN = 0x027A
CALIBRATED = 0x027B
SENSOR = 0x027E
BATTERY_PERCENTAGE = 0x040A

SENSOR_TEMP = 0x1392  # Fake address to pass external sensor temperature
SENSOR_ATTR = 0xFFF2
SENSOR_ATTR_NAME = "sensor_attr"

XIAOMI_CLUSTER_ID = 0xFCC0


class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    ep_attribute = "aqara_cluster"

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            SYSTEM_MODE: ("system_mode", t.uint8_t, True),
            PRESET: ("preset", t.uint8_t, True),
            WINDOW_DETECTION: ("window_detection", t.uint8_t, True),
            VALVE_DETECTION: ("valve_detection", t.uint8_t, True),
            VALVE_ALARM: ("valve_alarm", t.uint32_t, True),
            CHILD_LOCK: ("child_lock", t.uint8_t, True),
            AWAY_PRESET_TEMPERATURE: ("away_preset_temperature", t.uint32_t, True),
            WINDOW_OPEN: ("window_open", t.uint8_t, True),
            CALIBRATED: ("calibrated", t.uint8_t, True),
            SENSOR: ("sensor", t.uint8_t, True),
            BATTERY_PERCENTAGE: ("battery_percentage", t.uint8_t, True),
            SENSOR_TEMP: ("sensor_temp", t.uint32_t, True),
            SENSOR_ATTR: (SENSOR_ATTR_NAME, t.LVBytes, True),
        }
    )

    def _update_attribute(self, attrid, value):
        self.debug("Attribute/Value", attrid, value)
        if attrid == BATTERY_PERCENTAGE:
            self.endpoint.device.battery_bus.listener_event(
                "battery_percent_reported", value
            )
        super()._update_attribute(attrid, value)

    def aqaraHeader(self, counter: int, params: bytearray, action: int) -> bytearray:
        """Create Aqara header for setting external sensor."""
        header = bytes([0xAA, 0x71, len(params) + 3, 0x44, counter])
        integrity = 512 - functools.reduce(lambda sum, elem: sum + elem, header)

        return header + bytes([integrity, action, 0x41, len(params)])

    def _float_to_hex(self, f):
        """Convert float to hex."""
        return hex(struct.unpack("<I", struct.pack("<f", f))[0])

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Write attributes to device with internal 'attributes' validation."""
        sensor = bytearray.fromhex("00158d00019d1b98")
        attrs = {}

        for attr, value in attributes.items():
            # implemented with help from https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices/xiaomi.js

            if attr == SENSOR_TEMP:
                # set external sensor temp. this function expect value to be passed multiplied by 100
                temperatureBuf = bytearray.fromhex(
                    self._float_to_hex(round(float(value)))[2:]
                )

                params = sensor
                params += bytes([0x00, 0x01, 0x00, 0x55])
                params += temperatureBuf

                attrs = {}
                attrs[SENSOR_ATTR_NAME] = self.aqaraHeader(0x12, params, 0x05) + params

            elif attr == SENSOR:
                # set internal/external temperature sensor
                device = bytearray.fromhex(
                    ("%s" % (self.endpoint.device.ieee)).replace(":", "")
                )
                timestamp = bytes(reversed(t.uint32_t(int(time.time())).serialize()))

                if value == 0:
                    # internal sensor
                    params1 = timestamp
                    params1 += bytes([0x3D, 0x05])
                    params1 += device
                    params1 += bytes(
                        [
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                        ]
                    )

                    params2 = timestamp
                    params2 += bytes([0x3D, 0x04])
                    params2 += device
                    params2 += bytes(
                        [
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                            0x00,
                        ]
                    )

                    attrs1 = {}
                    attrs1[SENSOR_ATTR_NAME] = (
                        self.aqaraHeader(0x12, params1, 0x04) + params1
                    )
                    attrs[SENSOR_ATTR_NAME] = (
                        self.aqaraHeader(0x13, params2, 0x04) + params2
                    )

                    result = await super().write_attributes(attrs1, manufacturer)
                else:
                    # external sensor
                    params1 = timestamp
                    params1 += bytes([0x3D, 0x04])
                    params1 += device
                    params1 += sensor
                    params1 += bytes([0x00, 0x01, 0x00, 0x55])
                    params1 += bytes(
                        [
                            0x13,
                            0x0A,
                            0x02,
                            0x00,
                            0x00,
                            0x64,
                            0x04,
                            0xCE,
                            0xC2,
                            0xB6,
                            0xC8,
                        ]
                    )
                    params1 += bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x3D])
                    params1 += bytes([0x64])
                    params1 += bytes([0x65])

                    params2 = timestamp
                    params2 += bytes([0x3D, 0x05])
                    params2 += device
                    params2 += sensor
                    params2 += bytes([0x08, 0x00, 0x07, 0xFD])
                    params2 += bytes(
                        [
                            0x16,
                            0x0A,
                            0x02,
                            0x0A,
                            0xC9,
                            0xE8,
                            0xB1,
                            0xB8,
                            0xD4,
                            0xDA,
                            0xCF,
                            0xDF,
                            0xC0,
                            0xEB,
                        ]
                    )
                    params2 += bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x3D])
                    params2 += bytes([0x04])
                    params2 += bytes([0x65])

                    attrs1 = {}
                    attrs1[SENSOR_ATTR_NAME] = (
                        self.aqaraHeader(0x12, params1, 0x02) + params1
                    )
                    attrs[SENSOR_ATTR_NAME] = (
                        self.aqaraHeader(0x13, params2, 0x02) + params2
                    )

                    result = await super().write_attributes(attrs1, manufacturer)
            else:
                attrs[attr] = value

        result = await super().write_attributes(attrs, manufacturer)
        return result


class AGL001(XiaomiCustomDevice):
    """Aqara E1 Radiator Thermostat (AGL001) Device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=1
        # input_clusters=[0, 1, 3, 513, 64704]
        # output_clusters=[3, 513, 64704]>
        MODELS_INFO: [(LUMI, "lumi.airrtc.agl001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    Time.cluster_id,
                    XiaomiPowerConfiguration.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    XIAOMI_CLUSTER_ID,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ThermostatCluster,
                    Time.cluster_id,
                    XiaomiPowerConfiguration,
                    AqaraThermostatSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    ThermostatCluster,
                    AqaraThermostatSpecificCluster,
                    Ota.cluster_id,
                ],
            }
        }
    }
