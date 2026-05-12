"""Sonoff SWV - Zigbee smart water valve."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,  # Sensor device class
    SensorStateClass,  # Sensor state class (for line charts)
)

# Import unit constants (duration/volume)
from zigpy.quirks.v2.homeassistant import UnitOfTime, UnitOfVolume
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ValveState(t.enum8):
    """Water valve state (8-bit value, bit-defined)."""

    # Basic states (single bit)
    Normal = 0  # 000 (no abnormal condition)
    Water_Shortage = 1 << 0  # 001 (bit0: water shortage)
    Water_Leakage = 1 << 1  # 010 (bit1: water leakage)
    Anti_Frost_Alarm = 1 << 2  # 100 (bit2: anti-frost alarm)
    Water_Shortage_Channel_2 = 1 << 4  # bit4: channel 2 water shortage
    # Combined states (multiple bits triggered at the same time)
    Water_Shortage_And_Leakage = Water_Shortage | Water_Leakage  # 011
    Water_Shortage_And_Frost = Water_Shortage | Anti_Frost_Alarm  # 101
    Water_Leakage_And_Frost = Water_Leakage | Anti_Frost_Alarm  # 110
    All_Alarms = Water_Shortage | Water_Leakage | Anti_Frost_Alarm  # 111


class CustomSonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
            manufacturer_code=None,
        )
        # Water usage duration
        water_usage_duration = ZCLAttributeDef(
            id=0x501C,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        # Water usage volume
        water_usage_volume = ZCLAttributeDef(
            id=0x501B,
            type=t.uint32_t,
            manufacturer_code=None,
        )


(
    QuirkBuilder("SONOFF", "SWV-ZFU")
    .also_applies_to("SONOFF", "SWV-ZFE")
    .replaces(CustomSonoffCluster)
    # Water leak sensor (bit1)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda x: x & ValveState.Water_Leakage,
        unique_id_suffix="water_leak_status",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    # Water shortage sensor (bit0)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        # Show a water shortage alarm when either bit0 or bit4 is set,
        # without distinguishing channels.
        attribute_converter=lambda x: x
        & (ValveState.Water_Shortage | ValveState.Water_Shortage_Channel_2),
        unique_id_suffix="water_depletion_status",
        translation_key="Water depletion",
        fallback_name="Water depletion",
    )
    # Water usage duration sensor (channel 1, endpoint 1)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="water_usage_duration",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_duration",
        fallback_name="Water usage duration",
    )
    # Water usage volume sensor
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_volume.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,  # VOLUME must use total_increasing
        unit=UnitOfVolume.LITERS,
        unique_id_suffix="water_usage_volume",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_volume",
        fallback_name="Water usage volume",
    )
    .add_to_registry()
)

# Register dual-channel devices (SWV-ZF2U / SWV-ZF2E) separately,
# adding the channel 2 water usage duration line chart.
(
    QuirkBuilder("SONOFF", "SWV-ZF2")
    .also_applies_to("SONOFF", "SWV-ZF2U")
    .also_applies_to("SONOFF", "SWV-ZF2E")
    .replaces(CustomSonoffCluster)
    .replaces(
        CustomSonoffCluster, endpoint_id=2
    )  # Endpoint 2 also uses the custom cluster
    # Water leak sensor (bit1)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda x: x & ValveState.Water_Leakage,
        unique_id_suffix="water_leak_status",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    # Water shortage sensor (bit0/bit4)
    .binary_sensor(
        CustomSonoffCluster.AttributeDefs.water_valve_state.name,
        CustomSonoffCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=lambda x: x
        & (ValveState.Water_Shortage | ValveState.Water_Shortage_Channel_2),
        unique_id_suffix="water_depletion_status",
        translation_key="Water depletion",
        fallback_name="Water depletion",
    )
    # Water usage duration sensor - channel 1 (endpoint 1, 0x501C)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=1,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="water_usage_duration_ch1",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_duration_ch1",
        fallback_name="Water usage duration CH1",
    )
    # Water usage duration sensor - channel 2 (endpoint 2, 0x501C)
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        endpoint_id=2,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.MINUTES,
        unique_id_suffix="water_usage_duration_ch2",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_duration_ch2",
        fallback_name="Water usage duration CH2",
    )
    # Water usage volume sensor
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_volume.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,  # VOLUME must use total_increasing
        unit=UnitOfVolume.LITERS,
        unique_id_suffix="water_usage_volume",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_volume",
        fallback_name="Water usage volume",
    )
    .add_to_registry()
)

(
    QuirkBuilder("SONOFF", "SWV-ZNU")
    .also_applies_to("SONOFF", "SWV-ZNE")
    .replaces(CustomSonoffCluster)
    # Add water usage duration sensor
    .sensor(
        attribute_name=CustomSonoffCluster.AttributeDefs.water_usage_duration.name,
        cluster_id=CustomSonoffCluster.cluster_id,
        device_class=SensorDeviceClass.DURATION,  # Duration sensor
        state_class=SensorStateClass.MEASUREMENT,  # Key: measurement value, supports line charts
        unit=UnitOfTime.MINUTES,  # Unit: minutes
        unique_id_suffix="water_usage_duration",
        reporting_config=ReportingConfig(
            min_interval=30, max_interval=900, reportable_change=1
        ),
        translation_key="water_usage_duration",
        fallback_name="Water usage duration",
    )
    .add_to_registry()
)
