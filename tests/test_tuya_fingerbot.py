"""Tests for the Tuya Fingerbot quirk."""

from typing import Any
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration

import zhaquirks
from zhaquirks.tuya import TUYA_ACTIVE_STATUS_RPT_ALT

zhaquirks.setup()


def _device_value(device, key: str) -> Any:
    """Return the stored value of the quirk's device value named `key`."""
    definition = DEVICE_REGISTRY.match_entry(device).zha_device_factory.quirk_definition
    (value,) = (
        added.kwargs["value"]
        for added in definition.added_entities
        if added.kwargs["value"].key == key
    )
    return device.store.get(value)


def _battery_percentage(device) -> Any:
    """Return the battery percentage attribute of the power configuration cluster."""
    return device.endpoints[1].power.get(
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.name
    )


@pytest.mark.parametrize(
    "frame,read,value",
    [
        # Fingerbot Plus reporting DP 103 (sustain time, a device value) = 0 with
        # command 0x05, frame taken from the debug log in
        # zigpy/zha-device-handlers#5385
        (
            "09 45 05 00 09 67 02 00 04 00 00 00 00",
            lambda device: _device_value(device, "sustain_time"),
            0,
        ),
        # DP 105 (battery) = 80 % with command 0x05
        (
            "09 46 05 00 0a 69 02 00 04 00 00 00 50",
            _battery_percentage,
            160,
        ),
    ],
    ids=["sustain_time", "battery"],
)
def test_fingerbot_active_status_report_alt(
    zigpy_device_from_v2_quirk, frame, read, value
):
    """Test datapoints reported with Tuya command 0x05 are applied."""

    device = zigpy_device_from_v2_quirk("_TZ3210_a04acm9s", "TS0001")
    tuya_cluster = device.endpoints[1].tuya_manufacturer

    assert read(device) is None

    hdr, args = tuya_cluster.deserialize(bytes.fromhex(frame))
    assert hdr.command_id == TUYA_ACTIVE_STATUS_RPT_ALT

    with mock.patch.object(tuya_cluster, "send_default_rsp") as default_rsp:
        tuya_cluster.handle_message(hdr, args)

    assert read(device) == value
    default_rsp.assert_called_once_with(hdr, status=foundation.Status.SUCCESS)
