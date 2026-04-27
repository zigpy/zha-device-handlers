"""Tests for Develco/Frient IO module quirk."""

import asyncio
from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import BinaryInput, OnOff

from zhaquirks.develco.io_module import (
    FrientBinaryInput,
    FrientOnOffOutput,
    LinkedOutput,
)


def _get_io_module_device(zigpy_device_from_v2_quirk):
    """Create a quirked IO module device with all input/output endpoints."""
    return zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="IOMZB-110",
        endpoint_ids=[112, 113, 114, 115, 116, 117],
        cluster_ids={
            112: {BinaryInput.cluster_id: ClusterType.Server},
            113: {BinaryInput.cluster_id: ClusterType.Server},
            114: {BinaryInput.cluster_id: ClusterType.Server},
            115: {BinaryInput.cluster_id: ClusterType.Server},
            116: {
                BinaryInput.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            },
            117: {
                BinaryInput.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            },
        },
    )


async def test_io_module_input_link_sends_on_and_off_commands(
    zigpy_device_from_v2_quirk,
):
    """Test input changes send On/Off commands when timed mode is disabled."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)

    input_cluster = device.endpoints[112].binary_input
    output_cluster = device.endpoints[116].on_off

    assert isinstance(input_cluster, FrientBinaryInput)

    result = await input_cluster.write_attributes(
        {FrientBinaryInput.AttributeDefs.linked_output.name: LinkedOutput.output_1}
    )
    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]

    with mock.patch.object(
        output_cluster, "command", new=mock.AsyncMock(return_value="ok")
    ) as command_mock:
        input_cluster._update_attribute(
            input_cluster.AttributeDefs.present_value.id,
            1,
        )
        await asyncio.sleep(0)

        input_cluster._update_attribute(
            input_cluster.AttributeDefs.present_value.id,
            0,
        )
        await asyncio.sleep(0)

    assert command_mock.await_count == 2
    assert command_mock.await_args_list[0].args[0] == OnOff.ServerCommandDefs.on.id
    assert command_mock.await_args_list[1].args[0] == OnOff.ServerCommandDefs.off.id


async def test_io_module_input_without_link_does_not_toggle_output(
    zigpy_device_from_v2_quirk,
):
    """Test input changes do not trigger local output commands when link is unset."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)

    input_cluster = device.endpoints[113].binary_input
    output_1_cluster = device.endpoints[116].on_off
    output_2_cluster = device.endpoints[117].on_off

    with (
        mock.patch.object(
            output_1_cluster, "command", new=mock.AsyncMock(return_value="ok")
        ) as output_1_mock,
        mock.patch.object(
            output_2_cluster, "command", new=mock.AsyncMock(return_value="ok")
        ) as output_2_mock,
    ):
        input_cluster._update_attribute(
            input_cluster.AttributeDefs.present_value.id,
            1,
        )
        await asyncio.sleep(0)

    output_1_mock.assert_not_awaited()
    output_2_mock.assert_not_awaited()


async def test_io_module_reverse_polarity_write_does_not_immediately_send_output_command(
    zigpy_device_from_v2_quirk,
):
    """Test reverse polarity write itself does not emit an OnOff output command."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)

    input_cluster = device.endpoints[114].binary_input
    output_cluster = device.endpoints[116].on_off

    await input_cluster.write_attributes(
        {FrientBinaryInput.AttributeDefs.linked_output.name: LinkedOutput.output_1}
    )

    with mock.patch.object(
        output_cluster, "command", new=mock.AsyncMock(return_value="ok")
    ) as command_mock:
        with mock.patch.object(
            BinaryInput,
            "write_attributes",
            new=mock.AsyncMock(
                return_value=[
                    [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
                ]
            ),
        ):
            result = await input_cluster.write_attributes(
                {FrientBinaryInput.AttributeDefs.polarity.name: True}
            )
        assert result == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]
        await asyncio.sleep(0)

    command_mock.assert_not_awaited()


async def test_io_module_polarity_uses_standard_attribute_id(
    zigpy_device_from_v2_quirk,
):
    """Test polarity writes are delegated to the real BinaryInput attribute."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[115].binary_input

    with mock.patch.object(
        BinaryInput,
        "write_attributes",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_mock:
        await input_cluster.write_attributes({"polarity": True})

    write_mock.assert_awaited_once()
    assert write_mock.await_args.args[0] == {"polarity": True}


async def test_io_module_on_with_timed_off_settings_are_local_on_outputs(
    zigpy_device_from_v2_quirk,
):
    """Test output-timed settings are stored locally by the quirk."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    output_settings_cluster = device.endpoints[0x74].binary_input

    with mock.patch.object(
        BinaryInput,
        "write_attributes",
        new=mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as write_mock:
        result = await output_settings_cluster.write_attributes(
            {
                FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.name: 30,
                FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.name: 5,
            }
        )

    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    write_mock.assert_not_awaited()
    assert (
        output_settings_cluster.get(
            FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.id
        )
        == 30
    )
    assert (
        output_settings_cluster.get(
            FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.id
        )
        == 5
    )


async def test_io_module_read_attributes_raw_local_only_does_not_delegate(
    zigpy_device_from_v2_quirk,
):
    """Test local linked_output reads are served from cache without delegation."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input
    local_attr_name = FrientBinaryInput.AttributeDefs.linked_output.name
    local_attr_id = FrientBinaryInput.AttributeDefs.linked_output.id

    await input_cluster.write_attributes({local_attr_name: LinkedOutput.output_2})

    with mock.patch.object(
        BinaryInput,
        "read_attributes_raw",
        new=mock.AsyncMock(),
    ) as read_mock:
        (records,) = await input_cluster.read_attributes_raw([local_attr_name])

    read_mock.assert_not_awaited()
    assert len(records) == 1
    assert records[0].attrid == local_attr_id
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == LinkedOutput.output_2


async def test_io_module_read_attributes_raw_mixed_delegates_remote(
    zigpy_device_from_v2_quirk,
):
    """Test mixed local/remote reads delegate only remote attributes."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input
    local_attr_id = FrientBinaryInput.AttributeDefs.linked_output.id
    remote_attr_id = BinaryInput.AttributeDefs.present_value.id

    await input_cluster.write_attributes({local_attr_id: LinkedOutput.output_1})

    delegated_record = foundation.ReadAttributeRecord(
        remote_attr_id,
        foundation.Status.SUCCESS,
        foundation.TypeValue(),
    )
    delegated_record.value.value = 1

    with mock.patch.object(
        BinaryInput,
        "read_attributes_raw",
        new=mock.AsyncMock(return_value=([delegated_record],)),
    ) as read_mock:
        (records,) = await input_cluster.read_attributes_raw(
            [local_attr_id, remote_attr_id],
            manufacturer=0x1234,
        )

    read_mock.assert_awaited_once()
    assert read_mock.await_args.args[0] == [remote_attr_id]
    assert read_mock.await_args.kwargs["manufacturer"] == 0x1234
    assert {record.attrid for record in records} == {local_attr_id, remote_attr_id}


async def test_io_module_write_attributes_unknown_key_raises(
    zigpy_device_from_v2_quirk,
):
    """Test unknown write keys fail early instead of delegating."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input

    with (
        mock.patch.object(
            BinaryInput,
            "write_attributes",
            new=mock.AsyncMock(),
        ) as write_mock,
        pytest.raises(KeyError, match="Unknown attribute"),
    ):
        await input_cluster.write_attributes({"does_not_exist": 1})

    write_mock.assert_not_awaited()


async def test_io_module_nonzero_on_time_uses_on_with_timed_off_command(
    zigpy_device_from_v2_quirk,
):
    """Test non-zero OnTime uses OnWithTimedOff instead of On/Off commands."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input
    output_cluster = device.endpoints[0x74].on_off
    output_settings_cluster = device.endpoints[0x74].binary_input

    await input_cluster.write_attributes({"linked_output": LinkedOutput.output_1})
    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.id,
        30,
    )
    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.id,
        5,
    )

    with mock.patch.object(
        output_cluster,
        "command",
        new=mock.AsyncMock(return_value="ok"),
    ) as command_mock:
        input_cluster._update_attribute(BinaryInput.AttributeDefs.present_value.id, 1)
        await asyncio.sleep(0)
        input_cluster._update_attribute(BinaryInput.AttributeDefs.present_value.id, 0)
        await asyncio.sleep(0)

    command_mock.assert_awaited_once()
    assert (
        command_mock.await_args.args[0] == OnOff.ServerCommandDefs.on_with_timed_off.id
    )
    assert command_mock.await_args.kwargs["on_time"] == 30
    assert command_mock.await_args.kwargs["off_wait_time"] == 5


async def test_io_module_output_timed_settings_are_shared_for_any_linked_input(
    zigpy_device_from_v2_quirk,
):
    """Test output timed settings are shared by all inputs linked to same output."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_1_cluster = device.endpoints[0x70].binary_input
    input_2_cluster = device.endpoints[0x71].binary_input
    output_settings_cluster = device.endpoints[0x74].binary_input

    await input_1_cluster.write_attributes({"linked_output": LinkedOutput.output_1})
    await input_2_cluster.write_attributes({"linked_output": LinkedOutput.output_1})
    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.id,
        42,
    )
    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.id,
        7,
    )

    with mock.patch.object(
        OnOff,
        "command",
        new=mock.AsyncMock(return_value="ok"),
    ) as command_mock:
        input_1_cluster._update_attribute(BinaryInput.AttributeDefs.present_value.id, 1)
        await asyncio.sleep(0)
        input_2_cluster._update_attribute(BinaryInput.AttributeDefs.present_value.id, 1)
        await asyncio.sleep(0)

    assert command_mock.await_count == 2
    assert command_mock.await_args_list[0].kwargs["on_time"] == 42
    assert command_mock.await_args_list[0].kwargs["off_wait_time"] == 7
    assert command_mock.await_args_list[1].kwargs["on_time"] == 42
    assert command_mock.await_args_list[1].kwargs["off_wait_time"] == 7


async def test_output_entity_on_uses_on_with_timed_off_when_configured(
    zigpy_device_from_v2_quirk,
):
    """Test manual output ON uses OnWithTimedOff when output OnTime is non-zero."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    output_cluster = device.endpoints[0x74].on_off
    output_settings_cluster = device.endpoints[0x74].binary_input

    assert isinstance(output_cluster, FrientOnOffOutput)

    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.id,
        25,
    )
    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.id,
        3,
    )

    with mock.patch.object(
        OnOff, "command", new=mock.AsyncMock(return_value="ok")
    ) as command_mock:
        await output_cluster.command(OnOff.ServerCommandDefs.on.id)

    command_mock.assert_awaited_once()
    assert (
        command_mock.await_args.args[0] == OnOff.ServerCommandDefs.on_with_timed_off.id
    )
    assert command_mock.await_args.kwargs["on_time"] == 25
    assert command_mock.await_args.kwargs["off_wait_time"] == 3


async def test_output_entity_repeated_on_uses_command_only_behavior(
    zigpy_device_from_v2_quirk,
):
    """Test repeated output ON always forwards commands (no software lockout)."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    output_cluster = device.endpoints[0x74].on_off
    output_settings_cluster = device.endpoints[0x74].binary_input

    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_on_time.id,
        25,
    )
    output_settings_cluster._update_attribute(
        FrientBinaryInput.AttributeDefs.on_with_timed_off_off_wait_time.id,
        3,
    )

    with mock.patch.object(
        OnOff, "command", new=mock.AsyncMock(return_value="ok")
    ) as command_mock:
        await output_cluster.command(OnOff.ServerCommandDefs.on.id)
        await output_cluster.command(OnOff.ServerCommandDefs.on.id)

    assert command_mock.await_count == 2


async def test_output_entity_off_passthrough(
    zigpy_device_from_v2_quirk,
):
    """Test OFF command is passed through without remapping."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    output_cluster = device.endpoints[0x74].on_off

    with mock.patch.object(
        OnOff, "command", new=mock.AsyncMock(return_value="ok")
    ) as command_mock:
        await output_cluster.command(OnOff.ServerCommandDefs.off.id)

    command_mock.assert_awaited_once()
    assert command_mock.await_args.args[0] == OnOff.ServerCommandDefs.off.id


def test_io_module_polarity_does_not_locally_transform_input_state(
    zigpy_device_from_v2_quirk,
):
    """Test polarity changes do not locally alter BinaryInput present_value."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input

    input_cluster._update_attribute(BinaryInput.AttributeDefs.present_value.id, 1)
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.id) == 1

    input_cluster._update_attribute(BinaryInput.AttributeDefs.polarity.id, 1)
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.id) == 1

    input_cluster._update_attribute(BinaryInput.AttributeDefs.polarity.id, 0)
    assert input_cluster.get(BinaryInput.AttributeDefs.present_value.id) == 1


async def test_io_module_link_selector_sends_bind_request(
    zigpy_device_from_v2_quirk,
):
    """Test selecting linked output sends a bind request to that output endpoint."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input

    with mock.patch.object(
        device.zdo,
        "Bind_req",
        new=mock.AsyncMock(return_value=(foundation.Status.SUCCESS, None)),
    ) as bind_mock:
        await input_cluster.write_attributes({"linked_output": LinkedOutput.output_1})
        await asyncio.sleep(0)

    bind_mock.assert_awaited_once()
    assert bind_mock.await_args.args[0] == device.ieee
    assert bind_mock.await_args.args[1] == 0x70
    assert bind_mock.await_args.args[2] == BinaryInput.cluster_id
    destination = bind_mock.await_args.args[3]
    assert destination.addrmode == 0x03
    assert destination.ieee == device.ieee
    assert destination.endpoint == 0x74


async def test_io_module_link_selector_sends_unbind_request(
    zigpy_device_from_v2_quirk,
):
    """Test disabling a linked output sends an unbind request for the old link."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)
    input_cluster = device.endpoints[0x70].binary_input

    await input_cluster.write_attributes({"linked_output": LinkedOutput.output_1})

    with mock.patch.object(
        device.zdo,
        "Unbind_req",
        new=mock.AsyncMock(return_value=(foundation.Status.SUCCESS, None)),
    ) as unbind_mock:
        await input_cluster.write_attributes({"linked_output": LinkedOutput.none})
        await asyncio.sleep(0)

    unbind_mock.assert_awaited_once()
    assert unbind_mock.await_args.args[0] == device.ieee
    assert unbind_mock.await_args.args[1] == 0x70
    assert unbind_mock.await_args.args[2] == BinaryInput.cluster_id
    destination = unbind_mock.await_args.args[3]
    assert destination.addrmode == 0x03
    assert destination.ieee == device.ieee
    assert destination.endpoint == 0x74


def test_io_module_link_selectors_are_exposed_for_all_inputs(
    zigpy_device_from_v2_quirk,
):
    """Test each input endpoint exposes a linked output selector entity."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)

    expected = {
        112: "in1_linked_output",
        113: "in2_linked_output",
        114: "in3_linked_output",
        115: "in4_linked_output",
    }

    for endpoint_id, expected_suffix in expected.items():
        metadata = device.exposes_metadata[
            (endpoint_id, BinaryInput.cluster_id, ClusterType.Server)
        ]
        suffixes = {entity.unique_id_suffix for entity in metadata}
        assert expected_suffix in suffixes


def test_io_module_reverse_polarity_switches_are_exposed_for_all_inputs(
    zigpy_device_from_v2_quirk,
):
    """Test each input endpoint exposes a reverse polarity switch entity."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)

    expected = {
        112: "in1_reverse_polarity",
        113: "in2_reverse_polarity",
        114: "in3_reverse_polarity",
        115: "in4_reverse_polarity",
    }

    for endpoint_id, expected_suffix in expected.items():
        metadata = device.exposes_metadata[
            (endpoint_id, BinaryInput.cluster_id, ClusterType.Server)
        ]
        suffixes = {entity.unique_id_suffix for entity in metadata}
        assert expected_suffix in suffixes


def test_io_module_timed_off_numbers_are_exposed_for_all_outputs(
    zigpy_device_from_v2_quirk,
):
    """Test each output endpoint exposes OnWithTimedOff timing settings."""
    device = _get_io_module_device(zigpy_device_from_v2_quirk)

    expected_suffixes = {
        116: {
            "out1_on_with_timed_off_on_time",
            "out1_on_with_timed_off_off_wait_time",
        },
        117: {
            "out2_on_with_timed_off_on_time",
            "out2_on_with_timed_off_off_wait_time",
        },
    }

    for endpoint_id, expected in expected_suffixes.items():
        metadata = device.exposes_metadata[
            (endpoint_id, BinaryInput.cluster_id, ClusterType.Server)
        ]
        suffixes = {entity.unique_id_suffix for entity in metadata}
        assert expected.issubset(suffixes)
        assert f"{endpoint_id}-15" not in suffixes
