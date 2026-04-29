"""Tuya TS0049 (_TZ3000_kz1anoi8) battery-powered water valve.

Protocol notes (reverse-engineered):
  - On/Off:  Standard ZCL OnOff cluster (0x0006)
  - Timer:   Cluster 0xE001, Command 0xFE
             Payload: [DP=11, val_b3, val_b2, val_b1, val_b0]  (5 bytes, Big-Endian)
             Valid range: 0 - 86400 seconds (0 = no auto-off, valve stays open)
             Persistent: the device stores the value until changed.

Tuya DP mapping:
  DP  1: On/Off (Boolean)
  DP 11: Irrigation time in seconds (uint32, Big-Endian via 0xE001/0xFE)
"""

from __future__ import annotations

from typing import Any

from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import UNDEFINED, UndefinedType

from zhaquirks.tuya import TUYA_CLUSTER_E001_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster


class TuyaWaterValveCluster(TuyaMCUCluster):
    """Tuya Water Valve MCU Cluster for _TZ3000_kz1anoi8.

    Intercepts writes to ``irrigation_time`` (attr 0xEF0B) and sends them via
    Cluster 0xE001 / Command 0xFE with Big-Endian 4-byte encoding - the only
    protocol this device accepts for DP 11.
    Value 0 disables the auto-off timer (valve stays open indefinitely).
    """

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        manufacturer: int | UndefinedType | None = UNDEFINED,
        **kwargs: Any,
    ):
        """Write attributes, routing irrigation timer writes to Cluster 0xE001 / Command 0xFE."""
        e001_attrs = {}
        other_attrs = {}

        for attr, value in attributes.items():
            if isinstance(attr, str):
                attr_id = self.attributes_by_name[attr].id
            elif isinstance(attr, foundation.ZCLAttributeDef):
                attr_id = attr.id
            else:
                attr_id = attr
            if attr_id == 0xEF0B:
                e001_attrs[attr] = value
            else:
                other_attrs[attr] = value

        results = [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

        for attr, value in e001_attrs.items():
            sec = max(0, min(86400, int(value)))
            payload = bytes(
                [
                    11,  # DP 11 = irrigation time
                    (sec >> 24) & 0xFF,
                    (sec >> 16) & 0xFF,
                    (sec >> 8) & 0xFF,
                    sec & 0xFF,
                ]
            )
            tsn = self.endpoint.device.application.get_sequence()
            zcl_frame = bytes([0x11, tsn, 0xFE]) + payload
            await self.endpoint.device.request(
                profile=self.endpoint.profile_id,
                cluster=TUYA_CLUSTER_E001_ID,
                src_ep=self.endpoint.endpoint_id,
                dst_ep=self.endpoint.endpoint_id,
                sequence=tsn,
                data=zcl_frame,
                expect_reply=False,
            )
            self._update_attribute(self.attributes_by_name["irrigation_time"].id, sec)

        if other_attrs:
            results = await super().write_attributes(
                other_attrs,
                manufacturer=manufacturer,
                **kwargs,
            )

        return results


(
    TuyaQuirkBuilder("_TZ3000_kz1anoi8", "TS0049")
    .tuya_number(
        dp_id=11,
        type=t.uint32_t,
        attribute_name="irrigation_time",
        min_value=0,
        max_value=86400,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="irrigation_time",
        fallback_name="Irrigation Time",
    )
    .add_to_registry(replacement_cluster=TuyaWaterValveCluster)
)
