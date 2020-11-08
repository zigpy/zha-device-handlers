"""General quirk tests."""

import pytest
import zigpy.quirks as zq

import zhaquirks  # noqa: F401, E402
from zhaquirks.const import ENDPOINTS

ALL_QUIRK_CLASSES = (
    quirk
    for manufacturer in zq._DEVICE_REGISTRY._registry.values()
    for model in manufacturer.values()
    for quirk in model
)


@pytest.mark.parametrize("quirk", ALL_QUIRK_CLASSES)
def test_quirk_replacements(quirk):
    """Test all quirks have a replacement."""

    assert quirk.signature
    assert quirk.replacement

    assert quirk.replacement[ENDPOINTS]
