"""Inovelli quirk builder with shared entity definitions.

Inovelli devices expose a large, mostly shared set of configuration entities on
their manufacturer-specific cluster (``0xFC31``). These used to be hard-coded in
the ZHA library; this builder ports them to quirks v2 so each device file only
needs a single call per entity.

``unique_id`` preservation: ZHA-native entities include the cluster id in their
``unique_id`` (``{ieee}-{endpoint}-{cluster_id}-{suffix}``), but quirks v2
entities do not (``{ieee}-{endpoint}-{suffix}``). To keep the exact unique_ids
the ZHA library produced, every entity here is created with
``unique_id_suffix="64561-<attribute>"`` (``64561 == 0xFC31``). The internal
temperature sensor had no ZHA suffix, so its suffix is the bare cluster id.
"""

from enum import Enum
from typing import Self

import zigpy.types as t

from zhaquirks.builder import (
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.inovelli import InovelliCluster

INOVELLI_CLUSTER_ID = InovelliCluster.cluster_id  # 0xFC31 == 64561
INOVELLI_MMWAVE_CLUSTER_ID = 0xFC32  # 64562, VZM32-SN mmWave cluster


class InovelliOutputMode(t.enum1):
    """Inovelli output mode."""

    Dimmer = 0x00
    OnOff = 0x01


class InovelliSwitchType(t.enum8):
    """Inovelli switch mode."""

    Single_Pole = 0x00
    Three_Way_Dumb = 0x01
    Three_Way_AUX = 0x02
    Single_Pole_Full_Sine = 0x03


class InovelliFanSwitchType(t.enum1):
    """Inovelli fan switch mode."""

    Load_Only = 0x00
    Three_Way_AUX = 0x01


class InovelliLedScalingMode(t.enum1):
    """Inovelli led mode."""

    VZM31SN = 0x00
    LZW31SN = 0x01


class InovelliFanLedScalingMode(t.enum8):
    """Inovelli fan led mode."""

    VZM31SN = 0x00
    Grade_1 = 0x01
    Grade_2 = 0x02
    Grade_3 = 0x03
    Grade_4 = 0x04
    Grade_5 = 0x05
    Grade_6 = 0x06
    Grade_7 = 0x07
    Grade_8 = 0x08
    Grade_9 = 0x09
    Adaptive = 0x0A


class InovelliNonNeutralOutput(t.enum1):
    """Inovelli non neutral output selection."""

    Low = 0x00
    High = 0x01


class InovelliDimmingMode(t.enum1):
    """Inovelli dimming mode selection."""

    LeadingEdge = 0x00
    TrailingEdge = 0x01


class InovelliOverheatedState(t.enum8):
    """Inovelli overheat protection state."""

    Normal = 0x00
    Overheated = 0x01


class InovelliVZM32SwitchType(t.enum8):
    """Inovelli VZM32-SN switch type."""

    Single_Pole = 0x00
    Three_Way_AUX = 0x01


class InovelliLightOnPresenceBehavior(t.enum8):
    """Inovelli light on presence behavior."""

    Disabled = 0x00
    On_When_Occupied_Off_When_Unoccupied = 0x01
    Off_When_Vacant = 0x02
    On_When_Occupied = 0x03
    On_When_Vacant_Off_When_Occupied = 0x04
    On_When_Vacant = 0x05
    Off_When_Occupied = 0x06


class InovelliMmwaveRoomSizePreset(t.enum8):
    """Inovelli mmWave room size preset."""

    Custom = 0x00
    X_Small = 0x01
    Small = 0x02
    Medium = 0x03
    Large = 0x04
    X_Large = 0x05


class InovelliMmwaveSensitivity(t.enum8):
    """Inovelli mmWave detection sensitivity."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


class InovelliMmwaveTargetSpeed(t.enum8):
    """Inovelli mmWave target speed."""

    Low = 0x00
    Medium = 0x01
    Fast = 0x02


class InovelliQuirkBuilder(QuirkBuilder):
    """``QuirkBuilder`` subclass exposing Inovelli entities.

    Each ``inovelli_*`` method adds a single entity on the Inovelli manufacturer
    cluster (``0xFC31``) or, for the VZM32-SN mmWave entities, the mmWave cluster
    (``0xFC32``). Entities ported from the ZHA library mirror the metadata and
    ``unique_id`` ZHA previously produced (see module docstring); the mmWave
    entities are new and use the same ``<cluster_id>-<attribute>`` suffix scheme.
    """

    def _inovelli_suffix(
        self,
        attribute_name: str | None = None,
        *,
        cluster_id: int = INOVELLI_CLUSTER_ID,
    ) -> str:
        """Return the unique_id suffix matching the old ZHA-native entity.

        ZHA-native entities included the cluster id in their unique_id; replicate
        that here so existing entities are preserved (and stay consistent for new
        entities on the mmWave cluster).
        """
        if attribute_name is None:
            return f"{cluster_id}"
        return f"{cluster_id}-{attribute_name}"

    def _inovelli_number(
        self,
        attribute_name: str,
        *,
        min_value: float,
        max_value: float,
        fallback_name: str,
        endpoint_id: int = 1,
        cluster_id: int = INOVELLI_CLUSTER_ID,
    ) -> Self:
        return self.number(
            attribute_name=attribute_name,
            cluster_id=cluster_id,
            endpoint_id=endpoint_id,
            min_value=min_value,
            max_value=max_value,
            unique_id_suffix=self._inovelli_suffix(
                attribute_name, cluster_id=cluster_id
            ),
            translation_key=attribute_name,
            fallback_name=fallback_name,
        )

    def _inovelli_switch(
        self,
        attribute_name: str,
        *,
        fallback_name: str,
        translation_key: str | None = None,
        endpoint_id: int = 1,
        cluster_id: int = INOVELLI_CLUSTER_ID,
    ) -> Self:
        return self.switch(
            attribute_name=attribute_name,
            cluster_id=cluster_id,
            endpoint_id=endpoint_id,
            unique_id_suffix=self._inovelli_suffix(
                attribute_name, cluster_id=cluster_id
            ),
            translation_key=translation_key or attribute_name,
            fallback_name=fallback_name,
        )

    def _inovelli_select(
        self,
        attribute_name: str,
        enum_class: type[Enum],
        *,
        fallback_name: str,
        endpoint_id: int = 1,
        cluster_id: int = INOVELLI_CLUSTER_ID,
    ) -> Self:
        return self.enum(
            attribute_name=attribute_name,
            enum_class=enum_class,
            cluster_id=cluster_id,
            endpoint_id=endpoint_id,
            unique_id_suffix=self._inovelli_suffix(
                attribute_name, cluster_id=cluster_id
            ),
            translation_key=attribute_name,
            fallback_name=fallback_name,
        )

    # --- number entities -------------------------------------------------

    def inovelli_remote_dimming_up_speed(self, endpoint_id: int = 1) -> Self:
        """Add the remote dimming up speed number entity."""
        return self._inovelli_number(
            "dimming_speed_up_remote",
            min_value=0,
            max_value=126,
            fallback_name="Remote dimming up speed",
            endpoint_id=endpoint_id,
        )

    def inovelli_local_dimming_up_speed(self, endpoint_id: int = 1) -> Self:
        """Add the local dimming up speed number entity."""
        return self._inovelli_number(
            "dimming_speed_up_local",
            min_value=0,
            max_value=127,
            fallback_name="Local dimming up speed",
            endpoint_id=endpoint_id,
        )

    def inovelli_remote_dimming_down_speed(self, endpoint_id: int = 1) -> Self:
        """Add the remote dimming down speed number entity."""
        return self._inovelli_number(
            "dimming_speed_down_remote",
            min_value=0,
            max_value=127,
            fallback_name="Remote dimming down speed",
            endpoint_id=endpoint_id,
        )

    def inovelli_local_dimming_down_speed(self, endpoint_id: int = 1) -> Self:
        """Add the local dimming down speed number entity."""
        return self._inovelli_number(
            "dimming_speed_down_local",
            min_value=0,
            max_value=127,
            fallback_name="Local dimming down speed",
            endpoint_id=endpoint_id,
        )

    def inovelli_local_ramp_rate_off_to_on(self, endpoint_id: int = 1) -> Self:
        """Add the off-to-on local ramp rate number entity."""
        return self._inovelli_number(
            "ramp_rate_off_to_on_local",
            min_value=0,
            max_value=127,
            fallback_name="Local ramp rate off to on",
            endpoint_id=endpoint_id,
        )

    def inovelli_remote_ramp_rate_off_to_on(self, endpoint_id: int = 1) -> Self:
        """Add the off-to-on remote ramp rate number entity."""
        return self._inovelli_number(
            "ramp_rate_off_to_on_remote",
            min_value=0,
            max_value=127,
            fallback_name="Remote ramp rate off to on",
            endpoint_id=endpoint_id,
        )

    def inovelli_local_ramp_rate_on_to_off(self, endpoint_id: int = 1) -> Self:
        """Add the on-to-off local ramp rate number entity."""
        return self._inovelli_number(
            "ramp_rate_on_to_off_local",
            min_value=0,
            max_value=127,
            fallback_name="Local ramp rate on to off",
            endpoint_id=endpoint_id,
        )

    def inovelli_remote_ramp_rate_on_to_off(self, endpoint_id: int = 1) -> Self:
        """Add the on-to-off remote ramp rate number entity."""
        return self._inovelli_number(
            "ramp_rate_on_to_off_remote",
            min_value=0,
            max_value=127,
            fallback_name="Remote ramp rate on to off",
            endpoint_id=endpoint_id,
        )

    def inovelli_button_delay(self, endpoint_id: int = 1) -> Self:
        """Add the button delay number entity."""
        return self._inovelli_number(
            "button_delay",
            min_value=0,
            max_value=9,
            fallback_name="Button delay",
            endpoint_id=endpoint_id,
        )

    def inovelli_minimum_load_dimming_level(self, endpoint_id: int = 1) -> Self:
        """Add the minimum load dimming level number entity."""
        return self._inovelli_number(
            "minimum_level",
            min_value=1,
            max_value=254,
            fallback_name="Minimum load dimming level",
            endpoint_id=endpoint_id,
        )

    def inovelli_maximum_load_dimming_level(self, endpoint_id: int = 1) -> Self:
        """Add the maximum load dimming level number entity."""
        return self._inovelli_number(
            "maximum_level",
            min_value=2,
            max_value=255,
            fallback_name="Maximum load dimming level",
            endpoint_id=endpoint_id,
        )

    def inovelli_auto_shutoff_timer(self, endpoint_id: int = 1) -> Self:
        """Add the automatic switch shutoff timer number entity."""
        return self._inovelli_number(
            "auto_off_timer",
            min_value=0,
            max_value=32767,
            fallback_name="Automatic switch shutoff timer",
            endpoint_id=endpoint_id,
        )

    def inovelli_local_default_level(self, endpoint_id: int = 1) -> Self:
        """Add the local default dimming level number entity."""
        return self._inovelli_number(
            "default_level_local",
            min_value=0,
            max_value=255,
            fallback_name="Local default dimming level",
            endpoint_id=endpoint_id,
        )

    def inovelli_remote_default_level(self, endpoint_id: int = 1) -> Self:
        """Add the remote default dimming level number entity."""
        return self._inovelli_number(
            "default_level_remote",
            min_value=0,
            max_value=255,
            fallback_name="Remote default dimming level",
            endpoint_id=endpoint_id,
        )

    def inovelli_startup_default_level(self, endpoint_id: int = 1) -> Self:
        """Add the start-up default dimming level number entity."""
        return self._inovelli_number(
            "state_after_power_restored",
            min_value=0,
            max_value=255,
            fallback_name="Start-up default dimming level",
            endpoint_id=endpoint_id,
        )

    def inovelli_quick_start_time(self, endpoint_id: int = 1) -> Self:
        """Add the fan quick start time number entity."""
        return self._inovelli_number(
            "quick_start_time",
            min_value=0,
            max_value=10,
            fallback_name="Quick start time",
            endpoint_id=endpoint_id,
        )

    def inovelli_load_level_indicator_timeout(self, endpoint_id: int = 1) -> Self:
        """Add the load level indicator timeout number entity."""
        return self._inovelli_number(
            "load_level_indicator_timeout",
            min_value=0,
            max_value=11,
            fallback_name="Load level indicator timeout",
            endpoint_id=endpoint_id,
        )

    def inovelli_default_all_led_on_color(self, endpoint_id: int = 1) -> Self:
        """Add the default all-LED on color number entity."""
        return self._inovelli_number(
            "led_color_when_on",
            min_value=0,
            max_value=255,
            fallback_name="Default all LED on color",
            endpoint_id=endpoint_id,
        )

    def inovelli_default_all_led_off_color(self, endpoint_id: int = 1) -> Self:
        """Add the default all-LED off color number entity."""
        return self._inovelli_number(
            "led_color_when_off",
            min_value=0,
            max_value=255,
            fallback_name="Default all LED off color",
            endpoint_id=endpoint_id,
        )

    def inovelli_default_all_led_on_intensity(self, endpoint_id: int = 1) -> Self:
        """Add the default all-LED on intensity number entity."""
        return self._inovelli_number(
            "led_intensity_when_on",
            min_value=0,
            max_value=100,
            fallback_name="Default all LED on intensity",
            endpoint_id=endpoint_id,
        )

    def inovelli_default_all_led_off_intensity(self, endpoint_id: int = 1) -> Self:
        """Add the default all-LED off intensity number entity."""
        return self._inovelli_number(
            "led_intensity_when_off",
            min_value=0,
            max_value=100,
            fallback_name="Default all LED off intensity",
            endpoint_id=endpoint_id,
        )

    def inovelli_double_tap_up_level(self, endpoint_id: int = 1) -> Self:
        """Add the double tap up level number entity."""
        return self._inovelli_number(
            "double_tap_up_level",
            min_value=2,
            max_value=254,
            fallback_name="Double tap up level",
            endpoint_id=endpoint_id,
        )

    def inovelli_double_tap_down_level(self, endpoint_id: int = 1) -> Self:
        """Add the double tap down level number entity."""
        return self._inovelli_number(
            "double_tap_down_level",
            min_value=0,
            max_value=254,
            fallback_name="Double tap down level",
            endpoint_id=endpoint_id,
        )

    # --- switch entities -------------------------------------------------

    def inovelli_invert_switch(self, endpoint_id: int = 1) -> Self:
        """Add the invert switch entity."""
        return self._inovelli_switch(
            "invert_switch",
            fallback_name="Invert switch",
            endpoint_id=endpoint_id,
        )

    def inovelli_smart_bulb_mode(self, endpoint_id: int = 1) -> Self:
        """Add the smart bulb mode switch entity."""
        return self._inovelli_switch(
            "smart_bulb_mode",
            fallback_name="Smart bulb mode",
            endpoint_id=endpoint_id,
        )

    def inovelli_smart_fan_mode(self, endpoint_id: int = 1) -> Self:
        """Add the smart fan mode switch entity."""
        return self._inovelli_switch(
            "smart_fan_mode",
            fallback_name="Smart fan mode",
            endpoint_id=endpoint_id,
        )

    def inovelli_double_tap_up_enabled(self, endpoint_id: int = 1) -> Self:
        """Add the double tap up enabled switch entity."""
        return self._inovelli_switch(
            "double_tap_up_enabled",
            fallback_name="Double tap up enabled",
            endpoint_id=endpoint_id,
        )

    def inovelli_double_tap_down_enabled(self, endpoint_id: int = 1) -> Self:
        """Add the double tap down enabled switch entity."""
        return self._inovelli_switch(
            "double_tap_down_enabled",
            fallback_name="Double tap down enabled",
            endpoint_id=endpoint_id,
        )

    def inovelli_aux_switch_scenes(self, endpoint_id: int = 1) -> Self:
        """Add the aux switch scenes switch entity."""
        return self._inovelli_switch(
            "aux_switch_scenes",
            fallback_name="Aux switch scenes",
            endpoint_id=endpoint_id,
        )

    def inovelli_binding_off_to_on_sync_level(self, endpoint_id: int = 1) -> Self:
        """Add the binding off-to-on sync level switch entity."""
        return self._inovelli_switch(
            "binding_off_to_on_sync_level",
            fallback_name="Binding off to on sync level",
            endpoint_id=endpoint_id,
        )

    def inovelli_local_protection(self, endpoint_id: int = 1) -> Self:
        """Add the local protection switch entity."""
        return self._inovelli_switch(
            "local_protection",
            fallback_name="Local protection",
            endpoint_id=endpoint_id,
        )

    def inovelli_on_off_led_mode(self, endpoint_id: int = 1) -> Self:
        """Add the only-1-LED mode switch entity."""
        return self._inovelli_switch(
            "on_off_led_mode",
            translation_key="one_led_mode",
            fallback_name="Only 1 LED mode",
            endpoint_id=endpoint_id,
        )

    def inovelli_firmware_progress_led(self, endpoint_id: int = 1) -> Self:
        """Add the firmware progress LED switch entity."""
        return self._inovelli_switch(
            "firmware_progress_led",
            fallback_name="Firmware progress LED",
            endpoint_id=endpoint_id,
        )

    def inovelli_relay_click_in_on_off_mode(self, endpoint_id: int = 1) -> Self:
        """Add the disable relay click in on/off mode switch entity."""
        return self._inovelli_switch(
            "relay_click_in_on_off_mode",
            fallback_name="Disable relay click in on off mode",
            endpoint_id=endpoint_id,
        )

    def inovelli_disable_clear_notifications_double_tap(
        self, endpoint_id: int = 1
    ) -> Self:
        """Add the disable config 2x-tap-to-clear-notifications switch entity."""
        return self._inovelli_switch(
            "disable_clear_notifications_double_tap",
            fallback_name="Disable config 2x tap to clear notifications",
            endpoint_id=endpoint_id,
        )

    # --- select entities -------------------------------------------------

    def inovelli_output_mode(self, endpoint_id: int = 1) -> Self:
        """Add the output mode select entity."""
        return self._inovelli_select(
            "output_mode",
            InovelliOutputMode,
            fallback_name="Output mode",
            endpoint_id=endpoint_id,
        )

    def inovelli_switch_type(self, endpoint_id: int = 1) -> Self:
        """Add the (dimmer) switch type select entity."""
        return self._inovelli_select(
            "switch_type",
            InovelliSwitchType,
            fallback_name="Switch type",
            endpoint_id=endpoint_id,
        )

    def inovelli_fan_switch_type(self, endpoint_id: int = 1) -> Self:
        """Add the fan switch type select entity."""
        return self._inovelli_select(
            "switch_type",
            InovelliFanSwitchType,
            fallback_name="Switch type",
            endpoint_id=endpoint_id,
        )

    def inovelli_led_scaling_mode(self, endpoint_id: int = 1) -> Self:
        """Add the LED scaling mode select entity."""
        return self._inovelli_select(
            "led_scaling_mode",
            InovelliLedScalingMode,
            fallback_name="LED scaling mode",
            endpoint_id=endpoint_id,
        )

    def inovelli_fan_led_scaling_mode(self, endpoint_id: int = 1) -> Self:
        """Add the smart fan LED display levels select entity."""
        return self._inovelli_select(
            "smart_fan_led_display_levels",
            InovelliFanLedScalingMode,
            fallback_name="Smart fan LED display levels",
            endpoint_id=endpoint_id,
        )

    def inovelli_increased_non_neutral_output(self, endpoint_id: int = 1) -> Self:
        """Add the increased non-neutral output select entity."""
        return self._inovelli_select(
            "increased_non_neutral_output",
            InovelliNonNeutralOutput,
            fallback_name="Increased non-neutral output",
            endpoint_id=endpoint_id,
        )

    def inovelli_dimming_mode(self, endpoint_id: int = 1) -> Self:
        """Add the dimming mode (leading/trailing edge) select entity."""
        return self._inovelli_select(
            "leading_or_trailing_edge",
            InovelliDimmingMode,
            fallback_name="Dimming mode",
            endpoint_id=endpoint_id,
        )

    # --- sensor entities -------------------------------------------------

    def inovelli_internal_temperature(self, endpoint_id: int = 1) -> Self:
        """Add the internal temperature diagnostic sensor entity."""
        return self.sensor(
            attribute_name="internal_temp_monitor",
            cluster_id=INOVELLI_CLUSTER_ID,
            endpoint_id=endpoint_id,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfTemperature.CELSIUS,
            entity_type=EntityType.DIAGNOSTIC,
            unique_id_suffix=self._inovelli_suffix(),
            translation_key="internal_temp_monitor",
            fallback_name="Internal temperature",
        )

    def inovelli_overheated(self, endpoint_id: int = 1) -> Self:
        """Add the overheat protection diagnostic (enum) sensor entity."""
        return self.enum(
            attribute_name="overheated",
            enum_class=InovelliOverheatedState,
            cluster_id=INOVELLI_CLUSTER_ID,
            endpoint_id=endpoint_id,
            entity_platform=EntityPlatform.SENSOR,
            entity_type=EntityType.DIAGNOSTIC,
            unique_id_suffix=self._inovelli_suffix("overheated"),
            translation_key="overheated",
            fallback_name="Overheat protection",
        )

    # --- VZM32-SN specific entities (0xFC31) -----------------------------

    def inovelli_remote_protection(self, endpoint_id: int = 1):
        """Add the remote protection switch entity."""
        return self._inovelli_switch(
            "remote_protection",
            fallback_name="Remote protection",
            endpoint_id=endpoint_id,
        )

    def inovelli_vzm32_switch_type(self, endpoint_id: int = 1):
        """Add the VZM32-SN switch type select entity."""
        return self._inovelli_select(
            "switch_type",
            InovelliVZM32SwitchType,
            fallback_name="Switch type",
            endpoint_id=endpoint_id,
        )

    def inovelli_light_on_presence_behavior(self, endpoint_id: int = 1):
        """Add the light on presence behavior select entity."""
        return self._inovelli_select(
            "light_on_presence_behavior",
            InovelliLightOnPresenceBehavior,
            fallback_name="Light on presence behavior",
            endpoint_id=endpoint_id,
        )

    def inovelli_mmwave_room_size_preset(self, endpoint_id: int = 1):
        """Add the mmWave room size preset select entity."""
        return self._inovelli_select(
            "mmwave_room_size_preset",
            InovelliMmwaveRoomSizePreset,
            fallback_name="mmWave room size preset",
            endpoint_id=endpoint_id,
        )

    # --- VZM32-SN mmWave cluster entities (0xFC32) -----------------------

    def inovelli_mmwave_height_minimum_floor(self, endpoint_id: int = 1):
        """Add the mmWave minimum height (floor) number entity."""
        return self._inovelli_number(
            "mmwave_height_minimum_floor",
            min_value=-600,
            max_value=600,
            fallback_name="mmWave height minimum (floor)",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_height_maximum_ceiling(self, endpoint_id: int = 1):
        """Add the mmWave maximum height (ceiling) number entity."""
        return self._inovelli_number(
            "mmwave_height_maximum_ceiling",
            min_value=-600,
            max_value=600,
            fallback_name="mmWave height maximum (ceiling)",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_width_minimum_left(self, endpoint_id: int = 1):
        """Add the mmWave minimum width (left) number entity."""
        return self._inovelli_number(
            "mmwave_width_minimum_left",
            min_value=-600,
            max_value=600,
            fallback_name="mmWave width minimum (left)",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_width_maximum_right(self, endpoint_id: int = 1):
        """Add the mmWave maximum width (right) number entity."""
        return self._inovelli_number(
            "mmwave_width_maximum_right",
            min_value=-600,
            max_value=600,
            fallback_name="mmWave width maximum (right)",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_depth_minimum_near(self, endpoint_id: int = 1):
        """Add the mmWave minimum depth (near) number entity."""
        return self._inovelli_number(
            "mmwave_depth_minimum_near",
            min_value=0,
            max_value=600,
            fallback_name="mmWave depth minimum (near)",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_depth_maximum_far(self, endpoint_id: int = 1):
        """Add the mmWave maximum depth (far) number entity."""
        return self._inovelli_number(
            "mmwave_depth_maximum_far",
            min_value=0,
            max_value=600,
            fallback_name="mmWave depth maximum (far)",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_detect_sensitivity(self, endpoint_id: int = 1):
        """Add the mmWave detection sensitivity select entity."""
        return self._inovelli_select(
            "mmwave_detect_sensitivity",
            InovelliMmwaveSensitivity,
            fallback_name="mmWave sensitivity",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_detect_trigger(self, endpoint_id: int = 1):
        """Add the mmWave target speed select entity."""
        return self._inovelli_select(
            "mmwave_detect_trigger",
            InovelliMmwaveTargetSpeed,
            fallback_name="mmWave target speed",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )

    def inovelli_mmwave_hold_time(self, endpoint_id: int = 1):
        """Add the mmWave hold time number entity."""
        return self._inovelli_number(
            "mmwave_hold_time",
            min_value=0,
            max_value=4294967295,
            fallback_name="mmWave hold time",
            endpoint_id=endpoint_id,
            cluster_id=INOVELLI_MMWAVE_CLUSTER_ID,
        )
