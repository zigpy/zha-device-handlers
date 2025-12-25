"""Tests for Niko quirks."""

import asyncio
from unittest import mock

import pytest
from zigpy import types as t
from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
import zhaquirks

zhaquirks.setup()


SWITCH_SINGLE = (
    ["NIKO NV", "Single connectable switch,10A"],
    {"endpoint_ids": [0, 1, 242]},
)

SWITCH_DOUBLE = (
    ["NIKO NV", "Double connectable switch,10A"],
    {"endpoint_ids": [0, 1, 2, 242]},
)


# pylint: disable=R0903
class TestNikoSwitch:
    """Tests for Niko Connected Switches (552-721X1 and 552-721X2)."""

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    class TestClusters:
        """Test whether all clusters are present and complete."""

        def test_config_cluster(self, zigpy_device_from_v2_quirk, switch):
            """Test the configuration cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            cluster = device.endpoints[1].niko_config

            assert {attr.id: attr.access for attr in cluster.AttributeDefs} == {
                0x0000: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0100: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0104: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0105: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0107: foundation.ZCLAttributeAccess.from_str("rw"),
            }

        @mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
        async def test_config_cluster_preloading(
            self, zigpy_device_from_v2_quirk, switch
        ):
            """Test whether the config cluster pre-loads all attributes."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            cluster = device.endpoints[1].niko_config

            with mock.patch.object(
                cluster, "read_attributes", mock.AsyncMock()
            ) as read_attributes:
                await cluster.bind()
                read_attributes.assert_called_with(cluster.attributes)
                await wait_for_zigpy_tasks()

        def test_state_cluster(self, zigpy_device_from_v2_quirk, switch):
            """Test the state cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            cluster = device.endpoints[1].niko_state

            assert {attr.id: attr.access for attr in cluster.AttributeDefs} == {
                0x0001: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0002: foundation.ZCLAttributeAccess.from_str("p"),
            }

        def test_buttons_cluster(self, zigpy_device_from_v2_quirk, switch):
            """Test the buttons cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            cluster = device.endpoints[1].buttons

            assert {attr.id: attr.access for attr in cluster.AttributeDefs} == {
                # Button states
                0x0001: foundation.ZCLAttributeAccess.from_str("rp"),
                0x0002: foundation.ZCLAttributeAccess.from_str("rp"),
                0x0003: foundation.ZCLAttributeAccess.from_str("rp"),
                0x0004: foundation.ZCLAttributeAccess.from_str("rp"),
                # Status LED on/off
                0x0011: foundation.ZCLAttributeAccess.from_str("rwp"),
                0x0013: foundation.ZCLAttributeAccess.from_str("rwp"),
                # Status LED sync
                0x0021: foundation.ZCLAttributeAccess.from_str("rw"),
                0x0023: foundation.ZCLAttributeAccess.from_str("rw"),
                # Status LED alert color
                0x0100: foundation.ZCLAttributeAccess.from_str("rw"),
            }

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    # pylint: disable=R0903
    class TestConfiguration:
        """Test device configuration."""

        async def test_apply_custom_configuration(
            self, zigpy_device_from_v2_quirk, switch
        ):
            """Test whether attributes are set correctly."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            config_cluster = device.endpoints[1].niko_config
            state_cluster = device.endpoints[1].niko_state

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                await config_cluster.apply_custom_configuration()
                calls = request.mock_calls

                assert len(calls) == 1
                assert calls[0].kwargs["cluster"] == config_cluster.cluster_id
                assert (
                    calls[0].kwargs["command_id"]
                    == foundation.GeneralCommand.Write_Attributes
                )
                assert (
                    calls[0].kwargs["data"] == b"\x04\x5f\x12\x01\x02\x04\x01\x20\x01"
                )

            with mock.patch.object(
                state_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                await state_cluster.apply_custom_configuration()
                calls = request.mock_calls

                assert len(calls) == 1
                assert calls[0].kwargs["cluster"] == state_cluster.cluster_id
                assert (
                    calls[0].kwargs["command_id"]
                    == foundation.GeneralCommand.Write_Attributes
                )
                assert (
                    calls[0].kwargs["data"] == b"\x04\x5f\x12\x02\x02\x01\x00\x18\x1e"
                )

    class TestDeviceAutomationTriggers:
        """Test whether all device automation triggers are present."""

        def test_single_switch(self, zigpy_device_from_v2_quirk):
            """Test device automation triggers for 552-721X1."""
            device = zigpy_device_from_v2_quirk(*SWITCH_SINGLE[0], **SWITCH_SINGLE[1])
            triggers = device.device_automation_triggers

            assert triggers == {
                # Button 1
                ("remote_button_short_press", "button_1"): {
                    "command": "button_1_remote_button_short_press"
                },
                ("remote_button_short_release", "button_1"): {
                    "command": "button_1_remote_button_short_release"
                },
                ("remote_button_long_press", "button_1"): {
                    "command": "button_1_remote_button_long_press"
                },
                ("remote_button_long_release", "button_1"): {
                    "command": "button_1_remote_button_long_release"
                },
                # Button 2
                ("remote_button_short_press", "button_2"): {
                    "command": "button_2_remote_button_short_press"
                },
                ("remote_button_short_release", "button_2"): {
                    "command": "button_2_remote_button_short_release"
                },
                ("remote_button_long_press", "button_2"): {
                    "command": "button_2_remote_button_long_press"
                },
                ("remote_button_long_release", "button_2"): {
                    "command": "button_2_remote_button_long_release"
                },
            }

        def test_double_switch(self, zigpy_device_from_v2_quirk):
            """Test device automation triggers for 552-721X2."""
            device = zigpy_device_from_v2_quirk(*SWITCH_DOUBLE[0], **SWITCH_DOUBLE[1])
            triggers = device.device_automation_triggers

            assert triggers == {
                # Button 1
                ("remote_button_short_press", "button_1"): {
                    "command": "button_1_remote_button_short_press"
                },
                ("remote_button_short_release", "button_1"): {
                    "command": "button_1_remote_button_short_release"
                },
                ("remote_button_long_press", "button_1"): {
                    "command": "button_1_remote_button_long_press"
                },
                ("remote_button_long_release", "button_1"): {
                    "command": "button_1_remote_button_long_release"
                },
                # Button 2
                ("remote_button_short_press", "button_2"): {
                    "command": "button_2_remote_button_short_press"
                },
                ("remote_button_short_release", "button_2"): {
                    "command": "button_2_remote_button_short_release"
                },
                ("remote_button_long_press", "button_2"): {
                    "command": "button_2_remote_button_long_press"
                },
                ("remote_button_long_release", "button_2"): {
                    "command": "button_2_remote_button_long_release"
                },
                # Button 3
                ("remote_button_short_press", "button_3"): {
                    "command": "button_3_remote_button_short_press"
                },
                ("remote_button_short_release", "button_3"): {
                    "command": "button_3_remote_button_short_release"
                },
                ("remote_button_long_press", "button_3"): {
                    "command": "button_3_remote_button_long_press"
                },
                ("remote_button_long_release", "button_3"): {
                    "command": "button_3_remote_button_long_release"
                },
                # Button 4
                ("remote_button_short_press", "button_4"): {
                    "command": "button_4_remote_button_short_press"
                },
                ("remote_button_short_release", "button_4"): {
                    "command": "button_4_remote_button_short_release"
                },
                ("remote_button_long_press", "button_4"): {
                    "command": "button_4_remote_button_long_press"
                },
                ("remote_button_long_release", "button_4"): {
                    "command": "button_4_remote_button_long_release"
                },
            }

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    class TestButtonState:
        """Test button state and associated events."""

        @pytest.mark.parametrize(
            "case",
            [
                # Button 1
                [(0x00000, {})],
                [(0x00010, {0x0001})],
                [(0x00040, {})],
                # Button 2
                [(0x00000, {})],
                [(0x00100, {0x0002})],
                [(0x00400, {})],
                # Button 3
                [(0x00000, {})],
                [(0x01000, {0x0003})],
                [(0x04000, {})],
                # Button 4
                [(0x00000, {})],
                [(0x10000, {0x0004})],
                [(0x40000, {})],
                # Mixed
                [
                    (0x00000, {}),
                    (0x44440, {}),
                    (0x00010, {0x0001}),
                    (0x00110, {0x0001, 0x0002}),
                    (0x00140, {0x0002}),
                    (0x01100, {0x0002, 0x0003}),
                    (0x01400, {0x0003}),
                    (0x11000, {0x0003, 0x0004}),
                    (0x14000, {0x0004}),
                    (0x40000, {}),
                    (0x00110, {0x0001, 0x0002}),
                    (0x00440, {}),
                    (0x11110, {0x0001, 0x0002, 0x0003, 0x0004}),
                    (0x44440, {}),
                ],
            ],
        )
        async def test_read(self, zigpy_device_from_v2_quirk, switch, case):
            """Test whether button state changes cause attribute changes in the buttons cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])

            state_cluster = device.endpoints[1].niko_state
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                state_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                for state, on_buttons in case:
                    state_cluster.update_attribute(0x0002, state)

                    attrs, _ = await buttons_cluster.read_attributes(
                        [
                            0x0001,
                            0x0002,
                            0x0003,
                            0x0004,
                        ]
                    )
                    assert attrs[0x0001] == t.Bool(0x0001 in on_buttons)
                    assert attrs[0x0002] == t.Bool(0x0002 in on_buttons)
                    assert attrs[0x0003] == t.Bool(0x0003 in on_buttons)
                    assert attrs[0x0004] == t.Bool(0x0004 in on_buttons)

        @pytest.mark.parametrize(
            "case",
            [
                # Button 1
                [(0x00000, None, None)],
                [(0x00010, "button_1", "remote_button_short_press")],
                [(0x00040, "button_1", "remote_button_short_release")],
                # Button 2
                [(0x00000, None, None)],
                [(0x00100, "button_2", "remote_button_short_press")],
                [(0x00400, "button_2", "remote_button_short_release")],
                # Button 3
                [(0x00000, None, None)],
                [(0x01000, "button_3", "remote_button_short_press")],
                [(0x04000, "button_3", "remote_button_short_release")],
                # Button 4
                [(0x00000, None, None)],
                [(0x10000, "button_4", "remote_button_short_press")],
                [(0x40000, "button_4", "remote_button_short_release")],
                # Repeated same state
                [
                    (0x00000, None, None),
                    (0x00010, "button_1", "remote_button_short_press"),
                    (0x00010, None, None),
                    (0x00010, None, None),
                    (0x00000, None, None),
                    (0x00010, None, None),
                    (0x00040, "button_1", "remote_button_short_release"),
                    (0x00040, None, None),
                ],
                # Multi-button presses
                [
                    (0x00000, None, None),
                    (0x00010, "button_1", "remote_button_short_press"),
                    (0x00110, "button_2", "remote_button_short_press"),
                    (0x01110, "button_3", "remote_button_short_press"),
                    (0x11110, "button_4", "remote_button_short_press"),
                    (0x41110, "button_4", "remote_button_short_release"),
                    (0x04110, "button_3", "remote_button_short_release"),
                    (0x00410, "button_2", "remote_button_short_release"),
                    (0x00040, "button_1", "remote_button_short_release"),
                    (0x00000, None, None),
                ],
            ],
        )
        def test_events(self, zigpy_device_from_v2_quirk, switch, case):
            """Test whether button state changes cause events."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])

            state_cluster = device.endpoints[1].niko_state

            buttons_cluster = device.endpoints[1].buttons
            listener = mock.MagicMock()
            buttons_cluster.add_listener(listener)

            for state, button, press_type in case:
                listener.reset_mock()
                state_cluster.update_attribute(0x0002, state)

                # Test whether the event was emitted
                if not button:
                    assert listener.zha_send_event.call_count == 0
                else:
                    assert listener.zha_send_event.call_count == 1
                    assert listener.zha_send_event.call_args_list[0] == mock.call(
                        f"{button}_{press_type}",
                        {
                            "button": button,
                            "press_type": press_type,
                        },
                    )

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    class TestLedState:
        """Test reading and writing status LED state."""

        @pytest.mark.parametrize(
            "case",
            [
                [(0b00, t.Bool.false, t.Bool.false)],
                [(0b01, t.Bool.true, t.Bool.false)],
                [(0b10, t.Bool.false, t.Bool.true)],
                [(0b11, t.Bool.true, t.Bool.true)],
            ],
        )
        async def test_read(self, zigpy_device_from_v2_quirk, switch, case):
            """Test whether led state changes cause attribute changes in the buttons cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])

            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                for state, led1, led3 in case:
                    config_cluster.update_attribute(0x0105, state)

                    attrs, _ = await buttons_cluster.read_attributes([0x0011, 0x0013])
                    assert attrs[0x0011] == led1
                    assert attrs[0x0013] == led3

        @pytest.mark.parametrize(
            "case",
            [
                # LED 1
                [
                    (0x0011, t.Bool.false, 0b00),
                    (0x0011, t.Bool.true, 0b01),
                    (0x0011, t.Bool.true, 0b01),
                    (0x0011, t.Bool.false, 0b00),
                ],
                # LED 3
                [
                    (0x0013, t.Bool.false, 0b00),
                    (0x0013, t.Bool.true, 0b10),
                    (0x0013, t.Bool.true, 0b10),
                    (0x0013, t.Bool.false, 0b00),
                ],
                # Mixed
                [
                    (0x0011, t.Bool.false, 0b00),
                    (0x0013, t.Bool.false, 0b00),
                    (0x0011, t.Bool.true, 0b01),
                    (0x0013, t.Bool.true, 0b11),
                ],
            ],
        )
        async def test_write(self, zigpy_device_from_v2_quirk, switch, case):
            """Test writes of LED state."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = ([], foundation.Status.SUCCESS)
                for attrid, value, expected in case:
                    await buttons_cluster.write_attributes({attrid: value})
                    await wait_for_zigpy_tasks()

                    attr = config_cluster.get(0x0105)
                    assert (0 if attr is None else attr) == expected

        @pytest.mark.parametrize(
            "case",
            [
                # LED 1
                {
                    "writes": [
                        {0x0011: t.Bool.true},
                        {0x0011: t.Bool.true},
                        {0x0011: t.Bool.false},
                        {0x0011: t.Bool.true},
                    ],
                    "result": 0b01,
                    "calls": 3,
                },
                # LED 2
                {
                    "writes": [
                        {0x0013: t.Bool.true},
                        {0x0013: t.Bool.true},
                        {0x0013: t.Bool.false},
                        {0x0013: t.Bool.true},
                    ],
                    "result": 0b10,
                    "calls": 3,
                },
                # Mixed
                {
                    "writes": [
                        {0x0011: t.Bool.true},
                        {0x0011: t.Bool.true},
                        {0x0011: t.Bool.true},
                        {0x0013: t.Bool.true},
                        {0x0011: t.Bool.true},
                        {0x0013: t.Bool.true},
                    ],
                    "result": 0b11,
                    "calls": 2,
                },
            ],
        )
        async def test_rapid_write(self, zigpy_device_from_v2_quirk, switch, case):
            """Test rapid consecutive writes of LED state."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            async def slow_request(*args, **kwargs):
                assert not args
                assert kwargs["expect_reply"]
                await asyncio.sleep(0)
                return ([], foundation.Status.SUCCESS)

            with mock.patch.object(
                config_cluster.endpoint, "request", side_effect=slow_request
            ) as request:
                for attributes in case["writes"]:
                    await buttons_cluster.write_attributes(attributes)
                await wait_for_zigpy_tasks()

                assert request.called
                assert request.call_count == case["calls"]

                attr = config_cluster.get(0x0105)
                assert (0 if attr is None else attr) == case["result"]

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    class TestLedSync:
        """Test reading and writing status LED synchronization state."""

        @pytest.mark.parametrize(
            "case",
            [
                [(0x00, 0x0, 0x0)],
                [(0x01, 0x1, 0x0)],
                [(0x02, 0x2, 0x0)],
                [(0x10, 0x0, 0x1)],
                [(0x20, 0x0, 0x2)],
                [(0x11, 0x1, 0x1)],
                [(0x22, 0x2, 0x2)],
            ],
        )
        async def test_read(self, zigpy_device_from_v2_quirk, switch, case):
            """Test whether led sync changes cause attribute changes in the buttons cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])

            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                for state, led1_sync, led3_sync in case:
                    config_cluster.update_attribute(0x0107, state)

                    attrs, _ = await buttons_cluster.read_attributes([0x0021, 0x0023])
                    assert attrs[0x0021] == led1_sync
                    assert attrs[0x0023] == led3_sync

        @pytest.mark.parametrize(
            "case",
            [
                # LED 1
                [
                    (0x0021, 0x0, 0x00),
                    (0x0021, 0x1, 0x01),
                    (0x0021, 0x2, 0x02),
                ],
                # LED 3
                [
                    (0x0023, 0x0, 0x00),
                    (0x0023, 0x1, 0x10),
                    (0x0023, 0x2, 0x20),
                ],
                # Mixed
                [
                    (0x0021, 0x0, 0x00),
                    (0x0023, 0x0, 0x00),
                    (0x0021, 0x1, 0x01),
                    (0x0023, 0x1, 0x11),
                    (0x0021, 0x2, 0x12),
                    (0x0023, 0x2, 0x22),
                ],
            ],
        )
        async def test_write(self, zigpy_device_from_v2_quirk, switch, case):
            """Test writes of LED sync."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = ([], foundation.Status.SUCCESS)
                for attrid, value, expected in case:
                    await buttons_cluster.write_attributes({attrid: value})
                    await wait_for_zigpy_tasks()

                    attr = config_cluster.get(0x0107)
                    assert (0 if attr is None else attr) == expected

    @pytest.mark.parametrize("switch", [SWITCH_SINGLE, SWITCH_DOUBLE])
    class TestLedsAlert:
        """Test reading and writing status LED alert state."""

        @pytest.mark.parametrize(
            "case",
            [
                (0x000000,),
                (0x0000FF,),
                (0x00FF00,),
                (0xFF0000,),
                (0xFFFFFF,),
            ],
        )
        async def test_read(self, zigpy_device_from_v2_quirk, switch, case):
            """Test whether LED alert changes cause attribute changes in the buttons cluster."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])

            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = (foundation.Status.SUCCESS, "done")

                for led_alert in case:
                    config_cluster.update_attribute(0x0100, led_alert)

                    attrs, _ = await buttons_cluster.read_attributes([0x0100])
                    assert attrs[0x0100] == led_alert

        @pytest.mark.parametrize(
            "case",
            [
                (0x000000,),
                (0x0000FF,),
                (0x00FF00,),
                (0xFF0000,),
                (0xFFFFFF,),
            ],
        )
        async def test_write(self, zigpy_device_from_v2_quirk, switch, case):
            """Test writes of LED alert color."""
            device = zigpy_device_from_v2_quirk(*switch[0], **switch[1])
            config_cluster = device.endpoints[1].niko_config
            buttons_cluster = device.endpoints[1].buttons

            with mock.patch.object(
                config_cluster.endpoint, "request", mock.AsyncMock()
            ) as request:
                request.return_value = ([], foundation.Status.SUCCESS)
                for value in case:
                    await buttons_cluster.write_attributes({0x0100: value})
                    await wait_for_zigpy_tasks()

                    attrs, _ = await config_cluster.read_attributes(
                        [0x0100], only_cache=True
                    )
                    assert attrs[0x0100] == value
