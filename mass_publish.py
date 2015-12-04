"""
This script uses the publish.py script to pubslish a bunch of articles that
are configured in a yaml file. The articles in the yaml file should have a path
relative to the yaml file, for example if the yaml file is located at

~/foo/bar/config.yml

and the articles are located at

~/foo/bar/articles/

the config.yml file should look something like

articles/article1.html:
  section_id: 261820
articles/article2.html:
  section_id: 261820
articles/article3.html:
  section_id: 261942

"""

import yaml
import os
import sys

file_path = sys.argv[1]

file_path = os.path.expandvars(file_path)

data = yaml.load(open(file_path))

file_directory, file_name = os.path.split(file_path)

for item in data.keys():
    print("Publishing " + item)
    os.system("python publish.py " + file_directory + "/" + item + " " + str(data[item]['section_id']))
