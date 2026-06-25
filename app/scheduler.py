import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.crawl import create_jobs, run_crawl_job


SCHEDULED_CRAWL_JOBS = [
    {
        "id": "crawl-daily",
        "period": "daily",
        "trigger": "cron",
        "schedule": "day=*, hour=2",
        "timezone": "UTC",
        "cron": {"day": "*", "hour": 2},
    },
    {
        "id": "crawl-weekly",
        "period": "weekly",
        "trigger": "cron",
        "schedule": "day_of_week=mon, hour=3",
        "timezone": "UTC",
        "cron": {"day_of_week": "mon", "hour": 3},
    },
    {
        "id": "crawl-monthly",
        "period": "monthly",
        "trigger": "cron",
        "schedule": "day=1, hour=4",
        "timezone": "UTC",
        "cron": {"day": 1, "hour": 4},
    },
]


def trigger_scheduled_crawl(period: str, dispatch: bool = True) -> list[dict]:
    jobs = create_jobs(journal_ids=None, period=period, date_from=None, date_to=None)
    if dispatch:
        for job in jobs:
            asyncio.run(run_crawl_job(job["job_id"], job["journal_id"], job["date_from"], job["date_to"]))
    return jobs


def scheduled_crawl_jobs() -> list[dict]:
    return [{key: value for key, value in job.items() if key != "cron"} for job in SCHEDULED_CRAWL_JOBS]


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    for job in SCHEDULED_CRAWL_JOBS:
        scheduler.add_job(
            trigger_scheduled_crawl,
            job["trigger"],
            args=[job["period"]],
            id=job["id"],
            **job["cron"],
        )
    return scheduler
