"""Intelligent keypad."""

from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasWd, IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.builder import BinarySensorDeviceClass, EntityFilter, QuirkBuilder
from zhaquirks.develco import FRIENT

# Firmware 2.0 and newer reports `battery_percentage_remaining` itself
FIRMWARE_2_0 = 0x00020000


class KeypadPowerConfiguration(PowerConfigurationCluster):
    """Battery percentage derived from the voltage of the 4x AA pack."""

    MIN_VOLTS = 4.0  # the keypad flags a low battery below 4.0 V
    MAX_VOLTS = 6.0  # 4x 1.5 V


BASE_KEYPAD_QUIRK = (
    QuirkBuilder(FRIENT, "KEPZB-110")
    .prevent_default_entity_creation(endpoint_id=44, cluster_id=BinaryInput.cluster_id)
    # Hide the default `ias_zone` entity
    .removes_entity(
        EntityFilter(
            endpoint_id=44,
            cluster_id=IasZone.cluster_id,
            translation_key="ias_zone",
        )
    )
    .removes_entity(
        *(
            EntityFilter(
                endpoint_id=44,
                cluster_id=IasWd.cluster_id,
                translation_key=translation_key,
            )
            for translation_key in (
                "default_siren_tone",
                "default_siren_level",
                "default_strobe_level",
                "default_strobe",
            )
        )
    )
    .binary_sensor(
        endpoint_id=44,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
)

(
    # Firmware 1.x only reports the battery voltage
    BASE_KEYPAD_QUIRK.clone(omit_man_model_data=False)
    .firmware_version_filter(max_version=FIRMWARE_2_0, allow_missing=False)
    .replaces(KeypadPowerConfiguration, endpoint_id=44)
    .add_to_registry()
)

(
    BASE_KEYPAD_QUIRK.clone(omit_man_model_data=False)
    .firmware_version_filter(min_version=FIRMWARE_2_0, allow_missing=True)
    .add_to_registry()
)
