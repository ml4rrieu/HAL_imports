# Imports automatiques dans HAL et mailing aux auteurs 

Les codes partagés permettent : 

1. de verser automatiquement dans HAL des métadonnées récupérées depuis Scopus
2. d'effectuer du mailing aux auteurs pour les inciter à partager leur publication en accès ouvert


**2021-02 version pré-alpha**

***

## Reproduire le code pour son établissement

### 0. Configuration
- Installer python et les librairies listées dans le fichier `requirement.txt`
- Télécharger le .zip de ce dépot et dézipper
- Créer un fichier décrivant vos laboratoires à l'instar du fichier `data\stable\labCriteria.csv`
- Créer un fichier csv pour récupérer les données auteurs affiliés à votre établissement, avec les colonnes `key, surname, forename, initial, labname, orcid, mail, scopusId`
- Créer le fichier `path_and_perso_data.json` dans le dossier  `data\stable\` avec vos informations en respectant le modèle suivant : 

```json
{
	"path_labCriteria":"chemin et nom du fichier décrivant les laboratoires. voir ./hal_depot_auto/source/labCriteria.csv",
	"path_validAuthDb": "chemin et nom de la base de données locale en .csv sur les auteurs de votre établissement",
	"univ_scopusId" : 60029937,
	"univ_halStructId" : 81173,
	"perso_hal_contributorId" : 751146,
	"perso_login_halPreprod" : "login compte preprod hal",
	"perso_mdp_halPreprod" : "mdp compte preprod hal",
	"perso_login_hal" : "login compte hal",
	"perso_mdp_hal" : "mdp compte HAL",
	"perso_email": "your.email@univ.fr",
	"perso_scopusApikey" : false,
	"perso_scopusInstToken": false,
	"perso_login_server": "login pour se connecter au serveur",
	"perso_pwd_server" : "mot de passe"
}

```

<br />

### 1. Préparer les données

- Depuis scopus extraire une liste de publications (export en `csv` avec toutes les informations)

- Placez ce fichier dans le dossier `data/scopus_biblio/`

- Ouvrir le code `1_produce_tei_and_deposit2hal.py` et renseigner le nom du fichier dans la variable  `scopus_filename`

- Lancez le code avec `step = "verif_data"`

- Modifiez le cas échéant le fichier de scopus (colonne auteur) jusqu'à ce que tous les documents soient traités

- Relancez le code avec `step = "verif_auth"`

<br />

### 2. Alimenter une base de données locale sur les auteurs de votre établissement

- Lancez le code avec `step = "update_auth_db"` pour alimenter la base de données auteurs. Vérifiez dans la console si il y a des vérifications à faire la main

<br />

### 3. Produire les fichiers TEI

- Lancez le code avec `step = "produce_tei"`

- Reperez dans la console les publications pour lesquelles un domaine a été ajouté automatiquement, les vérifier et si nécessaure les modifier directement dans la TEI généré. (Quand aucun domaine n'a pu être déduit c'est celui de la santé qui est ajouté par défaut)

<br />

### 4. Récupérer les infos d'Unpaywall et verser dans HAL

- Lancez le code avec `step = "tei2preprod"` pour d'abord déposer dans la preprod

- Le cas échéant corriger les erreurs survenues lors des dépôts. Voir le fichier  `data/erreur_depot_hal.txt`

(la plupart des erreurs viennent de la preprod qui ne contient pas les identifiants récents de structures ou journaux)

- Lancez le code avec `step = "tei2hal"` pour cette fois alimenter HAL. Retrouvez la liste des documents traités dans `data/doc_imported.csv`

<br />

### 5. Enrichir les métadonnées

- Ajoutez une colonne `mail correspondant` dans le fichier `data/doc_imported.csv`. Compléter cette colonne d'un email d'un auteur pour les publications de type _article_ qui ne sont pas déjà en accès ouvert. Le but étant d'informer ces auteurs qu'ils peuvent, conformément à la loi pour une république numérique, les partager légalement dans HAL. (à l'UVSQ le tableau est chargé dans google drive pour travaille en équipe)

- Pour les doctype "communications dans un congrès" modifier la ville et le pays (par défaut `unknow` et `France` sont renseignés)

- Complétez autant que souhaité les affiliations des notices importées ou déjà présentes

<br />

### 6. Envoyer les emails

- Personnalisez les modèles d'emails `mailing_auteur/message.txt` et `mailing_auteur/message_pluriel.txt`

- Ouvrir le code  `2.mailing_auth.py`

- Dans la variable `liste_publi_ac_email` renseigner le tableau contenant les publications à traiter avec les emails des auteurs à contacter

- Si besoin tester avec `step = "test"`, puis envoyer tous les emails avec `step = "envoi"`


*** 

**todo**

dans le tableau de sortie  `doc_imported.csv` pre remplir l'email avec auteur de l'université ou auteur correspondant


~~regorganiser l'arborescence et code pour plus de fluidité~~

~~suppression des erreurs d'imports avec les types OUV COUV et COMM~~

~~amelioration detection langue du 2nd titre~~

~~ajour d'un fichier de correspondance iso-639-3 pour la langue des publications~~ 

~~resolution du probleme de domaine (déduction du domaine à partir du journal si au moins 10 occurences)~~

~~allégement : path_scopusStruct2halStruct déjà dans labCriteria.csv~~

~~prise en compte des data paper et article in press~~

~~extraire le mail de l'auteur correspondant~~

<br />

**vigilance**

- Si dépot dans HAL avec fichier en embargo, notre code le marque comme non OA (déduit de unpaywall) et si article un email sera envoyé : trouver une solution (req dans HAL et si file considérer OA ? )

- Ne pas laisser un laps de temps trop important entre le moment où les données de Unpaywall sont récupérées et celui où les auteurs sont contactés. Par expérience, si on laisse plus d'un mois on risque de contacter des auteurs alors que les articles ont été entre temps déposés dans une archive ouverte.

<br />
<br />

## Statistiques

fev. 2021

600 notices importées

311 emails envoyés

200 notices vérifiées déjà présentes dans HAL

100 pdf déposées par le SCD ou par les auteurs

<br />
voir les imports effectués : https://hal.archives-ouvertes.fr/search/index/q/*/contributorId_i/751146




