import requests, json, csv
import xml.etree.ElementTree as ET
'''
erreurs fréquentes
	journal is empty : c'est la preprod qui n'a pas encore le journal id
	domain : on a encore des pbs de domaine, par exemple archi arrive au lien de shs.archi
	sur les chapitres d'ouvrage
	language indiqué GE alors que ça doit être DE

fichiers de sortie
	out/doc_imported.csv
	out/erreur_depot_hal.txt

Maxence Larrieu 
2021 01
'''


#____________________________________________________________

type_import = 'preprod' #hal ou preprod ou test 
liste_doc_a_traiter = '../out/doc_analysed.csv'
#fichier_source = 'test.csv'

#____________________________________________________________



with open("../../path_and_perso_data.json") as fh : 
	local_data = json.load(fh)

## dpnnées pour le dépots via SWORD
head = {
	'Packaging': 'http://purl.org/net/sword-types/AOfr',
   	'Content-Type': 'text/xml',
   	'X-Allow-Completion' : None
	}

private = {
	'preprod':{
	'url':'https://api-preprod.archives-ouvertes.fr/sword/hal',
	'login': local_data["perso_login_halPreprod"],#maxenveUvsq', 
	'mdp': local_data["perso_mdp_halPreprod"]
	},
	'hal':{
	'url':'https://api.archives-ouvertes.fr/sword/hal',
	'login':local_data["perso_login_hal"],
	'mdp':local_data["perso_mdp_hal"],
	}
}

def reqUnpaywall(doi):
	"""search of repo ia version, if not searc for publisher"""
	url = 'https://api.unpaywall.org/v2/'
	req = requests.get(url+doi+'?email=youremail@inserm.fr')
	
	#print(url+doi+'?email=m@larri.eu')
	try : 
		res = req.json()
	except : 
		pb = "pb in upw answer"
		return 'closed'
	
	if not res.get("best_oa_location") or not res.get('is_oa'): return 'closed'

	if res.get("has_repository_copy") : return 'open in repository'
	if res['best_oa_location'].get("license") : 
		return 'open from publisher :'+ res['best_oa_location']['license']
	return 'open from publisher no license'

#____________________________________________________________


#___0___charger/créer les tables
# charger le fichier listant toutes les publications
doc_a_traiter = open(liste_doc_a_traiter, 'r', encoding='utf8')
reader = csv.DictReader(doc_a_traiter)

# une table de sortie pour lister les publications traitées
doc_imported = open('../out/doc_imported.csv', 'w', newline='', encoding='utf8')
writer = csv.writer(doc_imported)
writer.writerow(['state', 'doc type', 'lien hal', 'open access'])

# un fichier erreur pour sauvegarder les eventuelles erreurs
out_error = open('../out/erreur_depot_hal.txt', 'w', encoding='utf-8')


#___1___traiter les publications
for row in reader : 

	if row['state'] == 'not treated' : continue

	print(f"\n{row['eid']}")
	oatype = reqUnpaywall(row['doi'])
	addRow = [row['doctype'], oatype]

	if row['state'].startswith('already in') :
		addRow.insert(0, 'old')
		addRow.insert(2,row['halUris'])
		writer.writerow(addRow)
		print("\told")
		continue

	#print(f'\n{eid}\n\t{row['doi']}\n\t{addRow}')
						
	try : 
		xmlfh = open('../out/'+row['eid']+'.xml', 'r', encoding='utf-8')
	except : 
		print("\t!! fichier TEI introuvable")
		quit()

	xmlcontent = xmlfh.read()
	xmlcontent = xmlcontent.encode('UTF-8')

	if type_import == 'test': continue
		
	response = requests.post(private[type_import]['url'], headers = head, data = xmlcontent, auth=(private[type_import]['login'], private[type_import]['mdp']) )

	## verifier si le depot a eu lieu
	depotValide = True
	if response.status_code != 202 : 
		depotValide = False
	try : 
		root = ET.fromstring(response.text)
		linkelem = root.find("{http://www.w3.org/2005/Atom}link")
	except : 
		depotValide = False

	if not depotValide : 
		print( f"\terreur lors du dépot voir fichier")
		out_error.write(f"\n\n{row['eid']}\n")
		causeElem = root.find("{http://purl.org/net/sword/error/}verboseDescription")
		if causeElem.text : out_error.write(causeElem.text)
		else  : out_error.write(causeElem.text)
		continue
			
	## if it is valid retrieve data to populate csv
	addRow.insert(0,'new')
	addRow.insert(2, linkelem.attrib['href'] )
	print("\tnew")
	writer.writerow(addRow)
	xmlfh.close()

doc_a_traiter.close()
doc_imported.close()
out_error.close()
