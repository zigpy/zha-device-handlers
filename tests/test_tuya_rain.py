"""Test for Tuya rain sensor."""

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from tests.common import ClusterListener
from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks import LocalDataCluster
from zhaquirks.tuya.tuya_rain import TuyaRainPowerConfiguration

zhaquirks.setup()


ZCL_TUYA_RAIN_MV_01 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x00\x20"  # 32mv
ZCL_TUYA_RAIN_MV_02 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x01\xf4"  # 500mv
ZCL_TUYA_BATTERY_80 = b"\tp\x02\x00\x02\x04\x02\x00\x04\x00\x00\x00\x50"  # 80 %
ZCL_BATTERY_REPORT_78 = b"\x18\x01\x0a\x21\x00\x20\x9c"  # 156 half-percent


@pytest.mark.parametrize(
    "frame,value,rain_detected",
    [(ZCL_TUYA_RAIN_MV_01, 32, False), (ZCL_TUYA_RAIN_MV_02, 500, True)],
)
async def test_rain_sensor_state_report(
    zigpy_device_from_v2_quirk, frame, value, rain_detected
):
    """Test tuya rain sensor standard state reporting."""

    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer

    ias_listener = ClusterListener(rain_dev.endpoints[1].ias_zone)
    rain_listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    assert len(ias_listener.cluster_commands) == 0
    assert len(ias_listener.attribute_updates) == 1
    assert ias_listener.attribute_updates[0][0] == IasZone.AttributeDefs.zone_status.id
    assert ias_listener.attribute_updates[0][1] == (
        IasZone.ZoneStatus.Alarm_1 if rain_detected else 0
    )

    assert len(rain_listener.cluster_commands) == 1
    assert len(rain_listener.attribute_updates) == 1
    assert rain_listener.attribute_updates[0][0] == 0xEF69
    assert rain_listener.attribute_updates[0][1] == value


async def test_rain_sensor_battery_dp(zigpy_device_from_v2_quirk):
    """Test that the battery cluster is a real cluster that DP 4 still updates."""

    rain_dev = zigpy_device_from_v2_quirk("_TZ3210_tgvtvdoc", "TS0207")
    power = rain_dev.endpoints[1].power
    tuya_cluster = rain_dev.endpoints[1].tuya_manufacturer

    assert isinstance(power, TuyaRainPowerConfiguration)
    assert not isinstance(power, LocalDataCluster)

    power_listener = ClusterListener(power)

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_BATTERY_80)
    tuya_cluster.handle_message(hdr, args)

    assert power_listener.attribute_updates == [
        (PowerConfiguration.AttributeDefs.battery_percentage_remaining.id, 160)
    ]


async def test_rain_sensor_battery_reporting():
    """Test that ZHA sets up battery reporting and shows the reported level."""

    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "tz3210-tgvtvdoc-ts0207-0x00000043.json", DEVICE_REGISTRY
        )
        assert not device.skip_configuration

        power = device.device.endpoints[1].power
        power.bind.reset_mock()
        power.configure_reporting_multiple.reset_mock()

        await device.async_configure()

        assert power.bind.call_count == 1
        reported = {
            attr.name
            for call in power.configure_reporting_multiple.call_args_list
            for attr in call.args[0]
        }
        assert (
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name
            in reported
        )

        entity = device.get_platform_entity(
            Platform.SENSOR, unique_id="ab:cd:ef:12:9b:93:04:6b-1-1"
        )
        assert entity.native_value == 79  # from the diagnostics

        hdr, args = power.deserialize(ZCL_BATTERY_REPORT_78)
        power.handle_message(hdr, args)

        assert entity.native_value == 78
        assert entity.state.battery_size == "Other"
        assert entity.state.battery_quantity == 1
