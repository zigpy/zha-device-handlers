"""Tuya noise sensor."""

import time
from typing import Any

from zigpy import types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfSoundPressure,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID, TUYA_QUERY_DATA, TuyaCommand
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

DP_SOUND_PRESSURE = 1
DP_NOISE_LEVEL = 8
DP_NOISE_STATE = 101


class TuyaNoiseMCUCluster(TuyaMCUCluster):
    """Tuya MCU cluster that requests the sound pressure on state changes.

    The device does not reliably report the sound pressure DP on its own,
    only in response to a data query. Query it whenever the noise level or
    detection state changes.
    """

    QUERY_TRIGGER_DPS = (DP_NOISE_LEVEL, DP_NOISE_STATE)
    MIN_QUERY_INTERVAL = 5  # seconds

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init."""
        super().__init__(*args, **kwargs)
        self._last_trigger_values: dict[int, int] = {}
        self._last_query = 0.0

    def handle_get_data(self, command: TuyaCommand) -> foundation.Status:
        """Handle a report, then query the sound pressure if needed."""
        changed = False
        has_sound_pressure = False
        for record in command.datapoints:
            if record.dp == DP_SOUND_PRESSURE:
                has_sound_pressure = True
            elif record.dp in self.QUERY_TRIGGER_DPS:
                value = int(record.data.payload)
                if self._last_trigger_values.get(record.dp) != value:
                    self._last_trigger_values[record.dp] = value
                    changed = True

        status = super().handle_get_data(command)

        # Query responses include the sound pressure, so they never re-trigger
        now = time.monotonic()
        if (
            changed
            and not has_sound_pressure
            and now - self._last_query >= self.MIN_QUERY_INTERVAL
        ):
            self._last_query = now
            self.create_catching_task(self.command(TUYA_QUERY_DATA))

        return status

    # The base class aliases these to its own handle_get_data
    handle_set_data_response = handle_get_data
    handle_active_status_report = handle_get_data


class TuyaNoiseLevel(t.enum8):
    """Tuya noise level."""

    Quiet = 0x00
    Medium = 0x01
    Loud = 0x02


(
    TuyaQuirkBuilder("_TZE204_r6kfl9ta", "TS0601")  # ZY-N1 sound detector
    .tuya_sensor(
        dp_id=DP_SOUND_PRESSURE,
        attribute_name="sound_pressure",
        type=t.uint32_t,
        device_class=SensorDeviceClass.SOUND_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfSoundPressure.DECIBEL,
        entity_type=EntityType.STANDARD,
        fallback_name="Sound pressure",
    )
    .tuya_enum(
        dp_id=DP_NOISE_LEVEL,
        attribute_name="noise_level",
        enum_class=TuyaNoiseLevel,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Report,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="noise_level",
        fallback_name="Noise level",
    )
    # DP 101 reports 0 while noise is detected, higher values while quiet
    .tuya_dp_attribute(
        dp_id=DP_NOISE_STATE,
        attribute_name="noise_detected",
        type=t.Bool,
        converter=lambda x: x == 0,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Report,
    )
    .binary_sensor(
        attribute_name="noise_detected",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.SOUND,
        fallback_name="Noise detected",
    )
    # Medium level boundary, noise is detected above this level
    .tuya_number(
        dp_id=16,
        attribute_name="noise_threshold",
        type=t.uint32_t,
        device_class=NumberDeviceClass.SOUND_PRESSURE,
        unit=UnitOfSoundPressure.DECIBEL,
        min_value=0,
        max_value=120,
        step=1,
        translation_key="noise_threshold",
        fallback_name="Noise threshold",
    )
    # Loud level boundary
    .tuya_number(
        dp_id=20,
        attribute_name="loud_threshold",
        type=t.uint32_t,
        device_class=NumberDeviceClass.SOUND_PRESSURE,
        unit=UnitOfSoundPressure.DECIBEL,
        min_value=0,
        max_value=120,
        step=1,
        translation_key="loud_threshold",
        fallback_name="Loud threshold",
    )
    # Quiet time before noise detection clears
    .tuya_number(
        dp_id=22,
        attribute_name="fading_time",
        type=t.uint32_t,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=300,
        step=1,
        translation_key="fading_time",
        fallback_name="Fading time",
    )
    # Sustained noise needed before detection
    .tuya_number(
        dp_id=103,
        attribute_name="detection_delay",
        type=t.uint32_t,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=300,
        step=1,
        translation_key="detection_delay",
        fallback_name="Detection delay",
    )
    # Fetch initial values on startup
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry(replacement_cluster=TuyaNoiseMCUCluster)
)
