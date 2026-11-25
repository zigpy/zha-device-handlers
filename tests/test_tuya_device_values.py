"""Tests for Tuya datapoints kept as writable device values."""

import asyncio
import enum
from typing import Any
from unittest import mock

import pytest
from zha.application import EntityPlatform
from zha.application.platforms.binary_sensor import DeviceValueBinarySensor
from zha.application.platforms.number import DeviceValueNumber
from zha.application.platforms.select import DeviceValueSelect
from zha.application.platforms.switch import DeviceValueSwitch
from zha.exceptions import ZHAException
from zha.quirks import DEVICE_REGISTRY, DeviceRegistry
from zha.zigbee.store import device_value
import zigpy.types as t
from zigpy.zcl import foundation

from tests.common import attribute_cache_row, deleted_rows, wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder import BinarySensorDeviceClass, EntityType
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    TUYA_SEND_DATA,
    TUYA_SET_DATA,
    TuyaCommand,
    TuyaData,
    TuyaDatapointData,
    TuyaDPType,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    DPToDeviceValueMapping,
    TuyaMCUCluster,
    tuya_device_value_writer,
)
from zhaquirks.tuya.tuya_fingerbot import FingerBotMode, FingerBotReverse
from zhaquirks.tuya.tuya_siren import (
    TuyaAlarmVolume,
    TuyaSirenRingtoneV02,
    TuyaSirenState,
)

zhaquirks.setup()


class Speed(t.enum8):
    """Speed of the test device."""

    Low = 0x00
    High = 0x01


def _writable_builder(
    manufacturer: str = "_TZE200_values",
    model: str = "TS0601",
    registry: DeviceRegistry | None = None,
) -> TuyaQuirkBuilder:
    return (
        TuyaQuirkBuilder(manufacturer, model, registry=registry or DeviceRegistry())
        .tuya_switch(
            dp_id=1,
            attribute_name="child_lock",
            force_inverted=True,
            translation_key="child_lock",
            fallback_name="Child lock",
            as_device_value=True,
        )
        .tuya_number(
            dp_id=2,
            type=t.uint16_t,
            attribute_name="delay",
            min_value=0,
            max_value=600,
            step=0.5,
            multiplier=0.5,
            mode="box",
            translation_key="delay",
            fallback_name="Delay",
            endpoint_id=2,
            as_device_value=True,
        )
        .tuya_enum(
            dp_id=3,
            attribute_name="speed",
            enum_class=Speed,
            translation_key="speed",
            fallback_name="Speed",
            as_device_value=True,
        )
        .tuya_binary_sensor(
            dp_id=4,
            attribute_name="tamper",
            translation_key="tamper",
            fallback_name="Tamper",
            as_device_value=True,
        )
    )


def _sent_datapoints(request: mock.Mock) -> list[tuple[int, int, TuyaDatapointData]]:
    """Return the command ID and the datapoints of each request sent."""
    sent = []

    for call in request.call_args_list:
        command, rest = TuyaCommand.deserialize(call.kwargs["data"][3:])
        assert rest == b""
        (datapoint,) = command.datapoints
        sent.append((call.kwargs["command_id"], datapoint.dp, datapoint.data))

    return sent


def test_tuya_entities_as_device_values():
    """Tuya entity helpers keep datapoints as device values and keep unique IDs."""
    builder = _writable_builder()

    # No invented attributes on the Tuya cluster
    assert not builder.new_attributes
    assert builder.entity_metadata == []

    mappings = {dp: mapping for dp, (mapping,) in builder.tuya_dp_to_attribute.items()}
    assert all(isinstance(m, DPToDeviceValueMapping) for m in mappings.values())
    assert [mappings[dp].value.key for dp in (1, 2, 3, 4)] == [
        "child_lock",
        "delay",
        "speed",
        "tamper",
    ]
    assert mappings[1].wire_type is t.Bool
    assert mappings[2].wire_type is t.uint16_t
    assert mappings[3].wire_type is Speed
    assert mappings[4].wire_type is None

    switch, number, select, binary_sensor = builder.added_entities

    assert switch.entity_cls is DeviceValueSwitch
    assert switch.kwargs["unique_id_suffix"] == "1-child_lock"
    assert switch.kwargs["force_inverted"] is True
    assert switch.kwargs["translation_key"] == "child_lock"

    assert number.entity_cls is DeviceValueNumber
    assert number.kwargs["unique_id_suffix"] == "2-delay"
    assert number.kwargs["multiplier"] == 0.5
    assert number.kwargs["max_value"] == 600
    assert number.kwargs["mode"] == "box"

    assert select.entity_cls is DeviceValueSelect
    assert select.kwargs["unique_id_suffix"] == "1-speed"
    assert select.kwargs["enum"] is Speed

    assert binary_sensor.entity_cls is DeviceValueBinarySensor
    assert binary_sensor.kwargs["unique_id_suffix"] == "1-tamper"
    assert "writer" not in binary_sensor.kwargs

    for added, dp in ((switch, 1), (number, 2), (select, 3), (binary_sensor, 4)):
        assert added.endpoint_id is None
        assert added.kwargs["value"] is mappings[dp].value

    for added in (switch, number, select):
        assert callable(added.kwargs["writer"])


@pytest.mark.parametrize(
    "method,kwargs,match",
    [
        (
            "tuya_switch",
            {"invert_attribute_name": "inverted"},
            "cannot be inverted by an attribute",
        ),
        (
            "tuya_switch",
            {"entity_platform": EntityPlatform.SENSOR},
            "is a switch",
        ),
        (
            "tuya_enum",
            {"enum_class": Speed, "entity_platform": EntityPlatform.SENSOR},
            "Only a select",
        ),
        (
            "tuya_enum",
            {"enum_class": Speed, "access": foundation.ZCLAttributeAccess.Read},
            "must be writable",
        ),
        (
            "tuya_number",
            {"type": t.uint16_t, "access": foundation.ZCLAttributeAccess.Read},
            "must be writable",
        ),
        (
            "tuya_number",
            {"type": t.uint16_t, "attribute_initialized_from_cache": False},
            "cannot be read",
        ),
        (
            "tuya_binary_sensor",
            {"attribute_initialized_from_cache": False},
            "cannot be read",
        ),
        (
            "tuya_switch",
            {"fallback_name": None},
            "fallback_name",
        ),
        (
            "tuya_number",
            {"type": t.uint16_t, "translation_key": None},
            "translation_key or device_class",
        ),
    ],
)
def test_tuya_entities_as_device_values_refused(
    method: str, kwargs: dict[str, Any], match: str
):
    """What a device value entity cannot do is refused when the quirk is built."""
    builder = TuyaQuirkBuilder("_TZE200_values", "TS0601")
    kwargs = {
        "dp_id": 1,
        "attribute_name": "x",
        "translation_key": "x",
        "fallback_name": "X",
        "as_device_value": True,
    } | kwargs

    with pytest.raises(ValueError, match=match):
        getattr(builder, method)(**kwargs)


def test_device_value_entity_builders():
    """Generic builder methods add device value entities keyed by the value."""
    value = device_value("setting", int)

    async def writer(device, new_value):
        pass

    builder = (
        TuyaQuirkBuilder("_TZE200_values", "TS0601")
        .device_value_number(
            value, writer=writer, step=5, translation_key="n", fallback_name="N"
        )
        .device_value_switch(value, on_value=2, translation_key="s", fallback_name="S")
        .device_value_select(
            value,
            Speed,
            unique_id_suffix="mode",
            translation_key="m",
            fallback_name="M",
        )
        .device_value_binary_sensor(
            value, value_converter=bool, translation_key="b", fallback_name="B"
        )
    )

    number, switch, select, binary_sensor = builder.added_entities
    assert [a.entity_cls for a in builder.added_entities] == [
        DeviceValueNumber,
        DeviceValueSwitch,
        DeviceValueSelect,
        DeviceValueBinarySensor,
    ]
    assert number.kwargs["writer"] is writer
    assert number.kwargs["step"] == 5
    assert switch.kwargs["writer"] is None
    assert switch.kwargs["on_value"] == 2
    assert select.kwargs["enum"] is Speed
    assert binary_sensor.kwargs["value_converter"] is bool

    assert [a.kwargs["unique_id_suffix"] for a in builder.added_entities] == [
        "setting",
        "setting",
        "mode",
        "setting",
    ]

    for method in (
        builder.device_value_number,
        builder.device_value_switch,
        builder.device_value_binary_sensor,
    ):
        with pytest.raises(ValueError, match="translation_key or device_class"):
            method(value, fallback_name="X")

    with pytest.raises(ValueError, match="translation_key or device_class"):
        builder.device_value_select(value, Speed, fallback_name="X")


async def test_tuya_device_values_report_and_write(device_mock):
    """Reports set device values, and writes send them typed as the datapoint."""
    registry = DeviceRegistry()
    _writable_builder(
        device_mock.manufacturer, device_mock.model, registry
    ).skip_configuration().add_to_registry()

    device = registry.resolve(device_mock)
    cluster = device.endpoints[1].tuya_manufacturer
    added = {
        a.kwargs["value"].key: a
        for a in registry.match_entry(
            device
        ).zha_device_factory.quirk_definition.added_entities
    }

    def receive(dp: int, data: TuyaData) -> None:
        cluster.handle_get_data(
            TuyaCommand(status=0, tsn=1, datapoints=[TuyaDatapointData(dp, data)])
        )

    # Reports
    receive(1, TuyaData(t.Bool.true))
    receive(2, TuyaData(t.uint32_t(30)))
    receive(3, TuyaData(Speed.High))
    receive(4, TuyaData(t.Bool.false))

    values = {key: a.kwargs["value"] for key, a in added.items()}
    assert device.store[values["child_lock"]] == 1
    assert device.store[values["delay"]] == 30
    assert device.store[values["speed"]] == 1
    assert device.store[values["tamper"]] == 0

    # Writes
    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await added["child_lock"].kwargs["writer"](device, 0)
        await added["delay"].kwargs["writer"](device, 120)
        await added["speed"].kwargs["writer"](device, Speed.Low)

    sent = _sent_datapoints(request)
    assert [(command_id, dp) for command_id, dp, _ in sent] == [
        (TUYA_SET_DATA, 1),
        (TUYA_SET_DATA, 2),
        (TUYA_SET_DATA, 3),
    ]
    assert [(data.dp_type, data.payload) for _, _, data in sent] == [
        (TuyaDPType.BOOL, t.Bool.false),
        (TuyaDPType.VALUE, 120),
        (TuyaDPType.ENUM, 0),
    ]
    assert all(call.kwargs["expect_reply"] is False for call in request.call_args_list)

    # Set in the store once sent
    assert device.store[values["child_lock"]] == 0
    assert device.store[values["delay"]] == 120
    assert device.store[values["speed"]] == 0

    # A value no datapoint of the device maps cannot be written
    with pytest.raises(ZHAException, match="No Tuya MCU cluster maps"):
        await tuya_device_value_writer(device_value("unmapped", int))(device, 1)

    with pytest.raises(ZHAException, match="No datapoint maps"):
        await cluster.write_device_value(device_value("unmapped", int), 1)


async def test_tuya_device_value_write_stores_what_is_sent(device_mock):
    """The value cast to the datapoint's wire type is what is sent and stored."""
    registry = DeviceRegistry()
    _writable_builder(
        device_mock.manufacturer, device_mock.model, registry
    ).skip_configuration().add_to_registry()

    device = registry.resolve(device_mock)
    cluster = device.endpoints[1].tuya_manufacturer
    delay = device_value("delay", int)
    writer = tuya_device_value_writer(delay)

    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        # A fraction a uint16 datapoint cannot carry is cut off, and stored so
        await writer(device, 2.5)
        assert device.store.namespace(delay.namespace)[delay.key] == 2

        # Through the number entity, which divides by its multiplier and rounds
        zha_device = mock.MagicMock()
        zha_device.device = device
        number = DeviceValueNumber(
            zha_device,
            unique_id="number",
            value=delay,
            writer=writer,
            multiplier=0.5,
            translation_key="delay",
        )
        await number.async_set_native_value(60.4)
        assert device.store[delay] == 121
        assert number.native_value == 60.5

        # A value outside the wire type is refused before anything is sent
        request.reset_mock()
        with pytest.raises(ZHAException, match="not an unsigned 16 bit integer"):
            await writer(device, 70000)

    assert request.call_count == 0
    assert device.store[delay] == 121


async def test_tuya_device_value_write_without_store(device_mock):
    """Without a store, nothing is sent."""
    registry = DeviceRegistry()
    _writable_builder(
        device_mock.manufacturer, device_mock.model, registry
    ).skip_configuration().add_to_registry()

    device = registry.resolve(device_mock)
    cluster = device.endpoints[1].tuya_manufacturer

    with (
        mock.patch("zhaquirks.tuya.mcu.get_device_store", return_value=None),
        mock.patch.object(cluster.endpoint, "request") as request,
        pytest.raises(ZHAException, match="has no store"),
    ):
        await cluster.write_device_value(device_value("delay", int), 5)

    assert request.call_count == 0


async def test_tuya_device_value_write_through_read_converter(device_mock):
    """A datapoint read through a converter cannot be written without a dp_converter."""
    registry = DeviceRegistry()
    level = device_value("level", int)

    (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_dp_multi(8, [DPToDeviceValueMapping(level, converter=lambda x: x / 10)])
        .skip_configuration()
        .add_to_registry()
    )

    device = registry.resolve(device_mock)
    cluster = device.endpoints[1].tuya_manufacturer

    with (
        mock.patch.object(cluster.endpoint, "request") as request,
        pytest.raises(ZHAException, match="read through a converter"),
    ):
        await cluster.write_device_value(level, 5)

    assert request.call_count == 0
    assert level not in device.store

    # With a wire type, the builder refuses it already
    with pytest.raises(ValueError, match="cannot invert"):
        TuyaQuirkBuilder("_TZE200_values", "TS0601").tuya_dp_multi(
            9,
            [
                DPToDeviceValueMapping(
                    device_value("x", int), converter=lambda x: x, wire_type=t.uint8_t
                )
            ],
        )

    # A dp_converter builds the datapoint, so a read converter is fine then
    TuyaQuirkBuilder("_TZE200_values", "TS0601").tuya_dp_multi(
        9,
        [
            DPToDeviceValueMapping(
                device_value("x", int), converter=lambda x: x, wire_type=t.uint8_t
            )
        ],
        dp_converter=lambda x: x,
    )


def test_device_value_select_needs_int_enum():
    """Enums whose members are not ints are refused when the quirk is built."""

    class Color(enum.Enum):
        Red = "red"

    builder = TuyaQuirkBuilder("_TZE200_values", "TS0601")

    with pytest.raises(TypeError, match="int enum"):
        builder.tuya_enum(
            dp_id=1,
            attribute_name="color",
            enum_class=Color,
            translation_key="color",
            fallback_name="Color",
            as_device_value=True,
        )

    with pytest.raises(TypeError, match="int enum"):
        builder.device_value_select(
            device_value("color", int),
            Color,
            translation_key="color",
            fallback_name="Color",
        )


async def test_tuya_device_value_write_failure(device_mock):
    """A failure to send reaches the caller; the value stays stored, as an attribute does."""
    registry = DeviceRegistry()
    _writable_builder(
        device_mock.manufacturer, device_mock.model, registry
    ).skip_configuration().add_to_registry()

    device = registry.resolve(device_mock)
    cluster = device.endpoints[1].tuya_manufacturer
    delay = device_value("delay", int)
    device.store[delay] = 30
    seen = []

    async def failing_request(*args, **kwargs):
        # Stored when the command is built, before it is sent
        seen.append(device.store.get(delay))
        raise TimeoutError

    with (
        mock.patch.object(cluster.endpoint, "request", side_effect=failing_request),
        pytest.raises(TimeoutError),
    ):
        await tuya_device_value_writer(delay)(device, 120)

    assert seen == [120]

    # Kept until the device reports, as for an attribute write
    assert device.store[delay] == 120


async def test_tuya_device_value_write_dp_converter(device_mock):
    """A datapoint built by a converter gets the written value and its siblings."""
    registry = DeviceRegistry()
    low = device_value("low", int)
    high = device_value("high", int)

    (
        TuyaQuirkBuilder(device_mock.manufacturer, device_mock.model, registry=registry)
        .tuya_dp_multi(
            7,
            [
                DPToDeviceValueMapping(low),
                DPToAttributeMapping(TuyaMCUCluster.ep_attribute, "mid"),
                DPToDeviceValueMapping(high),
            ],
            dp_converter=lambda low, mid, high: t.uint32_t(
                (high or 0) << 16 | (mid or 0) << 8 | (low or 0)
            ),
        )
        .tuya_attribute(dp_id=7, attribute_name="mid", type=t.uint8_t)
        .skip_configuration()
        .add_to_registry()
    )

    device = registry.resolve(device_mock)
    cluster = device.endpoints[1].tuya_manufacturer
    cluster.update_attribute("mid", 0x22)
    device.store[high] = 0x33

    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await cluster.write_device_value(low, 0x11)

    ((_, dp, data),) = _sent_datapoints(request)
    assert dp == 7
    assert data.dp_type == TuyaDPType.VALUE
    assert data.payload == 0x332211

    # Only the written value is set; the siblings are left as they are
    assert device.store[low] == 0x11
    assert device.store[high] == 0x33
    assert cluster.get("mid") == 0x22

    # Concurrent writes to two values of the datapoint: the second is built after the
    # first has been stored, so the device ends with both
    async def slow_request(*args, **kwargs):
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return foundation.Status.SUCCESS

    with mock.patch.object(
        cluster.endpoint, "request", side_effect=slow_request
    ) as request:
        await asyncio.gather(
            cluster.write_device_value(low, 0x55),
            cluster.write_device_value(high, 0x66),
        )

    assert [data.payload for _, _, data in _sent_datapoints(request)] == [
        0x332255,
        0x662255,
    ]
    assert device.store[low] == 0x55
    assert device.store[high] == 0x66

    # A device value write and an attribute write of the same datapoint, in either
    # order: the later one is built from the earlier, so the device ends where the
    # store and the cache are
    with mock.patch.object(
        cluster.endpoint, "request", side_effect=slow_request
    ) as request:
        task = asyncio.create_task(cluster.write_device_value(low, 0x77))
        await asyncio.sleep(0)  # built and stored, now sending
        await cluster.write_attributes({"mid": 0x88})
        await task
        await wait_for_zigpy_tasks()

    assert [data.payload for _, _, data in _sent_datapoints(request)] == [
        0x662277,
        0x668877,
    ]

    with mock.patch.object(
        cluster.endpoint, "request", side_effect=slow_request
    ) as request:
        await cluster.write_attributes({"mid": 0x99})
        await cluster.write_device_value(high, 0xAA)
        await wait_for_zigpy_tasks()

    assert [data.payload for _, _, data in _sent_datapoints(request)] == [
        0x669977,
        0xAA9977,
    ]
    assert device.store[low] == 0x77
    assert device.store[high] == 0xAA
    assert cluster.get("mid") == 0x99


async def test_tuya_fingerbot_device_values(zigpy_device_from_v2_quirk):
    """The fingerbot keeps its settings as device values with unchanged unique IDs."""
    device = zigpy_device_from_v2_quirk("_TZ3210_dse8ogfy", "TS0001")
    cluster = device.endpoints[1].tuya_manufacturer
    definition = DEVICE_REGISTRY.match_entry(device).zha_device_factory.quirk_definition

    assert {
        (a.entity_cls, a.kwargs["unique_id_suffix"]) for a in definition.added_entities
    } == {
        (DeviceValueSelect, "1-mode"),
        (DeviceValueNumber, "1-down_movement"),
        (DeviceValueNumber, "1-sustain_time"),
        (DeviceValueSelect, "1-reverse"),
        (DeviceValueNumber, "1-up_movement"),
        (DeviceValueSwitch, "1-touch_control"),
    }

    # Only the battery is left as a quirk entity on a cluster
    assert [m.attribute_name for m in definition.entity_metadata] == []
    for name in ("mode", "down_movement", "touch_control"):
        assert name not in cluster.attributes_by_name

    added = {a.kwargs["value"].key: a for a in definition.added_entities}
    mode = added["mode"].kwargs["value"]

    # A mode report: datapoint 101, enum, "program"
    hdr, args = cluster.deserialize(b"\x09\x10\x02\x00\x10\x65\x04\x00\x01\x02")
    cluster.handle_message(hdr, args)
    assert device.store[mode] == FingerBotMode.PROGRAM

    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await added["mode"].kwargs["writer"](device, FingerBotMode.CLICK)
        await added["down_movement"].kwargs["writer"](device, 80)
        await added["touch_control"].kwargs["writer"](device, 1)

    # Sent with the quirk's write command
    assert [
        (command_id, dp, data.dp_type, data.payload)
        for command_id, dp, data in _sent_datapoints(request)
    ] == [
        (TUYA_SEND_DATA, 101, TuyaDPType.ENUM, FingerBotMode.CLICK),
        (TUYA_SEND_DATA, 102, TuyaDPType.VALUE, 80),
        (TUYA_SEND_DATA, 107, TuyaDPType.BOOL, t.Bool.true),
    ]
    assert device.store[mode] == FingerBotMode.CLICK


@pytest.mark.parametrize("typed", [True, False])
async def test_tuya_fingerbot_attributes_migrated(zigpy_device_from_v2_quirk, typed):
    """The fingerbot's old settings attributes move into its device values.

    They read back as a report would have stored them: the switch and enums as ints.
    """
    device = zigpy_device_from_v2_quirk("_TZ3210_dse8ogfy", "TS0001")
    cluster = device.endpoints[1].tuya_manufacturer
    definition = DEVICE_REGISTRY.match_entry(device).zha_device_factory.quirk_definition
    values = {
        a.kwargs["value"].key: a.kwargs["value"] for a in definition.added_entities
    }

    # The invented attributes the quirk had: ID, type and value
    old_attributes = {
        "mode": (0xEF65, FingerBotMode.PROGRAM),
        "down_movement": (0xEF66, t.uint16_t(80)),
        "sustain_time": (0xEF67, t.uint16_t(3)),
        "reverse": (0xEF68, FingerBotReverse.UP_OFF),
        "up_movement": (0xEF6A, t.uint16_t(20)),
        "touch_control": (0xEF6B, t.Bool.true),
    }
    rows = [
        attribute_cache_row(
            device,
            TUYA_CLUSTER_ID,
            attr_id,
            value.serialize() if typed else int(value),
            foundation.DataType.from_python_type(type(value)).type_id
            if typed
            else None,
            manufacturer_code=device.manufacturer_id,
        )
        for attr_id, value in old_attributes.values()
    ]

    result = device.load_attribute_cache(rows, migrate=True)
    assert len(deleted_rows(result)) == len(rows)

    stored = {key: device.store.get(values[key]) for key in old_attributes}
    assert stored == {
        "mode": 2,
        "down_movement": 80,
        "sustain_time": 3,
        "reverse": 1,
        "up_movement": 20,
        "touch_control": 1,
    }
    assert all(type(value) is int for value in stored.values())

    # As the entities read them
    assert FingerBotMode(stored["mode"]) is FingerBotMode.PROGRAM
    assert FingerBotReverse(stored["reverse"]) is FingerBotReverse.UP_OFF
    assert bool(stored["touch_control"]) is True

    # A report of the switch datapoint stores the same: 107, bool, on
    hdr, args = cluster.deserialize(b"\x09\x10\x02\x00\x10\x6b\x01\x00\x01\x01")
    cluster.handle_message(hdr, args)
    assert device.store.get(values["touch_control"]) == 1


def _old_attribute_rows(
    device, old_attributes: dict[str, tuple[int, Any]], typed: bool
) -> list:
    """Rows of the invented attributes a quirk had, typed or as untyped values."""
    return [
        attribute_cache_row(
            device,
            TUYA_CLUSTER_ID,
            attr_id,
            value.serialize() if typed else int(value),
            foundation.DataType.from_python_type(type(value)).type_id
            if typed
            else None,
            manufacturer_code=device.manufacturer_id,
        )
        for attr_id, value in old_attributes.values()
    ]


def _added_entities(device) -> dict[str, Any]:
    """Return the entities the device's quirk adds, by device value key."""
    definition = DEVICE_REGISTRY.match_entry(device).zha_device_factory.quirk_definition

    # No entity is left on an invented attribute of the Tuya cluster
    assert [
        m.attribute_name
        for m in definition.entity_metadata
        if m.cluster_id == TUYA_CLUSTER_ID
    ] == []

    return {a.kwargs["value"].key: a for a in definition.added_entities}


async def test_tuya_smart_siren_device_values(zigpy_device_from_v2_quirk):
    """The smart siren keeps its datapoints as device values, entities unchanged."""
    device = zigpy_device_from_v2_quirk("_TZE204_k7mfgaen", "TS0601")
    cluster = device.endpoints[1].tuya_manufacturer
    added = _added_entities(device)

    assert {
        (
            key,
            a.entity_cls,
            a.kwargs["unique_id_suffix"],
            a.kwargs["entity_type"],
            a.kwargs["translation_key"],
        )
        for key, a in added.items()
    } == {
        (
            "alarm_mode",
            DeviceValueSelect,
            "1-alarm_mode",
            EntityType.CONFIG,
            "alarm_mode",
        ),
        (
            "alarm_volume",
            DeviceValueSelect,
            "1-alarm_volume",
            EntityType.CONFIG,
            "alarm_volume",
        ),
        (
            "charge_state",
            DeviceValueBinarySensor,
            "1-charge_state",
            EntityType.DIAGNOSTIC,
            None,
        ),
        (
            "alarm_duration",
            DeviceValueNumber,
            "1-alarm_duration",
            EntityType.CONFIG,
            "alarm_duration",
        ),
        ("siren_on", DeviceValueSwitch, "1-siren_on", EntityType.STANDARD, "siren_on"),
        (
            "alarm_ringtone",
            DeviceValueSelect,
            "1-alarm_ringtone",
            EntityType.CONFIG,
            "alarm_ringtone",
        ),
    }
    for name in added:
        assert name not in cluster.attributes_by_name

    # Reports: siren on (13, bool) and charging (6, bool)
    for frame in (
        b"\x09\x10\x02\x00\x10\x0d\x01\x00\x01\x01",
        b"\x09\x10\x02\x00\x10\x06\x01\x00\x01\x01",
    ):
        hdr, args = cluster.deserialize(frame)
        cluster.handle_message(hdr, args)

    assert device.store.get(added["siren_on"].kwargs["value"]) == 1
    assert device.store.get(added["charge_state"].kwargs["value"]) == 1

    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await added["alarm_ringtone"].kwargs["writer"](
            device, TuyaSirenRingtoneV02.Door
        )
        await added["alarm_duration"].kwargs["writer"](device, 5)
        await added["siren_on"].kwargs["writer"](device, 0)

    assert [
        (command_id, dp, data.dp_type, data.payload)
        for command_id, dp, data in _sent_datapoints(request)
    ] == [
        (TUYA_SET_DATA, 21, TuyaDPType.ENUM, TuyaSirenRingtoneV02.Door),
        (TUYA_SET_DATA, 7, TuyaDPType.VALUE, 5),
        (TUYA_SET_DATA, 13, TuyaDPType.BOOL, t.Bool.false),
    ]
    assert device.store.get(added["siren_on"].kwargs["value"]) == 0


@pytest.mark.parametrize("typed", [True, False])
def test_tuya_smart_siren_attributes_migrated(zigpy_device_from_v2_quirk, typed):
    """The smart siren's old attributes move into its device values."""
    device = zigpy_device_from_v2_quirk("_TZE204_k7mfgaen", "TS0601")
    added = _added_entities(device)

    old_attributes = {
        "alarm_mode": (0xEF01, TuyaSirenState.Sound_and_light),
        "alarm_volume": (0xEF05, TuyaAlarmVolume.High),
        "charge_state": (0xEF06, t.Bool.true),
        "alarm_duration": (0xEF07, t.uint16_t(10)),
        "siren_on": (0xEF0D, t.Bool.false),
        "alarm_ringtone": (0xEF15, TuyaSirenRingtoneV02.Water),
    }
    rows = _old_attribute_rows(device, old_attributes, typed)

    result = device.load_attribute_cache(rows, migrate=True)
    assert len(result.migrated) == len(rows)

    assert {
        key: device.store.get(added[key].kwargs["value"]) for key in old_attributes
    } == {
        "alarm_mode": 2,
        "alarm_volume": 2,
        "charge_state": 1,
        "alarm_duration": 10,
        "siren_on": 0,
        "alarm_ringtone": 9,
    }


async def test_hobeian_contact_device_values(zigpy_device_from_v2_quirk):
    """The HOBEIAN door and vibration sensor keeps its datapoints as device values."""
    device = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-102ZM")
    cluster = device.endpoints[1].tuya_manufacturer
    added = _added_entities(device)

    assert {
        (
            key,
            a.entity_cls,
            a.kwargs["unique_id_suffix"],
            a.kwargs["entity_type"],
            a.kwargs.get("device_class"),
        )
        for key, a in added.items()
    } == {
        (
            "vibration",
            DeviceValueBinarySensor,
            "1-vibration",
            EntityType.STANDARD,
            BinarySensorDeviceClass.VIBRATION,
        ),
        (
            "contact",
            DeviceValueBinarySensor,
            "1-contact",
            EntityType.STANDARD,
            BinarySensorDeviceClass.OPENING,
        ),
        (
            "sensitivity_level",
            DeviceValueNumber,
            "1-sensitivity_level",
            EntityType.CONFIG,
            None,
        ),
    }

    # Reports: contact open (101, bool) and sensitivity 20 (6, value)
    for frame in (
        b"\x09\x10\x02\x00\x10\x65\x01\x00\x01\x01",
        b"\x09\x10\x02\x00\x10\x06\x02\x00\x04\x00\x00\x00\x14",
    ):
        hdr, args = cluster.deserialize(frame)
        cluster.handle_message(hdr, args)

    assert device.store.get(added["contact"].kwargs["value"]) == 1
    assert device.store.get(added["vibration"].kwargs["value"]) is None
    assert device.store.get(added["sensitivity_level"].kwargs["value"]) == 20

    with mock.patch.object(
        cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as request:
        await added["sensitivity_level"].kwargs["writer"](device, 35)

    assert [
        (command_id, dp, data.dp_type, data.payload)
        for command_id, dp, data in _sent_datapoints(request)
    ] == [(TUYA_SET_DATA, 6, TuyaDPType.VALUE, 35)]
    assert device.store.get(added["sensitivity_level"].kwargs["value"]) == 35


@pytest.mark.parametrize("typed", [True, False])
def test_hobeian_contact_attributes_migrated(zigpy_device_from_v2_quirk, typed):
    """The HOBEIAN sensor's old attributes move into its device values."""
    device = zigpy_device_from_v2_quirk("HOBEIAN", "ZG-102ZM")
    added = _added_entities(device)

    old_attributes = {
        "vibration": (0xEF01, t.Bool.false),
        "sensitivity_level": (0xEF06, t.uint8_t(25)),
        "contact": (0xEF65, t.Bool.true),
    }
    rows = _old_attribute_rows(device, old_attributes, typed)

    result = device.load_attribute_cache(rows, migrate=True)
    assert len(result.migrated) == len(rows)

    assert {
        key: device.store.get(added[key].kwargs["value"]) for key in old_attributes
    } == {"vibration": 0, "sensitivity_level": 25, "contact": 1}
