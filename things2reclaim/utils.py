from datetime import datetime
import re
from typing import Union, Dict, TypeVar, List
import difflib

from better_rich_prompts.prompt import ListPrompt
from rich import print as rprint

import things_handler

TIME_PATTERN = (
    r"((\d+\.?\d*) (hours|hrs|hour|hr|h))? ?((\d+\.?\d*) (mins|min|minutes|minute|m))?"
)
pattern = re.compile(TIME_PATTERN)

T = TypeVar("T") # generic type

def calculate_time_on_unit(tag_value: str) -> float:
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


def map_tag_values(
    things_task,
    tags_dict: Dict[str, str],
    params: Dict[str, Union[str, datetime, float]],
):
    for tag, value in tags_dict.items():
        match tag:
            case "MinTime":
                params["min_work_duration"] = calculate_time_on_unit(value)
            case "MaxTime":
                params["max_work_duration "] = calculate_time_on_unit(value)
            case "DeadlineTime":
                if things_task.get("deadline") is not None:
                    params["due_date"] = datetime.strptime(
                        f"{things_task['deadline']} {value}", "%Y-%m-%d %H:%M"
                    )
            case "StartTime":
                if things_task.get("start_date") is not None:
                    params["start_date"] = datetime.strptime(
                        f"{things_task['start_date']} {value}",
                        "%Y-%m-%d %H:%M",
                    )
            case _:
                print(f"Tag {tag} not recognized")


def get_closest_match(name: str, candidates: Dict[str, T]) -> T | None:
    possible_candidates: List[str] = difflib.get_close_matches(name, candidates.keys())

    if not possible_candidates:
        return None
    if len(possible_candidates) == 1:
        return candidates[possible_candidates[0]]

    return candidates[ListPrompt.ask("Select a candidate", possible_candidates)]


def pinfo(msg: str):
    rprint(f"[bold white]{msg}[/bold white]")


def pwarning(msg: str):
    rprint(f"[bold yellow]Warning: {msg}[/bold yellow]")


def perror(msg: str):
    rprint(f"[bold red]Error: {msg}[/bold red]")


def generate_things_id_tag(things_task) -> str:
    return f"things_task:{things_task["uuid"]}"


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


def things_reclaim_is_equal(things_task, reclaim_task) -> bool:
    return things_handler.full_name(things_task=things_task) == reclaim_task.name
