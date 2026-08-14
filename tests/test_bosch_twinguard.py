"""Tests for the Bosch Twinguard quirk."""

import asyncio
from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Alarms, PollControl, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    CarbonMonoxideConcentration,
    IlluminanceMeasurement,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)

from zhaquirks.bosch.twinguard import (
    BOSCH_MANUFACTURER_CODE,
    BURGLAR_ALARM_STATUS,
    CLEAR_ALARM,
    CLEAR_ALARM_STATUS,
    FIRE_ALARM,
    FIRE_ALARM_STATUS,
    PRE_ALARM,
    PRE_ALARM_STATUS,
    SELF_TEST_ALARM_STATUS,
    SILENCE_ALARM,
    SILENCED_ALARM_STATUS,
    TWINGUARD_ALARM_CLUSTER,
    TWINGUARD_MEASUREMENTS_CLUSTER,
    TWINGUARD_OPTIONS_CLUSTER,
    TWINGUARD_SETUP_CLUSTER,
    TWINGUARD_SMOKE_CLUSTER,
    BoschTwinguardAlarmCluster,
    BoschTwinguardAlarmsCluster,
    BoschTwinguardMeasurementsCluster,
    BoschTwinguardOptionsCluster,
    BoschTwinguardSetupCluster,
    BoschTwinguardSirenControl,
    BoschTwinguardSmokeCluster,
    TwinguardAlarmMode,
    TwinguardSensitivity,
    TwinguardSirenState,
)
from zhaquirks.builder import EntityType

TWINGUARD_CLUSTER_IDS = {
    1: {
        Alarms.cluster_id: ClusterType.Server,
        TWINGUARD_SMOKE_CLUSTER: ClusterType.Server,
        TWINGUARD_OPTIONS_CLUSTER: ClusterType.Server,
        # The Twinguard also has an Alarms client cluster on endpoint 1.
        # A dictionary cannot contain both cluster types for one ID, so add it below.
    },
    3: {TWINGUARD_MEASUREMENTS_CLUSTER: ClusterType.Server},
    4: {PowerConfiguration.cluster_id: ClusterType.Server},
    5: {TemperatureMeasurement.cluster_id: ClusterType.Server},
    6: {IlluminanceMeasurement.cluster_id: ClusterType.Server},
    7: {PollControl.cluster_id: ClusterType.Server},
    8: {PressureMeasurement.cluster_id: ClusterType.Server},
    9: {RelativeHumidity.cluster_id: ClusterType.Server},
    11: {CarbonMonoxideConcentration.cluster_id: ClusterType.Server},
    12: {
        TWINGUARD_SETUP_CLUSTER: ClusterType.Server,
        TWINGUARD_ALARM_CLUSTER: ClusterType.Server,
    },
}


def make_twinguard(
    zigpy_device_from_v2_quirk,
    manufacturer="BOSCH ST",
):
    """Create a quirked Twinguard with its relevant endpoints and clusters."""
    device = zigpy_device_from_v2_quirk(
        manufacturer=manufacturer,
        model="Champion",
        cluster_ids=TWINGUARD_CLUSTER_IDS,
    )
    device.endpoints[1].add_output_cluster(Alarms.cluster_id)
    return device


def test_twinguard_quirk_and_entities(zigpy_device_from_v2_quirk):
    """Test cluster replacements and V2 entity metadata."""
    device = make_twinguard(zigpy_device_from_v2_quirk)

    assert isinstance(device.endpoints[1].alarms, BoschTwinguardAlarmsCluster)
    assert isinstance(device.endpoints[1].twinguard_smoke, BoschTwinguardSmokeCluster)
    assert isinstance(
        device.endpoints[1].twinguard_options, BoschTwinguardOptionsCluster
    )
    assert isinstance(
        device.endpoints[1].twinguard_siren_control,
        BoschTwinguardSirenControl,
    )
    assert isinstance(
        device.endpoints[3].twinguard_measurements,
        BoschTwinguardMeasurementsCluster,
    )
    assert isinstance(device.endpoints[12].twinguard_setup, BoschTwinguardSetupCluster)
    assert isinstance(device.endpoints[12].twinguard_alarm, BoschTwinguardAlarmCluster)

    entry = DEVICE_REGISTRY.match_entry(device)
    metadata_by_suffix = {
        metadata.resolved_unique_id_suffix: metadata
        for metadata in entry.zha_device_factory.quirk_definition.entity_metadata
    }
    disabled_default_entities = {
        (metadata.endpoint_id, metadata.cluster_id)
        for metadata in entry.zha_device_factory.quirk_definition.disabled_default_entities
    }
    assert disabled_default_entities == {
        (4, PowerConfiguration.cluster_id),
        (5, TemperatureMeasurement.cluster_id),
        (6, IlluminanceMeasurement.cluster_id),
        (8, PressureMeasurement.cluster_id),
        (9, RelativeHumidity.cluster_id),
        (11, CarbonMonoxideConcentration.cluster_id),
    }
    assert set(metadata_by_suffix) == {
        "illuminance",
        "temperature",
        "humidity",
        "battery",
        "aqi",
        "eco2",
        "smoke",
        "self_test_active",
        "initiate_test_mode",
        "pre_alarm",
        "heartbeat",
        "alarm_mode",
        "siren_state",
        "sensitivity",
    }

    aqi = metadata_by_suffix["aqi"]
    battery = metadata_by_suffix["battery"]
    eco2 = metadata_by_suffix["eco2"]
    humidity = metadata_by_suffix["humidity"]
    illuminance = metadata_by_suffix["illuminance"]
    temperature = metadata_by_suffix["temperature"]
    assert illuminance.divisor == 2
    assert temperature.divisor == 100
    assert humidity.divisor == 100
    assert battery.divisor == 2
    assert battery.entity_type is EntityType.DIAGNOSTIC
    assert aqi.attribute_converter is None
    assert eco2.attribute_converter(42) == 920
    assert eco2.device_class is None
    assert eco2.translation_key == "estimated_co2"


def test_twinguard_alternate_manufacturer(zigpy_device_from_v2_quirk):
    """Test the alternate manufacturer string used by some Twinguards."""
    device = make_twinguard(
        zigpy_device_from_v2_quirk,
        manufacturer="BoschSmartHomeGmbH",
    )
    assert isinstance(device.endpoints[1].twinguard_smoke, BoschTwinguardSmokeCluster)


async def test_twinguard_fire_alarm_is_acknowledged(zigpy_device_from_v2_quirk):
    """Test fire notifications update state and are echoed to the device."""
    device = make_twinguard(zigpy_device_from_v2_quirk)
    alarms = device.endpoints[1].alarms
    alarms_client = device.endpoints[1].out_clusters[Alarms.cluster_id]
    alarms_client.client_command = mock.AsyncMock()

    header = foundation.ZCLHeader.cluster(
        tsn=1,
        command_id=Alarms.ClientCommandDefs.alarm.id,
        direction=foundation.Direction.Server_to_Client,
    )
    args = Alarms.ClientCommandDefs.alarm.schema(
        alarm_code=FIRE_ALARM,
        cluster_id=TWINGUARD_SMOKE_CLUSTER,
    )
    alarms.handle_cluster_request(header, args)
    await asyncio.sleep(0)

    siren_control = device.endpoints[1].twinguard_siren_control
    assert (
        siren_control.get(BoschTwinguardSirenControl.AttributeDefs.siren_state.id)
        == TwinguardSirenState.Fire
    )
    alarms_client.client_command.assert_awaited_once_with(
        Alarms.ClientCommandDefs.alarm.id,
        alarm_code=FIRE_ALARM,
        cluster_id=TWINGUARD_SMOKE_CLUSTER,
        expect_reply=False,
    )


@pytest.mark.parametrize(
    ("status", "state", "mode"),
    [
        (CLEAR_ALARM_STATUS, TwinguardSirenState.Clear, TwinguardAlarmMode.Stop),
        (
            SILENCED_ALARM_STATUS,
            TwinguardSirenState.Silenced,
            TwinguardAlarmMode.Stop,
        ),
        (FIRE_ALARM_STATUS, TwinguardSirenState.Fire, TwinguardAlarmMode.Fire),
        (
            PRE_ALARM_STATUS,
            TwinguardSirenState.Pre_alarm,
            TwinguardAlarmMode.Pre_alarm,
        ),
        (
            BURGLAR_ALARM_STATUS,
            TwinguardSirenState.Burglar,
            TwinguardAlarmMode.Burglar,
        ),
    ],
)
def test_twinguard_alarm_status_updates_local_state(
    zigpy_device_from_v2_quirk,
    status,
    state,
    mode,
):
    """Test reported alarm states update both local alarm entities."""
    device = make_twinguard(zigpy_device_from_v2_quirk)
    alarm_cluster = device.endpoints[12].twinguard_alarm
    siren_control = device.endpoints[1].twinguard_siren_control

    alarm_cluster.update_attribute(
        BoschTwinguardAlarmCluster.AttributeDefs.alarm_status.id,
        status,
    )

    assert (
        siren_control.get(BoschTwinguardSirenControl.AttributeDefs.siren_state.id)
        == state
    )
    assert (
        siren_control.get(BoschTwinguardSirenControl.AttributeDefs.alarm_mode.id)
        == mode
    )


def test_twinguard_self_test_does_not_change_alarm_mode(
    zigpy_device_from_v2_quirk,
):
    """Test self-test is reported without changing the selected alarm mode."""
    device = make_twinguard(zigpy_device_from_v2_quirk)
    alarm_cluster = device.endpoints[12].twinguard_alarm
    siren_control = device.endpoints[1].twinguard_siren_control
    siren_control.update_siren_state(TwinguardSirenState.Fire)

    alarm_cluster.update_attribute(
        BoschTwinguardAlarmCluster.AttributeDefs.alarm_status.id,
        SELF_TEST_ALARM_STATUS,
    )

    assert (
        siren_control.get(BoschTwinguardSirenControl.AttributeDefs.siren_state.id)
        == TwinguardSirenState.Self_test
    )
    assert (
        siren_control.get(BoschTwinguardSirenControl.AttributeDefs.alarm_mode.id)
        == TwinguardAlarmMode.Fire
    )


async def test_twinguard_siren_state_is_read_only(zigpy_device_from_v2_quirk):
    """Test the reported siren state cannot be written locally."""
    device = make_twinguard(zigpy_device_from_v2_quirk)
    siren_control = device.endpoints[1].twinguard_siren_control
    state_attribute = BoschTwinguardSirenControl.AttributeDefs.siren_state

    result = await siren_control.write_attributes(
        {state_attribute.name: TwinguardSirenState.Fire}
    )

    assert result == [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.READ_ONLY,
                attrid=state_attribute.id,
            )
        ]
    ]
    assert siren_control.get(state_attribute.id) == TwinguardSirenState.Clear


@pytest.mark.parametrize(
    ("mode", "alarm_codes", "burglar_data", "state"),
    [
        (
            TwinguardAlarmMode.Stop,
            [SILENCE_ALARM, CLEAR_ALARM],
            0x00,
            TwinguardSirenState.Clear,
        ),
        (
            TwinguardAlarmMode.Pre_alarm,
            [PRE_ALARM],
            0x00,
            TwinguardSirenState.Pre_alarm,
        ),
        (
            TwinguardAlarmMode.Fire,
            [FIRE_ALARM],
            0x00,
            TwinguardSirenState.Fire,
        ),
        (
            TwinguardAlarmMode.Burglar,
            [SILENCE_ALARM, CLEAR_ALARM],
            0x01,
            TwinguardSirenState.Burglar,
        ),
    ],
)
async def test_twinguard_alarm_mode_commands(
    zigpy_device_from_v2_quirk,
    mode,
    alarm_codes,
    burglar_data,
    state,
):
    """Test alarm-mode selections issue the expected Bosch commands."""
    device = make_twinguard(zigpy_device_from_v2_quirk)
    siren_control = device.endpoints[1].twinguard_siren_control
    alarms = device.endpoints[1].out_clusters[Alarms.cluster_id]
    burglar = device.endpoints[12].twinguard_alarm
    alarms.client_command = mock.AsyncMock()
    burglar.command = mock.AsyncMock()

    result = await siren_control.write_attributes(
        {BoschTwinguardSirenControl.AttributeDefs.alarm_mode.name: mode}
    )

    assert result == [
        [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    ]
    assert [
        call.kwargs["alarm_code"] for call in alarms.client_command.await_args_list
    ] == alarm_codes
    burglar.command.assert_awaited_once_with(
        BoschTwinguardAlarmCluster.ServerCommandDefs.burglar_alarm.id,
        data=burglar_data,
        manufacturer=BOSCH_MANUFACTURER_CODE,
        expect_reply=False,
    )
    assert (
        siren_control.get(BoschTwinguardSirenControl.AttributeDefs.siren_state.id)
        == state
    )


async def test_twinguard_pairing_configuration(zigpy_device_from_v2_quirk):
    """Test the Bosch pairing handshake and initial configuration."""
    device = make_twinguard(zigpy_device_from_v2_quirk)
    setup = device.endpoints[12].twinguard_setup
    options = device.endpoints[1].twinguard_options
    smoke = device.endpoints[1].twinguard_smoke

    clusters_to_bind = [
        device.endpoints[7].poll_control,
        device.endpoints[1].alarms,
        smoke,
        options,
        device.endpoints[3].twinguard_measurements,
        setup,
        device.endpoints[12].twinguard_alarm,
    ]
    for cluster in clusters_to_bind:
        cluster.bind = mock.AsyncMock()

    calls = mock.Mock()
    options_read = mock.patch.object(
        options, "read_attributes", mock.AsyncMock()
    ).start()
    pairing_command = mock.patch.object(setup, "command", mock.AsyncMock()).start()
    calls.attach_mock(options_read, "read_options")
    calls.attach_mock(pairing_command, "pairing_command")
    smoke.write_attributes = mock.AsyncMock()
    options.write_attributes = mock.AsyncMock()
    setup.write_attributes = mock.AsyncMock()
    smoke.read_attributes = mock.AsyncMock()
    setup.read_attributes = mock.AsyncMock()

    try:
        await setup.apply_custom_configuration()
    finally:
        mock.patch.stopall()

    for cluster in clusters_to_bind:
        cluster.bind.assert_awaited_once()

    assert calls.mock_calls[:2] == [
        mock.call.read_options(
            [BoschTwinguardOptionsCluster.AttributeDefs.pairing_state.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        ),
        mock.call.pairing_command(
            BoschTwinguardSetupCluster.ServerCommandDefs.pairing_completed.id,
            manufacturer=BOSCH_MANUFACTURER_CODE,
        ),
    ]
    smoke.write_attributes.assert_awaited_once_with(
        {
            BoschTwinguardSmokeCluster.AttributeDefs.sensitivity.id: TwinguardSensitivity.Medium
        },
        manufacturer=BOSCH_MANUFACTURER_CODE,
    )
    options.write_attributes.assert_awaited_once_with(
        {BoschTwinguardOptionsCluster.AttributeDefs.pre_alarm.id: 0x01},
        manufacturer=BOSCH_MANUFACTURER_CODE,
    )
    setup.write_attributes.assert_awaited_once_with(
        {BoschTwinguardSetupCluster.AttributeDefs.heartbeat.id: 0x01},
        manufacturer=BOSCH_MANUFACTURER_CODE,
    )
    assert options_read.await_args_list == [
        mock.call(
            [BoschTwinguardOptionsCluster.AttributeDefs.pairing_state.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        ),
        mock.call(
            [BoschTwinguardOptionsCluster.AttributeDefs.pre_alarm.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        ),
    ]
    smoke.read_attributes.assert_awaited_once_with(
        [BoschTwinguardSmokeCluster.AttributeDefs.sensitivity.id],
        manufacturer=BOSCH_MANUFACTURER_CODE,
    )
    setup.read_attributes.assert_awaited_once_with(
        [BoschTwinguardSetupCluster.AttributeDefs.heartbeat.id],
        manufacturer=BOSCH_MANUFACTURER_CODE,
    )
