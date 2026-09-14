"""Sonoff SNZB-02UL - Zigbee temperature/humidity sensor with weather request.

Device signature (confirmed via ZHA diagnostics):

- Manufacturer: SONOFF
- Model: SNZB-02UL
- Endpoint 1: 0xFC11 Server/in cluster (custom Sonoff cluster with weather command 0x14)

The device sends a Server→Client command 0x14 on cluster 0xFC11 to request
current weather (device_type: uint8, longitude: int32s, latitude: int32s).
The quirk decodes the request and emits a ``get_current_weather`` zha_event.
A Home Assistant automation Blueprint consumes the event, reads a user-selected
weather entity, and responds with a Client→Server command 0x14 carrying the
mapped weather enum (device_type: uint8, length: uint8, weather: enum8).
"""

import logging
import math
import time
from typing import Any

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfPressure, UnitOfTemperature
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks import LocalDataCluster
from zhaquirks.const import ZHA_SEND_EVENT

LOGGER = logging.getLogger(__name__)

MEASURED_VALUE_ATTR = 0x0000

REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA = 0x03
REMOTE_SENSOR_ID = 0x01
REMOTE_SENSOR_TYPE_TEMPERATURE = 0x00
REMOTE_SENSOR_TYPE_HUMIDITY = 0x01
REMOTE_SENSOR_TYPE_PRESSURE = 0x02
REMOTE_SENSOR_STATE_ONLINE = 0x01
REMOTE_SENSOR_STATE_RESTORED = 0x03
REMOTE_SENSOR_UNBIND_PAYLOAD = bytes(
    (
        0x01,
        0x01,
        0x00,  # One packet at index 0.
        0x03,
        0x05,  # Generic sensor data: count plus one 4-byte item.
        0x01,  # SensorCount.
        REMOTE_SENSOR_TYPE_TEMPERATURE,
        REMOTE_SENSOR_ID,
        0x00,
        0x00,  # Temperature sensor 1: unbound, no value.
    )
)

REMOTE_PACKET_TIMEOUT_SECONDS = 30

REMOTE_SENSOR_VALUE_TYPES = {
    REMOTE_SENSOR_TYPE_TEMPERATURE: (2, True),
    REMOTE_SENSOR_TYPE_HUMIDITY: (2, False),
    REMOTE_SENSOR_TYPE_PRESSURE: (4, True),
}

RemoteAttributeArrayValues = t.LVList[t.uint8_t, t.uint16_t]

# ---------------------------------------------------------------------------
# Weather enum – values the device expects in a 0x14 weather response.
# The device derives day/night presentation from its own time and location;
# these values are the six current-weather categories defined by the device.
# ---------------------------------------------------------------------------


class Weather(t.enum8):
    """SNZB-02UL weather enumeration."""

    Sunny = 0x00
    # Night_sunny = 0x01  -- reserved; device handles night on its own
    Partly_cloudy = 0x01
    Cloudy = 0x02
    Rainy = 0x03
    Snowy = 0x04
    Windy = 0x05


class TemperatureUnit(t.enum16):
    """Temperature unit."""

    Celsius = 0
    Fahrenheit = 1


# ---------------------------------------------------------------------------
# Custom cluster 0xFC11 with bidirectional weather command 0x14
# ---------------------------------------------------------------------------


class SNZB02ULCluster(CustomCluster):
    """Sonoff SNZB-02UL custom cluster (0xFC11) with weather request support."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Physical and local virtual remote-sensor attributes."""

        remote_attributes = ZCLAttributeDef(
            id=0x601E,
            type=foundation.Array,
            zcl_type=DataTypeId.array,
            manufacturer_code=None,
        )
        remote_sensor_source = ZCLAttributeDef(
            id=0xFFF0,
            type=t.Bool,
            manufacturer_code=None,
        )
        remote_temperature_data = ZCLAttributeDef(
            id=0xFFF1,
            type=t.int16s,
            manufacturer_code=None,
        )
        remote_humidity_data = ZCLAttributeDef(
            id=0xFFF2,
            type=t.uint16_t,
            manufacturer_code=None,
        )
        remote_pressure_data = ZCLAttributeDef(
            id=0xFFF3,
            type=t.int32s,
            manufacturer_code=None,
        )

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

    _SENSOR_VALUE_ATTRIBUTES = {
        REMOTE_SENSOR_TYPE_TEMPERATURE: AttributeDefs.remote_temperature_data,
        REMOTE_SENSOR_TYPE_HUMIDITY: AttributeDefs.remote_humidity_data,
        REMOTE_SENSOR_TYPE_PRESSURE: AttributeDefs.remote_pressure_data,
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the single in-flight remote attribute reassembly."""
        super().__init__(*args, **kwargs)
        self._remote_packet_count: int | None = None
        self._remote_packet_parts: dict[int, list[tuple[int, bytes]]] = {}
        self._remote_packet_started = 0.0
        super()._update_attribute(self.AttributeDefs.remote_sensor_source.id, False)

    @staticmethod
    def _make_remote_attribute_array(payload: bytes) -> foundation.Array:
        """Wrap business bytes in a ZCL Array<uint8>."""
        return foundation.Array(
            type=DataTypeId.uint8,
            value=RemoteAttributeArrayValues(payload),
        )

    @staticmethod
    def _array_payload(value: Any) -> bytes:
        """Extract business bytes from a ZCL Array<uint8>."""
        if isinstance(value, foundation.Array):
            if value.type != DataTypeId.uint8:
                raise ValueError("remote attribute Array elements must be uint8")
            value = value.value
        return bytes(int(item) for item in value)

    @classmethod
    def _encode_remote_sensor_packet(
        cls, sensor_type: int, raw_value: int
    ) -> foundation.Array:
        """Encode one fixed-ID online generic sensor item."""
        try:
            value_length, signed = REMOTE_SENSOR_VALUE_TYPES[sensor_type]
        except KeyError as exc:
            raise ValueError(f"unsupported remote sensor type: {sensor_type}") from exc

        value = int(raw_value).to_bytes(value_length, "little", signed=signed)
        sensor_item = (
            bytes(
                (
                    sensor_type,
                    REMOTE_SENSOR_ID,
                    REMOTE_SENSOR_STATE_ONLINE,
                    value_length,
                )
            )
            + value
        )
        sensor_value = bytes((1,)) + sensor_item
        tlv = (
            bytes((REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA, len(sensor_value))) + sensor_value
        )
        return cls._make_remote_attribute_array(bytes((1, 1, 0)) + tlv)

    @staticmethod
    def _parse_packet(payload: bytes) -> tuple[int, int, list[tuple[int, bytes]]]:
        """Parse and validate one remote attribute packet."""
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
            attr_type, value_length = payload[offset : offset + 2]
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
        """Parse a T=0x03 value without changing cached entity data."""
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

            if sensor_id == 0xFF:
                raise ValueError("reserved remote sensor ID")
            if sensor_state > REMOTE_SENSOR_STATE_RESTORED:
                raise ValueError("invalid remote sensor state")

            raw_value: int | None = None
            known_type = REMOTE_SENSOR_VALUE_TYPES.get(sensor_type)
            if known_type is not None:
                expected_length, signed = known_type
                if value_length not in (0, expected_length):
                    raise ValueError("invalid known remote sensor value length")
                if value_length == expected_length:
                    raw_value = int.from_bytes(sensor_value, "little", signed=signed)

            sensors.append((sensor_type, sensor_id, sensor_state, raw_value))

        if offset != len(value):
            raise ValueError("SensorCount does not match sensor data contents")
        return sensors

    def _apply_remote_attributes(self, attributes: list[tuple[int, bytes]]) -> None:
        """Validate supported TLVs first, then atomically publish fixed-source data."""
        sensor_updates: list[tuple[int, int, int, int | None]] = []
        for attr_type, value in attributes:
            if attr_type == REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA:
                sensor_updates.extend(self._parse_sensor_tlv(value))

        value_updates: dict[int, int | None] = {}
        for sensor_type, sensor_id, sensor_state, raw_value in sensor_updates:
            value_attribute = self._SENSOR_VALUE_ATTRIBUTES.get(sensor_type)
            if sensor_id != REMOTE_SENSOR_ID or value_attribute is None:
                continue
            if (
                sensor_state
                in (REMOTE_SENSOR_STATE_ONLINE, REMOTE_SENSOR_STATE_RESTORED)
                and raw_value is not None
            ):
                value_updates[value_attribute.id] = raw_value
            else:
                value_updates[value_attribute.id] = None

        for attrid, raw_value in value_updates.items():
            super()._update_attribute(attrid, raw_value)

    def _clear_remote_packet_assembly(self) -> None:
        """Discard an incomplete remote attribute transfer."""
        self._remote_packet_count = None
        self._remote_packet_parts = {}
        self._remote_packet_started = 0.0

    def _handle_remote_attribute_packet(self, value: Any) -> None:
        """Validate, reassemble, and apply a physical remote attribute Array."""
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

    @staticmethod
    def _write_status(
        attrid: int, status: foundation.Status
    ) -> foundation.WriteAttributesStatusRecord:
        """Create a normalized virtual attribute write result."""
        return foundation.WriteAttributesStatusRecord(status=status, attrid=attrid)

    async def write_attributes(
        self,
        attributes: dict[str | int | ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        *,
        update_cache: bool = True,
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Route local remote-sensor attributes through physical 0x601E writes."""
        normalized = {
            self.find_attribute(attribute, manufacturer_code=manufacturer).id: value
            for attribute, value in attributes.items()
        }
        source_switch_results: list[foundation.WriteAttributesStatusRecord] = []
        source_switch_id = self.AttributeDefs.remote_sensor_source.id
        if source_switch_id in normalized:
            source_enabled = bool(normalized.pop(source_switch_id))
            if source_enabled:
                # The blueprint now writes each selected source's actual value,
                # which creates its matching online 0x601E sensor item.
                super()._update_attribute(source_switch_id, True)
                source_switch_results.append(
                    self._write_status(source_switch_id, foundation.Status.SUCCESS)
                )
            else:
                source_result = await super().write_attributes(
                    {
                        self.AttributeDefs.remote_attributes: self._make_remote_attribute_array(
                            REMOTE_SENSOR_UNBIND_PAYLOAD
                        )
                    },
                    manufacturer,
                    update_cache=False,
                    **kwargs,
                )
                records = source_result[0]
                status = records[0].status if records else foundation.Status.FAILURE
                source_switch_results.append(
                    self._write_status(source_switch_id, status)
                )
                if status == foundation.Status.SUCCESS:
                    super()._update_attribute(source_switch_id, False)
                    super()._update_attribute(
                        self.AttributeDefs.remote_temperature_data.id, None
                    )

        virtual_ids = {
            attribute.id for attribute in self._SENSOR_VALUE_ATTRIBUTES.values()
        }
        invalid_comfort_ids: set[int] = set()
        for minimum, maximum in (
            (
                self.AttributeDefs.comfort_temperature_min,
                self.AttributeDefs.comfort_temperature_max,
            ),
            (
                self.AttributeDefs.comfort_humidity_min,
                self.AttributeDefs.comfort_humidity_max,
            ),
        ):
            minimum_value = normalized.get(minimum.id, self._attr_cache.get(minimum.id))
            maximum_value = normalized.get(maximum.id, self._attr_cache.get(maximum.id))
            if minimum_value is None or maximum_value is None:
                continue
            try:
                is_invalid = int(minimum_value) >= int(maximum_value)
            except (TypeError, ValueError):
                continue
            if is_invalid:
                invalid_comfort_ids.update(
                    attrid
                    for attrid in (minimum.id, maximum.id)
                    if attrid in normalized
                )

        remaining = {
            attrid: value
            for attrid, value in normalized.items()
            if attrid not in virtual_ids and attrid not in invalid_comfort_ids
        }
        results: list[foundation.WriteAttributesStatusRecord] = (
            source_switch_results
            + [
                self._write_status(attrid, foundation.Status.INVALID_VALUE)
                for attrid in invalid_comfort_ids
            ]
        )

        for sensor_type, value_attribute in self._SENSOR_VALUE_ATTRIBUTES.items():
            if value_attribute.id not in normalized:
                continue
            try:
                raw_value = int(normalized[value_attribute.id])
                remote_array = self._encode_remote_sensor_packet(sensor_type, raw_value)
            except (OverflowError, TypeError, ValueError):
                results.append(
                    self._write_status(
                        value_attribute.id, foundation.Status.INVALID_VALUE
                    )
                )
                continue

            super()._update_attribute(value_attribute.id, raw_value)
            physical_result = await super().write_attributes(
                {self.AttributeDefs.remote_attributes: remote_array},
                manufacturer,
                update_cache=False,
                **kwargs,
            )
            records = physical_result[0]
            status = records[0].status if records else foundation.Status.FAILURE
            results.append(self._write_status(value_attribute.id, status))
            if status == foundation.Status.SUCCESS:
                super()._update_attribute(
                    self.AttributeDefs.remote_sensor_source.id, True
                )

        if remaining:
            physical_result = await super().write_attributes(
                remaining,
                manufacturer,
                update_cache=update_cache,
                **kwargs,
            )
            results.extend(physical_result[0])
        return [results]

    def _update_attribute(
        self,
        attrid: int | t.uint16_t | ZCLAttributeDef,
        value: Any,
    ) -> None:
        """Decode physical remote attribute reports after normal cache handling."""
        attribute_id = attrid.id if isinstance(attrid, ZCLAttributeDef) else int(attrid)
        super()._update_attribute(attrid, value)

        if attribute_id != self.AttributeDefs.remote_attributes.id:
            return
        try:
            self._handle_remote_attribute_packet(value)
        except (TypeError, ValueError):
            LOGGER.warning("Ignoring malformed SNZB-02UL remote attribute packet")

    class ClientCommandDefs(foundation.BaseCommandDefs):
        """Commands that originate from the device (Server→Client)."""

        get_current_weather = foundation.ZCLCommandDef(
            id=0x14,
            schema={
                "device_type": t.uint8_t,
                "longitude": t.int32s,
                "latitude": t.int32s,
            },
            manufacturer_code=None,
        )

    class ServerCommandDefs(foundation.BaseCommandDefs):
        """Commands sent to the device (Client→Server)."""

        get_current_weather_response = foundation.ZCLCommandDef(
            id=0x14,
            schema={
                "device_type": t.uint8_t,
                "length": t.uint8_t,
                "weather": Weather,
            },
            manufacturer_code=None,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Emit a ``get_current_weather`` zha_event for command 0x14.

        Non-0x14 commands fall through to the default Zigbee stack handling
        (including ZCL Default Response when the frame requests it).
        """
        if hdr.command_id != 0x14:
            # Let the base implementation handle all non-weather commands,
            # including ZCL Default Response transmission.
            return super().handle_cluster_request(
                hdr, args, dst_addressing=dst_addressing
            )

        # Send ZCL Default Response if the frame requests it.
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        # Decode the payload for logging purposes, but the event consumers
        # must not rely on latitude / longitude for weather selection.
        device_type = args[0] if len(args) > 0 else None
        longitude = args[1] if len(args) > 1 else None
        latitude = args[2] if len(args) > 2 else None

        LOGGER.debug(
            "SNZB-02UL weather request: device_type=%s, lon=%s, lat=%s",
            device_type,
            longitude,
            latitude,
        )

        self.listener_event(
            ZHA_SEND_EVENT,
            "get_current_weather",
            {
                "device_type": device_type,
                "longitude": longitude,
                "latitude": latitude,
            },
        )


class SonoffTemperatureCluster(CustomCluster, TemperatureMeasurement):
    """Temperature cluster that refreshes calculated climate values."""

    def _update_attribute(self, attrid, value):
        """Update temperature and refresh derived values."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.measured_value.id and hasattr(
            self.endpoint, SonoffCalculatedClimateCluster.ep_attribute
        ):
            self.endpoint.sonoff_calculated_climate.update_calculated_values()


class SonoffRelativeHumidityCluster(CustomCluster, RelativeHumidity):
    """Relative humidity cluster that refreshes calculated climate values."""

    def _update_attribute(self, attrid, value):
        """Update relative humidity and refresh derived values."""
        super()._update_attribute(attrid, value)
        if attrid == self.AttributeDefs.measured_value.id and hasattr(
            self.endpoint, SonoffCalculatedClimateCluster.ep_attribute
        ):
            self.endpoint.sonoff_calculated_climate.update_calculated_values()


# ---------------------------------------------------------------------------
# Calculated climate cluster (dew point / VPD)
# ---------------------------------------------------------------------------


class SonoffCalculatedClimateCluster(LocalDataCluster):
    """Local cluster exposing values calculated from measured temperature and humidity."""

    cluster_id = 0xFC12
    ep_attribute = "sonoff_calculated_climate"

    class AttributeDefs(BaseAttributeDefs):
        """Calculated attribute definitions."""

        dew_point = ZCLAttributeDef(id=0x0000, type=t.int16s)
        saturation_vapor_pressure = ZCLAttributeDef(id=0x0001, type=t.uint16_t)
        vpd = ZCLAttributeDef(id=0x0002, type=t.uint16_t)

    @classmethod
    def calculate_dew_point(cls, temperature, humidity):
        """Calculate dew point using the Magnus formula."""
        if temperature is None or humidity is None:
            return None
        if humidity <= 0 or humidity > 100:
            return None

        a = 17.62
        b = 243.12

        try:
            ln_rh = math.log(humidity / 100.0)
            alpha = ln_rh + (a * temperature) / (b + temperature)
            return (b * alpha) / (a - alpha)
        except (ValueError, ZeroDivisionError):
            return None

    @classmethod
    def calculate_saturation_vapor_pressure(cls, temperature):
        """Calculate saturation vapor pressure using the Magnus formula."""
        if temperature is None:
            return None

        try:
            return 6.112 * math.exp((17.62 * temperature) / (temperature + 243.12))
        except (ValueError, ZeroDivisionError):
            return None

    @classmethod
    def calculate_vpd(cls, temperature, humidity):
        """Calculate Vapor Pressure Deficit (VPD)."""
        if temperature is None or humidity is None:
            return None
        if humidity < 0 or humidity > 100:
            return None

        e_sat = cls.calculate_saturation_vapor_pressure(temperature)
        if e_sat is None:
            return None

        e_actual = (humidity / 100.0) * e_sat
        return e_sat - e_actual

    def update_calculated_values(self):
        """Update calculated attributes from the latest measured temperature and humidity."""
        temperature = self._temperature_celsius()
        humidity = self._relative_humidity_percent()

        saturation_vapor_pressure = self.calculate_saturation_vapor_pressure(
            temperature
        )
        if saturation_vapor_pressure is not None:
            self._update_attribute(
                self.AttributeDefs.saturation_vapor_pressure.id,
                round(saturation_vapor_pressure * 100),
            )

        dew_point = self.calculate_dew_point(temperature, humidity)
        if dew_point is not None:
            self._update_attribute(
                self.AttributeDefs.dew_point.id,
                round(dew_point * 100),
            )

        vpd = self.calculate_vpd(temperature, humidity)
        if vpd is not None:
            self._update_attribute(
                self.AttributeDefs.vpd.id,
                round(vpd * 100),
            )

    def _temperature_celsius(self):
        """Return the cached measured temperature in Celsius."""
        if not hasattr(self.endpoint, "temperature"):
            return None
        value = self.endpoint.temperature._attr_cache.get(MEASURED_VALUE_ATTR)
        if value is None or value == 0x8000:
            return None
        return value / 100

    def _relative_humidity_percent(self):
        """Return the cached measured relative humidity as a percentage."""
        if not hasattr(self.endpoint, "humidity"):
            return None
        value = self.endpoint.humidity._attr_cache.get(MEASURED_VALUE_ATTR)
        if value is None or value == 0xFFFF:
            return None
        return value / 100


# ---------------------------------------------------------------------------
# Quirk registration
# ---------------------------------------------------------------------------


(
    QuirkBuilder("SONOFF", "SNZB-02UL")
    .replaces(SNZB02ULCluster)
    .replaces(SonoffTemperatureCluster)
    .replaces(SonoffRelativeHumidityCluster)
    .adds(SonoffCalculatedClimateCluster)
    .switch(
        SNZB02ULCluster.AttributeDefs.remote_sensor_source.name,
        SNZB02ULCluster.cluster_id,
        translation_key="remote_sensor_source",
        fallback_name="Remote sensor source",
    )
    .sensor(
        SNZB02ULCluster.AttributeDefs.remote_temperature_data.name,
        SNZB02ULCluster.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_temperature_data",
        fallback_name="Remote temperature data",
    )
    .sensor(
        SNZB02ULCluster.AttributeDefs.remote_humidity_data.name,
        SNZB02ULCluster.cluster_id,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_humidity_data",
        fallback_name="Remote humidity data",
    )
    .sensor(
        SNZB02ULCluster.AttributeDefs.remote_pressure_data.name,
        SNZB02ULCluster.cluster_id,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit="hPa",
        multiplier=0.01,
        suggested_display_precision=1,
        translation_key="remote_pressure_data",
        fallback_name="Remote pressure data",
    )
    .number(
        SNZB02ULCluster.AttributeDefs.comfort_temperature_min.name,
        SNZB02ULCluster.cluster_id,
        min_value=0,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="comfort_temperature_min",
        fallback_name="Comfort temperature min",
    )
    .number(
        SNZB02ULCluster.AttributeDefs.comfort_temperature_max.name,
        SNZB02ULCluster.cluster_id,
        min_value=0,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="comfort_temperature_max",
        fallback_name="Comfort temperature max",
    )
    .number(
        SNZB02ULCluster.AttributeDefs.comfort_humidity_min.name,
        SNZB02ULCluster.cluster_id,
        min_value=5,
        max_value=95,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="comfort_humidity_min",
        fallback_name="Comfort humidity min",
    )
    .number(
        SNZB02ULCluster.AttributeDefs.comfort_humidity_max.name,
        SNZB02ULCluster.cluster_id,
        min_value=5,
        max_value=95,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="comfort_humidity_max",
        fallback_name="Comfort humidity max",
    )
    .enum(
        SNZB02ULCluster.AttributeDefs.temperature_unit.name,
        TemperatureUnit,
        SNZB02ULCluster.cluster_id,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .number(
        SNZB02ULCluster.AttributeDefs.temperature_offset.name,
        SNZB02ULCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        SNZB02ULCluster.AttributeDefs.humidity_offset.name,
        SNZB02ULCluster.cluster_id,
        min_value=-50,
        max_value=50,
        step=0.1,
        device_class=NumberDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .sensor(
        attribute_name=SonoffCalculatedClimateCluster.AttributeDefs.dew_point.name,
        cluster_id=SonoffCalculatedClimateCluster.cluster_id,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="dew_point",
        fallback_name="Dew Point",
    )
    .sensor(
        attribute_name=SonoffCalculatedClimateCluster.AttributeDefs.vpd.name,
        cluster_id=SonoffCalculatedClimateCluster.cluster_id,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPressure.HPA,
        multiplier=0.01,
        translation_key="vapor_pressure_deficit",
        fallback_name="VPD",
    )
    .add_to_registry()
)
