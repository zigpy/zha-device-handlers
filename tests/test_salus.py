"""Tests for Salus quirks."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms import EntityCategory
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.hvac import Thermostat

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.salus import COMPUTIME_MANUFACTURER_CODE
from zhaquirks.salus.st100zb import (
    SalusFanCoilType,
    SalusHeatCoolOption,
    SalusHoldType,
    SalusInstallerCluster,
    SalusThermostat,
    SalusThermostatCluster,
    SalusTimeFormat,
)

zhaquirks.setup()


@pytest.fixture
def st100zb(zigpy_device_from_v2_quirk):
    """Salus ST100ZB with its clusters on endpoint 9."""
    return zigpy_device_from_v2_quirk(
        "SALUS",
        "ST100ZB",
        endpoint_ids=[9],
        cluster_ids={
            9: {
                Thermostat.cluster_id: ClusterType.Server,
                SalusThermostatCluster.cluster_id: ClusterType.Server,
                SalusInstallerCluster.cluster_id: ClusterType.Server,
            }
        },
    )


def test_st100zb_clusters(st100zb):
    """Test the ST100ZB clusters are replaced."""
    ep = st100zb.endpoints[9]
    assert isinstance(ep.thermostat, SalusThermostat)
    assert isinstance(ep.salus_thermostat, SalusThermostatCluster)
    assert isinstance(ep.salus_installer, SalusInstallerCluster)


async def test_st100zb_setpoint_limits(st100zb):
    """Test the absolute setpoint limits are answered locally."""
    thermostat = st100zb.endpoints[9].thermostat
    attrs = Thermostat.AttributeDefs

    with mock.patch.object(thermostat, "_read_attributes") as read_mock:
        success, fail = await thermostat.read_attributes(
            [
                attrs.abs_min_heat_setpoint_limit.name,
                attrs.abs_max_heat_setpoint_limit.name,
                attrs.abs_min_cool_setpoint_limit.name,
                attrs.abs_max_cool_setpoint_limit.name,
            ]
        )

    read_mock.assert_not_called()
    assert success == {
        attrs.abs_min_heat_setpoint_limit.name: 500,
        attrs.abs_max_heat_setpoint_limit.name: 3350,
        attrs.abs_min_cool_setpoint_limit.name: 650,
        attrs.abs_max_cool_setpoint_limit.name: 3500,
    }
    assert not fail


async def test_st100zb_hold_type_write(st100zb):
    """Test the hold type is written as a manufacturer-specific uint8."""
    cluster = st100zb.endpoints[9].salus_thermostat

    with mock.patch.object(cluster, "request", mock.AsyncMock()) as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "")
        await cluster.write_attributes(
            {
                SalusThermostatCluster.AttributeDefs.hold_type.name: (
                    SalusHoldType.Permanent_override
                )
            }
        )

    assert request_mock.call_count == 1
    assert request_mock.mock_calls[0].kwargs["manufacturer"] == (
        COMPUTIME_MANUFACTURER_CODE
    )
    (record,) = request_mock.mock_calls[0].args[3]
    assert record.attrid == SalusThermostatCluster.AttributeDefs.hold_type.id
    assert record.value.type == foundation.DataTypeId.uint8
    assert record.value.value == SalusHoldType.Permanent_override


async def test_st100zb_time_format(st100zb):
    """Test the time format is a boolean on the device."""
    cluster = st100zb.endpoints[9].salus_thermostat
    attr = SalusThermostatCluster.AttributeDefs.time_format

    with mock.patch.object(cluster, "request", mock.AsyncMock()) as request_mock:
        request_mock.return_value = (foundation.Status.SUCCESS, "")
        await cluster.write_attributes({attr.name: SalusTimeFormat.Format_24h})

    assert request_mock.mock_calls[0].kwargs["manufacturer"] == (
        COMPUTIME_MANUFACTURER_CODE
    )
    (record,) = request_mock.mock_calls[0].args[3]
    assert record.attrid == attr.id
    assert record.value.type == foundation.DataTypeId.bool_
    assert record.value.value == SalusTimeFormat.Format_24h

    # the device reports a boolean
    hdr = foundation.ZCLHeader.general(
        1,
        foundation.GeneralCommand.Report_Attributes,
        manufacturer=COMPUTIME_MANUFACTURER_CODE,
    )
    report = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema(
        attribute_reports=[
            foundation.Attribute(
                attr.id, foundation.TypeValue(foundation.DataTypeId.bool_, t.Bool.false)
            )
        ]
    )
    cluster.handle_message(hdr, report)
    assert cluster.get(attr.name) is SalusTimeFormat.Format_12h


@pytest.mark.parametrize(
    ("fan_coil_type", "current_option", "expected"),
    [
        # 4-pipe refuses heat only and cool only: reset to auto changeover
        (
            SalusFanCoilType.Four_pipe,
            SalusHeatCoolOption.Heat_only,
            {0x0000: SalusFanCoilType.Four_pipe, 0x0003: 3},
        ),
        (
            SalusFanCoilType.Four_pipe,
            SalusHeatCoolOption.Cool_only,
            {0x0000: SalusFanCoilType.Four_pipe, 0x0003: 3},
        ),
        # the option is unknown: reset as well
        (
            SalusFanCoilType.Four_pipe,
            None,
            {0x0000: SalusFanCoilType.Four_pipe, 0x0003: 3},
        ),
        # valid for both: kept
        (
            SalusFanCoilType.Four_pipe,
            SalusHeatCoolOption.Manual_changeover,
            {0x0000: SalusFanCoilType.Four_pipe},
        ),
        # 2-pipe allows every option
        (SalusFanCoilType.Two_pipe, None, {0x0000: SalusFanCoilType.Two_pipe}),
    ],
)
async def test_st100zb_fan_coil_type_write(
    st100zb, fan_coil_type, current_option, expected
):
    """Test a fan coil type change resets a heat/cool option it doesn't allow."""
    cluster = st100zb.endpoints[9].salus_installer
    attrs = SalusInstallerCluster.AttributeDefs
    read_result = (
        {attrs.heat_cool_option.name: current_option}
        if current_option is not None
        else {}
    )

    with (
        mock.patch.object(
            cluster, "read_attributes", mock.AsyncMock(return_value=(read_result, {}))
        ) as read_mock,
        mock.patch.object(cluster, "request", mock.AsyncMock()) as request_mock,
    ):
        request_mock.return_value = (foundation.Status.SUCCESS, "")
        await cluster.write_attributes({attrs.fan_coil_type.name: fan_coil_type})

    assert read_mock.call_count == (
        1 if fan_coil_type == SalusFanCoilType.Four_pipe else 0
    )
    assert request_mock.call_count == 1
    assert request_mock.mock_calls[0].kwargs["manufacturer"] == (
        COMPUTIME_MANUFACTURER_CODE
    )
    records = request_mock.mock_calls[0].args[3]
    assert {r.attrid: r.value.value for r in records} == expected
    assert all(r.value.type == foundation.DataTypeId.uint8 for r in records)


async def test_st100zb_heat_cool_option_write(st100zb):
    """Test the heat/cool option is written as is, without a read."""
    cluster = st100zb.endpoints[9].salus_installer
    attrs = SalusInstallerCluster.AttributeDefs

    with (
        mock.patch.object(cluster, "read_attributes", mock.AsyncMock()) as read_mock,
        mock.patch.object(cluster, "request", mock.AsyncMock()) as request_mock,
    ):
        request_mock.return_value = (foundation.Status.SUCCESS, "")
        await cluster.write_attributes(
            {
                attrs.fan_coil_type.id: SalusFanCoilType.Four_pipe,
                attrs.heat_cool_option.id: SalusHeatCoolOption.Manual_changeover,
            }
        )

    read_mock.assert_not_called()
    records = request_mock.mock_calls[0].args[3]
    assert {r.attrid: r.value.value for r in records} == {
        attrs.fan_coil_type.id: SalusFanCoilType.Four_pipe,
        attrs.heat_cool_option.id: SalusHeatCoolOption.Manual_changeover,
    }


async def test_st100zb_entities():
    """Test the quirk's entities when the device joins ZHA."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "salus-st100zb-0x00230012.json", DEVICE_REGISTRY
        )

        expected = {
            (Platform.BINARY_SENSOR, "ac_error_code"): (
                None,
                EntityCategory.DIAGNOSTIC,
                True,
            ),
            (Platform.SWITCH, "remote_sensing"): (
                "external_temperature_sensor",
                EntityCategory.CONFIG,
                True,
            ),
            (Platform.NUMBER, "min_cool_setpoint_limit"): (
                "min_cool_setpoint_limit",
                EntityCategory.CONFIG,
                True,
            ),
            (Platform.NUMBER, "max_cool_setpoint_limit"): (
                "max_cool_setpoint_limit",
                EntityCategory.CONFIG,
                True,
            ),
            (Platform.SELECT, "temperature_display_mode"): (
                "temperature_display_mode",
                EntityCategory.CONFIG,
                True,
            ),
            (Platform.SELECT, "hold_type"): ("hold_type", EntityCategory.CONFIG, True),
            (Platform.SELECT, "time_format"): (
                "time_format",
                EntityCategory.CONFIG,
                True,
            ),
            (Platform.SELECT, "fan_coil_type"): (
                "fan_coil_type",
                EntityCategory.CONFIG,
                False,
            ),
            (Platform.SELECT, "heat_cool_option"): (
                "heat_cool_option",
                EntityCategory.CONFIG,
                False,
            ),
        }

        for (platform, suffix), (key, category, enabled) in expected.items():
            entity = device.get_platform_entity(
                platform, unique_id=f"{device.ieee}-9-{suffix}"
            )
            assert entity.translation_key == key
            assert entity.entity_category == category
            assert entity.entity_registry_enabled_default is enabled

        climate = device.get_platform_entity(
            Platform.CLIMATE, unique_id=f"{device.ieee}-9"
        )
        assert climate.min_temp == 5.0
        assert climate.max_temp == 35.0

        time_format = device.get_platform_entity(
            Platform.SELECT, unique_id=f"{device.ieee}-9-time_format"
        )
        assert time_format.current_option == "Format 12h"
