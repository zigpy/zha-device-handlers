"""Tests for Sonoff BASICZBR3 quirk."""

import zhaquirks
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    ENDPOINT_ID,
    LONG_PRESS,
    PARAMS,
    SHORT_PRESS,
)
from zhaquirks.sonoff.basiczbr3 import FLASH, POWER_ON

zhaquirks.setup()

def test_basiczbr3_quirk_registered():
    """Test that the quirk is properly registered."""

    import zhaquirks.sonoff.basiczbr3  # noqa: F401

    from zigpy.quirks import DEVICE_REGISTRY

    quirks = DEVICE_REGISTRY.registry_v2.get(("SONOFF", "BASICZBR3"))
    assert quirks is not None, "BASICZBR3 quirk not found in registry"
    assert len(quirks) == 1, "Expected exactly one quirk for BASICZBR3"

def test_basiczbr3_device_automation_triggers():
    """Test that device automation triggers are correctly defined."""
    
    import zhaquirks.sonoff.basiczbr3  # noqa: F401
    
    from zigpy.quirks import DEVICE_REGISTRY
    
    quirks = DEVICE_REGISTRY.registry_v2.get(("SONOFF", "BASICZBR3"))
    assert quirks is not None, "BASICZBR3 quirk not found in registry"
    
    quirk_metadata = quirks[0]
    triggers = quirk_metadata.device_automation_triggers_metadata
    
    # Expected triggers
    expected_triggers = {
        (POWER_ON,): {
            COMMAND: "identify",
            CLUSTER_ID: 3,
            ENDPOINT_ID: 1,
            PARAMS: {"identify_time": 5},
        },
        (FLASH, SHORT_PRESS): {
            COMMAND: "trigger_effect",
            CLUSTER_ID: 3,
            ENDPOINT_ID: 1,
            PARAMS: {"effect_id": 0x00, "effect_variant": 0x00},
        },
        (FLASH, LONG_PRESS): {
            COMMAND: "trigger_effect", 
            CLUSTER_ID: 3,
            ENDPOINT_ID: 1,
            PARAMS: {"effect_id": 0x00, "effect_variant": 0x01},
        },
    }
    
    # Verify all expected triggers are present
    for trigger_key, expected_trigger in expected_triggers.items():
        assert trigger_key in triggers, f"Missing trigger: {trigger_key}"
        actual_trigger = triggers[trigger_key]
        
        for key, expected_value in expected_trigger.items():
            assert actual_trigger[key] == expected_value, f"Mismatch in {trigger_key}[{key}]: expected {expected_value}, got {actual_trigger[key]}"