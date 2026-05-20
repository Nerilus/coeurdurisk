/**
 * score2.js
 * =============================================================================
 * Portage JavaScript de coeur_risk.py
 *
 * Mode quantitatif : SCORE2 / SCORE2-OP (ESC 2021, pays à bas risque – France)
 * Mode qualitatif  : modèle pédagogique multi-facteurs basé sur ln(RR)
 *
 * Produit exactement la même structure JSON que POST /api/calc.
 * Utilisé en mode offline (navigator.onLine === false).
 * =============================================================================
 */

// ============================================================================
// COEFFICIENTS SCORE2 – pays à bas risque (France)
// ============================================================================

const SCORE2_COEFFICIENTS = {
  H: {
    age:              0.3742,
    tabac:            0.6012,
    pas:              0.2777,
    tchol:            0.1458,
    hdl:             -0.2698,
    tabac_age:       -0.0755,
    pas_age:         -0.0255,
    tchol_age:       -0.0281,
    hdl_age:          0.0426,
    baseline_survival: 0.9605,
  },
  F: {
    age:              0.4648,
    tabac:            0.7744,
    pas:              0.3131,
    tchol:            0.1002,
    hdl:             -0.2606,
    tabac_age:       -0.1088,
    pas_age:         -0.0277,
    tchol_age:       -0.0226,
    hdl_age:          0.0613,
    baseline_survival: 0.9776,
  },
};

const SCORE2_CALIBRATION = {
  H: { scale1: -0.5699, scale2: 0.7476 },
  F: { scale1: -0.7380, scale2: 0.7019 },
};

// Coefficients SCORE2-OP (70-89 ans)
const SCORE2_OP_COEFFICIENTS = {
  H: {
    age:              0.4219,
    tabac:            0.3564,
    pas:              0.2030,
    tchol:            0.0592,
    hdl:             -0.1549,
    tabac_age:       -0.0793,
    pas_age:         -0.0260,
    tchol_age:       -0.0143,
    hdl_age:          0.0310,
    baseline_survival: 0.8673,
  },
  F: {
    age:              0.5765,
    tabac:            0.4846,
    pas:              0.2680,
    tchol:            0.0611,
    hdl:             -0.1780,
    tabac_age:       -0.1060,
    pas_age:         -0.0294,
    tchol_age:       -0.0173,
    hdl_age:          0.0393,
    baseline_survival: 0.9144,
  },
};

const SCORE2_OP_CALIBRATION = {
  H: { scale1: -0.3143, scale2: 0.7557 },
  F: { scale1: -0.5765, scale2: 0.7168 },
};

// ============================================================================
// HELPERS
// ============================================================================

function _calculImc(poids, tailleCm) {
  const tailleM = tailleCm / 100;
  if (tailleM <= 0) return 0;
  return poids / (tailleM * tailleM);
}

function _categorieImc(imc) {
  if (imc < 18.5) return "Insuffisance pondérale";
  if (imc < 25)   return "Poids normal";
  if (imc < 30)   return "Surpoids";
  if (imc < 35)   return "Obésité modérée (classe I)";
  if (imc < 40)   return "Obésité sévère (classe II)";
  return "Obésité morbide (classe III)";
}

// ============================================================================
// SCORE2 / SCORE2-OP (ESC 2021, pays à bas risque)
// Entrée : objet patient (mêmes champs que PatientInput)
// Sortie : null si données insuffisantes, sinon objet résultat
// ============================================================================

function calculScore2(p) {
  if (p.age < 40 || p.age > 89)                           return null;
  if (p.tension_systolique == null)                        return null;
  if (p.cholesterol_total == null || p.cholesterol_hdl == null) return null;

  const sexe   = p.sexe;
  const fumeur = p.tabac === "oui" ? 1 : 0;

  let coef, calib, ageCenter;
  if (p.age < 70) {
    coef      = SCORE2_COEFFICIENTS[sexe];
    calib     = SCORE2_CALIBRATION[sexe];
    ageCenter = 60;
  } else {
    coef      = SCORE2_OP_COEFFICIENTS[sexe];
    calib     = SCORE2_OP_CALIBRATION[sexe];
    ageCenter = 75;
  }

  // Variables centrées
  const cage   = (p.age - ageCenter) / 5;
  const csbp   = (p.tension_systolique - 120) / 20;
  const ctchol = p.cholesterol_total - 6;
  const chdl   = (p.cholesterol_hdl - 1.3) / 0.5;

  // Score linéaire
  const lp = (
      coef.age       * cage
    + coef.tabac     * fumeur
    + coef.pas       * csbp
    + coef.tchol     * ctchol
    + coef.hdl       * chdl
    + coef.tabac_age * fumeur * cage
    + coef.pas_age   * csbp   * cage
    + coef.tchol_age * ctchol * cage
    + coef.hdl_age   * chdl   * cage
  );

  // Risque non calibré
  const s0 = coef.baseline_survival;
  let riskUncalib = 1 - Math.pow(s0, Math.exp(lp));
  if (riskUncalib <= 0) riskUncalib = 0.0001;
  if (riskUncalib >= 1) riskUncalib = 0.9999;

  // Calibration régionale
  const inner          = Math.log(-Math.log(1 - riskUncalib));
  const calibratedValue = calib.scale1 + calib.scale2 * inner;
  let riskCalibrated   = (1 - Math.exp(-Math.exp(calibratedValue))) * 100;
  riskCalibrated       = Math.max(0.1, Math.min(99.9, riskCalibrated));

  // Classification selon l'âge (ESC 2021)
  let categorie, couleur;
  if (p.age < 50) {
    if      (riskCalibrated < 2.5) { categorie = "Faible à modéré"; couleur = "vert";   }
    else if (riskCalibrated < 7.5) { categorie = "Élevé";           couleur = "orange"; }
    else                           { categorie = "Très élevé";      couleur = "rouge";  }
  } else if (p.age < 70) {
    if      (riskCalibrated < 5)   { categorie = "Faible à modéré"; couleur = "vert";   }
    else if (riskCalibrated < 10)  { categorie = "Élevé";           couleur = "orange"; }
    else                           { categorie = "Très élevé";      couleur = "rouge";  }
  } else {
    if      (riskCalibrated < 7.5) { categorie = "Faible à modéré"; couleur = "vert";   }
    else if (riskCalibrated < 15)  { categorie = "Élevé";           couleur = "orange"; }
    else                           { categorie = "Très élevé";      couleur = "rouge";  }
  }

  return {
    mode:             p.age < 70 ? "SCORE2" : "SCORE2-OP",
    risque_pct:       Math.round(riskCalibrated * 10) / 10,
    categorie,
    couleur,
    lp:               Math.round(lp * 10000) / 10000,
    risk_uncalib_pct: Math.round(riskUncalib * 100 * 10) / 10,
  };
}

// ============================================================================
// SCORE QUALITATIF – 22 facteurs, score max 108 pts
// Sources : INTERHEART, PSC, ERFC, AHA, Micha, Dong, He, Graudal, Zhao, etc.
// ============================================================================

function scoreQualitatif(p) {
  let score = 0;
  const details          = [];  // [nom, valeur, pts, pts_max]
  const recommandations  = [];
  const facteurs_positifs = [];
  let pts;

  // ── 1. ÂGE (0-14 pts) ──
  // HR ~2.0-3.0 par décennie après 40 ans (PSC, Lewington et al., Lancet 2002)
  if      (p.age < 40) pts = 0;
  else if (p.age < 50) pts = 3;
  else if (p.age < 55) pts = 5;
  else if (p.age < 60) pts = 7;
  else if (p.age < 65) pts = 9;
  else if (p.age < 70) pts = 11;
  else                 pts = 14;
  score += pts;
  details.push(["Âge", p.age, pts, 14]);

  // ── 2. SEXE (0-5 pts) ──
  // HR ~2.0 homme vs femme en âge moyen (EPIC-Norfolk, Eur J Prev Cardiol 2024)
  if (p.sexe === "H") {
    pts = 5;
  } else {
    pts = p.age >= 55 ? 2 : 0;  // post-ménopause
  }
  score += pts;
  details.push(["Sexe", p.sexe === "H" ? "Homme" : "Femme", pts, 5]);

  // ── 3. IMC (0-6 pts) ──
  // Surpoids HR 1.26, Obésité HR 1.69, Obésité sévère HR ~2.0 (Lancet 2014/2016)
  const imc = _calculImc(p.poids, p.taille);
  if (imc < 18.5) {
    pts = 1;
  } else if (imc < 25) {
    pts = 0;
    facteurs_positifs.push("IMC normal");
  } else if (imc < 30) {
    pts = 2;
    recommandations.push("Perdre du poids : viser un IMC < 25 réduirait votre risque cardiovasculaire (HR 1.26, Lancet 2014).");
  } else if (imc < 35) {
    pts = 4;
    recommandations.push("Consulter un nutritionniste : l'obésité augmente le risque CV de 69% (HR 1.69, Lancet 2014).");
  } else {
    pts = 6;
    recommandations.push("Prise en charge médicale de l'obésité recommandée : risque CV doublé (HR 2.0, Lancet 2016).");
  }
  score += pts;
  details.push(["IMC", `${imc.toFixed(1)} (${_categorieImc(imc)})`, pts, 6]);

  // ── 4. ANTÉCÉDENTS FAMILIAUX (0-5 pts) ──
  // HR 1.74 (EPIC-Norfolk, Heart 2011)
  if (p.antecedents_familiaux === "oui") {
    pts = 5;
    recommandations.push("Antécédents familiaux : surveillance cardiologique renforcée recommandée (HR 1.74, EPIC-Norfolk).");
  } else if (p.antecedents_familiaux === "ne_sais_pas") {
    pts = 2;
    recommandations.push("Renseignez-vous sur vos antécédents familiaux cardiovasculaires.");
  } else {
    pts = 0;
    facteurs_positifs.push("Pas d'antécédents familiaux cardiovasculaires");
  }
  score += pts;
  details.push(["Antécédents familiaux", p.antecedents_familiaux, pts, 5]);

  // ── 5. SÉDENTARITÉ (0-5 pts) ──
  // HR 1.90 mortalité CV, sédentarité élevée vs faible (AHA, Young et al., Circulation 2016)
  if (p.heures_assis === ">7h") {
    pts = 5;
    recommandations.push("Réduire le temps assis : se lever toutes les 30 min. La sédentarité prolongée augmente le risque CV de 90% (HR 1.90, AHA 2016).");
  } else if (p.heures_assis === "3-7h") {
    pts = 2;
  } else {
    pts = 0;
    facteurs_positifs.push("Faible temps de sédentarité");
  }
  score += pts;
  details.push(["Sédentarité (temps assis)", p.heures_assis, pts, 5]);

  // ── 6. ACTIVITÉ PHYSIQUE (0-2 pts) ──
  // HR 1.24 pour coronaropathie, inactif vs actif (Li & Siegrist, 2012)
  if (p.activite_physique === "<30min") {
    pts = 2;
    recommandations.push("Augmenter l'activité physique : 30 min/jour de marche rapide. L'inactivité augmente le risque CV de 24% indépendamment des autres facteurs (HR 1.24, méta-analyse 2012). L'effet total est plus important car l'activité améliore aussi le poids, la tension et le cholestérol.");
  } else if (p.activite_physique === "~30min") {
    pts = 1;
  } else {
    pts = 0;
    facteurs_positifs.push("Activité physique suffisante (>30 min/jour)");
  }
  score += pts;
  details.push(["Activité physique", p.activite_physique, pts, 2]);

  // ── 7. TABAC ACTIF (0-9 pts) ──
  // Fumeur actif OR 2.87 pour infarctus (INTERHEART, Yusuf et al., Lancet 2004)
  if (p.tabac === "oui") {
    pts = 9;
    recommandations.push("ARRÊTER DE FUMER : le tabac multiplie le risque d'infarctus par 2.87 (INTERHEART, Lancet 2004). Après 1 an d'arrêt, le risque diminue de 50%. Après 5 ans, il rejoint celui d'un non-fumeur.");
  } else if (p.tabac === "ancien_5ans") {
    pts = 5;
    recommandations.push("Ancien fumeur : le risque résiduel diminue progressivement. Après 5 ans d'arrêt, il rejoint celui d'un non-fumeur. Tenez bon !");
  } else {
    pts = 0;
    facteurs_positifs.push("Non-fumeur / arrêt depuis > 5 ans");
  }
  score += pts;
  details.push(["Tabac actif", p.tabac, pts, 9]);

  // ── 8. TABAC PASSIF (0-2 pts) ──
  // RR 1.25 (He et al., NEJM 1999)
  if (p.tabac_passif === "oui") {
    pts = 2;
    recommandations.push("Tabagisme passif : l'exposition augmente le risque CV de 25-30% (RR 1.25, He et al., NEJM 1999). Éviter les environnements enfumés.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Tabac passif", p.tabac_passif, pts, 2]);

  // ── 9. FRUITS & LÉGUMES (0-3 pts) ──
  // Absence de consommation quotidienne OR 1.43 (INTERHEART, Lancet 2004)
  if (p.fruits_legumes === "<2/sem") {
    pts = 3;
    recommandations.push("Consommer au moins 5 fruits et légumes par jour : le manque augmente le risque d'infarctus de 43% (OR 1.43, INTERHEART 2004).");
  } else if (p.fruits_legumes === "2-5/sem") {
    pts = 2;
  } else if (p.fruits_legumes === "2-4/jour") {
    pts = 1;
  } else {
    pts = 0;
    facteurs_positifs.push("Consommation suffisante de fruits et légumes");
  }
  score += pts;
  details.push(["Fruits et légumes", p.fruits_legumes, pts, 3]);

  // ── 10. SEL (0-1 pt) ──
  // RR 1.13 pour événements CV (Graudal et al., Nutrients 2020)
  if (p.ajout_sel === "oui") {
    pts = 1;
    recommandations.push("Réduire le sel : ne pas resaler les plats. L'excès de sel augmente le risque CV de 13% (RR 1.13, Graudal 2020) et l'hypertension de 33%.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Ajout de sel", p.ajout_sel, pts, 1]);

  // ── 11. PRÉPARATION DES REPAS (0-3 pts) ──
  // Alimentation ultra-transformée RR ~1.50 (Micha et al., Circulation 2010)
  if (p.preparation_repas === "industriel") {
    pts = 3;
    recommandations.push("Privilégier la cuisine maison : les plats industriels sont riches en sel, sucre et graisses saturées (RR ~1.50 pour événements CV, Micha et al., Circulation 2010).");
  } else if (p.preparation_repas === "conserves") {
    pts = 2;
  } else {
    pts = 0;
    facteurs_positifs.push("Cuisine maison");
  }
  score += pts;
  details.push(["Préparation des repas", p.preparation_repas, pts, 3]);

  // ── 12. CHARCUTERIE / FROMAGE (0-3 pts) ──
  // Viande transformée RR 1.42 par 50g/jour pour coronaropathie (Micha et al., Circulation 2010)
  if (p.charcuterie_fromage === "oui") {
    pts = 3;
    recommandations.push("Limiter charcuterie et fromage : la viande transformée augmente le risque coronarien de 42% par 50g/jour (RR 1.42, Micha et al., Circulation 2010).");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Charcuterie/Fromage régulier", p.charcuterie_fromage, pts, 3]);

  // ── 13. STRESS (0-7 pts) ──
  // Stress permanent OR 2.17 pour infarctus (INTERHEART psychosocial, Rosengren et al., Lancet 2004)
  if (p.stress === "permanent") {
    pts = 7;
    recommandations.push("Gérer le stress chronique : le stress permanent multiplie le risque d'infarctus par 2.17 (INTERHEART, Rosengren et al., Lancet 2004). Méditation, activité physique, suivi psychologique recommandés.");
  } else if (p.stress === "occasionnel") {
    pts = 3;
  } else {
    pts = 0;
    facteurs_positifs.push("Bon niveau de gestion du stress");
  }
  score += pts;
  details.push(["Stress", p.stress, pts, 7]);

  // ── 14. COLÈRES / HOSTILITÉ (0-3 pts) ──
  // HR 1.19-1.50 (Chida & Steptoe, JACC 2009)
  if (p.coleres === "tres_frequent") {
    pts = 3;
    recommandations.push("Colères fréquentes : l'hostilité chronique augmente le risque CV de 19 à 50% (HR 1.19-1.50, Chida & Steptoe, JACC 2009). Gestion des émotions, thérapie cognitivo-comportementale recommandées.");
  } else if (p.coleres === "frequent") {
    pts = 2;
    recommandations.push("Colères régulières : apprendre à gérer ses émotions réduit le risque cardiovasculaire.");
  } else if (p.coleres === "peu") {
    pts = 1;
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Colères / hostilité", p.coleres, pts, 3]);

  // ── 15. CHARGE FAMILIALE SEUL(E) (0-2 pts) ──
  // Isolement social HR 1.29 (Valtorta et al., Heart 2016)
  if (p.charge_familiale_seule === "oui") {
    pts = 2;
    recommandations.push("Charge familiale seul(e) : l'isolement et le stress chronique augmentent le risque CV de 29% (HR 1.29, Valtorta et al., Heart 2016). N'hésitez pas à chercher du soutien.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Charge familiale seul(e)", p.charge_familiale_seule, pts, 2]);

  // ── 16. ALCOOL (0-3 pts) ──
  // RR 1.35 pour mortalité (Zhao et al., JAMA Network Open 2023)
  if (p.alcool_excessif === "oui") {
    pts = 3;
    recommandations.push("Réduire la consommation d'alcool : l'excès augmente la mortalité de 35% (RR 1.35, Zhao et al., JAMA Network Open 2023). Max 2 verres/jour, pas tous les jours.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Alcool excessif", p.alcool_excessif, pts, 3]);

  // ── 17. BOISSONS ÉNERGISANTES (0-1 pt) ──
  // Risque d'arythmie, HTA aiguë (Fletcher et al., JACC 2017)
  if (p.boissons_energisantes === "oui") {
    pts = 1;
    recommandations.push("Boissons énergisantes : risque d'arythmie et d'hypertension aiguë (Fletcher et al., JACC 2017). À éviter, surtout en cas de pathologie cardiaque.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Boissons énergisantes", p.boissons_energisantes, pts, 1]);

  // ── 18. HYPERTENSION (0-10 pts) ──
  // PAS >140 OR 1.91 (INTERHEART, Lancet 2004) ; chaque +20 mmHg double le risque (PSC, Lancet 2002)
  if (p.hypertension === "oui") {
    if (p.tension_systolique != null && p.tension_systolique >= 160) {
      pts = 10;
      recommandations.push("Hypertension sévère : chaque +20 mmHg de PAS double le risque de décès coronarien (PSC, Lewington et al., Lancet 2002). Suivi médical urgent. Objectif < 140/90 mmHg.");
    } else if (p.tension_systolique != null && p.tension_systolique >= 140) {
      pts = 6;
      recommandations.push("Hypertension confirmée : risque d'infarctus multiplié par 1.91 (INTERHEART, Lancet 2004). Traitement et suivi régulier recommandés.");
    } else {
      pts = 4;
      recommandations.push("Hypertension diagnostiquée : vérifier régulièrement la tension.");
    }
  } else {
    pts = 0;
    if (p.tension_systolique != null && p.tension_systolique < 120) {
      facteurs_positifs.push("Tension artérielle optimale");
    }
  }
  score += pts;
  details.push(["Hypertension", p.hypertension, pts, 10]);

  // ── 19. CHOLESTÉROL (0-9 pts) ──
  // Quintile supérieur ApoB/ApoA1 OR 3.25 (INTERHEART, Lancet 2004)
  if (p.cholesterol_eleve === "oui") {
    if (p.cholesterol_total != null && p.cholesterol_total > 7) {
      pts = 9;
      recommandations.push("Cholestérol très élevé : le quintile supérieur multiplie le risque d'infarctus par 3.25 (INTERHEART, Lancet 2004). Traitement médical urgent.");
    } else if (p.cholesterol_total != null && p.cholesterol_total > 5.5) {
      pts = 5;
      recommandations.push("Cholestérol élevé : chaque +1 mmol/L augmente le risque coronarien de 52% (PSC, Lancet 2007). Adapter l'alimentation et consulter.");
    } else {
      pts = 3;
      recommandations.push("Cholestérol à surveiller : contrôle biologique annuel recommandé.");
    }
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Cholestérol élevé", p.cholesterol_eleve, pts, 9]);

  // ── 20. DIABÈTE (0-7 pts) ──
  // HR 2.00 pour coronaropathie (ERFC, Lancet 2010) ; OR 2.37 (INTERHEART)
  if (p.diabete === "oui") {
    if (p.glycemie != null && p.glycemie > 1.26) {
      pts = 7;
      recommandations.push("Diabète mal équilibré (glycémie > 1.26 g/L) : le diabète multiplie le risque coronarien par 2.37 (INTERHEART, Lancet 2004). Suivi endocrinologique indispensable.");
    } else {
      pts = 6;
      recommandations.push("Diabète : le risque coronarien est doublé (HR 2.00, ERFC, Lancet 2010). Équilibre glycémique essentiel.");
    }
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Diabète", p.diabete, pts, 7]);

  // ── 21. APNÉE DU SOMMEIL (0-5 pts) ──
  // HR 1.82 (Dong et al., Int J Cardiol 2013)
  if (p.apnee_sommeil === "oui") {
    pts = 5;
    recommandations.push("Apnée du sommeil : risque CV augmenté de 82% (HR 1.82, Dong et al., Int J Cardiol 2013). Traitement par PPC recommandé.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Apnée du sommeil", p.apnee_sommeil, pts, 5]);

  // ── 22. TROUBLES DU SOMMEIL (0-3 pts) ──
  // Insomnie chronique HR 1.45 (He et al., Eur J Prev Cardiol 2017)
  if (p.troubles_sommeil === "oui") {
    pts = 3;
    recommandations.push("Troubles du sommeil : l'insomnie chronique augmente le risque CV de 45% (HR 1.45, He et al., Eur J Prev Cardiol 2017). Consultation spécialisée recommandée, hygiène du sommeil à améliorer.");
  } else {
    pts = 0;
  }
  score += pts;
  details.push(["Troubles du sommeil", p.troubles_sommeil, pts, 3]);

  // ── TOTAL ET CLASSIFICATION ──
  // score_max théorique : 108 pts
  const scoreMax       = details.reduce((acc, d) => acc + d[3], 0);
  const scoreNormalise = (score / scoreMax) * 100;

  let categorie, couleur;
  if      (scoreNormalise < 15) { categorie = "Risque faible";          couleur = "vert";        }
  else if (scoreNormalise < 30) { categorie = "Risque faible à modéré"; couleur = "vert_jaune";  }
  else if (scoreNormalise < 50) { categorie = "Risque modéré";          couleur = "jaune";       }
  else if (scoreNormalise < 65) { categorie = "Risque modéré à élevé";  couleur = "orange";      }
  else if (scoreNormalise < 80) { categorie = "Risque élevé";           couleur = "rouge";       }
  else                          { categorie = "Risque très élevé";      couleur = "rouge_fonce"; }

  if (recommandations.length === 0) {
    recommandations.push("Continuez ainsi ! Votre mode de vie est favorable à votre santé cardiovasculaire.");
  }

  return {
    mode:             "Qualitatif",
    score_brut:       score,
    score_max:        scoreMax,
    score_normalise:  Math.round(scoreNormalise * 10) / 10,
    categorie,
    couleur,
    details,
    recommandations,
    facteurs_positifs,
    imc:              Math.round(imc * 10) / 10,
    categorie_imc:    _categorieImc(imc),
  };
}

// ============================================================================
// AVERTISSEMENTS DE COHÉRENCE – miroir de coherence_warnings() dans main.py
// ============================================================================

function coherenceWarnings(p) {
  const warn = [];

  // Hypertension vs PAS
  if (p.hypertension === "non" && p.tension_systolique != null && p.tension_systolique >= 140)
    warn.push("HTA_NON_MAIS_PAS_ELEVEE");
  if (p.hypertension === "oui" && p.tension_systolique == null)
    warn.push("HTA_OUI_MAIS_PAS_SAISIE");

  // Cholestérol vs valeurs
  if (p.cholesterol_eleve === "non" && p.cholesterol_total != null && p.cholesterol_total >= 6.2)
    warn.push("CHOLESTEROL_NON_MAIS_TOTAL_ELEVE");
  if (p.cholesterol_eleve === "oui" && p.cholesterol_total == null)
    warn.push("CHOLESTEROL_OUI_MAIS_TOTAL_PAS_SAISI");

  // Diabète vs glycémie
  if (p.diabete === "non" && p.glycemie != null && p.glycemie >= 1.26)
    warn.push("DIABETE_NON_MAIS_GLYCEMIE_ELEVEE");
  if (p.diabete === "oui" && p.glycemie == null)
    warn.push("DIABETE_OUI_MAIS_GLYCEMIE_PAS_SAISIE");

  // Valeurs hors plage plausible
  if (p.tension_systolique != null && (p.tension_systolique < 70 || p.tension_systolique > 250))
    warn.push("PAS_HORS_PLAUSIBLE");
  if (p.cholesterol_total != null && (p.cholesterol_total < 2 || p.cholesterol_total > 15))
    warn.push("TCHOL_HORS_PLAUSIBLE");
  if (p.cholesterol_hdl != null && (p.cholesterol_hdl < 0.3 || p.cholesterol_hdl > 5))
    warn.push("HDL_HORS_PLAUSIBLE");
  if (p.glycemie != null && (p.glycemie < 0.3 || p.glycemie > 5))
    warn.push("GLYCEMIE_HORS_PLAUSIBLE");

  // SCORE2 possible mais données manquantes
  if (p.age >= 40 && p.age <= 89) {
    if (p.tension_systolique == null || p.cholesterol_total == null || p.cholesterol_hdl == null) {
      warn.push("SCORE2_POSSIBLE_MAIS_DONNEES_MANQUANTES");
    }
  }

  return warn;
}

// ============================================================================
// ÉVALUATION COMBINÉE
// Produit exactement la même structure JSON que POST /api/calc
// ============================================================================

function evaluerRisque(p) {
  const resultat = {};

  resultat.qualitatif = scoreQualitatif(p);

  const score2 = calculScore2(p);
  if (score2) resultat.score2 = score2;

  resultat.warnings = coherenceWarnings(p);

  return resultat;
}

// Export CommonJS (Node / tests unitaires)
if (typeof module !== "undefined" && module.exports) {
  module.exports = { evaluerRisque, calculScore2, scoreQualitatif, coherenceWarnings };
}
