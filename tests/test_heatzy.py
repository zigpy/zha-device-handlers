"""Tests for Heatzy quirks."""

import asyncio
from unittest import mock

from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.heatzy.micro_duo import (
    BleOtaState,
    HeatzyBleOtaCluster,
    HeatzyBleOtaSwitch,
    HeatzyPilotWireCluster,
    PilotWireMode,
    _ble_ota_is_active,
)

zhaquirks.setup()


def test_micro_duo_custom_clusters(zigpy_device_from_v2_quirk) -> None:
    """The Micro Duo uses typed clusters for its pilot wire and BLE OTA APIs."""

    device = zigpy_device_from_v2_quirk(
        "Heatzy",
        "micro-duo",
        endpoint_ids=[1, 10, 11, 242],
        cluster_ids={
            1: {HeatzyPilotWireCluster.cluster_id: ClusterType.Server},
            11: {HeatzyBleOtaCluster.cluster_id: ClusterType.Server},
        },
    )

    pilot_wire = device.endpoints[1].in_clusters[HeatzyPilotWireCluster.cluster_id]
    ble_ota = device.endpoints[11].in_clusters[HeatzyBleOtaCluster.cluster_id]

    assert isinstance(pilot_wire, HeatzyPilotWireCluster)
    assert (
        pilot_wire.find_attribute("mode") == HeatzyPilotWireCluster.AttributeDefs.mode
    )
    assert HeatzyPilotWireCluster.AttributeDefs.mode.type is PilotWireMode

    assert isinstance(ble_ota, HeatzyBleOtaCluster)
    assert ble_ota.find_attribute("state") == HeatzyBleOtaCluster.AttributeDefs.state
    assert HeatzyBleOtaCluster.AttributeDefs.state.type is BleOtaState
    assert HeatzyBleOtaCluster.ServerCommandDefs.start_ble_ota.id == 0x00
    assert HeatzyBleOtaCluster.ServerCommandDefs.stop_ble_ota.id == 0x01


def test_micro_duo_ble_ota_switch() -> None:
    """The BLE OTA switch sends commands and follows the reported state."""

    switch = object.__new__(HeatzyBleOtaSwitch)
    switch._cluster = mock.Mock()
    switch._cluster.command = mock.AsyncMock()

    assert _ble_ota_is_active(BleOtaState.Disabled) is False
    assert _ble_ota_is_active(BleOtaState.Receiving) is True

    asyncio.run(switch.async_turn_on_off(True))
    switch._cluster.command.assert_awaited_once_with(0x00)

    switch._cluster.command.reset_mock()
    asyncio.run(switch.async_turn_on_off(False))
    switch._cluster.command.assert_awaited_once_with(0x01)
