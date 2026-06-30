"""Quirk for the Aqara Multi-State Sensor P100 (lumi.vibration.agl002 / DWZTCGQ11LM).

The P100 is a dual-mode sensor. In "object" mode it reports tap/movement/
vibration/orientation/fall events; in "door/window" mode it reports a contact
(open/closed) state. Without a quirk ZHA mis-maps the device to a door lock and a
generic on/off switch. This quirk removes those, exposes the Aqara configuration
attributes as Home Assistant entities, and surfaces the motion events as device
automation triggers.

Attribute IDs, types and value lookups follow the upstream
zigbee-herdsman-converters definition for this device, merged in
Koenkk/zigbee-herdsman-converters#11974, cross-checked against the device
diagnostics.
"""

from typing import Any, Final

from zha.application import Platform
from zigpy import types as t
from zigpy.zcl.clusters.closures import DoorLock
from zigpy.zcl.clusters.general import AnalogInput, OnOff
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import COMMAND, ZHA_SEND_EVENT
from zhaquirks.xiaomi import XiaomiAqaraE1Cluster, XiaomiPowerConfigurationPercent

# Action names emitted as zha_events / device automation triggers.
ACTION_TRIPLE_TAP = "triple_tap"
ACTION_MOVEMENT = "movement"
ACTION_VIBRATION = "vibration"
ACTION_ORIENTATION = "orientation"
ACTION_FALL = "fall"
ACTION_STATIC = "static"

# The five primary events arrive on the DoorLock cluster (0x0101) attribute 0x0055.
ACTION_ATTR_ID = 0x0055
ACTION_LOOKUP = {
    0: ACTION_TRIPLE_TAP,
    1: ACTION_MOVEMENT,
    2: ACTION_VIBRATION,
    3: ACTION_ORIENTATION,
    4: ACTION_FALL,
}


class DeviceMode(t.enum8):
    """Device operating mode (mutually exclusive)."""

    DoorWindow = 0x03
    Object = 0x05


class DoorWindowType(t.enum8):
    """Installation profile used in door/window mode."""

    Casement = 0x01
    Hopper = 0x02
    Composite = 0x03
    HingedDoor = 0x04


class Orientation(t.enum8):
    """Last reported orientation (relevant when action == orientation)."""

    FaceUp = 0x01
    FaceDown = 0x02
    Vertical = 0x03
    Tilt = 0x04


class DevicePosture(t.enum8):
    """Mounting orientation check.

    'Abnormal' when the sensor is incorrectly installed or needs calibration.
    """

    Normal = 0x01
    Abnormal = 0x02


class P100ManufacturerCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer-specific cluster (0xFCC0) for the P100.

    Holds the configuration attributes and the 'static' state flag. Battery is
    parsed from the periodic Aqara heartbeat blob (0x00F7) by the inherited
    XiaomiCluster handling and forwarded to XiaomiPowerConfigurationPercent.
    """

    # The "static" event has no representation on the DoorLock cluster; it is
    # signalled by attribute 0x01F3 transitioning to 1 once the device settles.
    STATIC_STATE_ATTR_ID = 0x01F3

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        vibration_detection: Final = ZCLAttributeDef(
            id=0x0107, type=t.Bool, access="rwp", is_manufacturer_specific=True
        )
        sensitivity: Final = ZCLAttributeDef(
            id=0x010C, type=t.uint8_t, access="rwp", is_manufacturer_specific=True
        )
        device_mode: Final = ZCLAttributeDef(
            id=0x0116,
            type=DeviceMode,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            is_manufacturer_specific=True,
        )
        fall_detection: Final = ZCLAttributeDef(
            id=0x01D8, type=t.Bool, access="rwp", is_manufacturer_specific=True
        )
        door_window_type: Final = ZCLAttributeDef(
            id=0x01EB,
            type=DoorWindowType,
            zcl_type=DataTypeId.uint8,
            access="rwp",
            is_manufacturer_specific=True,
        )
        report_interval: Final = ZCLAttributeDef(
            id=0x01EC, type=t.uint32_t, access="rwp", is_manufacturer_specific=True
        )
        movement_detection: Final = ZCLAttributeDef(
            id=0x01ED, type=t.Bool, access="rwp", is_manufacturer_specific=True
        )
        device_posture: Final = ZCLAttributeDef(
            id=0x01EE,
            type=DevicePosture,
            zcl_type=DataTypeId.uint8,
            access="rp",
            is_manufacturer_specific=True,
        )
        triple_tap_detection: Final = ZCLAttributeDef(
            id=0x01EF, type=t.Bool, access="rwp", is_manufacturer_specific=True
        )
        orientation_detection: Final = ZCLAttributeDef(
            id=0x01F0, type=t.Bool, access="rwp", is_manufacturer_specific=True
        )
        orientation: Final = ZCLAttributeDef(
            id=0x01F1,
            type=Orientation,
            zcl_type=DataTypeId.uint8,
            access="rp",
            is_manufacturer_specific=True,
        )
        static_state: Final = ZCLAttributeDef(
            id=0x01F3, type=t.uint8_t, access="rp", is_manufacturer_specific=True
        )
        # Battery reported as direct attributes (as used by the Z2M converter)
        # in addition to / instead of the Aqara heartbeat blob below.
        battery_voltage: Final = ZCLAttributeDef(
            id=0x0017, type=t.uint16_t, access="rp", is_manufacturer_specific=True
        )
        battery_percentage: Final = ZCLAttributeDef(
            id=0x0018, type=t.uint8_t, access="rp", is_manufacturer_specific=True
        )
        # Aqara heartbeat blob carrying battery voltage/percentage.
        aqara_attributes: Final = ZCLAttributeDef(
            id=0x00F7, type=t.LVBytes, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == self.STATIC_STATE_ATTR_ID and value == 1:
            self.listener_event(ZHA_SEND_EVENT, ACTION_STATIC, {})
        elif attrid == self.AttributeDefs.battery_voltage.id:
            # Voltage in mV; XiaomiPowerConfigurationPercent uses it for the
            # voltage attribute only, not for the percentage.
            self.endpoint.power.battery_reported(value)
        elif attrid == self.AttributeDefs.battery_percentage.id:
            # Already a 0-100 percentage; the power cluster scales to 0-200.
            self.endpoint.power.battery_percent_reported(value)


class P100ActionCluster(CustomCluster, DoorLock):
    """DoorLock-based cluster that turns the P100 motion events into zha_events.

    The device advertises a DoorLock cluster but uses attribute 0x0055 to report
    the five primary motion events rather than a real lock state.
    """

    class AttributeDefs(DoorLock.AttributeDefs):
        """Attribute definitions."""

        action_status: Final = ZCLAttributeDef(
            id=ACTION_ATTR_ID, type=t.uint16_t, is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == ACTION_ATTR_ID:
            action = ACTION_LOOKUP.get(value)
            if action is not None:
                self.listener_event(ZHA_SEND_EVENT, action, {})


def _is_default_switch(entity: Any) -> bool:
    """Match only the default OnOff switch entity.

    ``prevent_default_entity_creation`` is evaluated against every discovered
    entity, including this quirk's own Contact binary sensor (which also targets
    the OnOff cluster). ``entity.PLATFORM`` is ZHA's ``Platform`` enum, so
    compare against ``Platform.SWITCH`` to drop the switch while keeping the
    binary sensor.
    """
    return entity.PLATFORM == Platform.SWITCH


(
    QuirkBuilder("Aqara", "lumi.vibration.agl002")
    # Remove the entities ZHA creates by default from the raw signature.
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=DoorLock.cluster_id)
    # Only remove the default writable switch on OnOff; keep our Contact
    # binary sensor, which also targets this cluster.
    .prevent_default_entity_creation(
        endpoint_id=1,
        cluster_id=OnOff.cluster_id,
        function=_is_default_switch,
    )
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=AnalogInput.cluster_id)
    .prevent_default_entity_creation(endpoint_id=2, cluster_id=AnalogInput.cluster_id)
    # Custom clusters.
    .replaces(P100ManufacturerCluster)
    .replaces(P100ActionCluster)
    .adds(XiaomiPowerConfigurationPercent)
    # Contact (door/window mode). onOff == 1 means the contact is open.
    .binary_sensor(
        OnOff.AttributeDefs.on_off.name,
        OnOff.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.OPENING,
        attribute_converter=bool,
        primary=True,
        fallback_name="Contact",
    )
    # Configuration entities (manufacturer cluster).
    .enum(
        P100ManufacturerCluster.AttributeDefs.device_mode.name,
        DeviceMode,
        P100ManufacturerCluster.cluster_id,
        translation_key="device_mode",
        fallback_name="Device mode",
    )
    .enum(
        P100ManufacturerCluster.AttributeDefs.door_window_type.name,
        DoorWindowType,
        P100ManufacturerCluster.cluster_id,
        translation_key="door_window_type",
        fallback_name="Door/window type",
    )
    .number(
        P100ManufacturerCluster.AttributeDefs.sensitivity.name,
        P100ManufacturerCluster.cluster_id,
        min_value=1,
        max_value=10,
        step=1,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .number(
        P100ManufacturerCluster.AttributeDefs.report_interval.name,
        P100ManufacturerCluster.cluster_id,
        min_value=5,
        max_value=300,
        step=1,
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="report_interval",
        fallback_name="Report interval",
    )
    .switch(
        P100ManufacturerCluster.AttributeDefs.movement_detection.name,
        P100ManufacturerCluster.cluster_id,
        translation_key="movement_detection",
        fallback_name="Movement detection",
    )
    .switch(
        P100ManufacturerCluster.AttributeDefs.vibration_detection.name,
        P100ManufacturerCluster.cluster_id,
        translation_key="vibration_detection",
        fallback_name="Vibration detection",
    )
    .switch(
        P100ManufacturerCluster.AttributeDefs.fall_detection.name,
        P100ManufacturerCluster.cluster_id,
        translation_key="fall_detection",
        fallback_name="Fall detection",
    )
    .switch(
        P100ManufacturerCluster.AttributeDefs.orientation_detection.name,
        P100ManufacturerCluster.cluster_id,
        translation_key="orientation_detection",
        fallback_name="Orientation detection",
    )
    .switch(
        P100ManufacturerCluster.AttributeDefs.triple_tap_detection.name,
        P100ManufacturerCluster.cluster_id,
        translation_key="triple_tap_detection",
        fallback_name="Triple tap detection",
    )
    # Read-only diagnostics.
    .enum(
        P100ManufacturerCluster.AttributeDefs.orientation.name,
        Orientation,
        P100ManufacturerCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="orientation",
        fallback_name="Orientation",
    )
    .enum(
        P100ManufacturerCluster.AttributeDefs.device_posture.name,
        DevicePosture,
        P100ManufacturerCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="device_posture",
        fallback_name="Device posture",
    )
    .device_automation_triggers(
        {
            (ACTION_TRIPLE_TAP, ACTION_TRIPLE_TAP): {COMMAND: ACTION_TRIPLE_TAP},
            (ACTION_MOVEMENT, ACTION_MOVEMENT): {COMMAND: ACTION_MOVEMENT},
            (ACTION_VIBRATION, ACTION_VIBRATION): {COMMAND: ACTION_VIBRATION},
            (ACTION_ORIENTATION, ACTION_ORIENTATION): {COMMAND: ACTION_ORIENTATION},
            (ACTION_FALL, ACTION_FALL): {COMMAND: ACTION_FALL},
            (ACTION_STATIC, ACTION_STATIC): {COMMAND: ACTION_STATIC},
        }
    )
    .add_to_registry()
)
