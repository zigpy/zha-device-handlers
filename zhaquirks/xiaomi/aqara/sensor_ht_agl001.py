"""Quirk for the Aqara Climate Sensor W100 (lumi.sensor_ht.agl001).

Exposes the three buttons (plus/center/minus = endpoints 1/2/3) as zha_event and
device-automation triggers via the shared Aqara ``MultistateInputCluster``, and battery
from the 0xFCC0 heartbeat struct. The W100 reports battery percent only in heartbeat
tag 102 — there is no tag-1 voltage, and the standard PowerConfiguration attribute
always reports 0 — so ``XiaomiCluster._parse_aqara_attributes`` maps tag 102 for this
model (matching zigbee2mqtt's TH-S04D converter,
https://github.com/Koenkk/zigbee-herdsman-converters/pull/10787).

The W100 can also show a temperature and humidity sent by the coordinator in place of
its own. ``W100AqaraCluster`` exposes this as a display sensor select plus external
temperature/humidity numbers, which it translates into framed writes to attribute
0xFFF2, as zigbee2mqtt's ``lumiExternalSensor`` does. The device keeps reporting its
own measurements.
"""

import struct
import time
from typing import Any, Final

from zigpy import types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    PERCENTAGE,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
)
from zhaquirks.const import COMMAND, DOUBLE_PRESS, LONG_PRESS, LONG_RELEASE, SHORT_PRESS
from zhaquirks.xiaomi import (
    AQARA,
    RelativeHumidityCluster,
    TemperatureMeasurementCluster,
    XiaomiAqaraE1Cluster,
    XiaomiPowerConfiguration,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    COMMAND_3_DOUBLE,
    COMMAND_3_HOLD,
    COMMAND_3_RELEASE,
    COMMAND_3_SINGLE,
    MultistateInputCluster,
)

PLUS_BUTTON = "plus"
CENTER_BUTTON = "center"
MINUS_BUTTON = "minus"

# Placeholder IEEE of the "external sensor" the W100 is linked to.
EXTERNAL_SENSOR_IEEE = bytes.fromhex("00158d00019d1b98")
TEMPERATURE_CHANNEL = 0x01
HUMIDITY_CHANNEL = 0x02

FRAME_ACTION_LINK = 0x02
FRAME_ACTION_UNLINK = 0x04
FRAME_ACTION_VALUE = 0x05
FRAME_COUNTER_HUMIDITY = 0x12
FRAME_COUNTER_TEMPERATURE = 0x13
LINK_PREFIX_HUMIDITY = 0x15
LINK_PREFIX_TEMPERATURE = 0x14

# Fixed tails of the link frames. The six bytes after 0x06 are UTF-8 labels:
# "湿度" (humidity) and "温度" (temperature).
LINK_TAIL_HUMIDITY = (
    bytes(
        [0x00, HUMIDITY_CHANNEL, 0x00, 0x55, 0x15, 0x0A, 0x01, 0x00, 0x00, 0x01, 0x06]
    )
    + "湿度".encode()
    + bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x08, 0x65])
)
LINK_TAIL_TEMPERATURE = (
    bytes(
        [
            0x00,
            TEMPERATURE_CHANNEL,
            0x00,
            0x55,
            0x15,
            0x0A,
            0x01,
            0x00,
            0x00,
            0x01,
            0x06,
        ]
    )
    + "温度".encode()
    + bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x07, 0x63])
)
UNLINK_TAIL = bytes(12)


class DisplaySensor(t.enum8):
    """Readings shown on the W100's screen."""

    Internal = 0x00
    External = 0x01


def build_frame(counter: int, action: int, params: bytes) -> bytes:
    """Wrap params in the Aqara 0xFFF2 frame header."""
    header = bytes([0xAA, 0x71, len(params) + 3, 0x44, counter])
    checksum = (512 - sum(header)) & 0xFF
    return header + bytes([checksum, action, 0x41, len(params)]) + params


class W100AqaraCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster with the W100's external display controls.

    ``display_sensor``, ``external_temperature`` and ``external_humidity`` are local
    attributes: writes to them are translated into ``sensor_link`` frames, and reads
    are answered from the cache (``display_sensor`` is refreshed from ``sensor_mode``).
    """

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        sensor_mode: Final = ZCLAttributeDef(
            id=0x0172, type=t.uint8_t, access="r", manufacturer_code=0x115F
        )
        sensor_link: Final = ZCLAttributeDef(
            id=0xFFF2, type=t.LVBytes, access="w", manufacturer_code=0x115F
        )
        display_sensor: Final = ZCLAttributeDef(
            id=0xFFE0, type=DisplaySensor, access="rw"
        )
        # 0.1 °C
        external_temperature: Final = ZCLAttributeDef(
            id=0xFFE1, type=t.int16s, access="rw"
        )
        # 1 %
        external_humidity: Final = ZCLAttributeDef(
            id=0xFFE2, type=t.uint8_t, access="rw"
        )

    LOCAL_ATTRIBUTES = (
        AttributeDefs.display_sensor.id,
        AttributeDefs.external_temperature.id,
        AttributeDefs.external_humidity.id,
    )
    # external value attribute -> (frame channel, factor to hundredths of a unit)
    EXTERNAL_VALUES = {
        AttributeDefs.external_temperature.id: (TEMPERATURE_CHANNEL, 10),
        AttributeDefs.external_humidity.id: (HUMIDITY_CHANNEL, 100),
    }
    # sensor_mode values: 0/1 internal, 2/3 external
    SENSOR_MODE_EXTERNAL = (2, 3)

    def _update_attribute(self, attrid: int, value: Any) -> None:
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.sensor_mode.id:
            super()._update_attribute(
                self.AttributeDefs.display_sensor.id,
                DisplaySensor.External
                if value in self.SENSOR_MODE_EXTERNAL
                else DisplaySensor.Internal,
            )

    async def _send_frame(
        self, counter: int, action: int, params: bytes, **kwargs
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        return await super().write_attributes(
            {self.AttributeDefs.sensor_link.id: build_frame(counter, action, params)},
            **kwargs,
        )

    async def _set_display_sensor(self, value: DisplaySensor, **kwargs) -> None:
        timestamp = t.uint32_t_be(int(time.time())).serialize()
        ieee = self.endpoint.device.ieee.serialize()[::-1]  # big-endian
        if value == DisplaySensor.External:
            action = FRAME_ACTION_LINK
            humidity = EXTERNAL_SENSOR_IEEE + LINK_TAIL_HUMIDITY
            temperature = EXTERNAL_SENSOR_IEEE + LINK_TAIL_TEMPERATURE
        else:
            action = FRAME_ACTION_UNLINK
            humidity = temperature = UNLINK_TAIL

        prefix = bytes([LINK_PREFIX_HUMIDITY])
        await self._send_frame(
            FRAME_COUNTER_HUMIDITY,
            action,
            timestamp + prefix + ieee + humidity,
            **kwargs,
        )
        prefix = bytes([LINK_PREFIX_TEMPERATURE])
        await self._send_frame(
            FRAME_COUNTER_TEMPERATURE,
            action,
            timestamp + prefix + ieee + temperature,
            **kwargs,
        )
        super()._update_attribute(self.AttributeDefs.display_sensor.id, value)

        if value == DisplaySensor.External:
            for attrid in self.EXTERNAL_VALUES:
                if (cached := self.get(attrid)) is not None:
                    await self._send_value(attrid, cached, **kwargs)

    async def _send_value(self, attrid: int, value: int, **kwargs) -> None:
        channel, factor = self.EXTERNAL_VALUES[attrid]
        params = EXTERNAL_SENSOR_IEEE + bytes([0x00, channel, 0x00, 0x55])
        params += struct.pack(">f", value * factor)
        await self._send_frame(
            FRAME_COUNTER_HUMIDITY, FRAME_ACTION_VALUE, params, **kwargs
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate the local display attributes into sensor_link frames."""
        remaining = {}
        for attr, value in attributes.items():
            attr_def = self.find_attribute(attr)
            if attr_def == self.AttributeDefs.display_sensor:
                await self._set_display_sensor(DisplaySensor(value), **kwargs)
            elif attr_def.id in self.EXTERNAL_VALUES:
                value = attr_def.type(value)
                self._update_attribute(attr_def.id, value)
                if self.get(self.AttributeDefs.display_sensor.id) == (
                    DisplaySensor.External
                ):
                    await self._send_value(attr_def.id, value, **kwargs)
            else:
                remaining[attr] = value

        if remaining:
            return await super().write_attributes(remaining, **kwargs)
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def read_attributes(
        self,
        attributes: list[int | str | foundation.ZCLAttributeDef],
        allow_cache: bool = False,
        only_cache: bool = False,
        **kwargs,
    ) -> Any:
        """Answer local attributes from the cache; refresh display_sensor first."""
        attr_defs = [self.find_attribute(attr) for attr in attributes]
        if self.AttributeDefs.display_sensor in attr_defs and not only_cache:
            await super().read_attributes([self.AttributeDefs.sensor_mode.id], **kwargs)

        success, failure = {}, {}
        remaining = []
        for attr, attr_def in zip(attributes, attr_defs):
            if attr_def.id not in self.LOCAL_ATTRIBUTES:
                remaining.append(attr)
            elif (value := self.get(attr_def.id)) is not None:
                success[attr] = value
            else:
                failure[attr] = foundation.Status.UNSUPPORTED_ATTRIBUTE

        if remaining:
            remote_success, remote_failure = await super().read_attributes(
                remaining, allow_cache, only_cache, **kwargs
            )
            success.update(remote_success)
            failure.update(remote_failure)
        return success, failure


class W100PowerConfiguration(XiaomiPowerConfiguration):
    """PowerConfiguration that drops the device's own ZCL battery reports.

    The W100's battery_percentage_remaining attribute always reports 0, and a
    reporting config from a pre-quirk join persists in the device — a 0 every
    max-interval that overwrites the heartbeat-derived value. Battery comes solely
    from the 0xFCC0 heartbeat via ``battery_percent_reported``.
    """

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Drop attribute reports; pass everything else through."""
        if hdr.command_id == foundation.GeneralCommand.Report_Attributes:
            return
        super().handle_cluster_general_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder(AQARA, "lumi.sensor_ht.agl001")
    .friendly_name(manufacturer="Aqara", model="Climate Sensor W100")
    .replaces(TemperatureMeasurementCluster)
    .replaces(RelativeHumidityCluster)
    .replaces(W100PowerConfiguration)
    .replaces(W100AqaraCluster)
    .replaces(MultistateInputCluster)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=3)
    .enum(
        attribute_name=W100AqaraCluster.AttributeDefs.display_sensor.name,
        enum_class=DisplaySensor,
        cluster_id=W100AqaraCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="display_sensor",
        fallback_name="Display sensor",
    )
    .number(
        attribute_name=W100AqaraCluster.AttributeDefs.external_temperature.name,
        cluster_id=W100AqaraCluster.cluster_id,
        min_value=-20,
        max_value=60,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        mode="box",
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="external_temperature",
        fallback_name="External temperature",
    )
    .number(
        attribute_name=W100AqaraCluster.AttributeDefs.external_humidity.name,
        cluster_id=W100AqaraCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        mode="box",
        device_class=NumberDeviceClass.HUMIDITY,
        translation_key="external_humidity",
        fallback_name="External humidity",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, PLUS_BUTTON): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, PLUS_BUTTON): {COMMAND: COMMAND_1_RELEASE},
            (SHORT_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_DOUBLE},
            (LONG_PRESS, CENTER_BUTTON): {COMMAND: COMMAND_2_HOLD},
            (LONG_RELEASE, CENTER_BUTTON): {COMMAND: COMMAND_2_RELEASE},
            (SHORT_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_SINGLE},
            (DOUBLE_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_DOUBLE},
            (LONG_PRESS, MINUS_BUTTON): {COMMAND: COMMAND_3_HOLD},
            (LONG_RELEASE, MINUS_BUTTON): {COMMAND: COMMAND_3_RELEASE},
        }
    )
    .add_to_registry()
)
