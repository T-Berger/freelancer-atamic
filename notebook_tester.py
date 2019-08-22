import os
import io
import yaml
import json
import argparse
import nbformat
import re
import zipfile 
import smtplib

from glob import glob
from nbconvert.preprocessors import ExecutePreprocessor
from datetime import datetime
from slackclient import SlackClient
from io import StringIO
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
    
def test_notebooks():
    # define process executor with timeout in seconds and python runtime
    proc = ExecutePreprocessor(timeout=60, kernel_name='python3')
    proc.allow_errors = True

    # test all Jupyte notebooks from folder (remove hidden folders)
    for i in range(len(FOLDERS)):        
        # include only not hidden jupyter notebooks        
        files = sorted([y for x in os.walk(FOLDERS[i]) for y in glob(os.path.join(x[0], '[!.]*.ipynb'))])
        
        print()
        print('Parsing files from ' + FOLDERS[i] + ' with ' + str(len(files)) + ' files')
        print('+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-')
        
        errors = []
        nb = None
        i = 1       
        for file in files:
            print(str(i) + ' - Testing notebook ' + file)

            with open(file) as f:
                nb = nbformat.read(f, as_version=4)

                proc.preprocess(nb, {'metadata': {'path': '/'}})

                for cell in nb.cells:
                    if 'outputs' in cell:
                        for output in cell['outputs']:
                            if output.output_type == 'error':
                                errors.append({'notebook': file, 'cell': cell.execution_count, 'trace': output})
                                
            i = i + 1

    return nb, errors

def zip_notebooks(folders, dst):
    zf = zipfile.ZipFile(dst, "w")
    
    for i in range(len(folders)):        
        folder = os.path.abspath(folders[i])  
        
        for d, s, f in os.walk(folder):
            for n in f:              
                # exclude hidden fiels and folders                   
                if re.match(r"^[^.].*$", n):                
                    abs_name = os.path.abspath(os.path.join(d,n))
                    arc_name = abs_name[len(folder) + 1:]
                    
                    zf.write(abs_name, arc_name)                								
                
    zf.close()    

def email_notebooks(subject, zip_file):
	msg = MIMEMultipart()
	msg['Subject'] = subject
	msg['From'] = EMAIL_SENDER
	msg['To'] = EMAIL_RECIPIENT

	part = MIMEBase("application", "octet-stream")
	part.set_payload(open(zip_file, "rb").read())
	encoders.encode_base64(part)
	part.add_header("Content-Disposition", "attachment; filename=\"%s.zip\"" % (zip_file))
	msg.attach(part)	
    
	smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

	smtp.ehlo()
	smtp.starttls()
	smtp.ehlo()
    
	smtp.login(EMAIL_SENDER_USERNAME, EMAIL_SENDER_PASSWORD)
	smtp.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
	smtp.close()
    
if __name__ == '__main__':    
    # get FOLDERS from yaml file
    print('Get folders from configuration ...')
    with open("configuration.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    
    FOLDERS = cfg['folders']
    
    print()
    print('Configuration slack connection ...')
    
    # get sclack API Token        
    parser = argparse.ArgumentParser(description='Notebook Jupyter Tester', epilog='Example of use: python3 notebook_tester.py -t <SLACK_API_TOKEN> -u <USERNAME_SENDER_EMAIL> -p <PASSWORD_SENDER_EMAIL>')    
    parser.add_argument('-t', '--token', type=str, help='Slack API Token to notifie')
    parser.add_argument('-u', '--username', type=str, help='Sender username email account')
    parser.add_argument('-p', '--password', type=str, help='Sender password email account')

    args = parser.parse_args()
    
    # slack configuration
    SLACK_API_TOKEN = args.token
    
    # email configuration for gmail
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587    
    EMAIL_SENDER_USERNAME = args.username
    EMAIL_SENDER_PASSWORD = args.password
    EMAIL_SENDER = cfg['email'][0]['sender']
    EMAIL_RECIPIENT = cfg['email'][1]['recipient']
    
    client = SlackClient(SLACK_API_TOKEN)

    print('EMAIL_SENDER_USERNAME' + EMAIL_SENDER_USERNAME)
    print('EMAIL_SENDER_PASSWORD' + EMAIL_SENDER_PASSWORD)
    
    print()
    print('STEP01: Testing Jupyter notebooks from these folders: ')
    for i in range(len(FOLDERS)):
        print(' ' + FOLDERS[i])
    print()

    # STEP01: testing notebooks
    nb, errors = test_notebooks()
        
    if len(errors) > 0:
        initial_comment = 'Testing Atamic at ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' with errors'
        
        print('STEP01: Exist with some errors ...')
        print()
    else:
        initial_comment = 'Testing Atamic at ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ' with any error'
        
        print('STEP01: Exist without errors ...')
        print()
        
    logname = 'atamic_' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.log'
    log = json.dumps(errors, indent=4)
    
    strIO = StringIO(json.dumps(errors, indent=4))
    bIO = io.BytesIO(strIO.read().encode('utf8'))
            
    # STEP02: send slack notification from test
    response = client.api_call('files.upload',
                                channels='#test',
                                filename=logname,
                                title='Testing Atamic at ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                initial_comment=initial_comment,
                                file=bIO)
                     
    if response['ok'] == True:                                   
        print('STEP02: Slack Notification correctly ...')
        print()
    else:
        print('STEP02: Error Slack Notification')
        print(response)    
        
    # STEP03: zip all notebooks folders excluding dot files
    zip_name = 'notebooks.zip'
    zip_notebooks(FOLDERS, zip_name)        
    print('STEP03: Notebooks zipped correctly ...')
    print()
    
    # STEP04: email with a zip`attached if exist any error
    if len(errors) > 0:
        email_notebooks('Testing Atamic at ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), zip_name)
        print('STEP04: Email sent correctly ...')