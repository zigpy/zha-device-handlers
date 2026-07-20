"""Tests for the Sonoff MINI-ZB1 family quirks."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener
import zhaquirks

_MINI_ZB1_FAMILY_PATH = (
    Path(__file__).resolve().parents[1] / "zhaquirks" / "sonoff" / "MINI-ZB1 Family.py"
)
_MINI_ZB1_FAMILY_SPEC = spec_from_file_location(
    "zhaquirks.sonoff.mini_zb1_family_test_module", _MINI_ZB1_FAMILY_PATH
)
assert _MINI_ZB1_FAMILY_SPEC is not None and _MINI_ZB1_FAMILY_SPEC.loader is not None
mini_zb1_family = module_from_spec(_MINI_ZB1_FAMILY_SPEC)
sys.modules[_MINI_ZB1_FAMILY_SPEC.name] = mini_zb1_family
_MINI_ZB1_FAMILY_SPEC.loader.exec_module(mini_zb1_family)

FAST_SCENE_PACKET_MODIFY = mini_zb1_family.FAST_SCENE_PACKET_MODIFY
FAST_SCENE_PACKET_REPORT = mini_zb1_family.FAST_SCENE_PACKET_REPORT
COMMAND_DOUBLE = mini_zb1_family.COMMAND_DOUBLE
EXTERNAL_TRIGGER_MAP = mini_zb1_family.EXTERNAL_TRIGGER_MAP
FastSceneProtection = mini_zb1_family.FastSceneProtection
FastSceneState = mini_zb1_family.FastSceneState
SonoffCluster = mini_zb1_family.SonoffCluster
SonoffFastSceneConfigCluster = mini_zb1_family.SonoffFastSceneConfigCluster
decode_fast_scene_payload = mini_zb1_family.decode_fast_scene_payload
encode_fast_scene_payload = mini_zb1_family.encode_fast_scene_payload
fast_scene_array_from_payload = mini_zb1_family.fast_scene_array_from_payload
fast_scene_payload_from_array = mini_zb1_family.fast_scene_payload_from_array
_convert_signed_power = mini_zb1_family._convert_signed_power

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


def test_convert_signed_power_handles_reverse_flow():
    """Signed power helper decodes two's complement negative values."""

    assert _convert_signed_power(123456) == 123.456
    assert _convert_signed_power(0xFFFFFFFF) == -0.001
    assert _convert_signed_power(0xFFFFF060) == -4.0


def test_sonoff_fast_scene_config_update_fast_scene_state():
    """Decoded fast scene state is exposed as local attributes."""

    cluster = object.__new__(SonoffFastSceneConfigCluster)
    object.__setattr__(cluster, "_fast_scene_state", FastSceneState())
    object.__setattr__(cluster, "_update_attribute", mock.MagicMock())

    state = _sample_fast_scene_state()
    cluster.update_fast_scene_state(state)

    assert cluster._fast_scene_state == state
    assert cluster._update_attribute.call_args_list == [
        mock.call(cluster.AttributeDefs.protection_over_current_ma.id, 1234),
        mock.call(cluster.AttributeDefs.protection_over_load_mw.id, 567890),
        mock.call(cluster.AttributeDefs.protection_only_ext_mode_restore.id, True),
        mock.call(cluster.AttributeDefs.protection_over_voltage_mv.id, 250000),
        mock.call(cluster.AttributeDefs.protection_over_voltage_enabled.id, True),
        mock.call(cluster.AttributeDefs.protection_under_voltage_mv.id, 180000),
        mock.call(cluster.AttributeDefs.protection_under_voltage_enabled.id, True),
        mock.call(cluster.AttributeDefs.protection_auto_recover.id, True),
        mock.call(cluster.AttributeDefs.protection_notify.id, True),
    ]


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


async def test_minizb1gsp_fast_scene_propagation(zigpy_device_from_v2_quirk):
    """GSP fast scene reports propagate decoded values to the local cluster."""

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


async def test_minizb1gsp_fast_scene_write_attributes_logic(zigpy_device_from_v2_quirk):
    """GSP local fast scene writes merge into the real Sonoff attribute payload."""

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
                local_cluster.AttributeDefs.protection_under_voltage_enabled.name: False,
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
    assert decoded.protection.under_voltage_en == 0
    assert decoded.protection.notify_en == 0
    assert (
        local_cluster.get(local_cluster.AttributeDefs.protection_over_current_ma.id)
        == 1600
    )
    assert local_listener.attribute_updates


async def test_minizb1gsp_external_switch_events(zigpy_device_from_v2_quirk):
    """GSP exposes external trigger events for automations."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GSP",
        cluster_ids={1: {SonoffCluster.cluster_id: ClusterType.Server}},
    )

    cluster = device.endpoints[1].sonoff_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    assert device.device_automation_triggers[EXTERNAL_TRIGGER_MAP[COMMAND_DOUBLE]] == {
        "command": COMMAND_DOUBLE,
        "endpoint_id": 1,
    }

    cluster.update_attribute(
        cluster.AttributeDefs.external_trigger_event.id,
        cluster.AttributeDefs.external_trigger_event.type(0x02),
    )

    listener.zha_send_event.assert_called_once_with(COMMAND_DOUBLE, {"value": 0x02})


async def test_minizb1gp_applies_custom_configuration_reads_fast_scene(
    zigpy_device_from_v2_quirk,
):
    """GP custom configuration reads fast scene state and populates local attributes."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GP",
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


async def test_minizb1gs_external_switch_events(zigpy_device_from_v2_quirk):
    """GS exposes external trigger events for automations."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZB1GS",
        cluster_ids={1: {SonoffCluster.cluster_id: ClusterType.Server}},
    )

    cluster = device.endpoints[1].sonoff_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    assert device.device_automation_triggers[EXTERNAL_TRIGGER_MAP[COMMAND_DOUBLE]] == {
        "command": COMMAND_DOUBLE,
        "endpoint_id": 1,
    }

    cluster.update_attribute(
        cluster.AttributeDefs.external_trigger_event.id,
        cluster.AttributeDefs.external_trigger_event.type(0x02),
    )

    listener.zha_send_event.assert_called_once_with(COMMAND_DOUBLE, {"value": 0x02})
