import requests
import xml.etree.ElementTree as ET



def prepareData(doc, labData, auths, docType):
	''' structure the data has expected by the TEI
	ISBN
	'''
	dataTei = {}
	dataTei['doctype'] = docType 

	#_______ extract funding data	
	dataTei['funders'] = []	
	if doc['Funding Details']: dataTei['funders'].append(doc['Funding Details'])
	temp = [doc['Funding Text '+str(i)] for i in range(1,10) if doc.get('Funding Text '+str(i))]
	dataTei['funders'].extend(temp)


	#_______ get hal journalId
	dataTei['journalId'] = dataTei['issn'] = dataTei['jtitle'] = False

	if doc['ISSN']:
		#si moins de 8 carac on rempli de 0
		zeroMissed = 8 - len(doc['ISSN'])
		issn = ("0"* zeroMissed + doc['ISSN']) if zeroMissed > 0 else doc['ISSN']
		issn = issn[0:4]+'-'+issn[4:]

		prefix = 'http://api.archives-ouvertes.fr/ref/journal/?'
		suffix = '&fl=docid,valid_s,label_s'
		req = prefix +'q=issn_s:'+issn+suffix
		req = requests.get(req)
		req = req.json()
		reqIssn = [req['response']['numFound'], req['response']['docs']]
		
		# if journals finded get the first journalId
		if reqIssn[0] > 0 : 
			dataTei['journalId'] = str(reqIssn[1][0]['docid'])

		## if no journal fouded
		if reqIssn[0] == 0 : 
			dataTei['issn'] = issn
			dataTei['jtitle'] = doc['Source title']


	#_______ find hal domain
	dataTei['domain'] = False
	# with journal issn
	if dataTei['journalId'] : 
		prefix = 'http://api.archives-ouvertes.fr/search/?rows=0'
		suffix = '&facet=true&facet.field=domainAllCode_s&facet.sort=count&facet.limit=2'
		req = prefix + '&q=journalId_i:'+dataTei['journalId']+suffix
		#print(req)
		req = requests.get(req)
		try:
			req = req.json() ## souvent cette req n'aboutit pas : pb de temps
			dataTei['domain'] = req['facet_counts']['facet_fields']['domainAllCode_s'][0]
		except : 
			print('\tHAL API not worked for retrieve domain with journal')
			pass
			
	# with domain of laboratory
	if not dataTei['domain'] : 
		for item in auths : 
			if not item['labname'] or item['labname'] == 'uvsq': continue
			dataTei['domain'] = labData[item['labname']]['halDomain_id']
			break
	
	if not dataTei['domain'] : 
		dataTei['domain'] = 'sdv'
		print('\t!! attention aucun domaine trouvé')


	#_______ Abstract
	abstract = doc['Abstract']
	dataTei['abstract'] = False if abstract.startswith('[No abstr') else abstract[: abstract.find('©')-1]
	
	return dataTei




# documentation HAL TEI : https://api.archives-ouvertes.fr/documents/all.xml
def produceTeiTree(doc, auths, dataTei, titles ) :
	
	tree = ET.parse('../source/ART.xml')
	root = tree.getroot()
	ET.register_namespace('',"http://www.tei-c.org/ns/1.0")
	ns = {'tei':'http://www.tei-c.org/ns/1.0'}
	biblFullPath = 'tei:text/tei:body/tei:listBibl/tei:biblFull'


	#___CHANGE titlesStmt : suppr and add funder	
	#clear titlesStmt elements ( boz redundant info)
	eTitleStmt = root.find(biblFullPath+'/tei:titleStmt', ns)
	eTitleStmt.clear()

	# if applicable add funders	
	if len(dataTei['funders']) > 0 : 
		for fund in dataTei['funders']: 
			eFunder = ET.SubElement(eTitleStmt, 'funder')
			eFunder.text = fund.replace('\n', ' ').replace('\r', ' ')
			eFunder.tail='\n' + '\t'*6


	#___CHANGE editionStmt : suppr
	eBiblFull = root.find(biblFullPath, ns)
	eEdition = root.find(biblFullPath+'/tei:editionStmt', ns)
	eBiblFull.remove(eEdition)

	#___CHANGE seriesStmt
	eSeriesIdno = root.find(biblFullPath+'/tei:seriesStmt/tei:idno', ns)
	eSeriesIdno.set('n','UVSQ')

	#___CHANGE  sourceDesc / title
	eAnalytic = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic', ns)
	eTitle = root.find(biblFullPath+'/tei:sourceDesc/tei:biblStruct/tei:analytic/tei:title', ns)
	eAnalytic.remove(eTitle) 
			
	## todo faire un matching ac clé pays de Hal
	#https://api.archives-ouvertes.fr/search/?q=*%3A*&rows=0&wt=xml&indent=true&facet=true&facet.field=country_s
	##  Allemagne : 2-s2.0-85089348449
	# Si un seul titre et language doc = fr
	if len(titles[1]) < 2 and \
	doc['Language of Original Document'].startswith('Fren') :	
		eTitle = ET.Element('title', {'xml:lang':'fr'})
		eTitle.text = titles[0]
		eAnalytic.insert(0,eTitle )
	
	# Si un seul titre et language doc = en
	if len(titles[1]) < 2 and \
	doc['Language of Original Document'].startswith('Eng') :	
		eTitle = ET.Element('title', {'xml:lang':'en'})
		eTitle.text = titles[0]
		eAnalytic.insert(0,eTitle)

	# Si deux titres
	if len(titles[1]) > 2 : ##si deux titres, premier fr et 2nd en
		eTitle = ET.Element('title', {'xml:lang':'en'})
		eTitle.text = titles[0]
		eAnalytic.insert(0,eTitle)
		eTitle2 = ET.Element('title', {'xml:lang':'fr'})
		eTitle2.text = titles[1]
		eAnalytic.insert(1,eTitle2)

	#___CHANGE  sourceDesc / biblStruct / analytics / authors
	biblStructPath = biblFullPath+'/tei:sourceDesc/tei:biblStruct'
	author = root.find(biblStructPath+'/tei:analytic/tei:author', ns)
	eAnalytic.remove(author)

	for aut in auths : 
		role  = 'aut' if not aut['corresp'] else 'crp' #correspond ou non
		eAuth = ET.SubElement(eAnalytic, 'author', {'role':role}) 
		eAuth.tail='\n\n' + '\t'*7
		ePers = ET.SubElement(eAuth, 'persName')
		
		eForename = ET.SubElement(ePers, 'forename', {'type':"first"})
		if not aut['forename'] : eForename.text = aut['initial']
		else : eForename.text = aut['forename']

		eSurname = ET.SubElement(ePers, 'surname')
		eSurname.text = aut['surname']	
		
		#if applicable  add email 
		if aut['mail'] :
			eMail = ET.SubElement(eAuth, 'email')
			eMail.text = aut['mail'] 

		#if applicable add orcid
		if aut['orcid'] : 
			orcid = ET.SubElement(eAuth,'idno', {'type':'https://orcid.org/'})
			orcid.text = aut['orcid']			
		
		#if applicable add structId
		if aut['labname'] : 
			eAffiliation = ET.SubElement(eAuth, 'affiliation ')
			eAffiliation.set('ref', '#struct-'+str(aut['structId']))

		# if applicable add structId who has matched w scopu affid
		try : 
			aut['structIdFromScopus']
		except : pass
		else :
			eAffiliation = ET.SubElement(eAuth, 'affiliation ')
			eAffiliation.set('ref', '#struct-'+aut['structIdFromScopus'][0])
			
	
	## ADD SourceDesc / bibliStruct / monogr : isbn & title
	eMonogr = root.find(biblStructPath+'/tei:monogr', ns)
	index4meeting = 0
	## ne pas coller l'ISBN si c'est un doctype COMM
	if doc['ISBN'] and not dataTei['doctype'] == 'COMM': 
		
		eIsbn = ET.Element('idno', {'type':'isbn'})
		if ';' in doc['ISBN'] : 
			eIsbn.text = doc['ISBN'][:doc['ISBN'].index(';')] # on prend seulement le premier isbn
		else: 
			eIsbn.text = doc['ISBN']
		eMonogr.insert(0, eIsbn)

		eTitle = ET.Element('title', {'level':'m'})
		eTitle.text=doc['Source title']
		eMonogr.insert(1,eTitle)
		index4meeting+=2


	## ADD SourceDesc / bibliStruct / monogr : issn
	# if journal is in Hal
	if dataTei['journalId'] :
		eHalJid = ET.Element('idno', {'type':'halJournalId'})
		eHalJid.text = dataTei['journalId']
		eHalJid.tail = '\n'+'\t'*8
		eMonogr.insert(0,eHalJid)
		index4meeting+=1

	if not dataTei['journalId'] :
		eIdIssn = ET.Element('idno', {'type':'issn'})
		eIdIssn.text = dataTei['issn']
		eIdIssn.tail = '\n'+'\t'*8
		eMonogr.insert(0,eIdIssn)

		eTitleJ = ET.Element('title', {'level':'j'})
		eTitleJ.text = dataTei['jtitle']
		eTitleJ.tail = '\n'+'\t'*8
		eMonogr.insert(1,eTitleJ)
		index4meeting+=2

	
	## ADD SourceDesc / bibliStruct / monogr / meeting : meeting
	if dataTei['doctype'] == 'COMM' : 
		#conf title
		eMeeting = ET.Element('meeting')
		eMonogr.insert(index4meeting,eMeeting)
		eTitle = ET.SubElement(eMeeting, 'title')
		eTitle.text = doc['Conference name'] if doc['Conference name'] else 'unknow'
				
		#meeting date
		eDate = ET.SubElement(eMeeting, 'date', {'type':'start'}) 
		eDate.text = doc['Conference date'][-4:] if doc['Conference date'] else doc['Year']
				
		#settlement
		eSettlement = ET.SubElement(eMeeting, 'settlement')
		eSettlement.text = doc['Conference location'] if doc['Conference location'] else 'unknow'

		#country
		eSettlement = ET.SubElement(eMeeting, 'country',{'key':'fr'})

	
	#___ ADD SourceDesc / bibliStruct / monogr : Editor
	if doc['Editors'] : 
		eEditor = ET.Element('editor')
		eEditor.text = doc['Editors']
		eMonogr.insert(index4meeting+1,eEditor)
		


	#___ CHANGE  sourceDesc / monogr / imprint :  vol, issue, page, pubyear, publisher
	eImprint = root.find(biblStructPath+'/tei:monogr/tei:imprint', ns)
	for e in list(eImprint):
		if e.get('unit') == 'issue' : e.text = doc['Issue']
		if e.get('unit') == 'volume' : e.text = doc['Volume']
		if e.get('unit') == 'pp' : 
			if doc['Page start'] and doc['Page end'] :
				e.text = doc['Page start']+ "-"+doc['Page end']
			else : 
				e.text = ""
		if e.tag.endswith('date') : e.text = doc['Year']
		if e.tag.endswith('publisher') : e.text = doc['Publisher']


	#_____ADD  sourceDesc / biblStruct : DOI & Pubmed
	eBiblStruct = root.find(biblStructPath, ns)
	if doc['DOI'] : 
		eDoi = ET.SubElement(eBiblStruct, 'idno', {'type':'doi'} )
		eDoi.text = doc['DOI']

	if doc['PubMed ID'] : 
		ePubmed = ET.SubElement(eBiblStruct, 'idno', {'type':'pubmed'} )
		ePubmed.text = doc['PubMed ID']


	#___CHANGE  profileDesc / langUsage / language
	eLanguage = root.find(biblFullPath+'/tei:profileDesc/tei:langUsage/tei:language', ns)
	eLanguage.attrib['ident']=doc['Language of Original Document'][:2].lower()


	#___CHANGE  profileDesc / textClass / keywords/ term
	eTerm = root.find(biblFullPath+'/tei:profileDesc/tei:textClass/tei:keywords/tei:term', ns)
	eTerm.text = doc['Author Keywords']


	#___CHANGE  profileDesc / textClass / classCode : hal domaine & hal doctype
	eTextClass = root.find(biblFullPath+'/tei:profileDesc/tei:textClass', ns)
	for e in list(eTextClass):
		if e.tag.endswith('classCode') : 
			if e.attrib['scheme'] == 'halDomain': e.attrib['n'] = dataTei['domain']
			if e.attrib['scheme'] == 'halTypology': e.attrib['n'] = dataTei['doctype']


	#___CHANGE  profileDesc / abstract 
	eAbstract = root.find(biblFullPath+'/tei:profileDesc/tei:abstract', ns)
	eAbstract.text = dataTei['abstract']

	return tree
