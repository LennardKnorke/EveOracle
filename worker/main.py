# worker/main.py

from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shared.config import logger
from worker.tasks.killmails import update_zkill_killmails, init_killmails
from worker.tasks.itemprices import update_prices, init_prices
from worker.tasks.shipstats import update_ship_stats, init_shipstats



scheduler = BlockingScheduler(
    timezone=ZoneInfo("Europe/Amsterdam")
)

scheduler.add_job(
    update_zkill_killmails,
    IntervalTrigger(hours=2),
    id="update_zkill_killmails",
    max_instances=1,
    coalesce=True
)


scheduler.add_job(
    update_ship_stats,
    IntervalTrigger(hours=2),
    id="update_ship_stats",
    max_instances=1,
    coalesce=True
)

scheduler.add_job(
    update_prices,
    IntervalTrigger(hours=2),
    id="update_prices",
    max_instances=1,
    coalesce=True
)


if __name__ == "__main__":
    logger.info("Initiating EveOracle worker...")
    init_prices()
    init_shipstats()
    init_killmails()

    logger.info("Starting EveOracle worker...")
    scheduler.start()