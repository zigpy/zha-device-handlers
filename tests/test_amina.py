"""Tests for amina distribution AS devices."""

import asyncio
from unittest import mock

import pytest
from zha.application import Platform
from zha.application.platforms import EntityCategory
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.amina.amina_s import (
    AMINA_ENDPOINT_ID,
    AMINA_MANUFACTURER_CODE,
    Alarms,
    AminaControlCluster,
    EVStatus,
    ev_status_text,
)

zhaquirks.setup()

AMINA_S_DIAGNOSTICS = "amina-distribution-as-amina-s-0x01220000.json"
AMINA_S_IEEE = "ab:cd:ef:12:34:56:78:90"


@pytest.fixture
def amina_cluster(zigpy_device_from_v2_quirk) -> AminaControlCluster:
    """Return the quirked amina control cluster."""
    device = zigpy_device_from_v2_quirk(
        "amina distribution AS",
        "amina S",
        cluster_ids={
            AMINA_ENDPOINT_ID: {AminaControlCluster.cluster_id: ClusterType.Server}
        },
    )
    return device.endpoints[AMINA_ENDPOINT_ID].amina_control


def test_amina_s_quirk_applied(amina_cluster):
    """Test that the quirk replaces the control cluster."""
    assert isinstance(amina_cluster, AminaControlCluster)


async def test_amina_s_manufacturer_code(amina_cluster):
    """Test that requests use the amina manufacturer code, not the reported one."""
    attr_defs = AminaControlCluster.AttributeDefs

    with mock.patch("zigpy.device.Device.request", mock.AsyncMock()) as request_mock:
        # not a valid response, but only the outgoing request matters here
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        await amina_cluster.read_attributes([attr_defs.total_active_energy.id])
        await amina_cluster.configure_reporting(attr_defs.ev_status.id, 0, 300, 1)

    assert request_mock.call_count == 2

    for call in request_mock.call_args_list:
        assert call[1]["cluster"] == AminaControlCluster.cluster_id
        zcl_header, _ = foundation.ZCLHeader.deserialize(call[1]["data"])
        assert zcl_header.frame_control.is_manufacturer_specific
        # the mock device reports 1234, the cluster must send 0x143B
        assert zcl_header.manufacturer == AMINA_MANUFACTURER_CODE


async def test_amina_s_parses_device_report(amina_cluster):
    """Test that a report captured from a real device is decoded."""
    # ev_status report sent by the device with manufacturer code 0x143B
    data = bytes.fromhex("0c3b14340a0300190100")
    hdr, args = amina_cluster.deserialize(data)
    assert hdr.manufacturer == AMINA_MANUFACTURER_CODE

    with mock.patch.object(amina_cluster, "read_attributes", mock.AsyncMock()):
        amina_cluster.handle_message(hdr, args)

    assert (
        amina_cluster.get(AminaControlCluster.AttributeDefs.ev_status.id)
        == EVStatus.EV_connected
    )


async def test_amina_s_reads_energy_on_ev_status_change(amina_cluster):
    """Test that the energy counters are read when the EV status changes."""
    attr_defs = AminaControlCluster.AttributeDefs
    energy_attrs = [attr_defs.total_active_energy.id, attr_defs.last_session_energy.id]

    with mock.patch.object(
        amina_cluster, "read_attributes", mock.AsyncMock()
    ) as read_mock:
        # car plugged in
        amina_cluster.update_attribute(attr_defs.ev_status.id, EVStatus.EV_connected)
        await asyncio.sleep(0)
        read_mock.assert_called_once_with(energy_attrs, allow_cache=False)
        read_mock.reset_mock()

        # unchanged status, e.g. a periodic report
        amina_cluster.update_attribute(attr_defs.ev_status.id, EVStatus.EV_connected)
        await asyncio.sleep(0)
        read_mock.assert_not_called()

        # other attributes do not trigger a read
        amina_cluster.update_attribute(attr_defs.alarms.id, Alarms(0))
        await asyncio.sleep(0)
        read_mock.assert_not_called()

        # charging starts
        amina_cluster.update_attribute(
            attr_defs.ev_status.id, EVStatus.EV_connected | EVStatus.Charging
        )
        await asyncio.sleep(0)
        read_mock.assert_called_once_with(energy_attrs, allow_cache=False)


@pytest.mark.parametrize(
    ("ev_status", "expected"),
    [
        (EVStatus(0), "Not connected"),
        (EVStatus.Charging, "Not connected"),
        (EVStatus.EV_connected, "Connected"),
        (EVStatus.EV_connected | EVStatus.Ready_to_charge, "Ready to charge"),
        (
            EVStatus.EV_connected | EVStatus.Ready_to_charge | EVStatus.Charging,
            "Charging",
        ),
        (EVStatus.EV_connected | EVStatus.Charging | EVStatus.Derated, "Charging"),
        (EVStatus.EV_connected | EVStatus.Charging_paused, "Charging paused"),
    ],
)
def test_ev_status_text(ev_status, expected):
    """Test the EV status text converter."""
    assert ev_status_text(ev_status) == expected
    assert ev_status_text(int(ev_status)) == expected


async def test_amina_s_entities():
    """Test entity creation and state from device diagnostics."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, AMINA_S_DIAGNOSTICS, DEVICE_REGISTRY
        )

        def entity(platform: Platform, suffix: str):
            return device.get_platform_entity(
                platform, unique_id=f"{AMINA_S_IEEE}-{AMINA_ENDPOINT_ID}-{suffix}"
            )

        ev_connected = entity(Platform.BINARY_SENSOR, "ev_connected")
        ev_charging = entity(Platform.BINARY_SENSOR, "ev_charging")
        derated = entity(Platform.BINARY_SENSOR, "derated")
        alarm_active = entity(Platform.BINARY_SENSOR, "alarm_active")
        ev_status = entity(Platform.SENSOR, "ev_status_text")
        alarm_code = entity(Platform.SENSOR, "alarm_bits")
        total_energy = entity(Platform.SENSOR, "total_active_energy")
        session_energy = entity(Platform.SENSOR, "last_session_energy")

        def binary_states() -> dict[str, bool]:
            return {
                "ev_connected": ev_connected.is_on,
                "ev_charging": ev_charging.is_on,
                "derated": derated.is_on,
                "alarm_active": alarm_active.is_on,
            }

        # values from the diagnostics: car connected, not charging, no alarms
        assert binary_states() == {
            "ev_connected": True,
            "ev_charging": False,
            "derated": False,
            "alarm_active": False,
        }
        assert ev_status.native_value == "Connected"
        assert alarm_code.native_value == 0
        assert total_energy.native_value == 88.098
        assert session_energy.native_value == 2.549

        assert derated.entity_category == EntityCategory.DIAGNOSTIC
        assert alarm_active.entity_category == EntityCategory.DIAGNOSTIC
        assert alarm_code.entity_category == EntityCategory.DIAGNOSTIC

        cluster = device.device.endpoints[AMINA_ENDPOINT_ID].amina_control
        attr_defs = AminaControlCluster.AttributeDefs

        with mock.patch.object(cluster, "read_attributes", mock.AsyncMock()):
            cluster.update_attribute(
                attr_defs.ev_status.id,
                EVStatus.EV_connected | EVStatus.Charging | EVStatus.Derated,
            )
            cluster.update_attribute(attr_defs.alarms.id, Alarms.High_temperature)
            await asyncio.sleep(0)

        assert binary_states() == {
            "ev_connected": True,
            "ev_charging": True,
            "derated": True,
            "alarm_active": True,
        }
        assert ev_status.native_value == "Charging"
        assert alarm_code.native_value == Alarms.High_temperature

        cluster.update_attribute(attr_defs.total_active_energy.id, 91234)
        assert total_energy.native_value == 91.234
