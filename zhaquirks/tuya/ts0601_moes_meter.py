"""MOES ZM6LT1 single-phase energy meter with a CT clamp.

The meter does not send ordinary Tuya 0xEF00 reports. It packs its datapoints into a
segmented transfer on the Zosung cluster 0xED00, which the coordinator has to pull
part by part, like a learned IR code. The protocol follows the ZM6LT1 converter of
zigbee-herdsman-converters (src/devices/moes.ts).
"""

from typing import Any, Final, NamedTuple

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    PERCENTAGE,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster
from zhaquirks.tuya.ts1201 import ZosungIRTransmit, ir_msg_part_crc

# Longest part the coordinator asks for, as for IR codes.
SEGMENT_PART_LENGTH: Final = 0x38
# Longest report accepted; real reports are well under 100 bytes.
SEGMENT_MAX_LENGTH: Final = 4096
# Transfers kept open at once; older unfinished ones are dropped.
SEGMENT_MAX_TRANSFERS: Final = 4
# The meter announces its reports as Tuya cluster command 0x02 (data report).
SEGMENT_TUYA_REPORT_CMD: Final = 0x02

# DP17 holds the alarm settings as 4-byte records: [id][enabled][value u16 BE].
ALARM_RECORD_LENGTH: Final = 4
ALARM_OVER_CURRENT_ID: Final = 0x01
OVER_CURRENT_MIN: Final = 1
OVER_CURRENT_MAX: Final = 120


class PhaseData(NamedTuple):
    """Measurements of DP6."""

    voltage: int  # 0.1 V
    current: int  # mA
    power: int  # W
    power_factor: int | None  # %


def decode_phase(raw: Any) -> PhaseData | None:
    """Decode DP6, or return None for a frame too short to hold the measurements.

    Layout: 2 header bytes, voltage u16, current u24, active power u24, reactive
    power u24, apparent power u24, power factor u8 and a flags byte, all big endian.
    Flag bit 0 makes the current negative, bit 1 the active power.
    """
    data = bytes(raw)
    if len(data) < 10:
        return None
    current = int.from_bytes(data[4:7], "big")
    power = int.from_bytes(data[7:10], "big")
    flags = data[17] if len(data) > 17 else 0
    if flags & 0x01:
        current = -current
    if flags & 0x02:
        power = -power
    return PhaseData(
        voltage=int.from_bytes(data[2:4], "big"),
        current=current,
        power=power,
        power_factor=data[16] if len(data) > 16 else None,
    )


def _phase_value(field: str):
    """Return a converter that picks one measurement out of DP6."""

    def convert(raw: Any) -> int | None:
        phase = decode_phase(raw)
        return None if phase is None else getattr(phase, field)

    return convert


def _alarm_records_valid(data: bytes) -> bool:
    """Return whether DP17 consists of whole alarm records."""
    return bool(data) and len(data) % ALARM_RECORD_LENGTH == 0


def decode_alarm_settings(raw: Any) -> bytes | None:
    """Return DP17 as reported, kept so a threshold change can send it back whole."""
    data = bytes(raw)
    return t.LVBytes(data) if _alarm_records_valid(data) else None


def decode_over_current_threshold(raw: Any) -> int | None:
    """Return the over-current alarm threshold (A) from DP17."""
    data = bytes(raw)
    if not _alarm_records_valid(data):
        return None
    for offset in range(0, len(data), ALARM_RECORD_LENGTH):
        if data[offset] == ALARM_OVER_CURRENT_ID:
            return int.from_bytes(data[offset + 2 : offset + 4], "big")
    return None


def encode_over_current_threshold(alarm_settings: Any, over_current: Any) -> bytes:
    """Return DP17 as last reported, with a new over-current alarm threshold.

    The meter only accepts DP17 as a whole, so the other alarm records are sent back
    unchanged. Before the meter has reported DP17 there is nothing to send back.
    """
    data = bytearray(bytes(alarm_settings or b""))
    if not _alarm_records_valid(data):
        raise ValueError("Alarm settings not reported by the meter yet")
    value = int(over_current)
    if not OVER_CURRENT_MIN <= value <= OVER_CURRENT_MAX:
        raise ValueError(
            f"Over-current threshold must be {OVER_CURRENT_MIN}-{OVER_CURRENT_MAX} A"
        )
    offsets = [
        offset
        for offset in range(0, len(data), ALARM_RECORD_LENGTH)
        if data[offset] == ALARM_OVER_CURRENT_ID
    ]
    if len(offsets) != 1:
        raise ValueError("Alarm settings hold no single over-current record")
    data[offsets[0] + 2 : offsets[0] + 4] = value.to_bytes(2, "big")
    return t.SerializableBytes(bytes(data))


class MoesMeterManufCluster(TuyaMCUCluster):
    """Tuya MCU cluster that ignores datapoints it cannot decode."""

    def _dp_2_attr_update(self, datapoint: TuyaDatapointData) -> None:
        """Update the attributes of a datapoint unless one of them cannot be decoded."""
        for mapped_attr in self._dp_to_attributes.get(datapoint.dp, []):
            if (
                mapped_attr.converter
                and mapped_attr.converter(datapoint.data.payload) is None
            ):
                self.debug("Cannot decode data point %s: %s", datapoint.dp, datapoint)
                return
        super()._dp_2_attr_update(datapoint)


class MoesMeterSegmentedReports(ZosungIRTransmit):
    """Pull the segmented datapoint reports of the meter and pass them on.

    The meter announces a report with frame 0x00. The coordinator acknowledges it
    with 0x01 and asks for the parts with 0x02, each of which the meter sends with
    0x03. Once the report is complete the coordinator confirms it with 0x04.
    """

    def __init__(self, *args, **kwargs):
        """Init the cluster and its open transfers."""
        super().__init__(*args, **kwargs)
        self.reports: dict[int, bytearray] = {}
        self.report_lengths: dict[int, int] = {}

    def _send(self, command_id: int, **kwargs) -> None:
        """Send a frame of the transfer without waiting for it."""
        self.create_catching_task(
            self.command(command_id, **kwargs, expect_reply=False)
        )

    def _drop(self, seq: int) -> None:
        """Forget a transfer."""
        self.reports.pop(seq, None)
        self.report_lengths.pop(seq, None)

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ):
        """Handle a frame of a segmented report."""
        if not hdr.frame_control.disable_default_response:
            self.send_default_rsp(hdr, status=foundation.Status.SUCCESS)

        commands = self.ServerCommandDefs
        if hdr.command_id == commands.receive_ir_frame_00.id:
            self._start_report(args)
        elif hdr.command_id == commands.receive_ir_frame_03.id:
            self._receive_part(args)
        elif hdr.command_id == commands.receive_ir_frame_05.id:
            self._drop(args.seq)
        else:
            self.debug("Unhandled frame %s: %s", hdr.command_id, args)

    def _start_report(self, args: Any) -> None:
        """Accept an announced report and ask for its first part."""
        if (
            args.clusterid != TUYA_CLUSTER_ID
            or args.cmd != SEGMENT_TUYA_REPORT_CMD
            or not 2 <= args.length <= SEGMENT_MAX_LENGTH
        ):
            self.debug("Ignoring announced transfer: %s", args)
            return
        self.reports[args.seq] = bytearray()
        self.report_lengths[args.seq] = args.length
        for seq in list(self.reports)[:-SEGMENT_MAX_TRANSFERS]:
            self._drop(seq)
        self._send(
            self.ServerCommandDefs.receive_ir_frame_01.id,
            zero=0,
            seq=args.seq,
            length=args.length,
            unk1=args.unk1,
            clusterid=args.clusterid,
            unk2=args.unk2,
            cmd=args.cmd,
            unk3=args.unk3,
        )
        self._request_part(args.seq, 0)

    def _request_part(self, seq: int, position: int) -> None:
        """Ask the meter for the part of a report at a position."""
        self._send(
            self.ServerCommandDefs.receive_ir_frame_02.id,
            seq=seq,
            position=position,
            maxlen=SEGMENT_PART_LENGTH,
        )

    def _receive_part(self, args: Any) -> None:
        """Add a part to its report, and pass the report on once it is complete."""
        report = self.reports.get(args.seq)
        if report is None:
            return
        part = bytes(args.msgpart)
        length = self.report_lengths[args.seq]
        if (
            args.position != len(report)
            or not part
            or len(report) + len(part) > length
            or ir_msg_part_crc(part) != args.msgpartcrc
        ):
            self.debug("Dropping report %s after a bad part: %s", args.seq, args)
            self._drop(args.seq)
            return
        report += part
        if len(report) < length:
            self._request_part(args.seq, len(report))
            return
        self._drop(args.seq)
        self._send(
            self.ServerCommandDefs.receive_ir_frame_04.id,
            zero0=0,
            seq=args.seq,
            zero1=0,
        )
        self._pass_on(bytes(report))

    def _pass_on(self, report: bytes) -> None:
        """Decode the datapoints of a report and hand them to the Tuya MCU cluster.

        Layout: a u16 sequence number, then datapoints of
        [dp u8][type u8][length u16 BE][data].
        """
        datapoints = []
        offset = 2
        while offset < len(report):
            header = report[offset : offset + 4]
            if len(header) < 4:
                self.warning("Cannot decode segmented report %s", report.hex())
                return
            dp, dp_type = header[0], header[1]
            length = int.from_bytes(header[2:4], "big")
            data = report[offset + 4 : offset + 4 + length]
            if len(data) != length or dp_type > TuyaDPType.BITMAP:
                self.warning("Cannot decode segmented report %s", report.hex())
                return
            offset += 4 + length
            tuya_data = TuyaData()
            tuya_data.dp_type = TuyaDPType(dp_type)
            tuya_data.function = t.uint8_t(0)
            tuya_data.raw = t.LVBytes(data)
            datapoints.append(TuyaDatapointData(dp=dp, data=tuya_data))
        self.debug("Segmented report: %s", datapoints)
        mcu = getattr(self.endpoint, TuyaMCUCluster.ep_attribute)
        mcu.handle_get_data(TuyaCommand(status=0, tsn=0, datapoints=datapoints))


class RefreshMeasurements(t.enum8):
    """DP44 value asking the meter to report its measurements now."""

    Refresh = 0x01


(
    TuyaQuirkBuilder("_TZE28C1000000_2fnssffc", "TS0601")
    .applies_to("_TZE284_2fnssffc", "TS0601")
    .replaces(MoesMeterSegmentedReports)
    .tuya_sensor(
        dp_id=1,
        attribute_name="energy",
        type=t.uint32_t,
        divisor=100,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        fallback_name="Energy",
    )
    .tuya_sensor(
        dp_id=2,
        attribute_name="reverse_energy",
        type=t.uint32_t,
        divisor=100,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        translation_key="reverse_energy",
        fallback_name="Reverse energy",
    )
    .tuya_sensor(
        dp_id=10,
        attribute_name="fault",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault",
        fallback_name="Fault",
    )
    .tuya_sensor(
        dp_id=49,
        attribute_name="ac_frequency",
        type=t.uint16_t,
        divisor=100,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfFrequency.HERTZ,
        fallback_name="Frequency",
    )
    # DP6 holds voltage, current, power and power factor in one frame, so each gets
    # an attribute of its own on an unused DP id.
    .tuya_attribute(dp_id=0xF1, attribute_name="voltage", type=t.uint16_t)
    .tuya_attribute(dp_id=0xF2, attribute_name="current", type=t.int32s)
    .tuya_attribute(dp_id=0xF3, attribute_name="power", type=t.int32s)
    .tuya_attribute(dp_id=0xF4, attribute_name="power_factor", type=t.uint8_t)
    .tuya_dp_multi(
        dp_id=6,
        attribute_mapping=[
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute, name, converter=_phase_value(name)
            )
            for name in ("voltage", "current", "power", "power_factor")
        ],
    )
    .sensor(
        attribute_name="voltage",
        cluster_id=TUYA_CLUSTER_ID,
        divisor=10,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        fallback_name="Voltage",
    )
    .sensor(
        attribute_name="current",
        cluster_id=TUYA_CLUSTER_ID,
        divisor=1000,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        fallback_name="Current",
    )
    .sensor(
        attribute_name="power",
        cluster_id=TUYA_CLUSTER_ID,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        fallback_name="Power",
    )
    .sensor(
        attribute_name="power_factor",
        cluster_id=TUYA_CLUSTER_ID,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        fallback_name="Power factor",
    )
    # DP17: the whole alarm settings frame is kept, as writes have to send it back.
    .tuya_attribute(dp_id=0xF5, attribute_name="alarm_settings", type=t.LVBytes)
    .tuya_attribute(
        dp_id=0xF6,
        attribute_name="over_current_threshold",
        type=t.uint16_t,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
    )
    .tuya_dp_multi(
        dp_id=17,
        attribute_mapping=[
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "alarm_settings",
                converter=decode_alarm_settings,
            ),
            DPToAttributeMapping(
                TuyaMCUCluster.ep_attribute,
                "over_current_threshold",
                converter=decode_over_current_threshold,
            ),
        ],
        dp_converter=encode_over_current_threshold,
    )
    .number(
        attribute_name="over_current_threshold",
        cluster_id=TUYA_CLUSTER_ID,
        min_value=OVER_CURRENT_MIN,
        max_value=OVER_CURRENT_MAX,
        step=1,
        unit=UnitOfElectricCurrent.AMPERE,
        mode="box",
        translation_key="over_current_threshold",
        fallback_name="Over-current threshold",
    )
    .tuya_dp_attribute(
        dp_id=44,
        attribute_name="refresh_measurements",
        type=t.uint8_t,
        access=foundation.ZCLAttributeAccess.Write,
        dp_converter=lambda _: RefreshMeasurements.Refresh,
    )
    .write_attr_button(
        attribute_name="refresh_measurements",
        attribute_value=RefreshMeasurements.Refresh,
        cluster_id=TUYA_CLUSTER_ID,
        translation_key="refresh_measurements",
        fallback_name="Refresh measurements",
    )
    .tuya_enchantment(read_attr_spell=True, data_query_spell=True)
    .add_to_registry(replacement_cluster=MoesMeterManufCluster)
)
