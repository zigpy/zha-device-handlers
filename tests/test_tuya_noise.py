"""Tests for Tuya noise sensor."""

import pytest
from zha.application import EntityPlatform
from zha.quirks import DEVICE_REGISTRY

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.tuya.tuya_noise import TuyaNoiseLevel

zhaquirks.setup()


@pytest.mark.parametrize(
    "frame,attribute,value",
    [
        # DP 1: sound pressure 27 dB
        (
            b"\x09\x01\x02\x00\x01\x01\x02\x00\x04\x00\x00\x00\x1b",
            "sound_pressure",
            27,
        ),
        # DP 8: noise level loud
        (
            b"\x09\x02\x02\x00\x02\x08\x04\x00\x01\x02",
            "noise_level",
            TuyaNoiseLevel.Loud,
        ),
        # DP 101: 0 means noise detected
        (b"\x09\x03\x02\x00\x03\x65\x04\x00\x01\x00", "noise_detected", True),
        # DP 101: non-zero values are reported while quiet
        (b"\x09\x04\x02\x00\x04\x65\x04\x00\x01\x01", "noise_detected", False),
        (b"\x09\x05\x02\x00\x05\x65\x04\x00\x01\x03", "noise_detected", False),
    ],
)
async def test_tuya_noise_sensor(zigpy_device_from_v2_quirk, frame, attribute, value):
    """Test Tuya noise sensor datapoint reports."""

    device = zigpy_device_from_v2_quirk("_TZE204_r6kfl9ta", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(frame)
    tuya_cluster.handle_message(hdr, args)

    attr_id = tuya_cluster.find_attribute(attribute).id
    assert tuya_listener.attribute_updates == [(attr_id, value)]
    assert tuya_cluster.get(attribute) == value


async def test_tuya_noise_sensor_entities(zigpy_device_from_v2_quirk):
    """Test Tuya noise sensor entity creation."""

    device = zigpy_device_from_v2_quirk("_TZE204_r6kfl9ta", "TS0601")
    entry = DEVICE_REGISTRY.match_entry(device)
    platforms = {
        metadata.resolved_unique_id_suffix: metadata.entity_platform
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }

    assert platforms == {
        "sound_pressure": EntityPlatform.SENSOR,
        "noise_level": EntityPlatform.SENSOR,
        "noise_detected": EntityPlatform.BINARY_SENSOR,
    }
