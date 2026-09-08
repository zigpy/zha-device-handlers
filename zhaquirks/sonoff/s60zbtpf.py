"""SONOFF S60ZBTPF - Smart Socket with power measurement fix.

Firmware before v2.0.3 (`0x00002003`) keeps reporting power, current and voltage while
the socket is turned off. For those versions, the quirk sets `active_power` and
`rms_current` to 0 and `rms_voltage` to `uint16.non_value` when the socket is switched
off, and blocks further updates to the three attributes until it is switched back on.
v2.0.3 fixed the bug, so that version and newer do not get the workaround.

v2.0.2 also reports `instantaneous_demand` as supported, always with value 0. The
metering entity it would create is prevented for all firmware versions, as the device
never provides a useful value for it.

See https://github.com/zigpy/zigpy-ota/issues/164 for more details.

This variant also exposes SONOFF manufacturer attributes for:
- Network LED
- Protection trip status
- Current, voltage, and power protection settings
- Daily and monthly energy values
"""

from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from zhaquirks.clusters import CustomCluster

PROTECTION_TRIP_BIT = 0x04


def _protection_trip_active(value: Any) -> bool:
    """Return true when the protection-trip bit is set."""
    try:
        return bool(int(value) & PROTECTION_TRIP_BIT)
    except (TypeError, ValueError):
        return False


class SonoffS60OnOff(CustomCluster, OnOff):
    """Custom OnOff cluster that resets power readings when the socket is turned off."""

    def _update_attribute(
        self, attrid: int | t.uint16_t | foundation.ZCLAttributeDef, value: Any
    ) -> None:
        """Reset attributes to zero when the socket is turned off."""
        if (
            self.find_attribute(attrid) == OnOff.AttributeDefs.on_off
            and value == t.Bool.false
        ):
            self.endpoint.electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.active_power.id, 0
            )
            self.endpoint.electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.rms_current.id, 0
            )
            self.endpoint.electrical_measurement.update_attribute(
                ElectricalMeasurement.AttributeDefs.rms_voltage.id,
                foundation.DataType.uint16.non_value,
            )

        super()._update_attribute(attrid, value)


class SonoffS60ElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Custom ElectricalMeasurement cluster that prevents power updates when the socket is turned off."""

    def _update_attribute(
        self, attrid: int | t.uint16_t | foundation.ZCLAttributeDef, value: Any
    ) -> None:
        """Prevent updates when the socket is turned off."""
        if (
            self.endpoint.on_off.get(OnOff.AttributeDefs.on_off.id) == t.Bool.false
            # we should always get the ID here, but just in case, check for def too
            and self.find_attribute(attrid)
            in (
                ElectricalMeasurement.AttributeDefs.active_power,
                ElectricalMeasurement.AttributeDefs.rms_current,
                ElectricalMeasurement.AttributeDefs.rms_voltage,
            )
        ):
            return

        super()._update_attribute(attrid, value)


class SonoffS60ManufacturerCluster(CustomCluster):
    """SONOFF/eWeLink manufacturer cluster used by the S60 sockets."""

    cluster_id = 0xFC11
    ep_attribute = "ewelink"

    class AttributeDefs(BaseAttributeDefs):
        """Known S60 manufacturer attributes."""

        network_led = ZCLAttributeDef(
            id=0x0001,
            type=t.Bool,
            manufacturer_code=None,
        )

        protection_status = ZCLAttributeDef(
            id=0x0010,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        protection_current = ZCLAttributeDef(
            id=0x7004,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        protection_voltage = ZCLAttributeDef(
            id=0x7005,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        protection_power = ZCLAttributeDef(
            id=0x7006,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        outlet_control_protect_setting = ZCLAttributeDef(
            id=0x7007,
            type=t.uint8_t,
            manufacturer_code=None,
        )

        energy_today = ZCLAttributeDef(
            id=0x7009,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        energy_month = ZCLAttributeDef(
            id=0x700A,
            type=t.uint32_t,
            manufacturer_code=None,
        )
        energy_yesterday = ZCLAttributeDef(
            id=0x700B,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ac_current_max_overload_enable = ZCLAttributeDef(
            id=0x700C,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        ac_current_max_overload = ZCLAttributeDef(
            id=0x700D,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ac_voltage_max_overload_enable = ZCLAttributeDef(
            id=0x700E,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        ac_voltage_max_overload = ZCLAttributeDef(
            id=0x700F,
            type=t.uint32_t,
            manufacturer_code=None,
        )

        ac_power_max_overload_enable = ZCLAttributeDef(
            id=0x7010,
            type=t.uint8_t,
            manufacturer_code=None,
        )
        ac_power_max_overload = ZCLAttributeDef(
            id=0x7011,
            type=t.uint32_t,
            manufacturer_code=None,
        )


# firmware version that fixed the power reporting bug (max_version is exclusive)
S60_POWER_FIX_FW_VERSION = 0x00002003


s60_base_quirk = (
    QuirkBuilder("SONOFF", "S60ZBTPF")
    # .applies_to("SONOFF", "S60ZBTPG")  # Not enabled because this variant is untested.
    .replaces(SonoffS60ManufacturerCluster, endpoint_id=1)
    .switch(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.network_led.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        translation_key="network_led",
        fallback_name="Network LED",
    )
    .binary_sensor(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.protection_status.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attribute_converter=_protection_trip_active,
        unique_id_suffix="protection_status",
        translation_key="protection_status",
        fallback_name="Protection status",
    )
    .switch(
        attribute_name=(
            SonoffS60ManufacturerCluster.AttributeDefs.ac_current_max_overload_enable.name
        ),
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        off_value=0,
        on_value=1,
        translation_key="ac_current_max_overload_enable",
        fallback_name="Max current protection",
    )
    .number(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.ac_current_max_overload.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        min_value=0.1,
        max_value=17.0,
        step=0.1,
        unit=UnitOfElectricCurrent.AMPERE,
        mode="box",
        multiplier=0.001,
        device_class=NumberDeviceClass.CURRENT,
        translation_key="ac_current_max_overload",
        fallback_name="Maximum current",
    )
    .switch(
        attribute_name=(
            SonoffS60ManufacturerCluster.AttributeDefs.ac_voltage_max_overload_enable.name
        ),
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        off_value=0,
        on_value=1,
        translation_key="ac_voltage_max_overload_enable",
        fallback_name="Max voltage protection",
    )
    .number(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.ac_voltage_max_overload.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        min_value=165.0,
        max_value=277.0,
        step=1.0,
        unit=UnitOfElectricPotential.VOLT,
        mode="box",
        multiplier=0.001,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="ac_voltage_max_overload",
        fallback_name="Maximum voltage",
    )
    .switch(
        attribute_name=(
            SonoffS60ManufacturerCluster.AttributeDefs.ac_power_max_overload_enable.name
        ),
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        off_value=0,
        on_value=1,
        translation_key="ac_power_max_overload_enable",
        fallback_name="Max power protection",
    )
    .number(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.ac_power_max_overload.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        min_value=0.1,
        max_value=4000.0,
        step=0.1,
        unit=UnitOfPower.WATT,
        mode="box",
        multiplier=0.001,
        device_class=NumberDeviceClass.POWER,
        translation_key="ac_power_max_overload",
        fallback_name="Maximum power",
    )
    .sensor(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.energy_yesterday.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        divisor=1000,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_yesterday",
        fallback_name="Energy yesterday",
    )
    .sensor(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.energy_today.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        divisor=1000,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_today",
        fallback_name="Energy today",
    )
    .sensor(
        attribute_name=SonoffS60ManufacturerCluster.AttributeDefs.energy_month.name,
        cluster_id=SonoffS60ManufacturerCluster.cluster_id,
        endpoint_id=1,
        divisor=1000,
        suggested_display_precision=3,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="energy_month",
        fallback_name="Energy month",
    )
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=Metering.cluster_id,
        unique_id_suffix="1-1794",  # no actual suffix for this
    )
)

(
    # firmware before the fix, and devices not reporting a firmware version at all,
    # get the power reporting workaround
    s60_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(
        max_version=S60_POWER_FIX_FW_VERSION,
        allow_missing=True,
    )
    .replaces(SonoffS60OnOff)
    .replaces(SonoffS60ElectricalMeasurement)
    .add_to_registry()
)

(
    # the fixed firmware and newer only need the metering entity prevention
    s60_base_quirk.clone(omit_man_model_data=False)
    .firmware_version_filter(
        min_version=S60_POWER_FIX_FW_VERSION,
        allow_missing=False,
    )
    .add_to_registry()
)
