"""Tests for the Aqara Wall Outlet H2 UK (lumi.plug.aeu002)."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl.clusters.general import MultistateInput, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
)
from zhaquirks.xiaomi.aqara.plug_aeu002 import (
    AqaraH2UKElectricalMeasurement,
    AqaraH2UKManuCluster,
)

zhaquirks.setup()

ACTIVE_POWER = ElectricalMeasurement.AttributeDefs.active_power
AC_POWER_DIVISOR = ElectricalMeasurement.AttributeDefs.ac_power_divisor
AC_POWER_MULTIPLIER = ElectricalMeasurement.AttributeDefs.ac_power_multiplier
MULTI_CLICK = AqaraH2UKManuCluster.AttributeDefs.multi_click
PRESENT_VALUE = MultistateInput.AttributeDefs.present_value
ENDPOINTS = (1, 2, 3)
BUTTON_ENDPOINTS = (1, 2)


def test_power_scaling_pinned(zigpy_device_from_v2_quirk):
    """The divisor the device declares is overridden, the reported value is kept."""
    device = zigpy_device_from_v2_quirk(
        "Aqara", "lumi.plug.aeu002", endpoint_ids=list(ENDPOINTS)
    )

    for ep_id in ENDPOINTS:
        cluster = device.endpoints[ep_id].electrical_measurement
        assert isinstance(cluster, AqaraH2UKElectricalMeasurement)

        # what the device reports: watts, but a divisor of 10
        cluster.update_attribute(AC_POWER_MULTIPLIER.id, 1)
        cluster.update_attribute(AC_POWER_DIVISOR.id, 10)
        cluster.update_attribute(ACTIVE_POWER.id, 425)

        assert cluster.get(AC_POWER_MULTIPLIER.name) == 1
        assert cluster.get(AC_POWER_DIVISOR.name) == 1
        assert cluster.get(ACTIVE_POWER.name) == 425


@pytest.mark.parametrize(("ep_id", "button"), [(1, BUTTON_1), (2, BUTTON_2)])
@pytest.mark.parametrize(
    ("value", "press"),
    [(1, SHORT_PRESS), (2, DOUBLE_PRESS), (0, LONG_PRESS), (255, LONG_RELEASE)],
)
def test_button_events_match_triggers(
    zigpy_device_from_v2_quirk, ep_id, button, value, press
):
    """A press on a socket button fires the event its trigger listens for."""
    device = zigpy_device_from_v2_quirk(
        "Aqara", "lumi.plug.aeu002", endpoint_ids=list(ENDPOINTS)
    )
    cluster = device.endpoints[ep_id].multistate_input
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(PRESENT_VALUE.id, value)

    trigger = device.device_automation_triggers[(press, button)]
    assert listener.zha_send_event.call_args.args[0] == trigger[COMMAND]


async def test_zha_entities():
    """ZHA shows real watts and exposes the settings and switches per endpoint."""
    async with zha_gateway() as gateway:
        device = await join_device_from_diagnostics(
            gateway, "aqara-lumi-plug-aeu002.json", DEVICE_REGISTRY
        )
        ieee = device.ieee

        for ep_id in ENDPOINTS:
            device.get_platform_entity(
                Platform.SWITCH, unique_id=f"{ieee}-{ep_id}-{OnOff.cluster_id}"
            )
            power = device.get_platform_entity(
                Platform.SENSOR,
                unique_id=f"{ieee}-{ep_id}-{ElectricalMeasurement.cluster_id}",
            )
            device.device.endpoints[ep_id].electrical_measurement.update_attribute(
                ACTIVE_POWER.id, 425
            )
            assert power.native_value == 425

        device.get_platform_entity(
            Platform.SENSOR,
            unique_id=f"{ieee}-1-{Metering.cluster_id}-summation_delivered",
        )

        for ep_id in BUTTON_ENDPOINTS:
            device.get_platform_entity(
                Platform.SWITCH, unique_id=f"{ieee}-{ep_id}-child_lock"
            )
            multi_click = device.get_platform_entity(
                Platform.SWITCH, unique_id=f"{ieee}-{ep_id}-multi_click"
            )
            manu_cluster = device.device.endpoints[ep_id].opple_cluster
            manu_cluster.update_attribute(MULTI_CLICK.id, 1)
            assert multi_click.is_on is False
            manu_cluster.update_attribute(MULTI_CLICK.id, 2)
            assert multi_click.is_on is True

        device.get_platform_entity(Platform.SWITCH, unique_id=f"{ieee}-1-led_indicator")
        device.get_platform_entity(
            Platform.SWITCH, unique_id=f"{ieee}-1-flip_indicator_light"
        )
        device.get_platform_entity(
            Platform.NUMBER, unique_id=f"{ieee}-1-overload_protection"
        )
        device.get_platform_entity(
            Platform.SELECT, unique_id=f"{ieee}-1-power_on_state"
        )
