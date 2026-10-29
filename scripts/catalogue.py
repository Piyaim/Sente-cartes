#!/usr/bin/env python3
"""Met à jour l'entrée d'une région dans le catalogue lu par Sente.

Usage : catalogue.py <ancien catalogue (peut ne pas exister)> <nouveau catalogue>
Variables d'environnement : REGION, GITHUB_REPOSITORY, et selon ce qui vient d'être fabriqué :
  - carte : <REGION>.pmtiles présent, ZOOM_MAX, SOURCE_JOUR ;
  - recherche : <REGION>.recherche.db présent, RECHERCHE_JOUR.
Ce qui n'a pas été refabriqué est repris de l'ancien catalogue.
"""
import datetime
import hashlib
import json
import os
import sys

ancien, nouveau = sys.argv[1], sys.argv[2]
region_id = os.environ["REGION"]
depot = os.environ["GITHUB_REPOSITORY"]
carte = f"{region_id}.pmtiles"
recherche = f"{region_id}.recherche.db"

definitions = {r["id"]: r for r in json.load(open("regions.json", encoding="utf-8"))}
definition = definitions[region_id]


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def url(fichier):
    return f"https://github.com/{depot}/releases/download/regions/{fichier}"


catalogue = {"format": 1, "regions": []}
if os.path.exists(ancien):
    with open(ancien, encoding="utf-8") as f:
        catalogue = json.load(f)
precedente = next((r for r in catalogue.get("regions", []) if r["id"] == region_id), None)

if os.path.exists(carte):
    entree = {
        "id": region_id,
        "nom": definition["nom"],
        "fichier": carte,
        "url": url(carte),
        "taille": os.path.getsize(carte),
        "sha256": empreinte(carte),
        "donnees": os.environ["SOURCE_JOUR"],
        "zoom_max": int(os.environ["ZOOM_MAX"]),
        "bbox": definition["bbox"],
    }
    if precedente and "recherche" in precedente:
        entree["recherche"] = precedente["recherche"]
elif precedente:
    entree = dict(precedente)
else:
    sys.exit("Aucune carte pour cette région : fabriquez d'abord la carte (contenu « tout » ou « carte »).")

if os.path.exists(recherche):
    entree["recherche"] = {
        "fichier": recherche,
        "url": url(recherche),
        "taille": os.path.getsize(recherche),
        "sha256": empreinte(recherche),
        "donnees": os.environ["RECHERCHE_JOUR"],
    }

catalogue["regions"] = [r for r in catalogue.get("regions", []) if r["id"] != region_id] + [entree]
catalogue["regions"].sort(key=lambda r: r["nom"])
catalogue["format"] = 1
catalogue["genere"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
catalogue["attribution"] = (
    "Carte : © les contributeurs d'OpenStreetMap (ODbL), tuiles Protomaps. "
    "Recherche : Base Adresse Nationale (Licence Ouverte 2.0) et OpenStreetMap (ODbL)."
)

with open(nouveau, "w", encoding="utf-8") as f:
    json.dump(catalogue, f, ensure_ascii=False, indent=2)
