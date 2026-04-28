"""Tuya TS0049 (_TZ3000_kz1anoi8) water valve with configurable irrigation timer.

Protocol notes (reverse-engineered):
  - On/Off:  Standard ZCL OnOff cluster (0x0006), DP 1 reported via 0xEF00
  - Timer:   Cluster 0xE001 (TUYA_CLUSTER_E001_ID), Command 0xFE
             Payload: [DP=11, val_b3, val_b2, val_b1, val_b0]  (5 bytes, Big-Endian)
             Valid range: 0 – 86400 seconds (0 = kein Auto-Aus)
             Persistent: the device stores the value until changed.

Tuya DP mapping:
  DP  1: On/Off (Boolean)
  DP 11: Irrigation time in seconds (uint32, Big-Endian via 0xE001/0xFE)
"""

from __future__ import annotations

from typing import Optional

import zigpy.types as t

from zhaquirks.tuya import TUYA_CLUSTER_E001_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster


class TuyaWaterValveCluster(TuyaMCUCluster):
    """Tuya Water Valve MCU Cluster for _TZ3000_kz1anoi8.

    0xEF0B (irrigation_time):     Eingabe in Minuten, sendet Minuten * 60 Sekunden
    0xEF0C (irrigation_time_sec): Eingabe in Sekunden, sendet direkt
    """

    async def write_attributes(
        self,
        attributes: dict,
        allow_cache: bool = False,
        only_cache: bool = False,
        manufacturer: Optional[int] = None,
    ):
        """Write attributes, routing irrigation timer writes to Cluster 0xE001 / Command 0xFE."""
        e001_attrs = {}
        other_attrs = {}

        for attr, value in attributes.items():
            attr_id = (
                self.attributes_by_name[attr].id if isinstance(attr, str) else attr
            )
            if attr_id in (0xEF0B, 0xEF0C):
                e001_attrs[attr] = value
            else:
                other_attrs[attr] = value

        results = [{}, {}]

        for attr, value in e001_attrs.items():
            attr_id = (
                self.attributes_by_name[attr].id if isinstance(attr, str) else attr
            )
            if attr_id == 0xEF0B:
                # Minuten-Feld: Umrechnung in Sekunden
                minutes = max(0, min(1440, int(value)))
                sec = minutes * 60
                stored_attr = "irrigation_time"
                stored_val = minutes
            else:
                # Sekunden-Feld: direkt senden
                sec = max(0, min(86400, int(value)))
                stored_attr = "irrigation_time_sec"
                stored_val = sec

            payload = bytes(
                [
                    11,
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
            self._update_attribute(self.attributes_by_name[stored_attr].id, stored_val)
            # Gegenseitige Aktualisierung
            if attr_id == 0xEF0B:
                self._update_attribute(
                    self.attributes_by_name["irrigation_time_sec"].id, sec
                )
            else:
                self._update_attribute(
                    self.attributes_by_name["irrigation_time"].id, sec // 60
                )

        if other_attrs:
            results = await super().write_attributes(
                other_attrs,
                allow_cache=allow_cache,
                only_cache=only_cache,
                manufacturer=manufacturer,
            )

        return results


(
    TuyaQuirkBuilder("_TZ3000_kz1anoi8", "TS0049")
    .tuya_number(
        dp_id=11,
        type=t.uint32_t,
        attribute_name="irrigation_time",
        min_value=0,
        max_value=1440,
        step=1,
        unit="min",
        translation_key="irrigation_time",
        fallback_name="Bewässerungszeit",
    )
    .tuya_number(
        dp_id=12,
        type=t.uint32_t,
        attribute_name="irrigation_time_sec",
        min_value=0,
        max_value=86400,
        step=1,
        unit="s",
        translation_key="irrigation_time_sec",
        fallback_name="Bewässerungszeit (Sek.)",
    )
    .add_to_registry(replacement_cluster=TuyaWaterValveCluster)
)
