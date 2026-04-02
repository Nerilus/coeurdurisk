import unittest

from coeur_risk import (
    PatientData,
    calcul_score2,
    evaluer_risque,
    patient_demo,
    patient_demo_sain,
)


class TestScore2(unittest.TestCase):
    def test_score2_demo_patient_matches_expected(self):
        p = patient_demo()
        res = calcul_score2(p)
        self.assertIsNotNone(res)
        # Valeur observée dans la démo console (~9.3%) ; tolérance large pour éviter
        # des échecs si changement mineur d'arrondi.
        self.assertAlmostEqual(res["risque_pct"], 9.3, delta=0.3)
        self.assertIn(res["categorie"], {"Faible à modéré", "Élevé", "Très élevé"})

    def test_score2_returns_none_when_missing_required_inputs(self):
        p = PatientData(sexe="H", age=52, poids=80, taille=180)
        self.assertIsNone(calcul_score2(p))

    def _base_score2_patient(
        self,
        *,
        sexe: str = "H",
        age: int = 52,
        tabac: str = "non",
        pas: float = 120,
        tchol: float = 6.0,
        hdl: float = 1.3,
    ) -> PatientData:
        # Champs non nécessaires au SCORE2, mais présents dans la dataclass
        return PatientData(
            sexe=sexe,
            age=age,
            poids=80,
            taille=180,
            antecedents_familiaux="non",
            heures_assis="3-7h",
            activite_physique="~30min",
            tabac=tabac,
            tabac_passif="non",
            fruits_legumes="2-4/jour",
            ajout_sel="non",
            preparation_repas="maison",
            charcuterie_fromage="non",
            stress="jamais",
            coleres="jamais",
            charge_familiale_seule="non",
            alcool_excessif="non",
            boissons_energisantes="non",
            hypertension="non",
            tension_systolique=pas,
            tension_diastolique=80,
            cholesterol_eleve="non",
            cholesterol_total=tchol,
            cholesterol_ldl=None,
            cholesterol_hdl=hdl,
            diabete="non",
            glycemie=None,
            apnee_sommeil="non",
            troubles_sommeil="non",
        )

    def test_score2_monotonic_smoking_increases_risk(self):
        # Propriété attendue : à variables identiques, fumeur actuel >= non-fumeur
        for sexe in ("H", "F"):
            for age in (40, 50, 60, 69):
                p0 = self._base_score2_patient(sexe=sexe, age=age, tabac="non")
                p1 = self._base_score2_patient(sexe=sexe, age=age, tabac="oui")
                r0 = calcul_score2(p0)["risque_pct"]
                r1 = calcul_score2(p1)["risque_pct"]
                self.assertGreaterEqual(r1, r0, msg=f"sexe={sexe} age={age} r0={r0} r1={r1}")

    def test_score2_monotonic_sbp_increases_risk(self):
        for sexe in ("H", "F"):
            for age in (40, 55, 65):
                prev = None
                for pas in (100, 120, 140, 160, 180):
                    p = self._base_score2_patient(sexe=sexe, age=age, pas=pas)
                    r = calcul_score2(p)["risque_pct"]
                    if prev is not None:
                        self.assertGreaterEqual(r, prev, msg=f"sexe={sexe} age={age} pas={pas} prev={prev} r={r}")
                    prev = r

    def test_score2_monotonic_total_chol_increases_risk(self):
        for sexe in ("H", "F"):
            for age in (40, 55, 65):
                prev = None
                for tchol in (4.0, 5.0, 6.0, 7.0, 8.0):
                    p = self._base_score2_patient(sexe=sexe, age=age, tchol=tchol)
                    r = calcul_score2(p)["risque_pct"]
                    if prev is not None:
                        self.assertGreaterEqual(r, prev, msg=f"sexe={sexe} age={age} tchol={tchol} prev={prev} r={r}")
                    prev = r

    def test_score2_monotonic_hdl_decreases_risk(self):
        for sexe in ("H", "F"):
            for age in (40, 55, 65):
                prev = None
                for hdl in (0.8, 1.0, 1.3, 1.6, 2.0):
                    p = self._base_score2_patient(sexe=sexe, age=age, hdl=hdl)
                    r = calcul_score2(p)["risque_pct"]
                    if prev is not None:
                        self.assertLessEqual(r, prev, msg=f"sexe={sexe} age={age} hdl={hdl} prev={prev} r={r}")
                    prev = r

    def test_score2_mass_regression_hundreds_cases(self):
        # 2 sexes * 6 ages * 2 tabac * 5 pas * 5 tchol * 4 hdl = 2400 cas
        sexes = ("H", "F")
        ages = (40, 45, 50, 55, 60, 65)
        tabacs = ("non", "oui")
        pass_ = (100, 120, 140, 160, 180)
        tchs = (4.5, 5.5, 6.0, 7.0, 8.0)
        hdls = (0.9, 1.1, 1.3, 1.7)

        for sexe in sexes:
            for age in ages:
                for tabac in tabacs:
                    for pas in pass_:
                        for tchol in tchs:
                            for hdl in hdls:
                                p = self._base_score2_patient(sexe=sexe, age=age, tabac=tabac, pas=pas, tchol=tchol, hdl=hdl)
                                res = calcul_score2(p)
                                self.assertIsNotNone(res)
                                self.assertGreaterEqual(res["risque_pct"], 0.1)
                                self.assertLessEqual(res["risque_pct"], 99.9)
                                self.assertIn(res["mode"], {"SCORE2", "SCORE2-OP"})


class TestEvaluation(unittest.TestCase):
    def test_evaluer_risque_always_contains_qualitatif(self):
        p = patient_demo_sain()
        res = evaluer_risque(p)
        self.assertIn("qualitatif", res)
        qual = res["qualitatif"]
        self.assertIn("score_normalise", qual)
        self.assertIn("categorie", qual)

    def test_evaluer_risque_includes_score2_when_possible(self):
        p = patient_demo()
        res = evaluer_risque(p)
        self.assertIn("qualitatif", res)
        self.assertIn("score2", res)

    def test_qualitatif_bounds_and_consistency_many_cases(self):
        # centaines de cas qualitifs (sans PII) : vérifier bornes et cohérence du score
        sexes = ("H", "F")
        ages = (18, 25, 35, 45, 55, 65, 75)
        heures_assis = ("<3h", "3-7h", ">7h")
        activites = ("<30min", "~30min", ">30min")
        tabs = ("oui", "ancien_5ans", "non")
        fruits = ("<2/sem", "2-5/sem", "2-4/jour", "5+/jour")
        stress = ("jamais", "occasionnel", "permanent")

        count = 0
        for sexe in sexes:
            for age in ages:
                for assis in heures_assis:
                    for act in activites:
                        for tab in tabs:
                            for fr in fruits:
                                for st in stress:
                                    p = PatientData(
                                        sexe=sexe,
                                        age=age,
                                        poids=75,
                                        taille=175,
                                        antecedents_familiaux="non",
                                        heures_assis=assis,
                                        activite_physique=act,
                                        tabac=tab,
                                        tabac_passif="non",
                                        fruits_legumes=fr,
                                        ajout_sel="non",
                                        preparation_repas="maison",
                                        charcuterie_fromage="non",
                                        stress=st,
                                        coleres="jamais",
                                        charge_familiale_seule="non",
                                        alcool_excessif="non",
                                        boissons_energisantes="non",
                                        hypertension="non",
                                        tension_systolique=None,
                                        tension_diastolique=None,
                                        cholesterol_eleve="non",
                                        cholesterol_total=None,
                                        cholesterol_ldl=None,
                                        cholesterol_hdl=None,
                                        diabete="non",
                                        glycemie=None,
                                        apnee_sommeil="non",
                                        troubles_sommeil="non",
                                    )
                                    res = evaluer_risque(p)["qualitatif"]
                                    self.assertGreaterEqual(res["score_normalise"], 0.0)
                                    self.assertLessEqual(res["score_normalise"], 100.0)
                                    self.assertEqual(res["score_max"], 108)
                                    self.assertEqual(res["score_brut"], sum(x[2] for x in res["details"]))
                                    count += 1

        # Sanity check : on a bien généré des centaines de cas
        self.assertGreaterEqual(count, 500)


if __name__ == "__main__":
    unittest.main()

