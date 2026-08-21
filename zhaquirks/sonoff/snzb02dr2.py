"""Sonoff SNZB-02DR2 temperature/humidity sensor with remote sensor slots."""

import logging
import time
from typing import Any

import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import (
    PERCENTAGE,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

CONFIGURATION_TIP = "Briefly press the device button to wake it before configuring."
LOGGER = logging.getLogger(__name__)

REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA = 0x03
REMOTE_SENSOR_TYPE_TEMPERATURE = 0x00
REMOTE_SENSOR_TYPE_HUMIDITY = 0x01
REMOTE_SENSOR_STATE_ONLINE = 0x01
REMOTE_SENSOR_STATE_OFFLINE = 0x02
REMOTE_SENSOR_VALUE_LENGTH = 0x02
REMOTE_PACKET_TIMEOUT_SECONDS = 30
# The firmware maps sensor IDs 0 and 1 to the device's remote sensor slots 1 and 2.
SUPPORTED_VIRTUAL_SENSOR_IDS = frozenset({0x00, 0x01})

RemoteAttributeArrayValues = t.LVList[t.uint8_t, t.uint16_t]


def configuration_tip_converter(_value: Any) -> str:
    """Return the fixed reminder shown before configuration."""
    return CONFIGURATION_TIP


class TemperatureUnit(t.enum16):
    """Temperature unit."""

    Celsius = 0
    Fahrenheit = 1


class CustomSonoffCluster(CustomCluster):
    """Sonoff custom cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        comfort_temperature_max = ZCLAttributeDef(
            id=0x0003,
            type=t.int16s,
            manufacturer_code=None,
        )

        comfort_temperature_min = ZCLAttributeDef(
            id=0x0004,
            type=t.int16s,
            manufacturer_code=None,
        )

        comfort_humidity_min = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
            manufacturer_code=None,
        )

        comfort_humidity_max = ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
            manufacturer_code=None,
        )

        temperature_unit = ZCLAttributeDef(
            id=0x0007,
            type=TemperatureUnit,
            zcl_type=DataTypeId.uint16,
            manufacturer_code=None,
        )

        temperature_offset = ZCLAttributeDef(
            id=0x2003,
            type=t.int16s,
            manufacturer_code=None,
        )

        humidity_offset = ZCLAttributeDef(
            id=0x2004,
            type=t.int16s,
            manufacturer_code=None,
        )

        reset_max_min_record = ZCLAttributeDef(
            id=0x2013,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        temp_humi_source_status = ZCLAttributeDef(
            id=0x600E,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        remote_attributes = ZCLAttributeDef(
            id=0x601E,
            type=foundation.Array,
            zcl_type=DataTypeId.array,
            manufacturer_code=None,
        )

        configuration_tip = ZCLAttributeDef(
            id=0xFFF0,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        remote_temperature_sensor_id = ZCLAttributeDef(
            id=0xFFF1,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        remote_humidity_sensor_id = ZCLAttributeDef(
            id=0xFFF2,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        # Virtual scalar facades retain their names for stable HA entity IDs.
        remote_temperature_data = ZCLAttributeDef(
            id=0xFFF3,
            type=t.int16s,
            manufacturer_code=None,
        )

        remote_humidity_data = ZCLAttributeDef(
            id=0xFFF4,
            type=t.uint16_t,
            manufacturer_code=None,
        )

        remote_temperature_data_2 = ZCLAttributeDef(
            id=0xFFF6,
            type=t.int16s,
            manufacturer_code=None,
        )

        remote_humidity_data_2 = ZCLAttributeDef(
            id=0xFFF7,
            type=t.uint16_t,
            manufacturer_code=None,
        )

    _SENSOR_BINDING_ATTRIBUTES = {
        REMOTE_SENSOR_TYPE_TEMPERATURE: AttributeDefs.remote_temperature_sensor_id,
        REMOTE_SENSOR_TYPE_HUMIDITY: AttributeDefs.remote_humidity_sensor_id,
    }
    _SENSOR_VALUE_ATTRIBUTES = {
        REMOTE_SENSOR_TYPE_TEMPERATURE: AttributeDefs.remote_temperature_data,
        REMOTE_SENSOR_TYPE_HUMIDITY: AttributeDefs.remote_humidity_data,
    }
    _SENSOR_DISPLAY_ATTRIBUTES = {
        (REMOTE_SENSOR_TYPE_TEMPERATURE, 0x00): AttributeDefs.remote_temperature_data,
        (REMOTE_SENSOR_TYPE_HUMIDITY, 0x00): AttributeDefs.remote_humidity_data,
        (
            REMOTE_SENSOR_TYPE_TEMPERATURE,
            0x01,
        ): AttributeDefs.remote_temperature_data_2,
        (REMOTE_SENSOR_TYPE_HUMIDITY, 0x01): AttributeDefs.remote_humidity_data_2,
    }
    _ATTRIBUTE_TO_SENSOR_KEY = {
        AttributeDefs.remote_temperature_data.id: (
            REMOTE_SENSOR_TYPE_TEMPERATURE,
            0x00,
        ),
        AttributeDefs.remote_humidity_data.id: (REMOTE_SENSOR_TYPE_HUMIDITY, 0x00),
        AttributeDefs.remote_temperature_data_2.id: (
            REMOTE_SENSOR_TYPE_TEMPERATURE,
            0x01,
        ),
        AttributeDefs.remote_humidity_data_2.id: (REMOTE_SENSOR_TYPE_HUMIDITY, 0x01),
    }
    _BINDING_ATTRIBUTE_TO_SENSOR_TYPE = {
        AttributeDefs.remote_temperature_sensor_id.id: REMOTE_SENSOR_TYPE_TEMPERATURE,
        AttributeDefs.remote_humidity_sensor_id.id: REMOTE_SENSOR_TYPE_HUMIDITY,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize remote attribute state."""
        super().__init__(*args, **kwargs)
        self._remote_sensor_states: dict[tuple[int, int], int | None] = {
            sensor_key: None for sensor_key in self._SENSOR_DISPLAY_ATTRIBUTES
        }
        self._remote_sensor_values: dict[tuple[int, int], int] = {}
        self._remote_packet_count: int | None = None
        self._remote_packet_parts: dict[int, list[tuple[int, bytes]]] = {}
        self._remote_packet_started = 0.0

    def get(self, key: int | str, default: Any | None = None) -> Any:
        """Return remote readings only while remote sensor reporting is enabled."""
        attribute = self.find_attribute(key)
        if attribute.id == self.AttributeDefs.configuration_tip.id:
            return 1

        if (
            attribute.id in self._ATTRIBUTE_TO_SENSOR_KEY
            and not self._remote_source_enabled()
        ):
            return default
        return super().get(key, default)

    def _remote_source_enabled(self) -> bool:
        """Treat any non-zero 0x600E value as enabled remote sensor reporting."""
        status = super().get(self.AttributeDefs.temp_humi_source_status.name)
        return status is not None and int(status) != 0

    def _refresh_remote_display_attributes(self) -> None:
        """Refresh exposed remote readings after their reporting status changes."""
        enabled = self._remote_source_enabled()
        for sensor_key, attribute in self._SENSOR_DISPLAY_ATTRIBUTES.items():
            if enabled and sensor_key in self._remote_sensor_values:
                super()._update_attribute(
                    attribute.id, self._remote_sensor_values[sensor_key]
                )
            elif not enabled:
                super()._update_attribute(attribute.id, None)

    @staticmethod
    def _make_remote_attribute_array(payload: bytes) -> foundation.Array:
        """Wrap a remote sensor packet in a ZCL Array<uint8>."""
        return foundation.Array(
            type=DataTypeId.uint8,
            value=RemoteAttributeArrayValues(payload),
        )

    @staticmethod
    def _array_payload(value: Any) -> bytes:
        """Extract packet bytes from a ZCL Array value."""
        if isinstance(value, foundation.Array):
            if value.type != DataTypeId.uint8:
                raise ValueError("remote attribute Array elements must be uint8")
            value = value.value
        return bytes(int(item) for item in value)

    @classmethod
    def _encode_remote_sensor_packet(
        cls,
        sensor_type: int,
        sensor_id: int,
        raw_value: int,
    ) -> foundation.Array:
        """Encode one online sensor reading as a remote attribute packet."""
        if sensor_type == REMOTE_SENSOR_TYPE_TEMPERATURE:
            value = int(raw_value).to_bytes(2, "little", signed=True)
        elif sensor_type == REMOTE_SENSOR_TYPE_HUMIDITY:
            value = int(raw_value).to_bytes(2, "little", signed=False)
        else:
            raise ValueError(f"unsupported remote sensor type: {sensor_type}")

        sensor_item = (
            bytes(
                (
                    sensor_type,
                    sensor_id,
                    REMOTE_SENSOR_STATE_ONLINE,
                    REMOTE_SENSOR_VALUE_LENGTH,
                )
            )
            + value
        )
        sensor_value = bytes((1,)) + sensor_item
        tlv = (
            bytes((REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA, len(sensor_value))) + sensor_value
        )
        payload = bytes((1, 1, 0)) + tlv
        return cls._make_remote_attribute_array(payload)

    @staticmethod
    def _parse_packet(payload: bytes) -> tuple[int, int, list[tuple[int, bytes]]]:
        """Parse and validate one remote sensor packet."""
        if len(payload) < 3:
            raise ValueError("remote attribute packet header is truncated")

        remote_attr_count, packet_count, packet_index = payload[:3]
        if packet_count < 1 or packet_index >= packet_count:
            raise ValueError("invalid remote attribute packet index")

        attributes: list[tuple[int, bytes]] = []
        offset = 3
        for _ in range(remote_attr_count):
            if offset + 2 > len(payload):
                raise ValueError("remote attribute TLV header is truncated")
            attr_type = payload[offset]
            value_length = payload[offset + 1]
            offset += 2
            value_end = offset + value_length
            if value_end > len(payload):
                raise ValueError("remote attribute TLV value is truncated")
            attributes.append((attr_type, payload[offset:value_end]))
            offset = value_end

        if offset != len(payload):
            raise ValueError("remote attribute count does not match packet contents")
        return packet_count, packet_index, attributes

    @staticmethod
    def _parse_sensor_tlv(value: bytes) -> list[tuple[int, int, int, int | None]]:
        """Parse and validate a sensor-data TLV."""
        if not value:
            raise ValueError("sensor data is missing SensorCount")

        sensor_count = value[0]
        offset = 1
        sensors: list[tuple[int, int, int, int | None]] = []
        for _ in range(sensor_count):
            if offset + 4 > len(value):
                raise ValueError("sensor item header is truncated")
            sensor_type, sensor_id, sensor_state, value_length = value[
                offset : offset + 4
            ]
            offset += 4
            value_end = offset + value_length
            if value_end > len(value):
                raise ValueError("sensor item value is truncated")
            sensor_value = value[offset:value_end]
            offset = value_end

            if sensor_state > 0x03:
                raise ValueError("invalid remote sensor state")

            raw_value: int | None = None
            if sensor_type in (
                REMOTE_SENSOR_TYPE_TEMPERATURE,
                REMOTE_SENSOR_TYPE_HUMIDITY,
            ):
                if sensor_state == REMOTE_SENSOR_STATE_ONLINE:
                    if value_length not in (0, REMOTE_SENSOR_VALUE_LENGTH):
                        raise ValueError(
                            "online temperature/humidity must be 0 or 2 bytes"
                        )
                elif value_length not in (0, REMOTE_SENSOR_VALUE_LENGTH):
                    raise ValueError("invalid offline temperature/humidity length")

                if value_length == REMOTE_SENSOR_VALUE_LENGTH:
                    raw_value = int.from_bytes(
                        sensor_value,
                        "little",
                        signed=sensor_type == REMOTE_SENSOR_TYPE_TEMPERATURE,
                    )

            sensors.append((sensor_type, sensor_id, sensor_state, raw_value))

        if offset != len(value):
            raise ValueError("SensorCount does not match sensor data contents")
        return sensors

    def _apply_remote_attributes(self, attributes: list[tuple[int, bytes]]) -> None:
        """Validate supported TLVs, then update the matching remote sensor slots."""
        sensor_updates: list[tuple[int, int, int, int | None]] = []
        for attr_type, value in attributes:
            if attr_type == REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA:
                sensor_updates.extend(self._parse_sensor_tlv(value))

        for sensor_type, sensor_id, sensor_state, raw_value in sensor_updates:
            sensor_key = (sensor_type, sensor_id)
            value_attribute = self._SENSOR_DISPLAY_ATTRIBUTES.get(sensor_key)
            if value_attribute is None:
                continue

            self._remote_sensor_states[sensor_key] = sensor_state
            if sensor_state == REMOTE_SENSOR_STATE_ONLINE and raw_value is not None:
                self._remote_sensor_values[sensor_key] = raw_value
                if self._remote_source_enabled():
                    super()._update_attribute(value_attribute.id, raw_value)

    def _handle_remote_attribute_packet(self, value: Any) -> None:
        """Validate, reassemble, and apply a physical remote sensor packet."""
        payload = self._array_payload(value)
        packet_count, packet_index, attributes = self._parse_packet(payload)
        now = time.monotonic()

        if (
            self._remote_packet_count is not None
            and now - self._remote_packet_started > REMOTE_PACKET_TIMEOUT_SECONDS
        ):
            self._clear_remote_packet_assembly()

        if packet_count == 1:
            self._clear_remote_packet_assembly()
            self._apply_remote_attributes(attributes)
            return

        if packet_index == 0:
            self._remote_packet_count = packet_count
            self._remote_packet_parts = {}
            self._remote_packet_started = now
        elif self._remote_packet_count is None:
            return
        elif self._remote_packet_count != packet_count:
            self._clear_remote_packet_assembly()
            return

        self._remote_packet_parts[packet_index] = attributes
        if len(self._remote_packet_parts) != packet_count:
            return
        if any(index not in self._remote_packet_parts for index in range(packet_count)):
            return

        complete_attributes = [
            attribute
            for index in range(packet_count)
            for attribute in self._remote_packet_parts[index]
        ]
        self._clear_remote_packet_assembly()
        self._apply_remote_attributes(complete_attributes)

    def _clear_remote_packet_assembly(self) -> None:
        """Discard an incomplete remote sensor transfer."""
        self._remote_packet_count = None
        self._remote_packet_parts = {}
        self._remote_packet_started = 0.0

    @staticmethod
    def _write_status(
        attrid: int,
        status: foundation.Status,
    ) -> foundation.WriteAttributesStatusRecord:
        """Create a normalized write status for a remote sensor attribute."""
        return foundation.WriteAttributesStatusRecord(status=status, attrid=attrid)

    async def _write_remote_sensor_value(
        self,
        sensor_type: int,
        sensor_id: int,
        raw_value: int,
        manufacturer: int | UndefinedType | None,
        **kwargs: Any,
    ) -> foundation.Status:
        """Write one encoded sensor reading to the physical Array attribute."""
        try:
            remote_array = self._encode_remote_sensor_packet(
                sensor_type,
                sensor_id,
                raw_value,
            )
        except (OverflowError, ValueError):
            return foundation.Status.INVALID_VALUE

        result = await super().write_attributes(
            {self.AttributeDefs.remote_attributes: remote_array},
            manufacturer,
            update_cache=False,
            **kwargs,
        )
        records = result[0]
        if not records:
            return foundation.Status.FAILURE
        return records[0].status

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        *,
        update_cache: bool = True,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Route remote sensor slot writes through the physical Array attribute."""
        normalized = {
            self.find_attribute(attribute, manufacturer_code=manufacturer).id: value
            for attribute, value in attributes.items()
        }
        virtual_ids = set(self._ATTRIBUTE_TO_SENSOR_KEY) | set(
            self._BINDING_ATTRIBUTE_TO_SENSOR_TYPE
        )
        remaining = {
            attrid: value
            for attrid, value in normalized.items()
            if attrid not in virtual_ids
        }
        results: list[foundation.WriteAttributesStatusRecord] = []

        for sensor_type in (
            REMOTE_SENSOR_TYPE_TEMPERATURE,
            REMOTE_SENSOR_TYPE_HUMIDITY,
        ):
            binding_attribute = self._SENSOR_BINDING_ATTRIBUTES[sensor_type]
            value_attribute = self._SENSOR_VALUE_ATTRIBUTES[sensor_type]
            has_binding = binding_attribute.id in normalized
            has_value = value_attribute.id in normalized
            if not has_binding and not has_value:
                continue

            current_binding = super().get(binding_attribute.name)
            candidate_binding = normalized.get(binding_attribute.id, current_binding)
            if candidate_binding not in SUPPORTED_VIRTUAL_SENSOR_IDS:
                if has_binding:
                    results.append(
                        self._write_status(
                            binding_attribute.id, foundation.Status.INVALID_VALUE
                        )
                    )
                if has_value:
                    results.append(
                        self._write_status(
                            value_attribute.id, foundation.Status.INVALID_VALUE
                        )
                    )
                continue

            if not has_value:
                super()._update_attribute(binding_attribute.id, candidate_binding)
                results.append(
                    self._write_status(binding_attribute.id, foundation.Status.SUCCESS)
                )
                continue

            try:
                raw_value = int(normalized[value_attribute.id])
                self._encode_remote_sensor_packet(
                    sensor_type, candidate_binding, raw_value
                )
            except (OverflowError, TypeError, ValueError):
                if has_binding:
                    results.append(
                        self._write_status(
                            binding_attribute.id, foundation.Status.INVALID_VALUE
                        )
                    )
                results.append(
                    self._write_status(
                        value_attribute.id, foundation.Status.INVALID_VALUE
                    )
                )
                continue

            if has_binding:
                super()._update_attribute(binding_attribute.id, candidate_binding)
            sensor_key = (sensor_type, candidate_binding)
            self._remote_sensor_states[sensor_key] = REMOTE_SENSOR_STATE_ONLINE
            self._remote_sensor_values[sensor_key] = raw_value
            if self._remote_source_enabled():
                super()._update_attribute(
                    self._SENSOR_DISPLAY_ATTRIBUTES[sensor_key].id, raw_value
                )

            status = await self._write_remote_sensor_value(
                sensor_type,
                candidate_binding,
                raw_value,
                manufacturer,
                **kwargs,
            )
            if has_binding:
                results.append(self._write_status(binding_attribute.id, status))
            results.append(self._write_status(value_attribute.id, status))

        if remaining:
            physical_result = await super().write_attributes(
                remaining,
                manufacturer,
                update_cache=update_cache,
                **kwargs,
            )
            results.extend(physical_result[0])
            source_status = self.AttributeDefs.temp_humi_source_status
            if source_status.id in remaining and any(
                record.attrid == source_status.id
                and record.status == foundation.Status.SUCCESS
                for record in physical_result[0]
            ):
                self._update_attribute(source_status.id, remaining[source_status.id])
        return [results]

    def _update_attribute(
        self,
        attrid: int | t.uint16_t | ZCLAttributeDef,
        value: Any,
    ) -> None:
        """Decode physical remote sensor reports into exposed slot readings."""
        attribute_id = attrid.id if isinstance(attrid, ZCLAttributeDef) else int(attrid)
        super()._update_attribute(attrid, value)

        if attribute_id == self.AttributeDefs.temp_humi_source_status.id:
            self._refresh_remote_display_attributes()
            return
        if attribute_id != self.AttributeDefs.remote_attributes.id:
            return
        try:
            self._handle_remote_attribute_packet(value)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring malformed SNZB-02DR2 remote attribute packet")


(
    QuirkBuilder("SONOFF", "SNZB-02DR2")
    .replaces(CustomSonoffCluster)
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_temperature_min.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10,
        max_value=60,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="comfort_temperature_min",
        fallback_name="Comfort temperature min",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_temperature_max.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10,
        max_value=60,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="comfort_temperature_max",
        fallback_name="Comfort temperature max",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_humidity_min.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="comfort_humidity_min",
        fallback_name="Comfort humidity min",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_humidity_max.name,
        CustomSonoffCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="comfort_humidity_max",
        fallback_name="Comfort humidity max",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.temperature_unit.name,
        TemperatureUnit,
        CustomSonoffCluster.cluster_id,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.humidity_offset.name,
        CustomSonoffCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .write_attr_button(
        CustomSonoffCluster.AttributeDefs.reset_max_min_record.name,
        1,
        CustomSonoffCluster.cluster_id,
        translation_key="reset_max_min_record",
        fallback_name="Reset min/max records",
    )
    .switch(
        CustomSonoffCluster.AttributeDefs.temp_humi_source_status.name,
        CustomSonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="temp_humi_source_status",
        fallback_name="Enable remote sensor readings",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.remote_temperature_data.name,
        CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_temperature_data",
        fallback_name="Remote temperature (slot 1)",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.remote_humidity_data.name,
        CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_humidity_data",
        fallback_name="Remote humidity (slot 1)",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.remote_temperature_data_2.name,
        CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_temperature_data_2",
        fallback_name="Remote temperature (slot 2)",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.remote_humidity_data_2.name,
        CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_humidity_data_2",
        fallback_name="Remote humidity (slot 2)",
    )
    .sensor(
        CustomSonoffCluster.AttributeDefs.configuration_tip.name,
        CustomSonoffCluster.cluster_id,
        attribute_converter=configuration_tip_converter,
        translation_key="configuration_tip",
        fallback_name="Configuration reminder",
    )
    .add_to_registry()
)
