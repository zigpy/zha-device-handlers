"""Tests for Inovelli quirks (VZM series)."""

import pytest
from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.builder.builder import ReplaceCluster, ReplaceClusterOccurrences
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.inovelli.builder import INOVELLI_CLUSTER_ID, INOVELLI_MMWAVE_CLUSTER_ID

zhaquirks.setup()

INOVELLI_CLUSTER_IDS = (INOVELLI_CLUSTER_ID, INOVELLI_MMWAVE_CLUSTER_ID)


def _inovelli_v2_entries():
    """Yield (model, QuirkRegistryEntry) for every Inovelli VZM v2 quirk."""
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
        yield model, entry


def _inovelli_clusters_by_endpoint(entry, cluster_id):
    """Map endpoint id to the quirk's replacement class for ``cluster_id``.

    ``.replaces()`` targets a single endpoint, while
    ``.replace_cluster_occurrences()`` covers every endpoint that already has
    the cluster -- the latter is returned under the ``None`` key, as the
    device-wide fallback for endpoints with no explicit entry.
    """
    clusters = {}
    for op in entry.zigpy_transforms:
        if isinstance(op, ReplaceCluster):
            op_cluster_id = (
                op.cluster.cluster_id if op.cluster_id is None else op.cluster_id
            )
            if op_cluster_id == cluster_id and op.cluster_type == ClusterType.Server:
                clusters[op.endpoint_id] = op.cluster
        elif isinstance(op, ReplaceClusterOccurrences):
            if (
                op.cluster.cluster_id == cluster_id
                and ClusterType.Server in op.cluster_types
            ):
                clusters[None] = op.cluster
    return clusters


# Number of Inovelli manufacturer-cluster (0xFC31 / 0xFC32) entities each device
# file is expected to expose. Locks the per-model set: for VZM30/31/35/36 this is
# the set derived from the ZHA library's registration rules; VZM32-SN additionally
# exposes its mmWave-specific entities.
EXPECTED_ENTITY_COUNTS = {
    "VZM30SN.py": 38,
    "VZM31SN.py": 40,
    "VZM32SN.py": 50,  # 41 on 0xFC31 + 9 on the 0xFC32 mmWave cluster
    "VZM35SN.py": 38,
    "VZM36.py": 32,  # 17 on endpoint 1 + 15 on endpoint 2
}


def test_inovelli_quirks_present():
    """All five Inovelli VZM device files register a v2 quirk."""
    models = {model for model, _ in _inovelli_v2_entries()}
    assert models == set(EXPECTED_ENTITY_COUNTS)


@pytest.mark.parametrize(
    ("model", "entry"),
    [(m, e) for m, e in _inovelli_v2_entries()],
)
def test_inovelli_entity_unique_id_suffix(model, entry):
    """Every Inovelli cluster entity keeps the ZHA-native unique_id format.

    ZHA-native entities include the cluster id in their unique_id, but quirks v2
    entities do not. To avoid orphaning existing Home Assistant entities (and to
    stay consistent for the new mmWave entities), every entity must carry a
    ``<cluster_id>[-<attribute>]`` suffix (``64561 == 0xFC31``, ``64562 == 0xFC32``).
    """
    definition = entry.zha_device_factory.quirk_definition
    inovelli_entities = [
        em for em in definition.entity_metadata if em.cluster_id in INOVELLI_CLUSTER_IDS
    ]
    assert len(inovelli_entities) == EXPECTED_ENTITY_COUNTS[model]

    for em in inovelli_entities:
        suffix = em.unique_id_suffix
        cid = em.cluster_id
        assert suffix is not None
        # bare cluster id (internal temperature sensor) or ``<cluster_id>-<attribute>``
        assert suffix == str(cid) or suffix.startswith(f"{cid}-"), (
            f"{model}: unexpected unique_id suffix {suffix!r} for cluster {cid}"
        )


@pytest.mark.parametrize(
    ("model", "entry"),
    [(m, e) for m, e in _inovelli_v2_entries()],
)
def test_inovelli_entity_attribute_names_exist(model, entry):
    """Every Inovelli cluster entity is backed by an attribute that exists.

    The builder has to pass attribute names as string literals -- no single
    Inovelli cluster defines all of them, so ``AttributeDefs.x.name`` references
    are not practical there. A typo'd name would still register an entity with
    an intact ``<cluster_id>-`` unique_id suffix and an unchanged entity count,
    and would only surface at runtime as a broken entity. So check each name
    against the cluster the quirk actually installs on that entity's endpoint
    (the VZM36 has a different one on its light and fan endpoints).
    """
    for cluster_id in INOVELLI_CLUSTER_IDS:
        clusters = _inovelli_clusters_by_endpoint(entry, cluster_id)
        inovelli_entities = [
            em
            for em in entry.zha_device_factory.quirk_definition.entity_metadata
            if em.cluster_id == cluster_id
        ]

        for em in inovelli_entities:
            attribute_name = getattr(em, "attribute_name", None)
            if attribute_name is None:
                # Command-based entity (e.g. a button): nothing to look up. Assert
                # it really is one, so this branch can never silently swallow an
                # attribute-backed entity.
                assert hasattr(em, "command_name"), (
                    f"{model}: entity {em.unique_id_suffix!r} has neither an "
                    f"attribute_name nor a command_name"
                )
                continue

            cluster = clusters.get(em.endpoint_id, clusters.get(None))
            assert cluster is not None, (
                f"{model}: entity {em.unique_id_suffix!r} is on endpoint "
                f"{em.endpoint_id}, where the quirk replaces no Inovelli cluster"
            )
            assert attribute_name in cluster.attributes_by_name, (
                f"{model}: entity attribute {attribute_name!r} (endpoint "
                f"{em.endpoint_id}) does not exist on {cluster.__name__}"
            )
