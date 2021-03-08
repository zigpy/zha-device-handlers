"""General quirk tests."""

from unittest import mock

import pytest
import zigpy.device
import zigpy.endpoint
import zigpy.profiles
import zigpy.quirks as zq
import zigpy.types
import zigpy.zcl as zcl
import zigpy.zdo.types

import zhaquirks
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MANUFACTURER,
    MODEL,
    MODELS_INFO,
    NODE_DESCRIPTOR,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.xiaomi import XIAOMI_NODE_DESC

zhaquirks.setup()

ALL_QUIRK_CLASSES = []
for manufacturer in zq._DEVICE_REGISTRY._registry.values():
    for model_quirk_list in manufacturer.values():
        for quirk in model_quirk_list:
            if quirk in ALL_QUIRK_CLASSES:
                continue
            ALL_QUIRK_CLASSES.append(quirk)

del quirk, model_quirk_list, manufacturer


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
def test_quirk_replacements(quirk):
    """Test all quirks have a replacement."""

    assert quirk.signature
    assert quirk.replacement

    assert quirk.replacement[ENDPOINTS]


@pytest.fixture
def raw_device():
    """Raw device."""
    app = mock.MagicMock()
    ieee = zigpy.types.EUI64.convert("11:22:33:44:55:66:77:88")
    nwk = 0x1234
    return zigpy.device.Device(app, ieee, nwk)


def test_dev_from_signature_incomplete_sig(raw_device):
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
def test_dev_from_signature(raw_device, quirk_signature):
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
        assert [cluster_id for cluster_id in ep.in_clusters] == ep_data[INPUT_CLUSTERS]
        assert [cluster_id for cluster_id in ep.out_clusters] == ep_data[
            OUTPUT_CLUSTERS
        ]


@pytest.mark.parametrize(
    "quirk", (q for q in ALL_QUIRK_CLASSES if issubclass(q, zhaquirks.QuickInitDevice))
)
def test_quirk_quickinit(quirk):
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


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_signature(quirk):
    """Make sure signature look sane for all custom devices."""

    def _check_range(cluster):
        for range in zcl.Cluster._registry_range.keys():
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
                assert all((isinstance(cluster_id, int) for cluster_id in clusters))
                assert all((0 <= cluster_id <= 0xFFFF for cluster_id in clusters))

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


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_quirk_importable(quirk):
    """Ensure all quirks can be imported with a normal Python `import` statement."""

    path = f"{quirk.__module__}.{quirk.__name__}"
    assert all(
        [m and m.isidentifier() for m in path.split(".")]
    ), f"{path} is not importable"


def test_quirk_loading_error(tmp_path):
    """Ensure quirks do not silently fail to load."""

    custom_quirks = tmp_path / "custom_zha_quirks"
    custom_quirks.mkdir()

    (custom_quirks / "__init__.py").touch()

    (custom_quirks / "bosch").mkdir()
    (custom_quirks / "bosch/__init__.py").touch()
    # (custom_quirks / "bosch/custom_quirk.py").write_text('1/0')

    # Syntax errors are not swallowed
    (custom_quirks / "bosch/custom_quirk.py").write_text("1/")

    with pytest.raises(SyntaxError):
        zhaquirks.setup({zhaquirks.CUSTOM_QUIRKS_PATH: str(custom_quirks)})

    # Nor are import errors
    (custom_quirks / "bosch/custom_quirk.py").write_text("from os import foobarbaz7")

    with pytest.raises(ImportError):
        zhaquirks.setup({zhaquirks.CUSTOM_QUIRKS_PATH: str(custom_quirks)})


def test_custom_quirk_loading(zigpy_device_from_quirk, tmp_path):
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

    zhaquirks.setup({zhaquirks.CUSTOM_QUIRKS_PATH: str(custom_quirks)})

    assert not isinstance(zq.get_device(device), zhaquirks.bosch.motion.ISWZPR1WP13)
    assert type(zq.get_device(device)).__name__ == "TestReplacementISWZPR1WP13"
