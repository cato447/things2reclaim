#!/opt/homebrew/Caskroom/miniconda/base/envs/things-automation/bin/python3

import things
from reclaim_sdk.models.task import ReclaimTask
from datetime import datetime
import argparse
from typing import Dict, List
import re

regex = (
    r"((\d+\.?\d*) (hours|hrs|hour|hr|h))? ?((\d+\.?\d*) (mins|min|minutes|minute|m))?"
)
pattern = re.compile(regex)


def extract_uni_projects():
    uni_area = next(area for area in things.areas() if area["title"] == "Uni")
    return things.projects(area=uni_area["uuid"])


def get_tasks_for_project(project) -> Dict | List[Dict]:
    return things.tasks(project=project["uuid"], type="to-do")


def get_task_tags(things_task: Dict) -> Dict[str, str]:
    return {k: v for (k, v) in [tag.split(": ") for tag in things_task["tags"]]}


def set_default_reclaim_values(things_task, reclaim_task):
    tags_dict = get_task_tags(things_task)
    estimated_time = tags_dict.get("EstimatedTime")
    if estimated_time is None:
        raise ValueError("EstimatedTime tag is required")
    estimated_time = calculate_time_on_unit(estimated_time)
    reclaim_task.min_work_duration = estimated_time
    reclaim_task.max_work_duration = estimated_time
    reclaim_task.duration = estimated_time
    if things_task.get("start_date") is not None:
        reclaim_task.start_date = datetime.strptime(
            f"{things_task['start_date']} 08:00", "%Y-%m-%d %H:%M"
        )
    if things_task.get("deadline") is not None:
        reclaim_task.due_date = datetime.strptime(
            f"{things_task['deadline']} 22:00", "%Y-%m-%d %H:%M"
        )


def calculate_time_on_unit(tag_value) -> float | None:
    # This is a regex to match time in the format of 1h 30m
    # Minutes are optional if hours are present
    # Hours are optional if minutes are present
    # The regex will match two words when the correct format is found (format and emtpy word)
    values = pattern.findall(tag_value)
    time = 0
    if len(values) != 2:
        raise ValueError("Invalid time format")
    _, hours, _, _, mins, _ = values[0]
    if "" == hours and "" == mins:
        raise ValueError("Regex matched empty string")
    if "" != hours:
        time += float(hours)
    if "" != mins:
        time += float(mins) / 60

    return time


def list_reclaim_tasks():
    reclaim_tasks = ReclaimTask().search()
    for id, task in enumerate(reclaim_tasks):
        print(f"({id + 1}) {task.name} ")


def map_tag_values(things_task, reclaim_task):
    tags_dict = get_task_tags(things_task)
    for tag in tags_dict:
        match tag:
            case "MinTime":
                reclaim_task.min_work_duration = calculate_time_on_unit(tags_dict[tag])
            case "MaxTime":
                reclaim_task.max_work_duration = calculate_time_on_unit(tags_dict[tag])
            case "DeadlineTime":
                if things_task.get("deadline") is not None:
                    reclaim_task.due_date = datetime.strptime(
                        f"{things_task['deadline']} {tags_dict[tag]}", "%Y-%m-%d %H:%M"
                    )
            case "StartTime":
                if things_task.get("start_date") is not None:
                    reclaim_task.start_date = datetime.strptime(
                        f"{things_task['start_date']} {tags_dict[tag]}",
                        "%Y-%m-%d %H:%M",
                    )
            case _:
                print(f"Tag {tag} not recognized")


def things_to_reclaim(things_task, project_title):
    with ReclaimTask() as reclaim_task:
        reclaim_task.name = "{} {}".format(project_title, things_task["title"])
        set_default_reclaim_values(things_task=things_task, reclaim_task=reclaim_task)
        map_tag_values(things_task=things_task, reclaim_task=reclaim_task)
        reclaim_task_pretty_print(reclaim_task)


def things_task_pretty_print(task, project_title):
    print(f"\tTitle: {project_title} {task['title']}")
    print(f"\tStart date: {task['start_date']}")
    print(f"\tDeadline: {task['deadline']}")
    print(f"\tTags: {task['tags']}")


def reclaim_task_pretty_print(task):
    print(f"\tTitle: {task.name}")
    print(f"\tStart date: {task.start_date}")
    print(f"\tDeadline: {task.due_date}")
    print(f"\tMin work duration: {task.min_work_duration}")
    print(f"\tMax work duration: {task.max_work_duration}")
    print(f"\tDuration: {task.duration}")


def sync_things_to_reclaim():
    projects = extract_uni_projects()
    reclaim_task_names = [task.name for task in ReclaimTask().search()]
    for project in projects:
        things_tasks = get_tasks_for_project(project)
        for things_task in things_tasks:
            full_task_name = "{} {}".format(project["title"], things_task["title"])
            if full_task_name not in reclaim_task_names:
                print(f"Creating task {full_task_name} in Reclaim")
                things_to_reclaim(things_task, project["title"])
            else:
                print(f"Task {things_task['title']} already exists in Reclaim")


def print_time_needed():
    tasks = ReclaimTask.search()
    time_needed = 0
    for task in tasks:
        time_needed += task.duration

    print(f"Time needed to complete {len(tasks)} Tasks: {time_needed} hrs")
    print(f"Average time needed to complete a Task: {time_needed/len(tasks):.2f} hrs")


def main():
    parser = argparse.ArgumentParser(description="Sync Things 3 tasks to Reclaim")
    parser.add_argument("action", help="list, sync")
    args = parser.parse_args()
    match args.action:
        case "list":
            list_reclaim_tasks()
        case "sync":
            sync_things_to_reclaim()
        case "time":
            print_time_needed()
        case _:
            print("Invalid action")


if __name__ == "__main__":
    main()
