"""Tests for HOBEIAN quirks."""

from zigpy.profiles import zha

import zhaquirks.hobeian.zg_305z  # noqa: F401


def test_zg_305z_exposes_usb_outputs_as_switches(zigpy_device_from_v2_quirk):
    """The two independently controlled USB outputs are switches, not lights."""
    device = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-305Z", endpoint_ids=[1, 2])

    assert device[1].device_type == zha.DeviceType.ON_OFF_OUTPUT
    assert device[2].device_type == zha.DeviceType.ON_OFF_OUTPUT
