"""Tests for the climate presets of the Tuya TRVs in ts0601_trv."""

from unittest import mock

from zha.application.platforms.climate.const import HVACMode
from zha.quirks import DEVICE_REGISTRY
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time
import zigpy.zcl.foundation as zcl_f

from tests.zha_helpers import get_climate, join_device_from_signature, zha_gateway
from zhaquirks.tuya import TuyaManufClusterAttributes
from zhaquirks.tuya.ts0601_trv import MoesHY368Climate, ZonnsmartTV01Climate

TUYA_TRV_ENDPOINTS = {
    1: (
        zha.DeviceType.SMART_PLUG,
        [
            Basic.cluster_id,
            Groups.cluster_id,
            Scenes.cluster_id,
            TuyaManufClusterAttributes.cluster_id,
        ],
        [Time.cluster_id, Ota.cluster_id],
    )
}


async def assert_preset_writes(entity, preset: str, values: list[int]) -> None:
    """Set the preset and check the `operation_preset` values written."""
    thermostat = entity._cluster

    with mock.patch.object(
        thermostat,
        "write_attributes",
        return_value=[[zcl_f.WriteAttributesStatusRecord(zcl_f.Status.SUCCESS)]],
    ) as write_attributes:
        await entity.async_set_preset_mode(preset)

    assert [call.args[0] for call in write_attributes.mock_calls] == [
        {"operation_preset": value} for value in values
    ]
    assert entity.state.preset_mode == preset


async def test_moes_presets() -> None:
    """Test the Moes HY368 presets."""
    async with zha_gateway() as gateway:
        device = await join_device_from_signature(
            gateway, "_TZE200_rufdtfyv", "TS0601", TUYA_TRV_ENDPOINTS, DEVICE_REGISTRY
        )
        entity = get_climate(device)

        assert type(entity) is MoesHY368Climate
        assert entity.unique_id == f"{device.ieee}-1"
        assert entity.hvac_modes == [HVACMode.HEAT]
        assert entity.state.preset_modes == [
            "none",
            "away",
            "Schedule",
            "comfort",
            "eco",
            "boost",
            "Complex",
        ]
        assert entity.state.preset_mode == "none"

        await assert_preset_writes(entity, "away", [0])
        await assert_preset_writes(entity, "Schedule", [2, 1])
        await assert_preset_writes(entity, "comfort", [2, 3])
        await assert_preset_writes(entity, "eco", [2, 4])
        await assert_preset_writes(entity, "boost", [2, 5])
        await assert_preset_writes(entity, "Complex", [2, 6])
        await assert_preset_writes(entity, "none", [2])

        thermostat = device.device.endpoints[1].thermostat
        for value, preset in (
            (0, "away"),
            (1, "Schedule"),
            (2, "none"),
            (3, "comfort"),
            (4, "eco"),
            (5, "boost"),
            (6, "Complex"),
        ):
            thermostat.update_attribute(
                thermostat.AttributeDefs.operation_preset.id, value
            )
            assert entity.state.preset_mode == preset


async def test_zonnsmart_presets() -> None:
    """Test the ZONNSMART TV01-ZG presets."""
    async with zha_gateway() as gateway:
        device = await join_device_from_signature(
            gateway, "_TZE200_sur6q7ko", "TS0601", TUYA_TRV_ENDPOINTS, DEVICE_REGISTRY
        )
        entity = get_climate(device)

        assert type(entity) is ZonnsmartTV01Climate
        assert entity.unique_id == f"{device.ieee}-1"
        assert entity.state.preset_modes == [
            "none",
            "holiday",
            "Schedule",
            "frost protect",
        ]
        assert entity.state.preset_mode == "none"

        await assert_preset_writes(entity, "Schedule", [0])
        await assert_preset_writes(entity, "holiday", [1, 3])
        await assert_preset_writes(entity, "frost protect", [1, 4])
        await assert_preset_writes(entity, "none", [1])

        thermostat = device.device.endpoints[1].thermostat
        for value, preset in (
            (0, "Schedule"),
            (1, "none"),
            (2, "holiday"),
            (3, "holiday"),
            (4, "frost protect"),
        ):
            thermostat.update_attribute(
                thermostat.AttributeDefs.operation_preset.id, value
            )
            assert entity.state.preset_mode == preset
