"""Tests for Yokis quirks."""

import asyncio
from unittest import mock

import pytest
from zigpy.zcl.clusters.general import OnOff, LevelControl
from zigpy.zcl.clusters.closures import WindowCovering

import zhaquirks
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    BUTTON_5,
    BUTTON_6,
    BUTTON_7,
    BUTTON_8,
    COMMAND_ID,
    PRESS_TYPE
)
from zhaquirks.yokis.remote import (
    TLM1_TLC1_UP,
    TLM2_UP,
    TLM4_GALET4_UP,
    TLC2_MONITOR2_E2BP_E2BPA_UP,
    TLC4_E4BP_E4BPX_UP,
    TLC8_MONITOR_UP
)

zhaquirks.setup()



@pytest.mark.parametrize(
    "quirk, endpoints",
    (
        (TLM1_TLC1_UP, [1]),
        (TLM2_UP, [1, 2]),
        (TLM4_GALET4_UP, [1, 2, 3, 4]),
        (TLC2_MONITOR2_E2BP_E2BPA_UP, [1, 2]),
        (TLC4_E4BP_E4BPX_UP, [1, 2, 3, 4]),
        (TLC8_MONITOR_UP, [1, 2, 3, 4, 5, 6, 7, 8]),
    ),
)
async def test_yokis_remote_button(zigpy_device_from_quirk, quirk, endpoints):
    """Test that remote quirks do not interfere with commands processing."""
    # Device creation from quirks
    device = zigpy_device_from_quirk(quirk)

    # For each supported endpoint
    for endpoint_id in endpoints:
        """Test OnOff commands (push button)."""
        # Init OnOff cluster 
        cluster = device.endpoints[endpoint_id].out_clusters[OnOff.cluster_id]

        # Init listener to listen zigbee events
        listener = mock.MagicMock()
        cluster.add_listener(listener)

        # Simulate a OnOff toggle command (push button)
        cluster.handle_message(
            hdr=mock.MagicMock(
                command_id=OnOff.ServerCommandDefs().toggle.id
            ),
            args=[],
        )

        # Check if OnOff toggle command is correctly received
        assert listener.cluster_command.call_count == 1

@pytest.mark.parametrize(
    "quirk, expected_triggers",
    (
        (
            TLM1_TLC1_UP,
            {
                (SHORT_PRESS, BUTTON_1): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 1,
                },
            },
        ),
        (
            TLM2_UP,
            {
                (SHORT_PRESS, BUTTON_1): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 1,
                },
                (SHORT_PRESS, BUTTON_2): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 2,
                },
            },
        ),
        (
            TLM4_GALET4_UP,
            {
                (SHORT_PRESS, BUTTON_1): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 1,
                },
                (SHORT_PRESS, BUTTON_2): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 2,
                },
                (SHORT_PRESS, BUTTON_3): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 3,
                },
                (SHORT_PRESS, BUTTON_4): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 4,
                },
            },
        ),
        (
            TLC2_MONITOR2_E2BP_E2BPA_UP,
            {
                (SHORT_PRESS, BUTTON_1): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 1,
                },
                (SHORT_PRESS, BUTTON_2): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 2,
                },
            },
        ),
        (
            TLC4_E4BP_E4BPX_UP,
            {
                (SHORT_PRESS, BUTTON_1): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 1,
                },
                (SHORT_PRESS, BUTTON_2): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 2,
                },
                (SHORT_PRESS, BUTTON_3): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 3,
                },
                (SHORT_PRESS, BUTTON_4): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 4,
                },
            },
        ),
        (
            TLC8_MONITOR_UP,
            {
                (SHORT_PRESS, BUTTON_1): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 1,
                },
                (SHORT_PRESS, BUTTON_2): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 2,
                },
                (SHORT_PRESS, BUTTON_3): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 3,
                },
                (SHORT_PRESS, BUTTON_4): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 4,
                },
                (SHORT_PRESS, BUTTON_5): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 5,
                },
                (SHORT_PRESS, BUTTON_6): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 6,
                },
                (SHORT_PRESS, BUTTON_7): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 7,
                },
                (SHORT_PRESS, BUTTON_8): {
                    COMMAND: COMMAND_TOGGLE,
                    CLUSTER_ID: OnOff.cluster_id,
                    ENDPOINT_ID: 8,
                }
            },
        )
    ),
)
async def test_yokis_device_automation_triggers(quirk, expected_triggers):
    """Verify device_automation_triggers mapping."""

    # Check device_automation_triggers presence in the quirk
    assert hasattr(quirk, "device_automation_triggers")

    # Check if all trigger informations are set
    for trigger_name, trigger_info in expected_triggers.items():
        assert trigger_name in quirk.device_automation_triggers
        assert quirk.device_automation_triggers[trigger_name] == trigger_info