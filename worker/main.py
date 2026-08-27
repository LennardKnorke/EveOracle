# worker/main.py
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from worker.scheduled_tasks import (
    update_zkill_killmails,
    compress_oldest_zkill_year,
    update_prices,
)


scheduler = BlockingScheduler(
    timezone=ZoneInfo("Europe/Amsterdam")
)


scheduler.add_job(
    update_zkill_killmails,
    IntervalTrigger(seconds=20),
    id="update_zkill_killmails",
    max_instances=1,
    coalesce=True,
    misfire_grace_time=1,
)


scheduler.add_job(
    compress_oldest_zkill_year,
    IntervalTrigger(minutes=5),
    id="compress_oldest_zkill_year",
    max_instances=1,
    coalesce=True,
    misfire_grace_time=300,
)


scheduler.add_job(
    update_prices,
    CronTrigger(hour=14, minute=0),
    id="update_prices",
    max_instances=1,
    coalesce=True,
    misfire_grace_time=3600,
)


if __name__ == "__main__":
    print("Starting EveOracle worker...")
    scheduler.start()