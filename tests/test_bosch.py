"""Tests the Bosch thermostats quirk."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import ControlSequenceOfOperation, Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord

import zhaquirks
from zhaquirks.bosch.rbsh_trv0_zb_eu import (
    BoschOperatingMode,
    BoschThermostatCluster as BoschTrvThermostatCluster,
)

zhaquirks.setup()


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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Heating_Only}
        )
        assert success
        assert not fail
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # - Heating operation - by id
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: ControlSequenceOfOperation.Heating_Only
            }
        )
        assert success
        assert not fail
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Off (by-name)
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Heat}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Heat}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id: BoschOperatingMode.Pause
            }
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.name: BoschOperatingMode.Manual
            }
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Cooling_Only}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Cool}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Cool}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id: BoschOperatingMode.Manual,
            }
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {
                Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Off,
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.id: BoschOperatingMode.Manual,
            }
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {
                Thermostat.AttributeDefs.system_mode.id: Thermostat.SystemMode.Cool,
                BoschTrvThermostatCluster.AttributeDefs.operating_mode.name: BoschOperatingMode.Pause,
            }
        )
        assert success
        assert not fail
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
        assert success
        assert not fail
        assert Thermostat.SystemMode.Off in success.values()

        # - system_mode by id along other attributes
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [
                Thermostat.AttributeDefs.system_mode.id,
                Thermostat.AttributeDefs.pi_heating_demand.id,
            ]
        )
        assert success
        assert not fail
        assert Thermostat.SystemMode.Off in success.values()

        # - system_mode by name
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.name]
        )
        assert success
        assert not fail
        assert Thermostat.SystemMode.Off in success.values()

        # - system_mode by name along other attributes
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [
                Thermostat.AttributeDefs.system_mode.name,
                Thermostat.AttributeDefs.pi_heating_demand.name,
            ]
        )
        assert success
        assert not fail
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
        assert success
        assert not fail
        assert Thermostat.SystemMode.Heat in success.values()

        # - system_mode by name
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.name]
        )
        assert success
        assert not fail
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
        assert success
        assert not fail
        assert Thermostat.SystemMode.Cool in success.values()

        # - system_mode by name
        success, fail = await bosch_thermostat_cluster.read_attributes(
            [Thermostat.AttributeDefs.system_mode.name]
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Heating_Only}
        )
        assert success
        assert not fail
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Heating_Only
        )

        # -- Off
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Heat}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Cooling_Only}
        )
        assert success
        assert not fail
        assert (
            bosch_thermostat_cluster._attr_cache[
                Thermostat.AttributeDefs.ctrl_sequence_of_oper.id
            ]
            == ControlSequenceOfOperation.Cooling_Only
        )

        # -- Off
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
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
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {Thermostat.AttributeDefs.system_mode.name: Thermostat.SystemMode.Cool}
        )
        assert success
        assert not fail
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
