"""Tuya TS000x switches requiring proprietary relay separation commissioning."""

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


class TuyaRelaySeparationDevice(CustomZigpyDevice):
    """Tuya switch requiring a proprietary relay separation sequence."""

    async def apply_custom_configuration(self, *args, **kwargs):
        """Configure the device so each endpoint controls a separate relay."""

        # 1. Basic Read Attributes directed to APS endpoint 0xFF.
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

        # 3. Delay observed during Tuya commissioning.
        await asyncio.sleep(2.55)

        # 4. Send proprietary Basic cluster command 0xF0.
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

        await super().apply_custom_configuration(*args, **kwargs)


(
    QuirkBuilder("_TZ3000_c7xsiexw", "TS0002")
    .zigpy_device_class(TuyaRelaySeparationDevice)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=1)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=2)
    .replaces(TuyaZBE000Cluster, endpoint_id=1)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=1)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=2)
    .add_to_registry()
)


(
    QuirkBuilder("_TZ3000_iol4bl2y", "TS0003")
    .zigpy_device_class(TuyaRelaySeparationDevice)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=1)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=2)
    .replaces(TuyaZBOnOffAttributeCluster, endpoint_id=3)
    .replaces(TuyaZBE000Cluster, endpoint_id=1)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=1)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=2)
    .replaces(TuyaZBExternalSwitchTypeCluster, endpoint_id=3)
    .add_to_registry()
)
