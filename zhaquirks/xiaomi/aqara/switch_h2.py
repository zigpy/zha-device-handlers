from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import Identify
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.const import (
    ARGS,
    ATTR_ID,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    ENDPOINT_ID,
    PRESS_TYPE,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import AnalogInputCluster, XiaomiAqaraE1Cluster
from zhaquirks.xiaomi.aqara.opple_switch import MultistateInputCluster


class AqaraOperationMode(types.enum8):
    """Aqara operation mode attribute values."""

    Decoupled = 0x00
    Relay = 0x01


class AqaraPowerOnMode(types.enum8):
    """Aqara power on mode attribute values."""

    On = 0x00
    Previous = 0x01
    Off = 0x02
    Inverted = 0x03


class PowerMeasurementCluster(AnalogInputCluster):
    """Custom cluster for power measurement."""

    PRESENT_VALUE_ATTRIBUTE = 0x0055

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.configure_reporting(
            self.PRESENT_VALUE_ATTRIBUTE,
            0,
            600,
            1,
        )
        return result

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.PRESENT_VALUE_ATTRIBUTE:
            self.listener_event(
                ZHA_SEND_EVENT,
                {
                    "type": "power_measurement",
                    "value": value,
                },
            )


class AqaraManuSpecificCluster(XiaomiAqaraE1Cluster):
    """Manufacturer-specific cluster for Lumi features."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions for Aqara switch."""

        power_on_mode = ZCLAttributeDef(
            id=0x0517,
            type=AqaraPowerOnMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        operation_mode = ZCLAttributeDef(
            id=0x0200,
            type=AqaraOperationMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        led_indicator = ZCLAttributeDef(
            id=0x0203,
            type=types.Bool,
            zcl_type=DataTypeId.bool_,
            access="rw",
            is_manufacturer_specific=True,
        )

        flip_led_indicator = ZCLAttributeDef(
            id=0x00F0,
            type=types.Bool,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        lock_relay = ZCLAttributeDef(
            id=0x0285,
            type=types.Bool,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )

        multi_click = ZCLAttributeDef(
            id=0x0286,
            type=types.Bool,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
        )


(
    QuirkBuilder("Aqara", "lumi.switch.agl010")
    .adds_endpoint(1, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(2, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(4, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(5, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(21, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds(Identify, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=2)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(MultistateInputCluster, endpoint_id=5)
    .replaces(AqaraManuSpecificCluster, endpoint_id=1)
    .replaces(AqaraManuSpecificCluster, endpoint_id=2)
    .replaces(AqaraManuSpecificCluster, endpoint_id=4)
    .replaces(AqaraManuSpecificCluster, endpoint_id=5)
    .replaces(PowerMeasurementCluster, endpoint_id=21)
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.led_indicator.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="led_indicator",
        fallback_name="LED Indicator",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.flip_led_indicator.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="flip_led_indicator",
        fallback_name="Flip LED Indicator",
    )
    .enum(
        AqaraManuSpecificCluster.AttributeDefs.power_on_mode.name,
        AqaraPowerOnMode,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="power_on_mode",
        fallback_name="Power On Mode",
    )
    .enum(
        AqaraManuSpecificCluster.AttributeDefs.operation_mode.name,
        AqaraOperationMode,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="operation_mode_left",
        fallback_name="Operation Mode Left",
        unique_id_suffix="left",
    )
    .enum(
        AqaraManuSpecificCluster.AttributeDefs.operation_mode.name,
        AqaraOperationMode,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=2,
        translation_key="operation_mode_right",
        fallback_name="Operation Mode Right",
        unique_id_suffix="right",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.lock_relay.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="lock_relay_left",
        fallback_name="Lock Relay Left",
        unique_id_suffix="left",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.lock_relay.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=2,
        translation_key="lock_relay_right",
        fallback_name="Lock Relay Right",
        unique_id_suffix="right",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.multi_click.name,
        AqaraManuSpecificCluster.cluster_id,
        off_value=1,
        on_value=2,
        endpoint_id=4,
        translation_key="multi_click_left",
        fallback_name="Multi Click Left",
        unique_id_suffix="left",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.multi_click.name,
        AqaraManuSpecificCluster.cluster_id,
        off_value=1,
        on_value=2,
        endpoint_id=5,
        translation_key="multi_click_right",
        fallback_name="Multi Click Right",
        unique_id_suffix="right",
    )
    .device_automation_triggers(
        {
            (COMMAND_HOLD, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_HOLD,
                    VALUE: 0,
                },
            },
            (COMMAND_SINGLE, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_SINGLE,
                    VALUE: 1,
                },
            },
            (COMMAND_DOUBLE, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_DOUBLE,
                    VALUE: 2,
                },
            },
            (COMMAND_RELEASE, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_RELEASE,
                    VALUE: 255,
                },
            },
            (COMMAND_HOLD, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_HOLD,
                    VALUE: 0,
                },
            },
            (COMMAND_SINGLE, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_SINGLE,
                    VALUE: 1,
                },
            },
            (COMMAND_DOUBLE, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_DOUBLE,
                    VALUE: 2,
                },
            },
            (COMMAND_RELEASE, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_RELEASE,
                    VALUE: 255,
                },
            },
            (COMMAND_HOLD, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_HOLD,
                    VALUE: 0,
                },
            },
            (COMMAND_SINGLE, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_SINGLE,
                    VALUE: 1,
                },
            },
            (COMMAND_DOUBLE, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_DOUBLE,
                    VALUE: 2,
                },
            },
            (COMMAND_RELEASE, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_RELEASE,
                    VALUE: 255,
                },
            },
            (COMMAND_HOLD, BUTTON_4): {
                ENDPOINT_ID: 5,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_HOLD,
                    VALUE: 0,
                },
            },
            (COMMAND_SINGLE, BUTTON_4): {
                ENDPOINT_ID: 5,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_SINGLE,
                    VALUE: 1,
                },
            },
            (COMMAND_DOUBLE, BUTTON_4): {
                ENDPOINT_ID: 5,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_DOUBLE,
                    VALUE: 2,
                },
            },
            (COMMAND_RELEASE, BUTTON_4): {
                ENDPOINT_ID: 5,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_RELEASE,
                    VALUE: 255,
                },
            },
        }
    )
    .add_to_registry()
)

(
    QuirkBuilder("Aqara", "lumi.switch.agl009")
    .adds_endpoint(1, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(4, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds_endpoint(21, device_type=zha.DeviceType.ON_OFF_SWITCH)
    .adds(Identify, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=1)
    .replaces(MultistateInputCluster, endpoint_id=4)
    .replaces(AqaraManuSpecificCluster, endpoint_id=1)
    .replaces(AqaraManuSpecificCluster, endpoint_id=4)
    .replaces(PowerMeasurementCluster, endpoint_id=21)
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.led_indicator.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="led_indicator",
        fallback_name="LED Indicator",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.flip_led_indicator.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="flip_led_indicator",
        fallback_name="Flip LED Indicator",
    )
    .enum(
        AqaraManuSpecificCluster.AttributeDefs.power_on_mode.name,
        AqaraPowerOnMode,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="power_on_mode",
        fallback_name="Power On Mode",
    )
    .enum(
        AqaraManuSpecificCluster.AttributeDefs.operation_mode.name,
        AqaraOperationMode,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="operation_mode",
        fallback_name="Operation Mode",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.lock_relay.name,
        AqaraManuSpecificCluster.cluster_id,
        endpoint_id=1,
        translation_key="lock_relay",
        fallback_name="Lock Relay",
    )
    .switch(
        AqaraManuSpecificCluster.AttributeDefs.multi_click.name,
        AqaraManuSpecificCluster.cluster_id,
        off_value=1,
        on_value=2,
        endpoint_id=4,
        translation_key="multi_click",
        fallback_name="Multi Click",
    )
    .device_automation_triggers(
        {
            (COMMAND_HOLD, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_HOLD,
                    VALUE: 0,
                },
            },
            (COMMAND_SINGLE, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_SINGLE,
                    VALUE: 1,
                },
            },
            (COMMAND_DOUBLE, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_DOUBLE,
                    VALUE: 2,
                },
            },
            (COMMAND_RELEASE, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_RELEASE,
                    VALUE: 255,
                },
            },
            (COMMAND_HOLD, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_HOLD,
                    VALUE: 0,
                },
            },
            (COMMAND_SINGLE, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_SINGLE,
                    VALUE: 1,
                },
            },
            (COMMAND_DOUBLE, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_DOUBLE,
                    VALUE: 2,
                },
            },
            (COMMAND_RELEASE, BUTTON_3): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: MultistateInputCluster.cluster_id,
                ARGS: {
                    ATTR_ID: 0x0055,
                    PRESS_TYPE: COMMAND_RELEASE,
                    VALUE: 255,
                },
            },
        }
    )
    .add_to_registry()
)
