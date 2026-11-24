"""Tests for the SONOFF S61SZBTPB quirk."""

from unittest.mock import AsyncMock, patch

import pytest
from zigpy.zcl import foundation

import zhaquirks
from zhaquirks.sonoff import s61szbtpb

zhaquirks.setup()


@pytest.fixture
def sonoff_cluster():
    """Create a cluster instance without a full zigpy device graph."""
    cluster = object.__new__(s61szbtpb.SonoffCustomCluster)
    return cluster


def _status_record():
    """Return a successful write status record payload."""
    return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


@pytest.mark.parametrize(
    ("attribute_key", "expected"),
    [
        pytest.param(
            s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload,
            True,
            id="attribute_def",
        ),
        pytest.param(
            s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload.id,
            True,
            id="attribute_id",
        ),
        pytest.param(
            s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload.name,
            True,
            id="attribute_name",
        ),
        pytest.param("unknown", False, id="unknown_attribute"),
    ],
)
def test_has_attribute_supports_multiple_attribute_key_types(
    sonoff_cluster, attribute_key, expected
):
    """Attribute lookup accepts attribute definitions, ids, and names."""
    attr_def = s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload

    assert sonoff_cluster._has_attribute({attribute_key: 15000}, attr_def) is expected


@pytest.mark.asyncio
async def test_bind_enables_current_and_power_protection(sonoff_cluster):
    """Bind writes the non-user exposed enable flags."""
    with (
        patch.object(
            s61szbtpb.CustomCluster,
            "bind",
            AsyncMock(return_value="bind_result"),
        ) as super_bind,
        patch.object(
            sonoff_cluster,
            "write_attributes",
            AsyncMock(return_value=_status_record()),
        ) as write_attributes,
    ):
        result = await sonoff_cluster.bind()

    assert result == "bind_result"
    super_bind.assert_awaited_once()
    write_attributes.assert_awaited_once_with(
        s61szbtpb.SonoffCustomCluster.enable_config
    )


@pytest.mark.asyncio
async def test_write_current_threshold_enables_current_protection_first(sonoff_cluster):
    """Writing the current threshold auto-enables its protection flag first."""
    attributes = {
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload.name: 15000
    }

    with patch.object(
        s61szbtpb.CustomCluster,
        "write_attributes",
        AsyncMock(side_effect=[_status_record(), _status_record()]),
    ) as super_write:
        await sonoff_cluster.write_attributes(attributes)

    assert super_write.await_count == 2
    first_call = super_write.await_args_list[0]
    second_call = super_write.await_args_list[1]

    assert (
        first_call.args[0][
            s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload_enable.id
        ]
        == 0x01
    )
    assert second_call.args[0] == attributes


@pytest.mark.asyncio
async def test_write_power_threshold_enables_power_protection_first(sonoff_cluster):
    """Writing the power threshold auto-enables its protection flag first."""
    attributes = {
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_power_max_overload.name: 2500000
    }

    with patch.object(
        s61szbtpb.CustomCluster,
        "write_attributes",
        AsyncMock(side_effect=[_status_record(), _status_record()]),
    ) as super_write:
        await sonoff_cluster.write_attributes(attributes)

    assert super_write.await_count == 2
    first_call = super_write.await_args_list[0]
    second_call = super_write.await_args_list[1]

    assert (
        first_call.args[0][
            s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_power_max_overload_enable.id
        ]
        == 0x01
    )
    assert second_call.args[0] == attributes


@pytest.mark.asyncio
async def test_write_both_thresholds_enable_both_protections_first(sonoff_cluster):
    """Writing current and power thresholds enables both protection flags first."""
    attributes = {
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload.id: 15000,
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_power_max_overload.id: 2500000,
    }

    with patch.object(
        s61szbtpb.CustomCluster,
        "write_attributes",
        AsyncMock(side_effect=[_status_record(), _status_record()]),
    ) as super_write:
        await sonoff_cluster.write_attributes(attributes)

    assert super_write.await_count == 2
    assert super_write.await_args_list[0].args[0] == {
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_current_max_overload_enable.id: 0x01,
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_power_max_overload_enable.id: 0x01,
    }
    assert super_write.await_args_list[1].args[0] == attributes


@pytest.mark.asyncio
async def test_write_voltage_threshold_does_not_force_enable_voltage_protection(
    sonoff_cluster,
):
    """Writing the voltage threshold keeps voltage enable as a separate control."""
    attributes = {
        s61szbtpb.SonoffCustomCluster.AttributeDefs.ac_voltage_max_overload.name: 230000
    }

    with patch.object(
        s61szbtpb.CustomCluster,
        "write_attributes",
        AsyncMock(return_value=_status_record()),
    ) as super_write:
        await sonoff_cluster.write_attributes(attributes)

    super_write.assert_awaited_once_with(attributes)