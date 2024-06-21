from pytest import fixture

from datetime import datetime, timedelta
from dateutil import tz
from reclaim_sdk.models.task_event import ReclaimTaskEvent
from toggl_python import TimeEntry

from things2reclaim import utils

@fixture
def start_datetime():
    return datetime(2023,11,13,17,54,0, tzinfo=tz.gettz())

@fixture
def stop_datetime():
    return datetime(2023,11,13,21,24,0, tzinfo=tz.gettz())

@fixture
def title():
    return "Test Title"

@fixture
def correct_toggl_entry(start_datetime, stop_datetime, title) -> TimeEntry:
    return TimeEntry(wid=1337,pid=1337,duration=-1,start=start_datetime, stop=stop_datetime, description=title)

@fixture
def correct_reclaim_entry(start_datetime, stop_datetime, title) -> ReclaimTaskEvent:
    return ReclaimTaskEvent({"start" : start_datetime.isoformat(), "end" : stop_datetime.isoformat(), "title" : title})

def test_matching_time_entries(correct_toggl_entry, correct_reclaim_entry):
    assert utils.is_matching_time_entry(correct_toggl_entry, correct_reclaim_entry) == True

def test_start_diff_time_entries(correct_toggl_entry, correct_reclaim_entry):
    differed_toggl_entry = correct_toggl_entry
    differed_toggl_entry.start = differed_toggl_entry.start - timedelta(hours=1)
    assert utils.is_matching_time_entry(differed_toggl_entry, correct_reclaim_entry) == False

def test_stop_diff_time_entries(correct_toggl_entry, correct_reclaim_entry):
    differed_reclaim_entry = correct_reclaim_entry
    differed_reclaim_entry.end = differed_reclaim_entry.end - timedelta(hours=1)
    assert utils.is_matching_time_entry(correct_toggl_entry, differed_reclaim_entry) == False



