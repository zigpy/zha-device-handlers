"""Quirk for ZLinky_TIC."""

from collections.abc import Iterator
from copy import deepcopy
from typing import Final

from zha.application.platforms import BaseEntity
from zha.application.platforms.sensor import (
    BaseElectricalMeasurement,
    ElectricalMeasurementPoller,
)
from zha.zigbee.device import Device as ZHADevice
from zigpy.exceptions import ZigbeeException
from zigpy.profiles import zgp, zha
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Identify,
    Ota,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement, MeterIdentification
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from zhaquirks.builder.device import QuirkV2Device
from zhaquirks.builder.discovery import discover_quirks_v2_entities
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import CustomDevice, signature_matches
from zhaquirks.lixee import LIXEE, ZLINKY_MANUFACTURER_CLUSTER_ID
from zhaquirks.tuya import TuyaManufCluster


class ZLinkyTICManufacturerCluster(CustomCluster):
    """ZLinkyTICManufacturerCluster manufacturer cluster."""

    cluster_id = ZLINKY_MANUFACTURER_CLUSTER_ID
    name = "ZLinky_TIC Manufacturer specific"
    ep_attribute = "zlinky_manufacturer_specific"

    # The attribute comments below are in French to match the reference documentation,
    # see https://github.com/fairecasoimeme/Zlinky_TIC/tree/v9.0#synth%C3%A8se-d%C3%A9veloppeur
    # and https://github.com/fairecasoimeme/Zlinky_TIC/blob/v9.0/ZLinky/Source/LixeeCluster.h
    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        # Historical mode: OPTARIF "Option tarifaire" / String 4 car
        # Standard mode: NGTF "Nom du calendrier tarifaire fournisseur" / String 16 car
        hist_tariff_option_or_std_supplier_price_schedule_name: Final = ZCLAttributeDef(
            id=0x0000, type=t.LimitedCharString(16), is_manufacturer_specific=True
        )
        # Historical mode: DEMAIN "Couleur du lendemain" / String 4 car
        hist_tomorrow_color: Final = ZCLAttributeDef(
            id=0x0001, type=t.LimitedCharString(4), is_manufacturer_specific=True
        )
        # Historical mode: HHPHC "Horaire Heure Pleines Heures Creuses" / Uint8 1 car
        hist_schedule_peak_hours_off_peak_hours: Final = ZCLAttributeDef(
            id=0x0002, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Historical mode: PPOT "Présence des potentiels" (Triphasé) / Uint8 2 car
        hist_potentials_presence: Final = ZCLAttributeDef(
            id=0x0003, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Historical mode: PEJP "Préavis début EJP(30min)" / Uint8 2 car
        hist_ejp_start_notice: Final = ZCLAttributeDef(
            id=0x0004, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Historical mode: ADPS "Avertissement de Dépassement De Puissance Souscrite" / Uint16 3 car
        hist_subscribed_power_exceeding_warning: Final = ZCLAttributeDef(
            id=0x0005, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Historical mode: ADIR1 "Avertissement de Dépassement D'intensité phase 1" / Uint16 3 car
        hist_current_exceeding_warning_phase_1: Final = ZCLAttributeDef(
            id=0x0006, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Historical mode: ADIR2 "Avertissement de Dépassement D'intensité phase 2" / Uint16 3 car
        hist_current_exceeding_warning_phase_2: Final = ZCLAttributeDef(
            id=0x0007, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Historical mode: ADIR3 "Avertissement de Dépassement D'intensité phase 3" / Uint16 3 car
        hist_current_exceeding_warning_phase_3: Final = ZCLAttributeDef(
            id=0x0008, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Historical mode: MOTDETAT "Etat du Linky (From V13)" / String 6 car
        linky_status: Final = ZCLAttributeDef(
            id=0x0009, type=t.LimitedCharString(6), is_manufacturer_specific=True
        )
        # Historical and standard mode: "Tariff Period (From V15)" / String 16 car
        linky_tariff_period: Final = ZCLAttributeDef(
            id=0x0010, type=t.LimitedCharString(16), is_manufacturer_specific=True
        )
        # Historical and Standard mode: "Linky acquisition time (From V7)"" / Uint8 1 car
        linky_acquisition_time: Final = ZCLAttributeDef(
            id=0x0100, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: LTARF "Libellé tarif fournisseur en cours" / String 16 car
        std_current_supplier_price_description: Final = ZCLAttributeDef(
            id=0x0200, type=t.LimitedCharString(16), is_manufacturer_specific=True
        )
        # Standard mode: NTARF "Numéro de l'index tarifaire en cours" / Uint8 2 car
        std_current_tariff_index_number: Final = ZCLAttributeDef(
            id=0x0201, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: DATE "Date et heure courant" / String 10 car
        std_current_date_and_time: Final = ZCLAttributeDef(
            id=0x0202, type=t.LimitedCharString(10), is_manufacturer_specific=True
        )
        # Standard mode: EASD01 "Energie active soutirée Distributeur, index 01" / Uint32 9 car
        std_active_energy_withdrawn_distributor_index_01: Final = ZCLAttributeDef(
            id=0x0203, type=t.uint32_t, is_manufacturer_specific=True
        )
        # Standard mode: EASD02 "Energie active soutirée Distributeur, index 02" / Uint32 9 car
        std_active_energy_withdrawn_distributor_index_02: Final = ZCLAttributeDef(
            id=0x0204, type=t.uint32_t, is_manufacturer_specific=True
        )
        # Standard mode: EASD03 "Energie active soutirée Distributeur, index 03" / Uint32 9 car
        std_active_energy_withdrawn_distributor_index_03: Final = ZCLAttributeDef(
            id=0x0205, type=t.uint32_t, is_manufacturer_specific=True
        )
        # Standard mode: EASD04 "Energie active soutirée Distributeur, index 04" / Uint32 9 car
        std_active_energy_withdrawn_distributor_index_04: Final = ZCLAttributeDef(
            id=0x0206, type=t.uint32_t, is_manufacturer_specific=True
        )
        # Standard mode: SINSTI "Puissance app. Instantanée injectée" (Production) / Uint16 5 car
        std_apparent_power_injected_instantaneous: Final = ZCLAttributeDef(
            id=0x0207, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: SMAXIN "Puissance app max. injectée n" (Production) / Uint16 5 car
        std_apparent_power_injected_max: Final = ZCLAttributeDef(
            id=0x0208, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: SMAXIN-1 "Puissance app max. injectée n-1" (Production) / Uint16 5 car
        std_apparent_power_injected_max_1: Final = ZCLAttributeDef(
            id=0x0209, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: CCAIN "Point n de la courbe de charge active injectée" (Production) / Uint16 5 car
        std_injected_active_load_curve_point_n: Final = ZCLAttributeDef(
            id=0x0210, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: CCAIN-1 "Point n-1 de la courbe de charge active injectée" (Production) / Uint16 5 car
        std_injected_active_load_curve_point_n_1: Final = ZCLAttributeDef(
            id=0x0211, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: SMAXN-1 "Puissance app. max. soutirée n-1" (Monophasé) / Uint16 5 car
        # Standard mode: SMAXN1-1 "Puissance app. max. soutirée n-1 ph.1" (Triphasé) / Uint16 5 car
        std_apparent_power_withdrawn_max_phase_1_n_1: Final = ZCLAttributeDef(
            id=0x0212, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: SMAXN2-1 "Puissance app. max. soutirée n-1 ph. 2" (Triphasé) / Uint16 5 car
        std_apparent_power_withdrawn_max_phase_2_n_1: Final = ZCLAttributeDef(
            id=0x0213, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: SMAXN3-1 "Puissance app. max. soutirée n-1 ph. 3" (Triphasé) / Uint16 5 car
        std_apparent_power_withdrawn_max_phase_3_n_1: Final = ZCLAttributeDef(
            id=0x0214, type=t.uint16_t, is_manufacturer_specific=True
        )
        # Standard mode: MSG1 "Message court" / String 32 car
        std_message_short: Final = ZCLAttributeDef(
            id=0x0215, type=t.LimitedCharString(32), is_manufacturer_specific=True
        )
        # Standard mode: MSG2 "Message ultra court" / String 16 car
        std_message_ultra_short: Final = ZCLAttributeDef(
            id=0x0216, type=t.LimitedCharString(16), is_manufacturer_specific=True
        )
        # Standard mode: STGE "Registre de Statuts" / String 8 car /* codespell:ignore */
        std_status_register: Final = ZCLAttributeDef(
            id=0x0217, type=t.LimitedCharString(8), is_manufacturer_specific=True
        )
        # Standard mode: DPM1 "Début Pointe Mobile 1" / Uint8 2 car
        std_mobile_peak_start_1: Final = ZCLAttributeDef(
            id=0x0218, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: FPM1 "Fin Pointe Mobile 1" / Uint8 2 car
        std_mobile_peak_end_1: Final = ZCLAttributeDef(
            id=0x0219, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: DPM2 "Début Pointe Mobile 2" / Uint8 2 car
        std_mobile_peak_start_2: Final = ZCLAttributeDef(
            id=0x0220, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: FPM2 "Fin Pointe Mobile 2" / Uint8 2 car
        std_mobile_peak_end_2: Final = ZCLAttributeDef(
            id=0x0221, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: DPM3 "Début Pointe Mobile 3" / Uint8 2 car
        std_mobile_peak_start_3: Final = ZCLAttributeDef(
            id=0x0222, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: FPM3 "Fin Pointe Mobile 3" / Uint8 2 car
        std_mobile_peak_end_3: Final = ZCLAttributeDef(
            id=0x0223, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: RELAIS "RELAIS" / Uint16 3 car
        std_relay: Final = ZCLAttributeDef(
            id=0x0224, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: NJOURF "Numéro du jour en cours calendrier fournisseur" / Uint8 2 car
        std_supplier_calendar_current_day_number: Final = ZCLAttributeDef(
            id=0x0225, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: NJOURF+1 "Numéro du prochain jour calendrier fournisseur" / Uint8 2 car
        std_supplier_calendar_next_day_number: Final = ZCLAttributeDef(
            id=0x0226, type=t.uint8_t, is_manufacturer_specific=True
        )
        # Standard mode: PJOURF+1 "Profil du prochain jour calendrier fournisseur" / String 98 car
        std_supplier_calendar_next_day_profile: Final = ZCLAttributeDef(
            id=0x0227, type=t.LimitedCharString(98), is_manufacturer_specific=True
        )
        # Standard mode: PPOINTE1 "Profil du prochain jour de pointe" / String 98 car
        std_next_peak_day_profile: Final = ZCLAttributeDef(
            id=0x0228, type=t.LimitedCharString(98), is_manufacturer_specific=True
        )
        # Historical and Standard mode: - "Linky Mode (From V4)" / Uint8 1 car
        linky_mode: Final = ZCLAttributeDef(
            id=0x0300, type=t.uint8_t, is_manufacturer_specific=True
        )


class ZLinkyTICMetering(CustomCluster, Metering):
    """ZLinky_TIC custom metring cluster."""

    # ZLinky_TIC reports current_summ_delivered in Wh
    # Home Assistant expects kWh (1kWh = 1000 Wh)
    MULTIPLIER = 0x0301
    DIVISOR = 0x0302
    _CONSTANT_ATTRIBUTES = {MULTIPLIER: 1, DIVISOR: 1000}


class ZLinkyTIC(CustomDevice):
    """ZLinky_TIC from LiXee."""

    signature = {
        MODELS_INFO: [(LIXEE, "ZLinky_TIC")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Metering.cluster_id,
                    MeterIdentification.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    ZLinkyTICManufacturerCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    ZLinkyTICMetering,
                    MeterIdentification.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    ZLinkyTICManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }


class ZLinkyTICFWV12(ZLinkyTIC):
    """ZLinky_TIC from LiXee with firmware v12.0 & v13.0."""

    signature = deepcopy(ZLinkyTIC.signature)

    # Insert PowerConfiguration cluster in signature for devices with firmware v12.0 & v13.0
    signature[ENDPOINTS][1][INPUT_CLUSTERS].insert(1, PowerConfiguration.cluster_id)


class ZLinkyTICFWV14(ZLinkyTICFWV12):
    """ZLinky_TIC from LiXee with firmware v14.0+."""

    signature = deepcopy(ZLinkyTICFWV12.signature)
    replacement = deepcopy(ZLinkyTICFWV12.replacement)

    # Insert Time configuration cluster in signature for devices with firmware v14.0+
    signature[ENDPOINTS][1][INPUT_CLUSTERS].insert(1, Time.cluster_id)

    # Insert Tuya cluster in signature for devices with firmware v14.0+
    signature[ENDPOINTS][1][INPUT_CLUSTERS].insert(7, TuyaManufCluster.cluster_id)
    signature[ENDPOINTS][1][OUTPUT_CLUSTERS].insert(1, TuyaManufCluster.cluster_id)

    replacement[ENDPOINTS][1][INPUT_CLUSTERS].insert(1, Time.cluster_id)


class ZLinkyTICTariffCluster(ZLinkyTICManufacturerCluster):
    """ZLinky tariff attribute uses ZCL frames without a manufacturer code."""

    class AttributeDefs(ZLinkyTICManufacturerCluster.AttributeDefs):
        """Tariff attribute definition for firmware v15 and later."""

        linky_tariff_period: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.LimitedCharString(16),
            access="rp",
            manufacturer_code=None,
        )
        linky_mode: Final = ZCLAttributeDef(
            id=0x0300, type=t.uint8_t, access="r", manufacturer_code=None
        )


def tariff_period(value: str | bytes | None) -> str | None:
    """Remove TIC padding while preserving supplier labels and Tempo codes."""
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return " ".join(value.replace("\x00", "").split()) or None


class ZLinkyTICV15Device(QuirkV2Device):
    """Use TIC standard three-phase meanings only when the meter mode is known."""

    @property
    def standard_three_phase(self) -> bool:
        """Return whether the meter uses standard three-phase TIC, including production."""
        cluster = self.endpoints[1].zigpy_endpoint.zlinky_manufacturer_specific
        return cluster.get("linky_mode") in (3, 7)

    async def read_linky_mode(self) -> None:
        """Read meter metadata once if absent; never poll electrical measurements."""
        cluster = self.endpoints[1].zigpy_endpoint.zlinky_manufacturer_specific
        if cluster.get("linky_mode") is not None:
            return
        try:
            await cluster.read_attributes(["linky_mode"], allow_cache=True)
        except (TimeoutError, ZigbeeException):
            self.debug("Could not read Linky mode; retaining native electrical sensors")

    async def async_configure(self) -> None:
        """Identify the TIC mode before selecting reporting configurations."""
        await self.read_linky_mode()
        await super().async_configure()

    async def async_initialize(self, from_cache: bool = False) -> None:
        """Identify the TIC mode before entity discovery, including existing devices."""
        await self.read_linky_mode()
        await super().async_initialize(from_cache)

    def discover_entities(self) -> Iterator[BaseEntity]:
        """Keep native sensors outside the validated standard three-phase modes."""
        # Calling the ZHA base directly avoids creating the electrical quirk
        # entities outside these modes, hence avoids configuring their reports.
        for entity in ZHADevice.discover_entities(self):
            if self.standard_three_phase and isinstance(
                entity, (BaseElectricalMeasurement, ElectricalMeasurementPoller)
            ):
                continue
            yield entity
        for entity in discover_quirks_v2_entities(self):
            if self.standard_three_phase or not entity.targets_cluster(
                ElectricalMeasurement.cluster_id
            ):
                yield entity


# Preserve the exact v15+ signature; older firmware retains its legacy quirk.
ZLINKY_FW_V15_SIGNATURE = deepcopy(ZLinkyTICFWV14.signature)
ZLINKY_FW_V15_SIGNATURE[ENDPOINTS][1][DEVICE_TYPE] = zha.DeviceType.DIMMABLE_LIGHT

builder = (
    QuirkBuilder(LIXEE, "ZLinky_TIC")
    .filter(signature_matches(ZLINKY_FW_V15_SIGNATURE))
    .zha_device_class(ZLinkyTICV15Device)
    .replaces(ZLinkyTICMetering)
    .replaces(ZLinkyTICTariffCluster)
    .removes(TuyaManufCluster.cluster_id)
    .removes(TuyaManufCluster.cluster_id, cluster_type=ClusterType.Client)
    .sensor(
        attribute_name=ZLinkyTICTariffCluster.AttributeDefs.linky_tariff_period.name,
        cluster_id=ZLinkyTICTariffCluster.cluster_id,
        attribute_converter=tariff_period,
        reporting_config=ReportingConfig(
            min_interval=0,
            max_interval=3600,
            reportable_change=0,
        ),
        unique_id_suffix="tariff_period",
        translation_key="tariff_period",
        fallback_name="Tariff period",
    )
)

# Preserve native IDs where the measurement and unit are unchanged. The old
# total_active_power sensor used W for SMAXSN: use a fresh ID for its VA data.
# See the ZLinky firmware TIC mapping and Zigbee2MQTT's LiXee converter.
ZLINKY_THREE_PHASE_MEASUREMENTS = (
    (
        "rms_current",
        "2820-rms_current",
        "Current phase 1",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    (
        "rms_current_ph_b",
        "2820-rms_current_ph_b",
        "Current phase 2",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    (
        "rms_current_ph_c",
        "2820-rms_current_ph_c",
        "Current phase 3",
        SensorDeviceClass.CURRENT,
        UnitOfElectricCurrent.AMPERE,
    ),
    (
        "rms_voltage",
        "2820-rms_voltage",
        "Voltage phase 1",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    (
        "rms_voltage_ph_b",
        "2820-rms_voltage_ph_b",
        "Voltage phase 2",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    (
        "rms_voltage_ph_c",
        "2820-rms_voltage_ph_c",
        "Voltage phase 3",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
    ),
    (
        "apparent_power",
        "2820-apparent_power",
        "Apparent power phase 1",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "apparent_power_ph_b",
        "2820-apparent_power_ph_b",
        "Apparent power phase 2",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "apparent_power_ph_c",
        "2820-apparent_power_ph_c",
        "Apparent power phase 3",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "total_apparent_power",
        "2820-total_apparent_power",
        "Total apparent power",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "active_power",
        "2820",
        "Drawn load curve current point",
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
    ),
    (
        "active_power_ph_b",
        "2820-active_power_ph_b",
        "Drawn load curve previous point",
        SensorDeviceClass.POWER,
        UnitOfPower.WATT,
    ),
    (
        "active_power_max",
        "2820-apparent_power_max_phase_1",
        "Maximum apparent power phase 1",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "active_power_max_ph_b",
        "2820-apparent_power_max_phase_2",
        "Maximum apparent power phase 2",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "active_power_max_ph_c",
        "2820-apparent_power_max_phase_3",
        "Maximum apparent power phase 3",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    (
        "total_active_power",
        "2820-apparent_power_max_total",
        "Maximum total apparent power",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
)

for attribute, suffix, name, device_class, unit in ZLINKY_THREE_PHASE_MEASUREMENTS:
    builder.sensor(
        attribute_name=attribute,
        cluster_id=ElectricalMeasurement.cluster_id,
        device_class=device_class,
        state_class=SensorStateClass.MEASUREMENT,
        unit=unit,
        suggested_display_precision=0,
        reporting_config=ReportingConfig(
            min_interval=60, max_interval=900, reportable_change=1
        ),
        unique_id_suffix=suffix,
        translation_key=f"zlinky_{attribute}",
        fallback_name=name,
    )

builder.add_to_registry()
