"""Tests for Sonoff quirks."""

import json
from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.security import IasZone

from tests import zha_helpers
from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.const import COMMAND_DOUBLE, COMMAND_HOLD, COMMAND_SINGLE, COMMAND_TRIPLE
from zhaquirks.sonoff.snzb01m import SonoffButtonCluster
from zhaquirks.sonoff.snzb06p import (
    IlluminationStatus,
    SonoffFC11Cluster,
    SonoffLastIlluminationStateSensor,
    SonoffPresenceSensorInitWithoutRead,
)
from zhaquirks.sonoff.zbm5 import (
    SonoffCluster,
    SonoffDetachedRelayMask,
    SonoffInputConfigCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("mask", "expected_states"),
    [
        (
            SonoffDetachedRelayMask.Relay1,
            (True, False, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2,
            (True, True, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1
            | SonoffDetachedRelayMask.Relay2
            | SonoffDetachedRelayMask.Relay3,
            (True, True, True),
        ),
    ],
    ids=["relay1", "relay1+2", "relay1+2+3"],
)
async def test_sonoff_zbm5_relay_mask_propagation(
    zigpy_device_from_v2_quirk, mask, expected_states
):
    """Test relay mask updates propagate to local cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            },
            2: {OnOff.cluster_id: ClusterType.Server},
            3: {OnOff.cluster_id: ClusterType.Server},
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    sonoff_listener = ClusterListener(sonoff_cluster)
    local_listener = ClusterListener(local_cluster)

    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    sonoff_cluster.update_attribute(detach_mask_attr, mask)

    assert len(sonoff_listener.attribute_updates) == 1
    assert sonoff_listener.attribute_updates[0][0] == detach_mask_attr

    assert len(local_listener.attribute_updates) == 3
    assert local_listener.attribute_updates[0] == (relay_1_attr, expected_states[0])
    assert local_listener.attribute_updates[1] == (relay_2_attr, expected_states[1])
    assert local_listener.attribute_updates[2] == (relay_3_attr, expected_states[2])


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test writing relay attributes translates to mask write and updates local state."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    # Mock at the low level so real write_attributes runs and emits events
    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

        # Verify mask was written to device
        assert mock_write.call_count == 1
        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1
        assert (
            written_attrs[0].attrid == SonoffCluster.AttributeDefs.detach_relay_mask.id
        )

        # Verify local relay states updated via AttributeWrittenEvent
        relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
        relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
        relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

        assert local_listener.attribute_updates[0] == (relay_1_attr, True)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)

        # Write relay_1_detached = False to test clearing a bit
        local_listener.attribute_updates.clear()
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: False}
        )

        written_attrs = mock_write.call_args[0][0]
        assert written_attrs[0].value.value == SonoffDetachedRelayMask(0)

        assert local_listener.attribute_updates[0] == (relay_1_attr, False)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)


async def test_sonoff_cluster_failed_write_does_not_propagate(
    zigpy_device_from_v2_quirk,
):
    """Test that a failed mask write does not update local relay states."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    # Mock a failed write
    write_response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=SonoffCluster.AttributeDefs.detach_relay_mask.id,
            )
        ]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ):
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

    # Local relay states should not have been updated
    assert len(local_listener.attribute_updates) == 0


async def test_sonoff_cluster_apply_custom_configuration(zigpy_device_from_v2_quirk):
    """Test apply_custom_configuration reads mask and populates local relay states."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    mask_attr = SonoffCluster.AttributeDefs.detach_relay_mask
    mask = SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2

    # Mock raw ZCL read so the full read_attributes chain runs and fires events
    read_response = foundation.ReadAttributeRecord(
        attrid=mask_attr.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(type=mask_attr.zcl_type, value=mask),
    )
    with mock.patch.object(
        sonoff_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=[[read_response]]),
    ):
        await sonoff_cluster.apply_custom_configuration()

    # Verify local relay states were populated from the read
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    assert local_listener.attribute_updates[0] == (relay_1_attr, True)
    assert local_listener.attribute_updates[1] == (relay_2_attr, True)
    assert local_listener.attribute_updates[2] == (relay_3_attr, False)


@pytest.mark.parametrize("endpoint_id", [1, 2, 3, 4])
@pytest.mark.parametrize(
    ("value", "expected_command"),
    [
        (1, COMMAND_SINGLE),
        (2, COMMAND_DOUBLE),
        (3, COMMAND_HOLD),
        (4, COMMAND_TRIPLE),
    ],
)
async def test_snzb01m_button_events(
    zigpy_device_from_v2_quirk, endpoint_id, value, expected_command
):
    """Correct events are emitted for each endpoint and action."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[endpoint_id].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(
        SonoffButtonCluster.AttributeDefs.key_action_event.id, value
    )
    assert listener.zha_send_event.call_count == 1
    listener.zha_send_event.assert_called_with(expected_command, {})


async def test_snzb01m_invalid_attribute_update(zigpy_device_from_v2_quirk):
    """Invalid attribute values should not emit events."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(SonoffButtonCluster.AttributeDefs.key_action_event.id, 99)
    assert listener.zha_send_event.call_count == 0


async def test_snzb01m_non_button_attribute_update(zigpy_device_from_v2_quirk):
    """Non-button attributes must not generate button events."""

    device = zigpy_device_from_v2_quirk("SONOFF", "SNZB-01M", endpoint_ids=[1, 2, 3, 4])
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(0x0001, 1)
    assert listener.zha_send_event.call_count == 0


def _snzb06p_fc11_cluster(zigpy_device_from_v2_quirk):
    """Return the quirked 0xFC11 cluster of an SNZB-06P."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-06P",
        cluster_ids={
            1: {
                IasZone.cluster_id: ClusterType.Server,
                SonoffFC11Cluster.cluster_id: ClusterType.Server,
            }
        },
    )
    cluster = device.endpoints[1].sonoff_manufacturer
    assert isinstance(cluster, SonoffFC11Cluster)
    return cluster


# Report Attributes, server to client, no manufacturer code:
# last_illumination_state (0x2001, enum8) = Light
SNZB06P_ILLUMINATION_REPORT = bytes.fromhex("18010a01203001")


async def test_snzb06p_illumination_report_without_manufacturer_code(
    zigpy_device_from_v2_quirk,
):
    """The device reports 0x2001 without a manufacturer code, it must be cached."""
    cluster = _snzb06p_fc11_cluster(zigpy_device_from_v2_quirk)
    listener = ClusterListener(cluster)

    hdr, args = cluster.deserialize(SNZB06P_ILLUMINATION_REPORT)
    assert not hdr.frame_control.is_manufacturer_specific
    cluster.handle_message(hdr, args)

    attr_id = SonoffFC11Cluster.AttributeDefs.last_illumination_state.id
    assert listener.attribute_updates == [(attr_id, IlluminationStatus.Light)]
    assert cluster.get("last_illumination_state") == IlluminationStatus.Light


async def test_snzb06p_illumination_read_without_manufacturer_code(
    zigpy_device_from_v2_quirk,
):
    """0x2001 is read without a manufacturer code, and a report clears its unsupported mark."""
    cluster = _snzb06p_fc11_cluster(zigpy_device_from_v2_quirk)
    attr_id = SonoffFC11Cluster.AttributeDefs.last_illumination_state.id

    # Without presence, the device answers reads of 0x2001 with UNSUPPORTED_ATTRIBUTE
    read_mock = mock.AsyncMock(
        return_value=(
            [
                foundation.ReadAttributeRecord(
                    attr_id, foundation.Status.UNSUPPORTED_ATTRIBUTE
                )
            ],
        )
    )
    with mock.patch.object(cluster, "_read_attributes", read_mock):
        await cluster.read_attributes(["last_illumination_state"])

    assert read_mock.await_count == 1
    assert read_mock.await_args.kwargs["manufacturer"] is None
    assert cluster.is_attribute_unsupported("last_illumination_state")

    # The next report from the device stores the value and clears the mark
    hdr, args = cluster.deserialize(SNZB06P_ILLUMINATION_REPORT)
    cluster.handle_message(hdr, args)

    assert not cluster.is_attribute_unsupported("last_illumination_state")
    assert cluster.get("last_illumination_state") == IlluminationStatus.Light


SNZB06P_DIAGNOSTICS = "sonoff-snzb-06p-0x00001006.json"
SNZB06P_ILLUMINATION_UNIQUE_ID = "ab:cd:ef:12:dd:23:ca:15-1-64529-last_illumination"
ILLUMINATION_ATTR = SonoffFC11Cluster.AttributeDefs.last_illumination_state


def _snzb06p_diagnostics(tmp_path, monkeypatch, fc11_attributes: list) -> None:
    """Use the SNZB-06P diagnostics with the given 0xFC11 attributes."""
    data = json.loads((zha_helpers.DEVICES_DIR / SNZB06P_DIAGNOSTICS).read_text())
    (fc11,) = (
        cluster
        for cluster in data["endpoints"]["1"]["in_clusters"]
        if cluster["cluster_id"] == "0xfc11"
    )
    fc11["attributes"] = fc11_attributes
    (tmp_path / SNZB06P_DIAGNOSTICS).write_text(json.dumps(data))
    monkeypatch.setattr(zha_helpers, "DEVICES_DIR", tmp_path)


def _illumination_reads(cluster) -> int:
    """Count the reads of 0x2001 sent to the device."""
    return sum(
        ILLUMINATION_ATTR.id in call.args[0]
        for call in cluster.read_attributes_raw.await_args_list
    )


async def test_snzb06p_illumination_sensor_with_unsupported_mark(tmp_path, monkeypatch):
    """The illumination sensor is kept when a read marked 0x2001 unsupported."""
    # Diagnostics of a device whose read of 0x2001 was answered with
    # UNSUPPORTED_ATTRIBUTE before a value was reported, like the one in #5473
    _snzb06p_diagnostics(
        tmp_path,
        monkeypatch,
        [
            {
                "id": "0x2001",
                "name": "last_illumination_state",
                "zcl_type": "enum8",
                "unsupported": True,
            }
        ],
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, SNZB06P_DIAGNOSTICS, DEVICE_REGISTRY
        )
        cluster = device.device.endpoints[1].sonoff_manufacturer
        assert isinstance(cluster, SonoffFC11Cluster)
        assert cluster.is_attribute_unsupported("last_illumination_state")

        # The quirk's sensor replaces ZHA's, with the same unique ID, and has no value
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id=SNZB06P_ILLUMINATION_UNIQUE_ID
        )
        assert type(entity) is SonoffLastIlluminationStateSensor
        assert entity.native_value is None

        # The device reports the illumination after detecting presence
        hdr, args = cluster.deserialize(SNZB06P_ILLUMINATION_REPORT)
        cluster.handle_message(hdr, args)
        assert not cluster.is_attribute_unsupported("last_illumination_state")
        assert entity.native_value == IlluminationStatus.Light.name

        # A manual read answered with UNSUPPORTED_ATTRIBUTE still marks the attribute,
        # the sensor stays but is unknown until the next report
        cluster.read_attributes_raw = mock.AsyncMock(
            return_value=(
                [
                    foundation.ReadAttributeRecord(
                        ILLUMINATION_ATTR.id, foundation.Status.UNSUPPORTED_ATTRIBUTE
                    )
                ],
            )
        )
        await cluster.read_attributes(["last_illumination_state"], allow_cache=False)
        assert cluster.read_attributes_raw.await_count == 1
        assert cluster.is_attribute_unsupported("last_illumination_state")
        assert entity.is_supported()
        assert (
            device.get_platform_entity(
                Platform.SENSOR, unique_id=SNZB06P_ILLUMINATION_UNIQUE_ID
            )
            is entity
        )
        assert entity.native_value is None

        cluster.handle_message(hdr, args)
        assert entity.native_value == IlluminationStatus.Light.name


async def test_snzb06p_illumination_state_not_read(tmp_path, monkeypatch):
    """ZHA doesn't read 0x2001 when nothing is cached for it."""
    _snzb06p_diagnostics(tmp_path, monkeypatch, [])

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, SNZB06P_DIAGNOSTICS, DEVICE_REGISTRY
        )
        cluster = device.device.endpoints[1].sonoff_manufacturer
        assert cluster.get("last_illumination_state") is None

        # ZHA still binds the cluster, so the device keeps reporting
        assert cluster.bind.await_count == 1

        # Not read when joining, nor when initializing from the device (mains startup)
        assert _illumination_reads(cluster) == 0
        await device.async_initialize(from_cache=False)
        assert _illumination_reads(cluster) == 0
        assert any(
            type(entity) is SonoffPresenceSensorInitWithoutRead
            for entity in device._discovered_entities
        )

        # The sensor exists and gets its value from the next report
        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id=SNZB06P_ILLUMINATION_UNIQUE_ID
        )
        assert entity.native_value is None
        hdr, args = cluster.deserialize(SNZB06P_ILLUMINATION_REPORT)
        cluster.handle_message(hdr, args)
        assert entity.native_value == IlluminationStatus.Light.name
