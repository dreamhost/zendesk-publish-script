#! /usr/bin/env python

from bs4 import BeautifulSoup
import requests
import sys
import os
import json
import re
import yaml
from io import open

class article:
    def __init__(self, file_name, html_source, password, email, url,
            section_id, script_dir, title=None):
        self.file_name = file_name
        self.html_source = html_source
        self.password = password
        self.email = email
        self.url = url
        self.section_id = section_id
        self.script_dir = script_dir
        self.title = title

    # Publish the article if it needs to be published, else update it if it already exists
    # This function adds special dreamcloud buttons and uploads links
    def publish_or_update_dreamcloud(self):
        self.create_payload()
        self.labels = self.get_labels()
        section = self.get_section()
        if section['category_id'] == 202115418:
            self.add_dhc_signup_button()

        if section['category_id'] == 202115428:
            self.add_dho_signup_button()

        article_list_url = section["url"].rstrip(".json") + "/articles.json?per_page=500"

        self.article = self.get_article(article_list_url)

        if self.article:
            self.update_article_metadata()
            if self.tree.find_all('img'):
                self.upload_pictures()
            self.update_article()

        else:
            self.publish_article(article_list_url)
            self.article = self.get_article(article_list_url)
            if self.tree.find_all('img'):
                self.upload_pictures()
                self.update_article()

        print self.article['html_url']

    # Publish the article if it needs to be published, else update it if it already exists
    def publish_or_update_json(self):
        self.create_payload()
        self.labels = self.get_labels()
        section = self.get_section()
        article_list_url = section["url"].rstrip(".json") + "/articles.json?per_page=500"

        self.article = self.get_article(article_list_url)

        if self.article:
            self.update_article_metadata()
            self.update_article()

        else:
            self.publish_article(article_list_url)
            self.article = self.get_article(article_list_url)

        print self.article['html_url']

    def deprecate(self):
        self.create_payload()
        section = self.get_section()
        article_list_url = section["url"].rstrip(".json") + "/articles.json?per_page=500"

        self.article = self.get_article(article_list_url)
        if article:
            self.deprecate_article_metadata()
            print(file_path + " has been deprecated")
            print self.article['html_url']

        else:
            print("That article doesn't exist therefore cant be deprecated")

    # Update the artile metadata
    def deprecate_article_metadata(self):
        session = requests.Session()
        session.auth = (self.email, self.password)
        session.headers = {'Content-Type': 'application/json'}
        data = json.dumps({'translation':{'outdated': True}})
        url = self.url + "/api/v2/help_center/articles/" + str(self.article['id']) + "/translations/" + str(self.article["locale"]) + ".json"
        r = session.put(url, data)
        print(r.status_code)
        print(r.raise_for_status())

    # Publish the article to zendesk
    def publish_article(self, section_url):
        # Create a session so we can post to zendesk
        session = requests.Session()
        session.auth = (email, password)
        session.headers = {'Content-Type': 'application/json'}

        if self.tree.body:
            data = json.dumps({'article': {'locale': 'en-us', 'draft': False, 'title': self.title,
                'body': str(self.tree.body), 'label_names' : self.labels}})
        else:
            data = json.dumps({'article': {'locale': 'en-us', 'draft': False, 'title': self.title,
                'body': str(self.tree), 'label_names' : self.labels}})

        # Post to zendesk and get the response
        r = session.post(section_url, data)

        # Print response data
        print(r.status_code)
        print(r.raise_for_status())

    def add_dhc_signup_button(self):
        button_html_path = os.path.join(self.script_dir, 'dhc_button')
        with open(button_html_path, mode='r', encoding='utf-8') as f:
            button = f.read()

        self.tree.body.append(BeautifulSoup(str(button), "html.parser"))

    def add_dho_signup_button(self):
        button_html_path = os.path.join(self.script_dir, 'dho_button')
        with open(button_html_path, mode='r', encoding='utf-8') as f:
            button = f.read()

        self.tree.body.append(BeautifulSoup(str(button), "html.parser"))

    # Set self.tree and self.title based on the contents of the file self.file_name points to
    def create_payload(self):
        # Grab the title from the html
        self.tree = BeautifulSoup(self.html_source, "html.parser")
        if not self.title:
            try:
                self.title = self.tree.h1.string
                self.tree.h1.extract()
            except:
                self.title = self.tree.title.string

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
        if self.tree.body:
            data = json.dumps({'translation':{'body':str(self.tree.body), 'title':self.title}})
        else:
            data = json.dumps({'translation':{'body':str(self.tree), 'title':self.title}})

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
                    att_names.append(file_name)
                    attachments.append(r.json())
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

# Set self.tree and self.title based on the contents of the file self.file_name points to
def get_html_from_html_file(file_name):
    # Open the file and get its contents
    with open(file_name, mode='r', encoding='utf-8') as f:
        html_source = f.read()

    return html_source

# Set self.tree and self.title based on the contents of the file self.file_name points to
def get_json_from_file(file_name):
    # Open the file and get its contents
    with open(file_name, mode='r', encoding='utf-8') as f:
        json_source = f.read()
        json_source = json.loads(json_source)

    return json_source

# Grab variables for authentication and the url from the environment
env = os.environ
script_dir = os.path.dirname(sys.argv[0])

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


file_path = os.path.expandvars(file_path)

# Check if the file passed in as an argument is a yaml file, if it is, parse it
# and do the mass publishing stuff.
if re.match(".*\.yml", file_path) or re.match(".*\.yaml", file_path):

    data = yaml.load(open(file_path))

    file_directory, file_name = os.path.split(file_path)

    for section_id in data.keys():
        for article_directory in data[section_id].keys():
            for i in data[section_id][article_directory]:
                if not file_directory:
                    html_file = article_directory + '/' + i
                else:
                    html_file = file_directory + '/' + article_directory + '/' + i

                print("Publishing " + html_file)
                html_source = get_html_from_html_file(html_file)
                art = article(html_file, html_source, password, email, url, section_id,
                        script_dir)
                art.publish_or_update_dreamcloud()

# If it isnt publish the file specified to the section specified.
elif re.match(".*\.html", file_path):
    section_id = int(sys.argv[2])
    html_source = get_html_from_html_file(file_path)
    derp = article(file_path, html_source, password, email, url, section_id, script_dir)
    derp.publish_or_update_dreamcloud()

elif re.match(".*\.json", file_path):
    json_source = get_json_from_file(file_path)
    html_source = json_source['body']
    title = json_source['title']

    try:
        section_id = int(sys.argv[2])
    except:
        section_id = json_source['section_id']

    derp = article(file_path, html_source, password, email, url, section_id,
            script_dir, title)
    derp.publish_or_update_json()
