# Imports automatiques dans HAL et mailing aux auteurs 

Les codes partagés permettent : 

1. de déposer automatiquement dans HAL  à partir d'une extraction de Scopus
2. d'effectuer du mailing aux auteurs pour les inviter à partager leur publication en accès ouvert



**2021-01 version béta**

# todo

~~inclure les data paper~~

alléger : path_scopusStruct2halStruct déjà dans labCriteria.csv

ajouter un dict de correspondance entre pays scopus & pays HAL

pemrettre l'envoi à plusieurs destinataires

probleme avec domaine archi

retirer ISSN si chapitre d'ouvreage

~~extraire le mail de l'auth correspondant~~


***

## Reproduire le code pour son établissement

### 0. Configuration
- Installer python et les librairies listées dans le fichier `requirement.txt`
- Télécharger le .zip de ce dépot et dézipper
- Créer un fichier décrivant vos laboratoires à l'instar du fichier `hal_depot_auto\source\labCriteria.csv`
- Créer un fihcier csv pour récupérer les données auteurs affiliés à votre établissement, avec les colonnes `key, surname, forename, initial, labname, orcid, mail, scopusId`
- Créer le fichier `path_and_perso_data.json`, à la racine, avec vos informations en suivant ce modèle :

```json
{
	"path_labCriteria":"chemin et nom du fichier décrivant les laboratoires. voir ./hal_depot_auto/source/labCriteria.csv",
	"path_validAuthDb": "chemin et nom de la base de données locale en .csv sur les auteurs de votre établissement",
	"path_scopusStruct2halStruct":"chemin du fichier de correspondance entre les identifiants structures de HAL et ceux de Scopus",
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

- Extraire une liste de publications depuis scopus (export en `csv` avec toutes les informations)

- Placer ce fichier dans le dossier `hal_depot_auto/source/`

- Ouvrir le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` et préciser le dernier export de scopus (ligne 29)

- Lancez le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` avec le paramétrage `step = verifData`

- Modifier en conséquent le champs auteur du fichier source jusqu'a ce qu'il n'y ait plus d'erreur

- Lancez le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` avec le paramétrage `step = verifAuth`

<br />

### 2. Alimenter une base de données locale sur les auteurs de votre établissement

- Lancez le code `hal_depot_auto/code/1bis_populate_valid_auth_db.py` pour alimenter la base de données auteurs

<br />

### 3. Produire les fichiers TEI

- Lancez le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` avec le paramétrage `step = produceTei`

<br />

### 4. Récupérer depuis unpaywall les infos d'accès ouvert et verser dans HAL

- Lancez le code `hal_depot_auto/code/2_deposit_tei_to_hal.py`

<br />

### 5. Enrichir les métadonnées

- Retrouver la liste des publications importées dans le fichier `hal_depot_auto/out/doc_imported.csv`

- Dans HAL compléter les lacunes d'affiliations et ajouter les emails des auteurs à contacter

<br />

### 6. Envoyer les emails

- ouvrir le code  `mailing_auteur/mailing_auth.py`

- tester si nécessaire puis envoyer les emails `step = "envoi" `


 