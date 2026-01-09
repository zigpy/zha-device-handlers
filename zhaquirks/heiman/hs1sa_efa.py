"""Heiman HS1SA-E smoke sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder, ReportingConfig
from zigpy.quirks.v2.homeassistant import EntityType
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef, ZCLCommandDef

# Heiman's actual manufacturer code
HEIMAN_MANUF_CODE = 0x120B


class SmokeSirenEnum(t.enum8):
    """smoke siren type."""

    stop = 0
    smoke_siren = 1
    co_siren = 2


class SmokeRemoteMuteEnum(t.uint8_t):
    """smoke remote mute."""

    normal = 0
    mute = 1


class SmokeRemoteTestEnum(t.uint8_t):
    """smoke remote test."""

    normal = 0
    start_test = 1


def smoke_chamber_contamination_converter(value: int) -> str:
    """Extract contamination value."""
    value_hex = hex(value)[2:].zfill(8)
    actions = {
        "00": "normal",
        "01": "light contamination",
        "02": "medium contamication",
        "03": "critical contamication",
    }
    return actions.get(value_hex[2:4])


def smoke_level_unit_converter(value: int) -> str:
    """Extract smoke level unit."""
    value_hex = hex(value)[2:].zfill(8)
    actions = {
        "00": "dB/m",
        "01": "%ft OBS",
    }
    return actions.get(value_hex[2:4])


class ExtendIasZoneCluster(CustomCluster, IasZone):
    """Heiman IAS Zone cluster extension."""

    cluster_id = IasZone.cluster_id

    # Map the command name to your new function
    server_commands = IasZone.server_commands.copy()
    server_commands.update(
        {
            0x02: ZCLCommandDef(
                "initiate_test_mode",
                {
                    "test_mode_duration": t.uint8_t,
                    "current_zone_sensitivity": t.uint8_t,
                },
                direction=foundation.Direction.Client_to_Server,
                is_manufacturer_specific=False,  # Set to False for standard commands
            )
        }
    )

    async def command(self, command_id, *args, **kwargs):
        """Handle wd commands for the cluster."""
        # If the UI calls command 0x02 (initiate_test_mode) without arguments
        if command_id == 0x02 and not args:
            # Provide default: 5 seconds, 0 sensitivity
            return await super().command(command_id, 5, 0, **kwargs)
        return await super().command(command_id, *args, **kwargs)


class CustomHeimanCluster(CustomCluster):
    """Heiman custom cluster."""

    cluster_id = 0xFC90
    # manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID

    # We override the manufacturer_id at the cluster level
    @property
    def manufacturer_id(self) -> t.uint16_t:
        """Return manufacturer ID for the cluster."""
        return 0x120B

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        sensor_self_check_state = ZCLAttributeDef(
            id=0x0001,
            type=t.enum8,
            is_manufacturer_specific=True,
        )

        sensor_fault_state = ZCLAttributeDef(
            id=0x0002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        sensor_mute_state = ZCLAttributeDef(
            id=0x0009,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

        heartbeat_indicator = ZCLAttributeDef(
            id=0x1004,
            type=t.uint8_t,
        )

        siren_for_automation = ZCLAttributeDef(
            id=0x0012,
            type=t.enum8,
        )

        interconnectable = ZCLAttributeDef(
            id=0x1007,
            type=t.uint8_t,
        )

        smoke_level = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
        )

        smoke_unit = ZCLAttributeDef(
            id=0x0018,
            type=t.enum8,
        )

        chamber_contamination = ZCLAttributeDef(
            id=0x0017,
            type=t.enum8,
        )

        rebooted_count = ZCLAttributeDef(
            id=0x0019,
            type=t.uint16_t,
        )

        rejoined_count = ZCLAttributeDef(
            id=0x001A,
            type=t.uint16_t,
        )

        reported_packages = ZCLAttributeDef(
            id=0x001B,
            type=t.uint16_t,
        )

        remote_mute = ZCLAttributeDef(
            id=0x0008,
            type=t.uint8_t,
        )

        remote_test = ZCLAttributeDef(
            id=0x1009,
            type=t.uint8_t,
        )


(
    QuirkBuilder("HEIMAN", "HS1SA-EF-3.0")
    .removes(0x0502)
    .replaces(ExtendIasZoneCluster)
    .replaces(CustomHeimanCluster)
    .switch(
        CustomHeimanCluster.AttributeDefs.heartbeat_indicator.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="heartbeat_indicator",
        fallback_name="heartbeat indicator",
    )
    .enum(
        CustomHeimanCluster.AttributeDefs.siren_for_automation.name,
        SmokeSirenEnum,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="siren_for_automation_only",
        fallback_name="siren_for_automation_only",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.chamber_contamination.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_converter=smoke_chamber_contamination_converter,
        translation_key="chamber_contamination",
        fallback_name="chamber contamination",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.smoke_unit.name,
        CustomHeimanCluster.cluster_id,
        attribute_converter=smoke_level_unit_converter,
        translation_key="smoke_level_unit",
        fallback_name="smoke level unit",
        # reporting_config=ReportingConfig(
        #     min_interval=1,
        #     max_interval=5,
        #     reportable_change=10
        # )
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.sensor_self_check_state.name,
        CustomHeimanCluster.cluster_id,
        unique_id_suffix="selftest",
        translation_key="selftest",
        fallback_name="selftest",
        reporting_config=ReportingConfig(
            min_interval=2, max_interval=0, reportable_change=1
        ),
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.sensor_fault_state.name,
        CustomHeimanCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        unique_id_suffix="fault",
        translation_key="fault",
        fallback_name="fault",
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.sensor_mute_state.name,
        CustomHeimanCluster.cluster_id,
        unique_id_suffix="muted",
        translation_key="muted",
        fallback_name="muted",
    )
    .binary_sensor(
        CustomHeimanCluster.AttributeDefs.interconnectable.name,
        CustomHeimanCluster.cluster_id,
        unique_id_suffix="interconnectable",
        translation_key="interconnectable",
        fallback_name="interconnectable",
    )
    .switch(
        CustomHeimanCluster.AttributeDefs.remote_mute.name,
        CustomHeimanCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="remote_mute",
        fallback_name="remote mute",
    )
    .command_button(
        "initiate_test_mode",
        ExtendIasZoneCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        translation_key="remote_mute",
        fallback_name="remote Test",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.smoke_level.name,
        CustomHeimanCluster.cluster_id,
        multiplier=0.01,
        translation_key="smoke_level",
        fallback_name="smoke level",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.rebooted_count.name,
        CustomHeimanCluster.cluster_id,
        device_class=None,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="rebooted_count",
        fallback_name="rebooted count",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.rejoined_count.name,
        CustomHeimanCluster.cluster_id,
        device_class=None,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="rejoined_count",
        fallback_name="rejoined count",
    )
    .sensor(
        CustomHeimanCluster.AttributeDefs.reported_packages.name,
        CustomHeimanCluster.cluster_id,
        device_class=None,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="reported_packages",
        fallback_name="reported packages",
    )
    .add_to_registry()
)
