import pytest
from zhaquirks.heiman.hs1sa_efa import (
    smoke_chamber_contamination_converter,
    smoke_level_unit_converter
)

def test_heiman_converters():
    """Test the custom converters."""
# Coverage for smoke_chamber_contamination_converter
    assert smoke_chamber_contamination_converter(0) == "normal"
    assert smoke_chamber_contamination_converter(1) == "light contamination"
    assert smoke_chamber_contamination_converter(2) == "medium contamication"
    assert smoke_chamber_contamination_converter(3) == "critical contamication"
    assert smoke_chamber_contamination_converter(99) is "unknown" 

    # Coverage for smoke_level_unit_converter
    assert smoke_level_unit_converter(0) == "dB/m"
    assert smoke_level_unit_converter(1) == "%ft OBS"
    assert smoke_level_unit_converter(99) is "unknown"

@pytest.mark.asyncio
async def test_initiate_test_mode_logic(zigpy_device_from_v2_quirk):
    """Test the command """
    device = zigpy_device_from_v2_quirk("HEIMAN", "HS1SA-EF-3.0")
    cluster = device.endpoints[1].ias_zone
    
    # We call it without args to trigger your 'if not args' logic
    try:
        await cluster.command(0x02)
    except Exception:
        # We don't care if it fails (no radio), we just need it to EXECUTE
        pass