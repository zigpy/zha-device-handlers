"""General quirk tests."""

from __future__ import annotations

import collections
import importlib
import json
from pathlib import Path
from unittest import mock

import pytest
from zigpy import zcl
import zigpy.device
import zigpy.endpoint
import zigpy.profiles
import zigpy.quirks as zq
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types
from zigpy.zcl import foundation
import zigpy.zdo.types

import zhaquirks
from zhaquirks import const
import zhaquirks.bosch.motion
import zhaquirks.centralite.cl_3310S
from zhaquirks.const import (
    ARGS,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_COLOR_TEMP,
    COMMAND_MOVE_ON_OFF,
    COMMAND_MOVE_SATURATION,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    COMMAND_MOVE_TO_SATURATION,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STEP_HUE,
    COMMAND_STEP_ON_OFF,
    COMMAND_STEP_SATURATION,
    COMMAND_STOP,
    COMMAND_STOP_ON_OFF,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
import zhaquirks.konke
import zhaquirks.philips
from zhaquirks.xiaomi import XIAOMI_NODE_DESC
import zhaquirks.xiaomi.aqara.vibration_aq1

zhaquirks.setup()

ALL_QUIRK_CLASSES = []
for manufacturer in zq._DEVICE_REGISTRY._registry.values():
    for model_quirk_list in manufacturer.values():
        for quirk in model_quirk_list:
            if quirk in ALL_QUIRK_CLASSES:
                continue
            ALL_QUIRK_CLASSES.append(quirk)

del quirk, model_quirk_list, manufacturer


ALL_ZIGPY_CLUSTERS = frozenset(zcl.clusters.CLUSTERS_BY_NAME.values())


SIGNATURE_ALLOWED = {
    ENDPOINTS,
    MANUFACTURER,
    MODEL,
    MODELS_INFO,
    NODE_DESCRIPTOR,
}
SIGNATURE_EP_ALLOWED = {
    DEVICE_TYPE,
    INPUT_CLUSTERS,
    PROFILE_ID,
    OUTPUT_CLUSTERS,
}
SIGNATURE_REPLACEMENT_ALLOWED = {
    ENDPOINTS,
    MANUFACTURER,
    MODEL,
    NODE_DESCRIPTOR,
    SKIP_CONFIGURATION,
}


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_quirk_replacements(quirk: CustomDevice) -> None:
    """Test all quirks have a replacement."""

    assert quirk.signature
    assert quirk.replacement

    assert quirk.replacement[ENDPOINTS]


@pytest.fixture
def raw_device() -> zigpy.device.Device:
    """Raw device."""
    app = mock.MagicMock()
    ieee = zigpy.types.EUI64.convert("11:22:33:44:55:66:77:88")
    nwk = 0x1234
    return zigpy.device.Device(app, ieee, nwk)


def test_dev_from_signature_incomplete_sig(raw_device: zigpy.device.Device) -> None:
    """Test device initialization from quirk's based on incomplete signature."""

    class BadSigNoSignature(zhaquirks.QuickInitDevice):
        pass

    with pytest.raises(AssertionError):
        BadSigNoSignature.from_signature(raw_device, model="test_model")

    class BadSigNoModel(zhaquirks.QuickInitDevice):
        signature = {
            MODELS_INFO: [("manufacturer_1", "model_1")],
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
            ENDPOINTS: {
                3: {
                    PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
                    DEVICE_TYPE: zigpy.profiles.zha.DeviceType.LEVEL_CONTROL_SWITCH,
                    INPUT_CLUSTERS: [1, 6],
                    OUTPUT_CLUSTERS: [0x19],
                }
            },
        }

    with pytest.raises(KeyError):
        BadSigNoModel.from_signature(raw_device)

    # require model in method, if none is present in signature
    BadSigNoModel.from_signature(raw_device, model="model_model")

    # require manufacturer, if no signature[MODELS_INFO]
    BadSigNoModel.signature.pop(MODELS_INFO)
    with pytest.raises(KeyError):
        BadSigNoModel.from_signature(raw_device, model="model_model")
    BadSigNoModel.signature[MANUFACTURER] = "some manufacturer"
    BadSigNoModel.from_signature(raw_device, model="model_model")

    ep_sig_complete = {
        PROFILE_ID: zigpy.profiles.zha.PROFILE_ID,
        DEVICE_TYPE: zigpy.profiles.zha.DeviceType.LEVEL_CONTROL_SWITCH,
        INPUT_CLUSTERS: [1, 6],
        OUTPUT_CLUSTERS: [0x19],
    }

    class BadSigIncompleteEp(zhaquirks.QuickInitDevice):
        signature = {
            MANUFACTURER: "manufacturer",
            MODEL: "model",
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
            ENDPOINTS: {3: {**ep_sig_complete}},
        }

    BadSigIncompleteEp.from_signature(raw_device)

    for missing_item in ep_sig_complete:
        incomplete_ep = {**ep_sig_complete}
        incomplete_ep.pop(missing_item)
        BadSigIncompleteEp.signature[ENDPOINTS][3] = incomplete_ep
        with pytest.raises(KeyError):
            BadSigIncompleteEp.from_signature(raw_device)


@pytest.mark.parametrize(
    "quirk_signature",
    (
        {
            ENDPOINTS: {
                1: {
                    PROFILE_ID: 11,
                    DEVICE_TYPE: 22,
                    INPUT_CLUSTERS: [0, 1, 4],
                    OUTPUT_CLUSTERS: [0, 6, 8, 768],
                }
            },
            MANUFACTURER: "manufacturer_3",
            MODEL: "model_3",
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        },
        {
            ENDPOINTS: {
                2: {
                    PROFILE_ID: 33,
                    DEVICE_TYPE: 44,
                    INPUT_CLUSTERS: [0, 0x0201, 0x0402],
                    OUTPUT_CLUSTERS: [0x0019, 0x0401],
                },
                5: {
                    PROFILE_ID: 55,
                    DEVICE_TYPE: 66,
                    INPUT_CLUSTERS: [0, 6, 8],
                    OUTPUT_CLUSTERS: [0x0019, 0x0500],
                },
            },
            MANUFACTURER: "manufacturer_4",
            MODEL: "model_4",
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        },
        {
            ENDPOINTS: {
                2: {
                    PROFILE_ID: 33,
                    DEVICE_TYPE: 44,
                    INPUT_CLUSTERS: [0, 0x0201, 0x0402],
                    OUTPUT_CLUSTERS: [0x0019, 0x0401],
                },
                5: {
                    PROFILE_ID: 55,
                    DEVICE_TYPE: 66,
                    INPUT_CLUSTERS: [0, 6, 8],
                    OUTPUT_CLUSTERS: [0x0019, 0x0500],
                },
            },
            MODELS_INFO: (("LUMI", "model_4"),),
            MODEL: "model_4",
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        },
        {
            ENDPOINTS: {
                1: {
                    "profile_id": 260,
                    "device_type": 0x0100,
                    INPUT_CLUSTERS: [
                        0x0000,
                        0x0003,
                        0x0004,
                        0x0005,
                        0x0006,
                        0x0702,
                        0x0B05,
                    ],
                    OUTPUT_CLUSTERS: [0x000A, 0x0019],
                },
                2: {
                    "profile_id": 260,
                    "device_type": 0x0103,
                    INPUT_CLUSTERS: [0x0000, 0x0003, 0x0B05],
                    OUTPUT_CLUSTERS: [0x0003, 0x0006],
                },
            },
            MANUFACTURER: "manufacturer 5",
            MODEL: "model 5",
            NODE_DESCRIPTOR: XIAOMI_NODE_DESC,
        },
    ),
)
def test_dev_from_signature(
    raw_device: zigpy.device.Device, quirk_signature: dict
) -> None:
    """Test device initialization from quirk's based on signature."""

    class QuirkDevice(zhaquirks.QuickInitDevice):
        signature = quirk_signature

    device = QuirkDevice.from_signature(raw_device)
    assert device.status == zigpy.device.Status.ENDPOINTS_INIT
    if MANUFACTURER in quirk_signature:
        assert device.manufacturer == quirk_signature[MANUFACTURER]
    else:
        assert device.manufacturer == "LUMI"
    assert device.model == quirk_signature[MODEL]

    ep_signature = quirk_signature[ENDPOINTS]
    assert len(device.endpoints) == len(ep_signature) + 1  # ZDO endpoint
    for ep_id, ep_data in ep_signature.items():
        assert ep_id in device.endpoints
        ep = device.endpoints[ep_id]
        assert ep.status == zigpy.endpoint.Status.ZDO_INIT
        assert ep.profile_id == ep_data[PROFILE_ID]
        assert ep.device_type == ep_data[DEVICE_TYPE]
        assert list(ep.in_clusters) == ep_data[INPUT_CLUSTERS]
        assert list(ep.out_clusters) == ep_data[OUTPUT_CLUSTERS]


@pytest.mark.parametrize(
    "quirk",
    (q for q in ALL_QUIRK_CLASSES if issubclass(q, zhaquirks.QuickInitDevice)),
)
def test_quirk_quickinit(quirk: zigpy.quirks.CustomDevice) -> None:
    """Make sure signature in QuickInit Devices have all required attributes."""

    if not issubclass(quirk, zhaquirks.QuickInitDevice):
        return

    assert quirk.signature.get(MODELS_INFO) or quirk.signature[MANUFACTURER]
    assert quirk.signature[NODE_DESCRIPTOR]
    assert quirk.signature[ENDPOINTS]
    for ep_id, ep_data in quirk.signature[ENDPOINTS].items():
        assert ep_id
        assert PROFILE_ID in ep_data
        assert DEVICE_TYPE in ep_data
        assert isinstance(ep_data[INPUT_CLUSTERS], list)
        assert isinstance(ep_data[OUTPUT_CLUSTERS], list)


@pytest.mark.parametrize(
    "quirk",
    [
        quirk_cls
        for quirk_cls in ALL_QUIRK_CLASSES
        if quirk_cls
        not in (
            # Some devices have empty model info:
            zhaquirks.tuya.ty0201.TuyaTempHumiditySensorNoModel,
        )
    ],
)
def test_signature(quirk: CustomDevice) -> None:
    """Make sure signature look sane for all custom devices."""

    def _check_range(cluster: zcl.Cluster) -> bool:
        for range in zcl.Cluster._registry_range:
            if range[0] <= cluster <= range[1]:
                return True
        return False

    # enforce new style of signature
    assert ENDPOINTS in quirk.signature
    numeric = [eid for eid in quirk.signature if isinstance(eid, int)]
    assert not numeric
    assert set(quirk.signature).issubset(SIGNATURE_ALLOWED)
    models_info = quirk.signature.get(MODELS_INFO)
    if models_info is not None:
        for manufacturer, model in models_info:
            if manufacturer is not None:
                assert isinstance(manufacturer, str)
                assert manufacturer
            if model is not None:
                assert isinstance(model, str)
                assert model

    for m_m in (MANUFACTURER, MODEL):
        value = quirk.signature.get(m_m)
        if value is not None:
            assert isinstance(value, str)
            assert value

    # Check that the signature data is OK
    ep_signature = quirk.signature[ENDPOINTS]
    for ep_id, ep_data in ep_signature.items():
        assert isinstance(ep_id, int)
        assert 0x01 <= ep_id <= 0xFE
        assert set(ep_data).issubset(SIGNATURE_EP_ALLOWED)
        for sig_attr in (DEVICE_TYPE, PROFILE_ID):
            value = ep_data.get(sig_attr)
            if value is not None:
                assert isinstance(value, int)
                assert 0x0000 <= value <= 0xFFFF
        for clusters_type in (INPUT_CLUSTERS, OUTPUT_CLUSTERS):
            clusters = ep_data.get(clusters_type)
            if clusters is not None:
                assert all(isinstance(cluster_id, int) for cluster_id in clusters)
                assert all(0 <= cluster_id <= 0xFFFF for cluster_id in clusters)

        for m_m in (MANUFACTURER, MODEL):
            value = ep_data.get(m_m)
            if value is not None:
                assert isinstance(value, str)
                assert value

    # Check that the replacement data is OK
    assert set(quirk.replacement).issubset(SIGNATURE_REPLACEMENT_ALLOWED)
    for ep_id, ep_data in quirk.replacement[ENDPOINTS].items():
        assert isinstance(ep_id, int)
        assert 0x01 <= ep_id <= 0xFE
        assert set(ep_data).issubset(SIGNATURE_EP_ALLOWED)

        for sig_attr in (DEVICE_TYPE, PROFILE_ID):
            value = ep_data.get(sig_attr)
            if value is not None:
                assert isinstance(value, int)
                assert 0x0000 <= value <= 0xFFFF

        for clusters_type in (INPUT_CLUSTERS, OUTPUT_CLUSTERS):
            clusters = ep_data.get(clusters_type, [])
            for cluster in clusters:
                if clusters is not None:
                    if isinstance(cluster, int):
                        assert cluster in zcl.Cluster._registry or _check_range(cluster)
                    else:
                        assert issubclass(cluster, zcl.Cluster)

        for m_m in (MANUFACTURER, MODEL):
            value = ep_data.get(m_m)
            if value is not None:
                assert isinstance(value, str)
                assert value

        node_desc = ep_data.get(NODE_DESCRIPTOR)
        if node_desc is not None:
            assert isinstance(node_desc, zigpy.zdo.types.NodeDescriptor)


@pytest.mark.parametrize(
    "quirk",
    [
        quirk_cls
        for quirk_cls in ALL_QUIRK_CLASSES
        if quirk_cls
        not in (
            # Some quirks do not yet have model info:
            zhaquirks.xbee.xbee_io.XBeeSensor,
            zhaquirks.xbee.xbee3_io.XBee3Sensor,
            zhaquirks.tuya.ts0201.MoesTemperatureHumidtySensorWithScreen,
            zhaquirks.smartthings.tag_v4.SmartThingsTagV4,
            zhaquirks.smartthings.multi.SmartthingsMultiPurposeSensor,
            zhaquirks.netvox.z308e3ed.Z308E3ED,
            zhaquirks.gledopto.soposhgu10.SoposhGU10,
        )
    ],
)
def test_signature_model_info_given(quirk: CustomDevice) -> None:
    """Verify that quirks have MODELS_INFO, MODEL or MANUFACTURER in their signature."""

    if (
        not quirk.signature.get(MODELS_INFO)
        and not quirk.signature.get(MODEL)
        and not quirk.signature.get(MANUFACTURER)
    ):
        pytest.fail(
            f"Quirk {quirk} does not have MODELS_INFO, MODEL or MANUFACTURER in its signature. "
            f"At least one of these is required."
        )


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_quirk_importable(quirk: CustomDevice) -> None:
    """Ensure all quirks can be imported with a normal Python `import` statement."""

    path = f"{quirk.__module__}.{quirk.__name__}"
    assert all(
        m and m.isidentifier() for m in path.split(".")
    ), f"{path} is not importable"


def test_quirk_loading_error(tmp_path: Path, caplog) -> None:
    """Ensure quirks silently fail to load."""

    custom_quirks = tmp_path / "custom_zha_quirks"
    custom_quirks.mkdir()

    (custom_quirks / "__init__.py").touch()

    (custom_quirks / "bosch").mkdir()
    (custom_quirks / "bosch/__init__.py").touch()

    # Syntax errors are swallowed
    (custom_quirks / "bosch/custom_quirk.py").write_text("1/")

    caplog.clear()
    zhaquirks.setup(custom_quirks_path=str(custom_quirks))
    assert (
        "Unexpected exception importing custom quirk 'bosch.custom_quirk'"
        in caplog.text
    )
    assert "SyntaxError" in caplog.text

    # And so are import errors
    (custom_quirks / "bosch/custom_quirk.py").write_text("from os import foobarbaz7")

    caplog.clear()
    zhaquirks.setup(custom_quirks_path=str(custom_quirks))
    assert (
        "Unexpected exception importing custom quirk 'bosch.custom_quirk'"
        in caplog.text
    )
    assert "cannot import name 'foobarbaz7' from 'os'" in caplog.text


def test_custom_quirk_loading(
    zigpy_device_from_quirk: CustomDevice, tmp_path: Path
) -> None:
    """Make sure custom quirks take priority over regular quirks."""

    device = zigpy_device_from_quirk(
        zhaquirks.bosch.motion.ISWZPR1WP13, apply_quirk=False
    )
    assert type(device) is zigpy.device.Device

    # Make sure our target quirk will load after we re-setup zhaquirks
    zhaquirks.setup()
    assert type(zq.get_device(device)) is zhaquirks.bosch.motion.ISWZPR1WP13

    custom_quirks = tmp_path / "custom_zha_quirks"
    custom_quirks.mkdir()

    # Make our own custom quirk
    (custom_quirks / "__init__.py").touch()

    (custom_quirks / "bosch").mkdir()
    (custom_quirks / "bosch/__init__.py").touch()
    (custom_quirks / "bosch/custom_quirk.py").write_text(
        '''
"""Device handler for Bosch motion sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from zhaquirks.bosch import BOSCH
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

class TestReplacementISWZPR1WP13(CustomDevice):
    """Custom device representing Bosch motion sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1026, 1280, 32, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: [(BOSCH, "ISW-ZPR1-WP13")],
        ENDPOINTS: {
            5: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
'''
    )

    zhaquirks.setup(custom_quirks_path=str(custom_quirks))

    assert not isinstance(zq.get_device(device), zhaquirks.bosch.motion.ISWZPR1WP13)
    assert type(zq.get_device(device)).__name__ == "TestReplacementISWZPR1WP13"


def test_zigpy_custom_cluster_pollution() -> None:
    """Ensure all quirks subclass `CustomCluster`."""
    non_zigpy_clusters = {
        cluster
        for cluster in zcl.Cluster._registry.values()
        if not cluster.__module__.startswith("zigpy.")
    }

    if non_zigpy_clusters:
        raise RuntimeError(
            f"Custom clusters must subclass `CustomCluster`: {non_zigpy_clusters}"
        )


@pytest.mark.parametrize(
    "module_name",
    sorted({q.__module__ for q in ALL_QUIRK_CLASSES}),
)
def test_no_module_level_device_automation_triggers(module_name: str) -> None:
    """Ensure no quirk module has a module-level `device_automation_triggers` dict."""

    mod = importlib.import_module(module_name)
    assert not hasattr(mod, "device_automation_triggers")


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_migrated_lighting_automation_triggers(quirk: CustomDevice) -> None:
    """Ensure quirks with lighting or level control clusters are using PARAMS."""

    if not hasattr(quirk, "device_automation_triggers"):
        return

    for event in quirk.device_automation_triggers.values():
        if COMMAND not in event:
            continue

        command = event[COMMAND]

        # We only consider lighting commands for now
        if command in (
            COMMAND_MOVE_SATURATION,
            COMMAND_MOVE_TO_SATURATION,
            COMMAND_MOVE_COLOR_TEMP,
            COMMAND_STEP_HUE,
            COMMAND_STEP_SATURATION,
            COMMAND_STEP_COLOR_TEMP,
        ):
            cluster = zcl.clusters.lighting.Color
        elif command in (
            COMMAND_MOVE,
            COMMAND_MOVE_ON_OFF,
            COMMAND_STEP,
            COMMAND_STEP_ON_OFF,
            COMMAND_STOP,
            COMMAND_STOP_ON_OFF,
            COMMAND_MOVE_TO_LEVEL_ON_OFF,
        ):
            cluster = zcl.clusters.general.LevelControl
        else:
            continue

        if ARGS in event:
            raise ValueError(f"ARGS should be migrated to PARAMS: {command!r}")
        elif PARAMS not in event:
            continue

        schema = cluster.commands_by_name[command].schema
        schema(**event[PARAMS])


KNOWN_DUPLICATE_TRIGGERS = {
    zhaquirks.aurora.aurora_dimmer.AuroraDimmerBatteryPowered: [
        [
            # XXX: why is this constant defined in the module?
            (zhaquirks.aurora.aurora_dimmer.COLOR_UP, const.RIGHT),
            (zhaquirks.aurora.aurora_dimmer.COLOR_UP, const.LEFT),
        ],
        [
            (zhaquirks.aurora.aurora_dimmer.COLOR_DOWN, const.RIGHT),
            (zhaquirks.aurora.aurora_dimmer.COLOR_DOWN, const.LEFT),
        ],
    ],
    zhaquirks.paulmann.fourbtnremote.PaulmannRemote4Btn: [
        [
            (const.LONG_RELEASE, const.BUTTON_1),
            (const.LONG_RELEASE, const.BUTTON_2),
        ],
        [
            (const.LONG_RELEASE, const.BUTTON_3),
            (const.LONG_RELEASE, const.BUTTON_4),
        ],
    ],
    zhaquirks.thirdreality.button.Button: [
        [
            (const.LONG_PRESS, const.LONG_PRESS),
            (const.LONG_RELEASE, const.LONG_RELEASE),
        ]
    ],
}


# XXX: Test does not handle v2 quirks
@pytest.mark.parametrize(
    "quirk",
    [q for q in ALL_QUIRK_CLASSES if getattr(q, "device_automation_triggers", None)],
)
def test_quirk_device_automation_triggers_unique(quirk):
    """Ensure all quirks have unique device automation triggers."""

    events = collections.defaultdict(list)

    for trigger, event in quirk.device_automation_triggers.items():
        # XXX: Dictionary objects are not hashable
        frozen_event = json.dumps(event, sort_keys=True)
        events[frozen_event].append((trigger, event))

    for triggers_and_events in events.values():
        triggers = [trigger for trigger, _ in triggers_and_events]

        if len(triggers_and_events) > 1:
            if (
                quirk in KNOWN_DUPLICATE_TRIGGERS
                and triggers in KNOWN_DUPLICATE_TRIGGERS[quirk]
            ):
                fail_func = pytest.xfail
            else:
                fail_func = pytest.fail

            triggers_text = "\n".join(
                [f" * {event} <- {trigger}" for trigger, event in triggers_and_events]
            )
            fail_func(f"Triggers are not unique for {quirk}:\n{triggers_text}")


@pytest.mark.parametrize(
    "quirk",
    [
        quirk_cls
        for quirk_cls in ALL_QUIRK_CLASSES
        if quirk_cls
        not in (
            zhaquirks.xbee.xbee_io.XBeeSensor,
            zhaquirks.xbee.xbee3_io.XBee3Sensor,
        )
    ],
)
def test_attributes_updated_not_replaced(quirk: CustomDevice) -> None:
    """Verify no quirks subclass a ZCL cluster but delete its attributes list."""

    base_cluster_attrs_name = {}
    base_cluster_attrs_id = {}

    for cluster in zcl.clusters.CLUSTERS_BY_NAME.values():
        assert cluster.ep_attribute not in base_cluster_attrs_name
        base_cluster_attrs_name[cluster.ep_attribute] = set(
            cluster.attributes_by_name.keys()
        )
        base_cluster_attrs_id[cluster.cluster_id] = set(
            cluster.attributes_by_name.keys()
        )

    for ep_data in quirk.replacement[ENDPOINTS].values():
        for cluster in ep_data.get(INPUT_CLUSTERS, []) + ep_data.get(
            OUTPUT_CLUSTERS, []
        ):
            if (
                isinstance(cluster, int)
                or not issubclass(cluster, zcl.Cluster)
                or cluster in ALL_ZIGPY_CLUSTERS
            ):
                continue

            assert issubclass(cluster, zigpy.quirks.CustomCluster)

            # Check if attributes match based on cluster endpoint attribute
            if not (
                base_cluster_attrs_name.get(cluster.ep_attribute, set())
                <= set(cluster.attributes_by_name.keys())
            ):
                missing_attrs = base_cluster_attrs_name[cluster.ep_attribute] - set(
                    cluster.attributes_by_name.keys()
                )

                # A few are expected to fail and are handled by ZHA
                if cluster not in (
                    zhaquirks.centralite.cl_3310S.SmartthingsRelativeHumidityCluster,
                ):
                    pytest.fail(
                        f"Cluster {cluster} with endpoint name {cluster.ep_attribute!r}"
                        f" does not contain all named attributes: {missing_attrs}"
                    )

            # Check if attributes match based on cluster ID
            if not (
                base_cluster_attrs_id.get(cluster.cluster_id, set())
                <= set(cluster.attributes_by_name.keys())
            ):
                missing_attrs = base_cluster_attrs_id[cluster.cluster_id] - set(
                    cluster.attributes_by_name.keys()
                )

                # A few are expected to fail and are handled by ZHA
                if cluster not in (
                    zhaquirks.konke.KonkeOnOffCluster,
                    zhaquirks.philips.PhilipsOccupancySensing,
                    zhaquirks.xiaomi.aqara.vibration_aq1.VibrationAQ1.MultistateInputCluster,
                ):
                    pytest.fail(
                        f"Cluster {cluster} with endpoint ID 0x{cluster.cluster_id:04X}"
                        f" does not contain all named attributes: {missing_attrs}"
                    )

            base_clusters = set(cluster.__mro__) & ALL_ZIGPY_CLUSTERS

            # Completely custom cluster
            if len(base_clusters) == 0:
                continue
            elif len(base_clusters) > 1:
                pytest.fail(f"Cluster has more than one zigpy base class: {cluster}")

            base_cluster = list(base_clusters)[0]

            # Ensure the attribute IDs are extended
            base_attr_ids = set(base_cluster.attributes)
            quirk_attr_ids = set(cluster.attributes)

            if not base_attr_ids <= quirk_attr_ids:
                pytest.fail(
                    f"Cluster {cluster} deletes parent class's attributes instead of"
                    f" extending them: {base_attr_ids - quirk_attr_ids}"
                )

            # Ensure the attribute names are extended
            base_attr_names = {a.name for a in base_cluster.attributes.values()}
            quirk_attr_names = {a.name for a in cluster.attributes.values()}

            if not base_attr_names <= quirk_attr_names:
                pytest.fail(
                    f"Cluster {cluster} deletes parent class's attributes instead of"
                    f" extending them: {base_attr_names - quirk_attr_names}"
                )


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_no_duplicate_clusters(quirk: CustomDevice) -> None:
    """Verify no quirks contain clusters with duplicate cluster ids in the replacement."""

    def check_for_duplicate_cluster_ids(clusters) -> None:
        used_cluster_ids = set()

        for cluster in clusters:
            if isinstance(cluster, int):
                cluster_id = cluster
            else:
                cluster_id = cluster.cluster_id

            if cluster_id in used_cluster_ids:
                pytest.fail(
                    f"Cluster ID 0x{cluster_id:04X} is used more than once in the"
                    f" replacement for endpoint {ep_id} in {quirk}"
                )
            used_cluster_ids.add(cluster_id)

    for ep_id, ep_data in quirk.replacement[ENDPOINTS].items():  # noqa: B007
        check_for_duplicate_cluster_ids(ep_data.get(INPUT_CLUSTERS, []))
        check_for_duplicate_cluster_ids(ep_data.get(OUTPUT_CLUSTERS, []))


async def test_local_data_cluster(zigpy_device_from_v2_quirk) -> None:
    """Ensure reading attributes from a LocalDataCluster works as expected."""

    class TestLocalCluster(zhaquirks.LocalDataCluster):
        """Test cluster."""

        cluster_id = 0x1234
        _CONSTANT_ATTRIBUTES = {1: 10}
        _VALID_ATTRIBUTES = [2]

    (
        QuirkBuilder("manufacturer-local-test", "model")
        .adds(TestLocalCluster)
        .add_to_registry()
    )
    device = zigpy_device_from_v2_quirk("manufacturer-local-test", "model")
    assert isinstance(device.endpoints[1].in_clusters[0x1234], TestLocalCluster)

    # reading invalid attribute return unsupported attribute
    assert await device.endpoints[1].in_clusters[0x1234].read_attributes([0]) == (
        {},
        {0: foundation.Status.UNSUPPORTED_ATTRIBUTE},
    )

    # reading constant attribute works
    assert await device.endpoints[1].in_clusters[0x1234].read_attributes([1]) == (
        {1: 10},
        {},
    )

    # reading valid attribute returns None with success status
    assert await device.endpoints[1].in_clusters[0x1234].read_attributes([2]) == (
        {2: None},
        {},
    )
