#!/usr/bin/env python3
"""
=============================================================================
  COMMENT VA VOTRE COEUR ?
  Evaluation du Risque Cardiovasculaire
  -----
  Mode quantitatif : SCORE2 (ESC 2021) pour pays à bas risque (France)
  Mode qualitatif  : modèle pédagogique multi-facteurs basé sur ln(RR)
                     des grandes études épidémiologiques internationales
=============================================================================
"""

import math
import os
import sys
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from fpdf import FPDF


# ============================================================================
# DONNÉES DU PATIENT
# ============================================================================

@dataclass
class PatientData:
    # Profil
    sexe: str = ""              # "H" ou "F"
    age: int = 0
    poids: float = 0.0          # kg
    taille: float = 0.0         # cm

    # Hérédité
    antecedents_familiaux: str = ""  # "oui", "non", "ne_sais_pas"
    bilan_cardiaque: str = "non"     # "oui", "non"
    consultation_cardiologue: str = "non"  # "oui", "non"
    activite_weekend: str = "promenade"  # "television", "promenade", "jeux_videos", "sport"

    # Mode de vie
    heures_assis: str = ""          # "<3h", "3-7h", ">7h"
    activite_physique: str = ""     # "<30min", "~30min", ">30min"
    tabac: str = ""                 # "oui", "ancien_5ans", "non"
    tabac_passif: str = ""          # "oui", "non"
    fruits_legumes: str = ""        # "<2/sem", "2-5/sem", "2-4/jour", "5+/jour"
    ajout_sel: str = ""             # "oui", "non"
    preparation_repas: str = ""     # "industriel", "maison", "conserves"
    charcuterie_fromage: str = ""   # "oui", "non"
    stress: str = ""                # "jamais", "occasionnel", "permanent"
    coleres: str = ""               # "jamais", "peu", "frequent", "tres_frequent"
    charge_familiale_seule: str = ""  # "oui", "non"
    alcool_excessif: str = ""       # "oui", "non"
    boissons_energisantes: str = "" # "oui", "non"

    # Données médicales
    hypertension: str = ""          # "oui", "non"
    tension_systolique: Optional[float] = None   # mmHg
    tension_diastolique: Optional[float] = None  # mmHg
    cholesterol_eleve: str = ""     # "oui", "non"
    cholesterol_total: Optional[float] = None    # mmol/L
    cholesterol_ldl: Optional[float] = None      # mmol/L
    cholesterol_hdl: Optional[float] = None      # mmol/L
    diabete: str = ""               # "oui", "non"
    glycemie: Optional[float] = None             # g/L
    apnee_sommeil: str = ""         # "oui", "non"
    troubles_sommeil: str = ""      # "oui", "non"


# ============================================================================
# SCORE2 – MODE QUANTITATIF (ESC 2021, pays à bas risque)
# ============================================================================

# Coefficients SCORE2 pour pays à bas risque (France)
SCORE2_COEFFICIENTS = {
    "H": {  # Homme
        "age":       0.3742,
        "tabac":     0.6012,
        "pas":       0.2777,
        "tchol":     0.1458,
        "hdl":      -0.2698,
        "tabac_age": -0.0755,
        "pas_age":   -0.0255,
        "tchol_age": -0.0281,
        "hdl_age":   0.0426,
        "baseline_survival": 0.9605,
    },
    "F": {  # Femme
        "age":       0.4648,
        "tabac":     0.7744,
        "pas":       0.3131,
        "tchol":     0.1002,
        "hdl":      -0.2606,
        "tabac_age": -0.1088,
        "pas_age":   -0.0277,
        "tchol_age": -0.0226,
        "hdl_age":   0.0613,
        "baseline_survival": 0.9776,
    },
}

# Facteurs de calibration régionaux (pays à bas risque – France)
SCORE2_CALIBRATION = {
    "H": {"scale1": -0.5699, "scale2": 0.7476},
    "F": {"scale1": -0.7380, "scale2": 0.7019},
}

# SCORE2-OP coefficients (70-89 ans, pays à bas risque)
SCORE2_OP_COEFFICIENTS = {
    "H": {
        "age":       0.4219,
        "tabac":     0.3564,
        "pas":       0.2030,
        "tchol":     0.0592,
        "hdl":      -0.1549,
        "tabac_age": -0.0793,
        "pas_age":   -0.0260,
        "tchol_age": -0.0143,
        "hdl_age":   0.0310,
        "baseline_survival": 0.8673,
    },
    "F": {
        "age":       0.5765,
        "tabac":     0.4846,
        "pas":       0.2680,
        "tchol":     0.0611,
        "hdl":      -0.1780,
        "tabac_age": -0.1060,
        "pas_age":   -0.0294,
        "tchol_age": -0.0173,
        "hdl_age":   0.0393,
        "baseline_survival": 0.9144,
    },
}

SCORE2_OP_CALIBRATION = {
    "H": {"scale1": -0.3143, "scale2": 0.7557},
    "F": {"scale1": -0.5765, "scale2": 0.7168},
}


def calcul_score2(patient: PatientData) -> Optional[dict]:
    """
    Calcul SCORE2 / SCORE2-OP pour pays à bas risque (France).
    Retourne le risque à 10 ans d'événement CV fatal ou non fatal.
    Nécessite : sexe, âge (40-89), tabac, PAS, cholesterol total, HDL.
    """
    # Vérification des données requises
    if patient.age < 40 or patient.age > 89:
        return None
    if patient.tension_systolique is None:
        return None
    if patient.cholesterol_total is None or patient.cholesterol_hdl is None:
        return None

    sexe = patient.sexe
    fumeur = 1 if patient.tabac == "oui" else 0

    # Choix du modèle selon l'âge
    if patient.age < 70:
        coef = SCORE2_COEFFICIENTS[sexe]
        calib = SCORE2_CALIBRATION[sexe]
        age_center = 60
    else:
        coef = SCORE2_OP_COEFFICIENTS[sexe]
        calib = SCORE2_OP_CALIBRATION[sexe]
        age_center = 75

    # Transformations centrées
    cage = (patient.age - age_center) / 5
    csbp = (patient.tension_systolique - 120) / 20
    ctchol = patient.cholesterol_total - 6
    chdl = (patient.cholesterol_hdl - 1.3) / 0.5

    # Calcul du score linéaire
    lp = (
        coef["age"] * cage
        + coef["tabac"] * fumeur
        + coef["pas"] * csbp
        + coef["tchol"] * ctchol
        + coef["hdl"] * chdl
        + coef["tabac_age"] * fumeur * cage
        + coef["pas_age"] * csbp * cage
        + coef["tchol_age"] * ctchol * cage
        + coef["hdl_age"] * chdl * cage
    )

    # Risque non calibré
    s0 = coef["baseline_survival"]
    risk_uncalib = 1 - s0 ** math.exp(lp)

    # Calibration régionale (pays à bas risque)
    if risk_uncalib <= 0:
        risk_uncalib = 0.0001
    if risk_uncalib >= 1:
        risk_uncalib = 0.9999

    inner = math.log(-math.log(1 - risk_uncalib))
    calibrated_value = calib["scale1"] + calib["scale2"] * inner
    risk_calibrated = (1 - math.exp(-math.exp(calibrated_value))) * 100

    risk_calibrated = max(0.1, min(99.9, risk_calibrated))

    # Classification du risque selon l'âge
    if patient.age < 50:
        if risk_calibrated < 2.5:
            categorie = "Faible à modéré"
            couleur = "vert"
        elif risk_calibrated < 7.5:
            categorie = "Élevé"
            couleur = "orange"
        else:
            categorie = "Très élevé"
            couleur = "rouge"
    elif patient.age < 70:
        if risk_calibrated < 5:
            categorie = "Faible à modéré"
            couleur = "vert"
        elif risk_calibrated < 10:
            categorie = "Élevé"
            couleur = "orange"
        else:
            categorie = "Très élevé"
            couleur = "rouge"
    else:  # >= 70
        if risk_calibrated < 7.5:
            categorie = "Faible à modéré"
            couleur = "vert"
        elif risk_calibrated < 15:
            categorie = "Élevé"
            couleur = "orange"
        else:
            categorie = "Très élevé"
            couleur = "rouge"

    return {
        "mode": "SCORE2" if patient.age < 70 else "SCORE2-OP",
        "risque_pct": round(risk_calibrated, 1),
        "categorie": categorie,
        "couleur": couleur,
        "lp": round(lp, 4),
        "risk_uncalib_pct": round(risk_uncalib * 100, 1),
    }


# ============================================================================
# MODE QUALITATIF – Modèle pédagogique multi-facteurs
# ============================================================================

def calcul_imc(poids: float, taille_cm: float) -> float:
    """Calcul de l'Indice de Masse Corporelle."""
    taille_m = taille_cm / 100
    if taille_m <= 0:
        return 0
    return poids / (taille_m ** 2)


def categorie_imc(imc: float) -> str:
    if imc < 18.5:
        return "Insuffisance pondérale"
    elif imc < 25:
        return "Poids normal"
    elif imc < 30:
        return "Surpoids"
    elif imc < 35:
        return "Obésité modérée (classe I)"
    elif imc < 40:
        return "Obésité sévère (classe II)"
    else:
        return "Obésité morbide (classe III)"


def score_qualitatif(patient: PatientData) -> dict:
    """
    Évaluation qualitative multi-facteurs basée sur les risques relatifs (RR)
    publiés dans la littérature médicale. Chaque pondération est proportionnelle
    au ln(RR) du facteur, normalisé sur une échelle de points.

    Sources principales :
    - INTERHEART (Yusuf et al., Lancet 2004) — OR ajustés, 52 pays
    - Prospective Studies Collaboration (Lewington et al., Lancet 2002) — 1M adultes
    - Emerging Risk Factors Collaboration (Lancet 2010) — 102 études prospectives
    - AHA Science Advisory (Young et al., Circulation 2016) — sédentarité
    - Micha et al. (Circulation 2010) — viande transformée
    - Dong et al. (Int J Cardiol 2013) — apnée du sommeil
    - He et al. (NEJM 1999) — tabagisme passif
    - Graudal et al. (Nutrients 2020) — sel
    - Zhao et al. (JAMA Network Open 2023) — alcool
    - Global BMI Mortality Collaboration (Lancet 2016) — obésité
    - EPIC-Norfolk (Eur J Prev Cardiol 2024) — sexe, hérédité
    """
    score = 0
    details = []
    recommandations = []
    facteurs_positifs = []

    # ── 1. ÂGE (0-14 points) ──
    # HR ~2.0-3.0 par décennie après 40 ans (PSC, Lewington et al., Lancet 2002)
    # ln(2.5)/décennie × ~3 décennies max = poids très élevé
    if patient.age < 40:
        pts = 0
    elif patient.age < 50:
        pts = 3
    elif patient.age < 55:
        pts = 5
    elif patient.age < 60:
        pts = 7
    elif patient.age < 65:
        pts = 9
    elif patient.age < 70:
        pts = 11
    else:
        pts = 14
    score += pts
    details.append(("Âge", patient.age, pts, 14))

    # ── 2. SEXE (0-5 points) ──
    # HR ~2.0 homme vs femme en âge moyen (EPIC-Norfolk, Eur J Prev Cardiol 2024)
    # Ratio homme/femme ~2:1 (Framingham), écart se réduit post-ménopause
    if patient.sexe == "H":
        pts = 5
    else:
        pts = 2 if patient.age >= 55 else 0  # post-ménopause
    score += pts
    details.append(("Sexe", "Homme" if patient.sexe == "H" else "Femme", pts, 5))

    # ── 3. IMC (0-6 points) ──
    # Surpoids : HR 1.26 pour coronaropathie (Pooled 97 cohortes, Lancet 2014)
    # Obésité BMI>30 : HR 1.69 pour coronaropathie (même étude)
    # Obésité sévère : HR ~2.0 (Global BMI Mortality Collab., Lancet 2016)
    imc = calcul_imc(patient.poids, patient.taille)
    if imc < 18.5:
        pts = 1
    elif imc < 25:
        pts = 0
        facteurs_positifs.append("IMC normal")
    elif imc < 30:
        pts = 2   # ln(1.26) = 0.231 → 2 pts
        recommandations.append("Perdre du poids : viser un IMC < 25 réduirait votre risque cardiovasculaire (HR 1.26, Lancet 2014).")
    elif imc < 35:
        pts = 4   # ln(1.69) = 0.525 → 4 pts
        recommandations.append("Consulter un nutritionniste : l'obésité augmente le risque CV de 69% (HR 1.69, Lancet 2014).")
    else:
        pts = 6   # ln(2.0) = 0.693 → 6 pts
        recommandations.append("Prise en charge médicale de l'obésité recommandée : risque CV doublé (HR 2.0, Lancet 2016).")
    score += pts
    details.append(("IMC", f"{imc:.1f} ({categorie_imc(imc)})", pts, 6))

    # ── 4. ANTÉCÉDENTS FAMILIAUX (0-5 points) ──
    # HR 1.74 (IC 95% 1.56-1.95) — EPIC-Norfolk (Heart 2011)
    # ln(1.74) = 0.554 → 5 pts
    if patient.antecedents_familiaux == "oui":
        pts = 5
        recommandations.append("Antécédents familiaux : surveillance cardiologique renforcée recommandée (HR 1.74, EPIC-Norfolk).")
    elif patient.antecedents_familiaux == "ne_sais_pas":
        pts = 2
        recommandations.append("Renseignez-vous sur vos antécédents familiaux cardiovasculaires.")
    else:
        pts = 0
        facteurs_positifs.append("Pas d'antécédents familiaux cardiovasculaires")
    score += pts
    details.append(("Antécédents familiaux", patient.antecedents_familiaux, pts, 5))

    # ── 5. SÉDENTARITÉ (0-5 points) ──
    # HR 1.90 (IC 95% 1.36-2.66) mortalité CV, sédentarité élevée vs faible
    # (AHA Science Advisory, Young et al., Circulation 2016)
    # ln(1.90) = 0.642 → 5 pts
    if patient.heures_assis == ">7h":
        pts = 5
        recommandations.append("Réduire le temps assis : se lever toutes les 30 min. "
                               "La sédentarité prolongée augmente le risque CV de 90% (HR 1.90, AHA 2016).")
    elif patient.heures_assis == "3-7h":
        pts = 2
    else:
        pts = 0
        facteurs_positifs.append("Faible temps de sédentarité")
    score += pts
    details.append(("Sédentarité (temps assis)", patient.heures_assis, pts, 5))

    # ── 6. ACTIVITÉ PHYSIQUE (0-2 points) ──
    # HR 1.24 (IC 95% 1.13-1.36) pour coronaropathie, inactif vs actif
    # (Li & Siegrist, Int J Environ Res Public Health 2012, méta-analyse)
    # ln(1.24) = 0.215 → 2 pts
    # NB : effet indépendant faible car l'activité agit VIA les autres facteurs
    # (poids, TA, cholestérol) déjà comptés séparément.
    if patient.activite_physique == "<30min":
        pts = 2
        recommandations.append("Augmenter l'activité physique : 30 min/jour de marche rapide. "
                               "L'inactivité augmente le risque CV de 24% indépendamment des autres facteurs (HR 1.24, méta-analyse 2012). "
                               "L'effet total est plus important car l'activité améliore aussi le poids, la tension et le cholestérol.")
    elif patient.activite_physique == "~30min":
        pts = 1
    else:
        pts = 0
        facteurs_positifs.append("Activité physique suffisante (>30 min/jour)")
    score += pts
    details.append(("Activité physique", patient.activite_physique, pts, 2))

    # ── 7. TABAC ACTIF (0-9 points) ──
    # Fumeur actif : OR 2.87 (IC 99% 2.58-3.19) pour infarctus
    # (INTERHEART, Yusuf et al., Lancet 2004; 52 pays, 27 000 sujets)
    # ln(2.87) = 1.054 → 9 pts
    # Ancien fumeur <5 ans : risque résiduel ~50% → ~5 pts
    if patient.tabac == "oui":
        pts = 9
        recommandations.append("ARRÊTER DE FUMER : le tabac multiplie le risque d'infarctus par 2.87 (INTERHEART, Lancet 2004). "
                               "Après 1 an d'arrêt, le risque diminue de 50%. Après 5 ans, il rejoint celui d'un non-fumeur.")
    elif patient.tabac == "ancien_5ans":
        pts = 5
        recommandations.append("Ancien fumeur : le risque résiduel diminue progressivement. "
                               "Après 5 ans d'arrêt, il rejoint celui d'un non-fumeur. Tenez bon !")
    else:
        pts = 0
        facteurs_positifs.append("Non-fumeur / arrêt depuis > 5 ans")
    score += pts
    details.append(("Tabac actif", patient.tabac, pts, 9))

    # ── 8. TABAC PASSIF (0-2 points) ──
    # RR 1.25 (IC 95% 1.17-1.32) — He et al., NEJM 1999, méta-analyse
    # RR 1.30 conjoint fumeur (même étude)
    # ln(1.25) = 0.223 → 2 pts
    if patient.tabac_passif == "oui":
        pts = 2
        recommandations.append("Tabagisme passif : l'exposition augmente le risque CV de 25-30% "
                               "(RR 1.25, He et al., NEJM 1999). Éviter les environnements enfumés.")
    else:
        pts = 0
    score += pts
    details.append(("Tabac passif", patient.tabac_passif, pts, 2))

    # ── 8. ALIMENTATION – Fruits & Légumes (0-3 points) ──
    # Absence de consommation quotidienne : OR 1.43 pour infarctus
    # (INTERHEART, Yusuf et al., Lancet 2004)
    # PAR = 13.7% pour l'infarctus au niveau mondial
    # ln(1.43) = 0.358 → 3 pts
    if patient.fruits_legumes == "<2/sem":
        pts = 3
        recommandations.append("Consommer au moins 5 fruits et légumes par jour : "
                               "le manque augmente le risque d'infarctus de 43% (OR 1.43, INTERHEART 2004).")
    elif patient.fruits_legumes == "2-5/sem":
        pts = 2
    elif patient.fruits_legumes == "2-4/jour":
        pts = 1
    else:
        pts = 0
        facteurs_positifs.append("Consommation suffisante de fruits et légumes")
    score += pts
    details.append(("Fruits et légumes", patient.fruits_legumes, pts, 3))

    # ── 9. SEL (0-1 point) ──
    # RR 1.13 (IC 95% 1.06-1.20) pour événements CV (Graudal et al., Nutrients 2020)
    # ln(1.13) = 0.122 → 1 pt
    if patient.ajout_sel == "oui":
        pts = 1
        recommandations.append("Réduire le sel : ne pas resaler les plats. "
                               "L'excès de sel augmente le risque CV de 13% (RR 1.13, Graudal 2020) et l'hypertension de 33%.")
    else:
        pts = 0
    score += pts
    details.append(("Ajout de sel", patient.ajout_sel, pts, 1))

    # ── 10. PRÉPARATION DES REPAS (0-3 points) ──
    # Alimentation ultra-transformée : RR ~1.50 pour événements CV
    # (combinaison sel + graisses saturées + additifs, Micha et al., Circulation 2010)
    # ln(1.50) = 0.405 → 3 pts
    if patient.preparation_repas == "industriel":
        pts = 3
        recommandations.append("Privilégier la cuisine maison : les plats industriels sont riches en sel, sucre et graisses saturées "
                               "(RR ~1.50 pour événements CV, Micha et al., Circulation 2010).")
    elif patient.preparation_repas == "conserves":
        pts = 2
    else:
        pts = 0
        facteurs_positifs.append("Cuisine maison")
    score += pts
    details.append(("Préparation des repas", patient.preparation_repas, pts, 3))

    # ── 11. CHARCUTERIE / FROMAGE (0-3 points) ──
    # Viande transformée : RR 1.42 (IC 95% 1.07-1.89) par 50g/jour pour coronaropathie
    # (Micha et al., Circulation 2010, méta-analyse de 20 études)
    # ln(1.42) = 0.351 → 3 pts
    if patient.charcuterie_fromage == "oui":
        pts = 3
        recommandations.append("Limiter charcuterie et fromage : la viande transformée augmente le risque coronarien de 42% par 50g/jour "
                               "(RR 1.42, Micha et al., Circulation 2010).")
    else:
        pts = 0
    score += pts
    details.append(("Charcuterie/Fromage régulier", patient.charcuterie_fromage, pts, 3))

    # ── 12. STRESS (0-7 points) ──
    # Stress permanent : OR 2.17 pour infarctus
    # (INTERHEART psychosocial, Rosengren et al., Lancet 2004)
    # Facteurs psychosociaux combinés : OR 2.67, PAR = 32.5%
    # ln(2.17) = 0.775 → 7 pts
    if patient.stress == "permanent":
        pts = 7
        recommandations.append("Gérer le stress chronique : le stress permanent multiplie le risque d'infarctus par 2.17 "
                               "(INTERHEART, Rosengren et al., Lancet 2004). "
                               "Méditation, activité physique, suivi psychologique recommandés.")
    elif patient.stress == "occasionnel":
        pts = 3   # ln(1.48) = 0.392 → 3 pts (événements stressants, même étude)
    else:
        pts = 0
        facteurs_positifs.append("Bon niveau de gestion du stress")
    score += pts
    details.append(("Stress", patient.stress, pts, 7))

    # ── COLÈRES / HOSTILITÉ (0-3 points) ──
    # Hostilité chronique : HR 1.19-1.50 pour événements CV
    # (Chida & Steptoe, JACC 2009, méta-analyse de 25 études)
    # Colère aiguë comme déclencheur d'infarctus : OR ~1.5 (INTERHEART)
    # ln(1.5) = 0.405 → 3 pts
    if patient.coleres == "tres_frequent":
        pts = 3
        recommandations.append("Colères fréquentes : l'hostilité chronique augmente le risque CV de 19 à 50% "
                               "(HR 1.19-1.50, Chida & Steptoe, JACC 2009). "
                               "Gestion des émotions, thérapie cognitivo-comportementale recommandées.")
    elif patient.coleres == "frequent":
        pts = 2
        recommandations.append("Colères régulières : apprendre à gérer ses émotions réduit le risque cardiovasculaire.")
    elif patient.coleres == "peu":
        pts = 1
    else:
        pts = 0
    score += pts
    details.append(("Col\xe8res / hostilit\xe9", patient.coleres, pts, 3))

    # ── CHARGE FAMILIALE SEUL(E) (0-2 points) ──
    # Isolement social / stress chronique : HR 1.29 (IC 95% 1.04-1.59)
    # pour événements CV (Valtorta et al., Heart 2016, méta-analyse)
    # Stress psychosocial combiné : facteur aggravant (INTERHEART)
    # ln(1.29) = 0.255 → 2 pts
    if patient.charge_familiale_seule == "oui":
        pts = 2
        recommandations.append("Charge familiale seul(e) : l'isolement et le stress chronique augmentent "
                               "le risque CV de 29% (HR 1.29, Valtorta et al., Heart 2016). "
                               "N'hésitez pas à chercher du soutien.")
    else:
        pts = 0
    score += pts
    details.append(("Charge familiale seul(e)", patient.charge_familiale_seule, pts, 2))

    # ── ALCOOL (0-3 points) ──
    # >2 verres/jour : RR 1.35 pour mortalité (>=65g/jour)
    # (Zhao et al., JAMA Network Open 2023, méta-analyse de 107 cohortes)
    # ln(1.35) = 0.300 → 3 pts
    if patient.alcool_excessif == "oui":
        pts = 3
        recommandations.append("Réduire la consommation d'alcool : l'excès augmente la mortalité de 35% "
                               "(RR 1.35, Zhao et al., JAMA Network Open 2023). Max 2 verres/jour, pas tous les jours.")
    else:
        pts = 0
    score += pts
    details.append(("Alcool excessif", patient.alcool_excessif, pts, 3))

    # ── BOISSONS ÉNERGISANTES (0-1 point) ──
    # Risque d'arythmie, HTA aiguë, tachycardie
    # (Fletcher et al., JACC 2017 ; AHA Scientific Sessions 2019)
    # Effet modeste mais documenté → 1 pt
    if patient.boissons_energisantes == "oui":
        pts = 1
        recommandations.append("Boissons \xe9nergisantes : risque d'arythmie et d'hypertension aigu\xeb "
                               "(Fletcher et al., JACC 2017). \xc0 \xe9viter, surtout en cas de pathologie cardiaque.")
    else:
        pts = 0
    score += pts
    details.append(("Boissons \xe9nergisantes", patient.boissons_energisantes, pts, 1))

    # ── HYPERTENSION (0-10 points) ──
    # PAS >140 : OR 1.91 pour infarctus (INTERHEART, Lancet 2004)
    # Chaque +20 mmHg PAS double le risque de décès coronarien
    # (PSC, Lewington et al., Lancet 2002, 1 million d'adultes, 61 études)
    # PAS 160 vs 120 : HR ~3.5 → ln(3.5) = 1.253 → 10 pts
    # PAS 140-160 : HR ~1.91 → ln(1.91) = 0.647 → 6 pts
    if patient.hypertension == "oui":
        if patient.tension_systolique and patient.tension_systolique >= 160:
            pts = 10
            recommandations.append("Hypertension sévère : chaque +20 mmHg de PAS double le risque de décès coronarien "
                                   "(PSC, Lewington et al., Lancet 2002). Suivi médical urgent. Objectif < 140/90 mmHg.")
        elif patient.tension_systolique and patient.tension_systolique >= 140:
            pts = 6   # ln(1.91) → 6 pts
            recommandations.append("Hypertension confirmée : risque d'infarctus multiplié par 1.91 "
                                   "(INTERHEART, Lancet 2004). Traitement et suivi régulier recommandés.")
        else:
            pts = 4
            recommandations.append("Hypertension diagnostiquée : vérifier régulièrement la tension.")
    else:
        pts = 0
        if patient.tension_systolique and patient.tension_systolique < 120:
            facteurs_positifs.append("Tension artérielle optimale")
    score += pts
    details.append(("Hypertension", patient.hypertension, pts, 10))

    # ── 15. CHOLESTÉROL (0-9 points) ──
    # Quintile supérieur ApoB/ApoA1 : OR 3.25 pour infarctus (INTERHEART, Lancet 2004)
    # PAR = 49.2% pour ratio lipidique anormal
    # Par 1 mmol/L de cholestérol total : HR ~1.52 (50-69 ans, PSC, Lancet 2007)
    # ln(3.25) = 1.179 → 9 pts max
    if patient.cholesterol_eleve == "oui":
        if patient.cholesterol_total and patient.cholesterol_total > 7:
            pts = 9   # ln(3.25) → 9 pts
            recommandations.append("Cholestérol très élevé : le quintile supérieur multiplie le risque d'infarctus par 3.25 "
                                   "(INTERHEART, Lancet 2004). Traitement médical urgent.")
        elif patient.cholesterol_total and patient.cholesterol_total > 5.5:
            pts = 5   # ~ln(1.52) → intermédiaire
            recommandations.append("Cholestérol élevé : chaque +1 mmol/L augmente le risque coronarien de 52% (PSC, Lancet 2007). "
                                   "Adapter l'alimentation et consulter.")
        else:
            pts = 3
            recommandations.append("Cholestérol à surveiller : contrôle biologique annuel recommandé.")
    else:
        pts = 0
    score += pts
    details.append(("Cholestérol élevé", patient.cholesterol_eleve, pts, 9))

    # ── 16. DIABÈTE (0-7 points) ──
    # HR 2.00 (IC 95% 1.83-2.19) pour coronaropathie (ERFC, Lancet 2010, 102 études)
    # INTERHEART : OR 2.37 pour infarctus
    # Femmes : risque relatif encore plus élevé (3-7x, ESC 2021)
    # ln(2.37) = 0.863 → 7 pts max (mal équilibré)
    # ln(2.00) = 0.693 → 6 pts (équilibré)
    if patient.diabete == "oui":
        if patient.glycemie and patient.glycemie > 1.26:
            pts = 7
            recommandations.append("Diabète mal équilibré (glycémie > 1.26 g/L) : "
                                   "le diabète multiplie le risque coronarien par 2.37 (INTERHEART, Lancet 2004). "
                                   "Suivi endocrinologique indispensable.")
        else:
            pts = 6   # ln(2.00) → 6 pts
            recommandations.append("Diabète : le risque coronarien est doublé (HR 2.00, ERFC, Lancet 2010). "
                                   "Équilibre glycémique essentiel.")
    else:
        pts = 0
    score += pts
    details.append(("Diabète", patient.diabete, pts, 7))

    # ── 17. APNÉE DU SOMMEIL (0-5 points) ──
    # HR 1.82 (IC 95% 1.45-2.28) pour événements CV
    # (Dong et al., Int J Cardiol 2013, méta-analyse de 18 cohortes)
    # ln(1.82) = 0.599 → 5 pts
    if patient.apnee_sommeil == "oui":
        pts = 5
        recommandations.append("Apnée du sommeil : risque CV augmenté de 82% (HR 1.82, Dong et al., Int J Cardiol 2013). "
                               "Traitement par PPC recommandé.")
    else:
        pts = 0
    score += pts
    details.append(("Apn\xe9e du sommeil", patient.apnee_sommeil, pts, 5))

    # ── TROUBLES DU SOMMEIL (0-3 points) ──
    # Insomnie chronique : HR 1.45 (IC 95% 1.29-1.62) pour événements CV
    # (He et al., Eur J Prev Cardiol 2017, méta-analyse de 15 études)
    # Durée de sommeil <6h : HR 1.48 (Cappuccio et al., Eur Heart J 2011)
    # ln(1.45) = 0.372 → 3 pts
    if patient.troubles_sommeil == "oui":
        pts = 3
        recommandations.append("Troubles du sommeil : l'insomnie chronique augmente le risque CV de 45% "
                               "(HR 1.45, He et al., Eur J Prev Cardiol 2017). "
                               "Consultation sp\xe9cialis\xe9e recommand\xe9e, hygi\xe8ne du sommeil \xe0 am\xe9liorer.")
    else:
        pts = 0
    score += pts
    details.append(("Troubles du sommeil", patient.troubles_sommeil, pts, 3))

    # ── TOTAL ET CLASSIFICATION ──
    # Score maximum théorique : 108 points
    score_max = sum(d[3] for d in details)
    score_normalise = (score / score_max) * 100

    if score_normalise < 15:
        categorie = "Risque faible"
        couleur = "vert"
    elif score_normalise < 30:
        categorie = "Risque faible à modéré"
        couleur = "vert_jaune"
    elif score_normalise < 50:
        categorie = "Risque modéré"
        couleur = "jaune"
    elif score_normalise < 65:
        categorie = "Risque modéré à élevé"
        couleur = "orange"
    elif score_normalise < 80:
        categorie = "Risque élevé"
        couleur = "rouge"
    else:
        categorie = "Risque très élevé"
        couleur = "rouge_fonce"

    # Trier les recommandations par priorité (tabac en premier)
    if not recommandations:
        recommandations.append("Continuez ainsi ! Votre mode de vie est favorable à votre santé cardiovasculaire.")

    return {
        "mode": "Qualitatif",
        "score_brut": score,
        "score_max": score_max,
        "score_normalise": round(score_normalise, 1),
        "categorie": categorie,
        "couleur": couleur,
        "details": details,
        "recommandations": recommandations,
        "facteurs_positifs": facteurs_positifs,
        "imc": round(imc, 1),
        "categorie_imc": categorie_imc(imc),
    }


# ============================================================================
# ÉVALUATION COMBINÉE
# ============================================================================

def evaluer_risque(patient: PatientData) -> dict:
    """
    Évaluation complète du risque cardiovasculaire.
    - Si les données médicales sont disponibles → SCORE2 + Qualitatif
    - Sinon → Qualitatif seul
    """
    resultat = {}

    # Toujours calculer le score qualitatif
    resultat["qualitatif"] = score_qualitatif(patient)

    # Tenter le SCORE2 si les données sont disponibles
    score2 = calcul_score2(patient)
    if score2:
        resultat["score2"] = score2

    return resultat


# ============================================================================
# QUESTIONNAIRE INTERACTIF
# ============================================================================

def poser_question(question: str, options: dict, allow_empty: bool = False) -> str:
    """Poser une question avec des options numérotées."""
    print(f"\n  {question}")
    keys = list(options.keys())
    for i, (key, label) in enumerate(options.items(), 1):
        print(f"    {i}. {label}")
    while True:
        reponse = input("  > Votre choix : ").strip()
        if allow_empty and reponse == "":
            return ""
        try:
            idx = int(reponse)
            if 1 <= idx <= len(keys):
                return keys[idx - 1]
        except ValueError:
            pass
        print(f"    Veuillez entrer un nombre entre 1 et {len(keys)}")


def poser_nombre(question: str, min_val: float = 0, max_val: float = 999,
                 allow_empty: bool = False) -> Optional[float]:
    """Poser une question attendant un nombre."""
    print(f"\n  {question}")
    while True:
        reponse = input("  > ").strip()
        if allow_empty and reponse == "":
            return None
        try:
            val = float(reponse.replace(",", "."))
            if min_val <= val <= max_val:
                return val
            else:
                print(f"    Valeur entre {min_val} et {max_val} attendue.")
        except ValueError:
            print("    Veuillez entrer un nombre valide.")


def questionnaire_interactif() -> PatientData:
    """Questionnaire interactif complet – 25 questions."""
    patient = PatientData()

    print("\n" + "=" * 70)
    print("  COMMENT VA VOTRE COEUR ?")
    print("  Évaluation du Risque Cardiovasculaire")
    print("=" * 70)

    # ── PARTIE 1 : PROFIL ──
    print("\n" + "─" * 40)
    print("  PARTIE 1 : VOTRE PROFIL")
    print("─" * 40)

    patient.sexe = poser_question(
        "Quel est votre sexe ?",
        {"H": "Homme", "F": "Femme"}
    )
    patient.age = int(poser_nombre("Quel est votre âge ?", 18, 100))
    patient.poids = poser_nombre("Quel est votre poids (en kg) ?", 30, 300)
    patient.taille = poser_nombre("Quelle est votre taille (en cm) ?", 100, 250)

    # ── PARTIE 2 : HÉRÉDITÉ ──
    print("\n" + "─" * 40)
    print("  PARTIE 2 : HÉRÉDITÉ")
    print("─" * 40)

    patient.antecedents_familiaux = poser_question(
        "Un membre de votre famille proche a-t-il eu un problème cardiaque\n"
        "  avant 55 ans (homme) ou 65 ans (femme) ?",
        {"oui": "Oui", "non": "Non", "ne_sais_pas": "Je ne sais pas"}
    )

    patient.bilan_cardiaque = poser_question(
        "Avez-vous déjà effectué un bilan cardiaque ?",
        {"oui": "Oui", "non": "Non"}
    )

    patient.consultation_cardiologue = poser_question(
        "Avez-vous déjà consulté un cardiologue ?",
        {"oui": "Oui", "non": "Non"}
    )

    # ── PARTIE 3 : MODE DE VIE ──
    print("\n" + "─" * 40)
    print("  PARTIE 3 : MODE DE VIE")
    print("─" * 40)

    patient.activite_weekend = poser_question(
        "Parmi les activités suivantes, laquelle pratiqueriez-vous le plus facilement pendant vos weekends ?",
        {
            "television": "Regarder la télévision",
            "promenade": "Vous promener",
            "jeux_videos": "Jouer à des jeux vidéos",
            "sport": "Faire du sport",
        }
    )

    patient.heures_assis = poser_question(
        "Combien d'heures par jour passez-vous assis(e) ?",
        {"<3h": "Moins de 3 heures", "3-7h": "Entre 3 et 7 heures", ">7h": "Plus de 7 heures"}
    )

    patient.activite_physique = poser_question(
        "Combien de temps d'activité physique pratiquez-vous par jour ?",
        {"<30min": "Moins de 30 minutes", "~30min": "Environ 30 minutes", ">30min": "Plus de 30 minutes"}
    )

    patient.tabac = poser_question(
        "Fumez-vous ?",
        {"oui": "Oui, actuellement", "ancien_5ans": "Non, arrêté depuis moins de 5 ans", "non": "Non / Arrêté depuis plus de 5 ans"}
    )

    patient.tabac_passif = poser_question(
        "Une ou d'autres personnes fument-elles à votre domicile ?",
        {"oui": "Oui", "non": "Non"}
    )

    patient.fruits_legumes = poser_question(
        "Quelle est votre consommation de fruits et légumes ?",
        {"<2/sem": "Moins de 2 portions/semaine",
         "2-5/sem": "2 à 5 portions/semaine",
         "2-4/jour": "2 à 4 portions/jour",
         "5+/jour": "5 portions ou plus/jour"}
    )

    patient.ajout_sel = poser_question(
        "Ajoutez-vous du sel à vos plats ?",
        {"oui": "Oui, régulièrement", "non": "Non / Rarement"}
    )

    patient.preparation_repas = poser_question(
        "Comment sont préparés vos repas principalement ?",
        {"industriel": "Plats industriels / fast-food",
         "maison": "Cuisine maison",
         "conserves": "Conserves / plats en boîte"}
    )

    patient.charcuterie_fromage = poser_question(
        "Consommez-vous régulièrement de la charcuterie et/ou du fromage ?",
        {"oui": "Oui, presque tous les jours", "non": "Non / Occasionnellement"}
    )

    patient.stress = poser_question(
        "Comment évaluez-vous votre niveau de stress ?",
        {"jamais": "Rarement stressé(e)", "occasionnel": "Parfois stressé(e)", "permanent": "Stress permanent"}
    )

    patient.coleres = poser_question(
        "Êtes-vous sujet à des colères ?",
        {"jamais": "Jamais", "peu": "Peu", "frequent": "De façon fréquente", "tres_frequent": "De façon très fréquente"}
    )

    patient.charge_familiale_seule = poser_question(
        "Gérez-vous seul(e) votre environnement familial ?",
        {"oui": "Oui", "non": "Non"}
    )

    patient.alcool_excessif = poser_question(
        "Vous arrive-t-il de boire plus de 3 verres d'alcool dans la journée\n"
        "  1 à 2 fois par semaine (vin et bière compris) ?",
        {"oui": "Oui", "non": "Non"}
    )

    patient.boissons_energisantes = poser_question(
        "Vous arrive-t-il de boire des boissons énergisantes ?",
        {"oui": "Oui", "non": "Non"}
    )

    # ── PARTIE 4 : DONNÉES MÉDICALES ──
    print("\n" + "─" * 40)
    print("  PARTIE 4 : DONNÉES MÉDICALES")
    print("  (Si vous ne connaissez pas une valeur,")
    print("   appuyez sur Entrée pour passer)")
    print("─" * 40)

    patient.hypertension = poser_question(
        "Avez-vous été diagnostiqué(e) hypertendu(e) ?",
        {"oui": "Oui", "non": "Non"}
    )

    print("\n  Connaissez-vous votre tension artérielle ?")
    patient.tension_systolique = poser_nombre(
        "Tension systolique (le chiffre du haut, ex: 120) en mmHg :",
        60, 250, allow_empty=True
    )
    if patient.tension_systolique:
        patient.tension_diastolique = poser_nombre(
            "Tension diastolique (le chiffre du bas, ex: 80) en mmHg :",
            30, 150, allow_empty=True
        )

    patient.cholesterol_eleve = poser_question(
        "Avez-vous un cholestérol élevé ?",
        {"oui": "Oui", "non": "Non"}
    )

    print("\n  Connaissez-vous vos valeurs de cholestérol ? (en mmol/L)")
    patient.cholesterol_total = poser_nombre(
        "Cholestérol total (ex: 5.2) en mmol/L :",
        1, 15, allow_empty=True
    )
    if patient.cholesterol_total:
        patient.cholesterol_ldl = poser_nombre(
            "Cholestérol LDL (ex: 3.0) en mmol/L :",
            0.5, 10, allow_empty=True
        )
        patient.cholesterol_hdl = poser_nombre(
            "Cholestérol HDL (ex: 1.5) en mmol/L :",
            0.3, 5, allow_empty=True
        )

    patient.diabete = poser_question(
        "Êtes-vous diabétique ?",
        {"oui": "Oui", "non": "Non"}
    )

    patient.glycemie = poser_nombre(
        "Connaissez-vous votre glycémie à jeun (en g/L, ex: 0.95) ?",
        0.3, 5, allow_empty=True
    )

    patient.apnee_sommeil = poser_question(
        "Souffrez-vous d'apnée du sommeil ?",
        {"oui": "Oui", "non": "Non"}
    )

    patient.troubles_sommeil = poser_question(
        "Êtes-vous sujet à des troubles du sommeil (insomnie, réveils nocturnes,\n"
        "  moins de 7h de sommeil par nuit) ?",
        {"oui": "Oui", "non": "Non"}
    )

    return patient


# ============================================================================
# GÉNÉRATION DU RAPPORT PDF
# ============================================================================

class RapportPDF(FPDF):
    """Générateur de rapport PDF cardiovasculaire."""

    COULEURS = {
        "vert":        (46, 139, 87),
        "vert_jaune":  (154, 205, 50),
        "jaune":       (255, 193, 7),
        "orange":      (255, 140, 0),
        "rouge":       (220, 53, 69),
        "rouge_fonce": (139, 0, 0),
        "bleu":        (41, 98, 255),
        "bleu_clair":  (100, 149, 237),
        "gris":        (108, 117, 125),
        "gris_clair":  (248, 249, 250),
    }

    def __init__(self):
        super().__init__()
        self.set_margins(12, 12, 12)
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, "Comment va votre coeur ? - Evaluation cardiovasculaire", align="C")
        self.ln(2)
        self.set_draw_color(225, 225, 225)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(135, 135, 135)
        date_generation = datetime.now().strftime("%d/%m/%Y a %H:%M")
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}} | "
                  f"G\xe9n\xe9r\xe9 le {date_generation} | "
                  "Algorithme SCORE2 (ESC 2021) & mod\xe8le qualitatif", align="C")

    def titre_principal(self):
        self.add_page()
        self.ln(10)

        # Coeur stylisé avec texte
        # Coeur dessiné
        cx, cy = 105, self.get_y() + 15
        r = 8
        self.set_fill_color(220, 40, 60)
        self.set_draw_color(220, 40, 60)
        self.ellipse(cx - r, cy - r, r * 2, r * 2, "F")
        self.ln(25)

        self.set_font("Helvetica", "B", 26)
        self.set_text_color(33, 37, 41)
        self.cell(0, 15, "COMMENT VA VOTRE COEUR ?", align="C")
        self.ln(12)

        self.set_font("Helvetica", "", 14)
        self.set_text_color(108, 117, 125)
        self.cell(0, 8, "Rapport d'\xc9valuation du Risque Cardiovasculaire", align="C")
        self.ln(5)
        self.cell(0, 8, f"Date : {datetime.now().strftime('%d %B %Y')}", align="C")
        self.ln(15)

        # Cadre d'avertissement
        self.set_fill_color(255, 243, 205)
        self.set_draw_color(255, 193, 7)
        self.set_text_color(133, 100, 4)
        self.set_font("Helvetica", "B", 9)
        y = self.get_y()
        self.rect(15, y, 180, 22, "DF")
        self.set_xy(20, y + 3)
        self.cell(170, 5, "AVERTISSEMENT", align="C")
        self.set_font("Helvetica", "", 8)
        self.set_xy(20, y + 9)
        self.multi_cell(170, 4,
            "Ce rapport est \xe0 titre informatif et p\xe9dagogique uniquement. "
            "Il ne remplace en aucun cas une consultation m\xe9dicale. "
            "Consultez votre m\xe9decin pour une \xe9valuation personnalis\xe9e de votre risque cardiovasculaire.",
            align="C")
        self.ln(8)

    def section_resume_executif(self, resultats: dict):
        """Ajoute une synthese rapide lisible en 1 minute."""
        qual = resultats["qualitatif"]
        score2 = resultats.get("score2")

        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.COULEURS["bleu"])
        self.cell(0, 10, "1. SYNTHESE RAPIDE", ln=True)
        self.ln(2)

        # Cartouche principal
        couleur = self.COULEURS.get(qual.get("couleur", "gris"), self.COULEURS["gris"])
        y = self.get_y()
        self.set_fill_color(*couleur)
        self.rect(20, y, 170, 24, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 15)
        self.set_xy(20, y + 2)
        self.cell(170, 8, f"Risque global : {qual['categorie']}", align="C")
        self.set_font("Helvetica", "", 11)
        self.set_xy(20, y + 12)
        self.cell(170, 8, f"IMC : {qual['imc']} ({qual['categorie_imc']})", align="C")
        self.set_y(y + 28)

        self.set_text_color(80, 80, 80)
        self.set_font("Helvetica", "", 10)
        if score2:
            self.multi_cell(
                0,
                5,
                f"SCORE2 ({score2['mode']}) : {score2['risque_pct']}% a 10 ans ({score2['categorie']}).",
            )
        else:
            self.multi_cell(
                0,
                5,
                "SCORE2 non calcule (donnees medicales insuffisantes). Le score qualitatif reste interpretable.",
            )
        self.ln(2)

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(33, 37, 41)
        self.cell(0, 7, "Top 3 actions prioritaires :", ln=True)
        self.ln(1)

        self.set_font("Helvetica", "", 10)
        recos = resultats["qualitatif"].get("recommandations", [])
        for i, reco in enumerate(recos[:3], 1):
            self.cell(5)
            self.multi_cell(185, 5, f"{i}. {reco}")

        if not recos:
            self.cell(5)
            self.multi_cell(185, 5, "1. Continuez ainsi : votre profil actuel est favorable.")

        self.ln(4)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.multi_cell(
            0,
            4,
            "Document de prevention : il ne remplace pas un avis medical. "
            "En cas de symptomes, consultez votre medecin traitant ou un cardiologue.",
        )
        self.ln(4)

    def section_profil(self, patient: PatientData, imc: float, cat_imc: str):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.COULEURS["bleu"])
        self.cell(0, 10, "2. PROFIL DU PATIENT", ln=True)
        self.ln(3)

        # Tableau profil
        donnees = [
            ("Sexe", "Homme" if patient.sexe == "H" else "Femme"),
            ("\xc2ge", f"{patient.age} ans"),
            ("Poids", f"{patient.poids} kg"),
            ("Taille", f"{patient.taille} cm"),
            ("IMC", f"{imc:.1f} kg/m2 ({cat_imc})"),
        ]
        if patient.tension_systolique:
            ta = f"{int(patient.tension_systolique)}"
            if patient.tension_diastolique:
                ta += f"/{int(patient.tension_diastolique)}"
            ta += " mmHg"
            donnees.append(("Tension art\xe9rielle", ta))
        if patient.cholesterol_total:
            donnees.append(("Cholest\xe9rol total", f"{patient.cholesterol_total} mmol/L"))
        if patient.cholesterol_hdl:
            donnees.append(("Cholest\xe9rol HDL", f"{patient.cholesterol_hdl} mmol/L"))
        if patient.glycemie:
            donnees.append(("Glyc\xe9mie \xe0 jeun", f"{patient.glycemie} g/L"))

        self.set_font("Helvetica", "", 10)
        for i, (label, valeur) in enumerate(donnees):
            if i % 2 == 0:
                self.set_fill_color(*self.COULEURS["gris_clair"])
            else:
                self.set_fill_color(255, 255, 255)
            self.set_text_color(80, 80, 80)
            self.set_font("Helvetica", "B", 10)
            self.cell(70, 9, f"  {label}", fill=True)
            self.set_font("Helvetica", "", 10)
            self.set_text_color(33, 37, 41)
            self.cell(120, 9, f"  {valeur}", fill=True, ln=True)
        self.ln(8)

    def section_score2(self, resultat: dict):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.COULEURS["bleu"])
        self.cell(0, 10, f"3. RISQUE SCORE2 ({resultat['mode']})", ln=True)
        self.ln(3)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5,
            "Le SCORE2 (Systematic Coronary Risk Evaluation 2) est l'algorithme de r\xe9f\xe9rence "
            "de la Soci\xe9t\xe9 Europ\xe9enne de Cardiologie (ESC 2021) pour estimer le risque "
            "\xe0 10 ans d'\xe9v\xe9nement cardiovasculaire majeur (d\xe9c\xe8s CV, infarctus, AVC) "
            "chez les personnes sans ant\xe9c\xe9dent cardiovasculaire.")
        self.ln(5)

        # Grand encadré résultat
        couleur = self.COULEURS.get(resultat["couleur"], self.COULEURS["gris"])
        y = self.get_y()
        self.set_fill_color(*couleur)
        self.rect(30, y, 150, 30, "F")

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 24)
        self.set_xy(30, y + 3)
        self.cell(150, 12, f"{resultat['risque_pct']}%", align="C")
        self.set_font("Helvetica", "B", 12)
        self.set_xy(30, y + 17)
        self.cell(150, 10, f"Risque \xe0 10 ans : {resultat['categorie']}", align="C")
        self.set_y(y + 35)
        self.ln(3)

        # Échelle visuelle
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, "\xc9chelle de risque :", ln=True)

        y = self.get_y()
        bar_x = 30
        bar_w = 150
        bar_h = 8

        # Dégradé vert → jaune → orange → rouge
        segments = [
            (self.COULEURS["vert"], 0.3),
            (self.COULEURS["jaune"], 0.25),
            (self.COULEURS["orange"], 0.25),
            (self.COULEURS["rouge"], 0.2),
        ]
        x = bar_x
        for color, frac in segments:
            w = bar_w * frac
            self.set_fill_color(*color)
            self.rect(x, y, w, bar_h, "F")
            x += w

        # Marqueur position
        max_risk = 30
        pos = min(resultat["risque_pct"] / max_risk, 1.0)
        marker_x = bar_x + pos * bar_w
        self.set_fill_color(33, 37, 41)
        self.set_draw_color(255, 255, 255)
        # Triangle marker
        self.rect(marker_x - 1, y - 2, 3, bar_h + 4, "DF")

        self.set_y(y + bar_h + 2)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(120, 120, 120)
        self.cell(bar_w * 0.3, 4, "Faible", align="C")
        self.cell(bar_w * 0.25, 4, "Mod\xe9r\xe9", align="C")
        self.cell(bar_w * 0.25, 4, "\xc9lev\xe9", align="C")
        self.cell(bar_w * 0.2, 4, "Tr\xe8s \xe9lev\xe9", align="C")
        self.ln(8)

    def section_qualitatif(self, resultat: dict, has_score2: bool):
        num = "4" if has_score2 else "3"
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.COULEURS["bleu"])
        self.cell(0, 10, f"{num}. \xc9VALUATION QUALITATIVE MULTI-FACTEURS", ln=True)
        self.ln(3)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5,
            "Cette \xe9valuation prend en compte l'ensemble de vos facteurs de risque "
            "(mode de vie, ant\xe9c\xe9dents, donn\xe9es m\xe9dicales) pour \xe9tablir un profil "
            "de risque global bas\xe9 sur les donn\xe9es \xe9pid\xe9miologiques internationales.")
        self.ln(5)

        # Résultat principal
        couleur = self.COULEURS.get(resultat["couleur"], self.COULEURS["gris"])
        y = self.get_y()
        self.set_fill_color(*couleur)
        self.rect(30, y, 150, 25, "F")

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 18)
        self.set_xy(30, y + 2)
        self.cell(150, 10, resultat["categorie"].upper(), align="C")
        self.set_font("Helvetica", "", 11)
        self.set_xy(30, y + 13)
        self.cell(150, 8,
                  f"Score : {resultat['score_brut']}/{resultat['score_max']} "
                  f"({resultat['score_normalise']}%)", align="C")
        self.set_y(y + 30)
        self.ln(3)

        # Détail par facteur
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(33, 37, 41)
        self.cell(0, 8, "D\xe9tail par facteur de risque :", ln=True)
        self.ln(2)

        self.set_font("Helvetica", "B", 8.5)
        self.set_fill_color(41, 98, 255)
        self.set_text_color(255, 255, 255)
        self.cell(58, 8, "  FACTEUR", fill=True)
        self.cell(52, 8, "  VALEUR", fill=True)
        self.cell(28, 8, "  POINTS", fill=True, align="C")
        self.cell(52, 8, "  JAUGE", fill=True, ln=True)

        self.set_font("Helvetica", "", 8.5)
        for i, (facteur, valeur, pts, pts_max) in enumerate(resultat["details"]):
            if i % 2 == 0:
                self.set_fill_color(*self.COULEURS["gris_clair"])
            else:
                self.set_fill_color(255, 255, 255)

            self.set_text_color(60, 60, 60)
            self.cell(58, 8, f"  {facteur}", fill=True)

            val_str = str(valeur)
            if len(val_str) > 32:
                val_str = val_str[:29] + "..."
            self.cell(52, 8, f"  {val_str}", fill=True)

            self.set_text_color(33, 37, 41)
            self.set_font("Helvetica", "B", 8.5)
            self.cell(28, 8, f"{pts}/{pts_max}", fill=True, align="C")

            # Mini jauge
            self.set_font("Helvetica", "", 8.5)
            gauge_y = self.get_y() + 2.5
            gauge_x = self.get_x() + 2
            gauge_w = 48
            gauge_h = 3

            self.set_fill_color(230, 230, 230)
            self.rect(gauge_x, gauge_y, gauge_w, gauge_h, "F")

            if pts_max > 0:
                ratio = pts / pts_max
                if ratio < 0.3:
                    gc = self.COULEURS["vert"]
                elif ratio < 0.6:
                    gc = self.COULEURS["jaune"]
                else:
                    gc = self.COULEURS["rouge"]
                self.set_fill_color(*gc)
                self.rect(gauge_x, gauge_y, gauge_w * ratio, gauge_h, "F")

            self.cell(52, 8, "", fill=False, ln=True)

        self.ln(5)

    def section_facteurs_positifs(self, facteurs: list):
        if not facteurs:
            return

        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*self.COULEURS["vert"])
        self.cell(0, 8, "VOS POINTS FORTS", ln=True)
        self.ln(2)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(46, 139, 87)
        for f in facteurs:
            self.cell(5)
            self.cell(0, 6, f"  + {f}", ln=True)
        self.ln(5)

    def section_recommandations(self, recommandations: list, num: str):
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.COULEURS["bleu"])
        self.cell(0, 10, f"{num}. RECOMMANDATIONS PERSONNALIS\xc9ES", ln=True)
        self.ln(3)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5,
            "Voici les actions prioritaires pour am\xe9liorer votre sant\xe9 cardiovasculaire, "
            "class\xe9es par ordre d'impact :")
        self.ln(4)

        if not recommandations:
            recommandations = ["Continuez ainsi : votre mode de vie est favorable a votre sante cardiovasculaire."]

        for i, reco in enumerate(recommandations, 1):
            y = self.get_y()
            lines = self._count_lines(reco, 162)
            box_h = max(14, 8 + lines * 5)
            if y + box_h > 270:
                self.add_page()
                y = self.get_y()

            self.set_fill_color(246, 248, 252)
            self.set_draw_color(210, 220, 235)
            self.rect(14, y, 182, box_h, "DF")

            self.set_xy(18, y + 3)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*self.COULEURS["bleu"])
            self.cell(10, 5, f"{i}.")

            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(40, 40, 40)
            self.multi_cell(166, 5, reco)
            self.set_y(y + box_h + 3)

        self.ln(5)

    def _count_lines(self, text: str, width: float) -> int:
        """Estime le nombre de lignes pour un texte donné."""
        self.set_font("Helvetica", "", 9)
        words = text.split()
        line = ""
        count = 1
        for word in words:
            test = line + " " + word if line else word
            if self.get_string_width(test) > width:
                count += 1
                line = word
            else:
                line = test
        return count

    def section_methodologie(self, num: str):
        self.add_page()
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*self.COULEURS["bleu"])
        self.cell(0, 10, f"{num}. M\xc9THODOLOGIE & R\xc9F\xc9RENCES", ln=True)
        self.ln(5)

        # SCORE2
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(33, 37, 41)
        self.cell(0, 8, "Algorithme SCORE2 (mode quantitatif)", ln=True)
        self.ln(2)

        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        texte_score2 = (
            "SCORE2 (Systematic Coronary Risk Evaluation 2) est un algorithme d\xe9velopp\xe9, "
            "calibr\xe9 et valid\xe9 par la Soci\xe9t\xe9 Europ\xe9enne de Cardiologie (ESC) pour pr\xe9dire le "
            "risque \xe0 10 ans d'un premier \xe9v\xe9nement cardiovasculaire dans les populations "
            "europ\xe9ennes. Le mod\xe8le utilise 5 variables : \xe2ge, statut tabagique, pression "
            "art\xe9rielle systolique, cholest\xe9rol total et cholest\xe9rol HDL.\n\n"
            "Il est calibr\xe9 pour 4 r\xe9gions de risque en Europe. La France appartient \xe0 la "
            "r\xe9gion \xe0 bas risque. Les coefficients utilis\xe9s sont issus de la publication "
            "originale dans le European Heart Journal (2021).\n\n"
            "Pour les patients de 70-89 ans, le mod\xe8le SCORE2-OP (Older Persons) est utilis\xe9, "
            "avec des coefficients adapt\xe9s \xe0 cette tranche d'\xe2ge.\n\n"
            "Formule : Risque = 1 - S0^exp(LP) puis calibration r\xe9gionale\n"
            "o\xf9 LP = somme des (coefficient x variable centr\xe9e)\n"
            "et S0 = survie de base \xe0 10 ans."
        )
        self.multi_cell(0, 4.5, texte_score2)
        self.ln(5)

        # Seuils
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(33, 37, 41)
        self.cell(0, 7, "Seuils de risque SCORE2 :", ln=True)
        self.ln(2)

        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(41, 98, 255)
        self.set_text_color(255, 255, 255)
        self.cell(50, 6, "  TRANCHE D'\xc2GE", fill=True)
        self.cell(45, 6, "  FAIBLE-MOD\xc9R\xc9", fill=True, align="C")
        self.cell(45, 6, "  \xc9LEV\xc9", fill=True, align="C")
        self.cell(45, 6, "  TR\xc8S \xc9LEV\xc9", fill=True, ln=True, align="C")

        seuils = [
            ("< 50 ans (SCORE2)", "< 2.5%", "2.5 - 7.5%", ">= 7.5%"),
            ("50-69 ans (SCORE2)", "< 5%", "5 - 10%", ">= 10%"),
            (">= 70 ans (SCORE2-OP)", "< 7.5%", "7.5 - 15%", ">= 15%"),
        ]

        self.set_font("Helvetica", "", 8)
        for i, (tranche, faible, eleve, tres_eleve) in enumerate(seuils):
            bg = self.COULEURS["gris_clair"] if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(60, 60, 60)
            self.cell(50, 6, f"  {tranche}", fill=True)
            self.set_text_color(*self.COULEURS["vert"])
            self.cell(45, 6, f"  {faible}", fill=True, align="C")
            self.set_text_color(*self.COULEURS["orange"])
            self.cell(45, 6, f"  {eleve}", fill=True, align="C")
            self.set_text_color(*self.COULEURS["rouge"])
            self.cell(45, 6, f"  {tres_eleve}", fill=True, align="C", ln=True)
        self.ln(8)

        # Mode qualitatif
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(33, 37, 41)
        self.cell(0, 8, "Mod\xe8le qualitatif multi-facteurs (mode p\xe9dagogique)", ln=True)
        self.ln(2)

        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        texte_quali = (
            "Le mode qualitatif \xe9value 23 facteurs de risque pond\xe9r\xe9s proportionnellement "
            "au logarithme du risque relatif (ln(RR)) publi\xe9 dans la litt\xe9rature m\xe9dicale. "
            "Les sources incluent INTERHEART (Lancet 2004, 52 pays), la Prospective Studies "
            "Collaboration (Lancet 2002, 1M adultes), l'Emerging Risk Factors Collaboration "
            "(Lancet 2010, 102 \xe9tudes) et d'autres m\xe9ta-analyses de r\xe9f\xe9rence.\n\n"
            "Les facteurs \xe9valu\xe9s couvrent : le profil (\xe2ge, sexe, IMC), l'h\xe9r\xe9dit\xe9, "
            "le mode de vie (s\xe9dentarit\xe9, activit\xe9 physique, tabac, alimentation, stress, "
            "col\xe8res, alcool, sommeil) et les donn\xe9es m\xe9dicales (HTA, cholest\xe9rol, diab\xe8te, apn\xe9e).\n\n"
            "Chaque facteur re\xe7oit un score de 0 (pas de risque) au maximum de sa "
            "pond\xe9ration. Le score total est normalis\xe9 sur 100 et class\xe9 en 6 cat\xe9gories "
            "de risque."
        )
        self.multi_cell(0, 4.5, texte_quali)
        self.ln(5)

        # Pondérations
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(33, 37, 41)
        self.cell(0, 7, "Pond\xe9rations des facteurs :", ln=True)
        self.ln(2)

        # Liste des 23 facteurs calculés dans score_qualitatif()
        ponderations = [
            ("Âge", "14 pts", "HR ~2.5/décennie (PSC, Lancet 2002)"),
            ("Hypertension", "10 pts", "HR 2x-4x (PSC, Lancet 2002)"),
            ("Tabac actif", "9 pts", "OR 2.87 (INTERHEART, Lancet 2004)"),
            ("Cholestérol", "9 pts", "OR 3.25 top quintile (INTERHEART 2004)"),
            ("Stress", "7 pts", "OR 2.17 (INTERHEART, Lancet 2004)"),
            ("Diabète", "7 pts", "HR 2.00 (ERFC, Lancet 2010)"),
            ("IMC / Obésité", "6 pts", "HR 1.69 (97 cohortes, Lancet 2014)"),
            ("Ancien fumeur <5 ans", "5 pts", "Risque résiduel ~50% (Kenfield, JAMA 2008)"),
            ("Sédentarité", "5 pts", "HR 1.90 (AHA, Circulation 2016)"),
            ("Antécédents familiaux", "5 pts", "HR 1.74 (EPIC-Norfolk, Heart 2011)"),
            ("Sexe", "5 pts", "HR ~2.0 H vs F (EPIC-Norfolk 2024)"),
            ("Apnée du sommeil", "5 pts", "HR 1.82 (Dong, Int J Cardiol 2013)"),

            ("Colères / hostilité", "3 pts", "HR 1.19-1.50 (Chida, JACC 2009)"),
            ("Troubles du sommeil", "3 pts", "HR 1.45 (He, Eur J Prev Cardiol 2017)"),

            ("Fruits et légumes", "3 pts", "OR 1.43 (INTERHEART, Lancet 2004)"),
            ("Ajout de sel", "1 pt", "RR 1.13 (Graudal, Nutrients 2020)"),
            ("Préparation des repas", "3 pts", "RR ~1.50 (Micha et al., Circulation 2010)"),
            ("Charcuterie/Fromage régulier", "3 pts", "RR 1.42 (Micha et al., Circulation 2010)"),

            ("Charge familiale seul(e)", "2 pts", "HR 1.29 (Valtorta, Heart 2016)"),
            ("Alcool excessif", "3 pts", "RR 1.35 (Zhao, JAMA Network Open 2023)"),

            ("Tabac passif", "2 pts", "RR 1.25 (He, NEJM 1999)"),
            ("Activité physique", "2 pts", "HR 1.24 indépendant (Li & Siegrist, 2012)"),
            ("Boissons énergisantes", "1 pt", "Risque d'arythmie / HTA aiguë (Fletcher, JACC 2017)"),
        ]

        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(41, 98, 255)
        self.set_text_color(255, 255, 255)
        self.cell(55, 5, "  FACTEUR", fill=True)
        self.cell(20, 5, "  POIDS", fill=True, align="C")
        self.cell(115, 5, "  JUSTIFICATION", fill=True, ln=True)

        self.set_font("Helvetica", "", 7)
        for i, (facteur, poids, justif) in enumerate(ponderations):
            bg = self.COULEURS["gris_clair"] if i % 2 == 0 else (255, 255, 255)
            self.set_fill_color(*bg)
            self.set_text_color(60, 60, 60)
            self.cell(55, 5, f"  {facteur}", fill=True)
            self.set_font("Helvetica", "B", 7)
            self.cell(20, 5, f"  {poids}", fill=True, align="C")
            self.set_font("Helvetica", "", 7)
            self.cell(115, 5, f"  {justif}", fill=True, ln=True)
        self.ln(8)

        # Références
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(33, 37, 41)
        self.cell(0, 8, "R\xe9f\xe9rences", ln=True)
        self.ln(2)

        refs = [
            "1. SCORE2 Working Group (ESC). Eur Heart J, 2021;42(25):2439-2454.",
            "2. SCORE2-OP Working Group (ESC). Eur Heart J, 2021;42(25):2455-2467.",
            "3. 2021 ESC Guidelines on cardiovascular disease prevention. Eur Heart J, 2021.",
            "4. INTERHEART (Yusuf et al., Lancet 2004) - 52 pays, 27 000 sujets.",
            "5. Prospective Studies Collaboration (Lewington et al., Lancet 2002) - 1M adultes.",
            "6. Emerging Risk Factors Collaboration (Lancet 2010) - 102 études prospectives.",
            "7. Young et al., AHA Science Advisory. Circulation 2016 (sédentarité).",
            "8. Micha et al., Circulation 2010 (alimentation ultra-transformée / viande transformée).",
            "9. Dong et al., Int J Cardiol 2013 (apnée du sommeil).",
            "10. He et al., NEJM 1999 (tabagisme passif).",
            "11. He et al., Eur J Prev Cardiol 2017 (insomnie / troubles du sommeil).",
            "12. Cappuccio et al., Eur Heart J 2011 (durée de sommeil < 6h, synthèses).",
            "13. Chida & Steptoe, JACC 2009 (hostilité / colères).",
            "14. Valtorta et al., Heart 2016 (isolement social).",
            "15. Rosengren et al., Lancet 2004 (facteurs psychosociaux, INTERHEART).",
            "16. Kenfield et al., JAMA 2008 (ancien tabac < 5 ans).",
            "17. Li & Siegrist, Int J Environ Res Public Health 2012 (activité physique).",
            "18. Graudal et al., Nutrients 2020 (sel).",
            "19. Zhao et al., JAMA Network Open 2023 (alcool).",
            "20. Fletcher et al., JACC 2017 (boissons énergisantes).",
            "21. EPIC-Norfolk, Heart 2011 (antécédents familiaux).",
            "22. EPIC-Norfolk, Eur J Prev Cardiol 2024 (sexe / hérédité).",
            "23. Pooled analyses, Lancet 2014 (IMC / surpoids, cohortes).",
            "24. Global BMI Mortality Collaboration, Lancet 2016 (obésité sévère).",
            "25. Prospective Studies Collaboration, Lancet 2007 (cholestérol total par mmol/L).",
        ]

        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        for ref in refs:
            self.cell(5)
            self.cell(0, 5, ref, ln=True)


def generer_pdf(patient: PatientData, resultats: dict, filename: str = "rapport_coeur.pdf"):
    """Génère le rapport PDF complet."""
    pdf = RapportPDF()
    pdf.alias_nb_pages()

    # Page titre
    pdf.titre_principal()

    qual = resultats["qualitatif"]
    has_score2 = "score2" in resultats

    # Synthese rapide
    pdf.section_resume_executif(resultats)

    # Profil patient
    pdf.section_profil(patient, qual["imc"], qual["categorie_imc"])

    # SCORE2 si disponible
    if has_score2:
        pdf.section_score2(resultats["score2"])

    # Qualitatif
    pdf.section_qualitatif(qual, has_score2)

    # Points forts
    pdf.section_facteurs_positifs(qual["facteurs_positifs"])

    # Recommandations
    num_reco = "5" if has_score2 else "4"
    pdf.section_recommandations(qual["recommandations"], num_reco)

    # Méthodologie
    num_methodo = "6" if has_score2 else "5"
    pdf.section_methodologie(num_methodo)

    pdf.output(filename)
    return filename


# ============================================================================
# AFFICHAGE CONSOLE DES RÉSULTATS
# ============================================================================

def afficher_resultats(resultats: dict):
    """Affiche les résultats dans le terminal."""
    print("\n" + "=" * 70)
    print("  RÉSULTATS")
    print("=" * 70)

    qual = resultats["qualitatif"]

    if "score2" in resultats:
        s2 = resultats["score2"]
        print(f"\n  ┌─────────────────────────────────────────────┐")
        print(f"  │  SCORE2 ({s2['mode']}) – Pays à bas risque    │")
        print(f"  │  Risque à 10 ans : {s2['risque_pct']:>5.1f}%                   │")
        print(f"  │  Classification  : {s2['categorie']:<24s}│")
        print(f"  └─────────────────────────────────────────────┘")

    print(f"\n  ┌─────────────────────────────────────────────┐")
    print(f"  │  ÉVALUATION QUALITATIVE MULTI-FACTEURS      │")
    print(f"  │  Score : {qual['score_brut']:>3d}/{qual['score_max']:<3d} ({qual['score_normalise']:>5.1f}%)            │")
    print(f"  │  Classification : {qual['categorie']:<25s}│")
    print(f"  └─────────────────────────────────────────────┘")

    print(f"\n  IMC : {qual['imc']} ({qual['categorie_imc']})")

    print("\n  Détail par facteur :")
    print(f"  {'Facteur':<28s} {'Valeur':<20s} {'Points':>8s}  Jauge")
    print("  " + "─" * 75)
    for facteur, valeur, pts, pts_max in qual["details"]:
        val_str = str(valeur)[:18]
        ratio = pts / pts_max if pts_max > 0 else 0
        bar_len = int(ratio * 15)
        bar = "█" * bar_len + "░" * (15 - bar_len)
        print(f"  {facteur:<28s} {val_str:<20s} {pts:>3d}/{pts_max:<3d}  [{bar}]")

    if qual["facteurs_positifs"]:
        print("\n  ✓ Points forts :")
        for f in qual["facteurs_positifs"]:
            print(f"    + {f}")

    print("\n  Recommandations :")
    for i, reco in enumerate(qual["recommandations"], 1):
        print(f"    {i}. {reco}")


# ============================================================================
# MODE DÉMO (données pré-remplies)
# ============================================================================

def patient_demo() -> PatientData:
    """Crée un patient de démonstration pour tester l'algorithme."""
    return PatientData(
        sexe="H",
        age=52,
        poids=85,
        taille=178,
        antecedents_familiaux="oui",
        heures_assis=">7h",
        activite_physique="<30min",
        tabac="oui",
        tabac_passif="oui",
        fruits_legumes="2-5/sem",
        ajout_sel="oui",
        preparation_repas="industriel",
        charcuterie_fromage="oui",
        stress="permanent",
        coleres="frequent",
        charge_familiale_seule="non",
        alcool_excessif="non",
        boissons_energisantes="oui",
        hypertension="oui",
        tension_systolique=148,
        tension_diastolique=92,
        cholesterol_eleve="oui",
        cholesterol_total=6.8,
        cholesterol_ldl=4.2,
        cholesterol_hdl=1.1,
        diabete="non",
        glycemie=1.05,
        apnee_sommeil="non",
        troubles_sommeil="oui",
    )


def patient_demo_sain() -> PatientData:
    """Patient avec un profil sain."""
    return PatientData(
        sexe="F",
        age=35,
        poids=60,
        taille=165,
        antecedents_familiaux="non",
        heures_assis="<3h",
        activite_physique=">30min",
        tabac="non",
        tabac_passif="non",
        fruits_legumes="5+/jour",
        ajout_sel="non",
        preparation_repas="maison",
        charcuterie_fromage="non",
        stress="jamais",
        coleres="jamais",
        charge_familiale_seule="non",
        alcool_excessif="non",
        boissons_energisantes="non",
        hypertension="non",
        tension_systolique=115,
        tension_diastolique=72,
        cholesterol_eleve="non",
        cholesterol_total=4.5,
        cholesterol_ldl=2.5,
        cholesterol_hdl=1.8,
        diabete="non",
        glycemie=0.88,
        apnee_sommeil="non",
        troubles_sommeil="non",
    )


def patient_demo_modere() -> PatientData:
    """Patient avec risque modéré."""
    return PatientData(
        sexe="H",
        age=58,
        poids=82,
        taille=175,
        antecedents_familiaux="ne_sais_pas",
        heures_assis="3-7h",
        activite_physique="~30min",
        tabac="non",
        tabac_passif="non",
        fruits_legumes="2-4/jour",
        ajout_sel="non",
        preparation_repas="maison",
        charcuterie_fromage="oui",
        stress="occasionnel",
        coleres="peu",
        charge_familiale_seule="oui",
        alcool_excessif="non",
        boissons_energisantes="non",
        hypertension="oui",
        tension_systolique=138,
        tension_diastolique=85,
        cholesterol_eleve="oui",
        cholesterol_total=5.8,
        cholesterol_ldl=3.5,
        cholesterol_hdl=1.3,
        diabete="non",
        glycemie=1.02,
        apnee_sommeil="non",
        troubles_sommeil="oui",
    )


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "=" * 70)
    print("  COMMENT VA VOTRE COEUR ?")
    print("  Évaluation du Risque Cardiovasculaire")
    print("=" * 70)
    print("\n  Choisissez un mode :\n")
    print("  1. Questionnaire interactif (répondre aux 22 questions)")
    print("  2. Démo : patient à haut risque")
    print("  3. Démo : patient sain")
    print("  4. Démo : patient risque modéré")

    while True:
        choix = input("\n  > Votre choix (1-4) : ").strip()
        if choix in ("1", "2", "3", "4"):
            break

    if choix == "1":
        patient = questionnaire_interactif()
    elif choix == "2":
        patient = patient_demo()
        print("\n  [Mode démo : Patient à haut risque – Homme, 52 ans, fumeur, HTA, hypercholestérolémie]")
    elif choix == "3":
        patient = patient_demo_sain()
        print("\n  [Mode démo : Patiente saine – Femme, 35 ans, sportive, alimentation équilibrée]")
    else:
        patient = patient_demo_modere()
        print("\n  [Mode démo : Patient risque modéré – Homme, 58 ans, ex-fumeur, HTA limite]")

    # Évaluation
    resultats = evaluer_risque(patient)

    # Affichage console
    afficher_resultats(resultats)

    # Génération PDF
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "rapport_cardiovasculaire.pdf")
    generer_pdf(patient, resultats, pdf_path)
    print(f"\n  ✓ Rapport PDF généré : {pdf_path}")
    print()


if __name__ == "__main__":
    main()
