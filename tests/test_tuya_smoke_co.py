"""Offline protocol/quirk checks; no radio or real detector required."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from zha.application.platforms.binary_sensor import BinarySensor
from zha.application.platforms.sensor import EnumSensor
import zigpy.device
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import EntityPlatform
from zhaquirks.tuya import (
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
    tuya_smoke_co as q,
)
from zhaquirks.tuya.mcu import TuyaClusterData


async def test_smoke_co_reports():
    """Test matching, alarm transitions and Tuya report dispatch without hardware."""
    app = MagicMock()
    app.get_sequence.return_value = 1
    device = zigpy.device.Device(
        app, t.EUI64.convert("00:11:22:33:44:55:66:77"), 0x1234
    )
    device.manufacturer = "_TZE284_aoah6bv8"
    device.model = "TS0601"
    ep = device.add_endpoint(1)
    ep.profile_id = 0x0104
    ep.device_type = 0x0051
    for cid in (0, 4, 5, 0xED00, 0xEF00):
        ep.add_input_cluster(cid)
    for cid in (10, 25):
        ep.add_output_cluster(cid)
    assert q.QUIRK.device_match.matches(device)
    device.manufacturer = "_TZE284_other"
    assert not q.QUIRK.device_match.matches(device)
    device.manufacturer = "_TZE284_aoah6bv8"
    for transform in q.QUIRK.zigpy_transforms:
        device = transform(device)
    cluster = device.endpoints[1].in_clusters[0xEF00]
    assert 0xED00 in device.endpoints[1].in_clusters

    def state(name):
        """Read the binary state through ZHA using the cluster cache."""
        return BinarySensor.is_on.fget(
            SimpleNamespace(
                _cluster=cluster,
                _attribute_name=name,
                _attribute_converter=q.alarm_state,
            )
        )

    for name in ("smoke_state", "co_state", "battery_state"):
        assert state(name) is None, (name, cluster.get(name))

    def report(dp, value):
        """Round-trip the wire format before updating the cluster."""
        raw = TuyaDatapointData(dp=dp, data=TuyaData(value)).serialize()
        decoded, rest = TuyaDatapointData.deserialize(raw)
        assert not rest
        cluster._dp_2_attr_update(decoded)

    for dp, name, enum in (
        (1, "smoke_state", q.SmokeState),
        (18, "co_state", q.COState),
        (14, "battery_state", q.BatteryState),
    ):
        for value, expected in ((0, True), (1, False), (0, True)):
            report(dp, enum(value))
            assert state(name) is expected
    for value in (2, 3, 254):
        report(1, q.SmokeState(value))
        assert state("smoke_state") is None
    for value in range(4):
        report(9, q.CheckingResult(value))
        assert cluster.get("checking_result") == value
    for value in (0, 1, 2, 4, 8, 16, 31):
        report(11, t.bitmap8(value))
        assert cluster.get("fault_bitmap") == value
    for value in (True, False):
        report(16, t.Bool(value))
        assert bool(cluster.get("muffling")) is value
    for value in (True, False):
        commands = cluster.from_cluster_data(
            TuyaClusterData(
                endpoint_id=1,
                cluster_name=cluster.ep_attribute,
                cluster_attr="muffling",
                attr_value=t.Bool(value),
                expect_reply=False,
                manufacturer=None,
            )
        )
        assert len(commands) == 1
        dp = commands[0].datapoints[0]
        assert dp.dp == 16 and dp.data.dp_type == TuyaDPType.BOOL
        assert bool(dp.data.payload) is value
    # Exercise real ZCL deserialization and dispatch, including every supported
    # response/report command, rather than only invoking the DP mapper directly.
    for command_id in (1, 2, 6):
        for value, expected in ((0, True), (1, False)):
            cmd = TuyaCommand(
                status=0,
                tsn=1,
                datapoints=[TuyaDatapointData(dp=18, data=TuyaData(q.COState(value)))],
            )
            hdr = foundation.ZCLHeader.cluster(
                tsn=1,
                command_id=command_id,
                direction=foundation.Direction.Server_to_Client,
            )
            hdr = hdr.replace(
                frame_control=hdr.frame_control.replace(disable_default_response=True)
            )
            schema = cluster.client_commands[command_id].schema(data=cmd)
            decoded_hdr, decoded_args = cluster.deserialize(
                hdr.serialize() + schema.serialize()
            )
            cluster.handle_cluster_request(decoded_hdr, decoded_args)
            assert cluster.get("co_state") == value
            assert state("co_state") is expected
    # Muting must not clear an outstanding CO alarm.
    report(18, q.COState.Alarm)
    report(16, t.Bool(True))
    assert state("co_state") is True


def test_smoke_co_entities():
    """Verify all declared entities, unique IDs, enum names and read-only states."""
    metadata = q.QUIRK.zha_device_factory.quirk_definition.entity_metadata
    assert len(metadata) == 9
    identities = [
        (m.endpoint_id, m.unique_id_suffix or m.attribute_name) for m in metadata
    ]
    assert len(set(identities)) == len(identities)
    assert sum(m.entity_platform == EntityPlatform.BINARY_SENSOR for m in metadata) == 3
    assert sum(m.entity_platform == EntityPlatform.SENSOR for m in metadata) == 5
    assert sum(m.entity_platform == EntityPlatform.SWITCH for m in metadata) == 1
    for m in metadata:
        if m.entity_platform == EntityPlatform.BINARY_SENSOR:
            assert m.attribute_converter(0) is True
            assert m.attribute_converter(1) is False
            assert m.attribute_converter(255) is None
    for enum in (q.SmokeState, q.COState):
        sensor = SimpleNamespace(_enum=enum)
        assert EnumSensor.formatter(sensor, t.enum8(0)) == "Alarm"
        assert EnumSensor.formatter(sensor, t.enum8(1)) == "Normal"
