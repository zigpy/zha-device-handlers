"""Tests for the Bosch BSD-2 smoke alarm quirk."""

from unittest import mock

import pytest
from zha.quirks import QUIRK_REGISTRY_ENTRY_ATTR
from zigpy.exceptions import DeliveryError, ZigbeeException
from zigpy.profiles import zha
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.security import (
    IasWd,
    IasZone,
    SirenLevel,
    Strobe,
    StrobeLevel,
    WarningMode,
    WarningType,
)

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.bosch import rbsh_sd_zb_eu as bsd2
from zhaquirks.bosch.rbsh_sd_zb_eu import (
    ATTR_BROADCAST_ALARMS,
    ATTR_TEST_MODE,
    ATTR_TEST_MODE_TIMEOUT,
    BURGLAR_SIREN_ENDPOINT,
    SMOKE_SIREN_ENDPOINT,
    BoschAlarmMode,
    BoschBurglarSiren,
    BoschSmokeAlarmIasZone,
    BoschSmokeSiren,
)

zhaquirks.setup()

ZONE_STATUS = IasZone.AttributeDefs.zone_status.id
SENSITIVITY = IasZone.AttributeDefs.current_zone_sensitivity_level.name

OK = mock.Mock(status=foundation.Status.SUCCESS)
FAILED = mock.Mock(status=foundation.Status.FAILURE)

# Broadcast frames of Bosch's alarm_control command: manufacturer specific cluster
# command (frame control 0x15, no default response), manufacturer code 0x1209, the
# transaction sequence number 0x42, command 0x80, alarm mode and timeout
BROADCAST_SMOKE_240 = bytes.fromhex("150912428000f0")
BROADCAST_BURGLAR_STOP = bytes.fromhex("15091242800100")


def make_device(zigpy_device_from_v2_quirk, manufacturer="Bosch"):
    """Create a BSD-2 as it pairs, with only the IAS Zone cluster."""
    return zigpy_device_from_v2_quirk(
        manufacturer,
        "RBSH-SD-ZB-EU",
        endpoint_ids=[1],
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )


def quirk_definition(device):
    """Return the v2 quirk definition that was applied to a device."""
    entry = getattr(device, QUIRK_REGISTRY_ENTRY_ATTR)
    return entry.zha_device_factory.quirk_definition


def warning(mode=WarningMode.Burglar):
    """Create the warning that ZHA's basic siren sends."""
    warning = WarningType()
    warning.mode = mode
    warning.strobe = Strobe.No_strobe
    warning.level = SirenLevel.High_level_sound
    return warning


async def turn_on(siren, duration=5):
    """Turn a siren on like ZHA's basic siren does."""
    await siren.start_warning(
        warning=warning(),
        warning_duration=duration,
        strobe_duty_cycle=0,
        stobe_level=StrobeLevel.High_level_strobe,
    )


async def turn_off(siren):
    """Turn a siren off like ZHA's siren does."""
    await siren.start_warning(
        warning=warning(WarningMode.Stop),
        warning_duration=5,
        strobe_duty_cycle=0,
        stobe_level=StrobeLevel.High_level_strobe,
    )


async def write(cluster, attr_id, value):
    """Write a local attribute and return the status of the write."""
    result = await cluster.write_attributes({attr_id: value})
    return result[0][0].status


@pytest.fixture
def device(zigpy_device_from_v2_quirk):
    """Create a BSD-2 with its commands and the broadcast mocked."""
    device = make_device(zigpy_device_from_v2_quirk)
    zone = device.endpoints[1].ias_zone

    zone.alarm_control = mock.AsyncMock(return_value=OK)
    zone.init_test_mode = mock.AsyncMock(return_value=OK)
    zone.init_normal_op_mode = mock.AsyncMock(return_value=OK)
    device.application.broadcast = mock.AsyncMock(
        return_value=(foundation.Status.SUCCESS, "ok")
    )
    device.application.get_sequence = mock.Mock(return_value=0x42)

    with mock.patch.object(bsd2, "BROADCAST_REPEAT_DELAY", 0):
        yield device


@pytest.fixture
def zone(device):
    """Return the IAS Zone cluster."""
    return device.endpoints[1].ias_zone


@pytest.fixture
def smoke_siren(device):
    """Return the IAS WD cluster behind the smoke siren."""
    return device.endpoints[SMOKE_SIREN_ENDPOINT].ias_wd


@pytest.fixture
def burglar_siren(device):
    """Return the IAS WD cluster behind the burglar siren."""
    return device.endpoints[BURGLAR_SIREN_ENDPOINT].ias_wd


@pytest.mark.parametrize("manufacturer", ["Bosch", "BOSCH"])
def test_quirk_applies_to_both_manufacturer_strings(
    zigpy_device_from_v2_quirk, manufacturer
):
    """Test that the quirk applies to the device under both manufacturer strings."""
    device = make_device(zigpy_device_from_v2_quirk, manufacturer)

    assert isinstance(device.endpoints[1].ias_zone, BoschSmokeAlarmIasZone)
    assert isinstance(device.endpoints[SMOKE_SIREN_ENDPOINT].ias_wd, BoschSmokeSiren)
    assert isinstance(
        device.endpoints[BURGLAR_SIREN_ENDPOINT].ias_wd, BoschBurglarSiren
    )


def test_siren_endpoints(zigpy_device_from_v2_quirk):
    """Test that the sirens are added as warning devices next to the real endpoint."""
    device = make_device(zigpy_device_from_v2_quirk)

    assert set(device.endpoints) == {0, 1, SMOKE_SIREN_ENDPOINT, BURGLAR_SIREN_ENDPOINT}
    assert IasWd.cluster_id not in device.endpoints[1].in_clusters

    for endpoint_id in (SMOKE_SIREN_ENDPOINT, BURGLAR_SIREN_ENDPOINT):
        endpoint = device.endpoints[endpoint_id]
        assert endpoint.profile_id == zha.PROFILE_ID
        assert endpoint.device_type == zha.DeviceType.IAS_WARNING_DEVICE
        assert set(endpoint.in_clusters) == {IasWd.cluster_id}


def test_entities(zigpy_device_from_v2_quirk):
    """Test the entities of the quirk, the siren names and the device name."""
    definition = quirk_definition(make_device(zigpy_device_from_v2_quirk))

    assert {
        entity.fallback_name: (entity.entity_platform.name, entity.entity_type.name)
        for entity in definition.entity_metadata
    } == {
        "Linkage alarm": ("SWITCH", "CONFIG"),
        "Test mode": ("SWITCH", "CONFIG"),
        "Test mode timeout": ("NUMBER", "CONFIG"),
        "Manual smoke alarm": ("BINARY_SENSOR", "DIAGNOSTIC"),
        "Manual burglar alarm": ("BINARY_SENSOR", "DIAGNOSTIC"),
        "Smoke alarm silenced": ("BINARY_SENSOR", "DIAGNOSTIC"),
    }

    assert {
        change.endpoint_id: (
            change.new_fallback_name,
            change.new_primary,
            change.new_entity_category.name,
        )
        for change in definition.changed_entity_metadata
    } == {
        SMOKE_SIREN_ENDPOINT: ("Smoke siren", False, "CONFIG"),
        BURGLAR_SIREN_ENDPOINT: ("Burglar siren", False, "CONFIG"),
    }
    assert [feature.feature for feature in definition.exposes_features] == [
        "siren_basic"
    ]
    assert definition.friendly_name.model == "BSD-2"
    assert definition.friendly_name.manufacturer == "Bosch"


@pytest.mark.parametrize(
    ("bit", "name"),
    [
        (1, "Manual smoke alarm"),
        (7, "Manual burglar alarm"),
        (11, "Smoke alarm silenced"),
    ],
)
def test_zone_status_bit_converters(zigpy_device_from_v2_quirk, bit, name):
    """Test that each binary sensor reads its own bit of the zone status."""
    definition = quirk_definition(make_device(zigpy_device_from_v2_quirk))
    sensor = next(
        entity for entity in definition.entity_metadata if entity.fallback_name == name
    )

    assert sensor.attribute_name == IasZone.AttributeDefs.zone_status.name
    assert sensor.attribute_converter(1 << bit) is True
    assert sensor.attribute_converter(0xFFF & ~(1 << bit)) is False


def test_defaults(zone):
    """Test the values of the settings before they are changed."""
    assert bool(zone.get(ATTR_BROADCAST_ALARMS)) is True
    assert bool(zone.get(ATTR_TEST_MODE)) is False
    assert zone.get(ATTR_TEST_MODE_TIMEOUT) == 5


@pytest.mark.parametrize(
    ("status", "test_mode"),
    [
        (0b0000_0000_0000, False),
        (0b0100_0000_0000, True),
        (0b0100_0000_0001, True),
        (0b1001_1011_0010, False),
    ],
)
def test_zone_status_drives_test_mode(zone, status, test_mode):
    """Test that the test mode follows bit 10 of the zone status."""
    zone.update_attribute(ZONE_STATUS, status)

    assert bool(zone.get(ATTR_TEST_MODE)) is test_mode
    assert zone.get(ZONE_STATUS) == status


def test_zone_status_update_variants(zone):
    """Test a zone status given as attribute definition or without a value."""
    zone._update_attribute(IasZone.AttributeDefs.zone_status, 1 << 10)
    assert bool(zone.get(ATTR_TEST_MODE)) is True

    zone._update_attribute(ZONE_STATUS, None)
    assert bool(zone.get(ATTR_TEST_MODE)) is True


def test_zone_status_notifies_listeners(zone):
    """Test that a changed test mode is announced, so the switch follows it."""
    listener = ClusterListener(zone)

    zone.update_attribute(ZONE_STATUS, 1 << 10)

    assert (ATTR_TEST_MODE, True) in listener.attribute_updates


async def test_smoke_siren_unicast(device, zone, smoke_siren):
    """Test that the smoke siren sounds the smoke alarm on this device."""
    await write(zone, ATTR_BROADCAST_ALARMS, False)

    await turn_on(smoke_siren, duration=30)
    zone.alarm_control.assert_awaited_once_with(
        alarm_mode=BoschAlarmMode.Smoke, alarm_timeout=30, manufacturer=0x1209
    )
    device.application.broadcast.assert_not_awaited()

    zone.alarm_control.reset_mock()
    await turn_off(smoke_siren)
    zone.alarm_control.assert_awaited_once_with(
        alarm_mode=BoschAlarmMode.Smoke, alarm_timeout=0, manufacturer=0x1209
    )


async def test_burglar_siren_unicast(zone, burglar_siren):
    """Test that the burglar siren sounds the burglar alarm, whatever the tone."""
    await write(zone, ATTR_BROADCAST_ALARMS, False)

    await burglar_siren.start_warning(
        warning=warning(WarningMode.Fire),
        warning_duration=10,
        strobe_duty_cycle=0,
        stobe_level=StrobeLevel.High_level_strobe,
    )
    zone.alarm_control.assert_awaited_once_with(
        alarm_mode=BoschAlarmMode.Burglar, alarm_timeout=10, manufacturer=0x1209
    )

    zone.alarm_control.reset_mock()
    await turn_off(burglar_siren)
    zone.alarm_control.assert_awaited_once_with(
        alarm_mode=BoschAlarmMode.Burglar, alarm_timeout=0, manufacturer=0x1209
    )


@pytest.mark.parametrize(
    ("duration", "timeout"), [(1, 1), (240, 240), (1000, 240), (0, 1)]
)
async def test_alarm_duration_is_limited(zone, smoke_siren, duration, timeout):
    """Test that the alarm lasts between 1 and 240 seconds."""
    await write(zone, ATTR_BROADCAST_ALARMS, False)

    await turn_on(smoke_siren, duration=duration)

    assert zone.alarm_control.await_args.kwargs["alarm_timeout"] == timeout


async def test_refused_alarm_raises(zone, smoke_siren):
    """Test that a refused command raises, since ZHA marks the siren on after it."""
    await write(zone, ATTR_BROADCAST_ALARMS, False)
    zone.alarm_control.return_value = FAILED

    with pytest.raises(ZigbeeException):
        await turn_on(smoke_siren)


async def test_unicast_alarm_wire_format(zone):
    """Test the alarm_control command as it goes over the air."""
    del zone.alarm_control
    zone.endpoint.request = mock.AsyncMock(
        return_value=(foundation.Status.SUCCESS, "ok")
    )

    await zone.alarm_control(
        alarm_mode=BoschAlarmMode.Burglar, alarm_timeout=240, manufacturer=0x1209
    )

    request = zone.endpoint.request.await_args.kwargs
    assert request["cluster"] == IasZone.cluster_id
    # Frame control with a default response, manufacturer code, sequence number,
    # command 0x80, burglar mode, timeout 240
    data = request["data"]
    assert data[:3] == bytes.fromhex("050912")
    assert data[4:] == bytes.fromhex("8001f0")


async def test_broadcast_is_sent_twice(device, smoke_siren):
    """Test that the alarm is broadcast to every device, twice."""
    await turn_on(smoke_siren, duration=240)
    await wait_for_zigpy_tasks()

    device.endpoints[1].ias_zone.alarm_control.assert_not_awaited()
    assert device.application.broadcast.await_count == 2
    for call in device.application.broadcast.await_args_list:
        assert call.kwargs["profile"] == zha.PROFILE_ID
        assert call.kwargs["cluster"] == IasZone.cluster_id
        assert call.kwargs["dst_ep"] == 0xFF
        assert call.kwargs["broadcast_address"] == 0xFFFF
        assert call.kwargs["data"] == BROADCAST_SMOKE_240


async def test_broadcast_stop(device, burglar_siren):
    """Test that stopping a broadcast alarm sends timeout 0."""
    await turn_off(burglar_siren)
    await wait_for_zigpy_tasks()

    assert device.application.broadcast.await_count == 2
    assert device.application.broadcast.await_args.kwargs["data"] == (
        BROADCAST_BURGLAR_STOP
    )


async def test_broadcast_failure_raises(device, smoke_siren):
    """Test that a failed broadcast raises and sends no repeat."""
    device.application.broadcast.side_effect = DeliveryError("no route")

    with pytest.raises(ZigbeeException):
        await turn_on(smoke_siren)
    await wait_for_zigpy_tasks()

    assert device.application.broadcast.await_count == 1


async def test_failing_broadcast_repeat_is_logged(device, smoke_siren, caplog):
    """Test that a failing second broadcast is only logged."""
    device.application.broadcast.side_effect = [
        (foundation.Status.SUCCESS, "ok"),
        DeliveryError("no route"),
    ]

    await turn_on(smoke_siren)
    await wait_for_zigpy_tasks()

    assert "Repeating the alarm broadcast failed" in caplog.text


async def test_squawk_is_not_supported(smoke_siren):
    """Test that the device cannot squawk."""
    with pytest.raises(ZigbeeException):
        await smoke_siren.squawk(squawk=None)


async def test_siren_cluster_is_local(zone, smoke_siren):
    """Test that the added IAS WD cluster does not talk to the device."""
    assert await smoke_siren.bind() == (foundation.Status.SUCCESS,)
    zone.alarm_control.assert_not_awaited()


async def test_test_mode(zone):
    """Test that the test mode uses the IAS Zone commands with the set timeout."""
    assert await write(zone, ATTR_TEST_MODE_TIMEOUT, 7) == foundation.Status.SUCCESS
    assert zone.get(ATTR_TEST_MODE_TIMEOUT) == 7
    zone.init_test_mode.assert_not_awaited()

    assert await write(zone, ATTR_TEST_MODE, True) == foundation.Status.SUCCESS
    zone.init_test_mode.assert_awaited_once_with(
        test_mode_duration=7, current_zone_sensitivity_level=0
    )
    assert bool(zone.get(ATTR_TEST_MODE)) is True

    assert await write(zone, ATTR_TEST_MODE, False) == foundation.Status.SUCCESS
    zone.init_normal_op_mode.assert_awaited_once_with()
    assert bool(zone.get(ATTR_TEST_MODE)) is False


async def test_refused_test_mode_keeps_the_state(zone):
    """Test that a refused test mode command does not change the switch."""
    zone.init_test_mode.return_value = FAILED

    assert await write(zone, ATTR_TEST_MODE, True) == foundation.Status.FAILURE
    assert bool(zone.get(ATTR_TEST_MODE)) is False


async def test_linkage_alarm_only_changes_the_setting(device, zone):
    """Test that changing the broadcast setting sends nothing."""
    assert await write(zone, ATTR_BROADCAST_ALARMS, False) == foundation.Status.SUCCESS

    assert bool(zone.get(ATTR_BROADCAST_ALARMS)) is False
    zone.alarm_control.assert_not_awaited()
    device.application.broadcast.assert_not_awaited()


async def test_write_of_real_attributes_goes_to_the_device(zone):
    """Test that real attributes are written to the device, local ones are not."""
    with mock.patch.object(
        IasZone,
        "write_attributes",
        mock.AsyncMock(return_value=[[foundation.WriteAttributesStatusRecord(0)]]),
    ) as device_write:
        await zone.write_attributes({SENSITIVITY: 1})
        device_write.assert_awaited_once_with({SENSITIVITY: 1})
        device_write.reset_mock()

        result = await zone.write_attributes(
            {SENSITIVITY: 1, ATTR_TEST_MODE_TIMEOUT: 9}
        )

    device_write.assert_awaited_once_with({SENSITIVITY: 1})
    assert len(result[0]) == 2
    assert zone.get(ATTR_TEST_MODE_TIMEOUT) == 9
