"""Tests for Philips quirks."""

from unittest import mock

import pytest
from zigpy.zcl.foundation import ZCLHeader

import zhaquirks
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_HOLD,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PARAMS,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    RIGHT,
    SHORT_PRESS,
    SHORT_RELEASE,
    TRIPLE_PRESS,
    TURN_OFF,
    TURN_ON,
)
import zhaquirks.philips
from zhaquirks.philips import Button, ButtonPressQueue, PhilipsRemoteCluster, PressType
from zhaquirks.philips.rdm002 import PhilipsRDM002
from zhaquirks.philips.rom001 import PhilipsROM001
from zhaquirks.philips.rwl022 import PhilipsRWL022
from zhaquirks.philips.rwlfirstgen import PhilipsRWLFirstGen, PhilipsRWLFirstGen2
from zhaquirks.philips.wall_switch import PhilipsWallSwitch

zhaquirks.setup()


@pytest.mark.parametrize(
    "classes, triggers",
    (
        (
            [PhilipsRWLFirstGen, PhilipsRWLFirstGen2, PhilipsRWL022],
            {
                (SHORT_PRESS, TURN_ON): {COMMAND: "on_press"},
                (SHORT_PRESS, TURN_OFF): {COMMAND: "off_press"},
                (SHORT_PRESS, DIM_UP): {COMMAND: "up_press"},
                (SHORT_PRESS, DIM_DOWN): {COMMAND: "down_press"},
                (LONG_PRESS, TURN_ON): {COMMAND: "on_hold"},
                (LONG_PRESS, TURN_OFF): {COMMAND: "off_hold"},
                (LONG_PRESS, DIM_UP): {COMMAND: "up_hold"},
                (LONG_PRESS, DIM_DOWN): {COMMAND: "down_hold"},
                (DOUBLE_PRESS, TURN_ON): {COMMAND: "on_double_press"},
                (DOUBLE_PRESS, TURN_OFF): {COMMAND: "off_double_press"},
                (DOUBLE_PRESS, DIM_UP): {COMMAND: "up_double_press"},
                (DOUBLE_PRESS, DIM_DOWN): {COMMAND: "down_double_press"},
                (TRIPLE_PRESS, TURN_ON): {COMMAND: "on_triple_press"},
                (TRIPLE_PRESS, TURN_OFF): {COMMAND: "off_triple_press"},
                (TRIPLE_PRESS, DIM_UP): {COMMAND: "up_triple_press"},
                (TRIPLE_PRESS, DIM_DOWN): {COMMAND: "down_triple_press"},
                (QUADRUPLE_PRESS, TURN_ON): {COMMAND: "on_quadruple_press"},
                (QUADRUPLE_PRESS, TURN_OFF): {COMMAND: "off_quadruple_press"},
                (QUADRUPLE_PRESS, DIM_UP): {COMMAND: "up_quadruple_press"},
                (QUADRUPLE_PRESS, DIM_DOWN): {COMMAND: "down_quadruple_press"},
                (QUINTUPLE_PRESS, TURN_ON): {COMMAND: "on_quintuple_press"},
                (QUINTUPLE_PRESS, TURN_OFF): {COMMAND: "off_quintuple_press"},
                (QUINTUPLE_PRESS, DIM_UP): {COMMAND: "up_quintuple_press"},
                (QUINTUPLE_PRESS, DIM_DOWN): {COMMAND: "down_quintuple_press"},
                (SHORT_RELEASE, TURN_ON): {COMMAND: "on_short_release"},
                (SHORT_RELEASE, TURN_OFF): {COMMAND: "off_short_release"},
                (SHORT_RELEASE, DIM_UP): {COMMAND: "up_short_release"},
                (SHORT_RELEASE, DIM_DOWN): {COMMAND: "down_short_release"},
                (LONG_RELEASE, TURN_ON): {COMMAND: "on_long_release"},
                (LONG_RELEASE, TURN_OFF): {COMMAND: "off_long_release"},
                (LONG_RELEASE, DIM_UP): {COMMAND: "up_long_release"},
                (LONG_RELEASE, DIM_DOWN): {COMMAND: "down_long_release"},
            },
        ),
        (
            [PhilipsROM001],
            {
                (SHORT_PRESS, TURN_ON): {COMMAND: "on_press"},
                (LONG_PRESS, TURN_ON): {COMMAND: "on_hold"},
                (DOUBLE_PRESS, TURN_ON): {COMMAND: "on_double_press"},
                (TRIPLE_PRESS, TURN_ON): {COMMAND: "on_triple_press"},
                (QUADRUPLE_PRESS, TURN_ON): {COMMAND: "on_quadruple_press"},
                (QUINTUPLE_PRESS, TURN_ON): {COMMAND: "on_quintuple_press"},
                (SHORT_RELEASE, TURN_ON): {COMMAND: "on_short_release"},
                (LONG_RELEASE, TURN_ON): {COMMAND: "on_long_release"},
            },
        ),
        (
            [PhilipsWallSwitch],
            {
                (SHORT_PRESS, TURN_ON): {COMMAND: "left_press"},
                (LONG_PRESS, TURN_ON): {COMMAND: "left_hold"},
                (DOUBLE_PRESS, TURN_ON): {COMMAND: "left_double_press"},
                (TRIPLE_PRESS, TURN_ON): {COMMAND: "left_triple_press"},
                (QUADRUPLE_PRESS, TURN_ON): {COMMAND: "left_quadruple_press"},
                (QUINTUPLE_PRESS, TURN_ON): {COMMAND: "left_quintuple_press"},
                (SHORT_RELEASE, TURN_ON): {COMMAND: "left_short_release"},
                (LONG_RELEASE, TURN_ON): {COMMAND: "left_long_release"},
                (SHORT_PRESS, RIGHT): {COMMAND: "right_press"},
                (LONG_PRESS, RIGHT): {COMMAND: "right_hold"},
                (DOUBLE_PRESS, RIGHT): {COMMAND: "right_double_press"},
                (TRIPLE_PRESS, RIGHT): {COMMAND: "right_triple_press"},
                (QUADRUPLE_PRESS, RIGHT): {COMMAND: "right_quadruple_press"},
                (QUINTUPLE_PRESS, RIGHT): {COMMAND: "right_quintuple_press"},
                (SHORT_RELEASE, RIGHT): {COMMAND: "right_short_release"},
                (LONG_RELEASE, RIGHT): {COMMAND: "right_long_release"},
            },
        ),
    ),
)
def test_legacy_remote_automation_triggers(classes, triggers):
    """Ensure we don't break any automation triggers by changing their values."""

    for cls in classes:
        assert cls.device_automation_triggers == triggers


class _SimpleRemote(PhilipsRemoteCluster):
    BUTTONS = {
        1: Button("turn_on"),
        2: Button("right"),
    }
    PRESS_TYPES = {
        0: PressType("remote_button_long_release", "remote_button_long_release"),
    }
    SIMULATE_SHORT_EVENTS = None


class _RemoteWithTriggerOverrides(_SimpleRemote):
    BUTTONS = {
        1: Button("turn_on", "turn_on", "left"),
        2: Button("right"),
    }


class _RemoteWithSimulatedRelease(_SimpleRemote):
    SIMULATE_SHORT_EVENTS = [
        PressType("remote_button_short_press", "remote_button_short_press"),
        PressType("remote_button_short_release", "remote_button_short_release"),
    ]


class _RemoteWithCommandOverrides(_SimpleRemote):
    PRESS_TYPES: dict[int, PressType] = {
        1: PressType(LONG_PRESS, COMMAND_HOLD),
        3: PressType(LONG_RELEASE, "release"),
    }


class _RemoteWithSimulatedReleaseAndCommandOverride(_SimpleRemote):
    SIMULATE_SHORT_EVENTS = [
        PressType("remote_button_short_press", "short_press"),
        PressType("remote_button_short_release", "remote_button_short_release"),
    ]


@pytest.mark.parametrize(
    "cls, expected_value",
    (
        (
            _SimpleRemote,
            {
                ("remote_button_long_release", "turn_on"): {
                    COMMAND: "turn_on_remote_button_long_release"
                },
                ("remote_button_long_release", "right"): {
                    COMMAND: "right_remote_button_long_release"
                },
            },
        ),
        (
            _RemoteWithTriggerOverrides,
            {
                ("remote_button_long_release", "turn_on"): {
                    COMMAND: "left_remote_button_long_release"
                },
                ("remote_button_long_release", "right"): {
                    COMMAND: "right_remote_button_long_release"
                },
            },
        ),
        (
            _RemoteWithSimulatedRelease,
            {
                ("remote_button_long_release", "turn_on"): {
                    COMMAND: "turn_on_remote_button_long_release"
                },
                ("remote_button_long_release", "right"): {
                    COMMAND: "right_remote_button_long_release"
                },
                ("remote_button_short_press", "turn_on"): {
                    COMMAND: "turn_on_remote_button_short_press"
                },
                ("remote_button_short_press", "right"): {
                    COMMAND: "right_remote_button_short_press"
                },
                ("remote_button_short_release", "turn_on"): {
                    COMMAND: "turn_on_remote_button_short_release"
                },
                ("remote_button_short_release", "right"): {
                    COMMAND: "right_remote_button_short_release"
                },
                ("remote_button_double_press", "turn_on"): {
                    COMMAND: "turn_on_double_press"
                },
                ("remote_button_double_press", "right"): {
                    COMMAND: "right_double_press"
                },
                ("remote_button_triple_press", "turn_on"): {
                    COMMAND: "turn_on_triple_press"
                },
                ("remote_button_triple_press", "right"): {
                    COMMAND: "right_triple_press"
                },
                ("remote_button_quadruple_press", "turn_on"): {
                    COMMAND: "turn_on_quadruple_press"
                },
                ("remote_button_quadruple_press", "right"): {
                    COMMAND: "right_quadruple_press"
                },
                ("remote_button_quintuple_press", "turn_on"): {
                    COMMAND: "turn_on_quintuple_press"
                },
                ("remote_button_quintuple_press", "right"): {
                    COMMAND: "right_quintuple_press"
                },
            },
        ),
        (
            _RemoteWithCommandOverrides,
            {
                ("remote_button_long_press", "turn_on"): {COMMAND: "turn_on_hold"},
                ("remote_button_long_press", "right"): {COMMAND: "right_hold"},
                ("remote_button_long_release", "turn_on"): {COMMAND: "turn_on_release"},
                ("remote_button_long_release", "right"): {COMMAND: "right_release"},
            },
        ),
        (
            _RemoteWithSimulatedReleaseAndCommandOverride,
            {
                ("remote_button_long_release", "turn_on"): {
                    COMMAND: "turn_on_remote_button_long_release"
                },
                ("remote_button_long_release", "right"): {
                    COMMAND: "right_remote_button_long_release"
                },
                ("remote_button_short_press", "turn_on"): {
                    COMMAND: "turn_on_short_press"
                },
                ("remote_button_short_press", "right"): {COMMAND: "right_short_press"},
                ("remote_button_short_release", "turn_on"): {
                    COMMAND: "turn_on_remote_button_short_release"
                },
                ("remote_button_short_release", "right"): {
                    COMMAND: "right_remote_button_short_release"
                },
                ("remote_button_double_press", "turn_on"): {
                    COMMAND: "turn_on_double_press"
                },
                ("remote_button_double_press", "right"): {
                    COMMAND: "right_double_press"
                },
                ("remote_button_triple_press", "turn_on"): {
                    COMMAND: "turn_on_triple_press"
                },
                ("remote_button_triple_press", "right"): {
                    COMMAND: "right_triple_press"
                },
                ("remote_button_quadruple_press", "turn_on"): {
                    COMMAND: "turn_on_quadruple_press"
                },
                ("remote_button_quadruple_press", "right"): {
                    COMMAND: "right_quadruple_press"
                },
                ("remote_button_quintuple_press", "turn_on"): {
                    COMMAND: "turn_on_quintuple_press"
                },
                ("remote_button_quintuple_press", "right"): {
                    COMMAND: "right_quintuple_press"
                },
            },
        ),
    ),
)
def test_generate_device_automation_triggers(cls, expected_value):
    """Test trigger generation and button overrides."""

    assert cls.generate_device_automation_triggers() == expected_value


class ManuallyFiredButtonPressQueue:
    """Philips button queue to derive multiple press events."""

    def __init__(self):
        """Init."""
        self.reset()

    def fire(self):
        """Fire the callback. Trigger after all inputs, before running assertions."""

        if self._callback is not None:
            self._callback(self._click_counter)

    def reset(self):
        """Reset the button press queue."""

        self._click_counter = 0
        self._callback = None
        self._button = None

    def press(self, callback, button):
        """Process a button press."""
        if button != self._button:
            self._click_counter = 1
        else:
            self._click_counter += 1
        self._button = button
        self._callback = callback


@pytest.mark.parametrize(
    "dev, ep, button, events",
    (
        (
            PhilipsWallSwitch,
            1,
            "left",
            ["press", "short_release"],
        ),
        (
            PhilipsROM001,
            1,
            "on",
            ["press", "short_release"],
        ),
        (
            PhilipsRWLFirstGen,
            2,
            "on",
            ["press", "short_release"],
        ),
        (
            PhilipsRWLFirstGen2,
            2,
            "on",
            ["press", "short_release"],
        ),
        (
            PhilipsRWL022,
            1,
            "on",
            ["press", "short_release"],
        ),
    ),
)
def test_PhilipsRemoteCluster_short_press(
    zigpy_device_from_quirk, dev, ep, button, events
):
    """Test PhilipsRemoteCluster short button press logic."""

    device = zigpy_device_from_quirk(dev)

    cluster = device.endpoints[ep].philips_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)
    cluster.button_press_queue = ManuallyFiredButtonPressQueue()

    cluster.handle_cluster_request(ZCLHeader(), [1, 0, 0, 0, 0])
    cluster.handle_cluster_request(ZCLHeader(), [1, 0, 2, 0, 0])
    cluster.button_press_queue.fire()

    assert listener.zha_send_event.call_count == 2

    calls = [
        mock.call(
            f"{button}_{events[0]}",
            {
                "button": button,
                "press_type": events[0],
                "command_id": None,
                "duration": 0,
                "args": [1, 0, 0, 0, 0],
            },
        ),
        mock.call(
            f"{button}_{events[1]}",
            {
                "button": button,
                "press_type": events[1],
                "command_id": None,
                "duration": 0,
                "args": [1, 0, 2, 0, 0],
            },
        ),
    ]

    listener.zha_send_event.assert_has_calls(calls)


@pytest.mark.parametrize(
    "dev, ep, button",
    (
        (
            PhilipsROM001,
            1,
            "on",
        ),
        (
            PhilipsWallSwitch,
            1,
            "left",
        ),
        (
            PhilipsRWLFirstGen,
            2,
            "on",
        ),
        (
            PhilipsRWLFirstGen2,
            2,
            "on",
        ),
        (
            PhilipsRWL022,
            1,
            "on",
        ),
    ),
)
@pytest.mark.parametrize(
    "count, action_press_type",
    (
        (2, "double_press"),
        (3, "triple_press"),
        (4, "quadruple_press"),
        (5, "quintuple_press"),
    ),
)
def test_PhilipsRemoteCluster_multi_press(
    zigpy_device_from_quirk,
    dev,
    ep,
    button,
    count,
    action_press_type,
):
    """Test PhilipsRemoteCluster button multi-press logic."""

    device = zigpy_device_from_quirk(dev)

    cluster = device.endpoints[ep].philips_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)
    cluster.button_press_queue = ManuallyFiredButtonPressQueue()

    for _ in range(0, count):
        # btn1 short press
        cluster.handle_cluster_request(ZCLHeader(), [1, 0, 0, 0, 0])
        # btn1 short release
        cluster.handle_cluster_request(ZCLHeader(), [1, 0, 2, 0, 0])
    cluster.button_press_queue.fire()

    assert listener.zha_send_event.call_count == 1
    args_button_id = count + 2
    listener.zha_send_event.assert_has_calls(
        [
            mock.call(
                f"{button}_{action_press_type}",
                {
                    "button": button,
                    "press_type": action_press_type,
                    "command_id": None,
                    "duration": 0,
                    "args": [1, 0, args_button_id, 0, 0],
                },
            ),
        ]
    )


@pytest.mark.parametrize(
    "dev, ep",
    (
        (PhilipsWallSwitch, 1),
        (PhilipsROM001, 1),
        (PhilipsRWLFirstGen, 2),
        (PhilipsRWLFirstGen2, 2),
        (PhilipsRWL022, 1),
    ),
)
def test_PhilipsRemoteCluster_ignore_unknown_buttons(zigpy_device_from_quirk, dev, ep):
    """Ensure PhilipsRemoteCluster ignores unknown buttons."""

    device = zigpy_device_from_quirk(dev)

    cluster = device.endpoints[ep].philips_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.handle_cluster_request(ZCLHeader(), [99, 0, 0, 0, 0])

    assert listener.zha_send_event.call_count == 0


@pytest.mark.parametrize(
    "dev, ep, button, hold_press_type, release_press_type, release_press_type_arg",
    (
        (PhilipsROM001, 1, "on", "hold", "long_release", "hold_release"),
        (
            PhilipsWallSwitch,
            1,
            "left",
            "hold",
            "long_release",
            "hold_release",
        ),
        (
            PhilipsRWLFirstGen,
            2,
            "on",
            "hold",
            "long_release",
            "long_release",
        ),
        (
            PhilipsRWLFirstGen2,
            2,
            "on",
            "hold",
            "long_release",
            "long_release",
        ),
        (
            PhilipsRWL022,
            1,
            "on",
            "hold",
            "long_release",
            "long_release",
        ),
    ),
)
@pytest.mark.parametrize(
    "count",
    (
        (1),
        (2),
        (3),
    ),
)
def test_PhilipsRemoteCluster_long_press(
    zigpy_device_from_quirk,
    dev,
    ep,
    button,
    hold_press_type,
    release_press_type,
    release_press_type_arg,
    count,
):
    """Test PhilipsRemoteCluster button long press logic."""

    device = zigpy_device_from_quirk(dev)

    cluster = device.endpoints[ep].philips_remote_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)
    cluster.button_press_queue = ManuallyFiredButtonPressQueue()

    cluster.handle_cluster_request(ZCLHeader(), [1, 0, 0, 0, 0])
    for i in range(0, count):
        # btn1 long press
        cluster.handle_cluster_request(ZCLHeader(), [1, 0, 1, 0, (i + 1) * 40])

    # btn1 long release
    cluster.handle_cluster_request(ZCLHeader(), [1, 0, 3, 0, count * 40 + 10])
    cluster.button_press_queue.fire()

    assert listener.zha_send_event.call_count == count + 1

    calls = []
    for i in range(0, count):
        calls.append(
            mock.call(
                f"{button}_{hold_press_type}",
                {
                    "button": button,
                    "press_type": hold_press_type,
                    "command_id": None,
                    "duration": (i + 1) * 40,
                    "args": [1, 0, 1, 0, (i + 1) * 40],
                },
            )
        )
    calls.append(
        mock.call(
            f"{button}_{release_press_type}",
            {
                "button": button,
                "press_type": release_press_type_arg,
                "command_id": None,
                "duration": count * 40 + 10,
                "args": [1, 0, 3, 0, count * 40 + 10],
            },
        )
    )

    listener.zha_send_event.assert_has_calls(calls)


@pytest.mark.parametrize(
    "button_presses, result_count",
    (
        (
            [1],
            1,
        ),
        (
            [1, 1],
            2,
        ),
        (
            [1, 1, 3, 3, 3, 2, 2, 2, 2],
            4,
        ),
    ),
)
def test_ButtonPressQueue_presses_without_pause(button_presses, result_count):
    """Test ButtonPressQueue presses without pause in between presses."""

    q = ButtonPressQueue()
    q._ms_threshold = 50
    cb = mock.MagicMock()
    for btn in button_presses:
        q.press(cb, btn)

    # await cluster.button_press_queue._task
    # Instead of awaiting the job, significantly extending the time
    # these tests need, we just abort it and call the callback
    # ourselves.
    assert q._task is not None
    q._task.cancel()
    q._ms_last_click = 0
    q._callback(q._click_counter)
    cb.assert_called_once_with(result_count)


@pytest.mark.parametrize(
    "press_sequence, results",
    (
        (
            # switch buttons within a sequence,
            # new sequence start with different button
            (
                [1, 1, 3, 3],
                [2, 2, 2],
            ),
            (2, 3),
        ),
        (
            # no button switch within a sequence,
            # new sequence with same button
            (
                [1, 1, 1],
                [1],
            ),
            (3, 1),
        ),
    ),
)
async def test_ButtonPressQueue_presses_with_pause(press_sequence, results):
    """Test ButtonPressQueue with pauses in between button press sequences."""

    q = ButtonPressQueue()
    q._ms_threshold = 50
    cb = mock.MagicMock()

    for seq in press_sequence:
        for btn in seq:
            q.press(cb, btn)
        await q._task

    assert cb.call_count == len(results)

    calls = []
    for res in results:
        calls.append(mock.call(res))

    cb.assert_has_calls(calls)


def test_rdm002_triggers():
    """Ensure RDM002 triggers won't break."""

    buttons = [BUTTON_1, BUTTON_2, BUTTON_3, BUTTON_4]
    actions = {
        "remote_button_short_press": "press",
        "remote_button_long_press": "hold",
        "remote_button_short_release": "short_release",
        "remote_button_long_release": "long_release",
        "remote_button_double_press": "double_press",
        "remote_button_triple_press": "triple_press",
        "remote_button_quadruple_press": "quadruple_press",
        "remote_button_quintuple_press": "quintuple_press",
    }

    expected_triggers = {}
    for button in buttons:
        for action, command in actions.items():
            expected_triggers[(action, button)] = {COMMAND: f"{button}_{command}"}

    expected_triggers.update(
        {
            ("remote_button_short_press", "dim_up"): {
                COMMAND: "step_with_on_off",
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 0},
            },
            ("remote_button_short_press", "dim_down"): {
                COMMAND: "step_with_on_off",
                CLUSTER_ID: 8,
                ENDPOINT_ID: 1,
                PARAMS: {"step_mode": 1},
            },
        }
    )

    actual_triggers = PhilipsRDM002.device_automation_triggers

    assert actual_triggers == expected_triggers
