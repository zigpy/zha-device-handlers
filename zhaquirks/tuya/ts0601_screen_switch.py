"""Tuya TS0601 Zemismart screen switch quirks."""

from typing import Any

from zigpy.quirks.v2.homeassistant import EntityType
import zigpy.types as t
from zigpy.typing import UNDEFINED, UndefinedType
from zigpy.zcl import foundation

from zhaquirks.tuya import TuyaCommand, TuyaDatapointData
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster

SCREEN_SWITCH_SIGNATURES: tuple[tuple[str, int], ...] = (
    ("_TZE284_lnyz4a6v", 1),
    ("_TZE284_1tnysxwl", 1),
    ("_TZE284_dmckrsxg", 2),
    ("_TZE284_a2teqi5u", 2),
    ("_TZE28C1000000_a2teqi5u", 2),
    ("_TZE204_3ctwoaip", 2),
    ("_TZE284_e4pf6l87", 3),
    ("_TZE284_xvywzhmi", 3),
    ("_TZE284_y4jqpry8", 4),
    ("_TZE284_xibaabmu", 4),
    ("_TZE28C1000000_xibaabmu", 4),
)


class ScreenSwitchTuyaCluster(TuyaMCUCluster):
    """Tuya MCU cluster with string datapoint write support."""

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Defer attribute writes to Tuya set_data commands."""
        records = self._write_attr_records(attributes)

        for record in records:
            attr_name = self.attributes[record.attrid].name
            attr_value = record.value.value
            self.debug("write_attributes --> record: %s", record)

            for dp in self.get_dp_mapping(self.endpoint.endpoint_id, attr_name):
                value = attr_value

                if attr_to_dp_converter := self._attributes_to_dp_converters.get(dp):
                    value = attr_to_dp_converter(value)

                self.create_catching_task(
                    self.command(
                        self.mcu_write_command,
                        TuyaCommand(
                            status=0,
                            tsn=self.endpoint.device.application.get_sequence(),
                            datapoints=[TuyaDatapointData(dp, value)],
                        ),
                        expect_reply=False,
                        manufacturer=manufacturer,
                    )
                )

            self._update_attribute(record.attrid, attr_value)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]


def _screen_name(value: str) -> str:
    """Convert a screen name to the device-supported length."""
    return value[:12]


def _builder(manufacturer: str, gang_count: int) -> TuyaQuirkBuilder:
    """Build a screen switch quirk for a Zemismart TS0601 variant."""
    builder = TuyaQuirkBuilder(manufacturer, "TS0601")

    for gang in range(1, gang_count + 1):
        builder.tuya_switch(
            dp_id=gang,
            attribute_name=f"state_l{gang}",
            entity_type=EntityType.STANDARD,
            translation_key=f"state_l{gang}",
            fallback_name=f"Switch {gang}",
        )
        builder.tuya_dp_attribute(
            dp_id=104 + gang,
            attribute_name=f"name_l{gang}",
            type=t.CharacterString,
            access=foundation.ZCLAttributeAccess.Read
            | foundation.ZCLAttributeAccess.Write,
            dp_converter=_screen_name,
        )

    return builder.skip_configuration().tuya_enchantment(data_query_spell=True)


for _manufacturer, _gang_count in SCREEN_SWITCH_SIGNATURES:
    _builder(_manufacturer, _gang_count).add_to_registry(
        replacement_cluster=ScreenSwitchTuyaCluster
    )
