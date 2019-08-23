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
from apiclient import discovery
from apiclient.http import MediaFileUpload
from google.oauth2 import service_account
    
def test_notebooks():
    # define process executor with timeout in seconds and python runtime
    proc = ExecutePreprocessor(timeout=60, kernel_name='python3')
    proc.allow_errors = True

    # test all Jupyte notebooks from folder (remove hidden folders)
    for i in range(len(FOLDERS)):        
        # include only not hidden jupyter notebooks        
        files = sorted([y for x in os.walk(FOLDERS[i]) for y in glob(os.path.join(x[0], '[!.]*.ipynb'))])
        
        print()
        print('Parsing files from ' + FOLDERS[i] + ' with ' + str(len(files)) + ' files ')
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
	part.add_header("Content-Disposition", "attachment; filename=\"%s\"" % (zip_file))
	msg.attach(part)	
    
	smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

	smtp.ehlo()
	smtp.starttls()
	smtp.ehlo()
    
	smtp.login(EMAIL_SENDER_USERNAME, EMAIL_SENDER_PASSWORD)
	smtp.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
	smtp.close()
    
def drive_notebooks(file_name, drive_file):
    # get credentials from file and scope configured
    credentials = service_account.Credentials.from_service_account_file(DRIVE_CREDENTIALS, scopes=DRIVE_SCOPES)
    
    # obtain the API Drive service from version
    service = discovery.build('drive', 'v3', credentials=credentials)

    # Create a folder
    # https://developers.google.com/drive/v3/web/folder
#    folder_metadata = {
#        'name': 'notebooks',
#        'mimeType': 'application/vnd.google-apps.folder'
#    }
#    cloudFolder = service.files().create(body=folder_metadata).execute()
    
    # Upload a file in the folder
    # https://developers.google.com/api-client-library/python/guide/media_upload
    # https://developers.google.com/drive/v3/reference/files/create
#    file_metadata = {
#        'name': subject,
#        'parents': [cloudFolder['id']]
#    }

    file_metadata = {
        'name': file_name
    }
         
    # https://developers.google.com/api-client-library/python/guide/media_upload
    #media = MediaFileUpload(tf, mimetype='text/plain')
    media = MediaFileUpload(drive_file)
    
    # https://developers.google.com/drive/v3/web/manage-uploads
    cloudFile = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    # Share file with a human user
    # https://developers.google.com/drive/v3/web/manage-sharing
    # https://developers.google.com/drive/v3/reference/permissions/create
    service.permissions().create(fileId=cloudFile['id'], body={'type': 'user', 'role': 'reader', 'emailAddress': DRIVE_EMAIL}).execute()
        
if __name__ == '__main__':    
    # load yaml service configurations
    with open("configuration.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    print('yaml configuration file loaded correctly')
    print()
            
    # load command argument configurations
    parser = argparse.ArgumentParser(description='Notebook Jupyter Tester', epilog='Example of use: python3 notebook_tester.py -t <SLACK_CREDENTIALS> -eu <USERNAME_SENDER_EMAIL> -ep <PASSWORD_SENDER_EMAIL> -dc <DRIVE_CREDENTIALS>')    
    parser.add_argument('-t', '--token', type=str, help='Slack API Token to notifie')
    parser.add_argument('-eu', '--username', type=str, help='Sender username email account')
    parser.add_argument('-ep', '--password', type=str, help='Sender password email account')
    parser.add_argument('-dc', '--drive_credentials', default='service_account.json', type=str, help='Drive Credentials file')

    args = parser.parse_args()

    # get TRACE to print all app configurations on console
    TRACE = cfg['trace']    
    if TRACE == 1:
        print('Printing all app configurations on console')
        print()
        
    # get Jupyter Notebooks configurations
    FOLDERS = cfg['folders']
    
    if TRACE == 1:
        print('Jupyter Notebooks configurations')
        print('--------------------------------')
        print('FOLDERS: ' + ', '.join(FOLDERS))
        print()
        
    # get slack configurations
    SLACK_CREDENTIALS = args.token

    if TRACE == 1:
        print('Slack configurations')
        print('----------------------------')
        print('SLACK_API_TOKEN: ' + SLACK_CREDENTIALS)
        print()
    
    client = SlackClient(SLACK_CREDENTIALS)
        
    # get email SMTP configurations
    SMTP_HOST = cfg['email'][0]['host']
    SMTP_PORT = cfg['email'][1]['port']
    EMAIL_SENDER = cfg['email'][2]['sender']
    EMAIL_RECIPIENT = cfg['email'][3]['recipient']
    EMAIL_SENDER_USERNAME = args.username
    EMAIL_SENDER_PASSWORD = args.password
    
    if TRACE == 1:
        print('Email SMTP configurations')
        print('----------------------------')
        print('SMTP_HOST: ' + SMTP_HOST)
        print('SMTP_PORT: ' + str(SMTP_PORT))
        print('EMAIL_SENDER_USERNAME: ' + EMAIL_SENDER_USERNAME)
        print('EMAIL_SENDER_PASSWORD: ' + EMAIL_SENDER_PASSWORD)
        print('EMAIL_SENDER: ' + EMAIL_SENDER)    
        print('EMAIL_RECIPIENT: ' + EMAIL_RECIPIENT)
        print()
    
    # get Google Drive configurations
    DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
    DRIVE_CREDENTIALS = args.drive_credentials
    DRIVE_EMAIL = cfg['drive'][0]['email']
    
    if TRACE == 1:
        print('Google Drive configurations')
        print('-----------------------------------')
        print('DRIVE_SCOPES: ' + ', '.join(DRIVE_SCOPES))
        print('DRIVE_CREDENTIALS: ' + DRIVE_CREDENTIALS)
        print('DRIVE_EMAIL: ' + DRIVE_EMAIL)
        print()
    
    # get notification flags
    EMAIL_NOTIFICATION = cfg['notification'][0]['email']
    DRIVE_NOTIFICATION = cfg['notification'][1]['drive']
    
    if TRACE == 1:
        print('Notification flags')
        print('-----------------------------------')
        print('EMAIL_NOTIFICATION: ' + str(EMAIL_NOTIFICATION))
        print('DRIVE_NOTIFICATION: ' + str(DRIVE_NOTIFICATION))
        print()
    
    # Start python tester
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
    
    # STEP04: send notifications with a zip`attached if exist any error
    if len(errors) > 0:
        if (EMAIL_NOTIFICATION == 1):
            email_notebooks('Testing Atamic at ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), zip_name)
            print('STEP04: Email notification sent correctly ...')
            print()
        
        if (DRIVE_NOTIFICATION == 1):
            drive_notebooks('Testing Atamic at ' + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), zip_name)
            print('STEP04: Google Drive notification sent correctly ...')
            print()