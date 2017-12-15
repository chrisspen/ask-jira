import os

import yaml

from jira.client import JIRA

def get_jira():
    conf_fn = os.environ.get('ASKJIRA_CONF', '~/.ask_jira.yaml')
    conf = yaml.load(open(os.path.expanduser(conf_fn)))
    jira = JIRA({'server': conf['server']}, # add 'verify': False if HTTPS cert is untrusted
                basic_auth=(conf['user'], conf['password']))
    return jira
