"""Tests for Stelpro quirks."""

from zha.application.platforms.climate.const import HVACMode
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat

from tests.zha_helpers import (
    get_climate,
    join_device_from_signature,
    without_zha_entities,
    zha_gateway,
)
from zhaquirks.stelpro.sorb import StelproFanHeaterThermostat


async def test_stelpro_sorb_heat_only() -> None:
    """Test the Stelpro SORB thermostat only offers the heat mode."""
    with without_zha_entities(Thermostat.cluster_id, "StelproFanHeater"):
        async with zha_gateway() as gateway:
            device = await join_device_from_signature(
                gateway,
                "Stelpro",
                "SORB",
                {
                    25: (
                        zha.DeviceType.THERMOSTAT,
                        [Basic.cluster_id, Thermostat.cluster_id],
                        [],
                    )
                },
                DEVICE_REGISTRY,
            )
            entity = get_climate(device)

            assert type(entity) is StelproFanHeaterThermostat
            assert entity.unique_id == f"{device.ieee}-25"
            assert entity.hvac_modes == [HVACMode.HEAT]
