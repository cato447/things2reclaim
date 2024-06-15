import difflib
from datetime import datetime, timedelta
from pathlib import Path
import tomllib

import toggl_python
from better_rich_prompts.prompt import ListPrompt
from dateutil import tz
from toggl_python.entities import TimeEntry

_config = {}

CONFIG_PATH = Path("config/.toggl.toml")
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


def get_time_entry(time_entry_id: int):
    return toggl_python.TimeEntries(auth=auth).retrieve(time_entry_id)


def get_time_entries(since_days: int = 30):
    if since_days > 90:
        raise ValueError("since_days can't be more than 90 days")
    time_stamp = int((datetime.now() - timedelta(days=since_days)).timestamp())
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


def get_tags():
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
):
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

    if start is not None:
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


def stop_current_task():
    cur_task = get_current_time_entry()
    if cur_task is None:
        raise RuntimeError("No time entry is currently running")
    if time_entry_editor.DETAIL_URL is None:
        raise ValueError("DetailURL not set")
    url = time_entry_editor.BASE_URL.join(
        time_entry_editor.DETAIL_URL.format(id=cur_task.id)
    )

    return time_entry_editor.patch(url)
