

import logging
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

GOMA_TZ = pytz.timezone(settings.TIMEZONE)

scheduler = BackgroundScheduler(timezone=GOMA_TZ)




def _job_mark_absent() -> None:
    from app.services.attendance_service import mark_absent_employees

    db = SessionLocal()
    try:
        count = mark_absent_employees(db)
        logger.info("[SCHEDULER:absent] %d employees marked ABSENT", count)
    except Exception as exc:
        logger.error("[SCHEDULER:absent] ERROR: %s", exc, exc_info=True)
    finally:
        db.close()


def _job_sync_hikvision() -> None:
    from app.services.attendance_service import sync_with_hikvision

    db = SessionLocal()
    try:
        r = sync_with_hikvision(db)
        if r.new_scans:
            logger.info(
                "[SCHEDULER:sync] %d new scan(s) | %d attendance updated",
                r.new_scans, r.attendance_updated,
            )
        else:
            logger.debug(
                "[SCHEDULER:sync] No new scans — fetched=%d "
                "skip: %d anon | %d dup | %d unknown | %d parse_err",
                r.total_fetched,
                r.skipped_no_id, r.skipped_duplicate,
                r.skipped_unknown, r.skipped_parse_error,
            )
    except Exception as exc:
        logger.warning("[SCHEDULER:sync] Error: %s", exc)
    finally:
        db.close()


def _job_startup_sync() -> None:
    logger.info("[SCHEDULER:startup] Running startup catch-up sync")
    _job_sync_hikvision()




def start_scheduler() -> None:
    scheduler.add_job(
        _job_mark_absent,
        CronTrigger(hour=8, minute=21, day_of_week="mon-fri", timezone=GOMA_TZ),
        id="mark_absent",
        replace_existing=True,
        misfire_grace_time=120,
        coalesce=True,
    )

    scheduler.add_job(
        _job_sync_hikvision,
        IntervalTrigger(seconds=30, timezone=GOMA_TZ),
        id="sync_hikvision",
        replace_existing=True,
        misfire_grace_time=30,
        coalesce=True,
    )

    startup_run_at = datetime.now(GOMA_TZ) + timedelta(seconds=10)
    scheduler.add_job(
        _job_startup_sync,
        DateTrigger(run_date=startup_run_at, timezone=GOMA_TZ),
        id="startup_sync",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "[SCHEDULER] Started — tz=%s | sync@30s | absent@08:21(mon-fri) | startup@+10s",
        GOMA_TZ,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Stopped")
