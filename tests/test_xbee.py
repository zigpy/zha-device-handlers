"""Test XBee device."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import AnalogOutput, Basic, LevelControl, OnOff

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.xbee import (
    XBEE_AT_ENDPOINT,
    XBEE_AT_REQUEST_CLUSTER,
    XBEE_AT_RESPONSE_CLUSTER,
    XBEE_DATA_CLUSTER,
    XBEE_DATA_ENDPOINT,
    XBEE_IO_CLUSTER,
    XBEE_PROFILE_ID,
)
from zhaquirks.xbee.xbee3_io import XBee3Sensor
from zhaquirks.xbee.xbee_io import XBeeSensor

zhaquirks.setup()


async def test_basic_cluster(zigpy_device_from_quirk):
    """Test Basic cluster."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)
    assert xbee3_device.model == "XBee3"

    basic_cluster = xbee3_device.endpoints[XBEE_DATA_ENDPOINT].in_clusters[
        Basic.cluster_id
    ]

    # Check mandatory attributes
    succ, fail = await basic_cluster.read_attributes(("zcl_version", "power_source"))
    assert succ["zcl_version"] == 2
    assert succ["power_source"] == Basic.PowerSource.Unknown


async def test_digital_output(zigpy_device_from_quirk):
    """Test XBeeOnOff cluster."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)
    onoff_cluster = xbee3_device.endpoints[0xD0].in_clusters[OnOff.cluster_id]

    with mock.patch.object(
        xbee3_device.application,
        "remote_at_command",
        create=True,
        new_callable=mock.AsyncMock,
    ) as m1:
        # Turn the switch on
        _, status = await onoff_cluster.command(1)

        m1.assert_awaited_once()
        assert m1.await_args[0][1] == "D0"
        assert m1.await_args[0][2] == 5

        succ, fail = await onoff_cluster.read_attributes(("on_off",))
        assert succ["on_off"] == 1
        m1.reset_mock()

        # Turn the switch off
        _, status = await onoff_cluster.command(0)

        m1.assert_awaited_once()
        assert m1.await_args[0][1] == "D0"
        assert m1.await_args[0][2] == 4
        m1.reset_mock()

        succ, fail = await onoff_cluster.read_attributes(("on_off",))
        assert succ["on_off"] == 0


async def test_analog_output(zigpy_device_from_quirk):
    """Test XBeePWM cluster."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)
    pwm_cluster = xbee3_device.endpoints[0xDA].in_clusters[AnalogOutput.cluster_id]

    # Check mandatory attributes
    succ, fail = await pwm_cluster.read_attributes(
        (
            "max_present_value",
            "min_present_value",
            "out_of_service",
            "resolution",
            "status_flags",
        )
    )
    assert succ["max_present_value"] == 1023.0
    assert succ["min_present_value"] == 0.0
    assert succ["out_of_service"] == 0
    assert succ["resolution"] == 1.0
    assert succ["status_flags"] == 0

    with mock.patch.object(
        xbee3_device.application,
        "remote_at_command",
        create=True,
        new_callable=mock.AsyncMock,
    ) as m1:
        # Write value
        (status,) = await pwm_cluster.write_attributes({"present_value": 122.9})

        assert m1.await_count == 2
        assert m1.await_args_list[0][0][1] == "M0"
        assert m1.await_args_list[0][0][2] == 123
        assert m1.await_args_list[1][0][1] == "P0"
        assert m1.await_args_list[1][0][2] == 2
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]
        m1.reset_mock()

        # Write value with numeric attribute id
        (status,) = await pwm_cluster.write_attributes({0x0055: 234})

        assert m1.await_count == 2
        assert m1.await_args_list[0][0][1] == "M0"
        assert m1.await_args_list[0][0][2] == 234
        assert m1.await_args_list[1][0][1] == "P0"
        assert m1.await_args_list[1][0][2] == 2
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]
        m1.reset_mock()

        # Read value
        m1.configure_mock(return_value=345)

        succ, fail = await pwm_cluster.read_attributes(("present_value",))

        assert succ["present_value"] == 345.0
        m1.assert_awaited_once()
        assert m1.await_args[0][1] == "M0"
        assert len(m1.await_args[0]) == 2
        m1.reset_mock()


async def test_send_serial_data(zigpy_device_from_quirk):
    """Test sending serial data to XBee device."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)
    xbee3_device.application.request.reset_mock()

    # Send serial data
    _, status = (
        await xbee3_device.endpoints[XBEE_DATA_ENDPOINT]
        .out_clusters[XBEE_DATA_CLUSTER]
        .command(0, "Test UART data")
    )

    xbee3_device.application.request.assert_awaited_once_with(
        xbee3_device,
        XBEE_PROFILE_ID,
        XBEE_DATA_CLUSTER,
        XBEE_DATA_ENDPOINT,
        XBEE_DATA_ENDPOINT,
        1,
        b"Test UART data",
        expect_reply=False,
    )
    assert status == foundation.Status.SUCCESS


async def test_receive_serial_data(zigpy_device_from_quirk):
    """Test receiving serial data to XBee device."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)

    listener = mock.MagicMock()
    xbee3_device.endpoints[XBEE_DATA_ENDPOINT].out_clusters[
        LevelControl.cluster_id
    ].add_listener(listener)

    # Receive serial data
    xbee3_device.handle_message(
        XBEE_PROFILE_ID,
        XBEE_DATA_CLUSTER,
        XBEE_DATA_ENDPOINT,
        XBEE_DATA_ENDPOINT,
        b"Test UART data",
    )

    listener.zha_send_event.assert_called_once_with(
        "receive_data", {"data": "Test UART data"}
    )


@pytest.mark.parametrize(
    "command_id, request_value, request_data, response_data, response_command, response_value",
    (
        # Read positive int16_t argument
        (
            67,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeTP",
            b"\x01TP\x00\x00\x18",
            "tp_command_response",
            24,
        ),
        # Read negative int16_t argument
        (
            67,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeTP",
            b"\x01TP\x00\xff\xfc",
            "tp_command_response",
            -4,
        ),
        # Read string argument
        (
            8,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeNI",
            b"\x01NI\x00My Test XBee Device",
            "ni_command_response",
            b"My Test XBee Device",
        ),
        # Write string argument
        (
            8,
            b"My Test XBee Device",  # TODO: Check how hass sends strings in zha.issue_zigbee_cluster_command
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeNIMy Test XBee Device",
            b"\x01NI\x00",
            "ni_command_response",
            None,
        ),
        # Read uint64_t argument
        (
            15,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeOP",
            b"\x01OP\x00\xff\xee\xdd\xcc\xbb\xaa\x99\x88",
            "op_command_response",
            0xFFEEDDCCBBAA9988,
        ),
        # Write uint64_t argument
        (
            15,
            0xFEDCBA9876543210,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeOP\xfe\xdc\xba\x98\x76\x54\x32\x10",
            b"\x01OP\x00",
            "op_command_response",
            None,
        ),
        # Read uint32_t argument
        (
            1,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeDH",
            b"\x01DH\x00\xff\xee\xdd\xcc",
            "dh_command_response",
            0xFFEEDDCC,
        ),
        # Write uint32_t argument
        (
            2,
            0,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeDL\x00\x00\x00\x00",
            b"\x01DL\x00",
            "dl_command_response",
            None,
        ),
        # Read uint16_t argument
        (
            65,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe%V",
            b"\x01%V\x00\x0c\xe4",
            "percentv_command_response",
            3300,
        ),
        # Write uint16_t argument
        (
            66,
            2700,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeV+\x0a\x8c",
            b"\x01V+\x00",
            "vplus_command_response",
            None,
        ),
        # Read uint8_t argument
        (
            54,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeP0",
            b"\x01P0\x00\x00",
            "p0_command_response",
            0,
        ),
        # Write uint8_t argument
        (
            46,
            5,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeD0\x05",
            b"\x01D0\x00",
            "d0_command_response",
            None,
        ),
        # Read bool argument
        (
            31,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfePM",
            b"\x01PM\x00\x00",
            "pm_command_response",
            False,
        ),
        # Write bool argument
        (
            31,
            True,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfePM\x01",
            b"\x01PM\x00",
            "pm_command_response",
            None,
        ),
        # Command with no arguments
        (
            93,
            None,
            b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeAS",
            b"\x01AS\x00",
            "as_command_response",
            None,
        ),
    ),
)
async def test_remote_at_non_native(
    zigpy_device_from_quirk,
    command_id,
    request_value,
    request_data,
    response_data,
    response_command,
    response_value,
):
    """Test remote AT commands with non-XBee coordinator."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)

    listener = mock.MagicMock()
    xbee3_device.endpoints[XBEE_DATA_ENDPOINT].out_clusters[
        LevelControl.cluster_id
    ].add_listener(listener)

    def mock_at_response(*args, **kwargs):
        """Simulate remote AT command response from device."""
        xbee3_device.handle_message(
            XBEE_PROFILE_ID,
            XBEE_AT_RESPONSE_CLUSTER,
            XBEE_AT_ENDPOINT,
            XBEE_AT_ENDPOINT,
            response_data,
        )
        return mock.DEFAULT

    xbee3_device.application.request.reset_mock()
    xbee3_device.application.request.configure_mock(side_effect=mock_at_response)

    # Send remote AT command request
    _, status = (
        await xbee3_device.endpoints[XBEE_AT_ENDPOINT]
        .out_clusters[XBEE_AT_REQUEST_CLUSTER]
        .command(command_id, request_value)
    )

    xbee3_device.application.request.configure_mock(side_effect=None)

    xbee3_device.application.request.assert_awaited_once_with(
        xbee3_device,
        XBEE_PROFILE_ID,
        XBEE_AT_REQUEST_CLUSTER,
        XBEE_AT_ENDPOINT,
        XBEE_AT_ENDPOINT,
        1,
        request_data,
        expect_reply=False,
    )
    assert status == foundation.Status.SUCCESS
    listener.zha_send_event.assert_called_once_with(
        response_command, {"response": response_value}
    )


@pytest.mark.parametrize(
    "command_id, command, request_value, response_value",
    (
        # Read positive int16_t argument
        (67, "TP", None, 24),
        # Read negative int16_t argument
        (67, "TP", None, -4),
        # Read string argument
        (8, "NI", None, "My Test XBee Device"),
        # Write string argument
        (8, "NI", "My Test XBee Device", None),
        # Read uint64_t argument
        (15, "OP", None, 0xFFEEDDCCBBAA9988),
        # Write uint64_t argument
        (15, "OP", 0xFEDCBA9876543210, None),
        # Read uint32_t argument
        (1, "DH", None, 0xFFEEDDCC),
        # Write uint32_t argument
        (2, "DL", 0, None),
        # Read uint16_t argument
        (65, "%V", None, 3300),
        # Write uint16_t argument
        (66, "V+", 2700, None),
        # Read uint8_t argument
        (54, "P0", None, 0),
        # Write uint8_t argument
        (46, "D0", 5, None),
        # Read bool argument
        (31, "PM", None, False),
        # Write bool argument
        (31, "PM", True, None),
        # Command with no arguments
        (93, "AS", None, None),
    ),
)
async def test_remote_at_native(
    zigpy_device_from_quirk, command_id, command, request_value, response_value
):
    """Test remote AT commands with XBee coordinator."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)

    listener = mock.MagicMock()
    xbee3_device.endpoints[XBEE_DATA_ENDPOINT].out_clusters[
        LevelControl.cluster_id
    ].add_listener(listener)

    with mock.patch.object(
        xbee3_device.application,
        "remote_at_command",
        create=True,
        new_callable=mock.AsyncMock,
    ) as m1:
        m1.configure_mock(return_value=response_value)

        # Send remote AT command request
        _, status = (
            await xbee3_device.endpoints[XBEE_AT_ENDPOINT]
            .out_clusters[XBEE_AT_REQUEST_CLUSTER]
            .command(command_id, request_value)
        )

        if request_value is None:
            m1.assert_awaited_once_with(
                0x1234, command, apply_changes=True, encryption=False
            )
        else:
            m1.assert_awaited_once_with(
                0x1234, command, request_value, apply_changes=True, encryption=False
            )
        assert status == foundation.Status.SUCCESS
        listener.zha_send_event.assert_called_once_with(
            command.replace("%V", "PercentV").replace("V+", "VPlus").lower()
            + "_command_response",
            {"response": response_value},
        )


async def test_remote_at_tx_failure(zigpy_device_from_quirk):
    """Test remote AT commands with non-XBee coordinator with tx failure."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)

    listener = mock.MagicMock()
    xbee3_device.endpoints[XBEE_DATA_ENDPOINT].out_clusters[
        LevelControl.cluster_id
    ].add_listener(listener)

    def mock_at_response(*args, **kwargs):
        """Simulate remote AT command response from device."""
        xbee3_device.handle_message(
            XBEE_PROFILE_ID,
            XBEE_AT_RESPONSE_CLUSTER,
            XBEE_AT_ENDPOINT,
            XBEE_AT_ENDPOINT,
            b"\x01TP\x04",
        )
        return mock.DEFAULT

    xbee3_device.application.request.reset_mock()
    xbee3_device.application.request.configure_mock(side_effect=mock_at_response)

    # Send remote AT command request
    with pytest.raises(RuntimeError) as excinfo:
        _, status = (
            await xbee3_device.endpoints[XBEE_AT_ENDPOINT]
            .out_clusters[XBEE_AT_REQUEST_CLUSTER]
            .command(67)
        )

    assert str(excinfo.value) == "AT Command response: TX_FAILURE"
    xbee3_device.application.request.configure_mock(side_effect=None)


async def test_io_sample_report(zigpy_device_from_quirk):
    """Test DigitalIOCluster cluster."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)

    digital_listeners = [
        ClusterListener(xbee3_device.endpoints[e].on_off) for e in range(0xD0, 0xDF)
    ]
    analog_listeners = [
        ClusterListener(xbee3_device.endpoints[e if e != 0xD4 else 0xD7].analog_input)
        for e in range(0xD0, 0xD5)
    ]

    #   {'digital_samples': [1, None, 0, None, 1, None, 0, None, 1, None, 0, None, 1, None, 0], 'analog_samples': [341, None, 682, None, None, None, None, 3305]}
    xbee3_device.handle_message(
        XBEE_PROFILE_ID,
        XBEE_IO_CLUSTER,
        XBEE_DATA_ENDPOINT,
        XBEE_DATA_ENDPOINT,
        b"\x01\x55\x55\x85\x11\x11\x01\x55\x02\xaa\x0c\xe9",
    )

    for i in range(len(digital_listeners)):
        assert len(digital_listeners[i].cluster_commands) == 0
        assert len(digital_listeners[i].attribute_updates) == (i + 1) % 2
        if (i + 1) % 2:
            assert digital_listeners[i].attribute_updates[0] == (
                0x0000,
                (i / 2 + 1) % 2,
            )

    for i in range(len(analog_listeners)):
        assert len(analog_listeners[i].cluster_commands) == 0
        assert len(analog_listeners[i].attribute_updates) == (i + 1) % 2
        if (i + 1) % 2:
            assert analog_listeners[i].attribute_updates[0][0] == 0x0055

    assert 33.33333 < analog_listeners[0].attribute_updates[0][1] < 33.33334
    assert 66.66666 < analog_listeners[2].attribute_updates[0][1] < 66.66667
    assert analog_listeners[4].attribute_updates[0] == (0x0055, 3.305)


async def test_io_sample_report_on_at_response(zigpy_device_from_quirk):
    """Test update samples on non-native IS command response."""

    xbee_device = zigpy_device_from_quirk(XBeeSensor)
    assert xbee_device.model == "XBee2"

    digital_listeners = [
        ClusterListener(xbee_device.endpoints[e].on_off) for e in range(0xD0, 0xDF)
    ]
    analog_listeners = [
        ClusterListener(xbee_device.endpoints[e if e != 0xD4 else 0xD7].analog_input)
        for e in range(0xD0, 0xD5)
    ]

    listener = mock.MagicMock()
    xbee_device.endpoints[XBEE_DATA_ENDPOINT].out_clusters[
        LevelControl.cluster_id
    ].add_listener(listener)

    def mock_at_response(*args, **kwargs):
        """Simulate remote AT command response from device."""
        xbee_device.handle_message(
            XBEE_PROFILE_ID,
            XBEE_AT_RESPONSE_CLUSTER,
            XBEE_AT_ENDPOINT,
            XBEE_AT_ENDPOINT,
            b"\x01IS\x00\x01\x55\x55\x85\x11\x11\x01\x55\x02\xaa\x0c\xe9",
        )
        return mock.DEFAULT

    xbee_device.application.request.reset_mock()
    xbee_device.application.request.configure_mock(side_effect=mock_at_response)

    # Send remote AT command request
    _, status = (
        await xbee_device.endpoints[XBEE_AT_ENDPOINT]
        .out_clusters[XBEE_AT_REQUEST_CLUSTER]
        .command(92)
    )

    xbee_device.application.request.configure_mock(side_effect=None)

    xbee_device.application.request.assert_awaited_once_with(
        xbee_device,
        XBEE_PROFILE_ID,
        XBEE_AT_REQUEST_CLUSTER,
        XBEE_AT_ENDPOINT,
        XBEE_AT_ENDPOINT,
        1,
        b"2\x00\x02\x01\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfeIS",
        expect_reply=False,
    )
    assert status == foundation.Status.SUCCESS
    listener.zha_send_event.assert_called_once_with(
        "is_command_response",
        {
            "response": {
                "digital_samples": [
                    1,
                    None,
                    0,
                    None,
                    1,
                    None,
                    0,
                    None,
                    1,
                    None,
                    0,
                    None,
                    1,
                    None,
                    0,
                ],
                "analog_samples": [341, None, 682, None, None, None, None, 3305],
            }
        },
    )

    for i in range(len(digital_listeners)):
        assert len(digital_listeners[i].cluster_commands) == 0
        assert len(digital_listeners[i].attribute_updates) == (i + 1) % 2
        if (i + 1) % 2:
            assert digital_listeners[i].attribute_updates[0] == (
                0x0000,
                (i / 2 + 1) % 2,
            )

    for i in range(len(analog_listeners)):
        assert len(analog_listeners[i].cluster_commands) == 0
        assert len(analog_listeners[i].attribute_updates) == (i + 1) % 2
        if (i + 1) % 2:
            assert analog_listeners[i].attribute_updates[0][0] == 0x0055

    assert 33.33333 < analog_listeners[0].attribute_updates[0][1] < 33.33334
    assert 66.66666 < analog_listeners[2].attribute_updates[0][1] < 66.66667
    assert analog_listeners[4].attribute_updates[0] == (0x0055, 3.305)


@mock.patch("zigpy.zdo.ZDO.handle_ieee_addr_req")
async def test_zdo(handle_mgmt_lqi_resp, zigpy_device_from_quirk):
    """Test receiving ZDO data from XBee device."""

    xbee3_device = zigpy_device_from_quirk(XBee3Sensor)

    # Receive ZDOCmd.IEEE_addr_req
    xbee3_device.handle_message(0, 0x0001, 0, 0, b"\x07\x34\x12\x00\x00")

    assert handle_mgmt_lqi_resp.call_count == 1
    assert len(handle_mgmt_lqi_resp.call_args_list[0][0]) == 4
    assert handle_mgmt_lqi_resp.call_args_list[0][0][0].tsn == 0x07
    assert handle_mgmt_lqi_resp.call_args_list[0][0][0].command_id == 0x0001
    assert handle_mgmt_lqi_resp.call_args_list[0][0][1] == 0x1234
    assert handle_mgmt_lqi_resp.call_args_list[0][0][2] == 0
    assert handle_mgmt_lqi_resp.call_args_list[0][0][3] == 0
