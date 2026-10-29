# Sente-cartes

Régions téléchargeables par l'application [Sente](https://github.com/Piyaim/Sente).

Chaque région est un fichier PMTiles découpé dans la carte quotidienne [Protomaps](https://docs.protomaps.com/basemaps/downloads), elle-même produite à partir d'OpenStreetMap. Les fichiers et le catalogue (`catalogue.json`) sont publiés dans la version GitHub [« regions »](../../releases/tag/regions).

## Fabriquer ou mettre à jour une région

Onglet **Actions** → **Région** → **Run workflow**, choisir la région et le zoom maximal. Comptez de quelques minutes à une heure selon la taille.

Les régions disponibles et leurs emprises sont listées dans [regions.json](regions.json).

## Ce que contient le catalogue

Pour chaque région : nom, adresse du fichier, taille en octets, empreinte SHA-256 (vérifiée par Sente après téléchargement), date des données et zoom maximal.

## Licences

- **Données cartographiques** : © les contributeurs d'[OpenStreetMap](https://www.openstreetmap.org/copyright), sous licence [ODbL](https://opendatacommons.org/licenses/odbl/). Les tuiles Protomaps sont une œuvre produite (« Produced Work ») de ces données.
- **Code de ce dépôt** (workflow et script) : [GNU AGPL v3 ou ultérieure](LICENSE).

## Vie privée

Télécharger un fichier depuis GitHub transmet à GitHub votre adresse IP et les informations ordinaires d'une requête web. Sente n'y ajoute aucun identifiant. Pour n'avoir aucun échange réseau, copiez le fichier `.pmtiles` sur le téléphone et importez-le depuis Sente.
