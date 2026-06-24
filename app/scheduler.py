import asyncio

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.crawl import create_jobs, run_crawl_job


def trigger_scheduled_crawl(period: str, dispatch: bool = True) -> list[dict]:
    jobs = create_jobs(journal_ids=None, period=period, date_from=None, date_to=None)
    if dispatch:
        for job in jobs:
            asyncio.run(run_crawl_job(job["job_id"], job["journal_id"], job["date_from"], job["date_to"]))
    return jobs


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(trigger_scheduled_crawl, "cron", day="*", hour=2, args=["daily"], id="crawl-daily")
    scheduler.add_job(trigger_scheduled_crawl, "cron", day_of_week="mon", hour=3, args=["weekly"], id="crawl-weekly")
    scheduler.add_job(trigger_scheduled_crawl, "cron", day=1, hour=4, args=["monthly"], id="crawl-monthly")
    return scheduler
