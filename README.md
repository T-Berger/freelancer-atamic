# Description
Semaphore CD/CI Python Jupyter Notebook Tester Pipeline

# install semaphore CLI
curl https://storage.googleapis.com/sem-cli-releases/get.sh | bash

# connect to semaphore organization from shemaphore CLI
sem connect <ORGANIZATION>.semaphoreci.com <API_TOKEN>

  - API_TOKEN: is obtained from Organization->Account->API Token. Organization is Masalinas
  - ORGANIZATION: Organization where deploy pipelines

# create secrets in semaphore from shemaphore CLI
sem create secret <SECRET_NAME> -e <TOKEN_ID_1>=<TOKEN_VALUE_2> ... -e <TOKEN_ID_N>=<TOKEN_VALUE_N>

  - SECRET_NAME: name of the secret. Example: slack-secrets
  - TOKEN_ID_N: N name of the secret token included in previous SECRET_NAME. Example SLACK_API_TOKEN
  - TOKEN_VALUE_N: N value of the secret token included in previous SECRET_NAME. Example AAABBBCCC
