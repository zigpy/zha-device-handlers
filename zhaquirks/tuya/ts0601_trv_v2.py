"""Tuya TS0601 TRV."""

from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.types import t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.tuya import TUYA_QUERY_DATA, TuyaNewManufCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaAttributesCluster


class EnchantedDeviceV2(CustomDeviceV2):
    """Class for Tuya devices which need to be unlocked by casting a 'spell'.

    The spell is applied during device configuration.
    """

    # These values can be overridden from a quirk to enable (or disable) additional Tuya spells:
    tuya_spell_read_attributes: bool = True  # spell reading attributes on Basic cluster
    tuya_spell_data_query: bool = False  # additional spell needed for some devices

    async def apply_custom_configuration(self, *args, **kwargs):
        """Hooks device configuration to apply custom configuration."""
        # cast Tuya spell
        if self.tuya_spell_read_attributes:
            await self.spell_attribute_reads()
        if self.tuya_spell_data_query:
            await self.spell_data_query()

        # also apply custom configuration to clusters if defined
        await super().apply_custom_configuration(*args, **kwargs)

    async def spell_attribute_reads(self):
        """Cast 'attribute read' spell, so the Tuya device works correctly."""
        self.debug(
            "Executing attribute read spell on Tuya device %s",
            self.ieee,
        )
        attr_to_read = [4, 0, 1, 5, 7, 0xFFFE]
        basic_cluster = self.endpoints[1].in_clusters[Basic.cluster_id]
        await basic_cluster.read_attributes(attr_to_read)
        self.debug("Executed attribute read spell on Tuya device %s", self.ieee)

    async def spell_data_query(self):
        """Cast 'data query' spell, also required for some Tuya devices to send data."""
        self.debug("Executing data query spell on Tuya device %s", self.ieee)
        # tests verify that a device with an enabled 'data query spell' has a TuyaNewManufCluster (subclass)
        tuya_cluster = self.endpoints[1].in_clusters[TuyaNewManufCluster.cluster_id]
        await tuya_cluster.command(TUYA_QUERY_DATA)
        self.debug("Executed data query spell on Tuya device %s", self.ieee)


class TuyaThermostatSystemMode(t.enum8):
    """Tuya thermostat system mode enum."""

    Auto = 0x00
    Heat = 0x01
    Off = 0x02


class TuyaThermostat(Thermostat, TuyaAttributesCluster):
    """Tuya local thermostat cluster."""

    manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID

    _CONSTANT_ATTRIBUTES = {
        Thermostat.AttributeDefs.ctrl_sequence_of_oper.id: Thermostat.ControlSequenceOfOperation.Heating_Only
    }

    def __init__(self, *args, **kwargs):
        """Init a TuyaThermostat cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source.id
        )
        self.add_unsupported_attribute(
            Thermostat.AttributeDefs.setpoint_change_source_timestamp.id
        )
        self.add_unsupported_attribute(Thermostat.AttributeDefs.pi_heating_demand.id)

    async def write_attributes(self, attributes, manufacturer=None):
        """Overwrite to force manufacturer code."""

        return await super().write_attributes(
            attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
        )


(
    TuyaQuirkBuilder("_TZE204_ogx8u5z6", "TS0601")
    .tuya_dp(
        dp_id=2,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.system_mode.name,
        converter=lambda x: {
            TuyaThermostatSystemMode.Auto: Thermostat.SystemMode.Auto,
            TuyaThermostatSystemMode.Heat: Thermostat.SystemMode.Heat,
            TuyaThermostatSystemMode.Off: Thermostat.SystemMode.Off,
        }[x],
        dp_converter=lambda x: {
            Thermostat.SystemMode.Auto: TuyaThermostatSystemMode.Auto,
            Thermostat.SystemMode.Heat: TuyaThermostatSystemMode.Heat,
            Thermostat.SystemMode.Off: TuyaThermostatSystemMode.Off,
        }[x],
    )
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.occupied_heating_setpoint.name,
        converter=lambda x: x * 10,
        dp_converter=lambda x: x // 10,
    )
    .tuya_dp(
        dp_id=5,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.local_temperature.name,
        converter=lambda x: x * 10,
    )
    .tuya_dp(
        dp_id=47,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=Thermostat.AttributeDefs.local_temperature_calibration.name,
        converter=lambda x: x,
        dp_converter=lambda x: x + 0x100000000 if x < 0 else x,
    )
    .tuya_switch(
        dp_id=7,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_switch(
        dp_id=35,
        attribute_name="frost_protection",
        translation_key="frost_protection",
        fallback_name="Frost protection",
    )
    .tuya_switch(
        dp_id=39,
        attribute_name="scale_protection",
        translation_key="scale_protection",
        fallback_name="Scale protection",
    )
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaThermostat.ep_attribute,
        attribute_name=TuyaThermostat.AttributeDefs.running_state.name,
        converter=lambda x: 0x01 if not x else 0x00,  # Heat, Idle
    )
    .tuya_binary_sensor(
        dp_id=35,
        attribute_name="error",
        translation_key="error",
        fallback_name="Error or battery low",
    )
    .adds(TuyaThermostat)
    .device_class(EnchantedDeviceV2)
    .skip_configuration()
    .add_to_registry()
)
