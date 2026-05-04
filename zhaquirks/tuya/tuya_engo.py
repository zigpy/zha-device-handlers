"""ZHA quirk for Engo EONE-230W and E40-230 / E40-230W TS0601 thermostats."""

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster

# ---------- ENUMS ----------


class EngoSensorChoose(t.enum8):
    Internal = 0x00
    All = 0x01
    External = 0x02


class EngoRelayMode(t.enum8):
    NO = 0x00
    NC = 0x01
    OFF = 0x02


class EngoSensorError(t.enum8):
    Normal = 0x00
    E1 = 0x01
    E2 = 0x02


# ---------- CLUSTER ----------


class EngoThermostat(Thermostat, TuyaAttributesCluster):
    """Local thermostat cluster for Engo devices."""

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id
        )
        self.add_unsupported_attribute(Thermostat.AttributeDefs.pi_heating_demand.id)


# ---------- COMMON BUILDER ----------


def base_builder(ieee):
    return (
        TuyaQuirkBuilder(ieee, "TS0601")
        # DP 1: ON/OFF -> HVAC mode
        .tuya_dp(
            dp_id=1,
            ep_attribute=EngoThermostat.ep_attribute,
            attribute_name=EngoThermostat.AttributeDefs.system_mode.name,
            converter=lambda x: (
                Thermostat.SystemMode.Heat if x else Thermostat.SystemMode.Off
            ),
            dp_converter=lambda x: x != Thermostat.SystemMode.Off,
        )
        # DP 16: target temp (deci°C -> centi°C)
        .tuya_dp(
            dp_id=16,
            ep_attribute=EngoThermostat.ep_attribute,
            attribute_name=EngoThermostat.AttributeDefs.occupied_heating_setpoint.name,
            converter=lambda x: x * 10,
            dp_converter=lambda x: x // 10,
        )
        # DP 24: room temp
        .tuya_dp(
            dp_id=24,
            ep_attribute=EngoThermostat.ep_attribute,
            attribute_name=EngoThermostat.AttributeDefs.local_temperature.name,
            converter=lambda x: x * 10,
        )
        # DP 3: running state
        .tuya_dp(
            dp_id=3,
            ep_attribute=EngoThermostat.ep_attribute,
            attribute_name=EngoThermostat.AttributeDefs.running_state.name,
            converter=lambda x: {
                1: RunningState.Heat_State_On,
                2: RunningState.Idle,
            }.get(x, RunningState.Idle),
        )
        # DP 40: child lock
        .tuya_switch(
            dp_id=40,
            attribute_name="child_lock",
            translation_key="child_lock",
            fallback_name="Child lock",
        )
        # DP 44: backlight
        .tuya_number(
            dp_id=44,
            attribute_name="backlight",
            type=t.uint8_t,
            min_value=0,
            max_value=100,
            step=1,
            translation_key="backlight",
            fallback_name="Backlight",
        )
        # DP 120: sensor error
        .tuya_enum(
            dp_id=120,
            attribute_name="sensor_error",
            enum_class=EngoSensorError,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="sensor_error",
            fallback_name="Sensor error",
        )
        .adds(EngoThermostat)
        .skip_configuration()
    )


# ---------- DEVICE 1: EONE (with humidity) ----------

(
    base_builder("_TZE204_ca3i8m8p")
    # DP 34: humidity (only on EONE)
    .tuya_sensor(
        dp_id=34,
        attribute_name="humidity",
        type=t.uint16_t,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        unit="%",
        translation_key="humidity",
        fallback_name="Humidity",
    )
    .add_to_registry()
)


# ---------- DEVICE 2: E40 (no humidity by default) ----------

(base_builder("_TZE204_glk6viwg").add_to_registry())
