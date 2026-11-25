"""Tests for Telink devices running the custom ZigbeeTLc firmware."""

import pytest
from zha.quirks import DEVICE_REGISTRY

import zhaquirks

zhaquirks.setup()

# Present in every firmware build
COMMON = {"temperature_offset", "humidity_offset", "measurement_interval"}
# Only in builds with a display (`USE_DISPLAY`)
DISPLAY = {"display"}
# Only in builds with the comfort indicator (`SHOW_SMILEY`)
SMILEY = {
    "schedule_programming_visibility",
    "comfort_temperature_min",
    "comfort_temperature_max",
    "comfort_humidity_min",
    "comfort_humidity_max",
}


@pytest.mark.parametrize(
    ("manufacturer", "model", "attributes"),
    [
        ("MiaoMiaoCe", "MHO-C401N-z", COMMON | DISPLAY | SMILEY),
        ("MiaMiaoCe", "MHO-C401N-z", COMMON | DISPLAY | SMILEY),
        ("MiaoMiaoCe", "MHO-C401-z", COMMON | DISPLAY | SMILEY),
        ("MiaoMiaoCe", "MHO-C122-z", COMMON | DISPLAY | SMILEY),
        ("MiaMiaoCe", "MHO-C122-z", COMMON | DISPLAY | SMILEY),
        ("Xiaomi", "LYWSD03MMC-z", COMMON | DISPLAY | SMILEY),
        ("Xiaomi", "MJWSD06MMC-z", COMMON | DISPLAY | SMILEY),
        ("Sonoff", "TH03-z", COMMON | DISPLAY | SMILEY),
        ("Tuya", "LKTMZL02-z", COMMON | DISPLAY),
        ("Qingping", "CGDK2-z", COMMON | DISPLAY),
        ("Tuya", "TS0201-z", COMMON),
        ("Tuya", "TH03Z-z", COMMON),
        ("Tuya", "ZTH01-z", COMMON),
        ("Tuya", "ZTH02-z", COMMON),
        ("Tuya", "ZY-ZTH02-z", COMMON),
        ("Tuya", "ZG-227Z-z", COMMON),
    ],
)
def test_telink_entities_match_firmware(
    zigpy_device_from_v2_quirk, manufacturer, model, attributes
):
    """Only the attributes the device's firmware build has get an entity.

    Quirk entities are force-created, so an entity for an attribute the firmware
    build leaves out stays in Home Assistant with no state and fails every write.
    """
    device = zigpy_device_from_v2_quirk(manufacturer, model)
    entry = DEVICE_REGISTRY.match_entry(device)

    assert {
        metadata.attribute_name
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    } == attributes
