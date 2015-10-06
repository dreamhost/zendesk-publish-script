from bs4 import BeautifulSoup
import requests
import sys
import os
import json

# Load the html file and create the payload for the post request to zendesk
def create_payload(file_name):
    # Open the file and get its contents
    with open(file_name, mode='r', encoding='utf-8') as f:
        html_source = f.read()

    # Grab the title from the html
    tree = BeautifulSoup(html_source)
    title = tree.h1.string.strip()
    print(title)

    # Put the payload in the format that zendesk will accept
    data = {'article': {'locale': 'en-us', 'title': title, 'body': str(tree)}}
    return json.dumps(data)

# Grab variables for authentication and the url from the environment
env = os.environ

email = env['EMAIL']
password = env['ZENDESK_PASS']
url = env['ZENDESK_URL']

# Get the payload
data = create_payload(sys.argv[1])

# Create a session so we can post to zendesk
session = requests.Session()
session.auth = (email, password)
session.headers = {'Content-Type': 'application/json'}

# Post to zendesk and get the response
r = session.post(url, data)

# Print response data
print(r.status_code)
print(r.raise_for_status())
