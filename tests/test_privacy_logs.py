import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = r"""
import os
from fastapi.testclient import TestClient

os.environ["LOG_LEVEL"] = "INFO"

from webapp.main import app

client = TestClient(app)

payload = {
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
  "cholesterol_hdl": 1.1,
  "diabete": "non",
  "glycemie": 1.05,
  "apnee_sommeil": "non",
  "troubles_sommeil": "oui"
}

res = client.post("/api/calc", json=payload)
assert res.status_code == 200, res.text
print("OK")
"""


class TestPrivacyLogs(unittest.TestCase):
    def test_logs_do_not_contain_payload_fields(self):
        with tempfile.TemporaryDirectory() as td:
            log_file = str(Path(td) / "test.log")
            env = os.environ.copy()
            env["LOG_FILE"] = log_file
            env["LOG_LEVEL"] = "INFO"

            p = subprocess.run(
                [sys.executable, "-c", SCRIPT],
                cwd=str(Path(__file__).resolve().parents[1]),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(p.returncode, 0, msg=f"stdout={p.stdout}\nstderr={p.stderr}")
            self.assertTrue(Path(log_file).exists(), "log file not created")
            content = Path(log_file).read_text(encoding="utf-8", errors="ignore")

            # On vérifie qu'on ne logge pas les champs bruts (anonymat)
            forbidden = [
                "antecedents_familiaux",
                "heures_assis",
                "activite_physique",
                "tabac_passif",
                "fruits_legumes",
                "preparation_repas",
                "charcuterie_fromage",
                "tension_systolique",
                "cholesterol_total",
                "glycemie",
            ]
            for key in forbidden:
                self.assertNotIn(key, content, msg=f"Sensitive key leaked in logs: {key}")


if __name__ == "__main__":
    unittest.main()

