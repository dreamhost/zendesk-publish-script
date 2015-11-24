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
    tree = BeautifulSoup(html_source, "html.parser")
    title = tree.h1.string.strip()

    # Strip the class out of the divs that have an id and have the class
    # "section"
    for tag in tree.find_all('div', attrs={'class': 'section'}):
        if tag.has_attr('id'):
            del tag['class']

    # Return the title, the html that makes up the body and the html tree
    html = str(tree.body)
    return title, html, tree

# Get tags out of the meta tags in the html
def get_tags(tree):
    tags = []
    for item in tree.find_all('meta', attrs={'name' : 'tags'}):
        for tag in item['content'].split():
            tags.append(tag)
    return tags

# Get a list of sections and return the one we want
def get_section(url, section_id, email = None, password = None):
    session = requests.Session()
    session.auth = (email, password)
    response = session.get(url + "/api/v2/help_center/sections.json")
    sections = json.loads(response.content)
    section = None
    for i in sections["sections"]:
        if i['id'] == section_id:
            section = i
            break

    if not section:
        raise Exception("Failed to find section " + section_id)

    return section

# Get the article with the title we are searching for, return None if it doesnt
# exist.
def get_article(url, article_name, email=None, password=None):
    session = requests.Session()
    session.auth = (email, password)
    response = session.get(url)
    articles = json.loads(response.content)
    article = None
    for i in articles["articles"]:
        if i['name'] == article_name:
            article = i
            break

    if article:
        return article
    return None

# Update the article body and title with the contents it should have
def update_article(email, password, url, article, body, title):
    session = requests.Session()
    session.auth = (email, password)
    session.headers = {'Content-Type': 'application/json'}
    data = json.dumps({'translation':{'body':body, 'title':title}})
    url = url + "/api/v2/help_center/articles/" + str(article['id']) + "/translations/" + str(article["locale"]) + ".json"
    r = session.put(url, data)
    print(r.status_code)
    print(r.raise_for_status())

# Update the artile metadata
def update_article_metadata(email, password, url, article, tags):
    session = requests.Session()
    session.auth = (email, password)
    session.headers = {'Content-Type': 'application/json'}
    data = json.dumps({'article':{'label_names':tags}})
    url = url + "/api/v2/help_center/articles/" + str(article['id']) + ".json"
    r = session.put(url, data)
    print(r.status_code)
    print(r.raise_for_status())

# Search through the html for pictures, get a list of attachments that exist
# for the article, and if the picture is not in that list, upload it. Then edit
# the html to point to the right url for the image.
def upload_pictures(email, password, url, article, title,
                    article_file_name, tree):
    session = requests.Session()
    session.auth = (email, password)
    pic_url = url + "/api/v2/help_center/articles/" + str(article['id']) + "/attachments.json"
    article_dir = os.path.split(article_file_name)[0]

    # Get a list of article attachments
    attachments = get_article_attachments(
        email, password, url, article)['article_attachments']

    # Collect the file_names of all the attachments
    att_names = []
    for item in attachments:
        att_names.append(item['file_name'])
    for tag in tree.find_all('img'):
        if tag.has_attr('src'):
            file_path = article_dir + '/' + tag['src']
            file_name = os.path.split(file_path)[1]
            if file_name not in att_names:
                files = {'file': open(file_path, 'rb')}
                r = session.post(pic_url, files=files)
                print(r.status_code)
                print(r.raise_for_status())
                print(r.json())
                tag['src'] = r.json()['article_attachment']['content_url']
            else:
                for item in attachments:
                    if item['file_name'] == file_name:
                        print item
                        print item['content_url']
                        tag['src'] = item['content_url']
                        print tag['src']
                        break

    body = str(tree.body)
    update_article(email, password, url, article, body, title)

def get_article_attachments(email, password, url, article):
    session = requests.Session()
    session.auth = (email, password)
    url = url + "/api/v2/help_center/articles/" + str(article['id']) + "/attachments.json"
    r = session.get(url)
    return r.json()

# Grab variables for authentication and the url from the environment
env = os.environ

email = env['EMAIL']
password = env['ZENDESK_PASS']
url = env['ZENDESK_URL']
file_name = sys.argv[1]
section_id = int(sys.argv[2])

section = get_section(url, section_id, email, password)
section_url = section["url"].rstrip(".json")
section_url += "/articles.json"

# Get the payload
title, html, tree = create_payload(file_name)
tags = get_tags(tree)
# Get the article
article = get_article(section_url, title, email, password)
# If the article doesnt exist, upload it
if not article:
    data = json.dumps({'article': {'locale': 'en-us', 'title': title,
        'body': html, 'label_names' : tags}})
    # Create a session so we can post to zendesk
    session = requests.Session()
    session.auth = (email, password)
    session.headers = {'Content-Type': 'application/json'}

    # Post to zendesk and get the response
    r = session.post(section_url, data)

    # Print response data
    print(r.status_code)
    print(r.raise_for_status())
else:
    update_article_metadata(email, password, url, article, tags)
# Now that the article exists, upload the images and correct the urls for the
# images
article = get_article(section_url, title, email, password)
upload_pictures(email, password, url, article, title, file_name, tree)
