"""Philips Hue devices."""

from zigpy.quirks.v2 import QuirkBuilder

from zhaquirks.philips import PHILIPS, SIGNIFY, PhilipsHueLightCluster

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX001")
    .applies_to(SIGNIFY, "LCX002")
    .applies_to(SIGNIFY, "LCX003")
    .applies_to(SIGNIFY, "LCX005")
    .applies_to(SIGNIFY, "LCX006")
    .friendly_name(
        model="Hue Play gradient lightstrip",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LCX012")
    .applies_to(SIGNIFY, "LCX015")
    .applies_to(SIGNIFY, "LCX016")
    .applies_to(SIGNIFY, "LCX017")
    .friendly_name(
        model="Hue Festavia gradient light string",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTB003")
    .friendly_name(
        model="Hue White Ambiance BR30 E26",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929003116301")
    .applies_to(SIGNIFY, "929003116401")
    .applies_to(SIGNIFY, "929003116501")
    .applies_to(SIGNIFY, "929003116601")
    .friendly_name(
        model="Hue Perifo light tube",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "4080248U9")
    .applies_to(SIGNIFY, "915005987101")
    .applies_to(SIGNIFY, "915005987201")
    .applies_to(SIGNIFY, "915005987501")
    .applies_to(SIGNIFY, "915005987601")
    .applies_to(SIGNIFY, "915005987701")
    .applies_to(SIGNIFY, "915005987801")
    .applies_to(SIGNIFY, "929003479601")
    .applies_to(SIGNIFY, "929003479701")
    .friendly_name(
        model="Hue Signe gradient floor lamp",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "915005986901")
    .applies_to(SIGNIFY, "915005987001")
    .applies_to(SIGNIFY, "915005987401")
    .applies_to(SIGNIFY, "915005987301")
    .friendly_name(
        model="Hue Signe gradient table lamp",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "915005987901")
    .applies_to(SIGNIFY, "915005988001")
    .applies_to(SIGNIFY, "915005988101")
    .applies_to(SIGNIFY, "915005988201")
    .applies_to(SIGNIFY, "915005988401")
    .applies_to(SIGNIFY, "915005988501")
    .friendly_name(
        model="Hue Play gradient light tube",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "929003116301")
    .applies_to(SIGNIFY, "929003116401")
    .applies_to(SIGNIFY, "929003116501")
    .applies_to(SIGNIFY, "929003116601")
    .friendly_name(
        model="Hue Perifo light tube",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LTA001")
    .friendly_name(
        model="Hue white ambiance E27 with Bluetooth",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(SIGNIFY, "LWU001")
    .friendly_name(
        model="Hue P45 light bulb",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(PHILIPS, "7602031P7")
    .applies_to(PHILIPS, "7602031U7")
    .friendly_name(
        model="Hue Go",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)

(
    QuirkBuilder()
    .applies_to(PHILIPS, "1743130P7")
    .applies_to(PHILIPS, "1743430P7")
    .applies_to(PHILIPS, "1743230P7")
    .applies_to(PHILIPS, "1745430A7")
    .applies_to(PHILIPS, "1745430P7")
    .friendly_name(
        model="Hue Impress outdoor Pedestal",
        manufacturer="Philips",
    )
    .replaces(PhilipsHueLightCluster, endpoint_id=11)
    .add_to_registry()
)
