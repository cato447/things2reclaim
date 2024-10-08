from typing import Dict, List
import tomllib

import things

from database_handler import UploadedTasksDB
import utils

_config = {}
CONFIG_PATH = utils.get_project_root() / "things2reclaim/config/.things2reclaim.toml"
with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)


DATABASE_PATH = utils.get_project_root() / _config["database"]["path"]


def extract_uni_projects():
    uni_area = next(area for area in things.areas() if area["title"] == "Uni")
    return things.projects(area=uni_area["uuid"])


def get_task(task_id: str):
    return things.get(task_id)


def get_task_by_name(task_name: str):
    tasks = {task["name"] : task for task in get_all_things_tasks()}
    if task_name not in tasks.keys():
        return utils.get_closest_match(task_name, tasks)
    else:
        return tasks[task_name]


def complete(task_id: str):
    things.complete(task_id)


def get_tasks_for_project(project) -> Dict | List[Dict]:
    return things.tasks(project=project["uuid"], type="to-do")


def is_equal_fullname(things_task: Dict, name: str):
    return full_name(things_task=things_task) == name


def get_all_things_tasks() -> List:
    tasks = []
    projects = extract_uni_projects()
    for project in projects:
        tasks += get_tasks_for_project(project)
    return tasks


def get_all_uploaded_things_tasks() -> List:
    tasks = []
    with UploadedTasksDB(DATABASE_PATH) as db:
        for task_id in db.get_all_uploaded_tasks():
            tasks.append(get_task(task_id))
    return tasks


def get_task_tags(things_task: Dict) -> Dict[str, str]:
    return dict([tag.split(": ") for tag in things_task["tags"]])


def full_name(things_task) -> str:
    return f"{things_task['project_title']} {things_task['title']}"


def get_course_names():
    projects = extract_uni_projects()
    return [course["title"] for course in projects]
