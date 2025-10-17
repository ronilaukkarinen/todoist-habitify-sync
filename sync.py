#!/usr/bin/env python3
"""
Todoist to Habitify Sync Script
One-way sync: Completed Todoist tasks -> Habitify habit logs
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
import os
import sys

# Configuration
TODOIST_API_TOKEN = os.environ.get('TODOIST_API_TOKEN', '')
HABITIFY_API_KEY = os.environ.get('HABITIFY_API_KEY', '')
SYNC_STATE_FILE = os.path.join(os.path.dirname(__file__), '.sync_state.json')

# API Endpoints
TODOIST_COMPLETED_URL = 'https://api.todoist.com/sync/v9/completed/get_all'
HABITIFY_HABITS_URL = 'https://api.habitify.me/habits'
HABITIFY_LOGS_URL = 'https://api.habitify.me/logs'


def load_sync_state():
    """Load the last sync timestamp from state file"""
    if os.path.exists(SYNC_STATE_FILE):
        try:
            with open(SYNC_STATE_FILE, 'r') as f:
                state = json.load(f)
                return state.get('last_sync')
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_sync_state(timestamp):
    """Save the current sync timestamp to state file"""
    try:
        with open(SYNC_STATE_FILE, 'w') as f:
            json.dump({'last_sync': timestamp}, f)
    except IOError as e:
        print(f"Warning: Could not save sync state: {e}")


def make_request(url, headers, data=None, method='GET'):
    """Make an HTTP request using urllib"""
    try:
        if data:
            if method == 'POST':
                # For POST requests, send as form data
                data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
        else:
            req = urllib.request.Request(url, headers=headers, method=method)

        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return None


def get_completed_todoist_tasks(since_datetime):
    """Fetch completed Todoist tasks since the given datetime"""
    # Format: ISO 8601 datetime
    since_str = since_datetime.strftime('%Y-%m-%dT%H:%M')
    now_str = datetime.now().strftime('%Y-%m-%dT%H:%M')

    url = f"{TODOIST_COMPLETED_URL}?since={urllib.parse.quote(since_str)}&until={urllib.parse.quote(now_str)}"

    headers = {
        'Authorization': f'Bearer {TODOIST_API_TOKEN}'
    }

    print(f"Fetching Todoist tasks completed between {since_str} and {now_str}...")
    result = make_request(url, headers)

    if result and 'items' in result:
        return result['items']
    return []


def get_habitify_habits():
    """Fetch all Habitify habits"""
    headers = {
        'Authorization': HABITIFY_API_KEY
    }

    print("Fetching Habitify habits...")
    result = make_request(HABITIFY_HABITS_URL, headers)

    if result:
        # Debug: print the structure
        print(f"Debug - API response type: {type(result)}")
        print(f"Debug - API response keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        # Check if it's a dict with a 'data' key (common API pattern)
        if isinstance(result, dict) and 'data' in result:
            return result['data']
        return result
    return []


def create_habitify_log(habit_id, target_date, value=1, unit_type='rep'):
    """Create a log entry for a Habitify habit"""
    url = f"{HABITIFY_LOGS_URL}/{habit_id}"

    headers = {
        'Authorization': HABITIFY_API_KEY,
        'Content-Type': 'application/json'
    }

    data = json.dumps({
        'target_date': target_date,
        'value': value,
        'unit_type': unit_type
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"  Error creating log: {e.code} - {e.reason}")
        print(f"  Response body: {error_body}")
        return None
    except Exception as e:
        print(f"  Error creating log: {e}")
        return None


def sync_tasks():
    """Main sync function"""
    if not TODOIST_API_TOKEN:
        print("Error: TODOIST_API_TOKEN environment variable not set")
        sys.exit(1)

    if not HABITIFY_API_KEY:
        print("Error: HABITIFY_API_KEY environment variable not set")
        sys.exit(1)

    # Determine time range to check
    last_sync = load_sync_state()
    if last_sync:
        since_datetime = datetime.fromisoformat(last_sync)
        print(f"Last sync: {since_datetime}")
    else:
        # First run: check last 60 minutes
        since_datetime = datetime.now() - timedelta(minutes=60)
        print("First run: checking last 60 minutes")

    # Fetch completed Todoist tasks
    completed_tasks = get_completed_todoist_tasks(since_datetime)

    if not completed_tasks:
        print("No completed Todoist tasks found in this time range")
        save_sync_state(datetime.now().isoformat())
        return

    print(f"Found {len(completed_tasks)} completed Todoist task(s)")

    # Fetch Habitify habits
    habits = get_habitify_habits()

    if not habits:
        print("No Habitify habits found")
        save_sync_state(datetime.now().isoformat())
        return

    print(f"Found {len(habits)} Habitify habit(s)")

    # Create a mapping of habit names to habit IDs (case-insensitive)
    habit_map = {habit['name'].lower(): habit for habit in habits}

    # Sync completed tasks to Habitify
    synced_count = 0
    for task in completed_tasks:
        task_name = task['content']
        completed_at = task['completed_at']

        # Parse completed_at date
        try:
            completed_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            # Habitify expects ISO-8601 with timezone: 2021-05-21T07:00:00+07:00
            target_date = completed_date.strftime('%Y-%m-%dT%H:%M:%S%z')
            # Add colon in timezone offset (Python gives +0000, need +00:00)
            if len(target_date) >= 5 and target_date[-5] in '+-':
                target_date = target_date[:-2] + ':' + target_date[-2:]
        except Exception as e:
            print(f"  Error parsing date for '{task_name}': {e}")
            continue

        # Find matching habit by name (case-insensitive)
        matching_habit = habit_map.get(task_name.lower())

        if matching_habit:
            print(f"  Syncing: '{task_name}' (completed {target_date})")

            result = create_habitify_log(
                habit_id=matching_habit['id'],
                target_date=target_date
            )

            if result and result.get('status'):
                print(f"    ✓ Successfully logged to Habitify")
                synced_count += 1
            else:
                print(f"    ✗ Failed to log to Habitify")
        else:
            print(f"  Skipping: '{task_name}' (no matching Habitify habit)")

    print(f"\nSync complete: {synced_count}/{len(completed_tasks)} task(s) synced")

    # Save current timestamp
    save_sync_state(datetime.now().isoformat())


if __name__ == '__main__':
    sync_tasks()
