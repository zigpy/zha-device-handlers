"""Tests for Sonoff MINI-ZB1GSP quirks."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener
import zhaquirks

_MINI_ZB1GSP_PATH = (
    Path(__file__).resolve().parents[1] / "zhaquirks" / "sonoff" / "mini-zb1gsp.py"
)
_MINI_ZB1GSP_SPEC = spec_from_file_location(
    "zhaquirks.sonoff.mini_zb1gsp_test_module", _MINI_ZB1GSP_PATH
)
assert _MINI_ZB1GSP_SPEC is not None and _MINI_ZB1GSP_SPEC.loader is not None
mini_zb1gsp = module_from_spec(_MINI_ZB1GSP_SPEC)
sys.modules[_MINI_ZB1GSP_SPEC.name] = mini_zb1gsp
_MINI_ZB1GSP_SPEC.loader.exec_module(mini_zb1gsp)

FAST_SCENE_PACKET_MODIFY = mini_zb1gsp.FAST_SCENE_PACKET_MODIFY
FAST_SCENE_PACKET_REPORT = mini_zb1gsp.FAST_SCENE_PACKET_REPORT
FastSceneProtection = mini_zb1gsp.FastSceneProtection
FastSceneState = mini_zb1gsp.FastSceneState
SonoffCluster = mini_zb1gsp.SonoffCluster
SonoffFastSceneConfigCluster = mini_zb1gsp.SonoffFastSceneConfigCluster
decode_fast_scene_payload = mini_zb1gsp.decode_fast_scene_payload
encode_fast_scene_payload = mini_zb1gsp.encode_fast_scene_payload
fast_scene_array_from_payload = mini_zb1gsp.fast_scene_array_from_payload
fast_scene_payload_from_array = mini_zb1gsp.fast_scene_payload_from_array

zhaquirks.setup()


def _sample_fast_scene_state():
    """Return a representative fast scene configuration."""

    return FastSceneState(
        packet_type=FAST_SCENE_PACKET_REPORT,
        total_num=1,
        current_data_index=1,
        protection=FastSceneProtection(
            scene_switch=1,
            over_current_ma=1234,
            over_load_mw=567890,
            only_ext_mode_restore=1,
            over_voltage_mv=250000,
            over_voltage_en=1,
            under_voltage_mv=180000,
            under_voltage_en=1,
            auto_recover_en=1,
            notify_en=1,
        ),
    )


def test_fast_scene_payload_roundtrip():
    """Encoded fast scene payloads round-trip through the decoder."""

    state = _sample_fast_scene_state()

    payload = encode_fast_scene_payload(state, packet_type=FAST_SCENE_PACKET_MODIFY)
    decoded = decode_fast_scene_payload(payload)

    assert decoded.packet_type == FAST_SCENE_PACKET_MODIFY
    assert decoded.total_num == state.total_num
    assert decoded.current_data_index == state.current_data_index
    assert decoded.protection == state.protection


def test_fast_scene_payload_from_array_variants():
    """Payload extraction supports the value types used by zigpy."""

    payload = encode_fast_scene_payload(_sample_fast_scene_state())
    zcl_array = fast_scene_array_from_payload(payload)

    assert fast_scene_payload_from_array(zcl_array) == payload
    assert fast_scene_payload_from_array(payload) == payload
    assert fast_scene_payload_from_array(bytearray(payload)) == payload
    assert fast_scene_payload_from_array(list(payload)) == payload


@pytest.mark.parametrize(
    "bad_value",
    [
        None,
        object(),
        foundation.Array(type=foundation.DataTypeId.uint8, value=None),
    ],
)
def test_fast_scene_payload_from_array_invalid_values(bad_value):
    """Invalid payload inputs raise a ValueError."""

    with pytest.raises(ValueError):
        fast_scene_payload_from_array(bad_value)


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        (b"\x01\x01", "Fast scene payload is too short"),
        (b"\x01\x01\x01\x02", "Fast scene TLV header is incomplete"),
        (b"\x01\x01\x01\x02\x14\x01", "Fast scene TLV length exceeds payload"),
    ],
)
def test_decode_fast_scene_payload_invalid_values(payload, expected_message):
    """Malformed fast scene payloads are rejected."""

    with pytest.raises(ValueError, match=expected_message):
        decode_fast_scene_payload(payload)


def test_decode_fast_scene_payload_ignores_zero_padding():
    """Trailing zero padding does not break decoding."""

    payload = encode_fast_scene_payload(_sample_fast_scene_state()) + b"\x00\x00"

    decoded = decode_fast_scene_payload(payload)

    assert decoded.protection.over_current_ma == 1234
    assert decoded.protection.notify_en == 1


def test_sonoff_fast_scene_config_update_fast_scene_state():
    """Decoded fast scene state is exposed as local attributes."""

    cluster = object.__new__(SonoffFastSceneConfigCluster)
    cluster._attr_cache = {}
    cluster._fast_scene_state = FastSceneState()

    state = _sample_fast_scene_state()
    cluster.update_fast_scene_state(state)

    assert cluster._fast_scene_state == state
    assert (
        cluster.get(cluster.AttributeDefs.protection_over_current_ma.id)
        == state.protection.over_current_ma
    )
    assert (
        cluster.get(cluster.AttributeDefs.protection_over_load_mw.id)
        == state.protection.over_load_mw
    )
    assert (
        cluster.get(cluster.AttributeDefs.protection_only_ext_mode_restore.id) is True
    )
    assert cluster.get(cluster.AttributeDefs.protection_over_voltage_mv.id) == 250000
    assert cluster.get(cluster.AttributeDefs.protection_over_voltage_enabled.id) is True
    assert cluster.get(cluster.AttributeDefs.protection_under_voltage_mv.id) == 180000
    assert (
        cluster.get(cluster.AttributeDefs.protection_under_voltage_enabled.id) is True
    )
    assert cluster.get(cluster.AttributeDefs.protection_auto_recover.id) is True
    assert cluster.get(cluster.AttributeDefs.protection_notify.id) is True


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            [
                [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.SUCCESS
                    )
                ]
            ],
            True,
        ),
        (
            [
                [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.FAILURE
                    )
                ]
            ],
            False,
        ),
        ([], False),
        (None, False),
    ],
)
def test_sonoff_fast_scene_config_write_succeeded(result, expected):
    """Write success helper handles success and error payloads."""

    assert SonoffFastSceneConfigCluster._write_succeeded(result) is expected


async def test_sonoff_minizb1gsp_fast_scene_propagation(zigpy_device_from_v2_quirk):
    """Fast scene reports propagate decoded values to the local cluster."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GSP",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffFastSceneConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_fast_scene_config
    local_listener = ClusterListener(local_cluster)

    payload = encode_fast_scene_payload(_sample_fast_scene_state())
    sonoff_cluster.update_attribute(
        SonoffCluster.AttributeDefs.local_fast_scene_configuration.id,
        fast_scene_array_from_payload(payload),
    )

    assert local_listener.attribute_updates
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current_ma.id)
        == 1234
    )
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_load_mw.id)
        == 567890
    )
    assert (
        local_cluster.get(
            local_cluster.AttributeDefs.protection_over_voltage_enabled.id
        )
        is True
    )
    assert (
        local_cluster.get(
            local_cluster.AttributeDefs.protection_under_voltage_enabled.id
        )
        is True
    )


async def test_sonoff_minizb1gsp_fast_scene_failed_write_does_not_propagate(
    zigpy_device_from_v2_quirk,
):
    """Failed fast scene writes do not update local state."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GSP",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffFastSceneConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_fast_scene_config
    local_listener = ClusterListener(local_cluster)
    sonoff_cluster._fast_scene_state = _sample_fast_scene_state()

    write_response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=SonoffCluster.AttributeDefs.local_fast_scene_configuration.id,
            )
        ]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ):
        await local_cluster.write_attributes(
            {
                local_cluster.AttributeDefs.protection_over_current_ma.name: 1600,
            }
        )

    assert local_listener.attribute_updates == []


async def test_sonoff_minizb1gsp_fast_scene_write_attributes_logic(
    zigpy_device_from_v2_quirk,
):
    """Local fast scene writes merge into the real Sonoff attribute payload."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GSP",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffFastSceneConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_fast_scene_config
    local_listener = ClusterListener(local_cluster)
    sonoff_cluster._fast_scene_state = _sample_fast_scene_state()

    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await local_cluster.write_attributes(
            {
                local_cluster.AttributeDefs.protection_over_current_ma.name: 1600,
                local_cluster.AttributeDefs.protection_over_load_mw.name: 765432,
                local_cluster.AttributeDefs.protection_only_ext_mode_restore.name: False,
                local_cluster.AttributeDefs.protection_over_voltage_mv.name: 260000,
                local_cluster.AttributeDefs.protection_over_voltage_enabled.name: False,
                local_cluster.AttributeDefs.protection_under_voltage_mv.name: 170000,
                local_cluster.AttributeDefs.protection_under_voltage_enabled.name: False,
                local_cluster.AttributeDefs.protection_auto_recover.name: False,
                local_cluster.AttributeDefs.protection_notify.name: False,
            }
        )

    written_attrs = mock_write.call_args[0][0]
    assert len(written_attrs) == 1
    assert (
        written_attrs[0].attrid
        == SonoffCluster.AttributeDefs.local_fast_scene_configuration.id
    )

    payload = fast_scene_payload_from_array(written_attrs[0].value.value)
    decoded = decode_fast_scene_payload(payload)

    assert decoded.protection.over_current_ma == 1600
    assert decoded.protection.over_load_mw == 765432
    assert decoded.protection.only_ext_mode_restore == 0
    assert decoded.protection.over_voltage_mv == 260000
    assert decoded.protection.over_voltage_en == 0
    assert decoded.protection.under_voltage_mv == 170000
    assert decoded.protection.under_voltage_en == 0
    assert decoded.protection.auto_recover_en == 0
    assert decoded.protection.notify_en == 0

    assert local_listener.attribute_updates
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current_ma.id)
        == 1600
    )
    assert (
        local_cluster.get(
            local_cluster.AttributeDefs.protection_over_voltage_enabled.id
        )
        is False
    )
    assert local_cluster.get(local_cluster.AttributeDefs.protection_notify.id) is False


async def test_sonoff_minizb1gsp_apply_custom_configuration_reads_fast_scene(
    zigpy_device_from_v2_quirk,
):
    """Custom configuration reads fast scene state and populates local attributes."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GSP",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffFastSceneConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_fast_scene_config
    local_listener = ClusterListener(local_cluster)

    fast_scene_attr = SonoffCluster.AttributeDefs.local_fast_scene_configuration
    payload = fast_scene_array_from_payload(
        encode_fast_scene_payload(_sample_fast_scene_state())
    )
    read_response = foundation.ReadAttributeRecord(
        attrid=fast_scene_attr.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(type=fast_scene_attr.zcl_type, value=payload),
    )

    with mock.patch.object(
        sonoff_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=[[read_response]]),
    ) as mock_read:
        await sonoff_cluster.apply_custom_configuration()

    assert mock_read.call_args.args[0] == [fast_scene_attr.id]
    assert local_listener.attribute_updates
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current_ma.id)
        == 1234
    )
