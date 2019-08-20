import os
import io
import nbformat
import yaml
import json

from glob import glob
from nbconvert.preprocessors import ExecutePreprocessor
from datetime import datetime
from slackclient import SlackClient
from io import StringIO

def test_notebooks():
    # define process executor with timeout in seconds and python runtime
    proc = ExecutePreprocessor(timeout=60, kernel_name='python3')
    proc.allow_errors = True

    # test all Jupyte notebooks from folder (remove hidden folders)
    for i in range(len(FOLDERS)):        
        #files = sorted([y for x in os.walk(FOLDERS[i]) for y in glob(os.path.join(x[0], '[!.]*/*.ipynb'))])
        files = sorted([y for x in os.walk(FOLDERS[i]) for y in glob(os.path.join(x[0], '*.ipynb'))])        
        
        print()
        print('Parsing files from ' + FOLDERS[i] + ' with ' + str(len(files)) + ' files')
        print('+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-')
        errors = []
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
                                errors.append({'notebook': file, 'trace': output})
                                
            i = i + 1

    return nb, errors

if __name__ == '__main__':
    # get FOLDERS from yaml file
    print('Get folder from configuration ...')
    with open("configuration.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    
    FOLDERS = cfg['folders']    
    
    print()
    print('Configuration slack connection ...')
    
    SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']

    client = SlackClient(SLACK_API_TOKEN)

    print()
    print('Testing Jupyter notebooks from these folders: ')
    for i in range(len(FOLDERS)):
        print(' ' + FOLDERS[i])
    print()

    # testing notebooks
    nb, errors = test_notebooks()
        
    print('Exist this errors ...')
    
    #print(errors)
    #for error in errors:
    #    print()
    #    print('Notebook: ' + error['notebook'])       
    #    print(error['trace'])   
    
    logname = 'atamic_' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.log'
    log = json.dumps(errors, indent=4)
    
    strIO = StringIO(json.dumps(errors, indent=4))
    bIO = io.BytesIO(strIO.read().encode('utf8'))
    
    response = client.api_call('files.upload',
                                channels='#test',
                                filename=logname,
                                title='Testing Atamic!',
                                initial_comment='Testing Atamic!',
                                file=bIO)
                     
    if response['ok'] == True:                                   
        print('Message sent')
    else:
        print(response)    