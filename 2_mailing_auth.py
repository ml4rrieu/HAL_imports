"""
voir instructions : https://github.com/ml4rrieu/HAL_imports

Colonnes devant être présente dans le csv en entrée
	doc_type, open_access, emails, ok_?

la colonne 'emails', pour les articles sans accès ouvert, ne doit pas être lassée vide : indiquer 'pass' si vous ne souhaitez pas envoyer d'email
"""


#____________________________________________________________

liste_publi_ac_email = "doc_imported.csv" # le fichier doit être présent dans ./data/

# 'test' pour tester avec son mail perso
# 'envoi' pour traiter tous les documents et envoyer les emails aux auteurs
step = "envoi" 

#____________________________________________________________

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict
from string import Template 
import smtplib, json, csv, requests
import pandas as pd


def read_template(filename):
    with open(filename, 'r', encoding='utf-8') as template_file:
        template_file_content = template_file.read()
    return Template(template_file_content)


def reqHal(halId):
	base = "https://api.archives-ouvertes.fr/search/?q=halId_s:"
	req = requests.get(base+halId+"&fl=title_s")
	req = req.json()
	try : 
		return req['response']['docs'][0]['title_s'][0]
	except : 
		print(f"\n\n\nerror API HAL\n{halId}\n{base}+{halId}")
		quit()


with open("./data/stable/path_and_perso_data.json") as fh : 
	local_data = json.load(fh)

# ____ load publis liste to be treated
data = pd.read_csv("./data/"+liste_publi_ac_email)
sel_publications = data.loc[(data["doc_type"] =='ART') &\
(data['open_access'].isin(['closed','open from publisher : no licence'])) &\
(data['emails'] !='pass') &
(data['ok_?']) ]

# ____ configure SMTP server
s = smtplib.SMTP_SSL(host='smtps.uvsq.fr', port=465)
s.login(local_data["perso_login_server"], local_data["perso_pwd_server"])

#______ un csv pour s'assurer que les emails ont bien été envoyés
fh_stats_envoi = open("./data/stats_envoi_emails.csv", 'w', encoding='utf8', newline='')
out = csv.writer(fh_stats_envoi)

# ____ construct dict {email : [uris]}
# email comme clé de dictionnaire
mailNuris = defaultdict(list)
{r['mail correspondant']:mailNuris[r['mail correspondant']].append(r['lien hal']) for i,r in sel_publications.iterrows()}
print(f"nb auteur a contacter : {len(mailNuris)}")
#print(json.dumps(mailNuris))

for mail, uris in mailNuris.items():
	#if len(uris) == 1 : continue

	title = ['- '+reqHal(link[link.find('/',8)+1:]) for link in uris]
	title_and_link = [j for i in zip(title, uris) for j in i]
	title_and_link = "\n".join(title_and_link)
		
	# ____ load message template
	message_template = (read_template("./data/stable/message.txt") if len(title) == 1 else read_template("./data/stable/message_pluriel.txt"))
	
	# ____ create message
	msg = MIMEMultipart()
	message = message_template.substitute(TITLE = title_and_link )

	msg['From']= local_data["perso_email"]
	
	if step == "test" : 
		msg['To'] = local_data["perso_email"]
	
	elif step == "envoi" : 
		msg['To'] = mail
		msg['Cc'] = "hal.bib@uvsq.fr"
	
	msg['Subject'] = "Partager votre article sur HAL "+title[0]	

	# ____ add body to msg
	msg.attach(MIMEText(message, 'plain'))
	s.send_message(msg)

	out.writerow([mail, len(mailNuris[mail]), 'x'])
	print(f"\n{mail}\n{len(mailNuris[mail])} article\nmail sent")
	del msg
	
	if step == "test" : 
		break

s.quit()
fh_stats_envoi.close()