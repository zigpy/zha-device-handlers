"""Tests for Tuya TS0601 radiator thermostat _TZE200_a4bpgplm quirk."""

from unittest import mock

from zigpy.zcl import foundation
from zigpy.zcl.clusters.hvac import RunningState, Thermostat

from tests.common import ClusterListener, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()

# Incoming Tuya "get data" frames -> (expected thermostat attribute, expected value).
# Frame layout: <fc><tsn><cmd=0x02><status><seq><dp><type><len(2)><value>.
TUYA_READ_PLAN = (
    # DP1 system_mode/preset enum: 0=auto, 1=manual, 2=off, 3=on(valve open)
    (
        b"\t\xc2\x02\x00q\x01\x04\x00\x01\x00",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Auto,
    ),
    (
        b"\t\xc2\x02\x00q\x01\x04\x00\x01\x01",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Heat,
    ),
    (
        b"\t\xc2\x02\x00q\x01\x04\x00\x01\x02",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Off,
    ),
    (
        b"\t\xc2\x02\x00q\x01\x04\x00\x01\x03",
        Thermostat.AttributeDefs.system_mode,
        Thermostat.SystemMode.Heat,
    ),
    # DP2 setpoint: Tuya degC*10 -> ZCL degC*100 (21.0 -> 2100)
    (
        b"\t\xc2\x02\x00q\x02\x02\x00\x04\x00\x00\x00\xd2",
        Thermostat.AttributeDefs.occupied_heating_setpoint,
        2100,
    ),
    # DP3 local temperature: 21.5 -> 2150
    (
        b"\t\xc2\x02\x00q\x03\x02\x00\x04\x00\x00\x00\xd7",
        Thermostat.AttributeDefs.local_temperature,
        2150,
    ),
    # DP6 running state: 1 -> heating, 0 -> idle
    (
        b"\t\xc2\x02\x00q\x06\x04\x00\x01\x01",
        Thermostat.AttributeDefs.running_state,
        RunningState.Heat_State_On,
    ),
    (
        b"\t\xc2\x02\x00q\x06\x04\x00\x01\x00",
        Thermostat.AttributeDefs.running_state,
        RunningState.Idle,
    ),
)

# Outgoing frame for occupied_heating_setpoint=2500 (DP2 = 2500 // 10 = 250 = 0xFA).
SETPOINT_WRITE_FRAME = b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\xfa"


async def test_a4bpgplm_read(zigpy_device_from_v2_quirk):
    """Incoming datapoints update the thermostat cluster attributes."""
    quirked = zigpy_device_from_v2_quirk("_TZE200_a4bpgplm", "TS0601")
    ep = quirked.endpoints[1]

    assert ep.tuya_manufacturer is not None
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)
    assert isinstance(ep.thermostat, Thermostat)

    # Heating-only radiator valve, 5-35 degC range advertised to HA.
    assert (
        ep.thermostat.get(Thermostat.AttributeDefs.ctrl_sequence_of_oper.id)
        == Thermostat.ControlSequenceOfOperation.Heating_Only
    )
    assert (
        ep.thermostat.get(Thermostat.AttributeDefs.abs_min_heat_setpoint_limit.id)
        == 500
    )
    assert (
        ep.thermostat.get(Thermostat.AttributeDefs.abs_max_heat_setpoint_limit.id)
        == 3500
    )

    for msg, attr, value in TUYA_READ_PLAN:
        listener = ClusterListener(ep.thermostat)
        hdr, data = ep.tuya_manufacturer.deserialize(msg)
        status = ep.tuya_manufacturer.handle_get_data(data.data)
        assert status == foundation.Status.SUCCESS

        assert len(listener.attribute_updates) == 1
        assert listener.attribute_updates[0][0] == attr.id
        assert listener.attribute_updates[0][1] == value
        assert ep.thermostat.get(attr.id) == value


async def test_a4bpgplm_write_setpoint(zigpy_device_from_v2_quirk):
    """Writing the setpoint is scaled back to Tuya degC*10 and sent on DP2."""
    quirked = zigpy_device_from_v2_quirk("_TZE200_a4bpgplm", "TS0601")
    ep = quirked.endpoints[1]

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
    ) as m1:
        (status,) = await ep.thermostat.write_attributes(
            {"occupied_heating_setpoint": 2500}
        )
        await wait_for_zigpy_tasks()
        assert status[0].status == foundation.Status.SUCCESS

        kwargs = m1.call_args.kwargs
        assert kwargs["cluster"] == 0xEF00
        assert kwargs["command_id"] == 0
        assert kwargs["data"] == SETPOINT_WRITE_FRAME


async def test_a4bpgplm_write_system_mode(zigpy_device_from_v2_quirk):
    """system_mode writes DP1 as an ENUM datapoint (type 0x04).

    Regression guard: a plain int would be sent as a 4-byte VALUE (type 0x02)
    and the device silently ignores it (e.g. Off would never close the valve).
    DP1 payload tail is <dp=01><type=04><len=0001><value>: off=2, heat(manual)=1, auto=0.
    """
    quirked = zigpy_device_from_v2_quirk("_TZE200_a4bpgplm", "TS0601")
    ep = quirked.endpoints[1]

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    cases = (
        (Thermostat.SystemMode.Off, 0x02),
        (Thermostat.SystemMode.Heat, 0x01),
        (Thermostat.SystemMode.Auto, 0x00),
    )
    for mode, dp_value in cases:
        with mock.patch.object(
            ep.tuya_manufacturer.endpoint, "request", side_effect=async_success
        ) as m1:
            await ep.thermostat.write_attributes({"system_mode": mode})
            await wait_for_zigpy_tasks()

            kwargs = m1.call_args.kwargs
            assert kwargs["cluster"] == 0xEF00
            assert kwargs["command_id"] == 0
            # <dp=1><type=0x04 enum><len=0x0001><value>
            assert kwargs["data"].endswith(bytes([0x01, 0x04, 0x00, 0x01, dp_value]))
