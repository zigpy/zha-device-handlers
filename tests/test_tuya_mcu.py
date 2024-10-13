"""Tests for Tuya quirks."""

import datetime
from unittest import mock

import pytest
from zigpy.zcl import foundation

from tests.common import ClusterListener, MockDatetime
import zhaquirks
from zhaquirks.tuya import TUYA_MCU_VERSION_RSP, TUYA_SET_TIME, TuyaDPType
from zhaquirks.tuya.mcu import (
    ATTR_MCU_VERSION,
    TUYA_MCU_CONNECTION_STATUS,
    TuyaAttributesCluster,
    TuyaClusterData,
    TuyaMCUCluster,
)

zhaquirks.setup()

ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6d\x82"
ZCL_TUYA_SET_TIME = b"\x09\x12\x24\x0d\x00"


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
@pytest.mark.parametrize(
    "frame, zcl_tsn, mcu_tsn",
    (
        (
            b"\t@%\t\x00",
            64,
            9,
        ),
        (
            b"\tA%\x0b\x00",
            65,
            11,
        ),
        (
            b"\tB%\r\x00",
            66,
            13,
        ),
        (
            b"\t\x13%/\x00",
            19,
            47,
        ),
        (
            b"\t\x14%1\x00",
            20,
            49,
        ),
        (
            b"\t\x15%3\x00",
            21,
            51,
        ),
        (
            b"\t\x1b%\xf1\x00",
            27,
            241,
        ),
        (
            b"\t\x1c%\xf3\x00",
            28,
            243,
        ),
        (
            b"\t@%\xb9\x00",
            64,
            185,
        ),
        (
            b"\t'%\x11\x00",
            39,
            17,
        ),
        (
            b"\tS%\xec\x00",
            83,
            236,
        ),
        (
            b"\tu%\xd4\x00",
            117,
            212,
        ),
        (
            b"\tv%\xd6\x00",
            118,
            214,
        ),
        (
            b"\tl%\x1e\x00",
            108,
            30,
        ),
    ),
)
async def test_tuya_connection_status(
    zigpy_device_from_quirk, quirk, frame, zcl_tsn, mcu_tsn
):
    """Test TUYA_MCU_CONNECTION_STATUS messages."""

    tuya_device = zigpy_device_from_quirk(quirk)

    tuya_cluster = tuya_device.endpoints[1].tuya_manufacturer
    cluster_listener = ClusterListener(tuya_cluster)

    assert len(cluster_listener.attribute_updates) == 0

    # simulate a TUYA_MCU_CONNECTION_STATUS message
    hdr, args = tuya_cluster.deserialize(frame)
    assert hdr.command_id == TUYA_MCU_CONNECTION_STATUS
    assert hdr.tsn == zcl_tsn

    with mock.patch.object(
        TuyaAttributesCluster, "command"
    ) as m1:  # tuya_cluster parent class (because of super() call)
        tuya_cluster.handle_message(hdr, args)

        assert len(cluster_listener.cluster_commands) == 1
        assert cluster_listener.cluster_commands[0][1] == TUYA_MCU_CONNECTION_STATUS

        assert cluster_listener.cluster_commands[0][2].payload.tsn == mcu_tsn
        assert cluster_listener.cluster_commands[0][2].payload.status == b""

        m1.assert_called_once_with(
            TUYA_MCU_CONNECTION_STATUS,
            tuya_cluster.TuyaConnectionStatus(tsn=mcu_tsn, status=b"\x01"),
            expect_reply=False,
        )


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

    with mock.patch.object(tuya_cluster, "handle_mcu_version_response") as m1:
        tuya_cluster.handle_message(hdr, args)

        assert len(cluster_listener.cluster_commands) == 2
        assert cluster_listener.cluster_commands[1][1] == TUYA_MCU_VERSION_RSP
        assert cluster_listener.cluster_commands[1][2].version.version_raw == 130
        assert cluster_listener.cluster_commands[1][2].version.version == "2.0.2"

        m1.assert_called_once_with(
            tuya_cluster.MCUVersion(status=1, tsn=109, version_raw=130)
        )

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
        endpoint_id=1,
        cluster_name="on_off",
        cluster_attr="on_off",
        attr_value=1,
        expect_reply=True,
    )
    tcd_dimmer2_on = TuyaClusterData(
        endpoint_id=2,
        cluster_name="on_off",
        cluster_attr="on_off",
        attr_value=1,
        expect_reply=True,
    )
    tcd_dimmer2_off = TuyaClusterData(
        endpoint_id=2,
        cluster_name="on_off",
        cluster_attr="on_off",
        attr_value=0,
        expect_reply=True,
    )
    tcd_dimmer2_level = TuyaClusterData(
        endpoint_id=2,
        cluster_name="level",
        cluster_attr="current_level",
        attr_value=75,
        expect_reply=True,
    )
    tcd_dimmer2_level0 = TuyaClusterData(
        endpoint_id=2,
        cluster_name="level",
        cluster_attr="current_level",
        attr_value=0,
        expect_reply=True,
    )

    result_1 = tuya_cluster.from_cluster_data(tcd_1)
    assert result_1
    assert len(result_1) == 1
    assert result_1[0].datapoints
    assert len(result_1[0].datapoints) == 1
    assert result_1[0].datapoints[0].dp == 9
    assert result_1[0].datapoints[0].data.dp_type == TuyaDPType.VALUE
    assert result_1[0].datapoints[0].data.raw == b"\x00\x00\x00b"

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
        rsp = await dimmer2_cluster.command(0x0004, 75)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_any_call(tcd_dimmer2_on)  # on_off
        m1.assert_called_with(tcd_dimmer2_level)  # current_level
        assert m1.call_count == 3

        # test `move_to_level_with_on_off` quirk (call on_off + current_level)
        rsp = await dimmer2_cluster.command(
            0x0004, 75, 0
        )  # extra args ¿transition time?. Not on_off for sure
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_any_call(tcd_dimmer2_on)  # on_off
        m1.assert_called_with(tcd_dimmer2_level)  # current_level
        assert m1.call_count == 5

        # test `move_to_level_with_on_off` quirk (call on_off + current_level)
        rsp = await dimmer2_cluster.command(0x0004, 0, level=75)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_any_call(tcd_dimmer2_on)  # on_off
        m1.assert_called_with(tcd_dimmer2_level)  # current_level
        assert m1.call_count == 7

        # test `move_to_level_with_on_off` quirk (call on_off only)
        rsp = await dimmer2_cluster.command(0x0004)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_called_with(tcd_dimmer2_off)  # on_off
        assert m1.call_count == 8

        # test `move_to_level` quirk (only call current_level)
        rsp = await dimmer2_cluster.command(0x0000)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_called_with(tcd_dimmer2_level0)  # current_level
        assert m1.call_count == 9

        # test `move_to_level` quirk (only call current_level)
        rsp = await dimmer2_cluster.command(0x0000, 75)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_called_with(tcd_dimmer2_level)  # current_level
        assert m1.call_count == 10

        # test `move_to_level` quirk (only call current_level)
        rsp = await dimmer2_cluster.command(0x0000, level=75)
        assert rsp.status == foundation.Status.SUCCESS
        m1.assert_called_with(tcd_dimmer2_level)  # current_level
        assert m1.call_count == 11


async def test_tuya_mcu_classes():
    """Test tuya conversion from Data to ztype and reverse."""

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
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x05\xff")[0]
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
