"""
scheduler_service.py
--------------------
Runs continuously in the background, checking schedule.json every 30 seconds.
When the current time reaches a scheduled ad's start time, it turns the ad
set ON. When it reaches the end time, it turns the ad set OFF.

This is SEPARATE from assistant.py on purpose: assistant.py needs your
microphone and attention. This scheduler should keep running quietly in the
background (even overnight) so the ad still fires even if you're not sitting
at the PC or the voice assistant isn't open.

Recommended: add this to Windows Task Scheduler to run at PC startup, so it
survives restarts. See README.md for how.
"""

import os
import json
import time
import datetime

import meta_ads

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.json")
LOG_PATH = os.path.join(BASE_DIR, "scheduler_log.txt")

CHECK_INTERVAL_SECONDS = 30


def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def parse_dt(date_str, time_str):
    return datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")


def process_schedule():
    config = load_json(CONFIG_PATH, {})
    access_token = config.get("meta_access_token", "")
    schedule = load_json(SCHEDULE_PATH, [])

    if not access_token:
        log("No meta_access_token set in config.json — cannot control ads yet.")
        return

    now = datetime.datetime.now()
    changed = False

    for job in schedule:
        status = job.get("status", "pending")
        if status == "done":
            continue

        start_dt = parse_dt(job["date"], job["start_time"])
        end_dt = parse_dt(job["date"], job["end_time"])
        ad_set_id = job["ad_set_id"]
        name = job.get("name", ad_set_id)

        if status == "pending" and now >= start_dt:
            success, msg = meta_ads.activate_ad_set(ad_set_id, access_token)
            log(f"START '{name}': {msg}")
            if success:
                job["status"] = "active"
                changed = True

        elif status == "active" and now >= end_dt:
            success, msg = meta_ads.pause_ad_set(ad_set_id, access_token)
            log(f"STOP '{name}': {msg}")
            if success:
                job["status"] = "done"
                changed = True

    if changed:
        save_json(SCHEDULE_PATH, schedule)


def main():
    log("Ad scheduler service started. Watching schedule.json every 30 seconds.")
    while True:
        try:
            process_schedule()
        except Exception as e:
            log(f"Error while processing schedule: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
