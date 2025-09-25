"""NodOn on/off switch two channels."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
import zigpy.types as t
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.foundation import DataTypeId, ZCLAttributeDef

NODON = "NodOn"


class NodOnSwitchType(t.enum8):
    """NodOn switch type."""

    Bistable = 0x00
    Monostable = 0x01
    AutoDetect = 0x02


class OnOffSIN4_1_20(OnOff, CustomCluster):
    """NodOn custom OnOff cluster for SIN-4-1-20 and alike."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        """Select the switch type wire to the device. Available from version > V3.4.0."""
        switch_type = ZCLAttributeDef(
            id=0x1001,
            type=NodOnSwitchType,
            zcl_type=DataTypeId.enum8,  # need to explicitly set ZCL type
            access="rw",
            is_manufacturer_specific=True,
        )

        """Set the impulse duration in milliseconds (set value to 0 to deactivate the impulse mode). """
        impulse_mode_duration = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            access="rw",
            is_manufacturer_specific=True,
        )


class OnOffSIN4_2_20(OnOff, CustomCluster):
    """NodOn custom OnOff cluster for SIN-4-2-20 and alike."""

    class AttributeDefs(OnOff.AttributeDefs):
        """Attribute definitions."""

        """Select the switch type wire to the device. Available from version > V3.4.0."""
        switch_type = ZCLAttributeDef(
            id=0x1001,
            type=NodOnSwitchType,
            zcl_type=DataTypeId.enum8,  # need to explicitly set ZCL type
            access="rw",
            is_manufacturer_specific=True,
        )


(
    # quirk is similar to https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/nodon.ts#L100
    QuirkBuilder(NODON, "SIN-4-1-20")
    .applies_to(NODON, "SIN-4-1-21")
    .applies_to(NODON, "SIN-4-1-20_PRO")
    .replaces(OnOffSIN4_1_20)
    .enum(
        attribute_name=OnOffSIN4_1_20.AttributeDefs.switch_type.name,
        enum_class=NodOnSwitchType,
        cluster_id=OnOffSIN4_1_20.cluster_id,
        initially_disabled=True,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .number(
        attribute_name=OnOffSIN4_1_20.AttributeDefs.impulse_mode_duration.name,
        cluster_id=OnOffSIN4_1_20.cluster_id,
        min_value=0,
        max_value=10000,
        step=1,
        unit=UnitOfTime.MILLISECONDS,
        device_class=NumberDeviceClass.DURATION,
        initially_disabled=True,
        translation_key="impulse_mode_duration",
        fallback_name="Impulse mode duration",
    )
    .add_to_registry()
)

(
    # this quirk is a v2 version of 7397b6a
    QuirkBuilder(NODON, "SIN-4-2-20")
    .applies_to(NODON, "SIN-4-2-20_PRO")
    .removes(cluster_id=LevelControl.cluster_id, endpoint_id=1)
    .removes(cluster_id=LevelControl.cluster_id, endpoint_id=2)
    .replaces(OnOffSIN4_2_20, endpoint_id=1)
    .replaces(OnOffSIN4_2_20, endpoint_id=2)
    .enum(
        attribute_name=OnOffSIN4_1_20.AttributeDefs.switch_type.name,
        enum_class=NodOnSwitchType,
        cluster_id=OnOffSIN4_1_20.cluster_id,
        endpoint_id=1,
        initially_disabled=True,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .enum(
        attribute_name=OnOffSIN4_1_20.AttributeDefs.switch_type.name,
        enum_class=NodOnSwitchType,
        cluster_id=OnOffSIN4_1_20.cluster_id,
        endpoint_id=2,
        initially_disabled=True,
        translation_key="switch_type",
        fallback_name="Switch type",
    )
    .add_to_registry()
)
