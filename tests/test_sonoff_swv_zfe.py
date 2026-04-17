"""Tests for Sonoff SWV-ZFE smart water valve quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.swv_zfe import (
    SWVZFECluster,
    SWVZFEValveAlarmConfigCluster,
    SWVZFEValveAlarmSettingsPayload,
    swvzfe_be_swap,
    swvzfe_decode_valve_alarm_settings,
    swvzfe_fail_safe,
    swvzfe_frost_protection,
    swvzfe_normalize_valve_alarm_settings,
    swvzfe_pack_valve_alarm_settings,
    swvzfe_water_leakage,
    swvzfe_water_shortage,
)

zhaquirks.setup()


def test_swvzfe_be_swap() -> None:
    """Test that swvzfe_be_swap correctly reverses the byte order of a uint32."""
    # Device sends 300 as big-endian bytes; zigpy reads it as little-endian
    assert swvzfe_be_swap(0x2C010000) == 300
    # Round-trip: swapping twice should return the original value
    assert swvzfe_be_swap(swvzfe_be_swap(0xDEADBEEF)) == 0xDEADBEEF
    # Zero is invariant under byte-swap
    assert swvzfe_be_swap(0) == 0
    assert swvzfe_be_swap(None) is None


@pytest.mark.parametrize(
    ("value", "water_shortage", "water_leakage", "frost_protection", "fail_safe"),
    [
        (0x00, False, False, False, False),
        (0x01, True, False, False, False),
        (0x02, False, True, False, False),
        (0x04, False, False, True, False),
        (0x08, False, False, False, True),
        (0x0F, True, True, True, True),
        (0x05, True, False, True, False),
    ],
    ids=["none", "shortage", "leakage", "frost", "failsafe", "all", "shortage+frost"],
)
def test_swvzfe_valve_abnormal_state_converters(
    value, water_shortage, water_leakage, frost_protection, fail_safe
) -> None:
    """Test all valve_abnormal_state bit-extraction converter functions."""
    assert swvzfe_water_shortage(value) == water_shortage
    assert swvzfe_water_leakage(value) == water_leakage
    assert swvzfe_frost_protection(value) == frost_protection
    assert swvzfe_fail_safe(value) == fail_safe


def test_swvzfe_converters_handle_none() -> None:
    """All converter functions must return None when given None."""
    assert swvzfe_water_shortage(None) is None
    assert swvzfe_water_leakage(None) is None
    assert swvzfe_frost_protection(None) is None
    assert swvzfe_fail_safe(None) is None


def test_swvzfe_valve_alarm_settings_pack_decode() -> None:
    """Packed valve alarm settings round-trip between bytes and named fields."""
    payload = swvzfe_pack_valve_alarm_settings(
        enable_alarm_water_shortage=True,
        enable_alarm_water_leak=False,
        enable_frost_protection=True,
        enable_water_shortage_auto_close=True,
        enable_water_leak_auto_close=False,
        alarm_water_shortage_duration=7,
        alarm_water_leak_duration=2,
        set_frost_temperature=3,
        extra_enable_bits=0x80,
    )

    assert list(payload) == [0x8D, 7, 2, 3]
    assert swvzfe_decode_valve_alarm_settings(payload) == {
        "enable_alarm_water_shortage": True,
        "enable_alarm_water_leak": False,
        "enable_frost_protection": True,
        "enable_water_shortage_auto_close": True,
        "enable_water_leak_auto_close": False,
        "alarm_water_shortage_duration": 7,
        "alarm_water_leak_duration": 2,
        "set_frost_temperature": 3,
    }


def test_swvzfe_normalize_valve_alarm_settings_rejects_bad_length() -> None:
    """Packed valve alarm settings must always be exactly four bytes."""
    with pytest.raises(ValueError, match="exactly 4 bytes"):
        swvzfe_normalize_valve_alarm_settings([1, 2, 3])


@pytest.mark.parametrize(
    "model",
    ["SWV-ZFE", "SWV-ZNE", "SWV-ZNU", "SWV-ZFU"],
)
def test_swvzfe_quirk_applies(zigpy_device_from_v2_quirk, model: str) -> None:
    """Verify the quirk is registered for all SWV model variants."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        model,
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )
    assert SWVZFECluster.cluster_id in device.endpoints[1].in_clusters
    assert SWVZFEValveAlarmConfigCluster.cluster_id in device.endpoints[1].in_clusters
    assert isinstance(
        device.endpoints[1].swvzfe_cluster,
        SWVZFECluster,
    )
    assert isinstance(
        device.endpoints[1].swvzfe_valve_alarm_config,
        SWVZFEValveAlarmConfigCluster,
    )


async def test_swvzfe_valve_alarm_settings_propagation(zigpy_device_from_v2_quirk):
    """Packed valve_alarm_settings updates should populate the local config cluster."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster
    local_cluster = device.endpoints[1].swvzfe_valve_alarm_config
    local_listener = ClusterListener(local_cluster)

    payload = SWVZFEValveAlarmSettingsPayload([0x1B, 8, 3, 4])
    swvzfe_cluster.update_attribute(
        SWVZFECluster.AttributeDefs.valve_alarm_settings.id,
        payload,
    )

    assert len(local_listener.attribute_updates) == 8
    assert local_cluster.get("enable_alarm_water_shortage") is True
    assert local_cluster.get("enable_alarm_water_leak") is True
    assert local_cluster.get("enable_frost_protection") is False
    assert local_cluster.get("enable_water_shortage_auto_close") is True
    assert local_cluster.get("enable_water_leak_auto_close") is True
    assert local_cluster.get("alarm_water_shortage_duration") == 8
    assert local_cluster.get("alarm_water_leak_duration") == 3
    assert local_cluster.get("set_frost_temperature") == 4


async def test_swvzfe_valve_alarm_settings_write_attributes_logic(
    zigpy_device_from_v2_quirk,
):
    """Writing one local setting should translate into one packed array write."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster
    local_cluster = device.endpoints[1].swvzfe_valve_alarm_config
    local_listener = ClusterListener(local_cluster)

    swvzfe_cluster.update_attribute(
        SWVZFECluster.AttributeDefs.valve_alarm_settings.id,
        SWVZFEValveAlarmSettingsPayload([0x9F, 5, 2, 1]),
    )
    local_listener.attribute_updates.clear()

    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        swvzfe_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await local_cluster.write_attributes(
            {
                SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_alarm_water_shortage.name: False
            }
        )

        assert mock_write.call_count == 1
        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1

        written = written_attrs[0]
        assert written.attrid == SWVZFECluster.AttributeDefs.valve_alarm_settings.id
        assert written.value.type == foundation.DataTypeId.array
        assert written.value.value.type == foundation.DataTypeId.uint8
        assert list(written.value.value.value) == [0x9E, 5, 2, 1]

    assert len(local_listener.attribute_updates) == 8
    assert local_cluster.get("enable_alarm_water_shortage") is False
    assert local_cluster.get("enable_alarm_water_leak") is True
    assert local_cluster.get("enable_frost_protection") is True
    assert local_cluster.get("enable_water_shortage_auto_close") is True
    assert local_cluster.get("enable_water_leak_auto_close") is True
    assert local_cluster.get("alarm_water_shortage_duration") == 5
    assert local_cluster.get("alarm_water_leak_duration") == 2
    assert local_cluster.get("set_frost_temperature") == 1


async def test_swvzfe_valve_alarm_settings_failed_write_does_not_propagate(
    zigpy_device_from_v2_quirk,
):
    """A failed packed write must not update the local config entities."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster
    local_cluster = device.endpoints[1].swvzfe_valve_alarm_config
    local_listener = ClusterListener(local_cluster)

    swvzfe_cluster.update_attribute(
        SWVZFECluster.AttributeDefs.valve_alarm_settings.id,
        SWVZFEValveAlarmSettingsPayload([0x01, 5, 2, 1]),
    )
    local_listener.attribute_updates.clear()

    write_response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=SWVZFECluster.AttributeDefs.valve_alarm_settings.id,
            )
        ]
    ]
    with mock.patch.object(
        swvzfe_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ):
        await local_cluster.write_attributes(
            {
                SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_alarm_water_shortage.name: False
            }
        )

    assert len(local_listener.attribute_updates) == 0
    assert local_cluster.get("enable_alarm_water_shortage") is True


async def test_swvzfe_cluster_apply_custom_configuration(zigpy_device_from_v2_quirk):
    """Pairing-time read of valve_alarm_settings should populate the local cluster."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster
    local_cluster = device.endpoints[1].swvzfe_valve_alarm_config
    local_listener = ClusterListener(local_cluster)

    payload = SWVZFEValveAlarmSettingsPayload([0x05, 6, 2, 3])
    read_response = foundation.ReadAttributeRecord(
        attrid=SWVZFECluster.AttributeDefs.valve_alarm_settings.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(
            type=foundation.DataTypeId.array,
            value=payload,
        ),
    )

    with mock.patch.object(
        swvzfe_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=[[read_response]]),
    ):
        await swvzfe_cluster.apply_custom_configuration()

    assert len(local_listener.attribute_updates) == 8
    assert local_cluster.get("enable_alarm_water_shortage") is True
    assert local_cluster.get("enable_alarm_water_leak") is False
    assert local_cluster.get("enable_frost_protection") is True
    assert local_cluster.get("enable_water_shortage_auto_close") is False
    assert local_cluster.get("enable_water_leak_auto_close") is False
    assert local_cluster.get("alarm_water_shortage_duration") == 6
    assert local_cluster.get("alarm_water_leak_duration") == 2
    assert local_cluster.get("set_frost_temperature") == 3


async def test_swvzfe_cluster_apply_custom_configuration_ignores_read_failure(
    zigpy_device_from_v2_quirk,
):
    """Pairing-time read failures should not abort device configuration."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster

    with mock.patch.object(
        swvzfe_cluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=RuntimeError("bad array payload")),
    ):
        await swvzfe_cluster.apply_custom_configuration()


def test_swvzfe_cluster_deserialize_logs_raw_frame_on_parse_failure(
    zigpy_device_from_v2_quirk,
):
    """Cluster parse failures should log the raw frame for live debugging."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster

    with (
        mock.patch(
            "zigpy.quirks.CustomCluster.deserialize",
            side_effect=ValueError("bad array payload"),
        ),
        mock.patch.object(swvzfe_cluster, "warning") as warning,
        pytest.raises(ValueError, match="bad array payload"),
    ):
        swvzfe_cluster.deserialize(b"\x18\x01\x01\x20")

    warning.assert_called_once()
    assert warning.call_args.args[3] == "18 01 01 20"


def test_swvzfe_cluster_deserialize_repairs_duplicate_array_type(
    zigpy_device_from_v2_quirk,
):
    """Malformed 0x5020 reads with a duplicated array type should be repaired."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster

    hdr, response = swvzfe_cluster.deserialize(
        b"\x18\x01\x01\x20\x50\x00\x48\x48\x04\x00\x00\x00\x00\x00"
    )

    assert hdr.command_id == foundation.GeneralCommand.Read_Attributes_rsp
    assert len(response.status_records) == 1
    assert (
        response.status_records[0].attrid
        == SWVZFECluster.AttributeDefs.valve_alarm_settings.id
    )
    assert response.status_records[0].status == foundation.Status.SUCCESS
    assert response.status_records[0].value.type == foundation.DataTypeId.uint8
    assert list(response.status_records[0].value.value) == [0, 0, 0, 0]


def test_swvzfe_cluster_deserialize_repairs_duplicate_array_type_in_multi_record_rsp(
    zigpy_device_from_v2_quirk,
):
    """Malformed 0x5020 reads should be repaired even when not first in the response."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster

    hdr, response = swvzfe_cluster.deserialize(
        b"\x18\x01\x01\x00\x00\x00\x10\x00\x20\x50\x00\x48\x48\x04\x00\x00\x00\x00\x00"
    )

    assert hdr.command_id == foundation.GeneralCommand.Read_Attributes_rsp
    assert len(response.status_records) == 2
    assert response.status_records[0].attrid == SWVZFECluster.AttributeDefs.child_lock.id
    assert bool(response.status_records[0].value.value) is False
    assert (
        response.status_records[1].attrid
        == SWVZFECluster.AttributeDefs.valve_alarm_settings.id
    )
    assert response.status_records[1].value.type == foundation.DataTypeId.uint8
    assert list(response.status_records[1].value.value) == [0, 0, 0, 0]


async def test_swvzfe_valve_alarm_settings_write_attributes_lazy_initializes(
    zigpy_device_from_v2_quirk,
):
    """A local write should try to initialize 0x5020 before failing."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )

    swvzfe_cluster = device.endpoints[1].swvzfe_cluster
    local_cluster = device.endpoints[1].swvzfe_valve_alarm_config

    read_response = foundation.ReadAttributeRecord(
        attrid=SWVZFECluster.AttributeDefs.valve_alarm_settings.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(
            type=foundation.DataTypeId.array,
            value=SWVZFEValveAlarmSettingsPayload([0x01, 5, 2, 1]),
        ),
    )

    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with (
        mock.patch.object(
            swvzfe_cluster,
            "_read_attributes",
            mock.AsyncMock(return_value=[[read_response]]),
        ) as mock_read,
        mock.patch.object(
            swvzfe_cluster,
            "write_attributes_raw",
            mock.AsyncMock(return_value=write_response),
        ) as mock_write,
    ):
        await local_cluster.write_attributes(
            {
                SWVZFEValveAlarmConfigCluster.AttributeDefs.enable_alarm_water_shortage.name: False
            }
        )

    mock_read.assert_awaited_once()
    assert mock_write.await_count == 1
