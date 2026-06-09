"""Tests the Danfoss quirk (all tests were written for the Popp eT093WRO)."""

from unittest import mock

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord, ZCLAttributeDef

import zhaquirks
from zhaquirks.danfoss.thermostat import CustomizedStandardCluster

zhaquirks.setup()


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
async def test_danfoss_time_bind(zigpy_device_from_v2_quirk):
    """Test the time being set when binding the Time cluster."""
    device = zigpy_device_from_v2_quirk("Danfoss", "eTRV0103")

    danfoss_time_cluster = device.endpoints[1].time
    danfoss_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    patch_danfoss_trv_write = mock.patch.object(
        danfoss_time_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )

    with patch_danfoss_trv_write:
        await danfoss_thermostat_cluster.bind()

        assert 0x0000 in danfoss_time_cluster._attr_cache
        assert 0x0001 in danfoss_time_cluster._attr_cache
        assert 0x0002 in danfoss_time_cluster._attr_cache


async def test_danfoss_thermostat_write_attributes(zigpy_device_from_v2_quirk):
    """Test the Thermostat writes behaving correctly, in particular regarding setpoint."""
    device = zigpy_device_from_v2_quirk("Danfoss", "eTRV0103")

    danfoss_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    setting = -100
    operation = -0x01

    def mock_setpoint(oper, sett, manufacturer=None):
        nonlocal operation, setting
        operation = oper
        setting = sett

    # data is written to trv
    patch_danfoss_trv_write = mock.patch.object(
        danfoss_thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )
    patch_danfoss_setpoint = mock.patch.object(
        danfoss_thermostat_cluster,
        "setpoint_command",
        mock.AsyncMock(side_effect=mock_setpoint),
    )

    with patch_danfoss_trv_write:
        # data should be written to trv, but reach thermostat
        await danfoss_thermostat_cluster.write_attributes(
            {"external_open_window_detected": False}
        )
        assert not danfoss_thermostat_cluster._attr_cache[0x4003]

        with patch_danfoss_setpoint:
            # data should be received from danfoss_trv
            await danfoss_thermostat_cluster.write_attributes(
                {"occupied_heating_setpoint": 6}
            )
            assert danfoss_thermostat_cluster._attr_cache[0x0012] == 6
            assert operation == 0x01
            assert setting == 6

            danfoss_thermostat_cluster._attr_cache[0x0015] = (
                5  # min_limit is present normally
            )

            await danfoss_thermostat_cluster.write_attributes({"system_mode": 0x00})
            assert danfoss_thermostat_cluster._attr_cache[0x001C] == 0x04

            # setpoint to min_limit, when system_mode to off
            assert danfoss_thermostat_cluster._attr_cache[0x0012] == 5

            assert operation == 0x01
            assert setting == 5


async def test_customized_standardcluster(zigpy_device_from_v2_quirk):
    """Test customized standard cluster class correctly separating zigbee operations.

    This is regarding manufacturer specific attributes.
    """
    device = zigpy_device_from_v2_quirk("Danfoss", "eTRV0103")

    danfoss_thermostat_cluster = device.endpoints[1].in_clusters[Thermostat.cluster_id]

    assert CustomizedStandardCluster.combine_results([[4545], [5433]], [[345]]) == [
        [4545, 345],
        [5433],
    ]
    assert CustomizedStandardCluster.combine_results(
        [[4545], [5433]], [[345], [45355]]
    ) == [[4545, 345], [5433, 45355]]

    mock_attributes = {
        656: ZCLAttributeDef(type=t.uint8_t, is_manufacturer_specific=True),
        56454: ZCLAttributeDef(type=t.uint8_t, is_manufacturer_specific=False),
    }

    danfoss_thermostat_cluster.attributes = mock_attributes

    reports = None

    def mock_configure_reporting(reps, *args, **kwargs):
        nonlocal reports
        if mock_attributes[reps[0].attrid].is_manufacturer_specific:
            reports = reps

        return [[545], [4545]]

    # data is written to trv
    patch_danfoss_configure_reporting = mock.patch.object(
        CustomCluster,
        "_configure_reporting",
        mock.AsyncMock(side_effect=mock_configure_reporting),
    )

    with patch_danfoss_configure_reporting:
        one = foundation.AttributeReportingConfig()
        one.direction = True
        one.timeout = 4
        one.attrid = 56454

        two = foundation.AttributeReportingConfig()
        two.direction = True
        two.timeout = 4
        two.attrid = 656
        await danfoss_thermostat_cluster._configure_reporting([one, two])
        assert reports == [two]

    reports = None

    def mock_read_attributes(attrs, *args, **kwargs):
        nonlocal reports
        if mock_attributes[attrs[0]].is_manufacturer_specific:
            reports = attrs

        return [[545]]

    # data is written to trv
    patch_danfoss_read_attributes = mock.patch.object(
        CustomCluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read_attributes),
    )

    with patch_danfoss_read_attributes:
        result = await danfoss_thermostat_cluster._read_attributes([56454, 656])
        assert result
        assert reports == [656]

    def mock_read_attributes_fail(attrs, *args, **kwargs):
        nonlocal reports
        if mock_attributes[attrs[0]].is_manufacturer_specific:
            reports = attrs

        return [[545], [4545]]

    # data is written to trv
    patch_danfoss_read_attributes_fail = mock.patch.object(
        CustomCluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read_attributes_fail),
    )

    with patch_danfoss_read_attributes_fail:
        result, fail = await danfoss_thermostat_cluster._read_attributes([56454, 656])
        assert result
        assert fail
        assert reports == [656]
