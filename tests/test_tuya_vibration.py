# tests/test_tuya_vibration.py
import pytest
from zigpy.quirks.v2 import CustomDeviceV2
import zhaquirks
from zhaquirks.tuya.ts0601_vibration import uint_to_sint
zhaquirks.setup()

@pytest.mark.asyncio
async def test_ts0601_vibration_quirk_loads(zigpy_device_from_v2_quirk):
    """Test that the custom TS0601 vibration quirk loads correctly."""
    quirked_device = zigpy_device_from_v2_quirk("_TZE200_iba1ckek", "TS0601")
    
    # Verify that the quirk loaded and created a CustomDeviceV2
    assert isinstance(quirked_device, CustomDeviceV2)
    
    # Check that endpoint 1 exists
    assert 1 in quirked_device.endpoints
    ep = quirked_device.endpoints[1]
    
    # Verify that the basic cluster structure exists
    assert 0x0000 in ep.in_clusters  # Basic cluster
    assert 0xEF00 in ep.in_clusters  # Tuya manufacturer cluster

def test_uint_to_sint_converter():
    """Test the uint_to_sint converter function"""
    assert uint_to_sint(0) == 0
    assert uint_to_sint(50) == 50
    assert uint_to_sint(127) == 127
    assert uint_to_sint(128) == -128
    assert uint_to_sint(200) == -56
    assert uint_to_sint(255) == -1
