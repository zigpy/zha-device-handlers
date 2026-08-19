"""Tests for Yale quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.closures import DoorLock, OperationEvent
from zigpy.zcl.foundation import Status

import zhaquirks
from zhaquirks.yale.new_locks import (
    FixedDoorLock,
    YaleCluster,
    YaleOperationEventSource,
)

zhaquirks.setup()


@pytest.fixture
def yale_lock_device(zigpy_device_from_v2_quirk):
    """Yale YDM60 zigpy device with the quirk applied."""
    return zigpy_device_from_v2_quirk(
        "Yale",
        "YDM60",
        cluster_ids={
            1: {
                DoorLock.cluster_id: ClusterType.Server,
                YaleCluster.cluster_id: ClusterType.Server,
            }
        },
    )


def test_yale_lock_clusters_replaced(yale_lock_device):
    """The DoorLock and proprietary clusters are replaced with the fixed versions."""
    ep = yale_lock_device.endpoints[1]

    assert isinstance(ep.door_lock, FixedDoorLock)
    assert isinstance(ep.yale_cluster, YaleCluster)


@pytest.mark.parametrize(
    ("server_command_name", "lock_method_name"),
    [
        ("lock_door", "lock_door"),
        ("unlock_door", "unlock_door"),
    ],
)
async def test_lock_door_status_ordering(
    yale_lock_device, server_command_name, lock_method_name
):
    """lock_door/unlock_door must return (status, command_id), not (command_id, status).

    zha's lock platform checks result[0] is not Status.SUCCESS, but the raw
    DefaultResponse fields are (command_id, status) in that order. Without the
    fix, result[0] is the command_id (usually 0), so every successful
    lock/unlock would be logged as an error.
    """
    ep = yale_lock_device.endpoints[1]
    cluster = ep.door_lock

    fake_response = mock.Mock(command_id=0, status=Status.SUCCESS)
    with mock.patch.object(
        cluster, "command", mock.AsyncMock(return_value=fake_response)
    ) as mock_command:
        result = await getattr(cluster, lock_method_name)()

    mock_command.assert_called_once()
    assert result[0] is Status.SUCCESS
    assert result[1] == 0


def test_operation_event_notification_decodes_yale_source_byte():
    """Yale's source byte decodes via YaleOperationEventSource.

    The standard (and far more limited) zigpy OperationEventSource enum
    would decode this as "undefined_0x04" instead.
    """
    schema = FixedDoorLock.ClientCommandDefs.operation_event_notification.schema

    # source=4 (fingerprint), code=2 (Unlock), user_id=1 (HA code_slot 2), pin="", local_time=0
    data = (
        bytes([0x04, OperationEvent.Unlock])
        + (1).to_bytes(2, "little")
        + b"\x00"
        + (0).to_bytes(4, "little")
    )
    decoded, remaining = schema.deserialize(data)

    assert decoded.operation_event_source == YaleOperationEventSource.FingerprintUnlock
    assert decoded.operation_event_code == OperationEvent.Unlock
    assert decoded.user_id == 1
    assert remaining == b""
