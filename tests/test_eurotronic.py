"""Tests for the Eurotronic Spirit Zigbee quirk."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.eurotronic import HOST_FLAGS_ATTR
from zhaquirks.eurotronic.spzb0001 import SPZB0001

zhaquirks.setup()


def _mock_write(cluster, written):
    """Record what is written and answer with a global success."""

    async def _write_attributes(attributes, manufacturer=None, **kwargs):
        written.append({a.attrid: a.value.value for a in attributes})
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    return mock.patch.object(
        cluster, "_write_attributes", mock.AsyncMock(side_effect=_write_attributes)
    )


async def test_system_mode_write_updates_state(zigpy_device_from_quirk):
    """Setting the system mode writes the host flags and updates the system mode."""
    device = zigpy_device_from_quirk(SPZB0001)
    cluster = device.endpoints[1].thermostat

    # The valve reports heating (no off-mode flag)
    cluster._update_attribute(HOST_FLAGS_ATTR, 0x01)
    assert cluster.get("system_mode") == Thermostat.SystemMode.Heat

    written = []
    with _mock_write(cluster, written):
        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Off})
        assert written[-1] == {HOST_FLAGS_ATTR: 0x21}
        assert cluster.get("system_mode") == Thermostat.SystemMode.Off

        # Switching back on must not keep the "set off mode" flag of the last write
        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Heat})
        assert written[-1] == {HOST_FLAGS_ATTR: 0x11}
        assert cluster.get("system_mode") == Thermostat.SystemMode.Heat

        # Off again, from a cache that holds the "clear off mode" flag just written
        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Off})
        assert written[-1] == {HOST_FLAGS_ATTR: 0x21}
        assert cluster.get("system_mode") == Thermostat.SystemMode.Off


async def test_system_mode_write_keeps_other_flags(zigpy_device_from_quirk):
    """Only the off-mode flags change: child lock and mirrored display are kept."""
    device = zigpy_device_from_quirk(SPZB0001)
    cluster = device.endpoints[1].thermostat

    # Child lock (0x80) and mirrored display (0x02) are on, the valve is heating
    cluster._update_attribute(HOST_FLAGS_ATTR, 0x83)

    written = []
    with _mock_write(cluster, written):
        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Off})
        assert written[-1] == {HOST_FLAGS_ATTR: 0xA3}

        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Heat})
        assert written[-1] == {HOST_FLAGS_ATTR: 0x93}


async def test_system_mode_failed_write_keeps_state(zigpy_device_from_quirk):
    """A rejected host flags write leaves the system mode as it was."""
    device = zigpy_device_from_quirk(SPZB0001)
    cluster = device.endpoints[1].thermostat
    cluster._update_attribute(HOST_FLAGS_ATTR, 0x01)

    async def _write_attributes(attributes, manufacturer=None, **kwargs):
        return [
            [
                foundation.WriteAttributesStatusRecord(
                    foundation.Status.FAILURE, HOST_FLAGS_ATTR
                )
            ]
        ]

    with mock.patch.object(
        cluster, "_write_attributes", mock.AsyncMock(side_effect=_write_attributes)
    ):
        await cluster.write_attributes({"system_mode": Thermostat.SystemMode.Off})

    assert cluster.get("system_mode") == Thermostat.SystemMode.Heat
