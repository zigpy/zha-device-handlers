"""Device handler for the Bosch Twinguard smoke detector."""

from typing import Final

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Alarms, PollControl, PowerConfiguration
from zigpy.zcl.clusters.measurement import (
    CarbonMonoxideConcentration,
    IlluminanceMeasurement,
    PressureMeasurement,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
)

from zhaquirks import LocalDataCluster
from zhaquirks.builder import (
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
)
from zhaquirks.clusters import CustomCluster

BOSCH_MANUFACTURER_CODE = 0x1209
TWINGUARD_SMOKE_CLUSTER = 0xE000
TWINGUARD_MEASUREMENTS_CLUSTER = 0xE002
TWINGUARD_OPTIONS_CLUSTER = 0xE004
TWINGUARD_SETUP_CLUSTER = 0xE006
TWINGUARD_ALARM_CLUSTER = 0xE007
TWINGUARD_SIREN_CONTROL_CLUSTER = 0xFBFD

FIRE_ALARM = 0x10
PRE_ALARM = 0x11
CLEAR_ALARM = 0x14
SILENCE_ALARM = 0x16

CLEAR_ALARM_STATUS = 0x00200020
SILENCED_ALARM_STATUS = 0x00200040
FIRE_ALARM_STATUS = 0x00200081
PRE_ALARM_STATUS = 0x00200082
SELF_TEST_ALARM_STATUS = 0x01200020
BURGLAR_ALARM_STATUS = 0x02200020


class TwinguardSensitivity(t.enum16):
    """Smoke sensitivity values used by the Twinguard."""

    High = 0x0001
    Medium = 0x0002
    Low = 0x0003


class TwinguardAlarmMode(t.enum8):
    """Alarm modes supported by the Bosch protocol."""

    Stop = 0x00
    Pre_alarm = 0x01
    Fire = 0x02
    Burglar = 0x03


class TwinguardSirenState(t.enum8):
    """Read-only states reported by the Bosch alarm protocol."""

    Clear = 0x00
    Self_test = 0x01
    Burglar = 0x02
    Pre_alarm = 0x03
    Fire = 0x04
    Silenced = 0x05


async def set_bosch_alarm_mode(device, mode: TwinguardAlarmMode) -> None:
    """Select one of the Bosch alarm modes."""
    alarms = device.endpoints[1].out_clusters[Alarms.cluster_id]
    burglar = device.endpoints[12].in_clusters[TWINGUARD_ALARM_CLUSTER]

    if mode == TwinguardAlarmMode.Pre_alarm:
        await burglar.command(
            burglar.ServerCommandDefs.burglar_alarm.id,
            data=0x00,
            manufacturer=BOSCH_MANUFACTURER_CODE,
            expect_reply=False,
        )
        await alarms.client_command(
            Alarms.ClientCommandDefs.alarm.id,
            alarm_code=PRE_ALARM,
            cluster_id=TWINGUARD_SMOKE_CLUSTER,
            expect_reply=False,
        )
        return

    if mode == TwinguardAlarmMode.Fire:
        await burglar.command(
            burglar.ServerCommandDefs.burglar_alarm.id,
            data=0x00,
            manufacturer=BOSCH_MANUFACTURER_CODE,
            expect_reply=False,
        )
        await alarms.client_command(
            Alarms.ClientCommandDefs.alarm.id,
            alarm_code=FIRE_ALARM,
            cluster_id=TWINGUARD_SMOKE_CLUSTER,
            expect_reply=False,
        )
        return

    # Clear a smoke alarm before selecting burglar or stop.
    for alarm_code in (SILENCE_ALARM, CLEAR_ALARM):
        await alarms.client_command(
            Alarms.ClientCommandDefs.alarm.id,
            alarm_code=alarm_code,
            cluster_id=TWINGUARD_SMOKE_CLUSTER,
            expect_reply=False,
        )
    await burglar.command(
        burglar.ServerCommandDefs.burglar_alarm.id,
        data=0x01 if mode == TwinguardAlarmMode.Burglar else 0x00,
        manufacturer=BOSCH_MANUFACTURER_CODE,
        expect_reply=False,
    )


class BoschTwinguardSmokeCluster(CustomCluster):
    """Smoke-detector configuration on endpoint 1."""

    cluster_id: Final = TWINGUARD_SMOKE_CLUSTER
    ep_attribute: Final = "twinguard_smoke"

    class AttributeDefs(BaseAttributeDefs):
        """Bosch Twinguard smoke cluster attributes."""

        sensitivity: Final = ZCLAttributeDef(
            id=0x4003,
            type=TwinguardSensitivity,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Bosch Twinguard smoke cluster server commands."""

        initiate_test_mode: Final = ZCLCommandDef(
            id=0x00,
            schema={},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )


class BoschTwinguardMeasurementsCluster(CustomCluster):
    """Environmental measurements reported on endpoint 3."""

    cluster_id: Final = TWINGUARD_MEASUREMENTS_CLUSTER
    ep_attribute: Final = "twinguard_measurements"

    class AttributeDefs(BaseAttributeDefs):
        """Bosch Twinguard measurement cluster attributes."""

        humidity: Final = ZCLAttributeDef(
            id=0x4000,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )
        air_purity: Final = ZCLAttributeDef(
            id=0x4003,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )
        temperature: Final = ZCLAttributeDef(
            id=0x4004,
            type=t.int16s,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )
        illuminance: Final = ZCLAttributeDef(
            id=0x4005,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )
        battery: Final = ZCLAttributeDef(
            id=0x4006,
            type=t.uint16_t,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )


class BoschTwinguardOptionsCluster(CustomCluster):
    """Twinguard options on endpoint 1."""

    cluster_id: Final = TWINGUARD_OPTIONS_CLUSTER
    ep_attribute: Final = "twinguard_options"

    class AttributeDefs(BaseAttributeDefs):
        """Bosch Twinguard options cluster attributes."""

        pairing_state: Final = ZCLAttributeDef(
            id=0x4000,
            type=t.bitmap8,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )
        pre_alarm: Final = ZCLAttributeDef(
            id=0x4001,
            type=t.bitmap8,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )


class BoschTwinguardAlarmsCluster(CustomCluster, Alarms):
    """Acknowledge Bosch fire and pre-alarm notifications."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args,
        *,
        dst_addressing=None,
    ):
        """Echo fire alarms as the server-to-client frame Bosch expects."""
        super().handle_cluster_request(
            hdr,
            args,
            dst_addressing=dst_addressing,
        )
        if (
            hdr.direction != foundation.Direction.Server_to_Client
            or hdr.command_id != self.ClientCommandDefs.alarm.id
        ):
            return

        alarm_code = args.alarm_code
        siren_control = self.endpoint.in_clusters.get(TWINGUARD_SIREN_CONTROL_CLUSTER)
        if siren_control is not None:
            siren_states = {
                FIRE_ALARM: TwinguardSirenState.Fire,
                PRE_ALARM: TwinguardSirenState.Pre_alarm,
                CLEAR_ALARM: TwinguardSirenState.Clear,
                SILENCE_ALARM: TwinguardSirenState.Silenced,
            }
            if alarm_code in siren_states:
                siren_control.update_siren_state(siren_states[alarm_code])

        if alarm_code not in (FIRE_ALARM, PRE_ALARM):
            return

        alarms_client = self.endpoint.out_clusters[Alarms.cluster_id]
        self.create_catching_task(
            alarms_client.client_command(
                Alarms.ClientCommandDefs.alarm.id,
                alarm_code=alarm_code,
                cluster_id=TWINGUARD_SMOKE_CLUSTER,
                expect_reply=False,
            )
        )


class BoschTwinguardSetupCluster(CustomCluster):
    """Pairing and setup cluster on endpoint 12."""

    cluster_id: Final = TWINGUARD_SETUP_CLUSTER
    ep_attribute: Final = "twinguard_setup"

    class AttributeDefs(BaseAttributeDefs):
        """Bosch Twinguard setup cluster attributes."""

        heartbeat: Final = ZCLAttributeDef(
            id=0x5005,
            type=t.bitmap8,
            access="rwp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Bosch Twinguard setup cluster server commands."""

        pairing_completed: Final = ZCLCommandDef(
            id=0x01,
            schema={},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    async def apply_custom_configuration(self, *args, **kwargs):
        """Perform the Bosch-specific join handshake and initialize defaults."""
        device = self.endpoint.device
        endpoint_1 = device.endpoints[1]
        endpoint_3 = device.endpoints[3]

        await device.endpoints[7].in_clusters[PollControl.cluster_id].bind()
        await endpoint_1.in_clusters[Alarms.cluster_id].bind()
        await endpoint_1.in_clusters[TWINGUARD_SMOKE_CLUSTER].bind()
        await endpoint_1.in_clusters[TWINGUARD_OPTIONS_CLUSTER].bind()
        await endpoint_3.in_clusters[TWINGUARD_MEASUREMENTS_CLUSTER].bind()
        await self.bind()
        await self.endpoint.in_clusters[TWINGUARD_ALARM_CLUSTER].bind()

        # Both operations, in this order, are required for the Twinguard to
        # accept the coordinator. Without them it flashes red after joining.
        options = endpoint_1.in_clusters[TWINGUARD_OPTIONS_CLUSTER]
        await options.read_attributes(
            [BoschTwinguardOptionsCluster.AttributeDefs.pairing_state.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )
        await self.command(
            self.ServerCommandDefs.pairing_completed.id,
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )

        # Match the Bosch defaults and prime the ZHA attribute cache.
        smoke = endpoint_1.in_clusters[TWINGUARD_SMOKE_CLUSTER]
        await smoke.write_attributes(
            {
                BoschTwinguardSmokeCluster.AttributeDefs.sensitivity.id: TwinguardSensitivity.Medium
            },
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )
        await options.write_attributes(
            {BoschTwinguardOptionsCluster.AttributeDefs.pre_alarm.id: 0x01},
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )
        await self.write_attributes(
            {self.AttributeDefs.heartbeat.id: 0x01},
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )
        await smoke.read_attributes(
            [BoschTwinguardSmokeCluster.AttributeDefs.sensitivity.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )
        await options.read_attributes(
            [BoschTwinguardOptionsCluster.AttributeDefs.pre_alarm.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )
        await self.read_attributes(
            [self.AttributeDefs.heartbeat.id],
            manufacturer=BOSCH_MANUFACTURER_CODE,
        )


class BoschTwinguardAlarmCluster(CustomCluster):
    """Alarm state and burglar-siren control on endpoint 12."""

    cluster_id: Final = TWINGUARD_ALARM_CLUSTER
    ep_attribute: Final = "twinguard_alarm"

    class AttributeDefs(BaseAttributeDefs):
        """Bosch Twinguard alarm cluster attributes."""

        alarm_status: Final = ZCLAttributeDef(
            id=0x5000,
            type=t.bitmap32,
            access="rp",
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    class ServerCommandDefs(BaseCommandDefs):
        """Bosch Twinguard alarm cluster server commands."""

        burglar_alarm: Final = ZCLCommandDef(
            id=0x01,
            schema={"data": t.uint8_t},
            manufacturer_code=BOSCH_MANUFACTURER_CODE,
        )

    def _update_attribute(self, attrid, value):
        """Synchronize the local siren state with reported alarm state."""
        super()._update_attribute(attrid, value)
        if attrid != self.AttributeDefs.alarm_status.id:
            return

        siren_control = self.endpoint.device.endpoints[1].in_clusters.get(
            TWINGUARD_SIREN_CONTROL_CLUSTER
        )
        if siren_control is None:
            return

        siren_states = {
            CLEAR_ALARM_STATUS: TwinguardSirenState.Clear,
            SELF_TEST_ALARM_STATUS: TwinguardSirenState.Self_test,
            BURGLAR_ALARM_STATUS: TwinguardSirenState.Burglar,
            PRE_ALARM_STATUS: TwinguardSirenState.Pre_alarm,
            FIRE_ALARM_STATUS: TwinguardSirenState.Fire,
            SILENCED_ALARM_STATUS: TwinguardSirenState.Silenced,
        }
        if value in siren_states:
            siren_control.update_siren_state(siren_states[value])


class BoschTwinguardSirenControl(LocalDataCluster):
    """Local alarm-mode control and reported siren state."""

    cluster_id: Final = TWINGUARD_SIREN_CONTROL_CLUSTER
    ep_attribute: Final = "twinguard_siren_control"

    class AttributeDefs(BaseAttributeDefs):
        """Local Twinguard siren control attributes."""

        alarm_mode: Final = ZCLAttributeDef(
            id=0x0000,
            type=TwinguardAlarmMode,
            access="rwp",
        )
        siren_state: Final = ZCLAttributeDef(
            id=0x0001,
            type=TwinguardSirenState,
            access="rp",
        )

    _DEFAULT_VALUES = {
        AttributeDefs.alarm_mode.id: TwinguardAlarmMode.Stop,
        AttributeDefs.siren_state.id: TwinguardSirenState.Clear,
    }

    def update_siren_state(self, state: TwinguardSirenState) -> None:
        """Update reported state and synchronize the alarm-mode selector."""
        self._update_attribute(self.AttributeDefs.siren_state.id, state)
        mode_by_state = {
            TwinguardSirenState.Clear: TwinguardAlarmMode.Stop,
            TwinguardSirenState.Silenced: TwinguardAlarmMode.Stop,
            TwinguardSirenState.Burglar: TwinguardAlarmMode.Burglar,
            TwinguardSirenState.Pre_alarm: TwinguardAlarmMode.Pre_alarm,
            TwinguardSirenState.Fire: TwinguardAlarmMode.Fire,
        }
        if state in mode_by_state:
            self._update_attribute(
                self.AttributeDefs.alarm_mode.id,
                mode_by_state[state],
            )

    async def write_attributes(self, attributes, **kwargs):
        """Translate alarm-mode selections to Bosch alarm commands."""
        requested_mode = None
        for attribute, value in attributes.items():
            attribute_id = self.find_attribute(attribute).id
            if attribute_id == self.AttributeDefs.alarm_mode.id:
                requested_mode = TwinguardAlarmMode(value)
            elif attribute_id == self.AttributeDefs.siren_state.id:
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            status=foundation.Status.READ_ONLY,
                            attrid=attribute_id,
                        )
                    ]
                ]

        if requested_mode is None:
            return await super().write_attributes(attributes, **kwargs)

        await set_bosch_alarm_mode(self.endpoint.device, requested_mode)
        state_by_mode = {
            TwinguardAlarmMode.Stop: TwinguardSirenState.Clear,
            TwinguardAlarmMode.Pre_alarm: TwinguardSirenState.Pre_alarm,
            TwinguardAlarmMode.Fire: TwinguardSirenState.Fire,
            TwinguardAlarmMode.Burglar: TwinguardSirenState.Burglar,
        }
        self.update_siren_state(state_by_mode[requested_mode])
        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


(
    QuirkBuilder("BOSCH ST", "Champion")
    .applies_to("BoschSmartHomeGmbH", "Champion")
    .replaces(BoschTwinguardAlarmsCluster, endpoint_id=1)
    .replaces(BoschTwinguardSmokeCluster, endpoint_id=1)
    .replaces(BoschTwinguardMeasurementsCluster, endpoint_id=3)
    .replaces(BoschTwinguardOptionsCluster, endpoint_id=1)
    .replaces(BoschTwinguardSetupCluster, endpoint_id=12)
    .replaces(BoschTwinguardAlarmCluster, endpoint_id=12)
    .adds(BoschTwinguardSirenControl, endpoint_id=1)
    # All usable measurements arrive through the manufacturer cluster. The
    # corresponding standard clusters either remain stale or contain placeholders.
    .prevent_default_entity_creation(
        endpoint_id=4,
        cluster_id=PowerConfiguration.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=5,
        cluster_id=TemperatureMeasurement.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=6,
        cluster_id=IlluminanceMeasurement.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=8,
        cluster_id=PressureMeasurement.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=9,
        cluster_id=RelativeHumidity.cluster_id,
    )
    .prevent_default_entity_creation(
        endpoint_id=11,
        cluster_id=CarbonMonoxideConcentration.cluster_id,
    )
    .sensor(
        BoschTwinguardMeasurementsCluster.AttributeDefs.temperature.name,
        TWINGUARD_MEASUREMENTS_CLUSTER,
        endpoint_id=3,
        divisor=100,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        fallback_name="Temperature",
    )
    .sensor(
        BoschTwinguardMeasurementsCluster.AttributeDefs.humidity.name,
        TWINGUARD_MEASUREMENTS_CLUSTER,
        endpoint_id=3,
        divisor=100,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        fallback_name="Humidity",
    )
    .sensor(
        BoschTwinguardMeasurementsCluster.AttributeDefs.battery.name,
        TWINGUARD_MEASUREMENTS_CLUSTER,
        endpoint_id=3,
        divisor=2,
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        fallback_name="Battery",
    )
    .sensor(
        BoschTwinguardMeasurementsCluster.AttributeDefs.illuminance.name,
        TWINGUARD_MEASUREMENTS_CLUSTER,
        endpoint_id=3,
        divisor=2,
        unit=LIGHT_LUX,
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
        fallback_name="Illuminance",
    )
    .sensor(
        BoschTwinguardMeasurementsCluster.AttributeDefs.air_purity.name,
        TWINGUARD_MEASUREMENTS_CLUSTER,
        endpoint_id=3,
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        unique_id_suffix="aqi",
        fallback_name="Air quality index",
    )
    .sensor(
        BoschTwinguardMeasurementsCluster.AttributeDefs.air_purity.name,
        TWINGUARD_MEASUREMENTS_CLUSTER,
        endpoint_id=3,
        attribute_converter=lambda value: value * 10 + 500,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        unique_id_suffix="eco2",
        fallback_name="eCO2",
    )
    .binary_sensor(
        BoschTwinguardAlarmCluster.AttributeDefs.alarm_status.name,
        TWINGUARD_ALARM_CLUSTER,
        endpoint_id=12,
        entity_type=EntityType.STANDARD,
        attribute_converter=lambda value: bool(value & (1 << 7)),
        device_class=BinarySensorDeviceClass.SMOKE,
        unique_id_suffix="smoke",
        fallback_name="Smoke",
    )
    .binary_sensor(
        BoschTwinguardAlarmCluster.AttributeDefs.alarm_status.name,
        TWINGUARD_ALARM_CLUSTER,
        endpoint_id=12,
        attribute_converter=lambda value: bool(value & (1 << 24)),
        unique_id_suffix="self_test_active",
        translation_key="self_test_active",
        fallback_name="Self-test active",
    )
    .command_button(
        BoschTwinguardSmokeCluster.ServerCommandDefs.initiate_test_mode.name,
        TWINGUARD_SMOKE_CLUSTER,
        endpoint_id=1,
        translation_key="start_self_test",
        fallback_name="Start self-test",
    )
    .switch(
        BoschTwinguardOptionsCluster.AttributeDefs.pre_alarm.name,
        TWINGUARD_OPTIONS_CLUSTER,
        endpoint_id=1,
        translation_key="pre_alarm",
        fallback_name="Pre-alarm",
    )
    .switch(
        BoschTwinguardSetupCluster.AttributeDefs.heartbeat.name,
        TWINGUARD_SETUP_CLUSTER,
        endpoint_id=12,
        translation_key="heartbeat_led",
        fallback_name="Heartbeat LED",
    )
    .enum(
        BoschTwinguardSirenControl.AttributeDefs.alarm_mode.name,
        TwinguardAlarmMode,
        TWINGUARD_SIREN_CONTROL_CLUSTER,
        endpoint_id=1,
        entity_type=EntityType.STANDARD,
        translation_key="alarm_mode",
        fallback_name="Alarm mode",
    )
    .enum(
        BoschTwinguardSirenControl.AttributeDefs.siren_state.name,
        TwinguardSirenState,
        TWINGUARD_SIREN_CONTROL_CLUSTER,
        endpoint_id=1,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        unique_id_suffix="siren_state",
        translation_key="siren_state",
        fallback_name="Siren state",
    )
    .enum(
        BoschTwinguardSmokeCluster.AttributeDefs.sensitivity.name,
        TwinguardSensitivity,
        TWINGUARD_SMOKE_CLUSTER,
        endpoint_id=1,
        translation_key="smoke_sensitivity",
        fallback_name="Smoke sensitivity",
    )
    .add_to_registry()
)
