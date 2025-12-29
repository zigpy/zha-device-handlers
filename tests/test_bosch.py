"""Tests the Bosch quirks."""

import asyncio
import time
from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import ControlSequenceOfOperation, Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord

from tests.common import ZCL_IAS_MOTION_COMMAND, ClusterListener
import zhaquirks
from zhaquirks.bosch.rbsh_trv0_zb_eu import (
    BoschOperatingMode,
    BoschThermostatCluster as BoschTrvThermostatCluster,
)
from zhaquirks.bosch.rfdl_zb_ms import (
    BoschIasZone,
    BoschOccupancy,
    BoschRFDLZBMS,
    MOTION_TIMEOUT_S,
    STUCK_MOTION_THRESHOLD_S,
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


# =============================================================================
# Bosch RFDL-ZB-MS TriTech Motion Sensor Tests
# =============================================================================


def test_bosch_rfdl_zb_ms_signature(assert_signature_matches_quirk):
    """Test that the RFDL-ZB-MS device signature matches the quirk."""
    signature = {
        "node_descriptor": "NodeDescriptor(...)",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0402",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x0020",
                    "0x0400",
                    "0x0402",
                    "0x0500",
                    "0x0b05",
                ],
                "out_clusters": ["0x0019"],
            }
        },
        "manufacturer": "Bosch",
        "model": "RFDL-ZB-MS",
    }
    assert_signature_matches_quirk(BoschRFDLZBMS, signature)


def test_bosch_rfdl_zb_ms_device_has_motion_bus(zigpy_device_from_quirk):
    """Test that the RFDL-ZB-MS device has a motion bus."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    assert hasattr(device, "motion_bus")
    assert device.motion_bus is not None


def test_bosch_rfdl_zb_ms_replacement_clusters(zigpy_device_from_quirk):
    """Test that the RFDL-ZB-MS replacement clusters are present."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    ep = device.endpoints[1]

    # Check IAS Zone is our custom cluster
    assert isinstance(ep.ias_zone, BoschIasZone)

    # Check Occupancy cluster is present and is our custom cluster
    assert hasattr(ep, "occupancy")
    assert isinstance(ep.occupancy, BoschOccupancy)


async def test_bosch_rfdl_zb_ms_motion_event_sets_occupancy(zigpy_device_from_quirk):
    """Test that a motion event sets occupancy to 1."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # Initially unoccupied
    assert occupancy_cluster._attr_cache.get(0x0000, 0) == 0

    # Trigger motion event
    occupancy_cluster.motion_event()

    # Should be occupied now
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0] == (0x0000, 1)
    assert occupancy_cluster._occupied_since is not None


async def test_bosch_rfdl_zb_ms_motion_timeout_clears_occupancy(zigpy_device_from_quirk):
    """Test that occupancy clears after timeout."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # Patch the timeout to be very short for testing
    with mock.patch.object(
        zhaquirks.bosch.rfdl_zb_ms, "MOTION_TIMEOUT_S", 0.05
    ):
        # Trigger motion event
        occupancy_cluster.motion_event()

        assert len(occupancy_listener.attribute_updates) == 1
        assert occupancy_listener.attribute_updates[0] == (0x0000, 1)

        # Wait for timeout
        await asyncio.sleep(0.1)

        # Should be unoccupied now
        assert len(occupancy_listener.attribute_updates) == 2
        assert occupancy_listener.attribute_updates[1] == (0x0000, 0)
        assert occupancy_cluster._occupied_since is None
        assert occupancy_cluster._timer_handle is None


async def test_bosch_rfdl_zb_ms_clear_when_not_occupied_triggers_motion(
    zigpy_device_from_quirk,
):
    """Test that a clear event when not occupied is treated as motion (stuck sensor)."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # Ensure we're not occupied
    assert occupancy_cluster._occupied_since is None

    # Send clear event - should trigger motion
    occupancy_cluster.motion_clear()

    # Should be occupied now (treated as motion)
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0] == (0x0000, 1)
    assert occupancy_cluster._occupied_since is not None


async def test_bosch_rfdl_zb_ms_clear_after_threshold_triggers_motion(
    zigpy_device_from_quirk,
):
    """Test that a clear after STUCK_MOTION_THRESHOLD_S is treated as new motion."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # Trigger initial motion
    occupancy_cluster.motion_event()
    assert len(occupancy_listener.attribute_updates) == 1

    # Simulate time passing beyond threshold
    occupancy_cluster._occupied_since = time.monotonic() - STUCK_MOTION_THRESHOLD_S - 1

    # Send clear event - should trigger new motion
    occupancy_cluster.motion_clear()

    # Should have another occupancy update (reset timer)
    assert len(occupancy_listener.attribute_updates) == 2
    assert occupancy_listener.attribute_updates[1] == (0x0000, 1)


async def test_bosch_rfdl_zb_ms_clear_within_threshold_ignored(zigpy_device_from_quirk):
    """Test that a clear within STUCK_MOTION_THRESHOLD_S is ignored."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # Trigger initial motion
    occupancy_cluster.motion_event()
    assert len(occupancy_listener.attribute_updates) == 1

    # Clear arrives quickly (within threshold) - should be ignored
    occupancy_cluster.motion_clear()

    # No new updates - the clear was ignored
    assert len(occupancy_listener.attribute_updates) == 1


async def test_bosch_rfdl_zb_ms_multiple_motion_events_reset_timer(
    zigpy_device_from_quirk,
):
    """Test that multiple motion events reset the timer."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy

    with mock.patch.object(zhaquirks.bosch.rfdl_zb_ms, "MOTION_TIMEOUT_S", 0.1):
        # First motion event
        occupancy_cluster.motion_event()
        first_handle = occupancy_cluster._timer_handle

        await asyncio.sleep(0.05)

        # Second motion event should cancel and create new timer
        occupancy_cluster.motion_event()
        second_handle = occupancy_cluster._timer_handle

        # Timer handle should be different (new timer)
        assert first_handle is not second_handle

        # Wait a bit more but not full timeout from second event
        await asyncio.sleep(0.07)

        # Should still be occupied (timer was reset)
        assert occupancy_cluster._attr_cache.get(0x0000, 0) == 1

        # Wait for the full timeout from second event
        await asyncio.sleep(0.05)

        # Now should be unoccupied
        assert occupancy_cluster._attr_cache.get(0x0000, 0) == 0


async def test_bosch_rfdl_zb_ms_ias_zone_forwards_motion_to_bus(zigpy_device_from_quirk):
    """Test that IAS Zone cluster forwards motion events to the bus."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    ias_zone_cluster = device.endpoints[1].ias_zone
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # Send motion command via IAS Zone
    hdr, args = ias_zone_cluster.deserialize(ZCL_IAS_MOTION_COMMAND)
    ias_zone_cluster.handle_message(hdr, args)

    # Occupancy should be set
    assert len(occupancy_listener.attribute_updates) == 1
    assert occupancy_listener.attribute_updates[0] == (0x0000, 1)


async def test_bosch_rfdl_zb_ms_ias_zone_forwards_clear_to_bus(zigpy_device_from_quirk):
    """Test that IAS Zone cluster forwards clear events to the bus."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    ias_zone_cluster = device.endpoints[1].ias_zone
    occupancy_cluster = device.endpoints[1].occupancy
    occupancy_listener = ClusterListener(occupancy_cluster)

    # First trigger motion so we're occupied
    occupancy_cluster.motion_event()
    initial_updates = len(occupancy_listener.attribute_updates)

    # Simulate time passing beyond threshold so clear triggers new motion
    occupancy_cluster._occupied_since = time.monotonic() - STUCK_MOTION_THRESHOLD_S - 1

    # Create a clear command (zone status = 0, no alarm)
    # ZCL_IAS_MOTION_COMMAND has zone_status = 0x0001 (alarm1 set)
    # We need zone_status = 0x0000 (no alarm)
    clear_command = b"\t!\x00\x00\x00\x00\x00\x00\x00"

    hdr, args = ias_zone_cluster.deserialize(clear_command)
    ias_zone_cluster.handle_message(hdr, args)

    # Should have triggered motion_clear which treats as new motion
    assert len(occupancy_listener.attribute_updates) == initial_updates + 1


def test_bosch_rfdl_zb_ms_occupancy_pir_sensor_type(zigpy_device_from_quirk):
    """Test that occupancy cluster reports PIR sensor type."""
    device = zigpy_device_from_quirk(BoschRFDLZBMS)
    occupancy_cluster = device.endpoints[1].occupancy

    # Attribute 0x0010 is occupancy_sensor_type, should be 0 (PIR)
    assert occupancy_cluster._CONSTANT_ATTRIBUTES.get(0x0010) == 0
