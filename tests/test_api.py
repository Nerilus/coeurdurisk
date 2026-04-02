import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from webapp.main import app


def demo_payload():
    # Payload minimal complet (reprend demoHigh côté front)
    return {
        "sexe": "H",
        "age": 52,
        "poids": 85,
        "taille": 178,
        "antecedents_familiaux": "oui",
        "heures_assis": ">7h",
        "activite_physique": "<30min",
        "tabac": "oui",
        "tabac_passif": "oui",
        "fruits_legumes": "2-5/sem",
        "ajout_sel": "oui",
        "preparation_repas": "industriel",
        "charcuterie_fromage": "oui",
        "stress": "permanent",
        "coleres": "frequent",
        "charge_familiale_seule": "non",
        "alcool_excessif": "non",
        "boissons_energisantes": "oui",
        "hypertension": "oui",
        "tension_systolique": 148,
        "tension_diastolique": 92,
        "cholesterol_eleve": "oui",
        "cholesterol_total": 6.8,
        "cholesterol_ldl": 4.2,
        "cholesterol_hdl": 1.1,
        "diabete": "non",
        "glycemie": 1.05,
        "apnee_sommeil": "non",
        "troubles_sommeil": "oui",
    }


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_calc_endpoint_ok(self):
        res = self.client.post("/api/calc", json=demo_payload())
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("qualitatif", data)
        # score2 présent pour ce payload
        self.assertIn("score2", data)
        self.assertIn("risque_pct", data["score2"])
        self.assertIn("warnings", data)

    def test_calc_endpoint_hundreds_scenarios(self):
        # centaines de scénarios (variations contrôlées) pour garantir robustesse
        base = demo_payload()
        sexes = ["H", "F"]
        ages = [18, 35, 40, 52, 65, 75]
        tabs = ["oui", "ancien_5ans", "non"]
        assis = ["<3h", "3-7h", ">7h"]
        activ = ["<30min", "~30min", ">30min"]
        fruits = ["<2/sem", "2-5/sem", "2-4/jour", "5+/jour"]
        stress = ["jamais", "occasionnel", "permanent"]
        hta = ["oui", "non"]

        # 2*6*3*3*3*4*3*2 = 2592 scénarios (rapide)
        count = 0
        for s in sexes:
            for a in ages:
                for t in tabs:
                    for ha in assis:
                        for ap in activ:
                            for fr in fruits:
                                for st in stress:
                                    for h in hta:
                                        payload = dict(base)
                                        payload.update(
                                            {
                                                "sexe": s,
                                                "age": a,
                                                "tabac": t,
                                                "heures_assis": ha,
                                                "activite_physique": ap,
                                                "fruits_legumes": fr,
                                                "stress": st,
                                                "hypertension": h,
                                            }
                                        )
                                        # Pour les âges hors SCORE2, SCORE2 peut être absent : OK.
                                        res = self.client.post("/api/calc", json=payload)
                                        self.assertEqual(res.status_code, 200)
                                        data = res.json()
                                        self.assertIn("qualitatif", data)
                                        count += 1

        self.assertGreaterEqual(count, 500)

    def test_calc_endpoint_validation_422(self):
        # Invalid enum → 422
        payload = demo_payload()
        payload["sexe"] = "X"
        res = self.client.post("/api/calc", json=payload)
        self.assertEqual(res.status_code, 422)

    def test_coherence_warnings_trigger(self):
        payload = demo_payload()
        # Contradiction : HTA non mais PAS élevée
        payload["hypertension"] = "non"
        payload["tension_systolique"] = 170
        res = self.client.post("/api/calc", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("warnings", data)
        self.assertIn("HTA_NON_MAIS_PAS_ELEVEE", data["warnings"])

    def test_pdf_endpoint_returns_pdf(self):
        # Mock generer_pdf pour éviter le coût de FPDF en test
        def fake_generer_pdf(patient, resultats, filename):
            with open(filename, "wb") as f:
                f.write(b"%PDF-1.4\n%fake\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n")
            return filename

        with patch("webapp.main.generer_pdf", side_effect=fake_generer_pdf):
            res = self.client.post("/api/pdf", json=demo_payload())
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("content-type"), "application/pdf")
            self.assertGreater(len(res.content), 20)

    def test_email_endpoint_is_mocked(self):
        payload = demo_payload()
        payload.update(
            {
                "email_to": "test@example.com",
                "email_subject": "Test",
                "email_body": "Test body",
            }
        )

        def fake_generer_pdf(patient, resultats, filename):
            with open(filename, "wb") as f:
                f.write(b"%PDF-1.4 fake")
            return filename

        with patch(
            "webapp.main.smtp_config",
            return_value={"host": "x", "port": 587, "username": "u", "password": "p", "from_addr": "a", "use_starttls": True},
        ):
            with patch("webapp.main.generer_pdf", side_effect=fake_generer_pdf):
                with patch("webapp.main.send_email_with_pdf") as send_mock:
                    res = self.client.post("/api/email", json=payload)
                    self.assertEqual(res.status_code, 200, msg=res.text)
                    data = res.json()
                    self.assertTrue(data.get("ok"))
                    send_mock.assert_called_once()

    def test_email_endpoint_hundreds_mock_scenarios(self):
        base = demo_payload()

        def fake_generer_pdf(patient, resultats, filename):
            with open(filename, "wb") as f:
                f.write(b"%PDF-1.4 fake")
            return filename

        smtp = {"host": "x", "port": 587, "username": "u", "password": "p", "from_addr": "a", "use_starttls": True}
        subjects = ["Votre rapport", "Rapport CV", "Test"]
        bodies = ["Bonjour", "Bonjour,\n\nVoici votre rapport.", ""]
        tos = [f"user{i}@example.com" for i in range(1, 101)]

        with patch("webapp.main.smtp_config", return_value=smtp):
            with patch("webapp.main.generer_pdf", side_effect=fake_generer_pdf):
                with patch("webapp.main.send_email_with_pdf") as send_mock:
                    count = 0
                    for to in tos:
                        for sub in subjects:
                            for body in bodies:
                                payload = dict(base)
                                payload.update({"email_to": to, "email_subject": sub, "email_body": body})
                                with self.subTest(email_to=to, subject=sub):
                                    res = self.client.post("/api/email", json=payload)
                                    self.assertEqual(res.status_code, 200, msg=res.text)
                                    data = res.json()
                                    self.assertTrue(data.get("ok"))
                                    count += 1

                    # 100 * 3 * 3 = 900 scénarios
                    self.assertEqual(count, 900)
                    self.assertEqual(send_mock.call_count, 900)


if __name__ == "__main__":
    unittest.main()

