"""GLEDOPTO GL-C-007 2ID device.."""
import logging
from typing import Optional, Union

import zigpy.zcl.foundation as foundation
from zigpy import types as t
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.profiles import zll, zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.gledopto import GLEDOPTO


_LOGGER = logging.getLogger(__name__)


class BasicCluster(Basic, CustomCluster):
    """GLEDOPTO GL-C-007 2ID basic cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            Basic.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class OnOffCluster(OnOff, CustomCluster):
    """GLEDOPTO GL-C-007 2ID on/off cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            OnOff.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class IdentifyCluster(Identify, CustomCluster):
    """GLEDOPTO GL-C-007 2ID identify cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            Identify.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class GroupsCluster(Groups, CustomCluster):
    """GLEDOPTO GL-C-007 2ID groups cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            Groups.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class ScenesCluster(Scenes, CustomCluster):
    """GLEDOPTO GL-C-007 2ID scenes cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            Scenes.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class LevelControlCluster(LevelControl, CustomCluster):
    """GLEDOPTO GL-C-007 2ID level control cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            LevelControl.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class ColorCluster(Color, CustomCluster):
    """GLEDOPTO GL-C-007 2ID color cluster."""

    def command(
        self,
        command_id: Union[foundation.Command, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None
    ):
        """Command handler."""
        src_ep = 1
        dst_ep = self.endpoint.endpoint_id
        device = self.endpoint.device
        if tsn is None:
            tsn = self._endpoint.device.application.get_sequence()
        return device.request(
            # device,
            zha.PROFILE_ID,
            Color.cluster_id,
            src_ep,
            dst_ep,
            tsn,
            bytes([src_ep, tsn, command_id]),
            expect_reply=expect_reply,
        )


class Glc007id2(CustomDevice):
    """GLEDOPTO GL-C-007 2ID device."""

    signature = {
        # <SimpleDescriptor endpoint=15 profile=49246 device_type=0x220
        # device_version=2 input_clusters=[0, 3, 4, 5, 6, 8, 0x300=768]
        # output_clusters=[]>
        MODELS_INFO: [(GLEDOPTO, "GL-C-007")],
        ENDPOINTS: {
            15: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=11 profile=49246 device_type=0x0210
            # device_version=2
            # input_clusters=[0, 3, 4, 5, 6, 8, 0x300 = 768]
            # output_clusters=[]>
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=13 profile=49246 device_type= 0xe15e = 57694
            # device_version=2
            # input_clusters=[0x1000 = 4096]
            # output_clusters=[0x1000 = 4096]>
            13: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 57694,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            15: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    IdentifyCluster,
                    GroupsCluster,
                    ScenesCluster,
                    OnOffCluster,
                    LevelControlCluster,
                    ColorCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=11 profile=49246 device_type=0x0210
            # device_version=2
            # input_clusters=[0, 3, 4, 5, 6, 8, 0x300 = 768]
            # output_clusters=[]>
            11: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: zll.DeviceType.EXTENDED_COLOR_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=13 profile=49246 device_type= 0xe15e = 57694
            # device_version=2
            # input_clusters=[0x1000 = 4096]
            # output_clusters=[0x1000 = 4096]>
            13: {
                PROFILE_ID: zll.PROFILE_ID,
                DEVICE_TYPE: 57694,
                INPUT_CLUSTERS: [LightLink.cluster_id],
                OUTPUT_CLUSTERS: [LightLink.cluster_id],
            },
        }
    }
