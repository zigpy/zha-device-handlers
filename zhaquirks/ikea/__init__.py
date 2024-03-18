"""Ikea module."""

import logging

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration, Scenes

from zhaquirks import EventableCluster

_LOGGER = logging.getLogger(__name__)

IKEA = "IKEA of Sweden"
IKEA_CLUSTER_ID = 0xFC7C  # decimal = 64636
WWAH_CLUSTER_ID = 0xFC57  # decimal = 64599 ('Works with all Hubs' cluster)

IKEA_SHORTCUT_CLUSTER_V1_ID = 0xFC7F  # decimal = 64639 Shortcut V1 commands
IKEA_MATTER_SWITCH_CLUSTER_ID = 0xFC80  # decimal = 64640 Shortcut V2 commands
COMMAND_SHORTCUT_V1 = "shortcut_v1_events"

# PowerConfiguration cluster attributes
BATTERY_VOLTAGE = PowerConfiguration.attributes_by_name["battery_voltage"].id
BATTERY_SIZE = PowerConfiguration.attributes_by_name["battery_size"].id
BATTERY_QUANTITY = PowerConfiguration.attributes_by_name["battery_quantity"].id
BATTERY_RATED_VOLTAGE = PowerConfiguration.attributes_by_name[
    "battery_rated_voltage"
].id


class ScenesCluster(CustomCluster, Scenes):
    """Ikea Scenes cluster."""

    server_commands = Scenes.server_commands.copy()
    server_commands.update(
        {
            0x0007: foundation.ZCLCommandDef(
                "press",
                {"param1": t.int16s, "param2": t.int8s, "param3": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0008: foundation.ZCLCommandDef(
                "hold",
                {"param1": t.int16s, "param2": t.int8s},
                False,
                is_manufacturer_specific=True,
            ),
            0x0009: foundation.ZCLCommandDef(
                "release",
                {
                    "param1": t.int16s,
                },
                False,
                is_manufacturer_specific=True,
            ),
        }
    )


class ShortcutV1Cluster(EventableCluster):
    """Ikea Shortcut Button Cluster Variant 1."""

    cluster_id = IKEA_SHORTCUT_CLUSTER_V1_ID

    server_commands = {
        0x01: foundation.ZCLCommandDef(
            COMMAND_SHORTCUT_V1,
            {
                "shortcut_button": t.int8s,
                "shortcut_event": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
    }


class ShortcutV2Cluster(EventableCluster):
    """Ikea Shortcut Button Cluster Variant 2."""

    cluster_id = IKEA_MATTER_SWITCH_CLUSTER_ID

    server_commands = {
        0x00: foundation.ZCLCommandDef(
            "switch_latched",
            {
                "new_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x01: foundation.ZCLCommandDef(
            "initial_press",
            {
                "new_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x02: foundation.ZCLCommandDef(
            "long_press",
            {
                "previous_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x03: foundation.ZCLCommandDef(
            "short_release",
            {
                "previous_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x04: foundation.ZCLCommandDef(
            "long_release",
            {
                "previous_position": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x05: foundation.ZCLCommandDef(
            "multi_press_ongoing",
            {
                "new_position": t.int8s,
                # "current_number_of_presses_counted": t.int8s, # not implemented
            },
            False,
            is_manufacturer_specific=True,
        ),
        0x06: foundation.ZCLCommandDef(
            "multi_press_complete",
            {
                "previous_position": t.int8s,
                "total_number_of_presses_counted": t.int8s,
            },
            False,
            is_manufacturer_specific=True,
        ),
    }


# ZCL compliant IKEA power configuration clusters:
class PowerConfig1AAACluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 4,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2AAACluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 4,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2CRCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 10,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 1 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRXCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 1 CR2032 and zero voltage."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_VOLTAGE: 0,
        BATTERY_SIZE: 10,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


# doubling IKEA power configuration clusters:


class DoublingPowerConfigClusterIKEA(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation for IKEA devices.

    This implementation doubles battery pct remaining for IKEA devices with old firmware.
    """

    async def bind(self):
        """Bind cluster and read the sw_build_id for later use."""
        result = await super().bind()
        await self.endpoint.basic.read_attributes([Basic.AttributeDefs.sw_build_id.id])
        return result

    def _is_firmware_new(self):
        """Check if new firmware is installed that does not require battery doubling."""
        # get sw_build_id from attribute cache if available
        sw_build_id = self.endpoint.basic.get(Basic.AttributeDefs.sw_build_id.id)

        # sw_build_id is not cached or empty, so we consider it old firmware for now
        if not sw_build_id:
            return False

        # split sw_build_id into parts to check for new firmware
        split_fw_version = sw_build_id.split(".")
        if len(split_fw_version) >= 2:
            # guard against possible future version formatting which includes more than just numbers
            try:
                first_part = int(split_fw_version[0])
                second_part = int(split_fw_version[1])

                # new firmware is either 24.4.5 or above, or 2.4.5 or above
                # old firmware is 2.3.x or below
                return first_part >= 3 or (first_part >= 2 and second_part >= 4)
            except ValueError:
                _LOGGER.warning(
                    "sw_build_id is not a number: %s for device %s",
                    sw_build_id,
                    self.endpoint.device.ieee,
                )
                # sw_build_id is not a number, so it must be new firmware
                return True

        # unknown formatting of sw_build_id, so it must be new firmware
        return True

    async def _read_fw_and_update_battery_pct(self, reported_battery_pct):
        """Read firmware version and update battery percentage remaining if necessary."""
        # read sw_build_id from device
        await self.endpoint.basic.read_attributes([Basic.AttributeDefs.sw_build_id.id])

        # check if sw_build_id was read successfully and new firmware is installed
        # if so, update cache with reported battery percentage (non-doubled)
        if self._is_firmware_new():
            self._update_attribute(
                PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
                reported_battery_pct,
            )

    def _update_attribute(self, attrid, value):
        """Update attribute to double battery percentage if firmware is old/unknown.

        If the firmware version is unknown, a background task to read the firmware version is also started,
        but the percentage is also doubled for now then, as that task happens asynchronously.
        """
        if attrid == PowerConfiguration.AttributeDefs.battery_percentage_remaining.id:
            # if sw_build_id is not cached, create task to read from device, since it should be awake now
            if (
                self.endpoint.basic.get(Basic.AttributeDefs.sw_build_id.id, None)
                is None
            ):
                self.create_catching_task(self._read_fw_and_update_battery_pct(value))

            # double percentage if the firmware is old or unknown
            # the coroutine above will not have executed yet if the firmware is unknown,
            # so we double for now in that case too, and it updates again later if our doubling was wrong
            if not self._is_firmware_new():
                value = value * 2
        super()._update_attribute(attrid, value)


class DoublingPowerConfig2AAACluster(
    DoublingPowerConfigClusterIKEA, PowerConfig2AAACluster
):
    """Doubling power configuration cluster. Updating power attributes: 2 AAA."""


class DoublingPowerConfig2CRCluster(
    DoublingPowerConfigClusterIKEA, PowerConfig2CRCluster
):
    """Doubling power configuration cluster. Updating power attributes: 2 CR2032."""


class DoublingPowerConfig1CRCluster(
    DoublingPowerConfigClusterIKEA, PowerConfig1CRCluster
):
    """Doubling power configuration cluster. Updating power attributes: 1 CR2032."""


class DoublingPowerConfig1CRXCluster(
    DoublingPowerConfigClusterIKEA, PowerConfig1CRXCluster
):
    """Doubling power configuration cluster. Updating power attributes: 1 CR2032 and zero voltage."""
