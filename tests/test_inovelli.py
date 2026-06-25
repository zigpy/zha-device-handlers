"""Tests for Inovelli quirks (VZM series)."""

import pytest
from zha.quirks import DEVICE_REGISTRY

import zhaquirks
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.inovelli.builder import INOVELLI_CLUSTER_ID

zhaquirks.setup()


def _inovelli_v2_definitions():
    """Yield (model, QuirkDefinition) for every Inovelli VZM v2 quirk."""
    seen = set()
    for entry in DEVICE_REGISTRY:
        factory = entry.zha_device_factory
        if not isinstance(factory, QuirkV2Factory):
            continue
        if "inovelli" not in str(entry.source.file).lower():
            continue
        model = str(entry.source.file).split("/")[-1]
        if model in seen:
            continue
        seen.add(model)
        yield model, factory.quirk_definition


# Number of Inovelli ``0xFC31`` entities each device file is expected to expose.
# Locks the per-model set derived from the ZHA library's registration rules.
EXPECTED_ENTITY_COUNTS = {
    "VZM30SN.py": 38,
    "VZM31SN.py": 40,
    "VZM32SN.py": 37,
    "VZM35SN.py": 38,
    "VZM36.py": 32,  # 17 on endpoint 1 + 15 on endpoint 2
}


def test_inovelli_quirks_present():
    """All five Inovelli VZM device files register a v2 quirk."""
    models = {model for model, _ in _inovelli_v2_definitions()}
    assert models == set(EXPECTED_ENTITY_COUNTS)


@pytest.mark.parametrize(
    ("model", "definition"),
    [(m, d) for m, d in _inovelli_v2_definitions()],
)
def test_inovelli_entity_unique_id_suffix(model, definition):
    """Every Inovelli cluster entity keeps the ZHA-native unique_id.

    ZHA-native entities include the cluster id in their unique_id, but quirks v2
    entities do not. To avoid orphaning existing Home Assistant entities, every
    ported entity must carry a ``64561[-<attribute>]`` suffix (``64561 == 0xFC31``).
    """
    inovelli_entities = [
        em for em in definition.entity_metadata if em.cluster_id == INOVELLI_CLUSTER_ID
    ]
    assert len(inovelli_entities) == EXPECTED_ENTITY_COUNTS[model]

    for em in inovelli_entities:
        suffix = em.unique_id_suffix
        assert suffix is not None
        # bare cluster id (internal temperature sensor) or ``64561-<attribute>``
        assert suffix == str(INOVELLI_CLUSTER_ID) or suffix.startswith(
            f"{INOVELLI_CLUSTER_ID}-"
        ), f"{model}: unexpected unique_id suffix {suffix!r}"
