# zendesk-publish-script
This is a script that takes an html file and a section as arguments and
publishes the html to that zection on zendesk. Handles images and tags, also
can update a article if it already exists.

## Using the Script
First create a virtualenv with the required modules using:

`virtualenv venv ; . venv/bin/activate ; pip install -r requirements.txt`

After that you will also need to set some environment variables:
 - ZENDESK\_URL="https://subdomain.zendesk.com"
 - EMAIL="your email you use with zendesk"
 - ZENDESK\_PASS="Your Password"

Then you can run the script with:

`python publish.py file.html section_num`

To run the mass publish script, write a yaml file with the configs (see example.yml), then run:

`python mass_publish.py file.yml`
