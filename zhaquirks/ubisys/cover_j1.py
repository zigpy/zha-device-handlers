"""Ubisys Cover J1 quirk."""

import asyncio
import logging
from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import (
    DEGREE,
    PERCENTAGE,
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


_LOGGER = logging.getLogger(__name__)

_CALIBRATION_MODE_BIT = 0x02
_POLL_INTERVAL_S = 2
_MOTOR_TIMEOUT_S = 300


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
            if (wc.get_cached_value(attr) or 0) == 0:
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
            new_mode = current_mode | _CALIBRATION_MODE_BIT
        else:
            new_mode = current_mode & ~_CALIBRATION_MODE_BIT
        await wc.write_attributes({mode_attr: new_mode})
        await asyncio.sleep(_POLL_INTERVAL_S)

    async def _run_calibration(self) -> None:
        """Run the full auto-calibration sequence (Steps 1-9)."""
        wc = self.endpoint.device.endpoints[1].window_covering
        _LOGGER.warning("ubisys J1: Calibration starting")

        # Cancel any active calibration
        await self._set_calibration_mode(False)

        # Move to top position for a good starting point
        _LOGGER.warning("ubisys J1: Moving to top position")
        await wc.up_open()
        await self._wait_until_stopped()

        # Write preparation defaults (Step 2)
        _LOGGER.warning("ubisys J1: Writing preparation defaults")
        await self._write_preparation_defaults()

        # Enter calibration mode (Step 3)
        _LOGGER.warning("ubisys J1: Entering calibration mode")
        await self._set_calibration_mode(True)

        # Move down briefly, then stop (Step 4)
        _LOGGER.warning("ubisys J1: Moving down briefly")
        await wc.down_close()
        await asyncio.sleep(5)
        await wc.stop()
        await asyncio.sleep(_POLL_INTERVAL_S)

        # Move up to detect upper limit (Step 5)
        _LOGGER.warning("ubisys J1: Moving up to detect upper limit")
        await wc.up_open()
        await self._wait_until_stopped()

        # Move down to count steps open→close (Step 6)
        _LOGGER.warning("ubisys J1: Moving down to count steps (open to close)")
        await wc.down_close()
        await self._wait_until_stopped()

        # Move up to count steps close→open (Step 7)
        _LOGGER.warning("ubisys J1: Moving up to count steps (close to open)")
        await wc.up_open()
        await self._wait_until_stopped()

        # Exit calibration mode (Step 9)
        _LOGGER.warning("ubisys J1: Exiting calibration mode")
        await self._set_calibration_mode(False)

        # Re-read calibration attributes so HA entities reflect the new values.
        # Reading the manufacturer-specific attrs also triggers the config-to-standard
        # sync via _handle_config_attr_sync.
        _LOGGER.warning("ubisys J1: Reading back calibration results")
        await self._read_calibration_attributes()

        _LOGGER.warning("ubisys J1: Calibration complete")

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Handle calibration action attributes."""
        for attr in attributes:
            attr_def = self.find_attribute(attr)
            if attr_def == self.AttributeDefs.prepare_calibration:
                await self._write_preparation_defaults()
                return [[WriteAttributesStatusRecord(Status.SUCCESS)]]
            if attr_def == self.AttributeDefs.run_calibration:
                self.create_catching_task(self._run_calibration())
                return [[WriteAttributesStatusRecord(Status.SUCCESS)]]
            if attr_def == self.AttributeDefs.enter_calibration_mode:
                await self._set_calibration_mode(True)
                return [[WriteAttributesStatusRecord(Status.SUCCESS)]]
            if attr_def == self.AttributeDefs.exit_calibration_mode:
                await self._set_calibration_mode(False)
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
        translation_key="installed_open_limit_lift",
        fallback_name="Installed open limit lift",
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
        translation_key="installed_closed_limit_lift",
        fallback_name="Installed closed limit lift",
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
        translation_key="installed_open_limit_tilt",
        fallback_name="Installed open limit tilt",
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
        translation_key="installed_closed_limit_tilt",
        fallback_name="Installed closed limit tilt",
    )
    # --- Step counts (calibration, measured in full AC waves) ---
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.lift_to_tilt_transition_steps.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="lift_to_tilt_transition_steps",
        fallback_name="Tilt full turn steps (open to close)",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.total_steps.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="total_steps",
        fallback_name="Total steps (open to close)",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.lift_to_tilt_transition_steps_2.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="lift_to_tilt_transition_steps_2",
        fallback_name="Tilt full turn steps (close to open)",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.total_steps_2.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        translation_key="total_steps_2",
        fallback_name="Total steps (close to open)",
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
        max_value=65535,
        step=1,
        mode="box",
        translation_key="startup_steps",
        fallback_name="Startup steps",
    )
    # --- Calibration mode buttons ---
    .adds(UbisysJ1CalibrationCluster)
    .write_attr_button(
        attribute_name=UbisysJ1CalibrationCluster.AttributeDefs.prepare_calibration.name,
        attribute_value=True,
        cluster_id=UbisysJ1CalibrationCluster.cluster_id,
        translation_key="prepare_calibration",
        fallback_name="Prepare calibration",
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
