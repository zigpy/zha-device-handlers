"""AduroSmart multi contact sensor devices."""

import logging
import math
from typing import Any, Final, Optional, Union

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
import zigpy.types as t
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    BaseCommandDefs,
    ZCLAttributeDef,
    ZCLCommandDef,
    ZCLHeader,
)

_LOGGER = logging.getLogger(__name__)

ADUROLIGHT_ACCEL_CLUSTER_ID = 0xFCC1
ADUROLIGHT_ACCEL_COMMAND_REPORT_DATA = 0x0A


# Adurolight accel cluster implementation
class AduroSmartAccelCluster(CustomCluster):
    """AduroSmart multi contact sensor private cluster."""

    cluster_id = ADUROLIGHT_ACCEL_CLUSTER_ID
    name = "Adurolight Accel Cluster"
    ep_attribute = "adurolight_accel_cluster"

    class AttributeDefs(BaseAttributeDefs):
        """Define the attributes of a private cluster."""

        x_axis: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        y_axis: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )
        z_axis: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.int16s,
            access="rw",
            is_manufacturer_specific=True,
        )

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        button_event = ZCLCommandDef(
            id=ADUROLIGHT_ACCEL_COMMAND_REPORT_DATA,
            schema={
                "x_axis_id": t.uint16_t,
                "x_axis_type": t.uint8_t,
                "x_axis_value": t.int16s,
                "y_axis_id": t.uint16_t,
                "y_axis_type": t.uint8_t,
                "y_axis_value": t.int16s,
                "z_axis_id": t.uint16_t,
                "z_axis_type": t.uint8_t,
                "z_axis_value": t.int16s,
            },
            is_manufacturer_specific=True,
        )

    def get_accel_value(self, attrid, value):
        """Check for a valid accel value."""
        shifted_val = value >> 2
        result_float = (shifted_val * 977 / 1000) + 1
        value = math.floor(result_float)
        super()._update_attribute(attrid, value)

    def handle_cluster_request(
        self,
        hdr: ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        if hdr.command_id == ADUROLIGHT_ACCEL_COMMAND_REPORT_DATA:
            if len(args) == 9:
                attrid_1 = args[0]
                value_1 = args[2]
                attrid_2 = args[3]
                value_2 = args[5]
                attrid_3 = args[6]
                value_3 = args[8]
                if attrid_1 == 0x0000:
                    self.get_accel_value(attrid_1, value_1)
                if attrid_2 == 0x0001:
                    self.get_accel_value(attrid_2, value_2)
                if attrid_3 == 0x0002:
                    self.get_accel_value(attrid_3, value_3)
        else:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)


(
    QuirkBuilder("AduroSmart ERIA", "CSW_81909")
    .replaces(AduroSmartAccelCluster)
    .sensor(
        AduroSmartAccelCluster.AttributeDefs.x_axis.name,
        AduroSmartAccelCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ACCELERATION,
        translation_key="x_axis",
        fallback_name="X-Axis",
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=65535,
            reportable_change=0,
        ),
    )
    .sensor(
        AduroSmartAccelCluster.AttributeDefs.y_axis.name,
        AduroSmartAccelCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ACCELERATION,
        translation_key="y_axis",
        fallback_name="Y-Axis",
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=65535,
            reportable_change=0,
        ),
    )
    .sensor(
        AduroSmartAccelCluster.AttributeDefs.z_axis.name,
        AduroSmartAccelCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.ACCELERATION,
        translation_key="z_axis",
        fallback_name="Z-Axis",
        reporting_config=ReportingConfig(
            min_interval=1,
            max_interval=65535,
            reportable_change=0,
        ),
    )
    .add_to_registry()
)
