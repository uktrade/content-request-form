# content-request-form

## Overview
A form to request content changes to GOV.UK / Great.gov.uk websites.  User access is controlled by the DIT authbroker/staff-sso, and submitted tickets are inserted into the content team's Jira board.

## Dependencies
Python 3.6
DIT Authbroker/staff-sso
DIT ClamAV REST service
Jira

* the project does not require a database.

## Setting up a local development environment

1. Clone this repository

2. Create a virtual environment

```bash
# the project root:
virtualenv --python=python3 env
```

3. Install pip-tools: `pip install pip-tools`

4. Install dependencies with pip-sync: `pip-sync requirements-dev.txt`

5. Copy sample_env to .env

6. Add authbroker, clamav and Jira configuration values to your .env file

7. Start up the local webserver: `./manage.py runserver`

## Running the tests

From the project's root directory run `pytest`
