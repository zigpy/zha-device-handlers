"""Tests for the BEGA Smart DALI Controller 2 quirk."""

from __future__ import annotations

import asyncio
import contextlib
import time
from unittest import mock

import pytest
from zha.application import EntityPlatform, EntityType, Platform
from zha.application.platforms.binary_sensor.device_class import BinarySensorDeviceClass
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
import zigpy.exceptions
from zigpy.profiles import zgp, zha
import zigpy.types as t
import zigpy.zcl
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.greenpower import GreenPowerProxy
from zigpy.zcl.clusters.lighting import Color
from zigpy.zdo.types import NodeDescriptor

import zhaquirks
from zhaquirks.bega.sdc2 import (
    BEGA_MANUFACTURER_CODE,
    BegaDaliBus,
    BegaDaliGear,
    DaliBusMode,
    DaliBusStatus,
    DaliGearModeOptions,
    DaliScanMode,
    Sdc2Color,
)
from zhaquirks.builder.metadata import (
    BinarySensorMetadata,
    ZCLCommandButtonMetadata,
    ZCLEnumMetadata,
    ZCLSensorMetadata,
)

zhaquirks.setup()

MANUFACTURER = "BEGA Gantenbrink-Leuchten KG"
MODELS = ("Smart Dali Controller 2", "Smart DALI Controller 2")
BUS_ENDPOINT = 1
GEAR_ENDPOINTS = range(2, 34)
GREEN_POWER_ENDPOINT = 242
# further BEGA clusters on endpoint 1, not touched by the quirk
BEGA_LIGHT_CONTROLLER_CLUSTER_ID = 0xFCBE
BEGA_SYNC_SYSTEM_CLUSTER_ID = 0xFCC5

DALI_BUS_CLUSTER_ID = BegaDaliBus.cluster_id
BUS_SCAN = BegaDaliBus.ServerCommandDefs.bus_scan
MODE_OPTIONS = BegaDaliGear.AttributeDefs.mode_options
ON_OFF = OnOff.AttributeDefs.on_off
OFF = OnOff.ServerCommandDefs.off

COLOR_MODE = Color.AttributeDefs.color_mode.name
CURRENT_X = Color.AttributeDefs.current_x.name
CURRENT_Y = Color.AttributeDefs.current_y.name
COLOR_TEMPERATURE = Color.AttributeDefs.color_temperature.name
XY = Color.ColorMode.X_and_Y
CT = Color.ColorMode.Color_temperature
NEUTRAL_XY = {CURRENT_X: 20493, CURRENT_Y: 21562}
NEUTRAL_CT = 250

SUCCESS = foundation.Status.SUCCESS
FAILURE = foundation.Status.FAILURE


def default_response(
    status: foundation.Status = SUCCESS,
    command_id: int = foundation.GeneralCommand.Read_Attributes,
) -> foundation.CommandSchema:
    """Return the ZCL default response a device answers a command with."""
    return foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Default_Response
    ].schema(command_id=command_id, status=status)


DEFAULT_RESPONSE = default_response(foundation.Status.UNSUP_CLUSTER_COMMAND)

# unique ids are "{ieee}-1-{suffix}" and must never change
EXPECTED_ENTITIES = {
    "rescan_bus": (ZCLCommandButtonMetadata, EntityPlatform.BUTTON, EntityType.STANDARD, None),
    "add_new_luminaires": (ZCLCommandButtonMetadata, EntityPlatform.BUTTON, EntityType.STANDARD, None),
    "bus_mode": (ZCLEnumMetadata, EntityPlatform.SENSOR, EntityType.DIAGNOSTIC, None),
    "scan_running": (BinarySensorMetadata, EntityPlatform.BINARY_SENSOR, EntityType.STANDARD, BinarySensorDeviceClass.RUNNING),
    "active_gear_count": (ZCLSensorMetadata, EntityPlatform.SENSOR, EntityType.STANDARD, None),
    "bus_short_circuit": (BinarySensorMetadata, EntityPlatform.BINARY_SENSOR, EntityType.DIAGNOSTIC, BinarySensorDeviceClass.PROBLEM),
    "external_bus_supply": (BinarySensorMetadata, EntityPlatform.BINARY_SENSOR, EntityType.DIAGNOSTIC, BinarySensorDeviceClass.POWER),
    "address_conflict": (BinarySensorMetadata, EntityPlatform.BINARY_SENSOR, EntityType.DIAGNOSTIC, BinarySensorDeviceClass.PROBLEM),
}  # fmt: skip


def build_device(
    app: zigpy.application.ControllerApplication,
    ieee: t.EUI64,
    model: str = MODELS[0],
) -> zigpy.device.Device:
    """Build the controller as its device diagnostics describe it and apply the quirk."""
    device = zigpy.device.Device(app, ieee, t.NWK(0x1234))
    device.manufacturer = MANUFACTURER
    device.model = model
    # not the BEGA code on purpose: the quirk must not rely on the node descriptor
    device.node_desc = NodeDescriptor(manufacturer_code=1234)

    for endpoint_id in (BUS_ENDPOINT, *GEAR_ENDPOINTS):
        endpoint = device.add_endpoint(endpoint_id)
        endpoint.profile_id = zha.PROFILE_ID
        endpoint.device_type = zha.DeviceType.EXTENDED_COLOR_LIGHT
        for cluster in (Basic, Identify, Groups, Scenes, OnOff, LevelControl, Color):
            endpoint.add_input_cluster(cluster.cluster_id)
        endpoint.add_input_cluster(DALI_BUS_CLUSTER_ID)
        endpoint.add_output_cluster(DALI_BUS_CLUSTER_ID)

    bus_endpoint = device.endpoints[BUS_ENDPOINT]
    # the device lists an input cluster 0xFFFF where the OTA server would be
    for cluster_id in (
        0xFFFF,
        BEGA_LIGHT_CONTROLLER_CLUSTER_ID,
        BEGA_SYNC_SYSTEM_CLUSTER_ID,
    ):
        bus_endpoint.add_input_cluster(cluster_id)
    for cluster in (Identify, Groups, Scenes, OnOff, LevelControl, Ota, Color):
        bus_endpoint.add_output_cluster(cluster.cluster_id)
    bus_endpoint.add_output_cluster(BEGA_SYNC_SYSTEM_CLUSTER_ID)

    green_power = device.add_endpoint(GREEN_POWER_ENDPOINT)
    green_power.profile_id = zgp.PROFILE_ID
    green_power.device_type = zgp.DeviceType.PROXY_BASIC
    green_power.add_output_cluster(GreenPowerProxy.cluster_id)

    quirked = DEVICE_REGISTRY.resolve(device)
    app.devices[ieee] = quirked
    return quirked


@pytest.fixture
async def sdc2_device(MockAppController, ieee_mock):
    """Return a factory for quirked controllers; stops their polling tasks afterwards."""
    devices: list[zigpy.device.Device] = []

    def _dev(model: str = MODELS[0]) -> zigpy.device.Device:
        device = build_device(MockAppController, ieee_mock, model)
        devices.append(device)
        return device

    yield _dev

    tasks = [task for device in devices for task in device._tasks]
    for device in devices:
        device.on_remove()
    await asyncio.gather(*tasks, return_exceptions=True)


def entity_metadata(device: zigpy.device.Device) -> dict[str, object]:
    """Return the quirk's entity metadata by unique id suffix."""
    entry = DEVICE_REGISTRY.match_entry(device)
    return {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }


def sent_commands(request: mock.Mock) -> list[tuple]:
    """Return (cluster, command id, scan mode) for every command sent via `Cluster.request`."""
    sent = []
    for call in request.call_args_list:
        cluster, _general, command_id, _schema, *args = call.args
        scan_mode = call.kwargs.get("scan_mode", args[0] if args else None)
        sent.append((cluster, command_id, scan_mode))
    return sent


def test_quirk_applies_to_both_model_spellings(sdc2_device):
    """The model identifier is spelled differently depending on the production batch."""
    entries = []
    for model in MODELS:
        device = sdc2_device(model)
        assert isinstance(device.endpoints[BUS_ENDPOINT].bega_dali_bus, BegaDaliBus)
        entries.append(DEVICE_REGISTRY.match_entry(device))
    assert entries[0] is entries[1]


def test_clusters(sdc2_device):
    """Endpoint 1 carries the bus cluster, the gear endpoints the gear cluster, all the colour cluster."""
    device = sdc2_device()
    bus_endpoint = device.endpoints[BUS_ENDPOINT]
    assert isinstance(bus_endpoint.in_clusters[DALI_BUS_CLUSTER_ID], BegaDaliBus)
    for endpoint_id in GEAR_ENDPOINTS:
        gear_endpoint = device.endpoints[endpoint_id]
        assert isinstance(gear_endpoint.in_clusters[DALI_BUS_CLUSTER_ID], BegaDaliGear)
        assert isinstance(gear_endpoint.bega_dali_gear, BegaDaliGear)
    for endpoint_id in (BUS_ENDPOINT, *GEAR_ENDPOINTS):
        assert isinstance(device.endpoints[endpoint_id].light_color, Sdc2Color)
    # client clusters and the green power endpoint are left alone
    assert type(bus_endpoint.out_clusters[Color.cluster_id]) is Color
    assert type(bus_endpoint.out_clusters[OnOff.cluster_id]) is OnOff
    assert isinstance(
        device.endpoints[GREEN_POWER_ENDPOINT].out_clusters[GreenPowerProxy.cluster_id],
        GreenPowerProxy,
    )


def test_entity_metadata(sdc2_device):
    """All commissioning entities live on endpoint 1 with fixed unique id suffixes."""
    metadata = entity_metadata(sdc2_device())
    assert set(metadata) == set(EXPECTED_ENTITIES)

    for suffix, (cls, platform, entity_type, device_class) in EXPECTED_ENTITIES.items():
        meta = metadata[suffix]
        assert isinstance(meta, cls), suffix
        assert meta.endpoint_id == BUS_ENDPOINT
        assert meta.cluster_id == DALI_BUS_CLUSTER_ID
        assert meta.entity_platform == platform
        assert meta.entity_type == entity_type
        assert getattr(meta, "device_class", None) == device_class
        assert meta.fallback_name

    # the attribute and command names are part of the unique ids / polled attribute set
    assert BegaDaliBus.STATUS_ATTRIBUTES == ("bus_mode", "bus_status", "virtual_gears")
    assert set(BegaDaliBus.attributes_by_name) == set(BegaDaliBus.STATUS_ATTRIBUTES)
    assert metadata["bus_mode"].attribute_name == "bus_mode"
    assert metadata["bus_mode"].enum is DaliBusMode
    assert metadata["scan_running"].attribute_name == "bus_mode"
    assert metadata["active_gear_count"].attribute_name == "virtual_gears"
    for suffix in ("bus_short_circuit", "external_bus_supply", "address_conflict"):
        assert metadata[suffix].attribute_name == "bus_status"
    for suffix, scan_mode in (
        ("rescan_bus", DaliScanMode.New_installation),
        ("add_new_luminaires", DaliScanMode.Expand_system),
    ):
        assert metadata[suffix].command_name == "bus_scan"
        assert dict(metadata[suffix].kwargs) == {"scan_mode": scan_mode}

    # the attributes are not reportable: the entities read instead of using the cache
    for suffix in set(metadata) - {"rescan_bus", "add_new_luminaires"}:
        assert metadata[suffix].attribute_initialized_from_cache is False, suffix


def test_light_entity_names(sdc2_device):
    """The lights are named after their role; the useless "opening" sensor is suppressed."""
    definition = DEVICE_REGISTRY.match_entry(
        sdc2_device()
    ).zha_device_factory.quirk_definition
    light = mock.Mock(PLATFORM=Platform.LIGHT)
    switch = mock.Mock(PLATFORM=Platform.SWITCH)

    changes = {}
    for change in definition.changed_entity_metadata:
        assert change.cluster_id == OnOff.cluster_id
        assert change.function(light) and not change.function(switch)
        changes[change.endpoint_id] = change
    assert set(changes) == {BUS_ENDPOINT, *GEAR_ENDPOINTS}

    assert changes[BUS_ENDPOINT].new_translation_key == "dali_broadcast"
    assert changes[BUS_ENDPOINT].new_fallback_name == "DALI broadcast"
    assert changes[BUS_ENDPOINT].new_translation_placeholders is None
    for number, endpoint_id in enumerate(GEAR_ENDPOINTS, start=1):
        assert changes[endpoint_id].new_translation_key == "dali_luminaire"
        assert changes[endpoint_id].new_fallback_name == f"Luminaire {number}"
        assert dict(changes[endpoint_id].new_translation_placeholders) == {
            "number": str(number)
        }

    (prevented,) = definition.disabled_default_entities
    assert (prevented.endpoint_id, prevented.cluster_id, prevented.cluster_type) == (
        BUS_ENDPOINT,
        OnOff.cluster_id,
        ClusterType.Client,
    )
    assert prevented.function(mock.Mock(device_class="opening"))
    assert not prevented.function(mock.Mock(device_class=None))


def test_attribute_converters(sdc2_device):
    """The gear count and the status flags are derived from the raw attributes."""
    metadata = entity_metadata(sdc2_device())

    # two bits per gear, only the value 1 counts; gears 0, 3 and 31 here
    count = metadata["active_gear_count"].attribute_converter
    virtual_gears = t.uint64_t((1 << 0) | (2 << 2) | (3 << 4) | (1 << 6) | (1 << 62))
    assert count(virtual_gears) == 3
    assert count(t.uint64_t(0)) == 0
    assert count(t.uint64_t(0x5555_5555_5555_5555)) == 32

    flags = {
        "bus_short_circuit": DaliBusStatus.Bus_short,
        "external_bus_supply": DaliBusStatus.External_supply,
        "address_conflict": DaliBusStatus.Address_conflict,
    }
    for suffix, flag in flags.items():
        convert = metadata[suffix].attribute_converter
        assert convert(DaliBusStatus(flag)) is True, suffix
        assert convert(DaliBusStatus(flag | DaliBusStatus.Rx_error)) is True, suffix
        assert convert(DaliBusStatus(0)) is False, suffix
        assert convert(DaliBusStatus(DaliBusStatus.Rx_error)) is False, suffix

    running = metadata["scan_running"].attribute_converter
    assert [mode for mode in DaliBusMode if running(mode)] == [DaliBusMode.Scan]


async def test_new_installation_scan_switches_gears_off_first(sdc2_device):
    """A new-installation scan broadcasts Off on endpoint 1 and mirrors it into the cache."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus
    on_off_clusters = [
        device.endpoints[endpoint_id].on_off
        for endpoint_id in (BUS_ENDPOINT, *GEAR_ENDPOINTS)
    ]
    for on_off in on_off_clusters:
        on_off.update_attribute(ON_OFF.id, t.Bool.true)

    with mock.patch.object(
        zigpy.zcl.Cluster, "request", autospec=True, return_value=default_response()
    ) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)

    assert sent_commands(request) == [
        (device.endpoints[BUS_ENDPOINT].on_off, OFF.id, None),
        (bus, BUS_SCAN.id, DaliScanMode.New_installation),
    ]
    assert request.call_args.kwargs["manufacturer"] == BEGA_MANUFACTURER_CODE
    assert all(on_off.get(ON_OFF.id) == t.Bool.false for on_off in on_off_clusters)
    assert bus._follow_up_scan is True


async def test_expand_system_scan_keeps_gears_on(sdc2_device):
    """An expand-system scan only adds gears, so nothing is switched off."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus
    on_off = device.endpoints[GEAR_ENDPOINTS[0]].on_off
    on_off.update_attribute(ON_OFF.id, t.Bool.true)

    with mock.patch.object(
        zigpy.zcl.Cluster, "request", autospec=True, return_value=default_response()
    ) as request:
        # positional argument, as ZHA may pass it
        await bus.command(BUS_SCAN.id, DaliScanMode.Expand_system)

    assert sent_commands(request) == [(bus, BUS_SCAN.id, DaliScanMode.Expand_system)]
    assert on_off.get(ON_OFF.id) == t.Bool.true
    assert bus._follow_up_scan is False


@pytest.mark.parametrize(
    "rejection",
    [zigpy.exceptions.DeliveryError("no route"), default_response(FAILURE)],
    ids=["delivery error", "rejected"],
)
async def test_scan_is_sent_when_switching_off_fails(sdc2_device, rejection):
    """The scan is still worth running when the Off broadcast fails or is rejected."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus
    on_off = device.endpoints[BUS_ENDPOINT].on_off
    on_off.update_attribute(ON_OFF.id, t.Bool.true)

    async def fail_off(cluster, *args, **kwargs):
        if cluster is bus:
            return default_response()
        if isinstance(rejection, Exception):
            raise rejection
        return rejection

    with mock.patch.object(
        zigpy.zcl.Cluster, "request", autospec=True, side_effect=fail_off
    ) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)

    assert sent_commands(request) == [
        (on_off, OFF.id, None),
        (bus, BUS_SCAN.id, DaliScanMode.New_installation),
    ]
    # the gears were not switched off, so the cache is left alone
    assert on_off.get(ON_OFF.id) == t.Bool.true


def test_no_polling_without_event_loop(MockAppController, ieee_mock):
    """Devices built outside an event loop (unit tests) do not start a poll task."""
    device = build_device(MockAppController, ieee_mock)
    assert device.endpoints[BUS_ENDPOINT].bega_dali_bus._poll_task is None


@pytest.fixture
def fast_polling(monkeypatch):
    """Shrink the polling intervals so the polling tests run in well under a second."""
    for name in ("POLL_FAST_S", "POLL_SLOW_S", "POLL_BOOST_S"):
        monkeypatch.setattr(BegaDaliBus, name, 0.01)
    monkeypatch.setattr(BegaDaliBus, "FOLLOW_UP_SCAN_DELAY_S", 0)


class SimulatedController:
    """The controller behind patched `Cluster.request` and `read_attributes`.

    An accepted scan command puts the bus into scan mode for exactly one status
    read, then it is back in run mode.
    """

    def __init__(
        self,
        bus: BegaDaliBus,
        *,
        scan_status: foundation.Status = SUCCESS,
        expand_error: Exception | None = None,
        expand_reply: asyncio.Event | None = None,
        read_errors: int = 0,
        mode_failures: int = 0,
    ) -> None:
        """Initialize the simulation with the bus cluster the quirk talks to."""
        self.bus = bus
        self.mode = DaliBusMode.Run
        self.scan_status = scan_status
        self.expand_error = expand_error
        self.expand_reply = expand_reply  # holds back the reply to an expand scan
        self.read_errors = read_errors  # status reads that fail on the radio
        self.mode_failures = mode_failures  # run-mode reads that fail on bus_mode only

    async def request(self, cluster, _general, command_id, *args, **kwargs):
        """Answer a command like the device would."""
        if cluster is self.bus and command_id == BUS_SCAN.id:
            scan_mode = kwargs.get("scan_mode", args[0] if args else None)
            if scan_mode == DaliScanMode.Expand_system:
                if self.expand_reply is not None:
                    await self.expand_reply.wait()
                if self.expand_error:
                    raise self.expand_error
            if self.scan_status != SUCCESS:
                return default_response(self.scan_status, BUS_SCAN.id)
            self.mode = DaliBusMode.Scan
        return default_response()

    async def read(self, attributes, **kwargs):
        """Answer the status poll of the bus cluster."""
        assert attributes == list(BegaDaliBus.STATUS_ATTRIBUTES)
        if self.read_errors:
            self.read_errors -= 1
            raise zigpy.exceptions.DeliveryError("no route")
        mode, self.mode = self.mode, DaliBusMode.Run
        success = {"bus_status": DaliBusStatus(0), "virtual_gears": t.uint64_t(0)}
        if self.mode_failures and mode == DaliBusMode.Run:
            self.mode_failures -= 1
            return success, {"bus_mode": FAILURE}
        return {"bus_mode": mode, **success}, {}


@contextlib.contextmanager
def simulated(bus: BegaDaliBus, **knobs):
    """Patch the radio with a `SimulatedController`; yields the request mock."""
    controller = SimulatedController(bus, **knobs)
    with (
        mock.patch.object(
            zigpy.zcl.Cluster, "request", autospec=True, side_effect=controller.request
        ) as request,
        mock.patch.object(
            bus, "read_attributes", mock.AsyncMock(side_effect=controller.read)
        ),
    ):
        yield request


async def wait_until(condition, timeout: float = 2.0) -> None:
    """Wait for `condition()` to become true, polling in small steps."""
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not met in time"
        await asyncio.sleep(0.01)


async def test_status_polling_and_follow_up_scan(sdc2_device, fast_polling):
    """After a new-installation scan an expand-system scan follows once the bus runs again."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus
    assert bus._poll_task is not None and not bus._poll_task.done()

    # the first poll fails: the loop keeps going
    with simulated(bus, read_errors=1) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        await wait_until(lambda: request.call_count >= 3)
        # a few more polls: the follow-up scan is sent exactly once
        await asyncio.sleep(0.1)

    assert sent_commands(request) == [
        (device.endpoints[BUS_ENDPOINT].on_off, OFF.id, None),
        (bus, BUS_SCAN.id, DaliScanMode.New_installation),
        (bus, BUS_SCAN.id, DaliScanMode.Expand_system),
    ]
    assert bus._follow_up_scan is False
    assert not bus._poll_task.done()


async def test_rejected_configure_scan_has_no_follow_up(sdc2_device, fast_polling):
    """A rejected new-installation scan arms nothing, even after the boost expires."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus

    with simulated(bus, scan_status=FAILURE) as request:
        response = await bus.command(
            BUS_SCAN.id, scan_mode=DaliScanMode.New_installation
        )
        await asyncio.sleep(0.15)  # several polls, well past POLL_BOOST_S

    assert response.status == FAILURE
    assert sent_commands(request) == [
        (device.endpoints[BUS_ENDPOINT].on_off, OFF.id, None),
        (bus, BUS_SCAN.id, DaliScanMode.New_installation),
    ]
    assert bus._follow_up_scan is False


async def test_failed_follow_up_scan_is_not_retried(sdc2_device, fast_polling):
    """A follow-up scan that cannot be delivered is logged and dropped."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus

    with simulated(
        bus, expand_error=zigpy.exceptions.DeliveryError("no route")
    ) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        await wait_until(lambda: request.call_count >= 3)
        await asyncio.sleep(0.1)

    assert [scan_mode for _, _, scan_mode in sent_commands(request)] == [
        None,
        DaliScanMode.New_installation,
        DaliScanMode.Expand_system,
    ]
    assert bus._follow_up_scan is False
    assert not bus._poll_task.done()


async def test_newer_scan_supersedes_pending_follow_up(
    sdc2_device, fast_polling, monkeypatch
):
    """A configure scan during the follow-up delay cancels the older follow-up."""
    monkeypatch.setattr(BegaDaliBus, "FOLLOW_UP_SCAN_DELAY_S", 0.1)
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus
    on_off = device.endpoints[BUS_ENDPOINT].on_off

    with simulated(bus) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        # the first scan is over and its follow-up is waiting out the delay
        await wait_until(lambda: not bus._follow_up_scan)
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        await wait_until(lambda: request.call_count >= 5)
        await asyncio.sleep(0.15)

    # only the second scan gets a follow-up, after it has finished
    assert sent_commands(request) == [
        (on_off, OFF.id, None),
        (bus, BUS_SCAN.id, DaliScanMode.New_installation),
        (on_off, OFF.id, None),
        (bus, BUS_SCAN.id, DaliScanMode.New_installation),
        (bus, BUS_SCAN.id, DaliScanMode.Expand_system),
    ]
    assert bus._follow_up_scan is False


async def test_attribute_failure_keeps_scan_polling_fast(
    sdc2_device, fast_polling, monkeypatch
):
    """A bus_mode read failing on the device keeps the fast cadence of a running scan."""
    monkeypatch.setattr(BegaDaliBus, "POLL_SLOW_S", 5)
    monkeypatch.setattr(BegaDaliBus, "POLL_BOOST_S", 0)  # the boost must not mask it
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus

    # reads: Scan, then bus_mode fails, then Run
    with simulated(bus, mode_failures=1) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        # at the slow cadence the follow-up would only come after POLL_SLOW_S
        await wait_until(lambda: request.call_count >= 3, timeout=1.0)

    assert [scan_mode for _, _, scan_mode in sent_commands(request)] == [
        None,
        DaliScanMode.New_installation,
        DaliScanMode.Expand_system,
    ]


async def test_delayed_follow_up_reply_keeps_newer_scan(sdc2_device, fast_polling):
    """A reply to an older follow-up must not touch the state of a newer scan."""
    device = sdc2_device()
    bus = device.endpoints[BUS_ENDPOINT].bega_dali_bus
    expand_reply = asyncio.Event()

    with simulated(bus, expand_reply=expand_reply) as request:
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        # the follow-up has been sent and is waiting for the device's reply
        await wait_until(lambda: request.call_count == 3)
        await bus.command(BUS_SCAN.id, scan_mode=DaliScanMode.New_installation)
        expand_reply.set()
        await wait_until(lambda: request.call_count >= 5)
        await asyncio.sleep(0.15)

    # the second scan keeps its follow-up
    assert [scan_mode for _, _, scan_mode in sent_commands(request)] == [
        None,
        DaliScanMode.New_installation,
        DaliScanMode.Expand_system,
        None,
        DaliScanMode.New_installation,
        DaliScanMode.Expand_system,
    ]
    assert bus._follow_up_scan is False


def gear_read_result(options: int | None) -> object:
    """Return the device's answer to the capability read: a uint8 value or a default response."""
    if options is None:
        return DEFAULT_RESPONSE
    record = foundation.ReadAttributeRecord(
        MODE_OPTIONS.id,
        SUCCESS,
        foundation.TypeValue(foundation.DataTypeId.uint8, options),
    )
    return [[record]]


async def test_gear_capabilities_read(sdc2_device):
    """The gear capabilities are read through zigpy with the BEGA manufacturer code."""
    device = sdc2_device()
    endpoint = device.endpoints[GEAR_ENDPOINTS[1]]
    color = endpoint.light_color
    gear = endpoint.bega_dali_gear
    # a stale cached value must not be used: another gear may sit here after a rescan
    gear.update_attribute(MODE_OPTIONS.id, DaliGearModeOptions.Colour_rgbw)

    read = mock.AsyncMock(return_value=gear_read_result(0x12))
    with mock.patch.object(gear, "_read_attributes", read):
        options = await color._gear_mode_options()
    assert isinstance(options, DaliGearModeOptions)
    assert options == DaliGearModeOptions.Intensity | DaliGearModeOptions.Colour_tc
    assert read.call_args == mock.call(
        [MODE_OPTIONS.id], manufacturer=BEGA_MANUFACTURER_CODE
    )

    # a default response or a failed request means "unknown"
    read = mock.AsyncMock(return_value=gear_read_result(None))
    with mock.patch.object(gear, "_read_attributes", read):
        assert await color._gear_mode_options() is None
    read = mock.AsyncMock(side_effect=zigpy.exceptions.DeliveryError("no route"))
    with mock.patch.object(gear, "_read_attributes", read):
        assert await color._gear_mode_options() is None

    # endpoint 1 carries the bus cluster, not a gear
    assert await device.endpoints[BUS_ENDPOINT].light_color._gear_mode_options() is None


def colour_answer(answer: dict[str, int], status: foundation.Status):
    """Return a `_read_attributes` side effect answering the colour attributes in `answer`.

    The colour mode is always answered; the values carry `status`.
    """

    def _read(attributes, **kwargs):
        records = []
        for attrid in attributes:
            name = Color.attributes[attrid].name
            if name == COLOR_MODE:
                value = foundation.TypeValue(foundation.DataTypeId.enum8, answer[name])
                records.append(foundation.ReadAttributeRecord(attrid, SUCCESS, value))
            elif status == SUCCESS:
                value = foundation.TypeValue(foundation.DataTypeId.uint16, answer[name])
                records.append(foundation.ReadAttributeRecord(attrid, SUCCESS, value))
            else:
                records.append(foundation.ReadAttributeRecord(attrid, status))
        return [records]

    return _read


async def read_colour(
    device: zigpy.device.Device,
    endpoint_id: int,
    gear_options: int | None,
    answer: dict[str, int],
    status: foundation.Status = SUCCESS,
) -> dict[str, int]:
    """Read the colour attributes of an endpoint from a simulated device."""
    endpoint = device.endpoints[endpoint_id]
    color = endpoint.in_clusters[Color.cluster_id]
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(
                color,
                "_read_attributes",
                mock.AsyncMock(side_effect=colour_answer(answer, status)),
            )
        )
        if endpoint_id != BUS_ENDPOINT:
            stack.enter_context(
                mock.patch.object(
                    endpoint.in_clusters[DALI_BUS_CLUSTER_ID],
                    "_read_attributes",
                    mock.AsyncMock(return_value=gear_read_result(gear_options)),
                )
            )
        success, failure = await color.read_attributes(list(answer), allow_cache=False)
    assert not failure
    return {name: int(value) for name, value in success.items()}


def colour(mode: Color.ColorMode, x: int, y: int, ct: int) -> dict[str, int]:
    """Return a colour attribute answer."""
    return {COLOR_MODE: mode, CURRENT_X: x, CURRENT_Y: y, COLOR_TEMPERATURE: ct}


@pytest.mark.parametrize(
    ("gear_options", "answer", "status", "expected"),
    [
        # dim-only gear, a valid-looking xy = (0, 0): neutral white instead of blue
        (0x02, colour(XY, 0, 0, 0), SUCCESS, {COLOR_MODE: XY, **NEUTRAL_XY, COLOR_TEMPERATURE: NEUTRAL_CT}),
        # dim-only gear, the device answers FAILURE: same result
        (0x02, colour(XY, 0, 0, 0), FAILURE, {COLOR_MODE: XY, **NEUTRAL_XY, COLOR_TEMPERATURE: NEUTRAL_CT}),
        # dim-only gear with a stored colour temperature mode: still the neutral xy white
        (0x02, colour(CT, 0, 0, 300), SUCCESS, {COLOR_MODE: XY, **NEUTRAL_XY, COLOR_TEMPERATURE: 300}),
        # RGBW gear: untouched
        (0x0A, colour(XY, 30000, 31000, 300), SUCCESS, colour(XY, 30000, 31000, 300)),
        # tunable white gear: colour temperature mode, the colour temperature is kept
        (0x12, colour(XY, 0, 0, 300), SUCCESS, {COLOR_MODE: CT, **NEUTRAL_XY, COLOR_TEMPERATURE: 300}),
        # unknown capabilities (default response): trust the device
        (None, colour(XY, 1000, 2000, 300), SUCCESS, colour(XY, 1000, 2000, 300)),
        # unknown capabilities, the reads fail: only those are replaced
        (None, colour(XY, 1000, 2000, 300), FAILURE, {COLOR_MODE: XY, **NEUTRAL_XY, COLOR_TEMPERATURE: NEUTRAL_CT}),
        # colour temperature outside the 152-555 mired range of the device
        (0x12, colour(CT, 0, 0, 151), SUCCESS, {COLOR_MODE: CT, **NEUTRAL_XY, COLOR_TEMPERATURE: NEUTRAL_CT}),
        (0x12, colour(CT, 0, 0, 556), SUCCESS, {COLOR_MODE: CT, **NEUTRAL_XY, COLOR_TEMPERATURE: NEUTRAL_CT}),
        (0x12, colour(CT, 0, 0, 555), SUCCESS, {COLOR_MODE: CT, **NEUTRAL_XY, COLOR_TEMPERATURE: 555}),
    ],
)  # fmt: skip
async def test_colour_cleanup(sdc2_device, gear_options, answer, status, expected):
    """Colour reads are cleaned up according to the capabilities of the gear."""
    device = sdc2_device()
    result = await read_colour(device, GEAR_ENDPOINTS[1], gear_options, answer, status)
    assert result == expected


async def test_colour_read_default_response_is_passed_through(sdc2_device):
    """A default response to the colour read is left to zigpy: all attributes fail."""
    device = sdc2_device()
    color = device.endpoints[GEAR_ENDPOINTS[1]].light_color
    attributes = [COLOR_MODE, CURRENT_X, CURRENT_Y, COLOR_TEMPERATURE]
    with mock.patch.object(
        color, "_read_attributes", mock.AsyncMock(return_value=DEFAULT_RESPONSE)
    ):
        success, failure = await color.read_attributes(attributes, allow_cache=False)
    assert success == {}
    assert set(failure) == set(attributes)


async def test_colour_cleanup_on_bus_endpoint(sdc2_device):
    """Endpoint 1 has no gear capabilities: only failed reads are replaced."""
    device = sdc2_device()
    answer = colour(XY, 1000, 2000, 300)
    assert await read_colour(device, BUS_ENDPOINT, None, answer) == answer
    assert await read_colour(device, BUS_ENDPOINT, None, answer, FAILURE) == {
        COLOR_MODE: XY,
        **NEUTRAL_XY,
        COLOR_TEMPERATURE: NEUTRAL_CT,
    }
