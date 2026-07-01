"""Tests for TuyaQuirkBuilder."""

import datetime
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
import time_machine
from zigpy.quirks.registry import DeviceRegistry
from zigpy.quirks.v2 import CustomDeviceV2
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.const import BatterySize
from zhaquirks.tuya import (
    TUYA_QUERY_DATA,
    TUYA_SEND_DATA,
    TUYA_SET_TIME,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster,
    TuyaPowerConfigurationCluster2AAA,
)
from zhaquirks.tuya.builder import (
    TuyaAirQualityVOC,
    TuyaCO2Concentration,
    TuyaFormaldehydeConcentration,
    TuyaIasContact,
    TuyaIasFire,
    TuyaIasGas,
    TuyaIasVibration,
    TuyaIlluminance,
    TuyaPM25Concentration,
    TuyaQuirkBuilder,
    TuyaRelativeHumidity,
    TuyaSoilMoisture,
    TuyaTemperatureMeasurement,
    TuyaValveWaterConsumedNoInstDemand,
)
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster, TuyaOnOffNM
from zhaquirks.tuya.tuya_sensor import NoManufTimeTuyaMCUCluster

ZCL_TUYA_SET_TIME = b"\x09\x12\x24\x0d\x00"

zhaquirks.setup()


@pytest.mark.parametrize(
    "method_name,attr_name,exp_class",
    [
        ("tuya_battery", "power", TuyaPowerConfigurationCluster),
        ("tuya_metering", "smartenergy_metering", TuyaValveWaterConsumedNoInstDemand),
        ("tuya_onoff", "on_off", TuyaOnOffNM),
        ("tuya_soil_moisture", "soil_moisture", TuyaSoilMoisture),
        ("tuya_temperature", "temperature", TuyaTemperatureMeasurement),
        ("tuya_humidity", "humidity", TuyaRelativeHumidity),
        ("tuya_smoke", "ias_zone", TuyaIasFire),
        ("tuya_contact", "ias_zone", TuyaIasContact),
        ("tuya_co2", "carbon_dioxide_concentration", TuyaCO2Concentration),
        ("tuya_pm25", "pm25", TuyaPM25Concentration),
        ("tuya_voc", "voc_level", TuyaAirQualityVOC),
        ("tuya_vibration", "ias_zone", TuyaIasVibration),
        (
            "tuya_formaldehyde",
            "formaldehyde_concentration",
            TuyaFormaldehydeConcentration,
        ),
        ("tuya_gas", "ias_zone", TuyaIasGas),
        ("tuya_illuminance", "illuminance", TuyaIlluminance),
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


@pytest.mark.parametrize(
    "power_cfg,battery_type,battery_qty,battery_voltage,"
    "expected_size,expected_qty,expected_voltage",
    [
        (TuyaPowerConfigurationCluster2AAA, None, None, None, BatterySize.AAA, 2, 15),
        (None, BatterySize.CR123A, 1, 60, BatterySize.CR123A, 1, 60),
        (None, BatterySize.CR123A, 1, None, BatterySize.CR123A, 1, 30),
        (None, BatterySize.CR2450, 1, None, BatterySize.CR2450, 1, 30),
        (None, BatterySize.CR2032, 1, None, BatterySize.CR2032, 1, 30),
        (None, BatterySize.CR1632, 1, None, BatterySize.CR1632, 1, 30),
        (None, BatterySize.AA, None, None, BatterySize.AA, None, None),
        (None, None, None, None, None, None, None),
    ],
)
async def test_battery_methods(
    device_mock,
    power_cfg,
    battery_type,
    battery_qty,
    battery_voltage,
    expected_size,
    expected_qty,
    expected_voltage,
):
    """Test the battery convenience method."""

    registry = DeviceRegistry()

    (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_battery(
            dp_id=1,
            power_cfg=power_cfg,
            battery_type=battery_type,
            battery_qty=battery_qty,
            battery_voltage=battery_voltage,
        )
        .tuya_onoff(dp_id=3)
        .skip_configuration()
        .add_to_registry()
    )

    quirked = registry.get_device(device_mock)
    ep = quirked.endpoints[1]

    assert ep.power is not None
    assert isinstance(ep.power, power_cfg or TuyaPowerConfigurationCluster)

    assert ep.power.get("battery_size") == expected_size
    assert ep.power.get("battery_quantity") == expected_qty
    assert ep.power.get("battery_rated_voltage") == expected_voltage


async def test_tuya_quirkbuilder(device_mock):
    """Test adding a v2 Tuya Quirk to the registry and getting back a quirked device."""

    registry = DeviceRegistry()

    class TestEnum(t.enum8):
        """Test Enum."""

        A = 0x00
        B = 0x01

    class ModTuyaMCUCluster(TuyaMCUCluster):
        """Modified Cluster."""

    class Tuya3PhaseElectricalMeasurement(ElectricalMeasurement, TuyaLocalCluster):
        """Tuya Electrical Measurement cluster."""

    def dpToPower(data: bytes) -> int:
        return data[0]

    def dpToCurrent(data: bytes) -> int:
        return data[1]

    def dpToVoltage(data: bytes) -> int:
        return data[2]

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
        .tuya_dp_multi(
            dp_id=11,
            attribute_mapping=[
                DPToAttributeMapping(
                    ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                    attribute_name="active_power",
                    converter=dpToPower,
                ),
                DPToAttributeMapping(
                    ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                    attribute_name="rms_current",
                    converter=dpToCurrent,
                ),
                DPToAttributeMapping(
                    ep_attribute=Tuya3PhaseElectricalMeasurement.ep_attribute,
                    attribute_name="rms_voltage",
                    converter=dpToVoltage,
                ),
            ],
        )
        .adds(Tuya3PhaseElectricalMeasurement)
        .skip_configuration()
        .add_to_registry(replacement_cluster=ModTuyaMCUCluster)
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
    assert isinstance(ep.tuya_manufacturer, ModTuyaMCUCluster)
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
            priority=None,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

    assert tuya_listener.attribute_updates[0][0] == 0xEF0A
    assert tuya_listener.attribute_updates[0][1] == TestEnum.B

    electric_data = TuyaCommand(
        status=0,
        tsn=2,
        datapoints=[TuyaDatapointData(11, TuyaData("345"))],
    )
    tuya_cluster.handle_get_data(electric_data)
    electrical_meas_cluster = ep.electrical_measurement
    assert electrical_meas_cluster.get("active_power") == "3"
    assert electrical_meas_cluster.get("rms_current") == "4"
    assert electrical_meas_cluster.get("rms_voltage") == "5"


async def test_tuya_quirkbuilder_duplicated_mappings(device_mock):
    """Test that mapping the same DP multiple times will raise."""

    registry = DeviceRegistry()

    with pytest.raises(ValueError):
        (
            TuyaQuirkBuilder(
                device_mock.manufacturer, device_mock.model, registry=registry
            )
            .tuya_battery(dp_id=1)
            .tuya_onoff(dp_id=1)
            .skip_configuration()
            .add_to_registry()
        )

    with pytest.raises(ValueError):
        (
            TuyaQuirkBuilder(
                device_mock.manufacturer, device_mock.model, registry=registry
            )
            .tuya_battery(dp_id=1)
            .tuya_dp_multi(
                dp_id=1,
                attribute_mapping=[
                    DPToAttributeMapping(
                        ep_attribute=ElectricalMeasurement.ep_attribute,
                        attribute_name="active_power",
                    ),
                ],
            )
            .add_to_registry()
        )


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


@time_machine.travel(datetime.datetime(1970, 1, 1, 1, 0, tzinfo=ZoneInfo("Etc/GMT+1")))
async def test_tuya_mcu_set_time(device_mock):
    """Test TuyaQuirkBuilder replacement cluster, set_time requests (0x24) messages for MCU devices."""

    registry = DeviceRegistry()

    (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_battery(dp_id=1)
        .skip_configuration()
        .add_to_registry(replacement_cluster=NoManufTimeTuyaMCUCluster)
    )

    quirked = registry.get_device(device_mock)
    assert isinstance(quirked, CustomDeviceV2)
    assert quirked in registry

    ep = quirked.endpoints[1]

    assert not ep.tuya_manufacturer._is_manuf_specific
    assert not ep.tuya_manufacturer.server_commands[
        TUYA_SET_TIME
    ].is_manufacturer_specific

    # simulate a SET_TIME message
    hdr, args = ep.tuya_manufacturer.deserialize(ZCL_TUYA_SET_TIME)
    assert hdr.command_id == TUYA_SET_TIME

    with mock.patch.object(
        ep.tuya_manufacturer._endpoint,
        "request",
        return_value=foundation.Status.SUCCESS,
    ) as m1:
        ep.tuya_manufacturer.handle_message(hdr, args)
        await wait_for_zigpy_tasks()

        res_hdr = foundation.ZCLHeader.deserialize(m1.await_args[1]["data"])
        assert not res_hdr[0].manufacturer
        assert not res_hdr[0].frame_control.is_manufacturer_specific


@pytest.mark.parametrize(
    "force",
    [
        (False),
        (True),
    ],
)
async def test_tuya_quirkbuilder_force(device_mock, force):
    """Test adding an empty TuyaQuirkBuilder doesn't add an MCU cluster unless forced to."""

    registry = DeviceRegistry()

    (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .skip_configuration()
        .add_to_registry(force_add_cluster=force)
    )

    quirked = registry.get_device(device_mock)
    assert isinstance(quirked, CustomDeviceV2)
    assert quirked in registry

    ep = quirked.endpoints[1]

    if force:
        assert ep.tuya_manufacturer is not None
        assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)
    else:
        assert not hasattr(ep, "tuya_manufacturer")


@pytest.mark.parametrize(
    "kwargs,expected_cmd,expected_data",
    [
        (
            {},  # no kwarg should use default of TUYA_SET_DATA
            0,
            b"\x01\x01\x00\x00\x01\n\x04\x00\x01\x01",
        ),
        (
            {"mcu_write_command": TUYA_SEND_DATA},
            4,
            b"\x01\x01\x04\x00\x01\n\x04\x00\x01\x01",
        ),
    ],
)
async def test_tuya_override_mcu_command(
    device_mock, kwargs, expected_cmd, expected_data
):
    """Test TuyaQuirkBuilder overriding MCU datapoint write command."""

    registry = DeviceRegistry()

    class TestEnum(t.enum8):
        """Test Enum."""

        A = 0x00
        B = 0x01

    (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_enum(
            dp_id=10,
            attribute_name="test_enum",
            enum_class=TestEnum,
            translation_key="test_enum",
            fallback_name="Test enum",
        )
        .skip_configuration()
        .add_to_registry(**kwargs)
    )

    quirked = registry.get_device(device_mock)
    assert isinstance(quirked, CustomDeviceV2)
    assert quirked in registry

    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    tuya_cluster = ep.tuya_manufacturer
    tuya_listener = ClusterListener(tuya_cluster)
    assert tuya_cluster.attributes_by_name["test_enum"].id == 0xEF0A

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:
        (status,) = await tuya_cluster.write_attributes(
            {
                "test_enum": 0x01,
            },
        )

        await wait_for_zigpy_tasks()
        m1.assert_called_with(
            cluster=61184,
            sequence=1,
            data=expected_data,
            command_id=expected_cmd,
            timeout=5,
            expect_reply=False,
            use_ieee=False,
            ask_for_ack=None,
            priority=None,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

    assert tuya_listener.attribute_updates[0][0] == 0xEF0A
    assert tuya_listener.attribute_updates[0][1] == TestEnum.B
