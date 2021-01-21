import pandas as pd
import json, csv

"""
# but
crééer et mettre à jour une base données regroupant tous les auteurs affiliés à l'établissement.
nom du fichier de la base de donnée "valid_uvsq_authors.csv" (vAuthDb par la suite)

# Processus
	charge la table "../out/temp_uvsq_authors.csv"
	verifie si des auteurs de cette table sont déjà présent (par scopusId et orcid) dans la table vAuthDb
	si oui, compléter avec les éventuelles lacunes de vAuthDb
	si non, ajouter ces auteurs à la vAuthDb
	si il y a une correspondance avec la clé NOM P. alors retour consol demandant une vérification manuelle



ML 2021-01-13
"""


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
with open("../../path_and_perso_data.json") as fh : 
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
with open('../out/temp_uvsq_authors.csv', 'r', encoding='utf8') as fh : 
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

