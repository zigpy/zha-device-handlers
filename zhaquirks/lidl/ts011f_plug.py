"""LIDL TS011F plug."""
from __future__ import annotations

import asyncio
import logging

import zigpy
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
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
from zhaquirks.tuya.ts011f_plug import Plug_3AC_4USB

_LOGGER = logging.getLogger(__name__)


async def cast_tuya_magic_spell_task(
    dev: zigpy.device.Device, tries: int = 100, rejoin: bool = False
) -> None:
    """Initialize device so that all endpoints become available."""
    import inspect

    basic_cluster = dev.endpoints[1].in_clusters[0]

    # The magic spell is needed only once.
    # TODO: Improve by doing this only once (successfully).

    # Magic spell - part 1
    # Note: attribute order is important
    attr_to_read = [
        "manufacturer",
        "zcl_version",
        "app_version",
        "model",
        "power_source",
        0xFFFE,
    ]
    if "tries" in inspect.getfullargspec(basic_cluster.read_attributes)[0]:
        _LOGGER.debug(f"Cast Tuya Magic Spell on {dev.ieee!r} with {tries} tries")
        res = await basic_cluster.read_attributes(attr_to_read, tries=tries)
    else:
        _LOGGER.debug(f"Cast Tuya Magic Spell on {dev.ieee!r}")
        res = await basic_cluster.read_attributes(attr_to_read)

    _LOGGER.debug(f"Tuya Magic Spell result {res!r} for {dev.ieee!r}")

    # Magic spell - part 2 (skipped - does not seem to be needed)
    # attr_to_write={0xffde:13}
    # basic_cluster.write_attributes(attr_to_write)

    if rejoin:
        # Leave with rejoin - may need to be adjuste to work everywhere
        # or require a minimum zigpy version
        # This should have the device leave and rejoin immediately triggering
        # the discovery of the endpoints that appear after the magic trick

        # Note: this is not validated yet and disabled by default
        _LOGGER.debug(f"Send leave with rejoin request to {dev.ieee!r}")
        res = await dev.zdo.request(0x0034, dev.ieee, 0x01, tries)
        _LOGGER.debug(f"Leave with rejoin result {res!r} for {dev.ieee!r}")

        app = dev.application
        # Delete the device from the database
        app.listener_event("device_removed", dev)

        # Delete the device from zigpy
        app.devices.pop(dev.ieee, None)


def cast_tuya_magic_spell(dev: zigpy.device.Device, tries: int = 3) -> None:
    """Set up the magic spell asynchronously."""

    # Note for sleepy devices the number of tries may need to be increased to 100.

    dev._magic_spell_task = asyncio.create_task(
        cast_tuya_magic_spell_task(dev, tries=tries)
    )


class TuyaBasicCluster(CustomCluster, Basic):
    """Provide Tuya Basic Cluster with magic spell."""

    attributes = Basic.attributes.copy()
    attributes.update(
        {
            0xFFDE: ("tuya_FFDE", t.uint8_t, True),
            # 0xffe0: ("tuya_FFE0", TODO.Array, True),
            # 0xffe1: ("tuya_FFE1", TODO.Array, True),
            0xFFE2: ("tuya_FFE2", t.uint8_t, True),
            # 0xffe3: ("tuya_FFE3", TODO.Array, True),
        }
    )

    async def bind(self):
        """Bind cluster."""

        _LOGGER.debug(
            f"Requesting Tuya Magic Spell for {self.ieee!r} in basic bind method"
        )
        tries = 3
        await asyncio.create_task(cast_tuya_magic_spell_task(self, tries=tries))

        return await super().bind()


class Lidl_Plug_3AC_4USB(Plug_3AC_4USB):
    """LIDL 3 outlets + 4 USB with restore power state support."""

    def __init__(self, *args, **kwargs):
        """Initialize with task."""
        super().__init__(*args, **kwargs)

        # Use 'external' version that could be called from cluster
        # customiation
        cast_tuya_magic_spell(self, tries=3)

    signature = {
        MODEL: "TS011F",
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=266
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=1
            # input_clusters=[]
            # output_clusters=[33]>
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    # Uncomment to try TuyaBasicCluster implementation
    # Rename __init__ to disabled__init__ as well
    # replacement[1][INPUT_CLUSTERS][0] = TuyaBasicCluster
