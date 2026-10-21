#!/usr/bin/env python3
"""Verifie les seuils de performance d'un run JMeter ou Locust.

Sert de garde-fou en CI : le job echoue si le p95 depasse le seuil ou si des
erreurs sont apparues. Sans cela, un test de charge en CI est toujours vert,
meme quand la cible s'effondre.

Usage
-----
    python ci/check_thresholds.py --jtl resultats.jtl --max-p95-ms 500
    python ci/check_thresholds.py --locust-csv resultats_stats.csv --max-p95-ms 500

Le format est deduit du fichier : `.jtl` = JMeter, sinon CSV Locust.
Code de sortie : 0 si tout est sous les seuils, 1 sinon.

Note sur le percentile : calcul par rang (methode du plus proche rang), sans
interpolation. Le rapport HTML de JMeter interpole et peut afficher une valeur
legerement differente (ex. 101,9 ms contre 100 ms) ; l'ecart est sans effet sur
un seuil de garde-fou.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def percentile(values: list[float], ratio: float) -> float:
    """Percentile par rang (methode du plus proche rang), suffisant pour un seuil."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(-(-ratio * len(ordered) // 1)) - 1))
    return ordered[index]


def read_jtl(path: Path) -> tuple[int, list[float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"{path} ne contient aucun echantillon")
    latencies = [float(row["elapsed"]) for row in rows]
    failures = sum(1 for row in rows if str(row.get("success", "")).strip().lower() != "true")
    return failures, latencies


def read_locust_csv(path: Path) -> tuple[int, float, list[float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    aggregated = [row for row in rows if str(row.get("Name", "")).strip() == "Aggregated"]
    if not aggregated:
        raise SystemExit(f"{path} : ligne 'Aggregated' introuvable")
    row = aggregated[0]
    failures = int(float(row["Failure Count"]))
    requests = int(float(row["Request Count"]))
    p95 = float(row["95%"])
    return failures, p95, [p95] * requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifie les seuils d'un run de performance")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--jtl", type=Path, help="resultats bruts JMeter (.jtl)")
    source.add_argument("--locust-csv", type=Path, help="CSV _stats produit par Locust")
    parser.add_argument("--max-p95-ms", type=float, default=500.0, help="seuil p95 en ms (defaut 500)")
    parser.add_argument("--max-failures", type=int, default=0, help="nombre d'echecs tolere (defaut 0)")
    args = parser.parse_args()

    if args.jtl:
        tool = "JMeter"
        if not args.jtl.is_file():
            raise SystemExit(f"Fichier introuvable : {args.jtl}")
        failures, latencies = read_jtl(args.jtl)
        count = len(latencies)
        p95 = percentile(latencies, 0.95)
        p99 = percentile(latencies, 0.99)
        average = sum(latencies) / count
    else:
        tool = "Locust"
        if not args.locust_csv.is_file():
            raise SystemExit(f"Fichier introuvable : {args.locust_csv}")
        failures, p95, _ = read_locust_csv(args.locust_csv)
        rows = list(csv.DictReader(args.locust_csv.open(newline="", encoding="utf-8")))
        aggregated = next(row for row in rows if str(row.get("Name", "")).strip() == "Aggregated")
        count = int(float(aggregated["Request Count"]))
        average = float(aggregated["Average Response Time"])
        p99 = float(aggregated["99%"])

    print(f"Outil          : {tool}")
    print(f"Requetes       : {count}")
    print(f"Echecs         : {failures} (tolere : {args.max_failures})")
    print(f"Latence moyenne: {average:.1f} ms")
    print(f"p95            : {p95:.1f} ms (seuil : {args.max_p95_ms:.0f} ms)")
    print(f"p99            : {p99:.1f} ms")

    problems = []
    if failures > args.max_failures:
        problems.append(f"{failures} echec(s) > {args.max_failures} tolere(s)")
    if p95 > args.max_p95_ms:
        problems.append(f"p95 a {p95:.1f} ms > seuil {args.max_p95_ms:.0f} ms")

    if problems:
        print("\nECHEC : " + " ; ".join(problems), file=sys.stderr)
        return 1

    print("\nOK : tous les seuils sont respectes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
