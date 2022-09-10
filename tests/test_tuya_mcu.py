"""Tests for Tuya quirks."""

import datetime
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import foundation

import zhaquirks
from zhaquirks.tuya import TUYA_MCU_VERSION_RSP, TUYA_SET_TIME
from zhaquirks.tuya.mcu import (
    ATTR_MCU_VERSION,
    TuyaAttributesCluster,
    TuyaClusterData,
    TuyaDPType,
    TuyaMCUCluster,
)

from tests.common import ClusterListener, MockDatetime

zhaquirks.setup()

ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6D\x82"
ZCL_TUYA_SET_TIME = b"\x09\x12\x24\x0D\x00"


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_tuya_version(zigpy_device_from_quirk, quirk):
    """Test TUYA_MCU_VERSION_RSP messages."""

    tuya_device = zigpy_device_from_quirk(quirk)

    tuya_cluster = tuya_device.endpoints[1].tuya_manufacturer
    cluster_listener = ClusterListener(tuya_cluster)

    assert len(cluster_listener.attribute_updates) == 0

    # simulate a TUYA_MCU_VERSION_RSP message
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VERSION_RSP)
    assert hdr.command_id == TUYA_MCU_VERSION_RSP

    tuya_cluster.handle_message(hdr, args)
    assert len(cluster_listener.attribute_updates) == 1
    assert cluster_listener.attribute_updates[0][0] == ATTR_MCU_VERSION
    assert cluster_listener.attribute_updates[0][1] == "2.0.2"

    # read 'mcu_version' from cluster's attributes
    succ, fail = await tuya_cluster.read_attributes(("mcu_version",))
    assert succ["mcu_version"] == "2.0.2"


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_tuya_mcu_set_time(zigpy_device_from_quirk, quirk):
    """Test set_time requests (0x24) messages for MCU devices."""

    tuya_device = zigpy_device_from_quirk(quirk)

    tuya_cluster = tuya_device.endpoints[1].tuya_manufacturer
    cluster_listener = ClusterListener(tuya_cluster)

    # Mock datetime
    origdatetime = datetime.datetime
    datetime.datetime = MockDatetime

    # simulate a SET_TIME message
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SET_TIME)
    assert hdr.command_id == TUYA_SET_TIME

    with mock.patch.object(
        TuyaAttributesCluster, "command"
    ) as m1:  # tuya_cluster parent class (because of super() call)
        tuya_cluster.handle_message(hdr, args)

        assert len(cluster_listener.cluster_commands) == 1
        assert cluster_listener.cluster_commands[0][1] == TUYA_SET_TIME

        m1.assert_called_once_with(
            TUYA_SET_TIME, [0, 0, 28, 32, 0, 0, 14, 16], expect_reply=False
        )

    # restore datetime
    datetime.datetime = origdatetime  # restore datetime


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_tuya_methods(zigpy_device_from_quirk, quirk):
    """Test TUYA_MCU_VERSION_RSP messages."""

    tuya_device = zigpy_device_from_quirk(quirk)

    tuya_cluster = tuya_device.endpoints[1].tuya_manufacturer
    dimmer2_cluster = tuya_device.endpoints[2].level
    switch1_cluster = tuya_device.endpoints[1].on_off

    tcd_1 = TuyaClusterData(endpoint_id=2, cluster_attr="minimum_level", attr_value=25)

    tcd_switch1_on = TuyaClusterData(
        endpoint_id=1, cluster_attr="on_off", attr_value=1, expect_reply=True
    )
    tcd_dimmer2_on = TuyaClusterData(
        endpoint_id=2, cluster_attr="on_off", attr_value=1, expect_reply=True
    )
    tcd_dimmer2_level = TuyaClusterData(
        endpoint_id=2, cluster_attr="current_level", attr_value=75, expect_reply=True
    )

    result_1 = tuya_cluster.from_cluster_data(tcd_1)
    assert result_1
    assert result_1.dp == 9
    assert result_1.data.dp_type == TuyaDPType.VALUE
    assert result_1.data.raw == b"\x00\x00\x00b"

    tcd_2 = TuyaClusterData(
        endpoint_id=7, cluster_attr="not_exists_attribute", attr_value=25
    )
    result_2 = tuya_cluster.from_cluster_data(tcd_2)
    assert not result_2

    with mock.patch.object(tuya_cluster, "create_catching_task") as m1:
        tuya_cluster.tuya_mcu_command(tcd_2)
        # no DP resolution will not call TUYA_SET_DATA command
        m1.assert_not_called()

    result_3 = await dimmer2_cluster.command(0x0006)
    assert result_3.status == foundation.Status.UNSUP_CLUSTER_COMMAND

    with mock.patch.object(tuya_cluster, "tuya_mcu_command") as m1:
        rsp = await switch1_cluster.command(0x0001)

        m1.assert_called_once_with(tcd_switch1_on)
        assert rsp.status == foundation.Status.SUCCESS
        assert m1.call_count == 1

        rsp = await switch1_cluster.command(0x0004)
        m1.assert_called_once_with(tcd_switch1_on)  # no extra calls
        assert rsp.status == foundation.Status.UNSUP_CLUSTER_COMMAND
        assert m1.call_count == 1

        # test `move_to_level_with_on_off` quirk (call on_off + current_level)
        rsp = await dimmer2_cluster.command(0x0004, 75, 1)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_any_call(tcd_dimmer2_on)  # on_off
        m1.assert_called_with(tcd_dimmer2_level)  # current_level
        assert m1.call_count == 3


async def test_tuya_mcu_classes():
    """Test tuya conversion from Data to ztype and reverse."""

    # Test TuyaDPType class
    assert len(TuyaDPType) == 6
    assert TuyaDPType.BOOL.ztype == t.Bool
    # no ztype for TuyaDPType.RAW
    assert not TuyaDPType.RAW.ztype
    assert TuyaDPType(3) == TuyaDPType.STRING

    # Test TuyaMCUCluster.MCUVersion class
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x03\x82")[0]
    assert mcu_version
    assert mcu_version.tsn == 3
    assert mcu_version.version_raw == 130
    assert mcu_version.version == "2.0.2"
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x04\x01")[0]
    assert mcu_version
    assert mcu_version.version_raw == 1
    assert mcu_version.version == "0.0.1"
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x05\xFF")[0]
    assert mcu_version
    assert mcu_version.version_raw == 255
    assert mcu_version.version == "3.3.15"
    mcu_version = TuyaMCUCluster.MCUVersion()
    assert mcu_version
    assert not mcu_version.version

    # test TuyaClusterData.manufacturer values
    t_c_d = TuyaClusterData(manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID)
    assert t_c_d.manufacturer == -1
    t_c_d = TuyaClusterData(manufacturer=4619)
    assert t_c_d.manufacturer == 4619
    t_c_d = TuyaClusterData(manufacturer="4098")
    assert t_c_d.manufacturer == 4098
    with pytest.raises(ValueError):
        TuyaClusterData(manufacturer="xiaomi")
    with pytest.raises(ValueError):
        TuyaClusterData(manufacturer=b"")
