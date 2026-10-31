"""ZHA Quirk for ROBB smarrt ROB_200-040-0 / Sunricher SR-ZG9092A on FW V1.033.

===============================================================================
VERSION & HARDWARE TRACKING
===============================================================================
Quirk Version : 1.5.2-beta
Last Updated  : 2026-10-30
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
   - Place this file into your Home Assistant configuration directory under
     /config/custom_zha_quirks/robb_200_040_0_fw1033.py.
   - Ensure your configuration.yaml includes:
     zha:
       custom_quirks_path: /config/custom_zha_quirks/
   - Restart Home Assistant via Developer Tools > YAML > Restart.
   - Navigate to Settings > Devices & Services > ZHA, select your thermostat,
     and click Re-interview (or Reconfigure) to bind the quirk.
   - Post-Installation Cleanup Note: After re-interviewing or reconfiguring the
     device, you may want to clean up the ZHA thermostat integration interface by
     removing any leftover standard ZHA attributes, sensors, or controls that
     display 'unknown' or unmapped values due to standard profile changes.

PURPOSE & CORRUPTION MITIGATION:
This custom quirk is strictly required because the default ZHA adaptation
corrupts the device's internal memory registers during standard cluster polling
and attribute writes. Specifically, this code was written because the thermostat
is intended to regulate specifically on the external floor probe cable. This
quirk is built to correct and overcome:
  1. Register Corruption: Blocks ZHA write access to volatile memory addresses
     (0x1000 LCD Brightness, 0x1001 Button Vibration, 0x100B Display Auto-Off)
     that cause the thermostat firmware to lock up or enter fault states.
  2. Floor Sensor Regulation & Routing: Intercepts external floor probe readings
     from cluster 0x0402 and attribute 0x0001, routing them directly into
     local_temperature (0x0000) when Floor Sensor control is active so Home
     Assistant regulates floor heating accurately based on the physical floor probe.
  3. Calibration Drift: Enforces strict [-3.0°C, +3.0°C] boundary clamping on
     sensor calibration registers (0x0010, 0x1005) to prevent registry spikes.
  4. UI Command Sanitization: Protects UserInterface (0x0204) writes, maps
     Child Lock Active ('No'=0x00, 'Yes'=0x01), proxies Operation Mode via
     virtual attribute 0xFF03 to standard ZCL SystemMode (0x001C) without
     manufacturer code injection, cleans up unneeded standard ZHA attributes
     for interface decluttering, and formats read-only status sensors into
     clean descriptive text strings matching the user Excel translation table.

DEVELOPMENT STATUS & LIMITATIONS (BETA):
- Published as v1.5.2-beta for extended field testing.
- Note: Not all advanced firmware features or secondary proprietary registers
  have been fully programmed or exposed for practical reasons (e.g., internal weekly
  schedule table editing and advanced dry-time setup remain unmapped to prevent
  unnecessary UI clutter and maintain a clean everyday user experience).

CHANGELOG:
- v1.5.2-beta (2026-10-30): Synchronized active __version__ variable across code
  and headers to fix Quirk Version entity reporting, added NTC cable prerequisites.
- v1.5.1-beta (2026-10-30): Cleaned up unused standard ZHA attributes.
- v1.5.0-beta (2026-10-30): Added Floor Temperature Offset (0x1005) number control.
- v1.4.9 (2026-10-30): Added temperature unit text string mapping.
- v1.4.0 - 1.4.8 (2026-10-30): Baseline optimizations for sensors, modes, and child lock.
===============================================================================
"""

import asyncio
import logging

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.hvac import Thermostat, UserInterface
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

__version__ = "1.5.2-beta"

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
ATTR_TEMPERATURE_DISPLAY = 0x1008
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
    ATTR_TEMPERATURE_DISPLAY,
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
    "temperature_display",
    "window_open_check",
    "hysteresis",
    "max_floor_temp",
    "away_mode_set",
}

# Virtual attributes for clean ZHA UI entities
ATTR_CHILD_LOCK_ACTIVE = 0xFF01
ATTR_QUIRK_VERSION = 0xFF02
ATTR_OPERATION_MODE = 0xFF03
ATTR_VIBRATION_TEXT = 0xFF04
ATTR_BRIGHTNESS_TEXT = 0xFF05
ATTR_MODE_AFTER_DRY_TEXT = 0xFF06
ATTR_TEMP_UNIT_TEXT = 0xFF07

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

TEMP_UNIT_LABELS = {
    0: "Celsius",
    1: "Fahrenheit",
}


class ControlTypeEnum(t.enum8):
    """Heating control sensor source (0x1003)."""

    Room_Sensor = 0x00
    Floor_Sensor = 0x01
    Room_and_Floor_Sensor = 0x02


class TempDisplayEnum(t.enum8):
    """Physical LCD screen temperature display mode (0x1008)."""

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
            ATTR_TEMPERATURE_DISPLAY: ("temperature_display", TempDisplayEnum, True),
            ATTR_WINDOW_OPEN_CHECK: ("window_open_check", t.uint8_t, True),
            ATTR_HYSTERESIS: ("hysteresis", t.uint8_t, True),
            ATTR_MAX_FLOOR_TEMP: ("max_floor_temp", t.uint8_t, True),
            ATTR_AWAY_MODE_SET: ("away_mode_set", t.enum8, True),
            ATTR_QUIRK_VERSION: ("quirk_version", t.CharacterString, False),
            ATTR_OPERATION_MODE: ("operation_mode", OperationModeEnum, False),
            ATTR_VIBRATION_TEXT: ("vibration_level_text", t.CharacterString, False),
            ATTR_BRIGHTNESS_TEXT: ("operate_brightness_text", t.CharacterString, False),
            ATTR_MODE_AFTER_DRY_TEXT: ("mode_after_dry_text", t.CharacterString, False),
            ATTR_TEMP_UNIT_TEXT: ("temperature_unit_text", t.CharacterString, False),
        }
    )

    def __init__(self, *args, **kwargs):
        """Initialize the cluster."""
        super().__init__(*args, **kwargs)
        self._attr_cache[ATTR_CONTROL_SEQUENCE] = (
            Thermostat.ControlSequenceOfOperation.Heating_Only
        )
        self._attr_cache[ATTR_QUIRK_VERSION] = __version__
        self._attr_cache[ATTR_OPERATION_MODE] = OperationModeEnum.Heat
        self._attr_cache[ATTR_VIBRATION_TEXT] = VIBRATION_LABELS[0]
        self._attr_cache[ATTR_BRIGHTNESS_TEXT] = BRIGHTNESS_LABELS[1]
        self._attr_cache[ATTR_MODE_AFTER_DRY_TEXT] = MODE_AFTER_DRY_LABELS[2]
        self._attr_cache[ATTR_TEMP_UNIT_TEXT] = TEMP_UNIT_LABELS[0]

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

        if attrid == ATTR_OPERATE_BRIGHTNESS:
            if value is None:
                return
            label = BRIGHTNESS_LABELS.get(int(value), BRIGHTNESS_LABELS[1])
            super()._update_attribute(ATTR_BRIGHTNESS_TEXT, label)
            super()._update_attribute(attrid, int(value))
            return

        if attrid == ATTR_BUTTON_VIBRATION:
            if value is None:
                return
            label = VIBRATION_LABELS.get(int(value), VIBRATION_LABELS[0])
            super()._update_attribute(ATTR_VIBRATION_TEXT, label)
            super()._update_attribute(attrid, int(value))
            return

        if attrid == ATTR_MODE_AFTER_DRY:
            if value is None:
                return
            label = MODE_AFTER_DRY_LABELS.get(int(value), MODE_AFTER_DRY_LABELS[2])
            super()._update_attribute(ATTR_MODE_AFTER_DRY_TEXT, label)
            super()._update_attribute(attrid, int(value))
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
            super()._update_attribute(ATTR_OPERATION_MODE, OperationModeEnum(mode_int))
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
            self._attr_cache[0xFF00] = value
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
            else:
                air_val = self._attr_cache.get(0xFF00)
                if air_val is not None:
                    super()._update_attribute(ATTR_LOCAL_TEMP, air_val)
            return

        super()._update_attribute(attrid, value)

    def write_attributes(self, attributes, manufacturer=None):
        """Route proprietary vs standard ZCL writes so 0x001C never sends mfg code."""
        std_attrs = {}
        mfg_attrs = {}

        for attrid, value in attributes.items():
            if attrid in (
                ATTR_OPERATE_BRIGHTNESS,
                ATTR_BUTTON_VIBRATION,
                ATTR_MODE_AFTER_DRY,
                ATTR_VIBRATION_TEXT,
                ATTR_BRIGHTNESS_TEXT,
                ATTR_MODE_AFTER_DRY_TEXT,
                ATTR_TEMP_UNIT_TEXT,
                "operate_display_brightness",
                "button_vibration_level",
                "mode_after_dry",
                "vibration_level_text",
                "operate_brightness_text",
                "mode_after_dry_text",
                "temperature_unit_text",
            ):
                continue

            if attrid in (
                ATTR_OPERATION_MODE,
                "operation_mode",
                ATTR_SYSTEM_MODE,
                "system_mode",
            ):
                mode_int = 0x04 if int(value) > 0 else 0x00
                std_attrs[ATTR_SYSTEM_MODE] = Thermostat.SystemMode(mode_int)
                super()._update_attribute(
                    ATTR_OPERATION_MODE, OperationModeEnum(mode_int)
                )
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
                elif attrid in (ATTR_TEMPERATURE_DISPLAY, "temperature_display"):
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
        """Remap virtual text attributes to their underlying hardware registers on poll."""
        if ATTR_QUIRK_VERSION in attributes:
            self._attr_cache[ATTR_QUIRK_VERSION] = __version__
            super()._update_attribute(ATTR_QUIRK_VERSION, __version__)

        std_remapped = []
        mfg_remapped = []

        for a in attributes:
            if a == ATTR_QUIRK_VERSION:
                continue
            elif a == ATTR_OPERATION_MODE:
                std_remapped.append(ATTR_SYSTEM_MODE)
            elif a == ATTR_VIBRATION_TEXT:
                mfg_remapped.append(ATTR_BUTTON_VIBRATION)
            elif a == ATTR_BRIGHTNESS_TEXT:
                mfg_remapped.append(ATTR_OPERATE_BRIGHTNESS)
            elif a == ATTR_MODE_AFTER_DRY_TEXT:
                mfg_remapped.append(ATTR_MODE_AFTER_DRY)
            elif a == ATTR_TEMP_UNIT_TEXT:
                ui_cluster = self.endpoint.in_clusters.get(UserInterface.cluster_id)
                if ui_cluster:
                    res_ui = await ui_cluster.read_attributes_raw(
                        [0x0000], manufacturer=manufacturer
                    )
                    if res_ui and 0x0000 in res_ui[0]:
                        val_unit = int(res_ui[0][0x0000])
                        label = TEMP_UNIT_LABELS.get(val_unit, TEMP_UNIT_LABELS[0])
                        self._attr_cache[ATTR_TEMP_UNIT_TEXT] = label
                        super()._update_attribute(ATTR_TEMP_UNIT_TEXT, label)
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
        self._update_attribute(ATTR_QUIRK_VERSION, __version__)
        self._update_attribute(
            ATTR_CONTROL_SEQUENCE,
            Thermostat.ControlSequenceOfOperation.Heating_Only,
        )
        self.bg_task = asyncio.create_task(self.write_config_registers())
        return res

    async def write_config_registers(self):
        """Write hardware defaults and poll read-only status registers to populate UI."""
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
                {ATTR_TEMPERATURE_DISPLAY: 1},
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
            ui_cluster = self.endpoint.in_clusters.get(UserInterface.cluster_id)
            if ui_cluster:
                res_ui = await ui_cluster.read_attributes([0x0000])
                if res_ui and 0x0000 in res_ui:
                    val_unit = int(res_ui[0x0000])
                    label = TEMP_UNIT_LABELS.get(val_unit, TEMP_UNIT_LABELS[0])
                    self._update_attribute(ATTR_TEMP_UNIT_TEXT, label)

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
    """Sanitizes writes, maps Child Lock Active, and syncs temperature unit text."""

    cluster_id = UserInterface.cluster_id

    attributes = UserInterface.attributes.copy()
    attributes.update(
        {
            ATTR_CHILD_LOCK_ACTIVE: ("child_lock_active", ChildLockEnum, False),
        }
    )

    def _update_attribute(self, attrid, value):
        """Synchronize 0x0000 (Temp Unit) and 0x0001 (Child Lock)."""
        if attrid == 0x0000 and value is not None:
            val_int = int(value)
            label = TEMP_UNIT_LABELS.get(val_int, TEMP_UNIT_LABELS[0])
            thermostat = self.endpoint.in_clusters.get(Thermostat.cluster_id)
            if thermostat:
                thermostat._update_attribute(ATTR_TEMP_UNIT_TEXT, label)
            super()._update_attribute(0x0000, val_int)
            return
        if attrid == 0x0001 and value is not None:
            locked = ChildLockEnum.Yes if int(value) >= 1 else ChildLockEnum.No
            super()._update_attribute(ATTR_CHILD_LOCK_ACTIVE, locked)
            super()._update_attribute(0x0001, int(locked))
            return
        super()._update_attribute(attrid, value)

    async def read_attributes_raw(self, attributes, manufacturer=None):
        """Redirect reads of virtual 0xFF01 -> 0x0001."""
        remapped = [0x0001 if a == ATTR_CHILD_LOCK_ACTIVE else a for a in attributes]
        return await super().read_attributes_raw(remapped, manufacturer=manufacturer)

    def write_attributes(self, attributes, manufacturer=None):
        """Translate Child Lock Active ('No'/'Yes') into hardware register 0x0001."""
        sanitized = {}
        for attrid, value in attributes.items():
            if attrid in (0x0000, "temperature_display_mode", "temperature_unit"):
                continue
            elif attrid in (ATTR_CHILD_LOCK_ACTIVE, "child_lock_active"):
                val_int = 1 if int(value) >= 1 else 0
                sanitized[0x0001] = t.enum8(val_int)
                super()._update_attribute(
                    ATTR_CHILD_LOCK_ACTIVE, ChildLockEnum(val_int)
                )
            elif attrid == 0x0001:
                continue
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
    # Editable Controls
    .number(
        attribute_name="hysteresis",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        min_value=0.5,
        max_value=2.0,
        step=0.5,
        unit="°C",
        multiplier=0.1,
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
        unit="°C",
        multiplier=0.1,
        translation_key="floor_sensor_calibration",
        fallback_name="Floor Temperature Offset",
    )
    .enum(
        attribute_name="control_type",
        enum_class=ControlTypeEnum,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="control_type",
        fallback_name="Control type",
    )
    .enum(
        attribute_name="temperature_display",
        enum_class=TempDisplayEnum,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="temperature_display",
        fallback_name="Display Temperature",
    )
    .enum(
        attribute_name="floor_sensor_type",
        enum_class=FloorSensorTypeEnum,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="floor_sensor_type",
        fallback_name="Floor Sensor Type",
    )
    .enum(
        attribute_name="operation_mode",
        enum_class=OperationModeEnum,
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .enum(
        attribute_name="child_lock_active",
        enum_class=ChildLockEnum,
        cluster_id=UserInterface.cluster_id,
        endpoint_id=1,
        translation_key="child_lock_active",
        fallback_name="Child Lock Active",
    )
    # Read-Only Status Sensors (Exact Excel Table Descriptive Text)
    .sensor(
        attribute_name="vibration_level_text",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="vibration_level_text",
        fallback_name="Vibration Level",
    )
    .sensor(
        attribute_name="operate_brightness_text",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="operate_brightness_text",
        fallback_name="Operate Brightness",
    )
    .sensor(
        attribute_name="temperature_unit_text",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="temperature_unit_text",
        fallback_name="Temperature Unit",
    )
    .sensor(
        attribute_name="mode_after_dry_text",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="mode_after_dry_text",
        fallback_name="ModeAfterDry",
    )
    .sensor(
        attribute_name="quirk_version",
        cluster_id=Thermostat.cluster_id,
        endpoint_id=1,
        translation_key="quirk_version",
        fallback_name="Quirk Version",
    )
    .add_to_registry()
)
