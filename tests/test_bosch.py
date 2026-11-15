"""Tests the Bosch thermostats quirk."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zha.zigbee.cluster_config import (
    aggregate_cluster_configs,
    initialize_cluster_configs,
)
from zigpy.exceptions import ZigbeeException
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import ControlSequenceOfOperation, Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord

import zhaquirks
from zhaquirks.bosch.rbsh_trv0_zb_eu import (
    BoschOperatingMode,
    BoschRestartReason,
    BoschThermostatCluster as BoschTrvThermostatCluster,
    BoschUserInterfaceCluster,
    BoschValveAdaptStatus,
)
from zhaquirks.builder import NumberDeviceClass, UnitOfTemperature
from zhaquirks.builder.discovery import discover_quirks_v2_entities

zhaquirks.setup()


def _mock_bosch_write_statuses(status_by_attribute):
    """Return a device-style write response with failures or global success."""

    def mock_write(attributes, manufacturer=None):
        failures = [
            WriteAttributesStatusRecord(
                status_by_attribute[attribute.attrid], attrid=attribute.attrid
            )
            for attribute in attributes
            if status_by_attribute.get(attribute.attrid, foundation.Status.SUCCESS)
            != foundation.Status.SUCCESS
        ]
        return [
            failures or [WriteAttributesStatusRecord(foundation.Status.SUCCESS)],
            [],
        ]

    return mock.AsyncMock(side_effect=mock_write)


async def test_bosch_radiator_thermostat_II_write_attributes(
    zigpy_device_from_v2_quirk,
):
    """Test the Radiator Thermostat II writes behaving correctly."""

    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    # data is written to trv
    patch_bosch_trv_write = mock.patch.object(
        bosch_thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )

    # fake read response for attributes: return BoschOperatingMode.Manual for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr,
                foundation.Status.SUCCESS,
                foundation.TypeValue(None, BoschOperatingMode.Manual),
            )
            for attr in attributes
        ]
        return (records,)

    # data is read from trv
    patch_bosch_trv_read = mock.patch.object(
        bosch_thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read),
    )

    # check that system_mode ends-up writing operating_mode:
    with patch_bosch_trv_write, patch_bosch_trv_read:
        # - Heating operation - by name
        await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Heating_Only}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # - Heating operation - by id
        await bosch_thermostat_cluster.write_attributes(
            {
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: ControlSequenceOfOperation.Heating_Only
            }
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Off (by-name)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Pause
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Heat (by-name)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Heat}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Heat
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Off (by-id)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Off}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Pause
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Heat (by-id)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Heat}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Heat
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- operating_mode (by-id) changes system_mode
        await bosch_thermostat_cluster.write_attributes(
            {
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id: BoschOperatingMode.Pause
            }
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Pause
        )

        # -- operating_mode (by-name) changes system_mode
        await bosch_thermostat_cluster.write_attributes(
            {
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.name: BoschOperatingMode.Manual
            }
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Heat
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )

        # - Cooling operation
        await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Cooling_Only}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Cool
        )

        # -- Off (by-name)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Pause
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- Cool (by-name)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Cool}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Cool
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- Off (by-id)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Off}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Pause
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- Cool (by-id)
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Cool}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Cool
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- operating_mode (by-id) in cooling mode
        await bosch_thermostat_cluster.write_attributes(
            {
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id: BoschOperatingMode.Manual,
            }
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Cool
        )

        # -- operating_mode (by-id) gets ignored when system_mode is written
        await bosch_thermostat_cluster.write_attributes(
            {
                Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Off,
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id: BoschOperatingMode.Manual,
            }
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Pause
        )

        # -- operating_mode (by-name) gets ignored when system_mode is written
        await bosch_thermostat_cluster.write_attributes(
            {
                Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Cool,
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.name: BoschOperatingMode.Pause,
            }
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Cool
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
            ]
            == BoschOperatingMode.Manual
        )


async def test_bosch_radiator_thermostat_II_read_attributes_paused(
    zigpy_device_from_v2_quirk,
):
    """Test the Radiator Thermostat II reads behaving correctly when paused."""

    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    # fake read response for attributes: return BoschOperatingMode.Pause for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr,
                foundation.Status.SUCCESS,
                foundation.TypeValue(None, BoschOperatingMode.Pause),
            )
            for attr in attributes
        ]
        return (records,)

    # data is read from trv
    patch_bosch_trv_read = mock.patch.object(
        bosch_thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read),
    )

    # check that system_mode ends-up reading operating_mode:
    with patch_bosch_trv_read:
        # - system_mode by id
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.id]
        )
        assert Thermostat.SystemMode.Off in success.values()

        # - system_mode by id along other attributes
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [
                Thermostat.AttributeDefs.system_mode.id,
                BoschTrvThermostatCluster.AttributeDefs.pi_heating_demand.id,
            ]
        )
        assert Thermostat.SystemMode.Off in success.values()

        # - system_mode by name
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.name]
        )
        assert Thermostat.SystemMode.Off in success.values()

        # - system_mode by name along other attributes
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [
                Thermostat.AttributeDefs.system_mode.name,
                BoschTrvThermostatCluster.AttributeDefs.pi_heating_demand.name,
            ]
        )
        assert Thermostat.SystemMode.Off in success.values()


async def test_bosch_radiator_thermostat_II_read_attributes_manual_heat(
    zigpy_device_from_v2_quirk,
):
    """Test the Radiator Thermostat II reads behaving correctly when heat is enabled."""

    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    # fake read response for attributes: return BoschOperatingMode.Manual/ControlSequenceOfOperation.Heating_Only for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr,
                foundation.Status.SUCCESS,
                foundation.TypeValue(
                    None,
                    BoschOperatingMode.Manual
                    if attr == BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
                    else ControlSequenceOfOperation.Heating_Only,
                ),
            )
            for attr in attributes
        ]
        return (records,)

    # data is read from trv
    patch_bosch_trv_read = mock.patch.object(
        bosch_thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read),
    )

    # check that system_mode ends-up reading operating_mode and ControlSequenceOfOperation:
    with patch_bosch_trv_read:
        # - system_mode by id
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.id]
        )
        assert Thermostat.SystemMode.Heat in success.values()

        # - system_mode by name
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.name]
        )
        assert Thermostat.SystemMode.Heat in success.values()


async def test_bosch_radiator_thermostat_II_read_attributes_manual_cool(
    zigpy_device_from_v2_quirk,
):
    """Test the Radiator Thermostat II reads behaving correctly when cooling is enabled."""

    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    # fake read response for attributes: return BoschOperatingMode.Manual/ControlSequenceOfOperation.Cooling_Only for all attributes
    def mock_read(attributes, manufacturer=None):
        records = [
            foundation.ReadAttributeRecord(
                attr,
                foundation.Status.SUCCESS,
                foundation.TypeValue(
                    None,
                    BoschOperatingMode.Manual
                    if attr == BoschTrvThermostatCluster.AttributeDefs.operating_mode.id
                    else ControlSequenceOfOperation.Cooling_Only,
                ),
            )
            for attr in attributes
        ]
        return (records,)

    # data is read from trv
    patch_bosch_trv_read = mock.patch.object(
        bosch_thermostat_cluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read),
    )

    # check that system_mode ends-up reading operating_mode and ControlSequenceOfOperation:
    with patch_bosch_trv_read:
        # - system_mode by id
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.id]
        )
        assert Thermostat.SystemMode.Cool in success.values()

        # - system_mode by name
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.name]
        )
        assert Thermostat.SystemMode.Cool in success.values()


async def test_bosch_room_thermostat_II_230v_write_attributes(
    zigpy_device_from_v2_quirk,
):
    """Test the Room Thermostat II 230v system_mode writes behaving correctly."""

    device = zigpy_device_from_v2_quirk(manufacturer="Bosch", model="RBSH-RTH0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    # data is written to trv
    patch_bosch_trv_write = mock.patch.object(
        bosch_thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )

    with patch_bosch_trv_write:
        # check that system_mode ends-up writing operating_mode:

        # - Heating operation
        await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Heating_Only}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Off
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Heat
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Heat}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Heat
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # - Cooling operation
        await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Cooling_Only}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- Off
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Off
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- Cool
        await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Cool}
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.system_mode.id
            ]
            == Thermostat.SystemMode.Cool
        )
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )


async def test_bosch_radiator_thermostat_II_system_mode_report_ignored(
    zigpy_device_from_v2_quirk,
):
    """Test system_mode reports are ignored but still acknowledged."""

    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV0-ZB-EU")
    bosch_thermostat_cluster = device.endpoints[1].thermostat

    def receive(data: bytes) -> None:
        device.packet_received(
            t.ZigbeePacket(
                profile_id=260,
                cluster_id=Thermostat.cluster_id,
                src_ep=1,
                dst_ep=1,
                data=t.SerializableBytes(data),
            )
        )

    with mock.patch.object(
        bosch_thermostat_cluster, "send_default_rsp"
    ) as default_rsp_mock:
        # Frame control 0x08: default response requested, system_mode=Heat
        receive(b"\x08\x01\x0a\x1c\x00\x30\x04")
        assert default_rsp_mock.call_count == 1
        assert (
            bosch_thermostat_cluster.get(Thermostat.AttributeDefs.system_mode.name)
            is None
        )

        # system_mode=Heat and local_temperature=21.50 °C
        receive(b"\x08\x02\x0a\x1c\x00\x30\x04\x00\x00\x29\x66\x08")
        assert default_rsp_mock.call_count == 2
        assert (
            bosch_thermostat_cluster.get(Thermostat.AttributeDefs.system_mode.name)
            is None
        )
        assert (
            bosch_thermostat_cluster.get(
                Thermostat.AttributeDefs.local_temperature.name
            )
            == 2150
        )


async def test_bosch_radiator_thermostat_II_operating_mode_values(
    zigpy_device_from_v2_quirk,
):
    """Test all verified operating modes and reject unknown mode values."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    cluster._attr_cache[Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] = (
        ControlSequenceOfOperation.Heating_Only
    )

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(
                foundation.Status.SUCCESS, attrid=attribute.attrid
            )
            for attribute in attributes
        ]
        return [records, []]

    write_mock = mock.AsyncMock(side_effect=mock_write)
    with mock.patch.object(cluster, "_write_attributes", write_mock):
        for value, expected_system_mode in (
            (BoschOperatingMode.Schedule, Thermostat.SystemMode.Auto),
            (BoschOperatingMode.Manual, Thermostat.SystemMode.Heat),
            (BoschOperatingMode.Eco, Thermostat.SystemMode.Heat),
            (BoschOperatingMode.Away, Thermostat.SystemMode.Heat),
            (BoschOperatingMode.Holiday, Thermostat.SystemMode.Heat),
            (BoschOperatingMode.Pause, Thermostat.SystemMode.Off),
        ):
            result = await cluster.write_attributes(
                {"operating_mode": value},
            )

            assert result[0][0].status == foundation.Status.SUCCESS
            assert cluster.get("operating_mode") == value
            assert cluster.get("system_mode") == expected_system_mode
            assert write_mock.await_args.kwargs["manufacturer"] == 0x1209

        result = await cluster.write_attributes({"operating_mode": 0x06})
        assert result[0][0].status == foundation.Status.INVALID_VALUE

        write_mock.side_effect = None
        write_mock.return_value = [
            [
                WriteAttributesStatusRecord(
                    foundation.Status.UNSUPPORTED_ATTRIBUTE,
                    attrid=BoschTrvThermostatCluster.AttributeDefs.operating_mode.id,
                )
            ],
            [],
        ]
        result = await cluster.write_attributes(
            {"operating_mode": BoschOperatingMode.Eco},
        )
        assert result[0][0].status == foundation.Status.UNSUPPORTED_ATTRIBUTE
        assert cluster.get("operating_mode") != BoschOperatingMode.Eco
        assert cluster.get("system_mode") == Thermostat.SystemMode.Off


@pytest.mark.parametrize(
    ("operating_mode", "write_status", "expected_system_mode"),
    [
        (
            BoschOperatingMode.Manual,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (BoschOperatingMode.Eco, foundation.Status.SUCCESS, Thermostat.SystemMode.Cool),
        (
            BoschOperatingMode.Away,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (
            BoschOperatingMode.Holiday,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (
            BoschOperatingMode.Schedule,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Auto,
        ),
        (
            BoschOperatingMode.Pause,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Off,
        ),
        (
            BoschOperatingMode.Manual,
            foundation.Status.INVALID_VALUE,
            Thermostat.SystemMode.Heat,
        ),
        (
            BoschOperatingMode.Eco,
            foundation.Status.INVALID_VALUE,
            Thermostat.SystemMode.Heat,
        ),
    ],
)
async def test_bosch_control_sequence_updates_system_mode_after_success(
    zigpy_device_from_v2_quirk, operating_mode, write_status, expected_system_mode
):
    """Only a successful control-sequence write changes an active system mode."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    mode_attr = BoschTrvThermostatCluster.AttributeDefs.operating_mode
    control_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper
    system_attr = Thermostat.AttributeDefs.system_mode
    initial_system_mode = {
        BoschOperatingMode.Schedule: Thermostat.SystemMode.Auto,
        BoschOperatingMode.Pause: Thermostat.SystemMode.Off,
    }.get(operating_mode, Thermostat.SystemMode.Heat)
    cluster._update_attribute(mode_attr.id, operating_mode)
    cluster._update_attribute(control_attr.id, ControlSequenceOfOperation.Heating_Only)
    cluster._update_attribute(system_attr.id, initial_system_mode)

    with mock.patch.object(
        cluster,
        "_write_attributes",
        _mock_bosch_write_statuses({control_attr.id: write_status}),
    ):
        result = await cluster.write_attributes(
            {control_attr.name: ControlSequenceOfOperation.Cooling_Only}
        )

    assert result[0][0].status == write_status
    assert cluster.get(control_attr.name) == (
        ControlSequenceOfOperation.Cooling_Only
        if write_status == foundation.Status.SUCCESS
        else ControlSequenceOfOperation.Heating_Only
    )
    assert cluster.get(system_attr.name) == expected_system_mode


@pytest.mark.parametrize(
    ("mode_status", "temperature_status", "expected_system_mode"),
    [
        (
            foundation.Status.SUCCESS,
            foundation.Status.INVALID_VALUE,
            Thermostat.SystemMode.Heat,
        ),
        (
            foundation.Status.INVALID_VALUE,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Off,
        ),
        (
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Heat,
        ),
    ],
)
async def test_bosch_operating_mode_partial_write(
    zigpy_device_from_v2_quirk, mode_status, temperature_status, expected_system_mode
):
    """Synchronize system mode based on the mode write, not unrelated attributes."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    mode_attr = BoschTrvThermostatCluster.AttributeDefs.operating_mode
    temperature_attr = BoschTrvThermostatCluster.AttributeDefs.eco_temperature
    control_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper
    system_attr = Thermostat.AttributeDefs.system_mode
    cluster._update_attribute(mode_attr.id, BoschOperatingMode.Pause)
    cluster._update_attribute(control_attr.id, ControlSequenceOfOperation.Heating_Only)
    cluster._update_attribute(system_attr.id, Thermostat.SystemMode.Off)
    statuses = {mode_attr.id: mode_status, temperature_attr.id: temperature_status}

    with mock.patch.object(
        cluster, "_write_attributes", _mock_bosch_write_statuses(statuses)
    ):
        result = await cluster.write_attributes(
            {mode_attr.name: BoschOperatingMode.Eco, temperature_attr.name: 1800}
        )

    assert {record.attrid: record.status for record in result[0]} == statuses
    assert cluster.get(mode_attr.name) == (
        BoschOperatingMode.Eco
        if mode_status == foundation.Status.SUCCESS
        else BoschOperatingMode.Pause
    )
    assert cluster.get(system_attr.name) == expected_system_mode


@pytest.mark.parametrize(
    ("mode_status", "control_status", "temperature_status", "expected_system_mode"),
    [
        (
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
            foundation.Status.INVALID_VALUE,
            Thermostat.SystemMode.Cool,
        ),
        (
            foundation.Status.SUCCESS,
            foundation.Status.INVALID_VALUE,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Heat,
        ),
        (
            foundation.Status.INVALID_VALUE,
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (
            foundation.Status.INVALID_VALUE,
            foundation.Status.INVALID_VALUE,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Heat,
        ),
    ],
)
async def test_bosch_combined_operating_mode_and_control_writes(
    zigpy_device_from_v2_quirk,
    mode_status,
    control_status,
    temperature_status,
    expected_system_mode,
):
    """Derive system mode from whichever writes actually succeeded."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    mode_attr = BoschTrvThermostatCluster.AttributeDefs.operating_mode
    temperature_attr = BoschTrvThermostatCluster.AttributeDefs.eco_temperature
    control_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper
    system_attr = Thermostat.AttributeDefs.system_mode
    cluster._update_attribute(mode_attr.id, BoschOperatingMode.Manual)
    cluster._update_attribute(control_attr.id, ControlSequenceOfOperation.Heating_Only)
    cluster._update_attribute(system_attr.id, Thermostat.SystemMode.Heat)
    statuses = {
        mode_attr.id: mode_status,
        control_attr.id: control_status,
        temperature_attr.id: temperature_status,
    }

    with mock.patch.object(
        cluster, "_write_attributes", _mock_bosch_write_statuses(statuses)
    ):
        result = await cluster.write_attributes(
            {
                mode_attr.name: BoschOperatingMode.Eco,
                control_attr.name: ControlSequenceOfOperation.Cooling_Only,
                temperature_attr.name: 1800,
            }
        )

    assert {record.attrid: record.status for record in result[0]} == statuses
    assert cluster.get(mode_attr.name) == (
        BoschOperatingMode.Eco
        if mode_status == foundation.Status.SUCCESS
        else BoschOperatingMode.Manual
    )
    assert cluster.get(control_attr.name) == (
        ControlSequenceOfOperation.Cooling_Only
        if control_status == foundation.Status.SUCCESS
        else ControlSequenceOfOperation.Heating_Only
    )
    assert cluster.get(system_attr.name) == expected_system_mode


@pytest.mark.parametrize(
    ("mode_status", "control_status", "expected_system_mode"),
    [
        (
            foundation.Status.SUCCESS,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (
            foundation.Status.SUCCESS,
            foundation.Status.INVALID_VALUE,
            Thermostat.SystemMode.Heat,
        ),
        (
            foundation.Status.INVALID_VALUE,
            foundation.Status.SUCCESS,
            Thermostat.SystemMode.Cool,
        ),
        (
            foundation.Status.INVALID_VALUE,
            foundation.Status.INVALID_VALUE,
            Thermostat.SystemMode.Heat,
        ),
    ],
)
async def test_bosch_combined_system_mode_and_control_writes(
    zigpy_device_from_v2_quirk, mode_status, control_status, expected_system_mode
):
    """Keep translated system-mode writes consistent with control-sequence results."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    mode_attr = BoschTrvThermostatCluster.AttributeDefs.operating_mode
    control_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper
    system_attr = Thermostat.AttributeDefs.system_mode
    cluster._update_attribute(mode_attr.id, BoschOperatingMode.Eco)
    cluster._update_attribute(control_attr.id, ControlSequenceOfOperation.Heating_Only)
    cluster._update_attribute(system_attr.id, Thermostat.SystemMode.Heat)
    statuses = {mode_attr.id: mode_status, control_attr.id: control_status}

    with mock.patch.object(
        cluster, "_write_attributes", _mock_bosch_write_statuses(statuses)
    ):
        result = await cluster.write_attributes(
            {
                system_attr.name: Thermostat.SystemMode.Cool,
                control_attr.name: ControlSequenceOfOperation.Cooling_Only,
            }
        )

    assert {
        record.attrid: record.status for response in result for record in response
    } == statuses
    assert cluster.get(mode_attr.name) == (
        BoschOperatingMode.Manual
        if mode_status == foundation.Status.SUCCESS
        else BoschOperatingMode.Eco
    )
    assert cluster.get(control_attr.name) == (
        ControlSequenceOfOperation.Cooling_Only
        if control_status == foundation.Status.SUCCESS
        else ControlSequenceOfOperation.Heating_Only
    )
    assert cluster.get(system_attr.name) == expected_system_mode


async def test_bosch_operating_mode_missing_write_status(
    zigpy_device_from_v2_quirk,
):
    """Do not infer a mode write succeeded from another attribute's status."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    mode_attr = BoschTrvThermostatCluster.AttributeDefs.operating_mode
    temperature_attr = BoschTrvThermostatCluster.AttributeDefs.eco_temperature
    control_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper
    system_attr = Thermostat.AttributeDefs.system_mode
    cluster._update_attribute(mode_attr.id, BoschOperatingMode.Pause)
    cluster._update_attribute(control_attr.id, ControlSequenceOfOperation.Heating_Only)
    cluster._update_attribute(system_attr.id, Thermostat.SystemMode.Off)

    with mock.patch.object(
        Thermostat,
        "write_attributes",
        mock.AsyncMock(
            return_value=[
                [
                    WriteAttributesStatusRecord(
                        foundation.Status.SUCCESS, temperature_attr.id
                    )
                ]
            ]
        ),
    ):
        await cluster.write_attributes(
            {mode_attr.name: BoschOperatingMode.Eco, temperature_attr.name: 1800}
        )

    assert cluster.get(mode_attr.name) == BoschOperatingMode.Pause
    assert cluster.get(system_attr.name) == Thermostat.SystemMode.Off


@pytest.mark.parametrize(
    ("write_mode", "missing_attribute"),
    [
        (True, Thermostat.AttributeDefs.ctrl_sequence_of_oper),
        (False, BoschTrvThermostatCluster.AttributeDefs.operating_mode),
    ],
)
async def test_bosch_system_mode_not_guessed_when_required_read_fails(
    zigpy_device_from_v2_quirk, caplog, write_mode, missing_attribute
):
    """Keep the previous system mode when its other input cannot be read."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    mode_attr = BoschTrvThermostatCluster.AttributeDefs.operating_mode
    control_attr = Thermostat.AttributeDefs.ctrl_sequence_of_oper
    system_attr = Thermostat.AttributeDefs.system_mode
    cluster._update_attribute(system_attr.id, Thermostat.SystemMode.Off)
    if write_mode:
        attributes = {mode_attr.name: BoschOperatingMode.Eco}
    else:
        attributes = {control_attr.name: ControlSequenceOfOperation.Cooling_Only}
    read_mock = mock.AsyncMock(
        return_value=(
            [
                foundation.ReadAttributeRecord(
                    missing_attribute.id, foundation.Status.UNSUPPORTED_ATTRIBUTE
                )
            ],
        )
    )

    with (
        mock.patch.object(cluster, "_read_attributes", read_mock),
        mock.patch.object(cluster, "_write_attributes", _mock_bosch_write_statuses({})),
    ):
        result = await cluster.write_attributes(attributes)

    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster.get(system_attr.name) == Thermostat.SystemMode.Off
    read_mock.assert_awaited_once()
    assert "Cannot synchronize system mode" in caplog.text


@pytest.mark.parametrize("from_cache", [False, True])
@pytest.mark.parametrize("cached_reason", [None, BoschRestartReason.cold_start])
async def test_bosch_restart_reason_requests_fresh_initialization(
    zigpy_device_from_v2_quirk, from_cache, cached_reason
):
    """Read fresh during network initialization, but honor cache-only restore."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    entry = DEVICE_REGISTRY.match_entry(device)
    (metadata,) = (
        entity
        for entity in entry.zha_device_factory.quirk_definition.entity_metadata
        if entity.translation_key == "restart_reason"
    )
    cluster = device.endpoints[1].thermostat
    reason_attr = BoschTrvThermostatCluster.AttributeDefs.restart_reason
    if cached_reason is not None:
        cluster._update_attribute(reason_attr.id, cached_reason)
    endpoint = mock.Mock(id=1, zigpy_endpoint=device.endpoints[1])
    zha_device = mock.Mock(
        ieee=device.ieee,
        endpoints={1: endpoint},
        quirk_metadata=mock.Mock(entity_metadata=(metadata,)),
    )
    (entity,) = discover_quirks_v2_entities(zha_device)
    configs = aggregate_cluster_configs([entity])
    read_mock = mock.AsyncMock(
        return_value=(
            [
                foundation.ReadAttributeRecord(
                    reason_attr.id,
                    foundation.Status.SUCCESS,
                    foundation.TypeValue(None, BoschRestartReason.firmware_installed),
                )
            ],
        )
    )

    with mock.patch.object(cluster, "_read_attributes", read_mock):
        await initialize_cluster_configs(configs, from_cache=from_cache)

    assert metadata.reporting_config is None
    assert entity.entity_registry_enabled_default is False
    if from_cache:
        read_mock.assert_not_awaited()
        assert cluster.get(reason_attr.name) == cached_reason
    else:
        read_mock.assert_awaited_once()
        assert read_mock.await_args.kwargs["manufacturer"] == 0x1209
        assert cluster.get(reason_attr.name) == BoschRestartReason.firmware_installed


def test_bosch_radiator_thermostat_II_manufacturer_attribute_definitions():
    """Keep manufacturer codes and wire types on Bosch private attributes."""
    thermostat_attributes = BoschTrvThermostatCluster.AttributeDefs
    ui_attributes = BoschUserInterfaceCluster.AttributeDefs

    for attribute in (
        thermostat_attributes.operating_mode,
        thermostat_attributes.remote_temperature,
        thermostat_attributes.eco_temperature,
        thermostat_attributes.anti_freeze_enabled,
        thermostat_attributes.error_state,
        thermostat_attributes.restart_reason,
        ui_attributes.light_ring_on_temperature_change,
    ):
        assert attribute.manufacturer_code == 0x1209

    assert thermostat_attributes.remote_temperature.id == 0x4040
    assert thermostat_attributes.remote_temperature.type is t.int16s
    assert thermostat_attributes.eco_temperature.id == 0x4008
    assert thermostat_attributes.eco_temperature.type is t.uint16_t
    assert thermostat_attributes.error_state.id == 0x5000
    assert thermostat_attributes.error_state.type is t.bitmap8
    assert thermostat_attributes.restart_reason.id == 0x5010
    assert (
        thermostat_attributes.restart_reason.access
        == foundation.ZCLAttributeAccess.Read
    )
    assert [thermostat_attributes.restart_reason.type(v).name for v in (0, 1, 2)] == [
        "cold_start",
        "warm_start",
        "firmware_installed",
    ]
    assert ui_attributes.light_ring_on_temperature_change.id == 0x4031


def test_bosch_window_open_temperature_is_celsius(zigpy_device_from_v2_quirk):
    """Expose the window-open temperature as a Celsius temperature number."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    entry = DEVICE_REGISTRY.match_entry(device)
    (metadata,) = (
        entity
        for entity in entry.zha_device_factory.quirk_definition.entity_metadata
        if entity.translation_key == "window_open_temperature"
    )

    assert metadata.device_class == NumberDeviceClass.TEMPERATURE
    assert metadata.unit == UnitOfTemperature.CELSIUS


async def test_bosch_radiator_thermostat_II_unmapped_modes(
    zigpy_device_from_v2_quirk,
):
    """Reject unmapped system modes and unknown operating modes without guessing."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    cluster._update_attribute(
        Thermostat.AttributeDefs.system_mode.id, Thermostat.SystemMode.Heat
    )

    write_mock = mock.AsyncMock()
    with mock.patch.object(cluster, "_write_attributes", write_mock):
        result = await cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Dry}
        )
    assert result[0][0].status == foundation.Status.INVALID_VALUE
    assert result[0][0].attrid == Thermostat.AttributeDefs.system_mode.id
    assert not write_mock.await_count
    assert cluster.get("system_mode") == Thermostat.SystemMode.Heat

    def mock_read(attributes, manufacturer=None):
        return (
            [
                foundation.ReadAttributeRecord(
                    attr,
                    foundation.Status.SUCCESS,
                    foundation.TypeValue(None, 0x06),
                )
                for attr in attributes
            ],
        )

    with mock.patch.object(
        cluster, "_read_attributes", mock.AsyncMock(side_effect=mock_read)
    ):
        success, fail = await cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.id]
        )
    assert Thermostat.AttributeDefs.system_mode.id not in success
    assert fail[Thermostat.AttributeDefs.system_mode.id] == (
        foundation.Status.INVALID_VALUE
    )
    assert cluster.get("system_mode") == Thermostat.SystemMode.Heat


@pytest.mark.parametrize(
    ("valve_status", "device_status", "error"),
    [
        (BoschValveAdaptStatus.ReadyToCalibrate, foundation.Status.SUCCESS, None),
        (BoschValveAdaptStatus.Success, None, "valve status is Success"),
        (BoschValveAdaptStatus.FixMotorFailed, None, "valve status is FixMotorFailed"),
        (None, None, "valve status could not be read"),
        (
            BoschValveAdaptStatus.ReadyToCalibrate,
            foundation.Status.FAILURE,
            "rejected by device: FAILURE",
        ),
    ],
)
async def test_bosch_radiator_thermostat_II_calibrate_valve(
    zigpy_device_from_v2_quirk, valve_status, device_status, error
):
    """Only send valve calibration when the device reports it is ready."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    valve_status_attr = BoschTrvThermostatCluster.AttributeDefs.valve_adapt_status
    # A stale cached value must not allow calibration.
    cluster._update_attribute(
        valve_status_attr.id, BoschValveAdaptStatus.ReadyToCalibrate
    )

    def mock_read(attributes, manufacturer=None):
        assert attributes == [valve_status_attr.id]
        assert manufacturer == 0x1209
        if valve_status is None:
            record = foundation.ReadAttributeRecord(
                valve_status_attr.id, foundation.Status.UNSUPPORTED_ATTRIBUTE
            )
        else:
            record = foundation.ReadAttributeRecord(
                valve_status_attr.id,
                foundation.Status.SUCCESS,
                foundation.TypeValue(None, valve_status),
            )
        return ([record],)

    read_mock = mock.AsyncMock(side_effect=mock_read)
    request_mock = mock.AsyncMock(
        return_value=foundation.GENERAL_COMMANDS[
            foundation.GeneralCommand.Default_Response
        ].schema(command_id=0x41, status=device_status)
    )
    with (
        mock.patch.object(cluster, "_read_attributes", read_mock),
        mock.patch.object(cluster, "request", request_mock),
    ):
        if error is None:
            await cluster.calibrate_valve()
        else:
            with pytest.raises(ZigbeeException, match=error):
                await cluster.calibrate_valve()

    read_mock.assert_awaited_once()
    if device_status is None:
        request_mock.assert_not_awaited()
    else:
        request_mock.assert_awaited_once()
        assert request_mock.await_args.args[1] == 0x41
        assert request_mock.await_args.kwargs["manufacturer"] == 0x1209


async def test_bosch_radiator_thermostat_II_other_commands_not_guarded(
    zigpy_device_from_v2_quirk,
):
    """Do not read valve status for unrelated thermostat commands."""
    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV1-ZB-EU")
    cluster = device.endpoints[1].thermostat
    read_mock = mock.AsyncMock()
    request_mock = mock.AsyncMock()
    with (
        mock.patch.object(cluster, "_read_attributes", read_mock),
        mock.patch.object(cluster, "request", request_mock),
    ):
        await cluster.clear_weekly_schedule()

    read_mock.assert_not_awaited()
    request_mock.assert_awaited_once()


def test_bosch_valve_adapt_status_values():
    """Keep existing state names and add Bosch's fix-motor states."""
    assert [BoschValveAdaptStatus(v).name for v in range(8)] == [
        "Unknown",
        "ReadyToCalibrate",
        "CalibrationInProgress",
        "Error",
        "Success",
        "FixMotorStarted",
        "FixMotorFailed",
        "FixMotorSuccessful",
    ]
