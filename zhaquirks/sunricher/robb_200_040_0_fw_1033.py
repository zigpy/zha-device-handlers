"""ZHA Quirk for ROBB smarrt ROB_200-040-0 / Sunricher SR-ZG9092A on FW V1.033.

===============================================================================
VERSION & HARDWARE TRACKING
===============================================================================
Quirk Version : 1.5.17-beta
Last Updated  : 2026-11-01
Target Device : Sunricher SR-ZG9092A / ROBB smarrt ROB_200-040-0
CoreVer       : V1.033
ZigbeeVer     : V23.00 (0x00000017)
Manufacturer  : 0x1224 (Sunricher / ROBB smarrt)

PREREQUISITES & INSTALLATION GUIDE:
1. System & Hardware Prerequisites:
   - Home Assistant Core with ZHA (Zigbee Home Automation) enabled.
   - Target Hardware: ROBB smarrt / Sunricher SR-ZG9092A Floor Heating Thermostat
     (ROB_200-040-0) running CoreVer V1.033 and ZigbeeVer V23.00.
   - External NTC Floor Sensor Cable: A physically wired, compatible NTC floor probe
     must be connected to the thermostat's probe terminals, as this code is explicitly
     built to regulate heating based on the physical floor temperature.
2. Installation Steps:
   - Place this file into your Home Assistant configuration directory as
     /config/custom_zha_quirks/robb_200_040_0_fw_1033.py.
   - Ensure your configuration.yaml includes:
     zha:
       custom_quirks_path: /config/custom_zha_quirks/
   - Restart Home Assistant via Developer Tools > YAML > Restart.
   - Navigate to Settings > Devices & Services > ZHA, select your thermostat,
     and click Re-interview (or Reconfigure) to bind the quirk.
   - After reconfiguring the device, check its entity list for obsolete entities
     left by an earlier quirk version. Remove only stale entities that are no
     longer provided by this quirk.

PURPOSE & CORRUPTION MITIGATION:
This custom quirk is strictly required because the default ZHA adaptation
corrupts the device's internal memory registers during standard cluster polling
and attribute writes. This quirk was written because the thermostat is intended
to regulate using the external floor probe cable. It addresses:
  1. Register Corruption: Blocks writes to volatile memory addresses (0x1000,
     0x1001, 0x100B) that can cause the thermostat firmware to lock up.
  2. Floor Sensor Regulation & Routing: Intercepts external floor probe readings
     from cluster 0x0402 and attribute 0x0001, routing them directly into
     local_temperature (0x0000) when Floor Sensor control is active so Home
     Assistant regulates floor heating accurately based on the physical floor probe.
  3. Calibration Drift: Enforces strict [-3.0°C, +3.0°C] boundary clamping on
     sensor calibration registers (0x0010, 0x1005) to prevent registry spikes.
  4. UI Command Sanitization: Validates UserInterface (0x0204) writes and
     exposes operation mode and readable status labels directly from their
     underlying ZCL attributes.

CHANGELOG:
- v1.5.17-beta (2026-11-01): Expose the Basic-cluster application version
  (attribute 0x0001) as a sensor; remove the unrelated OTA version read.
- v1.5.15-beta (2026-11-01): Categorize temperature scale and keypad lock as config
  controls so read-only sensors are grouped before the controls in Home Assistant.
- v1.5.14-beta (2026-11-01): Use the public default-entity suppression helper's
  unique-ID filter instead of importing EntityFilter from the builder facade.
- v1.5.13-beta (2026-11-01): Expose editable temperature-scale and binary keypad-lock
  controls by limiting UI entity suppression to ZHA's built-in keypad-lockout entity.
  Mark the aliased standard UI attributes as non-manufacturer-specific.
- v1.5.12-beta (2026-11-01): Fixed fatal ImportError that was crashing the quirk.
  Removed invalid standard TemperatureDisplayMode import and replaced with a safely
  defined custom TempUnitEnum[cite: 1, 3].
===============================================================================
"""

import asyncio
import logging
from typing import Any

import zigpy.types as t
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks.builder import QuirkBuilder, UnitOfTemperature
from zhaquirks.clusters import CustomCluster

__version__ = "1.5.17-beta"

_LOGGER = logging.getLogger(__name__)

SUNRICHER_MANUFACTURER_CODE = 0x1224

# Standard ZCL Thermostat attributes (MUST NOT use manufacturer code)
ATTR_LOCAL_TEMP = 0x0000
ATTR_OUTDOOR_TEMP = 0x0001
ATTR_LOCAL_TEMP_CALIBRATION = 0x0010
ATTR_CONTROL_SEQUENCE = 0x001B
ATTR_SYSTEM_MODE = 0x001C

# Sunricher proprietary attribute IDs (Require manufacturer code 0x1224)
ATTR_OPERATE_BRIGHTNESS = 0x1000
ATTR_BUTTON_VIBRATION = 0x1001
ATTR_FLOOR_SENSOR_TYPE = 0x1002
ATTR_CONTROL_TYPE = 0x1003
ATTR_POWER_UP_STATUS = 0x1004
ATTR_FLOOR_SENSOR_CALIBRATION = 0x1005
ATTR_DRY_TIME = 0x1006
ATTR_MODE_AFTER_DRY = 0x1007
ATTR_LCD_DISPLAY_SOURCE = 0x1008
ATTR_WINDOW_OPEN_CHECK = 0x1009
ATTR_HYSTERESIS = 0x100A
ATTR_DISPLAY_AUTO_OFF = 0x100B
ATTR_MAX_FLOOR_TEMP = 0x2001
ATTR_AWAY_MODE_SET = 0x2002

PROPRIETARY_ATTRS = {
    ATTR_OPERATE_BRIGHTNESS,
    ATTR_BUTTON_VIBRATION,
    ATTR_FLOOR_SENSOR_TYPE,
    ATTR_CONTROL_TYPE,
    ATTR_POWER_UP_STATUS,
    ATTR_FLOOR_SENSOR_CALIBRATION,
    ATTR_DRY_TIME,
    ATTR_MODE_AFTER_DRY,
    ATTR_LCD_DISPLAY_SOURCE,
    ATTR_WINDOW_OPEN_CHECK,
    ATTR_HYSTERESIS,
    ATTR_MAX_FLOOR_TEMP,
    ATTR_AWAY_MODE_SET,
    "operate_display_brightness",
    "button_vibration_level",
    "floor_sensor_type",
    "control_type",
    "power_up_status",
    "floor_sensor_calibration",
    "dry_time",
    "mode_after_dry",
    "lcd_display_source",
    "window_open_check",
    "hysteresis",
    "max_floor_temp",
    "away_mode_set",
}

BLOCKED_WRITE_ATTRS = {
    ATTR_OPERATE_BRIGHTNESS,
    ATTR_BUTTON_VIBRATION,
    ATTR_DISPLAY_AUTO_OFF,
    "operate_display_brightness",
    "button_vibration_level",
    "display_auto_off",
}

# Exact descriptive display mappings from the uploaded Excel table
VIBRATION_LABELS = {
    0: "Off",
    1: "Low",
    2: "High",
}

BRIGHTNESS_LABELS = {
    0: "Low Level",
    1: "Mid  Level",
    2: "High Level",
}

MODE_AFTER_DRY_LABELS = {
    0: "OFF",
    1: "Manual mode",
    2: "Auto mode -schedule",
    3: "Away mode",
}


def _mapped_label(value: Any, labels: dict[int, str], default: str) -> str | None:
    """Return a display label for a value reported by a real ZCL attribute."""
    if value is None:
        return None
    return labels.get(int(value), default)


class ControlTypeEnum(t.enum8):
    """Heating control  (0x1003)."""

    Room_Sensor = 0x00
    Floor_Sensor = 0x01
    Room_and_Floor_Sensor = 0x02


class TempDisplayEnum(t.enum8):
    """What sensor temperature to display on LCD ? (0x1008)."""

    Room_Temp = 0x00
    Floor_Temp = 0x01


class FloorSensorTypeEnum(t.enum8):
    """External NTC floor sensor resistance curve (0x1002), B(25/50°C)=3950."""

    NTC_10k_Ohm = 0x01
    NTC_15k_Ohm = 0x02
    NTC_50k_Ohm = 0x03
    NTC_100k_Ohm = 0x04
    NTC_12k_Ohm = 0x05


class ChildLockEnum(t.enum8):
    """Child Lock Active states ('No' = Unlocked, 'Yes' = Locked)."""

    No = 0x00
    Yes = 0x01


class TempUnitEnum(t.enum8):
    """Temperature display unit (0x0000)."""

    Celsius = 0x00
    Fahrenheit = 0x01


class OperationModeEnum(t.enum8):
    """Operation Mode states mapped to standard ZCL SystemMode (0x001C)."""

    Off = 0x00
    Heat = 0x04


class SunricherThermostatCluster(CustomCluster, Thermostat):
    """Custom Thermostat Cluster managing sensor redirection and registers."""

    cluster_id = Thermostat.cluster_id

    attributes = Thermostat.attributes.copy()
    attributes.update(
        {
            ATTR_OPERATE_BRIGHTNESS: ("operate_display_brightness", t.enum8, True),
            ATTR_BUTTON_VIBRATION: ("button_vibration_level", t.enum8, True),
            ATTR_FLOOR_SENSOR_TYPE: ("floor_sensor_type", FloorSensorTypeEnum, True),
            ATTR_CONTROL_TYPE: ("control_type", ControlTypeEnum, True),
            ATTR_POWER_UP_STATUS: ("power_up_status", t.enum8, True),
            ATTR_FLOOR_SENSOR_CALIBRATION: ("floor_sensor_calibration", t.int8s, True),
            ATTR_DRY_TIME: ("dry_time", t.uint8_t, True),
            ATTR_MODE_AFTER_DRY: ("mode_after_dry", t.enum8, True),
            ATTR_LCD_DISPLAY_SOURCE: ("lcd_display_source", TempDisplayEnum, True),
            ATTR_WINDOW_OPEN_CHECK: ("window_open_check", t.uint8_t, True),
            ATTR_HYSTERESIS: ("hysteresis", t.uint8_t, True),
            ATTR_MAX_FLOOR_TEMP: ("max_floor_temp", t.uint8_t, True),
            ATTR_AWAY_MODE_SET: ("away_mode_set", t.enum8, True),
        }
    )

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self._air_temp = None
        self._attr_cache[ATTR_CONTROL_SEQUENCE] = (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        )

    def _get_current_floor_temp(self):
        """Retrieve latest known floor temperature from outdoor_temp or cluster 0x0402."""
        if ATTR_OUTDOOR_TEMP in self._attr_cache:
            return self._attr_cache[ATTR_OUTDOOR_TEMP]
        probe_cluster = self.endpoint.in_clusters.get(TemperatureMeasurement.cluster_id)
        if probe_cluster and 0x0000 in probe_cluster._attr_cache:
            return probe_cluster._attr_cache[0x0000]
        return None

    def _update_attribute(self, attrid, value):
        """Intercept and remediate data tracking before passing to ZHA."""
        if attrid == ATTR_DISPLAY_AUTO_OFF:
            return

        if attrid == ATTR_CONTROL_SEQUENCE:
            super()._update_attribute(
                ATTR_CONTROL_SEQUENCE,
                Thermostat.ControlSequenceOfOperation.Heating_Only,
            )
            return

        if attrid in (ATTR_LOCAL_TEMP_CALIBRATION, ATTR_FLOOR_SENSOR_CALIBRATION):
            if value is not None:
                if value > 30:
                    value = 30
                elif value < -30:
                    value = -30

        if attrid == ATTR_FLOOR_SENSOR_TYPE and value is not None:
            try:
                value = FloorSensorTypeEnum(int(value))
            except ValueError:
                value = FloorSensorTypeEnum.NTC_12k_Ohm
        if attrid == ATTR_SYSTEM_MODE and value is not None:
            mode_int = 0x04 if int(value) > 0 else 0x00
            super()._update_attribute(ATTR_SYSTEM_MODE, Thermostat.SystemMode(mode_int))
            return

        if attrid == ATTR_OUTDOOR_TEMP:
            super()._update_attribute(ATTR_OUTDOOR_TEMP, value)
            current_mode = self._attr_cache.get(
                ATTR_CONTROL_TYPE, ControlTypeEnum.Floor_Sensor
            )
            if current_mode == ControlTypeEnum.Floor_Sensor:
                super()._update_attribute(ATTR_LOCAL_TEMP, value)
            return

        if attrid == ATTR_LOCAL_TEMP:
            self._air_temp = value
            current_mode = self._attr_cache.get(
                ATTR_CONTROL_TYPE, ControlTypeEnum.Floor_Sensor
            )
            if current_mode == ControlTypeEnum.Floor_Sensor:
                floor_val = self._get_current_floor_temp()
                if floor_val is not None:
                    super()._update_attribute(ATTR_LOCAL_TEMP, floor_val)
                    return
                return
            super()._update_attribute(ATTR_LOCAL_TEMP, value)
            return

        if attrid == ATTR_CONTROL_TYPE:
            super()._update_attribute(attrid, value)
            if value == ControlTypeEnum.Floor_Sensor:
                floor_val = self._get_current_floor_temp()
                if floor_val is not None:
                    super()._update_attribute(ATTR_LOCAL_TEMP, floor_val)
            elif self._air_temp is not None:
                super()._update_attribute(ATTR_LOCAL_TEMP, self._air_temp)
            return

        super()._update_attribute(attrid, value)

    def write_attributes(self, attributes, manufacturer=None):
        """Route proprietary vs standard ZCL writes so 0x001C never sends mfg code."""
        std_attrs = {}
        mfg_attrs = {}

        for attrid, value in attributes.items():
            if attrid in BLOCKED_WRITE_ATTRS:
                continue

            if attrid in (ATTR_SYSTEM_MODE, "system_mode"):
                mode_int = 0x04 if int(value) > 0 else 0x00
                std_attrs[ATTR_SYSTEM_MODE] = Thermostat.SystemMode(mode_int)
                super()._update_attribute(
                    ATTR_SYSTEM_MODE, Thermostat.SystemMode(mode_int)
                )
            elif attrid in PROPRIETARY_ATTRS:
                if attrid in (ATTR_FLOOR_SENSOR_TYPE, "floor_sensor_type"):
                    mfg_attrs[attrid] = (
                        int(value) if int(value) in (1, 2, 3, 4, 5) else 5
                    )
                elif attrid in (ATTR_CONTROL_TYPE, "control_type"):
                    mfg_attrs[attrid] = int(value) if int(value) in (0, 1, 2) else 1
                elif attrid in (ATTR_LCD_DISPLAY_SOURCE, "lcd_display_source"):
                    mfg_attrs[attrid] = int(value) if int(value) in (0, 1) else 1
                elif attrid in (
                    ATTR_FLOOR_SENSOR_CALIBRATION,
                    "floor_sensor_calibration",
                ):
                    scaled = int(round(float(value) * 10))
                    mfg_attrs[attrid] = max(-30, min(30, scaled))
                else:
                    mfg_attrs[attrid] = value
            else:
                std_attrs[attrid] = value

        if mfg_attrs and not std_attrs:
            return super().write_attributes(
                mfg_attrs, manufacturer=SUNRICHER_MANUFACTURER_CODE
            )
        if std_attrs and not mfg_attrs:
            return super().write_attributes(std_attrs, manufacturer=None)
        if mfg_attrs and std_attrs:
            self._bg_task = asyncio.create_task(
                super().write_attributes(
                    mfg_attrs, manufacturer=SUNRICHER_MANUFACTURER_CODE
                )
            )
            return super().write_attributes(std_attrs, manufacturer=None)

        return []

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Read standard and manufacturer-specific attributes without unsafe ones."""
        std_remapped = []
        mfg_remapped = []

        for a in attributes:
            if a in (ATTR_DISPLAY_AUTO_OFF, "display_auto_off"):
                continue
            elif a in PROPRIETARY_ATTRS:
                mfg_remapped.append(a)
            else:
                std_remapped.append(a)

        res = [{}]
        if mfg_remapped:
            res = await super().read_attributes_raw(
                mfg_remapped, manufacturer=SUNRICHER_MANUFACTURER_CODE
            )
        if std_remapped:
            res = await super().read_attributes_raw(std_remapped, manufacturer=None)

        current_mode = self._attr_cache.get(
            ATTR_CONTROL_TYPE, ControlTypeEnum.Floor_Sensor
        )
        if current_mode == ControlTypeEnum.Floor_Sensor:
            floor_val = self._get_current_floor_temp()
            if floor_val is not None and ATTR_LOCAL_TEMP in self._attr_cache:
                self._attr_cache[ATTR_LOCAL_TEMP] = floor_val
        return res

    async def bind(self):
        """Bind the cluster and apply hardware defaults."""
        res = await super().bind()
        self._update_attribute(
            ATTR_CONTROL_SEQUENCE,
            Thermostat.ControlSequenceOfOperation.Heating_Only,
        )
        self._bg_task = asyncio.create_task(self.write_config_registers())
        return res

    async def write_config_registers(self):
        """Apply hardware defaults and read device attributes needed by the UI."""
        try:
            await asyncio.sleep(3)
            await self.write_attributes(
                {ATTR_FLOOR_SENSOR_TYPE: 5},
                manufacturer=SUNRICHER_MANUFACTURER_CODE,
            )
            await self.write_attributes(
                {ATTR_CONTROL_TYPE: 1},
                manufacturer=SUNRICHER_MANUFACTURER_CODE,
            )
            await self.write_attributes(
                {ATTR_HYSTERESIS: 10},
                manufacturer=SUNRICHER_MANUFACTURER_CODE,
            )
            await self.write_attributes(
                {ATTR_LCD_DISPLAY_SOURCE: 1},
                manufacturer=SUNRICHER_MANUFACTURER_CODE,
            )
            await self.read_attributes([ATTR_SYSTEM_MODE], manufacturer=None)
            await self.read_attributes(
                [
                    ATTR_OPERATE_BRIGHTNESS,
                    ATTR_BUTTON_VIBRATION,
                    ATTR_MODE_AFTER_DRY,
                    ATTR_FLOOR_SENSOR_CALIBRATION,
                ],
                manufacturer=SUNRICHER_MANUFACTURER_CODE,
            )
            user_interface = self.endpoint.in_clusters.get(UserInterface.cluster_id)
            if user_interface is not None:
                await user_interface.read_attributes(
                    [
                        0x0000,
                        0x0001,
                    ],
                    manufacturer=None,
                )

            _LOGGER.info(
                "ROB_200-040-0 (Quirk v%s): Applied hardware registers successfully",
                __version__,
            )
        except Exception as err:
            _LOGGER.warning(
                "ROB_200-040-0 (Quirk v%s): Register initialization deferred: %s",
                __version__,
                err,
            )


class SunricherFloorProbeCluster(CustomCluster, TemperatureMeasurement):
    """Feeds cluster 0x0402 updates into the thermostat cluster."""

    cluster_id = TemperatureMeasurement.cluster_id

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == 0x0000:
            thermostat = self.endpoint.in_clusters.get(Thermostat.cluster_id)
            if thermostat:
                thermostat._update_attribute(ATTR_OUTDOOR_TEMP, value)


class SunricherUserInterfaceCluster(CustomCluster, UserInterface):
    """Sanitize writes to the thermostat user interface attributes."""

    cluster_id = UserInterface.cluster_id

    attributes = UserInterface.attributes.copy()
    attributes.update(
        {
            0x0000: ("temperature_unit_scale", TempUnitEnum, False),
            0x0001: ("keypad_lock_active", ChildLockEnum, False),
        }
    )

    def _update_attribute(self, attrid, value):
        """Normalize temperature units and the binary child-lock setting."""
        if attrid == 0x0000 and value is not None:
            super()._update_attribute(attrid, TempUnitEnum(int(value)))
            return
        if attrid == 0x0001 and value is not None:
            locked = ChildLockEnum.Yes if int(value) >= 1 else ChildLockEnum.No
            super()._update_attribute(attrid, locked)
            return
        super()._update_attribute(attrid, value)

    def write_attributes(self, attributes, manufacturer=None):
        """Validate and write standard user interface attributes."""
        sanitized = {}
        for attrid, value in attributes.items():
            if attrid in (0x0000, "temperature_unit_scale", "temperature_display_mode"):
                sanitized[0x0000] = TempUnitEnum(int(value))
            elif attrid in (0x0001, "keypad_lock_active", "keypad_lockout"):
                val_int = 1 if int(value) >= 1 else 0
                sanitized[0x0001] = val_int
            else:
                sanitized[attrid] = value

        if not sanitized:
            return []

        return super().write_attributes(sanitized, manufacturer=manufacturer)


# --- Register device and expose UI controls & Sensors via QuirkBuilder ---

(
    QuirkBuilder("ROBB smarrt", "ROB_200-040-0")
    .applies_to("ROBB Smarrt", "ROB_200-040-0")
    .applies_to("Sunricher", "ZG9092")
    .applies_to("Sunricher", "SR-ZG9092A")
    .replaces(SunricherThermostatCluster, endpoint_id=1)
    .replaces(SunricherFloorProbeCluster, endpoint_id=1)
    .replaces(SunricherUserInterfaceCluster, endpoint_id=1)
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=UserInterface.cluster_id,
        unique_id_suffix="keypad_lockout",
    )
    # Editable Controls
    .number(
        attribute_name="hysteresis",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        min_value=0.5,
        max_value=2.0,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="hysteresis",
        fallback_name="Hysteresis",
    )
    .number(
        attribute_name="floor_sensor_calibration",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        min_value=-3.0,
        max_value=3.0,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="floor_sensor_calibration",
        fallback_name="Floor Temperature Offset",
    )
    .enum(
        attribute_name="control_type",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        enum_class=ControlTypeEnum,
        translation_key="control_type",
        fallback_name="Control type",
    )
    .enum(
        attribute_name="lcd_display_source",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        enum_class=TempDisplayEnum,
        translation_key="lcd_display_source",
        fallback_name="LCD Sensor Source",
    )
    .enum(
        attribute_name="floor_sensor_type",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        enum_class=FloorSensorTypeEnum,
        translation_key="floor_sensor_type",
        fallback_name="Floor Sensor Type",
    )
    .enum(
        attribute_name=Thermostat.AttributeDefs.system_mode.name,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        enum_class=OperationModeEnum,
        unique_id_suffix="operation_mode",
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .enum(
        attribute_name="keypad_lock_active",
        cluster_id=UserInterface.cluster_id,
        endpoint_id=1,
        enum_class=ChildLockEnum,
        translation_key="keypad_lock_active",
        fallback_name="Child Lock Active",
    )
    .enum(
        attribute_name="temperature_unit_scale",
        cluster_id=UserInterface.cluster_id,
        endpoint_id=1,
        enum_class=TempUnitEnum,
        translation_key="temperature_unit_scale",
        fallback_name="Temperature Scale",
    )
    # Read-Only Status Sensors
    .sensor(
        attribute_name=Basic.AttributeDefs.app_version.name,
        cluster_id=Basic.cluster_id,
        endpoint_id=1,
        attribute_initialized_from_cache=False,
        translation_key="application_version",
        fallback_name="Application version",
    )
    .sensor(
        attribute_name="button_vibration_level",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        attribute_converter=lambda value: _mapped_label(
            value, VIBRATION_LABELS, VIBRATION_LABELS[0]
        ),
        unique_id_suffix="vibration_level_text",
        translation_key="vibration_level_text",
        fallback_name="Vibration Level",
    )
    .sensor(
        attribute_name="operate_display_brightness",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        attribute_converter=lambda value: _mapped_label(
            value, BRIGHTNESS_LABELS, BRIGHTNESS_LABELS[1]
        ),
        unique_id_suffix="operate_brightness_text",
        translation_key="operate_brightness_text",
        fallback_name="Operate Brightness",
    )
    .sensor(
        attribute_name="mode_after_dry",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        attribute_converter=lambda value: _mapped_label(
            value, MODE_AFTER_DRY_LABELS, MODE_AFTER_DRY_LABELS[2]
        ),
        unique_id_suffix="mode_after_dry_text",
        translation_key="mode_after_dry_text",
        fallback_name="ModeAfterDry",
    )
    .add_to_registry()
)
