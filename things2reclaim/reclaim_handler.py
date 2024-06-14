from datetime import datetime
from pathlib import Path
from typing import List, Dict

import tomllib
from dateutil import tz
from reclaim_sdk.client import ReclaimClient
from reclaim_sdk.models.task import ReclaimTask
from reclaim_sdk.models.task_event import ReclaimTaskEvent

CONFIG_PATH = Path("config/.reclaim.toml")

_config = {}

with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

RECLAIM_TOKEN = _config["reclaim_ai"]["token"]

ReclaimClient(token=RECLAIM_TOKEN)


def get_reclaim_tasks() -> List[ReclaimTask]:
    return ReclaimTask.search()


def filter_for_subject(subject, tasks):
    return [task for task in tasks if task.name.startswith(subject)]


def get_project(task: ReclaimTask):
    return task.name.split(" ")[0]


def start_task(task: ReclaimTask):
    task.prioritize()


def create_reaclaim_task_from_dict(params: Dict):
    new_task = ReclaimTask()
    for key, value in params.items():
        setattr(new_task, key, value)
    new_task.save()


def log_work_for_task(task: ReclaimTask, start: datetime, end: datetime):
    """
    start and end are in Europe/Berlin timezone
    """
    utc = tz.tzutc()
    if start.tzinfo is None:
        raise ValueError("start is not timezone aware")

    if end.tzinfo is None:
        raise ValueError("end is not timezone aware")

    if not task.is_scheduled:
        raise RuntimeError("Task is not scheduled")

    last_event: ReclaimTaskEvent = task.events[-1]

    last_event.start = start.astimezone(utc)
    last_event.end = end.astimezone(utc)
    last_event._update()


def finish_task(task: ReclaimTask):
    task.mark_complete()


def get_reclaim_things_ids() -> List[str]:
    return [task.description.split(":")[1].strip() for task in ReclaimTask.search()]
