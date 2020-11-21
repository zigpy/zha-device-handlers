"""General quirk tests."""

from unittest import mock

import pytest
import zigpy.device
import zigpy.endpoint
import zigpy.profiles
import zigpy.quirks as zq
import zigpy.types

import zhaquirks  # noqa: F401, E402
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
)
from zhaquirks.xiaomi import XIAOMI_NODE_DESC

ALL_QUIRK_CLASSES = [
    quirk
    for manufacturer in zq._DEVICE_REGISTRY._registry.values()
    for model in manufacturer.values()
    for quirk in model
]


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


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
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
