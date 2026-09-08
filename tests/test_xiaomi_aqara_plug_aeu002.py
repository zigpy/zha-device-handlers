"""Tests for the Aqara Wall Outlet H2 UK (lumi.plug.aeu002)."""

from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

import zhaquirks
import zhaquirks.xiaomi.aqara.plug_aeu002  # noqa: F401

zhaquirks.setup()

POWER_ID = ElectricalMeasurement.AttributeDefs.active_power.id
VOLTAGE_ID = ElectricalMeasurement.AttributeDefs.rms_voltage.id


async def test_active_power_scaled_x10_on_all_endpoints(zigpy_device_from_v2_quirk):
    """active_power must be multiplied by 10 on EP1, EP2 and EP3."""
    device = zigpy_device_from_v2_quirk(
        "Aqara", "lumi.plug.aeu002", endpoint_ids=[1, 2, 3]
    )

    for ep_id in (1, 2, 3):
        cluster = device.endpoints[ep_id].electrical_measurement
        cluster.update_attribute(POWER_ID, 22)
        assert cluster.get(POWER_ID) == 220


async def test_non_power_attribute_passes_through(zigpy_device_from_v2_quirk):
    """Attributes other than active_power must not be scaled."""
    device = zigpy_device_from_v2_quirk(
        "Aqara", "lumi.plug.aeu002", endpoint_ids=[1, 2, 3]
    )

    cluster = device.endpoints[1].electrical_measurement
    cluster.update_attribute(VOLTAGE_ID, 240)
    assert cluster.get(VOLTAGE_ID) == 240


async def test_none_active_power_passes_through(zigpy_device_from_v2_quirk):
    """None must not be multiplied (would TypeError on int * None)."""
    device = zigpy_device_from_v2_quirk(
        "Aqara", "lumi.plug.aeu002", endpoint_ids=[1, 2, 3]
    )

    cluster = device.endpoints[1].electrical_measurement
    cluster.update_attribute(POWER_ID, None)
    assert cluster.get(POWER_ID) is None
