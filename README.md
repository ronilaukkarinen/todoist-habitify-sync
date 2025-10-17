# Todoist to Habitify sync

![bash](https://img.shields.io/badge/bash-%23121011.svg?style=for-the-badge&color=%23222222&logo=gnu-bash&logoColor=white)
![Todoist](https://img.shields.io/badge/todoist-badge?style=for-the-badge&logo=todoist&logoColor=%23ffffff&color=%23E44332)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

One-way synchronization from Todoist to Habitify. When you complete a Todoist task, it automatically marks the matching Habitify habit as done (based on task/habit name matching).

## Features

- Zero external dependencies (uses Python standard library only)
- One-way sync: Todoist → Habitify
- Name-based matching (case-insensitive)
- Tracks sync state to avoid duplicates
- Designed to run as a cronjob (every 5 minutes recommended)
- Checks completed tasks since last sync

## Prerequisites

- Python 3.6 or higher (no external packages needed!)
- Todoist API token
- Habitify API key
- Linux server with cron (or any system with cron-like scheduler)

## Cronjob

Add to crontab:

```cron
*/5 * * * * /path/to/todoist-habitify-sync/run-sync.sh 2>&1
```
