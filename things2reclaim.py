#!/opt/homebrew/Caskroom/miniconda/base/envs/things-automation/bin/python3

import things
from reclaim_sdk.models.task import ReclaimTask
from datetime import datetime


def extract_uni_projects():
    uni_area = next(area for area in things.areas() if area["title"] == "Uni")
    return things.projects(area=uni_area["uuid"])


def get_tasks_for_project(project):
    return things.tasks(project=project["uuid"], type="to-do")


def set_default_reclaim_values(things_task, reclaim_task):
    reclaim_task.min_work_duration = 0.5
    reclaim_task.max_work_duration = 2
    reclaim_task.duration = 2
    if things_task.get("start_date") is not None:
        reclaim_task.start_date = datetime.strptime(
            f"{things_task['start_date']} 08:00", "%Y-%m-%d %H:%M")
    if things_task.get("deadline") is not None:
        reclaim_task.due_date = datetime.strptime(
            f"{things_task['deadline']} 22:00", "%Y-%m-%d %H:%M")


def calculate_time_on_unit(tag_value) -> float:
    value, unit = tag_value.split(" ")
    match unit:
        case 'hours' | 'hrs' | 'hour' | 'hr' | "h":
            return int(value)
        case "mins" | "min" | "minutes" | "minute" | "m":
            return int(value) / 60


def map_tag_values(things_task, reclaim_task):
    tags_dict = {k: v for (k, v) in [tag.split(": ")
                                     for tag in things_task["tags"]]}
    for tag in tags_dict:
        match tag:
            case "MinTime":
                reclaim_task.min_work_duration = calculate_time_on_unit(
                    tags_dict[tag])
            case "MaxTime":
                reclaim_task.max_work_duration = calculate_time_on_unit(
                    tags_dict[tag])
            case "EstimatedTime":
                reclaim_task.duration = calculate_time_on_unit(tags_dict[tag])
            case "DeadlineTime":
                if things_task.get('deadline') is not None:
                    reclaim_task.due_date = datetime.strptime(
                        f"{things_task['deadline']} {tags_dict[tag]}", "%Y-%m-%d %H:%M")
            case "StartTime":
                if things_task.get('start_date') is not None:
                    reclaim_task.start_date = datetime.strptime(
                        f"{things_task['start_date']} {tags_dict[tag]}", "%Y-%m-%d %H:%M")
            case _:
                print(f"Tag {tag} not recognized")


def things_to_reclaim(things_task, project_title):
    with ReclaimTask() as reclaim_task:
        reclaim_task.name = "{} {}".format(project_title, things_task["title"])
        set_default_reclaim_values(
            things_task=things_task, reclaim_task=reclaim_task)
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


def main():
    projects = extract_uni_projects()
    reclaim_task_names = [task.name for task in ReclaimTask().search()]
    for project in projects:
        things_tasks = get_tasks_for_project(project)
        for things_task in things_tasks:
            full_task_name = "{} {}".format(
                project["title"], things_task["title"])
            if full_task_name not in reclaim_task_names:
                print(f"Creating task {full_task_name} in Reclaim")
                # things_task_pretty_print(things_task, project["title"])
                things_to_reclaim(things_task, project["title"])
            else:
                print(f"Task {things_task['title']} already exists in Reclaim")


if __name__ == "__main__":
    main()
