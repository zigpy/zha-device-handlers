"""Device handler for loratap TS130F smart curtain switch."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaZBExternalSwitchTypeCluster

ATTR_CURRENT_POSITION_LIFT_PERCENTAGE = 0x0008
CMD_GO_TO_LIFT_PERCENTAGE = 0x0005


class TuyaWithBacklightOnOffCluster(CustomCluster):
    """TuyaSmartCurtainOnOffCluster: fire events corresponding to press type."""

    cluster_id = OnOff.cluster_id

    LIGHT_MODE_1 = {0x8001: 0}
    LIGHT_MODE_2 = {0x8001: 1}
    LIGHT_MODE_3 = {0x8001: 2}

    attributes = {0x8001: ("backlight_mode", t.enum8)}


class TuyaCoveringCluster(CustomCluster, WindowCovering):
    """TuyaSmartCurtainWindowCoveringCluster: Allow to setup Window covering tuya devices."""

    attributes = WindowCovering.attributes.copy()
    attributes.update({0xF000: ("tuya_moving_state", t.enum8)})
    attributes.update({0xF001: ("calibration", t.enum8)})
    attributes.update({0xF002: ("motor_reversal", t.enum8)})
    attributes.update({0xF003: ("calibration_time", t.uint16_t)})

    def _update_attribute(self, attrid, value):
        if attrid == ATTR_CURRENT_POSITION_LIFT_PERCENTAGE:
            # Invert the percentage value (cf https://github.com/dresden-elektronik/deconz-rest-plugin/issues/3757)
            value = 100 - value
        super()._update_attribute(attrid, value)

    async def command(
        self, command_id, *args, manufacturer=None, expect_reply=True, tsn=None
    ):
        """Override default command to invert percent lift value."""
        if command_id == CMD_GO_TO_LIFT_PERCENTAGE:
            percent = args[0]
            # Invert the percentage value (cf https://github.com/dresden-elektronik/deconz-rest-plugin/issues/3757)
            percent = 100 - percent
            v = (percent,)
            return await super().command(command_id, *v)
        return await super().command(
            command_id,
            *args,
            manufacturer=manufacturer,
            expect_reply=expect_reply,
            tsn=tsn
        )


class TuyaTS130FTI(CustomDevice):
    """Tuya smart curtain roller shutter Time In."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0202, device_version=1, input_clusters=[0, 4, 5, 6, 10, 0x0102], output_clusters=[25]))
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    Time.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
        },
    }


class TuyaZemismartTS130F(CustomDevice):
    """Tuya ZemiSmart smart curtain roller shutter."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0202, device_version=1, input_clusters=[0x0000, 0x0004, 0x0005, 0x0006, 0x0102], output_clusters=[0x000a, 0x0019]))
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }


class TuyaTS130FTI2(CustomDevice):
    """Tuya smart curtain roller shutter Time In."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0203, device_version=1, input_clusters=[0x0000, 0x0004, 0x0005, 0x0006, 0x0102], output_clusters=[0x000a, 0x0019]))
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }


class TuyaTS130FTO(CustomDevice):
    """Tuya smart curtain roller shutter Time Out."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0202, device_version=1, input_clusters=[0, 4, 5, 6, 10, 0x0102], output_clusters=[25]))
        # This singnature is not correct is one copy of the first one and the cluster is not inline with the device.
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }


class TuyaTS130GP(CustomDevice):
    """Tuya ZemiSmart smart curtain roller shutter with Green Power."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0202, device_version=1, input_clusters=[0, 4, 5, 6, 0x0102], output_clusters=[0x000a, 0x0019]))
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class TuyaTS130Double_GP(CustomDevice):
    """Tuya double smart curtain roller shutter with Green Power."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0202, device_version=1, input_clusters=[0, 4, 5, 6, 0x0102], output_clusters=[0x000a, 0x0019]))
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                # "profile_id": 260, "device_type": "0x0202",
                # "in_clusters": ["0x0004","0x0005","0x0006","0x0102"],
                # "out_clusters": []
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class TuyaTS130ESTC(CustomDevice):
    """Tuya ZigBee Curtain Switch Module with External Switch Type Cluster."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=0x0202, device_version=1, input_clusters=[0x0000, 0x0004, 0x0005, 0x0006, 0x0102, 0xE001], output_clusters=[0x000a, 0x0019]))
        MODEL: "TS130F",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_DEVICE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    WindowCovering.cluster_id,
                    TuyaZBExternalSwitchTypeCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.WINDOW_COVERING_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaWithBacklightOnOffCluster,
                    TuyaCoveringCluster,
                    TuyaZBExternalSwitchTypeCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
