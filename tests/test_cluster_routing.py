"""Tests for direct routing between custom clusters."""

import asyncio
from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import LevelControl, OnOff, PowerConfiguration, Scenes
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import PM25

from tests.common import ZCL_IAS_MOTION_COMMAND, ClusterListener
import zhaquirks
from zhaquirks.adeo.color_controller import (
    SCENE_NO_GROUP,
    AdeoColorController,
    AdeoManufacturerCluster,
)
from zhaquirks.const import COMMAND_OFF, COMMAND_ON, COMMAND_STEP, OFF, ON
from zhaquirks.elko.smart_super_thermostat import (
    CHILD_LOCK,
    HEATING_ACTIVE,
    POWER_CONSUMPTION,
    ElkoSuperTRThermostat,
)
from zhaquirks.ikea.starkvind import IkeaAirpurifier, IkeaSTARKVIND, IkeaSTARKVIND_v2
from zhaquirks.konke.motion import KonkeMotion
from zhaquirks.mli.tint import TINT_SCENE_ATTR, TintRemote
from zhaquirks.sengled.e1e_g7f import (
    SengledE1EG7F,
    SengledE1EG7FManufacturerSpecificCluster,
)
from zhaquirks.smartthings.tag_v4 import SmartThingsTagV4
from zhaquirks.terncy import TerncyRawCluster
from zhaquirks.terncy.pp01 import TerncyAwarenessSwitch
from zhaquirks.tuya.ts0210 import TuyaVibration, TuyaVibration_TO
from zhaquirks.waxman.leaksmart import WAXMANleakSMARTv2, WAXMANleakSMARTv2NOPOLL
from zhaquirks.xiaomi.aqara.vibration_aq1 import (
    DROP_VALUE,
    ORIENTATION_ATTR,
    RECENT_ACTIVITY_LEVEL_ATTR,
    ROTATION_DEGREES_ATTR,
    STATUS_TYPE_ATTR,
    VIBE_VALUE,
    VibrationAQ1,
)
from zhaquirks.zhongxing.motion import SN10ZW

zhaquirks.setup()


@pytest.mark.parametrize("preset", (1, 2, 3, 4))
def test_adeo_preset_routes_to_output_scenes(zigpy_device_from_quirk, preset):
    """Adeo preset commands must originate from the output Scenes cluster."""
    device = zigpy_device_from_quirk(AdeoColorController)
    source = device.endpoints[1].out_clusters[AdeoManufacturerCluster.cluster_id]
    scenes = device.endpoints[1].out_clusters[Scenes.cluster_id]
    listener = mock.MagicMock()
    scenes.add_listener(listener)

    source.handle_cluster_request(mock.Mock(command_id=0), [preset, 0])

    listener.zha_send_event.assert_called_once_with("view", [SCENE_NO_GROUP, preset])


def test_tint_scene_write_routes_to_output_scenes(zigpy_device_from_quirk):
    """Tint's manufacturer attribute must update its output Scenes cluster."""
    device = zigpy_device_from_quirk(TintRemote)
    source = device.endpoints[1].basic
    scenes = device.endpoints[1].out_clusters[Scenes.cluster_id]
    attribute = mock.Mock(attrid=TINT_SCENE_ATTR)
    attribute.value.value = 3

    source.handle_cluster_general_request(
        mock.Mock(command_id=foundation.GeneralCommand.Write_Attributes),
        [[attribute]],
    )

    assert scenes.get(Scenes.AttributeDefs.current_scene.name) == 3

    attribute.value.value = 4
    source.handle_cluster_general_request(mock.Mock(command_id=0), [[attribute]])
    source.handle_cluster_general_request(
        mock.Mock(command_id=foundation.GeneralCommand.Write_Attributes),
        [[mock.Mock(attrid=TINT_SCENE_ATTR + 1)]],
    )
    assert scenes.get(Scenes.AttributeDefs.current_scene.name) == 3


@pytest.mark.parametrize(
    ("action", "step_size", "target_cluster_id", "command", "args"),
    (
        (1, 0, OnOff.cluster_id, COMMAND_ON, []),
        (2, 2, LevelControl.cluster_id, COMMAND_STEP, [0, 2, 0]),
        (2, 1, LevelControl.cluster_id, COMMAND_STEP, [0, 1, 0]),
        (3, 2, LevelControl.cluster_id, COMMAND_STEP, [1, 2, 0]),
        (3, 1, LevelControl.cluster_id, COMMAND_STEP, [1, 1, 0]),
        (4, 0, OnOff.cluster_id, COMMAND_OFF, []),
        (5, 0, OnOff.cluster_id, "on_double", []),
        (6, 0, OnOff.cluster_id, "on_long", []),
        (7, 0, OnOff.cluster_id, "off_double", []),
        (8, 0, OnOff.cluster_id, "off_long", []),
    ),
)
def test_sengled_actions_route_to_output_clusters(
    zigpy_device_from_quirk,
    action,
    step_size,
    target_cluster_id,
    command,
    args,
):
    """Sengled actions must retain their output-cluster event provenance."""
    device = zigpy_device_from_quirk(SengledE1EG7F)
    endpoint = device.endpoints[1]
    source = endpoint.out_clusters[SengledE1EG7FManufacturerSpecificCluster.cluster_id]
    on_off_listener = mock.MagicMock()
    level_listener = mock.MagicMock()
    endpoint.out_clusters[OnOff.cluster_id].add_listener(on_off_listener)
    endpoint.out_clusters[LevelControl.cluster_id].add_listener(level_listener)

    source.handle_cluster_request(mock.Mock(command_id=0), [action, 0, step_size, 0])

    target_listener = (
        on_off_listener if target_cluster_id == OnOff.cluster_id else level_listener
    )
    other_listener = (
        level_listener if target_cluster_id == OnOff.cluster_id else on_off_listener
    )
    target_listener.zha_send_event.assert_called_once_with(command, args)
    other_listener.zha_send_event.assert_not_called()


def test_sengled_unknown_action_does_not_resolve_output_clusters(device_mock):
    """Unknown Sengled actions must remain inert without requiring output clusters."""
    source = SengledE1EG7FManufacturerSpecificCluster(device_mock.endpoints[1])

    source.handle_cluster_request(mock.Mock(command_id=0), [99, 0, 0, 0])


async def test_terncy_motion_routes_by_side_and_updates_occupancy(
    zigpy_device_from_quirk,
):
    """Terncy raw reports must select the correct IAS endpoint."""
    device = zigpy_device_from_quirk(TerncyAwarenessSwitch)
    raw = device.endpoints[1].in_clusters[TerncyRawCluster.cluster_id]
    left = device.endpoints[1].ias_zone
    right = device.endpoints[2].ias_zone
    occupancy = device.endpoints[1].occupancy
    left_listener = ClusterListener(left)
    right_listener = ClusterListener(right)
    occupancy_listener = ClusterListener(occupancy)

    with (
        mock.patch.object(left, "reset_s", 0),
        mock.patch.object(right, "reset_s", 0),
        mock.patch.object(occupancy, "reset_s", 0),
    ):
        raw.handle_cluster_request(mock.Mock(command_id=4), [0, 0, 40])
        await asyncio.sleep(0.05)
        raw.handle_cluster_request(mock.Mock(command_id=4), [0, 0, 5])
        await asyncio.sleep(0.05)

    assert [command[2][0] for command in left_listener.cluster_commands] == [ON, OFF]
    assert [command[2][0] for command in right_listener.cluster_commands] == [ON, OFF]
    assert occupancy_listener.attribute_updates == [
        (0, 1),
        (0, 0),
        (0, 1),
        (0, 0),
    ]


async def test_zhongxing_motion_does_not_require_occupancy(
    zigpy_device_from_quirk,
):
    """Zhongxing motion reports must work without an occupancy cluster."""
    device = zigpy_device_from_quirk(SN10ZW)
    motion = device.endpoints[1].ias_zone
    listener = ClusterListener(motion)
    hdr, args = motion.deserialize(ZCL_IAS_MOTION_COMMAND)

    with mock.patch.object(motion, "reset_s", 0):
        motion.handle_message(hdr, args)
        await asyncio.sleep(0.05)

    assert not hasattr(device.endpoints[1], "occupancy")
    assert [command[2][0] for command in listener.cluster_commands] == [ON, OFF]


async def test_direct_motion_retrigger_cancels_the_first_reset(
    zigpy_device_from_quirk,
):
    """A retrigger must postpone both motion and occupancy reset timers."""
    device = zigpy_device_from_quirk(KonkeMotion)
    motion = device.endpoints[1].ias_zone
    occupancy = device.endpoints[1].occupancy
    motion_listener = ClusterListener(motion)
    occupancy_listener = ClusterListener(occupancy)
    hdr, args = motion.deserialize(ZCL_IAS_MOTION_COMMAND)

    with (
        mock.patch.object(motion, "reset_s", 0.1),
        mock.patch.object(occupancy, "reset_s", 0.1),
    ):
        motion.handle_message(hdr, args)
        await asyncio.sleep(0.03)
        motion.handle_message(hdr, args)
        await asyncio.sleep(0.08)

        assert [command[2][0] for command in motion_listener.cluster_commands] == [
            ON,
            ON,
        ]
        assert occupancy_listener.attribute_updates == [(0, 1), (0, 1)]

        await asyncio.sleep(0.06)

    assert [command[2][0] for command in motion_listener.cluster_commands] == [
        ON,
        ON,
        OFF,
    ]
    assert occupancy_listener.attribute_updates == [(0, 1), (0, 1), (0, 0)]


def test_smartthings_battery_report_updates_tracking_cluster(
    zigpy_device_from_quirk,
):
    """SmartThings battery reports must update the co-resident tracking cluster."""
    device = zigpy_device_from_quirk(SmartThingsTagV4)
    power = device.endpoints[1].power
    tracking = device.endpoints[1].binary_input
    tracking_listener = ClusterListener(tracking)

    power.update_attribute(PowerConfiguration.AttributeDefs.battery_voltage.id, 30)

    assert tracking_listener.attribute_updates == [(0, 1)]
    assert power.get(PowerConfiguration.AttributeDefs.battery_voltage.name) == 30


@pytest.mark.parametrize("quirk", (WAXMANleakSMARTv2, WAXMANleakSMARTv2NOPOLL))
def test_waxman_alerts_route_to_emulated_ias(zigpy_device_from_quirk, quirk):
    """Waxman wet and dry reports must be emitted by the emulated IAS cluster."""
    device = zigpy_device_from_quirk(quirk)
    source = device.endpoints[1].appliance_event
    target = device.endpoints[1].ias_zone
    listener = ClusterListener(target)

    source.handle_cluster_request(mock.Mock(command_id=1), [0, 0x1000])
    source.handle_cluster_request(mock.Mock(command_id=1), [0, 0])
    source.handle_cluster_request(mock.Mock(command_id=2), [0, 0x1000])

    assert [command[2] for command in listener.cluster_commands] == [[True], [False]]


def test_elko_reports_route_to_standard_clusters(zigpy_device_from_quirk):
    """Elko manufacturer attributes must update standard thermostat clusters."""
    device = zigpy_device_from_quirk(ElkoSuperTRThermostat)
    thermostat = device.endpoints[1].thermostat
    ui = device.endpoints[1].thermostat_ui
    electrical = device.endpoints[1].electrical_measurement

    thermostat.update_attribute(HEATING_ACTIVE, 1)
    assert thermostat.get(Thermostat.AttributeDefs.running_mode.name) == 4
    assert thermostat.get(Thermostat.AttributeDefs.running_state.name) == 1
    thermostat.update_attribute(HEATING_ACTIVE, 0)
    assert thermostat.get(Thermostat.AttributeDefs.running_mode.name) == 0
    assert thermostat.get(Thermostat.AttributeDefs.running_state.name) == 0

    thermostat.update_attribute(CHILD_LOCK, 1)
    assert ui.get(UserInterface.AttributeDefs.keypad_lockout.name) == 1
    thermostat.update_attribute(CHILD_LOCK, 0)
    assert ui.get(UserInterface.AttributeDefs.keypad_lockout.name) == 0

    thermostat.update_attribute(POWER_CONSUMPTION, 42)
    thermostat.update_attribute(POWER_CONSUMPTION, -1)
    assert electrical.get(ElectricalMeasurement.AttributeDefs.active_power.name) == 42


@pytest.mark.parametrize("quirk", (IkeaSTARKVIND, IkeaSTARKVIND_v2))
def test_starkvind_pm25_reports_route_to_pm25_cluster(zigpy_device_from_quirk, quirk):
    """Valid Starkvind manufacturer reports must update the PM2.5 cluster."""
    device = zigpy_device_from_quirk(quirk)
    source = device.endpoints[1].in_clusters[IkeaAirpurifier.cluster_id]
    target = device.endpoints[1].in_clusters[PM25.cluster_id]

    for value in (0, 42, 5499):
        source.update_attribute(
            IkeaAirpurifier.AttributeDefs.air_quality_25pm.id, value
        )
        assert target.get(PM25.AttributeDefs.measured_value.name) == value

    for value in (5500, 65535, None):
        source.update_attribute(
            IkeaAirpurifier.AttributeDefs.air_quality_25pm.id, value
        )
        assert target.get(PM25.AttributeDefs.measured_value.name) == 5499


@pytest.mark.parametrize("quirk", (TuyaVibration, TuyaVibration_TO))
async def test_tuya_vibration_report_triggers_motion(zigpy_device_from_quirk, quirk):
    """TS0210 source requests must trigger their IAS motion cluster directly."""
    device = zigpy_device_from_quirk(quirk)
    motion = device.endpoints[1].ias_zone
    listener = ClusterListener(motion)

    with mock.patch.object(motion, "reset_s", 0):
        motion.handle_cluster_request(mock.Mock(command_id=0), ())
        await asyncio.sleep(0.05)

    assert [command[2][0] for command in listener.cluster_commands] == [ON, OFF]


async def test_xiaomi_vibration_routes_motion_and_named_events(
    zigpy_device_from_quirk,
):
    """Xiaomi vibration reports must reach the co-resident IAS cluster."""
    device = zigpy_device_from_quirk(VibrationAQ1)
    source = device.endpoints[1].in_clusters[DoorLock.cluster_id]
    motion = device.endpoints[1].ias_zone
    motion_listener = ClusterListener(motion)
    event_listener = mock.MagicMock()
    motion.add_listener(event_listener)

    with mock.patch.object(motion, "reset_s", 0):
        source.update_attribute(STATUS_TYPE_ATTR, VIBE_VALUE)
        await asyncio.sleep(0.05)

    assert [command[2][0] for command in motion_listener.cluster_commands] == [ON, OFF]

    source.update_attribute(STATUS_TYPE_ATTR, DROP_VALUE)
    source.update_attribute(ROTATION_DEGREES_ATTR, 12)
    source.update_attribute(ORIENTATION_ATTR, 1 | (2 << 16) | (3 << 32))
    source.update_attribute(RECENT_ACTIVITY_LEVEL_ATTR, 0x341200)

    assert event_listener.zha_send_event.call_args_list == [
        mock.call("Drop", {}),
        mock.call("Drop", {"degrees": 12}),
        mock.call(
            "current_orientation",
            {
                "rawValueX": 1,
                "rawValueY": 2,
                "rawValueZ": 3,
                "X": 16,
                "Y": 32,
                "Z": 53,
            },
        ),
        mock.call("vibration_strength", {"strength": 0x1234}),
    ]

    event_listener.reset_mock()
    source.update_attribute(STATUS_TYPE_ATTR, 0)
    source.update_attribute(STATUS_TYPE_ATTR, 99)
    event_listener.zha_send_event.assert_not_called()
