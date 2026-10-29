# Sente-cartes

Régions téléchargeables par l'application [Sente](https://github.com/Piyaim/Sente). Chaque région comprend deux fichiers, publiés avec le catalogue (`catalogue.json`) dans la version GitHub [« regions »](../../releases/tag/regions) :

| Fichier | Contenu | Sources |
| --- | --- | --- |
| `<region>.pmtiles` | La carte | Carte quotidienne [Protomaps](https://docs.protomaps.com/basemaps/downloads), produite à partir d'OpenStreetMap |
| `<region>.recherche.db` | L'index de recherche hors ligne (SQLite) : adresses, rues, communes et lieux | Adresses : [Base Adresse Nationale](https://adresse.data.gouv.fr) ; lieux : [OpenStreetMap](https://www.openstreetmap.org) (export [Geofabrik](https://download.geofabrik.de)) |

## Fabriquer ou mettre à jour une région

Onglet **Actions** → **Région** → **Run workflow**, puis choisir :

- la **région** ;
- le **contenu** : `tout`, `carte` seule, ou `recherche` seule (la carte doit alors déjà exister) ;
- le **zoom maximal** de la carte.

Comptez jusqu'à deux heures pour `tout`. Les régions, leurs emprises, départements et extraits OpenStreetMap sont listés dans [regions.json](regions.json).

## Ce que contient le catalogue

Pour chaque région et chaque fichier : nom, adresse, taille en octets, empreinte SHA-256 (vérifiée par Sente après téléchargement) et date des données.

## Licences

- **Carte** : © les contributeurs d'[OpenStreetMap](https://www.openstreetmap.org/copyright), licence [ODbL](https://opendatacommons.org/licenses/odbl/) ; les tuiles Protomaps sont une œuvre produite (« Produced Work ») de ces données.
- **Index de recherche** : base dérivée d'OpenStreetMap, publiée sous licence **ODbL**. Elle contient aussi les adresses de la Base Adresse Nationale, publiées sous [Licence Ouverte 2.0](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0) (compatible), avec mention de la source et de la date dans la table `meta` du fichier.
- **Code de ce dépôt** (workflow et scripts) : [GNU AGPL v3 ou ultérieure](LICENSE).

## Vie privée

Télécharger un fichier depuis GitHub transmet à GitHub votre adresse IP et les informations ordinaires d'une requête web. Sente n'y ajoute aucun identifiant. Pour n'avoir aucun échange réseau, copiez les fichiers sur le téléphone et importez-les depuis Sente.
