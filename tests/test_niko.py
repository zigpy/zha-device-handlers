"""Tests for Niko quirks."""

from unittest import mock

import pytest
from zigpy import types as t
from zigpy.zcl import foundation

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
