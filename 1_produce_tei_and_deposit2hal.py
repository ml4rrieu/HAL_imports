"""
memo extraction scopus
	AF-ID ( 60029937 )  PUBDATETXT(July 2004) or loaddate(2 0200701) or  AND  RECENT ( 8 ) 

instructions
	https://github.com/ml4rrieu/HAL_imports
"""



#____________________________________________________________
# Nom de l'étape à lancer
# verif_data, verif_auth, update_auth_db, produce_tei, tei2preprod, tei2hal
step = "verif_data"  

# Nom du fichier extrait de scopus (a placer dans ./data/scopus_biblio/)
scopus_filename = "test.csv" #2020-12-scopus.csv


rowRange=[0,10000] # pour debug uniquement : intervalle de lignes à traiter
#____________________________________________________________



import sys, os, json, csv
sys.path.append(os.path.abspath("./py_functions"))
from functions import *
import produceTei


if step == "verif_data" : 
	
	publication_list = loadBibliography('./data/scopus_biblio/'+scopus_filename)
	for doc in publication_list : 
		print(doc['EID'])
		auths = extractAuthors(doc['Authors'], doc['Author(s) ID'])
		affils = extractRawAffil(auths, doc['Authors with affiliations'])
	print("\n\n>>>> les donnees sont conformes : passez a l etape verif_auth")
	quit()



if step == "verif_auth" or step == "produce_tei": 
	
	loadTables_and_createOutpus()
	labData = loadLabData_and_afid2structId()
	publication_list = loadBibliography('./data/scopus_biblio/'+scopus_filename)
	
	for i, doc in enumerate(publication_list) :
		if i < min(rowRange) : continue
		elif i > max(rowRange) : break
	
		docId = { 'eid':doc['EID'] , 'scopusLink':doc['Link'] , 'doi':doc['DOI'] }
		print(f"\n{i}\n{docId['eid']}")

		# _____1_____
		# if doctype not include : continue
		docId['doctype'] = matchDocType(doc['Document Type'])
		if not docId['doctype'] :
			if step == 'verifAuth' : print(f"\ndoctype not include : {doc['Document Type']}")
			else : addRow(docId ,'not treated', 'doctype not include : '+doc['Document Type'])
			continue
		
		# verify if you did not already treat this publication (hal contributorId_i)
		alreadyTreated = verifHalContributorId(docId['doi'])
		if alreadyTreated : 
			print(f"\talready in HAL and treated by you")
			continue
			
		#_____2_____ Extract & enrich authors data

		# from scopus table extract name, initial, authId
		auths = extractAuthors(doc['Authors'], doc['Author(s) ID'])

		# from scopus table extract corresp auth email
		auths = extractCorrespEmail(auths, doc['Correspondence Address'])

		# from scopus table extract raw affil
		affils = extractRawAffil(auths, doc['Authors with affiliations'])
		
		# from raw affil deduce labname 
		auths = deduceAffil(docId['eid'], labData, auths, affils)
		
		#if not auth is affiliated to your research units continue
		if not auths :
			addRow(docId, 'not treated', 'lab not founded')
			continue
		
		# from uvsqAuthors enrich authors data
		auths = enrichWithValidUvsqAuth(auths)
		
		# from scopus auhtors api retrieve forename, orcid
		auths = retrieveScopusAuths(auths)

		# for non uvsq auths, retrieve scopus search api (afid)
		auths = retrieveScopusAfid(docId['eid'], auths)
		
		if step == 'verif_auth' : 
			populateTempAuthDb(auths)
			continue

		if step == 'produce_tei' : 
			buffHal = {}
			titles = getTitles(doc['Title'])
	
			idInHal = reqWithIds(doc['DOI'], doc['PubMed ID'])
			if idInHal[0] > 0 :  
				addRow(docId, 'already in hal','', 'ids match',idInHal[1] )
				i+=1
				continue	

			titleInHal = reqWithTitle(titles)
			if titleInHal[0] > 0:
				#print(eid + '\n' + str(titleInHal))
				buffHal['hal_match'] = "titles match"
				buffHal['uris'] = titleInHal[1]

			#_____2d_____ Produce TEI
			dataTei = produceTei.prepareData(doc, labData, auths, docId['doctype'])
			docTei = produceTei.produceTeiTree(doc, auths, dataTei, titles)
			exportTei(docId, buffHal, docTei)

	finish(step)
	
	if step == 'verif_aut' : 
		print("\n\n>>>> les donnes auteurs ont ete recuperees : passez a l etape update_auth_db")
	if step == 'produce_tei' : 
		print("\n\n>>>> fichiers TEI produits : passez a l etape tei_to_hal")
	quit()



if step == "update_auth_db" : 
	import pandas as pd

	def getIndex(key, val, **val2changes):
		matched = []
		for i, row in enumerate(vAuthDb) :
			if row[key] == val : 
				matched.append(i)
		if not matched : 
			return False
		if len(matched) == 1 : 
			return matched[0]
		elif len(matched) >1 : 
			print(f"\nPlease verify : two {val} has been founded in valid auth db")


	##____0____load validAuthDb and load scopusId, authkeys and orcid as arrays
	with open("./data/stable/path_and_perso_data.json") as fh : 
		local_data = json.load(fh)
	
	# memo fields fields = ['key', 'surname', 'forename','initial', 'labname', 'orcid','mail', 'scopusId']
	vAuthDb, keys, scopusIds, orcids = [],  [],  [], []

	with open(local_data["path_validAuthDb"], 'r', encoding='utf8') as fh : 
		reader = csv.DictReader(fh)

		[vAuthDb.append(r) for r in reader]
		fh.seek(0) #rewind reader
		[scopusIds.append(row['scopusId'].strip() ) for row in reader if len(row['scopusId'])>3]
		fh.seek(0)
		[orcids.append(row['orcid'].strip()) for row in reader if row['orcid'] ]
		fh.seek(0)
		[keys.append(row['key'].strip() ) for row in reader]	
		
	print('taille de validAuthDb avant', len(vAuthDb))	


	##____1____for each lines in temp_uvsq_authors if auth already inside update vals else add aut to db
	with open('./data/temp_uvsq_authors.csv', 'r', encoding='utf8') as fh : 
		reader = csv.DictReader(fh)
		#[print(row) for i, row in enumerate(reader) if i < 5]
		for row_temp in reader : 
			row = {k: v for k, v in row_temp.items() if v !="False" } #remove key if value is False
				
			# si scopusId correspondent
			if row.get('scopusId') in scopusIds : 
				idx = getIndex('scopusId', row['scopusId'])
				if idx : 
					if row.get('orcid') : vAuthDb[idx]['orcid'] = row['orcid']				
					if row.get('mail') : vAuthDb[idx]['mail'] = row['mail']
					#print(f"\n{row['surname']} has been enrich")				

			# sinon si les orcids correspondent
			elif row.get('orcid') in orcids : 
				idx = getIndex('orcid', row['orcid'])
				if idx and row.get('mail') : 
					vAuthDb[idx]['mail'] = row['mail']
				
			# sinon si la clé, Nom  P. correspond
			elif row['key'] in keys : 
				print(f"\nNom p. déjà présent veuillez verifier")
				{print(k,"\t",v) for k, v in row.items() if v}
				#f = ['surname', 'forename','labname', 'orcid', 'mail','scopusId']
				#[print(row[k]) for k in f if row[k]]

			else : 
				vAuthDb.append(row)
				

	print('\n\ntaille de validAuthDb arpès', len(vAuthDb))	
	out = pd.DataFrame.from_dict(vAuthDb)
	out.fillna("", inplace = True) #retirer les valeurs False par des champs vides
	out.to_csv(local_data["path_validAuthDb"], index =False)



if step == "tei2preprod" or step == "tei2hal" : 

	import requests
	import xml.etree.ElementTree as ET

	type_import = "preprod" if step == "tei2preprod" else "hal"
	print(f"depots dans {type_import}")

	with open("./data/stable/path_and_perso_data.json") as fh : 
		local_data = json.load(fh)

	## identifiants perso pour depot via SWORD
	head = {
		'Packaging': 'http://purl.org/net/sword-types/AOfr',
	   	'Content-Type': 'text/xml',
	   	'X-Allow-Completion' : None
		}

	private = {
		'preprod':{
		'url':'https://api-preprod.archives-ouvertes.fr/sword/hal',
		'login': local_data["perso_login_halPreprod"], 
		'mdp': local_data["perso_mdp_halPreprod"]
		},
		'hal':{
		'url':'https://api.archives-ouvertes.fr/sword/hal',
		'login':local_data["perso_login_hal"],
		'mdp':local_data["perso_mdp_hal"],
		}
	}

	def reqUnpaywall(doi):
		"""search of repository  in oa_location, if not search for publisher"""
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

	#___0___load and create tables
	# charger le fichier listant toutes les publications
	doc_a_traiter = open("./data/doc_analysed.csv", 'r', encoding='utf8')
	reader = csv.DictReader(doc_a_traiter)
	
	# output table to list all publications that have been treated
	doc_imported = open('./data/doc_imported.csv', 'w', newline='', encoding='utf8')
	writer = csv.writer(doc_imported)
	writer.writerow(['state', 'doc type', 'lien hal', 'open access'])

	out_error = open('./data/erreur_depot_hal.txt', 'w', encoding='utf-8') # fichier txt pour capturer les erreurs sword

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
			xmlfh = open('./data/TEI/'+row['eid']+'.xml', 'r', encoding='utf-8')
		except : 
			print("\t/!\\ fichier TEI introuvable")
			quit()

		xmlcontent = xmlfh.read()
		xmlcontent = xmlcontent.encode('UTF-8')
	
		response = requests.post(private[type_import]['url'], headers = head, data = xmlcontent, auth=(private[type_import]['login'], private[type_import]['mdp']) )

		## verif if deposit is ok
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
				
		## if depot is valid get hal uri_s to populate csv
		addRow.insert(0,'new')
		addRow.insert(2, linkelem.attrib['href'] )
		print("\tnew")
		writer.writerow(addRow)
		xmlfh.close()

	doc_a_traiter.close()
	out_error.close()
	doc_imported.close()
	