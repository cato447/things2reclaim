#!/opt/homebrew/Caskroom/miniconda/base/envs/things-automation/bin/python3

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import tomllib

from dateutil import tz
from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated
import typer

from things2reclaim import reclaim_handler
from things2reclaim import things_handler
from things2reclaim import toggl_handler
from things2reclaim import utils
from things2reclaim.database_handler import UploadedTasksDB


CONFIG_PATH = Path("config/.things2reclaim.toml")

_config = {}
with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

DATABASE_PATH = _config["database"]["path"]

app = typer.Typer(
    add_completion=False, no_args_is_help=True, pretty_exceptions_enable=False
)
console = Console()


def complete_task_name(incomplete: str):
    for name in [task.name for task in reclaim_handler.get_reclaim_tasks()]:
        print(name)
        if name.startswith(incomplete):
            yield name


def things_to_reclaim(things_task):
    tags = things_handler.get_task_tags(things_task)
    estimated_time = tags.get("EstimatedTime")
    if estimated_time is None:
        raise ValueError("EstimatedTime tag is required")
    estimated_time = utils.calculate_time_on_unit(estimated_time)
    del tags["EstimatedTime"]

    params = {
        "name": things_handler.full_name(things_task),
        "description": utils.generate_things_id_tag(things_task),
        "tags": things_handler.get_task_tags(things_task),
        "min_work_duration": estimated_time,
        "max_work_duration": estimated_time,
        "duration": estimated_time,
    }

    if things_task.get("start_date"):
        params["start_date"] = datetime.strptime(
            f"{things_task['start_date']} 08:00", "%Y-%m-%d %H:%M"
        )
    if things_task.get("deadline"):
        params["due_date"] = datetime.strptime(
            f"{things_task['deadline']} 22:00", "%Y-%m-%d %H:%M"
        )

    utils.map_tag_values(things_task, tags, params)

    reclaim_handler.create_reaclaim_task_from_dict(params)


@app.command("init")
def initialize_uploaded_database(verbose: bool = False):
    """
    Initializes the uploaded tasks database
    """
    reclaim_things_uuids = reclaim_handler.get_reclaim_things_ids()
    added_tasks = 0
    with UploadedTasksDB(DATABASE_PATH) as db:
        for task_id in reclaim_things_uuids:
            try:
                db.add_uploaded_task(task_id)
                added_tasks += 1
            except sqlite3.IntegrityError as e:
                if verbose:
                    print(
                        f"Task with ID {task_id} already in database | Exception: {e}"
                    )
                else:
                    continue

    if added_tasks == 0:
        print("uploaded_tasks table is already initialized")
    else:
        print(
            f"Added {added_tasks} task{'s' if added_tasks > 1 else ''} to uploaded_tasks table"
        )


@app.command("upload")
def upload_things_to_reclaim(verbose: bool = False):
    """
    Upload things tasks to reclaim
    """
    projects = things_handler.extract_uni_projects()
    reclaim_task_names = [task.name for task in reclaim_handler.get_reclaim_tasks()]
    tasks_uploaded = 0
    with UploadedTasksDB(DATABASE_PATH) as db:
        for project in projects:
            things_tasks = things_handler.get_tasks_for_project(project)
            for things_task in things_tasks:
                full_task_name = things_handler.full_name(things_task=things_task)
                if full_task_name not in reclaim_task_names:
                    tasks_uploaded += 1
                    print(f"Creating task {full_task_name} in Reclaim")
                    things_to_reclaim(things_task)
                    db.add_uploaded_task(things_task["uuid"])
                else:
                    if verbose:
                        print(f"Task {things_task['title']} already exists in Reclaim")
    if tasks_uploaded == 0:
        rprint("No new tasks were found")
    elif tasks_uploaded == 1:
        rprint(f"Uploaded {tasks_uploaded} task{'s' if tasks_uploaded  > 1 else ''}")


@app.command("list")
def list_reclaim_tasks(subject: Annotated[Optional[str], typer.Argument()] = None):
    """
    List all current tasks
    """
    reclaim_tasks = reclaim_handler.get_reclaim_tasks()
    if subject is not None:
        reclaim_tasks = reclaim_handler.filter_for_subject(subject, reclaim_tasks)
    current_date = datetime.now(tz.tzutc())
    table = Table("Index", "Task", "Days left", title="Task list")
    for index, task in enumerate(reclaim_tasks):
        if current_date > task.due_date:
            days_behind = (current_date - task.due_date).days
            table.add_row(
                f"({index + 1})",
                task.name,
                Text(f"{days_behind} days overdue", style="bold red"),
            )
        else:
            days_left = (task.due_date - current_date).days
            table.add_row(
                f"({index + 1})",
                task.name,
                Text(f"{days_left} days left", style="bold white"),
            )
    console.print(table)


@app.command("start")
def start_task(
    task_name_parts: Annotated[List[str], typer.Argument(help="Task to start")],
):
    task_name = (" ").join(task_name_parts)
    tasks: Dict[str, reclaim_handler.ReclaimTask] = {
        task.name: task for task in reclaim_handler.get_reclaim_tasks()
    }
    if task_name not in tasks.keys():
        task = utils.get_closest_match(task_name, tasks)
        if task is None:
            utils.perror(f"No task with name {task_name} found")
            return
    else:
        task = tasks[task_name]

    current_task = toggl_handler.get_current_time_entry()
    if current_task is not None:
        utils.perror("Toggl Track is already running")
        return

    toggl_handler.start_task(task.name, reclaim_handler.get_project(task))
    reclaim_handler.start_task(task)
    print(f"Started task {task.name}")


@app.command("stop")
def stop_task():
    current_task = toggl_handler.get_current_time_entry()
    if current_task is None:
        utils.perror("No task is currently tracked in toggl")
        return

    stopped_task_name = current_task.description

    if stopped_task_name is None:
        utils.perror("Current toggl task has no name")
        return

    reclaim_dict = {task.name: task for task in reclaim_handler.get_reclaim_tasks()}

    if stopped_task_name in reclaim_dict.keys():
        stopped_task = reclaim_dict[stopped_task_name]
    else:
        stopped_task = utils.get_closest_match(stopped_task_name, reclaim_dict)

        if stopped_task is None:
            utils.perror(f"{stopped_task} not found in reclaim")
            return
    stop_time = datetime.now(tz.tzutc())
    if callable(current_task.start):
        current_task.start = current_task.start()

    toggl_handler.stop_current_task()

    if stopped_task.is_scheduled:
        reclaim_handler.log_work_for_task(stopped_task, current_task.start, stop_time)

        is_task_finished = Confirm.ask("Is task finished?", default=False)
        if is_task_finished:
            reclaim_handler.finish_task(stopped_task)
            rprint(f"Finished {stopped_task.name}")
    else:
        utils.pwarning("Work could not be logged in reclaim[")
    time_format = "%H:%M"
    local_zone = tz.gettz()
    rprint(
        f"""Logged work from {current_task.start.astimezone(local_zone).strftime(time_format)}
        to {stop_time.astimezone(local_zone).strftime(time_format)} for {stopped_task.name}"""
    )


@app.command("stats")
def show_task_stats():
    """
    Show task stats
    """
    current_date = datetime.now(tz.tzutc())
    reclaim_tasks = reclaim_handler.get_reclaim_tasks()
    tasks_fine = [task for task in reclaim_tasks if task.due_date >= current_date]
    tasks_overdue = [task for task in reclaim_tasks if task.due_date < current_date]

    fine_per_course = ["Fine"]
    overdue_per_course = ["Overdue"]
    course_names = things_handler.get_course_names()
    for course_name in course_names:
        fine_per_course.append(
            str(len(reclaim_handler.filter_for_subject(course_name, tasks_fine)))
        )
        overdue_per_course.append(
            str(len(reclaim_handler.filter_for_subject(course_name, tasks_overdue)))
        )

    table = Table(*(["Status"] + course_names))
    table.add_row(*fine_per_course)
    table.add_row(*overdue_per_course)

    console.print(table)


@app.command("time")
def print_time_needed():
    """
    Print sum of time needed for all reclaim tasks
    """
    tasks = reclaim_handler.get_reclaim_tasks()
    time_needed = 0

    for task in tasks:
        time_needed += task.duration

    print(f"Time needed to complete {len(tasks)} Tasks: {time_needed} hrs")
    print(f"Average time needed to complete a Task: {time_needed/len(tasks):.2f} hrs")

    try:
        tasks.sort(key=lambda x: x.scheduled_start_date)
    except TypeError:
        print("To many to-dos on list. Not all are scheduled")
        return
    last_task_date = tasks[-1].scheduled_start_date
    today = datetime.now(tz.tzutc())

    print(
        f"""Last task is scheduled for {last_task_date.strftime('%d.%m.%Y')}
        ({last_task_date - today} till completion)"""
    )


@app.command("finished")
def remove_finished_tasks_from_things():
    """
    Complete finished reclaim tasks in things
    """
    reclaim_things_uuids = reclaim_handler.get_reclaim_things_ids()
    finished_someting = False
    with UploadedTasksDB(DATABASE_PATH) as db:
        for task in things_handler.get_all_uploaded_things_tasks():
            if task["uuid"] not in reclaim_things_uuids:
                finished_someting = True
                print(
                    f"Found completed task: {things_handler.full_name(things_task=task)}"
                )
                things_handler.complete(task["uuid"])
                db.remove_uploaded_task(task["uuid"])

    if not finished_someting:
        print("Reclaim and Things are synced")


@app.command("sync")
def sync_things_and_reclaim(verbose: bool = False):
    """
    Sync tasks between things and reclaim
    First updated all finished tasks in reclaim to completed in things
    Then upload all new tasks from things to reclaim
    """
    utils.pinfo("Pulling from Reclaim")
    remove_finished_tasks_from_things()
    rprint("---------------------------------------------")
    utils.pinfo("Pushing to Reclaim")
    upload_things_to_reclaim(verbose=verbose)
    rprint("---------------------------------------------")


if __name__ == "__main__":
    app()
