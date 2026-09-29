"""Tests for Tuya noise sensor."""

from unittest import mock

import pytest
from zha.application import EntityPlatform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TUYA_QUERY_DATA
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
        # Settings
        (
            b"\x09\x06\x02\x00\x06\x10\x02\x00\x04\x00\x00\x00\x14",
            "noise_threshold",
            20,
        ),
        (
            b"\x09\x07\x02\x00\x07\x14\x02\x00\x04\x00\x00\x00\x28",
            "loud_threshold",
            40,
        ),
        (
            b"\x09\x08\x02\x00\x08\x16\x02\x00\x04\x00\x00\x00\x0a",
            "fading_time",
            10,
        ),
        (
            b"\x09\x09\x02\x00\x09\x67\x02\x00\x04\x00\x00\x00\x03",
            "detection_delay",
            3,
        ),
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
        "noise_threshold": EntityPlatform.NUMBER,
        "loud_threshold": EntityPlatform.NUMBER,
        "fading_time": EntityPlatform.NUMBER,
        "detection_delay": EntityPlatform.NUMBER,
    }


@pytest.mark.parametrize(
    "attribute,dp_id",
    [
        ("noise_threshold", 16),
        ("loud_threshold", 20),
        ("fading_time", 22),
        ("detection_delay", 103),
    ],
)
async def test_tuya_noise_sensor_write_settings(
    zigpy_device_from_v2_quirk, attribute, dp_id
):
    """Test writing Tuya noise sensor settings sends the matching datapoint."""

    device = zigpy_device_from_v2_quirk("_TZE204_r6kfl9ta", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        await tuya_cluster.write_attributes({attribute: 5})
        await wait_for_zigpy_tasks()

    assert m1.call_count == 1
    frame = m1.call_args.kwargs["data"]
    # frame control, tsn, command, tuya seq (2), dp, dp type, length (2), value (4)
    assert frame[5] == dp_id
    assert frame[-4:] == b"\x00\x00\x00\x05"


async def test_tuya_noise_sensor_queries_sound_pressure(zigpy_device_from_v2_quirk):
    """Test the sound pressure is queried when the noise state changes."""

    device = zigpy_device_from_v2_quirk("_TZE204_r6kfl9ta", "TS0601")
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    def report(frame: bytes) -> None:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    with mock.patch.object(tuya_cluster, "command") as command:
        # Noise level loud, reported as set_data_response (0x02)
        report(b"\x09\x01\x02\x00\x01\x08\x04\x00\x01\x02")
        await wait_for_zigpy_tasks()
        assert command.call_count == 1
        assert command.call_args.args == (TUYA_QUERY_DATA,)

        # Query response contains the sound pressure, no new query
        report(
            b"\x09\x02\x01\x00\x02\x01\x02\x00\x04\x00\x00\x00\x2e\x08\x04\x00\x01\x02"
        )
        await wait_for_zigpy_tasks()
        assert command.call_count == 1
        assert tuya_cluster.get("sound_pressure") == 46

        # Noise detected, but within the minimum query interval
        report(b"\x09\x03\x02\x00\x03\x65\x04\x00\x01\x00")
        await wait_for_zigpy_tasks()
        assert command.call_count == 1

        # Same value again after the interval, no query
        tuya_cluster._last_query -= tuya_cluster.MIN_QUERY_INTERVAL
        report(b"\x09\x04\x06\x00\x04\x65\x04\x00\x01\x00")
        await wait_for_zigpy_tasks()
        assert command.call_count == 1

        # Changed value via active status report (0x06), new query
        report(b"\x09\x05\x06\x00\x05\x08\x04\x00\x01\x00")
        await wait_for_zigpy_tasks()
        assert command.call_count == 2
