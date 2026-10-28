"""BEGA Smart DALI Controller 2.

The controller bridges up to 32 DALI gears to Zigbee: endpoint 1 is the DALI
bus (commands reach every gear as a DALI broadcast), endpoints 2-33 control one
gear each. ZHA already discovers all of them as lights. This quirk adds what is
needed to commission the DALI bus from Home Assistant through the manufacturer
specific cluster 0xFCDA on endpoint 1: buttons to set up and to extend the DALI
system, the bus mode, the bus status flags and the number of active gears.

The cluster attributes are not reportable, so the cluster polls them: slowly
while the bus is in run mode, quickly while a scan is running (about 5 s per
gear).

A separately marked block cleans up the colour values Home Assistant reads from
the lights (see `Sdc2Color`).
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Final

from zha.application import Platform
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
)
from zhaquirks.clusters import CustomCluster

BEGA_MANUFACTURER_CODE: Final = 0x1105

GEAR_COUNT_MAX: Final = 32
FIRST_GEAR_ENDPOINT: Final = 2  # gear n lives on endpoint n + 2
DALI_BUS_ENDPOINT: Final = 1


class DaliBusMode(t.enum8):
    """State of the DALI bus."""

    Init = 0x00
    Scan = 0x01
    Run = 0x02
    Critical_error = 0x03
    Error = 0x04


class DaliBusStatus(t.bitmap16):
    """DALI bus status flags."""

    Bus_short = 0x0001
    External_supply = 0x0002
    New_device = 0x0004
    Tx_conflict = 0x0008
    Rx_error = 0x0010
    Raw_replies = 0x0020
    Address_conflict = 0x0040


class DaliScanMode(t.enum8):
    """Argument of the bus scan command."""

    New_installation = 0x00  # every gear gets a new short address
    Expand_system = 0x01  # only gears without a short address are added


def active_gear_count(virtual_gears: int) -> int:
    """Count the gears in the virtual gears attribute: two bits per gear, 1 = active and available."""
    return sum(
        1
        for gear in range(GEAR_COUNT_MAX)
        if (int(virtual_gears) >> (2 * gear)) & 0x3 == 1
    )


class BegaDaliBus(CustomCluster):
    """BEGA DALI bus cluster on endpoint 1."""

    cluster_id: t.uint16_t = 0xFCDA
    name: str = "BEGA DALI Bus"
    ep_attribute: str = "bega_dali_bus"

    STATUS_ATTRIBUTES: Final = ("bus_mode", "bus_status", "virtual_gears")
    POLL_FAST_S: Final = 3
    POLL_SLOW_S: Final = 60
    # The device switches to scan mode a moment after the command was accepted.
    POLL_BOOST_S: Final = 10
    # A new-installation scan regularly misses gears. Like the BEGA app, an
    # expand-system scan follows once the bus is back in run mode.
    FOLLOW_UP_SCAN_DELAY_S: Final = 5

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the BEGA DALI bus cluster."""

        bus_mode: Final = ZCLAttributeDef(
            id=0x0000,
            type=DaliBusMode,
            access="r",
            manufacturer_code=BEGA_MANUFACTURER_CODE,
        )
        bus_status: Final = ZCLAttributeDef(
            id=0x0001,
            type=DaliBusStatus,
            access="r",
            manufacturer_code=BEGA_MANUFACTURER_CODE,
        )
        virtual_gears: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint64_t,
            access="r",
            manufacturer_code=BEGA_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Command definitions for the BEGA DALI bus cluster."""

        bus_scan: Final = ZCLCommandDef(
            id=0x02,
            schema={"scan_mode": DaliScanMode},
            manufacturer_code=BEGA_MANUFACTURER_CODE,
        )

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the cluster and start polling the bus attributes."""
        super().__init__(*args, **kwargs)
        self._poll_task: asyncio.Task | None = None
        self._poll_wake = asyncio.Event()
        self._boost_until = 0.0
        self._follow_up_scan = False  # expand-system scan due after the running scan
        self._scan_seen = False  # bus mode "Scan" observed since the last scan command
        self._scan_generation = 0  # counts accepted scan commands
        self._start_status_polling()

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, **kwargs
    ):
        """Send the command; a new-installation scan switches all gears off first, any scan is polled."""
        is_scan = command_id == self.ServerCommandDefs.bus_scan.id
        scan_mode = (
            kwargs.get("scan_mode", args[0] if args else None) if is_scan else None
        )
        new_installation = is_scan and scan_mode == DaliScanMode.New_installation
        if new_installation:
            await self._switch_all_gears_off()
        result = await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            **kwargs,
        )
        if is_scan and self._accepted(result):
            self._scan_started(follow_up=new_installation)
        return result

    @staticmethod
    def _accepted(response) -> bool:
        """Return whether the device accepted a command.

        A rejected command does not raise; the device answers with a default
        response carrying a non-success status.
        """
        status = getattr(response, "status", foundation.Status.SUCCESS)
        return status == foundation.Status.SUCCESS

    async def _switch_all_gears_off(self) -> None:
        """Switch every gear off with a single command and mirror it into the cached state.

        Off on endpoint 1 is a DALI broadcast and reaches every gear on the bus,
        including gears without a short address. The device does not report the
        new on/off state for all gear endpoints, so the cached attribute is
        updated locally to keep Home Assistant in sync without extra traffic.
        """
        try:
            response = await self.endpoint.on_off.off()
        except Exception as exc:  # noqa: BLE001  the scan is still worth running
            self.debug("Switching gears off before the scan failed: %r", exc)
            return
        if not self._accepted(response):
            self.debug("Switching gears off before the scan was rejected: %r", response)
            return
        for endpoint in self.endpoint.device.non_zdo_endpoints:
            on_off = endpoint.in_clusters.get(OnOff.cluster_id)
            if on_off is not None:
                on_off.update_attribute(OnOff.AttributeDefs.on_off.id, t.Bool.false)

    def _scan_started(self, *, follow_up: bool) -> None:
        self._follow_up_scan = follow_up
        self._scan_seen = False
        self._scan_generation += 1
        self._boost_until = time.monotonic() + self.POLL_BOOST_S
        self._start_status_polling()
        self._poll_wake.set()

    async def _send_follow_up_scan(self) -> None:
        """Add the gears the new-installation scan missed."""
        self._follow_up_scan = False
        generation = self._scan_generation
        await asyncio.sleep(self.FOLLOW_UP_SCAN_DELAY_S)
        if generation != self._scan_generation:
            return  # a newer scan command took over, it brings its own follow-up
        try:
            response = await super().command(
                self.ServerCommandDefs.bus_scan.id, scan_mode=DaliScanMode.Expand_system
            )
        except Exception as exc:  # noqa: BLE001
            self.debug("Follow-up scan failed: %r", exc)
            return
        # a newer scan may have been accepted while waiting for the reply
        if self._accepted(response) and generation == self._scan_generation:
            self._scan_started(follow_up=False)

    def _start_status_polling(self) -> None:
        if self._poll_task is not None and not self._poll_task.done():
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no event loop yet (devices built in unit tests)
        # Owned by the zigpy device, so it is cancelled when the device is
        # removed, re-interviewed or the application shuts down.
        self._poll_task = self.endpoint.device.create_task(
            self._poll_status(), name=f"{self.ep_attribute}_poll"
        )

    async def _poll_status(self) -> None:
        """Read the bus attributes forever, fast while the bus is busy."""
        fast = False
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    self._poll_wake.wait(),
                    self.POLL_FAST_S if fast else self.POLL_SLOW_S,
                )
            self._poll_wake.clear()
            try:
                result, _ = await self.read_attributes(list(self.STATUS_ATTRIBUTES))
            except Exception as exc:  # noqa: BLE001  keep the current pace after radio errors
                self.debug("Status poll failed: %r", exc)
            else:
                mode = result.get(self.AttributeDefs.bus_mode.name)
                if mode is not None:  # keep the current pace after attribute errors
                    fast = mode != DaliBusMode.Run
                if mode == DaliBusMode.Scan:
                    self._scan_seen = True
                elif (
                    mode == DaliBusMode.Run
                    and self._follow_up_scan
                    and (self._scan_seen or time.monotonic() >= self._boost_until)
                ):
                    await self._send_follow_up_scan()
                    fast = True
            if time.monotonic() < self._boost_until:
                fast = True


# =============================================================================
# Colour workaround.
#
# Self-contained: delete this block and the lines marked "colour workaround" in
# the QuirkBuilder chain below to drop it.
#
# Background: every endpoint advertises the same colour capabilities, because
# the firmware cannot change them at runtime when the gears on the bus change.
# The ZHA light entity restores its last Home Assistant state and does not act
# on colour attribute reports, so the colour it shows comes from the attributes
# it reads at start-up and on its periodic refresh. The device answers those
# reads with FAILURE for endpoints without a gear; for gears without colour
# support it answers FAILURE or, depending on its internal state, a
# valid-looking xy = (0, 0) (both end up blue in ZHA). It reports tunable-white
# gears in the xy colour mode and may deliver a colour temperature of 0. This
# cluster cleans up those reads and judges colour support by the capabilities
# of the gear, not by the read status.
# =============================================================================


class DaliGearModeOptions(t.bitmap8):
    """Capabilities of a DALI gear."""

    Switch = 0x01
    Intensity = 0x02
    Colour_xy = 0x04
    Colour_rgbw = 0x08
    Colour_tc = 0x10


class BegaDaliGear(CustomCluster):
    """BEGA DALI bus cluster on the gear endpoints, read for the gear capabilities."""

    cluster_id: t.uint16_t = BegaDaliBus.cluster_id
    name: str = "BEGA DALI Gear"
    ep_attribute: str = "bega_dali_gear"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for the BEGA DALI bus cluster on gear endpoints."""

        mode_options: Final = ZCLAttributeDef(
            id=0x1007,
            type=DaliGearModeOptions,
            access="r",
            manufacturer_code=BEGA_MANUFACTURER_CODE,
        )


# colour temperature physical min/max of the device
COLOR_TEMP_RANGE_MIREDS: Final = (152, 555)


class Sdc2Color(CustomCluster, Color):
    """Color cluster of the controller endpoints with cleaned-up read values."""

    # D65 white point and 4000 K, in ZCL units
    NEUTRAL_VALUES: Final = {
        Color.AttributeDefs.current_x.id: 20493,
        Color.AttributeDefs.current_y.id: 21562,
        Color.AttributeDefs.color_temperature.id: 250,
    }

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Read attributes and replace values ZHA could not display sensibly."""
        result = await super().read_attributes_raw(
            attributes, manufacturer=manufacturer, **kwargs
        )
        records = result[0]
        if not isinstance(records, list):
            return result
        options = None
        if any(
            record.attrid in self.NEUTRAL_VALUES
            or record.attrid == Color.AttributeDefs.color_mode.id
            for record in records
        ):
            options = await self._gear_mode_options()
        # unknown capabilities (bus endpoint, failed read): trust the device
        no_xy_colour = options is not None and not options & (
            DaliGearModeOptions.Colour_rgbw | DaliGearModeOptions.Colour_xy
        )
        tunable_white = options is not None and bool(
            options & DaliGearModeOptions.Colour_tc
        )
        for record in records:
            ok = record.status == foundation.Status.SUCCESS
            if record.attrid in (
                Color.AttributeDefs.current_x.id,
                Color.AttributeDefs.current_y.id,
            ) and (not ok or no_xy_colour):
                # no gear or no colour support: neutral white instead of ZHA's blue
                self._set_uint16(record, self.NEUTRAL_VALUES[record.attrid])
            elif record.attrid == Color.AttributeDefs.color_temperature.id and (
                not ok
                or not (
                    COLOR_TEMP_RANGE_MIREDS[0]
                    <= record.value.value
                    <= COLOR_TEMP_RANGE_MIREDS[1]
                )
            ):
                # no gear, or colour temperature not initialised on the gear yet
                self._set_uint16(record, self.NEUTRAL_VALUES[record.attrid])
            elif record.attrid == Color.AttributeDefs.color_mode.id and no_xy_colour:
                # a tunable-white gear is shown with its colour temperature, a gear
                # without any colour support with the neutral xy white
                record.status = foundation.Status.SUCCESS
                record.value = foundation.TypeValue(
                    type=foundation.DataTypeId.enum8,
                    value=Color.ColorMode.Color_temperature
                    if tunable_white
                    else Color.ColorMode.X_and_Y,
                )
        return result

    @staticmethod
    def _set_uint16(record: foundation.ReadAttributeRecord, value: int) -> None:
        record.status = foundation.Status.SUCCESS
        record.value = foundation.TypeValue(
            type=foundation.DataTypeId.uint16, value=t.uint16_t(value)
        )

    async def _gear_mode_options(self) -> DaliGearModeOptions | None:
        """Read the capabilities of the gear on this endpoint, None if unknown."""
        dali_gear = self.endpoint.in_clusters.get(BegaDaliGear.cluster_id)
        if not isinstance(dali_gear, BegaDaliGear):  # bus endpoint
            return None
        try:
            # not from the cache: after a rescan another gear may sit on this endpoint
            success, _ = await dali_gear.read_attributes(
                [BegaDaliGear.AttributeDefs.mode_options.name], allow_cache=False
            )
        except Exception as exc:  # noqa: BLE001  treat as unknown
            self.debug("Reading the gear capabilities failed: %r", exc)
            return None
        return success.get(BegaDaliGear.AttributeDefs.mode_options.name)


# ================================== end of the colour workaround ==============


sdc2 = (
    QuirkBuilder()
    # The model identifier comes from a manufacturing token on most devices.
    .applies_to("BEGA Gantenbrink-Leuchten KG", "Smart Dali Controller 2")
    .applies_to("BEGA Gantenbrink-Leuchten KG", "Smart DALI Controller 2")
    .replaces(BegaDaliBus, endpoint_id=DALI_BUS_ENDPOINT)
    # colour workaround, see Sdc2Color above
    .replace_cluster_occurrences(Sdc2Color, replace_client_instances=False)
    # Endpoint 1 has an On/Off client cluster for controlling bound BEGA devices;
    # the "opening" binary sensor ZHA derives from it is non-functional.
    .prevent_default_entity_creation(
        endpoint_id=DALI_BUS_ENDPOINT,
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        function=lambda entity: entity.device_class == "opening",
    )
    # The endpoint 1 light reaches every gear as a DALI broadcast; name it so.
    .change_entity_metadata(
        endpoint_id=DALI_BUS_ENDPOINT,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.PLATFORM == Platform.LIGHT,
        new_translation_key="dali_broadcast",
        new_fallback_name="DALI broadcast",
    )
    # A standard entity: Home Assistant lists it under "Controls" on top of the
    # device page instead of between the start-up settings under "Configuration".
    .command_button(
        command_name=BegaDaliBus.ServerCommandDefs.bus_scan.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        entity_type=EntityType.STANDARD,
        command_kwargs={"scan_mode": DaliScanMode.New_installation},
        unique_id_suffix="rescan_bus",
        translation_key="dali_configure_system",
        fallback_name="DALI configure system",
    )
    # Adds gears that have no short address yet; existing gears keep theirs.
    .command_button(
        command_name=BegaDaliBus.ServerCommandDefs.bus_scan.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        entity_type=EntityType.STANDARD,
        command_kwargs={"scan_mode": DaliScanMode.Expand_system},
        unique_id_suffix="add_new_luminaires",
        translation_key="dali_extend_system",
        fallback_name="DALI extend system",
    )
    .enum(
        attribute_name=BegaDaliBus.AttributeDefs.bus_mode.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        enum_class=DaliBusMode,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        translation_key="bus_mode",
        fallback_name="Bus mode",
    )
    .binary_sensor(
        attribute_name=BegaDaliBus.AttributeDefs.bus_mode.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.RUNNING,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda mode: mode == DaliBusMode.Scan,
        unique_id_suffix="scan_running",
        translation_key="dali_scan_running",
        fallback_name="DALI scan running",
    )
    .sensor(
        attribute_name=BegaDaliBus.AttributeDefs.virtual_gears.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        entity_type=EntityType.STANDARD,
        suggested_display_precision=0,
        attribute_initialized_from_cache=False,
        attribute_converter=active_gear_count,
        unique_id_suffix="active_gear_count",
        translation_key="connected_dali_luminaire",
        fallback_name="Connected DALI luminaire",
    )
    .binary_sensor(
        attribute_name=BegaDaliBus.AttributeDefs.bus_status.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda status: bool(status & DaliBusStatus.Bus_short),
        unique_id_suffix="bus_short_circuit",
        translation_key="bus_short_circuit",
        fallback_name="Bus short circuit",
    )
    .binary_sensor(
        attribute_name=BegaDaliBus.AttributeDefs.bus_status.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        device_class=BinarySensorDeviceClass.POWER,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda status: bool(status & DaliBusStatus.External_supply),
        unique_id_suffix="external_bus_supply",
        translation_key="external_bus_supply",
        fallback_name="External bus supply",
    )
    .binary_sensor(
        attribute_name=BegaDaliBus.AttributeDefs.bus_status.name,
        cluster_id=BegaDaliBus.cluster_id,
        endpoint_id=DALI_BUS_ENDPOINT,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda status: bool(
            status & DaliBusStatus.Address_conflict
        ),
        unique_id_suffix="address_conflict",
        translation_key="address_conflict",
        fallback_name="Address conflict",
    )
)

# Endpoints 2-33 carry one gear each. Gear n always lives on endpoint n + 2, so
# the names stay valid across resets and rescans of the DALI system.
for gear in range(GEAR_COUNT_MAX):
    endpoint_id = FIRST_GEAR_ENDPOINT + gear
    # colour workaround: the gear capabilities, see Sdc2Color above
    sdc2 = sdc2.replaces(BegaDaliGear, endpoint_id=endpoint_id)
    sdc2 = sdc2.change_entity_metadata(
        endpoint_id=endpoint_id,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.PLATFORM == Platform.LIGHT,
        new_translation_key="dali_luminaire",
        new_translation_placeholders={"number": str(gear + 1)},
        new_fallback_name=f"Luminaire {gear + 1}",
    )

sdc2.add_to_registry()
