#!/usr/bin/env python3
"""Met à jour l'entrée d'une région dans le catalogue lu par Sente.

Usage : catalogue.py <ancien catalogue (peut ne pas exister)> <nouveau catalogue>
Variables d'environnement : REGION, ZOOM_MAX, SOURCE_JOUR, GITHUB_REPOSITORY.
"""
import datetime
import hashlib
import json
import os
import sys

ancien, nouveau = sys.argv[1], sys.argv[2]
region_id = os.environ["REGION"]
fichier = f"{region_id}.pmtiles"

definitions = {r["id"]: r for r in json.load(open("regions.json", encoding="utf-8"))}
definition = definitions[region_id]

empreinte = hashlib.sha256()
with open(fichier, "rb") as f:
    for bloc in iter(lambda: f.read(1024 * 1024), b""):
        empreinte.update(bloc)

catalogue = {"format": 1, "regions": []}
if os.path.exists(ancien):
    with open(ancien, encoding="utf-8") as f:
        catalogue = json.load(f)

entree = {
    "id": region_id,
    "nom": definition["nom"],
    "fichier": fichier,
    "url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases/download/regions/{fichier}",
    "taille": os.path.getsize(fichier),
    "sha256": empreinte.hexdigest(),
    "donnees": os.environ["SOURCE_JOUR"],
    "zoom_max": int(os.environ["ZOOM_MAX"]),
    "bbox": definition["bbox"],
}

catalogue["regions"] = [r for r in catalogue.get("regions", []) if r["id"] != region_id] + [entree]
catalogue["regions"].sort(key=lambda r: r["nom"])
catalogue["genere"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
catalogue["attribution"] = "© les contributeurs d'OpenStreetMap (ODbL), carte Protomaps"

with open(nouveau, "w", encoding="utf-8") as f:
    json.dump(catalogue, f, ensure_ascii=False, indent=2)
