"""Spacetronik ZB-DG02 methane gas detector."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder


(
    TuyaQuirkBuilder("_TZE204_uc0iv1hb", "TS0601")
    .tuya_gas(dp_id=1)
    .tuya_enchantment(
        read_attr_spell=True,
        data_query_spell=True,
    )
    .add_to_registry()
)
