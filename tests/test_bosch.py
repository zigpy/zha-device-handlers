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

async def test_bosch_radiator_thermostat_II_write_attributes(zigpy_device_from_v2_quirk):
    """Test the Radiator Thermostat II writes behaving correctly."""

    device = zigpy_device_from_v2_quirk(manufacturer="BOSCH", model="RBSH-TRV0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS)
            for _ in attributes
        ]
        return [records, []]

    # data is written to trv
    patch_bosch_trv_write = mock.patch.object(
        bosch_thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )

    # check that system_mode ends-up writing operating_mode:
    with patch_bosch_trv_write:
        # - Heating operation
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Heating_Only}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Heating_Only

        # -- Off
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Off
        assert bosch_thermostat_cluster._attr_cache[BoschTrvThermostatCluster.AttributeDefs.operating_mode.id] == BoschOperatingMode.Pause
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Heating_Only

        # -- Heat
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Heat}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Heat
        assert bosch_thermostat_cluster._attr_cache[
                       BoschTrvThermostatCluster.AttributeDefs.operating_mode.id] == BoschOperatingMode.Manual
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Heating_Only

        # - Cooling operation
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Cooling_Only}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Cooling_Only

        # -- Off
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Off
        assert bosch_thermostat_cluster._attr_cache[BoschTrvThermostatCluster.AttributeDefs.operating_mode.id] == BoschOperatingMode.Pause
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Cooling_Only

        # -- Cool
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Cool}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Cool
        assert bosch_thermostat_cluster._attr_cache[
                       BoschTrvThermostatCluster.AttributeDefs.operating_mode.id] == BoschOperatingMode.Manual
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Cooling_Only


async def test_bosch_room_thermostat_II_230v_write_attributes(zigpy_device_from_v2_quirk):
    """Test the Room Thermostat II 230v system_mode writes behaving correctly."""

    device = zigpy_device_from_v2_quirk(manufacturer="Bosch", model="RBSH-RTH0-ZB-EU")

    bosch_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS)
            for _ in attributes
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
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Heating_Only

        # -- Off
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Off
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Heating_Only

        # -- Heat
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Heat}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Heat
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Heating_Only

        # - Cooling operation
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"ctrl_sequence_of_oper": ControlSequenceOfOperation.Cooling_Only}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Cooling_Only

        # -- Off
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Off}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Off
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Cooling_Only

        # -- Cool
        success, fail = await bosch_thermostat_cluster.write_attributes(
            {"system_mode": Thermostat.SystemMode.Cool}
        )
        assert success
        assert not fail
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.system_mode.id] == Thermostat.SystemMode.Cool
        assert bosch_thermostat_cluster._attr_cache[
                   Thermostat.AttributeDefs.ctrl_sequence_of_oper.id] == ControlSequenceOfOperation.Cooling_Only
