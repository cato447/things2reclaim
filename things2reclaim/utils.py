from datetime import datetime, timedelta
import re
from typing import Union, Dict, TypeVar, List, Optional
import difflib
from dateutil import tz

import emoji
from pathlib import Path
from better_rich_prompts.prompt import ListPrompt
from rich import print as rprint
from toggl_python import TimeEntry
from reclaim_sdk.models.task_event import ReclaimTaskEvent

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


def get_start_time(toggl_time_entry: TimeEntry):
    return toggl_time_entry.start() if callable(toggl_time_entry.start) else toggl_time_entry.start


def get_stop_time(time_entry: TimeEntry):
    if time_entry.stop is None:
        return get_start_time(time_entry) + timedelta(seconds=time_entry.duration) 
    else:
        return time_entry.stop() if callable(time_entry.stop) else time_entry.stop


def get_clean_time_entry_name(name : str):
    return emoji.replace_emoji(name).lstrip() 


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


def nearest_time_entry(items: Optional[List[ReclaimTaskEvent]], pivot: TimeEntry) -> Optional[ReclaimTaskEvent]:
    if not items:
        return None
    return min(items, key=lambda x: abs(x.start - get_start_time(pivot)))


def is_matching_time_entry(toggl_time_entry : Optional[TimeEntry], reclaim_time_entry : Optional[ReclaimTaskEvent]):
    if toggl_time_entry is None or reclaim_time_entry is None:
        print("One is none")
        return False
    if toggl_time_entry.description != get_clean_time_entry_name(reclaim_time_entry.name):
        print(f"toggl title: {toggl_time_entry.description}")
        print(f"reclaim title: {get_clean_time_entry_name(reclaim_time_entry.name)}")
        return False

    toggl_start = get_start_time(toggl_time_entry)
    toggl_stop = get_stop_time(toggl_time_entry)
    reclaim_start = reclaim_time_entry.start
    reclaim_end = reclaim_time_entry.end

    if toggl_start.tzinfo is None:
        raise ValueError("Toggl start is not timezone aware.")
    if toggl_stop.tzinfo is None:
        raise ValueError("Toggl stop is not timezone aware.")
    if reclaim_start.tzinfo is None:
        raise ValueError("Reclaim start is not timezone aware.")
    if reclaim_end.tzinfo is None:
        raise ValueError("Reclaim stop is not timezone aware.")

    if toggl_start.astimezone(tz.tzutc()) != reclaim_start.astimezone(tz.tzutc()):
        print(f"toggl_start: {toggl_start.isoformat()}")
        print(f"reclaim_start: {reclaim_start.isoformat()}")
        return False
    if toggl_stop.astimezone(tz.tzutc()) != reclaim_end.astimezone(tz.tzutc()):
        print(f"toggl_end: {toggl_stop.isoformat()}")
        print(f"reclaim_end: {reclaim_end.isoformat()}")
        return False
    return True

def pinfo(msg: str):
    rprint(f"[bold white]{msg}[/bold white]")


def pwarning(msg: str):
    rprint(f"[bold yellow]Warning: {msg}[/bold yellow]")


def perror(msg: str):
    rprint(f"[bold red]Error: {msg}[/bold red]")


def plogtime(start_time: datetime, end_time: datetime, task_name: str):
    time_format = "%H:%M"
    local_zone = tz.gettz()

    if start_time.tzinfo is None:
        raise ValueError("start_time has to be timezone aware.")

    if end_time.tzinfo is None:
        raise ValueError("end_time has to be timezone aware.")


    rprint(
        (f"Logged work from {start_time.astimezone(local_zone).strftime(time_format)} "
         f"to {end_time.astimezone(local_zone).strftime(time_format)} for {task_name}")
    )


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


def get_project_root() -> Path:
    return Path(__file__).parent.parent
