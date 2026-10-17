"""Tests for Aqara H2 switch quirks."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import MultistateInput

import zhaquirks
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    COMMAND_3_SINGLE,
    COMMAND_4_DOUBLE,
    COMMAND_4_HOLD,
    COMMAND_4_RELEASE,
    COMMAND_4_SINGLE,
    COMMAND_5_DOUBLE,
    COMMAND_5_HOLD,
    COMMAND_5_RELEASE,
    COMMAND_5_SINGLE,
)
from zhaquirks.xiaomi.aqara.switch_h2 import (
    AqaraManuSpecificCluster,
    AqaraMultiStateInputCluster,
)

zhaquirks.setup()


def _create_h2_device(zigpy_device_from_v2_quirk, model, endpoint_ids):
    """Resolve an H2 model with source clusters on replaced endpoints."""
    cluster_ids = {
        endpoint_id: {
            MultistateInput.cluster_id: ClusterType.Server,
            AqaraManuSpecificCluster.cluster_id: ClusterType.Server,
        }
        for endpoint_id in endpoint_ids
    }

    return zigpy_device_from_v2_quirk(
        "Aqara",
        model,
        endpoint_ids=endpoint_ids,
        cluster_ids=cluster_ids,
    )


@pytest.mark.parametrize(
    "model,source_endpoints,manufacturer_endpoints,expected_endpoints,expected_entities",
    [
        (
            "lumi.switch.agl010",
            [1, 2, 4, 5],
            [1, 2, 4, 5],
            {1, 2, 4, 5, 21},
            {
                (1, "led_indicator", "led_indicator"),
                (1, "flip_led_indicator", "flip_led_indicator"),
                (1, "power_on_mode", "power_on_mode"),
                (1, "operation_mode", "left"),
                (2, "operation_mode", "right"),
                (1, "lock_relay", "left"),
                (2, "lock_relay", "right"),
                (4, "multi_click", "left"),
                (5, "multi_click", "right"),
            },
        ),
        (
            "lumi.switch.agl009",
            [1, 4],
            [1],
            {1, 4, 21},
            {
                (1, "led_indicator", "led_indicator"),
                (1, "flip_led_indicator", "flip_led_indicator"),
                (1, "power_on_mode", "power_on_mode"),
                (1, "operation_mode", "operation_mode"),
                (1, "lock_relay", "lock_relay"),
                (4, "multi_click", "multi_click"),
            },
        ),
        (
            "lumi.switch.agl004",
            [1, 4],
            [1, 4],
            {1, 4},
            {
                (1, "led_indicator", "led_indicator"),
                (1, "flip_led_indicator", "flip_led_indicator"),
                (1, "power_on_mode", "power_on_mode"),
                (1, "operation_mode", "operation_mode"),
                (1, "lock_relay", "lock_relay"),
                (4, "multi_click", "multi_click"),
            },
        ),
        (
            "lumi.switch.agl005",
            [1, 2],
            [1, 2],
            {1, 2},
            {
                (1, "led_indicator", "led_indicator"),
                (1, "flip_led_indicator", "flip_led_indicator"),
                (1, "power_on_mode", "power_on_mode"),
                (1, "operation_mode", "operation_mode"),
                (2, "operation_mode", "operation_mode"),
                (1, "lock_relay", "lock_relay"),
                (2, "lock_relay", "lock_relay"),
            },
        ),
        (
            "lumi.switch.agl006",
            [1, 2, 3, 4],
            [1, 2, 3, 4],
            {1, 2, 3, 4},
            {
                (1, "led_indicator", "led_indicator"),
                (1, "flip_led_indicator", "flip_led_indicator"),
                (1, "power_on_mode", "power_on_mode"),
                (1, "operation_mode", "operation_mode"),
                (2, "operation_mode", "operation_mode"),
                (3, "operation_mode", "operation_mode"),
                (1, "lock_relay", "lock_relay"),
                (2, "lock_relay", "lock_relay"),
                (3, "lock_relay", "lock_relay"),
                (4, "multi_click", "multi_click"),
            },
        ),
    ],
)
def test_aqara_h2_entities_and_clusters(
    zigpy_device_from_v2_quirk,
    model,
    source_endpoints,
    manufacturer_endpoints,
    expected_endpoints,
    expected_entities,
):
    """Test each model's replaced clusters, endpoints, and entity definitions."""
    device = _create_h2_device(zigpy_device_from_v2_quirk, model, source_endpoints)

    assert set(device.endpoints) - {0} == expected_endpoints

    for endpoint_id in source_endpoints:
        endpoint = device.endpoints[endpoint_id]
        assert isinstance(
            endpoint.in_clusters[MultistateInput.cluster_id],
            AqaraMultiStateInputCluster,
        )

    for endpoint_id in manufacturer_endpoints:
        assert isinstance(
            device.endpoints[endpoint_id].in_clusters[
                AqaraManuSpecificCluster.cluster_id
            ],
            AqaraManuSpecificCluster,
        )

    entry = DEVICE_REGISTRY.match_entry(device)
    assert entry is not None
    entity_metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    actual_entities = {
        (
            metadata.endpoint_id,
            metadata.attribute_name,
            metadata.resolved_unique_id_suffix,
        )
        for metadata in entity_metadata
    }
    assert actual_entities == expected_entities


@pytest.mark.parametrize(
    "model,source_endpoints,expected_triggers",
    [
        (
            "lumi.switch.agl010",
            [1, 2, 4, 5],
            {
                (event, button): {COMMAND: command}
                for button, commands in (
                    (
                        BUTTON_1,
                        {
                            COMMAND_HOLD: COMMAND_1_HOLD,
                            COMMAND_SINGLE: COMMAND_1_SINGLE,
                            COMMAND_DOUBLE: COMMAND_1_DOUBLE,
                            COMMAND_RELEASE: COMMAND_1_RELEASE,
                        },
                    ),
                    (
                        BUTTON_2,
                        {
                            COMMAND_HOLD: COMMAND_2_HOLD,
                            COMMAND_SINGLE: COMMAND_2_SINGLE,
                            COMMAND_DOUBLE: COMMAND_2_DOUBLE,
                            COMMAND_RELEASE: COMMAND_2_RELEASE,
                        },
                    ),
                    (
                        BUTTON_3,
                        {
                            COMMAND_HOLD: COMMAND_4_HOLD,
                            COMMAND_SINGLE: COMMAND_4_SINGLE,
                            COMMAND_DOUBLE: COMMAND_4_DOUBLE,
                            COMMAND_RELEASE: COMMAND_4_RELEASE,
                        },
                    ),
                    (
                        BUTTON_4,
                        {
                            COMMAND_HOLD: COMMAND_5_HOLD,
                            COMMAND_SINGLE: COMMAND_5_SINGLE,
                            COMMAND_DOUBLE: COMMAND_5_DOUBLE,
                            COMMAND_RELEASE: COMMAND_5_RELEASE,
                        },
                    ),
                )
                for event, command in commands.items()
            },
        ),
        (
            "lumi.switch.agl009",
            [1, 4],
            {
                (event, button): {COMMAND: command}
                for button, commands in (
                    (
                        BUTTON_1,
                        {
                            COMMAND_HOLD: COMMAND_1_HOLD,
                            COMMAND_SINGLE: COMMAND_1_SINGLE,
                            COMMAND_DOUBLE: COMMAND_1_DOUBLE,
                            COMMAND_RELEASE: COMMAND_1_RELEASE,
                        },
                    ),
                    (
                        BUTTON_2,
                        {
                            COMMAND_HOLD: COMMAND_4_HOLD,
                            COMMAND_SINGLE: COMMAND_4_SINGLE,
                            COMMAND_DOUBLE: COMMAND_4_DOUBLE,
                            COMMAND_RELEASE: COMMAND_4_RELEASE,
                        },
                    ),
                )
                for event, command in commands.items()
            },
        ),
        (
            "lumi.switch.agl004",
            [1, 4],
            {
                (COMMAND_SINGLE, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
                (COMMAND_HOLD, BUTTON_2): {COMMAND: COMMAND_4_HOLD},
                (COMMAND_SINGLE, BUTTON_2): {COMMAND: COMMAND_4_SINGLE},
                (COMMAND_DOUBLE, BUTTON_2): {COMMAND: COMMAND_4_DOUBLE},
                (COMMAND_RELEASE, BUTTON_2): {COMMAND: COMMAND_4_RELEASE},
            },
        ),
        (
            "lumi.switch.agl005",
            [1, 2],
            {
                (COMMAND_SINGLE, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
                (COMMAND_SINGLE, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
            },
        ),
        (
            "lumi.switch.agl006",
            [1, 2, 3, 4],
            {
                (COMMAND_SINGLE, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
                (COMMAND_SINGLE, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
                (COMMAND_SINGLE, BUTTON_3): {COMMAND: COMMAND_3_SINGLE},
                (COMMAND_HOLD, BUTTON_4): {COMMAND: COMMAND_4_HOLD},
                (COMMAND_SINGLE, BUTTON_4): {COMMAND: COMMAND_4_SINGLE},
                (COMMAND_DOUBLE, BUTTON_4): {COMMAND: COMMAND_4_DOUBLE},
                (COMMAND_RELEASE, BUTTON_4): {COMMAND: COMMAND_4_RELEASE},
            },
        ),
    ],
)
def test_aqara_h2_device_automation_triggers(
    zigpy_device_from_v2_quirk, model, source_endpoints, expected_triggers
):
    """Test model-specific button trigger mappings."""
    device = _create_h2_device(zigpy_device_from_v2_quirk, model, source_endpoints)

    assert device.device_automation_triggers == expected_triggers
