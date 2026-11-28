"""Tests for the Tuya TS0201 sensors."""

import json
from pathlib import Path
from unittest import mock

from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.tuya import BaseEnchantedDevice
from zhaquirks.tuya.ts0201 import TuyaTemperatureHumidityAlarmCluster, ValueAlarm

zhaquirks.setup()

NEO = "tz3000-qaaysllp-ts0201.json"
IEEE = "cc:86:ec:ff:fe:c8:96:e0"


def _packet(endpoint_id: int, cluster_id: int, data: str) -> t.ZigbeePacket:
    return t.ZigbeePacket(
        profile_id=zha.PROFILE_ID,
        cluster_id=cluster_id,
        src_ep=endpoint_id,
        dst_ep=1,
        data=t.SerializableBytes(bytes.fromhex(data)),
    )


async def test_neo_ts0201_entities():
    """Temperature and humidity keep their entities, alarm settings are exposed."""
    diagnostics = json.loads(
        (Path(__file__).parent / "data" / "devices" / NEO).read_text()
    )

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(gateway, NEO, DEVICE_REGISTRY)

        assert isinstance(device.device, BaseEnchantedDevice)
        assert device.device.tuya_spell_read_attributes

        # Same entities as on the real device; virtual ones are not in diagnostics
        assert {
            (platform, unique_id)
            for platform, unique_id in device.platform_entities
            if platform != Platform.VIRTUAL
        } == {
            (Platform(platform), entity["unique_id"])
            for platform, entities in diagnostics["zha_lib_entities"].items()
            for entity in entities
        }
        assert {
            f"{IEEE}-2-1026",  # temperature, same unique_id as the v1 quirk
            f"{IEEE}-2-1029",  # humidity
        } <= {unique_id for _, unique_id in device.platform_entities}

        humidity_max = device.get_platform_entity(
            Platform.NUMBER, f"{IEEE}-1-alarm_humidity_max"
        )
        assert humidity_max.native_value == 100  # 0xD00D in the device's cache


async def test_neo_ts0201_spell_and_reports(zigpy_device_from_v2_quirk):
    """The spell reads Basic; reports from the hidden endpoint 2 are accepted."""
    device = zigpy_device_from_v2_quirk(
        "_TZ3000_qaaysllp",
        "TS0201",
        cluster_ids={1: {TuyaTemperatureHumidityAlarmCluster.cluster_id: 0}},
    )

    basic = device.endpoints[1].in_clusters[Basic.cluster_id]
    with mock.patch.object(basic, "read_attributes", mock.AsyncMock()) as read:
        await device.apply_custom_configuration()
    read.assert_awaited_once_with([4, 0, 1, 5, 7, 0xFFFE], split_requests=False)

    # Report_Attributes measured_value: 21.50 °C, 45.00 %
    device.packet_received(
        _packet(2, TemperatureMeasurement.cluster_id, "18010a0000296608")
    )
    device.packet_received(_packet(2, RelativeHumidity.cluster_id, "18020a0000219411"))
    assert device.endpoints[2].temperature.get("measured_value") == 2150
    assert device.endpoints[2].humidity.get("measured_value") == 4500

    # Alarm report: temperature min -10 °C (int16), humidity max 90 %
    alarm = device.endpoints[1].in_clusters[
        TuyaTemperatureHumidityAlarmCluster.cluster_id
    ]
    device.packet_received(_packet(1, alarm.cluster_id, "18030a0bd029f6ff0dd0295a00"))
    assert alarm.get("alarm_temperature_min") == -10
    assert alarm.get("alarm_humidity_max") == 90

    device.packet_received(_packet(1, alarm.cluster_id, "18040a06d03001"))
    assert alarm.get("alarm_temperature") == ValueAlarm.MAX_ALARM_ON


async def test_neo_ts0201_alarm_write_has_no_manufacturer_code(
    zigpy_device_from_v2_quirk,
):
    """0xE002 is not a manufacturer cluster: writes must not carry a Tuya code."""
    device = zigpy_device_from_v2_quirk(
        "_TZ3000_qaaysllp",
        "TS0201",
        cluster_ids={1: {TuyaTemperatureHumidityAlarmCluster.cluster_id: 0}},
    )
    alarm = device.endpoints[1].in_clusters[
        TuyaTemperatureHumidityAlarmCluster.cluster_id
    ]

    with mock.patch.object(
        alarm,
        "request",
        mock.AsyncMock(
            return_value=[
                [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
            ]
        ),
    ) as request:
        await alarm.write_attributes({"alarm_temperature_min": -5})

    assert request.call_args.kwargs["manufacturer"] is None
    (record,) = request.call_args.args[3]
    assert record.attrid == 0xD00B
    assert record.value.serialize() == bytes.fromhex("29fbff")  # int16 -5
