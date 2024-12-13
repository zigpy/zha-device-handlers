"""Tests for TuyaQuirkBuilder."""

from unittest import mock

import pytest
from zigpy.device import Device
from zigpy.quirks.registry import DeviceRegistry
from zigpy.quirks.v2 import CustomDeviceV2
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.builder import (
    TuyaIasContact,
    TuyaIasFire,
    TuyaPowerConfigurationCluster2AAA,
    TuyaQuirkBuilder,
    TuyaRelativeHumidity,
    TuyaSoilMoisture,
    TuyaTemperatureMeasurement,
    TuyaValveWaterConsumed,
)
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaOnOffNM

from .async_mock import sentinel

zhaquirks.setup()


@pytest.fixture(name="device_mock")
def real_device(MockAppController):
    """Device fixture with a single endpoint."""
    ieee = sentinel.ieee
    nwk = 0x2233
    device = Device(MockAppController, ieee, nwk)

    device.add_endpoint(1)
    device[1].profile_id = 0x0104
    device[1].device_type = 0x0051
    device.model = "model"
    device.manufacturer = "manufacturer"
    device[1].add_input_cluster(0x0000)
    device[1].add_input_cluster(0xEF00)
    device[1].add_output_cluster(0x000A)
    device[1].add_output_cluster(0x0019)
    return device


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
