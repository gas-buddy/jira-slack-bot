'''
This function handles a Slack slash command and echoes the details back to the user.

Follow these steps to configure the slash command in Slack:

  1. Navigate to https://<your-team-domain>.slack.com/services/new

  2. Search for and select "Slash Commands".

  3. Enter a name for your command and click "Add Slash Command Integration".

  4. Copy the token string from the integration settings and use it in the next section.

  5. After you complete this blueprint, enter the provided API endpoint URL in the URL field.


To encrypt your secrets use the following steps:

  1. Create or use an existing KMS Key - http://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html

  2. Click the "Enable Encryption Helpers" checkbox

  3. Paste <COMMAND_TOKEN> into the kmsEncryptedToken environment variable and click encrypt


Follow these steps to complete the configuration of your command API endpoint

  1. When completing the blueprint configuration select "Open" for security
     on the "Configure triggers" page.

  2. Enter a name for your execution role in the "Role name" field.
     Your function's execution role needs kms:Decrypt permissions. We have
     pre-selected the "KMS decryption permissions" policy template that will
     automatically add these permissions.

  3. Update the URL for your Slack slash command with the invocation URL for the
     created API resource in the prod stage.
'''

import boto3
import json
import logging
import os
import requests
import json
import random

from base64 import b64decode
from urlparse import parse_qs


ENCRYPTED_EXPECTED_TOKEN = os.environ['kmsEncryptedToken']
JIRA_USER = os.environ['jiraUsername']
ENCRYPTED_JIRA_PASSWORD = os.environ['jiraEncryptedPassword']

kms = boto3.client('kms')
expected_token = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_EXPECTED_TOKEN))['Plaintext']
expected_password = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_JIRA_PASSWORD))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_jira_summary(board):
    print('Getting Jira Sprint Summary')
    total_tasks = 0
    total_todo = 0
    total_in_progress = 0
    total_done = 0
    total_sprint_score = 0
    sprint_name = ''
    boardSprints = requests.get('https://gasbuddy.atlassian.net/rest/agile/1.0/board/'+board+'/sprint', auth=(JIRA_USER, expected_password))
    json_sprints = json.loads(boardSprints.text)
    for sprint in json_sprints['values']:
        if (sprint['state'] == 'active'):
            current_sprint = sprint['id']
            sprint_name = sprint['name']

    issues = requests.get('https://gasbuddy.atlassian.net/rest/agile/1.0/board/'+board+'/sprint/'+str(current_sprint)+'/issue', auth=(JIRA_USER, expected_password))
    json_issues = json.loads(issues.text)
    for issue in json_issues['issues']:

        total_tasks += 1
        if (isinstance( issue['fields']['customfield_10027'], float )):
            total_sprint_score += issue['fields']['customfield_10027']

        issue_name = issue['fields']['status']['name']
        if (issue_name == 'To Do'):
            total_todo += 1
        if (issue_name == 'In Progress'):
            total_in_progress += 1
        if (issue_name == 'Done'):
            total_done += 1

    return ('*Summary for ' + sprint_name + '*\n'
            + 'Total Tasks: ' + str(total_tasks) + '\n'
            + 'To Do: ' + str(total_todo) + '\n'
            + 'In Progress: ' + str(total_in_progress) + '\n'
            + 'Story Points: ' + str(int(total_sprint_score)))

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }

def pretty_respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': json.dumps({
           'response_type': 'in_channel',
           'text': res
        }),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    params = parse_qs(event['body'])
    token = params['token'][0]
    if token != expected_token:
        logger.error("Request token (%s) does not match expected", token)
        return respond(Exception('Invalid request token'))

    user = params['user_name'][0]
    command = params['command'][0]
    channel = params['channel_name'][0]
    command_text = params['text'][0]

    if (command_text.startswith('board ')):
        board = command_text.split(' ')[1]
        return pretty_respond(None, get_jira_summary(board))

    return respond(None, "%s invoked %s in %s with the following text: %s" % (user, command, channel, command_text))
