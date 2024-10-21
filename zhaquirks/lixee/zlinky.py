"""Quirk for ZLinky_TIC."""

from copy import deepcopy

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
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

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
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
    attributes = {
        # Historical mode: OPTARIF "Option tarifaire" / String 4 car
        # Standard mode: NGTF "Nom du calendrier tarifaire fournisseur" / String 16 car
        0x0000: (
            "hist_tariff_option_or_std_supplier_price_schedule_name",
            t.LimitedCharString(16),
            True,
        ),
        # Historical mode: DEMAIN "Couleur du lendemain" / String 4 car
        0x0001: ("hist_tomorrow_color", t.LimitedCharString(4), True),
        # Historical mode: HHPHC "Horaire Heure Pleines Heures Creuses" / Uint8 1 car
        0x0002: ("hist_schedule_peak_hours_off_peak_hours", t.uint8_t, True),
        # Historical mode: PPOT "Présence des potentiels" (Triphasé) / Uint8 2 car
        0x0003: ("hist_potentials_presence", t.uint8_t, True),
        # Historical mode: PEJP "Préavis début EJP(30min)" / Uint8 2 car
        0x0004: ("hist_ejp_start_notice", t.uint8_t, True),
        # Historical mode: ADPS "Avertissement de Dépassement De Puissance Souscrite" / Uint16 3 car
        0x0005: ("hist_subscribed_power_exceeding_warning", t.uint16_t, True),
        # Historical mode: ADIR1 "Avertissement de Dépassement D'intensité phase 1" / Uint16 3 car
        0x0006: ("hist_current_exceeding_warning_phase_1", t.uint16_t, True),
        # Historical mode: ADIR2 "Avertissement de Dépassement D'intensité phase 2" / Uint16 3 car
        0x0007: ("hist_current_exceeding_warning_phase_2", t.uint16_t, True),
        # Historical mode: ADIR3 "Avertissement de Dépassement D'intensité phase 3" / Uint16 3 car
        0x0008: ("hist_current_exceeding_warning_phase_3", t.uint16_t, True),
        # Historical mode: MOTDETAT "Etat du Linky (From V13)" / String 6 car
        0x0009: ("linky_status", t.LimitedCharString(6), True),
        # Historical and Standard mode: "Linky acquisition time (From V7)"" / Uint8 1 car
        0x0100: ("linky_acquisition_time", t.uint8_t, True),
        # Standard mode: LTARF "Libellé tarif fournisseur en cours" / String 16 car
        0x0200: (
            "std_current_supplier_price_description",
            t.LimitedCharString(16),
            True,
        ),
        # Standard mode: NTARF "Numéro de l’index tarifaire en cours" / Uint8 2 car
        0x0201: ("std_current_tariff_index_number", t.uint8_t, True),
        # Standard mode: DATE "Date et heure courant" / String 10 car
        0x0202: ("std_current_date_and_time", t.LimitedCharString(10), True),
        # Standard mode: EASD01 "Energie active soutirée Distributeur, index 01" / Uint32 9 car
        0x0203: ("std_active_energy_withdrawn_distributor_index_01", t.uint32_t, True),
        # Standard mode: EASD02 "Energie active soutirée Distributeur, index 02" / Uint32 9 car
        0x0204: ("std_active_energy_withdrawn_distributor_index_02", t.uint32_t, True),
        # Standard mode: EASD03 "Energie active soutirée Distributeur, index 03" / Uint32 9 car
        0x0205: ("std_active_energy_withdrawn_distributor_index_03", t.uint32_t, True),
        # Standard mode: EASD04 "Energie active soutirée Distributeur, index 04" / Uint32 9 car
        0x0206: ("std_active_energy_withdrawn_distributor_index_04", t.uint32_t, True),
        # Standard mode: SINSTI "Puissance app. Instantanée injectée" (Production) / Uint16 5 car
        0x0207: ("std_apparent_power_injected_instantaneous", t.uint16_t, True),
        # Standard mode: SMAXIN "Puissance app max. injectée n" (Production) / Uint16 5 car
        0x0208: ("std_apparent_power_injected_max", t.uint16_t, True),
        # Standard mode: SMAXIN-1 "Puissance app max. injectée n-1" (Production) / Uint16 5 car
        0x0209: ("std_apparent_power_injected_max_1", t.uint16_t, True),
        # Standard mode: CCAIN "Point n de la courbe de charge active injectée" (Production) / Uint16 5 car
        0x0210: ("std_injected_active_load_curve_point_n", t.uint16_t, True),
        # Standard mode: CCAIN-1 "Point n-1 de la courbe de charge active injectée" (Production) / Uint16 5 car
        0x0211: ("std_injected_active_load_curve_point_n_1", t.uint16_t, True),
        # Standard mode: SMAXN-1 "Puissance app. max. soutirée n-1" (Monophasé) / Uint16 5 car
        # Standard mode: SMAXN1-1 "Puissance app. max. soutirée n-1 ph.1" (Triphasé) / Uint16 5 car
        0x0212: ("std_apparent_power_withdrawn_max_phase_1_n_1", t.uint16_t, True),
        # Standard mode: SMAXN2-1 "Puissance app. max. soutirée n-1 ph. 2" (Triphasé) / Uint16 5 car
        0x0213: ("std_apparent_power_withdrawn_max_phase_2_n_1", t.uint16_t, True),
        # Standard mode: SMAXN3-1 "Puissance app. max. soutirée n-1 ph. 3" (Triphasé) / Uint16 5 car
        0x0214: ("std_apparent_power_withdrawn_max_phase_3_n_1", t.uint16_t, True),
        # Standard mode: MSG1 "Message court" / String 32 car
        0x0215: ("std_message_short", t.LimitedCharString(32), True),
        # Standard mode: MSG2 "Message ultra court" / String 16 car
        0x0216: ("std_message_ultra_short", t.LimitedCharString(16), True),
        # Standard mode: STGE "Registre de Statuts" / String 8 car /* codespell:ignore */
        0x0217: ("std_status_register", t.LimitedCharString(8), True),
        # Standard mode: DPM1 "Début Pointe Mobile 1" / Uint8 2 car
        0x0218: ("std_mobile_peak_start_1", t.uint8_t, True),
        # Standard mode: FPM1 "Fin Pointe Mobile 1" / Uint8 2 car
        0x0219: ("std_mobile_peak_end_1", t.uint8_t, True),
        # Standard mode: DPM2 "Début Pointe Mobile 2" / Uint8 2 car
        0x0220: ("std_mobile_peak_start_2", t.uint8_t, True),
        # Standard mode: FPM2 "Fin Pointe Mobile 2" / Uint8 2 car
        0x0221: ("std_mobile_peak_end_2", t.uint8_t, True),
        # Standard mode: DPM3 "Début Pointe Mobile 3" / Uint8 2 car
        0x0222: ("std_mobile_peak_start_3", t.uint8_t, True),
        # Standard mode: FPM3 "Fin Pointe Mobile 3" / Uint8 2 car
        0x0223: ("std_mobile_peak_end_3", t.uint8_t, True),
        # Standard mode: RELAIS "RELAIS" / Uint16 3 car
        0x0224: ("std_relay", t.uint8_t, True),
        # Standard mode: NJOURF "Numéro du jour en cours calendrier fournisseur" / Uint8 2 car
        0x0225: ("std_supplier_calendar_current_day_number", t.uint8_t, True),
        # Standard mode: NJOURF+1 "Numéro du prochain jour calendrier fournisseur" / Uint8 2 car
        0x0226: ("std_supplier_calendar_next_day_number", t.uint8_t, True),
        # Standard mode: PJOURF+1 "Profil du prochain jour calendrier fournisseur" / String 98 car
        0x0227: (
            "std_supplier_calendar_next_day_profile",
            t.LimitedCharString(98),
            True,
        ),
        # Standard mode: PPOINTE1 "Profil du prochain jour de pointe" / String 98 car
        0x0228: ("std_next_peak_day_profile", t.LimitedCharString(98), True),
        # Historical and Standard mode: - "Linky Mode (From V4)" / Uint8 1 car
        0x0300: ("linky_mode", t.uint8_t, True),
    }


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
