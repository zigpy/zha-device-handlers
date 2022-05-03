"""Generate a quirk using jinja2 templates and device diagnostic data."""

from collections import defaultdict
import json
import logging

from jinja2 import Environment, FileSystemLoader
from zigpy.profiles import zha, zll
from zigpy.zcl import clusters

_LOGGER = logging.getLogger(__name__)


all_clusters = set()


def process_profiles(data: dict) -> dict:
    """Process the profiles in the device signature."""
    profiles = set()
    for endpoint in data["signature"]["endpoints"].values():
        profiles.add(endpoint["profile_id"])
    data["present_profiles"] = profiles
    data["zha_profile"] = zha.PROFILE_ID
    data["zll_profile"] = zll.PROFILE_ID
    return data


def process_endpoints(data: dict) -> None:
    """Process the endpoints in the device signature."""
    for id, endpoint in data["signature"]["endpoints"].items():
        endpoint["device_type"] = process_device_type(
            endpoint["profile_id"], endpoint["device_type"]
        )
        endpoint["profile_id"] = process_profile_id(endpoint["profile_id"])
        endpoint["in_clusters"] = process_clusters(endpoint["in_clusters"])
        endpoint["out_clusters"] = process_clusters(endpoint["out_clusters"])


def process_profile_id(profile_id: int) -> str | int:
    """Process the profile id."""
    if profile_id == zha.PROFILE_ID:
        return "zha.PROFILE_ID"
    elif profile_id == zll.PROFILE_ID:
        return "zll.PROFILE_ID"
    else:
        return profile_id


def process_device_type(profile_id: int, device_type: int) -> str | int:
    """Process the device type."""
    if profile_id == zha.PROFILE_ID:
        return f"zha.DeviceType.{zha.DeviceType(device_type).name}"
    elif profile_id == zll.PROFILE_ID:
        return f"zll.DeviceType.{zll.DeviceType(device_type).name}"
    else:
        return device_type


def process_clusters(data: dict) -> dict:
    """Process the clusters in the device signature."""
    processed_clusters = []
    for cluster_id in data:
        id = int(cluster_id, 16)
        if id in clusters.CLUSTERS_BY_ID:
            cluster = clusters.CLUSTERS_BY_ID[id]
            all_clusters.add(cluster)
            class_name = cluster.__name__
            processed_clusters.append(f"{class_name}.cluster_id")
        else:
            processed_clusters.append(cluster_id)
    return processed_clusters


# reading the data from the file
with open("./diagnostics.json") as f:
    diagnostics_file_data = f.read()

diagnostics_data = json.loads(diagnostics_file_data)

env = Environment(loader=FileSystemLoader("./templates"))
quirk_template = env.get_template("quirk_template.txt")

template_data = process_profiles(diagnostics_data.get("data"))

process_endpoints(template_data)

grouped_clusters = defaultdict(list)
for cluster in all_clusters:
    grouped_clusters[cluster.__module__].append(cluster.__name__)

for module, classes in grouped_clusters.items():
    classes.sort()


template_data["grouped_clusters"] = dict(sorted(grouped_clusters.items()))

print(quirk_template.render(template_data))
