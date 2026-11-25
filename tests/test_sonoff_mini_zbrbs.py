"""Tests for mini_zbrbs.py."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl.foundation import DataTypeId

# 这个测试文件放在脚本旁边，依赖仓库里的 zha/zigpy 源码，这里把路径准备好。
for _parent in Path(__file__).resolve().parents:
    _candidate = _parent / "code" / "zha"
    if (_candidate / "zha-device-handlers").is_dir():
        for _path in (
            _candidate / "zha-device-handlers",
            _candidate / "zha",
            _candidate / "zigpy",
        ):
            if str(_path) not in sys.path:
                sys.path.insert(0, str(_path))
        break

import zhaquirks  # noqa: E402
from zhaquirks.clusters import CustomCluster  # noqa: E402


class BuilderSpy:
    """记录脚本里的 QuirkBuilder 链式调用，避免真的重复注册 quirk。"""

    instances = []

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.calls = []
        self.instances.append(self)

    def _record(self, method, *args, **kwargs):
        self.calls.append((method, args, kwargs))
        return self

    def replaces(self, *args, **kwargs):
        return self._record("replaces", *args, **kwargs)

    def enum(self, *args, **kwargs):
        return self._record("enum", *args, **kwargs)

    def switch(self, *args, **kwargs):
        return self._record("switch", *args, **kwargs)

    def write_attr_button(self, *args, **kwargs):
        return self._record("write_attr_button", *args, **kwargs)

    def add_to_registry(self, *args, **kwargs):
        return self._record("add_to_registry", *args, **kwargs)


class EntityPlatformStub:
    SENSOR = mock.sentinel.entity_platform_sensor


class EntityTypeStub:
    DIAGNOSTIC = mock.sentinel.entity_type_diagnostic


# 用假的 builder 模块加载脚本：既能检查链式配置，又不会污染真实 quirk registry。
builder_stub = types.ModuleType("zhaquirks.builder")
builder_stub.EntityPlatform = EntityPlatformStub
builder_stub.EntityType = EntityTypeStub
builder_stub.QuirkBuilder = BuilderSpy
sys.modules["zhaquirks.builder"] = builder_stub
zhaquirks.builder = builder_stub

SCRIPT_PATH = Path(__file__).with_name("mini_zbrbs.py")
MODULE_NAME = "_mini_zbrbs_under_test"


def _load_module():
    BuilderSpy.instances.clear()
    sys.modules.pop(MODULE_NAME, None)

    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


mini_zbrbs = _load_module()


def _one_builder_call(method, first_arg):
    assert len(BuilderSpy.instances) == 1
    calls = [
        call
        for call in BuilderSpy.instances[0].calls
        if call[0] == method and call[1] and call[1][0] == first_arg
    ]
    assert len(calls) == 1
    return calls[0]


@pytest.fixture
def cluster():
    return mini_zbrbs.SonoffCluster(mock.Mock(), is_server=True)


def _base_write_mock(result=None):
    return mock.patch.object(
        CustomCluster,
        "write_attributes",
        new_callable=mock.AsyncMock,
        return_value=result if result is not None else [[mock.sentinel.write_ok]],
    )


def test_quirk_metadata():
    assert mini_zbrbs.QUIRK_METADATA == {
        "name": "SONOFF MINI-ZBRBS",
        "model": "MINI-ZBRBS",
        "version": "1.0",
        "update_date": "2026-11-24",
        "author": "SONOFF",
        "manufacturer": "SONOFF",
        "description": (
            "SONOFF MINI-ZBRBS - Window covering roller shutter motor controller."
        ),
    }


@pytest.mark.parametrize(
    ("enum_class", "expected"),
    [
        (
            mini_zbrbs.SonoffCoverCalibrationStatus,
            {"not_calibrated": 0x00, "calibrated": 0x01},
        ),
        (
            mini_zbrbs.SonoffMotorState,
            {"stopped": 0x00, "opening": 0x01, "closing": 0x02},
        ),
        (
            mini_zbrbs.SonoffExternalSwitchTriggerType,
            {"edge_trigger": 0x00, "pulse_trigger": 0x01},
        ),
    ],
)
def test_enum_values(enum_class, expected):
    for name, value in expected.items():
        assert int(getattr(enum_class, name)) == value


def test_sonoff_cluster_id():
    assert mini_zbrbs.SonoffCluster.cluster_id == 0xFC11


@pytest.mark.parametrize(
    ("name", "attr_id", "attr_type"),
    [
        (
            "external_trigger_mode",
            0x0016,
            mini_zbrbs.SonoffExternalSwitchTriggerType,
        ),
        ("single_switch_mode", 0x6038, t.Bool),
        ("cover_calibrated", 0x5012, mini_zbrbs.SonoffCoverCalibrationStatus),
        ("motor_state", 0x5013, mini_zbrbs.SonoffMotorState),
        ("attrib_0010", 0x0010, t.uint32_t),
        ("attrib_0012", 0x0012, t.int16s),
        ("limits_calibration", 0x5001, t.uint8_t),
        ("cluster_revision", 0xFFFD, t.uint16_t),
    ],
)
def test_attribute_definitions(name, attr_id, attr_type):
    attr_def = getattr(mini_zbrbs.SonoffCluster.AttributeDefs, name)

    assert attr_def.id == attr_id
    assert attr_def.type is attr_type
    assert attr_def.manufacturer_code is None


@pytest.mark.parametrize(
    ("name", "zcl_type"),
    [
        ("external_trigger_mode", DataTypeId.uint8),
        ("single_switch_mode", DataTypeId.bool_),
        ("cover_calibrated", DataTypeId.uint8),
        ("motor_state", DataTypeId.uint8),
    ],
)
def test_explicit_zcl_types(name, zcl_type):
    assert getattr(mini_zbrbs.SonoffCluster.AttributeDefs, name).zcl_type == zcl_type


@pytest.mark.parametrize("name", ["motor_state", "attrib_0010"])
def test_read_only_attributes(name):
    access = getattr(mini_zbrbs.SonoffCluster.AttributeDefs, name).access
    assert access.name == "Read"


def test_builder_configuration():
    assert len(BuilderSpy.instances) == 1
    builder = BuilderSpy.instances[0]

    assert builder.init_args == ("SONOFF", "MINI-ZBRBS")
    assert builder.init_kwargs == {}
    assert [call[0] for call in builder.calls] == [
        "replaces",
        "enum",
        "switch",
        "enum",
        "enum",
        "write_attr_button",
        "add_to_registry",
    ]

    assert _one_builder_call("replaces", mini_zbrbs.SonoffCluster)[1] == (
        mini_zbrbs.SonoffCluster,
    )

    external = _one_builder_call("enum", "external_trigger_mode")
    assert external[1] == (
        "external_trigger_mode",
        mini_zbrbs.SonoffExternalSwitchTriggerType,
        0xFC11,
    )
    assert external[2] == {
        "translation_key": "external_trigger_mode",
        "fallback_name": "External trigger mode",
    }

    single = _one_builder_call("switch", "single_switch_mode")
    assert single[1] == ("single_switch_mode", 0xFC11)
    assert single[2] == {
        "translation_key": "single_switch_mode",
        "fallback_name": "Single switch mode",
    }

    calibrated = _one_builder_call("enum", "cover_calibrated")
    assert calibrated[2] == {
        "entity_platform": EntityPlatformStub.SENSOR,
        "entity_type": EntityTypeStub.DIAGNOSTIC,
        "translation_key": "calibrated",
        "fallback_name": "Calibrated",
    }

    motor = _one_builder_call("enum", "motor_state")
    assert motor[2] == {
        "entity_platform": EntityPlatformStub.SENSOR,
        "entity_type": EntityTypeStub.DIAGNOSTIC,
        "initially_disabled": True,
        "translation_key": "motor_state",
        "fallback_name": "Motor state",
    }

    limits = _one_builder_call("write_attr_button", "limits_calibration")
    assert limits[1] == ("limits_calibration", 2, 0xFC11)
    assert limits[2] == {
        "translation_key": "configure_limits",
        "fallback_name": "Configure cover limits",
    }

    registered = [call for call in builder.calls if call[0] == "add_to_registry"]
    assert registered == [("add_to_registry", (), {})]


def test_write_attributes_normalizes_names_and_preserves_manufacturer(cluster):
    attributes = {
        "single_switch_mode": False,
        mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
            mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
        ),
        "unknown_attribute": 7,
    }

    with _base_write_mock() as write:
        result = asyncio.run(cluster.write_attributes(attributes, manufacturer=0x1234))

    assert result == [[mock.sentinel.write_ok]]
    write.assert_awaited_once_with(
        {
            0x6038: False,
            0x0016: mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger,
            "unknown_attribute": 7,
        },
        0x1234,
    )


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
            },
        ),
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.edge_trigger
                ),
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: True,
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
            },
        ),
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.edge_trigger
                ),
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.edge_trigger
                ),
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: False,
            },
        ),
        (
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: False,
            },
            {
                mini_zbrbs.SonoffCluster.AttributeDefs.external_trigger_mode.id: (
                    mini_zbrbs.SonoffExternalSwitchTriggerType.pulse_trigger
                ),
                mini_zbrbs.SonoffCluster.AttributeDefs.single_switch_mode.id: False,
            },
        ),
    ],
)
def test_write_attributes_trigger_mode_rules(cluster, attributes, expected):
    with _base_write_mock() as write:
        asyncio.run(cluster.write_attributes(attributes))

    write.assert_awaited_once_with(expected, None)
