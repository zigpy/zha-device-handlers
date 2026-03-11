"""Ubisys Cover J1 quirk."""

import asyncio
import logging
from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    DEGREE,
    PERCENTAGE,
    EntityPlatform,
    EntityType,
    UnitOfLength,
    UnitOfPower,
    UnitOfTime,
)
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl import (
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    AttributeWrittenEvent,
)
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    Status,
    WriteAttributesStatusRecord,
    ZCLAttributeDef,
)

from zhaquirks import LocalDataCluster
from zhaquirks.quirk_ids import SE_POLL_SUMMATION
from zhaquirks.ubisys import UbisysCluster, UbisysInputConfigCluster

_LOGGER = logging.getLogger(__name__)

_POLL_INTERVAL_S = 2  # seconds between operational_status polls
_MOTOR_TIMEOUT_S = 300  # 5 minutes
_BRIEF_MOVE_DURATION_S = 5  # auto-calibration: seconds to move down before stopping
_AC_FREQUENCY_HZ = 50  # steps are measured in full AC waves
_SECONDS_PER_STEP = 1 / _AC_FREQUENCY_HZ


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysWindowCovering(CustomCluster, WindowCovering):
    """WindowCovering with ubisys manufacturer-specific calibration attributes.

    The device has writable versions of standard read-only attributes at the
    same IDs but with manufacturer code 0x10F2. These are used during
    calibration to configure the cover type, limits, and step counts.
    """

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Extended WindowCovering attributes for ubisys calibration."""

        # Standard attribute missing from WindowCovering AttributeDefs (R6 draft attr)
        operational_status: Final = ZCLAttributeDef(
            id=0x000A, type=t.bitmap8, access="rp"
        )
        # Writable versions of standard attributes (same IDs, manufacturer code 0x10F2)
        window_covering_type_config: Final = ZCLAttributeDef(
            id=0x0000, type=t.enum8, manufacturer_code=0x10F2
        )
        config_status_config: Final = ZCLAttributeDef(
            id=0x0007, type=t.bitmap8, manufacturer_code=0x10F2
        )
        installed_open_limit_lift_config: Final = ZCLAttributeDef(
            id=0x0010, type=t.uint16_t, manufacturer_code=0x10F2
        )
        installed_closed_limit_lift_config: Final = ZCLAttributeDef(
            id=0x0011, type=t.uint16_t, manufacturer_code=0x10F2
        )
        installed_open_limit_tilt_config: Final = ZCLAttributeDef(
            id=0x0012, type=t.uint16_t, manufacturer_code=0x10F2
        )
        installed_closed_limit_tilt_config: Final = ZCLAttributeDef(
            id=0x0013, type=t.uint16_t, manufacturer_code=0x10F2
        )
        # Manufacturer-specific calibration attributes
        turnaround_guard_time: Final = ZCLAttributeDef(
            id=0x1000, type=t.uint8_t, manufacturer_code=0x10F2
        )
        lift_to_tilt_transition_steps: Final = ZCLAttributeDef(
            id=0x1001, type=t.uint16_t, manufacturer_code=0x10F2
        )
        total_steps: Final = ZCLAttributeDef(
            id=0x1002, type=t.uint16_t, manufacturer_code=0x10F2
        )
        lift_to_tilt_transition_steps_2: Final = ZCLAttributeDef(
            id=0x1003, type=t.uint16_t, manufacturer_code=0x10F2
        )
        total_steps_2: Final = ZCLAttributeDef(
            id=0x1004, type=t.uint16_t, manufacturer_code=0x10F2
        )
        additional_steps: Final = ZCLAttributeDef(
            id=0x1005, type=t.uint8_t, manufacturer_code=0x10F2
        )
        inactive_power_threshold: Final = ZCLAttributeDef(
            id=0x1006, type=t.uint16_t, manufacturer_code=0x10F2
        )
        startup_steps: Final = ZCLAttributeDef(
            id=0x1007, type=t.uint16_t, manufacturer_code=0x10F2
        )

    # Maps manufacturer-specific config attr names to standard ZCLAttributeDefs.
    # After writing a config attr, the standard attr cache is updated to match.
    # Note: cannot use AttributeDefs.*.name here — .name is None at class definition time.
    _CONFIG_TO_STANDARD: dict[str, ZCLAttributeDef] = {
        "window_covering_type_config": WindowCovering.AttributeDefs.window_covering_type,
        "config_status_config": WindowCovering.AttributeDefs.config_status,
        "installed_open_limit_lift_config": WindowCovering.AttributeDefs.installed_open_limit_lift,
        "installed_closed_limit_lift_config": WindowCovering.AttributeDefs.installed_closed_limit_lift,
        "installed_open_limit_tilt_config": WindowCovering.AttributeDefs.installed_open_limit_tilt,
        "installed_closed_limit_tilt_config": WindowCovering.AttributeDefs.installed_closed_limit_tilt,
    }

    def __init__(self, *args, **kwargs):
        """Init and register event handler for config-to-standard sync."""
        super().__init__(*args, **kwargs)
        self.on_event(AttributeWrittenEvent.event_type, self._handle_config_attr_sync)
        self.on_event(AttributeReportedEvent.event_type, self._handle_config_attr_sync)
        self.on_event(AttributeUpdatedEvent.event_type, self._handle_config_attr_sync)

    def _handle_config_attr_sync(
        self,
        event: AttributeWrittenEvent | AttributeReportedEvent | AttributeUpdatedEvent,
    ) -> None:
        """Sync standard attribute cache when a config attribute changes."""
        if isinstance(event, AttributeWrittenEvent) and event.status != Status.SUCCESS:
            return
        if (std_attr := self._CONFIG_TO_STANDARD.get(event.attribute_name)) is not None:
            self._update_attribute(std_attr, event.value)


class UbisysJ1InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the J1.

    EP2 -> EP1 with WindowCovering self-binding.
    Only detached mode is exposed (input_mode templates are OnOff-based
    and don't apply to cover commands).
    """

    BIND_CLUSTERS: list[int] = [WindowCovering.cluster_id]


class CalibrationState(t.enum8):
    """Auto-calibration progress state."""

    Idle = 0
    Moving_to_top = 1
    Writing_defaults = 2
    Entering_calibration = 3
    Moving_down = 4
    Detecting_upper_limit = 5
    Counting_open_to_close = 6
    Counting_close_to_open = 7
    Exiting_calibration = 8
    Complete = 9
    Failed = 10


class UbisysJ1CalibrationCluster(LocalDataCluster):
    """Virtual cluster for J1 calibration actions.

    - prepare_calibration: resets calibration attributes to defaults (Step 2)
    - run_calibration: runs the full auto-calibration sequence (Steps 1-9)
    """

    cluster_id = 0xFBFE
    name = "Ubisys J1 Calibration"
    ep_attribute = "ubisys_j1_calibration"

    class AttributeDefs(BaseAttributeDefs):
        """Calibration action attributes."""

        prepare_calibration: Final = ZCLAttributeDef(id=0x0000, type=t.Bool)
        run_calibration: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        enter_calibration_mode: Final = ZCLAttributeDef(id=0x0002, type=t.Bool)
        exit_calibration_mode: Final = ZCLAttributeDef(id=0x0003, type=t.Bool)
        calibration_state: Final = ZCLAttributeDef(id=0x0004, type=CalibrationState)

    def __init__(self, *args, **kwargs):
        """Init with calibration state set to Idle."""
        super().__init__(*args, **kwargs)
        self._update_attribute(
            self.AttributeDefs.calibration_state, CalibrationState.Idle
        )

    def _set_state(self, state: CalibrationState) -> None:
        """Update the calibration state attribute."""
        _LOGGER.debug("ubisys J1: Calibration state -> %s", state.name)
        self._update_attribute(self.AttributeDefs.calibration_state, state)

    async def _write_preparation_defaults(self) -> None:
        """Write calibration preparation defaults to the WindowCovering cluster."""
        wc = self.endpoint.device.endpoints[1].window_covering
        attrs = UbisysWindowCovering.AttributeDefs
        await wc.write_attributes(
            {
                attrs.installed_open_limit_lift_config: 0x0000,
                attrs.installed_closed_limit_lift_config: 0x00F0,
                attrs.installed_open_limit_tilt_config: 0x0000,
                attrs.installed_closed_limit_tilt_config: 0x0384,
                attrs.lift_to_tilt_transition_steps: 0xFFFF,
                attrs.total_steps: 0xFFFF,
                attrs.lift_to_tilt_transition_steps_2: 0xFFFF,
                attrs.total_steps_2: 0xFFFF,
            }
        )

    async def _read_calibration_attributes(self) -> None:
        """Read all calibration attributes from the device."""
        wc = self.endpoint.device.endpoints[1].window_covering
        attrs = UbisysWindowCovering.AttributeDefs
        await wc.read_attributes(
            [
                attrs.window_covering_type_config,
                attrs.config_status_config,
                attrs.installed_open_limit_lift_config,
                attrs.installed_closed_limit_lift_config,
                attrs.installed_open_limit_tilt_config,
                attrs.installed_closed_limit_tilt_config,
                attrs.lift_to_tilt_transition_steps,
                attrs.total_steps,
                attrs.lift_to_tilt_transition_steps_2,
                attrs.total_steps_2,
                attrs.additional_steps,
                attrs.inactive_power_threshold,
                attrs.startup_steps,
                attrs.turnaround_guard_time,
            ]
        )

    async def _wait_until_stopped(self) -> None:
        """Poll operational_status until the motor stops.

        Raises TimeoutError if the motor doesn't stop within _MOTOR_TIMEOUT_S.
        """
        wc = self.endpoint.device.endpoints[1].window_covering
        attr = UbisysWindowCovering.AttributeDefs.operational_status
        elapsed = 0
        while True:
            await asyncio.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S
            await wc.read_attributes([attr])
            status = wc.get_cached_value(attr) or 0
            _LOGGER.debug("ubisys J1: operational_status=0x%02X (%ds)", status, elapsed)
            if status == 0:
                break
            if elapsed >= _MOTOR_TIMEOUT_S:
                raise TimeoutError(f"Motor did not stop within {_MOTOR_TIMEOUT_S}s")
        await asyncio.sleep(_POLL_INTERVAL_S)

    async def _set_calibration_mode(self, enable: bool) -> None:
        """Set or clear the calibration bit in window_covering_mode."""
        wc = self.endpoint.device.endpoints[1].window_covering
        mode_attr = WindowCovering.AttributeDefs.window_covering_mode
        await wc.read_attributes([mode_attr])
        current_mode = wc.get_cached_value(mode_attr) or 0
        if enable:
            new_mode = (
                current_mode | WindowCovering.WindowCoveringMode.Run_in_calibration_mode
            )
        else:
            new_mode = (
                current_mode
                & ~WindowCovering.WindowCoveringMode.Run_in_calibration_mode
            )
        await wc.write_attributes({mode_attr: new_mode})
        await asyncio.sleep(_POLL_INTERVAL_S)

    async def _run_calibration(self) -> None:
        """Run the full auto-calibration sequence (Steps 1-9)."""
        wc = self.endpoint.device.endpoints[1].window_covering

        try:
            # Cancel any active calibration
            self._set_state(CalibrationState.Moving_to_top)
            await self._set_calibration_mode(False)

            # Move to top position for a good starting point
            await wc.up_open()
            await self._wait_until_stopped()

            # Write preparation defaults (Step 2)
            self._set_state(CalibrationState.Writing_defaults)
            await self._write_preparation_defaults()

            # Enter calibration mode (Step 3)
            self._set_state(CalibrationState.Entering_calibration)
            await self._set_calibration_mode(True)

            # Move down briefly, then stop (Step 4)
            self._set_state(CalibrationState.Moving_down)
            await wc.down_close()
            await asyncio.sleep(_BRIEF_MOVE_DURATION_S)
            await wc.stop()
            await asyncio.sleep(_POLL_INTERVAL_S)

            # Move up to detect upper limit (Step 5)
            self._set_state(CalibrationState.Detecting_upper_limit)
            await wc.up_open()
            await self._wait_until_stopped()

            # Move down to count steps open -> close (Step 6)
            self._set_state(CalibrationState.Counting_open_to_close)
            await wc.down_close()
            await self._wait_until_stopped()

            # Move up to count steps close -> open (Step 7)
            self._set_state(CalibrationState.Counting_close_to_open)
            await wc.up_open()
            await self._wait_until_stopped()

            # Exit calibration mode (Step 9)
            self._set_state(CalibrationState.Exiting_calibration)
            await self._set_calibration_mode(False)

            self._set_state(CalibrationState.Complete)
        except Exception:
            _LOGGER.exception("ubisys J1: Auto-calibration failed")
            self._set_state(CalibrationState.Failed)
            raise
        finally:
            # Re-read calibration attributes so HA entities reflect the new values.
            # Reading the manufacturer-specific attrs also triggers the
            # config-to-standard sync via _handle_config_attr_sync.
            await self._read_calibration_attributes()

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Handle calibration action attributes."""
        for attr in attributes:
            attr_def = self.find_attribute(attr)

            if attr_def == self.AttributeDefs.prepare_calibration:
                self._set_state(CalibrationState.Idle)
                await self._write_preparation_defaults()
            elif attr_def == self.AttributeDefs.run_calibration:
                self.create_catching_task(self._run_calibration())
            elif attr_def == self.AttributeDefs.enter_calibration_mode:
                await self._set_calibration_mode(True)
            elif attr_def == self.AttributeDefs.exit_calibration_mode:
                await self._set_calibration_mode(False)
            else:
                continue
            return [[WriteAttributesStatusRecord(Status.SUCCESS)]]

        return await super().write_attributes(attributes, manufacturer, **kwargs)


(
    QuirkBuilder(manufacturer="ubisys", model="J1 (5502)")
    .applies_to(manufacturer="ubisys", model="J1-R (5602)")
    .replaces(UbisysCluster, endpoint_id=232)
    .replaces(UbisysWindowCovering, endpoint_id=1)
    .enum(
        attribute_name=UbisysWindowCovering.AttributeDefs.window_covering_type_config.name,
        enum_class=WindowCovering.WindowCoveringType,
        cluster_id=UbisysWindowCovering.cluster_id,
        translation_key="window_covering_type",
        fallback_name="Window covering type",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.inactive_power_threshold.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65.535,
        step=0.001,
        multiplier=0.001,
        unit=UnitOfPower.WATT,
        mode="box",
        translation_key="inactive_power_threshold",
        fallback_name="Inactive power threshold",
    )
    # --- Installed limits (calibration) ---
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.installed_open_limit_lift_config.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        unit=UnitOfLength.CENTIMETERS,
        mode="box",
        device_class=NumberDeviceClass.DISTANCE,
        translation_key="open_limit_lift",
        fallback_name="Open limit lift",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.installed_closed_limit_lift_config.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        unit=UnitOfLength.CENTIMETERS,
        mode="box",
        device_class=NumberDeviceClass.DISTANCE,
        translation_key="closed_limit_lift",
        fallback_name="Closed limit lift",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.installed_open_limit_tilt_config.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=6553.5,
        step=0.1,
        multiplier=0.1,
        unit=DEGREE,
        mode="box",
        translation_key="open_limit_tilt",
        fallback_name="Open limit tilt",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.installed_closed_limit_tilt_config.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=6553.5,
        step=0.1,
        multiplier=0.1,
        unit=DEGREE,
        mode="box",
        translation_key="closed_limit_tilt",
        fallback_name="Closed limit tilt",
    )
    # --- Step counts (calibration, measured in full AC waves) ---
    # Displayed in seconds assuming 50 Hz AC frequency (0.02s per step)
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.lift_to_tilt_transition_steps.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535 * _SECONDS_PER_STEP,
        step=_SECONDS_PER_STEP,
        multiplier=_SECONDS_PER_STEP,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="tilt_turn_time_open_to_close",
        fallback_name="Tilt turn time (open to close)",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.total_steps.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535 * _SECONDS_PER_STEP,
        step=_SECONDS_PER_STEP,
        multiplier=_SECONDS_PER_STEP,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="travel_time_open_to_close",
        fallback_name="Travel time (open to close)",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.lift_to_tilt_transition_steps_2.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535 * _SECONDS_PER_STEP,
        step=_SECONDS_PER_STEP,
        multiplier=_SECONDS_PER_STEP,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="tilt_turn_time_close_to_open",
        fallback_name="Tilt turn time (close to open)",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.total_steps_2.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535 * _SECONDS_PER_STEP,
        step=_SECONDS_PER_STEP,
        multiplier=_SECONDS_PER_STEP,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="travel_time_close_to_open",
        fallback_name="Travel time (close to open)",
    )
    # --- Other calibration settings ---
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.turnaround_guard_time.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0.5,
        max_value=12.7,
        step=0.05,
        multiplier=0.05,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="turnaround_guard_time",
        fallback_name="Turnaround guard time",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.additional_steps.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        mode="box",
        translation_key="additional_steps",
        fallback_name="Additional steps",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.startup_steps.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535 * _SECONDS_PER_STEP,
        step=_SECONDS_PER_STEP,
        multiplier=_SECONDS_PER_STEP,
        unit=UnitOfTime.SECONDS,
        mode="box",
        device_class=NumberDeviceClass.DURATION,
        translation_key="startup_time",
        fallback_name="Startup time",
    )
    # --- Calibration mode buttons ---
    .adds(UbisysJ1CalibrationCluster)
    .write_attr_button(
        attribute_name=UbisysJ1CalibrationCluster.AttributeDefs.prepare_calibration.name,
        attribute_value=True,
        cluster_id=UbisysJ1CalibrationCluster.cluster_id,
        translation_key="prepare_manual_calibration",
        fallback_name="Prepare manual calibration",
    )
    .write_attr_button(
        attribute_name=UbisysJ1CalibrationCluster.AttributeDefs.run_calibration.name,
        attribute_value=True,
        cluster_id=UbisysJ1CalibrationCluster.cluster_id,
        translation_key="run_auto_calibration",
        fallback_name="Run auto-calibration",
    )
    .write_attr_button(
        attribute_name=UbisysJ1CalibrationCluster.AttributeDefs.enter_calibration_mode.name,
        attribute_value=True,
        cluster_id=UbisysJ1CalibrationCluster.cluster_id,
        translation_key="enter_calibration_mode",
        fallback_name="Enter calibration mode",
    )
    .write_attr_button(
        attribute_name=UbisysJ1CalibrationCluster.AttributeDefs.exit_calibration_mode.name,
        attribute_value=True,
        cluster_id=UbisysJ1CalibrationCluster.cluster_id,
        translation_key="exit_calibration_mode",
        fallback_name="Exit calibration mode",
    )
    .enum(
        attribute_name=UbisysJ1CalibrationCluster.AttributeDefs.calibration_state.name,
        enum_class=CalibrationState,
        cluster_id=UbisysJ1CalibrationCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="auto_calibration_state",
        fallback_name="Auto-calibration state",
    )
    .adds(UbisysJ1InputConfigCluster)
    .switch(
        attribute_name=UbisysJ1InputConfigCluster.AttributeDefs.detached.name,
        cluster_id=UbisysJ1InputConfigCluster.cluster_id,
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .replaces(UbisysElectricalMeasurement, endpoint_id=3)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="3-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .add_to_registry()
)
