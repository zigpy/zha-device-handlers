"""Tuya TS0002 switch manufactured by _TZ3000_c7xsiexw."""

import asyncio

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import Basic

from zhaquirks.builder import QuirkBuilder
from zhaquirks.device import CustomZigpyDevice
from zhaquirks.tuya import (
    TuyaZBE000Cluster,
    TuyaZBExternalSwitchTypeCluster,
    TuyaZBOnOffAttributeCluster,
)


class TS0002C7XSDevice(CustomZigpyDevice):
    """Tuya TS0002 requiring a proprietary relay separation sequence."""

    async def apply_custom_configuration(self, *args, **kwargs):
        """Configure the device so endpoints 1 and 2 control separate relays."""

        # Tuya gateway commissioning sequence observed with a Zigbee sniffer.
        #
        # 1. Basic Read Attributes directed to APS endpoint 0xFF.
        #
        # ZCL:
        #   Frame control: 0x10
        #   Command:       0x00 (Read Attributes)
        #
        # Attributes:
        #   0x0004 Manufacturer Name
        #   0x0000 ZCL Version
        #   0x0001 Application Version
        #   0x0005 Model Identifier
        #   0x0007 Power Source
        #   0xFFFE Tuya proprietary
        tsn = self.application.get_sequence()

        read_payload = bytes(
            [
                0x10,
                int(tsn),
                0x00,
                0x04,
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x05,
                0x00,
                0x07,
                0x00,
                0xFE,
                0xFF,
            ]
        )

        await self.request(
            profile=zha.PROFILE_ID,
            cluster=Basic.cluster_id,
            src_ep=1,
            dst_ep=0xFF,
            sequence=tsn,
            data=read_payload,
            expect_reply=False,
        )

        # 2. Write Basic attribute 0xFFDE = 0x0D.
        #
        # ZCL:
        #   Frame control: 0x00
        #   Command:       0x02 (Write Attributes)
        #   Attribute:     0xFFDE
        #   Data type:     0x20 (uint8)
        #   Value:         0x0D
        tsn = self.application.get_sequence()

        ffde_payload = bytes(
            [
                0x00,
                int(tsn),
                0x02,
                0xDE,
                0xFF,
                0x20,
                0x0D,
            ]
        )

        await self.request(
            profile=zha.PROFILE_ID,
            cluster=Basic.cluster_id,
            src_ep=1,
            dst_ep=1,
            sequence=tsn,
            data=ffde_payload,
            expect_reply=False,
        )

        # 3. The Tuya gateway waits approximately 2.55 seconds here.
        await asyncio.sleep(2.55)

        # 4. Send proprietary Basic cluster command 0xF0.
        #
        # ZCL:
        #   Frame control: 0x11
        #     - cluster specific
        #     - client -> server
        #     - disable default response
        #   Command: 0xF0
        tsn = self.application.get_sequence()

        f0_payload = bytes(
            [
                0x11,
                int(tsn),
                0xF0,
            ]
        )

        await self.request(
            profile=zha.PROFILE_ID,
            cluster=Basic.cluster_id,
            src_ep=1,
            dst_ep=1,
            sequence=tsn,
            data=f0_payload,
            expect_reply=False,
        )

        # Continue normal quirk/custom-cluster configuration.
        await super().apply_custom_configuration(*args, **kwargs)


(
    QuirkBuilder("_TZ3000_c7xsiexw", "TS0002")
    .zigpy_device_class(TS0002C7XSDevice)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=1)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=2)
    .replaces(TuyaZBE000Cluster, endpoint_id=1)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=1)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=2)
    .add_to_registry()
)
