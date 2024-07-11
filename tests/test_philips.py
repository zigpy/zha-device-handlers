"""Tests for Philips RDM001 and RDM004 quirks."""
import pytest

from tests.common import ClusterListener

import zhaquirks
from zhaquirks.philips.rdm001 import PhilipsRDM001

zhaquirks.setup()

@pytest.mark.parametrize("manufacturer,model",
    [
        ("Philips", "RDM001"),
        ("Signify Netherlands B.V.", "RDM001"),
    ],
)

def test_RDM001_signature(
    manufacturer: str, model: str, assert_signature_matches_quirk
) -> None:
    """Test that the signature of all supported RDM devices is matched to its quirk."""
    signature = {
        "node_descriptor": "<SimpleDescriptor endpoint=1 profile=260 device_type=2080 device_version=1 input_clusters=[0, 1, 3, 64512] output_clusters=[3, 4, 6, 8, 25]>",
        "endpoints": {
            "1": {
                "profile_id": 260,
                "device_type": "0x820",
                "in_clusters": [
                    "0x0",
                    "0x1",
                    "0x3",
                    "0xFC00",
                ],
                "out_clusters": ["0x3", "0x4", "0x6", "0x8", "0x19"],
            }
        },
        "manufacturer": manufacturer,
        "model": model,
        "class": "zhaquirks.philips.rdm001.PhilipsRDM001",
    }

    assert_signature_matches_quirk(
        zhaquirks.philips.rdm001.PhilipsRDM001, signature
    ) 
