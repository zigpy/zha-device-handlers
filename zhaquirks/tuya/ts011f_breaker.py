"""TS011F Circuit Breaker * Tongou TO-Q-SY2-JZT."""

from typing import Any, Optional, Union
import logging
import enum
from struct import iter_unpack, pack

from zigpy.profiles import zgp, zha
from zigpy.quirks.v2 import QuirkBuilder, CustomDeviceV2
from zigpy.quirks.v2.homeassistant import (
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfPower,
)
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks import LocalDataCluster

from zhaquirks.quirk_ids import TUYA_PLUG_ONOFF
from zhaquirks.tuya import (
    EnchantedDevice,
    TuyaNewManufCluster,
    TuyaZB1888Cluster,
    TuyaZBE000Cluster,
    TuyaZBElectricalMeasurement,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBMeteringCluster,
    TuyaZBMeteringClusterWithUnit,
    TuyaZBOnOffAttributeCluster,
    TuyaLocalCluster,
)

_LOGGER = logging.getLogger("ts011f_breaker")

TUYA_OPTIONS_2_DATA = 0xE6
TUYA_OPTIONS_3_DATA = 0xE7


class Breaker(t.enum8):
    Off = 0x00
    On = 0x01


class TuyaZBExternalSwitchTypeThresholdCluster(
    LocalDataCluster, TuyaZBExternalSwitchTypeCluster
):
    """Tuya External Switch Type With Threshold Cluster."""

    name = "Tuya External Switch Type With Threshold Cluster"
    ep_attribute = "tuya_external_switch_type_threshold"

    class AttributeDefs(TuyaZBExternalSwitchTypeCluster.AttributeDefs):
        """Attribute definitions."""

        temperature_breaker = foundation.ZCLAttributeDef(
            id=0xE605,
            type=Breaker,
            is_manufacturer_specific=True,
            zcl_type=foundation.DataTypeId.uint8,
        )
        temperature_threshold = foundation.ZCLAttributeDef(
            id=0xE685, type=t.uint16_t, is_manufacturer_specific=True
        )
        power_breaker = foundation.ZCLAttributeDef(
            id=0xE607,
            type=Breaker,
            is_manufacturer_specific=True,
            zcl_type=foundation.DataTypeId.uint8,
        )
        power_threshold = foundation.ZCLAttributeDef(
            id=0xE687, type=t.uint16_t, is_manufacturer_specific=True
        )
        over_current_breaker = foundation.ZCLAttributeDef(
            id=0xE701,
            type=Breaker,
            is_manufacturer_specific=True,
            zcl_type=foundation.DataTypeId.uint8,
        )
        over_current_threshold = foundation.ZCLAttributeDef(
            id=0xE781, type=t.uint16_t, is_manufacturer_specific=True
        )
        over_voltage_breaker = foundation.ZCLAttributeDef(
            id=0xE703,
            type=Breaker,
            is_manufacturer_specific=True,
            zcl_type=foundation.DataTypeId.uint8,
        )
        over_voltage_threshold = foundation.ZCLAttributeDef(
            id=0xE783, type=t.uint16_t, is_manufacturer_specific=True
        )
        under_voltage_breaker = foundation.ZCLAttributeDef(
            id=0xE704,
            type=Breaker,
            is_manufacturer_specific=True,
            zcl_type=foundation.DataTypeId.uint8,
        )
        under_voltage_threshold = foundation.ZCLAttributeDef(
            id=0xE784, type=t.uint16_t, is_manufacturer_specific=True
        )

    class ServerCommandDefs(TuyaZBExternalSwitchTypeCluster.ServerCommandDefs):
        """Server command definitions."""

        set_options_2 = foundation.ZCLCommandDef(
            TUYA_OPTIONS_2_DATA,
            {"data?": t.SerializableBytes},
            is_manufacturer_specific=True,
        )
        set_options_3 = foundation.ZCLCommandDef(
            TUYA_OPTIONS_3_DATA,
            {"data?": t.SerializableBytes},
            is_manufacturer_specific=True,
        )

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: tuple,
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""
        data = args

        _LOGGER.debug(
            "[0x%04x:%s:0x%04x] Received value %s "
            "for attribute 0x%04x (command 0x%04x)",
            self.endpoint.device.nwk,
            self.endpoint.endpoint_id,
            self.cluster_id,
            repr(data),
            hdr.command_id,
            hdr.command_id,
        )

        if hdr.command_id in (TUYA_OPTIONS_2_DATA, TUYA_OPTIONS_3_DATA):
            for (attr_id, breaker, threshold) in iter_unpack(">bbH", data):
                self._update_attribute((hdr.command_id << 8) + attr_id, breaker)
                self._update_attribute(
                    (hdr.command_id << 8) + 0x80 + attr_id, threshold
                )

        super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)

    async def write_attributes(self, attributes, manufacturer=None):
        """Defer attributes writing to the set_options_* command."""

        local, remote = {}, {}

        remote_attr_ids = list(
            map(
                lambda attrDef: attrDef.id,
                TuyaZBExternalSwitchTypeCluster.AttributeDefs,
            )
        )

        for key, value in attributes.items():
            if (
                key in TuyaZBExternalSwitchTypeCluster.AttributeDefs
                or key in remote_attr_ids
            ):
                remote[key] = value
            else:
                local[key] = value

        _LOGGER.debug(
            "write_attributes attrs:  %s local: %s remote %s",
            repr(attributes),
            repr(local),
            repr(remote),
        )

        if local:
            records = self._write_attr_records(local)

            _LOGGER.debug("write_attributes records:  %s ", repr(records))

            command_attributes = {TUYA_OPTIONS_2_DATA: {}, TUYA_OPTIONS_3_DATA: {}}

            for attribute in records:
                attr_id = attribute.attrid
                command_id = attr_id >> 8
                comp_attr_id = attr_id ^ 0x80
                if not attr_id in command_attributes[command_id]:
                    if comp_attr_id in local:
                        comp_attr = next(
                            filter(lambda a: a.id == comp_attr_id, records), None
                        )
                        comp_value = comp_attr.value.value
                    else:
                        comp_value = self.get(comp_attr_id)

                    if comp_value != None:
                        command_attributes[command_id][attr_id & 0x7F] = {
                            ((attr_id & 0x80) >> 7): attribute.value.value,
                            ((comp_attr_id & 0x80) >> 7): comp_value,
                        }

            for command_id, command_attribute in command_attributes.items():
                if command_attribute:
                    data = bytearray(b"")
                    for attr_id, values in command_attribute.items():
                        data.extend(pack(">bbH", attr_id, values[0], values[1]))

                    await super().command(command_id, data)

        if remote:
            await TuyaZBExternalSwitchTypeCluster.write_attributes(
                self, remote, manufacturer
            )

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def read_attributes(
        self,
        attributes: list[int | str],
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: int | t.uint16_t | None = None,
    ) -> Any:
        local_success, local_failure = {}, {}
        remote_success, remote_failure = {}, {}
        local, remote = [], []

        remote_attr_ids = list(
            map(
                lambda attrDef: attrDef.id,
                TuyaZBExternalSwitchTypeCluster.AttributeDefs,
            )
        )

        for attribute in attributes:
            if isinstance(attribute, str):
                attrid = self.attributes_by_name[attribute].id
            else:
                # Allow reading attributes that aren't defined
                attrid = attribute

            if attrid in remote_attr_ids:
                remote.append(attrid)
            else:
                local.append(attrid)

        _LOGGER.debug(
            "read_attributes attrs:  %s local: %s remote %s",
            repr(attributes),
            repr(local),
            repr(remote),
        )

        if local:
            local_success, local_failure = await LocalDataCluster.read_attributes(
                self, local, allow_cache, only_cache, manufacturer
            )

        if remote:
            (
                remote_success,
                remote_failure,
            ) = await TuyaZBExternalSwitchTypeCluster.read_attributes(
                self, remote, allow_cache, only_cache, manufacturer
            )

        return local_success | remote_success, local_failure | remote_failure


class CB_Metering_Threshold(CustomDeviceV2, EnchantedDevice):
    """Circuit breaker with monitoring, e.g. Tongou TO-Q-SY2-JZT. First one using this definition was _TZ3000_cayepv1a."""

    quirk_id = TUYA_PLUG_ONOFF


(
    QuirkBuilder("_TZ3000_cayepv1a", "TS011F")
    .also_applies_to("_TZ3000_lepzuhto", "TS011F")
    .also_applies_to("_TZ3000_qystbcjg", "TS011F")
    .device_class(CB_Metering_Threshold)
    .replaces(TuyaZBOnOffAttributeCluster)
    .replaces(TuyaZBMeteringCluster)
    .replaces(TuyaZBElectricalMeasurement)
    .replaces(TuyaZBE000Cluster)
    .replaces(TuyaZBExternalSwitchTypeThresholdCluster)
    .switch(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.temperature_breaker.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        fallback_name="Temperature Breaker",
        translation_key=TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.temperature_breaker.name,
    )
    .number(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.temperature_threshold.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=40,
        max_value=100,
        unit=UnitOfTemperature.CELSIUS,
        mode="box",
        fallback_name="Temperature Threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
    )
    .switch(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.power_breaker.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        fallback_name="Power Breaker",
        translation_key=TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.power_breaker.name,
    )
    .number(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.power_threshold.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=1,
        max_value=26,
        unit=UnitOfPower.KILO_WATT,
        mode="box",
        fallback_name="Power Threshold",
        device_class=NumberDeviceClass.POWER,
    )
    .switch(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.over_current_breaker.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        fallback_name="Over Current Breaker",
        translation_key=TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.over_current_breaker.name,
    )
    .number(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.over_current_threshold.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=1,
        max_value=63,
        unit=UnitOfElectricCurrent.AMPERE,
        mode="box",
        fallback_name="Over Current Threshold",
        device_class=NumberDeviceClass.CURRENT,
    )
    .switch(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.over_voltage_breaker.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        fallback_name="Over Voltage Breaker",
        translation_key=TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.over_voltage_breaker.name,
    )
    .number(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.over_voltage_threshold.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=230,
        max_value=265,
        unit=UnitOfElectricPotential.VOLT,
        mode="box",
        fallback_name="Over Voltage Threshold",
        device_class=NumberDeviceClass.VOLTAGE,
    )
    .switch(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.under_voltage_breaker.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        fallback_name="Under Voltage Breaker",
        translation_key=TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.under_voltage_breaker.name,
    )
    .number(
        TuyaZBExternalSwitchTypeThresholdCluster.AttributeDefs.under_voltage_threshold.name,
        TuyaZBExternalSwitchTypeThresholdCluster.cluster_id,
        attribute_initialized_from_cache=False,
        min_value=75,
        max_value=240,
        unit=UnitOfElectricPotential.VOLT,
        mode="box",
        fallback_name="Under Voltage Threshold",
        device_class=NumberDeviceClass.VOLTAGE,
    )
    .add_to_registry()
)
