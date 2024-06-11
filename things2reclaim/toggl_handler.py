from toggl_python.entities import TimeEntry
import toggl_python
import tomllib
from pathlib import Path

from datetime import datetime, timedelta

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


def get_time_entries(since_days: int = 30):
    if since_days > 90:
        raise ValueError("since_days can't be more than 90 days")
    time_stamp = int((datetime.now() - timedelta(days=since_days)).timestamp())
    return toggl_python.TimeEntries(auth=auth).list(since=time_stamp)


def get_current_time_entry():
    time_entries = toggl_python.TimeEntries(auth=auth)
    time_entries.ADDITIONAL_METHODS = {
        "current": {
            "url": "me/time_entries/current",
            "entity": toggl_python.TimeEntry,
            "single_item": True,
        }
    }
    return time_entries.current()


def create_task_time_entry(description: str, project: str):
    if project not in project_dict.keys():
        raise ValueError(f"{project} is not an active toggl project")
    time_entry = TimeEntry(
        created_with="things-automation",
        wid=workspace.id,
        pid=project_dict[project].id,
        description=description,
        duration=-1,
    )
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
