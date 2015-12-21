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

    # Publish the article if it needs to be published, else update it if it already exists
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
                self.article = self.get_article(article_list_url)
                self.upload_pictures()
                self.update_article()

    # Publish the article to zendesk
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

    # Set self.tree and self.title based on the contents of the file self.file_name points to
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
                    tag['src'] = r.json()['article_attachment']['content_url']
                else:
                    for item in attachments:
                        if item['file_name'] == file_name:
                            tag['src'] = item['content_url']
                            break

    # Get a list of article attachments so we know if we need to upload them or if they already exist
    def get_article_attachments(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        url = self.url + "/api/v2/help_center/articles/" + str(self.article['id']) + "/attachments.json"
        r = session.get(url)
        return r.json()

# Grab variables for authentication and the url from the environment
env = os.environ

try:
    email = env['EMAIL']
except:
    print("The environment variable 'EMAIL' is not set, please set it to the email that you use with zendesk")
    sys.exit(1)

try:
    password = env['ZENDESK_PASS']
except:
    print("The environment variable 'ZENDESK_PASS' is not set, please set it to your zendesk password")
    sys.exit(1)

try:
    url = env['ZENDESK_URL']
except:
    print("The environment variable 'ZENDESK_URL' is not set, please set it to the url of the zendesk you wish to publish to")
    sys.exit(1)

try:
    file_path = sys.argv[1]
except:
    print("You did not pass a file as an argument into the program")
    sys.exit(1)

# Check if the file passed in as an argument is a yaml file, if it is, parse it
# and do the mass publishing stuff.
if re.match(".*\.yml", file_path) or re.match(".*\.yaml", file_path):
    file_path = os.path.expandvars(file_path)

    data = yaml.load(open(file_path))

    file_directory, file_name = os.path.split(file_path)

    for article_directory in data.keys():
        for i in data[article_directory]['articles']:
            html_file = file_directory + '/' + article_directory + '/' + i
            print("Publishing " + html_file)
            art = article(html_file, password, email, url, data[article_directory]['section_id'])
            art.publish_or_update()

# If it isnt publish the file specified to the section specified.
else:
    section_id = int(sys.argv[2])
    derp = article(file_path, password, email, url, section_id)
    derp.publish_or_update()
