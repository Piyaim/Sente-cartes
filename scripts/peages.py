#!/usr/bin/env python3
"""Fabrique le fichier des péages d'une région pour Sente, à partir d'OpenTollData.

Source : OpenTollData (https://github.com/louis2038/OpenTollData), données sous licence ODbL 1.0,
version figée par son identifiant de commit (variable OPENTOLLDATA du workflow).

On garde les gares de péage situées dans l'emprise de la région, élargie pour ne pas couper les
sections qui la traversent, avec les tarifs de chaque section fermée (entrée → sortie) et de chaque
barrière ouverte, pour les 5 classes françaises (1 : voiture, 5 : moto).

Usage : peages.py --region ID --bbox O,S,E,N --entree GLOBAL_networkV4.json --commit SHA --sortie FICHIER.json
"""
import argparse
import json
import sys

FORMAT = 1
MARGE = 0.6  # degrés ajoutés autour de la région : gares voisines d'une section qui entre dans la région
CLASSES = ("class_1", "class_2", "class_3", "class_4", "class_5")


def prix(valeurs):
    """Les 5 tarifs en centimes (entiers : pas d'arrondi flottant côté appli)."""
    return [int(round(float(valeurs[c]) * 100)) for c in CLASSES]


def date_iso(date_fr):
    """« 03/04/2026 » → « 20260403 »."""
    j, m, a = date_fr.split("/")
    return f"{a}{m.zfill(2)}{j.zfill(2)}"


def construire(args):
    source = json.load(open(args.entree, encoding="utf-8"))
    ouest, sud, est, nord = (float(v) for v in args.bbox.split(","))

    noms = []
    index = {}
    gares = []
    for nom, d in sorted(source["toll_description"].items()):
        lat, lon = float(d["lat"]), float(d["lon"])
        if not (sud - MARGE <= lat <= nord + MARGE and ouest - MARGE <= lon <= est + MARGE):
            continue
        index[nom] = len(noms)
        noms.append(nom)
        gares.append({
            "n": nom,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "t": "o" if d.get("type") == "open" else "f",
            "op": d.get("operator", ""),
        })

    sections = []
    vues = set()
    for reseau in source["networks"]:
        for entree, sorties in reseau["connection"].items():
            if entree not in index:
                continue
            for sortie, valeurs in sorties.items():
                if sortie not in index or entree == sortie:
                    continue
                cle = (index[entree], index[sortie])
                if cle in vues:
                    continue
                vues.add(cle)
                distance = valeurs.get("distance") or ""
                sections.append([cle[0], cle[1], float(distance) if distance else None, prix(valeurs["price"])])

    ouvertes = {}
    for nom, valeurs in source["open_toll_price"].items():
        if nom in index:
            ouvertes[str(index[nom])] = prix(valeurs["price"])

    sortie = {
        "format": FORMAT,
        "region": args.region,
        "source": "OpenTollData",
        "commit": args.commit,
        "tarifs": date_iso(source["date"]),
        "licence": "ODbL 1.0 — OpenTollData " + source.get("copyright", "") + " ; © les contributeurs d'OpenStreetMap",
        "classes": ["voiture", "intermédiaire", "poids lourd 2 essieux", "poids lourd 3 essieux et plus", "moto"],
        "gares": gares,
        "sections": sections,
        "ouvertes": ouvertes,
    }
    with open(args.sortie, "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Péages : {len(gares)} gares, {len(sections)} sections, {len(ouvertes)} barrières ouvertes, tarifs du {source['date']}")
    if not gares:
        sys.exit("Aucune gare de péage dans cette région.")
    print(f"PEAGES_JOUR={date_iso(source['date'])}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--region", required=True)
    p.add_argument("--bbox", required=True, help="ouest,sud,est,nord")
    p.add_argument("--entree", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--sortie", required=True)
    construire(p.parse_args())
