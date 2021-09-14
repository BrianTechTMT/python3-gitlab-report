This project is use for collecting report from GITLAB API
To get the report we will be using Python 3 Script, report.py.
To run the script, make sure your machine has Python 3 installed.

Use command line: 	python3 report.py [-options,--long-options] (Pick below)
					   -h,--help (To get options help on terminal)
					   -m,--mock (To run mock test)
					   -l,--live (To run live test)

This script will give user result report from GITLAB for each new projects from each time there is a new pipeline report from the API
Report includes project ids, project names, report results, test counts, etc.
