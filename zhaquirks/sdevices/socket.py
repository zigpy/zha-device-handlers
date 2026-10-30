"""SDevices smart wall socket.

Covers the native SDevices wall socket:

* SBDV-00202  Smart Wall Socket (relay, energy metering, protection thresholds)

Single endpoint EP1: the relay (``OnOff``), energy metering and protection
thresholds on the 0xFCCF cluster, device temperature on ``DeviceTemperature``
(replaced with a divisor=1 sensor - this device reports whole degrees, while
ZHA's native one divides by 100) and diagnostics on ``Diagnostic``. The socket
has no button actions.

The relay is exposed as a ``switch`` entity (endpoint device type
``ON_OFF_OUTPUT``), matching the reference ``zigbee-herdsman-converters``
implementation. The power-on behavior comes from ZHA's built-in ``OnOff``
start-up select.
"""

from __future__ import annotations

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import DeviceTemperature

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.sdevices import (
    SDEVICES,
    EmergencyRecovery,
    SDevicesCluster,
    SDevicesDeviceTemperatureCluster,
    SDevicesDiagnosticCluster,
    SDevicesOnOffCluster,
    SDevicesReportingCluster,
)

_READ_ON_STARTUP = {"attribute_initialized_from_cache": False}

# Emergency flags are exposed as binary sensors on the synthetic per-bit
# attributes (see SDevicesCluster._update_attribute). Each has its own attribute,
# so they update independently and correctly on a live report.
_EMERGENCY_FLAGS = (
    # (synthetic attribute name, fallback name)
    ("emergency_overvoltage", "Emergency overvoltage"),
    ("emergency_undervoltage", "Emergency undervoltage"),
    ("emergency_overcurrent", "Emergency overcurrent"),
    ("emergency_overheat", "Emergency overheat"),
)


def _add_led_entities(qb: QuirkBuilder) -> QuirkBuilder:
    """Add the ON and OFF LED indicator entities on EP1."""
    for state in ("on", "off"):
        qb = (
            qb.switch(
                f"led_indicator_{state}_enable",
                SDevicesCluster.cluster_id,
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_{state}_enable",
                fallback_name=f"LED indicator ({state})",
                **_READ_ON_STARTUP,
            )
            .number(
                f"led_indicator_{state}_h",
                SDevicesCluster.cluster_id,
                min_value=0,
                max_value=359,
                step=1,
                unit="°",
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_{state}_h",
                fallback_name=f"LED hue ({state})",
                **_READ_ON_STARTUP,
            )
            .number(
                f"led_indicator_{state}_s",
                SDevicesCluster.cluster_id,
                min_value=0,
                max_value=254,
                step=1,
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_{state}_s",
                fallback_name=f"LED saturation ({state})",
                **_READ_ON_STARTUP,
            )
            .number(
                f"led_indicator_{state}_b",
                SDevicesCluster.cluster_id,
                min_value=1,
                max_value=254,
                step=1,
                entity_type=EntityType.CONFIG,
                translation_key=f"led_indicator_{state}_b",
                fallback_name=f"LED brightness ({state})",
                **_READ_ON_STARTUP,
            )
        )
    return qb


def _add_metering(qb: QuirkBuilder) -> QuirkBuilder:
    """Add energy metering sensors using the firmware reporting configuration."""
    return (
        qb.sensor(
            "rms_voltage_mv",
            SDevicesCluster.cluster_id,
            divisor=1000,
            suggested_display_precision=1,
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            **_READ_ON_STARTUP,
            # No translation_key: rely on the device_class so Home Assistant core
            # localizes the name ("Voltage" -> "Напряжение" etc.). A custom
            # translation_key would need strings shipped in ZHA to be translated.
            fallback_name="Voltage",
        )
        .sensor(
            "rms_current_ma",
            SDevicesCluster.cluster_id,
            divisor=1000,
            suggested_display_precision=3,
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            **_READ_ON_STARTUP,
            # No translation_key: device_class drives the localized name.
            fallback_name="Current",
        )
        .sensor(
            "active_power_mw",
            SDevicesCluster.cluster_id,
            divisor=1000,
            suggested_display_precision=1,
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            **_READ_ON_STARTUP,
            # No translation_key: device_class drives the localized name.
            fallback_name="Power",
        )
    )


def _add_thresholds(qb: QuirkBuilder) -> QuirkBuilder:
    """Add the protection / recovery config entities."""
    return (
        qb.enum(
            "emergency_shutoff_recovery",
            EmergencyRecovery,
            SDevicesCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="emergency_shutoff_recovery",
            fallback_name="Emergency recovery",
            **_READ_ON_STARTUP,
        )
        .number(
            "upper_voltage_threshold",
            SDevicesCluster.cluster_id,
            min_value=230,
            max_value=260,
            step=1,
            multiplier=0.001,  # mV -> V
            unit=UnitOfElectricPotential.VOLT,
            device_class=NumberDeviceClass.VOLTAGE,
            entity_type=EntityType.CONFIG,
            translation_key="upper_voltage_threshold",
            fallback_name="Upper voltage threshold",
            **_READ_ON_STARTUP,
        )
        .number(
            "lower_voltage_threshold",
            SDevicesCluster.cluster_id,
            min_value=100,
            max_value=230,
            step=1,
            multiplier=0.001,  # mV -> V
            unit=UnitOfElectricPotential.VOLT,
            device_class=NumberDeviceClass.VOLTAGE,
            entity_type=EntityType.CONFIG,
            translation_key="lower_voltage_threshold",
            fallback_name="Lower voltage threshold",
            **_READ_ON_STARTUP,
        )
        .number(
            "upper_current_threshold",
            SDevicesCluster.cluster_id,
            min_value=0.1,
            max_value=16,
            step=0.1,
            multiplier=0.001,  # mA -> A
            unit=UnitOfElectricCurrent.AMPERE,
            device_class=NumberDeviceClass.CURRENT,
            entity_type=EntityType.CONFIG,
            translation_key="upper_current_threshold",
            fallback_name="Upper current threshold",
            **_READ_ON_STARTUP,
        )
        .number(
            "upper_temp_threshold",
            SDevicesCluster.cluster_id,
            min_value=10,
            max_value=100,
            step=1,
            unit=UnitOfTemperature.CELSIUS,
            device_class=NumberDeviceClass.TEMPERATURE,
            entity_type=EntityType.CONFIG,
            translation_key="temperature_threshold",
            fallback_name="Overtemperature threshold",
            **_READ_ON_STARTUP,
        )
    )


def _add_diagnostics(qb: QuirkBuilder) -> QuirkBuilder:
    """Add the diagnostics / telemetry sensors on the Diagnostic cluster.

    attribute_initialized_from_cache=False forces a read on configure (otherwise
    they stay Unknown: the Diagnostic cluster is not bound, and these attributes
    are not read on startup by default).
    """
    return (
        qb.sensor(
            "sdevices_uptime_s",
            SDevicesDiagnosticCluster.cluster_id,
            unit=UnitOfTime.SECONDS,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="uptime",
            fallback_name="Uptime",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "number_of_resets",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="resets_count",
            fallback_name="Resets count",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_button1_clicks",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="button_clicks_1",
            fallback_name="Button 1 clicks",
            **_READ_ON_STARTUP,
        )
        .sensor(
            "sdevices_relay1_switches",
            SDevicesDiagnosticCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            translation_key="relay_switches_1",
            fallback_name="Relay 1 switches",
            **_READ_ON_STARTUP,
        )
    )


def _socket(manufacturer: str, model: str) -> QuirkBuilder:
    """Build the SDevices wall socket (00202)."""
    qb = (
        # Device type Mains Power Outlet (0x0009) per the device data model; ZHA
        # maps its OnOff cluster to the switch platform (it is not a light type).
        QuirkBuilder(manufacturer, model)
        .replaces_endpoint(1, device_type=zha.DeviceType.MAIN_POWER_OUTLET)
        .replaces(SDevicesOnOffCluster)
        .replaces(SDevicesReportingCluster)
        .replaces(SDevicesDeviceTemperatureCluster)
        .replaces(SDevicesDiagnosticCluster)
        # ZCL DeviceTemperature (0x0002) reports currentTemperature in whole
        # degrees Celsius (ZCLv8); ZHA's native sensor wrongly divides by 100
        # (that divisor fits TemperatureMeasurement 0x0402, not 0x0002) - replace
        # it with a divisor=1 sensor. The custom cluster binds while retaining
        # the reporting table supplied by the firmware.
        .prevent_default_entity_creation(
            endpoint_id=1,
            cluster_id=DeviceTemperature.cluster_id,
            function=lambda entity: entity.__class__.__name__ == "DeviceTemperature",
        )
        .sensor(
            "current_temperature",
            DeviceTemperature.cluster_id,
            endpoint_id=1,
            divisor=1,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfTemperature.CELSIUS,
            entity_type=EntityType.DIAGNOSTIC,
            unique_id_suffix=str(DeviceTemperature.cluster_id),
            **_READ_ON_STARTUP,
            translation_key="device_temperature",
            fallback_name="Device temperature",
        )
        .switch(
            "child_lock",
            SDevicesCluster.cluster_id,
            entity_type=EntityType.CONFIG,
            translation_key="child_lock",
            fallback_name="Child lock",
            **_READ_ON_STARTUP,
        )
    )
    qb = _add_led_entities(qb)
    qb = _add_metering(qb)
    qb = _add_thresholds(qb)
    qb = _add_diagnostics(qb)
    # Raw emergency bitmap. SDevicesCluster binds without replacing the firmware
    # reporting configuration and splits the value into the per-flag attributes.
    qb = qb.sensor(
        "emergency_shutoff_state",
        SDevicesCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        **_READ_ON_STARTUP,
        translation_key="emergency_shutoff_state",
        fallback_name="Emergency shutoff state",
    )
    # One binary sensor per emergency flag, on its own synthetic attribute.
    for attr_name, fallback_name in _EMERGENCY_FLAGS:
        qb = qb.binary_sensor(
            attr_name,
            SDevicesCluster.cluster_id,
            entity_type=EntityType.DIAGNOSTIC,
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key=attr_name,
            fallback_name=fallback_name,
        )
    return qb


_socket(SDEVICES, "SBDV-00202").add_to_registry()
