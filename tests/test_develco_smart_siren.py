"""Tests for Develco smart siren quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.security import IasWd, IasZone

from zhaquirks.develco.smart_siren import FrientIasWd


def _get_siren_cluster(zigpy_device_from_v2_quirk):
    """Create a siren device and return endpoint 43 IAS WD cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="SIRZB-110",
        endpoint_ids=[43],
        cluster_ids={
            43: {
                IasWd.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )
    return device.endpoints[43].ias_wd


async def test_frient_ias_wd_resolve_attr_id(zigpy_device_from_v2_quirk):
    """Test FrientIasWd._resolve_attr_id handles supported key types."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    assert isinstance(ias_wd, FrientIasWd)

    local_attr_id = FrientIasWd.AttributeDefs.squawk_level.id
    local_attr_def = FrientIasWd.AttributeDefs.squawk_level

    assert ias_wd._resolve_attr_id(local_attr_def.name) == local_attr_id
    assert ias_wd._resolve_attr_id(local_attr_def) == local_attr_id
    assert ias_wd._resolve_attr_id(local_attr_id) == local_attr_id
    assert ias_wd._resolve_attr_id("does_not_exist") is None
    assert ias_wd._resolve_attr_id(object()) is None


async def test_frient_ias_wd_read_attributes_raw_local_only(
    zigpy_device_from_v2_quirk,
):
    """Test local squawk level reads without delegating to base cluster."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_id = FrientIasWd.AttributeDefs.squawk_level.id

    with mock.patch.object(IasWd, "read_attributes_raw", new=mock.AsyncMock()) as m:
        (records,) = await ias_wd.read_attributes_raw([local_attr_id])

    m.assert_not_called()
    assert len(records) == 1
    assert records[0].attrid == local_attr_id
    assert records[0].status == foundation.Status.SUCCESS
    assert records[0].value.value == IasWd.Squawk.SquawkLevel.Low_level_sound


async def test_frient_ias_wd_read_attributes_raw_local_only_name(
    zigpy_device_from_v2_quirk,
):
    """Test local squawk reads by attribute name without delegation."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_id = FrientIasWd.AttributeDefs.squawk_level.id
    local_attr_name = FrientIasWd.AttributeDefs.squawk_level.name

    with mock.patch.object(IasWd, "read_attributes_raw", new=mock.AsyncMock()) as m:
        (records,) = await ias_wd.read_attributes_raw([local_attr_name])

    m.assert_not_called()
    assert len(records) == 1
    assert records[0].attrid == local_attr_id
    assert records[0].status == foundation.Status.SUCCESS


async def test_frient_ias_wd_read_attributes_raw_local_only_attrdef(
    zigpy_device_from_v2_quirk,
):
    """Test local squawk reads by ZCLAttributeDef without delegation."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_def = FrientIasWd.AttributeDefs.squawk_level

    with mock.patch.object(IasWd, "read_attributes_raw", new=mock.AsyncMock()) as m:
        (records,) = await ias_wd.read_attributes_raw([local_attr_def])

    m.assert_not_called()
    assert len(records) == 1
    assert records[0].attrid == local_attr_def.id
    assert records[0].status == foundation.Status.SUCCESS


async def test_frient_ias_wd_read_attributes_raw_mixed_delegates(
    zigpy_device_from_v2_quirk,
):
    """Test local squawk reads are merged with delegated remote reads."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_id = FrientIasWd.AttributeDefs.squawk_level.id
    remote_attr_id = IasWd.AttributeDefs.max_duration.id

    ias_wd.update_attribute(local_attr_id, IasWd.Squawk.SquawkLevel.High_level_sound)

    remote_record = foundation.ReadAttributeRecord(
        remote_attr_id,
        foundation.Status.SUCCESS,
        foundation.TypeValue(),
    )
    remote_record.value.value = 30

    with mock.patch.object(
        IasWd,
        "read_attributes_raw",
        new=mock.AsyncMock(return_value=([remote_record],)),
    ) as m:
        (records,) = await ias_wd.read_attributes_raw(
            [local_attr_id, remote_attr_id], manufacturer=0x1234
        )

    m.assert_called_once()
    assert m.call_args.args[0] == [remote_attr_id]
    assert m.call_args.kwargs["manufacturer"] == 0x1234
    assert {record.attrid for record in records} == {local_attr_id, remote_attr_id}
    local_record = next(record for record in records if record.attrid == local_attr_id)
    assert local_record.value.value == IasWd.Squawk.SquawkLevel.High_level_sound


async def test_frient_ias_wd_read_attributes_raw_remote_only_delegates(
    zigpy_device_from_v2_quirk,
):
    """Test remote-only reads are delegated unchanged to base cluster."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    remote_attr_id = IasWd.AttributeDefs.max_duration.id

    remote_record = foundation.ReadAttributeRecord(
        remote_attr_id,
        foundation.Status.SUCCESS,
        foundation.TypeValue(),
    )
    remote_record.value.value = 55

    with mock.patch.object(
        IasWd,
        "read_attributes_raw",
        new=mock.AsyncMock(return_value=([remote_record],)),
    ) as m:
        (records,) = await ias_wd.read_attributes_raw(
            [remote_attr_id], manufacturer=0x1234
        )

    m.assert_called_once()
    assert m.call_args.args[0] == [remote_attr_id]
    assert m.call_args.kwargs["manufacturer"] == 0x1234
    assert len(records) == 1
    assert records[0].attrid == remote_attr_id
    assert records[0].value.value == 55


async def test_frient_ias_wd_write_attributes_local_only(zigpy_device_from_v2_quirk):
    """Test local squawk writes are applied and not delegated."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_id = FrientIasWd.AttributeDefs.squawk_level.id

    with mock.patch.object(IasWd, "write_attributes", new=mock.AsyncMock()) as m:
        result = await ias_wd.write_attributes(
            {local_attr_id: IasWd.Squawk.SquawkLevel.Medium_level_sound}
        )

    m.assert_not_called()
    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    assert ias_wd.get(local_attr_id) == IasWd.Squawk.SquawkLevel.Medium_level_sound


async def test_frient_ias_wd_write_attributes_mixed_delegates(
    zigpy_device_from_v2_quirk,
):
    """Test mixed writes keep local squawk handling and delegate others."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_def = FrientIasWd.AttributeDefs.squawk_level
    remote_attr_id = IasWd.AttributeDefs.max_duration.id
    status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    attrs = {
        local_attr_def.name: IasWd.Squawk.SquawkLevel.High_level_sound,
        remote_attr_id: 45,
    }

    with mock.patch.object(
        IasWd,
        "write_attributes",
        new=mock.AsyncMock(return_value=[status]),
    ) as m:
        result = await ias_wd.write_attributes(attrs, manufacturer=0x1234, timeout=9)

    m.assert_called_once()
    assert m.call_args.args[0] == {remote_attr_id: 45}
    assert m.call_args.kwargs["manufacturer"] == 0x1234
    assert m.call_args.kwargs["timeout"] == 9
    assert result == [status]
    assert ias_wd.get(local_attr_def.id) == IasWd.Squawk.SquawkLevel.High_level_sound


async def test_frient_ias_wd_write_attributes_local_only_attrdef_key(
    zigpy_device_from_v2_quirk,
):
    """Test local squawk writes support ZCLAttributeDef as key."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_def = FrientIasWd.AttributeDefs.squawk_level

    with mock.patch.object(IasWd, "write_attributes", new=mock.AsyncMock()) as m:
        result = await ias_wd.write_attributes(
            {local_attr_def: IasWd.Squawk.SquawkLevel.Low_level_sound}
        )

    m.assert_not_called()
    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    assert ias_wd.get(local_attr_def.id) == IasWd.Squawk.SquawkLevel.Low_level_sound


async def test_frient_ias_wd_write_attributes_unknown_key_raises(
    zigpy_device_from_v2_quirk,
):
    """Test unknown attributes fail early with a clear error."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)

    with (
        mock.patch.object(IasWd, "write_attributes", new=mock.AsyncMock()) as m,
        pytest.raises(KeyError, match="Unknown attribute"),
    ):
        await ias_wd.write_attributes({"does_not_exist": 1})

    m.assert_not_called()


async def test_frient_ias_wd_write_attributes_empty_returns_success(
    zigpy_device_from_v2_quirk,
):
    """Test empty writes are treated as successful no-op."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)

    result = await ias_wd.write_attributes({})

    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]


async def test_frient_ias_wd_squawk_uses_cached_level(zigpy_device_from_v2_quirk):
    """Test squawk command uses configured local squawk level."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)
    local_attr_id = FrientIasWd.AttributeDefs.squawk_level.id

    ias_wd.update_attribute(local_attr_id, IasWd.Squawk.SquawkLevel.High_level_sound)

    with mock.patch.object(
        ias_wd, "command", new=mock.AsyncMock(return_value="ok")
    ) as m:
        result = await ias_wd.squawk(0x10)

    m.assert_called_once()
    assert m.call_args.args[0] == IasWd.ServerCommandDefs.squawk.id
    squawk_arg = m.call_args.kwargs["squawk"]
    assert squawk_arg.level == IasWd.Squawk.SquawkLevel.High_level_sound
    assert result == "ok"


async def test_frient_ias_wd_squawk_uses_default_level_when_unset(
    zigpy_device_from_v2_quirk,
):
    """Test squawk command falls back to default level when cache is unset."""
    ias_wd = _get_siren_cluster(zigpy_device_from_v2_quirk)

    with mock.patch.object(
        ias_wd, "command", new=mock.AsyncMock(return_value="ok")
    ) as m:
        result = await ias_wd.squawk(0x00)

    m.assert_called_once()
    squawk_arg = m.call_args.kwargs["squawk"]
    assert squawk_arg.level == IasWd.Squawk.SquawkLevel.Low_level_sound
    assert result == "ok"


async def test_frient_ias_wd_metadata_entities_present(zigpy_device_from_v2_quirk):
    """Test v2 metadata exposes expected max_duration/squawk entities."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="SIRZB-110",
        endpoint_ids=[43],
        cluster_ids={
            43: {
                IasWd.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )

    metadata = device.exposes_metadata[(43, IasWd.cluster_id, ClusterType.Server)]
    translation_keys = {meta.translation_key for meta in metadata}

    assert "max_duration" in translation_keys
    assert "squawk_volume" in translation_keys
    assert "squawk_armed" in translation_keys
    assert "squawk_disarmed" in translation_keys


def test_power_binary_sensor_attribute_converter(zigpy_device_from_v2_quirk):
    """Test power entity converter with inverted IAS AC_mains bit semantics."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="frient A/S",
        model="SIRZB-110",
        endpoint_ids=[43],
        cluster_ids={
            43: {
                IasWd.cluster_id: ClusterType.Server,
                IasZone.cluster_id: ClusterType.Server,
            }
        },
    )

    metadata = device.exposes_metadata[(43, IasZone.cluster_id, ClusterType.Server)]
    power_meta = next(
        entity for entity in metadata if entity.unique_id_suffix == "power"
    )
    converter = power_meta.attribute_converter

    # IAS AC_mains bit set indicates battery operation, so AC power must be False.
    assert converter(IasZone.ZoneStatus.AC_mains) is False
    # IAS AC_mains bit unset indicates mains power, so AC power must be True.
    assert converter(IasZone.ZoneStatus.Alarm_1) is True
    # IAS AC_mains bit still wins when combined with other zone status flags.
    assert converter(IasZone.ZoneStatus.AC_mains | IasZone.ZoneStatus.Alarm_1) is False
