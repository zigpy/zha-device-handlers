"""Plugwise Emma 170-01 Smart Thermostat ZHA quirk.

Cluster summary:

  genBasic (0x0000)
    Standard: power_source (0x0007), sw_build_id (0x4000), product_url (0x000B),
              product_code (0x000A — written at runtime with the backplate
              variant string: "OpenTherm" | "OnOff" | "Wireless").

  genPowerCfg (0x0001)
    Standard: battery_percentage_remaining (0x0021)
    Mfg:      battery_type (0x007F, mfgCode 0x1172)
              0x00=Alkaline (Fujitsu), 0x01=NiMH (Eneloop)

  genIdentify (0x0003) — standard identify / front-light

  hvacThermostat (0x0201)
    Standard: local_temperature, occupied_heating_setpoint, occupied_cooling_setpoint,
              system_mode, pi_heating_demand, running_state (0x0029),
              outdoor_temperature (0x0001), local_temperature_calibration,
              min/max_heat/cool_setpoint_limit, ctrl_sequence_of_oper
    Mfg (mfgCode 0x1172):
      0xF000 external_heat_demand        UINT16  R/W  hundredths-°C OpenTherm setpoint, 0=disabled
      0xF001 external_heat_demand_timeout UINT16 R/W  watchdog seconds 300-3600
      0xF002 boiler_water_temperature    INT16S  R    hundredths-°C supply water
      0xF003 dhw_temperature             INT16S  R    hundredths-°C DHW
      0xF004 return_water_temperature    INT16S  R    hundredths-°C return water
      0xF005 application_fault_code      BITMAP8 R    OpenTherm fault bitmap (message ID 5 high byte)
      0xF006 oem_fault_code              UINT8   R    OEM fault code (message ID 5 low byte)
      0xF007 max_dhw_setpoint            INT16S  R/W  hundredths-°C max DHW setpoint, 0=not yet received
      0xF008 max_boiler_setpoint         INT16S  R/W  hundredths-°C max CH water setpoint, 0=not yet received

  hvacUserInterfaceCfg (0x0204) — keypad_lockout (standard)

  msTemperatureMeasurement (0x0402) — room temperature
  msRelativeHumidity (0x0405)       — room humidity
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, PowerConfiguration
from zigpy.zcl.clusters.hvac import Thermostat
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import ZCLAttributeAccess, ZCLAttributeDef
from zigpy.zcl.helpers import ReportingConfig

from zhaquirks.builder import (
    EntityType,
    QuirkBuilder,
    ReportingConfig as EntityReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

PLUGWISE: Final = "Plugwise"
PLUGWISE_MFG_CODE: Final = 0x1172

# ── Manufacturer-specific attribute IDs on hvacThermostat (mfgCode 0x1172) ──
ATTR_EXT_HEAT_DEMAND: Final = 0xF000
ATTR_EXT_HEAT_DEMAND_TIMEOUT: Final = 0xF001
ATTR_BOILER_WATER_TEMP: Final = 0xF002
ATTR_DHW_TEMP: Final = 0xF003
ATTR_RETURN_WATER_TEMP: Final = 0xF004
ATTR_APP_FAULT_CODE: Final = 0xF005
ATTR_OEM_FAULT_CODE: Final = 0xF006
ATTR_MAX_DHW_SETPOINT: Final = 0xF007
ATTR_MAX_BOILER_SETPOINT: Final = 0xF008

# ── Manufacturer-specific attribute ID on genPowerCfg (mfgCode 0x1172) ──
ATTR_BATTERY_TYPE: Final = 0x007F

_READ_ONLY: Final = ZCLAttributeAccess.Read | ZCLAttributeAccess.Report
_READ_WRITE: Final = (
    ZCLAttributeAccess.Read | ZCLAttributeAccess.Write | ZCLAttributeAccess.Report
)


class EmmaBatteryType(t.enum8):
    """Battery chemistry type for Emma thermostat (mfg attr 0x007F on genPowerCfg)."""

    Alkaline = 0x00  # Non-rechargeable, e.g. Fujitsu
    NiMH = 0x01  # Rechargeable, e.g. Eneloop


class EmmaApplicationFaultCode(t.bitmap8):
    """OpenTherm application fault bitmap (mfg attr 0xF005 on hvacThermostat).

    Corresponds to OpenTherm message ID 5 high byte.
    """

    ServiceRequest = 0x01
    LockoutReset = 0x02
    LowWaterPressure = 0x04
    GasFlameFault = 0x08
    AirPressureFault = 0x10
    WaterOverTemp = 0x20


# ── Reporting-config restrictions enforced by Emma firmware ──────────────────
# Emma returns INVALID_VALUE if a ConfigureReporting request falls outside the
# device-accepted ranges, so we clamp the parameters ZHA requests to a value
# the firmware accepts before they hit the wire.
#
# The on-device rule for the "restricted" thermostat attributes is
# ``min_intv > 1`` OR ``max_intv > 870`` → INVALID_VALUE.
# ZHA's REPORT_CONFIG_CLIMATE defaults are (min=30, max=900), so we must clamp
# both min down to ≤ 1 and max down to ≤ 870.

_EMMA_THERMOSTAT_MIN_INTERVAL_LIMIT: Final = 1  # seconds, firmware default
_EMMA_THERMOSTAT_MAX_INTERVAL_LIMIT: Final = 870  # seconds, firmware default
_EMMA_LOCAL_TEMP_CHANGE_RANGE: Final = (1, 10)  # hundredths-°C, firmware default

# Temperature Measurement / Relative Humidity require *exact* defaults.
_EMMA_HUMIDITY_MIN_INTERVAL: Final = 1
_EMMA_HUMIDITY_MAX_INTERVAL: Final = 870
_EMMA_HUMIDITY_CHANGE_RANGE: Final = (10, 300)  # hundredths-%RH

# Thermostat attributes whose reporting intervals Emma firmware restricts.
_EMMA_THERMOSTAT_RESTRICTED_ATTRS: Final = frozenset(
    {
        Thermostat.AttributeDefs.pi_cooling_demand.id,  # 0x0007
        Thermostat.AttributeDefs.pi_heating_demand.id,  # 0x0008
        Thermostat.AttributeDefs.local_temperature_calibration.id,  # 0x0010
        Thermostat.AttributeDefs.occupied_cooling_setpoint.id,  # 0x0011
        Thermostat.AttributeDefs.occupied_heating_setpoint.id,  # 0x0012
        Thermostat.AttributeDefs.system_mode.id,  # 0x001C
        Thermostat.AttributeDefs.running_state.id,  # 0x0029 (HVAC Relay State)
    }
)

# Power Configuration attributes: max_interval floors from firmware defaults.
_EMMA_POWER_MAX_INTERVAL_FLOOR: Final = {
    PowerConfiguration.AttributeDefs.battery_voltage.id: 65534,  # 0x0020
    PowerConfiguration.AttributeDefs.battery_percentage_remaining.id: 43200,  # 0x0021
}


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp ``value`` into the inclusive ``[lo, hi]`` range."""
    return max(lo, min(hi, value))


class EmmaThermostatCluster(CustomCluster, Thermostat):
    """hvacThermostat cluster extended with Plugwise manufacturer-specific attributes.

    Adds OpenTherm boiler telemetry (read-only) and external heat demand control
    (read/write) attributes, all gated by mfgCode 0x1172.
    """

    class AttributeDefs(Thermostat.AttributeDefs):
        """Thermostat attribute definitions plus Emma mfg-specific attributes."""

        # ── External heat demand (R/W) ────────────────────────────────────────
        external_heat_demand: Final = ZCLAttributeDef(
            id=ATTR_EXT_HEAT_DEMAND,
            type=t.uint16_t,
            access=_READ_WRITE,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        external_heat_demand_timeout: Final = ZCLAttributeDef(
            id=ATTR_EXT_HEAT_DEMAND_TIMEOUT,
            type=t.uint16_t,
            access=_READ_WRITE,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )

        # ── OpenTherm boiler readings (R only) ────────────────────────────────
        boiler_water_temperature: Final = ZCLAttributeDef(
            id=ATTR_BOILER_WATER_TEMP,
            type=t.int16s,
            access=_READ_ONLY,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        dhw_temperature: Final = ZCLAttributeDef(
            id=ATTR_DHW_TEMP,
            type=t.int16s,
            access=_READ_ONLY,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        return_water_temperature: Final = ZCLAttributeDef(
            id=ATTR_RETURN_WATER_TEMP,
            type=t.int16s,
            access=_READ_ONLY,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        application_fault_code: Final = ZCLAttributeDef(
            id=ATTR_APP_FAULT_CODE,
            type=EmmaApplicationFaultCode,
            access=_READ_ONLY,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        oem_fault_code: Final = ZCLAttributeDef(
            id=ATTR_OEM_FAULT_CODE,
            type=t.uint8_t,
            access=_READ_ONLY,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )

        # ── Max setpoints from boiler (R/W, write requires Unlocked External Control) ──
        max_dhw_setpoint: Final = ZCLAttributeDef(
            id=ATTR_MAX_DHW_SETPOINT,
            type=t.int16s,
            access=_READ_WRITE,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )
        max_boiler_setpoint: Final = ZCLAttributeDef(
            id=ATTR_MAX_BOILER_SETPOINT,
            type=t.int16s,
            access=_READ_WRITE,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )

    async def configure_reporting_multiple(
        self, config: dict[ZCLAttributeDef, ReportingConfig]
    ) -> dict[ZCLAttributeDef, int]:
        """Clamp ZHA's defaults to ranges Emma firmware accepts before sending.

        Emma rejects ConfigureReporting requests outside its firmware limits
        with INVALID_VALUE. ZHA's default REPORT_CONFIG_CLIMATE uses max=900 s
        and reportable_change=25 hundredths-°C, both of which Emma refuses for
        the listed attributes. Override clamps to the device-accepted bounds so
        reporting actually gets configured.
        """
        clamped: dict[ZCLAttributeDef, ReportingConfig] = {}
        for attr_def, rcfg in config.items():
            new_min = rcfg.min_interval
            new_max = rcfg.max_interval
            new_change = rcfg.reportable_change

            if attr_def.id in _EMMA_THERMOSTAT_RESTRICTED_ATTRS:
                # Firmware: min > 1 OR max > 870 → INVALID_VALUE. Clamp both.
                new_min = min(new_min, _EMMA_THERMOSTAT_MIN_INTERVAL_LIMIT)
                new_max = min(new_max, _EMMA_THERMOSTAT_MAX_INTERVAL_LIMIT)

            if attr_def.id == Thermostat.AttributeDefs.local_temperature.id:
                lo, hi = _EMMA_LOCAL_TEMP_CHANGE_RANGE
                new_change = _clamp(new_change, lo, hi)

            clamped[attr_def] = ReportingConfig(
                min_interval=new_min,
                max_interval=new_max,
                reportable_change=new_change,
            )
        return await super().configure_reporting_multiple(clamped)


class EmmaHumidityCluster(CustomCluster, RelativeHumidity):
    """msRelativeHumidity cluster with Emma's strict reporting constraints.

    Emma firmware requires ``min_interval`` and ``max_interval`` to be
    *exactly* 1 and 870 seconds and ``reportable_change`` in the inclusive
    range 10..300 (0.10-3.00 %RH). Any other values return INVALID_VALUE.
    """

    async def configure_reporting_multiple(
        self, config: dict[ZCLAttributeDef, ReportingConfig]
    ) -> dict[ZCLAttributeDef, int]:
        """Force exact intervals and clamp change to Emma's accepted range."""
        clamped: dict[ZCLAttributeDef, ReportingConfig] = {}
        for attr_def, rcfg in config.items():
            if attr_def.id == RelativeHumidity.AttributeDefs.measured_value.id:
                lo, hi = _EMMA_HUMIDITY_CHANGE_RANGE
                clamped[attr_def] = ReportingConfig(
                    min_interval=_EMMA_HUMIDITY_MIN_INTERVAL,
                    max_interval=_EMMA_HUMIDITY_MAX_INTERVAL,
                    reportable_change=_clamp(rcfg.reportable_change, lo, hi),
                )
            else:
                clamped[attr_def] = rcfg
        return await super().configure_reporting_multiple(clamped)


class EmmaPowerConfigCluster(CustomCluster, PowerConfiguration):
    """genPowerCfg cluster extended with Plugwise battery-type attribute."""

    class AttributeDefs(PowerConfiguration.AttributeDefs):
        """PowerConfiguration attribute definitions plus Emma battery_type."""

        battery_type: Final = ZCLAttributeDef(
            id=ATTR_BATTERY_TYPE,
            type=EmmaBatteryType,
            access=_READ_WRITE,
            manufacturer_code=PLUGWISE_MFG_CODE,
        )

    async def configure_reporting_multiple(
        self, config: dict[ZCLAttributeDef, ReportingConfig]
    ) -> dict[ZCLAttributeDef, int]:
        """Clamp max_interval to Emma's minimum-acceptable floor.

        Emma firmware requires ``max ≥ 65534 s`` for battery_voltage and
        ``max ≥ 43200 s`` for battery_percentage_remaining; values below those
        floors are rejected with INVALID_VALUE.
        """
        clamped: dict[ZCLAttributeDef, ReportingConfig] = {}
        for attr_def, rcfg in config.items():
            new_max = rcfg.max_interval
            floor = _EMMA_POWER_MAX_INTERVAL_FLOOR.get(attr_def.id)
            if floor is not None:
                new_max = max(new_max, floor)

            clamped[attr_def] = ReportingConfig(
                min_interval=rcfg.min_interval,
                max_interval=new_max,
                reportable_change=rcfg.reportable_change,
            )
        return await super().configure_reporting_multiple(clamped)


# ── Register quirk ───────────────────────────────────────────────────────────
#
# QuirkBuilder v2 matches on manufacturer + model only — no strict endpoint
# signature required. ZHA will substitute the custom clusters for the standard
# ones wherever they appear in the device's endpoint list.
(
    QuirkBuilder(PLUGWISE, "170-01")
    # ── Friendly device name in HA Device info ────────────────────────────
    # The ZCL model identifier "170-01" is a Plugwise SKU; users see "Emma"
    # on the product. The specific variant (Wired Pro / Wireless / OpenTherm
    # / OnOff) is surfaced separately via the product_label diagnostic sensor.
    .friendly_name(manufacturer=PLUGWISE, model="Emma thermostat")
    # ── Cluster substitutions ─────────────────────────────────────────────
    .replaces(EmmaThermostatCluster)
    .replaces(EmmaPowerConfigCluster)
    .replaces(EmmaHumidityCluster)
    # ── Basic-cluster product identification (diagnostic sensors) ─────────
    # Emma firmware doesn't implement Basic 0x000E (product_label) — the
    # backplate-detection logic instead writes the variant string ("OpenTherm",
    # "OnOff", or "Wireless") into product_code (0x000A) at runtime, and the
    # product family is also encoded in product_url (e.g. ".../emma-wired-pro").
    .sensor(
        attribute_name=Basic.AttributeDefs.product_code.name,
        cluster_id=Basic.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        attribute_converter=lambda value: bytes(value).decode(
            "utf-8", errors="replace"
        ),
        # Firmware writes a new product_code when the backplate changes
        # (OpenTherm / OnOff / Wireless). Configure reporting so ZHA binds
        # the Basic cluster and receives the update without a manual
        # reconfigure.
        reporting_config=EntityReportingConfig(
            min_interval=1, max_interval=65534, reportable_change=1
        ),
        translation_key="product_code",
        fallback_name="Product code",
    )
    .sensor(
        attribute_name=Basic.AttributeDefs.product_url.name,
        cluster_id=Basic.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        translation_key="product_url",
        fallback_name="Product URL",
    )
    # ── Identify: replace the auto Button (sends the ZCL Identify command)
    # with a write-attribute button. Emma firmware reacts to writes on the
    # identify_time attribute (0x0000) and ignores the Identify command, so
    # pressing the standard button does nothing. This pair hides the default
    # button (ZHA's only Identify-cluster entity) and adds one that writes 10
    # seconds into identify_time, which the firmware reads back and uses to
    # drive the e-paper identify indicator.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=Identify.cluster_id)
    .write_attr_button(
        attribute_name=Identify.AttributeDefs.identify_time.name,
        attribute_value=10,
        cluster_id=Identify.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="identify",
        fallback_name="Identify",
    )
    # ── Enable RSSI / LQI by default (auto-discovered, normally disabled) ─
    .change_entity_metadata(
        cluster_id=Basic.cluster_id,
        unique_id_suffix="rssi",
        new_entity_registry_enabled_default=True,
    )
    .change_entity_metadata(
        cluster_id=Basic.cluster_id,
        unique_id_suffix="lqi",
        new_entity_registry_enabled_default=True,
    )
    .sensor(
        attribute_name=Basic.AttributeDefs.sw_build_id.name,
        cluster_id=Basic.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="sw_build_id",
        fallback_name="Firmware version",
    )
    # ── Drop redundant room-temp entity ───────────────────────────────────
    # Emma exposes the same room temperature on both msTemperatureMeasurement
    # (0x0402) and hvacThermostat.local_temperature. Remove the dedicated
    # measurement cluster so only the thermostat's local_temperature surfaces
    # as the current-temperature reading on the climate entity.
    .removes(TemperatureMeasurement.cluster_id)
    # ── Intended Boiler Setpoint (°C view of pi_heating_demand) ────────
    # Emma firmware reports the *intended boiler water setpoint in °C* (0-100)
    # via the standard pi_heating_demand attribute. We add a temperature sensor
    # alongside ZHA's auto-discovered percentage sensor so users see both the
    # raw value and the temperature interpretation. ``unique_id_suffix`` keeps
    # the new entity's unique id distinct from the auto-discovered one.
    .sensor(
        attribute_name=Thermostat.AttributeDefs.pi_heating_demand.name,
        cluster_id=Thermostat.cluster_id,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unique_id_suffix="intended_boiler_setpoint",
        translation_key="intended_boiler_setpoint",
        fallback_name="Intended boiler setpoint",
    )
    # ── OpenTherm boiler temperature sensors (hundredths-°C → °C) ─────────
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.boiler_water_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="boiler_water_temperature",
        fallback_name="Boiler water temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.dhw_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="dhw_temperature",
        fallback_name="DHW temperature",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.return_water_temperature.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="return_water_temperature",
        fallback_name="Return water temperature",
    )
    # ── Boiler fault code sensors (diagnostic) ────────────────────────────
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.application_fault_code.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="application_fault_code",
        fallback_name="Application fault code",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.oem_fault_code.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="oem_fault_code",
        fallback_name="OEM fault code",
    )
    # ── Max DHW / boiler setpoints (hundredths-°C → °C, writable when unlocked) ──
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_dhw_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="max_dhw_setpoint",
        fallback_name="Max DHW setpoint",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_dhw_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=0.01,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_dhw_setpoint",
        fallback_name="Max DHW setpoint",
    )
    .sensor(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_boiler_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        divisor=100,
        suggested_display_precision=1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="max_boiler_setpoint",
        fallback_name="Max boiler setpoint",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.max_boiler_setpoint.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=100.0,
        step=0.01,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="max_boiler_setpoint",
        fallback_name="Max boiler setpoint",
    )
    # ── External heat demand (user-writeable, hundredths-°C ↔ °C) ─────────
    # multiplier=0.01: raw_device_value * 0.01 = displayed_°C
    #                  displayed_°C / 0.01 = raw_device_value written
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.external_heat_demand.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=0.0,
        max_value=90.0,
        step=0.01,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="external_heat_demand",
        fallback_name="External heat demand",
    )
    .number(
        attribute_name=EmmaThermostatCluster.AttributeDefs.external_heat_demand_timeout.name,
        cluster_id=EmmaThermostatCluster.cluster_id,
        min_value=300,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="external_heat_demand_timeout",
        fallback_name="External heat demand timeout",
    )
    # ── Battery chemistry selection ───────────────────────────────────────
    .enum(
        attribute_name=EmmaPowerConfigCluster.AttributeDefs.battery_type.name,
        enum_class=EmmaBatteryType,
        cluster_id=EmmaPowerConfigCluster.cluster_id,
        translation_key="battery_type",
        fallback_name="Battery type",
    )
    .add_to_registry()
)
