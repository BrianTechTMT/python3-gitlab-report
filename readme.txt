This project is use for collecting report from GITLAB API
To get the report we will be using Python 3 Script, report.py in projects folder.
To run the script, make sure your machine has Python 3 installed.

Requirements to run the file:
- edit the telegraf file etc/default for your own url token
- projects.json in config directory on the github is a mock file so you will need to edit it or replace it with your own when you run the live test
- Edit the report.py script for your live test: On line 10 of the script, change out base url with your project base url. If you have a token for your url put a "#" on line 56 to comment it out and uncomment (remove "#") on line 57.

Use command line: 	python3 report.py [-options,--long-options] (Pick below)
					   -h,--help (To get options help on terminal)
					   -m,--mock (To run mock test)
					   -l,--live (To run live test)

This script will give user result report from GITLAB for each new projects from each time there is a new pipeline report from the API
Report includes project ids, project names, report results, test counts, etc.
