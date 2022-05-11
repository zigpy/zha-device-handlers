"""Locate existing quirks that may match a device diagnostic file from ZHA."""

import json

import zigpy.quirks as zq

import zhaquirks

zhaquirks.setup()

ALL_QUIRK_CLASSES = []
for manufacturer in zq._DEVICE_REGISTRY._registry.values():
    for model_quirk_list in manufacturer.values():
        for quirk in model_quirk_list:
            if quirk in ALL_QUIRK_CLASSES:
                continue
            ALL_QUIRK_CLASSES.append(quirk)

del quirk, model_quirk_list, manufacturer


with open("./diagnostics.json") as f:
    diagnostics_file_data = f.read()

diagnostics_data = json.loads(diagnostics_file_data)

signature = diagnostics_data.get("data").get("signature")

for quirk in ALL_QUIRK_CLASSES:
    sig_ep_ids = {int(id) for id in signature.get("endpoints").keys()}
    quirk_ep_ids = {int(id) for id in quirk.signature.get("endpoints").keys()}

    if not sig_ep_ids.issubset(quirk_ep_ids):
        continue

    quirk_match = True
    for quirk_endpoint_id, quirk_endpoint in quirk.signature.get("endpoints").items():
        endpoint = signature.get("endpoints").get(str(quirk_endpoint_id))
        if int(quirk_endpoint.get("device_type")) != int(
            endpoint.get("device_type"), base=16
        ):
            quirk_match = False
            break
        if quirk_endpoint.get("profile_id") != endpoint.get("profile_id"):
            quirk_match = False
            break
        endpoint_input_clusters = {
            int(cluster_id, base=16) for cluster_id in endpoint.get("in_clusters")
        }
        endpoint_output_clusters = {
            int(cluster_id, base=16) for cluster_id in endpoint.get("out_clusters")
        }
        quirk_input_clusters = {
            int(cluster_id) for cluster_id in quirk_endpoint.get("input_clusters")
        }
        quirk_output_clusters = {
            int(cluster_id) for cluster_id in quirk_endpoint.get("output_clusters")
        }

        if not endpoint_input_clusters.issubset(
            quirk_input_clusters
        ) or not endpoint_output_clusters.issubset(quirk_output_clusters):
            quirk_match = False
            break

    if quirk_match:
        print(quirk.__name__)
        break
