import csv, requests, json, re, os, io
import xml.etree.ElementTree as ET
#from fuzzywuzzy import fuzz


#def addRow(eid, doi, state, treat_info='', hal_match='', uris=''):
def addRow(docId, state, treat_info='', hal_match='', uris=''):

	print(f"\tadded to csv\n\t{state}")
	if docId["doctype"] : 
		print(f"\t{docId['doctype']}")

	if "not include" not in treat_info and docId['doi'] : 
		print(f"\t{docId['doi']}") 

	if treat_info : 
		print(f"\t{treat_info}")
	if hal_match : 
		print(f"\t{hal_match}")
	if uris : 
		print(f"\t{','.join(uris)}")

	writeDoc.writerow([docId['eid'], docId['doi'], docId['doctype'],
	state, treat_info, hal_match, ','.join(uris)])


#______0_____ INIT
def loadTables_and_createOutpus():

	# load local data : path and personal data
	global local_data
	with open("./data/stable/path_and_perso_data.json") as fh : 
		local_data = json.load(fh)

	
	global apikey, insttoken
	apikey = local_data.get("perso_scopusApikey")
	insttoken = local_data.get("perso_scopusInstToken")
	print("scopus api key loaded") if apikey else print("no scopus key loaded")

		
	# load valid authors db
	global validUvsqAuth # a dictionnary with "NAME F."" as key for authors
	with open(local_data["path_validAuthDb"], 'r', encoding="utf-8") as auth_fh:
		reader = csv.DictReader(auth_fh)
		validUvsqAuth = {row['key']: row for row in reader}

	# create temporary authors database
	global temp_uvsqAuth
	temp_uvsqAuth = []

	# csv output for biblio analysed
	global docs_table
	docs_table = open('./data/doc_analysed.csv', 'w', newline='', encoding="utf8")
	global writeDoc
	writeDoc = csv.writer(docs_table, delimiter =',')
	writeDoc.writerow(['eid', 'doi', 'doctype', 'state', 'treat_info', 'hal_match', 'halUris'])

	# txt output for affiliation and deduction made
	global affil_txt
	affil_txt = io.open('./data/affil_analysed.txt', 'w', encoding='utf-8')


def loadLabData_and_afid2structId():
	t = open(local_data["path_labCriteria"], newline='', encoding='utf8')
	reader = csv.DictReader(t)
	labData = {row['sigle'].strip() : row.copy() for row in reader}
	
	global afid2structId
	afid2structId = {row["scopus_struct_id"] : row["hal_id"] for k, row in labData.items()}
	# add univ scopus id and hal univ structId
	afid2structId[ str(local_data["univ_scopusId"]) ] = str(local_data["univ_halStructId"])

	return labData



def loadBibliography(path):
	t = open(path, newline='', encoding='utf-8-sig')
	return csv.DictReader(t)



#______1_____ ENRICH & STRUCTURE AUTHORS DATA

def matchDocType(doctype):
	doctype_scopus2hal = {'Article': 'ART', 'Article in Press' : 'ART', 'Review':'ART', 'Business Article':'ART', "Data Paper":"ART", 'Conference Paper':'COMM',\
'Conference Review':'COMM', 'Book':'OUV', 'Book Chapter':'COUV'}
	
	if doctype in doctype_scopus2hal.keys() :
		return doctype_scopus2hal[doctype]
	else :
		return False

def reqHal(field, value = ""):
	prefix= 'https://api.archives-ouvertes.fr/search/?' #halId_s
	suffix = "&fl=uri_s,title_s&wt=json"
	req = prefix + '&q='+ field + value+ suffix
	found = False
	while not found : 
		req = requests.get(req)
		try : 
			fromHal = req.json()
			found = True
		except : 
			pass
	
	num = fromHal['response'].get('numFound')
	docs = fromHal['response'].get('docs', [])
	return [num, docs]


def verifHalContributorId(doi):
	finded = False
	if doi : 
		reqId = reqHal('doiId_id:', doi+"&fl=contributorId_i" )
		for item in reqId[1]:
			if item['contributorId_i'] == local_data["perso_hal_contributorId"] : 
				finded = True
				break
	return finded


def extractAuthors(authors, authId):
	''' from table Extract surname and initial foremane and authid
	ex de liste de nom : 
	Taher Y., Haque R., AlShaer M., v. d. Heuvel W.J., Zeitouni K., Araujo R., Hacid M.-S., 
	il peut mm avoir des des virgules pour le nom d'un auteur doi.org/10.1002/rcm.8244
	'''
	## CODE PROBLEM WITH this data :   Scott R.T., Jr., de Ziegler D. : PRODUCE ERROR boz it sees 3 auths

	authors_cut = authors.split(',')
	authId_cut = authId[:-1].split(';')
	if not len(authors_cut) == len(authId_cut) : 
		print("pb : nb auth et nb authId ne correspondent pas ")
		quit()
	
	auths = []
	for auth_idx, auth in enumerate(authors_cut):
		
		if '.' not in auth : #escape les groupements d'auteur
			print(f"\tauteur échappé\t{auth}")
			continue
		
		auth = auth.strip() # le Nom P.
		elem = auth.split() 
		#le surname est le dernier élément qui ne finit pas par un point
		for i in reversed(range( len(elem))) : 
			if not elem[i].endswith('.'):
				idx = auth.index(elem[i]) + len(elem[i])
				surname = auth[: idx]
				initial = auth[idx:].strip()
				#print(surname,'\t', intial )
				break
				
		if len(surname) == 0 or len(initial) < 1 : 
			print('!! pb id name \t',auth)
			quit()			
		
		auths.append(
			{'surname': surname, 
			'initial':initial, 
			'forename':False,
			'scopusId':authId_cut[auth_idx],
			'orcid':False,
			'mail':False, 
			'corresp':False
			})
		
	return auths


def extractCorrespEmail(auths, corresp):
	for i in range(len(auths)) : 
		if corresp.startswith(auths[i]['surname']) and 'email' in corresp :
			mail = corresp[corresp.find('mail') + len('mail: '):].strip()
			auths[i]['mail'] = mail
			auths[i]['corresp'] = True
			break
	return auths


def extractRawAffil(auths, rawAffils):	
	'''extract raw affil from scopus table'''
	#il faut partir du début, aller jusqu'au 2e nom, et cela délimite la 1er affil
	
	nbAuth = len(auths)
	affils = []
	i = 1
	while i <= nbAuth :
		preFullName = auths[i-1]['surname']+", "+auths[i-1]['initial']

		if i == nbAuth :
			aff = rawAffils[ rawAffils.index(preFullName) : ]    
		else :
			postFullName = auths[i]['surname']+", "+auths[i]['initial']
			aff = rawAffils[ rawAffils.index(preFullName) : rawAffils.index(postFullName)]

		#exclude name in affil
		nameLen = len(preFullName+', ')
		affils.append(aff[nameLen: ])
		i+=1       

	if len(auths) != len(affils) : 
		print('\n!!!!!!! nb of auths not match nb of affils')
		quit()
	
	#for i in range(0, len(auths)): print(i,"|",
	# 	auths[i]['surname'],"|",
	# 	auths[i]['initial'],"|",
	# 	affils[i])

	return affils


def searchFormeLg(data, fromcsv):
	"""utilisé dans deduceAffil """	
	cut = fromcsv.split(',')
	regtotal = len(cut)
	regcount = 0
	for i in cut:
		i = i.strip()
		if re.search(i, data): regcount +=1
	
	return 1 if regcount == regtotal else 0
	
		
def deduceAffil(eid, labData, auths, affils):
	"""deduce affiliation with labData"""
	# algorithme on part de l'affiliation brute et on trouve le labo correspondant
	
	findedAff = {}
	tutelle = ['uvsq', 'versaill', 'saclay']
	docFromUvsq = False
	for i in range(len(affils)):
		aff = affils[i].casefold()
		afffinded = False
		
		for lab in labData : 
			sigle = code = lablg = tutelles = 0
			
			#___1. search for lab element		
			if lab in aff : sigle = 1			
			if labData[lab]['code1'] in aff and labData[lab]['code2'] in aff : code = 1			
			lablg = searchFormeLg(aff, labData[lab]['regexp'])
		

			#___2. search for tutelle element
			for tut in tutelle : 
				if tut in aff : tutelles = 1

			if labData[lab]['tutelle suppl'] :
				ext_tutelles = labData[lab]['tutelle suppl'].split(',')			
				for tut in ext_tutelles : 
					if tut.strip().lower() in aff : 
						tutelles = 1


			#__3. if lab element & tutelle element 
			if sigle + code + lablg > 0 and tutelles > 0 : 
				auths[i]['labname'] = lab
				afffinded = docFromUvsq =  True
				if not aff in findedAff : 
					findedAff[aff] = lab
				break

					
		#if nothing finded at lab level search at univ level
		if not afffinded :
			if 'uvsq' in aff or ('univ' in aff and 'versaill' in aff) : 
				auths[i]["labname"] = 'uvsq'
				docFromUvsq = True
			else :
				auths[i]["labname"] = False


	if not docFromUvsq : return False
	else : 
		# export to txt file
		affil_txt.write('\n\n'+eid+'\n')
		{affil_txt.write(f"{k}\n{v}\n\n") for k, v in findedAff.items()}
		

		#add hal structId to authors
		for item in auths : 
			if not item['labname']: continue
			if item['labname'] == 'uvsq' : item['structId'] = 81173
			else :
				item['structId'] = labData[item['labname']]['hal_id']			
		return auths
		


def enrichWithValidUvsqAuth(auths):
	""" complete auth data w local file 'validUvsqAuth' """

	for item in auths:
		if not item['labname'] : continue # si aut pas uvsq go next
		key = item['surname']+' '+item['initial'] 
		if key in validUvsqAuth : 
			fields = ['forename', 'orcid'] ##on ne prend pas le mail enregistré sur notre base local
			# if nothing from scopus but present in local db then add value
			for f in fields : 
				# if nothing is present then we enrich w uvsq auth db
				if not item[f] : item[f] = validUvsqAuth[key][f]
	return auths


def reqScopus(suffix):
	prefix = "https://api.elsevier.com/content/"	
	req = requests.get(prefix+suffix, 
		headers={'Accept':'application/json',
		'X-ELS-APIKey':apikey,
		'X-ELS-Insttoken':insttoken	
		})	
	req = req.json()
	if req.get("service-error") : 
		print(f"\n\n!!probleme API scopus : \n\n{req}")
		quit()
	return req


def retrieveScopusAuths(auths):
	if not apikey : 
		return auths
	""" from scopus get forename and orcid
	memo : si on pousse un orcid qui est attaché à un idHAL alors l'idHAL s'ajoute automatiquement """
	
	
	for item in auths :

		if item["forename"] and item["orcid"] : 
			continue
		
		req = reqScopus('author?author_id='+ item['scopusId']+'&field=surname,given-name,orcid')
		try : 
			# a faire evoluer pour intégrer les alias eg 57216794169
			req = req['author-retrieval-response'][0]
		except : 
			pass

		#get forname
		if not item["forename"] and req.get("preferred-name"): 
			item["forename"] = req["preferred-name"].get('given-name')
		
		#get orcid 
		if not item["orcid"] and req.get("coredata") : 
			item['orcid'] = req['coredata'].get("orcid")

	return auths


def retrieveScopusAfid(eid, auths):
	"""from scopus API retrieve structure identifant"""
	if not apikey : 
		return auths
	
	req = reqScopus(f"search/scopus?query=eid({eid})&field=author,affiliation")
	req = req['search-results']['entry'][0]['author']
	#if aut has no labname search for afid
	i = 0
	while i < len(auths):				
		if not auths[i]['labname'] :
			for item in req : 
				if auths[i]['surname'] == item['surname'] : 
					try : item['afid']
					except : pass
					else : 
						tempaffid = []
						for afid in item['afid']:
							if afid['$'] in afid2structId: 
								tempaffid.append(
								afid2structId[afid['$']]
								)
						if tempaffid : 
							auths[i]['structIdFromScopus'] = tempaffid
							
		i+=1
	return auths


def populateTempAuthDb(auths) : 
	"""populate a local temporary author database"""
	
	for item in auths :
		if not item['labname'] : continue
		existAlready = False
		for vauth in temp_uvsqAuth : 
			if item['surname'] == vauth['surname'] and item['initial'] == vauth['initial']: 
				
				existAlready = True
				if item['orcid'] : vauth['orcid'] = item['orcid']
				if item['mail'] : vauth['mail']  = item['mail']
		

		if not existAlready : 
			temp_uvsqAuth.append(item)



#______2_____ REQ HAL

def getTitles(inScopus):
	"""extract titles from scopus table"""
	cutTitle = inScopus.split('[')
	if len(cutTitle) > 1:
		cutindex = inScopus.index('[')
		titleOne = inScopus[0: cutindex].rstrip()
		titleTwo = inScopus[cutindex+1: -1].rstrip()
	else:
		titleOne = inScopus
		titleTwo = ""
	return [titleOne, titleTwo]


def reqWithIds(doi, pubmedId):
	"""recherche dans HAL si le DOI ou PUBMEDID est déjà présent """
	
	idInHal = [0,[]] #nb of item, list of uris
	
	if doi:
		reqId = reqHal('doiId_id:', doi )
		idInHal[0] = reqId[0]	
		for i in reqId[1] : 
			idInHal[1].append(i['uri_s'])
	
	if pubmedId : 
		reqId = reqHal('pubmedId_id', pubmedId)
		idInHal[0] += reqId[0]
		for i in reqId[1] : 
			idInHal[1].append(i['uri_s'])

	return idInHal


def reqWithTitle(titles):
	"""recherche dans HAL si une notice avec le mm titre existe """
	
	titleInHal = [0,[]] 

	reqTitle = reqHal('title_t:\"', titles[0]+ '\"')
	for i in reqTitle[1] : 
			titleInHal[1].append(i['uri_s'])
	
	#test avec le 2nd titre
	if len(titles[1]) > 3: 
		reqTitle_bis = reqHal('title_t:\"', titles[1]+ '\"')
		reqTitle[0] += reqTitle_bis[0]
		
		for i in reqTitle_bis[1] : 
			titleInHal[1].append(i['uri_s'])
		
	titleInHal[0] = reqTitle[0] 
	return titleInHal


def reqWithAuthPlusTitle(auths, titles):
	"""recherche dans HAL si une publication avec les mm auteurs existe
	si oui verifier la proxemie entre les titres"""
	
	#a list of authors
	nameList = []
	for item in auths : nameList.append(item['surname'])

	authNtitleInHal = [0,[]] 
	reqAuth = reqHal('authLastName_t:',' AND '.join(nameList))

	if reqAuth[0]>0 : #if some docs check similarity w titles
		for item in reqAuth[1] :
			halTitle = item['title_s'][0]
			for t in titles : 
				ratio = fuzz.ratio(t, halTitle)
				 # threshold for similarity
				if ratio > 70:
					authNtitleInHal[0] += 1
					authNtitleInHal[1].append(item['uri_s'])

	return authNtitleInHal


#______3_____ Produce TEI HAL

def exportTei(docId, buffHal, docTei) : 
	tree = docTei 
	root = tree.getroot()
	ET.register_namespace('',"http://www.tei-c.org/ns/1.0")
	ns = {'tei':'http://www.tei-c.org/ns/1.0'}
	root.attrib["xmlns:hal"] = "http://hal.archives-ouvertes.fr/"
	
	tree.write('./data/TEI/'+docId['eid']+".xml",
	xml_declaration=True,
	encoding="utf-8", 
	short_empty_elements=False)

	if buffHal : 
		state = "already in hal and TEI generated"
		addRow(docId, state, '', buffHal['hal_match'], buffHal['uris'] )
	else : 
		addRow(docId, "TEI generated")
	
def finish(step): 	
	if step == "verif_auth" : 
		##produce auth table
		fnames = ['key', 'surname', 'forename', 'initial', 'labname', 'orcid', 'mail', 'scopusId']
		with open('./data/temp_uvsq_authors.csv', 'w', newline='', encoding='utf8') as fh :
			writeAuthor = csv.writer(fh)
			writeAuthor.writerow(fnames)
			for auth in temp_uvsqAuth : 
				orcid = auth['orcid'] if auth['orcid'] else ''
				mail = auth['mail'] if auth['mail'] else ''
				row = [auth['surname']+' '+auth['initial'], auth['surname'], auth['forename'], auth['initial'], auth['labname'], orcid, mail, auth['scopusId'] ]
				writeAuthor.writerow(row)

	docs_table.close()
	affil_txt.close()
	quit()
