"""Tests for the Tuya Fingerbot quirk."""

from unittest import mock

import pytest
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration

import zhaquirks
from zhaquirks.tuya import TUYA_ACTIVE_STATUS_RPT_ALT

zhaquirks.setup()


@pytest.mark.parametrize(
    "frame,cluster_attr,attribute_name,value",
    [
        # Fingerbot Plus reporting DP 103 (sustain time) = 0 with command 0x05,
        # frame taken from the debug log in zigpy/zha-device-handlers#5385
        (
            "09 45 05 00 09 67 02 00 04 00 00 00 00",
            "tuya_manufacturer",
            "sustain_time",
            0,
        ),
        # DP 105 (battery) = 80 % with command 0x05
        (
            "09 46 05 00 0a 69 02 00 04 00 00 00 50",
            PowerConfiguration.ep_attribute,
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
            160,
        ),
    ],
)
def test_fingerbot_active_status_report_alt(
    zigpy_device_from_v2_quirk, frame, cluster_attr, attribute_name, value
):
    """Test datapoints reported with Tuya command 0x05 are applied."""

    device = zigpy_device_from_v2_quirk("_TZ3210_a04acm9s", "TS0001")
    ep = device.endpoints[1]
    tuya_cluster = ep.tuya_manufacturer
    target_cluster = getattr(ep, cluster_attr)

    assert target_cluster.get(attribute_name) is None

    hdr, args = tuya_cluster.deserialize(bytes.fromhex(frame))
    assert hdr.command_id == TUYA_ACTIVE_STATUS_RPT_ALT

    with mock.patch.object(tuya_cluster, "send_default_rsp") as default_rsp:
        tuya_cluster.handle_message(hdr, args)

    assert target_cluster.get(attribute_name) == value
    default_rsp.assert_called_once_with(hdr, status=foundation.Status.SUCCESS)
