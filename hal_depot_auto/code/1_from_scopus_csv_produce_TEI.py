from functions import *
import produceTei, json

'''
1. extract data from scopus :  AF-ID ( 60029937 ) 
	PUBDATETXT(July 2004) or loaddate(2 0200701) or  AND  RECENT ( 8 ) 

2a. run code w step = verifData
2b. run code w step = verifAuth

3. verify "affil_analysed.txt" & update "uvsq_valid_auth" w dedicated code

4. run code w step = produceTei

Maxence Larrieu 
2021 01
'''

#____________________________________________________________

step = 'produceTei' #verifData, verifAuth, produceTei
rowRange=[0,10]

#____________________________________________________________



#__________ Import data
#bibli = loadBibliography('../source/2020-12-scopus.csv')
bibli = loadBibliography('../source/scopus.csv')
load_tables_and_create_outputs()
labData = loadLabCriteria()



#____0____ verif  data completude
if step == 'verifData' : 
	for i, doc in enumerate(bibli) : 
		print(doc['EID'])
		auths = extractAuthors(doc['Authors'], doc['Author(s) ID'])
		affils = extractRawAffil(auths, doc['Authors with affiliations'])
	print(">>>>YES ! data is conform, go to 2nd step 'verifAuth' ")
	quit()

for i, doc in enumerate(bibli) :
	
	if i < min(rowRange) : continue
	elif i > max(rowRange) : break
	
	docId = { 'eid':doc['EID'] , 'scopusLink':doc['Link'] , 'doi':doc['DOI'] }
	print(f"\n{i}\n{docId['eid']}")


	# _____0_____
	# if doctype not include : continue
	docId['doctype'] = matchDocType(doc['Document Type'])
	if not docId['doctype'] :
		if step == 'verifAuth' : print(f"\ndoctype not include : {doc['Document Type']}")
		else : addRow(docId ,'not treated', 'doctype not include : '+doc['Document Type'])
		continue
	
	#verif if doc has already been treated by hal uvsq
	alreadyTreated = verifHalContributorId(docId['doi'])
	if alreadyTreated : 
		print(f"\talready in HAL and treated by you")
		continue
	
		
	#_____1_____ Extract & enrich Authors data

	# from scopus table extract name, initial, authId
	auths = extractAuthors(doc['Authors'], doc['Author(s) ID'])

	# from scopus table extract corresp auth email
	auths = extractCorrespEmail(auths, doc['Correspondence Address'])

	# from scopus table extract raw affil
	affils = extractRawAffil(auths, doc['Authors with affiliations'])
	
	# from raw affil deduce labname 
	auths = deduceAffil(docId['eid'], labData, auths, affils)
	
	#if it does not come from uvsq : continue
	if not auths :
		addRow(docId, 'not treated', 'lab not founded')
		continue
	
	# from uvsqAuthors enrich authors data
	auths = enrichWithValidUvsqAuth(auths)
	
	# if no forename retrieve data from scopus auhtors api (forename, orcid)
	auths = retrieveScopusAuths(auths)

	# for non uvsq auths, retrieve scopus search api (afid)
	auths = retrieveScopusAfid(docId['eid'], auths)

	
	if step == 'verifAuth' : 
		populateTempAuthDb(auths)
		continue

	#print(json.dumps(auths,indent=4))
	
	

	#_____2_____ REQ Hal
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

	'''
	if titleInHal[0] == 0:		
		authNtitle = reqWithAuthPlusTitle(auths, titles)
		if authNtitle[0] > 1 : 
			#print(authNtitle)
			buffHal['hal_match'] = "auth plus title match"
			buffHal['uris'] = authNtitle[1]
	'''
	
	#_____3_____ Construct TEI
	dataTei = produceTei.prepareData(doc, labData, auths, docId['doctype'])
	# print('domain is', dataTei['domain'])
	docTei = produceTei.produceTeiTree(doc, auths, dataTei, titles)
	exportTei(docId, buffHal, docTei)


finish(step)
