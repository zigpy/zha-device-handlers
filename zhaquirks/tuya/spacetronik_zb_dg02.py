"""Spacetronik ZB-DG02 methane gas detector."""

from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import BinarySensorDeviceClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE204_uc0iv1hb", "TS0601")
    .tuya_gas(dp_id=1)
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=IasZone.cluster_id,
        new_device_class=BinarySensorDeviceClass.GAS,
    )
    .tuya_enchantment(
        read_attr_spell=True,
        data_query_spell=True,
    )
    .add_to_registry()
)
