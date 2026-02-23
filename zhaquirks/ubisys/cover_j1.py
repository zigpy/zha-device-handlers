"""Ubisys Cover J1 quirk."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.quirk_ids import SE_POLL_SUMMATION
from zhaquirks.ubisys import UbisysCluster, UbisysInputConfigCluster


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysWindowCovering(CustomCluster, WindowCovering):
    """WindowCovering with ubisys manufacturer-specific calibration attributes.

    The device has writable versions of standard read-only attributes at the
    same IDs but with manufacturer code 0x10F2. These are used during
    calibration to configure the cover type, limits, and step counts.
    """

    class AttributeDefs(WindowCovering.AttributeDefs):
        """Extended WindowCovering attributes for ubisys calibration."""

        # Writable versions of standard attributes (same IDs, manufacturer code 0x10F2)
        window_covering_type_config: Final = ZCLAttributeDef(
            id=0x0000, type=t.enum8, manufacturer_code=0x10F2
        )
        config_status_config: Final = ZCLAttributeDef(
            id=0x0007, type=t.bitmap8, manufacturer_code=0x10F2
        )
        installed_open_limit_lift_config: Final = ZCLAttributeDef(
            id=0x0010, type=t.uint16_t, manufacturer_code=0x10F2
        )
        installed_closed_limit_lift_config: Final = ZCLAttributeDef(
            id=0x0011, type=t.uint16_t, manufacturer_code=0x10F2
        )
        installed_open_limit_tilt_config: Final = ZCLAttributeDef(
            id=0x0012, type=t.uint16_t, manufacturer_code=0x10F2
        )
        installed_closed_limit_tilt_config: Final = ZCLAttributeDef(
            id=0x0013, type=t.uint16_t, manufacturer_code=0x10F2
        )
        # Manufacturer-specific calibration attributes
        turnaround_guard_time: Final = ZCLAttributeDef(
            id=0x1000, type=t.uint8_t, manufacturer_code=0x10F2
        )
        lift_to_tilt_transition_steps: Final = ZCLAttributeDef(
            id=0x1001, type=t.uint16_t, manufacturer_code=0x10F2
        )
        total_steps: Final = ZCLAttributeDef(
            id=0x1002, type=t.uint16_t, manufacturer_code=0x10F2
        )
        lift_to_tilt_transition_steps_2: Final = ZCLAttributeDef(
            id=0x1003, type=t.uint16_t, manufacturer_code=0x10F2
        )
        total_steps_2: Final = ZCLAttributeDef(
            id=0x1004, type=t.uint16_t, manufacturer_code=0x10F2
        )
        additional_steps: Final = ZCLAttributeDef(
            id=0x1005, type=t.uint8_t, manufacturer_code=0x10F2
        )
        inactive_power_threshold: Final = ZCLAttributeDef(
            id=0x1006, type=t.uint16_t, manufacturer_code=0x10F2
        )
        startup_steps: Final = ZCLAttributeDef(
            id=0x1007, type=t.uint16_t, manufacturer_code=0x10F2
        )


class UbisysJ1InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the J1.

    EP2 -> EP1 with WindowCovering self-binding.
    Only detached mode is exposed (input_mode templates are OnOff-based
    and don't apply to cover commands).
    """

    BIND_CLUSTERS: list[int] = [WindowCovering.cluster_id]


(
    QuirkBuilder(manufacturer="ubisys", model="J1 (5502)")
    .applies_to(manufacturer="ubisys", model="J1-R (5602)")
    .replaces(UbisysCluster, endpoint_id=232)
    .replaces(UbisysWindowCovering, endpoint_id=1)
    .enum(
        attribute_name=UbisysWindowCovering.AttributeDefs.window_covering_type_config.name,
        enum_class=WindowCovering.WindowCoveringType,
        cluster_id=UbisysWindowCovering.cluster_id,
        translation_key="window_covering_type",
        fallback_name="Window covering type",
    )
    .number(
        attribute_name=UbisysWindowCovering.AttributeDefs.inactive_power_threshold.name,
        cluster_id=UbisysWindowCovering.cluster_id,
        min_value=0,
        max_value=65534,
        step=1,
        translation_key="inactive_power_threshold",
        fallback_name="Inactive power threshold",
    )
    .adds(UbisysJ1InputConfigCluster)
    .switch(
        attribute_name=UbisysJ1InputConfigCluster.AttributeDefs.detached.name,
        cluster_id=UbisysJ1InputConfigCluster.cluster_id,
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .applies_to(manufacturer="ubisys", model="J1-R (5602)")
    .replaces(UbisysElectricalMeasurement, endpoint_id=3)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="3-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .add_to_registry()
)
