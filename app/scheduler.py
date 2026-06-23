from apscheduler.schedulers.background import BackgroundScheduler

from app.services.crawl import create_jobs


def trigger_scheduled_crawl(period: str) -> list[dict]:
    return create_jobs(journal_ids=None, period=period, date_from=None, date_to=None)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(trigger_scheduled_crawl, "cron", day="*", hour=2, args=["daily"], id="crawl-daily")
    scheduler.add_job(trigger_scheduled_crawl, "cron", day_of_week="mon", hour=3, args=["weekly"], id="crawl-weekly")
    scheduler.add_job(trigger_scheduled_crawl, "cron", day=1, hour=4, args=["monthly"], id="crawl-monthly")
    return scheduler

