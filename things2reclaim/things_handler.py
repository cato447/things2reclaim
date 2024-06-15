from typing import Dict, List
from pathlib import Path
import tomllib

import things

from things2reclaim.database_handler import UploadedTasksDB

_config = {}
CONFIG_PATH = Path("config/.things2reclaim.toml")
with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)


DATABASE_PATH = _config["database"]["path"]


def extract_uni_projects():
    uni_area = next(area for area in things.areas() if area["title"] == "Uni")
    return things.projects(area=uni_area["uuid"])


def get_task(task_id: int):
    return things.get(task_id)


def complete(task_id: int):
    things.complete(task_id)


def get_tasks_for_project(project) -> Dict | List[Dict]:
    return things.tasks(project=project["uuid"], type="to-do")


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
