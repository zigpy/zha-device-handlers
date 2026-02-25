"""Ubisys Dimmer D1 quirk."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.quirk_ids import SE_POLL_SUMMATION
from zhaquirks.ubisys import (
    InputMode,
    UbisysCluster,
    UbisysInputConfigCluster,
    build_onoff_actions,
)


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class DimmerInputMode(t.enum8):
    """Input mode for ubisys dimmer devices.

    Extends the base OnOff modes with dimmer-specific options.
    """

    Toggle = 0x00
    Toggle_switch = 0x01
    On_off_switch = 0x02
    Dimmer_single = 0x03
    Dimmer_double = 0x04


_DEFAULT_DIMMING_RATE = 50  # move_with_on_off rate for level control


def build_dimmer_single_actions(input_index: int, source_ep: int) -> list[bytes]:
    """Build input actions for dimmer single mode.

    Short press → toggle, long press → move level up/down alternately,
    release → stop.
    Transitions: 0x07 = short press, 0x86 = long press alt 1,
                 0xC6 = long press alt 2, 0x0B = release after long press
    LevelControl cluster 0x0008: 0x05 = move_with_on_off, 0x03 = stop
    """
    rate = _DEFAULT_DIMMING_RATE
    return [
        bytes([input_index, 0x07, source_ep, 0x06, 0x00, 0x02]),  # toggle
        bytes([input_index, 0x86, source_ep, 0x08, 0x00, 0x05, 0x00, rate]),  # move up
        bytes(
            [input_index, 0xC6, source_ep, 0x08, 0x00, 0x05, 0x01, rate]
        ),  # move down
        bytes([input_index, 0x0B, source_ep, 0x08, 0x00, 0x03]),  # stop
    ]


def build_dimmer_double_actions(
    input_index_up: int,
    source_ep_up: int,
    input_index_down: int,
    source_ep_down: int,
) -> list[bytes]:
    """Build input actions for dimmer double mode (paired inputs).

    Input 1 (up): short press → on, long press → move level up, release → stop.
    Input 2 (down): short press → off, long press → move level down, release → stop.
    Transitions: 0x07 = short press, 0x06 = long press, 0x0B = release after long press
    """
    rate = _DEFAULT_DIMMING_RATE
    return [
        # Up button
        bytes([input_index_up, 0x07, source_ep_up, 0x06, 0x00, 0x01]),  # on
        bytes(
            [input_index_up, 0x06, source_ep_up, 0x08, 0x00, 0x05, 0x00, rate]
        ),  # move up
        bytes([input_index_up, 0x0B, source_ep_up, 0x08, 0x00, 0x03]),  # stop
        # Down button
        bytes([input_index_down, 0x07, source_ep_down, 0x06, 0x00, 0x00]),  # off
        bytes(
            [input_index_down, 0x06, source_ep_down, 0x08, 0x00, 0x05, 0x01, rate]
        ),  # move down
        bytes([input_index_down, 0x0B, source_ep_down, 0x08, 0x00, 0x03]),  # stop
    ]


class PhaseControlMode(t.enum8):
    """Phase control mode for the D1 dimmer."""

    Automatic = 0x00
    Forward = 0x01
    Reverse = 0x02


class UbisysDimmerSetup(CustomCluster):
    """Ubisys Dimmer Setup cluster 0xFC01.

    Manufacturer-specific cluster for dimmer configuration and diagnostics.
    Uses manufacturer_code=None (ubisysNull) — the device does not expect
    a manufacturer code in the ZCL frame for this cluster's attributes.
    """

    cluster_id = 0xFC01
    name = "Ubisys Dimmer Setup"
    ep_attribute = "ubisys_dimmer_setup"

    class AttributeDefs(BaseAttributeDefs):
        """Dimmer setup attribute definitions."""

        status: Final = ZCLAttributeDef(
            id=0x0001, type=t.bitmap8, manufacturer_code=None
        )
        mode: Final = ZCLAttributeDef(id=0x0002, type=t.bitmap8, manufacturer_code=None)


class UbisysLevelControl(CustomCluster, LevelControl):
    """LevelControl with ubisys minimum_on_level attribute."""

    class AttributeDefs(LevelControl.AttributeDefs):
        """Extended LevelControl attributes."""

        minimum_on_level: Final = ZCLAttributeDef(
            id=0x0000, type=t.uint8_t, manufacturer_code=0x10F2
        )


class UbisysD1InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the D1 with two inputs.

    Input 1: EP2 -> EP1 (OnOff + LevelControl)
    Input 2: EP3 -> EP1 (OnOff + LevelControl)
    """

    BIND_CLUSTERS: list[int] = [OnOff.cluster_id, LevelControl.cluster_id]

    class AttributeDefs(BaseAttributeDefs):
        """D1 input configuration attributes for both inputs."""

        input_mode_1: Final = ZCLAttributeDef(id=0x0000, type=DimmerInputMode)
        detached_1: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        input_mode_2: Final = ZCLAttributeDef(id=0x0002, type=DimmerInputMode)
        detached_2: Final = ZCLAttributeDef(id=0x0003, type=t.Bool)

    _ATTRIBUTE_DEFAULTS: dict[int, Any] = {
        AttributeDefs.input_mode_1.id: DimmerInputMode.Toggle,
        AttributeDefs.detached_1.id: t.Bool.false,
        AttributeDefs.input_mode_2.id: DimmerInputMode.Toggle,
        AttributeDefs.detached_2.id: t.Bool.true,
    }

    _INPUT_MODE_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("input_mode_1", 0, 2),  # Input 1: index 0, source EP2
        ("input_mode_2", 1, 3),  # Input 2: index 1, source EP3
    )

    _DETACHED_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("detached_1", 2, 1),  # EP2 -> EP1
        ("detached_2", 3, 1),  # EP3 -> EP1
    )

    def _resolve_modes(
        self, override_attr_name: str, override_mode: InputMode
    ) -> list[DimmerInputMode]:
        """Resolve effective DimmerInputMode for each input."""
        modes: list[DimmerInputMode] = []
        for attr_name, _, _ in self._INPUT_MODE_CONFIG:
            if attr_name == override_attr_name:
                modes.append(DimmerInputMode(override_mode))
            else:
                attr_def = self.find_attribute(attr_name)
                modes.append(
                    DimmerInputMode(
                        self._attr_cache.get(attr_def.id, DimmerInputMode.Toggle)
                    )
                )
        return modes

    def _build_all_actions(
        self, override_attr_name: str, override_mode: InputMode
    ) -> list[bytes]:
        """Build actions with dimmer mode support."""
        modes = self._resolve_modes(override_attr_name, override_mode)

        # Dimmer_double: both inputs are paired
        if any(m == DimmerInputMode.Dimmer_double for m in modes):
            _, idx_up, ep_up = self._INPUT_MODE_CONFIG[0]
            _, idx_down, ep_down = self._INPUT_MODE_CONFIG[1]
            return build_dimmer_double_actions(idx_up, ep_up, idx_down, ep_down)

        # Per-input actions
        actions: list[bytes] = []
        for (_, input_index, source_ep), mode in zip(self._INPUT_MODE_CONFIG, modes):
            if mode == DimmerInputMode.Dimmer_single:
                actions.extend(build_dimmer_single_actions(input_index, source_ep))
            else:
                actions.extend(
                    build_onoff_actions(input_index, source_ep, InputMode(mode))
                )
        return actions

    async def write_attributes(
        self,
        attributes: dict[str | int, Any],
        manufacturer=None,
        **kwargs,
    ) -> list:
        """Handle writes with Dimmer_double sync between inputs."""
        for attr, value in attributes.items():
            attr_name = self.find_attribute(attr).name

            for mode_attr_name, _, _ in self._INPUT_MODE_CONFIG:
                if attr_name == mode_attr_name:
                    new_mode = DimmerInputMode(value)
                    other_attr_name = next(
                        name
                        for name, _, _ in self._INPUT_MODE_CONFIG
                        if name != mode_attr_name
                    )
                    other_attr = self.find_attribute(other_attr_name)
                    other_mode = DimmerInputMode(
                        self._attr_cache.get(other_attr.id, DimmerInputMode.Toggle)
                    )

                    if (
                        new_mode == DimmerInputMode.Dimmer_double
                        and other_mode != DimmerInputMode.Dimmer_double
                    ):
                        # Entering double mode: sync other input
                        self._update_attribute(
                            other_attr, DimmerInputMode.Dimmer_double
                        )
                        # Both inputs must be bound for double mode to work —
                        # re-bind any detached inputs before writing actions
                        for det_attr_name, _, _ in self._DETACHED_CONFIG:
                            det_attr = self.find_attribute(det_attr_name)
                            if self._attr_cache.get(det_attr.id, t.Bool.false):
                                await self._set_detached(det_attr_name, False)
                    elif (
                        new_mode != DimmerInputMode.Dimmer_double
                        and other_mode == DimmerInputMode.Dimmer_double
                    ):
                        # Leaving double mode: reset other to Dimmer_single
                        self._update_attribute(
                            other_attr, DimmerInputMode.Dimmer_single
                        )
                    break

        return await super().write_attributes(attributes, manufacturer, **kwargs)


(
    QuirkBuilder(manufacturer="ubisys", model="D1 (5503)")
    .applies_to(manufacturer="ubisys", model="D1-R (5603)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysD1InputConfigCluster)
    .adds(UbisysDimmerSetup)
    .replaces(UbisysLevelControl, endpoint_id=1)
    # --- Input mode / detached ---
    .enum(
        attribute_name=UbisysD1InputConfigCluster.AttributeDefs.input_mode_1.name,
        enum_class=DimmerInputMode,
        cluster_id=UbisysD1InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .switch(
        attribute_name=UbisysD1InputConfigCluster.AttributeDefs.detached_1.name,
        cluster_id=UbisysD1InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .enum(
        attribute_name=UbisysD1InputConfigCluster.AttributeDefs.input_mode_2.name,
        enum_class=DimmerInputMode,
        cluster_id=UbisysD1InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .switch(
        attribute_name=UbisysD1InputConfigCluster.AttributeDefs.detached_2.name,
        cluster_id=UbisysD1InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 2",
        translation_placeholders={"input_id": "2"},
    )
    # --- Phase control mode ---
    .enum(
        attribute_name=UbisysDimmerSetup.AttributeDefs.mode.name,
        enum_class=PhaseControlMode,
        cluster_id=UbisysDimmerSetup.cluster_id,
        translation_key="phase_control",
        fallback_name="Phase control",
    )
    # --- Minimum on level ---
    .number(
        attribute_name=UbisysLevelControl.AttributeDefs.minimum_on_level.name,
        cluster_id=UbisysLevelControl.cluster_id,
        min_value=0,
        max_value=255,
        step=1,
        translation_key="minimum_on_level",
        fallback_name="Minimum on level",
    )
    # Status binary sensors (forward/reverse phase active, overload,
    # capacitive/inductive load) require polling, so aren't exposed
    # --- Electrical measurement ---
    .replaces(UbisysElectricalMeasurement, endpoint_id=4)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=4,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="4-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=4,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .device_automation_triggers(
        {
            # this also toggles light by default
            # XXX: move_with_on_off + stop_with_on_off are also fired when holding down
            #  move_with_on_off with move_mode 0 and 1
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
        }
    )
    .add_to_registry()
)
