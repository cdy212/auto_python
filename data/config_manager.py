import json
import os
from .models import Job

CONFIG_FILE = 'jobs_config.json'

# 이 파일은 이전 아키텍처 제안과 동일합니다.
def save_jobs(jobs):
    try:
        jobs_as_dict = {name: job.to_dict() for name, job in jobs.items()}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(jobs_as_dict, f, indent=4)
        return True, f"Saved {len(jobs)} job(s)."
    except IOError as e:
        return False, f"ERROR: Failed to save config file: {e}"

def load_jobs():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            jobs_as_dict = json.load(f)
            jobs = {name: Job.from_dict(data) for name, data in jobs_as_dict.items()}
            return jobs
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading config file: {e}")
        return {}