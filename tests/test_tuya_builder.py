"""Tests for TuyaQuirkBuilder."""

from unittest import mock

import pytest
from zigpy.quirks.registry import DeviceRegistry
from zigpy.quirks.v2 import CustomDeviceV2
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya import TUYA_QUERY_DATA
from zhaquirks.tuya.builder import (
    TuyaAirQualityVOC,
    TuyaCO2Concetration,
    TuyaFormaldehydeConcetration,
    TuyaIasContact,
    TuyaIasFire,
    TuyaPM25Concetration,
    TuyaPowerConfigurationCluster2AAA,
    TuyaQuirkBuilder,
    TuyaRelativeHumidity,
    TuyaSoilMoisture,
    TuyaTemperatureMeasurement,
    TuyaValveWaterConsumed,
)
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaOnOffNM

zhaquirks.setup()


@pytest.mark.parametrize(
    "method_name,attr_name,exp_class",
    [
        ("tuya_battery", "power", TuyaPowerConfigurationCluster2AAA),
        ("tuya_metering", "smartenergy_metering", TuyaValveWaterConsumed),
        ("tuya_onoff", "on_off", TuyaOnOffNM),
        ("tuya_soil_moisture", "soil_moisture", TuyaSoilMoisture),
        ("tuya_temperature", "temperature", TuyaTemperatureMeasurement),
        ("tuya_humidity", "humidity", TuyaRelativeHumidity),
        ("tuya_smoke", "ias_zone", TuyaIasFire),
        ("tuya_contact", "ias_zone", TuyaIasContact),
        ("tuya_co2", "carbon_dioxide_concentration", TuyaCO2Concetration),
        ("tuya_pm25", "pm25", TuyaPM25Concetration),
        ("tuya_voc", "voc_level", TuyaAirQualityVOC),
        (
            "tuya_formaldehyde",
            "formaldehyde_concentration",
            TuyaFormaldehydeConcetration,
        ),
    ],
)
async def test_convenience_methods(device_mock, method_name, attr_name, exp_class):
    """Test TuyaQuirkBuilder convenience methods."""

    registry = DeviceRegistry()

    entry = TuyaQuirkBuilder(
        device_mock.manufacturer, device_mock.model, registry=registry
    )
    entry = getattr(entry, method_name)(dp_id=1)
    entry.skip_configuration().add_to_registry()

    quirked = registry.get_device(device_mock)
    assert isinstance(quirked, CustomDeviceV2)
    assert quirked in registry

    ep = quirked.endpoints[1]

    ep_attr = getattr(ep, attr_name)
    assert ep_attr is not None
    assert isinstance(ep_attr, exp_class)


async def test_tuya_quirkbuilder(device_mock):
    """Test adding a v2 Tuya Quirk to the registry and getting back a quirked device."""

    registry = DeviceRegistry()

    class TestEnum(t.enum8):
        """Test Enum."""

        A = 0x00
        B = 0x01

    entry = (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_battery(dp_id=1)
        .tuya_onoff(dp_id=3)
        .tuya_switch(
            dp_id=6,
            attribute_name="test_onoff",
            translation_key="test_onoff",
            fallback_name="Test on/off",
        )
        .tuya_number(
            dp_id=7,
            attribute_name="test_number",
            type=t.uint16_t,
            translation_key="test_number",
            fallback_name="Test number",
        )
        .tuya_binary_sensor(
            dp_id=8,
            attribute_name="test_binary",
            translation_key="test_binary",
            fallback_name="Test binary",
        )
        .tuya_sensor(
            dp_id=9,
            attribute_name="test_sensor",
            type=t.uint8_t,
            translation_key="test_sensor",
            fallback_name="Test sensor",
        )
        .tuya_enum(
            dp_id=10,
            attribute_name="test_enum",
            enum_class=TestEnum,
            translation_key="test_enum",
            fallback_name="Test enum",
        )
        .skip_configuration()
        .add_to_registry()
    )

    # coverage for overridden __eq__ method
    assert entry.adds_metadata[0] != entry.adds_metadata[1]
    assert entry.adds_metadata[0] != entry

    quirked = registry.get_device(device_mock)
    assert isinstance(quirked, CustomDeviceV2)
    assert quirked in registry

    ep = quirked.endpoints[1]

    assert ep.basic is not None
    assert isinstance(ep.basic, Basic)

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    tuya_cluster = ep.tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    assert tuya_cluster.attributes_by_name["mcu_version"].id == 0xEF00
    assert tuya_cluster.attributes_by_name["test_onoff"].id == 0xEF06
    assert tuya_cluster.attributes_by_name["test_number"].id == 0xEF07
    assert tuya_cluster.attributes_by_name["test_binary"].id == 0xEF08
    assert tuya_cluster.attributes_by_name["test_sensor"].id == 0xEF09
    assert tuya_cluster.attributes_by_name["test_enum"].id == 0xEF0A

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(
            {
                "test_enum": 0x01,
            }
        )

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=b"\x01\x01\x00\x00\x01\n\x04\x00\x01\x01",
            command_id=0,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=t.PacketPriority.NORMAL,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

    assert tuya_listener.attribute_updates[0][0] == 0xEF0A
    assert tuya_listener.attribute_updates[0][1] == TestEnum.B


@pytest.mark.parametrize(
    "read_attr_spell,data_query_spell",
    [
        (True, False),
        (False, True),
        (True, True),
        (False, False),
    ],
)
async def test_tuya_spell(device_mock, read_attr_spell, data_query_spell):
    """Test that enchanted Tuya devices have their spells applied during configuration."""
    registry = DeviceRegistry()

    entry = (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_battery(dp_id=1)
        .tuya_onoff(dp_id=3)
        .tuya_enchantment(
            read_attr_spell=read_attr_spell, data_query_spell=data_query_spell
        )
        .skip_configuration()
        .add_to_registry()
    )

    # coverage for overridden __eq__ method
    assert entry.adds_metadata[0] != entry.adds_metadata[1]
    assert entry.adds_metadata[0] != entry

    quirked = registry.get_device(device_mock)

    assert isinstance(quirked, CustomDeviceV2)
    assert quirked in registry

    request_patch = mock.patch("zigpy.zcl.Cluster.request", mock.AsyncMock())
    with request_patch as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        # call apply_custom_configuration() on each EnchantedDevice
        # ZHA does this during device configuration normally
        await quirked.apply_custom_configuration()

        # the number of Tuya spells that are allowed to be cast, so the sum of enabled Tuya spells
        enabled_tuya_spells_num = (
            quirked.tuya_spell_read_attributes + quirked.tuya_spell_data_query
        )

        # verify request was called the correct number of times
        assert request_mock.call_count == enabled_tuya_spells_num

        # used to check list of mock calls below
        messages = 0

        # check 'attribute read spell' was cast correctly (if enabled)
        if quirked.tuya_spell_read_attributes:
            assert (
                request_mock.mock_calls[messages][1][1]
                == foundation.GeneralCommand.Read_Attributes
            )
            assert request_mock.mock_calls[messages][1][3] == [4, 0, 1, 5, 7, 65534]
            messages += 1

        # check 'query data spell' was cast correctly (if enabled)
        if quirked.tuya_spell_data_query:
            assert not request_mock.mock_calls[messages][1][0]
            assert request_mock.mock_calls[messages][1][1] == TUYA_QUERY_DATA
            messages += 1

        request_mock.reset_mock()
