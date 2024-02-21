#!/opt/homebrew/Caskroom/miniconda/base/envs/things-automation/bin/python3

import things
from reclaim_sdk.models.task import ReclaimTask
from datetime import datetime


def extract_uni_projects():
    uni_area = next(area for area in things.areas() if area["title"] == "Uni")
    return things.projects(area=uni_area["uuid"])


def get_tasks_for_project(project):
    return things.tasks(project=project["uuid"], type="to-do")


def things_to_reclaim(things_task, project_title):
    with ReclaimTask() as reclaim_task:
        reclaim_task.name = "{} {}".format(project_title, things_task["title"])
        reclaim_task.start_date = datetime.strptime(
            things_task["start_date"], "%Y-%m-%d")
        reclaim_task.due_date = datetime.strptime(
            things_task["deadline"], "%Y-%m-%d")


def things_task_pretty_print(task, project_title):
    print(f"\tTitle: {project_title} {task['title']}")
    print(f"\tStart date: {task['start_date']}")
    print(f"\tDeadline: {task['deadline']}")


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
                things_task_pretty_print(things_task, project["title"])
                things_to_reclaim(things_task, project["title"])
            else:
                print(f"Task {things_task['title']} already exists in Reclaim")


if __name__ == "__main__":
    main()
