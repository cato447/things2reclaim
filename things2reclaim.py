#!/opt/homebrew/Caskroom/miniconda/base/envs/things-automation/bin/python3

import re
from datetime import date, datetime, timedelta
from time import sleep
from typing import Dict, List, Optional

import things
import typer
from pytz import timezone
from reclaim_sdk.models.task import ReclaimTask
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()

regex = (
    r"((\d+\.?\d*) (hours|hrs|hour|hr|h))? ?((\d+\.?\d*) (mins|min|minutes|minute|m))?"
)
pattern = re.compile(regex)


def extract_uni_projects():
    uni_area = next(area for area in things.areas() if area["title"] == "Uni")
    return things.projects(area=uni_area["uuid"])


def get_tasks_for_project(project) -> Dict | List[Dict]:
    return things.tasks(project=project["uuid"], type="to-do")


def get_task_tags(things_task: Dict) -> Dict[str, str]:
    return {k: v for (k, v) in [tag.split(": ") for tag in things_task["tags"]]}


def set_default_reclaim_values(things_task, reclaim_task):
    tags_dict = get_task_tags(things_task)
    estimated_time = tags_dict.get("EstimatedTime")
    if estimated_time is None:
        raise ValueError("EstimatedTime tag is required")
    estimated_time = calculate_time_on_unit(estimated_time)
    reclaim_task.min_work_duration = estimated_time
    reclaim_task.max_work_duration = estimated_time
    reclaim_task.duration = estimated_time
    if things_task.get("start_date") is not None:
        reclaim_task.start_date = datetime.strptime(
            f"{things_task['start_date']} 08:00", "%Y-%m-%d %H:%M"
        )
    if things_task.get("deadline") is not None:
        reclaim_task.due_date = datetime.strptime(
            f"{things_task['deadline']} 22:00", "%Y-%m-%d %H:%M"
        )


def calculate_time_on_unit(tag_value) -> float | None:
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


def map_tag_values(things_task, reclaim_task):
    tags_dict = get_task_tags(things_task)
    for tag in tags_dict:
        match tag:
            case "MinTime":
                reclaim_task.min_work_duration = calculate_time_on_unit(tags_dict[tag])
            case "MaxTime":
                reclaim_task.max_work_duration = calculate_time_on_unit(tags_dict[tag])
            case "DeadlineTime":
                if things_task.get("deadline") is not None:
                    reclaim_task.due_date = datetime.strptime(
                        f"{things_task['deadline']} {tags_dict[tag]}", "%Y-%m-%d %H:%M"
                    )
            case "StartTime":
                if things_task.get("start_date") is not None:
                    reclaim_task.start_date = datetime.strptime(
                        f"{things_task['start_date']} {tags_dict[tag]}",
                        "%Y-%m-%d %H:%M",
                    )
            case _:
                print(f"Tag {tag} not recognized")


def generate_things_id_tag(things_task) -> str:
    return f"things_task:{things_task["uuid"]}"


def things_to_reclaim(things_task, project_title):
    with ReclaimTask() as reclaim_task:
        reclaim_task.name = "{} {}".format(project_title, things_task["title"])
        reclaim_task.description = generate_things_id_tag(things_task=things_task)
        set_default_reclaim_values(things_task=things_task, reclaim_task=reclaim_task)
        map_tag_values(things_task=things_task, reclaim_task=reclaim_task)
        reclaim_task_pretty_print(reclaim_task)


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


def full_name(things_task) -> str:
    return f"{things_task['project_title']} {things_task['title']}"


def get_all_things_tasks() -> List:
    tasks = []
    projects = extract_uni_projects()
    for project in projects:
        tasks += get_tasks_for_project(project)
    return tasks


def things_reclaim_is_equal(things_task, reclaim_task) -> bool:
    return full_name(things_task=things_task) == reclaim_task.name


def get_course_names():
    projects = extract_uni_projects()
    return [course["title"] for course in projects]


@app.command("upload")
def upload_things_to_reclaim(verbose: bool = False):
    """
    Upload things tasks to reclaim
    """
    projects = extract_uni_projects()
    reclaim_task_names = [task.name for task in ReclaimTask().search()]
    tasks_uploaded = 0
    for project in projects:
        things_tasks = get_tasks_for_project(project)
        for things_task in things_tasks:
            full_task_name = full_name(things_task=things_task)
            if full_task_name not in reclaim_task_names:
                tasks_uploaded += 1
                print(f"Creating task {full_task_name} in Reclaim")
                things_to_reclaim(things_task, project["title"])
            else:
                if verbose:
                    print(f"Task {things_task['title']} already exists in Reclaim")
    if tasks_uploaded == 0:
        rprint("No new tasks were found")
    elif tasks_uploaded == 1:
        rprint(f"Uploaded {tasks_uploaded} task{'s' if tasks_uploaded  > 1 else ''}")


def get_subject_reclaim_tasks(subject, tasks):
    return [task for task in tasks if task.name.startswith(subject)]


@app.command("list")
def list_reclaim_tasks(subject: Annotated[Optional[str], typer.Argument()] = None):
    """
    List all current tasks
    """
    reclaim_tasks = ReclaimTask().search()
    if subject is not None:
        reclaim_tasks = get_subject_reclaim_tasks(subject, reclaim_tasks)
    current_date = datetime.now().replace(tzinfo=timezone("UTC"))
    table = Table("Index", "Task", "Days left", title="Task list")
    for id, task in enumerate(reclaim_tasks):
        if current_date > task.due_date:
            days_behind = (current_date - task.due_date).days
            table.add_row(
                f"({id + 1})",
                task.name,
                Text(f"{days_behind} days overdue", style="bold red"),
            )
        else:
            days_left = (task.due_date - current_date).days
            table.add_row(
                f"({id + 1})",
                task.name,
                Text(f"{days_left} days left", style="bold white"),
            )
    console.print(table)


@app.command("stats")
def show_task_stats():
    """
    Show task stats
    """
    current_date = datetime.now().replace(tzinfo=timezone("UTC"))
    reclaim_tasks = ReclaimTask().search()
    tasks_fine = [task for task in reclaim_tasks if task.due_date >= current_date]
    tasks_overdue = [task for task in reclaim_tasks if task.due_date < current_date]

    fine_per_course = ["Fine"]
    overdue_per_course = ["Overdue"]
    course_names = get_course_names()
    for course_name in course_names:
        fine_per_course.append(
            str(len(get_subject_reclaim_tasks(course_name, tasks_fine)))
        )
        overdue_per_course.append(
            str(len(get_subject_reclaim_tasks(course_name, tasks_overdue)))
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
    tasks = ReclaimTask.search()
    tasks.sort(key=lambda x: x.scheduled_start_date)

    time_needed = 0

    for task in tasks:
        time_needed += task.duration

    print(f"Time needed to complete {len(tasks)} Tasks: {time_needed} hrs")
    print(f"Average time needed to complete a Task: {time_needed/len(tasks):.2f} hrs")

    last_task_date = tasks[-1].scheduled_start_date
    today = datetime.now().replace(tzinfo=timezone("UTC"))

    print(
        f"Last task is scheduled for {last_task_date.strftime('%d.%m.%Y')} ({last_task_date - today} till completion)"
    )


@app.command("finished")
def remove_finished_tasks_from_things():
    """
    Complete finished reclaim tasks in things
    """
    reclaim_things_uuids = [
        task.description.split(":")[1].strip() for task in ReclaimTask.search()
    ]
    finished_someting = False
    for task in get_all_things_tasks():
        if task["uuid"] not in reclaim_things_uuids:
            finished_someting = True
            print(f"Found completed task: {full_name(things_task=task)}")
            things.complete(task["uuid"])

    if not finished_someting:
        print("Reclaim and Things are synced")


@app.command("sync")
def sync_things_and_reclaim(verbose: bool = False):
    """
    Sync tasks between things and reclaim
    First updated all finished tasks in reclaim to completed in things
    Then upload all new tasks from things to reclaim
    """
    rprint("[bold white]Pulling from Reclaim[/bold white]")
    remove_finished_tasks_from_things()
    rprint("---------------------------------------------")
    sleep(2)
    rprint("[bold white]Pushing to Reclaim[/bold white]")
    upload_things_to_reclaim(verbose=verbose)
    rprint("---------------------------------------------")


if __name__ == "__main__":
    app()
