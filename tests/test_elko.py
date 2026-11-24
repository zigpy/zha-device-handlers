"""Tests for Elko quirks."""

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat

import zhaquirks
from zhaquirks.elko.smart_super_thermostat import (
    ActiveSensor,
    ElkoSuperTRThermostat,
    ElkoSuperTRThermostatCluster,
)

zhaquirks.setup()


def _report(device, attrs: dict[int, foundation.TypeValue]) -> None:
    """Deliver an attribute report from the thermostat as received over the air."""
    hdr = foundation.ZCLHeader.general(
        tsn=0x10,
        command_id=foundation.GeneralCommand.Report_Attributes,
        manufacturer=None,
        direction=foundation.Direction.Server_to_Client,
    )
    payload = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema(
        attribute_reports=[
            foundation.Attribute(attrid=attrid, value=value)
            for attrid, value in attrs.items()
        ]
    )
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Thermostat.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(hdr.serialize() + payload.serialize()),
        )
    )


@pytest.mark.parametrize(
    "active_sensor, air, floor, expected",
    [
        (ActiveSensor.AIR, 2150, 1900, 2150),
        (ActiveSensor.FLOOR, 2150, 1900, 1900),
        (ActiveSensor.PROTECTION, 2150, 1900, 2150),
    ],
)
async def test_local_temperature_follows_active_sensor(
    zigpy_device_from_quirk, active_sensor, air, floor, expected
):
    """Local temperature reports are applied once the active sensor is known."""
    device = zigpy_device_from_quirk(ElkoSuperTRThermostat)
    cluster = device.endpoints[1].thermostat
    assert isinstance(cluster, ElkoSuperTRThermostatCluster)

    _report(
        device,
        {
            ElkoSuperTRThermostatCluster.AttributeDefs.active_sensor.id: (
                foundation.TypeValue(type=0x30, value=active_sensor)
            )
        },
    )
    _report(
        device,
        {
            ElkoSuperTRThermostatCluster.AttributeDefs.local_temperature.id: (
                foundation.TypeValue(type=0x29, value=t.int16s(air))
            ),
            ElkoSuperTRThermostatCluster.AttributeDefs.floor_sensor_temperature.id: (
                foundation.TypeValue(type=0x29, value=t.int16s(floor))
            ),
        },
    )

    assert cluster.get("local_temperature") == expected
