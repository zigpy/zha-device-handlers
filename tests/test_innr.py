"""Tests for Innr quirks."""

from unittest import mock

import pytest
from zigpy.profiles import zll
import zigpy.types as t
from zigpy.zcl import (
    AttributeReportedEvent,
    AttributeUpdatedEvent,
    ClusterType,
    ReportingConfig,
)
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ConfigureReportingResponseRecord, Status

import zhaquirks
from zhaquirks.innr import MeteringClusterInnrNew, MeteringClusterInnrOld
from zhaquirks.innr.innr_sp120_plug import SP120
from zhaquirks.innr.innr_sp240_plug import (
    ElectricalMeasurementClusterSP240,
    InnrCluster,
)

zhaquirks.setup()

# firmware version that fixed the metering divisor bug (max_version is exclusive)
SP240_DIVISOR_FIX_FW_VERSION = 0x191B3685

# the SP 242 (UK) uses the SP 240 quirk
SP240_MODELS = ["SP 240", "SP 242"]


@pytest.mark.parametrize("model", SP240_MODELS)
@pytest.mark.parametrize(
    "firmware_version",
    [SP240_DIVISOR_FIX_FW_VERSION - 1, SP240_DIVISOR_FIX_FW_VERSION],
)
def test_innr_sp240_cluster_order(zigpy_device_from_v2_quirk, firmware_version, model):
    """Test the SP 240 quirk keeps the device's cluster order.

    ZHA configures reporting in this order, and the plug only has a few
    reporting slots: Metering must stay ahead of Electrical Measurement.
    LevelControl is removed by the quirk, so it is absent from the result.
    """
    raw_cluster_ids = [
        Basic.cluster_id,
        Identify.cluster_id,
        Groups.cluster_id,
        Scenes.cluster_id,
        OnOff.cluster_id,
        LevelControl.cluster_id,
        Metering.cluster_id,
        ElectricalMeasurement.cluster_id,
        LightLink.cluster_id,
        InnrCluster.cluster_id,
    ]
    device = zigpy_device_from_v2_quirk(
        "innr",
        model,
        cluster_ids={1: dict.fromkeys(raw_cluster_ids, ClusterType.Server)},
        firmware_version=firmware_version,
    )

    # LevelControl is removed (the plug cannot dim), everything else keeps its order
    assert list(device.endpoints[1].in_clusters) == [
        cluster_id
        for cluster_id in raw_cluster_ids
        if cluster_id != LevelControl.cluster_id
    ]
    assert isinstance(
        device.endpoints[1].in_clusters[Metering.cluster_id],
        MeteringClusterInnrOld | MeteringClusterInnrNew,
    )
    assert isinstance(
        device.endpoints[1].in_clusters[InnrCluster.cluster_id], InnrCluster
    )


@pytest.mark.parametrize(
    ("firmware_version", "expected_cluster", "expected_divisor"),
    [
        # firmware before the fix uses the old override (divisor 100)
        (
            SP240_DIVISOR_FIX_FW_VERSION - 1,
            MeteringClusterInnrOld,
            100,
        ),
        # the fixed firmware and newer use the new override (divisor 1000)
        (
            SP240_DIVISOR_FIX_FW_VERSION,
            MeteringClusterInnrNew,
            1000,
        ),
        (
            SP240_DIVISOR_FIX_FW_VERSION + 1,
            MeteringClusterInnrNew,
            1000,
        ),
        # a device that does not report a firmware version is treated as new
        # (the new quirk has allow_missing=True, the old one allow_missing=False)
        (
            None,
            MeteringClusterInnrNew,
            1000,
        ),
    ],
)
@pytest.mark.parametrize("model", SP240_MODELS)
def test_innr_sp240_firmware_version_metering(
    zigpy_device_from_v2_quirk,
    firmware_version,
    expected_cluster,
    expected_divisor,
    model,
):
    """Test the correct Innr SP 240 quirk is selected based on firmware version."""
    device = zigpy_device_from_v2_quirk(
        "innr",
        model,
        cluster_ids={
            1: {
                LevelControl.cluster_id: ClusterType.Server,
                Metering.cluster_id: ClusterType.Server,
                ElectricalMeasurement.cluster_id: ClusterType.Server,
            }
        },
        firmware_version=firmware_version,
    )

    # both variants drop LevelControl and skip reporting the EM scaling constants
    assert LevelControl.cluster_id not in device.endpoints[1].in_clusters
    assert isinstance(
        device.endpoints[1].electrical_measurement, ElectricalMeasurementClusterSP240
    )

    metering_cluster = device.endpoints[1].smartenergy_metering
    assert isinstance(metering_cluster, expected_cluster)

    # the constant divisor override is applied regardless of what the device reports
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == expected_divisor


@pytest.mark.parametrize("model", SP240_MODELS)
async def test_innr_sp240_skips_em_scaling_constant_reporting(
    zigpy_device_from_v2_quirk, model
):
    """The SP 240 does not configure reporting for the EM scaling constants."""
    device = zigpy_device_from_v2_quirk(
        "innr",
        model,
        cluster_ids={1: {ElectricalMeasurement.cluster_id: ClusterType.Server}},
    )
    em_cluster = device.endpoints[1].electrical_measurement
    attrs = ElectricalMeasurement.AttributeDefs
    reporting = ReportingConfig(min_interval=0, max_interval=900, reportable_change=1)

    with mock.patch.object(
        em_cluster,
        "_configure_reporting",
        mock.AsyncMock(
            return_value=[
                [
                    ConfigureReportingResponseRecord(
                        status=Status.INSUFFICIENT_SPACE,
                        direction=0,
                        attrid=attrs.rms_voltage.id,
                    )
                ]
            ]
        ),
    ) as configure_reporting:
        result = await em_cluster.configure_reporting_multiple(
            {
                attrs.ac_power_multiplier: reporting,
                attrs.ac_power_divisor: reporting,
                attrs.active_power: reporting,
                attrs.ac_current_multiplier: reporting,
                attrs.ac_current_divisor: reporting,
                attrs.rms_current: reporting,
                attrs.ac_voltage_multiplier: reporting,
                attrs.ac_voltage_divisor: reporting,
                attrs.rms_voltage: reporting,
            }
        )

    # only the measurements are sent to the device
    assert configure_reporting.await_count == 1
    sent_records = configure_reporting.await_args.args[0]
    assert [record.attrid for record in sent_records] == [
        attrs.active_power.id,
        attrs.rms_current.id,
        attrs.rms_voltage.id,
    ]

    # the scaling constants are answered locally, the device's statuses pass through
    assert result == {
        attrs.ac_power_multiplier: Status.UNREPORTABLE_ATTRIBUTE,
        attrs.ac_power_divisor: Status.UNREPORTABLE_ATTRIBUTE,
        attrs.active_power: Status.SUCCESS,
        attrs.ac_current_multiplier: Status.UNREPORTABLE_ATTRIBUTE,
        attrs.ac_current_divisor: Status.UNREPORTABLE_ATTRIBUTE,
        attrs.rms_current: Status.SUCCESS,
        attrs.ac_voltage_multiplier: Status.UNREPORTABLE_ATTRIBUTE,
        attrs.ac_voltage_divisor: Status.UNREPORTABLE_ATTRIBUTE,
        attrs.rms_voltage: Status.INSUFFICIENT_SPACE,
    }

    # a request for only scaling constants sends nothing to the device
    with mock.patch.object(
        em_cluster, "_configure_reporting", mock.AsyncMock()
    ) as configure_reporting:
        result = await em_cluster.configure_reporting_multiple(
            {attrs.ac_power_divisor: reporting}
        )

    configure_reporting.assert_not_awaited()
    assert result == {attrs.ac_power_divisor: Status.UNREPORTABLE_ATTRIBUTE}


# Real SP 120 device-initiated metering report:
#   fc=0x1c   -> manufacturer-specific, server-to-client, disable-default-response
#   manuf=0x1166 (Innr), TSN=0x16, cmd=0x0a (Report_Attributes)
#   attr 0x0430 (Innr manufacturer-specific, uint64) = 0
#   attr 0x0000 (current_summ_delivered, uint48)     = 35
SP120_MANUF_SUMMATION_REPORT = (
    b"\x1c\x66\x11\x16\x0a"
    b"\x30\x04\x27\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x25\x23\x00\x00\x00\x00\x00"
)


async def test_sp120_manufacturer_framed_summation(zigpy_device_from_quirk):
    """The manufacturer-framed summation report updates current_summ_delivered."""
    device = zigpy_device_from_quirk(SP120)
    metering_cluster = device.endpoints[1].smartenergy_metering

    events = []
    metering_cluster.on_event(AttributeReportedEvent.event_type, events.append)
    metering_cluster.on_event(AttributeUpdatedEvent.event_type, events.append)

    device.packet_received(
        t.ZigbeePacket(
            profile_id=zll.PROFILE_ID,
            cluster_id=Metering.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(SP120_MANUF_SUMMATION_REPORT),
        )
    )

    # Must resolve to the named standard attribute (None without the quirk).
    summation_events = [
        e
        for e in events
        if e.attribute_name == Metering.AttributeDefs.current_summ_delivered.name
    ]
    assert len(summation_events) == 1
    assert summation_events[0].value == 35

    # ...and cached as the standard attribute the energy sensor reads.
    assert metering_cluster.get(Metering.AttributeDefs.current_summ_delivered) == 35


async def test_sp120_plain_summation_still_parses(zigpy_device_from_quirk):
    """A normal (non-manufacturer) summation report is unaffected by the override."""
    device = zigpy_device_from_quirk(SP120)
    metering_cluster = device.endpoints[1].smartenergy_metering

    events = []
    metering_cluster.on_event(AttributeReportedEvent.event_type, events.append)
    metering_cluster.on_event(AttributeUpdatedEvent.event_type, events.append)

    # fc=0x18 (no manufacturer bit), TSN=0x01, cmd=0x0a,
    # attr 0x0000 (current_summ_delivered, uint48) = 1234
    device.packet_received(
        t.ZigbeePacket(
            profile_id=zll.PROFILE_ID,
            cluster_id=Metering.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(
                b"\x18\x01\x0a\x00\x00\x25\xd2\x04\x00\x00\x00\x00"
            ),
        )
    )

    summation_events = [
        e
        for e in events
        if e.attribute_name == Metering.AttributeDefs.current_summ_delivered.name
    ]
    assert len(summation_events) == 1
    assert summation_events[0].value == 1234
    assert metering_cluster.get(Metering.AttributeDefs.current_summ_delivered) == 1234
