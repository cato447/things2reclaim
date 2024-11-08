from typing import Dict, List

from task_scheduler_client.configuration import Configuration
from task_scheduler_client.api.default_api import DefaultApi
from task_scheduler_client.api_client import ApiClient
from task_scheduler_client.models.task import Task

client = ApiClient(Configuration(host="http://localhost:8000"))
api = DefaultApi(client)

def get_tasks() -> List[Task]:
    return api.get_tasks_tasks_get()

def remap_dict_keys(params: Dict):
    key_mapping = {"min_work_duration": "min_time", "max_work_duration": "max_work", "duration": "estimated_time", "due_date": "deadline", "description": "things_id"}
    return {key_mapping.get(k,k): v for k, v in params.items()}

def remove_keys(params: Dict):
    keys_to_remove = {"tags"}
    return {k: v for k, v in params.items() if k not in keys_to_remove}

def change_value(params: Dict):
    keys_to_change = {"things_id": "things_task:"}
    return {k: (v if k not in keys_to_change else v.removeprefix(keys_to_change[k])) for k, v in params.items()}

def param_dict_to_task(params: Dict):
    remapped_keys = remap_dict_keys(params)
    stripped_keys = remove_keys(remapped_keys)
    return change_value(stripped_keys)

def create_task(task: Task):
    api.create_task_tasks_post(task)

def create_task_from_dict(params: Dict):
    params = param_dict_to_task(params)
    task = Task.from_dict(params)
    if task is None:
        raise ValueError
    api.create_task_tasks_post(task)

