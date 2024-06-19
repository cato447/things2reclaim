from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Pattern, Optional
import re

import emoji
import tomllib
from dateutil import tz
from reclaim_sdk.client import ReclaimClient
from reclaim_sdk.models.task import ReclaimTask
from reclaim_sdk.models.task_event import ReclaimTaskEvent

from deadline_status import DeadlineStatus 

CONFIG_PATH = Path("config/.reclaim.toml")

_config = {}

with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

RECLAIM_TOKEN = _config["reclaim_ai"]["token"]

THINGS_ID_PATTERN = "things_task:[a-zA-z0-9]+" 

things_id_pattern : Pattern[str] = re.compile(THINGS_ID_PATTERN)

ReclaimClient(token=RECLAIM_TOKEN)


def get_reclaim_tasks() -> List[ReclaimTask]:
    return ReclaimTask.search()


def get_reclaim_task_names(tasks : Optional[List[ReclaimTask]] = None):
    if not tasks:
        tasks = get_reclaim_tasks()
    return [task.name for task in tasks]


def filter_for_subject(subject, tasks):
    return [task for task in tasks if task.name.startswith(subject)]


def filter_for_deadline_status(cur_date : datetime, deadline_status : DeadlineStatus, tasks : List[ReclaimTask]):
    # [task for task in reclaim_tasks if task.due_date >= current_date]
    match deadline_status:
        case DeadlineStatus.FINE:
            return [task for task in tasks if (task.due_date and task.due_date >= cur_date)]
        case DeadlineStatus.OVERDUE:
            return [task for task in tasks if (task.due_date and task.due_date < cur_date)]
        case DeadlineStatus.NONE:
            return [task for task in tasks if task.due_date is None]


def get_project(task: ReclaimTask):
    return task.name.split(" ")[0]


def get_clean_time_entry_name(name : str):
    return emoji.replace_emoji(name).lstrip() 

def get_task_events_since(since_days: int = 0) -> List[ReclaimTaskEvent]:
    date_now = datetime.now(tz.tzutc()).date()
    date_since = date_now - timedelta(days=since_days)
    date_end = date_now + timedelta(days = 1) # end date is exclusive
    events = ReclaimTaskEvent.search(date_since, date_end)
    task_names = get_reclaim_task_names()
    print(task_names)
    [print(get_clean_time_entry_name(event.name)) for event in events]
    return [event for event in events if get_clean_time_entry_name(event.name) in task_names]


def get_events_date_range(from_date: date, to_date: date):
    return ReclaimTaskEvent.search(from_date, to_date)


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
        raise ValueError("Task is not scheduled")

    if not task.events:
        raise ValueError("Event list is empty")

    last_event: ReclaimTaskEvent = task.events[-1]

    last_event.start = start.astimezone(utc)
    last_event.end = end.astimezone(utc)
    last_event.save()


def finish_task(task: ReclaimTask):
    task.mark_complete()


def get_things_id(task: ReclaimTask):
    things_id_match = things_id_pattern.match(task.description)
    if things_id_match is None:
        raise ValueError(f"things id could not be found in description of reclaim task {task.name}")
    things_id_tag : str = things_id_match.group()

    return things_id_tag.split(":")[1]

def get_reclaim_things_ids() -> List[str]: 
    return [get_things_id(task) for task in ReclaimTask.search()]
