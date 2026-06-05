"""Aeotec Pico Shutter (ZGA004) Custom ZHA V2 Quirk."""

import enum
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.zcl.clusters.closures import WindowCovering
import zigpy.types as t

AEOTEC_MFG_CODE = 0x1310

# ---------------------------------------------------------------------------
# ZCL enum types — subclass t.enum8 so zigpy serialises correctly AND
# subclass enum.IntEnum so ZHA's select entity can map values on read-back.
# One class does both jobs; no duplicate enums needed.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ZCL enum types — subclass t.enum8 so zigpy serialises correctly AND
# subclass enum.Enum so ZHA's select entity can map values on read-back.
# One class does both jobs; no duplicate enums needed.
# ---------------------------------------------------------------------------
class SwitchType(t.enum8, enum.Enum):
    Toggle = 0x00
    Momentary = 0x01
    Auto_Recognize_Mode = 0x04

class SwitchActions(t.enum8, enum.Enum):
    On_Press_Off_Release = 0x00
    Off_Press_On_Release = 0x01
    Toggle = 0x02

class Controls(t.enum8, enum.Enum):
    Disable_Local_Control = 0x00
    Enable_Local_Control = 0x01

class OperatingModes(t.enum8, enum.Enum):
    Roller_Shade_Mode = 0x00
    Shutter_Mode = 0x01

class SlatsPosition(t.enum8, enum.Enum):
    Do_not_return = 0x00
    Return_after_gateway_activation = 0x01
    Return_after_any_activation = 0x02

class MovementType(t.enum8, enum.Enum):
    Momentary = 0x00
    Continuous = 0x01

class SelfCalibration(t.enum8, enum.Enum):
    Disabled = 0x00
    Enabled = 0x01

# ---------------------------------------------------------------------------
# Custom Clusters
# ---------------------------------------------------------------------------
class AeotecWindowCoveringLift(CustomCluster, WindowCovering):
    """Forces Endpoint 1 to be recognized as Lift-Only (Roller Shade)."""
    _CONSTANT_ATTRIBUTES = {
        0x0000: 0x00,  # Type 0: Roller Shade (Lift only)
    }

class AeotecWindowCoveringTilt(CustomCluster, WindowCovering):
    """Forces Endpoint 2 to be recognized as Tilt-Only."""
    _CONSTANT_ATTRIBUTES = {
        0x0000: 0x07,  # Type 7: Tilt Blind Tilt Only
    }

class AeotecSwitchConfigurationCluster(CustomCluster):
    """Aeotec Private Cluster [0xFD00] — switch type configuration."""
    cluster_id = 0xFD00
    name = "Aeotec Switch Type Configuration"
    ep_attribute = "aeotec_switch_config"
    manufacturer = AEOTEC_MFG_CODE

    attributes = {
        0x0000: ("switch_type", SwitchType, False),
        0x0010: ("switch_actions", SwitchActions, False),
        0x0011: ("controls", Controls, False),
        0x0012: ("group_id", t.uint16_t, False),
    }

    async def read_attributes(self, attributes, allow_cache=False, only_cache=False, manufacturer=None):
        # Manufacturer code required for reads on this private cluster.
        return await super().read_attributes(
            attributes,
            allow_cache=allow_cache,
            only_cache=only_cache,
            manufacturer=self.manufacturer,
        )

    async def _read_attributes(self, attr_ids, manufacturer=None):
        # ZHA bypasses read_attributes and calls _read_attributes directly.
        # Force manufacturer code here so the ZCL frame is sent correctly.
        return await super()._read_attributes(attr_ids, manufacturer=self.manufacturer)

    async def _write_attributes(self, records, **kwargs):
        # Force manufacturer code on every write to avoid
        # UNSUPPORTED_ATTRIBUTE (134) on this private cluster.
        kwargs["manufacturer"] = self.manufacturer
        return await super()._write_attributes(records, **kwargs)


class AeotecWindowConfigurationCluster(CustomCluster):
    """Aeotec Private Cluster [0xFD03] — window/motor configuration."""
    cluster_id = 0xFD03
    name = "Aeotec Window Configuration"
    ep_attribute = "aeotec_window_config"
    manufacturer = AEOTEC_MFG_CODE

    attributes = {
        0x0001: ("operating_modes", t.uint8_t, False),
        0x0002: ("slats_tilting_time", t.uint16_t, False),
        0x0003: ("slats_position", t.uint8_t, False),
        0x0004: ("moving_up_down_time", t.uint16_t, False),
        0x0005: ("momentary_movement_time", t.uint16_t, False),
        0x0006: ("momentary_continuous_movement", t.uint8_t, False),
        0x0007: ("motor_response_time", t.uint8_t, False),
        0x0008: ("self_calibration_enable", t.uint8_t, False),
    }

    # No overrides — 0xFD03 works without manufacturer code


# ---------------------------------------------------------------------------
# Build the V2 Quirk
# ---------------------------------------------------------------------------
(
    QuirkBuilder("AEOTEC", "ZGA004")
    .replaces(AeotecWindowCoveringLift, endpoint_id=1)     # Force EP1 to Lift-only
    .replaces(AeotecWindowCoveringTilt, endpoint_id=2)     # Force EP2 to Tilt-only
    .replaces(AeotecWindowConfigurationCluster, endpoint_id=1)
    .replaces(AeotecSwitchConfigurationCluster, endpoint_id=4)
    .replaces(AeotecSwitchConfigurationCluster, endpoint_id=5)

    # ===========================================================================
    # UI Entities — Switch Configuration [0xFD00] — endpoints 4 & 5
    # ===========================================================================
    .enum(
        cluster_id=AeotecSwitchConfigurationCluster.cluster_id,
        endpoint_id=4,
        attribute_name="switch_type",
        enum_class=SwitchType,
        translation_key="switch_type",
        fallback_name="Switch Type (S1)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecSwitchConfigurationCluster.cluster_id,
        endpoint_id=5,
        attribute_name="switch_type",
        enum_class=SwitchType,
        translation_key="switch_type",
        fallback_name="Switch Type (S2)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecSwitchConfigurationCluster.cluster_id,
        endpoint_id=4,
        attribute_name="switch_actions",
        enum_class=SwitchActions,
        translation_key="switch_actions",
        fallback_name="Switch Actions (S1)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecSwitchConfigurationCluster.cluster_id,
        endpoint_id=5,
        attribute_name="switch_actions",
        enum_class=SwitchActions,
        translation_key="switch_actions",
        fallback_name="Switch Actions (S2)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecSwitchConfigurationCluster.cluster_id,
        endpoint_id=4,
        attribute_name="controls",
        enum_class=Controls,
        translation_key="controls",
        fallback_name="Local Motor Control (S1)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecSwitchConfigurationCluster.cluster_id,
        endpoint_id=5,
        attribute_name="controls",
        enum_class=Controls,
        translation_key="controls",
        fallback_name="Local Motor Control (S2)",
        entity_type=EntityType.CONFIG,
    )

    # ===========================================================================
    # UI Entities — Window Covering [0x0102] — Motor Direction / LED
    # 0=Normal, 1=Reversed, 8=Normal+LED, 9=Reversed+LED
    # ===========================================================================
    .number(
        cluster_id=WindowCovering.cluster_id,
        endpoint_id=1,
        attribute_name="window_covering_mode",
        min_value=0,
        max_value=9,
        step=1,
        translation_key="motor_direction",
        fallback_name="Motor Direction / LED (0=Normal 1=Rev 8=Normal+LED 9=Rev+LED)",
        entity_type=EntityType.CONFIG,
    )

    # ===========================================================================
    # UI Entities — Window Configuration [0xFD03] — endpoint 1
    # ===========================================================================
    .enum(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="operating_modes",
        enum_class=OperatingModes,
        translation_key="operating_modes",
        fallback_name="Operating Mode",
        entity_type=EntityType.CONFIG,
    )
    .number(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="slats_tilting_time",
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="slats_tilting_time",
        fallback_name="Slats Tilting Full Turn Time (x0.01s)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="slats_position",
        enum_class=SlatsPosition,
        translation_key="slats_position",
        fallback_name="Slats Position Return",
        entity_type=EntityType.CONFIG,
    )
    .number(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="moving_up_down_time",
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="moving_up_down_time",
        fallback_name="Moving Up/Down Time (x0.01s)",
        entity_type=EntityType.CONFIG,
    )
    .number(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="momentary_movement_time",
        min_value=0,
        max_value=65535,
        step=1,
        translation_key="momentary_movement_time",
        fallback_name="Momentary Movement Time (ms)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="momentary_continuous_movement",
        enum_class=MovementType,
        translation_key="momentary_continuous_movement",
        fallback_name="Movement Type",
        entity_type=EntityType.CONFIG,
    )
    .number(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="motor_response_time",
        min_value=0,
        max_value=255,
        step=1,
        translation_key="motor_response_time",
        fallback_name="Motor Response Time (x0.01s)",
        entity_type=EntityType.CONFIG,
    )
    .enum(
        cluster_id=AeotecWindowConfigurationCluster.cluster_id,
        endpoint_id=1,
        attribute_name="self_calibration_enable",
        enum_class=SelfCalibration,
        translation_key="self_calibration_enable",
        fallback_name="Self-Calibration",
        entity_type=EntityType.CONFIG,
    )

    .add_to_registry()
)