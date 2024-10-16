"""Tests for Tuya spells."""

from unittest import mock

import pytest
import zigpy
from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, OnOff

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TUYA_QUERY_DATA,
    EnchantedDevice,
    TuyaNewManufCluster,
    TuyaZBOnOffAttributeCluster,
)
import zhaquirks.tuya.ts0601_valve

zhaquirks.setup()


class TuyaTestSpellDevice(EnchantedDevice):
    """Tuya test spell device."""

    tuya_spell_data_query = True  # enable additional data query spell

    signature = {
        MODELS_INFO: [("UjqjHq6ZErY23tgs", "zo9WD7q5dbvDj96y")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    OnOff.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    TuyaZBOnOffAttributeCluster,
                    TuyaNewManufCluster,
                ],
                OUTPUT_CLUSTERS: [],
            }
        }
    }


ENCHANTED_QUIRKS = [TuyaTestSpellDevice]
for manufacturer in zigpy.quirks._DEVICE_REGISTRY._registry.values():
    for model_quirk_list in manufacturer.values():
        for quirk_entry in model_quirk_list:
            if quirk_entry in ENCHANTED_QUIRKS:
                continue
            if issubclass(quirk_entry, EnchantedDevice):
                ENCHANTED_QUIRKS.append(quirk_entry)

del quirk_entry, model_quirk_list, manufacturer


async def test_tuya_spell(zigpy_device_from_quirk):
    """Test that enchanted Tuya devices have their spells applied during configuration."""
    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        for quirk in ENCHANTED_QUIRKS:
            device = zigpy_device_from_quirk(quirk)
            assert isinstance(device, EnchantedDevice)

            # call apply_custom_configuration() on each EnchantedDevice
            # ZHA does this during device configuration normally
            await device.apply_custom_configuration()

            # the number of Tuya spells that are allowed to be cast, so the sum of enabled Tuya spells
            enabled_tuya_spells_num = (
                device.tuya_spell_read_attributes + device.tuya_spell_data_query
            )

            # skip if no Tuya spells are enabled,
            # this case is already handled in the test_tuya_spell_devices_valid() test
            if enabled_tuya_spells_num == 0:
                continue

            # verify request was called the correct number of times
            assert request_mock.call_count == enabled_tuya_spells_num

            # used to check list of mock calls below
            messages = 0

            # check 'attribute read spell' was cast correctly (if enabled)
            if device.tuya_spell_read_attributes:
                assert (
                    request_mock.mock_calls[messages][1][1]
                    == foundation.GeneralCommand.Read_Attributes
                )
                assert request_mock.mock_calls[messages][1][3] == [4, 0, 1, 5, 7, 65534]
                messages += 1

            # check 'query data spell' was cast correctly (if enabled)
            if device.tuya_spell_data_query:
                assert not request_mock.mock_calls[messages][1][0]
                assert request_mock.mock_calls[messages][1][1] == TUYA_QUERY_DATA
                messages += 1

            request_mock.reset_mock()


def test_tuya_spell_devices_valid():
    """Test that all enchanted Tuya devices have at least one spell enabled."""

    for quirk in ENCHANTED_QUIRKS:
        # check that at least one Tuya spell is enabled for an EnchantedDevice
        if not quirk.tuya_spell_read_attributes and not quirk.tuya_spell_data_query:
            pytest.fail(
                f"Enchanted quirk {quirk} does not have any Tuya spells enabled. "
                f"Enable at least one Tuya spell by setting `TUYA_SPELL_READ_ATTRIBUTES` or `TUYA_SPELL_DATA_QUERY` "
                f"or inherit CustomDevice rather than EnchantedDevice."
            )

        tuya_cluster_exists = False  # cluster subclassing TuyaNewManufCluster existing

        # iterate over all clusters in the replacement
        for endpoint_id, endpoint in quirk.replacement[ENDPOINTS].items():
            if endpoint_id != 1:  # cluster with data query spell command on endpoint 1
                continue
            for cluster in endpoint[INPUT_CLUSTERS] + endpoint[OUTPUT_CLUSTERS]:
                if not isinstance(cluster, int):
                    # check if there's a valid Tuya cluster where the id wasn't modified
                    if (
                        issubclass(cluster, TuyaNewManufCluster)
                        and cluster.cluster_id == TuyaNewManufCluster.cluster_id
                    ):
                        tuya_cluster_exists = True
                        break

        # an EnchantedDevice with the data query spell must also have a cluster subclassing TuyaNewManufCluster
        if quirk.tuya_spell_data_query and not tuya_cluster_exists:
            pytest.fail(
                f"{quirk} set Tuya data query spell but has no cluster subclassing `TuyaNewManufCluster` on endpoint 1"
            )
