"""Tests for the Eurotronic Spirit Zigbee thermostat quirk."""

from unittest import mock

import pytest
from zha.application.platforms.climate.const import HVACMode
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.typing import UNDEFINED
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import Status, WriteAttributesStatusRecord

import zhaquirks
from zhaquirks.eurotronic import EurotronicThermostat, HostFlags, ThermostatCluster

zhaquirks.setup()


@pytest.fixture
def zha_device(zigpy_device_from_v2_quirk):
    """Create the ZHA device for a quirked SPZB0001."""
    device = zigpy_device_from_v2_quirk(
        "Eurotronic",
        "SPZB0001",
        cluster_ids={1: {Thermostat.cluster_id: ClusterType.Server}},
    )
    device.endpoints[1].profile_id = zha.PROFILE_ID
    device.endpoints[1].device_type = zha.DeviceType.THERMOSTAT

    gateway = mock.MagicMock()
    gateway.config.config.device_overrides = {}

    return DEVICE_REGISTRY.match_entry(device).zha_device_factory(device, gateway)


@pytest.fixture
def thermostat(zha_device) -> EurotronicThermostat:
    """Create the quirk's climate entity."""
    return EurotronicThermostat(
        endpoint=zha_device.endpoints[1],
        device=zha_device,
        cluster=zha_device.device.endpoints[1].thermostat,
    )


def test_hvac_mode_from_host_flags(thermostat):
    """The mode is derived from the off bit in host_flags."""
    assert thermostat.hvac_mode is None

    thermostat.cluster.update_attribute(
        ThermostatCluster.AttributeDefs.host_flags.id, HostFlags.Clear_Off_Mode | 1
    )
    assert thermostat.hvac_mode == HVACMode.OFF

    thermostat.cluster.update_attribute(
        ThermostatCluster.AttributeDefs.host_flags.id, 1
    )
    assert thermostat.hvac_mode == HVACMode.HEAT


async def test_set_hvac_mode_writes_host_flags(thermostat):
    """Setting the mode writes the matching host_flags bit."""
    thermostat.cluster.update_attribute(
        ThermostatCluster.AttributeDefs.host_flags.id, 1
    )

    write = mock.AsyncMock(return_value=[[WriteAttributesStatusRecord(Status.SUCCESS)]])

    with mock.patch.object(thermostat.cluster, "write_attributes", write):
        await thermostat.async_set_hvac_mode(HVACMode.OFF)

    assert write.mock_calls == [
        mock.call(
            {
                ThermostatCluster.AttributeDefs.host_flags.name: HostFlags.Set_Off_Mode
                | 1
            },
            manufacturer=UNDEFINED,
        )
    ]


def test_target_temperature_from_current_setpoint(thermostat):
    """The target temperature comes from the manufacturer-specific setpoint."""
    thermostat.cluster.update_attribute(
        ThermostatCluster.AttributeDefs.host_flags.id, 1
    )
    thermostat.cluster.update_attribute(
        ThermostatCluster.AttributeDefs.current_temperature_setpoint.id, 2150
    )

    assert thermostat.target_temperature == 21.5
