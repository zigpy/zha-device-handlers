"""Tests for Heatzy quirks."""

from unittest import mock

from zigpy.zcl import ClusterType
from zigpy.zcl.foundation import DataTypeId

import zhaquirks
from zhaquirks.heatzy.micro_duo import (
    BleOtaState,
    HeatzyBleOtaCluster,
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
    assert HeatzyPilotWireCluster.AttributeDefs.mode.zcl_type is DataTypeId.uint8
    assert HeatzyPilotWireCluster.AttributeDefs.mode.manufacturer_code is None

    assert isinstance(ble_ota, HeatzyBleOtaCluster)
    assert ble_ota.find_attribute("state") == HeatzyBleOtaCluster.AttributeDefs.state
    assert HeatzyBleOtaCluster.AttributeDefs.state.type is BleOtaState
    assert HeatzyBleOtaCluster.AttributeDefs.state.zcl_type is DataTypeId.uint8
    assert HeatzyBleOtaCluster.AttributeDefs.state.manufacturer_code is None
    assert HeatzyBleOtaCluster.ServerCommandDefs.start_ble_ota.id == 0x00
    assert HeatzyBleOtaCluster.ServerCommandDefs.stop_ble_ota.id == 0x01
    assert HeatzyBleOtaCluster.ServerCommandDefs.start_ble_ota.manufacturer_code is None
    assert HeatzyBleOtaCluster.ServerCommandDefs.stop_ble_ota.manufacturer_code is None


async def test_micro_duo_ble_ota_switch() -> None:
    """The BLE OTA switch sends commands and follows the reported state."""

    cluster = object.__new__(HeatzyBleOtaCluster)
    cluster.command = mock.AsyncMock()
    cluster.read_attributes = mock.AsyncMock()
    cluster._update_attribute = mock.Mock()

    assert _ble_ota_is_active(BleOtaState.Disabled) is False
    assert _ble_ota_is_active(BleOtaState.Receiving) is True

    await HeatzyBleOtaCluster.write_attributes(cluster, {"enabled": True})
    cluster.command.assert_awaited_once_with(0x00)
    cluster.read_attributes.assert_awaited_once_with([0x0000])
    cluster._update_attribute.assert_called_once_with(0x0001, True)

    cluster.command.reset_mock()
    cluster.read_attributes.reset_mock()
    cluster._update_attribute.reset_mock()
    await HeatzyBleOtaCluster.write_attributes(cluster, {"enabled": False})
    cluster.command.assert_awaited_once_with(0x01)
    cluster.read_attributes.assert_awaited_once_with([0x0000])
    cluster._update_attribute.assert_called_once_with(0x0001, False)
