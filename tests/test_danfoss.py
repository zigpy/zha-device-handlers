"""Tests the Danfoss quirk (all tests were written for the Popp eT093WRO)."""

import asyncio
from typing import cast
from unittest import mock

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.foundation import WriteAttributesStatusRecord, ZCLAttributeDef

import zhaquirks
from zhaquirks.clusters import CustomCluster
from zhaquirks.danfoss.thermostat import CustomizedStandardCluster

zhaquirks.setup()


def test_popp_signature(assert_signature_matches_quirk):
    """Test the signature matching the Device Class."""
    signature = {
        "node_descriptor": "NodeDescriptor(logical_type=<LogicalType.EndDevice: 2>, complex_descriptor_available=0, user_descriptor_available=0, reserved=0, aps_flags=0, frequency_band=<FrequencyBand.Freq2400MHz: 8>, mac_capability_flags=<MACCapabilityFlags.AllocateAddress: 128>, manufacturer_code=4678, maximum_buffer_size=82, maximum_incoming_transfer_size=82, server_mask=11264, maximum_outgoing_transfer_size=82, descriptor_capability_field=<DescriptorCapability.NONE: 0>, *allocate_address=True, *is_alternate_pan_coordinator=False, *is_coordinator=False, *is_end_device=True, *is_full_function_device=False, *is_mains_powered=False, *is_receiver_on_when_idle=False, *is_router=False, *is_security_capable=False)",
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=769, device_version=1, input_clusters=[0, 1, 3, 10, 32, 513, 516, 2821], output_clusters=[0, 25])
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x0301",
                "in_clusters": [
                    "0x0000",
                    "0x0001",
                    "0x0003",
                    "0x000a",
                    "0x0020",
                    "0x0201",
                    "0x0204",
                    "0x0b05",
                ],
                "out_clusters": ["0x0000", "0x0019"],
            }
        },
        "manufacturer": "D5X84YU",
        "model": "eT093WRO",
        "class": "danfoss.thermostat.DanfossThermostat",
    }

    assert_signature_matches_quirk(
        zhaquirks.danfoss.thermostat.DanfossThermostat, signature
    )


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
async def test_danfoss_time_bind(zigpy_device_from_quirk):
    """Test the time being set when binding the Time cluster."""
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)

    danfoss_time_cluster = device.endpoints[1].time
    danfoss_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    patch_danfoss_trv_write = mock.patch.object(
        danfoss_time_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )

    with patch_danfoss_trv_write:
        await danfoss_thermostat_cluster.bind()

        assert 0x0000 in danfoss_time_cluster._attr_cache
        assert 0x0001 in danfoss_time_cluster._attr_cache
        assert 0x0002 in danfoss_time_cluster._attr_cache


async def test_danfoss_thermostat_write_attributes(zigpy_device_from_quirk):
    """Test the Thermostat writes behaving correctly, in particular regarding setpoint."""
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)

    danfoss_thermostat_cluster = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    setting = -100
    operation = -0x01

    def mock_setpoint(oper, sett, manufacturer=None):
        nonlocal operation, setting
        operation = oper
        setting = sett

    # data is written to trv
    patch_danfoss_trv_write = mock.patch.object(
        danfoss_thermostat_cluster,
        "_write_attributes",
        mock.AsyncMock(side_effect=mock_write),
    )
    patch_danfoss_setpoint = mock.patch.object(
        danfoss_thermostat_cluster,
        "setpoint_command",
        mock.AsyncMock(side_effect=mock_setpoint),
    )

    with patch_danfoss_trv_write:
        # data should be written to trv, but reach thermostat
        await danfoss_thermostat_cluster.write_attributes(
            {"external_open_window_detected": False}
        )
        assert not danfoss_thermostat_cluster._attr_cache[0x4003]

        with patch_danfoss_setpoint:
            # data should be received from danfoss_trv
            await danfoss_thermostat_cluster.write_attributes(
                {"occupied_heating_setpoint": 6}
            )
            assert danfoss_thermostat_cluster._attr_cache[0x0012] == 6
            assert operation == 0x01
            assert setting == 6

            danfoss_thermostat_cluster._attr_cache[0x0015] = (
                5  # min_limit is present normally
            )

            await danfoss_thermostat_cluster.write_attributes({"system_mode": 0x00})
            assert danfoss_thermostat_cluster._attr_cache[0x001C] == 0x04

            # setpoint to min_limit, when system_mode to off
            assert danfoss_thermostat_cluster._attr_cache[0x0012] == 5

            assert operation == 0x01
            assert setting == 5


async def test_customized_standardcluster(zigpy_device_from_quirk):
    """Test customized standard cluster class correctly separating zigbee operations.

    This is regarding manufacturer specific attributes.
    """
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)

    danfoss_thermostat_cluster = device.endpoints[1].in_clusters[Thermostat.cluster_id]

    assert CustomizedStandardCluster.combine_results([[4545], [5433]], [[345]]) == [
        [4545, 345],
        [5433],
    ]
    assert CustomizedStandardCluster.combine_results(
        [[4545], [5433]], [[345], [45355]]
    ) == [[4545, 345], [5433, 45355]]

    mock_attributes = {
        656: ZCLAttributeDef(type=t.uint8_t, is_manufacturer_specific=True),
        56454: ZCLAttributeDef(type=t.uint8_t, is_manufacturer_specific=False),
    }

    danfoss_thermostat_cluster.attributes = mock_attributes

    reports = None

    def mock_configure_reporting(reps, *args, **kwargs):
        nonlocal reports
        if mock_attributes[reps[0].attrid].is_manufacturer_specific:
            reports = reps

        return [[545], [4545]]

    # data is written to trv
    patch_danfoss_configure_reporting = mock.patch.object(
        CustomCluster,
        "_configure_reporting",
        mock.AsyncMock(side_effect=mock_configure_reporting),
    )

    with patch_danfoss_configure_reporting:
        one = foundation.AttributeReportingConfig()
        one.direction = True
        one.timeout = 4
        one.attrid = 56454

        two = foundation.AttributeReportingConfig()
        two.direction = True
        two.timeout = 4
        two.attrid = 656
        await danfoss_thermostat_cluster._configure_reporting([one, two])
        assert reports == [two]

    # typed wide so mypy doesn't narrow to None (the mocked _read_attributes
    # side effect reassigns this to a list), which would flag the assert below
    # as comparing an always-None value and mark later code unreachable
    reports = cast(list | None, None)

    def mock_read_attributes(attrs, *args, **kwargs):
        nonlocal reports
        if mock_attributes[attrs[0]].is_manufacturer_specific:
            reports = attrs

        return [[545]]

    # data is written to trv
    patch_danfoss_read_attributes = mock.patch.object(
        CustomCluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read_attributes),
    )

    with patch_danfoss_read_attributes:
        result = await danfoss_thermostat_cluster._read_attributes([56454, 656])
        assert result
        assert reports == [656]

    def mock_read_attributes_fail(attrs, *args, **kwargs):
        nonlocal reports
        if mock_attributes[attrs[0]].is_manufacturer_specific:
            reports = attrs

        return [[545], [4545]]

    # data is written to trv
    patch_danfoss_read_attributes_fail = mock.patch.object(
        CustomCluster,
        "_read_attributes",
        mock.AsyncMock(side_effect=mock_read_attributes_fail),
    )

    with patch_danfoss_read_attributes_fail:
        result, fail = await danfoss_thermostat_cluster._read_attributes([56454, 656])
        assert result
        assert fail
        assert reports == [656]


# GetWeeklyScheduleResponse frames captured from an eTRV0103 (firmware 0x00000020).
# The second byte is the TSN chosen by the device, never the TSN of the request.
SCHEDULE_RSP_FRIDAY = bytes.fromhex("091d0004200100000807860134081a0408072805a406")
SCHEDULE_RSP_SATURDAY = bytes.fromhex("091e0004400100000807860134081a0408072805a406")

# Thermostat transitions in the captured frames: (minutes after midnight, centi-°C)
SCHEDULE_VALUES = [0, 1800, 390, 2100, 1050, 1800, 1320, 1700]


def _thermostat_packet(data: bytes) -> t.ZigbeePacket:
    """Build a packet from the thermostat cluster of endpoint 1 carrying `data`."""
    return t.ZigbeePacket(
        profile_id=260,
        cluster_id=Thermostat.cluster_id,
        src_ep=1,
        dst_ep=1,
        data=t.SerializableBytes(data),
    )


def _with_tsn(data: bytes, tsn: int) -> bytes:
    """Return the ZCL frame `data` with its TSN replaced by `tsn`."""
    return data[:1] + bytes([tsn]) + data[2:]


async def _wait_for_pending_tsns(device, count: int) -> list[int]:
    """Wait until at least `count` requests are pending, return their TSNs."""
    for _ in range(100):
        if len(device._requests) >= count:
            return sorted(key.tsn for key in device._requests)
        await asyncio.sleep(0)

    raise AssertionError(f"expected {count} pending requests: {device._requests}")


async def test_danfoss_weekly_schedule_response_own_tsn(zigpy_device_from_quirk):
    """Test that a response carrying the device's own TSN resolves the request."""
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)
    thermostat = device.endpoints[1].thermostat
    listener = mock.MagicMock()
    thermostat.add_listener(listener)

    request = asyncio.create_task(
        thermostat.get_weekly_schedule(
            days_to_return=Thermostat.SeqDayOfWeek.Friday,
            mode_to_return=Thermostat.SeqMode.Heat,
        )
    )
    (tsn,) = await _wait_for_pending_tsns(device, 1)
    assert tsn != SCHEDULE_RSP_FRIDAY[1]

    device.packet_received(_thermostat_packet(SCHEDULE_RSP_FRIDAY))

    rsp = await asyncio.wait_for(request, 1)
    assert rsp.day_of_week_for_sequence == Thermostat.SeqDayOfWeek.Friday
    assert rsp.values == SCHEDULE_VALUES
    assert not device._weekly_schedule_requests

    # the response still reaches the cluster and is surfaced as a ZHA event
    listener.zha_send_event.assert_called_once_with("get_weekly_schedule_response", rsp)


async def test_danfoss_weekly_schedule_response_concurrent(zigpy_device_from_quirk):
    """Test that two queued GetWeeklySchedule requests are both resolved."""
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)
    thermostat = device.endpoints[1].thermostat
    listener = mock.MagicMock()
    thermostat.add_listener(listener)

    friday = asyncio.create_task(
        thermostat.get_weekly_schedule(
            Thermostat.SeqDayOfWeek.Friday, Thermostat.SeqMode.Heat
        )
    )
    saturday = asyncio.create_task(
        thermostat.get_weekly_schedule(
            Thermostat.SeqDayOfWeek.Saturday, Thermostat.SeqMode.Heat
        )
    )

    # the second request may still be queued behind the first one in zigpy
    await _wait_for_pending_tsns(device, 1)
    assert len(device._weekly_schedule_requests) == 2

    device.packet_received(_thermostat_packet(SCHEDULE_RSP_FRIDAY))
    rsp_friday = await asyncio.wait_for(friday, 1)
    assert rsp_friday.day_of_week_for_sequence == Thermostat.SeqDayOfWeek.Friday

    await _wait_for_pending_tsns(device, 1)
    device.packet_received(_thermostat_packet(SCHEDULE_RSP_SATURDAY))
    rsp_saturday = await asyncio.wait_for(saturday, 1)
    assert rsp_saturday.day_of_week_for_sequence == Thermostat.SeqDayOfWeek.Saturday

    assert not device._weekly_schedule_requests
    assert listener.zha_send_event.call_count == 2


async def test_danfoss_weekly_schedule_response_matching_tsn(zigpy_device_from_quirk):
    """Test a response that echoes the request TSN still emits a ZHA event."""
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)
    thermostat = device.endpoints[1].thermostat
    listener = mock.MagicMock()
    thermostat.add_listener(listener)

    request = asyncio.create_task(
        thermostat.get_weekly_schedule(
            Thermostat.SeqDayOfWeek.Friday, Thermostat.SeqMode.Heat
        )
    )
    (tsn,) = await _wait_for_pending_tsns(device, 1)

    device.packet_received(_thermostat_packet(_with_tsn(SCHEDULE_RSP_FRIDAY, tsn)))

    rsp = await asyncio.wait_for(request, 1)
    assert rsp.values == SCHEDULE_VALUES
    listener.zha_send_event.assert_called_once_with("get_weekly_schedule_response", rsp)


async def test_danfoss_weekly_schedule_response_tsn_collision(zigpy_device_from_quirk):
    """Test the device's own TSN never resolves another pending Thermostat request."""
    device = zigpy_device_from_quirk(zhaquirks.danfoss.thermostat.DanfossThermostat)
    thermostat = device.endpoints[1].thermostat

    read = asyncio.create_task(
        thermostat.read_attributes_raw([Thermostat.AttributeDefs.local_temperature.id])
    )
    (tsn,) = await _wait_for_pending_tsns(device, 1)

    device.packet_received(_thermostat_packet(_with_tsn(SCHEDULE_RSP_FRIDAY, tsn)))
    await asyncio.sleep(0)

    assert not read.done()
    read.cancel()
