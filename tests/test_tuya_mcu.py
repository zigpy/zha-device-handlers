"""Tests for Tuya quirks."""

import pytest
import zigpy.types as t

import zhaquirks
from zhaquirks.tuya import TUYA_MCU_VERSION_RSP
from zhaquirks.tuya.mcu import ATTR_MCU_VERSION, TuyaDPType, TuyaMCUCluster

from tests.common import ClusterListener

zhaquirks.setup()

# ZCL_TUYA_VERSION_RSP = b"\tp\x17\x00\x03\x82"
ZCL_TUYA_VERSION_RSP = b"\x09\x06\x11\x01\x6D\x82"


@pytest.mark.parametrize(
    "quirk", (zhaquirks.tuya.ts0601_dimmer.TuyaDoubleSwitchDimmer,)
)
async def test_tuya_version(zigpy_device_from_quirk, quirk):
    """Test TUYA_MCU_VERSION_RSP messages."""

    tuya_device = zigpy_device_from_quirk(quirk)

    tuya_cluster = tuya_device.endpoints[1].tuya_manufacturer
    cluster_listener = ClusterListener(tuya_cluster)

    assert len(cluster_listener.attribute_updates) == 0

    # simulate a TUYA_MCU_VERSION_RSP message
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VERSION_RSP)
    assert hdr.command_id == TUYA_MCU_VERSION_RSP

    tuya_cluster.handle_message(hdr, args)
    assert len(cluster_listener.attribute_updates) == 1
    assert cluster_listener.attribute_updates[0][0] == ATTR_MCU_VERSION
    assert cluster_listener.attribute_updates[0][1] == "2.0.2"

    # read 'mcu_version' from cluster's attributes
    succ, fail = await tuya_cluster.read_attributes(("mcu_version",))
    assert succ["mcu_version"] == "2.0.2"


async def test_tuya_mcu_classes():
    """Test tuya conversion from Data to ztype and reverse."""

    # Test TuyaDPType class
    assert len(TuyaDPType) == 6
    assert TuyaDPType.BOOL.ztype == t.Bool
    assert TuyaDPType.get_from_ztype(t.uint32_t) == TuyaDPType.VALUE
    # no ztype for TuyaDPType.RAW
    assert not TuyaDPType.RAW.ztype
    assert TuyaDPType(3) == TuyaDPType.STRING

    # Test TuyaMCUCluster.MCUVersion class
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x03\x82")[0]
    assert mcu_version
    assert mcu_version.tsn == 3
    assert mcu_version.version_raw == 130
    assert mcu_version.version == "2.0.2"
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x04\x01")[0]
    assert mcu_version
    assert mcu_version.version_raw == 1
    assert mcu_version.version == "0.0.1"
    mcu_version = TuyaMCUCluster.MCUVersion.deserialize(b"\x00\x05\xFF")[0]
    assert mcu_version
    assert mcu_version.version_raw == 255
    assert mcu_version.version == "3.3.15"
