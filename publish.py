from bs4 import BeautifulSoup
import requests
import sys
import os
import json
import re
import yaml
from io import open

class article:
    def __init__(self, file_name, password, email, url, section_id):
        self.file_name = file_name
        self.password = password
        self.email = email
        self.url = url
        self.section_id = section_id

    def publish_or_update(self):
        self.create_payload()
        self.labels = self.get_labels()
        section = self.get_section()
        article_list_url = section["url"].rstrip(".json") + "/articles.json?per_page=500"

        self.article = self.get_article(article_list_url)

        if self.article:
            self.update_article_metadata()
            if self.tree.find_all('img'):
                self.upload_pictures()
            self.update_article()

        else:
            self.publish_article(article_list_url)
            if self.tree.find_all('img'):
                self.upload_pictures()
                self.update_article()

    def publish_article(self, section_url):
        # Create a session so we can post to zendesk
        session = requests.Session()
        session.auth = (email, password)
        session.headers = {'Content-Type': 'application/json'}

        data = json.dumps({'article': {'locale': 'en-us', 'draft': False, 'title': self.title,
            'body': str(self.tree.body), 'label_names' : self.labels}})

        # Post to zendesk and get the response
        r = session.post(section_url, data)

        # Print response data
        print(r.status_code)
        print(r.raise_for_status())

    def create_payload(self):
        # Open the file and get its contents
        with open(self.file_name, mode='r', encoding='utf-8') as f:
            html_source = f.read()

        # Grab the title from the html
        self.tree = BeautifulSoup(html_source, "html.parser")
        self.title = self.tree.h1.string.strip()

        # Strip the class out of the divs that have an id and have the class
        # "section"
        for tag in self.tree.find_all('div', attrs={'class': 'section'}):
            if tag.has_attr('id'):
                del tag['class']

    # Get labels out of the meta labels in the html
    def get_labels(self):
        labels = []
        for item in self.tree.find_all('meta', attrs={'name' : 'labels'}):
            for label in item['content'].split():
                labels.append(label)
        return labels

    # Get a list of sections and return the one we want
    def get_section(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        response = session.get(self.url + "/api/v2/help_center/sections.json?per_page=100")
        sections = json.loads(response.content)
        section = None
        for i in sections["sections"]:
            if i['id'] == self.section_id:
                section = i
                break

        if not section:
            raise Exception("Failed to find section " + str(self.section_id))

        return section

    # Get the article with the title we are searching for, return None if it doesnt
    # exist.
    def get_article(self, url):
        session = requests.Session()
        session.auth = (self.email, self.password)
        response = session.get(url)
        articles = json.loads(response.content)
        article = None
        for i in articles["articles"]:
            if i['name'] == self.title:
                article = i
                break

        return article

    # Update the article body and title with the contents it should have
    def update_article(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        session.headers = {'Content-Type': 'application/json'}
        data = json.dumps({'translation':{'body':str(self.tree.body), 'title':self.title}})
        url = self.url + "/api/v2/help_center/articles/" + str(self.article['id']) + "/translations/" + str(self.article["locale"]) + ".json"
        r = session.put(url, data)
        print(r.status_code)
        print(r.raise_for_status())

    # Update the artile metadata
    def update_article_metadata(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        session.headers = {'Content-Type': 'application/json'}
        data = json.dumps({'article':{'label_names':self.labels}})
        url = self.url + "/api/v2/help_center/articles/" + str(self.article['id']) + ".json"
        r = session.put(url, data)
        print(r.status_code)
        print(r.raise_for_status())

    # Search through the html for pictures, get a list of attachments that exist
    # for the article, and if the picture is not in that list, upload it. Then edit
    # the html to point to the right url for the image.
    def upload_pictures(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        pic_url = self.url + "/api/v2/help_center/articles/" + str(self.article['id']) + "/attachments.json"
        article_dir = os.path.split(self.file_name)[0]

        # Get a list of article attachments
        attachments = self.get_article_attachments()['article_attachments']

        # Collect the file_names of all the attachments
        att_names = []
        for item in attachments:
            att_names.append(item['file_name'])

        for tag in self.tree.find_all('img'):
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

    def get_article_attachments(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        url = self.url + "/api/v2/help_center/articles/" + str(self.article['id']) + "/attachments.json"
        r = session.get(url)
        return r.json()

# Grab variables for authentication and the url from the environment
env = os.environ

email = env['EMAIL']
password = env['ZENDESK_PASS']
url = env['ZENDESK_URL']
file_path = sys.argv[1]

# Check if the file passed in as an argument is a yaml file, if it is, parse it
# and do the mass publishing stuff.
if re.match(".*\.yml", file_path) or re.match(".*\.yaml", file_path):
    file_path = os.path.expandvars(file_path)

    data = yaml.load(open(file_path))

    file_directory, file_name = os.path.split(file_path)

    for item in data.keys():
        print("Publishing " + item)
        html_file = file_directory + '/' + item
        art = article(html_file, password, email, url, data[item]['section_id'])
        art.publish_or_update()

# If it isnt publish the file specified to the section specified.
else:
    section_id = int(sys.argv[2])
    derp = article(file_path, password, email, url, section_id)
    derp.publish_or_update()
