#!/bin/bash
VENV=${VENV:-venv}
$VENV/bin/pylint --rcfile=pylint.rc *.py bin/ask-jira.py ask_jira
