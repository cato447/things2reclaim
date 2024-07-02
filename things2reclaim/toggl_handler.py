import difflib
from datetime import datetime, timedelta, date, time
import tomllib
from typing import List

import toggl_python
from better_rich_prompts.prompt import ListPrompt
from dateutil import tz
from toggl_python.entities import TimeEntry

import utils

_config = {}

CONFIG_PATH = utils.get_project_root() / "things2reclaim/config/.toggl.toml"
with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

TOKEN = _config["toggl_track"]["token"]

auth = toggl_python.TokenAuth(TOKEN)
workspace = toggl_python.Workspaces(auth=auth).list()[0]
project_dict = {
    project.name: project
    for project in toggl_python.Workspaces(auth=auth).projects(_id=workspace.id)
    if project.active
}
time_entry_editor = toggl_python.WorkspaceTimeEntries(
    auth=auth, workspace_id=workspace.id
)


def get_time_entry(time_entry_id: int) -> toggl_python.TimeEntry:
    return toggl_python.TimeEntries(auth=auth).retrieve(time_entry_id)


def delete_time_entry(time_entry_id: int) -> bool:
    return time_entry_editor.delete_timeentry(time_entry_id)


def get_start_time(time_entry: toggl_python.TimeEntry):
    return time_entry.start() if callable(time_entry.start) else time_entry.start


def get_stop_time(time_entry: toggl_python.TimeEntry):
    if time_entry.stop is None:
        raise ValueError(f"TimeEntry {time_entry.description} is still running")
    return time_entry.stop() if callable(time_entry.stop) else time_entry.stop


def get_time_entries_date_range(from_date: date, to_date: date):
    return toggl_python.TimeEntries(auth=auth).list(
        start_date=from_date.isoformat(), end_date=to_date.isoformat()
    )


def get_time_entries_since(since_days: int = 30) -> List[toggl_python.TimeEntry]:
    """
    get time entries since days at midnight
    """
    if since_days > 90:
        raise ValueError("since_days can't be more than 90 days")
    midnight = datetime.combine(datetime.now(tz.tzlocal()), time.min)
    time_stamp = int((midnight - timedelta(days=since_days)).timestamp())
    return toggl_python.TimeEntries(auth=auth).list(since=time_stamp)


def get_current_time_entry() -> TimeEntry | None:
    time_entries = toggl_python.TimeEntries(auth=auth)
    time_entries.ADDITIONAL_METHODS = {
        "current": {
            "url": "me/time_entries/current",
            "entity": toggl_python.TimeEntry,
            "single_item": True,
        }
    }
    return time_entries.current()


def get_tags() -> List[toggl_python.Tag]:
    return toggl_python.Workspaces(auth=auth).tags(_id=workspace.id)


def get_approriate_tag(description: str) -> str | None:
    tag_dict = {tag.name: tag for tag in get_tags()}
    parts = description.replace("VL", "Vorlesung").split(" ")
    possible_tags = set()
    for part in parts:
        possible_tags.update(difflib.get_close_matches(part, tag_dict.keys()))

    if not possible_tags:
        print("Found no matching tags")
        return None

    possible_tags = list(possible_tags)

    if len(possible_tags) == 1:
        return possible_tags[0]
    return ListPrompt.ask("Select the best fitting tag", possible_tags)


def create_task_time_entry(
    description: str, project: str, start: datetime | None = None, duration: int = -1
) -> toggl_python.TimeEntry:
    """
    duration is in seconds
    """
    if project not in project_dict.keys():
        raise ValueError(f"{project} is not an active toggl project")

    time_entry = TimeEntry(
        created_with="things-automation",
        wid=workspace.id,
        pid=project_dict[project].id,
        description=description,
        duration=duration,
    )

    if start is None:
        start = datetime.now(tz.tzutc())
    else:
        if start.tzinfo is None:
            raise ValueError("start has to be timezone aware")
        start = start.astimezone(tz.tzutc())

    time_entry.start = start

    tag = get_approriate_tag(description)
    if tag:
        time_entry.tags = [tag]

    return time_entry


def start_task(description: str, project: str):
    time_entry_editor.create(create_task_time_entry(description, project))


def stop_task(task: TimeEntry) -> TimeEntry | None:
    if time_entry_editor.DETAIL_URL is None:
        raise ValueError("DetailURL not set")

    url = time_entry_editor.BASE_URL.join(
        time_entry_editor.DETAIL_URL.format(id=task.id)
    )
    response = time_entry_editor.patch(url)
    data = response.json()
    if data:
        return TimeEntry(**data)


def stop_current_task():
    cur_task = get_current_time_entry()
    if cur_task is None:
        raise RuntimeError("No time entry is currently running")
    return stop_task(cur_task)
