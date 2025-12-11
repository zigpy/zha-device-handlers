"""Aqara E1 Radiator Thermostat Quirk - Version 4 with Full External Sensor Support.

This quirk adds complete external temperature sensor support including:
- Sensor registration (switching between internal/external modes)
- External temperature input

Based on the Zigbee2MQTT implementation in zigbee-herdsman-converters/lib/lumi.ts

Original quirk: zhaquirks/xiaomi/aqara/thermostat_agl001.py
Modification by: Andy (Carse IT Services) with Claude assistance
Date: December 2025
"""
from __future__ import annotations

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

# =============================================================================
# CONSTANTS
# =============================================================================

ZCL_SYSTEM_MODE = Thermostat.attributes_by_name["system_mode"].id

# Aqara TRV attribute IDs
SYSTEM_MODE = 0x0271
PRESET = 0x0272
WINDOW_DETECTION = 0x0273
VALVE_DETECTION = 0x0274
VALVE_ALARM = 0x0275
CHILD_LOCK = 0x0277
AWAY_PRESET_TEMPERATURE = 0x0279
WINDOW_OPEN = 0x027A
CALIBRATED = 0x027B
SCHEDULE = 0x027D
SENSOR = 0x027E  # 638 decimal - sensor mode (0=internal, 1=external)
BATTERY_PERCENTAGE = 0x040A

# Binary data attribute
AQARA_FFF2 = 0xFFF2

# Custom virtual attributes for our quirk
EXTERNAL_TEMPERATURE_INPUT = 0x0EE0  # For sending temperature values
SENSOR_REGISTER = 0x0EE1  # For triggering sensor registration

XIAOMI_CLUSTER_ID = 0xFCC0
MANUFACTURER_CODE = 0x115F  # 4447

# Fake sensor IEEE address (from Z2M implementation)
FAKE_SENSOR_IEEE = bytes.fromhex('00158d00019d1b98')

# System mode mapping
XIAOMI_SYSTEM_MODE_MAP = {
    0: Thermostat.SystemMode.Off,
    1: Thermostat.SystemMode.Heat,
}


# =============================================================================
# HELPER FUNCTIONS - Binary payload builders
# =============================================================================

def build_lumi_header(counter: int, params_length: int, action: int) -> bytes:
    """
    Build the Aqara/Lumi message header.
    
    Args:
        counter: Message sequence counter (0x12 or 0x13 typically)
        params_length: Length of the parameters section
        action: Action code (0x02=register, 0x04=unregister, 0x05=send temp)
    
    Returns:
        9-byte header
    """
    header_start = bytes([0xAA, 0x71, params_length + 3, 0x44, counter])
    integrity = (512 - sum(header_start)) & 0xFF
    return header_start + bytes([integrity, action, 0x41, params_length])


def build_sensor_registration_payloads(device_ieee: bytes) -> tuple[bytes, bytes]:
    """
    Build the two registration payloads to enable external sensor mode.
    
    This registers a fake sensor with the TRV so it will accept external
    temperature readings.
    
    Args:
        device_ieee: The TRV's IEEE address as 8 bytes
    
    Returns:
        Tuple of (message1, message2) to send in sequence
    """
    # Current timestamp as 4-byte big-endian
    timestamp = struct.pack('>I', int(time.time()))
    
    # Message 1: Register humidity-type sensor
    # The Chinese characters in the original are sensor type descriptors
    params1 = (
        timestamp +
        bytes([0x3d, 0x04]) +
        device_ieee +
        FAKE_SENSOR_IEEE +
        bytes([
            0x00, 0x01, 0x00, 0x55,  # Fixed bytes
            0x13, 0x0a, 0x02, 0x00, 0x00, 0x64, 0x04,  # Sensor config
            0xce, 0xc2, 0xb6, 0xc8,  # Chinese chars (湿度)
            0x00, 0x00, 0x00, 0x00, 0x00,
            0x01, 0x3d, 0x64, 0x65
        ])
    )
    
    # Message 2: Register temperature-type sensor
    params2 = (
        timestamp +
        bytes([0x3d, 0x05]) +
        device_ieee +
        FAKE_SENSOR_IEEE +
        bytes([
            0x08, 0x00, 0x07, 0xfd,  # Fixed bytes
            0x16, 0x0a, 0x02, 0x0a,  # Sensor config
            0xc9, 0xe8, 0xb1, 0xb8, 0xd4, 0xda, 0xcf, 0xdf, 0xc0, 0xeb,  # Chinese chars
            0x00, 0x00, 0x00, 0x00, 0x00,
            0x01, 0x3d, 0x04, 0x65
        ])
    )
    
    # Build complete messages with headers
    # Action 0x02 = register sensor
    msg1 = build_lumi_header(0x12, len(params1), 0x02) + params1
    msg2 = build_lumi_header(0x13, len(params2), 0x02) + params2
    
    return msg1, msg2


def build_sensor_unregistration_payloads(device_ieee: bytes) -> tuple[bytes, bytes]:
    """
    Build the two payloads to disable external sensor mode (return to internal).
    
    Args:
        device_ieee: The TRV's IEEE address as 8 bytes
    
    Returns:
        Tuple of (message1, message2) to send in sequence
    """
    timestamp = struct.pack('>I', int(time.time()))
    
    # Messages to unregister - just device IEEE with zeros for sensor
    params1 = (
        timestamp +
        bytes([0x3d, 0x05]) +
        device_ieee +
        bytes([0x00] * 12)  # 12 zero bytes instead of sensor IEEE + extra
    )
    
    params2 = (
        timestamp +
        bytes([0x3d, 0x04]) +
        device_ieee +
        bytes([0x00] * 12)
    )
    
    # Action 0x04 = unregister sensor
    msg1 = build_lumi_header(0x12, len(params1), 0x04) + params1
    msg2 = build_lumi_header(0x13, len(params2), 0x04) + params2
    
    return msg1, msg2


def build_external_temp_payload(temperature: float) -> bytes:
    """
    Build the payload to send an external temperature reading.
    
    Args:
        temperature: Temperature in Celsius
    
    Returns:
        Complete binary payload for attribute 0xFFF2
    """
    # Convert temperature: multiply by 100, encode as big-endian float
    temp_value = round(temperature * 100)
    temp_bytes = struct.pack('>f', temp_value)
    
    # Params: sensor_id (8) + fixed bytes (4) + temperature (4) = 16 bytes
    params = FAKE_SENSOR_IEEE + bytes([0x00, 0x01, 0x00, 0x55]) + temp_bytes
    
    # Action 0x05 = send temperature
    return build_lumi_header(0x12, len(params), 0x05) + params


# =============================================================================
# THERMOSTAT CLUSTER
# =============================================================================

class ThermostatCluster(CustomCluster, Thermostat):
    """Custom thermostat cluster that redirects system_mode to Xiaomi cluster."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.attributes_by_name[
            "ctrl_sequence_of_oper"
        ].id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
    ):
        """Pass reading system_mode to Xiaomi cluster."""
        successful_r, failed_r = {}, {}
        remaining_attributes = attributes.copy()

        if ZCL_SYSTEM_MODE in attributes or "system_mode" in attributes:
            self.debug("Passing 'system_mode' read to Xiaomi cluster")

            if ZCL_SYSTEM_MODE in attributes:
                remaining_attributes.remove(ZCL_SYSTEM_MODE)
            if "system_mode" in attributes:
                remaining_attributes.remove("system_mode")

            successful_r, failed_r = await self.endpoint.opple_cluster.read_attributes(
                [SYSTEM_MODE], allow_cache, only_cache, manufacturer
            )
            if SYSTEM_MODE in successful_r:
                successful_r[ZCL_SYSTEM_MODE] = XIAOMI_SYSTEM_MODE_MAP[
                    successful_r.pop(SYSTEM_MODE)
                ]

        if remaining_attributes:
            remaining_result = await super().read_attributes(
                remaining_attributes, allow_cache, only_cache, manufacturer
            )
            successful_r.update(remaining_result[0])
            failed_r.update(remaining_result[1])
        return successful_r, failed_r

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """Pass writing system_mode to Xiaomi cluster."""
        result = []
        remaining_attributes = attributes.copy()
        system_mode_value = None

        if ZCL_SYSTEM_MODE in attributes:
            remaining_attributes.pop(ZCL_SYSTEM_MODE)
            system_mode_value = attributes.get(ZCL_SYSTEM_MODE)
        if "system_mode" in attributes:
            remaining_attributes.pop("system_mode")
            system_mode_value = attributes.get("system_mode")

        if system_mode_value is not None:
            self.debug("Passing 'system_mode' write to Xiaomi cluster")
            result += await self.endpoint.opple_cluster.write_attributes(
                {SYSTEM_MODE: min(int(system_mode_value), 1)}
            )

        if remaining_attributes:
            result += await super().write_attributes(remaining_attributes, manufacturer)
        return result


# =============================================================================
# AQARA-SPECIFIC CLUSTER WITH EXTERNAL SENSOR SUPPORT
# =============================================================================

class AqaraThermostatSpecificCluster(XiaomiAqaraE1Cluster):
    """
    Aqara manufacturer-specific cluster with full external temperature support.
    
    Supports:
    - sensor_register: Write "external" or "internal" to switch modes
    - external_temperature_input: Write temperature values (0-55°C)
    """

    ep_attribute = "opple_cluster"

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            SYSTEM_MODE: ("system_mode", t.uint8_t, True),
            PRESET: ("preset", t.uint8_t, True),
            WINDOW_DETECTION: ("window_detection", t.uint8_t, True),
            VALVE_DETECTION: ("valve_detection", t.uint8_t, True),
            VALVE_ALARM: ("valve_alarm", t.uint8_t, True),
            CHILD_LOCK: ("child_lock", t.uint8_t, True),
            AWAY_PRESET_TEMPERATURE: ("away_preset_temperature", t.uint32_t, True),
            WINDOW_OPEN: ("window_open", t.uint8_t, True),
            CALIBRATED: ("calibrated", t.uint8_t, True),
            SCHEDULE: ("schedule", t.uint8_t, True),
            SENSOR: ("sensor", t.uint8_t, True),
            BATTERY_PERCENTAGE: ("battery_percentage", t.uint8_t, True),
            # Virtual attributes for external sensor control
            EXTERNAL_TEMPERATURE_INPUT: ("external_temperature_input", t.Single, True),
            SENSOR_REGISTER: ("sensor_register", t.uint8_t, True),
            # Binary data attribute
            AQARA_FFF2: ("aqara_fff2", t.LVBytes, True),
        }
    )

    def _update_attribute(self, attrid, value):
        """Handle attribute updates from the device."""
        self.debug("Updating attribute on Xiaomi cluster %s with %s", attrid, value)
        
        if attrid == SYSTEM_MODE:
            self.endpoint.thermostat.update_attribute(
                ZCL_SYSTEM_MODE, XIAOMI_SYSTEM_MODE_MAP[value]
            )
        
        super()._update_attribute(attrid, value)

    def _get_device_ieee_bytes(self) -> bytes:
        """Get the device's IEEE address as bytes."""
        ieee_str = str(self.endpoint.device.ieee)
        # Remove colons and convert to bytes
        ieee_hex = ieee_str.replace(':', '')
        return bytes.fromhex(ieee_hex)

    async def write_attributes(
        self, attributes: dict[str | int, Any], manufacturer: int | None = None
    ) -> list:
        """
        Handle attribute writes with special handling for sensor registration
        and external temperature input.
        """
        result = []
        remaining_attributes = attributes.copy()

        # Handle sensor_register (switch between internal/external mode)
        sensor_mode = None
        if SENSOR_REGISTER in attributes:
            sensor_mode = attributes.pop(SENSOR_REGISTER)
            remaining_attributes.pop(SENSOR_REGISTER, None)
        if "sensor_register" in attributes:
            sensor_mode = attributes.pop("sensor_register")
            remaining_attributes.pop("sensor_register", None)

        if sensor_mode is not None:
            await self._handle_sensor_registration(sensor_mode)

        # Handle external_temperature_input
        ext_temp = None
        if EXTERNAL_TEMPERATURE_INPUT in attributes:
            ext_temp = attributes.pop(EXTERNAL_TEMPERATURE_INPUT)
            remaining_attributes.pop(EXTERNAL_TEMPERATURE_INPUT, None)
        if "external_temperature_input" in attributes:
            ext_temp = attributes.pop("external_temperature_input")
            remaining_attributes.pop("external_temperature_input", None)

        if ext_temp is not None:
            await self._handle_external_temperature(ext_temp)

        # Write remaining attributes normally
        if remaining_attributes:
            result.extend(
                await super().write_attributes(remaining_attributes, manufacturer)
            )

        return result

    async def _handle_sensor_registration(self, mode) -> None:
        """
        Handle switching between internal and external sensor modes.
        
        Args:
            mode: 1/"external" for external, 0/"internal" for internal
        """
        import asyncio
        
        # Normalize mode value
        if isinstance(mode, str):
            mode = 1 if mode.lower() == "external" else 0
        
        device_ieee = self._get_device_ieee_bytes()
        
        if mode == 1:
            self.debug("Registering external sensor for device %s", device_ieee.hex())
            msg1, msg2 = build_sensor_registration_payloads(device_ieee)
        else:
            self.debug("Unregistering external sensor, returning to internal")
            msg1, msg2 = build_sensor_unregistration_payloads(device_ieee)
        
        # Send both registration messages IN PARALLEL to beat sleepy device timeout
        try:
            self.debug("Sending BOTH registration messages in parallel...")
            self.debug("Message 1: %s", msg1.hex())
            self.debug("Message 2: %s", msg2.hex())
            
            # Fire both writes simultaneously - don't wait for first to complete
            results = await asyncio.gather(
                super().write_attributes(
                    {AQARA_FFF2: msg1},
                    manufacturer=MANUFACTURER_CODE
                ),
                super().write_attributes(
                    {AQARA_FFF2: msg2},
                    manufacturer=MANUFACTURER_CODE
                ),
                return_exceptions=True  # Don't fail if one times out
            )
            
            self.debug("Parallel registration results: %s", results)
            
            # Check results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.warning("Registration message %d failed: %s", i+1, result)
                else:
                    self.debug("Registration message %d succeeded: %s", i+1, result)
            
            self.debug("Sensor registration complete")
        except Exception as e:
            self.error("Failed to register sensor: %s", e)
            raise

    async def _handle_external_temperature(self, temperature: float) -> None:
        """
        Send an external temperature reading to the TRV.
        
        Args:
            temperature: Temperature in Celsius (0-55 range)
        """
        # Validate and clamp
        if not 0 <= temperature <= 55:
            self.warning(
                "External temperature %s out of range (0-55), clamping",
                temperature
            )
            temperature = max(0, min(55, temperature))
        
        self.debug("Writing external temperature: %s°C", temperature)
        
        payload = build_external_temp_payload(temperature)
        
        try:
            self.debug("Sending temperature payload: %s", payload.hex())
            await super().write_attributes(
                {AQARA_FFF2: payload},
                manufacturer=MANUFACTURER_CODE
            )
            self.debug("External temperature write completed")
        except Exception as e:
            self.error("Failed to write external temperature: %s", e)
            raise


# =============================================================================
# DEVICE DEFINITION
# =============================================================================

class AGL001(XiaomiCustomDevice):
    """Aqara E1 Radiator Thermostat with external sensor support."""

    signature = {
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
                    AqaraThermostatSpecificCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    AqaraThermostatSpecificCluster.cluster_id,
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
