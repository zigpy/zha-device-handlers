"""Aqara Wall Outlet H2 UK (WP-P09D / lumi.plug.aeu002).

Two UK sockets and a USB port, each switched on its own endpoint, with a button
per socket and power monitoring.

Every endpoint's ElectricalMeasurement cluster declares `ac_power_divisor` 10 but
reports `active_power` in whole watts, so ZHA shows a tenth of the real draw. The
quirk pins the power multiplier and divisor to 1 and leaves the value alone.

Switch and power endpoints do not line up:

  EP1: switch socket 1, power total
  EP2: switch socket 2, power socket 1 + USB
  EP3: switch USB,      power socket 2

Settings live in the manufacturer cluster: child lock and multi-click mode per
button on EP1 and EP2, LED indicator, flip indicator light, overload protection
and power on state on EP1. Button presses arrive as MultistateInput reports on
EP1 and EP2. Attribute ids and values follow the zigbee-herdsman-converters
definition for this model.
"""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import NumberDeviceClass, QuirkBuilder, UnitOfPower
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    SHORT_PRESS,
)
from zhaquirks.xiaomi import AQARA, XIAOMI_AQARA_ATTRIBUTE_E1, XiaomiAqaraE1Cluster
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_RELEASE,
    COMMAND_1_SINGLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_RELEASE,
    COMMAND_2_SINGLE,
    MultistateInputCluster,
)

LUMI_MANUFACTURER_CODE = 0x115F


class AqaraH2UKPowerOnState(t.enum8):
    """Socket state after mains power returns."""

    On = 0x00
    Previous = 0x01
    Off = 0x02
    Inverted = 0x03


class AqaraH2UKElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """ElectricalMeasurement with the wrongly declared power scaling pinned to 1."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_power_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 1,
    }


class AqaraH2UKManuCluster(XiaomiAqaraE1Cluster):
    """Manufacturer cluster carrying the outlet settings."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        aqara_attributes: Final = ZCLAttributeDef(
            id=XIAOMI_AQARA_ATTRIBUTE_E1,
            type=t.LVBytes,
            manufacturer_code=LUMI_MANUFACTURER_CODE,
        )
        flip_indicator_light: Final = ZCLAttributeDef(
            id=0x00F0, type=t.uint8_t, manufacturer_code=LUMI_MANUFACTURER_CODE
        )
        led_indicator: Final = ZCLAttributeDef(
            id=0x0203, type=t.Bool, manufacturer_code=LUMI_MANUFACTURER_CODE
        )
        overload_protection: Final = ZCLAttributeDef(
            id=0x020B, type=t.Single, manufacturer_code=LUMI_MANUFACTURER_CODE
        )
        child_lock: Final = ZCLAttributeDef(
            id=0x0285, type=t.uint8_t, manufacturer_code=LUMI_MANUFACTURER_CODE
        )
        # 1 single click only, 2 also reports double, hold and release
        multi_click: Final = ZCLAttributeDef(
            id=0x0286, type=t.uint8_t, manufacturer_code=LUMI_MANUFACTURER_CODE
        )
        power_on_state: Final = ZCLAttributeDef(
            id=0x0517,
            type=AqaraH2UKPowerOnState,
            zcl_type=DataTypeId.uint8,
            manufacturer_code=LUMI_MANUFACTURER_CODE,
        )


(
    QuirkBuilder(AQARA, "lumi.plug.aeu002")
    .friendly_name(manufacturer="Aqara", model="Wall Outlet H2 UK")
    .replaces(AqaraH2UKElectricalMeasurement, endpoint_id=1)
    .replaces(AqaraH2UKElectricalMeasurement, endpoint_id=2)
    .replaces(AqaraH2UKElectricalMeasurement, endpoint_id=3)
    .replaces(AqaraH2UKManuCluster, endpoint_id=1)
    .replaces(AqaraH2UKManuCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .switch(
        AqaraH2UKManuCluster.AttributeDefs.child_lock.name,
        AqaraH2UKManuCluster.cluster_id,
        endpoint_id=1,
        translation_key="child_lock_socket_1",
        fallback_name="Socket 1 child lock",
    )
    .switch(
        AqaraH2UKManuCluster.AttributeDefs.child_lock.name,
        AqaraH2UKManuCluster.cluster_id,
        endpoint_id=2,
        translation_key="child_lock_socket_2",
        fallback_name="Socket 2 child lock",
    )
    .switch(
        AqaraH2UKManuCluster.AttributeDefs.multi_click.name,
        AqaraH2UKManuCluster.cluster_id,
        endpoint_id=1,
        off_value=1,
        on_value=2,
        translation_key="multi_click_socket_1",
        fallback_name="Socket 1 multi-click mode",
    )
    .switch(
        AqaraH2UKManuCluster.AttributeDefs.multi_click.name,
        AqaraH2UKManuCluster.cluster_id,
        endpoint_id=2,
        off_value=1,
        on_value=2,
        translation_key="multi_click_socket_2",
        fallback_name="Socket 2 multi-click mode",
    )
    .switch(
        AqaraH2UKManuCluster.AttributeDefs.led_indicator.name,
        AqaraH2UKManuCluster.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .switch(
        AqaraH2UKManuCluster.AttributeDefs.flip_indicator_light.name,
        AqaraH2UKManuCluster.cluster_id,
        translation_key="flip_indicator_light",
        fallback_name="Flip indicator light",
    )
    .number(
        AqaraH2UKManuCluster.AttributeDefs.overload_protection.name,
        AqaraH2UKManuCluster.cluster_id,
        min_value=100,
        max_value=3250,
        step=1,
        unit=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        translation_key="overload_protection",
        fallback_name="Overload protection",
    )
    .enum(
        AqaraH2UKManuCluster.AttributeDefs.power_on_state.name,
        AqaraH2UKPowerOnState,
        AqaraH2UKManuCluster.cluster_id,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON_1): {COMMAND: COMMAND_1_SINGLE},
            (DOUBLE_PRESS, BUTTON_1): {COMMAND: COMMAND_1_DOUBLE},
            (LONG_PRESS, BUTTON_1): {COMMAND: COMMAND_1_HOLD},
            (LONG_RELEASE, BUTTON_1): {COMMAND: COMMAND_1_RELEASE},
            (SHORT_PRESS, BUTTON_2): {COMMAND: COMMAND_2_SINGLE},
            (DOUBLE_PRESS, BUTTON_2): {COMMAND: COMMAND_2_DOUBLE},
            (LONG_PRESS, BUTTON_2): {COMMAND: COMMAND_2_HOLD},
            (LONG_RELEASE, BUTTON_2): {COMMAND: COMMAND_2_RELEASE},
        }
    )
    .add_to_registry()
)
