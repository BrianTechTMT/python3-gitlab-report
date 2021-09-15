import json
import re
import sys, getopt
import os
import requests


def get_projects_mock():
    """
    Read projects json
    """
    project_json = open("projects.json")
    project_identity = json.load(project_json)
    return project_identity

def get_projects_live():
    resources = open("etc/default/telegraf")
    data = []
    keys = ["url", "token"]
    for resource in resources:
        info = resource.strip().split("\"")
        data.append(info[1])
    report = {keys[i]: data[i] for i in range(len(keys))}
    head = {'PRIVATE-TOKEN: {token}'.format(token=report['token'])}
    json2 = requests.get("{url}".format(url=report['url']))
    project_identity = json2.json()
    return project_identity

def get_base_info():
    """
    Get projects and it's names
    """
    if str(sys.argv[1].split("-")[1])=="m":
        loaded_json = get_projects_mock()
    elif str(sys.argv[1].split("-")[1])=="l":
        loaded_json = get_projects_live()
    projects_id_name = []

    for i in range(len(loaded_json)):
        per_proj_id_name = ""

        for j in range(len(loaded_json[i])):
            id_and_name = str(loaded_json[i][j])
            per_proj_id_name += id_and_name

        projects_id_name.append(per_proj_id_name)

    return projects_id_name


def get_projects_paths():
    """
    Get paths to project base on the JSON
    """
    projects_ids = get_base_info()
    projects_paths = []

    for projects in projects_ids:
        found_id = re.findall(r'^\D*(\d+)', projects)
        projects_paths.append("projects/{id}/".format(id=found_id[0]))

    return projects_paths


def get_ids(path):
    """
    Get Pipelines IDs
    """
    # pipe_list = requests.get("https://gitlab.com/api/v4/projects/")
    link = path + "pipelines.json"
    id_list = open(link)
    x = json.load(id_list)
    return x


def get_all_ids(paths):
    """
    Get pipeline IDs from API
    """
    match_status_list = ["success", "failed", "manual", "skipped", "cancelled"]
    project_id = []
    for path in paths:
        project_id_list = get_ids(path)
        for item in project_id_list:
            if item['status'] in match_status_list:
                project_id.append(item['id'])
    return project_id


def get_project_name(project_number):
    """
    Get project name
    """
    file = open("projects.json", "r")
    x = (json.load(file))

    for i in range(len(x)):

        if x[i][0] == project_number:
            return x[i][1]


def get_result_report(project_id, path):
    """
    Get Report for each pipeline
    """
    s = path + "pipeline_id/" + str(project_id) + "/test_report_summary.json"
    pipe_list = open(s)
    data = json.load(pipe_list)
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


def existing_id():
    """
    Get the existing ID from the server
    """
    lst_id = []
    if not os.path.exists("ID_File.txt"):
        pipe_id_file = open("ID_File.txt", "a+")
    else:
        pipe_id_file = open("ID_File.txt", "r+")
        pipelines_list = []

        for pipelines in pipe_id_file:
            pipelines_list = pipelines.split(",")

        if len(pipelines_list) != 0:
            pipelines_list.pop()
        else:
            pipelines_list = []

        lst_id = [int(m) for m in pipelines_list]

    pipe_id_file.close()
    return lst_id


def compare_ids(json_list, file_list):
    """
    Compare the ID list from API and ID previously found and stored on server
    """
    new_pipeline_id = []

    if json_list == file_list:
        new_pipeline_id = new_pipeline_id

    else:
        new_pipeline_id = [pipe_id for pipe_id in json_list if pipe_id not in file_list]

    return new_pipeline_id


def print_influx_protocol(pipe_id_dictionary, report_dictionary, path):
    """
    Print out report function
    """
    projects_id_search = re.findall("(?<=projects/).*(?=/)", path)
    projects_id = int(projects_id_search[0])
    project_name = get_project_name(projects_id)
    opening_line = "gitlab_test_report,project_id={projectID}".format(projectID=projects_id)
    tag_line, field_line = "", ""
    tags = ["project_id", "ref", "sha", "id", "proj_name", "build_ids"]
    print_report_dict = {**pipe_id_dictionary, **report_dictionary}

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


def protocols():
    # Get Project_paths
    project_paths = get_projects_paths()

    # Get pipeline IDs
    proj_id_from_json = get_all_ids(project_paths)
    proj_on_file = existing_id()

    # Compare IDS
    compare_list = compare_ids(proj_id_from_json, proj_on_file)

    if compare_list != proj_on_file and len(compare_list) != 0:
        id_file = open("ID_File.txt", "a")

        for i in compare_list:
            id_file.write(str(i) + ",")  # Write the IDs onto a file
        id_file.close()
        # Get Pipeline IDs infos from compared IDs
        pipe_id_list = []

        for project_path in project_paths:
            pipe_ids = get_ids(project_path)
            # Get Pipe ID paths from get_ids(), pipe_ids is all the pipeline IDs stats per project

            for pipe_id in pipe_ids:  # Use each ID to get the report from JSON file
                match_status_tags = ["ref", "sha", "id", "web_url", "created_at", "source"]
                if pipe_id['id'] in compare_list:  # Trace ID
                    report_dict = get_result_report(pipe_id['id'], project_path)
                    # Create path to report json then get a dictionary in return
                    print_dict = {key: pipe_id.get(key) for key in match_status_tags}
                    # reformat the dictionary
                    print_influx_protocol(print_dict, report_dict, project_path)
                    # print out the function

    elif len(compare_list) == 0:
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
                protocols()
            elif current_argument in ("-h", "--help"):
                print("Options:\t-m,--mock\t Mock Test\n"
                      "\t\t-l,--live\t Live Test")
            elif current_argument in ("-l", "--live"):
                protocols()
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)
