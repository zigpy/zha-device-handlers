"""Tests the Danfoss quirks (Ally/Popp TRVs and DEVI DEVIreg thermostats)."""

from typing import cast
from unittest import mock

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Time
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.foundation import WriteAttributesStatusRecord, ZCLAttributeDef

import zhaquirks
from zhaquirks.clusters import CustomCluster
from zhaquirks.danfoss.devireg import DeviThermostatCluster
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


def devireg_device(zigpy_device_from_v2_quirk):
    """Create a quirked DEVIreg Display Connect device."""
    return zigpy_device_from_v2_quirk(
        "devi",
        "devi_c",
        cluster_ids={
            1: {
                Time.cluster_id: ClusterType.Server,
                Thermostat.cluster_id: ClusterType.Server,
                TemperatureMeasurement.cluster_id: ClusterType.Server,
            }
        },
    )


async def test_devireg_heater_on_mirrors_running_state(zigpy_device_from_v2_quirk):
    """Test the relay state being mirrored into the emulated running_state."""
    device = devireg_device(zigpy_device_from_v2_quirk)

    thermostat = device.endpoints[1].thermostat
    assert isinstance(thermostat, DeviThermostatCluster)

    heater_on = DeviThermostatCluster.AttributeDefs.heater_on
    running_state = Thermostat.AttributeDefs.running_state

    thermostat.update_attribute(heater_on.id, 1)
    assert thermostat.get(running_state.name) == Thermostat.RunningState.Heat_State_On

    thermostat.update_attribute(heater_on.id, 0)
    assert thermostat.get(running_state.name) == Thermostat.RunningState.Idle


async def test_devireg_running_state_served_locally(zigpy_device_from_v2_quirk):
    """Test running_state reads never reaching the device."""
    device = devireg_device(zigpy_device_from_v2_quirk)

    thermostat = device.endpoints[1].thermostat
    heater_on = DeviThermostatCluster.AttributeDefs.heater_on
    running_state = Thermostat.AttributeDefs.running_state
    local_temperature = Thermostat.AttributeDefs.local_temperature

    read_mock = mock.AsyncMock()
    with mock.patch.object(thermostat, "_read_attributes", read_mock):
        # Nothing cached yet: served locally as Idle, no remote read
        success, failure = await thermostat.read_attributes([running_state.name])
        assert not failure
        assert success[running_state.name] == Thermostat.RunningState.Idle
        read_mock.assert_not_called()

        # Derived from the cached relay state
        thermostat.update_attribute(heater_on.id, 1)
        success, failure = await thermostat.read_attributes([running_state.name])
        assert not failure
        assert success[running_state.name] == Thermostat.RunningState.Heat_State_On
        read_mock.assert_not_called()

    # Other attributes in the same read still reach the device
    def mock_read(attr_ids, manufacturer=None, **kwargs):
        records = []
        for attrid in attr_ids:
            record = foundation.ReadAttributeRecord(
                attrid, foundation.Status.SUCCESS, foundation.TypeValue()
            )
            record.value.value = 2100
            records.append(record)
        return [records]

    read_mock = mock.AsyncMock(side_effect=mock_read)
    with mock.patch.object(thermostat, "_read_attributes", read_mock):
        success, failure = await thermostat.read_attributes(
            [local_temperature.name, running_state.name]
        )

    assert not failure
    assert success[local_temperature.name] == 2100
    assert success[running_state.name] == Thermostat.RunningState.Heat_State_On
    assert read_mock.mock_calls[0].args[0] == [local_temperature.id]

    # A failed remote read still serves running_state from the local cache
    read_mock = mock.AsyncMock(return_value=[foundation.Status.FAILURE])
    with mock.patch.object(thermostat, "_read_attributes", read_mock):
        success, failure = await thermostat.read_attributes(
            [local_temperature.name, running_state.name]
        )

    assert success[running_state.name] == Thermostat.RunningState.Heat_State_On
    assert failure[local_temperature.name] == foundation.Status.FAILURE


async def test_devireg_write_attributes(zigpy_device_from_v2_quirk):
    """Test the off emulation and the sub-15 degree setpoint clamp workaround."""
    device = devireg_device(zigpy_device_from_v2_quirk)

    thermostat = device.endpoints[1].thermostat
    system_mode = Thermostat.AttributeDefs.system_mode
    setpoint = Thermostat.AttributeDefs.occupied_heating_setpoint
    min_limit = Thermostat.AttributeDefs.min_heat_setpoint_limit

    written = []

    def mock_write(attributes, manufacturer=None):
        written.append({record.attrid: record.value.value for record in attributes})
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    patch_write = mock.patch.object(
        thermostat, "_write_attributes", mock.AsyncMock(side_effect=mock_write)
    )
    patch_sleep = mock.patch(
        "zhaquirks.danfoss.devireg.asyncio.sleep", mock.AsyncMock()
    )

    with patch_write, patch_sleep as sleep_mock:
        # Setpoint at or above 15 degrees: single write, no workaround
        await thermostat.write_attributes({setpoint.name: 2100})
        assert written == [{setpoint.id: 2100}]
        sleep_mock.assert_not_called()

        # Setpoint crossing below 15 degrees: 15 degrees written first
        written.clear()
        await thermostat.write_attributes({setpoint.name: 1200})
        assert written == [{setpoint.id: 1500}, {setpoint.id: 1200}]
        sleep_mock.assert_awaited_once()

        # Setpoint already below 15 degrees: no workaround
        written.clear()
        await thermostat.write_attributes({setpoint.name: 900})
        assert written == [{setpoint.id: 900}]
        sleep_mock.assert_awaited_once()

        # Off is emulated with the minimum setpoint and stays in heat mode
        written.clear()
        thermostat.update_attribute(min_limit.id, 500)
        await thermostat.write_attributes({system_mode.name: 0x00})
        assert written == [
            {system_mode.id: Thermostat.SystemMode.Heat, setpoint.id: 500}
        ]
        assert thermostat.get(system_mode.name) == Thermostat.SystemMode.Heat
        assert thermostat.get(setpoint.name) == 500

        # Off crossing below 15 degrees applies the workaround
        written.clear()
        thermostat.update_attribute(setpoint.id, 2000)
        await thermostat.write_attributes({system_mode.name: 0x00})
        assert written == [
            {setpoint.id: 1500},
            {system_mode.id: Thermostat.SystemMode.Heat, setpoint.id: 500},
        ]


@mock.patch("zigpy.zcl.Cluster.bind", mock.AsyncMock())
async def test_devireg_time_bind(zigpy_device_from_v2_quirk):
    """Test the time being written when binding the thermostat cluster."""
    device = devireg_device(zigpy_device_from_v2_quirk)

    time_cluster = device.endpoints[1].time
    thermostat = device.endpoints[1].thermostat

    def mock_write(attributes, manufacturer=None):
        records = [
            WriteAttributesStatusRecord(foundation.Status.SUCCESS) for _ in attributes
        ]
        return [records, []]

    with mock.patch.object(
        time_cluster, "_write_attributes", mock.AsyncMock(side_effect=mock_write)
    ):
        await thermostat.bind()

        assert Time.AttributeDefs.time.id in time_cluster._attr_cache
        assert Time.AttributeDefs.time_status.id in time_cluster._attr_cache
        assert Time.AttributeDefs.time_zone.id in time_cluster._attr_cache
