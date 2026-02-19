"""Ubisys Dimmer D1 quirk."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lighting import Ballast
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
)
from zhaquirks.quirk_ids import SE_POLL_SUMMATION
from zhaquirks.ubisys import InputMode, UbisysCluster, UbisysInputConfigCluster


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


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

        capabilities: Final = ZCLAttributeDef(
            id=0x0000, type=t.bitmap8, manufacturer_code=None
        )
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

        input_mode_1: Final = ZCLAttributeDef(id=0x0000, type=InputMode)
        detached_1: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        input_mode_2: Final = ZCLAttributeDef(id=0x0002, type=InputMode)
        detached_2: Final = ZCLAttributeDef(id=0x0003, type=t.Bool)

    _ATTRIBUTE_DEFAULTS: dict[int, Any] = {
        AttributeDefs.input_mode_1.id: InputMode.Toggle,
        AttributeDefs.detached_1.id: t.Bool.false,
        AttributeDefs.input_mode_2.id: InputMode.Toggle,
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
        enum_class=InputMode,
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
        enum_class=InputMode,
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
    # --- Ballast min/max level ---
    .number(
        attribute_name=Ballast.AttributeDefs.min_level.name,
        cluster_id=Ballast.cluster_id,
        min_value=1,
        max_value=254,
        step=1,
        translation_key="ballast_minimum_level",
        fallback_name="Ballast minimum level",
    )
    .number(
        attribute_name=Ballast.AttributeDefs.max_level.name,
        cluster_id=Ballast.cluster_id,
        min_value=1,
        max_value=254,
        step=1,
        translation_key="ballast_maximum_level",
        fallback_name="Ballast maximum level",
    )
    # --- Dimmer capabilities (diagnostic binary sensors) ---
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.capabilities.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x01),
        unique_id_suffix="forward_phase_support",
        translation_key="forward_phase_support",
        fallback_name="Forward phase control support",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.capabilities.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x02),
        unique_id_suffix="reverse_phase_support",
        translation_key="reverse_phase_support",
        fallback_name="Reverse phase control support",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.capabilities.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x20),
        unique_id_suffix="reactance_discriminator",
        translation_key="reactance_discriminator",
        fallback_name="Reactance discriminator",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.capabilities.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x40),
        unique_id_suffix="configurable_curve",
        translation_key="configurable_curve",
        fallback_name="Configurable curve",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.capabilities.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x80),
        unique_id_suffix="overload_detection",
        translation_key="overload_detection",
        fallback_name="Overload detection",
    )
    # --- Dimmer operating status (diagnostic binary sensors) ---
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.status.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x01),
        unique_id_suffix="forward_phase_active",
        translation_key="forward_phase_active",
        fallback_name="Forward phase control active",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.status.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x02),
        unique_id_suffix="reverse_phase_active",
        translation_key="reverse_phase_active",
        fallback_name="Reverse phase control active",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.status.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x08),
        device_class=BinarySensorDeviceClass.PROBLEM,
        unique_id_suffix="overload",
        translation_key="overload",
        fallback_name="Overload",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.status.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x40),
        unique_id_suffix="capacitive_load",
        translation_key="capacitive_load",
        fallback_name="Capacitive load detected",
    )
    .binary_sensor(
        attribute_name=UbisysDimmerSetup.AttributeDefs.status.name,
        cluster_id=UbisysDimmerSetup.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=lambda v: bool(v & 0x80),
        unique_id_suffix="inductive_load",
        translation_key="inductive_load",
        fallback_name="Inductive load detected",
    )
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
            # XXX: move_with_on_off + stop_with_on_off are also fired when holding down
            #  move_with_on_off with move_mode 0 and 1
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
        }
    )
    .add_to_registry()
)
