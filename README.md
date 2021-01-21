**2021-01 en construction**

Codes permettant (1) de déposer automatiquement dans HAL  à partir d'une extraction de Scopus et (2)
d'effectuer du mailing aux auteurs pour les inviter à partager leur publication en accès ouvert si ce n'est déjà le cas.

### Configuration
- Installer python et les librairies listées dans le fichier `requirement.txt`
- Télécharger le .zip de ce dépot et dézipper
- Compléter le fichier `path_and_perso_data.json` avec vos informations conformémant au modèle :
```json
{
	"path_labCriteria":"chemin et nom du fichier décrivant les laboratoires de votre établissement",
	"path_validAuthDb": "chemin et nom de la base de données locale en .csv sur les auteurs de votre établissement",
	"path_scopusStruct2halStruct":"chemin du fichier de correspondance entre les identifiants structures de HAL et ceux de Scopus",
	"perso_hal_contributorId" : 751146, //votre numero de contributeur HAL
	"perso_login_halPreprod" : "login compte preprod hal",
	"perso_mdp_halPreprod" : "mdp compte preprod hal",
	"perso_login_hal" : "login compte hal",
	"perso_mdp_hal" : "mdp compte HAL",
	"perso_email":"your.email@univ.fr", // pour requeter dans Unpaywall
	"perso_scopusApikey" : false,
	"perso_scopusInstToken": false,
	"perso_login_server": "login pour se connecter au serveur",
	"perso_pwd_server" : "mot de passe"
}

```

### Etapes

<br />

**Préparer les données**

- Extraire une liste de publications depuis scopus (export en `csv` avec toutes les informations)

- Placer ce fichier dans le dossier `hal_depot_auto/source/`

- Ouvrir le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` et préciser le dernier export de scopus (ligne 29)

- Lancez le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` avec le paramétrage `step = verifData`

- Modifier en conséquent le champs auteur du fichier source jusqu'a ce qu'il n'y ait plus d'erreur

- Lancez le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` avec le paramétrage `step = verifAuth`

<br />

**Alimenter une base de données locale sur les auteurs de votre établissement**

- Lancez le code `hal_depot_auto/code/1bis_populate_valid_auth_db.py` pour alimenter la base de données auteurs

<br />

**Produire les fichiers TEI**

- Lancez le code `hal_depot_auto/code/1_from_scopus_csv_produce_TEI.py` avec le paramétrage `step = produceTei`

**Récupérer les infos d'accès ouvert et verser dans HAL** 

- Lancez le code `hal_depot_auto/code/2_deposit_tei_to_hal.py`

<br />

**Enrichir les métadonnées**

- retrouver les notices importées dans HAL dans le fichier `hal_depot_auto/out/doc_imported.csv`

- Compléter dans HAL les lacunes d'affiliations et ajouter les emails des auteurs à contacter

<br />

**Envoyer les emails**

- ouvrir le code  `mailing_auteur/mailing_auth.py`

- tester si nécessaire puis envoyer les emails `step = "envoi" `
**** 


 




# mailing_authors
Script permettant de faire des mails automatiques aux auteurs correspondants des _articles_ non disponibles en accès ouvert. 
En accord avec la loi "Pour une répblique numérique" on invite les auteurs à déposer la version acceptée pour publication de leur article.


