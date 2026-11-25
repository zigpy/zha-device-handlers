"""Tests for Zehnder quirks."""

from unittest import mock

import pytest
from zha.application.platforms.climate.const import HVACMode
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import Basic, Identify
from zigpy.zcl.clusters.hvac import SystemMode, Thermostat
import zigpy.zcl.foundation as zcl_f

from tests.zha_helpers import (
    get_climate,
    join_device_from_signature,
    without_zha_entities,
    zha_gateway,
)
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.zehnder.thermostat import ZehnderThermostat

ZEHNDER_ENDPOINTS = {
    1: (
        zha.DeviceType.THERMOSTAT,
        [Basic.cluster_id, Identify.cluster_id, Thermostat.cluster_id],
        [Identify.cluster_id],
    )
}


@pytest.mark.parametrize(
    "manufacturer",
    ["ZEHNDER GROUP VAUX ANDIGNY      ", "ZEHNDER GROUP VAUX ANDIGNY"],
)
async def test_zehnder_thermostat(manufacturer: str) -> None:
    """Test the Zehnder thermostat heats in the auto system mode."""
    with without_zha_entities(Thermostat.cluster_id, "ZehnderThermostat"):
        async with zha_gateway() as gateway:
            device = await join_device_from_signature(
                gateway,
                manufacturer,
                "ALCANTARA2 D1.00P1.02Z1.00",
                ZEHNDER_ENDPOINTS,
                DEVICE_REGISTRY,
            )
            entity = get_climate(device)
            thermostat = entity._cluster

            assert type(entity) is ZehnderThermostat
            assert entity.unique_id == f"{device.ieee}-1"
            assert entity.hvac_modes == [HVACMode.OFF, HVACMode.HEAT]

            thermostat.update_attribute(
                Thermostat.AttributeDefs.local_temperature.id, 2100
            )
            assert entity.state.current_temperature is None

            thermostat.update_attribute(
                Thermostat.AttributeDefs.system_mode.id, SystemMode.Auto
            )
            assert entity.state.hvac_mode == HVACMode.HEAT
            thermostat.update_attribute(
                Thermostat.AttributeDefs.system_mode.id, SystemMode.Off
            )
            assert entity.state.hvac_mode == HVACMode.OFF

            with mock.patch.object(
                thermostat,
                "write_attributes",
                return_value=[
                    [zcl_f.WriteAttributesStatusRecord(zcl_f.Status.SUCCESS)]
                ],
            ) as write_attributes:
                await entity.async_set_hvac_mode(HVACMode.HEAT)
                await entity.async_set_hvac_mode(HVACMode.HEAT_COOL)
                await entity.async_set_hvac_mode(HVACMode.OFF)

            assert [call.args[0] for call in write_attributes.mock_calls] == [
                {"system_mode": SystemMode.Auto},
                {"system_mode": SystemMode.Off},
            ]


def test_zehnder_without_thermostat(zigpy_device_from_v2_quirk) -> None:
    """Test the quirk doesn't apply to Zehnder devices without a thermostat."""
    device = zigpy_device_from_v2_quirk("ZEHNDER GROUP VAUX ANDIGNY", "Other")
    assert not isinstance(device, CustomZigpyDevice)

    device = zigpy_device_from_v2_quirk(
        "ZEHNDER GROUP VAUX ANDIGNY",
        "Other",
        cluster_ids={2: {Thermostat.cluster_id: ClusterType.Server}},
    )
    assert isinstance(device, CustomZigpyDevice)
