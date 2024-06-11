from typing import List
import tomllib
from pathlib import Path

from reclaim_sdk.models.task import ReclaimTask
from reclaim_sdk.client import ReclaimClient

CONFIG_PATH = Path("config/.reclaim.toml")

_config = {}

with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

RECLAIM_TOKEN = _config["reclaim_ai"]["token"]

ReclaimClient(token=RECLAIM_TOKEN)


def get_reclaim_tasks():
    return ReclaimTask.search()


def filter_for_subject(subject, tasks):
    return [task for task in tasks if task.name.startswith(subject)]


def create_reaclaim_task(**params):
    new_task = ReclaimTask(**params)
    new_task.save()


def get_reclaim_things_ids() -> List[str]:
    return [task.description.split(":")[1].strip() for task in ReclaimTask.search()]
