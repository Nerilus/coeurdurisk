#!/usr/bin/env python3
"""
Load test simple pour /api/calc.

Exemple:
  python3 scripts/load_test_calc.py --total 2000 --concurrency 50
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import statistics
import time
import urllib.error
import urllib.request
from typing import Dict, List, Tuple


def build_payload(variate: bool) -> Dict:
    if not variate:
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

    return {
        "sexe": random.choice(["H", "F"]),
        "age": random.randint(18, 85),
        "poids": round(random.uniform(50, 110), 1),
        "taille": round(random.uniform(150, 195), 1),
        "antecedents_familiaux": random.choice(["oui", "non", "ne_sais_pas"]),
        "heures_assis": random.choice(["<3h", "3-7h", ">7h"]),
        "activite_physique": random.choice(["<30min", "~30min", ">30min"]),
        "tabac": random.choice(["oui", "ancien_5ans", "non"]),
        "tabac_passif": random.choice(["oui", "non"]),
        "fruits_legumes": random.choice(["<2/sem", "2-5/sem", "2-4/jour", "5+/jour"]),
        "ajout_sel": random.choice(["oui", "non"]),
        "preparation_repas": random.choice(["industriel", "maison", "conserves"]),
        "charcuterie_fromage": random.choice(["oui", "non"]),
        "stress": random.choice(["jamais", "occasionnel", "permanent"]),
        "coleres": random.choice(["jamais", "peu", "frequent", "tres_frequent"]),
        "charge_familiale_seule": random.choice(["oui", "non"]),
        "alcool_excessif": random.choice(["oui", "non"]),
        "boissons_energisantes": random.choice(["oui", "non"]),
        "hypertension": random.choice(["oui", "non"]),
        "tension_systolique": random.choice([None, random.randint(100, 180)]),
        "tension_diastolique": random.choice([None, random.randint(60, 110)]),
        "cholesterol_eleve": random.choice(["oui", "non"]),
        "cholesterol_total": random.choice([None, round(random.uniform(4.0, 8.0), 1)]),
        "cholesterol_ldl": random.choice([None, round(random.uniform(2.0, 5.0), 1)]),
        "cholesterol_hdl": random.choice([None, round(random.uniform(0.8, 1.8), 1)]),
        "diabete": random.choice(["oui", "non"]),
        "glycemie": random.choice([None, round(random.uniform(0.8, 1.6), 2)]),
        "apnee_sommeil": random.choice(["oui", "non"]),
        "troubles_sommeil": random.choice(["oui", "non"]),
    }


def one_request(url: str, timeout: float, variate: bool) -> Tuple[int, float]:
    payload = build_payload(variate)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            # Lire le body pour simuler un client réel
            _ = resp.read()
    except urllib.error.HTTPError as e:
        code = int(e.code)
    except Exception:
        code = 0
    dt_ms = (time.perf_counter() - t0) * 1000.0
    return code, dt_ms


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Simuler plusieurs personnes sur /api/calc")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/calc", help="URL de l'endpoint")
    parser.add_argument("--total", type=int, default=1000, help="Nombre total de requêtes")
    parser.add_argument("--concurrency", type=int, default=50, help="Nombre de workers simultanés")
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout d'une requête (secondes)")
    parser.add_argument("--variate", action="store_true", help="Varier les payloads (plus réaliste)")
    args = parser.parse_args()

    t_all = time.perf_counter()
    codes: List[int] = []
    latencies: List[float] = []

    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(one_request, args.url, args.timeout, args.variate) for _ in range(args.total)]
        for f in cf.as_completed(futures):
            code, lat = f.result()
            codes.append(code)
            latencies.append(lat)

    total_time = time.perf_counter() - t_all
    ok_2xx = sum(1 for c in codes if 200 <= c < 300)
    count_422 = codes.count(422)
    count_5xx = sum(1 for c in codes if 500 <= c < 600)
    count_network = codes.count(0)

    print("=== Résumé charge API ===")
    print(f"URL            : {args.url}")
    print(f"Total requêtes : {args.total}")
    print(f"Concurrence    : {args.concurrency}")
    print(f"Durée totale   : {total_time:.2f}s")
    print(f"Débit moyen    : {args.total / total_time:.2f} req/s")
    print("--- Statuts ---")
    print(f"2xx            : {ok_2xx}")
    print(f"422            : {count_422}")
    print(f"5xx            : {count_5xx}")
    print(f"erreurs réseau : {count_network}")
    print("--- Latences (ms) ---")
    print(f"min            : {min(latencies):.2f}")
    print(f"moyenne        : {statistics.mean(latencies):.2f}")
    print(f"p50            : {percentile(latencies, 50):.2f}")
    print(f"p90            : {percentile(latencies, 90):.2f}")
    print(f"p95            : {percentile(latencies, 95):.2f}")
    print(f"p99            : {percentile(latencies, 99):.2f}")
    print(f"max            : {max(latencies):.2f}")


if __name__ == "__main__":
    main()

