import json
import re
import sys, getopt
import os
import requests


STATUS_LIST = ["success", "failed", "manual", "skipped", "cancelled"]
PROJECT_JSON_PATH = "/../config/projects.json"
BASE_URL = "http://localhost:8000/PycharmProjects/pythonProject5/"
TOKEN_FILE_PATH = "/../etc/default/telegraf"
LAST_RUN_FILE = "/var/tmp/tmp_pipeline_ids"

def get_projects():
    """
    Read projects json
    """
    project_json = open(os.path.dirname(__file__) + PROJECT_JSON_PATH)
    project_identity = json.load(project_json)
    return project_identity

def get_live_token():
    """
    Get Live Test Token
    """
    token_file = open(os.path.dirname(__file__) + TOKEN_FILE_PATH)
    keyword = "GITLAB_API_SECRET"
    git_token=""
    for tokens in token_file:
        token = tokens.split("\n")
        for token_key in token:
            if keyword in token_key:
                gitlab_token = token_key.split("\"")[1]
    return gitlab_token


def get_projects_url_paths(*args):
    """
    Get paths to project base on the JSON
    """
    projects_infos = get_projects()
    projects_url_paths = []

    for project in projects_infos:
        projects_url_paths.append("projects/{id}/".format(id=project[0]))
    return projects_url_paths


def live_url_request(url,arg):
    """
    Use for each time the script ask for json string from server
    """
    request_url = BASE_URL + url
    if arg == "-m":
        json_response = requests.get(request_url)
    elif arg == "-l":
        json_response = requests.get(request_url, headers= {'PRIVATE-TOKEN: {url_token}'
                                 .format(url_token=get_live_token())})
    return json_response


def get_pipe_ids(url,arg):
    """
    Get All Pipelines IDs
    """
    if arg in ["-m", "--mock"]:
        link = url + "pipelines"
        id_list = open(link)
        pipelines = json.load(id_list)
    elif arg in ["-l", "--live"]:
        url += "pipelines"
        encoded_pipelines = live_url_request(url,arg)
        pipelines = encoded_pipelines.json()
    return pipelines


def get_match_pipe_ids(urls,arg):
    """
    Get pipeline IDs from API that is terminal
    """
    match_pipe_id_list = []
    for url in urls:
        pipelines = get_pipe_ids(url,arg)
        for pipeline in pipelines:
            if pipeline['status'] in STATUS_LIST:
                match_pipe_id_list.append(pipeline['id'])
    print(match_pipe_id_list)
    return match_pipe_id_list


def get_project_name(project_number):
    """
    Get project name
    """
    name = get_projects()
    for i in range(len(name)):
        if name[i][0] == project_number:
            return name[i][1]


def get_result_report(project_id, url):
    """
    Get Report for each pipeline
    """
    program_arg = sys.argv[1].split("-")[1]
    report_url = url + "pipeline_id/" + str(project_id) + "/test_report_summary"

    if program_arg in ["m","mock"]:
        pipe_list = open(report_url)
        data = json.load(pipe_list)
    elif program_arg in ["l","live"]:
        pipe_list = live_url_request(report_url)
        data = pipe_list.json()

    report_tags = ["name", "total_time", "total_count", "success_count", "failed_count", "skipped_count", "error_count",
                   "build_ids", "suite_error"]
    report_data = {}
    for k, v in data.items():

        if type(v) == list:

            for i in v:
                report_data = {key: i.get(key) for key in report_tags}

        else:
            continue

    return report_data


def existing_pipe_ids():
    """
    Get the existing ID from the server
    """
    ids_list = []
    if not os.path.exists(os.path.dirname(__file__) + LAST_RUN_FILE): # Check if record file exist
        pipe_id_file = open(os.path.dirname(__file__) + LAST_RUN_FILE, "a+") # if not then create
    else:
        pipe_id_file = open(os.path.dirname(__file__) + LAST_RUN_FILE, "w+") # else, start checking the list
        pipelines = []
        for existing_pipeline in pipe_id_file:
            pipelines = existing_pipeline.split(",")

        ids_list = [int(pipeline) for pipeline in pipelines]

    pipe_id_file.close()
    return ids_list


def compare_ids(ids_in_json_list, ids_in_file_list):
    """
    Compare the ID list from API and ID previously found and stored on server
    """
    new_pipeline_id = []

    if ids_in_json_list == ids_in_file_list:
        new_pipeline_id = []

    else:
        new_pipeline_id = [pipe_id for pipe_id in ids_in_json_list if pipe_id not in ids_in_file_list]

    return new_pipeline_id


def print_influx_protocol(print_report_dict, url):
    """
    Print out report function
    """
    projects_id_search = re.findall("(?<=projects/).*(?=/)", url)
    # Why Regex because it's already have a project ID passed into the path so regex can quickly track the
    # last number in the url and use it to get project name.
    projects_id = int(projects_id_search[0])
    project_name = get_project_name(projects_id)
    opening_line = "gitlab_test_report,project_id={projectID}".format(projectID=projects_id)
    tag_line, field_line = "", ""
    tags = ["project_id", "ref", "sha", "id", "proj_name", "build_ids"]

    for k, v in print_report_dict.items():

        if k in tags:

            if k == "build_ids":
                tag_line += ",{key}={value}".format(key=k, value=v[0])

            else:
                tag_line += ",{key}={value}".format(key=k, value=v)

        elif k == "web_url":
            field_line += "{key}=\"{value}\"".format(key=k, value=v)

        else:
            field_line += ",{key}={value}".format(key=k, value="\"{string}\"".format(string=v) if type(v) != int else v)

    print(opening_line + tag_line + ",project_name=" + project_name + " " + field_line)


def get_report_summary(*arg):
    # Get project paths
    arg=arg[0]
    projects_locations = get_projects_url_paths()  # A List

    # Get pipeline IDs
    json_pipe_ids = get_match_pipe_ids(projects_locations,arg)
    file_pipe_ids = existing_pipe_ids()

    # Compare IDS
    compared_ids_list = compare_ids(json_pipe_ids, file_pipe_ids)
    if compared_ids_list != file_pipe_ids and len(compared_ids_list) != 0:
        id_file = open(os.path.dirname(__file__) + LAST_RUN_FILE, "w")
        list_to_write_to_file = file_pipe_ids + compared_ids_list
        print(list_to_write_to_file)
        pipe_id_str = ','.join([str(i) for i in list_to_write_to_file])
        id_file.write(pipe_id_str)
        id_file.close()
        # Get Pipeline IDs infos from compared IDs
        pipe_id_list = []

        for each_project_url in projects_locations:  # A single url
            pipes = get_pipe_ids(each_project_url,arg)
            # Get Pipe ID paths from get_pipe_ids(), pipe_ids is all the pipeline IDs stats per project

            for pipe in pipes:  # Use each pipe ID to get the report from JSON file
                match_status_tags = ["ref", "sha", "id", "web_url", "created_at", "source", "name", "build_ids"]
                if pipe['id'] in compared_ids_list:  # Trace ID
                    report_dict = get_result_report(pipe['id'], each_project_url)
                    # Create path to report json then get a dictionary in return
                    pipe_tag_dict = {key: pipe.get(key) for key in match_status_tags}
                    # reformat the dictionary
                    print_report_dict = {**pipe_tag_dict, **report_dict}
                    # Merge the dictionaries
                    print_influx_protocol(print_report_dict, each_project_url)
                    # print out the result

    elif len(compared_ids_list) == 0:
        print("No new update")


if __name__ == '__main__':
    # Command Argument
    import getopt, sys

    # Get full command-line arguments
    full_cmd_arguments = sys.argv

    # Keep all but the first
    argument_list = full_cmd_arguments[1:]
    short_options = "hml"
    long_options = ["help", "mock", "live"]
    if len(argument_list) == 0:
        print("Options:\t-m,--mock\t Mock Test\n"
              "\t\t-l,--live\t Live Test")

    try:
        arguments, values = getopt.getopt(argument_list, short_options, long_options)
        for current_argument, current_value in arguments:
            if current_argument in ("-m", "--mock"):
                get_report_summary(current_argument)
            elif current_argument in ("-h", "--help"):
                print("Options:\t-m,--mock\t Mock Test\n"
                      "\t\t-l,--live\t Live Test")
            elif current_argument in ("-l", "--live"):
                get_report_summary(current_argument)
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)
