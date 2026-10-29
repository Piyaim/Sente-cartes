#!/usr/bin/env python3
"""Fabrique l'index de recherche hors ligne d'une région (SQLite) pour Sente.

Sources :
  - adresses : Base Adresse Nationale (CSV par département, Licence Ouverte 2.0) ;
  - lieux : OpenStreetMap (export GeoJSON ligne à ligne d'osmium, ODbL).

Usage : recherche.py --region ID --ban DOSSIER --osm FICHIER.geojsonseq --sortie FICHIER.db

Le texte indexé est « normalisé » (minuscules, sans accents ni ponctuation) ; l'appli
applique exactement la même normalisation à ce que l'on tape (Normalisation.kt).
"""
import argparse
import csv
import datetime
import glob
import gzip
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter

FORMAT = 1

# ---------------------------------------------------------------- normalisation

_REMPLACEMENTS = {"œ": "oe", "æ": "ae", "ß": "ss"}
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normaliser(texte: str) -> str:
    """Identique à Normalisation.normaliser() côté appli."""
    texte = texte.lower()
    for a, b in _REMPLACEMENTS.items():
        texte = texte.replace(a, b)
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return _NON_ALNUM.sub(" ", texte).strip()


# ---------------------------------------------------------------- catégories OSM

# (clé, valeur) → (code, libellé). Le code sert aux recherches par catégorie de l'appli.
CATEGORIES = {
    ("shop", "bakery"): ("bakery", "Boulangerie"),
    ("shop", "pastry"): ("pastry", "Pâtisserie"),
    ("shop", "supermarket"): ("supermarket", "Supermarché"),
    ("shop", "convenience"): ("convenience", "Supérette"),
    ("shop", "butcher"): ("butcher", "Boucherie"),
    ("shop", "greengrocer"): ("greengrocer", "Primeur"),
    ("shop", "cheese"): ("cheese", "Fromagerie"),
    ("shop", "wine"): ("wine", "Caviste"),
    ("shop", "books"): ("books", "Librairie"),
    ("shop", "newsagent"): ("newsagent", "Presse"),
    ("shop", "tobacco"): ("tobacco", "Tabac"),
    ("shop", "florist"): ("florist", "Fleuriste"),
    ("shop", "hairdresser"): ("hairdresser", "Coiffeur"),
    ("shop", "optician"): ("optician", "Opticien"),
    ("shop", "clothes"): ("clothes", "Vêtements"),
    ("shop", "shoes"): ("shoes", "Chaussures"),
    ("shop", "hardware"): ("hardware", "Quincaillerie"),
    ("shop", "doityourself"): ("doityourself", "Bricolage"),
    ("shop", "electronics"): ("electronics", "Électronique"),
    ("shop", "mobile_phone"): ("mobile_phone", "Téléphonie"),
    ("shop", "bicycle"): ("bicycle", "Vélociste"),
    ("shop", "car_repair"): ("car_repair", "Garage"),
    ("shop", "car"): ("car", "Concession automobile"),
    ("shop", "motorcycle"): ("motorcycle", "Concession moto"),
    ("shop", "tyres"): ("tyres", "Pneus"),
    ("shop", "sports"): ("sports", "Sport"),
    ("shop", "furniture"): ("furniture", "Ameublement"),
    ("shop", "garden_centre"): ("garden_centre", "Jardinerie"),
    ("shop", "laundry"): ("laundry", "Laverie"),
    ("shop", "dry_cleaning"): ("dry_cleaning", "Pressing"),
    ("shop", "beauty"): ("beauty", "Institut de beauté"),
    ("shop", "pet"): ("pet", "Animalerie"),
    ("shop", "chemist"): ("chemist", "Droguerie"),
    ("shop", "department_store"): ("department_store", "Grand magasin"),
    ("amenity", "fuel"): ("fuel", "Station-service"),
    ("amenity", "charging_station"): ("charging_station", "Borne de recharge"),
    ("amenity", "parking"): ("parking", "Parking"),
    ("amenity", "bicycle_parking"): ("bicycle_parking", "Parking vélos"),
    ("amenity", "motorcycle_parking"): ("motorcycle_parking", "Parking motos"),
    ("amenity", "pharmacy"): ("pharmacy", "Pharmacie"),
    ("amenity", "hospital"): ("hospital", "Hôpital"),
    ("amenity", "clinic"): ("clinic", "Clinique"),
    ("amenity", "doctors"): ("doctors", "Médecin"),
    ("amenity", "dentist"): ("dentist", "Dentiste"),
    ("amenity", "veterinary"): ("veterinary", "Vétérinaire"),
    ("amenity", "restaurant"): ("restaurant", "Restaurant"),
    ("amenity", "fast_food"): ("fast_food", "Restauration rapide"),
    ("amenity", "cafe"): ("cafe", "Café"),
    ("amenity", "bar"): ("bar", "Bar"),
    ("amenity", "pub"): ("bar", "Bar"),
    ("amenity", "ice_cream"): ("ice_cream", "Glacier"),
    ("amenity", "post_office"): ("post_office", "Bureau de poste"),
    ("amenity", "bank"): ("bank", "Banque"),
    ("amenity", "atm"): ("atm", "Distributeur de billets"),
    ("amenity", "toilets"): ("toilets", "Toilettes"),
    ("amenity", "drinking_water"): ("drinking_water", "Eau potable"),
    ("amenity", "townhall"): ("townhall", "Mairie"),
    ("amenity", "library"): ("library", "Bibliothèque"),
    ("amenity", "school"): ("school", "École"),
    ("amenity", "college"): ("college", "Lycée"),
    ("amenity", "university"): ("university", "Université"),
    ("amenity", "kindergarten"): ("kindergarten", "École maternelle"),
    ("amenity", "cinema"): ("cinema", "Cinéma"),
    ("amenity", "theatre"): ("theatre", "Théâtre"),
    ("amenity", "marketplace"): ("marketplace", "Marché"),
    ("amenity", "place_of_worship"): ("place_of_worship", "Lieu de culte"),
    ("amenity", "police"): ("police", "Police / gendarmerie"),
    ("amenity", "fire_station"): ("fire_station", "Caserne de pompiers"),
    ("amenity", "bus_station"): ("bus_station", "Gare routière"),
    ("amenity", "car_rental"): ("car_rental", "Location de voitures"),
    ("amenity", "car_wash"): ("car_wash", "Lavage auto"),
    ("amenity", "bicycle_rental"): ("bicycle_rental", "Location de vélos"),
    ("tourism", "museum"): ("museum", "Musée"),
    ("tourism", "hotel"): ("hotel", "Hôtel"),
    ("tourism", "guest_house"): ("guest_house", "Chambre d'hôtes"),
    ("tourism", "hostel"): ("hostel", "Auberge de jeunesse"),
    ("tourism", "camp_site"): ("camp_site", "Camping"),
    ("tourism", "caravan_site"): ("caravan_site", "Aire de camping-cars"),
    ("tourism", "attraction"): ("attraction", "Site touristique"),
    ("tourism", "viewpoint"): ("viewpoint", "Point de vue"),
    ("tourism", "picnic_site"): ("picnic_site", "Aire de pique-nique"),
    ("tourism", "zoo"): ("zoo", "Zoo"),
    ("tourism", "theme_park"): ("theme_park", "Parc d'attractions"),
    ("leisure", "park"): ("park", "Parc"),
    ("leisure", "sports_centre"): ("sports_centre", "Centre sportif"),
    ("leisure", "swimming_pool"): ("swimming_pool", "Piscine"),
    ("leisure", "stadium"): ("stadium", "Stade"),
    ("railway", "station"): ("station", "Gare"),
    ("railway", "halt"): ("station", "Gare"),
    ("aerialway", "station"): ("aerialway_station", "Remontée mécanique"),
    ("natural", "peak"): ("peak", "Sommet"),
    ("place", "city"): ("city", "Ville"),
    ("place", "town"): ("town", "Ville"),
    ("place", "village"): ("village", "Village"),
    ("place", "suburb"): ("suburb", "Quartier"),
    ("place", "quarter"): ("suburb", "Quartier"),
    ("place", "neighbourhood"): ("neighbourhood", "Quartier"),
    ("place", "hamlet"): ("hamlet", "Hameau"),
    ("place", "locality"): ("locality", "Lieu-dit"),
}

# Ces lieux sont utiles même sans nom (on trouve « la station la plus proche »).
SANS_NOM_ACCEPTES = {"fuel", "charging_station", "parking", "toilets", "atm", "drinking_water",
                     "bicycle_parking", "motorcycle_parking", "pharmacy"}

ORDRE_CLES = ("amenity", "shop", "tourism", "leisure", "railway", "aerialway", "natural", "place")


def categorie(tags):
    for cle in ORDRE_CLES:
        valeur = tags.get(cle)
        if valeur and (cle, valeur) in CATEGORIES:
            return CATEGORIES[(cle, valeur)]
    if tags.get("shop") and tags.get("shop") != "vacant":
        return ("shop", "Commerce")
    return None


def point_representatif(geometrie):
    """Point pour un nœud ; moyenne des sommets de l'anneau extérieur pour une surface."""
    t, c = geometrie.get("type"), geometrie.get("coordinates")
    if t == "Point":
        return c[0], c[1]
    if t == "Polygon":
        anneau = c[0]
    elif t == "MultiPolygon":
        anneau = max((p[0] for p in c), key=len)
    else:
        return None
    anneau = anneau[:-1] if len(anneau) > 1 and anneau[0] == anneau[-1] else anneau
    return sum(p[0] for p in anneau) / len(anneau), sum(p[1] for p in anneau) / len(anneau)


def adresse_osm(tags):
    rue = " ".join(x for x in (tags.get("addr:housenumber"), tags.get("addr:street")) if x)
    ville = " ".join(x for x in (tags.get("addr:postcode"), tags.get("addr:city")) if x)
    return ", ".join(x for x in (rue, ville) if x)


def e6(valeur: float) -> int:
    return int(round(valeur * 1_000_000))


# ---------------------------------------------------------------- BAN

def lire_ban(dossier):
    """Renvoie (voies, numéros, communes). Accepte le format « csv » et, à défaut, « csv-bal »."""
    voies = {}        # clé (insee, nom) → [id, nom, commune, Counter(cp), somme_lat, somme_lon, n]
    numeros = []      # (id_voie, numéro, lat, lon)
    communes = {}     # insee → [nom, Counter(cp), somme_lat, somme_lon, n]
    fichiers = sorted(glob.glob(os.path.join(dossier, "*.csv.gz")))
    if not fichiers:
        sys.exit(f"Aucun fichier BAN dans {dossier}")
    for chemin in fichiers:
        with gzip.open(chemin, "rt", encoding="utf-8", newline="") as flux:
            lecteur = csv.DictReader(flux, delimiter=";")
            bal = "voie_nom" in (lecteur.fieldnames or [])
            for ligne in lecteur:
                if bal:
                    nom_voie = ligne.get("voie_nom") or ligne.get("lieudit_complement_nom") or ""
                    insee, nom_commune, cp = ligne.get("commune_insee", ""), ligne.get("commune_nom", ""), ""
                    numero, rep = ligne.get("numero", ""), ligne.get("suffixe", "")
                    lon, lat = ligne.get("long", ""), ligne.get("lat", "")
                else:
                    nom_voie = ligne.get("nom_voie") or ligne.get("nom_ld") or ""
                    insee, nom_commune, cp = ligne.get("code_insee", ""), ligne.get("nom_commune", ""), ligne.get("code_postal", "")
                    numero, rep = ligne.get("numero", ""), ligne.get("rep", "")
                    lon, lat = ligne.get("lon", ""), ligne.get("lat", "")
                try:
                    lat_f, lon_f = float(lat), float(lon)
                except ValueError:
                    continue
                if not nom_voie or not insee:
                    continue
                cle = (insee, nom_voie)
                v = voies.get(cle)
                if v is None:
                    v = voies[cle] = [len(voies) + 1, nom_voie, nom_commune, Counter(), 0.0, 0.0, 0]
                if cp:
                    v[3][cp] += 1
                v[4] += lat_f
                v[5] += lon_f
                v[6] += 1
                c = communes.get(insee)
                if c is None:
                    c = communes[insee] = [nom_commune, Counter(), 0.0, 0.0, 0]
                if cp:
                    c[1][cp] += 1
                c[2] += lat_f
                c[3] += lon_f
                c[4] += 1
                try:
                    n = int(numero)
                except ValueError:
                    continue
                if 0 < n < 99999:  # 99999 : lieu-dit sans numéro dans la BAN
                    numeros.append((v[0], f"{n}{(rep or '').strip().lower()}", lat_f, lon_f))
    return voies, numeros, communes


# ---------------------------------------------------------------- base

SCHEMA = """
CREATE TABLE meta (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
CREATE TABLE voies (id INTEGER PRIMARY KEY, nom TEXT NOT NULL, commune TEXT NOT NULL, cp TEXT NOT NULL,
                    lat INTEGER NOT NULL, lon INTEGER NOT NULL);
CREATE VIRTUAL TABLE voies_fts USING fts4(content="", texte);
CREATE TABLE numeros (voie INTEGER NOT NULL, num TEXT NOT NULL, dlat INTEGER NOT NULL, dlon INTEGER NOT NULL,
                      PRIMARY KEY (voie, num)) WITHOUT ROWID;
CREATE TABLE lieux (id INTEGER PRIMARY KEY, nom TEXT NOT NULL, code TEXT NOT NULL, libelle TEXT NOT NULL,
                    lat INTEGER NOT NULL, lon INTEGER NOT NULL, adresse TEXT, horaires TEXT, tel TEXT,
                    site TEXT, fauteuil TEXT, osm TEXT);
CREATE VIRTUAL TABLE lieux_fts USING fts4(content="", texte);
"""


def construire(args):
    if os.path.exists(args.sortie):
        os.remove(args.sortie)
    db = sqlite3.connect(args.sortie)
    db.executescript("PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA page_size=4096;" + SCHEMA)

    voies, numeros, communes = lire_ban(args.ban)
    print(f"BAN : {len(voies)} voies, {len(numeros)} adresses numérotées, {len(communes)} communes")

    centres = {}
    lignes_voies, lignes_fts = [], []
    for (insee, _), (vid, nom, commune, cps, slat, slon, n) in voies.items():
        lat, lon = slat / n, slon / n
        centres[vid] = (lat, lon)
        cp = cps.most_common(1)[0][0] if cps else ""
        lignes_voies.append((vid, nom, commune, cp, e6(lat), e6(lon)))
        lignes_fts.append((vid, normaliser(f"{nom} {commune} {cp}")))
    db.executemany("INSERT INTO voies VALUES (?,?,?,?,?,?)", lignes_voies)
    db.executemany("INSERT INTO voies_fts(docid, texte) VALUES (?,?)", lignes_fts)

    vus = set()
    lignes_num = []
    for vid, num, lat, lon in numeros:
        if (vid, num) in vus:
            continue
        vus.add((vid, num))
        clat, clon = centres[vid]
        # Écart au centre de la voie, au cent-millième de degré (environ 1 m) : petits entiers, base plus légère.
        lignes_num.append((vid, num, int(round((lat - clat) * 100_000)), int(round((lon - clon) * 100_000))))
    db.executemany("INSERT INTO numeros VALUES (?,?,?,?)", lignes_num)
    del vus, lignes_num, numeros

    lieux = []
    for insee, (nom, cps, slat, slon, n) in communes.items():
        cp = cps.most_common(1)[0][0] if cps else ""
        lieux.append((nom, "commune", "Commune", e6(slat / n), e6(slon / n), cp, None, None, None, None, None, f"{nom} {cp}"))

    vus_osm = set()
    with open(args.osm, encoding="utf-8") as flux:
        for ligne in flux:
            ligne = ligne.strip().lstrip("\x1e")
            if not ligne:
                continue
            objet = json.loads(ligne)
            tags = objet.get("properties") or {}
            ident = f"{tags.get('@type', '')}/{tags.get('@id', '')}"
            if ident in vus_osm:
                continue
            vus_osm.add(ident)
            cat = categorie(tags)
            if cat is None:
                continue
            code, libelle = cat
            nom = tags.get("name:fr") or tags.get("name") or ""
            if not nom:
                if code not in SANS_NOM_ACCEPTES:
                    continue
                nom = tags.get("brand") or tags.get("operator") or libelle
            point = point_representatif(objet.get("geometry") or {})
            if point is None:
                continue
            lon, lat = point
            adresse = adresse_osm(tags)
            ville = tags.get("addr:city", "")
            lieux.append((
                nom, code, libelle, e6(lat), e6(lon), adresse or None,
                tags.get("opening_hours"), tags.get("phone") or tags.get("contact:phone"),
                tags.get("website") or tags.get("contact:website"), tags.get("wheelchair"),
                ident if tags.get("@type") in ("node", "way", "relation") else None,
                f"{nom} {libelle} {ville}",
            ))

    print(f"Lieux : {len(lieux)} (dont {len(communes)} communes)")
    for i, l in enumerate(lieux, start=1):
        db.execute("INSERT INTO lieux VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (i,) + l[:11])
        db.execute("INSERT INTO lieux_fts(docid, texte) VALUES (?,?)", (i, normaliser(l[11])))

    db.execute("CREATE INDEX lieux_code ON lieux (code, lat)")
    maintenant = datetime.datetime.now(datetime.timezone.utc)
    for cle, valeur in {
        "format": str(FORMAT),
        "region": args.region,
        "genere": maintenant.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "donnees": maintenant.strftime("%Y%m%d"),
        "sources": "Base Adresse Nationale (Licence Ouverte 2.0) ; © les contributeurs d'OpenStreetMap (ODbL)",
    }.items():
        db.execute("INSERT INTO meta VALUES (?,?)", (cle, valeur))
    db.commit()
    db.execute("INSERT INTO voies_fts(voies_fts) VALUES ('optimize')")
    db.execute("INSERT INTO lieux_fts(lieux_fts) VALUES ('optimize')")
    db.commit()
    db.execute("ANALYZE")
    db.execute("VACUUM")
    db.close()
    print(f"Index : {os.path.getsize(args.sortie) // 1_048_576} Mo")


if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--region", required=True)
    parseur.add_argument("--ban", required=True, help="dossier des CSV BAN (.csv.gz)")
    parseur.add_argument("--osm", required=True, help="export osmium au format geojsonseq")
    parseur.add_argument("--sortie", required=True)
    construire(parseur.parse_args())
