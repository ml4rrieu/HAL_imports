'''
Script pour faire du mailing aux auteurs correspondants dont les articles ne sont pas en accès ouvert,
en les invitant à déposer leur PDF conformément à la "loi pour une république numérique"

un extrait du fichier csv utilisé 
	index,state,type,lien hal,open access,qui traite,traité ?,commentaire,mail correspondant,mail envoyé
	78,new,ART,https://hal.archives-ouvertes.fr/hal-02876608,closed,pesronneA,ok ,,dfg.xxx@aphp.fr,
	85,new,ART,https://hal.archives-ouvertes.fr/hal-02876615,closed,pesronneA,ok,,caroline.xxx@uvsq.fr,
	86,new,ART,https://hal.archives-ouvertes.fr/hal-02876616,closed,pesronneB,ok,,caroline.xxx@uvsq.fr,
	9,new,COMM,https://hal.archives-ouvertes.fr/hal-02677090,closed,pesronneB,ok,,,

la colonne 'mail correspondant', pour les articles sans accès ouvert, ne doit pas être lassée vide : 
indiquer  'pass' si ne souhaitez pas envoyez de mail pour ces publications

Maxence Larrieu 
2021 01
'''


#____________________________________________________________

liste_publi_ac_email = "Hal Uvsq Imports - octobre.csv"
step = "test" # test or 'envoi' pour envoyer les mails

#____________________________________________________________

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict
import pandas as pd
from string import Template 
import smtplib, json, csv, requests


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


with open("../path_and_perso_data.json") as fh : 
	local_data = json.load(fh)

# ____ load publis liste to be treated
data = pd.read_csv(liste_publi_ac_email)
sel_publications = data.loc[(data.type =='ART') &\
(data['open access'].isin(['closed','open from publisher : no licence'])) &\
(data['mail correspondant'] !='pass') &\
(data['qui traite']) ]

# ____ configure SMTP server
fh = open("../path_and_perso_data.json")
private = json.load(fh)
s = smtplib.SMTP_SSL(host='smtps.uvsq.fr', port=465)
s.login(private["perso_login_server"], private["perso_pwd_server"])

#______ un csv pour extraire des stats basiques
fh_stats_envoi = open("stats_envoi.csv", 'w', encoding='utf8', newline='')
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
	message_template = (read_template("message.txt") if len(title) == 1 else read_template("message_pluriel.txt"))
	
	# ____ create message
	msg = MIMEMultipart()
	message = message_template.substitute(TITLE = title_and_link )

	msg['From']="hal.bib@uvsq.fr"
	
	if step == "test" : 
		msg['To'] = local_data["perso_email"]
	
	elif step == "valid" : 
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

