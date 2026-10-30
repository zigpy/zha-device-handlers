"""Ikea module."""

import logging

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration, Scenes
from zigpy.zcl.foundation import BaseCommandDefs

from zhaquirks import EventableCluster
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import BatterySize

_LOGGER = logging.getLogger(__name__)

IKEA = "IKEA of Sweden"
IKEA_CLUSTER_ID = 0xFC7C  # decimal = 64636
WWAH_CLUSTER_ID = 0xFC57  # decimal = 64599 ('Works with all Hubs' cluster)

IKEA_SHORTCUT_CLUSTER_V1_ID = 0xFC7F  # decimal = 64639 Shortcut V1 commands
IKEA_MATTER_SWITCH_CLUSTER_ID = 0xFC80  # decimal = 64640 Shortcut V2 commands

# PowerConfiguration cluster attributes
BATTERY_VOLTAGE = PowerConfiguration.attributes_by_name["battery_voltage"].id
BATTERY_SIZE = PowerConfiguration.attributes_by_name["battery_size"].id
BATTERY_QUANTITY = PowerConfiguration.attributes_by_name["battery_quantity"].id
BATTERY_RATED_VOLTAGE = PowerConfiguration.attributes_by_name[
    "battery_rated_voltage"
].id


class ScenesCluster(CustomCluster, Scenes):
    """Ikea Scenes cluster."""

    class ServerCommandDefs(Scenes.ServerCommandDefs):
        """Server command definitions."""

        press = foundation.ZCLCommandDef(
            id=0x0007,
            schema={"param1": t.int16s, "param2": t.int8s, "param3": t.int8s},
            is_manufacturer_specific=True,
        )
        hold = foundation.ZCLCommandDef(
            id=0x0008,
            schema={"param1": t.int16s, "param2": t.int8s},
            is_manufacturer_specific=True,
        )
        release = foundation.ZCLCommandDef(
            id=0x0009,
            schema={"param1": t.int16s},
            is_manufacturer_specific=True,
        )


class ShortcutV1Cluster(EventableCluster):
    """Ikea Shortcut Button Cluster Variant 1."""

    cluster_id = IKEA_SHORTCUT_CLUSTER_V1_ID

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        shortcut_v1_events = foundation.ZCLCommandDef(
            id=0x01,
            schema={
                "shortcut_button": t.int8s,
                "shortcut_event": t.int8s,
            },
            is_manufacturer_specific=True,
        )


class ShortcutV2Cluster(EventableCluster):
    """Ikea Shortcut Button Cluster Variant 2."""

    cluster_id = IKEA_MATTER_SWITCH_CLUSTER_ID

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        switch_latched = foundation.ZCLCommandDef(
            id=0x00,
            schema={
                "new_position": t.int8s,
            },
            is_manufacturer_specific=True,
        )
        initial_press = foundation.ZCLCommandDef(
            id=0x01,
            schema={
                "new_position": t.int8s,
            },
            is_manufacturer_specific=True,
        )
        long_press = foundation.ZCLCommandDef(
            id=0x02,
            schema={
                "previous_position": t.int8s,
            },
            is_manufacturer_specific=True,
        )
        short_release = foundation.ZCLCommandDef(
            id=0x03,
            schema={
                "previous_position": t.int8s,
            },
            is_manufacturer_specific=True,
        )
        long_release = foundation.ZCLCommandDef(
            id=0x04,
            schema={
                "previous_position": t.int8s,
            },
            is_manufacturer_specific=True,
        )
        multi_press_ongoing = foundation.ZCLCommandDef(
            id=0x05,
            schema={
                "new_position": t.int8s,
                # "current_number_of_presses_counted": t.int8s, # not implemented
            },
            is_manufacturer_specific=True,
        )
        multi_press_complete = foundation.ZCLCommandDef(
            id=0x06,
            schema={
                "previous_position": t.int8s,
                "total_number_of_presses_counted": t.int8s,
            },
            is_manufacturer_specific=True,
        )


# ZCL compliant IKEA power configuration clusters:
class PowerConfig1AAACluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: BatterySize.AAA,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2AAACluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 AAA."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: BatterySize.AAA,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 15,
    }


class PowerConfig2CRCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 2 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: BatterySize.CR2032,
        BATTERY_QUANTITY: 2,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 1 CR2032."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_SIZE: BatterySize.CR2032,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


class PowerConfig1CRXCluster(CustomCluster, PowerConfiguration):
    """Updating power attributes: 1 CR2032 and zero voltage."""

    _CONSTANT_ATTRIBUTES = {
        BATTERY_VOLTAGE: 0,
        BATTERY_SIZE: BatterySize.CR2032,
        BATTERY_QUANTITY: 1,
        BATTERY_RATED_VOLTAGE: 30,
    }


# doubling IKEA power configuration clusters:


# sw_build_id was not read from the device in this run yet
_SW_BUILD_ID_NOT_READ = object()


class DoublingPowerConfigClusterIKEA(CustomCluster, PowerConfiguration):
    """PowerConfiguration cluster implementation for IKEA devices.

    This implementation doubles battery pct remaining for IKEA devices with old firmware.

    The firmware is told apart by the cached ``sw_build_id`` of the Basic cluster, which can
    be left over from before an OTA update. So it is read again on the first battery report
    of a run and when the OTA file version changes.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        # OTA file version at the last successful sw_build_id read in this run
        self._sw_build_id_ota_version = _SW_BUILD_ID_NOT_READ

    async def bind(self):
        """Bind cluster and read the sw_build_id for later use."""
        result = await super().bind()
        await self._read_sw_build_id()
        return result

    def _ota_file_version(self):
        """Return the cached OTA file version, updated on every image query."""
        ota_cluster = self.endpoint.out_clusters.get(Ota.cluster_id)
        if ota_cluster is None:
            return None
        return ota_cluster.get(Ota.AttributeDefs.current_file_version.id)

    def _sw_build_id_outdated(self):
        """Check if sw_build_id needs to be read from the device."""
        if self.endpoint.basic.get(Basic.AttributeDefs.sw_build_id.id) is None:
            return True
        # not read in this run yet, or the device was updated since
        return self._sw_build_id_ota_version != self._ota_file_version()

    async def _read_sw_build_id(self):
        """Read sw_build_id from the device and remember the OTA file version."""
        ota_version = self._ota_file_version()
        success, _ = await self.endpoint.basic.read_attributes(
            [Basic.AttributeDefs.sw_build_id.id]
        )
        if Basic.AttributeDefs.sw_build_id.id in success:
            self._sw_build_id_ota_version = ota_version

    def _is_firmware_new(self):
        """Check if new firmware is installed that does not require battery doubling."""
        # get sw_build_id from attribute cache if available
        sw_build_id = self.endpoint.basic.get(Basic.AttributeDefs.sw_build_id.id)

        # sw_build_id is not cached or empty, so we consider it new firmware for now
        if not sw_build_id:
            return True

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

    async def _read_fw_and_update_battery_pct(self, reported_battery_pct, doubled):
        """Read firmware version and update battery percentage remaining if necessary."""
        await self._read_sw_build_id()

        # if the firmware read changed whether the reported percentage must be doubled,
        # update the cache with the reported battery percentage again,
        # _update_attribute doubles it or not based on the firmware known now
        if (not self._is_firmware_new()) != doubled:
            self._update_attribute(
                PowerConfiguration.AttributeDefs.battery_percentage_remaining.id,
                reported_battery_pct,
            )

    def _update_attribute(self, attrid, value):
        """Update attribute to double battery percentage if firmware is old.

        If the firmware version is unknown or may be outdated, a background task to read
        the firmware version is also started. The percentage is doubled based on the firmware
        known now, as that task happens asynchronously. It updates the percentage later
        if the firmware read changed that.
        """
        if attrid == PowerConfiguration.AttributeDefs.battery_percentage_remaining.id:
            # double percentage if the firmware is confirmed old
            double = not self._is_firmware_new()

            # if sw_build_id is not known to be current, create task to read it from
            # the device, since it should be awake now
            if self._sw_build_id_outdated():
                self.create_catching_task(
                    self._read_fw_and_update_battery_pct(value, double)
                )

            if double:
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
