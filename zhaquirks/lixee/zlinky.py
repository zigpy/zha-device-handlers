"""Quirk for ZLinky_TIC."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Identify, Ota
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement, MeterIdentification
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster
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


class ZLinkyTICManufacturerCluster(CustomCluster, ManufacturerSpecificCluster):
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
        0x0000: ("histo_optarif_or_standard_ngtf", t.LimitedCharString(16), True),
        # Historical mode: DEMAIN "Couleur du lendemain" / String 4 car
        0x0001: ("histo_demain", t.LimitedCharString(4), True),
        # Historical mode: HHPHC "Horaire Heure Pleines Heures Creuses" / Uint8 1 car
        0x0002: ("histo_hhphc", t.uint8_t, True),
        # Historical mode: PPOT "Présence des potentiels" (Triphasé) / Uint8 2 car
        0x0003: ("histo_ppot", t.uint8_t, True),
        # Historical mode: PEJP "Préavis début EJP(30min)" / Uint8 2 car
        0x0004: ("histo_pejp", t.uint8_t, True),
        # Historical mode: ADPS "Avertissement de Dépassement De Puissance Souscrite" / Uint16 3 car
        0x0005: ("histo_adps", t.uint16_t, True),
        # Historical mode: ADIR1 "Avertissement de Dépassement D'intensité phase 1" / Uint16 3 car
        0x0006: ("histo_adir1", t.uint16_t, True),
        # Historical mode: ADIR2 "Avertissement de Dépassement D'intensité phase 2" / Uint16 3 car
        0x0007: ("histo_adir2", t.uint16_t, True),
        # Historical mode: ADIR3 "Avertissement de Dépassement D'intensité phase 3" / Uint16 3 car
        0x0008: ("histo_adir3", t.uint16_t, True),
        # Historical and Standard mode: "Linky acquisition time (From V7)"" / Uint8 1 car
        0x0100: ("linky_acquisition_time", t.uint8_t, True),
        # Standard mode: LTARF "Libellé tarif fournisseur en cours" / String 16 car
        0x0200: ("standard_ltarf", t.LimitedCharString(16), True),
        # Standard mode: NTARF "Numéro de l’index tarifaire en cours" / Uint8 2 car
        0x0201: ("standard_ntarf", t.uint8_t, True),
        # Standard mode: DATE "Date et heure courant" / String 10 car
        0x0202: ("standard_date", t.LimitedCharString(10), True),
        # Standard mode: EASD01 "Energie active soutirée Distributeur, index 01" / Uint32 9 car
        0x0203: ("standard_easd01", t.uint32_t, True),
        # Standard mode: EASD02 "Energie active soutirée Distributeur, index 02" / Uint32 9 car
        0x0204: ("standard_easd02", t.uint32_t, True),
        # Standard mode: EASD03 "Energie active soutirée Distributeur, index 03" / Uint32 9 car
        0x0205: ("standard_easd03", t.uint32_t, True),
        # Standard mode: EASD04 "Energie active soutirée Distributeur, index 04" / Uint32 9 car
        0x0206: ("standard_easd04", t.uint32_t, True),
        # Standard mode: SINSTI "Puissance app. Instantanée injectée" (Production) / Uint16 5 car
        0x0207: ("standard_sinsti", t.uint16_t, True),
        # Standard mode: SMAXIN "Puissance app max. injectée n" (Production) / Uint16 5 car
        0x0208: ("standard_smaxin", t.uint16_t, True),
        # Standard mode: SMAXIN-1 "Puissance app max. injectée n-1" (Production) / Uint16 5 car
        0x0209: ("standard_smaxin_1", t.uint16_t, True),
        # Standard mode: CCAIN "Point n de la courbe de charge active injectée" (Production) / Uint16 5 car
        0x0210: ("standard_ccain", t.uint16_t, True),
        # Standard mode: CCAIN-1 "Point n-1 de la courbe de charge active injectée" (Production) / Uint16 5 car
        0x0211: ("standard_ccain_1", t.uint16_t, True),
        # Standard mode: SMAXN-1 "Puissance app. max. soutirée n-1" (Monophasé) / Uint16 5 car
        # Standard mode: SMAXN1-1 "Puissance app. max. soutirée n-1 ph.1" (Triphasé) / Uint16 5 car
        0x0212: ("standard_smaxn1_1", t.uint16_t, True),
        # Standard mode: SMAXN2-1 "Puissance app. max. soutirée n-1 ph. 2" (Triphasé) / Uint16 5 car
        0x0213: ("standard_smaxn2_1", t.uint16_t, True),
        # Standard mode: SMAXN3-1 "Puissance app. max. soutirée n-1 ph. 3" (Triphasé) / Uint16 5 car
        0x0214: ("standard_smaxn3_1", t.uint16_t, True),
        # Standard mode: MSG1 "Message court" / String 32 car
        0x0215: ("standard_msg1", t.LimitedCharString(32), True),
        # Standard mode: MSG2 "Message ultra court" / String 16 car
        0x0216: ("standard_msg2", t.LimitedCharString(16), True),
        # Standard mode: STGE "Registre de Statuts" / String 8 car
        0x0217: ("standard_stge", t.LimitedCharString(8), True),
        # Standard mode: DPM1 "Début Pointe Mobile 1" / Uint8 2 car
        0x0218: ("standard_dpm1", t.uint8_t, True),
        # Standard mode: FPM1 "Fin Pointe Mobile 1" / Uint8 2 car
        0x0219: ("standard_fpm1", t.uint8_t, True),
        # Standard mode: DPM2 "Début Pointe Mobile 2" / Uint8 2 car
        0x0220: ("standard_dpm2", t.uint8_t, True),
        # Standard mode: FPM2 "Fin Pointe Mobile 2" / Uint8 2 car
        0x0221: ("standard_fpm2", t.uint8_t, True),
        # Standard mode: DPM3 "Début Pointe Mobile 3" / Uint8 2 car
        0x0222: ("standard_dpm3", t.uint8_t, True),
        # Standard mode: FPM3 "Fin Pointe Mobile 3" / Uint8 2 car
        0x0223: ("standard_fpm3", t.uint8_t, True),
        # Standard mode: RELAIS "RELAIS" / Uint16 3 car
        0x0224: ("standard_relais", t.uint8_t, True),
        # Standard mode: NJOURF "Numéro du jour en cours calendrier fournisseur" / Uint8 2 car
        0x0225: ("standard_njourf", t.uint8_t, True),
        # Standard mode: NJOURF+1 "Numéro du prochain jour calendrier fournisseur" / Uint8 2 car
        0x0226: ("standard_njourf_1", t.uint8_t, True),
        # Standard mode: PJOURF+1 "Profil du prochain jour calendrier fournisseur" / String 98 car
        0x0227: ("standard_pjourf_1", t.LimitedCharString(98), True),
        # Standard mode: PPOINTE1 "Profil du prochain jour de pointe" / String 98 car
        0x0228: ("standard_ppointe1", t.LimitedCharString(98), True),
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
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
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
                    Identify.cluster_id,
                    ZLinkyTICMetering,
                    MeterIdentification.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    ZLinkyTICManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
