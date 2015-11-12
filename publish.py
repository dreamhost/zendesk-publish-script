from bs4 import BeautifulSoup
import requests
import sys
import os
import json
from io import open

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

def get_section(url, section_name, email = None, password = None):
    session = requests.Session()
    response = session.get(url + "/api/v2/help_center/sections.json")
    sections = json.loads(response.content)
    section = None
    for i in sections["sections"]:
        if i['name'] == section_name:
            section = i
            break

    if not section:
        raise Exception("Failed to find section " + section_name)

    print(section)
    return section

# Grab variables for authentication and the url from the environment
env = os.environ

email = env['EMAIL']
section_name = env['SECTION']
password = env['ZENDESK_PASS']
url = env['ZENDESK_URL']

section = get_section(url, section_name)
section_url = section["url"].rstrip(".json")
section_url += "/articles.json"
print section_url

# Get the payload
data = create_payload(sys.argv[1])

# Create a session so we can post to zendesk
session = requests.Session()
session.auth = (email, password)
session.headers = {'Content-Type': 'application/json'}

# Post to zendesk and get the response
r = session.post(section_url, data)

# Print response data
print(r.status_code)
print(r.raise_for_status())
