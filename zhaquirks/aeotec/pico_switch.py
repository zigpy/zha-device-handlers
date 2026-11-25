"""Aeotec Pico Switch (ZGA002)."""

from typing import Final

from zha.application.platforms.sensor import DeviceTemperature
import zigpy.types as t
from zigpy.zcl.clusters.general import DeviceTemperature as DeviceTemperatureCluster
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster

AEOTEC_MANUFACTURER_CODE = 0x1310  # 4880, "AEOTEC LIMITED"


class AeotecSwitchType(t.enum8):
    """Physical type of the wired external switch."""

    Toggle = 0x00  # maintained / rocker switch
    Momentary = 0x01  # push button
    Auto_Detect = 0x04  # device figures out the switch type on its own


class AeotecSwitchActions(t.enum8):
    """How the external switch state drives the relay."""

    Follow = 0x00  # relay mirrors switch position (closed = on, open = off)
    Invert = 0x01  # relay is the inverse of switch position
    Toggle = 0x02  # every switch edge toggles the relay, position-independent


class AeotecControls(t.enum8):
    """Whether the external switch can control the relay locally."""

    Disabled = 0x00
    Enabled = 0x01


class AeotecSwitchTypeConfigCluster(CustomCluster):
    """Aeotec manufacturer-specific switch type configuration cluster [0xFD00]."""

    cluster_id: t.uint16_t = 0xFD00
    name: str = "Aeotec Switch Type Configuration"
    ep_attribute: str = "aeotec_switch_type_config"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        switch_type: Final = ZCLAttributeDef(
            id=0x0000,
            type=AeotecSwitchType,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_CODE,
        )
        switch_actions: Final = ZCLAttributeDef(
            id=0x0010,
            type=AeotecSwitchActions,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_CODE,
        )
        controls: Final = ZCLAttributeDef(
            id=0x0011,
            type=AeotecControls,
            access="rw",
            manufacturer_code=AEOTEC_MANUFACTURER_CODE,
        )


class WholeDegreeDeviceTemperature(DeviceTemperature):
    """Device temperature in whole degrees."""

    _divisor = None  # Setting it to `1` would make the temperature a float
    _attr_suggested_display_precision = 0
    _attr_fallback_name = "Device temperature"


(
    QuirkBuilder("AEOTEC", "ZGA002")
    .friendly_name(manufacturer="Aeotec", model="Pico Switch")
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=2)
    .replaces(AeotecSwitchTypeConfigCluster, endpoint_id=3)
    .replaces_entity(
        DeviceTemperature,
        WholeDegreeDeviceTemperature,
        endpoint_id=1,
        cluster_id=DeviceTemperatureCluster.cluster_id,
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=2,
        translation_key="switch_type_id",
        fallback_name="S1 switch type",
        translation_placeholders={"id": "S1"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=2,
        translation_key="switch_actions_id",
        fallback_name="S1 switch actions",
        translation_placeholders={"id": "S1"},
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=2,
        translation_key="local_control_id",
        fallback_name="S1 local control",
        translation_placeholders={"id": "S1"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_type.name,
        enum_class=AeotecSwitchType,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="switch_type_id",
        fallback_name="S2 switch type",
        translation_placeholders={"id": "S2"},
    )
    .enum(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.switch_actions.name,
        enum_class=AeotecSwitchActions,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="switch_actions_id",
        fallback_name="S2 switch actions",
        translation_placeholders={"id": "S2"},
    )
    .switch(
        attribute_name=AeotecSwitchTypeConfigCluster.AttributeDefs.controls.name,
        cluster_id=AeotecSwitchTypeConfigCluster.cluster_id,
        endpoint_id=3,
        translation_key="local_control_id",
        fallback_name="S2 local control",
        translation_placeholders={"id": "S2"},
    )
    .add_to_registry()
)
